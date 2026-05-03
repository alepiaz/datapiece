"""
This module provides a console interface for interacting with a database.
"""

import logging
from typing import Optional

from pyreadline3 import Readline  # type: ignore

from datapiece.scripts.commands import Commands
from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.utils.config import get_key_dict


class Console:
    """
    A console interface for interacting with a database.

    Attributes:
        handler (DBQueryHandler): An instance of DBQueryHandler for handling database queries.
        config (dict): A configuration dictionary.
        commands_instance (Commands): An instance of Commands for handling commands.
        commands (list): A list of command names.
    """

    def __init__(self, handler: DBQueryHandler, config: dict) -> None:
        """
        The constructor for the Console class.

        Parameters:
            handler (DBQueryHandler): An instance of DBQueryHandler for handling database queries.
            config (dict): A configuration dictionary.
        """
        self.handler = handler
        self.config = config
        self.commands_instance = Commands(handler, get_key_dict(config, "commands"))
        self.commands = self.commands_instance.get_command_names()

    def start(self) -> None:
        """
        Starts the console interface.
        """
        readline = Readline()
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.completer)

        print('Welcome to the SQL Console. Type "exit" to quit.')

        while True:
            try:
                command = readline.readline(">>> ")
                if command.lower().strip() == "exit":
                    break
                command_parts = command.split()
                if not command_parts:
                    continue
                command_name = command_parts[0]
                if command_name in self.commands:
                    getattr(self.commands_instance, command_name)(*command_parts[1:])
                else:
                    print(f"Unknown command: {command_name}")
            except KeyboardInterrupt:
                # Handle Ctrl+C
                logging.info("Exit")
                continue
            except EOFError:
                logging.info("Exit")
                # Handle Ctrl+D / EOF
                break

        self.handler.close()

    def completer(self, text: str, state: int) -> Optional[str]:
        """
        Provides command completion options.

        Parameters:
            text (str): The current input text.
            state (int): The current completion state.

        Returns:
            str: A completion option that starts with the input text,
                or None if no more options are available.
        """
        options = [i for i in self.commands if i.startswith(text)]
        if state < len(options):
            return options[state]
        return None
