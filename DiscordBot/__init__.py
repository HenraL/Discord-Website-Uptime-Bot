"""Minimal launcher for the DiscordWebsiteMonitor script.

This module provides an entrypoint so the package can be executed with
``python -m DiscordBot``. It delegates to the standalone
``DiscordWebsiteMonitor`` module.
"""

from functools import partial

# Adding the current directory to path (for import safety)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Identifying the usable program
RUNNER = None


try:
    import src
    RUNNER = src.start_wrapper
    __all__ = ["src"]
except ImportError as e:
    print(
        f"Failed to import version 2 of the program, trying another import mode, v2 import error: '{e}'"
    )
    try:
        from . import src
        RUNNER = src.start_wrapper
        __all__ = ["src"]
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
            __all__ = ["DiscordWebsiteMonitor"]
        except ImportError as e2:
            err: str = f"Could not find any versions of the program that could be started, v1 import error: {e2}"
            print(err)
            raise RuntimeError(err) from e2


# If we are the main entrypoint, starting the program
if __name__ == "__main__":
    if RUNNER:
        RUNNER()
