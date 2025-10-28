"""Discord Website Uptime Bot.

This script implements a Discord bot that monitors the status of a specified
website and posts periodic updates to a designated Discord channel.

Configuration and usage notes are described in the module-level README
comments below and by the associated environment variables used by the
script.
"""

import os
import re
import sys
import pathlib
from urllib3 import util as uurlib3
from typing import Optional, Dict, Any, Union
import json  # Ensure this is included
import discord
import requests
from discord.ext import tasks

DEBUG: bool = False


def _print_debug(string: str) -> None:
    """Print a debug line when DEBUG is enabled.

    Args:
        string (str): Message to print when debugging is active.
    """
    if DEBUG:
        print(f"[DEBUG] {string}")


def _load_dotenv_if_present() -> None:
    """Check for a .env or ../.env file and inject variables into os.environ if present."""
    env_paths = [
        pathlib.Path(__file__).parent / ".env",
        pathlib.Path(__file__).parent.parent / ".env"
    ]
    for env_path in env_paths:
        if env_path.is_file():
            with env_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Match KEY=VALUE, allowing for spaces around =
                    match = re.match(
                        r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
                    if match:
                        key, value = match.groups()
                        # Remove optional surrounding quotes
                        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        os.environ.setdefault(key, value)
            print(f"environement file ({env_path}) loaded.")
            return  # Only load the first found .env file
    print("No environement files loaded")


def _get_environement_variable(var_name: str) -> str:
    """Get the environement variable from the system environement

    Args:
        var_name (str): The name to look for

    Raises:
        ValueError: The error raised when the variable is not present.

    Returns:
        str: The value of the variable.
    """
    if var_name not in os.environ:
        raise ValueError(
            f"The expected environement variable {var_name} is missing.")
    return os.environ[var_name]


def _create_savefile_if_not_present(save_file: str) -> None:
    """Ensure the parent folder and save file exist.

    Args:
        save_file (str): Path to the save file to create if absent.
    """
    folders: str = str(pathlib.Path(save_file).parent)
    if os.path.isdir(folders) is False:
        print(f"Creating savefile folders ({folders})")
        os.makedirs(folders, exist_ok=True)
    if os.path.isfile(save_file) is False:
        print(f"Creating an empty savefile ({save_file})")
        with open(save_file, "w", encoding="utf-8") as f:
            f.write("")


def _get_base_url(url: str) -> str:
    """Return the scheme+host[:port] base part of a URL.

    Args:
        url (str): Full URL string.

    Returns:
        str: Base URL (scheme://host[:port]).
    """
    decomposed_url_node: uurlib3.Url = uurlib3.parse_url(url)
    host: str = decomposed_url_node.host if decomposed_url_node.host else ""
    scheme: str = f"{decomposed_url_node.scheme}://" if decomposed_url_node.scheme else ""
    port: str = f":{decomposed_url_node.port}" if decomposed_url_node.port else ""
    return f"{scheme}{host}{port}"


_load_dotenv_if_present()

# Insert your bot token here (replace with your own token)
TOKEN: str = _get_environement_variable("TOKEN")

# The URL of the webpage you want to monitor
WEBSITE_URL: str = _get_environement_variable("WEBSITE_URL")
WEBSITE_DOMAIN_NAME: str = _get_base_url(WEBSITE_URL)

# Replace with your Discord channel ID (as an integer)
_env_key: str = "CHANNEL_ID"
node: str = _get_environement_variable(_env_key)
if not node.isnumeric():
    raise TypeError(
        f"Expected {_env_key} to by of type 'int' but got type '{type(node)}'"
    )
CHANNEL_ID: Optional[int] = int(node)

# File to store the message ID persistently
MESSAGE_ID_FILE: str = str(
    pathlib.Path(__file__).parent / "data" / "status_message_id.json"
)

_create_savefile_if_not_present(MESSAGE_ID_FILE)

# Keyword to verify website content (adjust as needed)
EXPECTED_CONTENT: str = _get_environement_variable("EXPECTED_CONTENT")

# Create an instance of a client
intents: discord.Intents = discord.Intents.default()
intents.messages = True
client: discord.Client = discord.Client(intents=intents)


def check_website_status_and_content(url: str, keyword: str) -> str:
    """Check website availability and whether expected content is present.

    The check is case-insensitive, ignores extra whitespace and allows for
    partial matches.

    Args:
        url (str): URL to query.
        keyword (str): Keyword to search for in the page.

    Returns:
        str: Status string describing the result ("up_and_operational", "up_but_not_operational", or "down").
    """
    try:
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        if response.status_code == 200:
            # Normalize whitespace and lowercase
            page_content = re.sub(r'\\s+', ' ', response.text).lower()
            keyword_norm = re.sub(r'\\s+', ' ', keyword).lower().strip(' "\'')
            _print_debug(f" Normalized keyword: '{keyword_norm}'")
            _print_debug(
                f"First 500 chars of normalized page text: '{page_content}'"
            )
            found = keyword_norm in page_content
            _print_debug(f"Keyword found: {found}")
            if found:
                return "up_and_operational"  # Website is up and contains the expected content
            return "up_but_not_operational"  # Website is up but missing expected content
        return "down"  # Website is not reachable
    except requests.exceptions.RequestException:
        return "down"  # Website is not reachable


def load_message_id() -> Optional[Any]:
    """Function to load the message ID from a file

    Returns:
        Optional[Any]: The value of 'message_id', None otherwise.
    """
    try:
        if MESSAGE_ID_FILE is None:
            return None
        with open(MESSAGE_ID_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("message_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_message_id(message_id: int) -> None:
    """Function to save the message ID to a file

    Args:
        message_id (int): The id of the message to control and update.

    Returns:
        None: This function returns None regardless of the internal process.
    """
    if MESSAGE_ID_FILE is None:
        return None
    with open(MESSAGE_ID_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f)
    return None

#


@tasks.loop(seconds=60)
async def monitor_website():
    """Task that runs every 1 minute (60 seconds) to check website status

    Returns:
        _type_: _description_
    """
    if CHANNEL_ID is None:
        return None
    status_message_id = load_message_id()
    channel = client.get_channel(CHANNEL_ID)

    if not channel:
        print("Channel not found")
        return
    print(f"Channel type: {type(channel)}")

    # Only proceed if channel is a TextChannel or Thread
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        print("Channel is not a TextChannel or Thread. Cannot send messages.")
        return

    # Check the website status and content
    status = check_website_status_and_content(WEBSITE_URL, EXPECTED_CONTENT)

    # Determine the appropriate message content
    if status == "up_and_operational":
        message_content = f":green_circle: Website '({WEBSITE_DOMAIN_NAME})' is UP and Operational"
    elif status == "up_but_not_operational":
        message_content = f":yellow_circle: Website '({WEBSITE_DOMAIN_NAME})' is UP but NOT Operational"
    else:
        message_content = f":red_circle: Website '({WEBSITE_DOMAIN_NAME})' is DOWN"

    try:
        # Try to fetch the existing message
        if status_message_id:
            try:
                status_message = await channel.fetch_message(status_message_id)
                # Edit the existing message
                await status_message.edit(content=message_content)
            except discord.NotFound:
                # If the message no longer exists, send a new one
                print("Message not found. Sending a new one.")
                status_message = await channel.send(message_content)
                save_message_id(status_message.id)
        else:
            # If there's no known message ID, send a new message
            status_message = await channel.send(message_content)
            save_message_id(status_message.id)
    except discord.HTTPException as e:
        print(f"Failed to send or edit message: {e}")


@client.event
async def on_ready():
    """Handle the Discord 'on_ready' event and start monitoring.

    Starts the periodic website monitoring task after login.
    """
    print(f'Logged in as {client.user}')
    monitor_website.start()


def _check_constants() -> None:
    """Function in charge of making sure that the required program constants are defined.

    Raises:
        ValueError: Raises a ValueError with the name of the variable that was not defined.
    """
    constants_to_check: Dict[str, Union[Optional[str], Optional[int]]] = {
        "TOKEN": TOKEN,
        "WEBSITE_URL": WEBSITE_URL,
        "CHANNEL_ID": CHANNEL_ID,
        "MESSAGE_ID_FILE": MESSAGE_ID_FILE,
        "EXPECTED_CONTENT": EXPECTED_CONTENT
    }
    for key, value in constants_to_check.items():
        if value is None:
            raise ValueError(f"{key} is not defined.")


if __name__ == "__main__":
    # Run the bot
    try:
        _check_constants()
    except ValueError as e:
        raise RuntimeError("Initialisation error") from e
    if TOKEN is not None:
        sys.exit(client.run(TOKEN))
