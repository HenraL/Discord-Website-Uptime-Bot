"""Program entrypoint helpers.

Provides the :class:`Main` class which wires together configuration,
database and bot initialization. Use this module to start the
application from the command line or as a package entrypoint.
"""
import os
import sys
import json

from functools import partial

from pathlib import Path as pPath

from typing import Any, Optional, List

from .program_globals import constants as CONST
from .program_globals import helpers as HLP

from .sql import SQL
from .bot import DiscordBot, MessageHandler


class Main:
    """The main class of the program.

    Coordinates configuration, database and bot initialization for the
    application.
    """

    disp: HLP.Disp = HLP.initialise_logger(__qualname__, False)

    def __init__(self, delay: float = 60, output_mode: Optional[CONST.OutputMode] = None, debug: bool = False) -> None:
        """Create a Main controller instance.

        Args:
            debug (bool): Enable debug logging.
        """
        self.debug: bool = debug
        self.delay: float = delay  # seconds
        self.output_mode: Optional[CONST.OutputMode] = output_mode
        self.disp.update_disp_debug(self.debug)
        self.token: Optional[str] = None
        self.config_file: Optional[str] = None
        self.config_content: Optional[List[Any]] = None
        self.sqlite: Optional[SQL] = None
        self.bot: Optional[DiscordBot] = None
        self.msg_handler: Optional[MessageHandler] = None
        self._artificial_delay: Optional[float] = None

    def __del__(self) -> None:
        """Cleanly stop the program and release resources.

        This method attempts to free the sqlite and bot instances if they
        are present.
        """
        if self.sqlite:
            del self.sqlite
            self.sqlite = None
        if self.bot:
            self.bot.shutdown()
            del self.bot
            self.bot = None

    def __call__(self, *args: Any, **kwds: Any) -> int:
        """Function in charge of making the class callable as if it were a function.

        Returns:
            int: The execution status of the function.
        """
        return self.main(*args, **kwds)

    def _load_environement_if_present(self) -> int:
        """Load environment variables from configured locations.

        Returns:
            int: the load status.
        """
        self.token = HLP.get_environement_variable(CONST.TOKEN_KEY)
        self.config_file = HLP.get_environement_variable(CONST.CONFIG_FILE_KEY)
        if not self.output_mode:
            try:
                _output_mode: str = HLP.get_environement_variable(
                    CONST.OUTPUT_MODE_KEY
                ).lower()
                if _output_mode == CONST.OUTPUT_RAW.lower():
                    self.output_mode = CONST.OutputMode.RAW
                elif _output_mode == CONST.OUTPUT_MARKDOWN.lower():
                    self.output_mode = CONST.OutputMode.MARKDOWN
                elif _output_mode == CONST.OUTPUT_EMBED.lower():
                    self.output_mode = CONST.OutputMode.EMBED
                else:
                    raise ValueError(f"Unknown output mode: '{_output_mode}'")
            except ValueError as e:
                self.disp.log_debug(
                    f"No output mode provided in the environement file. Error: {e}. Current value: '{self.output_mode}'"
                )
            try:
                _artificial_delay_str: str = HLP.get_environement_variable(
                    CONST.ARTIFICIAL_DELAY_KEY
                ).lower()
                try:
                    self._artificial_delay = float(_artificial_delay_str)
                except ValueError as e:
                    self.disp.log_debug(
                        f"The provided delay is not a number, error: {type(e).__name__}: {str(e)}"
                    )
            except ValueError as e:
                self.disp.log_debug(
                    f"No artificial delay provided in the environement file. Error: {e}. Current value: '{self._artificial_delay}'"
                )

        return CONST.SUCCESS

    async def _initialise_sqlite(self) -> None:
        """Function in charge of initialising the SQL database

        Returns:
            SQL: An SQL instance
        """
        url: str = CONST.DATABASE_PATH
        port: int = 0
        username: str = ""
        password: str = ""
        db_name: str = CONST.DATABASE_NAME
        success: int = CONST.SUCCESS
        error: int = CONST.ERROR
        debug: bool = self.debug
        HLP.create_savefile_if_not_present(url)
        self.sqlite = SQL(
            url=url,
            port=port,
            username=username,
            password=password,
            db_name=db_name,
            success=success,
            error=error,
            debug=debug
        )
        tmp = await self.sqlite.create(
            url,
            port,
            username,
            password,
            db_name,
            success,
            error,
            debug
        )
        if isinstance(tmp, SQL):
            self.sqlite = tmp
            self.disp.log_info("Sqlite instance initialised")
        else:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_SQL_INITIALISATION_ERROR}{CONST.RESET_COLOUR}"
            )

    def _load_messages(self) -> None:
        """Load and parse the JSON configuration file referenced by ``self.config_file``.

        Raises:
            RuntimeError: If the configuration file is missing, empty or
                not valid JSON.
        """
        if not self.config_file:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_MISSING_CONFIG_FILE}{CONST.RESET_COLOUR}"
            )
        final_path: str = self.config_file
        if not os.path.isfile(final_path):
            self.disp.log_debug(
                "The provided file path does not exist or is incomplete. Attempting to fix."
            )
            final_paths: List[str] = [
                os.path.abspath(str(pPath(CONST.CWD) / final_path)),
                os.path.abspath(str(pPath(CONST.CWD) / ".." / final_path)),
                os.path.abspath(
                    str(pPath(CONST.CWD) / ".." / ".." / final_path)
                )
            ]
            self.disp.log_debug(
                f"Paths that are going to be checked: {final_paths}"
            )
            final_path = ""
            for path in final_paths:
                self.disp.log_debug(f"Checking path: {path}")
                if os.path.isfile(path):
                    self.disp.log_debug(
                        f"Path '({path})' exists, using that instead of the default"
                    )
                    final_path = path
                    break
            if final_path == "":
                raise RuntimeError(
                    f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_CONFIG_FILE_NOT_FOUND}{CONST.RESET_COLOUR}"
                )
        try:
            with open(final_path, "r", encoding="utf-8") as f:
                data = f.read()
        except (OSError) as e:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_CONFIG_FILE_LOAD_ERROR}{CONST.RESET_COLOUR}"
            ) from e
        if len(data) == 0:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_EMPTY_CONFIG_FILE}{CONST.RESET_COLOUR}"
            )
        try:
            json_data = json.loads(data)
        except (json.JSONDecodeError, TypeError) as e:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_BADLY_FORMATED_JSON}{CONST.RESET_COLOUR}"
            ) from e
        self.disp.log_debug("Configuration loaded")
        self.config_content = json_data

    async def async_main(self) -> int:
        """Function in charge initialising the asynchronous parts of the program.

        Returns:
            int: The execution status of the program.
        """
        self.disp.log_debug("Initialising sqlite")
        try:
            await self._initialise_sqlite()
            self.disp.log_debug("sqlite initialised")
        except (RuntimeError, AssertionError) as e:
            self.disp.log_error(f"sqlite error: {e}")
            return CONST.ERROR
        self.disp.log_debug("After the sqlite initialisation block")
        self.disp.log_debug("Initialising the bot")
        if not self.bot:
            self.disp.log_error(
                "There is no discord bot instance to be started."
            )
            return CONST.ERROR
        self.bot.initialise()
        self.disp.log_info("Bot Initialised")
        self.disp.log_info("Initialising the message handler")
        if not self.sqlite:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_NO_SQL_HANDLER_INSTANCE}{CONST.RESET_COLOUR}"
            )
        if not self.config_content:
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}{CONST.MSG_CRITICAL_NO_CONFIG_CONTENT}{CONST.RESET_COLOUR}"
            )
        self.msg_handler = MessageHandler(
            self.sqlite,
            self.config_content,
            self.output_mode,
            self.debug
        )
        self.disp.log_info("Message handler initialised")
        self.disp.log_info("Calling Message Handler's boot function")
        status = await self.msg_handler.boot_up()
        if status != CONST.SUCCESS:
            self.disp.log_error("Message handler boot sequence failed.")
            return CONST.ERROR
        self.disp.log_info("Message handler's boot function succeeded.")
        self.disp.log_info(
            "Assigning the Message Handler instance to the bot."
        )
        self.bot.update_message_handler_instance(self.msg_handler)
        self.disp.log_debug("Bot's Message handler updated")
        self.disp.log_info("Starting bot")
        await self.bot.run(interval_seconds=self.delay)
        self.disp.log_info("Bot run finished.")
        return CONST.SUCCESS

    def _main(self, *args: Any, **kwds: Any) -> int:
        """The main function of the class, the one called as an entrypoint.

        Returns:
            int: _description_
        """
        HLP.load_dotenv_if_present(CONST.CWD)
        HLP.DISP.update_disp_debug(self.debug)
        self.disp.log_debug(f"Passed args: {args}")
        self.disp.log_debug(f"Passed keywords: {kwds}")
        try:
            if self._load_environement_if_present() != CONST.SUCCESS:
                return CONST.ERROR
            self.disp.log_debug("Environement file loaded.")
        except ValueError as e:
            self.disp.log_error(f"Environement file error: {e}")
            return CONST.ERROR
        self.disp.log_debug("Loading the configuration file")
        try:
            self._load_messages()
        except RuntimeError as e:
            self.disp.log_error(f"Configuration loading error: {e}")
            return CONST.ERROR
        self.disp.log_debug("Configuration file loaded")
        self.disp.log_debug("Initialising bot")
        if not self.token or not self.config_content:
            self.disp.log_error(
                "The token or configuration content is missing, aborting program"
            )
            return CONST.ERROR
        self.bot = DiscordBot(
            None,
            self.token,
            self.debug
        )
        if self._artificial_delay:
            self.bot.update_delay_between_sends(self._artificial_delay)
        self.disp.log_debug("Bot initialised")
        return HLP.await_async_function_from_synchronous(partial(self.async_main))

    def _free_bot(self) -> None:
        """Function in charge of freeing any instance of the discord bot that may be present
        """
        try:
            self.disp.log_debug("Freeing bot if it has been initialised")
            if isinstance(self.bot, DiscordBot):
                self.disp.log_debug("Closing the bot connection if any")
                if self.bot.discord_client:
                    HLP.await_async_function_from_synchronous(
                        partial(self.bot.discord_client.close)
                    )
                    self.disp.log_debug("Connection closed")
                else:
                    self.disp.log_debug("No connection to close")
                self.bot.shutdown()
                self.disp.log_info("Bot shutdown")
                del self.bot
                self.bot = None
                self.disp.log_debug("Bot freed")
            else:
                self.disp.log_debug("Bot wasn't allocated")
        except Exception as e:
            self.disp.log_warning(
                f"During shutdown the following error occurred (bot): {e}"
            )

    def _free_sqlite(self) -> None:
        """Function in charge of freeing the sqlite connection if any were initialised
        """
        try:
            self.disp.log_debug(
                "Freeing any sqlite connections that might be present"
            )
            # Run async close in a new event loop just in case
            if isinstance(self.sqlite, SQL):
                HLP.await_async_function_from_synchronous(
                    partial(self.sqlite.close)
                )
                self.disp.log_debug("Sqlite connection freed")
                del self.sqlite
                self.sqlite = None
                self.disp.log_debug("sqlite freed")
            else:
                self.disp.log_debug("No sqlite instance to free")
        except Exception as e:
            self.disp.log_warning(
                f"During shutdown the following error occurred (sqlite): {e}"
            )

    def _free_ressources(self) -> None:
        """Function in charge of calling the child functions that will release allocated ressources if any.
        """
        self.disp.log_debug(
            f"{CONST.DEBUG_COLOUR}Freeing ressources{CONST.DEBUG_COLOUR}"
        )
        self._free_bot()
        self._free_sqlite()
        self.disp.log_debug(
            f"{CONST.DEBUG_COLOUR}Ressources freed{CONST.RESET_COLOUR}"
        )

    def main(self, *args: Any, **kwds: Any) -> int:
        """Function in charge of catching the keyboard interrupt, thus allowing the program to cleanly shutdown

        Returns:
            int: _description_
        """
        _freeing_ressources_info: str = CONST.INFO_COLOUR + \
            "Freeing ressources"+CONST.RESET_COLOUR
        try:
            status = self._main(*args, **kwds)
            self._free_ressources()
            return status
        except KeyboardInterrupt:
            self.disp.log_info(
                CONST.INFO_COLOUR+"CTRL+C caught, cleanly shutting down"+CONST.RESET_COLOUR
            )
            self._free_ressources()
            return CONST.SUCCESS
        except RuntimeError as e:
            self.disp.log_info(_freeing_ressources_info)
            self._free_ressources()
            self.disp.log_critical(
                f"{CONST.CRITICAL_COLOUR}An internal critical error has caused the program to stop prematurely, see above for error{CONST.RESET_COLOUR}"
            )
            self.disp.log_error(
                f"{CONST.CRITICAL_COLOUR}[error: '{type(e).__name__}{CONST.CRITICAL_COLOUR}':'{str(e)}{CONST.CRITICAL_COLOUR}']{CONST.RESET_COLOUR}"
            )
            return CONST.ERROR
        except Exception as e:
            self.disp.log_critical(
                f"{CONST.CRITICAL_COLOUR}An unhandled error has been caught.{CONST.RESET_COLOUR}"
            )
            self.disp.log_info(_freeing_ressources_info)
            self._free_ressources()
            self.disp.log_critical(
                f"{CONST.CRITICAL_COLOUR}Error name: {type(e).__name__}{CONST.RESET_COLOUR}"
            )
            self.disp.log_critical(
                f"{CONST.CRITICAL_COLOUR}Error content: {str(e)}{CONST.RESET_COLOUR}"
            )
            raise RuntimeError(
                f"{CONST.CRITICAL_COLOUR}Critical program error '{type(e).__name__}'{CONST.RESET_COLOUR}"
            ) from e


def start_wrapper() -> None:
    """Function in charge or providing an easy way of starting the program.
    """
    DATA = HLP.check_input_args()
    if isinstance(DATA, int):
        sys.exit(DATA)
    DEBUG = DATA[0]
    DELAY = DATA[1]
    OUTPUT_MODE = DATA[2]
    HLP.DISP.log_debug(
        f"DATA={DATA}, DEBUG={DEBUG}, DELAY={DELAY}, OUTPUT_MODE={OUTPUT_MODE}"
    )
    MI = Main(delay=DELAY, output_mode=OUTPUT_MODE, debug=DEBUG)
    sys.exit(MI.main())


if __name__ == "__main__":
    start_wrapper()
