"""Configuration constants for the Discord Website Uptime Bot.

This module exposes user-tweakable constants that change the behaviour of
the bot. Each entry below lists the variable name, its default value, the
expected type, and a short description including valid/optional values and
practical notes on when to change it.

Groups:
    - Discord behaviour: message/embed defaults and privileged intent toggles.
    - Logging and timing: sizes, delays and timeouts that affect requests/loops.
    - Header impersonation presets: several HTTP header dictionaries you can
        swap into `HEADER_IMPERSONALISATION` to make requests look like a
        specific browser/runtime (useful when sites block non-browser clients).
    - Database: path and filename for the SQLite DB.
    - Status/emoji/embed configuration: constants used for formatting outputs.

Key variables (summary):

    DISCORD_EMBEDING_MESSAGE (Optional[str])
        - Default: None
        - Type: Optional[str]
        - Purpose: Text to send before embeds when using EMBED output mode.
            - None => only send the embed (no extra content).
            - "" (empty string) => use the embed description as the message content.
            - any other string => that string will be sent as content before the embed.

    DISCORD_DEFAULT_MESSAGE_CONTENT (bool)
        - Default: False
        - Type: bool
        - Purpose: If True, request the privileged MESSAGE_CONTENT intent so the
            bot can read message content. Requires enabling the intent in the
            Discord Developer Portal for the bot. Toggle only if you need to read
            user messages for command parsing or similar features.

    DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED (bool)
        - Default: False
        - Type: bool
        - Purpose: If True the bot will automatically restart the Discord client
            when runtime configuration that affects the client's behaviour changes
            (for example toggling message content intent). Useful during testing.

    CWD (str)
        - Default: computed from this file's location
        - Type: str (absolute path)
        - Purpose: Base directory used to resolve relative paths (for example
            the `data` directory). You can change it, but only if you know the
            implications on where the DB and other runtime files will be created.

    DEFAULT_CASE_SENSITIVITY (bool)
        - Default: False
        - Type: bool
        - Purpose: Default behaviour when comparing/searching website names.

    RESPONSE_LOG_SIZE (int)
        - Default: 500
        - Type: int (or -1)
        - Purpose: Number of characters from an HTTP response to include in logs.
            Set to -1 to include the full response body (may be large; use with care).

    MIN_DELAY_BETWEEN_CHECKS (float)
        - Default: 10
        - Type: float (seconds)
        - Purpose: Minimum delay between each main loop iteration to avoid
            being rate-limited by Discord or the monitored websites. Do not set
            below 10 unless you understand rate limits for your use case.

    MAX_ALLOWED_EMBEDDED_FIELDS / MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS /
    MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS (ints)
        - Defaults: 25, 255, 1024
        - Type: int
        - Purpose: Mirror Discord's embed limits. Change only if Discord updates
            its API limits; these values protect against creating invalid embeds.

    INLINE_FIELDS (bool)
        - Default: True
        - Type: bool
        - Purpose: Whether fields in embeds should be inlined by default.

    HEADER_IMPERSONALISATION (Dict[str,str])
        - Default: _FIREFOX_HEADER_MIN
        - Type: Dict[str, str]
        - Purpose: HTTP headers used to impersonate a browser/runtime when
            fetching websites. Available presets:
                - _FIREFOX_HEADER_MIN, _FIREFOX_HEADER_FULL
                - _CHROME_HEADER_MIN, _CHROME_HEADER_FULL
                - _CURL_HEADER_FULL
                - _POSTMAN_HEADER_MIN, _POSTMAN_HEADER_FULL
        - Example: set to _CHROME_HEADER_FULL to make requests appear to come
            from Chrome; useful when sites block non-browser user agents.

    QUERY_TIMEOUT (int)
        - Default: 5
        - Type: int (seconds)
        - Purpose: Maximum wait time for an HTTP request to respond before
            considering the connection dead. Increase for slow sites, but keep
            mindful of overall loop timing and rate limits.

    DATABASE_PATH (str) / DATABASE_NAME (str)
        - Defaults: <CWD>/data, "database.sqlite3"
        - Type: str
        - Purpose: Filesystem location and name for the SQLite database file.
            Ensure the directory exists and is writable by the bot.

    UP / DOWN / PARTIALLY_UP / UNKNOWN_STATUS (str)
        - Defaults: "Up", "Down", "Partially Up", "Unknown Status"
        - Purpose: Canonical status strings used throughout the project.

    *_EMOJI (str)
        - Examples: UP_EMOJI = ":green_circle:"
        - Purpose: Emoji constants shown alongside statuses and timeframes.

    EMBED_COLOUR_* (discord.Color)
        - Defaults: green(), red(), yellow(), purple()
        - Type: discord.Color
        - Purpose: Colors used for embedding status messages in Discord.

Notes
    - Most of these settings are safe to tweak for local/test deployments.
    - Be cautious when lowering timing/delay values or enabling privileged
        Discord intents — both can affect API rate limits and permissions.
    - Header presets are convenience dictionaries; you can modify or add
        your own if you need a different impersonation profile.
"""

import os

from pathlib import Path

from platform import system as ps

import uuid

from typing import Dict, Optional

from discord import Color

# This is a function in charge of faking the postman token (this is not meant to be changed)


def _generate_random_postman_token() -> str:
    """Generate a random Postman-style token.

    Returns:
        A UUID4 string in the form "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", which matches the sample structure used elsewhere in the project.
    """
    token = str(uuid.uuid4())
    return token


# Prepend message shown before an embed's content. Controls what (if any)
# text is sent alongside an embed when output mode is EMBED:
#  - None => do not send any prepended text (only the embed will be sent)
#  - "" (empty string) => use the embed's description (e.g. website + status)
#  - any other string => that string will be sent as content before the embed
# DISCORD_EMBEDING_MESSAGE
# Default: None
# Type: Optional[str]
# Purpose: Controls whether and what text is sent alongside embed messages
# when using EMBED output mode. Use None to send only the embed, an empty
# string to forward the embed description as a message, or any other string
# to prepend that text before the embed.
DISCORD_EMBEDING_MESSAGE: Optional[str] = None  # ""

# Whether to request the privileged MESSAGE_CONTENT intent from Discord.
# When True the bot will ask for message content access (allows reading
# message content). Enabling this requires turning the intent on in the
# Discord Developer Portal for the bot and may require a client restart.
# DISCORD_DEFAULT_MESSAGE_CONTENT
# Default: False
# Type: bool
# Purpose: If True the bot will request the privileged MESSAGE_CONTENT
# intent from Discord so it can read message content. Enable only if your
# bot needs to inspect user messages; also toggle the intent in the
# Discord Developer Portal.
DISCORD_DEFAULT_MESSAGE_CONTENT: bool = False

# If True, automatically restart the Discord client when runtime configuration
# that affects the client's behaviour (for example toggling the
# MESSAGE_CONTENT intent) is changed. Restarting ensures the new settings
# are picked up without a full manual restart.
# DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED
# Default: False
# Type: bool
# Purpose: When enabled, the bot will attempt to restart the discord client
# automatically if critical configuration changes at runtime (e.g. intent
# toggles) so new settings are applied without a manual restart.
DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED: bool = False

# CWD
# Default: computed from this file location
# Type: str (absolute path)
# Purpose: Base directory used to resolve relative paths (for example the
# `data` directory). Change only if you want to relocate runtime files.
CWD: str = os.path.abspath(str(Path(__file__).parent.parent.parent.parent))

# DEFAULT_CASE_SENSITIVITY
# Default: False
# Type: bool
# Purpose: Default behaviour for case sensitivity when comparing or
# searching website names. Set to True to make comparisons case-sensitive.
DEFAULT_CASE_SENSITIVITY: bool = False

# RESPONSE_LOG_SIZE
# Default: 500
# Type: int (or -1)
# Purpose: Number of characters from an HTTP response to include in logs.
# Set to -1 to include the full response body (may be very large).
RESPONSE_LOG_SIZE: int = 500

# MIN_DELAY_BETWEEN_CHECKS
# Default: 10 (seconds)
# Type: float
# Purpose: Minimum delay between main loop iterations. Prevents API
# rate limiting; do not set below recommended platform limits.
MIN_DELAY_BETWEEN_CHECKS: float = 10

# MAX_ALLOWED_EMBEDDED_FIELDS
# Default: 25
# Type: int
# Purpose: Maximum number of embed fields (keeps embeds valid per Discord limits).
MAX_ALLOWED_EMBEDDED_FIELDS: int = 25

# MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS
# Default: 255
# Type: int
# Purpose: Maximum characters allowed in an embed field's name/key.
MAX_ALLOWED_KEY_CHARACTERS_IN_FIELDS: int = 255

# MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS
# Default: 1024
# Type: int
# Purpose: Maximum characters allowed in an embed field's value.
MAX_ALLOWED_VALUE_CHARACTERS_IN_FIELDS: int = 1024

# INLINE_FIELDS
# Default: True
# Type: bool
# Purpose: Whether embed fields are inline by default when creating embeds.
INLINE_FIELDS: bool = True

# Website querying
# This is the header that will be used if the request fails to try and impersonate a browser


# Bellow are header presets you can set in the HEADER_IMPERSONALISATION to see if this fixes the issue
_FIREFOX_HEADER_MIN: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

_FIREFOX_HEADER_FULL: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:144.0) Gecko/20100101 Firefox/144.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en,en-GB;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Connection": "keep-alive",
    "Cookie": "doxygen_width=256; _ga=GA1.4.821560d8-97fc-e072-bcca-fb64489a8995; js=y",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Priority": "u=0, i"
}

_CHROME_HEADER_MIN: Dict[str, str] = {
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
}

_CHROME_HEADER_FULL: Dict[str, str] = {
    "Connection": "keep-alive",
    "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": ps(),
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-GB,en;q=0.9,fr-FR;q=0.8,fr;q=0.7,de-AT;q=0.6,de;q=0.5,en-US;q=0.4"
}

_CURL_HEADER_FULL: Dict[str, str] = {
    "User-Agent": "curl/8.5.0",
    "Accept": "*/*"
}


_POSTMAN_HEADER_MIN: Dict[str, str] = {
    "User-Agent": "PostmanRuntime/7.49.0",
    "Accept": "*/*"
}


_POSTMAN_HEADER_FULL: Dict[str, str] = {
    "User-Agent": "PostmanRuntime/7.49.0",
    "Accept": "*/*",
    "Cache-Control": "no-cache",
    "Postman-Token": _generate_random_postman_token(),
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

# HEADER_IMPERSONALISATION
# Default: _FIREFOX_HEADER_MIN
# Type: Dict[str, str]
# Purpose: HTTP headers used to impersonate a browser/runtime when
# fetching websites. Swap with any of the `_*_HEADER_*` presets above or
# provide a custom dict to work around UA-based blocking or content variations.
HEADER_IMPERSONALISATION: Dict[str, str] = _FIREFOX_HEADER_MIN

# QUERY_TIMEOUT
# Default: 5 (seconds)
# Type: int
# Purpose: Maximum amount of time to wait for an HTTP response before
# treating the connection as failed. Increase for slow endpoints.
QUERY_TIMEOUT: int = 5

# DATABASE_PATH
# Default: <CWD>/data
# Type: str (absolute path)
# Purpose: Directory where the SQLite database file is stored. Ensure
# the directory exists and is writable by the bot process.
DATABASE_PATH: str = os.path.abspath(str(Path(CWD) / "data"))

# DATABASE_NAME
# Default: "database.sqlite3"
# Type: str
# Purpose: Filename for the SQLite database used by the bot.
DATABASE_NAME: str = "database.sqlite3"

# Website status strings
# These are canonical status labels used across the codebase. Change
# only if you want different displayed wording in messages/logs.
UP: str = "Up"
DOWN: str = "Down"
PARTIALLY_UP: str = "Partially Up"
UNKNOWN_STATUS: str = "Unknown Status"

# Status emoji constants
# Purpose: Emoji shown alongside status messages. You can replace these
# with other emoji shortcodes or Unicode characters to change appearance.
UP_EMOJI: str = ":green_circle:"
PARTIALLY_UP_EMOJI: str = ":yellow_circle:"
DOWN_EMOJI: str = ":red_circle:"
UNKNOWN_STATUS_EMOJI: str = ":purple_circle:"

# Timeframe emoji constants
# Purpose: Emoji used to label timeframes in reports (day/week/month/year).
TIMEFRAME_EMOJI_DAY: str = ":clock1:"
TIMEFRAME_EMOJI_WEEK: str = ":calendar:"
TIMEFRAME_EMOJI_MONTH: str = ":crescent_moon:"
TIMEFRAME_EMOJI_YEAR: str = "🗃️"

# Embed colours for statuses
# Purpose: Discord embed colors for each site status. Replace with other
# `discord.Color` values to customize embed appearance.
EMBED_COLOUR_UP: Color = Color.green()
EMBED_COLOUR_DOWN: Color = Color.red()
EMBED_COLOUR_PARTIALLY_UP: Color = Color.yellow()
EMBED_COLOUR_UNKNOWN_STATUS: Color = Color.purple()
