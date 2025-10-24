"""Program-wide constants.

Contains fixed values (error codes, database table definitions, date
formats and JSON schema descriptors) used across the application.
"""
import os
import dataclasses
from typing import List, Tuple, Dict, TypeAlias

from pathlib import Path

ERROR: int = 1
SUCCESS: int = 0
VERSION: str = "2.0.0"
AUTHOR: str = "(c) Henry Letellier"
CWD: str = os.path.abspath(str(Path(__file__).parent.parent.parent.parent))

# Database info
DATABASE_PATH: str = os.path.abspath(str(Path(CWD) / "data"))
DATABASE_NAME: str = "database.sqlite3"

# Env searched keys
TOKEN_KEY: str = "TOKEN"
CONFIG_FILE_KEY: str = "CONFIG_FILE"

# website status

UP: str = "Up"
DOWN: str = "Down"
PARTIALLY_UP: str = "Partially Up"
WEBSITE_STATUS: Dict[str, str] = {
    "up": UP,
    "partially up": PARTIALLY_UP,
    "partiallyup": PARTIALLY_UP,
    "down": DOWN
}

# Table structure
SQLITE_TABLE_NAME_MESSAGES: str = "messages"
SQLITE_TABLE_COLUMNS_MESSAGES: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("name", "TEXT"),
    ("message_id", "INTEGER UNIQUE NOT NULL"),
    ("url", "TEXT UNIQUE NOT NULL"),
    ("channel", "INTEGER NOT NULL"),
    ("expected_content", "TEXT NOT NULL"),
    ("expected_status", "INTEGER NOT NULL")
]
SQLITE_TABLE_NAME_DEAD_CHECKS: str = "dead_checks"
SQLITE_TABLE_COLUMNS_DEAD_CHECKS: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("message_id", "INTEGER NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE"),
    ("keyword", "TEXT NOT NULL"),
    ("response", "TEXT NOT NULL")
]
SQLITE_TABLE_NAME_STATUS_HISTORY: str = "status_history"
SQLITE_TABLE_COLUMNS_STATUS_HISTORY: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("message_id", "INTEGER NOT NULL REFERENCES messages(message_id) ON DELETE CASCADE"),
    ("status", "TEXT NOT NULL CHECK(status IN ('Down', 'PartiallyUp', 'Up'))"),
    ("timestamp", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
]
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
JSON_EXPECTED_STATUS: JSON_KEY_TYPE = ("expected_status", int)
JSON_DEADCHECKS: JSON_KEY_TYPE = ("dead_checks", List)
JSON_DEADCHECKS_KEYWORD: JSON_KEY_TYPE = ("keyword", str)
JSON_DEADCHECKS_RESPONSE: JSON_KEY_TYPE = ("response", str)


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
class DeadCheck:
    """Dataclass representing a single dead-check configuration.

    Fields:
        keyword (str): Keyword to search for.
        response (str): Expected response label for the keyword.
    """
    keyword: str = ""
    response: str = ""


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
    expected_status: int = 0
    dead_checks: List[DeadCheck] = dataclasses.field(default_factory=list)
