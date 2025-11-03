"""
wsgi_flucker.py — Entry file for Discord Website Uptime Bot under O2Switch Passenger.

This simply loads and runs DiscordBot/__main__.py once, in-process.
No threads, no manual loops — The event loop in the program handles everything.
This file exists as a tiny WSGI "shim" intended for use on hosts (Passenger / cPanel)
that only support starting Python code through a WSGI entrypoint.

Note: this is a hacky / brittle technique — it only attempts to coax a long-running
asyncio-based Discord bot into starting from a WSGI-style launcher. WSGI servers are
not designed to host persistent background workers; this shim may be killed by the
host, behave inconsistently, or conflict with the hosting provider's lifecycle.
Prefer running the bot under Docker, systemd, a supervisor (supervisord), or a
proper process manager. Only use this shim when you understand the limitations.
"""

import os
import sys
import traceback
import importlib.util
import importlib.machinery
from types import ModuleType
from typing import Any, Callable, Iterable

sys.path.insert(0, os.path.dirname(__file__))

try:
    from wsgi_lock import acquire_wsgi_lock
except ImportError as e:
    raise ImportError(
        "Could not locate the lock handler module to prevent more than 1 process from starting."
    ) from e


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
    if spec is None or hasattr(spec, "loader") is False:
        raise ImportError(
            f"Could not load spec for module '{modname}' from '{filename}'"
        )

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
    return [b"Discord Website Uptime Bot WSGI entry alive.\n"]


# ---- Startup ----
try:
    print("[Startup] Importing DiscordBot/__main__.py ...", flush=True)
    bot_main = load_source('discordbot_main', 'DiscordBot/__main__.py')

    if hasattr(bot_main, "RUNNER") and callable(bot_main.RUNNER):
        print("[Startup] Attempting to acquire WSGI lock ...", flush=True)
        if acquire_wsgi_lock():
            print("[Startup] Lock acquired, starting bot RUNNER() ...", flush=True)
            bot_main.RUNNER()
        else:
            print("[Startup] Another instance is running. Skipping RUNNER.", flush=True)
    else:
        print("[Error] RUNNER not found in DiscordBot/__main__.py", flush=True)

except Exception:
    print("[Error] Exception during startup:", flush=True)
    traceback.print_exc()
