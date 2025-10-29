"""Program-wide constants.

Contains fixed values (error codes, database table definitions, date
formats and JSON schema descriptors) used across the application.
"""
import dataclasses
from typing import List, Tuple, Dict, Type, TypeAlias, Optional, Union


from enum import Enum

from discord import Color

from .config import \
    DISCORD_EMBEDING_MESSAGE, DISCORD_DEFAULT_MESSAGE_CONTENT, DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED, \
    CWD, \
    DEFAULT_CASE_SENSITIVITY, \
    RESPONSE_LOG_SIZE, MIN_DELAY_BETWEEN_CHECKS, MAX_ALLOWED_EMBEDDED_FIELDS, MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS, MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS, INLINE_FIELDS, \
    HEADER_IMPERSONALISATION, QUERY_TIMEOUT, \
    DATABASE_PATH, DATABASE_NAME, \
    UP, DOWN, PARTIALLY_UP, UNKNOWN_STATUS, \
    UP_EMOJI, PARTIALLY_UP_EMOJI, DOWN_EMOJI, UNKNOWN_STATUS_EMOJI, \
    TIMEFRAME_EMOJI_DAY, TIMEFRAME_EMOJI_MONTH, TIMEFRAME_EMOJI_WEEK, TIMEFRAME_EMOJI_YEAR, \
    EMBED_COLOUR_UP, EMBED_COLOUR_DOWN, EMBED_COLOUR_PARTIALLY_UP, EMBED_COLOUR_UNKNOWN_STATUS

# Program status codes
ERROR: int = 1
SUCCESS: int = 0

# Program versions and author
VERSION: str = "2.0.0"
AUTHOR: str = "(c) Henry Letellier"

# This is a way to set an artificial lag between each website update in order to not risk getting rate limited in the message updates
DELAY_BETWEEN_MESSAGE_SENDS_SECONDS: float = 0

# Env searched keys
TOKEN_KEY: str = "TOKEN"
DEBUG_TOKEN: str = "DEBUG"
CONFIG_FILE_KEY: str = "CONFIG_FILE"
OUTPUT_MODE_KEY: str = "OUTPUT_MODE"
ARTIFICIAL_DELAY_KEY: str = "ARTIFICIAL_DELAY"

# message colour
BOLD_TEXT: str = "\033[1m"
RESET_COLOUR: str = "\033[0m"
BACKGROUND_COLOUR: str = "\033[48;5;232m"  # black
CRITICAL_COLOUR: str = BOLD_TEXT + BACKGROUND_COLOUR + "\033[38;5;9m"  # red
ERROR_COLOUR: str = BOLD_TEXT + BACKGROUND_COLOUR + \
    "\033[38;5;124m"  # darker shade of red
WARNING_COLOUR: str = BACKGROUND_COLOUR + "\033[38;5;11m"  # yellow
INFO_COLOUR: str = BACKGROUND_COLOUR + \
    "\033[38;5;10m"  # lime green (close enough)
DEBUG_COLOUR: str = BACKGROUND_COLOUR + "\033[38;5;14m"

# Discord message newline
DISCORD_MESSAGE_NEWLINE: str = "\n"
DISCORD_MESSAGE_BEGIN_FOOTER: str = "==== Begin Footer ====" + DISCORD_MESSAGE_NEWLINE
DISCORD_MESSAGE_END_FOOTER: str = "==== End Footer ====" + DISCORD_MESSAGE_NEWLINE

# Output mode

OUTPUT_RAW: str = "raw"
OUTPUT_MARKDOWN: str = "markdown"
OUTPUT_EMBED: str = "embed"


class OutputMode(Enum):
    """The enum containing resembling the format of the output message.

    Args:
        Enum (str): The enum item of the class.
    """
    RAW = OUTPUT_RAW
    MARKDOWN = OUTPUT_MARKDOWN
    EMBED = OUTPUT_EMBED


OM: Type[OutputMode] = OutputMode


# Tracked timeframes
TIMEFRAME_DAY: str = "day"
TIMEFRAME_WEEK: str = "week"
TIMEFRAME_MONTH: str = "month"
TIMEFRAME_YEAR: str = "year"
TIMEFRAME_EMOJIS: Dict[str, str] = {
    TIMEFRAME_DAY: TIMEFRAME_EMOJI_DAY,
    TIMEFRAME_WEEK: TIMEFRAME_EMOJI_WEEK,
    TIMEFRAME_MONTH: TIMEFRAME_EMOJI_MONTH,
    TIMEFRAME_YEAR: TIMEFRAME_EMOJI_YEAR
}

# Permissions message
DISCORD_MESSAGE_CONTENT_INTENT_ERROR: str = "For all modes, if in a bot, please make sure that the Message Content Intent is enabled."
DISCORD_PERMISSIONS_EXPLANATION: List[str] = [
    "",
    DISCORD_MESSAGE_CONTENT_INTENT_ERROR,
    "",
    # RAW text messages
    f"{OUTPUT_RAW} mode (plain text messages):",
    " • Send Messages – the bot must have permission to post in the channel.",
    " • Read Messages / View Channel – the bot must be able to see the channel to send messages.",
    "",
    # Markdown messages
    f"{OUTPUT_MARKDOWN} mode (formatted text using Discord markdown):",
    " • Send Messages – required to post the content.",
    " • Read Messages / View Channel – to access the channel.",
    " • Embed Links – not strictly required for markdown formatting, but some advanced markdown content may rely on links or mentions.",
    "",
    # EMBEDDED messages
    f"{OUTPUT_EMBED} mode (using Discord embeds):",
    " • Send Messages – needed to post the embed.",
    " • Read Messages / View Channel – needed to access the channel.",
    " • Embed Links – mandatory to send embed content.",
    " • Attach Files – if the embed includes images or thumbnails that are uploaded (might come in future updates)."
    "",
    "",
    "",
    ""
]

# website status


class WebsiteStatus(Enum):
    """The enum containing the states that the websites can be in.

    Args:
        Enum (str): The enum item of the class.
    """
    UP = UP
    DOWN = DOWN
    PARTIALLY_UP = PARTIALLY_UP
    UNKNOWN_STATUS = UNKNOWN_STATUS


WS: Type[WebsiteStatus] = WebsiteStatus

WEBSITE_STATUS: Dict[str, WebsiteStatus] = {
    "up": WebsiteStatus.UP,
    "partially up": WebsiteStatus.PARTIALLY_UP,
    "partially-up": WebsiteStatus.PARTIALLY_UP,
    "partially_up": WebsiteStatus.PARTIALLY_UP,
    "partiallyup": WebsiteStatus.PARTIALLY_UP,
    "down": WebsiteStatus.DOWN,
    "unknown status": WebsiteStatus.UNKNOWN_STATUS,
    "unknown-status": WebsiteStatus.UNKNOWN_STATUS,
    "unknown_status": WebsiteStatus.UNKNOWN_STATUS,
    "unknownstatus": WebsiteStatus.UNKNOWN_STATUS
}

STATUS_EMOJI: Dict[WebsiteStatus, str] = {
    WebsiteStatus.UP: UP_EMOJI,
    WebsiteStatus.PARTIALLY_UP: PARTIALLY_UP_EMOJI,
    WebsiteStatus.DOWN: DOWN_EMOJI,
    WebsiteStatus.UNKNOWN_STATUS: UNKNOWN_STATUS_EMOJI
}

# Embed colour
EMBED_COLOUR: Dict[WebsiteStatus, Color] = {
    WebsiteStatus.UP: EMBED_COLOUR_UP,
    WebsiteStatus.PARTIALLY_UP: EMBED_COLOUR_PARTIALLY_UP,
    WebsiteStatus.DOWN: EMBED_COLOUR_DOWN,
    WebsiteStatus.UNKNOWN_STATUS: EMBED_COLOUR_UNKNOWN_STATUS
}

# Table structure
SQLITE_URL_MESSAGE_ID_NAME: str = "url"
SQLITE_MESSAGES_MESSAGE_ID_NAME: str = "message_id"
SQLITE_DEAD_CHECKS_MESSAGE_ID_NAME: str = "website_id"
SQLITE_STATUS_MESSAGE_ID_NAME: str = "website_id"
SQLITE_STATUS_STATUS_NAME: str = "status"
SQLITE_STATUS_TIMESTAMP_NAME: str = "timestamp"

SQLITE_TABLE_NAME_MESSAGES: str = "messages"
SQLITE_TABLE_COLUMNS_MESSAGES: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("name", "TEXT"),
    (f"{SQLITE_MESSAGES_MESSAGE_ID_NAME}", "INTEGER UNIQUE NULL"),
    (f"{SQLITE_URL_MESSAGE_ID_NAME}", "TEXT UNIQUE NOT NULL"),
    ("channel", "INTEGER NOT NULL"),
    ("expected_content", "TEXT NOT NULL"),
    ("expected_status", "INTEGER NOT NULL"),
    ("creation_date", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("last_update", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
]
SQLITE_TABLE_NAME_DEAD_CHECKS: str = "dead_checks"
SQLITE_TABLE_COLUMNS_DEAD_CHECKS: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    (
        f"{SQLITE_DEAD_CHECKS_MESSAGE_ID_NAME}",
        "INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE"
    ),
    ("keyword", "TEXT NOT NULL"),
    (
        "response",
        f"TEXT NOT NULL CHECK(response IN ('{DOWN}', '{PARTIALLY_UP}', '{UP}'))"
    )
]
SQLITE_TABLE_NAME_STATUS_HISTORY: str = "status_history"
SQLITE_TABLE_COLUMNS_STATUS_HISTORY: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    (
        f"{SQLITE_STATUS_MESSAGE_ID_NAME}",
        "INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE"
    ),
    (
        f"{SQLITE_STATUS_STATUS_NAME}",
        f"TEXT NOT NULL CHECK(status IN ('{DOWN}', '{PARTIALLY_UP}', '{UP}'))"
    ),
    (
        f"{SQLITE_STATUS_TIMESTAMP_NAME}",
        "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
    )
]
SQLITE_MESSAGE_TRIGGER_NAME: str = "update_last_modified"
SQLITE_MESSAGE_TRIGGER: str = f"""
CREATE TRIGGER {SQLITE_MESSAGE_TRIGGER_NAME}
AFTER UPDATE ON {SQLITE_TABLE_NAME_MESSAGES}
FOR EACH ROW
BEGIN
    UPDATE {SQLITE_TABLE_NAME_MESSAGES}
    SET last_update = CURRENT_TIMESTAMP
    WHERE id = OLD.id;
END;
"""
SQLITE_MESSAGE_HANDLER_TABLES: Dict[str, List[Tuple[str, str]]] = {
    SQLITE_TABLE_NAME_MESSAGES: SQLITE_TABLE_COLUMNS_MESSAGES,
    SQLITE_TABLE_NAME_STATUS_HISTORY: SQLITE_TABLE_COLUMNS_STATUS_HISTORY,
    SQLITE_TABLE_NAME_DEAD_CHECKS: SQLITE_TABLE_COLUMNS_DEAD_CHECKS
}


# JSON structure nodes

JSON_KEY_TYPE: TypeAlias = Tuple[str, type]

JSON_NAME: JSON_KEY_TYPE = ("name", str)
JSON_URL: JSON_KEY_TYPE = ("url", str)
JSON_CHANNEL: JSON_KEY_TYPE = ("channel", int)
JSON_EXPECTED_CONTENT: JSON_KEY_TYPE = ("expected_content", str)
JSON_CASE_SENSITIVE: JSON_KEY_TYPE = ("case_sensitive", bool)
JSON_EXPECTED_STATUS: JSON_KEY_TYPE = ("expected_status", int)
JSON_DEADCHECKS: JSON_KEY_TYPE = ("dead_checks", List)
JSON_DEADCHECKS_KEYWORD: JSON_KEY_TYPE = ("keyword", str)
JSON_DEADCHECKS_RESPONSE: JSON_KEY_TYPE = ("response", str)
JSON_DEADCHECKS_CASE_SENSITIVE: JSON_KEY_TYPE = ("case_sensitive", bool)


class JSONDataNotFound(Exception):
    """Exception raised when a required JSON key is missing.

    Attributes:
        json_key (str): The missing key name.
    """

    def __init__(self, json_key: str = "", *args: object) -> None:
        """Initialize the JSONDataNotFound exception.

        Args:
            json_key (str): Name of the missing JSON key.
        """
        super().__init__(*args)
        self.json_key: str = json_key
        self.error: str = f"Json key '({json_key})' not present in json data."

    def __str__(self) -> str:
        """Return a human-readable error message.

        Returns:
            str: Formatted error message describing the missing key.
        """
        return f"{self.error}"

# Expected json structure


@dataclasses.dataclass
class QueryStatus:
    """Dataclass representing a single dead-check configuration.

    Fields:
        keyword (str): Keyword to search for.
        response (str): Expected response label for the keyword.
    """
    website_id: Optional[int] = None
    status: WebsiteStatus = WS.UP


@dataclasses.dataclass
class DeadCheck:
    """Dataclass representing a single dead-check configuration.

    Fields:
        keyword (str): Keyword to search for.
        response (str): Expected response label for the keyword.
    """
    keyword: str = ""
    response: WebsiteStatus = WS.UP
    case_sensitive: bool = DEFAULT_CASE_SENSITIVITY


@dataclasses.dataclass
class WebsiteNode:
    """Dataclass representing a configured website to monitor.

    Fields:
        name (str): Friendly name for the site.
        url (str): URL to monitor.
        channel (int): Discord channel id where status posts are sent.
        expected_content (str): Content substring expected to be present when the site is operational.
        expected_status (int): Expected status code value.
        dead_checks (List[DeadCheck]): List of dead-check rules associated with the site.
    """
    name: str = ""
    url: str = ""
    channel: int = 0
    expected_content: str = ""
    case_sensitive: bool = DEFAULT_CASE_SENSITIVITY
    expected_status: int = 0
    dead_checks: List[DeadCheck] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class DiscordMessage:
    website_id: Optional[int] = None
    status: Optional[WebsiteStatus] = None
    website_pretty_url: Optional[str] = None
    message_human: Union[str, List[Tuple[str, str]]] = ""
    message_channel: Optional[int] = None
    message_id: Optional[int] = None


# Important error messages set in a way that is eye catchy

# Runtime error
MSG_RUNTIME_CRITICAL_INIT_ERROR: str = "Bot initialisation error"
MSG_CRITICAL_DISABLE_MESSAGE_CONTENT: str = "Failed to disable message content intent, exiting."
MSG_CRITICAL_NO_ACTIVE_CLIENT_INSTANCE: str = "No active client instance."
MSG_CRITICAL_NO_SQL_HANDLER_INSTANCE: str = "No sql handler instances found"
MSG_CRITICAL_NO_CONFIG_CONTENT: str = "No Configuration content found"
MSG_CRITICAL_SQL_INITIALISATION_ERROR: str = "Failed to initialise the SQL class"
MSG_CRITICAL_MISSING_CONFIG_FILE: str = "Missing configuration file."
MSG_CRITICAL_CONFIG_FILE_NOT_FOUND: str = "Configuration file not found"
MSG_CRITICAL_CONFIG_FILE_LOAD_ERROR: str = "Configuration file load error"
MSG_CRITICAL_EMPTY_CONFIG_FILE: str = "Empty configuration file"
MSG_CRITICAL_BADLY_FORMATED_JSON: str = "The provided data is not in the json format or is badly formated."
# Message error
MSG_ERROR_UPDATE_ERROR: str = ERROR_COLOUR + \
    "Failed to update message, skipping update"+RESET_COLOUR
MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED: str = ERROR_COLOUR + \
    "Discord client not initialized."+RESET_COLOUR
MSG_ERROR_DISCORD_CLIENT_INITIALISATION_FAILED: str = ERROR_COLOUR + \
    "Discord client initialisation failed."+RESET_COLOUR
MSG_ERROR_WEBSITE_UPDATE_FAILED: str = ERROR_COLOUR + \
    "Website update failed, see above for error details"+RESET_COLOUR
MSG_ERROR_NO_MESSAGE_HANDLER_INSTANCE: str = ERROR_COLOUR + \
    "There are not message handler instances present, skipping update"+RESET_COLOUR
MSG_ERROR_MESSAGE_SEND_FAILED: str = ERROR_COLOUR + \
    "Failed to send message, skipping update"+RESET_COLOUR
MSG_ERROR_MESSAGE_RETRIEVAL_FAILED: str = ERROR_COLOUR + \
    "Attempting to retrieve the message failed, presuming that it does not exist."+RESET_COLOUR
MSG_ERROR_NO_CHANNEL_OR_MESSAGE_ID: str = ERROR_COLOUR + \
    "Discord message missing channel or message ID."+RESET_COLOUR
MSG_ERROR_CHANNEL_NOT_A_TEXTCHANNEL_OR_THREAD: str = ERROR_COLOUR + \
    "Channel is not a TextChannel or Thread. Cannot send messages."+RESET_COLOUR
MSG_ERROR_MESSAGE_MISSING_CHANNEL_ID: str = ERROR_COLOUR + \
    "Discord message missing channel ID."+RESET_COLOUR
MSG_ERROR_CHANNEL_IS_NOT_A_TEXTCHANNEL_OR_THREAD: str = ERROR_COLOUR + \
    "Channel is not a TextChannel or Thread. Cannot send messages."+RESET_COLOUR
MSG_ERROR_MESSAGE_INTENTS_STATUS_MISSING: str = ERROR_COLOUR + \
    "Could not find the discord intents status, abandoning"+RESET_COLOUR
MSG_ERROR_SOMETHING_DEFINITELY_FAILED: str = ERROR_COLOUR + \
    "Well, something is definitely wrong, because it failed on the second time to, abandoning."+RESET_COLOUR
MSG_ERROR_NO_ACTIVE_CLIENT: str = ERROR_COLOUR+"No active client"+RESET_COLOUR

__all__: List[str] = [
    "CWD",
    "DEFAULT_CASE_SENSITIVITY",
    "RESPONSE_LOG_SIZE",
    "MIN_DELAY_BETWEEN_CHECKS",
    "MAX_ALLOWED_EMBEDDED_FIELDS",
    "MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS",
    "MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS",
    "INLINE_FIELDS",
    "HEADER_IMPERSONALISATION",
    "QUERY_TIMEOUT",
    "DATABASE_PATH",
    "DATABASE_NAME",
    "VERSION",
    "AUTHOR",
    "DELAY_BETWEEN_MESSAGE_SENDS_SECONDS",
    "DISCORD_EMBEDING_MESSAGE",
    "DISCORD_DEFAULT_MESSAGE_CONTENT",
    "DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED",
    "TOKEN_KEY",
    "DEBUG_TOKEN",
    "CONFIG_FILE_KEY",
    "OUTPUT_MODE_KEY",
    "ARTIFICIAL_DELAY_KEY",
    # message colour,
    "BOLD_TEXT",
    "RESET_COLOUR",
    "BACKGROUND_COLOUR",
    "CRITICAL_COLOUR",
    "ERROR_COLOUR",
    "WARNING_COLOUR",
    "INFO_COLOUR",
    "DEBUG_COLOUR",
    # Discord message newline,
    "DISCORD_MESSAGE_NEWLINE",
    "DISCORD_MESSAGE_BEGIN_FOOTER",
    "DISCORD_MESSAGE_END_FOOTER",
    # Output mode,
    "OUTPUT_RAW",
    "OUTPUT_MARKDOWN",
    "OUTPUT_EMBED",
    "OutputMode",
    # Tracked timeframes,
    "TIMEFRAME_DAY",
    "TIMEFRAME_WEEK",
    "TIMEFRAME_MONTH",
    "TIMEFRAME_YEAR",
    "TIMEFRAME_EMOJIS",
    # Permissions message,
    "DISCORD_MESSAGE_CONTENT_INTENT_ERROR",
    "DISCORD_PERMISSIONS_EXPLANATION",
    # website status,
    "UP",
    "DOWN",
    "PARTIALLY_UP",
    "UNKNOWN_STATUS",
    "WebsiteStatus",
    "WS",
    "WEBSITE_STATUS",
    # Status emoji's,
    "UP_EMOJI",
    "PARTIALLY_UP_EMOJI",
    "DOWN_EMOJI",
    "UNKNOWN_STATUS_EMOJI",
    "STATUS_EMOJI",
    "EMBED_COLOUR",
    "EMBED_COLOUR_UP",
    "EMBED_COLOUR_DOWN",
    "EMBED_COLOUR_PARTIALLY_UP",
    "EMBED_COLOUR_UNKNOWN_STATUS",
    # Table structure,
    "SQLITE_MESSAGES_MESSAGE_ID_NAME",
    "SQLITE_DEAD_CHECKS_MESSAGE_ID_NAME",
    "SQLITE_STATUS_MESSAGE_ID_NAME",
    "SQLITE_STATUS_STATUS_NAME",
    "SQLITE_STATUS_TIMESTAMP_NAME",
    "SQLITE_TABLE_NAME_MESSAGES",
    "SQLITE_TABLE_COLUMNS_MESSAGES",
    "SQLITE_TABLE_NAME_DEAD_CHECKS",
    "SQLITE_TABLE_COLUMNS_DEAD_CHECKS",
    "SQLITE_TABLE_NAME_STATUS_HISTORY",
    "SQLITE_TABLE_COLUMNS_STATUS_HISTORY",
    "SQLITE_MESSAGE_TRIGGER_NAME",
    "SQLITE_MESSAGE_TRIGGER",
    "SQLITE_MESSAGE_HANDLER_TABLES",
    # JSON structure nodes,
    "JSON_KEY_TYPE",
    "JSON_NAME",
    "JSON_URL",
    "JSON_CHANNEL",
    "JSON_EXPECTED_CONTENT",
    "JSON_CASE_SENSITIVE",
    "JSON_EXPECTED_STATUS",
    "JSON_DEADCHECKS",
    "JSON_DEADCHECKS_KEYWORD",
    "JSON_DEADCHECKS_RESPONSE",
    "JSON_DEADCHECKS_CASE_SENSITIVE",
    "JSONDataNotFound",
    # Expected json structure,
    "QueryStatus",
    "DeadCheck",
    "WebsiteNode",
    "DiscordMessage",
    # Runtime error,
    "MSG_RUNTIME_CRITICAL_INIT_ERROR",
    "MSG_CRITICAL_DISABLE_MESSAGE_CONTENT",
    "MSG_CRITICAL_NO_ACTIVE_CLIENT_INSTANCE",
    "MSG_CRITICAL_NO_SQL_HANDLER_INSTANCE",
    "MSG_CRITICAL_NO_CONFIG_CONTENT",
    "MSG_CRITICAL_SQL_INITIALISATION_ERROR",
    "MSG_CRITICAL_MISSING_CONFIG_FILE",
    "MSG_CRITICAL_CONFIG_FILE_NOT_FOUND",
    "MSG_CRITICAL_CONFIG_FILE_LOAD_ERROR",
    "MSG_CRITICAL_EMPTY_CONFIG_FILE",
    "MSG_CRITICAL_BADLY_FORMATED_JSON",
    # Message error,
    "MSG_ERROR_UPDATE_ERROR",
    "MSG_ERROR_DISCORD_CLIENT_NOT_INITIALISED",
    "MSG_ERROR_DISCORD_CLIENT_INITIALISATION_FAILED",
    "MSG_ERROR_WEBSITE_UPDATE_FAILED",
    "MSG_ERROR_NO_MESSAGE_HANDLER_INSTANCE",
    "MSG_ERROR_MESSAGE_SEND_FAILED",
    "MSG_ERROR_MESSAGE_RETRIEVAL_FAILED",
    "MSG_ERROR_NO_CHANNEL_OR_MESSAGE_ID",
    "MSG_ERROR_CHANNEL_NOT_A_TEXTCHANNEL_OR_THREAD",
    "MSG_ERROR_MESSAGE_MISSING_CHANNEL_ID",
    "MSG_ERROR_CHANNEL_IS_NOT_A_TEXTCHANNEL_OR_THREAD",
    "MSG_ERROR_MESSAGE_INTENTS_STATUS_MISSING",
    "MSG_ERROR_SOMETHING_DEFINITELY_FAILED",
    "MSG_ERROR_NO_ACTIVE_CLIENT"
]
