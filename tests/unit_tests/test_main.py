"""
Unit tests for the datapiece.setup.main() entry point.
"""

import unittest
from unittest.mock import MagicMock, patch

from datapiece.setup import main


class TestMain(unittest.TestCase):
    """Tests for the main() function."""

    def _run_main(self, **kwargs):
        """Helper: run main() with all I/O mocked out."""
        with patch("datapiece.setup.load_config", return_value={}) as mock_load, \
             patch("datapiece.setup.create_handler") as mock_handler, \
             patch("datapiece.setup.create_console") as mock_console_factory:
            mock_console = MagicMock()
            mock_console_factory.return_value = mock_console
            main("config.json", **kwargs)
        return mock_load, mock_handler, mock_console_factory, mock_console

    def test_main_loads_config(self):
        mock_load, _, _, _ = self._run_main()
        mock_load.assert_called_once_with("config.json")

    def test_main_calls_start(self):
        _, _, _, mock_console = self._run_main()
        mock_console.start.assert_called_once()

    def test_main_tutorial_calls_run_tutorial(self):
        _, _, _, mock_console = self._run_main(tutorial=True)
        mock_console.run_tutorial.assert_called_once()
        mock_console.start.assert_not_called()

    def test_main_debug_passes_debug_flag(self):
        _, mock_handler, mock_console_factory, _ = self._run_main(debug=True)
        mock_handler.assert_called_once()
        _, kwargs = mock_handler.call_args
        self.assertTrue(kwargs.get("debug"))

    def test_main_runtime_error_is_caught(self):
        with patch("datapiece.setup.load_config", return_value={}), \
             patch("datapiece.setup.create_handler"), \
             patch("datapiece.setup.create_console") as mock_factory, \
             patch("builtins.print") as mock_print:
            mock_console = MagicMock()
            mock_console.start.side_effect = RuntimeError("DB unavailable")
            mock_factory.return_value = mock_console
            main("config.json")
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("DB unavailable", output)


if __name__ == "__main__":
    unittest.main()
