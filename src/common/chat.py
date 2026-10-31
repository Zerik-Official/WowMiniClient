"""
Chat message type constants and parsing.
Byte values differ between Vanilla and post-Vanilla expansions.
"""

from __future__ import annotations

from common.types import WowExpansion


class ChatEvents:
    """
    Chat message type IDs that vary by expansion.
    Lazy-initialized per expansion to match the original Scala behavior.
    """

    _expansion: WowExpansion | None = None

    # Vanilla values
    CHAT_MSG_SAY: int = 0x00
    CHAT_MSG_PARTY: int = 0x01
    CHAT_MSG_RAID: int = 0x02
    CHAT_MSG_GUILD: int = 0x03
    CHAT_MSG_OFFICER: int = 0x04
    CHAT_MSG_YELL: int = 0x05
    CHAT_MSG_WHISPER: int = 0x06
    CHAT_MSG_EMOTE: int = 0x08
    CHAT_MSG_TEXT_EMOTE: int = 0x09
    CHAT_MSG_SYSTEM: int = 0x0A
    CHAT_MSG_CHANNEL: int = 0x0E
    CHAT_MSG_CHANNEL_JOIN: int = 0x0F
    CHAT_MSG_CHANNEL_LEAVE: int = 0x10
    CHAT_MSG_CHANNEL_LIST: int = 0x11
    CHAT_MSG_CHANNEL_NOTICE: int = 0x12
    CHAT_MSG_CHANNEL_NOTICE_USER: int = 0x13
    CHAT_MSG_BATTLEGROUND: int = 0x1E
    CHAT_MSG_ACHIEVEMENT: int = 0x30
    CHAT_MSG_GUILD_ACHIEVEMENT: int = 0x31

    @classmethod
    def init(cls, expansion: WowExpansion) -> None:
        """
        Set the expansion and adjust byte values accordingly.
        Must be called once before using parse/valueOf.

        Args:
            expansion: The target game expansion.
        """
        cls._expansion = expansion
        is_vanilla = expansion == WowExpansion.VANILLA

        is_tbc_plus = not is_vanilla
        cls.CHAT_MSG_SAY = 0x00 if is_vanilla else 0x01
        cls.CHAT_MSG_PARTY = 0x01 if is_vanilla else 0x02
        cls.CHAT_MSG_RAID = 0x0C if is_vanilla else 0x0D
        cls.CHAT_MSG_GUILD = 0x03 if is_vanilla else 0x04
        cls.CHAT_MSG_OFFICER = 0x04 if is_vanilla else 0x05
        cls.CHAT_MSG_YELL = 0x05 if is_vanilla else 0x06
        cls.CHAT_MSG_WHISPER = 0x06 if is_vanilla else 0x07
        cls.CHAT_MSG_EMOTE = 0x08 if is_vanilla else 0x0A
        cls.CHAT_MSG_TEXT_EMOTE = 0x09 if is_vanilla else 0x0B
        cls.CHAT_MSG_CHANNEL = 0x0E if is_vanilla else 0x11
        cls.CHAT_MSG_SYSTEM = 0x0A if is_vanilla else 0x00
        cls.CHAT_MSG_CHANNEL_JOIN = 0x0F if is_vanilla else 0x12
        cls.CHAT_MSG_CHANNEL_LEAVE = 0x10 if is_vanilla else 0x13
        cls.CHAT_MSG_CHANNEL_LIST = 0x11 if is_vanilla else 0x14
        cls.CHAT_MSG_CHANNEL_NOTICE = 0x12 if is_vanilla else 0x15
        cls.CHAT_MSG_CHANNEL_NOTICE_USER = 0x13 if is_vanilla else 0x16
        cls.CHAT_MSG_BATTLEGROUND = 0x1C if is_vanilla else 0x1E
        cls.CHAT_MSG_ACHIEVEMENT = 0x2E if expansion == WowExpansion.MOP else 0x30
        cls.CHAT_MSG_GUILD_ACHIEVEMENT = 0x2F if expansion == WowExpansion.MOP else 0x31

    @classmethod
    def parse(cls, tp: str) -> int:
        """
        Resolve a chat type string to its byte ID for the current expansion.

        Args:
            tp: Chat type name (e.g. "say", "guild", "officer", "channel").

        Returns:
            Byte ID for the given type name, or -1 if unknown.
        """
        mapping = {
            "system": cls.CHAT_MSG_SYSTEM,
            "say": cls.CHAT_MSG_SAY,
            "party": cls.CHAT_MSG_PARTY,
            "raid": cls.CHAT_MSG_RAID,
            "guild": cls.CHAT_MSG_GUILD,
            "officer": cls.CHAT_MSG_OFFICER,
            "yell": cls.CHAT_MSG_YELL,
            "emote": cls.CHAT_MSG_EMOTE,
            "whisper": cls.CHAT_MSG_WHISPER,
            "channel": cls.CHAT_MSG_CHANNEL,
            "custom": cls.CHAT_MSG_CHANNEL,
            "battleground": cls.CHAT_MSG_BATTLEGROUND,
        }
        return mapping.get(tp.lower(), -1)

    @classmethod
    def value_of(cls, tp: int) -> str:
        """
        Resolve a byte ID to its human-readable chat type name.

        Args:
            tp: Byte ID of the chat type.

        Returns:
            Human-readable name (e.g. "Say", "Guild"), or "Unknown".
        """
        if tp in (cls.CHAT_MSG_EMOTE, cls.CHAT_MSG_TEXT_EMOTE):
            return "Emote"
        mapping = {
            cls.CHAT_MSG_SAY: "Say",
            cls.CHAT_MSG_PARTY: "Party",
            cls.CHAT_MSG_RAID: "Raid",
            cls.CHAT_MSG_GUILD: "Guild",
            cls.CHAT_MSG_OFFICER: "Officer",
            cls.CHAT_MSG_YELL: "Yell",
            cls.CHAT_MSG_WHISPER: "Whisper",
            cls.CHAT_MSG_CHANNEL: "Channel",
            cls.CHAT_MSG_SYSTEM: "System",
            cls.CHAT_MSG_BATTLEGROUND: "Battleground",
        }
        return mapping.get(tp, "Unknown")
