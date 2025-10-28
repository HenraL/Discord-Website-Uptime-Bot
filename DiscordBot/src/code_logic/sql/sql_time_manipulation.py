"""Date/time conversion helpers used by SQL modules.

Utilities to convert between :class:`datetime` instances and the
project's string formats used when storing timestamps in the database.
"""
from datetime import datetime

from display_tty import Disp
from ..program_globals.helpers import initialise_logger

from . import sql_constants as SCONST


class SQLTimeManipulation:
    """Utility functions to convert between datetime and formatted strings.

    This helper centralises the project's date/time formatting so the
    SQL-related modules can remain consistent when inserting or reading
    timestamps from the database.
    """

    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(self, debug: bool = False) -> None:
        """Create the time helper.

        Args:
            debug (bool): Enable debug logging output.
        """
        self.debug: bool = debug
        # ----------------------- Inherited from SCONST  -----------------------
        self.date_only: str = SCONST.DATE_ONLY
        self.date_and_time: str = SCONST.DATE_AND_TIME
        # --------------------------- logger section ---------------------------
        self.disp.update_disp_debug(self.debug)

    def datetime_to_string(self, datetime_instance: datetime, date_only: bool = False, sql_mode: bool = False) -> str:
        """Format a :class:`datetime` to the project's string representation.

        Args:
            datetime_instance (datetime): Datetime to format.
            date_only (bool): When True, return only the date portion.
            sql_mode (bool): When True, include millisecond precision suitable
                for insertion into SQL text fields.

        Raises:
            ValueError: If ``datetime_instance`` is not a :class:`datetime`.

        Returns:
            str: Formatted date/time string.
        """

        if not isinstance(datetime_instance, datetime):
            self.disp.log_error(
                "The input is not a datetime instance.",
                "datetime_to_string"
            )
            raise ValueError("Error: Expected a datetime instance.")
        if date_only is True:
            return datetime_instance.strftime(self.date_only)
        converted_time = datetime_instance.strftime(self.date_and_time)
        if sql_mode is True:
            microsecond = datetime_instance.strftime("%f")[:3]
            res = f"{converted_time}.{microsecond}"
        else:
            res = f"{converted_time}"
        return res

    def string_to_datetime(self, datetime_string_instance: str, date_only: bool = False) -> datetime:
        """Parse a formatted date/time string into a :class:`datetime`.

        Args:
            datetime_string_instance (str): The string to parse.
            date_only (bool): When True, parse using the date-only format.

        Raises:
            ValueError: If the input is not a string or cannot be parsed.

        Returns:
            datetime: Parsed :class:`datetime` instance.
        """

        if not isinstance(datetime_string_instance, str):
            self.disp.log_error(
                "The input is not a string instance.",
                "string_to_datetime"
            )
            raise ValueError("Error: Expected a string instance.")
        if date_only is True:
            return datetime.strptime(datetime_string_instance, self.date_only)
        return datetime.strptime(datetime_string_instance, self.date_and_time)

    def get_correct_now_value(self) -> str:
        """Return the current date/time formatted using the project's pattern.

        Returns:
            str: Formatted current date/time string.
        """
        current_time = datetime.now()
        return current_time.strftime(self.date_and_time)

    def get_correct_current_date_value(self) -> str:
        """Return the current date formatted using the project's date-only pattern.

        Returns:
            str: Formatted current date string.
        """
        current_time = datetime.now()
        return current_time.strftime(self.date_only)
