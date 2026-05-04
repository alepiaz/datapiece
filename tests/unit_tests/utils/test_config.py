"""
Unit tests for the config util.
"""

import unittest
from unittest.mock import mock_open, patch

from datapiece.scripts.utils.config import (get_key_dict, get_key_list,
                                            get_key_str, load_config)


class TestConfig(unittest.TestCase):
    """
    Test case for the config util.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.sample_dict = {
            "dict": {"key": "value1"},
            "str": "value2",
            "list": ["value3", "value4"],
        }

    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value"}')
    def test_load_config(self, mock_file):
        """
        Test the load_config method.
        """
        result = load_config("dummy_path")
        self.assertEqual(result, {"key": "value"})
        mock_file.assert_called_once_with("dummy_path", "r", encoding="utf-8")

    def test_get_key_dict(self):
        """
        Test the get_key_dict method.
        """
        result = get_key_dict(self.sample_dict, "dict")
        self.assertEqual(result, {"key": "value1"})

    def test_get_key_str(self):
        """
        Test the get_key_str method.
        """
        result = get_key_str(self.sample_dict, "str")
        self.assertEqual(result, "value2")

    def test_get_key_list(self):
        """
        Test the get_key_list method.
        """
        result = get_key_list(self.sample_dict, "list")
        self.assertEqual(result, ["value3", "value4"])

    def test_load_config_file_not_found_raises_system_exit(self):
        with patch("builtins.open", side_effect=FileNotFoundError), \
             patch("builtins.print"):
            with self.assertRaises(SystemExit):
                load_config("missing.json")

    def test_load_config_invalid_json_raises_system_exit(self):
        with patch("builtins.open", new_callable=mock_open, read_data="not valid json"), \
             patch("builtins.print"):
            with self.assertRaises(SystemExit):
                load_config("bad.json")


if __name__ == "__main__":
    unittest.main()
