"""Bot package: Discord integration and message handling helpers.

Exports the :class:`DiscordBot` and :class:`MessageHandler` classes.
"""

from .discord_bot import DiscordBot
from .message_handler import MessageHandler

__all__ = [
    "DiscordBot",
    "MessageHandler"
]
