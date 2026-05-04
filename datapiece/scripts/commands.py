"""
This module defines the Commands class which provides an interface for executing SQL commands.
"""

import csv
import logging
import re
from typing import Any, Callable, Optional

from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.session import Session
from datapiece.scripts.utils import colors

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Maps (command, arg_position) → (sql, label) for context-aware tab completion.
# Console reads this to build suggestions like "1:Romance Dawn".
COMPLETION_MAP: dict[str, dict[int, tuple[str, str] | list[str]]] = {
    "start_chapter": {1: ("SELECT ArcID, ArcName FROM Arcs ORDER BY ArcID", "arc")},
    "add_arc":       {0: ("SELECT SagaID, SagaName FROM Sagas ORDER BY SagaID", "saga")},
    "list_arcs":     {0: ("SELECT SagaID, SagaName FROM Sagas ORDER BY SagaID", "saga")},
    "list_chapters": {0: ("SELECT ArcID, ArcName FROM Arcs ORDER BY ArcID", "arc")},
    "find":          {0: []},  # handled inline — returns static list
}


class Commands:
    """
    A class for executing database commands.

    Attributes:
        handler (DBQueryHandler): Executes the queries.
        session (Session): Tracks the current reading context.
    """

    def __init__(self, handler: DBQueryHandler, config: dict[str, Any], session: Session) -> None:
        self.handler = handler
        self.config = config
        self.session = session
        self._registry: dict[str, Callable] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        self._registry["add_saga"]      = self.add_saga
        self._registry["list_sagas"]    = self.list_sagas
        self._registry["add_arc"]       = self.add_arc
        self._registry["list_arcs"]     = self.list_arcs
        self._registry["start_volume"]  = self.start_volume
        self._registry["list_volumes"]  = self.list_volumes
        self._registry["start_chapter"] = self.start_chapter
        self._registry["list_chapters"] = self.list_chapters
        self._registry["status"]        = self.status
        self._registry["last"]          = self.last
        self._registry["find"]          = self.find
        self._registry["go"]            = self.go
        self._registry["back"]          = self.back
        self._registry["undo"]          = self.undo
        self._registry["count"]         = self.count
        self._registry["export"]        = self.export

    def get_command_names(self) -> list[str]:
        """Return the list of registered command names."""
        return list(self._registry.keys())

    def _is_valid_command(self, func: str) -> bool:
        return func in self._registry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _saga_exists(self, saga_id: int) -> bool:
        result = self.handler.fetch_query(
            "SELECT 1 FROM Sagas WHERE SagaID = ?", params=(saga_id,)
        )
        return result is not None and bool(result)

    def _arc_exists(self, arc_id: int) -> bool:
        result = self.handler.fetch_query(
            "SELECT 1 FROM Arcs WHERE ArcID = ?", params=(arc_id,)
        )
        return result is not None and bool(result)

    def _volume_exists(self, volume_number: int) -> bool:
        result = self.handler.fetch_query(
            "SELECT 1 FROM Volumes WHERE VolumeNumber = ?", params=(volume_number,)
        )
        return result is not None and bool(result)

    def _snapshot_session(self) -> dict:
        return {
            "volume":   self.session.get("volume"),
            "arc_id":   self.session.get("arc_id"),
            "chapter":  self.session.get("chapter"),
            "page":     self.session.get("page"),
            "panel_id": self.session.get("panel_id"),
        }

    # ------------------------------------------------------------------
    # Sagas
    # ------------------------------------------------------------------

    def add_saga(self, *args: str) -> None:
        """add_saga <name> <order>  —  last token is the order number."""
        logger.debug("add_saga called with args=%s", args)
        if len(args) < 2:
            print(colors.warn("Usage: add_saga <name> <order>"))
            return
        try:
            order = int(args[-1])
        except ValueError:
            print(colors.error("Error: <order> must be an integer."))
            return
        name = " ".join(args[:-1])
        prev = self._snapshot_session()
        saga_id = self.handler.execute_insert(
            "INSERT INTO Sagas (SagaName, SagaOrder) VALUES (?, ?)",
            params=(name, order),
        )
        if saga_id is not None:
            self.session.record_insert("Sagas", "SagaID", saga_id, f"Saga '{name}'", prev)
            print(colors.ok(f"Saga '{name}' added  [ID {saga_id}]."))
        else:
            print(colors.error(f"Failed to add saga '{name}'. It may already exist."))

    def list_sagas(self) -> None:
        """list_sagas  —  print all sagas ordered by SagaOrder."""
        rows = self.handler.fetch_query(
            "SELECT SagaID, SagaOrder, SagaName FROM Sagas ORDER BY SagaOrder"
        )
        if rows is None:
            print(colors.error("Database error — could not fetch sagas."))
            return
        if not rows:
            print(colors.dim("No sagas found."))
            return
        print(colors.header(f"{'ID':<6} {'Order':<6} Name"))
        print(colors.dim("-" * 40))
        for saga_id, order, name in rows:
            print(f"{colors.info(str(saga_id)):<14} {str(order):<6} {name}")

    # ------------------------------------------------------------------
    # Arcs
    # ------------------------------------------------------------------

    def add_arc(self, *args: str) -> None:
        """add_arc <saga_id> <name> <order>  —  first token is saga_id, last is order."""
        logger.debug("add_arc called with args=%s", args)
        if len(args) < 3:
            print(colors.warn("Usage: add_arc <saga_id> <name> <order>"))
            return
        try:
            saga_id = int(args[0])
            order = int(args[-1])
        except ValueError:
            print(colors.error("Error: <saga_id> and <order> must be integers."))
            return
        name = " ".join(args[1:-1])
        if not name:
            print(colors.warn("Usage: add_arc <saga_id> <name> <order>"))
            return
        if not self._saga_exists(saga_id):
            print(colors.warn(
                f"Warning: saga {saga_id} does not exist. Run list_sagas to check IDs."
            ))
            return
        prev = self._snapshot_session()
        arc_id = self.handler.execute_insert(
            "INSERT INTO Arcs (SagaID, ArcName, ArcOrder) VALUES (?, ?, ?)",
            params=(saga_id, name, order),
        )
        if arc_id is not None:
            self.session.record_insert("Arcs", "ArcID", arc_id, f"Arc '{name}'", prev)
            print(colors.ok(f"Arc '{name}' added  [ID {arc_id}]."))
        else:
            print(colors.error(f"Failed to add arc '{name}'."))

    def list_arcs(self, saga_id: Optional[str] = None) -> None:
        """list_arcs [saga_id]  —  list all arcs, optionally filtered by saga."""
        if saga_id is not None:
            try:
                sid = int(saga_id)
            except ValueError:
                print(colors.error("Error: <saga_id> must be an integer."))
                return
            rows = self.handler.fetch_query(
                "SELECT ArcID, SagaID, ArcOrder, ArcName FROM Arcs "
                "WHERE SagaID = ? ORDER BY ArcOrder",
                params=(sid,),
            )
        else:
            rows = self.handler.fetch_query(
                "SELECT ArcID, SagaID, ArcOrder, ArcName FROM Arcs ORDER BY SagaID, ArcOrder"
            )
        if rows is None:
            print(colors.error("Database error — could not fetch arcs."))
            return
        if not rows:
            print(colors.dim("No arcs found."))
            return
        print(colors.header(f"{'ID':<6} {'SagaID':<8} {'Order':<6} Name"))
        print(colors.dim("-" * 50))
        for arc_id, s_id, order, name in rows:
            print(f"{colors.info(str(arc_id)):<14} {str(s_id):<8} {str(order):<6} {name}")

    # ------------------------------------------------------------------
    # Volumes
    # ------------------------------------------------------------------

    def start_volume(self, number: str, release_date: Optional[str] = None) -> None:
        """start_volume <number> [release_date]  —  open a volume as the active context.

        Creates the volume if it does not exist yet.  Resets chapter/page/panel context.
        release_date format: YYYY-MM-DD
        """
        logger.debug("start_volume called: number=%s date=%s", number, release_date)
        try:
            vol = int(number)
        except ValueError:
            print(colors.error("Error: <number> must be an integer."))
            return

        if release_date is not None and not _DATE_RE.match(release_date):
            print(colors.error("Error: release_date must be in YYYY-MM-DD format."))
            return

        current_vol = self.session.get("volume")
        if current_vol is not None and current_vol != vol:
            current_chap = self.session.get("chapter")
            if current_chap is not None:
                print(colors.warn(
                    f"Warning: switching from Volume {current_vol} "
                    f"(last chapter: {current_chap}). "
                    f"Make sure all chapters were entered before switching."
                ))

        prev = self._snapshot_session()
        if self._volume_exists(vol):
            print(colors.dim(f"Volume {vol} already in database."))
        else:
            if release_date:
                ok = self.handler.execute_query(
                    "INSERT INTO Volumes (VolumeNumber, ReleaseDate) VALUES (?, ?)",
                    params=(vol, release_date),
                )
            else:
                ok = self.handler.execute_query(
                    "INSERT INTO Volumes (VolumeNumber) VALUES (?)",
                    params=(vol,),
                )
            if not ok:
                print(colors.error(f"Failed to create volume {vol}."))
                return
            self.session.record_insert("Volumes", "VolumeNumber", vol, f"Volume {vol}", prev)
            print(colors.ok(f"Volume {vol} added to database."))

        self.session.set(volume=vol, chapter=None, page=None, panel_id=None)
        print(colors.info(f"Now in Volume {vol}."))

    def list_volumes(self) -> None:
        """list_volumes  —  print all volumes ordered by VolumeNumber."""
        rows = self.handler.fetch_query(
            "SELECT VolumeNumber, ReleaseDate FROM Volumes ORDER BY VolumeNumber"
        )
        if rows is None:
            print(colors.error("Database error — could not fetch volumes."))
            return
        if not rows:
            print(colors.dim("No volumes found."))
            return
        print(colors.header(f"{'Number':<8} ReleaseDate"))
        print(colors.dim("-" * 24))
        for number, release_date in rows:
            print(f"{colors.info(str(number)):<14} {release_date or colors.dim('-')}")

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    def start_chapter(self, *args: str) -> None:  # pylint: disable=too-many-branches
        """start_chapter <number> [arc_id] [name] [pub_date] [page_count]

        Requires an active volume (run start_volume first).
        arc_id: if the second token is an integer it is used as the arc and
                remembered in the session; otherwise the session's last arc_id
                is reused automatically.

        Trailing detection (right to left):
          - last token is purely numeric  → page_count
          - last token matches YYYY-MM-DD → pub_date
          - remaining tokens joined       → chapter name
        """
        logger.debug("start_chapter called with args=%s", args)
        if not args:
            print(colors.warn(
                "Usage: start_chapter <number> [arc_id] [name] [pub_date] [page_count]"
            ))
            return

        volume = self.session.get("volume")
        if volume is None:
            print(colors.error("No active volume. Run: start_volume <number>"))
            return

        try:
            chapter_number = int(args[0])
        except ValueError:
            print(colors.error("Error: <number> must be an integer."))
            return

        rest = list(args[1:])

        arc_id = None
        if rest:
            try:
                arc_id = int(rest[0])
                rest = rest[1:]
            except ValueError:
                arc_id = self.session.get("arc_id")
        else:
            arc_id = self.session.get("arc_id")

        if arc_id is None:
            print(colors.error(
                "No arc set. Provide an arc_id: start_chapter <number> <arc_id> [name] ..."
                "\nRun list_arcs to see arc IDs."
            ))
            return

        if not self._arc_exists(arc_id):
            print(colors.warn(
                f"Warning: arc {arc_id} does not exist. Run list_arcs to check IDs."
            ))
            return

        page_count = None
        pub_date = None
        if rest and rest[-1].isdigit():
            page_count = int(rest.pop())
        if rest and _DATE_RE.match(rest[-1]):
            pub_date = rest.pop()

        name = " ".join(rest) if rest else None

        current_chap = self.session.get("chapter")
        if current_chap is not None and current_chap != chapter_number:
            current_page = self.session.get("page")
            if current_page is not None:
                print(colors.warn(
                    f"Warning: switching from Chapter {current_chap} "
                    f"(last page: {current_page}). Make sure all pages were entered."
                ))

        prev = self._snapshot_session()
        ok = self.handler.execute_query(
            "INSERT INTO Chapters (ChapterID, ChapterNumber, VolumeNumber, "
            "ArcID, ChapterName, PublicationDate, PageCount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            params=(chapter_number, chapter_number, volume, arc_id, name, pub_date, page_count),
        )
        if not ok:
            print(colors.error(
                f"Failed to add chapter {chapter_number}. "
                f"It may already exist — use list_chapters {arc_id} to check."
            ))
            return

        label = f" '{name}'" if name else ""
        self.session.record_insert(
            "Chapters", "ChapterID", chapter_number,
            f"Chapter {chapter_number}{label}", prev
        )
        self.session.set(arc_id=arc_id, chapter=chapter_number, page=None, panel_id=None)
        print(colors.ok(f"Chapter {chapter_number}{label} added.") + " " +
              colors.info(f"Now in Chapter {chapter_number}."))

    def list_chapters(self, arc_id: str) -> None:
        """list_chapters <arc_id>  —  list all chapters in an arc."""
        try:
            aid = int(arc_id)
        except ValueError:
            print(colors.error("Error: <arc_id> must be an integer."))
            return
        if not self._arc_exists(aid):
            print(colors.warn(
                f"Warning: arc {arc_id} does not exist. Run list_arcs to check IDs."
            ))
            return
        rows = self.handler.fetch_query(
            "SELECT ChapterNumber, VolumeNumber, PublicationDate, PageCount, ChapterName "
            "FROM Chapters WHERE ArcID = ? ORDER BY ChapterNumber",
            params=(aid,),
        )
        if rows is None:
            print(colors.error("Database error — could not fetch chapters."))
            return
        if not rows:
            print(colors.dim(f"No chapters found for arc {arc_id}."))
            return
        print(colors.header(f"{'No.':<6} {'Vol':<5} {'Pages':<6} {'Date':<12} Name"))
        print(colors.dim("-" * 60))
        for number, volume, pub_date, page_count, ch_name in rows:
            print(
                f"{colors.info(str(number)):<14} "
                f"{str(volume or colors.dim('-')):<5} "
                f"{str(page_count or colors.dim('-')):<6} "
                f"{pub_date or colors.dim('-'):<12} "
                f"{ch_name or colors.dim('-')}"
            )

    # ------------------------------------------------------------------
    # Session info
    # ------------------------------------------------------------------

    def status(self) -> None:
        """status  —  show the current reading context."""
        vol   = self.session.get("volume")
        arc   = self.session.get("arc_id")
        chap  = self.session.get("chapter")
        page  = self.session.get("page")
        panel = self.session.get("panel_id")

        def _fmt(v: Any) -> str:
            return colors.info(str(v)) if v is not None else colors.dim("-")

        print(colors.bold("Current session:"))
        print(f"  Volume:  {_fmt(vol)}")
        print(f"  Arc:     {_fmt(arc)}")
        print(f"  Chapter: {_fmt(chap)}")
        print(f"  Page:    {_fmt(page)}")
        print(f"  Panel:   {_fmt(panel)}")

    # ------------------------------------------------------------------
    # last
    # ------------------------------------------------------------------

    def last(self) -> None:
        """last  —  show the most recently inserted item."""
        record = self.session.get("last_insert")
        if not record:
            print(colors.dim("No insert recorded this session."))
            return
        print(
            colors.bold("Last insert:") + "  " +
            colors.ok(record["display"]) + "  " +
            colors.dim(f"({record['table']}.{record['id_col']} = {record['id_val']})")
        )

    # ------------------------------------------------------------------
    # find
    # ------------------------------------------------------------------

    def find(self, *args: str) -> None:
        """find <type> <term>  —  search for rows by name.

        Types: arc, saga, chapter, volume
        Example: find arc dawn
        """
        types_map = {
            "arc": (
                "SELECT ArcID, ArcName FROM Arcs WHERE ArcName LIKE ?",
                "ArcID", "ArcName",
            ),
            "saga": (
                "SELECT SagaID, SagaName FROM Sagas WHERE SagaName LIKE ?",
                "SagaID", "SagaName",
            ),
            "chapter": (
                "SELECT ChapterID, ChapterName FROM Chapters WHERE ChapterName LIKE ?",
                "ChapterID", "ChapterName",
            ),
            "volume": (
                "SELECT VolumeNumber, ReleaseDate FROM Volumes WHERE VolumeNumber LIKE ?",
                "VolumeNumber", "ReleaseDate",
            ),
        }
        if len(args) < 2:
            print(colors.warn("Usage: find <type> <term>   types: " + ", ".join(types_map)))
            return
        kind = args[0].lower()
        term = "%" + " ".join(args[1:]) + "%"
        if kind not in types_map:
            print(colors.error(f"Unknown type '{kind}'. Choose from: {', '.join(types_map)}"))
            return
        query = types_map[kind][0]
        rows = self.handler.fetch_query(query, params=(term,))
        if rows is None:
            print(colors.error("Database error — search failed."))
            return
        if not rows:
            print(colors.dim(f"No {kind}s matching '{' '.join(args[1:])}'."))
            return
        print(colors.header(f"{'ID':<8} Name"))
        print(colors.dim("-" * 40))
        for row_id, row_name in rows:
            print(f"{colors.info(str(row_id)):<14} {row_name or colors.dim('-')}")

    # ------------------------------------------------------------------
    # go
    # ------------------------------------------------------------------

    def go(self, path: str = "") -> None:
        """go [V<n>][/C<n>][/P<n>][/Pn<n>]  —  jump to a position in the hierarchy.

        Examples:
          go V3          — move to volume 3, clear chapter/page/panel
          go V3/C22      — move to volume 3, chapter 22
          go C15         — stay in current volume, jump to chapter 15
        """
        if not path:
            print(colors.warn("Usage: go [V<n>][/C<n>][/P<n>][/Pn<n>]   e.g. go V3/C22"))
            return

        updates: dict[str, Any] = {}
        tokens = re.findall(r"(?i)(V|C|Pn|P)(\d+)", path)
        if not tokens:
            print(colors.error(f"Cannot parse '{path}'. Example: go V3/C22"))
            return
        key_map = {"v": "volume", "c": "chapter", "p": "page", "pn": "panel_id"}
        for prefix, value in tokens:
            key = key_map.get(prefix.lower())
            if key:
                updates[key] = int(value)

        # Clear children of the highest-level key provided
        if "volume" in updates:
            for child in ["chapter", "page", "panel_id"]:
                if child not in updates:
                    updates[child] = None
        elif "chapter" in updates:
            for child in ["page", "panel_id"]:
                if child not in updates:
                    updates[child] = None

        self.session.set(**updates)
        label = self.session.prompt_label().strip()
        print(colors.info(f"Session set to {label}."))

    # ------------------------------------------------------------------
    # back
    # ------------------------------------------------------------------

    def back(self) -> None:
        """back  —  step out of the current level (panel → page → chapter → volume)."""
        popped = self.session.back()
        if popped is None:
            print(colors.dim("Session is already empty."))
        else:
            label = self.session.prompt_label()
            context = f" — now at {label.strip()}" if label.strip() else " — session is empty"
            print(colors.info(f"Cleared {popped}{context}."))

    # ------------------------------------------------------------------
    # undo
    # ------------------------------------------------------------------

    def undo(self) -> None:
        """undo  —  delete the last inserted row and restore the previous session state."""
        logger.debug("undo called")
        record = self.session.pop_last_insert()
        if not record:
            print(colors.dim("Nothing to undo."))
            return
        table   = record["table"]
        id_col  = record["id_col"]
        id_val  = record["id_val"]
        display = record["display"]
        prev    = record.get("prev_state", {})

        if id_val == -1:
            print(colors.warn("Last insert was a dry-run — nothing to delete."))
        else:
            ok = self.handler.execute_query(
                f"DELETE FROM {table} WHERE {id_col} = ?", params=(id_val,)
            )
            if not ok:
                print(colors.error(f"Failed to delete {display}."))
                return

        if prev:
            self.session.set(**prev)
        print(colors.ok(f"Undone: {display} deleted."))
        label = self.session.prompt_label()
        if label:
            print(colors.info(f"Session restored to {label.strip()}."))

    # ------------------------------------------------------------------
    # count
    # ------------------------------------------------------------------

    def count(self, *args: str) -> None:
        """count <type> [filter_id]  —  count rows in a table.

        Examples:
          count chapters          — total chapters
          count chapters 2        — chapters in arc 2
          count arcs 1            — arcs in saga 1
        """
        config_map = {
            "chapters": ("Chapters", "ArcID",    "arc"),
            "arcs":     ("Arcs",     "SagaID",   "saga"),
            "volumes":  ("Volumes",  None,        None),
            "sagas":    ("Sagas",    None,        None),
        }
        if not args:
            print(colors.warn("Usage: count <type> [id]   types: " + ", ".join(config_map)))
            return
        kind = args[0].lower()
        if kind not in config_map:
            print(colors.error(f"Unknown type '{kind}'. Choose from: {', '.join(config_map)}"))
            return
        table, filter_col, filter_label = config_map[kind]
        if len(args) > 1 and filter_col:
            try:
                fid = int(args[1])
            except ValueError:
                print(colors.error("Error: filter id must be an integer."))
                return
            rows = self.handler.fetch_query(
                f"SELECT COUNT(*) FROM {table} WHERE {filter_col} = ?", params=(fid,)
            )
            suffix = f" in {filter_label} {fid}"
        else:
            rows = self.handler.fetch_query(f"SELECT COUNT(*) FROM {table}")
            suffix = ""
        if rows is None:
            print(colors.error("Database error — could not count rows."))
            return
        total = rows[0][0] if rows else 0
        print(f"{colors.bold(str(total))} {kind}{suffix}")

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------

    def export(self, *args: str) -> None:  # pylint: disable=too-many-locals
        """export <type> [filter_id] [output_file]  —  dump a table to CSV.

        Examples:
          export chapters              — all chapters → chapters.csv
          export chapters 2            — arc 2 chapters → chapters_arc2.csv
          export chapters 2 east.csv   — custom filename
        """
        config_map = {
            "chapters": (
                "SELECT ChapterNumber, VolumeNumber, ArcID, ChapterName, "
                "PublicationDate, PageCount FROM Chapters",
                "ArcID", "arc",
            ),
            "arcs":    ("SELECT ArcID, SagaID, ArcOrder, ArcName FROM Arcs", "SagaID", "saga"),
            "sagas":   ("SELECT SagaID, SagaOrder, SagaName FROM Sagas", None, None),
            "volumes": ("SELECT VolumeNumber, ReleaseDate FROM Volumes", None, None),
        }
        if not args:
            print(colors.warn("Usage: export <type> [filter_id] [file]"))
            return
        kind = args[0].lower()
        if kind not in config_map:
            print(colors.error(f"Unknown type '{kind}'. Choose from: {', '.join(config_map)}"))
            return

        base_query, filter_col, filter_label = config_map[kind]
        rest = list(args[1:])
        fid = None
        outfile = None

        if rest:
            try:
                fid = int(rest[0])
                rest = rest[1:]
            except ValueError:
                pass
        if rest:
            outfile = rest[0]

        if fid is not None and filter_col:
            query = base_query + f" WHERE {filter_col} = ? ORDER BY 1"
            params: tuple = (fid,)
            default_name = f"{kind}_{filter_label}{fid}.csv"
        else:
            query = base_query + " ORDER BY 1"
            params = ()
            default_name = f"{kind}.csv"

        outfile = outfile or default_name
        rows = self.handler.fetch_query(query, params=params)
        if rows is None:
            print(colors.error("Database error — export failed."))
            return
        if not rows:
            print(colors.dim(f"No data to export for {kind}."))
            return

        with open(outfile, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(colors.ok(f"Exported {len(rows)} row(s) to {colors.bold(outfile)}."))
