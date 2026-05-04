"""
Unit tests for the extended Session functionality (back, last_insert, undo support).
"""

import tempfile
import os
import unittest

from datapiece.scripts.session import Session


class TestSessionBack(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "session.json")

    def _make(self, **kwargs):
        s = Session(self.path)
        if kwargs:
            s.set(**kwargs)
        return s

    def test_back_clears_deepest_set(self):
        s = self._make(volume=1, chapter=5)
        key = s.back()
        self.assertEqual(key, "chapter")
        self.assertIsNone(s.get("chapter"))
        self.assertEqual(s.get("volume"), 1)

    def test_back_clears_panel_before_page(self):
        s = self._make(volume=1, chapter=3, page=2, panel_id=7)
        key = s.back()
        self.assertEqual(key, "panel_id")
        self.assertIsNone(s.get("panel_id"))
        self.assertEqual(s.get("page"), 2)

    def test_back_on_empty_returns_none(self):
        s = self._make()
        result = s.back()
        self.assertIsNone(result)

    def test_back_persists_to_disk(self):
        s = self._make(volume=1, chapter=5)
        s.back()
        reloaded = Session(self.path)
        self.assertIsNone(reloaded.get("chapter"))
        self.assertEqual(reloaded.get("volume"), 1)


class TestSessionLastInsert(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "session.json")

    def test_record_and_pop(self):
        s = Session(self.path)
        s.record_insert("Sagas", "SagaID", 1, "Saga 'East Blue'", {"volume": None})
        record = s.pop_last_insert()
        self.assertIsNotNone(record)
        self.assertEqual(record["table"], "Sagas")
        self.assertEqual(record["id_val"], 1)
        self.assertEqual(record["display"], "Saga 'East Blue'")

    def test_pop_clears_last_insert(self):
        s = Session(self.path)
        s.record_insert("Sagas", "SagaID", 1, "Saga 'East Blue'", {})
        s.pop_last_insert()
        self.assertIsNone(s.pop_last_insert())

    def test_pop_on_empty_returns_none(self):
        s = Session(self.path)
        self.assertIsNone(s.pop_last_insert())

    def test_record_persists_to_disk(self):
        s = Session(self.path)
        s.record_insert("Chapters", "ChapterID", 5, "Chapter 5", {"volume": 1})
        reloaded = Session(self.path)
        record = reloaded.get("last_insert")
        self.assertEqual(record["id_val"], 5)
        self.assertEqual(record["prev_state"]["volume"], 1)


if __name__ == "__main__":
    unittest.main()
