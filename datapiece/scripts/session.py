"""
Persistent session state — tracks the reader's current position in the manga hierarchy.
Saved to disk after every change so work can be resumed across restarts.
"""

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_HIERARCHY = ("volume", "arc_id", "chapter", "page", "panel_id")
_ALL_KEYS = _HIERARCHY + ("saga_id", "last_insert",)


class Session:
    """
    Holds and persists the current reading context.

    Attributes:
        path (str): Path to the JSON file used for persistence.
    """

    def __init__(self, path: str = "session.json", ephemeral: bool = False) -> None:
        self.path = path
        self.ephemeral = ephemeral
        self._state: dict[str, Any] = dict.fromkeys(_ALL_KEYS, None)
        if not ephemeral:
            self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in _ALL_KEYS:
                if key in data:
                    self._state[key] = data[key]
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Session file %s unreadable (%s): %s", self.path, type(e).__name__, e)
            print("Warning: session file could not be read — starting a fresh session.")

    def save(self) -> None:
        """Persist the current state to disk (no-op when ephemeral)."""
        if self.ephemeral:
            print("(debug) Session is ephemeral — state not written to disk.")
            return
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except OSError as e:
            logger.warning("Could not save session to %s: %s", self.path, e)
            print(f"Warning: could not save session to {self.path}: {e}")

    def set(self, **kwargs: Any) -> None:
        """Update one or more state keys and persist."""
        self._state.update(kwargs)
        self.save()

    def get(self, key: str) -> Optional[Any]:
        """Return the value for key, or None if absent."""
        return self._state.get(key)

    def back(self) -> Optional[str]:
        """
        Clears the deepest non-None level in the hierarchy and returns its name,
        or None if the session is already empty.
        """
        for key in reversed(_HIERARCHY):
            if self._state[key] is not None:
                self._state[key] = None
                self.save()
                return key
        return None

    def record_insert(  # pylint: disable=too-many-arguments
        self,
        table: str,
        id_col: str,
        id_val: Any,
        display: str,
        prev_state: Optional[dict] = None,
    ) -> None:
        """Store the last insert so it can be undone."""
        self._state["last_insert"] = {
            "table": table,
            "id_col": id_col,
            "id_val": id_val,
            "display": display,
            "prev_state": prev_state or {},
        }
        self.save()

    def pop_last_insert(self) -> Optional[dict]:
        """Return and clear the last insert record."""
        record = self._state.get("last_insert")
        self._state["last_insert"] = None
        self.save()
        return record

    def prompt_label(self) -> str:
        """Returns a bracket prefix like '[V1/C5] ' for the console prompt."""
        parts = []
        if self._state["volume"] is not None:
            parts.append(f"V{self._state['volume']}")
        if self._state["chapter"] is not None:
            parts.append(f"C{self._state['chapter']}")
        if self._state["page"] is not None:
            parts.append(f"P{self._state['page']}")
        if self._state["panel_id"] is not None:
            parts.append(f"Pn{self._state['panel_id']}")
        return f"[{'/'.join(parts)}] " if parts else ""
