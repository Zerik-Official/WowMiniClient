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
        """
        Send a chat message to the WoW game server.

        Args:
            tp: Chat message type constant.
            message: Text content of the message.
            target: Optional channel or player name.
        """

    @abstractmethod
    def send_notification(self, message: str) -> None:
        """
        Send a guild notification to WoW.

        Args:
            message: Notification text to send to guild chat.
        """

    @abstractmethod
    def handle_who(self, arguments: str | None) -> str | None:
        """
        Process a WHO query and return the result.

        Args:
            arguments: Search filter text, or None for online guild list.

        Returns:
            Formatted result string, or None if sent to server.
        """

    @abstractmethod
    def handle_gmotd(self) -> str | None:
        """
        Return the guild Message of the Day.

        Returns:
            Guild MOTD string, or None if not yet received.
        """
