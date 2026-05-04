"""
This module provides a console application that interacts with a database.

The application uses a configuration file to set up a console and a database query handler.
The console takes user input and uses the database query handler to interact with the database.
"""

import argparse
import logging
import sys

from datapiece.scripts.utils.config import load_config
from datapiece.scripts.utils.setup import create_console, create_handler


def main(
    config_path: str,
    debug: bool = False,
    tutorial: bool = False,
    log_level: str = "WARNING",
) -> None:
    """
    The main function of the application. It does the following:

    1. Loads the configuration file.
    2. Creates an instance of the DBQueryHandler class.
    3. Creates an instance of the Console class.
    4. Starts the console (or runs the tutorial).

    If a RuntimeError occurs while starting the console,
        it catches the exception and logs an error message.
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
    config = load_config(config_path)
    # tutorial always implies an isolated in-memory DB
    use_debug = debug or tutorial
    handler = create_handler(config, debug=use_debug)
    console = create_console(handler, config, debug=use_debug)

    try:
        if tutorial:
            console.run_tutorial()
        else:
            console.start()
    except RuntimeError as error:
        print(f"Error: {error}")
        logging.error("An error occurred while starting the console: %s", error)


if __name__ == "__main__":  # pragma: no cover

    parser = argparse.ArgumentParser(
        description="Start the console with a given config file."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.json",
        help="The path to the config file.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run with an in-memory database — no changes are saved to disk.",
    )
    parser.add_argument(
        "--tutorial",
        action="store_true",
        help="Run the interactive tutorial (always uses an in-memory database).",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging verbosity (default: WARNING). Output goes to stderr.",
    )
    args = parser.parse_args()

    main(args.config, debug=args.debug, tutorial=args.tutorial, log_level=args.log_level)
