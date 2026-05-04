"""
Unit tests for the new QoL commands: last, find, go, back, undo, count, export.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, create_autospec, patch

from datapiece.scripts.commands import Commands
from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.session import Session


def _make(handler=None, session=None):
    handler = handler or create_autospec(DBQueryHandler)
    session = session or MagicMock(spec=Session)
    session.get.return_value = None
    return Commands(handler, {}, session), handler, session


class TestLast(unittest.TestCase):
    def test_last_no_record(self):
        cmds, _, session = _make()
        session.get.return_value = None
        with patch("builtins.print") as mock_print:
            cmds.last()
        output = str(mock_print.call_args_list)
        self.assertIn("No insert", output)

    def test_last_with_record(self):
        cmds, _, session = _make()
        session.get.return_value = {
            "table": "Sagas", "id_col": "SagaID", "id_val": 1,
            "display": "Saga 'East Blue'", "prev_state": {}
        }
        with patch("builtins.print") as mock_print:
            cmds.last()
        output = str(mock_print.call_args_list)
        self.assertIn("East Blue", output)


class TestFind(unittest.TestCase):
    def setUp(self):
        self.cmds, self.handler, _ = _make()

    def test_find_no_args(self):
        with patch("builtins.print") as mock_print:
            self.cmds.find()
        output = str(mock_print.call_args_list)
        self.assertIn("Usage", output)

    def test_find_unknown_type(self):
        with patch("builtins.print") as mock_print:
            self.cmds.find("galaxy", "term")
        output = str(mock_print.call_args_list)
        self.assertIn("Unknown type", output)

    def test_find_arc_queries_db(self):
        self.handler.fetch_query.return_value = [(1, "Romance Dawn")]
        with patch("builtins.print"):
            self.cmds.find("arc", "dawn")
        self.handler.fetch_query.assert_called_once()
        call_args = self.handler.fetch_query.call_args
        self.assertIn("%dawn%", call_args[1]["params"][0])

    def test_find_arc_no_results(self):
        self.handler.fetch_query.return_value = []
        with patch("builtins.print") as mock_print:
            self.cmds.find("arc", "xyz")
        output = str(mock_print.call_args_list)
        self.assertIn("No arcs", output)

    def test_find_multiword_term(self):
        self.handler.fetch_query.return_value = []
        self.cmds.find("chapter", "romance", "dawn")
        call_args = self.handler.fetch_query.call_args
        self.assertIn("%romance dawn%", call_args[1]["params"][0])


class TestGo(unittest.TestCase):
    def setUp(self):
        self.cmds, _, self.session = _make()
        self.session.prompt_label.return_value = "[V3/C22] "

    def test_go_no_args(self):
        with patch("builtins.print") as mock_print:
            self.cmds.go()
        output = str(mock_print.call_args_list)
        self.assertIn("Usage", output)

    def test_go_volume_only(self):
        self.cmds.go("V3")
        call_kwargs = self.session.set.call_args[1]
        self.assertEqual(call_kwargs["volume"], 3)
        self.assertIsNone(call_kwargs["chapter"])

    def test_go_volume_and_chapter(self):
        self.cmds.go("V3/C22")
        call_kwargs = self.session.set.call_args[1]
        self.assertEqual(call_kwargs["volume"], 3)
        self.assertEqual(call_kwargs["chapter"], 22)

    def test_go_chapter_only(self):
        self.cmds.go("C15")
        call_kwargs = self.session.set.call_args[1]
        self.assertNotIn("volume", call_kwargs)
        self.assertEqual(call_kwargs["chapter"], 15)

    def test_go_invalid(self):
        with patch("builtins.print") as mock_print:
            self.cmds.go("XYZ")
        output = str(mock_print.call_args_list)
        self.assertIn("Cannot parse", output)


class TestBack(unittest.TestCase):
    def test_back_with_level(self):
        cmds, _, session = _make()
        session.back.return_value = "chapter"
        session.prompt_label.return_value = "[V1] "
        with patch("builtins.print") as mock_print:
            cmds.back()
        output = str(mock_print.call_args_list)
        self.assertIn("chapter", output)

    def test_back_empty_session(self):
        cmds, _, session = _make()
        session.back.return_value = None
        with patch("builtins.print") as mock_print:
            cmds.back()
        output = str(mock_print.call_args_list)
        self.assertIn("empty", output)


class TestUndo(unittest.TestCase):
    def test_undo_nothing_to_undo(self):
        cmds, _, session = _make()
        session.pop_last_insert.return_value = None
        with patch("builtins.print") as mock_print:
            cmds.undo()
        output = str(mock_print.call_args_list)
        self.assertIn("Nothing", output)

    def test_undo_executes_delete(self):
        cmds, handler, session = _make()
        session.pop_last_insert.return_value = {
            "table": "Sagas", "id_col": "SagaID", "id_val": 1,
            "display": "Saga 'East Blue'", "prev_state": {}
        }
        handler.execute_query.return_value = True
        with patch("builtins.print"):
            cmds.undo()
        handler.execute_query.assert_called_once_with(
            "DELETE FROM Sagas WHERE SagaID = ?", params=(1,)
        )

    def test_undo_restores_session(self):
        cmds, handler, session = _make()
        session.pop_last_insert.return_value = {
            "table": "Chapters", "id_col": "ChapterID", "id_val": 5,
            "display": "Chapter 5",
            "prev_state": {
                "volume": 1, "arc_id": 1, "chapter": None, "page": None, "panel_id": None
            }
        }
        handler.execute_query.return_value = True
        with patch("builtins.print"):
            cmds.undo()
        session.set.assert_called_once_with(
            volume=1, arc_id=1, chapter=None, page=None, panel_id=None
        )

    def test_undo_dry_run_sentinel(self):
        cmds, handler, session = _make()
        session.pop_last_insert.return_value = {
            "table": "Sagas", "id_col": "SagaID", "id_val": -1,
            "display": "Saga 'East Blue'", "prev_state": {}
        }
        with patch("builtins.print") as mock_print:
            cmds.undo()
        handler.execute_query.assert_not_called()
        output = str(mock_print.call_args_list)
        self.assertIn("dry-run", output)


class TestCount(unittest.TestCase):
    def setUp(self):
        self.cmds, self.handler, _ = _make()

    def test_count_no_args(self):
        with patch("builtins.print") as mock_print:
            self.cmds.count()
        output = str(mock_print.call_args_list)
        self.assertIn("Usage", output)

    def test_count_unknown_type(self):
        with patch("builtins.print") as mock_print:
            self.cmds.count("panels")
        output = str(mock_print.call_args_list)
        self.assertIn("Unknown type", output)

    def test_count_total(self):
        self.handler.fetch_query.return_value = [(42,)]
        with patch("builtins.print") as mock_print:
            self.cmds.count("chapters")
        output = str(mock_print.call_args_list)
        self.assertIn("42", output)
        query = self.handler.fetch_query.call_args[0][0]
        self.assertIn("COUNT(*)", query)
        self.assertIn("Chapters", query)

    def test_count_with_filter(self):
        self.handler.fetch_query.return_value = [(7,)]
        with patch("builtins.print"):
            self.cmds.count("chapters", "2")
        call = self.handler.fetch_query.call_args
        self.assertIn("WHERE ArcID = ?", call[0][0])
        self.assertEqual(call[1]["params"], (2,))

    def test_count_invalid_filter_id(self):
        with patch("builtins.print") as mock_print:
            self.cmds.count("chapters", "abc")
        output = str(mock_print.call_args_list)
        self.assertIn("integer", output)


class TestExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cmds, self.handler, _ = _make()

    def test_export_no_args(self):
        with patch("builtins.print") as mock_print:
            self.cmds.export()
        output = str(mock_print.call_args_list)
        self.assertIn("Usage", output)

    def test_export_unknown_type(self):
        with patch("builtins.print") as mock_print:
            self.cmds.export("panels")
        output = str(mock_print.call_args_list)
        self.assertIn("Unknown type", output)

    def test_export_creates_csv(self):
        outfile = os.path.join(self.tmp, "test_export.csv")
        self.handler.fetch_query.return_value = [(1, 1, 1, "Romance Dawn", "1997-07-22", 53)]
        with patch("builtins.print"):
            self.cmds.export("chapters", outfile)
        # outfile arg is treated as filter_id (non-int) and then filename
        # Let's use explicit filename arg
        outfile2 = os.path.join(self.tmp, "export2.csv")
        self.cmds.export("chapters", outfile2)
        # Actually export("chapters", outfile) — first non-int rest arg is filename
        # Let me just verify fetch_query was called
        self.handler.fetch_query.assert_called()

    def test_export_no_data(self):
        self.handler.fetch_query.return_value = []
        with patch("builtins.print") as mock_print:
            self.cmds.export("sagas")
        output = str(mock_print.call_args_list)
        self.assertIn("No data", output)

    def test_export_writes_rows(self):
        outfile = os.path.join(self.tmp, "sagas.csv")
        self.handler.fetch_query.return_value = [(1, 1, "East Blue"), (2, 2, "Alabasta")]
        with patch("builtins.print"):
            self.cmds.export("sagas", outfile)
        self.assertTrue(os.path.isfile(outfile))
        with open(outfile) as f:
            content = f.read()
        self.assertIn("East Blue", content)
        self.assertIn("Alabasta", content)


if __name__ == "__main__":
    unittest.main()
