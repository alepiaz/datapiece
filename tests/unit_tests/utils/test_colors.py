"""
Unit tests for the colors utility.
"""

import unittest
from unittest.mock import Mock, patch

from datapiece.scripts.utils import colors


class TestColors(unittest.TestCase):
    def setUp(self):
        colors.disable()

    def test_ok_plain(self):
        self.assertEqual(colors.ok("hello"), "hello")

    def test_warn_plain(self):
        self.assertEqual(colors.warn("hello"), "hello")

    def test_error_plain(self):
        self.assertEqual(colors.error("hello"), "hello")

    def test_info_plain(self):
        self.assertEqual(colors.info("hello"), "hello")

    def test_dim_plain(self):
        self.assertEqual(colors.dim("hello"), "hello")

    def test_bold_plain(self):
        self.assertEqual(colors.bold("hello"), "hello")

    def test_header_plain(self):
        self.assertEqual(colors.header("hello"), "hello")

    def test_ok_colored(self):
        colors._enabled = True
        result = colors.ok("hello")
        self.assertIn("hello", result)
        self.assertIn("\033[", result)
        colors._enabled = False

    def test_functions_return_str(self):
        for fn in (colors.ok, colors.warn, colors.error, colors.info,
                   colors.dim, colors.bold, colors.header):
            self.assertIsInstance(fn("test"), str)


class TestInit(unittest.TestCase):
    def tearDown(self):
        colors.disable()

    def test_init_non_tty_does_nothing(self):
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            colors.init()
        self.assertFalse(colors._enabled)

    def test_init_non_windows_enables(self):
        with patch("sys.stdout") as mock_stdout, \
             patch("datapiece.scripts.utils.colors.os") as mock_os:
            mock_stdout.isatty.return_value = True
            mock_os.name = "posix"
            colors.init()
        self.assertTrue(colors._enabled)

    def test_init_windows_success(self):
        mock_kernel32 = Mock()
        mock_kernel32.GetConsoleMode.return_value = True
        mock_mode = Mock()
        mock_mode.value = 0  # must be int for bitwise OR to work
        mock_ctypes = Mock()
        mock_ctypes.windll.kernel32 = mock_kernel32
        mock_ctypes.c_ulong.return_value = mock_mode
        with patch("sys.stdout") as mock_stdout, \
             patch("datapiece.scripts.utils.colors.os") as mock_os, \
             patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            mock_stdout.isatty.return_value = True
            mock_os.name = "nt"
            colors.init()
        self.assertTrue(colors._enabled)

    def test_init_windows_exception(self):
        mock_ctypes = Mock()
        mock_ctypes.windll.kernel32.GetStdHandle.side_effect = Exception("no handle")
        with patch("sys.stdout") as mock_stdout, \
             patch("datapiece.scripts.utils.colors.os") as mock_os, \
             patch.dict("sys.modules", {"ctypes": mock_ctypes}):
            mock_stdout.isatty.return_value = True
            mock_os.name = "nt"
            colors.init()
        self.assertFalse(colors._enabled)


if __name__ == "__main__":
    unittest.main()
