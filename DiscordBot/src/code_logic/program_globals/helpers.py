"""File containing general functions that aim to help th basic program logic."""
import os
import re
import sys
import pathlib
import asyncio
import threading
from typing import Any
from functools import partial
import urllib3.util as uurlib3

from display_tty import Disp, TOML_CONF, SAVE_TO_FILE, FILE_NAME
from ask_question import AskQuestion

from . import constants as CONST

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
                        r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
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
    print("\t-\t-h, --help   \tDisplay this help and exit")
    print("\t-\t-d, --debug  \tEnable debugging mode")
    print("\t-\t-a, --author \tDisplay the Author name and exit")
    print("\t-\t-v, --version\tDisplay the version of this program and exit")


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


def check_input_args() -> bool:
    """Function to check the arguments that were provided by the user.

    Returns:
        bool: Wether debug is enabled or not.
    """
    DEBUG = False
    for i in sys.argv:
        DISP.log_debug(f"arg: {i}")
        node: str = i.lower()
        DISP.log_debug(f"arg_lower: {node}")
        if "-d" in node:
            DEBUG = not DEBUG
            DISP.update_disp_debug(DEBUG)
            DISP.log_debug("Debug is active")
        if "-h" in node:
            display_help()
            sys.exit(CONST.SUCCESS)
        if "-v" in node:
            display_version()
            sys.exit(CONST.SUCCESS)
        if "-a" in node:
            display_author()
            sys.exit(CONST.SUCCESS)
    return DEBUG


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

    # Case 1: A loop exists and is running in *this* thread
    if loop and loop.is_running():
        # Check if we're in the same thread as the loop
        if threading.current_thread() is threading.main_thread():
            # We're inside the same thread as the running loop (e.g. in async code)
            # We cannot block, so create a task and run it via loop.run_until_complete if possible
            task = loop.create_task(function())
            return loop.run_until_complete(task)
        # We’re in another thread, safe to use run_coroutine_threadsafe
        future = asyncio.run_coroutine_threadsafe(function(), loop)
        return future.result()

    # Case 2: No loop running anywhere in this thread
    with _LOOP_LOCK:
        return asyncio.run(function())
