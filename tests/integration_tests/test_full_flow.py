"""
Integration tests for the full application flow.
"""

import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from datapiece.scripts.commands import Commands
from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.session import Session


SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "schema.sql")


class TestFullFlow(unittest.TestCase):
    """
    Integration tests that exercise the real database and schema.
    """

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test.db")
        self.session_path = os.path.join(self.tmp_dir, "session.json")
        config = {"schema": SCHEMA_PATH, "db": self.db_path, "mode": "test"}
        self.handler = DBQueryHandler(config)
        self.session = Session(self.session_path)
        self.commands = Commands(self.handler, {}, self.session)
        self._input_patcher = patch("builtins.input", return_value="")
        self._input_patcher.start()
        self.addCleanup(self._input_patcher.stop)

    def tearDown(self) -> None:
        self.handler.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def test_schema_is_created_on_fresh_db(self) -> None:
        """All expected tables exist after handler initialises a fresh database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        for expected in ("Volumes", "Characters", "Chapters", "Sagas", "Arcs"):
            self.assertIn(expected, tables)

    def test_db_directory_created_automatically(self) -> None:
        """Handler creates missing parent directories before connecting."""
        nested_path = os.path.join(self.tmp_dir, "nested", "subdir", "fresh.db")
        config = {"schema": SCHEMA_PATH, "db": nested_path, "mode": "test"}
        handler = DBQueryHandler(config)
        handler.close()
        self.assertTrue(os.path.exists(nested_path))

    # ------------------------------------------------------------------
    # Sagas
    # ------------------------------------------------------------------

    def test_add_saga_inserts_row(self) -> None:
        """add_saga persists a saga row with the correct name and order."""
        self.commands.add_saga("East Blue", "1")
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT SagaName, SagaOrder FROM Sagas WHERE SagaID = 1").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "East Blue")
        self.assertEqual(row[1], 1)

    def test_add_saga_duplicate_fails_gracefully(self) -> None:
        """add_saga does not raise when called with duplicate arguments."""
        self.commands.add_saga("East Blue", "1")
        # Inserting same order violates UNIQUE on (SagaName, SagaOrder) if any — but
        # actually there's no unique constraint except primary key. A second insert
        # with the same name/order will just create a new row.  The real guard is
        # the execute_insert returning None on sqlite error.
        # Just verify no exception is raised.
        self.commands.add_saga("East Blue", "1")

    # ------------------------------------------------------------------
    # Arcs
    # ------------------------------------------------------------------

    def test_add_arc_inserts_row(self) -> None:
        """add_arc persists an arc row with the correct name, order, and saga reference."""
        self.commands.add_saga("East Blue", "1")
        self.commands.add_arc("1", "Romance Dawn", "1")
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT ArcName, ArcOrder, SagaID FROM Arcs WHERE ArcID = 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "Romance Dawn")
        self.assertEqual(row[2], 1)

    def test_add_arc_rejects_missing_saga(self) -> None:
        """add_arc does not insert an arc when the referenced saga does not exist."""
        # saga 99 was never inserted — command should warn and not insert
        self.commands.add_arc("99", "Romance Dawn", "1")
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT * FROM Arcs").fetchall()
        conn.close()
        self.assertEqual(rows, [])

    # ------------------------------------------------------------------
    # Volumes
    # ------------------------------------------------------------------

    def test_start_volume_inserts_row(self) -> None:
        """start_volume persists a volume row with the correct number."""
        self.commands.start_volume("1")
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT VolumeNumber FROM Volumes WHERE VolumeNumber = 1").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_start_volume_sets_session(self) -> None:
        """start_volume updates the session volume and clears chapter."""
        self.commands.start_volume("3")
        self.assertEqual(self.session.get("volume"), 3)
        self.assertIsNone(self.session.get("chapter"))

    def test_start_volume_existing_does_not_duplicate(self) -> None:
        """start_volume called twice with the same number does not create a duplicate row."""
        self.commands.start_volume("1")
        self.commands.start_volume("1")  # second call — volume already exists
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT VolumeNumber FROM Volumes WHERE VolumeNumber = 1").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)

    def test_start_volume_with_release_date(self) -> None:
        """start_volume stores the release date entered at the interactive prompt."""
        with patch("builtins.input", return_value="1997-12-24"):
            self.commands.start_volume("1")
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT ReleaseDate FROM Volumes WHERE VolumeNumber = 1").fetchone()
        conn.close()
        self.assertEqual(row[0], "1997-12-24")

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    def test_start_chapter_inserts_row(self) -> None:
        """start_chapter persists a chapter row with metadata from interactive prompts."""
        self.commands.add_saga("East Blue", "1")
        self.commands.add_arc("1", "Romance Dawn", "1")
        self.commands.start_volume("1")
        with patch("builtins.input") as mock_input:
            mock_input.side_effect = ["Romance Dawn", "1997-07-22", "53"]
            self.commands.start_chapter("1", "1")
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT ChapterNumber, ChapterName, PublicationDate, PageCount "
            "FROM Chapters WHERE ChapterID = 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)
        self.assertEqual(row[1], "Romance Dawn")
        self.assertEqual(row[2], "1997-07-22")
        self.assertEqual(row[3], 53)

    def test_start_chapter_sets_session(self) -> None:
        """start_chapter updates the session chapter and arc_id."""
        self.commands.add_saga("East Blue", "1")
        self.commands.add_arc("1", "Romance Dawn", "1")
        self.commands.start_volume("1")
        self.commands.start_chapter("1", "1")
        self.assertEqual(self.session.get("chapter"), 1)
        self.assertEqual(self.session.get("arc_id"), 1)
        self.assertIsNone(self.session.get("page"))

    def test_start_chapter_reuses_arc_from_session(self) -> None:
        """start_chapter reuses the arc_id stored in the session when omitted."""
        self.commands.add_saga("East Blue", "1")
        self.commands.add_arc("1", "Romance Dawn", "1")
        self.commands.start_volume("1")
        self.commands.start_chapter("1", "1")         # sets arc_id=1 in session
        self.commands.start_chapter("2")              # should reuse arc_id=1
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT ArcID FROM Chapters WHERE ChapterID = 2").fetchone()
        conn.close()
        self.assertEqual(row[0], 1)

    def test_list_chapters_returns_correct_arc(self) -> None:
        """Only chapters belonging to the specified arc are returned."""
        self.commands.add_saga("East Blue", "1")
        self.commands.add_arc("1", "Romance Dawn", "1")
        self.commands.start_volume("1")
        for i in range(1, 4):
            with patch("builtins.input") as mock_input:
                mock_input.side_effect = [f"Chapter {i}", "", ""]
                self.commands.start_chapter(str(i), "1")
        rows = self.handler.fetch_query(
            "SELECT ChapterNumber FROM Chapters WHERE ArcID = 1 ORDER BY ChapterNumber"
        )
        self.assertIsNotNone(rows)
        self.assertEqual([r[0] for r in rows or []], [1, 2, 3])

    def test_start_chapter_duplicate_fails_gracefully(self) -> None:
        """start_chapter does not raise when called with a duplicate chapter number."""
        self.commands.add_saga("East Blue", "1")
        self.commands.add_arc("1", "Romance Dawn", "1")
        self.commands.start_volume("1")
        self.commands.start_chapter("1", "1")
        # Duplicate should not raise
        self.commands.start_chapter("1", "1")

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def test_session_persists_to_disk(self) -> None:
        """Session state is written to disk and reloadable across instances."""
        self.commands.start_volume("5")
        # Re-load session from the same file
        reloaded = Session(self.session_path)
        self.assertEqual(reloaded.get("volume"), 5)

    # ------------------------------------------------------------------
    # Duplicate insert guard
    # ------------------------------------------------------------------

    def test_duplicate_volume_fails_gracefully(self) -> None:
        """A second INSERT with the same VolumeNumber returns False without raising."""
        ok1 = self.handler.execute_query(
            "INSERT INTO Volumes (VolumeNumber) VALUES (?)", params=(99,)
        )
        ok2 = self.handler.execute_query(
            "INSERT INTO Volumes (VolumeNumber) VALUES (?)", params=(99,)
        )
        self.assertTrue(ok1)
        self.assertFalse(ok2)


if __name__ == "__main__":
    unittest.main()
