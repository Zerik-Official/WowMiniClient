"""
GameCommandHandler interface defining message sending and WHO/GMOTD commands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class GameCommandHandler(ABC):
    """Interface for sending messages to WoW and handling commands."""

    @abstractmethod
    def send_message_to_wow(
        self, tp: int, message: str, target: str | None = None
    ) -> None:
        """Send a chat message to the WoW game server."""

    @abstractmethod
    def send_notification(self, message: str) -> None:
        """Send a guild notification message."""

    @abstractmethod
    def handle_who(self, arguments: str | None) -> str | None:
        """Handle a WHO query, returning optional inline result."""

    @abstractmethod
    def handle_gmotd(self) -> str | None:
        """Return the guild MOTD string if available, otherwise None."""
