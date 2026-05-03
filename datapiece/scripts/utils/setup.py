"""
This module provides utility functions for the setup of the application.
"""

from typing import Any, Dict

from datapiece.scripts.console import Console
from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.utils.config import get_key_dict


def create_handler(config: Dict[str, Any], debug: bool = False) -> DBQueryHandler:
    """
    Creates a DBQueryHandler instance.

    Args:
        config (Dict[str, Any]): The configuration dictionary.
        debug (bool): When True, use an in-memory database.

    Returns:
        DBQueryHandler: The created DBQueryHandler instance.
    """
    return DBQueryHandler(get_key_dict(config, "handler"), debug=debug)


def create_console(handler: DBQueryHandler, config: Dict[str, Any], debug: bool = False) -> Console:
    """
    Creates a Console instance.

    Args:
        handler (DBQueryHandler): The DBQueryHandler instance.
        config (Dict[str, Any]): The configuration dictionary.
        debug (bool): When True, use an ephemeral session and show debug banner.

    Returns:
        Console: The created Console instance.
    """
    return Console(handler, get_key_dict(config, "console"), debug=debug)
