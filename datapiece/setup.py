"""
This module provides a console application that interacts with a database.

The application uses a configuration file to set up a console and a database query handler.
The console takes user input and uses the database query handler to interact with the database.
"""

import argparse
import logging

from datapiece.scripts.utils.config import load_config
from datapiece.scripts.utils.setup import create_console, create_handler


def main(config_path: str) -> None:
    """
    The main function of the application. It does the following:

    1. Loads the configuration file.
    2. Creates an instance of the DBQueryHandler class.
    3. Creates an instance of the Console class.
    4. Starts the console.

    If a RuntimeError occurs while starting the console,
        it catches the exception and logs an error message.
    """
    logging.basicConfig(level=logging.INFO)
    config = load_config(config_path)
    handler = create_handler(config)
    console = create_console(handler, config)

    try:
        console.start()
    except RuntimeError as error:
        logging.error("An error occurred while starting the console: %s", error)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Start the console with a given config file."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.json",
        help="The path to the config file.",
    )
    args = parser.parse_args()

    main(args.config)
