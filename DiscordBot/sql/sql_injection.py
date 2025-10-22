"""
    EPITECH PROJECT, 2022
    Desktop_pet (Workspace)
    File description:
    injection.py

    The file un charge of checking if an injection is attempted with the open database
"""

import base64
import binascii
from typing import Union, List, Any, Callable

from display_tty import Disp, TOML_CONF, SAVE_TO_FILE, FILE_NAME


class SQLInjection:
    """Helpers to detect likely SQL injection attempts.

    This class provides a set of defensive checks (symbol, keyword and
    logic-gate detection) that are used across the project before constructing
    SQL queries. The checks are conservative and return ``True`` when an
    injection-like pattern is detected.

    Attributes:
        error (int): Numeric error code used by callers.
        success (int): Numeric success code used by callers.
        debug (bool): When True, additional debug output is emitted.
    """

    def __init__(self, error: int = 84, success: int = 0, debug: bool = False) -> None:
        # ---------------------------- Status codes ----------------------------
        self.debug: bool = debug
        self.error: int = error
        self.success: int = success
        # ---------------------------- Logging data ----------------------------
        self.disp: Disp = Disp(
            TOML_CONF,
            SAVE_TO_FILE,
            FILE_NAME,
            self.debug,
            logger=self.__class__.__name__
        )
        # ------------------ Injection checking related data  ------------------
        self.injection_err: int = (-1)
        self.injection_message: str = "Injection attempt detected"
        self.symbols: List[str] = [';', '--', '/*', '*/']
        self.keywords: List[str] = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE',
            'DROP', 'CREATE', 'ALTER', 'TABLE', 'UNION', 'JOIN', 'WHERE'
        ]
        self.command: List[str] = self.keywords
        self.logic_gates: List[str] = ['OR', 'AND', 'NOT']
        self.all: List[str] = []
        self.all.extend(self.keywords)
        self.all.extend(self.symbols)
        self.all.extend(self.keywords)

    def _perror(self, string: str = "") -> None:
        """Log/display a short injection-related error message.

        Args:
            string (str): Human-readable error message to display.
        """
        self.disp.disp_print_error(f"(Injection) {string}")

    def _is_base64(self, string: str) -> bool:
        """Return True if ``string`` is valid base64.

        Args:
            string (str): Candidate string.

        Returns:
            bool: True if ``string`` decodes as base64, False otherwise.
        """
        try:
            base64.b64decode(string, validate=True)
            return True
        except (binascii.Error, ValueError):
            return False

    def check_if_symbol_sql_injection(self, string: Union[str, List[str]]) -> bool:
        """Detect injection-like symbols in the input.

        This looks for characters or sequences commonly used in SQL
        injection payloads (for example ``;`` or ``--``). If ``string`` is a
        list, each element is checked recursively.

        Args:
            string (Union[str, List[str]]): String or list of strings to scan.

        Returns:
            bool: True when an injection-like symbol is detected, False
                otherwise.
        """
        if isinstance(string, List):
            for i in string:
                if self.check_if_symbol_sql_injection(i):
                    return True
            return False
        if isinstance(string, str):
            if ";base64" in string:
                return self._is_base64(string)
            for i in self.symbols:
                if i in string:
                    self.disp.log_debug(
                        f"Failed for {string}, node {i} was found.",
                        "check_if_symbol_sql_injection"
                    )
                    return True
        else:
            msg = "(check_if_symbol_sql_injection) string must be a string or a List of strings"
            self._perror(msg)
            return True
        return False

    def check_if_command_sql_injection(self, string: Union[str, List[str]]) -> bool:
        """Detect SQL keywords in the input.

        This checks for common SQL command keywords (SELECT, DROP, UNION,
        etc.). If ``string`` is a list, each element is checked recursively.

        Args:
            string (Union[str, List[str]]): String or list of strings to scan.

        Returns:
            bool: True when an SQL keyword is found, False otherwise.
        """
        if self.debug:
            msg = "(check_if_command_sql_injection) string = "
            msg += f"'{string}', type(string) = '{type(string)}'"
            self.disp.disp_print_debug(msg)
        if isinstance(string, List):
            for i in string:
                if self.check_if_command_sql_injection(i):
                    return True
            return False
        if isinstance(string, str):
            for i in self.keywords:
                if i in string:
                    self.disp.log_debug(
                        f"Failed for {string}, node {i} was found.",
                        "check_if_command_sql_injection"
                    )
                    return True
        else:
            msg = "(check_if_command_sql_injection) string must be a string or a List of strings"
            self._perror(msg)
            return True
        return False

    def check_if_logic_gate_sql_injection(self, string: Union[str, List[str]]) -> bool:
        """Detect logical operators (AND/OR/NOT) in the input.

        Useful to catch attempts that combine conditions to bypass simple
        filters. Accepts a string or list of strings.

        Args:
            string (Union[str, List[str]]): String or list of strings to scan.

        Returns:
            bool: True when a logic gate is present, False otherwise.
        """
        if isinstance(string, List) is True:
            for i in string:
                if self.check_if_logic_gate_sql_injection(i):
                    return True
            return False
        if isinstance(string, str):
            for i in self.logic_gates:
                if i in string:
                    self.disp.log_debug(
                        f"Failed for {string}, node {i} was found.",
                        "check_if_logic_gate_sql_injection"
                    )
                    return True
        else:
            msg = "(check_if_logic_gate_sql_injection) string must be a string or a List of strings"
            self._perror(msg)
            return True
        return False

    def check_if_symbol_and_command_injection(self, string: Union[str, List[str]]) -> bool:
        """Combined check for symbol- or keyword-based injection patterns.

        Args:
            string (Union[str, List[str]]): Input to scan.

        Returns:
            bool: True when either symbol- or keyword-based injection is found.
        """
        is_symbol = self.check_if_symbol_sql_injection(string)
        is_command = self.check_if_command_sql_injection(string)
        if is_symbol or is_command:
            return True
        return False

    def check_if_symbol_and_logic_gate_injection(self, string: Union[str, List[str]]) -> bool:
        """Combined check for symbol- or logic-gate-based injection patterns.

        Args:
            string (Union[str, List[str]]): Input to scan.

        Returns:
            bool: True when symbol- or logic-gate-based injection is found.
        """
        is_symbol = self.check_if_symbol_sql_injection(string)
        is_logic_gate = self.check_if_logic_gate_sql_injection(string)
        if is_symbol or is_logic_gate:
            return True
        return False

    def check_if_command_and_logic_gate_injection(self, string: Union[str, List[str]]) -> bool:
        """Combined check for keyword- or logic-gate-based injection patterns.

        Args:
            string (Union[str, List[str]]): Input to scan.

        Returns:
            bool: True when a command or logic-gate-based injection is found.
        """
        is_command = self.check_if_command_sql_injection(string)
        is_logic_gate = self.check_if_logic_gate_sql_injection(string)
        if is_command or is_logic_gate:
            return True
        return False

    def check_if_sql_injection(self, string: Union[str, List[str]]) -> bool:
        """High-level SQL injection detection using all configured checks.

        This method runs a combined scan (symbols, keywords and logic gates)
        and returns True if any of the component checks considers the input
        dangerous.

        Args:
            string (Union[str, List[str]]): Input to scan; may be a string or a
                list (including nested lists).

        Returns:
            bool: True when an injection-like pattern is detected, False
                otherwise.
        """
        if isinstance(string, List) is True:
            for i in string:
                if self.check_if_sql_injection(i):
                    return True
            return False
        if isinstance(string, str):
            if ";base64" in string:
                return self._is_base64(string)
            for i in self.all:
                if i in string:
                    return True
        else:
            msg = "(check_if_sql_injection) string must be a string or a List of strings"
            self._perror(msg)
            return True
        return False

    def check_if_injections_in_strings(self, array_of_strings: Union[str, List[str], List[List[str]]]) -> bool:
        """Scan an array (possibly nested) of strings for injection patterns.

        This convenience function accepts a string, a list of strings, or a
        nested list of strings and returns True if any element appears to be
        an injection.

        Args:
            array_of_strings (Union[str, List[str], List[List[str]]]): Item(s) to scan.

        Returns:
            bool: True when an injection-like value is detected.
        """
        if isinstance(array_of_strings, List) is True:
            for i in array_of_strings:
                if isinstance(i, List) is True:
                    if self.check_if_injections_in_strings(i) is True:
                        return True
                    continue
                if not isinstance(i, str):
                    err_message = "(check_if_injections_in_strings) Expected a string but "
                    err_message += f"got an {type(i)}"
                    self._perror(err_message)
                    return True
                if self.check_if_sql_injection(i):
                    return True
            return False
        if isinstance(array_of_strings, str):
            if self.check_if_sql_injection(array_of_strings):
                return True
            return False
        err_message = "(check_if_injections_in_strings) The provided item is neither a List a table or a string"
        self._perror(err_message)
        return False

    def run_test(self, title: str, array: List[Any], function: Callable[[Any], bool], expected_response: bool = False, global_status: int = 0) -> int:
        """Run a small functional test over the injection-checker functions.

        This helper is used by :meth:`test_injection_class` and not by the
        production code path. It calls ``function`` for each element in
        ``array`` and compares the result to ``expected_response``.

        Args:
            title (str): Short test title printed to stdout.
            array (List[Any]): Items to test (may be strings or nested lists).
            function (Callable[[Any], bool]): Function to call for each item.
            expected_response (bool): Expected boolean response for each call.
            global_status (int): Running global status to update.

        Returns:
            int: Updated global status (``0`` for success, error code otherwise).
        """
        err = 84
        global_response = global_status
        print(f"{title}", end="")
        for i in array:
            print(".", end="")
            response = function(i)
            if response != expected_response:
                print("[error]")
                global_response = err
        print("[success]")
        return global_response

    def test_injection_class(self) -> int:
        """Run a small suite of self-tests for the injection checks.

        Returns:
            int: ``0`` on success, non-zero error code if any test fails.
        """
        success = 0
        global_status = success
        test_sentences = [
            "SHOW TABLES;",
            "SHOW Databases;",
            "DROP TABLES;",
            "SHOW DATABASE;",
            "SELECT * FROM table;",
        ]
        global_status = self.run_test(
            title="Logic gate test:",
            array=self.logic_gates,
            function=self.check_if_logic_gate_sql_injection,
            expected_response=True,
            global_status=global_status
        )
        global_status = self.run_test(
            title="Keyword check:",
            array=self.keywords,
            function=self.check_if_command_sql_injection,
            expected_response=True,
            global_status=global_status
        )
        global_status = self.run_test(
            title="Symbol check:",
            array=self.symbols,
            function=self.check_if_symbol_sql_injection,
            expected_response=True,
            global_status=global_status
        )
        global_status = self.run_test(
            title="All injections:",
            array=self.all,
            function=self.check_if_sql_injection,
            expected_response=True,
            global_status=global_status
        )
        global_status = self.run_test(
            title="Array check:",
            array=[self.all],
            function=self.check_if_injections_in_strings,
            expected_response=True,
            global_status=global_status
        )
        global_status = self.run_test(
            title="Double array check:",
            array=[self.all, self.all],
            function=self.check_if_injections_in_strings,
            expected_response=True,
            global_status=global_status
        )
        global_status = self.run_test(
            title="SQL sentences:",
            array=test_sentences,
            function=self.check_if_sql_injection,
            expected_response=True,
            global_status=global_status
        )
        return global_status


if __name__ == "__main__":
    II = SQLInjection()
    res = II.test_injection_class()
    print(f"test status = {res}")
