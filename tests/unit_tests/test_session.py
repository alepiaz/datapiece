"""
Unit tests for the Session class.
"""

import json
import os
import tempfile
import unittest

from datapiece.scripts.session import Session


class TestSession(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp_dir, "session.json")

    def _make(self):
        return Session(self.path)

    def test_defaults_are_none(self):
        s = self._make()
        for key in ("volume", "arc_id", "chapter", "page", "panel_id"):
            self.assertIsNone(s.get(key))

    def test_set_persists_to_disk(self):
        s = self._make()
        s.set(volume=3)
        self.assertTrue(os.path.isfile(self.path))
        with open(self.path) as f:
            data = json.load(f)
        self.assertEqual(data["volume"], 3)

    def test_load_restores_state(self):
        s = self._make()
        s.set(volume=2, arc_id=1, chapter=7)
        reloaded = Session(self.path)
        self.assertEqual(reloaded.get("volume"), 2)
        self.assertEqual(reloaded.get("arc_id"), 1)
        self.assertEqual(reloaded.get("chapter"), 7)

    def test_set_multiple_keys(self):
        s = self._make()
        s.set(volume=1, chapter=None, page=None, panel_id=None)
        self.assertEqual(s.get("volume"), 1)
        self.assertIsNone(s.get("chapter"))

    def test_prompt_label_empty(self):
        s = self._make()
        self.assertEqual(s.prompt_label(), "")

    def test_prompt_label_volume_only(self):
        s = self._make()
        s.set(volume=3)
        self.assertEqual(s.prompt_label(), "[V3] ")

    def test_prompt_label_full(self):
        s = self._make()
        s.set(volume=1, chapter=5, page=3, panel_id=2)
        self.assertEqual(s.prompt_label(), "[V1/C5/P3/Pn2] ")

    def test_prompt_label_volume_and_chapter(self):
        s = self._make()
        s.set(volume=2, chapter=10)
        self.assertEqual(s.prompt_label(), "[V2/C10] ")

    def test_corrupt_file_handled_gracefully(self):
        with open(self.path, "w") as f:
            f.write("not valid json{{")
        # Should not raise
        s = Session(self.path)
        self.assertIsNone(s.get("volume"))

    def test_missing_file_handled_gracefully(self):
        missing = os.path.join(self.tmp_dir, "no_such_file.json")
        s = Session(missing)
        self.assertIsNone(s.get("volume"))


if __name__ == "__main__":
    unittest.main()
