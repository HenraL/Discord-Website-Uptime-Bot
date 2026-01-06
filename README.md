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

## Environment configuration

This project supports two operational modes: the original single-site script (v1) and the newer, more flexible v2 program that can monitor multiple sites from a JSON configuration file. Documentation below is retro-compatible — v1 variables still work and are documented first, followed by v2 options.

Important: create a `.env` file based on `sample.env` and place it at the repository root. If the `.env` file is missing or incomplete, the bot/container will not start.

### v1 (single-site, simple) — legacy/compatible

The minimal env variables used by the v1 script are the same as before. If you only need to monitor one URL, keep using these:

```env
# .env (v1)
TOKEN=your_discord_bot_token
WEBSITE_URL=https://example.com
CHANNEL_ID=123456789012345678
EXPECTED_CONTENT=Some keyword or phrase
```

- Keep `sample.env` for reference in the repository.
- Do not commit your real `.env` file (it's in `.gitignore`).

### v2 (recommended for multiple sites / improved features)

The v2 program (default when running the package entrypoint under `DiscordBot/src` code path) reads a JSON configuration file that defines one or more websites to monitor and offers additional environment options.

Core environment variables for v2:

- `TOKEN` (string, required)
  - Your Discord bot token.
- `CONFIG_FILE` (string, required for v2)
  - Path to a JSON configuration file that describes the websites to monitor.
  - This path may be absolute or relative to the project `CWD`. Example: `DiscordBot/config/websites.json` or `websites.sample.json`.
- `OUTPUT_MODE` (string, optional)
  - One of: `raw`, `markdown`, `embed` (case-insensitive).
  - Controls how status messages are sent to Discord (plain text, formatted markdown, or rich embeds).
  - If omitted, the program will try to infer/default the output mode.
- `ARTIFICIAL_DELAY` (float, optional)
  - Introduce an extra delay (seconds) between sends to reduce rate of updates. Helpful in testing or when you need slower update cadence.

Example `.env` for v2 usage:

```env
# .env (v2)
TOKEN=your_discord_bot_token
CONFIG_FILE=DiscordBot/config/websites.json
OUTPUT_MODE=embed
ARTIFICIAL_DELAY=2.5
```

What the `CONFIG_FILE` should contain

- The configuration file is JSON and follows the structure used in `DiscordBot/config/websites.sample.json` (and `websites.jsonc`/`websites.json` if present). Each entry describes a website node and includes keys such as `name`, `url`, `channel`, `expected_content`, `case_sensitive` and `dead_checks` entries. The code validates the file and will refuse to run if it is missing or malformed.

Advanced runtime configuration (tweak in code)

- v2 also exposes many fine-grained program constants that can be edited in code (or overridden by editing the module values) located in `DiscordBot/src/code_logic/program_globals/config.py`. These are not environment variables but are documented here so advanced users know where to tune behaviour. Examples:
  - `DISCORD_EMBEDING_MESSAGE` — text sent alongside embeds (None / empty string / custom text).
  - `DISCORD_DEFAULT_MESSAGE_CONTENT` — toggle requesting the privileged MESSAGE_CONTENT intent.
  - `DISCORD_RESTART_CLIENT_WHEN_CONFIG_CHANGED` — whether to auto-restart the client when certain runtime configuration changes.
  - `HEADER_IMPERSONALISATION` — HTTP header preset used when fetching sites (several browser-like presets available: Firefox/Chrome/Curl/Postman variants).
  - `QUERY_TIMEOUT` — HTTP request timeout (seconds).
  - `DATABASE_PATH` / `DATABASE_NAME` — location and filename for the SQLite DB used by v2.
  - Logging, embed size and formatting constants such as `RESPONSE_LOG_SIZE`, `MIN_DELAY_BETWEEN_CHECKS`, `INLINE_FIELDS`, and embed colour/emoji constants.

If you want to change these advanced values without editing the source, you can also fork/extend the code to read them from environment variables or a separate runtime config file — but by default they are Python constants inside the project.

#### Detailed structure of a json website block

```jsonc
[                                          // This is your opening bracket that will welcome the list of websites to monitor
    {                                      // This is the opening curly bracket that will welcome the details for a website to be monitored
        "name": "Google",                  // This is the name/description that will be displayed on the status response
        "url": "https://google.com",       // This is the actual target of the website to monitor
        "channel": 1234567891234567891     // This is the discorc channel on which to post the message
        "expected_content": "<head>",      // This is the raw content to check for (it checks your string against the raw gathered response from the website.)
        "expected_status": 200,            // This is the expected status code for success, 200 success, 404 not found, 500 internal server error, etc
        "case_sensitive": false,           // This is wether to consider if the string must be compared in a case sensitive way or not (if false, both strings (expected content and the website response) are converted to lowercase before comparison)
        "dead_checks": [                   // This is a section where you can specify the status to be displayed if a specific string is encountered in the response, the available statuses are: Up, Down, Partially Up, Unknown Status
            {                              // This is the opening curly bracket for the first 'dead_check'
                "keyword": "Server error", // This is the keyword to look for
                "response": "PartiallyUp", // This is the response to override the default one with (if found)
                "case_sensitive": true     // This is how you specify wether to convert everythin to lowercase beforehand or not
            },                             // This is the closing curly bracket of the first 'dead_check', it is followed by a comma if you wish to add a nother one.
            {                              // This is the opening curly bracket of the second 'dead_check'
                "keyword": "maintenance",  // This is the keyword to look for
                "response": "Down"         // This is the response override the default one with (if found)
            }                              // This is the closing curly bracket of the second block, it is this time not followed by a comma because there are no other checks to perform
        ]                                  // This is the closing bracket of the 'dead_check' list
    }                                      // THis is the closing bracket of the first website node, if there were a website following it, it would have a comma
]                                          // This is the closing bracket of the json file, it will never be followed by a comma.

```

### For advanced users / developers

If you're comfortable editing Python and want to modify deeper design choices or tune runtime behaviour beyond environment variables, take a look at the fully documented `config.py` module:

- `DiscordBot/src/code_logic/program_globals/config.py`

This file contains extensive inline documentation for each constant (defaults, types and purpose) and includes presets (for example HTTP header impersonation profiles) you can swap in. Editing these constants lets you change embed behaviour, timeouts, header impersonation, database paths and other core behaviour. Be careful: changes here affect runtime behaviour globally and may require restarting the bot.

Compatibility notes

- v2 is designed to be retro-compatible but more strict about which variables it uses at runtime:
  - `TOKEN` is required and used by both v1 and v2.
  - v1-style single-site variables (`WEBSITE_URL`, `CHANNEL_ID`, `EXPECTED_CONTENT`) are tolerated — they may be present in your `.env` file without causing errors — but v2 will ignore them when running in multi-site/config mode. They remain useful only if you run the legacy v1 script.
  - For multi-site or more advanced usage, use `CONFIG_FILE` with the v2 JSON schema.

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

## WSGI shim (Passenger / cPanel)

There is a small file, `wsgi_flucker.py`, included as a convenience for certain
shared hosting environments (Passenger / cPanel) that only start Python processes
via a WSGI entrypoint. That file is a very small WSGI "shim" which attempts to
launch the bot from the WSGI process.

Important: this is a brittle and hacky technique. WSGI servers and hosting
panels are not designed to host long-running background workers (like an
asyncio-based Discord bot). The shim may be killed or behave unpredictably
depending on the hosting provider's lifecycle management. Prefer running the
bot under Docker, a dedicated VM, `systemd`/supervisord, or another proper
process manager for production usage. Use the WSGI shim only as a last resort
and with the limitations in mind.

---

## Gotchas

Using the Embed mode (V2 version and above) but not seing your message, have you checked to make sure your agent has the following authorisations:

- message sending
- message editing
- link embedding

---

## Commit Message Convention

This repository uses a simple, descriptive commit message style. See the [COMMIT_CONVENTION](./COMMIT_CONVENTION.md) file for details and examples.

---

## Contributing

Feel free to fork the repository and submit pull requests!

---

## License

This project is licensed under a **Custom Open Source License** based on the MIT License. See the [LICENSE](./LICENSE) file for details.
