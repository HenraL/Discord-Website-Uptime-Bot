"""File containing general functions that aim to help th basic program logic."""
import os
import re
import sys
import pathlib
import asyncio
import threading
from typing import Any, Tuple, Optional, Union
from functools import partial
import urllib3.util as uurlib3

from colorama import just_fix_windows_console
from display_tty import Disp, TOML_CONF, SAVE_TO_FILE, FILE_NAME
from ask_question import AskQuestion

from . import constants as CONST

# All the crappy little windows display bugs that could occur
just_fix_windows_console()

_LOOP_LOCK = threading.Lock()

AQ: AskQuestion = AskQuestion()


def initialise_logger(class_name: str, debug: bool = False) -> Disp:
    """Function to create the Logger library

    Args:
        class_name (str): The name of the class impacted by the logger
        debug (bool, optional): Whether the logger should display debug levels or not. Defaults to False.

    Returns:
        Disp: The initialised instance
    """
    return Disp(
        TOML_CONF,
        SAVE_TO_FILE,
        FILE_NAME,
        debug=debug,
        logger=class_name
    )


DISP: Disp = initialise_logger(
    f"<no_class, file: {os.path.basename(__file__)}>",
    False
)


def load_dotenv_if_present(cwd: str = "") -> None:
    """Check for a .env or ../.env file and inject variables into os.environ if present.

    Args:
        cwd (str, optional): The base path to look for the environement file. Defaults to "".
    """
    if cwd == "":
        cwd = __file__
    env_paths = [
        pathlib.Path(cwd) / ".env",
        pathlib.Path(cwd).parent / ".env",
        pathlib.Path(cwd).parent.parent / ".env"
    ]
    DISP.log_debug(f"Environment search paths: {env_paths}")
    for env_path in env_paths:
        if env_path.is_file():
            with env_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Match KEY=VALUE, allowing for spaces around =
                    match = re.match(
                        r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$',
                        line
                    )
                    if match:
                        key, value = match.groups()
                        # Remove optional surrounding quotes
                        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        os.environ.setdefault(key, value)
            DISP.log_info(f"environement file ({env_path}) loaded.")
            return  # Only load the first found .env file
    DISP.log_info("No environement files loaded")


def get_environement_variable(var_name: str) -> str:
    """Get the environement variable from the system environement

    Args:
        var_name (str): The name to look for

    Raises:
        ValueError: The error raised when the variable is not present.

    Returns:
        str: The value of the variable.
    """
    if var_name not in os.environ:
        raise ValueError(
            f"The expected environement variable {var_name} is missing."
        )
    return os.environ[var_name]


def create_savefile_if_not_present(save_file: str, last_node_is_a_file: bool = False) -> None:
    """Function in charge of creating the savefile if non where found

    Args:
        save_file (str): The save file path.
    """
    if last_node_is_a_file:
        folders: str = str(pathlib.Path(save_file).parent)
    else:
        folders: str = str(pathlib.Path(save_file))
    if os.path.exists(folders) and not os.path.isdir(folders):
        question: str = f"The destination path '({folders})' exists and is not a folder, do you wish to remove it? [(y)es/(n)o]: "
        resp = AQ.ask_question(question=question, answer_type="bool")
        if not isinstance(resp, bool):
            raise RuntimeError(
                f"Received a response in an unexpected format, response: '{resp}', type: '{type(resp)}'"
            )
        if resp:
            DISP.log_info(
                f"Removing destination path '({folders})'"
            )
            os.remove(folders)
        else:
            raise RuntimeError(
                "You refused to remove the destination path, please move it to another location or remove it yourself for the program to work."
            )
    if not os.path.isdir(folders):
        DISP.log_info(f"Creating savefile folders ({folders})")
        os.makedirs(folders, exist_ok=True)
    if os.path.isfile(save_file) is False and last_node_is_a_file:
        DISP.log_info(f"Creating an empty savefile ({save_file})")
        with open(save_file, "w", encoding="utf-8") as f:
            f.write("")


def get_base_url(url: str) -> str:
    """Function in charge of returning the base url of the website being checked

    Args:
        url (str): The url to process.

    Returns:
        str: The processed url
    """
    DISP.log_debug(f"Input url: {url}")
    decomposed_url_node: uurlib3.Url = uurlib3.parse_url(url)
    host: str = decomposed_url_node.host if decomposed_url_node.host else ""
    scheme: str = f"{decomposed_url_node.scheme}://" if decomposed_url_node.scheme else ""
    port: str = f":{decomposed_url_node.port}" if decomposed_url_node.port else ""
    DISP.log_debug(f"host: {host}, scheme: {scheme}, port: {port}")
    final: str = f"{scheme}{host}{port}"
    DISP.log_info(f"cleaned url: {final}")
    return final


def display_help() -> None:
    """Function in charge of displaying the help for the program
    """
    print("USAGE:")
    print(
        f"\t{sys.orig_argv[0]} {sys.argv[0]} [--help | --debug | --author | --version]"
    )
    print("OPTIONS:")
    print("\t-\t-h, --help                    \tDisplay this help and exit.")
    print("\t-\t-d, --debug                   \tEnable debugging mode.")
    print("\t-\t-a, --author                  \tDisplay the Author name and exit.")
    print("\t-\t-v, --version                 \tDisplay the version of this program and exit.")
    print("\t-\t-s <delay>, --seconds=<delay> \tSet the delay (seconds) between each iteration check (default: 60).")
    print(
        f"\t-\t-o <mode>, --output=<mode>    \tSet the output mode ({CONST.OUTPUT_RAW}, {CONST.OUTPUT_MARKDOWN}, {CONST.OUTPUT_EMBED}) of the discord message for the run, set it in the environement for persistence."
    )


def display_version() -> None:
    """Function in charge of displaying the version of the program.
    """
    print("VERSION:")
    print(f"The version of this program is: {CONST.VERSION}")


def display_author() -> None:
    """Function in charge of displaying the author of the program.
    """
    print("AUTHOR:")
    print(f"This program was written by {CONST.AUTHOR}")


def check_input_args() -> Union[int, Tuple[bool, float, Optional[CONST.OutputMode]]]:
    """Function to check the arguments that were provided by the user.

    Returns:
        bool: Wether debug is enabled or not.
    """
    DISP.log_info("Loading environement prematurely (in case it is present)")
    load_dotenv_if_present(CONST.CWD)
    DISP.log_info("If present, the environement was loaded prematurely")
    _index: int = -1
    _delay: float = 60
    _debug: bool = os.environ.get(
        CONST.DEBUG_TOKEN,
        ""
    ).lower() in (
        "1",
        "true",
        "yes"
    )
    _argc: int = len(sys.argv)
    _output_mode: Optional[CONST.OutputMode] = None
    while _index+1 < _argc:
        _index += 1
        DISP.log_debug(f"argv[{_index}]={sys.argv[_index]}")
        _node: str = sys.argv[_index].lower()
        DISP.log_debug(f"arg_lower: '{_node}'")
        if "-d" in _node or "--d" in _node:
            _debug = not _debug
            DISP.update_disp_debug(_debug)
            DISP.log_debug("Debug is active")
        if "-h" in _node or "--h" in _node:
            display_help()
            return CONST.SUCCESS
        if "-v" in _node or "--v" in _node:
            display_version()
            return CONST.SUCCESS
        if "-a" in _node or "--a" in _node:
            display_author()
            return CONST.SUCCESS
        if "-o" in _node or "--o" in _node or "-output" in _node or "--output" in _node:
            child = ""
            if "=" in _node:
                child = _node.split("=", 1)[-1]
            elif _index+1 != _argc and sys.argv[_index+1][0] != '-':
                child = sys.argv[_index+1].lower()
                _index += 1
            else:
                DISP.log_warning(
                    f"Unknown or badly formated parameter: '{_node}'"
                )
            if len(child) == 0:
                DISP.log_warning(
                    "Parameter value is missing, skipping argument"
                )
                continue
            if child == CONST.OUTPUT_RAW:
                _output_mode = CONST.OutputMode.RAW
            elif child == CONST.OUTPUT_MARKDOWN:
                _output_mode = CONST.OutputMode.MARKDOWN
            elif child == CONST.OUTPUT_EMBED:
                _output_mode = CONST.OutputMode.EMBED
            else:
                DISP.log_warning(
                    f"Wrong parameter, expected ({CONST.OUTPUT_RAW}, {CONST.OUTPUT_MARKDOWN}, {CONST.OUTPUT_EMBED}) but got: {child}"
                )
                _output_mode = None
        if "-s" in _node or "--s" in _node or "-second" in _node or "--second" in _node:
            child = ""
            if "=" in _node:
                child = _node.split("=", 1)[-1]
            elif _index+1 != _argc and sys.argv[_index+1][0] != '-':
                child = sys.argv[_index+1].lower()
                _index += 1
            else:
                DISP.log_warning(
                    f"Unknown or badly formated parameter: '{_node}'"
                )
            if len(child) == 0:
                DISP.log_warning(
                    "Parameter value is missing, skipping argument"
                )
                continue
            try:
                value: float = float(child)
                if value < 0:
                    DISP.log_warning(
                        "Negative values not supported, converting to positive"
                    )
                    value *= -1
                if value < CONST.MIN_DELAY_BETWEEN_CHECKS:
                    DISP.log_warning(
                        f"Waiting delay is smaller than the default allowed, defaulting to minimum allowed: {CONST.MIN_DELAY_BETWEEN_CHECKS}"
                    )
                    value = CONST.MIN_DELAY_BETWEEN_CHECKS
                _delay = value
            except ValueError as e:
                DISP.log_warning(
                    f"Provided value is not a number, ignoring, (info) error: {e}"
                )
    _resp = [_debug, _delay, _output_mode]
    DISP.log_debug(f"Debug, Delay = {_resp}")
    _tupled = tuple(_resp)
    DISP.log_debug(f"_tupled = {_tupled}")
    return _tupled


def await_async_function_from_synchronous(function: partial) -> Any:
    """Safely call an async function from sync code, thread-safe and loop-aware.

    Args:
        function (partial): The asynchronous function to call.

    Returns:
        Any: the return value of the function, if any
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        if threading.current_thread() is threading.main_thread():
            task = loop.create_task(function())
            return loop.run_until_complete(task)
        future = asyncio.run_coroutine_threadsafe(function(), loop)
        return future.result()

    with _LOOP_LOCK:
        return asyncio.run(function())
