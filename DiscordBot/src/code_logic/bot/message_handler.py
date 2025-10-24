"""Message handling layer for the bot.

Contains :class:`MessageHandler` which validates JSON configuration for
monitored websites, ensures required database tables exist, and exposes
helpers to check website status and content.
"""

from typing import List, Tuple, Dict, Any, Optional, Union, cast

import re
import requests
from urllib3 import util as uurlib3

from display_tty import Disp

from ..sql import SQL
from ..program_globals import constants as CONST
from ..program_globals.helpers import initialise_logger


class MessageHandler:
    """Process and validate website message configurations and manage table setup.

    Validates the JSON schema for website monitoring, ensures required
    database tables exist and exposes routines used by the bot to check
    website status and log results.
    """

    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(self, sql_connection: SQL, message_schema: List[Any], debug: bool = False) -> None:
        """Initialize the MessageHandler.

        Args:
            sql_connection (SQL): Database access facade.
            message_schema (List[Any]): Raw JSON schema describing websites.
            debug (bool): Enable debug logging.
        """
        self.debug: bool = debug
        self.connection: SQL = sql_connection
        self.message_schema: List[Any] = message_schema
        self.processed_json: List[CONST.WebsiteNode] = []
        self.cleaned_urls: Dict[str, str] = {}
        self.disp.update_disp_debug(self.debug)

    def _clean_url(self, raw_url: str) -> str:
        self.disp.log_debug(
            f"Checking if the unprocessed url '({raw_url})' has a verified instance in the cache url."
        )
        if raw_url in self.cleaned_urls:
            self.disp.log_debug("Found the url in the cache.")
            return self.cleaned_urls[raw_url]
        self.disp.log_debug(
            "Unprocessed url not present in the cache, converting and adding."
        )
        decomposed_url_node: uurlib3.Url = uurlib3.parse_url(raw_url)
        self.disp.log_debug(f"Decomposed url: {decomposed_url_node}")
        host: str = decomposed_url_node.host if decomposed_url_node.host else ""
        self.disp.log_debug(f"Located host : '{host}'")
        scheme: str = f"{decomposed_url_node.scheme}://" if decomposed_url_node.scheme else ""
        self.disp.log_debug(f"Located scheme : '{scheme}'")
        port: str = f":{decomposed_url_node.port}" if decomposed_url_node.port else ""
        self.disp.log_debug(f"Located port : '{port}'")
        final_url: str = f"{scheme}{host}{port}"
        self.disp.log_debug(f"Processed url: '{final_url}'")
        self.cleaned_urls[raw_url] = final_url
        self.disp.log_debug("Processed url added to cache.")
        return final_url

    def _make_human_readable(self, url: str, status: CONST.WebsiteStatus) -> str:
        cleaned_url: str = self._clean_url(url)
        if status == CONST.UP:
            return f":green_circle: Website '({cleaned_url})' is UP and Operational"
        if status == CONST.PARTIALLY_UP:
            return f":yellow_circle: Website '({cleaned_url})' is UP but NOT Operational"
        if status == CONST.DOWN:
            return f":red_circle: Website '({cleaned_url})' is DOWN"
        return f":purple_circle: Website '({cleaned_url})' has an unhandled status '({status})'"

    def _check_if_keyword_in_content(self, needle: str, haystack: str, case_sensitive: bool = False) -> bool:
        self.disp.log_debug(f"Case sensitive: {case_sensitive}")
        needle_cleaned: str = re.sub(r'\\s+', ' ', needle)
        if not case_sensitive:
            needle_cleaned = needle_cleaned.lower()
        self.disp.log_debug(f" Normalized needle: '{needle_cleaned}'")
        haystack_cleaned: str = re.sub(r'\\s+', ' ', haystack)
        if not case_sensitive:
            haystack_cleaned = haystack_cleaned.lower()
        haystack_cleaned = haystack_cleaned.strip()
        self.disp.log_debug(
            f"1rst 500 characters of the normalized haystack: '{haystack_cleaned[:500]}'"
        )
        found: bool = needle_cleaned in haystack_cleaned
        self.disp.log_debug(f"Needle found: {found}")
        return found

    def _check_deadchecks(self, request: requests.Response, dead_checks: List[CONST.DeadCheck], default: CONST.WebsiteStatus = CONST.WS.UP) -> CONST.WebsiteStatus:
        website_response: str = request.text
        website_response_lower: str = ""
        _tmp_response: str = ""
        _tmp_dead_check: str = ""
        for check in dead_checks:
            _tmp_response = ""
            _tmp_dead_check = ""
            if check.case_sensitive is False:
                if website_response_lower == "":
                    website_response_lower = website_response.lower()
                _tmp_response = website_response_lower
                _tmp_dead_check = check.keyword.lower()
            else:
                _tmp_response = website_response
                _tmp_dead_check = check.keyword
            if self._check_if_keyword_in_content(_tmp_dead_check, _tmp_response, True):
                return check.response
        return default

    def _check_website_status_and_content(self, website: CONST.WebsiteNode, dead_checks: List[CONST.DeadCheck]) -> CONST.WebsiteStatus:
        """Check the website status and content.

        The check is case-insensitive, ignores extra whitespace and allows
        for partial matches.

        Args:
            url (str): The url to query.
            keyword (str): The keyword to search for in the page.

        Returns:
            str: Status string describing the result.
        """
        _url: str = website.url
        _status: int = website.expected_status
        _keyword: str = website.expected_content
        _case_sensitive: bool = website.case_sensitive
        try:
            # Timeout after 5 seconds
            response = requests.get(_url, timeout=5)
            if response.status_code == _status:
                # Normalize whitespace and lowercase
                found: bool = self._check_if_keyword_in_content(
                    _keyword,
                    response.text,
                    _case_sensitive
                )
                self.disp.log_debug(f"Keyword found: {found}")
                if found:
                    self.disp.log_info(f"Website '{_url}' is up.")
                    return self._check_deadchecks(response, dead_checks, CONST.WS.UP)
                self.disp.log_warning(f"Website '{_url}' is partially up.")
                return self._check_deadchecks(response, dead_checks, CONST.WS.PARTIALLY_UP)
            self.disp.log_warning(f"Websie '{_url}' is down.")
            return self._check_deadchecks(response, dead_checks, CONST.WS.DOWN)
        except requests.exceptions.RequestException:
            self.disp.log_warning(f"Websie '{_url}' is down.")
            return CONST.WS.DOWN

    async def _check_connection(self, website: CONST.WebsiteNode) -> Union[CONST.QueryStatus, int]:
        """Function in charge of logging the status of the checked website.

        Args:
            url (str): The string of the url to check.

        Returns:
            int: The check status.
        """
        _qs: CONST.QueryStatus = CONST.QueryStatus()
        _qs.website_id = await self._get_website_id(website.url)
        if not _qs.website_id:
            self.disp.log_error(
                f"Website '{website.url}' not found in the database.")
            return CONST.ERROR
        _qs.status = self._check_website_status_and_content(
            website,
            website.dead_checks
        )
        return _qs

    async def _get_website_id(self, url: str) -> Union[int, None]:
        if url == "":
            self.disp.log_warning("Empty url provided.")
            return None
        source_table: str = CONST.SQLITE_TABLE_NAME_MESSAGES
        table_content: Union[int, List[Tuple[str, Any]]] = await self.connection.get_data_from_table(source_table, 'id', f"url='{url}'", False)
        self.disp.log_debug(f"Gathered data = {table_content}")
        if isinstance(table_content, int):
            self.disp.log_error(
                f"Failed to retrieve the id column name from the table '{table_content}'."
            )
            return None
        table_id_cleaned: Optional[int] = None
        if isinstance(table_content, List):
            if isinstance(table_content[0], Tuple):
                if isinstance(table_content[0][0], int):
                    table_id_cleaned = table_content[0][0]
        self.disp.log_debug(f"table_id_cleaned: {table_id_cleaned}")
        if not table_id_cleaned:
            self.disp.log_error(
                f"Expected to get a table id of type int but got '{type(table_id_cleaned)}', this could be because the url is not present in the '({source_table})'"
            )
            return None
        return table_id_cleaned

    async def _initialise_table(self) -> int:
        """Create required tables in the database if they do not exist.

        Returns:
            int: CONST.SUCCESS on success or CONST.ERROR on failure.
        """
        try:
            tables = await self.connection.get_table_names()
            self.disp.log_debug(f"available tables {tables}")
            if isinstance(tables, int):
                tables = []
            for name, structure in CONST.SQLITE_MESSAGE_HANDLER_TABLES.items():
                if name not in tables:
                    self.disp.log_debug(
                        f"Table '{name}' not found, creating"
                    )
                    status = await self.connection.create_table(
                        name,
                        structure
                    )
                    self.disp.log_debug(f"Creation status: {status}")
                    if status != CONST.SUCCESS:
                        self.disp.log_error(f"Failed to create table: '{name}")
                        return status
                else:
                    self.disp.log_debug(f"Table '{name}' found, leaving as is")
            return CONST.SUCCESS
        except RuntimeError as e:
            self.disp.log_error(
                f"Failed to create the required tables. Error: {e}"
            )
            return CONST.ERROR

    async def _set_up_trigger(self) -> int:
        triggers: Union[int, List[str]] = await self.connection.get_trigger_names()
        if isinstance(triggers, int):
            self.disp.log_error(
                "Failed to gather the triggers from the database.")
            return CONST.ERROR
        self.disp.log_debug(f"Gathered triggers: {triggers}")
        if CONST.SQLITE_MESSAGE_TRIGGER_NAME not in triggers:
            status: int = await self.connection.create_trigger(
                CONST.SQLITE_TABLE_NAME_MESSAGES,
                CONST.SQLITE_MESSAGE_TRIGGER
            )
            if status != CONST.SUCCESS:
                self.disp.log_error(
                    f"Failed to create trigger: {CONST.SQLITE_MESSAGE_TRIGGER_NAME}"
                )
            return status
        self.disp.log_debug(
            f"Trigger {CONST.SQLITE_MESSAGE_TRIGGER_NAME} already exists, ignoring."
        )
        return CONST.SUCCESS

    def _mark_corrupted(self, message: str) -> bool:
        """Log a warning that a JSON node is corrupted and return True.

        Args:
            message (str): Warning message to emit.

        Returns:
            bool: Always True to indicate corruption.
        """
        self.disp.log_warning(message)
        return True

    def _validate_json_node_value(self, json_data: Dict[str, Any], schema: CONST.JSON_KEY_TYPE) -> Union[Any, CONST.JSONDataNotFound]:
        """Validate a single JSON node value against the expected schema.

        Args:
            json_data (Dict[str, Any]): The JSON object to inspect.
            schema (CONST.JSON_KEY_TYPE): Tuple of (key_name, expected_type).

        Returns:
            Union[Any, CONST.JSONDataNotFound]: The value if valid or a JSONDataNotFound marker.
        """
        key_name, expected_type = schema
        for json_key, value in json_data.items():
            if json_key.lower() == key_name.lower():
                if isinstance(value, expected_type):
                    return value
                self.disp.log_warning(
                    f"Key '{json_key}' expected type '{expected_type.__name__}', got '{type(value).__name__}'"
                )
                return CONST.JSONDataNotFound(json_key)
        return CONST.JSONDataNotFound(str(schema[0]))

    def _validate_deadcheck(self, check_data: Dict[str, Any]) -> Union[CONST.DeadCheck, int]:
        """Validate a single dead_check item from configuration.

        Returns a :class:`CONST.DeadCheck` on success or CONST.ERROR on failure.
        """
        corrupted_data: bool = False
        dc: CONST.DeadCheck = CONST.DeadCheck()
        _class_node: Union[Any, CONST.JSONDataNotFound] = self._validate_json_node_value(
            check_data,
            CONST.JSON_DEADCHECKS_KEYWORD
        )
        if isinstance(_class_node, CONST.JSONDataNotFound):
            corrupted_data = self._mark_corrupted(str(_class_node))
        else:
            dc.keyword = _class_node
        _class_node: Union[Any, CONST.JSONDataNotFound] = self._validate_json_node_value(
            check_data,
            CONST.JSON_DEADCHECKS_RESPONSE
        )
        if isinstance(_class_node, CONST.JSONDataNotFound):
            corrupted_data = self._mark_corrupted(str(_class_node))
        else:
            _response: str = _class_node
            if _response.lower() not in CONST.WEBSITE_STATUS:
                corrupted_data = self._mark_corrupted(
                    f"Unknown response type, you provided '({_response})' but expected values were '({' or '.join(CONST.WEBSITE_STATUS)})'"
                )
            else:
                _tmp: str = _response.lower()
                dc.response = CONST.WEBSITE_STATUS[_tmp]
        _class_node: Union[Any, CONST.JSONDataNotFound] = self._validate_json_node_value(
            check_data,
            CONST.JSON_DEADCHECKS_CASE_SENSITIVE
        )
        if isinstance(_class_node, CONST.JSONDataNotFound):
            self.disp.log_warning(
                f"The deadcheck case sensitive is not specified, using default case sensitivity value '({CONST.DEFAULT_CASE_SENSITIVITY})'"
            )
            dc.case_sensitive = CONST.DEFAULT_CASE_SENSITIVITY
        else:
            dc.case_sensitive = _class_node
        if corrupted_data:
            self.disp.log_error(
                "One or more values of the website item are corrupted, please check warning above for more information."
            )
            return CONST.ERROR
        return dc

    def _validate_deadchecks(self, deadchecks: List[Dict[str, Union[str, int]]]) -> Union[List[CONST.DeadCheck], int]:
        """Validate a list of dead_check entries.

        Returns a list of :class:`CONST.DeadCheck` objects or CONST.ERROR.
        """
        _dead_checks: List[CONST.DeadCheck] = []
        for check_data in deadchecks:
            if len(check_data) == 0:
                self.disp.log_warning(
                    f"You submitted an empty dead_check instance, you submitted '({check_data})' of type '({type(check_data)})', skipping."
                )
                continue
            check = self._validate_deadcheck(check_data)
            if not isinstance(check, CONST.DeadCheck):
                self.disp.log_critical(
                    "An error occurred during the verification of the DeadChecks"
                )
                return CONST.ERROR
            _dead_checks.append(check)
        return _dead_checks

    def _validate_website(self, node: Dict[str, Any]) -> Union[CONST.WebsiteNode, int]:
        """Validate a single website configuration node and return a WebsiteNode.

        Returns:
            Union[CONST.WebsiteNode, int]: Validated WebsiteNode or CONST.ERROR.
        """
        # Create and return the WebsiteNode instance
        corrupted_data: bool = False
        _wn: CONST.WebsiteNode = CONST.WebsiteNode()
        _items: Dict[CONST.JSON_KEY_TYPE, str] = {
            CONST.JSON_NAME: "name",
            CONST.JSON_URL: "url",
            CONST.JSON_CHANNEL: "channel",
            CONST.JSON_EXPECTED_CONTENT: "expected_content",
            CONST.JSON_EXPECTED_STATUS: "expected_status",
        }
        for key, value in _items.items():
            _class_node: Union[Any, CONST.JSONDataNotFound] = self._validate_json_node_value(
                node,
                key
            )
            if isinstance(_class_node, CONST.JSONDataNotFound):
                corrupted_data = self._mark_corrupted(str(_class_node))
            else:
                setattr(_wn, value, _class_node)

        _class_node: Union[Any, CONST.JSONDataNotFound] = self._validate_json_node_value(
            node,
            CONST.JSON_CASE_SENSITIVE
        )
        if isinstance(_class_node, CONST.JSONDataNotFound):
            self.disp.log_warning(
                f"The website key case sensitive is not specified, using default case sensitivity value '({CONST.DEFAULT_CASE_SENSITIVITY})'"
            )
            _wn.case_sensitive = CONST.DEFAULT_CASE_SENSITIVITY
        else:
            _wn.case_sensitive = _class_node

        _class_node: Union[Any, CONST.JSONDataNotFound] = self._validate_json_node_value(
            node,
            CONST.JSON_DEADCHECKS
        )
        if isinstance(_class_node, list):
            _validate_dead_check_node: Union[List[CONST.DeadCheck], int] = self._validate_deadchecks(
                cast(List[Dict[str, str | int]], _class_node)
            )
            if isinstance(_validate_dead_check_node, List):
                _wn.dead_checks = _validate_dead_check_node
            else:
                corrupted_data = True
        if corrupted_data:
            self.disp.log_error(
                "One or more values of the website item are corrupted, please check warning above for more information."
            )
            return CONST.ERROR
        return _wn

    def _validate_json(self) -> int:
        """Function in charge of checking and validating that the json provided structure was valid.

        Returns:
            int: The status of the check, SUCCESS if no errors were found, ERROR otherwise
        """
        self.processed_json = []
        node: List[Any] = self.message_schema
        if not isinstance(node, List):
            self.disp.log_error(
                "Invalid json format, expected the base to be a list"
            )
            return CONST.ERROR
        for item in node:
            if not isinstance(item, Dict):
                self.disp.log_error(
                    f"Invalid json format, the node: '{item}' should be a dictionnary (or json object) not '{type(item)}'"
                )
                return CONST.ERROR
            website: Union[
                CONST.WebsiteNode,
                int
            ] = self._validate_website(item)
            if not isinstance(website, CONST.WebsiteNode):
                self.disp.log_critical(
                    "An error occurred while checking the provided json data."
                )
                return CONST.ERROR
            self.processed_json.append(website)
        self.disp.log_debug(f"Processed json: {self.processed_json}")
        return CONST.SUCCESS

    async def _update_message_table(self, websites: CONST.WebsiteNode) -> int:
        table: str = CONST.SQLITE_TABLE_NAME_MESSAGES
        columns: Union[List[str], int] = await self.connection.get_table_column_names(table)
        if isinstance(columns, int):
            self.disp.log_error(
                f"Failed to retrieve the column names from the '{table}' table."
            )
            return CONST.ERROR
        self.disp.log_debug(f"Table '{table}' columns: '{columns}'")
        columns_cleaned: List[str] = columns[1:-2]
        self.disp.log_debug(
            f"Table '{table}' columns_cleaned: '{columns_cleaned}'")
        data: List[str] = [
            websites.name,
            "NULL",
            websites.url,
            str(websites.channel),
            websites.expected_content,
            str(websites.expected_status)
        ]
        status: int = await self.connection.insert_or_update_data_into_table(
            table,
            data,
            columns_cleaned
        )
        return status

    async def _update_dead_checks_table(self, websites: CONST.WebsiteNode) -> int:
        dest_table: str = CONST.SQLITE_TABLE_NAME_DEAD_CHECKS
        table_id_raw: Union[int, None] = await self._get_website_id(websites.url)
        if table_id_raw is None:
            self.disp.log_error(
                f"Could not obtain the main table's id from the website's url '({websites.url})'"
            )
            return CONST.ERROR
        table_id_cleaned_str: str = str(table_id_raw)
        columns: Union[List[str], int] = await self.connection.get_table_column_names(dest_table)
        if isinstance(columns, int):
            self.disp.log_error(
                f"Failed to retrieve the column names from the '{dest_table}' table."
            )
            return CONST.ERROR
        self.disp.log_debug(f"Table '{dest_table}' columns: '{columns}'")
        columns_cleaned: List[str] = columns[1:]
        self.disp.log_debug(
            f"Table '{dest_table}' columns_cleaned: '{columns_cleaned}'"
        )
        buffer: List[List[str]] = []
        for index, item in enumerate(websites.dead_checks):
            self.disp.log_debug(f"Prepping deadcheck {index}: {item}")
            data: List[str] = [
                table_id_cleaned_str,
                item.keyword,
                str(item.response.value),
            ]
            buffer.append(data)
        status: int = await self.connection.insert_or_update_data_into_table(
            dest_table,
            buffer,
            columns_cleaned
        )
        return status

    async def _update_status_history_table(self, websites: CONST.WebsiteNode) -> int:
        dest_table: str = CONST.SQLITE_TABLE_NAME_STATUS_HISTORY
        columns: Union[List[str], int] = await self.connection.get_table_column_names(dest_table)
        if isinstance(columns, int):
            self.disp.log_error(
                f"Failed to retrieve the column names from the '{dest_table}' table."
            )
            return CONST.ERROR
        self.disp.log_debug(f"Table '{dest_table}' columns: '{columns}'")
        columns_cleaned: List[str] = columns[1:-1]
        self.disp.log_debug(
            f"Table '{dest_table}' columns_cleaned: '{columns_cleaned}'"
        )
        status_check: Union[
            CONST.QueryStatus,
            int
        ] = await self._check_connection(websites)
        if not isinstance(status_check, CONST.QueryStatus):
            self.disp.log_error(
                f"Failed to check the website's '{websites.url}' status."
            )
            return CONST.ERROR
        self.disp.log_debug(f"Prepping status check {status_check}")
        data: List[str] = [
            str(status_check.website_id),
            str(status_check.status.value),
        ]
        self.disp.log_debug("Writing check to the database")
        status: int = await self.connection.insert_or_update_data_into_table(
            dest_table,
            data,
            columns_cleaned
        )
        return status

    async def _update_table_content(self) -> int:
        """Function in charge of filling the table with the content of the json config

        Returns:
            int: The filling status.
        """
        for website in self.processed_json:
            status: int = await self._update_message_table(website)
            if status != CONST.SUCCESS:
                self.disp.log_error(
                    f"Failed to insert or update message {website.url} in table {CONST.SQLITE_TABLE_NAME_MESSAGES}"
                )
                return CONST.ERROR
            status: int = await self._update_dead_checks_table(website)
            if status != CONST.SUCCESS:
                self.disp.log_error(
                    f"Failed to insert or update message {website.url} in table {CONST.SQLITE_TABLE_NAME_DEAD_CHECKS}"
                )
                return CONST.ERROR
            status: int = await self._update_status_history_table(website)
            if status != CONST.SUCCESS:
                self.disp.log_error(
                    f"Failed to obtain the website's status '({website.url})'"
                )
                return CONST.ERROR
        return CONST.SUCCESS

    async def boot_up(self) -> int:
        """Function containing the steps for the class to properly start up.

        Returns:
            int: The run status of the class
        """
        status: int = await self._initialise_table()
        if status != CONST.SUCCESS:
            self.disp.log_error("The initialisation of the tables failed.")
            return CONST.ERROR
        status: int = await self._set_up_trigger()
        if status != CONST.SUCCESS:
            self.disp.log_error("The setting up of the trigger failed.")
            return CONST.ERROR
        status: int = self._validate_json()
        if status != CONST.SUCCESS:
            self.disp.log_error("Invalid Json config file structure")
            return CONST.ERROR
        status: int = await self._update_table_content()
        if status != CONST.SUCCESS:
            self.disp.log_error(
                "Failed to update the table content with the configuration content"
            )
            return CONST.ERROR
        return CONST.SUCCESS

    async def run(self) -> None:
        """Function in charge of running the logic of the bot's mainloop"""
        return
