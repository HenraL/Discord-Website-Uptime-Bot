"""Minimal launcher for the DiscordWebsiteMonitor script.

This module provides an entrypoint so the package can be executed with
``python -m DiscordBot``. It delegates to the standalone
``DiscordWebsiteMonitor`` module.
"""

import DiscordWebsiteMonitor as DWM


if __name__ == "__main__":
    DWM.client.run(DWM.TOKEN)
