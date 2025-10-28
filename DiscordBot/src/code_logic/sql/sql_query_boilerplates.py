"""SQL query helpers and high-level database boilerplates.

This module implements :class:`SQLQueryBoilerplates`, a collection of
async convenience functions to create/drop tables, insert/update or
query data using an underlying async connection manager. The helpers
perform defensive sanitisation and basic SQL injection checks.
"""
from typing import List, Dict, Union, Any, Tuple, Literal, overload, Sequence

import sqlite3

from display_tty import Disp
from ..program_globals.helpers import initialise_logger

from . import sql_constants as SCONST
from .sql_injection import SQLInjection
from .sql_connections import SQLManageConnections
from .sql_sanitisation_functions import SQLSanitiseFunctions


class SQLQueryBoilerplates:
    """High-level SQL query helpers and boilerplate functions.

    This class provides convenient async methods to query and modify the
    database using an underlying async connection manager (``SQLManageConnections``).
    Methods generally return either a data structure (for SELECT-like
    queries) or an integer status code (``self.success`` / ``self.error``)
    for operations that modify data.
    """

    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(self, sql_pool: SQLManageConnections, success: int = 0, error: int = 84, debug: bool = False) -> None:
        """Initialize the query helper.

        Args:
            sql_pool (SQLManageConnections): Async connection manager used to
                run queries and commands.
            success (int, optional): Numeric success code. Defaults to 0.
            error (int, optional): Numeric error code. Defaults to 84.
            debug (bool, optional): Enable debug logging. Defaults to False.
        """
        # -------------------------- Inherited values --------------------------
        self.sql_pool: SQLManageConnections = sql_pool
        self.error: int = error
        self.debug: bool = debug
        self.success: int = success
        # --------------------------- logger section ---------------------------
        self.disp.update_disp_debug(self.debug)
        # ---------------------- The anty injection class ----------------------
        self.sql_injection: SQLInjection = SQLInjection(
            self.error,
            self.success,
            self.debug
        )
        # -------------------- Keyword sanitizing functions --------------------
        self.sanitize_functions: SQLSanitiseFunctions = SQLSanitiseFunctions(
            success=self.success, error=self.error, debug=self.debug
        )

    def _normalize_cell(self, cell: object) -> Union[str, None, int, float]:
        """Normalise a cell value for parameter binding.

        Converts special tokens (now/current_date) and preserves numeric
        types. Returns None for null-like inputs.
        """
        if cell is None:
            return None
        if isinstance(cell, (int, float)):
            return cell
        s = str(cell)
        sl = s.lower()
        if sl in ("now", "now()"):
            return self.sanitize_functions.sql_time_manipulation.get_correct_now_value()
        if sl in ("current_date", "current_date()"):
            return self.sanitize_functions.sql_time_manipulation.get_correct_current_date_value()
        return s

    async def get_triggers(self) -> Union[int, Dict[str, str]]:
        """Return a dictionary of all triggers and their SQL definitions.

        Returns:
            Union[int, Dict[str, str]]: Dict of {trigger_name: sql_definition}, or ``self.error``.
        """
        title = "get_triggers"
        self.disp.log_debug(
            "Fetching all triggers and their SQL definitions.", title
        )

        query = "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND name NOT LIKE 'sqlite_%';"
        resp = await self.sql_pool.run_and_fetch_all(query=query, values=[])

        if isinstance(resp, int):
            self.disp.log_error("Failed to fetch triggers.", title)
            return self.error

        data: Dict[str, str] = {}
        for row in resp:
            if len(row) >= 2 and row[0] and row[1]:
                data[row[0]] = row[1]

        self.disp.log_debug(f"Triggers fetched: {list(data.keys())}", title)
        return data

    async def get_table_column_names(self, table_name: str) -> Union[List[str], int]:
        """Return the list of column names for ``table_name``.

        Args:
            table_name (str): Name of the table to inspect.

        Returns:
            Union[List[str], int]: List of column names on success, or
            ``self.error`` on failure.
        """
        title = "get_table_column_names"
        try:
            columns = await self.describe_table(table_name)
            if isinstance(columns, int):
                self.disp.log_error(
                    f"Failed to describe table {table_name}.",
                    title
                )
                return self.error
            data = []
            for i in columns:
                data.append(i[0])
            return data
        except RuntimeError as e:
            msg = "Error: Failed to get column names of the tables.\n"
            msg += f"\"{str(e)}\""
            self.disp.log_error(msg, "get_table_column_names")
            return self.error

    async def get_trigger(self, trigger_name: str) -> Union[int, str]:
        """Return the SQL definition of a specific trigger.

        Args:
            trigger_name (str): The trigger name to fetch.

        Returns:
            Union[int, str]: The SQL definition, or ``self.error`` on failure.
        """
        title = "get_trigger"
        self.disp.log_debug(
            f"Getting trigger definition for '{trigger_name}'", title
        )

        if not trigger_name:
            self.disp.log_error("Trigger name cannot be empty.", title)
            return self.error

        # SQL injection defense
        if self.sql_injection.check_if_injections_in_strings([trigger_name]):
            self.disp.log_error(
                "SQL Injection detected in trigger name.", title
            )
            return self.error

        query = f"SELECT sql FROM sqlite_master WHERE type='trigger' AND name = '{trigger_name}';"
        resp = await self.sql_pool.run_and_fetch_all(query=query, values=[])

        if isinstance(resp, int) or not resp:
            self.disp.log_error(
                f"Failed to retrieve trigger '{trigger_name}'.", title
            )
            return self.error

        sql_definition = resp[0][0] if resp and len(resp[0]) > 0 else None
        if not sql_definition:
            self.disp.log_error(
                f"No SQL definition found for trigger '{trigger_name}'.", title
            )
            return self.error

        self.disp.log_debug(
            f"SQL for trigger '{trigger_name}':\n{sql_definition}", title
        )
        return sql_definition

    async def get_table_names(self) -> Union[int, List[str]]:
        """Return a list of non-internal table names in the database.

        Returns:
            Union[int, List[str]]: List of table names or ``self.error`` on failure.
        """
        title = "get_table_names"
        self.disp.log_debug("Getting table names.", title)
        # sqlite: List tables from sqlite_master; ignore internal sqlite_ tables
        resp = await self.sql_pool.run_and_fetch_all(
            query="SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';",
            values=[]
        )
        if isinstance(resp, int):
            self.disp.log_error(
                "Failed to fetch the table names.",
                title
            )
            return self.error
        self.disp.log_debug(f"response = {resp}")
        data = []
        for i in resp:
            data.append(i[0])
        self.disp.log_debug(f"response (cleaned) = {data}")
        self.disp.log_debug("Tables fetched", title)
        return data

    async def get_trigger_names(self) -> Union[int, List[str]]:
        """Return a list of non-internal trigger names in the database.

        Returns:
            Union[int, List[str]]: List of trigger names, or ``self.error`` on failure.
        """
        title = "get_trigger_names"
        self.disp.log_debug("Getting trigger names.", title)

        query = "SELECT name FROM sqlite_master WHERE type='trigger' AND name NOT LIKE 'sqlite_%';"
        resp = await self.sql_pool.run_and_fetch_all(query=query, values=[])

        if isinstance(resp, int):
            self.disp.log_error("Failed to fetch trigger names.", title)
            return self.error

        data = []
        for i in resp:
            if i and i[0]:
                data.append(i[0])
        self.disp.log_debug(f"Triggers fetched: {data}", title)
        return data

    async def describe_table(self, table: str) -> Union[int, List[Any]]:
        """Fetch the schema description for a table.

        This returns rows similar to SQLite's PRAGMA table_info but is
        transformed so the first element is the column name (to remain
        compatible with previous MySQL-style DESCRIBE results).

        Args:
            table (str): Name of the table to describe.

        Raises:
            RuntimeError: On critical SQLite errors (re-raised as RuntimeError).

        Returns:
            Union[int, List[Any]]: Transformed description rows on success,
            or ``self.error`` on failure.
        """
        title = "describe_table"
        self.disp.log_debug(f"Describing table {table}", title)
        if self.sql_injection.check_if_sql_injection(table):
            self.disp.log_error("Injection detected.", "sql")
            return self.error
        try:
            # SQLite equivalent: PRAGMA table_info(table) returns rows: (cid, name, type, notnull, dflt_value, pk)
            resp = await self.sql_pool.run_and_fetch_all(
                query=f"PRAGMA table_info('{table}');",
                values=[]
            )
            if isinstance(resp, int):
                self.disp.log_error(
                    f"Failed to describe table  {table}", title
                )
                return self.error
            # Transform rows so first element is the column name to stay compatible with MySQL DESCRIBE shape
            transformed = []
            for row in resp:
                # row might be tuple like (cid, name, type, notnull, dflt_value, pk)
                if len(row) >= 2:
                    name = row[1]
                    transformed.append((name,) + tuple(row[2:]))
                else:
                    transformed.append((row[0],))
            return transformed
        except sqlite3.ProgrammingError as pe:
            msg = f"ProgrammingError: The table '{table}' does not exist or the query failed."
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from pe
        except sqlite3.IntegrityError as ie:
            msg = f"IntegrityError: There was an integrity constraint issue while describing the table '{table}'."
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from ie
        except sqlite3.OperationalError as oe:
            msg = f"OperationalError: There was an operational error while describing the table '{table}'."
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from oe
        except sqlite3.Error as e:
            msg = f"SQLite Error: An unexpected error occurred while describing the table '{table}'."
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e
        except RuntimeError as e:
            msg = "A runtime error occurred during the table description process."
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e

    async def create_table(self, table: str, columns: List[Tuple[str, str]]) -> int:
        """Create a new table in the SQLite database.

        Args:
            table (str): Name of the new table.
            columns (List[Tuple[str, str]]): List of (column_name, column_type) pairs.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on failure.

        Example:
            Example usage to create a basic ``users`` table:

            .. code-block:: python

                # Define the table name and column definitions
                table_name = "users"
                columns = [
                    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
                    ("username", "TEXT NOT NULL UNIQUE"),
                    ("email", "TEXT NOT NULL"),
                    ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                ]

                # Create the table asynchronously
                result = await self.create_table(table_name, columns)

                # Check if the operation succeeded
                if result == self.success:
                    print(f"Table '{table_name}' created successfully.")
                else:
                    print(f"Failed to create table '{table_name}'.")

        Notes:
            - This method automatically checks for SQL injection attempts using :class:`SQLInjection` before executing the query.
            - Single quotes in table or column names are escaped defensively.
            - The query uses ``CREATE TABLE IF NOT EXISTS`` to avoid errors if the table already exists.
        """
        title = "create_table"
        self.disp.log_debug(f"Creating table '{table}'", title)

        # --- SQL injection protection ---
        # Check both table name and column data
        if self.sql_injection.check_if_injections_in_strings([table]):
            self.disp.log_error(
                "Injection detected in table name.", title
            )
            return self.error

        try:
            # Escape single quotes in table/column names defensively
            table_safe = table.replace("'", "''")
            _tmp = []
            for name, col_type in columns:
                # Escape single quotes in column names defensively
                safe_name = name.replace("'", "''")
                _tmp.append(f"'{safe_name}' {col_type}")
            columns_def = ", ".join(_tmp)

            query = f"CREATE TABLE IF NOT EXISTS '{table_safe}' ({columns_def});"
            self.disp.log_debug(f"Executing SQL: {query}", title)

            result = await self.sql_pool.run_and_commit(query=query, values=[])
            if isinstance(result, int) and result == self.error:
                self.disp.log_error(f"Failed to create table '{table}'", title)
                return self.error

            self.disp.log_info(f"Table '{table}' created successfully.", title)
            return self.success

        except sqlite3.OperationalError as oe:
            msg = f"OperationalError while creating table '{table}': {oe}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from oe
        except sqlite3.Error as e:
            msg = f"SQLite Error while creating table '{table}': {e}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e
        except Exception as e:
            msg = f"Unexpected error while creating table '{table}': {e}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e

    async def insert_data_into_table(self, table: str, data: Union[List[List[Union[str, None, int, float]]], List[Union[str, None, int, float]]], column: Union[List[str], None] = None) -> int:
        """Insert one or multiple rows into ``table``.

        Args:
            table (str): Table name.
            data (Union[List[List[Union[str, None, int, float]]], List[Union[str, None, int, float]]]): Row data. Either a
                single row or a list of rows where each cell may be str/int/float/None.
            column (List[str] | None): Optional list of columns to insert into.

        Returns:
            int: ``self.success`` on success or ``self.error`` on failure.
        """
        title = "insert_data_into_table"
        self.disp.log_debug("Inserting data into the table.", title)

        # Only check table/column names for injection — values are parameterized
        check_list = [table]
        if column is not None:
            check_list.extend(column)
        if self.sql_injection.check_if_injections_in_strings(check_list):
            self.disp.log_error("Injection detected.", "sql")
            return self.error

        # determine columns List if not provided
        if column is None:
            columns_raw = await self.get_table_column_names(table)
            if isinstance(columns_raw, int):
                return self.error
            column = columns_raw
        # At this point column should be a List of strings
        _tmp_cols: Union[List[str], str] = self.sanitize_functions.escape_risky_column_names(
            column
        )
        # normalize sanitized column names into a list
        if isinstance(_tmp_cols, list):
            column = _tmp_cols
        else:
            column = [str(_tmp_cols)]
        column_str = ", ".join(column)
        column_length = len(column)

        # Build parameter placeholders and values list
        values_list: List[Union[str, None, int, float]] = []
        if isinstance(data, list) and (len(data) > 0 and isinstance(data[0], list)):
            self.disp.log_debug("processing double array", title)
            placeholders = []
            for line in data:
                # ensure line length and normalize runtime type (may be Sequence)
                if isinstance(line, str):
                    # treat a string as a single cell
                    line_vals = [line]
                elif not isinstance(line, list):
                    try:
                        line_vals = list(line)
                    except Exception:
                        line_vals = [line]
                else:
                    line_vals = line
                row_vals: List[Union[str, None, int, float]] = []
                for i in range(column_length):
                    if i < len(line_vals):
                        v = line_vals[i]
                    else:
                        v = None
                    normalised_cell = self._normalize_cell(v)
                    self.disp.log_debug(f"Normalised cell: {normalised_cell}")
                    row_vals.append(normalised_cell)
                values_list.extend(row_vals)
                placeholders.append(
                    "(" + ", ".join(["?"] * column_length) + ")")
            values = ", ".join(placeholders)

        elif isinstance(data, list):
            self.disp.log_debug("processing single array", title)
            row_vals: List[Union[str, None, int, float]] = []
            for i in range(column_length):
                if i < len(data):
                    v = data[i]
                else:
                    v = None
                normalised_cell = self._normalize_cell(v)
                self.disp.log_debug(f"Normalised cell: {normalised_cell}")
                row_vals.append(normalised_cell)
            values_list.extend(row_vals)
            values = "(" + ", ".join(["?"] * column_length) + ")"
        else:
            self.disp.log_error(
                "data is expected to be, either of type: List[str] or List[List[str]]",
                title
            )
            return self.error

        sql_query = f"INSERT INTO {table} ({column_str}) VALUES {values}"
        self.disp.log_debug(f"sql_query = '{sql_query}'", title)
        return await self.sql_pool.run_editing_command(sql_query, values_list, table, "insert")

    async def insert_trigger(self, trigger_name: str, trigger_sql: str) -> int:
        """Insert a new SQL trigger into the database.

        Args:
            trigger_name (str): Name of the trigger to create.
            trigger_sql (str): SQL command defining the trigger.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on error.
        """
        title = "insert_trigger"
        self.disp.log_debug(f"Inserting trigger: {trigger_name}", title)

        # Sanity checks
        if not trigger_name or not trigger_sql:
            self.disp.log_error(
                "Trigger name and SQL must not be empty.", title
            )
            return self.error

        # Injection prevention
        if self.sql_injection.check_if_injections_in_strings(trigger_name):
            self.disp.log_error(
                "SQL Injection detected in trigger creation.", title
            )
            return self.error

        # Run the SQL command
        sql_query = trigger_sql.strip()
        self.disp.log_debug(f"Executing trigger creation:\n{sql_query}", title)

        result = await self.sql_pool.run_editing_command(sql_query, [], trigger_name, "create_trigger")
        if result != self.success:
            self.disp.log_error(
                f"Failed to create trigger '{trigger_name}'.", title
            )
            return self.error

        self.disp.log_info(
            f"Trigger '{trigger_name}' successfully created.", title
        )
        return self.success

    @overload
    async def get_data_from_table(
        self,
        table: str,
        column: Union[str, List[str]],
        where: Union[str, List[str]] = "",
        beautify: Literal[True] = True,
    ) -> Union[int, List[Dict[str, Any]]]: ...

    @overload
    async def get_data_from_table(
        self,
        table: str,
        column: Union[str, List[str]],
        where: Union[str, List[str]] = "",
        beautify: Literal[False] = False,
    ) -> Union[int, List[Tuple[Any, Any]]]: ...

    async def get_data_from_table(self, table: str, column: Union[str, List[str]], where: Union[str, List[str]] = "", beautify: bool = True) -> Union[int, Union[List[Dict[str, Any]], List[Tuple[Any, Any]]]]:
        """Query rows from ``table`` and optionally return them in a beautified form.

        Args:
            table (str): Table name.
            column (Union[str, List[str]]): Column name(s) or '*' to select.
            where (Union[str, List[str]], optional): WHERE clause or list of
                conditions. Defaults to empty string.
            beautify (bool, optional): If True, convert rows to list of dicts
                keyed by column names. Defaults to True.

        Returns:
            Union[int, List[Dict[str, Any]], List[Tuple[str, Any]]]: Beautified list of Dictionaries on success and if beautify is True, otherwise, a list of tuples is beautify is set to False, or ``self.error`` on failure.
        """
        title = "get_data_from_table"
        self.disp.log_debug(f"fetching data from the table {table}", title)
        # Defensive: allow injection checker to accept mixed types
        # build injection check items (table + column names only)
        check_items: List[str] = [table]
        if isinstance(column, list):
            check_items.extend([str(c) for c in column])
        else:
            check_items.append(str(column))
        if self.sql_injection.check_if_injections_in_strings(check_items) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return self.error
        # Normalize column selection to a string
        if isinstance(column, list):
            safe_cols = self.sanitize_functions.escape_risky_column_names(
                column)
            if isinstance(safe_cols, list):
                column_str = ", ".join(safe_cols)
            else:
                column_str = str(safe_cols)
        else:
            column_str = str(column)
        sql_command = f"SELECT {column_str} FROM {table}"
        # Normalize WHERE clause using sanitizer result (could be str or list)
        if isinstance(where, (str, list)):
            where_sanitized = self.sanitize_functions.escape_risky_column_names_where_mode(
                where)
            if isinstance(where_sanitized, list):
                where = " AND ".join(where_sanitized)
            else:
                where = where_sanitized
        if where != "":
            sql_command += f" WHERE {where}"
        self.disp.log_debug(f"sql_query = '{sql_command}'", title)
        resp = await self.sql_pool.run_and_fetch_all(query=sql_command, values=[])
        # Narrow runtime type so static analyzer sees we have a list below
        if isinstance(resp, int):
            if resp != self.success:
                self.disp.log_error(
                    "Failed to fetch the data from the table.", title
                )
                return self.error
            resp_list = []
        else:
            resp_list = resp
        self.disp.log_debug(f"Queried data: {resp}", title)
        if beautify is False:
            return resp_list
        data = await self.describe_table(table)
        if isinstance(data, int):
            return self.error
        return self.sanitize_functions.beautify_table(data, resp_list)

    async def get_table_size(self, table: str, column: Union[str, List[str]], where: Union[str, List[str]] = "") -> int:
        """Return the number of rows matching the optional WHERE clause.

        Args:
            table (str): Table name.
            column (Union[str, List[str]]): Column to COUNT over (often '*').
            where (Union[str, List[str]], optional): WHERE clause or list of
                conditions. Defaults to empty string.

        Returns:
            int: Number of matching rows, or ``SCONST.GET_TABLE_SIZE_ERROR`` on error.
        """
        title = "get_table_size"
        self.disp.log_debug(f"fetching data from the table {table}", title)
        # build safe check items for injection detection
        check_items = [table]
        if isinstance(column, list):
            check_items.extend([str(c) for c in column])
        else:
            check_items.append(str(column))
        if self.sql_injection.check_if_injections_in_strings(check_items) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return SCONST.GET_TABLE_SIZE_ERROR
        if isinstance(column, list):
            column = ", ".join(column)
        sql_command = f"SELECT COUNT({column}) FROM {table}"
        if isinstance(where, (str, list)):
            where_sanitized = self.sanitize_functions.escape_risky_column_names_where_mode(
                where)
            if isinstance(where_sanitized, list):
                where = " AND ".join(where_sanitized)
            else:
                where = where_sanitized
        if where != "":
            sql_command += f" WHERE {where}"
        self.disp.log_debug(f"sql_query = '{sql_command}'", title)
        resp = await self.sql_pool.run_and_fetch_all(query=sql_command, values=[])
        if isinstance(resp, int):
            if resp != self.success:
                self.disp.log_error(
                    "Failed to fetch the data from the table.", title
                )
                return SCONST.GET_TABLE_SIZE_ERROR
            resp_list = []
        else:
            resp_list = resp
        if len(resp_list) == 0:
            self.disp.log_error(
                "There was no data returned by the query.", title
            )
            return SCONST.GET_TABLE_SIZE_ERROR
        if not isinstance(resp_list[0], tuple):
            self.disp.log_error("The data returned is not a tuple.", title)
            return SCONST.GET_TABLE_SIZE_ERROR
        return resp_list[0][0]

    async def update_data_in_table(self, table: str, data: List[Union[str, None, int, float]], column: Union[List[str], str, None], where: Union[str, List[str]] = "") -> int:
        """Update rows in ``table`` matching ``where`` with values from ``data``.

        Args:
            table (str): Table name.
            data (List[Union[str, None, int, float]]): New values to set.
            column (List): Column names corresponding to data.
            where (Union[str, List[str]], optional): WHERE clause or list of
                conditions. Defaults to empty string.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on failure.
        """
        title = "update_data_in_table"
        msg = f"Updating the data contained in the table: {table}"
        self.disp.log_debug(msg, title)
        if column is None:
            column = ""

        # Only check table/column names for injection — data is parameterized
        check_items = [table]
        if isinstance(column, list):
            check_items.extend([str(c) for c in column])
        else:
            check_items.append(str(column))
        if self.sql_injection.check_if_injections_in_strings(check_items) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return self.error

        if column == "":
            columns_raw = await self.get_table_column_names(table)
            if isinstance(columns_raw, int):
                return self.error
            column = columns_raw

        # Ensure column is a List[str] for subsequent operations
        _tmp_cols2: Union[List[str], str] = self.sanitize_functions.escape_risky_column_names(
            column
        )
        if isinstance(_tmp_cols2, list):
            column = _tmp_cols2
        else:
            column = [str(_tmp_cols2)]

        if isinstance(column, str) and isinstance(data, str):
            data = [data]
            column = [column]
            column_length = len(column)

        column_length = len(column)
        self.disp.log_debug(
            f"data = {data}, column = {column}, length = {column_length}",
            title
        )

        where_sanitized = self.sanitize_functions.escape_risky_column_names_where_mode(
            where
        )
        if isinstance(where_sanitized, list):
            where = " AND ".join(where_sanitized)
        else:
            where = where_sanitized

        # Build SET clause with placeholders and parameter list
        set_parts: List[str] = []
        params: List[Union[str, None, int, float]] = []
        for i in range(column_length):
            set_parts.append(f"{column[i]} = ?")
            if i < len(data):
                v = data[i]
            else:
                v = None
            normalised_cell: Union[
                int,
                str,
                float,
                None
            ] = self._normalize_cell(v)
            self.disp.log_debug(f"Normalised cell: {normalised_cell}")
            params.append(normalised_cell)

        update_line = ", ".join(set_parts)
        sql_query = f"UPDATE {table} SET {update_line}"

        if where != "":
            sql_query += f" WHERE {where}"

        self.disp.log_debug(f"sql_query = '{sql_query}'", title)

        return await self.sql_pool.run_editing_command(sql_query, params, table, "update")

    async def insert_or_update_trigger(self, trigger_name: str, trigger_sql: str) -> int:
        """Insert or update an existing SQL trigger.

        Args:
            trigger_name (str): Name of the trigger to create or replace.
            trigger_sql (str): SQL command defining the trigger.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on error.
        """
        title = "insert_or_update_trigger"
        self.disp.log_debug(
            f"Creating or replacing trigger: {trigger_name}", title
        )

        # First, drop the existing trigger (if any)
        drop_result = await self.remove_trigger(trigger_name)
        if drop_result not in (self.success, self.error):
            self.disp.log_warning(
                f"Unexpected drop_trigger result: {drop_result}", title
            )

        # Insert the new one
        return await self.insert_trigger(trigger_name, trigger_sql)

    async def insert_or_update_data_into_table(self, table: str, data: Union[List[List[Union[str, None, int, float]]], List[Union[str, None, int, float]]], columns: Union[List[str], None] = None) -> int:
        """Insert new rows or update existing rows for ``table``.

        This method determines column names if not provided and delegates
        to the appropriate INSERT/UPDATE boilerplate.

        Args:
            table (str): Table name.
            data (Union[List[List[str]], List[str]]): Data to insert or update.
            columns (List[str] | None, optional): Column names. Defaults to None.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on error.
        """
        title = "insert_or_update_data_into_table"
        self.disp.log_debug(
            "Inserting or updating data into the table.", title
        )

        check_list = [table]
        if columns:
            check_list.extend(columns)
        if self.sql_injection.check_if_injections_in_strings(check_list):
            self.disp.log_error("SQL Injection detected.", "sql")
            return self.error

        if columns is None:
            cols_raw = await self.get_table_column_names(table)
            if isinstance(cols_raw, int):
                return self.error
            columns = cols_raw

        # ensure columns is a concrete list for downstream calls
        if columns is not None and not isinstance(columns, list):
            try:
                columns = list(columns)
            except Exception:
                columns = [str(columns)]

        table_content = await self.get_data_from_table(
            table=table, column=columns, where="", beautify=False
        )
        # ensure table_content is iterable
        if isinstance(table_content, int):
            if table_content != self.success:
                self.disp.log_critical(
                    f"Failed to retrieve data from table {table}", title
                )
                return self.error
        table_content_list = table_content
        # table_content_list is now safe to iterate over (ensure runtime type for static checkers)
        if not isinstance(table_content_list, list):
            self.disp.log_error(
                f"Unexpected table content type for table {table}", title
            )
            return self.error

        if isinstance(data, list) and data and isinstance(data[0], list):
            self.disp.log_debug("Processing double data List", title)
            table_content_dict = {}
            for line in table_content_list:
                table_content_dict[str(line[0])] = line

            for line in data:
                if not line:
                    self.disp.log_warning("Empty line, skipping.", title)
                    continue
                # narrow type for the linter/typing
                if isinstance(line, str):
                    line_list = [line]
                elif not isinstance(line, list):
                    try:
                        line_list = list(line)
                    except Exception:
                        line_list = [line]
                else:
                    line_list = line
                node0 = str(line_list[0])
                if node0 in table_content_dict:
                    await self.update_data_in_table(
                        table,
                        line_list,
                        columns,
                        f"{columns[0]} = {node0}"
                    )
                else:
                    # ensure column arg is a concrete list
                    cols = columns if isinstance(
                        columns, list) else list(columns)
                    await self.insert_data_into_table(table, line_list, cols)
            # finished processing multiple rows
            return self.success

        # Single-row processing
        if isinstance(data, list):
            self.disp.log_debug("Processing single data List", title)
            if not data:
                self.disp.log_warning("Empty data List, skipping.", title)
                return self.success

            node0 = str(data[0])
            # If a row with the same first-column key exists, update it
            for line in table_content_list:
                if str(line[0]) == node0:
                    return await self.update_data_in_table(
                        table, data, columns, f"{columns[0]} = {node0}"
                    )

            # No existing row found — insert as new row
            cols = columns if isinstance(columns, list) else list(columns)
            return await self.insert_data_into_table(table, data, cols)

        # If we reach here, the input type was unexpected
        self.disp.log_error(
            "Data must be of type List[str] or List[List[str]]", title
        )
        return self.error

    async def remove_data_from_table(self, table: str, where: Union[str, Sequence[str]] = "") -> int:
        """Delete rows from ``table`` matching ``where``.

        Args:
            table (str): Table name to delete rows from.
            where (Union[str, List[str]], optional): WHERE clause or list of
                conditions to filter rows. If empty, all rows are deleted.

        Returns:
            int: ``self.success`` on success or ``self.error`` on failure.
        """
        self.disp.log_debug(
            f"Removing data from table {table}",
            "remove_data_from_table"
        )
        if self.sql_injection.check_if_sql_injection(table) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return self.error

        if isinstance(where, list):
            where = " AND ".join(where)

        sql_query = f"DELETE FROM {table}"

        if where != "":
            sql_query += f" WHERE {where}"

        self.disp.log_debug(
            f"sql_query = '{sql_query}'",
            "remove_data_from_table"
        )

        return await self.sql_pool.run_editing_command(sql_query, [], table, "delete")

    async def remove_table(self, table: str) -> int:
        """Drop/Remove (delete) a table from the SQLite database.

        Args:
            table (str): Name of the table to drop.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on failure.

        Example:
            Example usage to drop the ``users`` table:

            .. code-block:: python

                table_name = "users"
                result = await self.drop_table(table_name)

                if result == self.success:
                    print(f"Table '{table_name}' dropped successfully.")
                else:
                    print(f"Failed to drop table '{table_name}'.")

        Notes:
            - The method performs SQL injection detection on the table name.
            - If the table does not exist, no error is raised (uses ``DROP TABLE IF EXISTS`` internally).
        """
        title = "drop_table"
        self.disp.log_debug(f"Dropping table '{table}'", title)

        # --- SQL injection protection ---
        if self.sql_injection.check_if_injections_in_strings([table]):
            self.disp.log_error("Injection detected in table name.", title)
            return self.error

        try:
            # Escape quotes for safety
            table_safe = table.replace("'", "''")
            query = f"DROP TABLE IF EXISTS '{table_safe}';"
            self.disp.log_debug(f"Executing SQL: {query}", title)

            result = await self.sql_pool.run_and_commit(query=query, values=[])
            if isinstance(result, int) and result == self.error:
                self.disp.log_error(f"Failed to drop table '{table}'", title)
                return self.error

            self.disp.log_info(f"Table '{table}' dropped successfully.", title)
            return self.success

        except sqlite3.OperationalError as oe:
            msg = f"OperationalError while dropping table '{table}': {oe}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from oe
        except sqlite3.Error as e:
            msg = f"SQLite Error while dropping table '{table}': {e}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e
        except Exception as e:
            msg = f"Unexpected error while dropping table '{table}': {e}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e

    async def remove_trigger(self, trigger_name: str) -> int:
        """Drop/Remove an existing SQL trigger if it exists.

        Args:
            trigger_name (str): Name of the trigger to drop.

        Returns:
            int: ``self.success`` on success, or ``self.error`` on error.
        """
        title = "drop_trigger"
        self.disp.log_debug(f"Dropping trigger: {trigger_name}", title)

        if not trigger_name:
            self.disp.log_error("Trigger name cannot be empty.", title)
            return self.error

        # Sanitize to prevent injections
        if self.sql_injection.check_if_injections_in_strings([trigger_name]):
            self.disp.log_error(
                "SQL Injection detected in trigger name.", title
            )
            return self.error

        sql_query = f"DROP TRIGGER IF EXISTS {trigger_name};"
        self.disp.log_debug(f"Executing SQL:\n{sql_query}", title)

        result = await self.sql_pool.run_editing_command(sql_query, [], trigger_name, "drop_trigger")
        if result != self.success:
            self.disp.log_error(
                f"Failed to drop trigger '{trigger_name}'.", title
            )
            return self.error

        self.disp.log_info(
            f"Trigger '{trigger_name}' dropped successfully.", title
        )
        return self.success
