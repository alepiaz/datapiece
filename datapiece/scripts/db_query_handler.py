"""
This module defines the DBQueryHandler class for handling database queries.
"""

import logging
import os
import sqlite3

from datapiece.scripts.utils.config import get_key_str
from datapiece.scripts.utils.files import (is_readable_existing_file,
                                           is_existing_file_in_writeable_directory)


class DBQueryHandler:
    """
    A handler for database queries.

    Attributes:
        schema_file (str): Path to the schema file.
        db_path (str): Path to the SQLite database file.
        delete_db (bool): Flag indicating whether to delete the existing database.
        conn (sqlite3.Connection): SQLite database connection.
        cursor (sqlite3.Cursor): SQLite database cursor.
    """

    def __init__(self, config: dict, delete_db: bool = False) -> None:
        """
        Initializes the DBQueryHandler with the given configuration and deletion flag.

        Parameters:
            config (dict): Configuration dictionary.
            delete_db (bool): Deletion flag.
        """

        self.schema_file = get_key_str(config, "schema")
        self.db_path = get_key_str(config, "db")
        self.test_mode = get_key_str(config, "mode") == "test"
        self.delete_db = delete_db
        self._handle_database_deletion()
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        os.makedirs(db_dir, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._connect_to_database()

    def _handle_database_deletion(self) -> None:
        """
        Deletes the existing database file if needed and if the file is readable.
        """
        if self._is_needed_to_delete() and is_readable_existing_file(self.db_path):
            os.remove(self.db_path)

    def _is_needed_to_delete(self) -> bool:
        """
        Checks if the database should be deleted due to delete_db or test_mode being True.

        Returns:
            bool: True if deletion is needed, False otherwise.
        """
        return self.delete_db or self.test_mode

    def _connect_to_database(self) -> None:
        """
        Connects to the SQLite database.
        """
        if is_existing_file_in_writeable_directory(self.db_path):
            self._create_database()

    def _create_database(self) -> None:
        """
        Creates the database schema if necessary.

        """
        sql_commands = self._load_commands_from_schema()
        self._execute_sql_commands_list(sql_commands)

    def _load_commands_from_schema(self) -> list[str]:
        """
        Loads the SQL commands from the schema file.

        Returns:
            list[str]: List of SQL commands.
        """
        try:
            with open(self.schema_file, "r", encoding="utf-8") as f:
                return [cmd.strip() for cmd in f.read().split(";") if cmd.strip()]
        except FileNotFoundError:
            logging.error("Schema file %s does not exist.", self.schema_file)
            return []

    def _execute_sql_commands_list(self, sql_commands: list[str]) -> None:
        """
        Executes the given list of SQL commands and commits the changes.

        Parameters:
            sql_commands (list): List of SQL commands.
        """
        for command in sql_commands:
            self.execute_query(command, commit=False)
        self.conn.commit()

    def execute_query(self, query: str, params: tuple = (), commit: bool = True) -> bool:
        """
        Executes the given SQL query and commits the changes.

        Parameters:
            query (str): SQL query.
            params (tuple): Query parameters for parameterized queries.
            commit (bool): Whether to commit after execution.

        Returns:
            bool: True if the query succeeded, False otherwise.
        """
        try:
            self.cursor.execute(query, params)
            if commit:
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            logging.error("Query failed: %s | Error: %s", query, e)
            return False

    def close(self) -> None:
        """
        Closes the database connection.
        """
        self.conn.close()
