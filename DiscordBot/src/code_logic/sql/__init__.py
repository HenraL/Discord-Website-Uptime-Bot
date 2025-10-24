"""SQL helpers package.

Provides an async-friendly SQL facade and related utilities used by the
application (``SQL``, ``SQLInjection``, etc.).
"""

from .sql_manager import SQL
from .sql_injection import SQLInjection

__all__ = [
    "SQLInjection",
    "SQL"
]
