"""
Unit tests for the Commands class.
"""

import unittest
from unittest.mock import MagicMock, create_autospec, patch

from datapiece.scripts.commands import Commands
from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.session import Session


def _make_commands(handler=None, session=None):
    handler = handler or create_autospec(DBQueryHandler)
    session = session or MagicMock(spec=Session)
    session.get.return_value = None
    return Commands(handler, {}, session), handler, session


class TestCommandsRegistry(unittest.TestCase):
    """Tests for the Commands registry and command name lookup."""

    def setUp(self):
        """Set up a Commands instance with mock dependencies."""
        self.commands, self.handler, self.session = _make_commands()

    def test_get_command_names_returns_list(self):
        """get_command_names returns a list that excludes internal methods."""
        names = self.commands.get_command_names()
        self.assertIsInstance(names, list)
        self.assertNotIn("__init__", names)

    def test_is_valid_command(self):  # pylint: disable=protected-access
        """_is_valid_command returns True for registered commands only."""
        self.assertTrue(self.commands._is_valid_command("start_volume"))
        self.assertTrue(self.commands._is_valid_command("start_chapter"))
        self.assertTrue(self.commands._is_valid_command("add_saga"))
        self.assertFalse(self.commands._is_valid_command("__init__"))
        self.assertFalse(self.commands._is_valid_command("nonexistent"))

    def test_all_sprint1_commands_registered(self):
        """All sprint-1 commands are present in the registry."""
        names = self.commands.get_command_names()
        expected = [
            "add_saga", "list_sagas", "add_arc", "list_arcs",
            "start_volume", "list_volumes", "start_chapter", "list_chapters",
            "status",
        ]
        for cmd in expected:
            self.assertIn(cmd, names)


class TestAddSaga(unittest.TestCase):
    """Tests for the add_saga command."""

    def setUp(self):
        """Set up mock Commands instance."""
        self.commands, self.handler, _ = _make_commands()

    def test_add_saga_success(self):
        """add_saga inserts the row and prints a confirmation."""
        self.handler.execute_insert.return_value = 1
        with patch("builtins.print") as mock_print:
            self.commands.add_saga("East Blue", "1")
        self.handler.execute_insert.assert_called_once_with(
            "INSERT INTO Sagas (SagaName, SagaOrder) VALUES (?, ?)",
            params=("East Blue", 1),
        )
        mock_print.assert_called_once_with("Saga 'East Blue' added  [ID 1].")

    def test_add_saga_failure_prints_message(self):
        """add_saga prints an error when the insert returns None."""
        self.handler.execute_insert.return_value = None
        with patch("builtins.print") as mock_print:
            self.commands.add_saga("East Blue", "1")
        mock_print.assert_called_once_with(
            "Failed to add saga 'East Blue'. It may already exist."
        )

    def test_add_saga_missing_args(self):
        """add_saga prints usage when fewer than two arguments are provided."""
        with patch("builtins.print") as mock_print:
            self.commands.add_saga("East Blue")
        mock_print.assert_called_once_with("Usage: add_saga <name> <order>")

    def test_add_saga_non_integer_order(self):
        """add_saga prints an error when order is not an integer."""
        with patch("builtins.print") as mock_print:
            self.commands.add_saga("East Blue", "abc")
        mock_print.assert_called_once_with("Error: <order> must be an integer.")

    def test_add_saga_multiword_name(self):
        """add_saga joins all tokens except the last as the name."""
        self.handler.execute_insert.return_value = 2
        self.commands.add_saga("Whole", "Cake", "Island", "8")
        self.handler.execute_insert.assert_called_once_with(
            "INSERT INTO Sagas (SagaName, SagaOrder) VALUES (?, ?)",
            params=("Whole Cake Island", 8),
        )


class TestAddArc(unittest.TestCase):
    """Tests for the add_arc command."""

    def setUp(self):
        """Set up mock Commands instance with an existing saga."""
        self.commands, self.handler, _ = _make_commands()
        self.handler.fetch_query.return_value = [(1,)]  # saga exists

    def test_add_arc_success(self):
        """add_arc inserts the row and prints a confirmation."""
        self.handler.execute_insert.return_value = 1
        with patch("builtins.print") as mock_print:
            self.commands.add_arc("1", "Romance Dawn", "1")
        self.handler.execute_insert.assert_called_once_with(
            "INSERT INTO Arcs (SagaID, ArcName, ArcOrder) VALUES (?, ?, ?)",
            params=(1, "Romance Dawn", 1),
        )
        mock_print.assert_called_once_with("Arc 'Romance Dawn' added  [ID 1].")

    def test_add_arc_missing_args(self):
        """add_arc prints usage when fewer than three arguments are provided."""
        with patch("builtins.print") as mock_print:
            self.commands.add_arc("1", "Romance Dawn")
        mock_print.assert_called_once_with("Usage: add_arc <saga_id> <name> <order>")

    def test_add_arc_invalid_saga_id(self):
        """add_arc prints an error when saga_id or order is not an integer."""
        with patch("builtins.print") as mock_print:
            self.commands.add_arc("x", "Romance Dawn", "1")
        mock_print.assert_called_once_with("Error: <saga_id> and <order> must be integers.")

    def test_add_arc_saga_not_found(self):
        """add_arc warns and skips insert when the saga does not exist."""
        self.handler.fetch_query.return_value = []  # saga missing
        with patch("builtins.print") as mock_print:
            self.commands.add_arc("99", "Romance Dawn", "1")
        mock_print.assert_called_once_with(
            "Warning: saga 99 does not exist. Run list_sagas to check IDs."
        )
        self.handler.execute_insert.assert_not_called()

    def test_add_arc_multiword_name(self):
        """add_arc joins middle tokens as the arc name."""
        self.handler.execute_insert.return_value = 3
        self.commands.add_arc("1", "Syrup", "Village", "3")
        self.handler.execute_insert.assert_called_once_with(
            "INSERT INTO Arcs (SagaID, ArcName, ArcOrder) VALUES (?, ?, ?)",
            params=(1, "Syrup Village", 3),
        )


class TestStartVolume(unittest.TestCase):
    """Tests for the start_volume command."""

    def setUp(self):
        """Set up mock Commands instance with no pre-existing volume."""
        self.commands, self.handler, self.session = _make_commands()
        self.handler.fetch_query.return_value = []  # volume does not exist by default

    def test_start_volume_creates_new_volume(self):
        """start_volume inserts and activates a new volume."""
        self.handler.execute_query.return_value = True
        with patch("builtins.print"):
            self.commands.start_volume("1")
        self.handler.execute_query.assert_called_once_with(
            "INSERT INTO Volumes (VolumeNumber) VALUES (?)", params=(1,)
        )
        self.session.set.assert_called_once_with(volume=1, chapter=None, page=None, panel_id=None)

    def test_start_volume_with_release_date(self):
        """start_volume passes release_date when provided."""
        self.handler.execute_query.return_value = True
        self.commands.start_volume("1", "1997-12-24")
        self.handler.execute_query.assert_called_once_with(
            "INSERT INTO Volumes (VolumeNumber, ReleaseDate) VALUES (?, ?)",
            params=(1, "1997-12-24"),
        )

    def test_start_volume_already_exists_skips_insert(self):
        """start_volume skips the INSERT when the volume already exists."""
        self.handler.fetch_query.return_value = [(1,)]  # volume exists
        with patch("builtins.print"):
            self.commands.start_volume("1")
        self.handler.execute_query.assert_not_called()
        self.session.set.assert_called_once_with(volume=1, chapter=None, page=None, panel_id=None)

    def test_start_volume_invalid_number(self):
        """start_volume prints an error when volume number is not an integer."""
        with patch("builtins.print") as mock_print:
            self.commands.start_volume("abc")
        mock_print.assert_called_once_with("Error: <number> must be an integer.")
        self.session.set.assert_not_called()

    def test_start_volume_invalid_date_format(self):
        """start_volume prints an error when date is not in YYYY-MM-DD format."""
        with patch("builtins.print") as mock_print:
            self.commands.start_volume("1", "24-12-1997")
        mock_print.assert_called_once_with(
            "Error: release_date must be in YYYY-MM-DD format."
        )
        self.session.set.assert_not_called()

    def test_start_volume_context_switch_warning(self):
        """start_volume prints a warning when switching from a different active volume."""
        self.session.get.side_effect = {"volume": 1, "chapter": 5}.get
        self.handler.fetch_query.return_value = []
        self.handler.execute_query.return_value = True
        with patch("builtins.print") as mock_print:
            self.commands.start_volume("2")
        calls = [str(c) for c in mock_print.call_args_list]
        self.assertTrue(any("Warning" in c for c in calls))


class TestStartChapter(unittest.TestCase):
    """Tests for the start_chapter command."""

    def setUp(self):
        """Set up mock Commands instance with an active volume and existing arc."""
        self.commands, self.handler, self.session = _make_commands()
        # Default: volume is set, arc exists
        self.session.get.side_effect = {
            "volume": 1, "arc_id": None, "chapter": None, "page": None
        }.get
        self.handler.fetch_query.return_value = [(1,)]  # arc exists
        self.handler.execute_query.return_value = True

    def test_start_chapter_no_volume(self):
        """start_chapter prints an error when no volume is active."""
        self.session.get.side_effect = {}.get
        with patch("builtins.print") as mock_print:
            self.commands.start_chapter("1", "1")
        mock_print.assert_called_once_with(
            "No active volume. Run: start_volume <number>"
        )

    def test_start_chapter_no_arc_no_session_arc(self):
        """start_chapter errors when no arc_id is provided and none is in session."""
        with patch("builtins.print") as mock_print:
            self.commands.start_chapter("1")  # no arc provided, none in session
        self.assertIn(
            "No arc set.",
            mock_print.call_args_list[0][0][0],
        )

    def test_start_chapter_arc_not_found(self):
        """start_chapter warns and skips insert when the arc does not exist."""
        self.handler.fetch_query.return_value = []  # arc does not exist
        with patch("builtins.print") as mock_print:
            self.commands.start_chapter("1", "99")
        mock_print.assert_called_once_with(
            "Warning: arc 99 does not exist. Run list_arcs to check IDs."
        )
        self.handler.execute_query.assert_not_called()

    def test_start_chapter_inserts_minimal(self):
        """start_chapter inserts a chapter with only required fields."""
        self.commands.start_chapter("1", "1")
        self.handler.execute_query.assert_called_once_with(
            "INSERT INTO Chapters (ChapterID, ChapterNumber, VolumeNumber, "
            "ArcID, ChapterName, PublicationDate, PageCount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            params=(1, 1, 1, 1, None, None, None),
        )
        self.session.set.assert_called_once_with(
            arc_id=1, chapter=1, page=None, panel_id=None
        )

    def test_start_chapter_with_all_metadata(self):
        """start_chapter parses name, pub_date, and page_count from trailing tokens."""
        self.commands.start_chapter("5", "2", "The", "Truth", "About", "Nami", "1998-03-10", "19")
        self.handler.execute_query.assert_called_once_with(
            "INSERT INTO Chapters (ChapterID, ChapterNumber, VolumeNumber, "
            "ArcID, ChapterName, PublicationDate, PageCount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            params=(5, 5, 1, 2, "The Truth About Nami", "1998-03-10", 19),
        )

    def test_start_chapter_reuses_session_arc(self):
        """start_chapter uses the arc_id from the session when not explicitly provided."""
        self.session.get.side_effect = {
            "volume": 1, "arc_id": 3, "chapter": None, "page": None
        }.get
        self.commands.start_chapter("10", "Some Chapter Name")
        self.handler.execute_query.assert_called_once_with(
            "INSERT INTO Chapters (ChapterID, ChapterNumber, VolumeNumber, "
            "ArcID, ChapterName, PublicationDate, PageCount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            params=(10, 10, 1, 3, "Some Chapter Name", None, None),
        )


class TestListCommands(unittest.TestCase):
    """Tests for list_sagas, list_arcs, list_volumes, and list_chapters commands."""

    def setUp(self):
        """Set up mock Commands instance."""
        self.commands, self.handler, self.session = _make_commands()

    def test_list_sagas_empty(self):
        """list_sagas prints a 'no sagas' message when the table is empty."""
        self.handler.fetch_query.return_value = []
        with patch("builtins.print") as mock_print:
            self.commands.list_sagas()
        mock_print.assert_called_once_with("No sagas found.")

    def test_list_sagas_with_rows(self):
        """list_sagas includes each saga name in the printed output."""
        self.handler.fetch_query.return_value = [(1, 1, "East Blue")]
        with patch("builtins.print") as mock_print:
            self.commands.list_sagas()
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("East Blue", output)

    def test_list_arcs_filtered(self):
        """list_arcs with a saga_id queries only arcs for that saga."""
        self.handler.fetch_query.return_value = [(1, 1, 1, "Romance Dawn")]
        with patch("builtins.print"):
            self.commands.list_arcs("1")
        self.handler.fetch_query.assert_called_once_with(
            "SELECT ArcID, SagaID, ArcOrder, ArcName FROM Arcs WHERE SagaID = ? ORDER BY ArcOrder",
            params=(1,),
        )

    def test_list_arcs_invalid_saga_id(self):
        """list_arcs prints an error when the saga_id is not an integer."""
        with patch("builtins.print") as mock_print:
            self.commands.list_arcs("xyz")
        mock_print.assert_called_once_with("Error: <saga_id> must be an integer.")

    def test_list_volumes_empty(self):
        """list_volumes prints a 'no volumes' message when the table is empty."""
        self.handler.fetch_query.return_value = []
        with patch("builtins.print") as mock_print:
            self.commands.list_volumes()
        mock_print.assert_called_once_with("No volumes found.")

    def test_list_chapters_arc_not_found(self):
        """list_chapters warns when the arc does not exist."""
        self.handler.fetch_query.return_value = []
        with patch("builtins.print") as mock_print:
            self.commands.list_chapters("99")
        mock_print.assert_called_once_with(
            "Warning: arc 99 does not exist. Run list_arcs to check IDs."
        )

    def test_list_chapters_invalid_arc_id(self):
        """list_chapters prints an error when arc_id is not an integer."""
        with patch("builtins.print") as mock_print:
            self.commands.list_chapters("abc")
        mock_print.assert_called_once_with("Error: <arc_id> must be an integer.")


class TestStatus(unittest.TestCase):
    """Tests for the status command."""

    def test_status_prints_all_fields(self):
        """status prints volume, arc, chapter, page, and panel values."""
        commands, _, session = _make_commands()
        session.get.side_effect = {
            "volume": 1, "arc_id": 2, "chapter": 5, "page": None, "panel_id": None
        }.get
        with patch("builtins.print") as mock_print:
            commands.status()
        output = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("1", output)
        self.assertIn("2", output)
        self.assertIn("5", output)


if __name__ == "__main__":
    unittest.main()
