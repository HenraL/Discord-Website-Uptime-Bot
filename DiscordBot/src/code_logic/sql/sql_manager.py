"""
File in charge of containing the interfacing between an sql library and the program.
This contains functions that simplify the process of interacting with databases as well as check for injection attempts.
"""

from typing import Optional, Callable, Awaitable, Union, List, Dict, Tuple, Any

from display_tty import Disp
from ..program_globals.helpers import initialise_logger

from .sql_time_manipulation import SQLTimeManipulation
from .sql_connections import SQLManageConnections
from .sql_query_boilerplates import SQLQueryBoilerplates


class SQL:
    """
    Manage database access and provide high-level query helpers.

    This class wraps a low-level connection manager and exposes convenience
    async methods for common operations. The underlying connection pool is
    asynchronous; therefore construction via ``SQL(...)`` only creates a
    lightweight facade. Callers should use the async factory
    ``await SQL.create(...)`` to obtain a fully-initialised instance.

    Attributes:
        disp (Disp): Logger instance used by the SQL helpers.
        sql_manage_connections (Optional[SQLManageConnections]): The low-level
            async connection manager.
        sql_query_boilerplates (Optional[SQLQueryBoilerplates]): High-level
            query helpers created after async init.
        get_data_from_table (callable | None): Convenience async callable;
            bound after initialisation.
    """

    # Initialise the logger globally in the class.
    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(self, url: str, port: int, username: str, password: str, db_name: str, success: int = 0, error: int = 84, debug: bool = False):
        """
        Create a lightweight SQL facade instance.

        The synchronous constructor initialises the facade and lightweight
        helpers that do not require an active async connection. The actual
        async connection pool is created by :py:meth:`create`.

        Args:
            url (str): DB host or file path (for sqlite this is a filename).
            port (int): DB port (unused for sqlite but retained for API compatibility).
            username (str): DB username (unused for sqlite).
            password (str): DB password (unused for sqlite).
            db_name (str): Database name or sqlite filename.
            success (int, optional): numeric success code used across the
                sql helpers. Defaults to 0.
            error (int, optional): numeric error code used across the sql
                helpers. Defaults to 84.
            debug (bool, optional): enable debug logging. Defaults to False.

        Note:
            For sqlite usage, ``port``, ``username`` and ``password`` are
            typically unused; they are present for backwards compatibility.
        """
        async def _uninitialized(*args, **kwargs):
            raise RuntimeError("SQLQueryBoilerplates method not initialized")
        self.debug: bool = debug
        self.success: int = success
        self.error: int = error
        self.url: str = url
        self.port: int = port
        self.username: str = username
        self.password: str = password
        self.db_name: str = db_name
        # ----------------- Pre class variable initialisation  -----------------
        # These are declared Optional so they can be assigned None during
        # construction and cleaned up in __del__.
        self.sql_time_manipulation: Optional[SQLTimeManipulation] = None
        self.sql_query_boilerplates: Optional[SQLQueryBoilerplates] = None
        # --------------------------- logger section ---------------------------
        self.disp.update_disp_debug(self.debug)
        # ------------- The class in charge of the sql connection  -------------
        self.sql_manage_connections: Optional[SQLManageConnections] = SQLManageConnections(
            url=self.url,
            port=self.port,
            username=self.username,
            password=self.password,
            db_name=self.db_name,
            success=self.success,
            error=self.error,
            debug=self.debug
        )

        # ---------------------------- Time logger  ----------------------------
        self.sql_time_manipulation = SQLTimeManipulation(
            self.debug
        )
        self.datetime_to_string = self.sql_time_manipulation.datetime_to_string
        self.string_to_datetime = self.sql_time_manipulation.string_to_datetime
        self._get_correct_now_value = self.sql_time_manipulation.get_correct_now_value
        self._get_correct_current_date_value = self.sql_time_manipulation.get_correct_current_date_value
        # --------------------------- debug section  ---------------------------
        # Note: pool initialisation is async. Use the async factory `create` to
        # obtain a fully-initialized SQL instance.
        self.sql_manage_connections.show_connection_info("__init__")
        # sql_query_boilerplates will be created by the async factory once the
        # connection pool is initialised.
        self.sql_query_boilerplates = None
        # ------------------------- Convenience rebinds ------------------------
        self.create_table: Callable[
            [str, List[Tuple[str, str]]],
            Awaitable[int]
        ]
        self.get_table_column_names: Callable[
            [str],
            Awaitable[Union[List[str], int]]
        ]
        self.get_table_names: Callable[
            [],
            Awaitable[Union[int, List[str]]]
        ]
        self.describe_table: Callable[
            [str],
            Awaitable[Union[int, List[Any]]]
        ]
        self.insert_data_into_table: Callable[
            [str, Union[List[List[str]], List[str]], Union[List[str], None]],
            Awaitable[int]
        ]
        self.get_data_from_table: Callable[
            [str, Union[str, List[str]], Union[str, List[str]], bool],
            Awaitable[Union[int, List[Dict[str, Any]]]]
        ]
        self.get_table_size: Callable[
            [str, Union[str, List[str]], Union[str, List[str]]],
            Awaitable[int]
        ]
        self.update_data_in_table: Callable[
            [str, List[str], Union[List[str], str, None], Union[str, List[str]]],
            Awaitable[int]
        ]
        self.insert_or_update_data_into_table: Callable[
            [str, Union[List[List[str]], List[str]], Union[List[str], None]],
            Awaitable[int]
        ]
        self.remove_data_from_table: Callable[
            [str, Union[str, List[str]]],
            Awaitable[int]
        ]
        self.drop_data_from_table: Callable[
            [str],
            Awaitable[int]
        ]
        self.drop_table: Callable[
            [str],
            Awaitable[int]
        ]
        self.remove_table: Callable[
            [str],
            Awaitable[int]
        ]
        self.create_table = _uninitialized
        self.get_table_column_names = _uninitialized
        self.get_table_names = _uninitialized
        self.describe_table = _uninitialized
        self.insert_data_into_table = _uninitialized
        self.get_data_from_table = _uninitialized
        self.get_table_size = _uninitialized
        self.update_data_in_table = _uninitialized
        self.insert_or_update_data_into_table = _uninitialized
        self.remove_data_from_table = _uninitialized
        self.drop_data_from_table = _uninitialized
        self.remove_table = _uninitialized
        self.drop_table = _uninitialized

    def __del__(self) -> None:
        """
            Disconnect the database when the class is destroyed
        """
        if self.sql_manage_connections is not None:
            del self.sql_manage_connections
            self.sql_manage_connections = None
        if self.sql_time_manipulation is not None:
            del self.sql_time_manipulation
            self.sql_time_manipulation = None
        if self.sql_query_boilerplates is not None:
            del self.sql_query_boilerplates
            self.sql_query_boilerplates = None

    @classmethod
    async def create(cls, url: str, port: int, username: str, password: str, db_name: str, success: int = 0, error: int = 84, debug: bool = False):
        """
        Async factory to create and initialise an SQL instance.

        This factory completes asynchronous initialisation steps that the
        synchronous constructor cannot perform (notably the connection
        pool initialisation). After this call returns the instance is ready
        for async usage and convenience async callables are bound on the
        instance.

        Args:
            url (str): DB host or file path (for sqlite this is a filename).
            port (int): DB port (unused for sqlite but retained for API
                compatibility).
            username (str): DB username (unused for sqlite).
            password (str): DB password (unused for sqlite).
            db_name (str): Database name or sqlite filename.
            success (int, optional): numeric success code used across the
                sql helpers. Defaults to 0.
            error (int, optional): numeric error code used across the sql
                helpers. Defaults to 84.
            debug (bool, optional): enable debug logging. Defaults to False.

        Returns:
            SQL: Initialized SQL instance ready for async operations.

        Raises:
            RuntimeError: If the connection pool cannot be initialised.

        Example:
            sql = await SQL.create('db.sqlite', 0, '', '', 'db.sqlite')
            await sql.get_data_from_table('my_table')
        """

        self = cls(
            url,
            port,
            username,
            password,
            db_name,
            success=success,
            error=error,
            debug=debug
        )
        # Initialise the async connection pool
        # static checkers see `sql_manage_connections` as Optional; assert
        # it's available to narrow the type for the following calls.
        assert self.sql_manage_connections is not None
        assert self.disp is not None
        if await self.sql_manage_connections.initialise_pool() != self.success:
            msg = "Failed to initialise the connection pool."
            self.disp.log_critical(msg, "create")
            raise RuntimeError(f"Error: {msg}")
        # Create the query helper now that the pool is ready
        self.sql_query_boilerplates = SQLQueryBoilerplates(
            sql_pool=self.sql_manage_connections, success=self.success,
            error=self.error, debug=self.debug
        )
        # Bind convenience methods
        self.create_table = self.sql_query_boilerplates.create_table
        self.get_table_column_names = self.sql_query_boilerplates.get_table_column_names
        self.get_table_names = self.sql_query_boilerplates.get_table_names
        self.describe_table = self.sql_query_boilerplates.describe_table
        self.insert_data_into_table = self.sql_query_boilerplates.insert_data_into_table
        self.get_data_from_table = self.sql_query_boilerplates.get_data_from_table
        self.get_table_size = self.sql_query_boilerplates.get_table_size
        self.update_data_in_table = self.sql_query_boilerplates.update_data_in_table
        self.insert_or_update_data_into_table = self.sql_query_boilerplates.insert_or_update_data_into_table
        self.remove_data_from_table = self.sql_query_boilerplates.remove_data_from_table
        self.drop_data_from_table = self.sql_query_boilerplates.remove_data_from_table
        self.remove_table = self.sql_query_boilerplates.drop_table
        self.drop_table = self.sql_query_boilerplates.drop_table
        return self

    async def close(self) -> None:
        """Cleanly close async resources like the connection pool."""
        if self.sql_manage_connections is not None:
            try:
                await self.sql_manage_connections.destroy_pool()
            except Exception as e:
                if self.disp:
                    self.disp.log_error(
                        f"Error while closing connection pool: {e}")
        # Clean up all references
        self.sql_manage_connections = None
        self.sql_query_boilerplates = None
        self.sql_time_manipulation = None
