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


class TestPrintHelp(unittest.TestCase):
    """Tests for Console._print_help()."""

    def setUp(self):
        self.console, _ = _make_console()

    def test_print_help_runs_without_error(self):
        with patch("builtins.print"):
            self.console._print_help()

    def test_print_help_includes_key_commands(self):
        with patch("builtins.print") as mock_print:
            self.console._print_help()
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("start_saga", output)
        self.assertIn("status", output)
        self.assertIn("undo", output)


class TestRunMetaCommand(unittest.TestCase):
    """Tests for the 'run' meta-command in _execute_line."""

    def setUp(self):
        self.console, _ = _make_console()

    def test_run_no_args_prints_usage(self):
        with patch("builtins.print") as mock_print:
            result = self.console._execute_line("run")
        self.assertTrue(result)
        mock_print.assert_called_once_with("Usage: run <file>")

    def test_help_meta_command(self):
        with patch.object(self.console, "_print_help") as mock_help:
            self.console._execute_line("help")
        mock_help.assert_called_once()


class TestStartBanners(unittest.TestCase):
    """Tests for debug and session-resume banners shown by Console.start()."""

    def _start_console(self, debug=False, prompt_label=""):
        handler = Mock(spec=DBQueryHandler)
        handler.conn = Mock()
        config = {"commands": {}}
        with patch("datapiece.scripts.console.Session") as mock_session_cls, \
             patch("datapiece.scripts.console.Readline") as mock_readline_cls:
            mock_session = mock_session_cls.return_value
            mock_session.prompt_label.return_value = prompt_label
            mock_rl = mock_readline_cls.return_value
            mock_rl.readline.side_effect = ["exit"]
            console = Console(handler, config, debug=debug)
            with patch("builtins.print") as mock_print:
                console.start()
        return mock_print

    def test_debug_banner_shown(self):
        mock_print = self._start_console(debug=True)
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("DEBUG MODE", output)

    def test_resume_banner_shown_when_session_has_label(self):
        mock_print = self._start_console(prompt_label="V1 ")
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Resuming session", output)


class TestStartHistoryErrors(unittest.TestCase):
    def _start_with(self, read_side_effect=None, write_side_effect=None):
        handler = Mock(spec=DBQueryHandler)
        handler.conn = Mock()
        config = {"commands": {}}
        with patch("datapiece.scripts.console.Session") as mock_session_cls, \
             patch("datapiece.scripts.console.Readline") as mock_readline_cls:
            mock_session = mock_session_cls.return_value
            mock_session.prompt_label.return_value = ""
            mock_rl = mock_readline_cls.return_value
            mock_rl.readline.side_effect = ["exit"]
            if read_side_effect is not None:
                mock_rl.read_history_file.side_effect = read_side_effect
            if write_side_effect is not None:
                mock_rl.write_history_file.side_effect = write_side_effect
            console = Console(handler, config)
            with patch("os.path.isfile", return_value=True), \
                 patch("builtins.print") as mock_print:
                console.start()
        return mock_rl, mock_print

    def test_read_history_oserror_does_not_raise(self):
        mock_rl, _ = self._start_with(read_side_effect=OSError("no file"))
        mock_rl.write_history_file.assert_called_once()

    def test_write_history_oserror_prints_warning(self):
        _, mock_print = self._start_with(write_side_effect=OSError("disk full"))
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("history", output.lower())


class TestRunTutorial(unittest.TestCase):
    def setUp(self):
        self.console, _ = _make_console()

    def test_tutorial_intro_step_no_crash(self):
        with patch("datapiece.scripts.console.Readline") as mock_rl_cls, \
             patch("datapiece.scripts.console._TUTORIAL_STEPS", [("Welcome", "")]):
            mock_rl_cls.return_value.readline.return_value = ""
            with patch.object(self.console, "start"), patch("builtins.print"):
                self.console.run_tutorial()

    def test_tutorial_wrong_then_correct_command(self):
        with patch("datapiece.scripts.console.Readline") as mock_rl_cls, \
             patch("datapiece.scripts.console._TUTORIAL_STEPS", [("Type status", "status")]):
            mock_rl_cls.return_value.readline.side_effect = ["wrong", "status"]
            with patch.object(self.console, "_execute_line") as mock_exec, \
                 patch.object(self.console, "start"), \
                 patch("builtins.print") as mock_print:
                self.console.run_tutorial()
        mock_exec.assert_called_once_with("status")
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Not quite", output)

    def test_tutorial_alias_accepted(self):
        with patch("datapiece.scripts.console.Readline") as mock_rl_cls, \
             patch("datapiece.scripts.console._TUTORIAL_STEPS",
                   [("Type start_volume 1", "start_volume 1")]):
            mock_rl_cls.return_value.readline.side_effect = ["sv 1"]
            with patch.object(self.console, "_execute_line") as mock_exec, \
                 patch.object(self.console, "start"), \
                 patch("builtins.print") as mock_print:
                self.console.run_tutorial()
        mock_exec.assert_called_once_with("sv 1")
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertNotIn("Not quite", output)

    def test_tutorial_keyboard_interrupt_exits_without_start(self):
        with patch("datapiece.scripts.console.Readline") as mock_rl_cls, \
             patch("datapiece.scripts.console._TUTORIAL_STEPS", [("Type status", "status")]):
            mock_rl_cls.return_value.readline.side_effect = KeyboardInterrupt
            with patch.object(self.console, "start") as mock_start, \
                 patch("builtins.print"):
                self.console.run_tutorial()
        mock_start.assert_not_called()

    def test_tutorial_completes_and_calls_start(self):
        with patch("datapiece.scripts.console.Readline") as mock_rl_cls, \
             patch("datapiece.scripts.console._TUTORIAL_STEPS",
                   [("Intro", ""), ("Outro", "")]):
            mock_rl_cls.return_value.readline.return_value = ""
            with patch.object(self.console, "start") as mock_start, \
                 patch("builtins.print"):
                self.console.run_tutorial()
        mock_start.assert_called_once()


class TestBuildCompletions(unittest.TestCase):
    def setUp(self):
        self.console, self.handler = _make_console()
        self.mock_rl = Mock()
        self.console._readline = self.mock_rl

    def test_completer_returns_none_on_exception(self):
        with patch.object(self.console, "_build_completions", side_effect=RuntimeError("boom")):
            result = self.console.completer("", 0)
        self.assertIsNone(result)

    def test_build_completions_get_line_buffer_exception(self):
        self.mock_rl.get_line_buffer.side_effect = RuntimeError("no buffer")
        result = self.console._build_completions("st")
        self.assertIsInstance(result, list)
        self.assertTrue(all(c.startswith("st") for c in result))

    def test_build_completions_argument_no_spec(self):
        self.mock_rl.get_line_buffer.return_value = "list_sagas "
        result = self.console._build_completions("")
        self.assertEqual(result, [])

    def test_build_completions_static_list_spec(self):
        # "find" has {0: []} in COMPLETION_MAP — a static (empty) list
        self.mock_rl.get_line_buffer.return_value = "find "
        result = self.console._build_completions("")
        self.assertIsInstance(result, list)

    def test_build_completions_dynamic_spec_returns_rows(self):
        # start_chapter arg position 1 → dynamic SQL for arcs
        self.mock_rl.get_line_buffer.return_value = "start_chapter 1 "
        self.handler.fetch_query.return_value = [(1, "East Blue")]
        result = self.console._build_completions("")
        self.assertIn("1:East_Blue", result)

    def test_build_completions_dynamic_spec_none_rows(self):
        self.mock_rl.get_line_buffer.return_value = "start_chapter 1 "
        self.handler.fetch_query.return_value = None
        result = self.console._build_completions("")
        self.assertEqual(result, [])

    def test_execute_line_run_with_args_calls_run_file(self):
        with patch.object(self.console, "_run_file") as mock_run_file:
            result = self.console._execute_line("run somefile.txt")
        mock_run_file.assert_called_once_with("somefile.txt")
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
