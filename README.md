# Discord Website Monitor Bot

A Discord bot that monitors the status and operational state of specified websites and updates a Discord channel with color-coded messages.

## Features
- Monitors websites periodically.
- Updates Discord with status messages (up, down, or partially operational).
- Automatically handles reconnects and disruptions.
- Supports Docker deployment or local/virtual environment setups.

---

## Prerequisites

- Python 3.9+
- Docker (for containerized deployment)
- Access to a Discord bot token through the Discord Developer Portal (There's tutorials online)
- Channel ID where the bot will post updates

---

## Configuration
   - Discord Bot Token: Replace TOKEN in the DiscordWebsiteMonitor.py files.
   - Channel ID: Replace CHANNEL_ID with the ID of your Discord channel.
   - Website URL: Replace website_url with the URL to monitor.
   - Expected Content: Replace EXPECTED_CONTENT with a keyword to verify operational status.

## Running with Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/kioskun/Discord-Website-Uptime-Bot.git
   cd DiscordWebsiteMonitor
2. Build and run the containers:
   ```bash
   docker-compose up -d
4. Verify the containers are running:
   ```bash
   docker ps
   
## Running Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/kioskun/Discord-Website-Uptime-Bot.git
   cd DiscordWebsiteMonitor
   
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
  
3. Install dependencies:
   ```bash
   pip install -r requirements.txt

4.Navigate to the desired bot folder (e.g., DiscordBot1) and run the bot:
   ```bash
   cd DiscordBot1
   python3 DiscordWebsiteMonitor.py
   ```
## Instructions for Users
   - If using Docker, ensure docker-compose.yml is in the root.
   - If running locally, ensure Python and the required dependencies are installed.
   - Include clear instructions in README.md.
     
## Contributing
   Feel free to fork the repository and submit pull requests!

## License
This project is licensed under a **Custom Open Source License** based on the MIT License. See the [LICENSE](./LICENSE) file for details.
