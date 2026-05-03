"""
Unit tests for the DBQueryHandler class.
"""

import unittest
from unittest.mock import MagicMock, patch

from datapiece.scripts.db_query_handler import DBQueryHandler


# pylint: disable=W0212
class TestDBQueryHandler(unittest.TestCase):
    """
    Test case for the DBQueryHandler class.
    """

    def setUp(self) -> None:
        """
        Set up the test case.
        """
        self.schema = """
        CREATE TABLE IF NOT EXISTS DummyTable (
            DummyField TEXT
        );
        """
        self.db_name = "dummy_db"
        self.mock_config = {"schema": self.schema, "db": self.db_name}

        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        with patch("sqlite3.connect", return_value=self.mock_conn):
            self.handler = DBQueryHandler(self.mock_config)

    def test_is_needed_to_delete(self) -> None:
        """
        Test the _is_needed_to_delete method.
        """
        test_cases = [
            (True, False, True),
            (False, True, True),
            (False, False, False),
        ]
        for delete_db, test_mode, expected in test_cases:
            with self.subTest():
                self.handler.delete_db = delete_db
                self.handler.test_mode = test_mode
                self.assertEqual(self.handler._is_needed_to_delete(), expected)

    @patch("os.remove")
    @patch("datapiece.scripts.db_query_handler.is_readable_existing_file")
    def test_handle_database_deletion(self, mock_exists, mock_remove) -> None:
        """
        Test the _handle_database_deletion method.
        """
        mock_exists.return_value = True
        self.handler.delete_db = True
        self.handler._handle_database_deletion()
        mock_remove.assert_called_once_with(self.db_name)

    @patch("datapiece.scripts.db_query_handler.is_existing_file_in_writeable_directory")
    def test_connect_to_database(self, mock_exists) -> None:
        """
        Test the _create_database method for failing and passing testcase.
        """
        for return_value in (True, False):
            with patch.object(
                DBQueryHandler, "_create_database"
            ) as mock_create_database:
                mock_exists.return_value = return_value
                self.handler._connect_to_database()
                if return_value:
                    mock_create_database.assert_called_once()
                else:
                    mock_create_database.assert_not_called()

    def _test_load_commands_from_schema(
        self, file_exists: bool, expected_commands: list[str]
    ) -> None:
        """
        Helper method to test the _load_commands_from_schema method.
        """
        if file_exists:
            with patch(
                "builtins.open",
                new_callable=unittest.mock.mock_open,
                read_data=";".join(expected_commands),
            ):
                commands = self.handler._load_commands_from_schema()
        else:
            with patch("builtins.open", side_effect=FileNotFoundError), patch(
                "logging.error"
            ):
                commands = self.handler._load_commands_from_schema()

        self.assertEqual(commands, expected_commands)

    def test_load_commands_from_schema_file_exists(self) -> None:
        """
        Test the _load_commands_from_schema method when the schema file exists.
        """
        self._test_load_commands_from_schema(True, ["command1", "command2"])

    def test_load_commands_from_schema_file_not_exists(self) -> None:
        """
        Test the _load_commands_from_schema method when the schema file does not exist.
        """
        self._test_load_commands_from_schema(False, [])

    @patch.object(DBQueryHandler, "execute_query")
    def test_execute_sql_commands_list(self, mock_execute_query) -> None:
        """
        Test the _execute_sql_commands_list method.
        """
        sql_commands = ["command1", "command2"]
        self.handler._execute_sql_commands_list(sql_commands)

        mock_execute_query.assert_any_call("command1", commit=False)
        mock_execute_query.assert_any_call("command2", commit=False)

        self.mock_conn.commit.assert_called_once()

    @patch.object(DBQueryHandler, "_load_commands_from_schema")
    @patch.object(DBQueryHandler, "_execute_sql_commands_list")
    def test_create_database(self, mock_execute, mock_load) -> None:
        """
        Test the _create_database method.
        """
        mock_load.return_value = ["command1", "command2"]
        self.handler._create_database()

        mock_load.assert_called_once()
        mock_execute.assert_called_once_with(["command1", "command2"])

    def test_execute_query(self) -> None:
        """
        Test the execute_query method.
        """
        query = "SELECT * FROM DummyTable"
        result = self.handler.execute_query(query)
        self.assertTrue(result)
        self.mock_cursor.execute.assert_called_once_with(query, ())
        self.mock_conn.commit.assert_called_once()

    def test_close(self) -> None:
        """
        Test the _close method.
        """
        self.handler.close()
        self.mock_conn.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
