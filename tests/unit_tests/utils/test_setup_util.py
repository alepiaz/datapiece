"""
Unit tests for the setup util.
"""

import unittest
from unittest.mock import patch

from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.utils.setup import create_console, create_handler


class TestSetupUtil(unittest.TestCase):
    """
    Test case for the setup util.
    """

    def setUp(self) -> None:
        """
        Set up the test case.
        """
        self.config_handler = {"handler": "dummy_handler"}
        self.config_console = {"console": "dummy_console"}

    @patch("datapiece.scripts.utils.setup.get_key_dict")
    @patch("datapiece.scripts.utils.setup.DBQueryHandler")
    def test_create_handler(self, mock_db_query_handler, mock_get_key_dict) -> None:
        """
        Test the create_handler method.
        """
        mock_get_key_dict.return_value = self.config_handler
        config = self.config_handler
        create_handler(config)
        mock_db_query_handler.assert_called_once_with(mock_get_key_dict.return_value, debug=False)

    @patch("datapiece.scripts.utils.setup.get_key_dict")
    @patch("datapiece.scripts.utils.setup.Console")
    def test_create_console(self, mock_console, mock_get_key_dict) -> None:
        """
        Test the create_console method.
        """
        mock_get_key_dict.return_value = self.config_console
        console = create_console(
            DBQueryHandler(self.config_handler), self.config_console
        )
        self.assertEqual(console, mock_console.return_value)
        mock_get_key_dict.assert_called_once_with(self.config_console, "console")


if __name__ == "__main__":
    unittest.main()
