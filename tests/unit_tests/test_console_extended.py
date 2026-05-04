"""
Unit tests for Console QoL features: aliases, comment skipping, run file, dry-run.
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from datapiece.scripts.console import Console, _DEFAULT_ALIASES
from datapiece.scripts.db_query_handler import DBQueryHandler


def _make_console(extra_config=None):
    handler = Mock(spec=DBQueryHandler)
    handler.conn = Mock()
    config = {"commands": {}, **(extra_config or {})}
    with patch("datapiece.scripts.console.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        mock_session.prompt_label.return_value = ""
        console = Console(handler, config)
    return console, handler


class TestDefaultAliases(unittest.TestCase):
    def test_default_aliases_present(self):
        for alias, cmd in _DEFAULT_ALIASES.items():
            self.assertIsInstance(alias, str)
            self.assertIsInstance(cmd, str)

    def test_sv_maps_to_start_volume(self):
        self.assertEqual(_DEFAULT_ALIASES["sv"], "start_volume")

    def test_sc_maps_to_start_chapter(self):
        self.assertEqual(_DEFAULT_ALIASES["sc"], "start_chapter")


class TestConsoleAliasResolution(unittest.TestCase):
    def setUp(self):
        self.console, _ = _make_console()

    def test_alias_resolves_to_command(self):
        with patch.object(self.console.commands_instance, "start_volume") as mock_cmd:
            self.console._execute_line("sv 1")
        mock_cmd.assert_called_once_with("1")

    def test_alias_sc(self):
        with patch.object(self.console.commands_instance, "start_chapter") as mock_cmd:
            self.console._execute_line("sc 1 1")
        mock_cmd.assert_called_once_with("1", "1")

    def test_config_alias_overrides(self):
        console, _ = _make_console(extra_config={"aliases": {"x": "list_sagas"}})
        with patch.object(console.commands_instance, "list_sagas") as mock_cmd:
            console._execute_line("x")
        mock_cmd.assert_called_once_with()


class TestCommentSkipping(unittest.TestCase):
    def setUp(self):
        self.console, _ = _make_console()

    def test_comment_line_skipped(self):
        with patch.object(self.console.commands_instance, "add_saga") as mock_cmd:
            self.console._execute_line("# this is a comment")
        mock_cmd.assert_not_called()

    def test_blank_line_skipped(self):
        with patch.object(self.console.commands_instance, "add_saga") as mock_cmd:
            self.console._execute_line("   ")
        mock_cmd.assert_not_called()

    def test_inline_comment_not_stripped(self):
        # "add_saga East Blue 1 # comment" — the comment is part of args, not stripped
        # (we only skip full-line comments)
        with patch.object(self.console.commands_instance, "add_saga") as mock_cmd:
            self.console._execute_line("add_saga East Blue 1")
        mock_cmd.assert_called_once()


class TestExecuteLineExitSignal(unittest.TestCase):
    def setUp(self):
        self.console, _ = _make_console()

    def test_exit_returns_false(self):
        result = self.console._execute_line("exit")
        self.assertFalse(result)

    def test_normal_command_returns_true(self):
        with patch.object(self.console.commands_instance, "list_sagas"):
            result = self.console._execute_line("list_sagas")
        self.assertTrue(result)


class TestRunFile(unittest.TestCase):
    def setUp(self):
        self.console, _ = _make_console()
        self.tmp = tempfile.mkdtemp()

    def test_run_missing_file(self):
        with patch("builtins.print") as mock_print:
            self.console._run_file(os.path.join(self.tmp, "nonexistent.txt"))
        output = str(mock_print.call_args_list)
        self.assertIn("not found", output)

    def test_run_executes_commands(self):
        path = os.path.join(self.tmp, "cmds.txt")
        with open(path, "w") as f:
            f.write("# setup\n")
            f.write("list_sagas\n")
            f.write("list_volumes\n")

        with patch.object(self.console.commands_instance, "list_sagas") as mock_sagas, \
             patch.object(self.console.commands_instance, "list_volumes") as mock_volumes, \
             patch("builtins.print"):
            self.console._run_file(path)

        mock_sagas.assert_called_once()
        mock_volumes.assert_called_once()

    def test_run_skips_comments_in_file(self):
        path = os.path.join(self.tmp, "cmds.txt")
        with open(path, "w") as f:
            f.write("# this is a comment\n")
            f.write("list_sagas\n")

        with patch.object(self.console.commands_instance, "list_sagas") as mock_sagas, \
             patch("builtins.print"):
            self.console._run_file(path)

        mock_sagas.assert_called_once()

    def test_run_stops_on_exit(self):
        path = os.path.join(self.tmp, "cmds.txt")
        with open(path, "w") as f:
            f.write("list_sagas\n")
            f.write("exit\n")
            f.write("list_volumes\n")  # should NOT be reached

        with patch.object(self.console.commands_instance, "list_sagas"), \
             patch.object(self.console.commands_instance, "list_volumes") as mock_volumes, \
             patch("builtins.print"):
            self.console._run_file(path)

        mock_volumes.assert_not_called()


class TestUnknownCommand(unittest.TestCase):
    def test_unknown_command_prints_error(self):
        console, _ = _make_console()
        with patch("builtins.print") as mock_print:
            console._execute_line("totally_unknown_cmd")
        output = str(mock_print.call_args_list)
        self.assertIn("Unknown command", output)


if __name__ == "__main__":
    unittest.main()
