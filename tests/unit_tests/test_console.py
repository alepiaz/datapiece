"""
Unit tests for the Console class.
"""

import unittest
from typing import List, Tuple, Union
from unittest.mock import Mock, patch

from datapiece.scripts.console import Console
from datapiece.scripts.db_query_handler import DBQueryHandler


class TestConsole(unittest.TestCase):
    """
    Test case for the Console class.
    """

    def setUp(self) -> None:
        """
        Set up the test case.
        """
        self.mock_handler = Mock(spec=DBQueryHandler)
        self.mock_handler.conn = Mock()
        self.mock_config = {"commands": {"exclude_list": ["__init__"]}}
        self.session_patcher = patch("datapiece.scripts.console.Session")
        self.mock_session_cls = self.session_patcher.start()
        self.mock_session = self.mock_session_cls.return_value
        self.mock_session.prompt_label.return_value = ""
        self.console = Console(self.mock_handler, self.mock_config)
        self.patcher = patch("datapiece.scripts.console.Readline")
        self.mock_readline = self.patcher.start()
        self.mock_readline_instance = self.mock_readline.return_value

    def tearDown(self) -> None:
        """
        Clean up after the test case.
        """
        self.mock_readline.stop()
        self.session_patcher.stop()

    def _test_start(
        self,
        input_text: List[str],
        expected_output: str,
        expected_call: Union[str, Tuple[str]],
    ) -> None:
        """
        Helper method to test the start method of the Console class.
        """
        self.mock_readline_instance.readline.side_effect = input_text
        with patch(expected_output) as mock_output:
            self.console.start()
            mock_output.assert_called_with(*expected_call)

    def test_start_known_command(self) -> None:
        """
        Test the start method with a known command.
        """
        self._test_start(
            ["start_volume 1", "exit"],
            "datapiece.scripts.commands.Commands.start_volume",
            ("1",),
        )

    def test_start_unknown_command(self) -> None:
        """
        Test the start method with an unknown command.
        """
        self._test_start(
            ["unknown_command", "exit"],
            "builtins.print",
            ("Unknown command: unknown_command",),
        )

    def test_start_keyboard_interrupt(self) -> None:
        """
        Test the start method with a keyboard interrupt.
        """
        self.mock_readline_instance.readline.side_effect = iter([KeyboardInterrupt])
        with patch("logging.info") as mock_output:
            with self.assertRaises(StopIteration):
                self.console.start()
            mock_output.assert_called_with("Exit")

    def test_start_eof_error(self) -> None:
        """
        Test the start method with an EOF error.
        """
        self.mock_readline_instance.readline.side_effect = [EOFError]
        with patch("logging.info") as mock_output:
            self.console.start()
            mock_output.assert_called_with("Exit")

    def test_completer(self) -> None:
        """
        Test the completer method.
        """
        self.console.commands = ["command1", "command2"]
        self.assertEqual(self.console.completer("comm", 0), "command1")
        self.assertEqual(self.console.completer("comm", 1), "command2")
        self.assertIsNone(self.console.completer("xyz", 0))


if __name__ == "__main__":
    unittest.main()
