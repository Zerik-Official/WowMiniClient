"""
Thread-safe logger with tag-based filtering and colored output.
Allows per-tag and per-level filtering rules.
"""

import threading
from datetime import datetime
from enum import StrEnum, unique
from typing import Final, Literal

from colorama import Fore, Style

_log_lock = threading.Lock()

ENABLED_TAGS: Final[set[str]] = set()

DISABLED_LEVELS: Final[set[str]] = set()

TAG_LEVEL_RULES: dict[str, set[str]] = {}

LogLevel = Literal["INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG", "CRITICAL"]


@unique
class Tags(StrEnum):
    MAIN = "MAIN"
    CONFIG = "CONFIG"
    REALM = "REALM"
    GAME = "GAME"
    DISCORD = "DISCORD"
    WARDEN = "WARDEN"
    CRYPTO = "CRYPTO"
    NETWORK = "NETWORK"
    COMMAND = "COMMAND"
    SYSTEM = "SYSTEM"


_COLORS: Final[dict[str, str]] = {
    "INFO": Fore.CYAN,
    "SUCCESS": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "DEBUG": Fore.MAGENTA,
    "CRITICAL": Fore.RED + Style.BRIGHT,
}


def log(level: LogLevel, tag: Tags | str, message: str) -> None:
    """
    Print a log message applying tag and level filters.

    Args:
        level: Log severity level (INFO, SUCCESS, WARNING, ERROR, DEBUG, CRITICAL).
        tag: Module or component tag (e.g. MAIN, REALM, GAME).
        message: Text to display.
    """
    level_up: str = level.upper()
    tag_up: str = tag.upper()

    if level_up in DISABLED_LEVELS:
        return

    if ENABLED_TAGS and tag_up not in ENABLED_TAGS:
        return

    if tag_up in TAG_LEVEL_RULES and level_up in TAG_LEVEL_RULES[tag_up]:
        return

    timestamp: str = datetime.now().strftime("%H:%M:%S")
    color: str = _COLORS.get(level_up, Fore.WHITE)
    lvl_fmt: str = f"{level_up:^9}"
    tag_fmt: str = f"{tag_up:^20}"

    with _log_lock:
        print(
            f"{Style.DIM}{timestamp}{Style.RESET_ALL} "
            f"[{color}{lvl_fmt}{Style.RESET_ALL}] "
            f"[{Fore.WHITE}{Style.BRIGHT}{tag_fmt}{Style.RESET_ALL}] "
            f"{message}"
        )
