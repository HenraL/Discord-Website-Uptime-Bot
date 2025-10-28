"""Top-level package exports for the DiscordBot application.

Exports a small, convenience API for programmatic usage of the
``code_logic`` package (the program entrypoint and helpers).
"""

from .code_logic import Main
from .code_logic.program_globals import HLP
__all__ = [
    "Main",
    "HLP"
]
