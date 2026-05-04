"""
Unit tests for the colors utility.
"""

import unittest

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


if __name__ == "__main__":
    unittest.main()
