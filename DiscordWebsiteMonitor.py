
---

### **Updated Code**

```python
import sys
import json  # Ensure this is included
import discord
import requests
from discord.ext import tasks

# Insert your bot token here (replace with your own token)
TOKEN = '<YOUR_BOT_TOKEN>'

# The URL of the webpage you want to monitor
website_url = '<YOUR_WEBSITE_URL>'

# Replace with your Discord channel ID (as an integer)
CHANNEL_ID = <YOUR_CHANNEL_ID>

# File to store the message ID persistently
MESSAGE_ID_FILE = "status_message_id.json"

# Keyword to verify website content (adjust as needed)
EXPECTED_CONTENT = "<EXPECTED_CONTENT_ON_PAGE>"

# Create an instance of a client
intents = discord.Intents.default()
intents.messages = True
client = discord.Client(intents=intents)

# Function to check the website status and content
def check_website_status_and_content(url, keyword):
    try:
        response = requests.get(url, timeout=5)  # Timeout after 5 seconds
        if response.status_code == 200:
            if keyword in response.text:
                return "up_and_operational"  # Website is up and contains the expected content
            else:
                return "up_but_not_operational"  # Website is up but missing expected content
        else:
            return "down"  # Website is not reachable
    except requests.exceptions.RequestException:
        return "down"  # Website is not reachable

# Function to load the message ID from a file
def load_message_id():
    try:
        with open(MESSAGE_ID_FILE, "r") as f:
            data = json.load(f)
            return data.get("message_id")
    except (FileNotFoundError, json.JSONDecodeError):
        return None

# Function to save the message ID to a file
def save_message_id(message_id):
    with open(MESSAGE_ID_FILE, "w") as f:
        json.dump({"message_id": message_id}, f)

# Task that runs every 1 minute (60 seconds) to check website status
@tasks.loop(seconds=60)
async def monitor_website():
    status_message_id = load_message_id()
    channel = client.get_channel(CHANNEL_ID)

    if not channel:
        print("Channel not found")
        return

    # Check the website status and content
    status = check_website_status_and_content(website_url, EXPECTED_CONTENT)

    # Determine the appropriate message content
    if status == "up_and_operational":
        message_content = ":green_circle: Website is UP and Operational"
    elif status == "up_but_not_operational":
        message_content = ":yellow_circle: Website is UP but NOT Operational"
    else:
        message_content = ":red_circle: Website is DOWN"

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
    print(f'Logged in as {client.user}')
    monitor_website.start()

# Run the bot
client.run(TOKEN)
