"""
This module defines the Commands class which provides an interface for executing SQL commands.

TODO:
    * Add more command methods as needed.
    * Store temporary informations in a file
"""

from typing import Any, Callable

from datapiece.scripts.db_query_handler import DBQueryHandler


class Commands:
    """
    A class for executing database commands.

    Attributes:
        handler (DBQueryHandler): Executes the queries.
    """

    def __init__(self, handler: DBQueryHandler, config: dict[str, Any]) -> None:
        """
        Constructs all the necessary attributes for the Commands object.

        Args:
            handler (DBQueryHandler): An instance of DBQueryHandler to execute the queries.
            config (dict): A dictionary containing config information for commands.
        """
        self.handler = handler
        self.config = config
        self._registry: dict[str, Callable] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """
        Registers all available user-facing commands into the internal registry.
        """
        self._registry["start_volume"] = self.start_volume

    def get_command_names(self) -> list[str]:
        """
        Get a list of registered command names.

        Returns:
            list[str]: A list of commands.
        """
        return list(self._registry.keys())

    def _is_valid_command(self, func: str) -> bool:
        """
        Check if the given name corresponds to a registered command.
        """
        return func in self._registry

    def start_volume(self, volume_number: int) -> None:
        """
        Inserts a new volume with the given volume number into the 'Volumes' table.

        Args:
            volume_number (int): The number of the volume to be started.
        """
        query = "INSERT INTO `Volumes` (`VolumeNumber`) VALUES (?)"
        success = self.handler.execute_query(query, params=(volume_number,))
        if success:
            print(f"Volume {volume_number} added successfully.")
        else:
            print(f"Failed to add volume {volume_number}. It may already exist.")
