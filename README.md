## License
This project is licensed under a **Custom Open Source License** based on the MIT License. See the [LICENSE](./LICENSE) file for details.

# Discord Website Status Monitor Bot

A Discord bot to monitor website status and operational state. It periodically checks a specified URL, verifies expected content, and updates a Discord channel with color-coded messages. Handles message persistence and gracefully manages connectivity issues. Easy to deploy with Docker or Python.

## Features
- Periodic website checks with configurable intervals.
- Color-coded status updates in a Discord channel.
- Handles persistent messages using JSON for message ID storage.
- Resilient to connectivity disruptions.

## Setup Instructions
1. Clone this repository.
2. Edit the `status_bot.py` script to add your:
   - Discord bot token.
   - Channel ID.
   - Website URL.
   - Expected content to verify website operation.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
