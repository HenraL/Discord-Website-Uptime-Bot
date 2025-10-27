"""Discord bot integration helpers.

Contains :class:`DiscordBot`, a small wrapper that sets up the
Discord client and provides methods used by the higher-level program
to initialise and run the bot.
"""

from typing import List, Optional, Union, Tuple, Any
from datetime import datetime

import discord
from discord import Embed, Color
from discord.ext import tasks


from display_tty import Disp

from .message_handler import MessageHandler

from ..program_globals.helpers import initialise_logger
from ..program_globals.constants import DiscordMessage, SUCCESS, ERROR, \
    OutputMode, WebsiteStatus, EMBED_COLOUR, STATUS_EMOJI, \
    MAX_ALLOWED_EMBEDDED_FIELDS, MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS, MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS, \
    INLINE_FIELDS, \
    DISCORD_MESSAGE_NEWLINE, DISCORD_MESSAGE_BEGIN_FOOTER, DISCORD_MESSAGE_END_FOOTER, \
    DISCORD_EMBEDING_MESSAGE, DISCORD_PERMISSIONS_EXPLANATION, DISCORD_MESSAGE_CONTENT_INTENT_ERROR, \
    DISCORD_DEFAULT_MESSAGE_CONTENT, DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED, \
    MSG_RUNTIME_CRITICAL_INIT_ERROR, MSG_CRITICAL_DISABLE_MESSAGE_CONTENT, MSG_CRITICAL_NO_ACTIVE_CLIENT_INSTANCE, \
    MSG_ERROR_UPDATE_ERROR, MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED, MSG_ERROR_DISCORD_CLIENT_INITIALISATION_FAILED, \
    MSG_ERROR_WEBSITE_UPDATE_FAILED, MSG_ERROR_NO_MESSAGE_HANDLER_INSTANCE, MSG_ERROR_MESSAGE_SEND_FAILED, MSG_ERROR_MESSAGE_RETRIEVAL_FAILED, \
    MSG_ERROR_NO_CHANNEL_OR_MESSAGE_ID, MSG_ERROR_CHANNEL_NOT_A_TEXTCHANNEL_OR_THREAD, MSG_ERROR_MESSAGE_MISSING_CHANNEL_ID, \
    MSG_ERROR_CHANNEL_IS_NOT_A_TEXTCHANNEL_OR_THREAD, MSG_ERROR_MESSAGE_INTENTS_STATUS_MISSING, MSG_ERROR_SOMETHING_DEFINITELY_FAILED, MSG_ERROR_NO_ACTIVE_CLIENT, \
    DEBUG_COLOUR, INFO_COLOUR, WARNING_COLOUR, ERROR_COLOUR, CRITICAL_COLOUR, RESET_COLOUR


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
        self.output_mode: OutputMode = OutputMode.RAW
        self.disp.update_disp_debug(self.debug)
        self.message_handler: Optional[MessageHandler] = message_handler
        self.discord_intents: Optional[discord.Intents] = None
        self.discord_client: Optional[discord.Client] = None
        self._update_loop: Optional[tasks.Loop] = None
        self._discord_default_message_content_enabled: bool = DISCORD_DEFAULT_MESSAGE_CONTENT

    def __del__(self) -> None:
        """Ensure the bot is shut down during object destruction."""
        self.shutdown()

    def initialise(self) -> None:
        """Function in charge of setting up the connection for the interraction with the discord api.
        """
        self.discord_intents = discord.Intents.default()
        self.discord_intents.messages = True
        self.discord_intents.guilds = True
        self.discord_intents.message_content = bool(
            self._discord_default_message_content_enabled
        )
        if self.discord_intents is not None:
            self.discord_client = discord.Client(
                intents=self.discord_intents
            )
            self.discord_client.event(self._on_ready_wrapper)
            self.disp.log_debug(
                "Discord client initialised and event registered."
            )
            return
        self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_INITIALISATION_FAILED)

    def on_ready(self) -> None:
        """Called when the bot is connected and ready."""
        if self.discord_client:
            self.disp.log_info(f"Connected as {self.discord_client.user}")
        else:
            self.disp.log_error(MSG_ERROR_NO_ACTIVE_CLIENT)

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

    def _log_missing_message_content_intent(self, recalled: bool = False) -> None:
        if not recalled:
            self.disp.log_warning(
                WARNING_COLOUR+"MESSAGE_CONTENT privileged intent has been disabled for this runtime!"+RESET_COLOUR
            )
            self.disp.log_warning(
                WARNING_COLOUR+"The bot will continue running, but it cannot read or process message content."+RESET_COLOUR
            )
            self.disp.log_warning(
                WARNING_COLOUR+"If you need message content access, enable 'MESSAGE CONTENT INTENT' in your bot settings on the Discord Developer Portal."+RESET_COLOUR
            )
        else:
            self.disp.log_debug(
                DEBUG_COLOUR +
                "Skipping repeated MESSAGE_CONTENT intent warning (already disabled this session)." +
                RESET_COLOUR
            )

    def _log_retrying_message(self) -> None:
        self.disp.log_warning("Attempt failed, retrying once...")

    def _log_retrying_bot_initialisation(self) -> None:
        self.disp.log_warning("Bot initialisation failed, retrying once...")

    def _log_abandoning_message(self, err: Optional[str] = None) -> None:
        self.disp.log_error(MSG_ERROR_SOMETHING_DEFINITELY_FAILED)
        if err:
            self.disp.log_debug(f"[error: '{type(err).__name__}':'{err}']")
            self.disp.log_error(f"Second attempt error: {str(err)}")
        self._log_permissions_message()

    def _log_permissions_message(self) -> None:
        self.disp.log_error(
            "Have you checked that your agent (the sender: bot/user/etc) has the following permissions:"
        )
        for i in DISCORD_PERMISSIONS_EXPLANATION:
            self.disp.log_error(f"{i}")

    def _log_discord_message_intent_error(self, pre_message: Optional[str] = None, error: Optional[Any] = None) -> None:
        if pre_message:
            self.disp.log_critical(CRITICAL_COLOUR+pre_message+RESET_COLOUR)
        if error:
            self.disp.log_error(
                f"[error: '{type(error).__name__}':'{str(error)}']"
            )
        self.disp.log_error(DISCORD_MESSAGE_CONTENT_INTENT_ERROR)
        if pre_message:
            self.disp.log_critical(CRITICAL_COLOUR+pre_message+RESET_COLOUR)

    def _get_message_colour(self, message_status: Optional[WebsiteStatus]) -> Color:
        if message_status in EMBED_COLOUR:
            return EMBED_COLOUR[message_status]
        return Color.purple()

    def _restart_bot(self) -> int:
        try:
            self.disp.log_warning(
                WARNING_COLOUR+"Restarting client"+RESET_COLOUR)
            self.shutdown()
            self.initialise()
            self.disp.log_info(
                INFO_COLOUR+"Client restarted successfully"+RESET_COLOUR)
            return SUCCESS
        except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden, discord.PrivilegedIntentsRequired) as e:
            self.disp.log_error(
                ERROR_COLOUR +
                f"Restart error: [error: '{type(e).__name__}':'{str(e)}']" +
                RESET_COLOUR
            )
            self._log_permissions_message()
            return ERROR

    def _disable_discord_message_content_intent(self, reboot: bool = True) -> int:
        self._log_missing_message_content_intent()
        if not self.discord_intents:
            self.disp.log_error(MSG_ERROR_MESSAGE_INTENTS_STATUS_MISSING)
            return ERROR
        if hasattr(self.discord_intents, "message_content"):
            self.discord_intents.message_content = False
            self._discord_default_message_content_enabled = False
        self.disp.log_warning(
            f"Runtime change: DISCORD_DEFAULT_MESSAGE_CONTENT={DISCORD_DEFAULT_MESSAGE_CONTENT}, "
            f"discord_intents.message_content={self.discord_intents.message_content}"
        )
        if DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED and reboot:
            self.disp.log_warning(
                "Configuration has been changed and client reboot (DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED) has been set to true"
            )
            return self._restart_bot()
        return SUCCESS

    async def _get_channel_name(self, discord_message: DiscordMessage) -> str:
        """Return the name of the channel corresponding to the message's channel ID."""
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return "<unknown>"

        channel_id: Optional[int] = discord_message.message_channel
        if channel_id is None:
            self.disp.log_warning("No channel ID found in message object.")
            return "<no-channel>"

        _channel_error: str = f"<no-name:{channel_id}>"
        _channel_missing: str = f"<missing:{channel_id}>"
        self.disp.log_debug(f"_channel_error: {_channel_error}")
        self.disp.log_debug(f"_channel_missing: {_channel_missing}")
        channel = self.discord_client.get_channel(channel_id)
        if channel is None:
            channel: Union[None, Any] = await self._attempt_channel_fetch(channel_id)
            if not channel:
                self.disp.log_warning(
                    f"Could not fetch channel ({channel_id})"
                )
                return _channel_missing
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                self.disp.log_error(
                    MSG_ERROR_CHANNEL_NOT_A_TEXTCHANNEL_OR_THREAD
                )
                return _channel_error
        return getattr(channel, "name", _channel_error)

    def _get_website_title(self, message_data: DiscordMessage) -> str:
        final_message: str = ""
        status: str = WebsiteStatus.UNKNOWN_STATUS.value
        status_emoji: str = STATUS_EMOJI[WebsiteStatus.UNKNOWN_STATUS]
        if message_data.status:
            if message_data.status in WebsiteStatus:
                status = message_data.status.value
            if message_data.status in STATUS_EMOJI:
                status_emoji = STATUS_EMOJI[message_data.status]
        final_message += f"{status_emoji} {status}"
        return final_message

    def _get_website_description(self, message_data: DiscordMessage) -> str:
        final_message: str = ""
        url: str = "Website"
        status: str = WebsiteStatus.UNKNOWN_STATUS.value
        status_emoji: str = STATUS_EMOJI[WebsiteStatus.UNKNOWN_STATUS]
        if message_data.website_pretty_url:
            url = message_data.website_pretty_url
        if message_data.status:
            if message_data.status in WebsiteStatus:
                status = message_data.status.value
            if message_data.status in STATUS_EMOJI:
                status_emoji = STATUS_EMOJI[message_data.status]
        final_message += f"{url}: {status_emoji} {status}"
        return final_message

    def _get_embed_message(self, discord_message: DiscordMessage) -> Embed:
        self.disp.log_info("Generating imbedded message")
        colour: Color = self._get_message_colour(discord_message.status)
        website_title: str = self._get_website_title(discord_message)
        website_description: str = self._get_website_description(
            discord_message
        )
        self.disp.log_debug(f"colour: {colour}")
        self.disp.log_debug(f"website_title: '{website_title}'")
        self.disp.log_debug(f"website_description: {website_description}")
        embed: Embed = Embed(
            title=website_title,
            description=website_description,
            color=colour
        )
        empty_string: str = "<empty>"
        overflow: str = ""
        field_counter = 0
        if isinstance(discord_message.message_human, List):
            for item in discord_message.message_human:
                if isinstance(item, Tuple):
                    key: str = empty_string
                    value: str = empty_string
                    if len(item) == 1:
                        key = str(
                            item[0]
                        )[:MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS].strip()
                    if len(item) >= 2:
                        key = str(
                            item[0]
                        )[:MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS].strip()
                        value = str(
                            item[1]
                        )[:MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS].strip()
                    if not key.strip() and not value.strip():
                        self.disp.log_warning(
                            f"Key: '{key}', Value: '{value}' are empty, skipping"
                        )
                        continue
                    if key.strip() == "" or key.strip().isspace():
                        key = empty_string
                    if value.strip() == "" or value.strip().isspace():
                        value = empty_string
                    if field_counter < MAX_ALLOWED_EMBEDDED_FIELDS:
                        embed.add_field(
                            name=key,
                            value=value,
                            inline=INLINE_FIELDS
                        )
                        field_counter += 1
                    else:
                        self.disp.log_warning(
                            f"Maximum allowed fields exceeded, adding field to string buffer. MAX FIELDS: {MAX_ALLOWED_EMBEDDED_FIELDS}"
                        )
                        overflow += f"key: {key}, value: {value}"
                        overflow += DISCORD_MESSAGE_NEWLINE
                else:
                    self.disp.log_warning(
                        f"Unsupported type, adding it as is to the string buffer. Type: {type(item)}, content: '{item}'"
                    )
                    overflow += str(item) + DISCORD_MESSAGE_NEWLINE
        footer_message: str = "Bellow you will find the fields and data that could not fit in the main body of the message:"
        footer_message += DISCORD_MESSAGE_NEWLINE
        footer_message += DISCORD_MESSAGE_BEGIN_FOOTER
        footer_message += f"Updated at {datetime.now().isoformat(timespec='seconds')}"
        footer_message += DISCORD_MESSAGE_NEWLINE
        if len(overflow) > 0:
            footer_message += overflow
        footer_message += DISCORD_MESSAGE_END_FOOTER
        embed.set_footer(text=footer_message)

        self.disp.log_info("Embedded message generated")
        self.disp.log_debug(f"Generated embedding: {embed}")
        self.disp.log_debug(f"Embedding content: '{embed.to_dict()}'")
        return embed

    def _get_correct_prepended_embedding_message(self, discord_message: DiscordMessage) -> Union[str, None]:
        final_message: Union[str, None] = None
        if DISCORD_EMBEDING_MESSAGE == "":
            final_message = self._get_website_description(
                message_data=discord_message
            )
            self.disp.log_debug(f"Prepending message: {final_message}")
        elif DISCORD_EMBEDING_MESSAGE is not None and DISCORD_EMBEDING_MESSAGE != "":
            final_message = str(DISCORD_EMBEDING_MESSAGE)
            self.disp.log_debug(f"Prepending message: {final_message}")
        return final_message

    async def _attempt_channel_fetch(self, channel_id: int, recall: bool = True) -> Union[None, Any]:
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return None
        try:
            if self._discord_default_message_content_enabled != DISCORD_DEFAULT_MESSAGE_CONTENT:
                self._log_missing_message_content_intent(recalled=(not recall))
            channel = await self.discord_client.fetch_channel(channel_id)
            self.disp.log_debug(f"channel content: {channel}")
            return channel
        except (discord.InvalidData, discord.HTTPException, discord.NotFound, discord.Forbidden) as e:
            self.disp.log_error(
                f"Failed to fetch channel {channel_id}: {e} [error: '{type(e).__name__}':'{e}']"
            )
            if recall:
                self._log_retrying_message()
                return await self._get_channel_connection(channel_id, recall=False)
            self._log_abandoning_message(str(e))
            return None
        except discord.PrivilegedIntentsRequired as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_warning(
                f"Caught error: ({type(e).__name__}):{str(e)}"
            )
            status: int = self._disable_discord_message_content_intent()
            if status != SUCCESS:
                return None

            return await self._attempt_channel_fetch(channel_id, recall=True)

    async def _get_channel_connection(self, channel_id: int, recall: bool = True) -> Union[None, Any]:
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return None

        channel = self.discord_client.get_channel(channel_id)
        if channel is None:
            return await self._attempt_channel_fetch(channel_id, recall=recall)
        return channel

    async def _get_discord_message(self, channel_id: int, message_id: int, recall: bool = True) -> Union[None, discord.Message]:
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return None

        channel: Union[None, discord.Thread, discord.abc.PrivateChannel] = await self._get_channel_connection(channel_id)
        if not channel:
            self.disp.log_debug(f"channel: {channel}")
            self.disp.log_error(
                f"Failed to obtain an instance of channel: {channel_id}"
            )
            return None

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            self.disp.log_error(
                MSG_ERROR_CHANNEL_IS_NOT_A_TEXTCHANNEL_OR_THREAD
            )
            return None

        try:
            msg = await channel.fetch_message(message_id)
            self.disp.log_debug(f"Gathered message: {msg}")
            return msg
        except discord.NotFound as e:
            self.disp.log_warning(
                f"Message {message_id} not found in channel {channel_id}. It might have been deleted. [error: '{type(e).__name__}':'{e}']"
            )
            if recall:
                self._log_retrying_message()
                return await self._get_discord_message(channel_id, message_id, recall=False)
            self._log_abandoning_message(str(e))
            return None
        except discord.Forbidden as e:
            self.disp.log_error(
                f"Missing permissions to edit message {message_id} in channel {channel_id}. [error: '{type(e).__name__}':'{e}']"
            )
            self._log_permissions_message()
            return None
        except discord.HTTPException as e:
            self.disp.log_error(
                f"Failed to edit message {message_id}: {e} [error: '{type(e).__name__}':'{e}']"
            )
            if recall:
                self._log_retrying_message()
                return await self._get_discord_message(channel_id, message_id, recall=False)
            self._log_abandoning_message(str(e))
            return None

    async def _send_message(self, discord_message: DiscordMessage, recall: bool = True) -> int:
        """Send a message to a Discord channel and store its message ID."""
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return ERROR

        channel_id: Optional[int] = discord_message.message_channel
        if channel_id is None:
            self.disp.log_debug(f"Channel_id: {channel_id}")
            self.disp.log_error(MSG_ERROR_MESSAGE_MISSING_CHANNEL_ID)
            return ERROR

        channel: Union[discord.guild.GuildChannel, discord.Thread, discord.abc.PrivateChannel, None] = await self._get_channel_connection(channel_id)
        if channel is None:
            self.disp.log_debug(f"Channel: {channel}")
            self.disp.log_error(f"Failed to fetch channel {channel_id}")
            return ERROR

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            self.disp.log_debug(f"channel: {channel}")
            self.disp.log_error(MSG_ERROR_CHANNEL_NOT_A_TEXTCHANNEL_OR_THREAD)
            return ERROR

        try:
            # You can use embed, file, etc. here if desired.
            if self.output_mode == OutputMode.EMBED:
                embed: Embed = self._get_embed_message(discord_message)
                self.disp.log_debug(f"Embed message: {embed}")
                final_message: Union[str, None] = self._get_correct_prepended_embedding_message(
                    discord_message
                )
                sent_msg = await channel.send(content=final_message, embed=embed)
                self.disp.log_debug(
                    f"Updated message content: {sent_msg.content}"
                )
                self.disp.log_debug(f"Updated embeds: {sent_msg.embeds}")
            else:
                sent_msg = await channel.send(content=str(discord_message.message_human))
                self.disp.log_debug(
                    f"Updated message content: {sent_msg.content}"
                )
                self.disp.log_debug(f"Updated embeds: {sent_msg.embeds}")
            discord_message.message_id = sent_msg.id
            self.disp.log_debug(
                f"Sent message '{discord_message.message_human}' to channel '{channel_id}' (msg_id={sent_msg.id})."
            )
            return SUCCESS
        except discord.Forbidden as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_error(
                f"Missing permissions to send message in channel {channel_id}."
            )
            self._log_permissions_message()
        except discord.HTTPException as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_error(
                f"Failed to send message in channel {channel_id}: {e}"
            )
            if recall:
                self._log_retrying_message()
                return await self._send_message(
                    discord_message,
                    recall=False
                )
            self._log_abandoning_message(str(e))
        return ERROR

    async def _update_message(self, discord_message: DiscordMessage, recall: bool = True) -> int:
        """Edit an existing Discord message."""
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return ERROR

        channel_id: Optional[int] = discord_message.message_channel
        message_id: Optional[int] = discord_message.message_id

        if not channel_id or not message_id:
            self.disp.log_debug(
                f"channel_id={channel_id}, message_id={message_id}"
            )
            self.disp.log_error(MSG_ERROR_NO_CHANNEL_OR_MESSAGE_ID)
            return ERROR

        message: Union[discord.Message, None] = await self._get_discord_message(channel_id, message_id)
        if message is None:
            self.disp.log_debug(f"message: {message}")
            self.disp.log_error(f"Failed to fetch channel {channel_id}")
            return ERROR

        try:
            if self.output_mode == OutputMode.EMBED:
                embed: Embed = self._get_embed_message(discord_message)
                self.disp.log_debug(f"embed message: {embed}")
                final_message: Union[str, None] = self._get_correct_prepended_embedding_message(
                    discord_message
                )
                updated_msg = await message.edit(content=final_message, embed=embed)
                self.disp.log_debug(
                    f"Updated message content: {updated_msg.content}"
                )
                self.disp.log_debug(f"Updated embeds: {updated_msg.embeds}")
            else:
                updated_msg = await message.edit(content=str(discord_message.message_human), embed=None)
                self.disp.log_debug(
                    f"Updated message content: {updated_msg.content}"
                )
                self.disp.log_debug(f"Updated embeds: {updated_msg.embeds}")
            self.disp.log_debug(
                f"Updated message (id={message_id}) in channel '{channel_id}' with new content."
            )
            return SUCCESS
        except discord.NotFound as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_warning(
                f"Message {message_id} not found in channel {channel_id}. It might have been deleted."
            )
            if recall:
                self.disp.log_warning("Message not found, sending instead...")
                return await self._send_process(discord_message, recall=recall)
        except discord.Forbidden as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_error(
                f"Missing permissions to edit message {message_id} in channel {channel_id}."
            )
            self._log_permissions_message()
        except discord.HTTPException as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_error(f"Failed to edit message {message_id}: {e}")
            if recall:
                self._log_retrying_message()
                return await self._update_message(discord_message, recall=False)
            self._log_abandoning_message(str(e))
        except TypeError as e:
            self.disp.log_debug(f"[error: '{type(e).__name__}':'{e}']")
            self.disp.log_error(
                f"A type error occurred, message edit failed, {message_id}: {e}"
            )
            if recall:
                self._log_retrying_message()
                return await self._update_message(discord_message, recall=False)
            self._log_abandoning_message(str(e))
        return ERROR

    async def _check_message_presence(self, channel_id: Optional[int], message_id: Optional[int]) -> bool:
        """Edit an existing Discord message."""
        if not self.discord_client:
            self.disp.log_error(MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED)
            return False

        if not channel_id or not message_id:
            self.disp.log_debug(
                f"channel_id={channel_id}, message_id={message_id}"
            )
            self.disp.log_error(MSG_ERROR_NO_CHANNEL_OR_MESSAGE_ID)
            return False

        message: Union[discord.Message, None] = await self._get_discord_message(channel_id, message_id)
        self.disp.log_debug(
            f"[message: '{type(message).__name__}':'{message}']"
        )
        if not message:
            self.disp.log_error(MSG_ERROR_MESSAGE_RETRIEVAL_FAILED)
            return False
        self.disp.log_debug(f"Message exists: {message}")
        return True

    async def _send_process(self, message: DiscordMessage, recall: bool = True) -> int:
        if not self.message_handler:
            self.disp.warning_message(
                "No message handler instance found, skipping"
            )
            return ERROR
        # No message was ever sent, sending the first one
        status: int = await self._send_message(message, recall=recall)
        self.disp.log_debug(f"status={status}")
        if status != SUCCESS:
            self.disp.log_error(MSG_ERROR_MESSAGE_SEND_FAILED)
            return ERROR
        status: int = await self.message_handler.refresh_message_id(message)
        self.disp.log_debug(f"status={status}")
        if status != SUCCESS:
            self.disp.log_warning(
                f"Failed to update the website's '(id: {message.website_id})' message_id '({message.message_id})' in the database."
            )
            return ERROR
        channel_name: str = await self._get_channel_name(message)
        self.disp.log_debug(f"channel_name:{channel_name}")
        self.disp.log_info(
            f"Website status '({message.message_human})' sent to channel '{channel_name}'."
        )
        return SUCCESS

    async def _refresh_message_statuses(self) -> None:
        """
        Function in charge of refreshing or sending messages to the discord server.
        """
        if not self.message_handler:
            self.disp.log_error(MSG_ERROR_NO_MESSAGE_HANDLER_INSTANCE)
            return
        self.output_mode = self.message_handler.get_output_mode()
        message_update: Union[int, List[DiscordMessage]] = await self.message_handler.run()
        if not isinstance(message_update, List):
            self.disp.log_error(MSG_ERROR_WEBSITE_UPDATE_FAILED)
            return
        for message in message_update:
            if not message.message_id:
                status: int = await self._send_process(message)
                self.disp.log_debug(f"Message sending process: {status}")
                continue
            message_present: bool = await self._check_message_presence(message.message_channel, message.message_id)
            self.disp.log_debug(f"message_present: {message_present}")
            if not message_present:
                status: int = await self._send_message(message)
                self.disp.log_debug(f"Message sending process: {status}")
                continue
            # A message exists, updating it
            status: int = await self._update_message(message)
            if status != SUCCESS:
                self.disp.log_error(MSG_ERROR_UPDATE_ERROR)
                continue
            response = await self._get_channel_name(message)
            self.disp.log_info(
                f"Website status '({message.message_human})' updated message ('{message.message_id}') on channel '{response}'."
            )
            continue

    def _create_loop(self, interval_seconds: float):
        """Create a dynamic Discord task loop."""
        @tasks.loop(seconds=interval_seconds)
        async def loop():
            await self._refresh_message_statuses()
        return loop

    async def run(self, interval_seconds: float = 60) -> None:
        """Start the Discord bot and its update loop."""
        _error_no_client: str = f"{CRITICAL_COLOUR}{MSG_CRITICAL_NO_ACTIVE_CLIENT_INSTANCE}{RESET_COLOUR}"
        if not self.discord_client:
            self.initialise()

        if not isinstance(self.discord_client, discord.Client):
            self.disp.log_critical(_error_no_client)
            raise RuntimeError(_error_no_client)

        self._update_loop = self._create_loop(interval_seconds)
        self._update_loop.start()

        self.disp.log_info(
            INFO_COLOUR +
            f"Bot loop started with {interval_seconds}s interval."+RESET_COLOUR
        )
        try:
            await self.discord_client.start(self.token)
        except discord.PrivilegedIntentsRequired as e:
            self._log_retrying_bot_initialisation()
            status: int = self._disable_discord_message_content_intent(
                reboot=False
            )
            if status != SUCCESS:
                self.disp.log_error(
                    CRITICAL_COLOUR+MSG_CRITICAL_DISABLE_MESSAGE_CONTENT + RESET_COLOUR
                )
                raise RuntimeError(MSG_RUNTIME_CRITICAL_INIT_ERROR) from e
            try:
                await self.discord_client.start(self.token)
            except discord.PrivilegedIntentsRequired as err:
                self._log_discord_message_intent_error(
                    pre_message=str(
                        CRITICAL_COLOUR+MSG_RUNTIME_CRITICAL_INIT_ERROR+RESET_COLOUR
                    ),
                    error=e
                )
                raise RuntimeError(
                    CRITICAL_COLOUR+MSG_RUNTIME_CRITICAL_INIT_ERROR+RESET_COLOUR
                ) from err
