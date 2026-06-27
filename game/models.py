"""
Data models for WoW game protocol messages.
"""

from __future__ import annotations


def unpack_guid(data: bytes, pos: int = 0) -> tuple[int, int]:
    guid = 0
    mask_bits = data[pos] if pos < len(data) else 0
    pos += 1
    for i in range(8):
        if mask_bits & (1 << i):
            guid |= (data[pos] & 0xFF) << (i * 8)
            pos += 1
    return guid, pos


class Player:
    def __init__(self, name: str, char_class: int) -> None:
        self.name = name
        self.char_class = char_class


class GuildMember:
    def __init__(self, name: str, is_online: bool, char_class: int,
                 level: int, zone_id: int, last_logoff: float) -> None:
        self.name = name
        self.is_online = is_online
        self.char_class = char_class
        self.level = level
        self.zone_id = zone_id
        self.last_logoff = last_logoff


class ChatMessage:
    def __init__(self, guid: int, tp: int, message: str,
                 channel: str | None = None) -> None:
        self.guid = guid
        self.tp = tp
        self.message = message
        self.channel = channel


class NameQueryMessage:
    def __init__(self, guid: int, name: str, char_class: int) -> None:
        self.guid = guid
        self.name = name
        self.char_class = char_class


class CharEnumMessage:
    def __init__(self, name: str, guid: int, race: int, guild_guid: int) -> None:
        self.name = name
        self.guid = guid
        self.race = race
        self.guild_guid = guild_guid


class GuildInfo:
    def __init__(self, name: str, ranks: dict[int, str]) -> None:
        self.name = name
        self.ranks = ranks


class AuthChallengeMessage:
    def __init__(self, session_key: bytes, response: bytes) -> None:
        self.session_key = session_key
        self.response = response
