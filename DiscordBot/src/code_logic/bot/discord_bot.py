"""Discord bot integration helpers.

Contains :class:`DiscordBot`, a small wrapper that sets up the
Discord client and provides methods used by the higher-level program
to initialise and run the bot.
"""

from typing import List, Any, Optional

import requests
import discord
from discord.ext import tasks
from display_tty import Disp

from .message_handler import MessageHandler

from ..program_globals.helpers import initialise_logger


class DiscordBot:
    """Handle Discord bot functions.

    Coordinates Discord client setup and exposes methods used by the
    application to initialise, run and shutdown the bot.
    """
    disp: Disp = initialise_logger(__qualname__, False)

    def __init__(self, message_handler: Optional[MessageHandler], token: str, debug: bool = False) -> None:
        """Initialize the DiscordBot wrapper.

        Args:
            message_handler (Optional[MessageHandler]): Optional handler instance to attach.
            token (str): Discord bot token.
            debug (bool): Enable debug logging.
        """
        self.debug: bool = debug
        self.token: str = token
        self.disp.update_disp_debug(self.debug)
        self.message_handler: Optional[MessageHandler] = message_handler
        self.discord_intents: Optional[discord.Intents] = None
        self.discord_client: Optional[discord.Client] = None

    def __del__(self) -> None:
        """Ensure the bot is shut down during object destruction."""
        self.shutdown()

    def update_message_handler_instance(self, instance: MessageHandler) -> None:
        """Function in charge of updating the instance for the Message Handler class.

        Args:
            instance (MessageHandler): The initialised handler instance.
        """
        self.disp.log_debug(
            f"Assigning the instance '({instance})' to the handler '({self.message_handler})'.")
        self.message_handler = instance
        self.disp.log_debug("Message handler instance updated")

    def initialise(self) -> None:
        """Function in charge of setting up the connection for the interraction with the discord api.
        """
        self.discord_intents = discord.Intents.default()
        self.discord_intents.messages = True
        if self.discord_intents is not None:
            self.discord_client = discord.Client(
                intents=self.discord_intents
            )

    def shutdown(self) -> None:
        """Function in charge of shutting down the bot.
        """
        if self.discord_client:
            del self.discord_client
            self.discord_client = None
        if self.discord_intents:
            del self.discord_intents
            self.discord_intents = None

    async def run(self, interval_seconds: int = 60) -> None:
        """Function in charge of running the main logic of the bot
        """
        if self.message_handler:
            await self.message_handler.run()
