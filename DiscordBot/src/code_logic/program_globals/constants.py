"""Program-wide constants.

Contains fixed values (error codes, database table definitions, date
formats and JSON schema descriptors) used across the application.
"""
import os
import dataclasses
from typing import List, Tuple, Dict, Type, TypeAlias, Optional

from pathlib import Path

from enum import Enum

ERROR: int = 1
SUCCESS: int = 0
VERSION: str = "2.0.0"
AUTHOR: str = "(c) Henry Letellier"
CWD: str = os.path.abspath(str(Path(__file__).parent.parent.parent.parent))
# default value for the case sensitivity check option.
DEFAULT_CASE_SENSITIVITY: bool = False

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


class WebsiteStatus(Enum):
    """The enum containing the states that the websites can be in.

    Args:
        Enum (str): The enum item of the class.
    """
    UP = UP
    DOWN = DOWN
    PARTIALLY_UP = PARTIALLY_UP


WS: Type[WebsiteStatus] = WebsiteStatus

WEBSITE_STATUS: Dict[str, WebsiteStatus] = {
    "up": WebsiteStatus.UP,
    "partially up": WebsiteStatus.PARTIALLY_UP,
    "partially-up": WebsiteStatus.PARTIALLY_UP,
    "partially_up": WebsiteStatus.PARTIALLY_UP,
    "partiallyup": WebsiteStatus.PARTIALLY_UP,
    "down": WebsiteStatus.DOWN
}

# Table structure
SQLITE_TABLE_NAME_MESSAGES: str = "messages"
SQLITE_TABLE_COLUMNS_MESSAGES: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("name", "TEXT"),
    ("message_id", "INTEGER UNIQUE NULL"),
    ("url", "TEXT UNIQUE NOT NULL"),
    ("channel", "INTEGER NOT NULL"),
    ("expected_content", "TEXT NOT NULL"),
    ("expected_status", "INTEGER NOT NULL"),
    ("creation_date", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
    ("last_update", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
]
SQLITE_TABLE_NAME_DEAD_CHECKS: str = "dead_checks"
SQLITE_TABLE_COLUMNS_DEAD_CHECKS: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("website_id", "INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE"),
    ("keyword", "TEXT NOT NULL"),
    (
        "response",
        f"TEXT NOT NULL CHECK(response IN ('{DOWN}', '{PARTIALLY_UP}', '{UP}'))"
    )
]
SQLITE_TABLE_NAME_STATUS_HISTORY: str = "status_history"
SQLITE_TABLE_COLUMNS_STATUS_HISTORY: List[Tuple[str, str]] = [
    ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("website_id", "INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE"),
    (
        "status",
        f"TEXT NOT NULL CHECK(status IN ('{DOWN}', '{PARTIALLY_UP}', '{UP}'))"
    ),
    ("timestamp", "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP")
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
