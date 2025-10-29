"""Minimal launcher for the DiscordWebsiteMonitor script.

This module provides an entrypoint so the package can be executed with
``python -m DiscordBot``. It delegates to the standalone
``DiscordWebsiteMonitor`` module.
"""

from functools import partial

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


if __name__ == "__main__":
    if RUNNER:
        RUNNER()
