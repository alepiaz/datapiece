"""
Unit tests for the files util.
"""

import os
import unittest
from unittest.mock import patch

from datapiece.scripts.utils.files import (is_path_existent, is_path_readable,
                                           is_path_writeable,
                                           is_readable_existing_file,
                                           is_writeable_existing_file,
                                           is_existing_file_in_writeable_directory)


class TestFiles(unittest.TestCase):
    """
    Test case for the config util.
    """

    @patch("os.path.exists")
    def test_is_path_existent(self, mock_exists) -> None:
        """
        Test is_path_existent method.
        """
        mock_exists.return_value = True
        self.assertTrue(is_path_existent("dummy_path"))
        mock_exists.assert_called_once_with("dummy_path")

    @patch("os.access")
    def test_is_path_readable(self, mock_access) -> None:
        """
        Test is_path_readable method.
        """
        mock_access.return_value = True
        self.assertTrue(is_path_readable("dummy_path"))
        mock_access.assert_called_once_with("dummy_path", os.R_OK)

    @patch("os.access")
    def test_is_path_writeable(self, mock_access) -> None:
        """
        Test is_path_writeable method.
        """
        mock_access.return_value = True
        self.assertTrue(is_path_writeable("dummy_path"))
        mock_access.assert_called_once_with("dummy_path", os.W_OK)

    @patch("datapiece.scripts.utils.files.is_path_existent")
    @patch("datapiece.scripts.utils.files.is_path_readable")
    def test_is_readable_existing_file(self, mock_readable, mock_existent) -> None:
        """
        Test is_readable_existing_file method.
        """
        mock_existent.return_value = True
        mock_readable.return_value = True
        self.assertTrue(is_readable_existing_file("dummy_path"))

    @patch("datapiece.scripts.utils.files.is_path_existent")
    @patch("datapiece.scripts.utils.files.is_path_writeable")
    def test_is_writeable_existing_file(self, mock_writeable, mock_existent) -> None:
        """
        Test is_writeable_existing_file method.
        """
        mock_existent.return_value = True
        mock_writeable.return_value = True
        self.assertTrue(is_writeable_existing_file("dummy_path"))

    @patch("os.path.dirname")
    @patch("os.path.abspath")
    @patch("datapiece.scripts.utils.files.is_path_existent")
    @patch("datapiece.scripts.utils.files.is_path_writeable")
    def test_is_existing_file_in_writeable_directory(
        self, mock_writeable, mock_existent, mock_abspath, mock_dirname
    ) -> None:
        """
        Test is_existing_file_in_writeable_directory method.
        """
        mock_existent.return_value = True
        mock_writeable.return_value = True
        mock_abspath.return_value = "dummy_path"
        mock_dirname.return_value = "dummy_dir"
        self.assertTrue(is_existing_file_in_writeable_directory("dummy_path"))

    @patch("os.path.exists", side_effect=OSError("disk error"))
    def test_is_path_existent_oserror(self, _mock) -> None:
        self.assertFalse(is_path_existent("bad_path"))

    @patch("os.access", side_effect=OSError("disk error"))
    def test_is_path_readable_oserror(self, _mock) -> None:
        self.assertFalse(is_path_readable("bad_path"))

    @patch("os.access", side_effect=OSError("disk error"))
    def test_is_path_writeable_oserror(self, _mock) -> None:
        self.assertFalse(is_path_writeable("bad_path"))


if __name__ == "__main__":
    unittest.main()
