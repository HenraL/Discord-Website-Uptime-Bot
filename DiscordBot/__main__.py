"""Minimal launcher for the DiscordWebsiteMonitor script.

This module provides an entrypoint so the package can be executed with
``python -m DiscordBot``. It delegates to the standalone
``DiscordWebsiteMonitor`` module.
"""

# for wrapping the v1 call
from functools import partial

# For reading variables from the environment
import os

# Adding the current directory to path (for import safety)
import sys
from pathlib import Path


# Set up file logging if specific variables are set to true
from rotary_logger import RotaryLogger, RL_CONST
sys.path.insert(0, str(Path(__file__).parent))

LOG_FOLDER_BASE_NAME: str = "logs"
LOG_BOOL_CHECK = ("1", "true", "yes")
LOG_TO_FILE = os.environ.get("LOG_TO_FILE", "").lower() in LOG_BOOL_CHECK
LOG_MERGE: bool = os.environ.get("MERGE_LOG", "true").lower() in LOG_BOOL_CHECK
LOG_FOLDER = str(
    Path(__file__).parent / os.environ.get(
        "LOG_FOLDER_NAME",
        default=LOG_FOLDER_BASE_NAME
    )
)

if LOG_TO_FILE:
    RI: RotaryLogger = RotaryLogger(
        log_to_file=LOG_TO_FILE,
        override=False,
        raw_log_folder=LOG_FOLDER,
        merge_streams=LOG_MERGE,
        prefix_out_stream=True,
        prefix_err_stream=True
    )
    RI.start_logging(
        log_folder=Path(LOG_FOLDER),
        max_filesize=2*RL_CONST.GB1,
        merged=LOG_MERGE,
        log_to_file=LOG_TO_FILE
    )
    print("Rotary logger initialised")


# Identifying the usable program
RUNNER = None


try:
    import src
    RUNNER = src.start_wrapper
except ImportError as e:
    print(
        f"Failed to import version 2 of the program, trying another import mode, v2 import error: '{e}'"
    )
    try:
        from .src import start_wrapper
        RUNNER = start_wrapper
    except ImportError as error:
        print(
            f"Failed to import version 2 of the program, defaulting to v1, v2 import error: '{error}'"
        )
        try:
            import DiscordWebsiteMonitor
            RUNNER = partial(
                DiscordWebsiteMonitor.client.run,
                DiscordWebsiteMonitor.TOKEN
            )
        except ImportError as e2:
            err: str = f"Could not find any versions of the program that could be started, v1 import error: {e2}"
            print(err)
            raise RuntimeError(err) from e2


# If we are the main entrypoint, starting the program
if __name__ == "__main__":
    if RUNNER:
        RUNNER()
