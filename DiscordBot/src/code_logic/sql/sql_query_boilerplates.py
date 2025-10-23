"""
    File in charge of storing the functions that will interract directly with the database.
"""

from typing import List, Dict, Union, Any, Tuple, cast

import sqlite3

from display_tty import Disp
from ..program_globals.helpers import initialise_logger

from . import sql_constants as SCONST
from .sql_injection import SQLInjection
from .sql_connections import SQLManageConnections
from .sql_sanitisation_functions import SQLSanitiseFunctions


class SQLQueryBoilerplates:
    """
    High-level SQL query helpers and boilerplate functions.

    This class provides convenient async methods to query and modify the
    database using an underlying async connection manager (``SQLManageConnections``).
    Methods generally return either a data structure (for SELECT-like
    queries) or an integer status code (``self.success`` / ``self.error``)
    for operations that modify data.
    """

    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(self, sql_pool: SQLManageConnections, success: int = 0, error: int = 84, debug: bool = False) -> None:
        """
        Initialize the query helper.

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

    async def get_table_column_names(self, table_name: str) -> Union[List[str], int]:
        """
        Return the list of column names for ``table_name``.

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

    async def get_table_names(self) -> Union[int, List[str]]:
        """
        Return a list of non-internal table names in the database.

        Returns:
            Union[int, List[str]]: List of table names or ``self.error`` on failure.
        """
        title = "get_table_names"
        self.disp.log_debug("Getting table names.", title)
        # sqlite: List tables from sqlite_master; ignore internal sqlite_ tables
        resp = await self.sql_pool.run_and_fetch_all(
            query="SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
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

    async def describe_table(self, table: str) -> Union[int, List[Any]]:
        """
        Fetch the schema description for a table.

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
                query=f"PRAGMA table_info('{table}');")
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
        """
        Create a new table in the SQLite database.

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
            columns_def = ", ".join(
                f"'{name.replace("'", "''")}' {col_type}" for name, col_type in columns
            )

            query = f"CREATE TABLE IF NOT EXISTS '{table_safe}' ({columns_def});"
            self.disp.log_debug(f"Executing SQL: {query}", title)

            result = await self.sql_pool.run_and_commit(query=query)
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

    async def drop_table(self, table: str) -> int:
        """
        Drop (delete) a table from the SQLite database.

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

            result = await self.sql_pool.run_and_commit(query=query)
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

    async def insert_data_into_table(self, table: str, data: Union[List[List[str]], List[str]], column: Union[List[str], None] = None) -> int:
        """
        Insert one or multiple rows into ``table``.

        Args:
            table (str): Table name.
            data (Union[List[List[str]], List[str]]): Row data. Either a
                single row (List[str]) or a list of rows (List[List[str]]).
            column (List[str] | None): Optional list of columns to insert into.

        Returns:
            int: ``self.success`` on success or ``self.error`` on failure.
        """
        title = "insert_data_into_table"
        self.disp.log_debug("Inserting data into the table.", title)
        if self.sql_injection.check_if_injections_in_strings(cast(Union[str, List[str], List[List[str]]], [table, data, column])):
            self.disp.log_error("Injection detected.", "sql")
            return self.error
        # determine columns List if not provided
        if column is None:
            columns_raw = await self.get_table_column_names(table)
            if isinstance(columns_raw, int):
                return self.error
            column = cast(List[str], columns_raw)
        # At this point column should be a List of strings; cast for the type checker
        column = cast(List[str], column)
        _tmp_cols: Union[List[str], str] = self.sanitize_functions.escape_risky_column_names(
            column)
        column = cast(List[str], _tmp_cols)
        column_str = ", ".join(column)
        column_length = len(column)

        if isinstance(data, List) and (len(data) > 0 and isinstance(data[0], List)):
            self.disp.log_debug("processing double array", title)
            values = ""
            max_lengths = len(data)
            for index, line in enumerate(data):
                values += self.sanitize_functions.process_sql_line(
                    cast(List[str], line), column, column_length
                )
                if index < max_lengths - 1:
                    values += ", "
                if index == max_lengths - 1:
                    break

        elif isinstance(data, List):
            self.disp.log_debug("processing single array", title)
            values = self.sanitize_functions.process_sql_line(
                cast(List[str], data), column, column_length
            )
        else:
            self.disp.log_error(
                "data is expected to be, either of type: List[str] or List[List[str]]",
                title
            )
            return self.error
        sql_query = f"INSERT INTO {table} ({column_str}) VALUES {values}"
        self.disp.log_debug(f"sql_query = '{sql_query}'", title)
        return await self.sql_pool.run_editing_command(sql_query, table, "insert")

    async def get_data_from_table(self, table: str, column: Union[str, List[str]], where: Union[str, List[str]] = "", beautify: bool = True) -> Union[int, List[Dict[str, Any]]]:
        """
        Query rows from ``table`` and optionally return them in a
        beautified dict form.

        Args:
            table (str): Table name.
            column (Union[str, List[str]]): Column name(s) or '*' to select.
            where (Union[str, List[str]], optional): WHERE clause or list of
                conditions. Defaults to empty string.
            beautify (bool, optional): If True, convert rows to list of dicts
                keyed by column names. Defaults to True.

        Returns:
            Union[int, List[Dict[str, Any]]]: Beautified list of rows on
            success, or ``self.error`` on failure.
        """
        title = "get_data_from_table"
        self.disp.log_debug(f"fetching data from the table {table}", title)
        # Defensive: allow injection checker to accept mixed types
        if self.sql_injection.check_if_injections_in_strings(cast(Union[str, List[str], List[List[str]]], [table, column])) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return self.error
        if isinstance(column, List):
            column = self.sanitize_functions.escape_risky_column_names(column)
            column = ", ".join(column)
        sql_command = f"SELECT {column} FROM {table}"
        if isinstance(where, (str, List)):
            where = self.sanitize_functions.escape_risky_column_names_where_mode(
                where
            )
        if isinstance(where, List):
            where = " AND ".join(where)
        if where != "":
            sql_command += f" WHERE {where}"
        self.disp.log_debug(f"sql_query = '{sql_command}'", title)
        resp = await self.sql_pool.run_and_fetch_all(query=sql_command)
        if isinstance(resp, int) and resp != self.success:
            self.disp.log_error(
                "Failed to fetch the data from the table.", title
            )
            return self.error
        self.disp.log_debug(f"Queried data: {resp}", title)
        if beautify is False:
            return resp
        data = await self.describe_table(table)
        if isinstance(data, int):
            return self.error
        resp_List = cast(List[Any], resp)
        return self.sanitize_functions.beautify_table(cast(List[str], data), resp_List)

    async def get_table_size(self, table: str, column: Union[str, List[str]], where: Union[str, List[str]] = "") -> int:
        """
        Return the number of rows matching the optional WHERE clause.

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
        if self.sql_injection.check_if_injections_in_strings(cast(Union[str, List[str], List[List[str]]], [table, column])) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return SCONST.GET_TABLE_SIZE_ERROR
        if isinstance(column, List):
            column = ", ".join(column)
        sql_command = f"SELECT COUNT({column}) FROM {table}"
        if isinstance(where, (str, List)):
            where = self.sanitize_functions.escape_risky_column_names_where_mode(
                where
            )
        if isinstance(where, List):
            where = " AND ".join(where)
        if where != "":
            sql_command += f" WHERE {where}"
        self.disp.log_debug(f"sql_query = '{sql_command}'", title)
        resp = await self.sql_pool.run_and_fetch_all(query=sql_command)
        if isinstance(resp, int) and resp != self.success:
            self.disp.log_error(
                "Failed to fetch the data from the table.", title
            )
            return SCONST.GET_TABLE_SIZE_ERROR
        resp_List = cast(List[Any], resp)
        if len(resp_List) == 0:
            self.disp.log_error(
                "There was no data returned by the query.", title
            )
            return SCONST.GET_TABLE_SIZE_ERROR
        if not isinstance(resp_List[0], tuple):
            self.disp.log_error("The data returned is not a tuple.", title)
            return SCONST.GET_TABLE_SIZE_ERROR
        return resp_List[0][0]

    async def update_data_in_table(self, table: str, data: List[str], column: Union[List[str], str, None], where: Union[str, List[str]] = "") -> int:
        """
        Update rows in ``table`` matching ``where`` with values from ``data``.

        Args:
            table (str): Table name.
            data (List[str]): New values to set.
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

        if self.sql_injection.check_if_injections_in_strings(cast(Union[str, List[str], List[List[str]]], [table, column, data])) or self.sql_injection.check_if_symbol_and_command_injection(where):
            self.disp.log_error("Injection detected.", "sql")
            return self.error

        if column == "":
            columns_raw = await self.get_table_column_names(table)
            if isinstance(columns_raw, int):
                return self.error
            column = cast(List[str], columns_raw)

        # Ensure column is a List[str] for subsequent operations
        column = cast(List[str], column)
        _tmp_cols2: Union[List[str], str] = self.sanitize_functions.escape_risky_column_names(
            column)
        column = cast(List[str], _tmp_cols2)

        if isinstance(column, str) and isinstance(data, str):
            data = [data]
            column = [column]
            column_length = len(column)

        column_length = len(column)
        self.disp.log_debug(
            f"data = {data}, column = {column}, length = {column_length}",
            title
        )

        where = self.sanitize_functions.escape_risky_column_names_where_mode(
            where
        )

        if isinstance(where, List):
            where = " AND ".join(where)

        update_line = self.sanitize_functions.compile_update_line(
            data, cast(List[str], column), column_length
        )

        sql_query = f"UPDATE {table} SET {update_line}"

        if where != "":
            sql_query += f" WHERE {where}"

        self.disp.log_debug(f"sql_query = '{sql_query}'", title)

        return await self.sql_pool.run_editing_command(sql_query, table, "update")

    async def insert_or_update_data_into_table(self, table: str, data: Union[List[List[str]], List[str]], columns: Union[List[str], None] = None) -> int:
        """
        Insert new rows or update existing rows for ``table``.

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
            "Inserting or updating data into the table.", title)

        if self.sql_injection.check_if_injections_in_strings(cast(Union[str, List[str], List[List[str]]], [table] + (columns or []))):
            self.disp.log_error("SQL Injection detected.", "sql")
            return self.error

        if columns is None:
            cols_raw = await self.get_table_column_names(table)
            if isinstance(cols_raw, int):
                return self.error
            columns = cast(List[str], cols_raw)

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
        table_content_List = cast(List[Any], table_content)
        # table_content_List is now safe to iterate over

        if isinstance(data, List) and data and isinstance(data[0], List):
            self.disp.log_debug("Processing double data List", title)
            table_content_dict = {
                str(line[0]): line for line in table_content_List}

            for line in data:
                if not line:
                    self.disp.log_warning("Empty line, skipping.", title)
                    continue
                node0 = str(line[0])
                if node0 in table_content_dict:
                    await self.update_data_in_table(
                        table, cast(List[str], line), cast(List[str], columns),
                        f"{columns[0]} = {node0}"
                    )
                else:
                    await self.insert_data_into_table(table, cast(List[str], line), cast(List[str], columns))
            # finished processing multiple rows
            return self.success

        elif isinstance(data, List):
            self.disp.log_debug("Processing single data List", title)
            if not data:
                self.disp.log_warning("Empty data List, skipping.", title)
                return self.success

            node0 = str(data[0])
            for line in table_content_List:
                if str(line[0]) == node0:
                    return await self.update_data_in_table(table, cast(List[str], data), cast(List[str], columns), f"{columns[0]} = {node0}")
            return await self.insert_data_into_table(table, cast(List[str], data), cast(List[str], columns))

        else:
            self.disp.log_error(
                "Data must be of type List[str] or List[List[str]]", title
            )
            return self.error

    async def remove_data_from_table(self, table: str, where: Union[str, List[str]] = "") -> int:
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

        if isinstance(where, List):
            where = " AND ".join(where)

        sql_query = f"DELETE FROM {table}"

        if where != "":
            sql_query += f" WHERE {where}"

        self.disp.log_debug(
            f"sql_query = '{sql_query}'",
            "remove_data_from_table"
        )

        return await self.sql_pool.run_editing_command(sql_query, table, "delete")
