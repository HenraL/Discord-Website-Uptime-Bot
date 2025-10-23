"""File in charge of containing the variables that will not change during the program execution.
"""

from pathlib import Path
import os

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
