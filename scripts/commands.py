"""
This module defines the Commands class which provides an interface for executing SQL commands.

TODO:
    * Add more command methods as needed.
    * Store temporary informations in a file
"""

from scripts.db_query_handler import DBQueryHandler
from scripts.utils.json import get_key_list


class Commands:
    """
    A class for executing database commands.

    Attributes:
        handler (DBQueryHandler): Executes the queries.
    """

    def __init__(self, handler: DBQueryHandler, config: dict):
        """
        Constructs all the necessary attributes for the Commands object.

        Args:
            handler (DBQueryHandler): An instance of DBQueryHandler to execute the queries.
            config (dict): A dictionary containing config information for commands
        """
        self.handler = handler
        self.config = config
        self.exclude_list = get_key_list(config, "exclude_list")

    def get_command_names(self):
        return [
            func
            for func in dir(self)
            if callable(getattr(self, func)) and not func in self.exclude_list
        ]

    def start_volume(self, volume_number: int):
        query = f"INSERT INTO Volumes (VolumeNumber) VALUES ({volume_number})"
        self.handler.execute_query(query)
