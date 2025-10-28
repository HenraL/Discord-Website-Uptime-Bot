"""Minimal launcher for the DiscordWebsiteMonitor script.

This module provides an entrypoint so the package can be executed with
``python -m DiscordBot``. It delegates to the standalone
``DiscordWebsiteMonitor`` module.
"""

DWM = None
V2 = None

try:
    import src.code_logic
    V2 = src.code_logic.start_wrapper
except ImportError as e:
    print(
        f"Failed to import version 2 of the program, defaulting to v1, v2 import error: '{e}'"
    )
    try:
        import DiscordWebsiteMonitor
        DWM = DiscordWebsiteMonitor
    except ImportError as e2:
        err: str = f"Could not find any versions of the program that could be started, v1 import error: {e2}"
        print(err)
        raise RuntimeError(err) from e2


if __name__ == "__main__":
    if V2:
        V2()
    if DWM:
        DWM.client.run(DWM.TOKEN)
