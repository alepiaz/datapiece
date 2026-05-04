"""
Unit tests for DBQueryHandler dry_run mode.
"""

import unittest
from unittest.mock import MagicMock, patch

from datapiece.scripts.db_query_handler import DBQueryHandler


class TestDryRun(unittest.TestCase):
    def _make_handler(self, dry_run: bool) -> DBQueryHandler:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        config = {"schema": "", "db": "dummy.db"}
        with patch("sqlite3.connect", return_value=mock_conn):
            h = DBQueryHandler(config, dry_run=dry_run)
        h.mock_cursor = mock_cursor
        h.mock_conn = mock_conn
        return h

    def test_execute_query_write_skipped_in_dry_run(self):
        h = self._make_handler(dry_run=True)
        with patch("builtins.print") as mock_print:
            result = h.execute_query("INSERT INTO Sagas VALUES (?)", params=("x",))
        self.assertTrue(result)
        h.mock_cursor.execute.assert_not_called()
        output = str(mock_print.call_args_list)
        self.assertIn("[dry-run]", output)

    def test_execute_query_select_runs_in_dry_run(self):
        h = self._make_handler(dry_run=True)
        h.execute_query("SELECT * FROM Sagas")
        h.mock_cursor.execute.assert_called_once()

    def test_execute_insert_dry_run_returns_sentinel(self):
        h = self._make_handler(dry_run=True)
        with patch("builtins.print"):
            result = h.execute_insert("INSERT INTO Sagas VALUES (?)", params=("x",))
        self.assertEqual(result, -1)
        h.mock_cursor.execute.assert_not_called()

    def test_execute_query_write_runs_normally_when_not_dry_run(self):
        h = self._make_handler(dry_run=False)
        h.execute_query("INSERT INTO Sagas VALUES (?)", params=("x",))
        h.mock_cursor.execute.assert_called_once()

    def test_execute_insert_runs_normally_when_not_dry_run(self):
        h = self._make_handler(dry_run=False)
        h.mock_cursor.lastrowid = 1
        result = h.execute_insert("INSERT INTO Sagas VALUES (?)", params=("x",))
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
