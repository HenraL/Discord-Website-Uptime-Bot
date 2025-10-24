"""Discord bot integration helpers.

Contains :class:`DiscordBot`, a small wrapper that sets up the
Discord client and provides methods used by the higher-level program
to initialise and run the bot.
"""

from typing import List, Optional, Union

import discord
from discord.ext import tasks
from display_tty import Disp

from .message_handler import MessageHandler

from ..program_globals.helpers import initialise_logger
from ..program_globals.constants import DiscordMessage, SUCCESS, ERROR


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
        self._update_loop: Optional[tasks.Loop] = None

    def __del__(self) -> None:
        """Ensure the bot is shut down during object destruction."""
        self.shutdown()

    def on_ready(self) -> None:
        """Called when the bot is connected and ready."""
        if self.discord_client:
            self.disp.log_info(f"Connected as {self.discord_client.user}")
        else:
            self.disp.log_error("No active client")

    async def _on_ready_wrapper(self) -> None:
        """Internal async hook that forwards to the real handler."""
        self.on_ready()

    def update_message_handler_instance(self, instance: MessageHandler) -> None:
        """Function in charge of updating the instance for the Message Handler class.

        Args:
            instance (MessageHandler): The initialised handler instance.
        """
        self.disp.log_debug(
            f"Assigning the instance '({instance})' to the handler '({self.message_handler})'."
        )
        self.message_handler = instance
        self.disp.log_debug("Message handler instance updated")

    def initialise(self) -> None:
        """Function in charge of setting up the connection for the interraction with the discord api.
        """
        self.discord_intents = discord.Intents.default()
        self.discord_intents.messages = True
        self.discord_intents.guilds = True
        if self.discord_intents is not None:
            self.discord_client = discord.Client(
                intents=self.discord_intents
            )
            self.discord_client.event(self._on_ready_wrapper)
            self.disp.log_debug(
                "Discord client initialised and event registered."
            )
            return
        self.disp.log_error("Discord client initialisation failed.")

    def shutdown(self) -> None:
        """Function in charge of shutting down the bot.
        """
        if self.discord_client:
            del self.discord_client
            self.discord_client = None
        if self.discord_intents:
            del self.discord_intents
            self.discord_intents = None
        if self._update_loop and self._update_loop.is_running():
            self._update_loop.cancel()

    async def _get_channel_name(self, discord_message: DiscordMessage) -> str:
        """Return the name of the channel corresponding to the message's channel ID."""
        if not self.discord_client:
            self.disp.log_error("Discord client not initialized.")
            return "<unknown>"

        channel_id: Optional[int] = discord_message.message_channel
        if channel_id is None:
            self.disp.log_warning("No channel ID found in message object.")
            return "<no-channel>"

        channel = self.discord_client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.discord_client.fetch_channel(channel_id)
            except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden) as e:
                self.disp.log_warning(
                    f"Could not fetch channel ({channel_id}): {e}"
                )
                return f"<missing:{channel_id}>"
        return getattr(channel, "name", f"<no-name:{channel_id}>")

    async def _send_message(self, discord_message: DiscordMessage) -> int:
        """Send a message to a Discord channel and store its message ID."""
        if not self.discord_client:
            self.disp.log_error("Discord client not initialized.")
            return ERROR

        channel_id: Optional[int] = discord_message.message_channel
        if channel_id is None:
            self.disp.log_error("Discord message missing channel ID.")
            return ERROR

        channel = self.discord_client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.discord_client.fetch_channel(channel_id)
            except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden) as e:
                self.disp.log_error(
                    f"Failed to fetch channel {channel_id}: {e}"
                )
                return ERROR

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            self.disp.log_error(
                "Channel is not a TextChannel or Thread. Cannot send messages."
            )
            return ERROR

        try:
            # You can use embed, file, etc. here if desired.
            sent_msg = await channel.send(discord_message.message_human)
            discord_message.message_id = sent_msg.id
            self.disp.log_debug(
                f"Sent message '{discord_message.message_human}' to channel '{channel_id}' (msg_id={sent_msg.id})."
            )
            return SUCCESS
        except discord.Forbidden:
            self.disp.log_error(
                f"Missing permissions to send message in channel {channel_id}."
            )
        except discord.HTTPException as e:
            self.disp.log_error(
                f"Failed to send message in channel {channel_id}: {e}"
            )
        return ERROR

    async def _update_message(self, discord_message: DiscordMessage) -> int:
        """Edit an existing Discord message."""
        if not self.discord_client:
            self.disp.log_error("Discord client not initialized.")
            return ERROR

        channel_id: Optional[int] = discord_message.message_channel
        message_id: Optional[int] = discord_message.message_id

        if not channel_id or not message_id:
            self.disp.log_error(
                "Discord message missing channel or message ID."
            )
            return ERROR

        channel = self.discord_client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.discord_client.fetch_channel(channel_id)
            except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden) as e:
                self.disp.log_error(
                    f"Failed to fetch channel {channel_id}: {e}")
                return ERROR

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            self.disp.log_error(
                "Channel is not a TextChannel or Thread. Cannot send messages."
            )
            return ERROR

        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(content=discord_message.message_human)
            self.disp.log_debug(
                f"Updated message (id={message_id}) in channel '{channel_id}' with new content.")
            return SUCCESS
        except discord.NotFound:
            self.disp.log_warning(
                f"Message {message_id} not found in channel {channel_id}. It might have been deleted.")
        except discord.Forbidden:
            self.disp.log_error(
                f"Missing permissions to edit message {message_id} in channel {channel_id}.")
        except discord.HTTPException as e:
            self.disp.log_error(f"Failed to edit message {message_id}: {e}")
        return ERROR

    async def _refresh_message_statuses(self) -> None:
        """
        Function in charge of refreshing or sending messages to the discord server.
        """
        if not self.message_handler:
            self.disp.log_error(
                "There are not message handler instances present, skipping update")
            return
        message_update: Union[int, List[DiscordMessage]] = await self.message_handler.run()
        if not isinstance(message_update, List):
            self.disp.log_error(
                "Website update failed, see above for error details"
            )
            return
        for message in message_update:
            if not message.message_id:
                # No message was ever sent, sending the first one
                status: int = await self._send_message(message)
                if status != SUCCESS:
                    self.disp.log_error(
                        "Failed to send message, skipping update"
                    )
                    continue
                status: int = await self.message_handler.refresh_message_id(message)
                if status != SUCCESS:
                    self.disp.log_warning(
                        f"Failed to update the website's '(id: {message.website_id})' message_id '({message.message_id})' in the database."
                    )
                    continue
                self.disp.log_info(
                    f"Website status '({message.message_human})' sent to channel '{self._get_channel_name(message)}'."
                )
                continue
            # A message exists, updating it
            status: int = await self._update_message(message)
            if status != SUCCESS:
                self.disp.log_error(
                    "Failed to update message, skipping update"
                )
                continue
            self.disp.log_info(
                f"Website status '({message.message_human})' updated message ('{message.message_id}') on channel '{self._get_channel_name(message)}'."
            )
            continue

    def _create_loop(self, interval_seconds: int):
        """Create a dynamic Discord task loop."""
        @tasks.loop(seconds=interval_seconds)
        async def loop():
            await self._refresh_message_statuses()
        return loop

    async def run(self, interval_seconds: int = 60) -> None:
        """Start the Discord bot and its update loop."""
        if not self.discord_client:
            self.initialise()

        if isinstance(self.discord_client, discord.Client):
            self._update_loop = self._create_loop(interval_seconds)
            self._update_loop.start()

            self.disp.log_info(
                f"Bot loop started with {interval_seconds}s interval.")
            await self.discord_client.start(self.token)
