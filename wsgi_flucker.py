"""
wsgi_flucker.py — Entry file for Discord Website Uptime Bot under O2Switch Passenger.

This simply loads and runs DiscordBot/__main__.py once, in-process.
No threads, no manual loops — The event loop in the program handles everything.
This is a file to call only if one is trying to start the bot in a wsgi app,
such app is typically found in CPanel python starter
"""

import os
import sys
import traceback
import importlib.util
import importlib.machinery
from types import ModuleType
from typing import Any, Callable, Iterable

sys.path.insert(0, os.path.dirname(__file__))


def load_source(modname: str, filename: str) -> ModuleType:
    """Function in charge of locating the program's entrypoint

    Args:
        modname (str): The name of the module's identity
        filename (str): The file to locate the code in

    Raises:
        ImportError: If the module or file could not be located.

    Returns:
        _type_: _description_
    """
    loader = importlib.machinery.SourceFileLoader(modname, filename)
    spec = importlib.util.spec_from_file_location(
        modname, filename, loader=loader)
    if spec is None:
        raise ImportError(
            f"Could not load spec for module '{modname}' from '{filename}'")

    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"Module '{modname}' has no loader")

    spec.loader.exec_module(module)
    return module


def application(
    _environ: dict[str, Any],
    start_response: Callable[[str, list[tuple[str, str]]], None]
) -> Iterable[bytes]:
    """Passenger requires a callable named 'application'."""
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b"Discord Website Uptime Bot is running under Passenger.\n"]


# ---- Startup sequence ----
try:
    print("[Startup] Importing DiscordBot/__main__.py ...", flush=True)
    bot_main = load_source('discordbot_main', 'DiscordBot/__main__.py')

    if hasattr(bot_main, "RUNNER") and callable(bot_main.RUNNER):
        print("[Startup] Calling RUNNER() ...", flush=True)
        bot_main.RUNNER()
    else:
        print("[Error] RUNNER not found in DiscordBot/__main__.py", flush=True)

except Exception:
    print("[Error] Exception during startup:", flush=True)
    traceback.print_exc()
