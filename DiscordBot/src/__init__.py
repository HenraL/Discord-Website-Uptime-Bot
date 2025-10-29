"""Top-level package exports for the DiscordBot application.

Exports a small, convenience API for programmatic usage of the
``code_logic`` package (the program entrypoint and helpers).
"""

from .code_logic import Main, start_wrapper
from .code_logic.program_globals import HLP
__all__ = [
    "HLP",
    "Main",
    "start_wrapper"
]
