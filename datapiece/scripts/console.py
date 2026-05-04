"""
This module provides a console interface for interacting with a database.

QoL features:
  - Persistent command history (saved across restarts)
  - Ctrl+R reverse history search
  - Command + field tab-completion (context-aware)
  - Alias resolution (config-driven + built-in defaults)
  - Inline comments  (lines starting with #)
  - `run <file>` meta-command for batch input
  - Dry-run mode (--dry-run flag shows queries without writing)
  - Coloured output
"""

import logging
import os
from typing import Optional

try:
    from pyreadline3 import Readline  # type: ignore
except ImportError:  # pragma: no cover
    import readline as _rl  # pylint: disable=import-outside-toplevel

    class Readline:  # type: ignore  # pylint: disable=too-few-public-methods
        """Thin wrapper around the stdlib readline module for non-Windows platforms."""

        def parse_and_bind(self, s: str) -> None:
            """Bind a readline key sequence."""
            _rl.parse_and_bind(s)  # type: ignore[attr-defined]

        def set_completer(self, fn) -> None:
            """Set the completer function."""
            _rl.set_completer(fn)  # type: ignore[attr-defined]

        def read_history_file(self, path: str) -> None:
            """Load history from a file."""
            _rl.read_history_file(path)  # type: ignore[attr-defined]

        def write_history_file(self, path: str) -> None:
            """Save history to a file."""
            _rl.write_history_file(path)  # type: ignore[attr-defined]

        def readline(self, prompt: str = "") -> str:
            """Read a line of input with a prompt."""
            return input(prompt)

        def get_line_buffer(self) -> str:
            """Return the current line buffer."""
            return _rl.get_line_buffer()  # type: ignore[attr-defined]

from datapiece.scripts.commands import Commands, COMPLETION_MAP
from datapiece.scripts.db_query_handler import DBQueryHandler
from datapiece.scripts.session import Session
from datapiece.scripts.utils import colors
from datapiece.scripts.utils.config import get_key_dict, get_key_str

logger = logging.getLogger(__name__)


# Built-in aliases — can be overridden or extended in config.json
_DEFAULT_ALIASES: dict[str, str] = {
    "ss":  "start_saga",
    "sa":  "start_arc",
    "sv":  "start_volume",
    "sc":  "start_chapter",
    "lv":  "list_volumes",
    "lc":  "list_chapters",
    "ls":  "list_sagas",
    "la":  "list_arcs",
    "as":  "add_saga",
    "aa":  "add_arc",
    "st":  "status",
    "b":   "back",
}


# Each step is (explanation, expected_command).
# A blank command means "press Enter to continue" (no validation).
_TUTORIAL_STEPS: list[tuple[str, str]] = [
    (
        "Welcome to the DataPiece tutorial!\n"
        "You are running on an isolated in-memory database — nothing here\n"
        "affects your real data. Type each command exactly as shown to continue.\n"
        "Press Enter to begin.",
        "",
    ),
    (
        "Step 1 — Start a Saga.\n"
        "Sagas are the top-level story groups (e.g. 'East Blue').\n"
        "The order is assigned automatically.\n"
        "Syntax:  start_saga <name>\n"
        "Type:    start_saga East Blue",
        "start_saga East Blue",
    ),
    (
        "Step 2 — Start an Arc inside the active Saga.\n"
        "Arcs belong to a Saga and group related chapters.\n"
        "The session remembers which saga you just opened — no ID needed.\n"
        "Syntax:  start_arc <name>\n"
        "Type:    start_arc Romance Dawn",
        "start_arc Romance Dawn",
    ),
    (
        "Step 3 — Open a Volume.\n"
        "start_volume sets the active volume context for all following chapters.\n"
        "Syntax:  start_volume <number> [release_date]\n"
        "Type:    start_volume 1 1997-12-24",
        "start_volume 1 1997-12-24",
    ),
    (
        "Step 4 — Add a Chapter.\n"
        "The session already knows which arc and volume you are in.\n"
        "Syntax:  start_chapter <number> [name] [pub_date] [page_count]\n"
        "Type:    start_chapter 1 Romance Dawn 1999-07-22 53",
        "start_chapter 1 Romance Dawn 1999-07-22 53",
    ),
    (
        "Step 5 — Check your current session.\n"
        "Shows which Volume, Arc, and Chapter you are working in.\n"
        "Type:    status",
        "status",
    ),
    (
        "Step 6 — List chapters in the current arc.\n"
        "Syntax:  list_chapters <arc_id>\n"
        "Type:    list_chapters 1",
        "list_chapters 1",
    ),
    (
        "Step 7 — Add a second chapter (arc is remembered from the session).\n"
        "Syntax:  start_chapter <number> [name] [pub_date] [page_count]\n"
        "Type:    start_chapter 2 Luffy and the Pirate King 1999-08-05 54",
        "start_chapter 2 Luffy and the Pirate King 1999-08-05 54",
    ),
    (
        "Step 8 — Undo the last insert.\n"
        "Deletes the last inserted row and restores the previous session state.\n"
        "Type:    undo",
        "undo",
    ),
    (
        "Step 9 — Count rows in a table.\n"
        "Syntax:  count <type> [filter_id]\n"
        "Type:    count chapters",
        "count chapters",
    ),
    (
        "Tutorial complete!\n"
        "The normal workflow is:  start_saga → start_arc → start_volume → start_chapter\n"
        "Use add_saga / add_arc to insert metadata without changing your active context.\n"
        "This database is temporary — experiment freely. Type 'exit' to quit.",
        "",
    ),
]


class Console:  # pylint: disable=too-many-instance-attributes
    """
    A console interface for interacting with a database.
    """

    def __init__(self, handler: DBQueryHandler, config: dict, debug: bool = False) -> None:
        self.handler = handler
        self.config = config
        self.debug = debug

        session_path = get_key_str(config, "session_path") or "session.json"
        self.session = Session(session_path, ephemeral=debug)

        self.commands_instance = Commands(
            handler, get_key_dict(config, "commands"), self.session
        )
        self.commands = self.commands_instance.get_command_names()

        # Aliases: defaults merged with anything in config
        self.aliases: dict[str, str] = dict(_DEFAULT_ALIASES)
        cfg_aliases = get_key_dict(config, "aliases")
        self.aliases.update(cfg_aliases)

        self.history_path = get_key_str(config, "history_path") or ".datapiece_history"

        # Readline instance stored so the completer can call get_line_buffer()
        self._readline: Optional[Readline] = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the interactive console loop."""
        rl = Readline()
        self._readline = rl
        rl.parse_and_bind("tab: complete")
        rl.parse_and_bind("set show-all-if-ambiguous on")
        rl.set_completer(self.completer)

        # Persistent history
        if os.path.isfile(self.history_path):
            try:
                rl.read_history_file(self.history_path)
            except OSError as e:
                logger.warning("Could not load history from %s: %s", self.history_path, e)

        colors.init()

        print(
            colors.bold("Welcome to DataPiece.") +
            '  Type "exit" to quit, "status" to see your position, "help" for commands.'
        )
        if self.debug:
            print(colors.warn(
                "[DEBUG MODE] Using in-memory database — no changes will be saved to disk."
            ))
        elif self.session.prompt_label():
            print(colors.info(f"Resuming session: {self.session.prompt_label().strip()}"))

        while True:
            try:
                prompt = self.session.prompt_label() + ">>> "
                line = rl.readline(prompt)
                self._execute_line(line)
                if line.lower().strip() == "exit":
                    break
            except KeyboardInterrupt:
                logger.debug("User interrupt (KeyboardInterrupt) — continuing.")
                print()
                continue
            except EOFError:
                logger.debug("User interrupt (EOFError) — exiting.")
                break

        try:
            rl.write_history_file(self.history_path)
        except OSError as e:
            logger.warning("Could not save history to %s: %s", self.history_path, e)
            print(colors.warn(f"Warning: could not save command history to {self.history_path}."))

        self.handler.close()

    # ------------------------------------------------------------------
    # Line execution — reused by start() and run <file>
    # ------------------------------------------------------------------

    def _execute_line(self, line: str) -> bool:
        """
        Process one input line. Returns False if the caller should stop (exit).
        """
        # Strip trailing newline / whitespace
        stripped = line.strip()

        # Exit signal
        if stripped.lower() == "exit":
            return False

        # Blank lines and comments
        if not stripped or stripped.startswith("#"):
            return True

        # Resolve alias
        parts = stripped.split()
        command_name = self.aliases.get(parts[0], parts[0])
        args = parts[1:]

        # Meta-commands handled in Console
        if command_name == "help":
            self._print_help()
            return True

        if command_name == "run":
            if args:
                self._run_file(args[0])
            else:
                print(colors.warn("Usage: run <file>"))
            return True

        # Dispatch to Commands
        if command_name in self.commands:
            getattr(self.commands_instance, command_name)(*args)
        else:
            print(colors.error(f"Unknown command: {command_name}"))

        return True

    # ------------------------------------------------------------------
    # Tutorial
    # ------------------------------------------------------------------

    def run_tutorial(self) -> None:
        """Walk the user through a guided sequence of commands."""
        rl = Readline()
        self._readline = rl
        rl.parse_and_bind("tab: complete")
        rl.set_completer(self.completer)
        colors.init()

        for explanation, expected in _TUTORIAL_STEPS:
            print()
            print(colors.bold("─" * 60))
            print(colors.info(explanation))
            print(colors.bold("─" * 60))

            if not expected:
                # Intro / outro — just wait for Enter
                try:
                    rl.readline("")
                except (KeyboardInterrupt, EOFError):
                    print()
                    break
                continue

            # Require the user to type the correct command
            while True:
                try:
                    raw = rl.readline(colors.dim("tutorial>>> "))
                except (KeyboardInterrupt, EOFError):
                    print()
                    return

                typed = raw.strip()
                if not typed:
                    continue

                # Resolve aliases so e.g. "sv 1" is accepted for "start_volume 1"
                parts = typed.split()
                resolved = self.aliases.get(parts[0], parts[0]) + (
                    (" " + " ".join(parts[1:])) if len(parts) > 1 else ""
                )

                if resolved == expected:
                    self._execute_line(typed)
                    break
                print(colors.warn(
                    f"Not quite. Expected:  {colors.bold(expected)}"
                ))

        print()
        print(colors.bold("Entering interactive mode. Type 'exit' to quit."))
        self.start()

    # ------------------------------------------------------------------
    # Batch file execution
    # ------------------------------------------------------------------

    def _run_file(self, path: str) -> None:
        if not os.path.isfile(path):
            print(colors.error(f"File not found: {path}"))
            return
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        print(colors.info(f"Running {len(lines)} lines from {path} …"))
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                print(colors.dim(f"  [{i}] {stripped}"))
            if not self._execute_line(line):
                break
        print(colors.info("Done."))

    # ------------------------------------------------------------------
    # Tab completion
    # ------------------------------------------------------------------

    def completer(self, text: str, state: int) -> Optional[str]:
        """
        Context-aware tab completion.

        - Empty / partial text at position 0 → complete command names + aliases
        - Arguments → look up COMPLETION_MAP to suggest IDs with names
        """
        try:
            options = self._build_completions(text)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Tab completion error: %s", e, exc_info=True)
            options = []
        if state < len(options):
            return options[state]
        return None

    def _build_completions(self, text: str) -> list[str]:  # pylint: disable=too-many-locals
        line: str = ""
        if self._readline is not None:
            try:
                line = self._readline.get_line_buffer()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug("readline.get_line_buffer() failed: %s", e)

        parts = line.split()
        at_first_token = not parts or (len(parts) == 1 and not line.endswith(" "))

        if at_first_token:
            # Complete command names + alias keys
            all_names = self.commands + list(self.aliases.keys())
            return [n for n in all_names if n.startswith(text)]

        # Resolve alias to real command for argument lookup
        raw_command = parts[0]
        command = self.aliases.get(raw_command, raw_command)
        # Arg position = number of tokens already typed after the command name
        arg_pos = len(parts) - 1 - (0 if line.endswith(" ") else 1)

        field_map = COMPLETION_MAP.get(command, {})
        spec = field_map.get(arg_pos)

        if spec is None:
            return []

        if isinstance(spec, list):
            # Static list (e.g. find types)
            return [s for s in spec if s.startswith(text)]

        # Dynamic query
        sql, _ = spec
        rows = self.handler.fetch_query(sql)
        if rows is None:
            return []

        # Format as "ID:Name" so user can see what they're picking
        suggestions = [f"{row[0]}:{str(row[1]).replace(' ', '_')}" for row in rows]
        return [s for s in suggestions if s.startswith(text)]

    # ------------------------------------------------------------------
    # Help
    # ------------------------------------------------------------------

    def _print_help(self) -> None:
        sections = [
            ("Session navigation  (normal workflow)",
             [("start_saga <name>",                              "Create saga, enter it"),
              ("start_arc <name>",                              "Create arc in active saga"),
              ("start_volume <n> [date]",                       "Open a volume"),
              ("start_chapter <n> [arc] [name] [date] [pages]", "Open a chapter"),
              ("go [V<n>][/C<n>]",                              "Jump to any position"),
              ("back",                                           "Step up one level"),
              ]),
            ("Metadata (exception — does not change active context)",
             [("add_saga <name> [order]",             "Insert a saga out-of-sequence"),
              ("add_arc <saga_ref> <name> [order]",   "Insert an arc out-of-sequence"),
              ]),
            ("Lists",
             [("list_sagas",                          "All sagas"),
              ("list_arcs [saga_id]",                 "All arcs (optional filter)"),
              ("list_volumes",                        "All volumes"),
              ("list_chapters <arc_id>",              "Chapters in an arc"),
              ]),
            ("Utilities",
             [("status",                              "Show current session"),
              ("last",                                "Show last inserted item"),
              ("find <type> <term>",                  "Search by name"),
              ("count <type> [id]",                   "Count rows"),
              ("undo",                                "Delete last insert"),
              ("export <type> [id] [file]",           "Dump to CSV"),
              ("run <file>",                          "Execute a command file"),
              ]),
            ("Aliases (short forms)",
             [(f"{a} → {cmd}", "") for a, cmd in sorted(self.aliases.items())]),
        ]
        for section, cmds in sections:
            print(colors.bold(f"\n{section}"))
            for cmd, desc in cmds:
                pad = colors.info(f"  {cmd:<45}")
                print(f"{pad} {colors.dim(desc)}" if desc else f"  {cmd}")
