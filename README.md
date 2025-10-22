# Discord Website Uptime Bot

A Discord bot that monitors the status and operational state of a specified website and posts updates to a Discord channel. Supports both Docker and local Python environments.

---

## Project Structure

```text
Discord-Website-Uptime-Bot/
├── DiscordBot/
│   ├── __main__.py
│   ├── DiscordWebsiteMonitor.py
│   ├── requirements.txt
│   └── data/                       # Created at runtime if missing
│       └── status_message_id.json  # Created at runtime if missing
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── sample.env
├── LICENSE
├── .gitignore
├── README.md
└── COMMIT_CONVENTION.md
```

---

## Obtaining the Code

Clone the repository and enter the directory:

```bash
git clone https://github.com/HenraL/Discord-Website-Uptime-Bot.git Discord-Website-Uptime-Bot-HenraL
cd Discord-Website-Uptime-Bot-HenraL
```

---

## Environment Configuration

**You must create a `.env` file based on `sample.env` and place it at the root of the repository.**  
If the `.env` file is missing or incomplete, the bot/container will not start.

```env
# .env
TOKEN=your_discord_bot_token
WEBSITE_URL=https://example.com
CHANNEL_ID=123456789012345678
EXPECTED_CONTENT=Some keyword or phrase
```

- Do not remove `sample.env` (it is for reference and git history).
- Do not commit your `.env` file; it is excluded by `.gitignore`.

---

## Running with Docker

1. Ensure Docker is installed and running.
2. Place your `.env` file in the same directory as `docker-compose.yml`.
3. Build and run the bot:

   ```bash
   docker-compose up -d
   ```

   - If you see an error like `Got permission denied while trying to connect to the Docker daemon socket`, you may need to run with `sudo`:

     ```bash
     sudo docker-compose up -d
     ```

4. The bot will start automatically and post status updates to your specified Discord channel.

---

## Running Locally (Python/venv)

1. Create the virtual environment:

   ```bash
   python3 -m venv venv
   # On Windows:
   #   python -m venv venv
   #   or py -m venv venv
   ```

2. Activate the virtual environment:

   ```bash
   . venv/bin/activate
   # On Windows:
   #   venv\Scripts\activate
   ```

3. Upgrade pip (keep this step separate for clarity):

   ```bash
   python3 -m pip install -U pip
   # On Windows:
   #   python -m pip install -U pip
   #   or py -m pip install -U pip
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Place your `.env` file in the project root (same directory as [README.md](./README.md) and [docker-compose.yml](./docker-compose.yml))..
6. Run the bot (recommended way):

   ```bash
   python3 DiscordBot
   # On Windows:
   #   python DiscordBot
   #   or py DiscordBot
   ```

---

## How It Works

- The bot loads configuration from environment variables.
- Every minute, it checks the specified website for availability and the presence of the expected content.
- It posts or edits a single message in your Discord channel to reflect the current status.
- The message ID is stored in `DiscordBot/data/status_message_id.json` for persistence.

---

## Commit Message Convention

This repository uses a simple, descriptive commit message style. See the [COMMIT_CONVENTION](./COMMIT_CONVENTION.md) file for details and examples.

---

## Contributing

Feel free to fork the repository and submit pull requests!

---

## License

This project is licensed under a **Custom Open Source License** based on the MIT License. See the [LICENSE](./LICENSE) file for details.
