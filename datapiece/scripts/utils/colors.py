"""
ANSI color helpers. Degrades to plain text when colors are unavailable.
Works in Windows Terminal, macOS Terminal, and Linux without extra dependencies.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_CYAN   = "\033[36m"
_WHITE  = "\033[37m"

_enabled = False


def init() -> None:
    """Enable ANSI colors if the terminal supports them."""
    global _enabled
    if not sys.stdout.isatty():
        return
    if os.name == "nt":
        # Enable VIRTUAL_TERMINAL_PROCESSING on Windows 10+
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
            _enabled = True
        except Exception as e:
            logger.debug("ANSI color init failed: %s", e)
    else:
        _enabled = True


def disable() -> None:
    global _enabled
    _enabled = False


def ok(text: str) -> str:
    """Green — successful insert / positive confirmation."""
    return f"{_GREEN}{text}{_RESET}" if _enabled else text


def warn(text: str) -> str:
    """Yellow — non-fatal warnings."""
    return f"{_YELLOW}{text}{_RESET}" if _enabled else text


def error(text: str) -> str:
    """Red — failures and errors."""
    return f"{_RED}{text}{_RESET}" if _enabled else text


def info(text: str) -> str:
    """Cyan — informational output (lists, status)."""
    return f"{_CYAN}{text}{_RESET}" if _enabled else text


def dim(text: str) -> str:
    """Dim — secondary detail in tables (nulls, dashes)."""
    return f"{_DIM}{text}{_RESET}" if _enabled else text


def bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}" if _enabled else text


def header(text: str) -> str:
    """Bold cyan — table headers."""
    return f"{_BOLD}{_CYAN}{text}{_RESET}" if _enabled else text
