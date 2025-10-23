"""
    Async SQL connection manager using aiosqlite.

    This module replaces the previous synchronous sqlite3-based manager with
    an async-friendly implementation using aiosqlite. Public methods that
    perform I/O are asynchronous (async def).
"""

from typing import Union, Any, Optional

from pathlib import Path

import sqlite3
import asyncio
import aiosqlite

from display_tty import Disp
from ..program_globals.helpers import initialise_logger

from . import sql_constants as SCONST


class SQLManageConnections:
    """Async connection manager for sqlite using aiosqlite.

    This class provides a small, async-friendly facade around a single
    :class:`aiosqlite.Connection` instance. It serializes access with an
    :class:`asyncio.Lock` so that multiple asyncio tasks do not attempt to
    use the same connection/cursor concurrently.

    Behaviour / contract:
    - Call :meth:`initialise_pool` once at startup to open the sqlite file.
    - Use :meth:`get_connection` / :meth:`get_cursor` to obtain resources.
    - Prefer the convenience methods :meth:`run_and_fetch_all` and
      :meth:`run_editing_command` for simple queries.
    - Public I/O methods are asynchronous and must be awaited.

    Attributes:
        connection (Optional[aiosqlite.Connection]): The active aiosqlite
            connection or ``None`` if not initialised.
        _lock (asyncio.Lock): Lock used to serialize connection/cursor use.
    """

    # Initialise the logger globally in the class.
    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(
        self,
        url: str,
        port: int,
        username: str,
        password: str,
        db_name: str,
        success: int = 0,
        error: int = 84,
        debug: bool = False,
    ) -> None:
        self.error: int = error
        self.debug: bool = debug
        self.success: int = success
        self.url: str = url
        self.port: int = port
        self.username: str = username
        self.password: str = password
        self.db_name: str = str(Path(self.url) / db_name)
        # --------------------------- logger section ---------------------------
        self.disp.update_disp_debug(self.debug)

        # The aiosqlite connection (async object)
        self.connection: Optional[aiosqlite.Connection] = None
        # Async lock to serialize access across asyncio tasks
        self._lock = asyncio.Lock()

    def show_connection_info(self, func_name: str = "show_connection_info") -> None:
        """Log connection metadata for debugging.

        This method does not perform any I/O; it only logs the configured
        connection information (database filename, host/url and port) via the
        project's logging helper.

        Args:
            func_name (str): Optional title used in the logger.

        Returns:
            None
        """
        msg = f"DB name: {self.db_name}, host/url: {self.url}, port: {self.port}\n"
        self.disp.log_debug(msg, func_name)

    async def initialise_pool(self) -> int:
        """Open an :class:`aiosqlite.Connection` and apply recommended PRAGMAs.

        This prepares the SQLite file for concurrent reads/writes by enabling
        WAL mode and setting a busy timeout. On success the created
        connection is stored on :attr:`connection` and :data:`self.success` is
        returned. On fatal SQLite errors a :class:`RuntimeError` is raised.

        Returns:
            int: ``self.success`` on success.

        Raises:
            RuntimeError: If a low-level sqlite3.* error occurs while
                initialising the connection. The original sqlite exception
                is attached as the cause.
        """
        title = "initialise_pool"
        self.disp.log_debug("Initialising async sqlite connection.", title)
        try:
            conn = await aiosqlite.connect(self.db_name)
            try:
                await conn.execute("PRAGMA journal_mode=WAL;")
            except sqlite3.Error:
                pass
            try:
                await conn.execute("PRAGMA busy_timeout=5000;")
            except sqlite3.Error:
                pass
            try:
                await conn.execute("PRAGMA foreign_keys=ON;")
            except sqlite3.Error:
                pass
            await conn.commit()
            self.connection = conn
            return self.success
        except sqlite3.ProgrammingError as pe:
            msg = "ProgrammingError: The connection could not be initialized."
            msg += f"Original error: {str(pe)}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from pe
        except sqlite3.IntegrityError as ie:
            msg = "IntegrityError: Integrity issue while initializing the connection."
            msg += f" Original error: {str(ie)}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from ie
        except sqlite3.OperationalError as oe:
            msg = "OperationalError: Operational error occurred during connection initialization."
            msg += f" Original error: {str(oe)}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from oe
        except sqlite3.Error as e:
            msg = "SQLite Error: An unexpected error occurred during connection initialization."
            msg += f"Original error: {str(e)}"
            self.disp.log_critical(msg, title)
            raise RuntimeError(msg) from e

    def get_connection(self) -> aiosqlite.Connection:
        """Return the active :class:`aiosqlite.Connection`.

        This does not open a connection; it only returns the connection
        previously created by :meth:`initialise_pool`.

        Returns:
            aiosqlite.Connection: The active connection object.

        Raises:
            RuntimeError: If :attr:`connection` is ``None`` (not initialised).
        """
        title = "get_connection"
        if self.connection is None:
            raise RuntimeError("Connection is not initialized.")
        self.disp.log_debug("Getting an aiosqlite connection", title)
        return self.connection

    async def get_cursor(self, connection: aiosqlite.Connection) -> aiosqlite.Cursor:
        """Return a cursor for the provided :class:`aiosqlite.Connection`.

        The method performs a lightweight liveness check using
        :meth:`is_connection_active` and raises if the connection appears
        inactive. The returned cursor must be closed by the caller (or by
        :meth:`release_connection_and_cursor`) when no longer needed.

        Args:
            connection (aiosqlite.Connection): The connection to create a
                cursor from.

        Returns:
            aiosqlite.Cursor: A new cursor bound to ``connection``.

        Raises:
            RuntimeError: If the provided connection is not active.
        """
        if not await self.is_connection_active(connection):
            raise RuntimeError("Cannot get cursor, connection is not active.")
        cur = await connection.cursor()
        return cur

    async def close_cursor(self, cursor: aiosqlite.Cursor) -> int:
        """Close a cursor if it is active.

        Args:
            cursor (aiosqlite.Cursor): Cursor to close.

        Returns:
            int: ``self.success`` on successful close, otherwise ``self.error``.
        """
        title = "close_cursor"
        self.disp.log_debug("Closing cursor, if it is open.", title)
        if await self.is_cursor_active(cursor):
            self.disp.log_debug("Closing cursor", title)
            try:
                # aiosqlite Cursor.close is awaitable
                async with self._lock:
                    await cursor.close()
            except sqlite3.Error:
                pass
            return self.success
        self.disp.log_error(
            "The cursor did not have an active connection.", title)
        return self.error

    async def return_connection(self, connection: aiosqlite.Connection) -> int:
        """Close the given connection and clear the stored connection.

        This method will attempt to close ``connection`` and set
        :attr:`connection` to ``None`` if the provided connection matches the
        stored one. The closure is performed while holding the internal lock
        to avoid races with concurrent operations.

        Args:
            connection (aiosqlite.Connection): Connection to close.

        Returns:
            int: ``self.success`` if closed, otherwise ``self.error``.
        """
        title = "return_connection"
        self.disp.log_debug("Closing a database connection.", title)
        if await self.is_connection_active(connection):
            self.disp.log_debug("Connection has been closed.", title)
            try:
                async with self._lock:
                    await connection.close()
            except sqlite3.Error:
                pass
            self.connection = None
            return self.success
        self.disp.log_error(
            "Connection was not open in the first place.", title)
        return self.error

    async def destroy_pool(self) -> int:
        """Close the stored connection if present and clear internal state.

        This is a convenience method suitable for teardown: it will close the
        stored :attr:`connection` if set and set it to ``None``. It will not
        raise on errors and always returns ``self.success`` (teardown is best
        effort).

        Returns:
            int: ``self.success``.
        """
        title = "destroy_pool"
        self.disp.log_debug("Destroying pool, if it exists.", title)
        if self.connection is not None:
            try:
                self.disp.log_debug("Closing sqlite connection.", title)
                async with self._lock:
                    await self.connection.close()
            except sqlite3.Error:
                pass
            self.connection = None
        self.disp.log_warning("There was no pool to be destroyed.", title)
        return self.success

    async def release_connection_and_cursor(self, connection: Union[aiosqlite.Connection, None], cursor: Union[aiosqlite.Cursor, None] = None) -> None:
        """Close/cleanup cursor and connection objects safely.

        This helper is used by methods that created a temporary cursor and
        need to ensure both the cursor and its connection are closed in a
        safe order. It logs the numerical status returned by the underlying
        close helpers.

        Args:
            connection (Optional[aiosqlite.Connection]): Connection to close.
            cursor (Optional[aiosqlite.Cursor]): Cursor to close.

        Returns:
            None
        """
        title = "release_connection_and_cursor"
        msg = "Connections have ended with status: "
        self.disp.log_debug("Closing cursor.", title)
        status_cursor = await self.close_cursor(cursor) if cursor is not None else self.error
        msg += f"cursor = {status_cursor}, "
        self.disp.log_debug("Closing connection.", title)
        status_conn = await self.return_connection(connection) if connection is not None else self.error
        msg += f"connection = {status_conn}"
        self.disp.log_debug(msg, title)

    async def run_and_commit(self, query: str, cursor: Union[aiosqlite.Cursor, None] = None) -> int:
        """Execute a write-style SQL statement and commit the transaction.

        The method will either use the provided cursor or create one from the
        stored connection. Access to the shared connection/cursor is
        serialized with an internal lock. On success ``self.success`` is
        returned; on programming/SQLite errors a :class:`RuntimeError` is
        raised to surface the underlying problem.

        Args:
            query (str): SQL statement to execute (INSERT/UPDATE/DELETE/...).
            cursor (Optional[aiosqlite.Cursor]): Optional cursor to reuse.

        Returns:
            int: ``self.success`` on success or ``self.error`` on handled
                failures.

        Raises:
            RuntimeError: For unhandled sqlite exceptions (ProgrammingError,
                OperationalError, IntegrityError) the original exception is
                re-raised wrapped in a RuntimeError.
        """
        title = "run_and_commit"
        self.disp.log_debug("Running and committing sql query.", title)
        if cursor is None:
            self.disp.log_debug("No cursor found, generating one.", title)
            connection = self.get_connection()
            if connection is None:
                self.disp.log_critical(SCONST.CONNECTION_FAILED, title)
                return self.error
            internal_cursor = await self.get_cursor(connection)
            if internal_cursor is None:
                self.disp.log_critical(SCONST.CURSOR_FAILED, title)
                return self.error
        else:
            self.disp.log_debug("Cursor found, using it.", title)
            internal_cursor = cursor
        try:
            # Serialize access to the shared connection/cursor
            async with self._lock:
                self.disp.log_debug(f"Executing query: {query}.", title)
                await internal_cursor.execute(query)
                self.disp.log_debug("Committing content.", title)
            # commit using the aiosqlite connection
            conn = getattr(internal_cursor, "_connection", None)
            if conn is None:
                conn = self.connection
            if conn is not None:
                await conn.commit()
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            return self.success
        except sqlite3.ProgrammingError as pe:
            msg = "ProgrammingError: Failed to execute the query."
            msg += f" Original error: {str(pe)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            raise RuntimeError(msg) from pe
        except sqlite3.IntegrityError as ie:
            msg = "IntegrityError: Integrity constraint issue occurred during query execution."
            msg += f" Original error: {str(ie)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            raise RuntimeError(msg) from ie
        except sqlite3.OperationalError as oe:
            msg = "OperationalError: Operational error occurred during query execution."
            msg += f" Original error: {str(oe)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            raise RuntimeError(msg) from oe
        except sqlite3.Error as e:
            msg = "SQLite Error: An unexpected error occurred during query execution."
            msg += f" Original error: {str(e)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            raise RuntimeError(msg) from e

    async def run_and_fetch_all(self, query: str, cursor: Union[aiosqlite.Cursor, None] = None) -> Union[int, Any]:
        """Execute a SELECT-style query and return fetched rows.

        The method returns a list of rows (as produced by
        :meth:`aiosqlite.Cursor.fetchall`) on success, or ``self.error`` on
        failure. The raw rows are returned (caller may use
        :meth:`SQLSanitiseFunctions.beautify_table` to convert to dicts).

        Args:
            query (str): SQL SELECT statement to execute.
            cursor (Optional[aiosqlite.Cursor]): Optional cursor to reuse.

        Returns:
            Union[int, Any]: The fetched rows (usually a List[tuple]) or
                ``self.error`` on failure.
        """
        title = "run_and_fetchall"
        if cursor is None:
            connection = self.get_connection()
            if connection is None:
                self.disp.log_critical(SCONST.CONNECTION_FAILED, title)
                return self.error
            internal_cursor = await self.get_cursor(connection)
            if internal_cursor is None:
                self.disp.log_critical(SCONST.CURSOR_FAILED, title)
                return self.error
        else:
            internal_cursor = cursor
        try:
            # Serialize access to the shared connection/cursor
            async with self._lock:
                self.disp.log_debug(f"Executing query: {query}.", title)
                await internal_cursor.execute(query)
                if internal_cursor is None or internal_cursor.description is None:
                    self.disp.log_error(
                        "Failed to gather data from the table, cursor is invalid.", title
                    )
                    if cursor is None:
                        self.disp.log_debug(
                            "The cursor was generated by us, releasing.", title
                        )
                        await self.release_connection_and_cursor(
                            connection, internal_cursor
                        )
                    else:
                        self.disp.log_debug(
                            "The cursor was provided, not releasing.", title
                        )
                    return self.error
                self.disp.log_debug(
                    "Storing a copy of the content of the cursor.", title
                )
                raw_data = await internal_cursor.fetchall()
                self.disp.log_debug(f"Raw gathered data {raw_data}", title)
                # Ensure we return a concrete list (fetchall may return an iterable)
                data = list(raw_data)
                self.disp.log_debug(f"Data gathered: {data}.", title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            return data
        except sqlite3.ProgrammingError as pe:
            msg = "ProgrammingError: Failed to execute the query."
            msg += f" Original error: {str(pe)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            raise RuntimeError(msg) from pe
        except sqlite3.IntegrityError as ie:
            msg = "IntegrityError: Integrity constraint issue occurred during query execution."
            msg += f" Original error: {str(ie)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
                raise RuntimeError(msg) from ie
        except sqlite3.OperationalError as oe:
            msg = "OperationalError: Operational error occurred during query execution."
            msg += f" Original error: {str(oe)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
            raise RuntimeError(msg) from oe
        except sqlite3.Error as e:
            msg = "SQLite Error: An unexpected error occurred during query execution."
            msg += f" Original error: {str(e)}"
            self.disp.log_error(msg, title)
            if cursor is None:
                self.disp.log_debug(
                    "The cursor was generated by us, releasing.", title
                )
                await self.release_connection_and_cursor(connection, internal_cursor)
            else:
                self.disp.log_debug(
                    "The cursor was provided, not releasing.", title
                )
                raise RuntimeError(msg) from e

    async def run_editing_command(self, sql_query: str, table: str, action_type: str = "update") -> int:
        """Convenience wrapper to run a modifying SQL command and handle
        logging/return codes.

        Args:
            sql_query (str): SQL statement to execute.
            table (str): Table being modified (used in logs).
            action_type (str): Short textual description used for logging.

        Returns:
            int: ``self.success`` on success or ``self.error`` on failure.
        """
        title = "_run_editing_command"
        try:
            resp = await self.run_and_commit(query=sql_query)
            if resp != self.success:
                self.disp.log_error(
                    f"Failed to {action_type} data in '{table}'.", title
                )
                return self.error
            self.disp.log_debug("command ran successfully.", title)
            return self.success
        except sqlite3.Error as e:
            self.disp.log_error(
                f"Failed to {action_type} data in '{table}': {str(e)}", title
            )
            return self.error

    def __del__(self) -> None:
        """Destructor: best-effort cleanup without awaiting.

        Note: :class:`aiosqlite.Connection.close` is a coroutine. Executing
        asynchronous cleanup in ``__del__`` is unsafe. This destructor only
        tries to drop the reference to the connection so the event loop may
        eventually clean up resources.
        """
        # Best-effort: drop the stored connection reference. Avoid raising
        # from __del__ since destructors should not emit exceptions.
        if getattr(self, "connection", None) is not None:
            self.connection = None

    def is_pool_active(self) -> bool:
        """Quick check whether a connection is currently stored.

        Returns:
            bool: True if :attr:`connection` is not ``None``.
        """
        title = "is_pool_active"
        self.disp.log_debug("Checking if the connection is active.", title)
        resp = self.connection is not None
        if resp:
            self.disp.log_debug("The connection is active.", title)
            return True
        self.disp.log_error("The connection is not active.", title)
        return False

    async def is_connection_active(self, connection: Optional[aiosqlite.Connection]) -> bool:
        """Lightweight liveness check for a connection.

        This attempts a minimal SELECT against the provided connection while
        holding the internal lock. The method returns ``True`` if a
        statement executed successfully and ``False`` otherwise.

        Args:
            connection (Optional[aiosqlite.Connection]): Connection to test.

        Returns:
            bool: True if connection appears usable.
        """
        title = "is_connection_active"
        self.disp.log_debug("Checking if the connection is active.", title)
        try:
            if connection is not None:
                # Lightweight check: run a simple SELECT 1
                async with self._lock:
                    cur = await connection.execute("SELECT 1")
                    # fetchone to ensure it executed
                    await cur.fetchone()
                self.disp.log_debug("The connection is active.", title)
                return True
        except sqlite3.Error:
            self.disp.log_error("The connection is not active.", title)
            return False
        self.disp.log_error("The connection is not active.", title)
        return False

    async def is_cursor_active(self, cursor: Optional[aiosqlite.Cursor]) -> bool:
        """Test whether a cursor looks bound to an active connection.

        The implementation detects a cursor as active if it has a ``_connection``
        attribute or if the manager holds a stored connection. This is a best
        effort check; callers should still handle exceptions when using the
        cursor.

        Args:
            cursor (Optional[aiosqlite.Cursor]): Cursor to inspect.

        Returns:
            bool: True when the cursor is likely active.
        """
        title = "is_cursor_active"
        self.disp.log_debug(
            "Checking if the provided cursor is active.", title)
        self.disp.log_debug(f"Content of the cursor: {dir(cursor)}.", title)
        resp = False
        if cursor is not None:
            # If we assigned the _connection attribute in get_cursor, use it
            if hasattr(cursor, "_connection") and getattr(cursor, "_connection") is not None:
                resp = True
            elif self.connection is not None:
                resp = True
        if resp:
            self.disp.log_debug("The cursor is active.", title)
            return True
        self.disp.log_error("The cursor is not active.", title)
        return False
