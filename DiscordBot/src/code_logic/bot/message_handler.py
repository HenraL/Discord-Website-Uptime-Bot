"""Message handling layer for the bot.

Contains :class:`MessageHandler` which validates JSON configuration for
monitored websites, ensures required database tables exist, and exposes
helpers to check website status and content.
"""

from typing import List, Tuple, Dict, Any, Optional, Union, Iterable, cast, overload

from datetime import datetime, timedelta, date, timezone

from collections import defaultdict

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

    def __init__(self, sql_connection: SQL, message_schema: List[Any], output_mode: Optional[CONST.OutputMode] = None, debug: bool = False) -> None:
        """Initialize the MessageHandler.

        Args:
            sql_connection (SQL): Database access facade.
            message_schema (List[Any]): Raw JSON schema describing websites.
            debug (bool): Enable debug logging.
        """
        self.debug: bool = debug
        self.boot_called: bool = False
        self.output_mode: CONST.OutputMode = CONST.OutputMode.RAW
        self.set_output_type(output_mode)
        self.connection: SQL = sql_connection
        self.message_schema: List[Any] = message_schema
        self.processed_json: List[CONST.WebsiteNode] = []
        self.cleaned_urls: Dict[str, str] = {}
        self.disp.update_disp_debug(self.debug)

    def set_output_type(self, mode: Optional[CONST.OutputMode]) -> None:
        if not mode or mode not in CONST.OutputMode:
            self.output_mode = CONST.OM.RAW
            self.disp.log_warning(
                f"The provided mode is unknown, defaulting to {str(self.output_mode)}"
            )
            return
        self.disp.log_info(f"Output mode set to {mode.name}")
        self.output_mode = mode

    def get_output_mode(self) -> CONST.OutputMode:
        return self.output_mode

    def _clean_url(self, raw_url: str) -> str:
        """Normalize a raw URL to its base (scheme + host + optional port).

        The result is cached in ``self.cleaned_urls`` for subsequent calls.

        Args:
            raw_url (str): The raw URL to normalise.

        Returns:
            str: Normalized base URL (e.g. "https://example.com:8080").
        """
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

    def _get_last_update_human_date(self) -> Union[str, Tuple[str, str]]:
        """Return a human-readable "last updated" string formatted per output mode.

        Returns either a plain string or a tuple suitable for embed fields.
        """
        _current_date = self.connection.get_correct_now_value()
        self.disp.log_debug(f"Current date: {_current_date}")
        if self.output_mode == CONST.OM.MARKDOWN:
            _final = f"**Last updated**: {_current_date}"
        elif self.output_mode == CONST.OM.EMBED:
            return ("Last updated", f"{_current_date}")
        else:
            _final = f"Last updated: {_current_date}"
        return _final

    def _get_desired_timeframes(self) -> Dict[str, date]:
        """Return a mapping of timeframe keys to cutoff dates.

        The keys are the constants (day/week/month/year) used elsewhere
        to aggregate uptime statistics.
        """
        _now = datetime.now(timezone.utc).date()
        ranges = {
            CONST.TIMEFRAME_DAY: _now - timedelta(days=1),
            CONST.TIMEFRAME_WEEK: _now - timedelta(weeks=1),
            CONST.TIMEFRAME_MONTH: _now - timedelta(days=30),
            CONST.TIMEFRAME_YEAR: _now - timedelta(days=365),
        }
        return ranges

    def _initialised_desired_frames(self) -> Dict[str, defaultdict]:
        """Create initial counters (defaultdict(int)) for each timeframe.

        Returns:
            Dict[str, defaultdict]: Empty counters keyed by timeframe names.
        """
        counters = {
            CONST.TIMEFRAME_DAY: defaultdict(int),
            CONST.TIMEFRAME_WEEK: defaultdict(int),
            CONST.TIMEFRAME_MONTH: defaultdict(int),
            CONST.TIMEFRAME_YEAR: defaultdict(int),
        }
        return counters

    def _format_timeframes(self, counter: defaultdict, name: str) -> Union[str, Tuple[str, str]]:
        """Format a timeframe counter into a string or embed tuple.

        Args:
            counter (defaultdict): Counters for UP/PARTIALLY_UP/DOWN/etc.
            name (str): Human readable timeframe name (day/week/month/year).

        Returns:
            Union[str, Tuple[str, str]]: Formatted output depending on output mode.
        """
        up = counter.get(CONST.UP, 0)
        down = counter.get(CONST.DOWN, 0)
        partial = counter.get(CONST.PARTIALLY_UP, 0)
        unknown = sum(counter.values()) - (up + down + partial)
        _emoji: str = CONST.TIMEFRAME_EMOJIS[name]
        if self.output_mode == CONST.OM.MARKDOWN:
            final_string: str = f"> {_emoji} **{name.title()}**: {CONST.UP_EMOJI} {up} | {CONST.PARTIALLY_UP_EMOJI} {partial} | {CONST.DOWN_EMOJI} {down} | {CONST.UNKNOWN_STATUS_EMOJI} {unknown}"
        elif self.output_mode == CONST.OM.EMBED:
            resp: Tuple[str, str] = (
                f"{_emoji} {name.title()}",
                f"{CONST.UP_EMOJI} {up} | {CONST.PARTIALLY_UP_EMOJI} {partial} | {CONST.DOWN_EMOJI} {down} | {CONST.UNKNOWN_STATUS_EMOJI} {unknown}"
            )
            return resp
        else:
            final_string: str = f"{_emoji} {name.title()}: {CONST.UP_EMOJI} {up} | {CONST.PARTIALLY_UP_EMOJI} {partial} | {CONST.DOWN_EMOJI} {down} | {CONST.UNKNOWN_STATUS_EMOJI} {unknown}"
        return final_string

    def _get_latest_checks_per_day(self, data: List[Dict[str, Any]]) -> Dict[date, Dict[str, Any]]:
        """From historical checks pick the latest entry per date.

        Args:
            data (List[Dict[str, Any]]): List of rows with timestamp field.

        Returns:
            Dict[date, Dict[str, Any]]: Mapping from date to the latest row for that date.
        """
        daily_latest: Dict[date, Dict[str, Any]] = {}
        for check in data:
            try:
                check_time = self.connection.string_to_datetime(
                    datetime_string_instance=check[CONST.SQLITE_STATUS_TIMESTAMP_NAME],
                    date_only=False
                )
            except (RuntimeError, ValueError) as e:
                self.disp.log_error(f"Failed to parse datetime: {e}")
                continue

            check_date = check_time.date()
            if check_date not in daily_latest or check_time > daily_latest[check_date][f"{CONST.SQLITE_STATUS_TIMESTAMP_NAME}"]:
                daily_latest[check_date] = {
                    f"{CONST.SQLITE_STATUS_STATUS_NAME}": check[CONST.SQLITE_STATUS_STATUS_NAME],
                    f"{CONST.SQLITE_STATUS_TIMESTAMP_NAME}": check_time
                }
        self.disp.log_debug(f"Aggregated daily data: {daily_latest}")
        return daily_latest

    def _compile_website_data(self, data: List[Dict[str, Any]]) -> Union[str, List[Tuple[str, str]]]:
        """Aggregate raw status rows into formatted uptime summaries.

        Args:
            data (List[Dict[str, Any]]): Raw status history rows for a website.

        Returns:
            Union[str, List[Tuple[str, str]]]: Formatted summary depending on output mode.
        """
        _data_cleaned: Dict[
            date, Dict[str, Any]
        ] = self._get_latest_checks_per_day(data)
        _timeframes: Dict[str, date] = self._get_desired_timeframes()
        _desired_frames: Dict[
            str,
            defaultdict
        ] = self._initialised_desired_frames()
        for day, info in _data_cleaned.items():
            status: str = info[CONST.SQLITE_STATUS_STATUS_NAME]
            if day >= _timeframes[str(CONST.TIMEFRAME_DAY)]:
                _desired_frames[str(CONST.TIMEFRAME_DAY)][status] += 1
            if day >= _timeframes[str(CONST.TIMEFRAME_WEEK)]:
                _desired_frames[str(CONST.TIMEFRAME_WEEK)][status] += 1
            if day >= _timeframes[str(CONST.TIMEFRAME_MONTH)]:
                _desired_frames[str(CONST.TIMEFRAME_MONTH)][status] += 1
            if day >= _timeframes[str(CONST.TIMEFRAME_YEAR)]:
                _desired_frames[str(CONST.TIMEFRAME_YEAR)][status] += 1

        _uptime_summary_string: str = ""
        _uptime_summary_tuple: Tuple[str, str] = ("", "")
        if self.output_mode == CONST.OM.EMBED:
            _uptime_summary_tuple = ("Uptime Summary", "")
        elif self.output_mode == CONST.OM.MARKDOWN:
            _uptime_summary_string = "**Uptime Summary**"
        else:
            _uptime_summary_string = "Uptime Summary"

        _timeframe_day: Union[str, Tuple[str, str]] = self._format_timeframes(
            _desired_frames[str(CONST.TIMEFRAME_DAY)],
            str(CONST.TIMEFRAME_DAY)
        )
        _timeframe_week: Union[str, Tuple[str, str]] = self._format_timeframes(
            _desired_frames[str(CONST.TIMEFRAME_WEEK)],
            str(CONST.TIMEFRAME_WEEK)
        )
        _timeframe_month: Union[str, Tuple[str, str]] = self._format_timeframes(
            _desired_frames[str(CONST.TIMEFRAME_MONTH)],
            str(CONST.TIMEFRAME_MONTH)
        )
        _timeframe_year: Union[str, Tuple[str, str]] = self._format_timeframes(
            _desired_frames[str(CONST.TIMEFRAME_YEAR)],
            str(CONST.TIMEFRAME_YEAR)
        )

        if self.output_mode == CONST.OM.EMBED:
            final_data = [
                _uptime_summary_tuple,
                _timeframe_day,
                _timeframe_week,
                _timeframe_month,
                _timeframe_year
            ]
            return final_data
        final_data = [
            _uptime_summary_string,
            _timeframe_day,
            _timeframe_week,
            _timeframe_month,
            _timeframe_year
        ]
        return CONST.DISCORD_MESSAGE_NEWLINE.join(final_data)

    async def _get_website_data(self, website_id: int) -> Union[str, List[Tuple[str, str]]]:
        """Gather and format a website's historical status data for presentation.

        Args:
            website_id (int): Identifier of the website in the DB.

        Returns:
            Union[str, List[Tuple[str, str]]]: Formatted history content or an error placeholder.
        """
        if self.output_mode == CONST.OM.MARKDOWN:
            _error_message: Union[
                str, List[Tuple[str, str]]
            ] = "**<status history unavailable>**"
        elif self.output_mode == CONST.OM.EMBED:
            _error_message: Union[
                str, List[Tuple[str, str]]
            ] = [
                (
                    "Status history",
                    "unavailable"
                )
            ]
        else:
            _error_message: Union[
                str, List[Tuple[str, str]]
            ] = "<status history unavailable>"
        _table_of_interest: str = CONST.SQLITE_TABLE_NAME_STATUS_HISTORY
        _sql_table_columns: Union[List[str], int] = await self.connection.get_table_column_names(_table_of_interest)
        if isinstance(_sql_table_columns, int):
            self.disp.log_error(
                f"Failed to gather table data, table: {_table_of_interest}, error: {_sql_table_columns}"
            )
            return _error_message
        self.disp.log_debug(f"Gathered table names: {_sql_table_columns}")
        _sql_query: Union[int, List[Dict[str, Any]]] = await self.connection.get_data_from_table(
            _table_of_interest,
            _sql_table_columns,
            where=f"{CONST.SQLITE_STATUS_MESSAGE_ID_NAME}='{website_id}'",
            beautify=True
        )
        if isinstance(_sql_query, int):
            self.disp.log_error(
                f"Failed to gather table data, table: {_table_of_interest}, error: {_sql_query}"
            )
            return _error_message
        self.disp.log_debug(f"Table data: {_sql_query}")
        if self.output_mode == CONST.OM.MARKDOWN:
            _legend: Union[str, List[Tuple[str, str]]] = "**Legend**"
            _legend_end: Union[
                str, List[Tuple[str, str]]
            ] = f"{CONST.UP_EMOJI} = {CONST.UP} | {CONST.PARTIALLY_UP_EMOJI} = {CONST.PARTIALLY_UP} | {CONST.DOWN_EMOJI} = {CONST.DOWN} | {CONST.UNKNOWN_STATUS_EMOJI} = {CONST.UNKNOWN_STATUS}"
        elif self.output_mode == CONST.OM.EMBED:
            _legend: Union[str, List[Tuple[str, str]]] = [("Legend", "")]
            _legend_end: Union[
                str, List[Tuple[str, str]]
            ] = [
                (f"{CONST.UP_EMOJI}", f"{CONST.UP}"),
                (f"{CONST.PARTIALLY_UP_EMOJI}", f"{CONST.PARTIALLY_UP}"),
                (f"{CONST.DOWN_EMOJI}", f"{CONST.DOWN}"),
                (f"{CONST.UNKNOWN_STATUS_EMOJI}", f"{CONST.UNKNOWN_STATUS}")
            ]
        else:
            _legend: Union[str, List[Tuple[str, str]]] = "Legend"
            _legend_end: Union[
                str, List[Tuple[str, str]]
            ] = f"{CONST.UP_EMOJI} = {CONST.UP} | {CONST.PARTIALLY_UP_EMOJI} = {CONST.PARTIALLY_UP} | {CONST.DOWN_EMOJI} = {CONST.DOWN} | {CONST.UNKNOWN_STATUS_EMOJI} = {CONST.UNKNOWN_STATUS}"
        _compiled_data: Union[str, List[Tuple[str, str]]] = self._compile_website_data(
            _sql_query
        )
        final_data = []
        for item in [_legend, _legend_end, _compiled_data]:
            if isinstance(item, List):
                final_data.extend(cast(Iterable, item))
            else:
                final_data.append(item)
        if self.output_mode == CONST.OM.EMBED:
            return final_data
        return CONST.DISCORD_MESSAGE_NEWLINE.join(final_data)

    async def _get_meta_data(self, url: str) -> Union[str, List[Tuple[str, str]]]:
        """Build metadata (last updated + activity summary) for a URL.

        Args:
            url (str): The website URL to query metadata for.

        Returns:
            Union[str, List[Tuple[str, str]]]: Meta information in the configured output mode.
        """
        _last_updated: Union[
            str,
            Tuple[str, str]
        ] = self._get_last_update_human_date()
        _website_id: Optional[int] = await self._get_website_id(url)
        if not _website_id:
            self.disp.log_error(
                f"Failed to get the reference id, error: {_website_id}"
            )
            if self.output_mode == CONST.OM.MARKDOWN:
                return "**<no prior activity (or unaccessible)>**"
            if self.output_mode == CONST.OM.EMBED:
                return [("Activity", "none or unaccessible")]
            return "<no prior activity (or unaccessible)>"
        _extra_data: Union[str, List[Tuple[str, str]]] = await self._get_website_data(_website_id)
        if self.output_mode == CONST.OM.MARKDOWN:
            _padding: Union[
                str, List[Tuple[str, str]]
            ] = CONST.DISCORD_MESSAGE_NEWLINE
        elif self.output_mode == CONST.OM.EMBED:
            _padding: Union[str, List[Tuple[str, str]]] = [("", ""), ("", "")]
        else:
            _padding: Union[
                str, List[Tuple[str, str]]
            ] = CONST.DISCORD_MESSAGE_NEWLINE
        final_meta_data = []
        for item in [_last_updated, _padding, _extra_data]:
            if isinstance(item, List):
                final_meta_data.extend(cast(Iterable, item))
            else:
                final_meta_data.append(item)
        if self.output_mode == CONST.OM.EMBED:
            return final_meta_data
        return CONST.DISCORD_MESSAGE_NEWLINE.join(final_meta_data)

    def _make_raw_url_human_readable(self, raw_url: str) -> Union[str, Tuple[str, str]]:
        """Return a small human-readable representation of the full raw URL.

        The return type adapts to the configured output mode.
        """
        if self.output_mode == CONST.OM.MARKDOWN:
            return f"**Full url**: {raw_url}"
        elif self.output_mode == CONST.OM.EMBED:
            return ("Full url", f"{raw_url}")
        else:
            return f"Full url: {raw_url}"

    async def _make_human_readable(self, url: str, status: CONST.WebsiteStatus) -> Union[str, List[Tuple[str, str]]]:
        """Compose the human-facing status message for a single website.

        Args:
            url (str): The website URL.
            status (CONST.WebsiteStatus): The computed status enum.

        Returns:
            Union[str, List[Tuple[str, str]]]: Formatted message depending on output mode.
        """
        cleaned_url: str = self._clean_url(url)
        data: Union[str, List[Tuple[str, str]]] = await self._get_meta_data(url)
        raw_url: Union[
            str,
            Tuple[str, str]
        ] = self._make_raw_url_human_readable(url)
        if status == CONST.WS.UP:
            if self.output_mode == CONST.OM.MARKDOWN:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.UP_EMOJI} Website '({cleaned_url})' is **UP and Operational**"
            elif self.output_mode == CONST.OM.EMBED:
                status_string: Union[str, Tuple[str, str]] = (
                    f"{CONST.UP_EMOJI} '({cleaned_url})'",
                    "UP and Operational"
                )
            else:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.UP_EMOJI} Website '({cleaned_url})' is UP and Operational"
        elif status == CONST.WS.PARTIALLY_UP:
            if self.output_mode == CONST.OM.MARKDOWN:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.PARTIALLY_UP_EMOJI} Website '({cleaned_url})' is **UP but NOT Operational**"
            elif self.output_mode == CONST.OM.EMBED:
                status_string: Union[str, Tuple[str, str]] = (
                    f"{CONST.PARTIALLY_UP_EMOJI} '({cleaned_url})'",
                    "UP but NOT Operational"
                )
            else:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.PARTIALLY_UP_EMOJI} Website '({cleaned_url})' is UP but NOT Operational"
        elif status == CONST.WS.DOWN:
            if self.output_mode == CONST.OM.MARKDOWN:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.DOWN_EMOJI} Website '({cleaned_url})' is **DOWN**"
            elif self.output_mode == CONST.OM.EMBED:
                status_string: Union[str, Tuple[str, str]] = (
                    f"{CONST.DOWN_EMOJI} '({cleaned_url})'",
                    "DOWN"
                )
            else:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.DOWN_EMOJI} Website '({cleaned_url})' is DOWN"
        else:
            if self.output_mode == CONST.OM.MARKDOWN:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.UNKNOWN_STATUS_EMOJI} Website '({cleaned_url})' has an **UNHANDLED STATUS** '({status})'"
            elif self.output_mode == CONST.OM.EMBED:
                status_string: Union[str, Tuple[str, str]] = (
                    f"{CONST.UNKNOWN_STATUS_EMOJI} '({cleaned_url})'",
                    f"UNHANDLED STATUS '({status})'"
                )
            else:
                status_string: Union[
                    str,
                    Tuple[str, str]
                ] = f"{CONST.UNKNOWN_STATUS_EMOJI} Website '({cleaned_url})' has an UNHANDLED STATUS '({status})'"
        final_string = []
        for item in [status_string, raw_url, data]:
            if isinstance(item, List):
                final_string.extend(cast(Iterable, item))
            else:
                final_string.append(item)
        if self.output_mode == CONST.OM.EMBED:
            return final_string
        return CONST.DISCORD_MESSAGE_NEWLINE.join(final_string)

    def _check_if_keyword_in_content(self, needle: str, haystack: str, case_sensitive: bool = False) -> bool:
        """Check whether ``needle`` exists in ``haystack`` ignoring extra whitespace.

        Args:
            needle (str): The substring to search for.
            haystack (str): The text to search within.
            case_sensitive (bool): If True, perform a case-sensitive search.

        Returns:
            bool: True if found, False otherwise.
        """
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
            f"1rst {CONST.RESPONSE_LOG_SIZE} characters of the normalized haystack: '{haystack_cleaned[:CONST.RESPONSE_LOG_SIZE]}'"
        )
        found: bool = needle_cleaned in haystack_cleaned
        self.disp.log_debug(f"Needle found: {found}")
        return found

    def _check_deadchecks(self, request: requests.Response, dead_checks: List[CONST.DeadCheck], default: CONST.WebsiteStatus = CONST.WS.UP) -> CONST.WebsiteStatus:
        """Evaluate "dead check" keywords in the response and map them to a status.

        Args:
            request (requests.Response): The HTTP response to inspect.
            dead_checks (List[CONST.DeadCheck]): Dead-check rules to apply.
            default (CONST.WebsiteStatus): Default status to return if none match.

        Returns:
            CONST.WebsiteStatus: The status chosen by matching rules or the default.
        """
        website_response: str = request.text
        website_response_lower: str = ""
        _tmp_response: str = ""
        _tmp_dead_check: str = ""
        self.disp.log_debug(f"request={request}")
        self.disp.log_debug(f"default={default}")
        self.disp.log_debug(f"dead_checks={dead_checks}")
        for check in dead_checks:
            _tmp_response = ""
            _tmp_dead_check = ""
            self.disp.log_debug(f"check={check}")
            if check.case_sensitive is False:
                if website_response_lower == "":
                    website_response_lower = website_response.lower()
                _tmp_response = website_response_lower
                _tmp_dead_check = check.keyword.lower()
            else:
                _tmp_response = website_response
                _tmp_dead_check = check.keyword
            self.disp.log_debug(
                f"_tmp_response[:{CONST.RESPONSE_LOG_SIZE}]='{_tmp_response[:CONST.RESPONSE_LOG_SIZE]}'"
            )
            self.disp.log_debug(f"_tmp_dead_check='{_tmp_dead_check}'")
            if self._check_if_keyword_in_content(_tmp_dead_check, _tmp_response, True):
                self.disp.log_debug(
                    f"Keyword '{_tmp_dead_check}' located in response"
                )
                return check.response
        self.disp.log_debug(
            f"no dead check found, returning default '{default.name}'"
        )
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
        """Return the database id for a website URL or None if not found.

        Args:
            url (str): The website URL to look up.

        Returns:
            Union[int, None]: The integer id or None if missing/unavailable.
        """
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
        """Insert or update the main messages table for a website node.

        Args:
            websites (CONST.WebsiteNode): The validated website node.

        Returns:
            int: CONST.SUCCESS or CONST.ERROR.
        """
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
        """Insert or update dead-check entries for a website node.

        Args:
            websites (CONST.WebsiteNode): The validated website node.

        Returns:
            int: CONST.SUCCESS or CONST.ERROR.
        """
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

    @overload
    async def _update_status_history_table(
        self, websites: CONST.WebsiteNode) -> int: ...

    @overload
    async def _update_status_history_table(
        self, websites: CONST.WebsiteNode, query_status: bool) -> Union[int, CONST.QueryStatus]: ...

    async def _update_status_history_table(self, websites: CONST.WebsiteNode, query_status: bool = False) -> Union[int, CONST.QueryStatus]:
        """Check website status, write a row to the status history table.

        Args:
            websites (CONST.WebsiteNode): The website node to check.
            query_status (bool): If True, return the QueryStatus instead of the numeric result.

        Returns:
            Union[int, CONST.QueryStatus]: The inserted row status code or the QueryStatus object when requested.
        """
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
        status: int = await self.connection.insert_data_into_table(
            dest_table,
            data,
            columns_cleaned
        )
        if status == CONST.SUCCESS and query_status:
            return status_check
        return status

    async def _update_table_content(self) -> int:
        """Fill the DB tables with entries derived from the validated JSON configuration.

        Returns:
            int: CONST.SUCCESS on success, otherwise CONST.ERROR.
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

    async def _check_database_connection(self) -> int:
        """Ensure the SQL connection is functional, attempt to initialise if not.

        Returns:
            int: CONST.SUCCESS if a working connection is available, otherwise CONST.ERROR.
        """
        try:
            _ = await self.connection.get_table_names()
            return CONST.SUCCESS
        except RuntimeError as e:
            self.disp.log_warning(
                f"Database connection not initialised, initialising with the 'create' function, error: {e}"
            )
            try:
                _url = self.connection.url
                _port = self.connection.port
                _username = self.connection.username
                _password = self.connection.password
                _db_name = self.connection.db_name
                _success = self.connection.success
                _error = self.connection.error
                _debug = self.connection.debug
                self.disp.log_debug("Attempting to initialise the connection")
                _conn_tmp: SQL = await self.connection.create(
                    url=_url,
                    port=_port,
                    username=_username,
                    password=_password,
                    db_name=_db_name,
                    success=_success,
                    error=_error,
                    debug=_debug
                )
                try:
                    self.disp.log_debug(
                        "Attempting to get the tables in the database"
                    )
                    _ = await _conn_tmp.get_table_names()
                    self.disp.log_debug(
                        "Updating the class connection reference."
                    )
                    self.connection = _conn_tmp
                    self.disp.log_info(
                        "Database connection initialisation success."
                    )
                    return CONST.SUCCESS
                except RuntimeError as err:
                    self.disp.log_error(
                        f"Database connection initialisation failed: '{err}'"
                    )
                    return CONST.ERROR
            except RuntimeError as r_err:
                self.disp.log_error(
                    f"Database connection initialisation failed: '{r_err}'"
                )
                return CONST.ERROR

    async def boot_up(self) -> int:
        """Function containing the steps for the class to properly start up.

        Returns:
            int: The run status of the class
        """
        status: int = await self._check_database_connection()
        if status != CONST.SUCCESS:
            self.disp.log_error("The database connection check failed.")
            return CONST.ERROR
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
        self.boot_called = True
        return CONST.SUCCESS

    async def refresh_message_id(self, discord_message: CONST.DiscordMessage) -> int:
        """Function in charge of updating the message id in the database with the latest discord returned id.

        Args:
            discord_message (CONST.DiscordMessage): _description_

        Returns:
            int: _description_
        """
        if not discord_message.website_id or not discord_message.message_channel or not discord_message.message_id:
            self.disp.log_warning(
                "Received corrupted or invalid DiscordMessage dataclass, skipping"
            )
            return CONST.ERROR
        status: int = await self.connection.update_data_in_table(
            CONST.SQLITE_TABLE_NAME_MESSAGES,
            [str(discord_message.message_id)],
            [str(CONST.SQLITE_MESSAGES_MESSAGE_ID_NAME)],
            f"id='{discord_message.website_id}'"
        )
        if status != CONST.SUCCESS:
            self.disp.log_error(
                "Failed to update the website in the database with the current discord message id."
            )
        return status

    async def _get_message_id_from_database(self, discord_message: CONST.DiscordMessage) -> Union[CONST.DiscordMessage, int]:
        """Function in charge of getting the message id from the database if present.

        Args:
            discord_message (CONST.DiscordMessage): _description_

        Returns:
            int: _description_
        """
        if not discord_message.website_id or not discord_message.message_channel:
            self.disp.log_warning(
                "Received corrupted or invalid DiscordMessage dataclass, skipping"
            )
            return CONST.ERROR
        content: Union[int, List[Tuple[Any, Any]]] = await self.connection.get_data_from_table(
            CONST.SQLITE_TABLE_NAME_MESSAGES,
            [str(CONST.SQLITE_MESSAGES_MESSAGE_ID_NAME)],
            f"id='{discord_message.website_id}'",
            beautify=False
        )
        if isinstance(content, int):
            self.disp.log_error(
                "Failed to retreive the website's message id from the database."
            )
            return CONST.ERROR
        self.disp.log_debug(f"Gathered data: {content}")
        if len(content) > 0:
            if isinstance(content[0], Tuple):
                if isinstance(content[0][0], int):
                    discord_message.message_id = content[0][0]
                elif isinstance(content[0][0], str) and content[0][0].lower() == "null":
                    discord_message.message_id = None
                else:
                    self.disp.log_error(
                        f"Unknown or unsupported cell format, got: '{content[0][0]}' of type: '{type(content[0][0])}'"
                    )
        self.disp.log_debug(f"Final message id: {discord_message.message_id}")
        return discord_message

    async def _build_discord_message(self, website_node: CONST.WebsiteNode) -> Union[int, CONST.DiscordMessage]:
        """Prepare a CONST.DiscordMessage for a given website_node.

        This checks status, builds human readable content, and attempts to
        look up any existing message id in the database.
        """
        _dm: CONST.DiscordMessage = CONST.DiscordMessage()
        _dm.message_channel = website_node.channel
        query_status: Union[int, CONST.QueryStatus] = await self._update_status_history_table(website_node, True)
        if isinstance(query_status, int):
            self.disp.log_error("Failed to check the website status.")
            return CONST.ERROR
        _dm.status = query_status.status
        _dm.message_human = await self._make_human_readable(
            website_node.url,
            query_status.status
        )
        _dm.website_pretty_url = self._clean_url(website_node.url)
        _dm.website_id = query_status.website_id
        message_id: Union[int, CONST.DiscordMessage] = await self._get_message_id_from_database(_dm)
        if isinstance(message_id, int):
            self.disp.log_warning(
                "Message id not found in the database, ignoring because it will be set upon the first message send."
            )
        else:
            _dm.message_id = message_id.message_id
        return _dm

    async def run(self) -> Union[int, List[CONST.DiscordMessage]]:
        """Function in charge of running the logic of the bot's mainloop"""
        if not self.processed_json or not self.boot_called:
            self.disp.log_error(
                "There are no websites to monitor, did you think to call the boot_up function?"
            )
            return CONST.ERROR
        run_status: List[CONST.DiscordMessage] = []
        for site in self.processed_json:
            if not isinstance(site, CONST.WebsiteNode):
                self.disp.log_warning(
                    f"The current site node is of an unknown type, got '({type(site)})' but expected '{type(CONST.WebsiteNode)}', skipping"
                )
                continue
            _tmp: Union[int, CONST.DiscordMessage] = await self._build_discord_message(site)
            if not isinstance(_tmp, CONST.DiscordMessage):
                self.disp.log_warning(
                    f"Failed to check '({site.url})', skipping update"
                )
                continue
            run_status.append(_tmp)
        return run_status
