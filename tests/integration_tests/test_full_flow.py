"""
Integration tests for the full application flow.
"""

import os
import sqlite3
import tempfile
import unittest

from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.commands import Commands


SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "sql", "schema.sql")


class TestFullFlow(unittest.TestCase):
    """
    Integration tests that exercise the real database and schema.
    """

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test.db")
        config = {
            "schema": SCHEMA_PATH,
            "db": self.db_path,
            "mode": "test",
        }
        self.handler = DBQueryHandler(config)
        self.commands = Commands(self.handler, {})

    def tearDown(self) -> None:
        self.handler.close()

    def test_schema_is_created_on_fresh_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        self.assertIn("Volumes", tables)
        self.assertIn("Characters", tables)
        self.assertIn("Chapters", tables)

    def test_start_volume_inserts_row(self) -> None:
        self.commands.start_volume(1)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT VolumeNumber FROM Volumes WHERE VolumeNumber = 1")
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1)

    def test_start_volume_duplicate_fails_gracefully(self) -> None:
        success1 = self.handler.execute_query(
            "INSERT INTO `Volumes` (`VolumeNumber`) VALUES (?)", params=(99,)
        )
        success2 = self.handler.execute_query(
            "INSERT INTO `Volumes` (`VolumeNumber`) VALUES (?)", params=(99,)
        )
        self.assertTrue(success1)
        self.assertFalse(success2)

    def test_db_directory_created_automatically(self) -> None:
        nested_path = os.path.join(self.tmp_dir, "nested", "subdir", "fresh.db")
        config = {
            "schema": SCHEMA_PATH,
            "db": nested_path,
            "mode": "test",
        }
        handler = DBQueryHandler(config)
        handler.close()
        self.assertTrue(os.path.exists(nested_path))


if __name__ == "__main__":
    unittest.main()
