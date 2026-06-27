# ruff: noqa: E501
"""
Game packet handlers per expansion.
Merged from GamePacketHandler, GamePacketHandlerTBC, GamePacketHandlerWotLK,
GamePacketHandlerCataclysm15595, GamePacketHandlerMoP18414.
"""

from __future__ import annotations

import hashlib
import logging
import random
import struct
import time
from collections.abc import Callable
from typing import Any

from common.chat import ChatEvents
from common.types import (
    Packet,
    PacketBitWriter,
    PacketWriter,
    WowExpansion,
    global_state,
)
from crypto.header import GameHeaderCrypt
from game.command_handler import GameCommandHandler
from game.packets import (
    AuthResponseCodes,
    ChatNotify,
    Classes,
    GamePackets,
    GamePacketsCataclysm,
    GamePacketsMoP,
    GamePacketsTBC,
    GamePacketsWotLK,
    GuildEvents,
    Races,
)
from game.resources import GameResources

logger = logging.getLogger(__name__)

ADDON_INFO_VANILLA = bytes([  # noqa: E501
    0x56, 0x01, 0x00, 0x00, 0x78, 0x9C, 0x75, 0xCC, 0xBD, 0x0E, 0xC2, 0x30, 0x0C, 0x04, 0xE0, 0xF2,
    0x1E, 0xBC, 0x0C, 0x61, 0x40, 0x95, 0xC8, 0x42, 0xC3, 0x8C, 0x4C, 0xE2, 0x22, 0x0B, 0xC7, 0xA9,
    0x8C, 0xCB, 0x4F, 0x9F, 0x1E, 0x16, 0x24, 0x06, 0x73, 0xEB, 0x77, 0x77, 0x81, 0x69, 0x59, 0x40,
    0xCB, 0x69, 0x33, 0x67, 0xA3, 0x26, 0xC7, 0xBE, 0x5B, 0xD5, 0xC7, 0x7A, 0xDF, 0x7D, 0x12, 0xBE,
    0x16, 0xC0, 0x8C, 0x71, 0x24, 0xE4, 0x12, 0x49, 0xA8, 0xC2, 0xE4, 0x95, 0x48, 0x0A, 0xC9, 0xC5,
    0x3D, 0xD8, 0xB6, 0x7A, 0x06, 0x4B, 0xF8, 0x34, 0x0F, 0x15, 0x46, 0x73, 0x67, 0xBB, 0x38, 0xCC,
    0x7A, 0xC7, 0x97, 0x8B, 0xBD, 0xDC, 0x26, 0xCC, 0xFE, 0x30, 0x42, 0xD6, 0xE6, 0xCA, 0x01, 0xA8,
    0xB8, 0x90, 0x80, 0x51, 0xFC, 0xB7, 0xA4, 0x50, 0x70, 0xB8, 0x12, 0xF3, 0x3F, 0x26, 0x41, 0xFD,
    0xB5, 0x37, 0x90, 0x19, 0x66, 0x8F,
])

ADDON_INFO_TBC = bytes([
    0xD0, 0x01, 0x00, 0x00, 0x78, 0x9C, 0x75, 0xCF, 0x3B, 0x0E, 0xC2, 0x30, 0x0C, 0x80, 0xE1, 0x72,
    0x0F, 0x2E, 0x43, 0x18, 0x50, 0xA5, 0x66, 0xA1, 0x65, 0x46, 0x26, 0x71, 0x2B, 0xAB, 0x89, 0x53,
    0x19, 0x87, 0x47, 0x4F, 0x0F, 0x0B, 0x62, 0x71, 0xBD, 0x7E, 0xD6, 0x6F, 0xD9, 0x25, 0x5A, 0x57,
    0x90, 0x78, 0x3D, 0xD4, 0xA0, 0x54, 0xF8, 0xD2, 0x36, 0xBB, 0xFC, 0xDC, 0x77, 0xCD, 0x77, 0xDC,
    0xCF, 0x1C, 0xA8, 0x26, 0x1C, 0x09, 0x53, 0xF4, 0xC4, 0x94, 0x61, 0xB1, 0x96, 0x88, 0x23, 0xF1,
    0x64, 0x06, 0x8E, 0x25, 0xDF, 0x40, 0xBB, 0x32, 0x6D, 0xDA, 0x80, 0x2F, 0xB5, 0x50, 0x60, 0x54,
    0x33, 0x79, 0xF2, 0x7D, 0x95, 0x07, 0xBE, 0x6D, 0xAC, 0x94, 0xA2, 0x03, 0x9E, 0x4D, 0x6D, 0xF9,
    0xBE, 0x60, 0xB0, 0xB3, 0xAD, 0x62, 0xEE, 0x4B, 0x98, 0x51, 0xB7, 0x7E, 0xF1, 0x10, 0xA4, 0x98,
    0x72, 0x06, 0x8A, 0x26, 0x0C, 0x90, 0x90, 0xED, 0x7B, 0x83, 0x40, 0xC4, 0x7E, 0xA6, 0x94, 0xB6,
    0x98, 0x18, 0xC5, 0x36, 0xCA, 0xE8, 0x81, 0x61, 0x42, 0xF9, 0xEB, 0x07, 0x63, 0xAB, 0x8B, 0xEC,
])

ADDON_INFO_WOTLK = bytes([
    0x9E, 0x02, 0x00, 0x00, 0x78, 0x9C, 0x75, 0xD2, 0xC1, 0x6A, 0xC3, 0x30, 0x0C, 0x86, 0x71, 0xEF,
    0x29, 0x76, 0xE9, 0x9B, 0xEC, 0xB4, 0xB4, 0x50, 0xC2, 0xEA, 0xCB, 0xE2, 0x9E, 0x8B, 0x62, 0x7F,
    0x4B, 0x44, 0x6C, 0x39, 0x38, 0x4E, 0xB7, 0xF6, 0x3D, 0xFA, 0xBE, 0x65, 0xB7, 0x0D, 0x94, 0xF3,
    0x4F, 0x48, 0xF0, 0x47, 0xAF, 0xC6, 0x98, 0x26, 0xF2, 0xFD, 0x4E, 0x25, 0x5C, 0xDE, 0xFD, 0xC8,
    0xB8, 0x22, 0x41, 0xEA, 0xB9, 0x35, 0x2F, 0xE9, 0x7B, 0x77, 0x32, 0xFF, 0xBC, 0x40, 0x48, 0x97,
    0xD5, 0x57, 0xCE, 0xA2, 0x5A, 0x43, 0xA5, 0x47, 0x59, 0xC6, 0x3C, 0x6F, 0x70, 0xAD, 0x11, 0x5F,
    0x8C, 0x18, 0x2C, 0x0B, 0x27, 0x9A, 0xB5, 0x21, 0x96, 0xC0, 0x32, 0xA8, 0x0B, 0xF6, 0x14, 0x21,
    0x81, 0x8A, 0x46, 0x39, 0xF5, 0x54, 0x4F, 0x79, 0xD8, 0x34, 0x87, 0x9F, 0xAA, 0xE0, 0x01, 0xFD,
    0x3A, 0xB8, 0x9C, 0xE3, 0xA2, 0xE0, 0xD1, 0xEE, 0x47, 0xD2, 0x0B, 0x1D, 0x6D, 0xB7, 0x96, 0x2B,
    0x6E, 0x3A, 0xC6, 0xDB, 0x3C, 0xEA, 0xB2, 0x72, 0x0C, 0x0D, 0xC9, 0xA4, 0x6A, 0x2B, 0xCB, 0x0C,
    0xAF, 0x1F, 0x6C, 0x2B, 0x52, 0x97, 0xFD, 0x84, 0xBA, 0x95, 0xC7, 0x92, 0x2F, 0x59, 0x95, 0x4F,
    0xE2, 0xA0, 0x82, 0xFB, 0x2D, 0xAA, 0xDF, 0x73, 0x9C, 0x60, 0x49, 0x68, 0x80, 0xD6, 0xDB, 0xE5,
    0x09, 0xFA, 0x13, 0xB8, 0x42, 0x01, 0xDD, 0xC4, 0x31, 0x6E, 0x31, 0x0B, 0xCA, 0x5F, 0x7B, 0x7B,
    0x1C, 0x3E, 0x9E, 0xE1, 0x93, 0xC8, 0x8D,
])

ADDON_INFO_CATA = bytes([
    0xE0, 0x03, 0x00, 0x00, 0x78, 0x9C, 0x75, 0x93, 0x61, 0x6E, 0xC3, 0x20, 0x0C, 0x85, 0xBF, 0x73,
    0x8A, 0x5D, 0x7A, 0x4F, 0xB4, 0x2A, 0x51, 0x57, 0x4D, 0xAB, 0xD4, 0xFE, 0x77, 0x32, 0xA9, 0x8B,
    0x22, 0x4C, 0x4A, 0x18, 0x4D, 0xBB, 0xDB, 0x2F, 0x41, 0x93, 0xA6, 0x26, 0xCA, 0xF0, 0x79, 0xEF,
    0x19, 0xBF, 0x3C, 0x3F, 0x39, 0xC8, 0x45, 0xF4, 0xF2, 0x3B, 0x88, 0x7E, 0x68, 0x6C, 0xCF, 0xF0,
    0x84, 0x03, 0xFA, 0x70, 0x3E, 0x64, 0x0F, 0xC3, 0xC7, 0xE3, 0x31, 0xFB, 0xC3, 0xC5, 0x74, 0x80,
    0xEC, 0xB8, 0x3D, 0x27, 0x38, 0x7A, 0xD0, 0xC9, 0x6C, 0xD2, 0xE2, 0xD7, 0x22, 0xDB, 0x8A, 0x34,
    0xC8, 0xA9, 0xE3, 0x31, 0x81, 0x43, 0x70, 0x78, 0x25, 0x74, 0xB6, 0x22, 0x8F, 0x00, 0x17, 0x35,
    0x11, 0x79, 0x4C, 0xBE, 0xD5, 0x1B, 0x38, 0x30, 0x6D, 0x80, 0xF4, 0xA8, 0x4F, 0xB5, 0x03, 0x87,
    0xC6, 0x82, 0x68, 0xA8, 0x03, 0x17, 0x61, 0x8B, 0x93, 0x5E, 0xE9, 0x28, 0x5A, 0x55, 0xC1, 0x82,
    0xC6, 0x80, 0x10, 0x34, 0x0E, 0x27, 0x4D, 0xC6, 0x43, 0x03, 0xE1, 0xC8, 0x6D, 0x92, 0xD5, 0xF8,
    0x19, 0x74, 0x38, 0x82, 0x09, 0x27, 0x20, 0xBB, 0x17, 0x18, 0xF4, 0xE6, 0xE7, 0x7D, 0x29, 0x7C,
    0x25, 0xFD, 0xE8, 0x67, 0x6C, 0xE6, 0xB6, 0x66, 0x76, 0x1A, 0x7C, 0xF1, 0x86, 0x67, 0x1F, 0x50,
    0x5E, 0x79, 0x16, 0x0F, 0x4E, 0x91, 0xE4, 0xEE, 0x36, 0x76, 0xEA, 0xEC, 0x79, 0x11, 0xCD, 0xD1,
    0x0D, 0xCD, 0x8B, 0x6A, 0x96, 0x05, 0xF5, 0x8C, 0xE4, 0x33, 0x39, 0xBB, 0x05, 0xDF, 0xA7, 0x69,
    0xC7, 0x3E, 0x08, 0xBB, 0xB4, 0x40, 0x25, 0x07, 0x3F, 0x8D, 0x68, 0xF4, 0x1B, 0x1D, 0x02, 0x0E,
    0x1B, 0x17, 0x27, 0x85, 0x64, 0x0A, 0x57, 0x49, 0xC5, 0x26, 0x86, 0x24, 0x95, 0xA3, 0x55, 0x71,
    0x1E, 0x5B, 0x01, 0x8B, 0x2A, 0x3F, 0x32, 0xF7, 0xB1, 0x76, 0xCF, 0x92, 0xBE, 0x64, 0x01, 0x46,
    0x58, 0x27, 0xBC, 0x60, 0x09, 0x56, 0x21, 0x25, 0x86, 0x9F, 0x1D, 0x50, 0xEB, 0x22, 0x4D, 0x3F,
    0xDF, 0x9A, 0x1C, 0xB5, 0xEA, 0x84, 0x57, 0x96, 0x36, 0x35, 0x69, 0xBD, 0x6E, 0x84, 0xEE, 0x64,
    0x4D, 0x03, 0x16, 0xE0, 0xA1, 0x45, 0x6D, 0x5F, 0x6A, 0xEE, 0x51, 0xB7, 0xB7, 0x5E, 0x6D, 0xAB,
    0x7A, 0x72, 0xFA, 0xB3, 0x46, 0x4C, 0x1E, 0x45, 0x65, 0x17, 0x26, 0x5B, 0x05, 0x96, 0x78, 0xA6,
    0xEE, 0xC0, 0xA5, 0x54, 0xFF, 0xBF, 0xCD, 0x38, 0x85, 0x5D, 0xC7, 0x64, 0x50, 0xA1, 0x6B, 0x47,
    0xBD, 0xDF, 0x66, 0x0E, 0xDD, 0xEF, 0xE2, 0xFF, 0x55, 0x7C, 0xC5, 0xEF, 0x1B, 0x7A, 0xEB, 0x96,
    0xC4,
])

ADDON_INFO_MOP = bytes([
    0x30, 0x05, 0x00, 0x00, 0x78, 0x9C, 0x75, 0x93, 0x61, 0x6E, 0x83, 0x30, 0x0C, 0x85, 0xD9, 0x3D,
    0x76, 0x84, 0x5D, 0xA2, 0xED, 0x56, 0xD4, 0xA9, 0x48, 0xAC, 0xD0, 0xFE, 0x9D, 0x4C, 0xE2, 0x82,
    0x45, 0x88, 0x91, 0x09, 0x6C, 0xED, 0xE5, 0xB7, 0xA0, 0x49, 0xD3, 0x26, 0x39, 0xFC, 0xE4, 0x7B,
    0x76, 0xE2, 0x97, 0xE7, 0xA7, 0x2C, 0xCB, 0xB6, 0x8E, 0xEE, 0x77, 0x10, 0xFB, 0xBE, 0x31, 0x1D,
    0xE1, 0x82, 0x03, 0xFA, 0x70, 0x3E, 0x64, 0x0F, 0xC3, 0xC7, 0xE3, 0x31, 0xFB, 0xC7, 0xC5, 0x74,
    0x80, 0xEC, 0xB8, 0xBD, 0x25, 0x38, 0x7A, 0xD0, 0xC9, 0x6C, 0x02, 0xB1, 0x57, 0xD9, 0x16, 0xA4,
    0x41, 0x99, 0x3A, 0x1E, 0x13, 0x38, 0x04, 0x87, 0x57, 0x42, 0x67, 0x0B, 0xF2, 0x34, 0xC0, 0xA8,
    0x89, 0xC8, 0x5B, 0xF2, 0xAD, 0xDE, 0xC0, 0x81, 0xE9, 0x0B, 0x90, 0x1E, 0xF5, 0xA9, 0x76, 0xE0,
    0xD0, 0x5B, 0x10, 0x0D, 0x75, 0xE0, 0x22, 0x6C, 0x71, 0xD2, 0x2B, 0x1D, 0x45, 0xAB, 0x2A, 0x58,
    0xD0, 0x5E, 0x40, 0x08, 0x1A, 0x87, 0x93, 0x26, 0xE3, 0xA1, 0x81, 0x70, 0xE4, 0x36, 0xC9, 0x6A,
    0xFC, 0x0C, 0x3A, 0x1C, 0xC1, 0x84, 0x13, 0x90, 0xDD, 0x0B, 0x0C, 0x7A, 0xF3, 0xF3, 0xBE, 0x14,
    0xBE, 0x92, 0x7E, 0xF4, 0x33, 0x36, 0x73, 0x5B, 0x33, 0x3B, 0x0D, 0xBE, 0x78, 0xC3, 0xB3, 0x0F,
    0x28, 0xAF, 0x3C, 0x8B, 0x07, 0xA7, 0x48, 0x72, 0x77, 0x1B, 0x3B, 0x75, 0xF6, 0xBC, 0x88, 0xE6,
    0xE8, 0x86, 0xE6, 0x45, 0x35, 0xCB, 0x82, 0x7A, 0x46, 0xF2, 0x99, 0x9C, 0xDD, 0x82, 0xEF, 0xD3,
    0x74, 0xC7, 0x3E, 0x08, 0xBB, 0xB4, 0x40, 0x25, 0x07, 0x3F, 0x8D, 0x68, 0xF4, 0x1B, 0x1D, 0x02,
    0x0E, 0x1B, 0x17, 0x27, 0x85, 0x64, 0x0A, 0x57, 0x49, 0xC5, 0x26, 0x86, 0x24, 0x95, 0xA3, 0x55,
    0x71, 0x1E, 0x5B, 0x01, 0x8B, 0x2A, 0x3F, 0x32, 0xF7, 0xB1, 0x76, 0xCF, 0x92, 0xBE, 0x64, 0x01,
    0x46, 0x58, 0x27, 0xBC, 0x60, 0x09, 0x56, 0x21, 0x25, 0x86, 0x9F, 0x1D, 0x50, 0xEB, 0x22, 0x4D,
    0x3F, 0xDF, 0x9A, 0x1C, 0xB5, 0xEA, 0x84, 0x57, 0x96, 0x36, 0x35, 0x69, 0xBD, 0x6E, 0x84, 0xEE,
    0x64, 0x4D, 0x03, 0x16, 0xE0, 0xA1, 0x45, 0x6D, 0x5F, 0x6A, 0xEE, 0x51, 0xB7, 0xB7, 0x5E, 0x6D,
    0xAB, 0x7A, 0x72, 0xFA, 0xB3, 0x46, 0x4C, 0x1E, 0x45, 0x65, 0x17, 0x26, 0x5B, 0x05, 0x96, 0x78,
    0xA6, 0xEE, 0xC0, 0xA5, 0x54, 0xFF, 0xBF, 0xCD, 0x38, 0x85, 0x5D, 0xC7, 0x64, 0x50, 0xA1, 0x6B,
    0x47, 0xBD, 0xDF, 0x66, 0x0E, 0xDD, 0xEF, 0xE2, 0xFF, 0x55, 0x7C, 0xC5, 0xEF, 0x1B, 0xE8, 0xAD,
    0x5B, 0x82,
])

_ADDON_INFO: dict[WowExpansion, bytes] = {
    WowExpansion.VANILLA: ADDON_INFO_VANILLA,
    WowExpansion.TBC: ADDON_INFO_TBC,
    WowExpansion.WOTLK: ADDON_INFO_WOTLK,
    WowExpansion.CATACLYSM: ADDON_INFO_CATA,
    WowExpansion.MOP: ADDON_INFO_MOP,
}


class Player:
    """Player cache entry."""

    def __init__(self, name: str, char_class: int) -> None:
        self.name = name
        self.char_class = char_class


class GuildMember:
    """Guild roster entry."""

    def __init__(self, name: str, is_online: bool, char_class: int,
                 level: int, zone_id: int, last_logoff: float) -> None:
        self.name = name
        self.is_online = is_online
        self.char_class = char_class
        self.level = level
        self.zone_id = zone_id
        self.last_logoff = last_logoff


class ChatMessage:
    """Parsed chat message from the game server."""

    def __init__(self, guid: int, tp: int, message: str,
                 channel: str | None = None) -> None:
        self.guid = guid
        self.tp = tp
        self.message = message
        self.channel = channel


class NameQueryMessage:
    """Parsed name query response."""

    def __init__(self, guid: int, name: str, char_class: int) -> None:
        self.guid = guid
        self.name = name
        self.char_class = char_class


class CharEnumMessage:
    """Parsed character enum entry."""

    def __init__(self, name: str, guid: int, race: int, guild_guid: int) -> None:
        self.name = name
        self.guid = guid
        self.race = race
        self.guild_guid = guild_guid


class GuildInfo:
    """Guild name and rank mapping."""

    def __init__(self, name: str, ranks: dict[int, str]) -> None:
        self.name = name
        self.ranks = ranks


class AuthChallengeMessage:
    """Parsed auth challenge with session key and response bytes."""

    def __init__(self, session_key: bytes, response: bytes) -> None:
        self.session_key = session_key
        self.response = response


def unpack_guid(data: bytes, pos: int = 0) -> tuple[int, int]:
    """Unpack a WoW packed GUID (byte-masked). Returns (guid, new_pos)."""
    guid = 0
    mask_bits = data[pos] if pos < len(data) else 0
    pos += 1
    for i in range(8):
        if mask_bits & (1 << i):
            guid |= (data[pos] & 0xFF) << (i * 8)
            pos += 1
    return guid, pos


class GamePacketHandler(GamePackets, GameCommandHandler):
    """Base Vanilla game packet handler."""

    def __init__(self, realm_id: int, realm_name: str,
                 session_key: bytes,
                 game_event_callback: Any,
                 send_callback: Callable[[int, bytes], None]) -> None:
        self.realm_id = realm_id
        self.realm_name = realm_name
        self.session_key = session_key
        self.game_event_callback = game_event_callback
        self.send = send_callback
        self.addon_info = _ADDON_INFO.get(global_state.expansion, ADDON_INFO_VANILLA)
        self.connect_time = time.time() * 1000

        self.self_character_id: int = 0
        self.language_id: int = 7
        self.in_world = False
        self.guild_guid: int = 0
        self.guild_info: GuildInfo | None = None
        self.guild_motd: str | None = None
        self.player_roster: dict[int, Player] = {}
        self.guild_roster: dict[int, GuildMember] = {}
        self.last_requested_guild_roster: float = 0.0
        self.received_char_enum = False
        self._queued_messages: dict[int, list[ChatMessage]] = {}
        self._ping_id = 0

    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        """
        Route an incoming packet to the appropriate handler.

        Args:
            msg: Decoded packet.

        Returns:
            List of (opcode, payload) for outgoing packets.
        """
        out: list[tuple[int, bytes]] = []
        mid = msg.id

        if mid == self.SMSG_AUTH_CHALLENGE:
            self._handle_auth_challenge(msg, out)
        elif mid == self.SMSG_AUTH_RESPONSE:
            self._handle_auth_response(msg, out)
        elif mid == self.SMSG_NAME_QUERY:
            self._handle_name_query(msg)
        elif mid == self.SMSG_CHAR_ENUM:
            self._handle_char_enum(msg, out)
        elif mid == self.SMSG_LOGIN_VERIFY_WORLD:
            self._handle_login_verify_world(out)
        elif mid == self.SMSG_GUILD_QUERY:
            self._handle_guild_query(msg)
        elif mid == self.SMSG_GUILD_EVENT:
            self._handle_guild_event(msg)
        elif mid == self.SMSG_GUILD_ROSTER:
            self._handle_guild_roster(msg)
        elif mid == self.SMSG_MESSAGECHAT or mid == getattr(self, 'SMSG_GM_MESSAGECHAT', -1):
            self._handle_message_chat(msg)
        elif mid == self.SMSG_CHANNEL_NOTIFY:
            self._handle_channel_notify(msg)
        elif mid == self.SMSG_NOTIFICATION:
            self._handle_notification(msg)
        elif mid == self.SMSG_WHO:
            self._handle_who(msg)
        elif mid == self.SMSG_SERVER_MESSAGE:
            self._handle_server_message(msg)
        elif mid == self.SMSG_INVALIDATE_PLAYER:
            self._handle_invalidate_player(msg)
        elif mid == self.SMSG_WARDEN_DATA:
            self._handle_warden_data(msg, out)

        return out

    def on_connected(self) -> None:
        """Called when the TCP connection is established."""
        logger.info("Connected to game server.")

    def disconnect(self) -> None:
        """Cleanup on disconnection."""
        self.in_world = False
        self.game_event_callback.disconnected()

    def send_message_to_wow(self, tp: int, message: str,
                            target: str | None = None) -> None:
        """Send a chat message (implementation of GameCommandHandler)."""
        payload = self._build_chat_message(tp, message.encode("utf-8"),
                                           target.encode("utf-8") if target else None)
        self.send(self.CMSG_MESSAGECHAT, payload)

    def send_notification(self, message: str) -> None:
        """Send a guild notification."""
        self.send_message_to_wow(ChatEvents.CHAT_MSG_GUILD, message)

    def handle_who(self, arguments: str | None) -> str | None:
        """Handle WHO command."""
        if arguments:
            payload = self._build_who_message(arguments)
            self.send(self.CMSG_WHO, payload)
            return None

        return self._build_guildies_online()

    def handle_gmotd(self) -> str | None:
        """Return the current guild MOTD."""
        return self.guild_motd

    def send_name_query(self, guid: int) -> None:
        """Request a player name by GUID."""
        pw = PacketWriter()
        pw.write_long_le(guid)
        self.send(self.CMSG_NAME_QUERY, pw.build())

    def send_logout(self) -> bytes | None:
        """Request logout."""
        return struct.pack("<H", self.CMSG_LOGOUT_REQUEST)

    # -- Private handlers --

    def _handle_auth_challenge(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        auth_msg = self._parse_auth_challenge(msg)
        global_state.game_crypt = GameHeaderCrypt()
        global_state.game_crypt.init(auth_msg.session_key)
        out.append((self.CMSG_AUTH_CHALLENGE, auth_msg.response))

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_int_le(global_state.game_build)
        pw.write_int_le(0)
        pw.write_bytes(account)
        pw.write_byte(0)
        pw.write_int(client_seed)

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        pw.write_bytes(md.digest())

        pw.write_bytes(self.addon_info)
        return AuthChallengeMessage(self.session_key, pw.build())

    def _handle_auth_response(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        code = self._parse_auth_response(msg)
        if code == AuthResponseCodes.AUTH_OK:
            logger.info("Successfully logged in!")
            self._send_char_enum(out)
        elif code == AuthResponseCodes.AUTH_WAIT_QUEUE:
            if msg.remaining() >= 14:
                msg.skip(10)
            position = msg.read_int_le()
            logger.info(f"Queue enabled. Position: {position}")
        else:
            logger.error(AuthResponseCodes.get_message(code))
            self.game_event_callback.error()

    def _parse_auth_response(self, msg: Packet) -> int:
        return msg.read_byte()

    def _send_char_enum(self, out: list[tuple[int, bytes]]) -> None:
        if not self.received_char_enum:
            out.append((self.CMSG_CHAR_ENUM, b""))

    def _handle_char_enum(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        if self.received_char_enum:
            if self.in_world:
                return
            else:
                logger.info("Received character enum more than once. Trying again...")
        self.received_char_enum = True
        character = self._parse_char_enum(msg)
        if character is None:
            logger.error(f"Character {global_state.config.wow.character} not found!")
        else:
            logger.info(f"Logging in with character {character.name}")
            self.self_character_id = character.guid
            self.language_id = Races.get_language(character.race)
            self.guild_guid = character.guild_guid
            payload = self._write_player_login()
            out.append((self.CMSG_PLAYER_LOGIN, payload))

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        characters_num = msg.read_byte()
        for _ in range(characters_num):
            guid = msg.read_long_le()
            name = msg.read_string()
            race = msg.read_byte()
            msg.skip(1)  # class
            msg.skip(1)  # gender
            msg.skip(1)  # skin
            msg.skip(1)  # face
            msg.skip(1)  # hair style
            msg.skip(1)  # hair color
            msg.skip(1)  # facial hair
            msg.skip(1)  # level
            msg.skip(4)  # zone
            msg.skip(4)  # map
            msg.skip(12)  # x + y + z
            guild_guid = msg.read_int_le()
            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)
            msg.skip(4)  # character flags
            msg.skip(1)  # first login
            msg.skip(12)  # pet info
            msg.skip(19 * 5)  # equipment info
            msg.skip(5)  # first bag display info
        return None

    def _write_player_login(self) -> bytes:
        pw = PacketWriter()
        pw.write_long_le(self.self_character_id)
        return pw.build()

    def _handle_login_verify_world(self, out: list[tuple[int, bytes]]) -> None:
        if self.in_world:
            return
        logger.info("Successfully joined the world!")
        self.in_world = True
        self.game_event_callback.connected()
        self._run_keep_alive(out)
        self._run_guild_roster_executor(out)
        if self.guild_guid != 0:
            self._query_guild_name(out)
            self._update_guild_roster(out)
        self._join_channels(out)

    def _run_keep_alive(self, out: list[tuple[int, bytes]]) -> None:
        pass  # Vanilla has no keep alive

    def _run_guild_roster_executor(self, out: list[tuple[int, bytes]]) -> None:
        self.last_requested_guild_roster = time.time() * 1000
        out.append((self.CMSG_GUILD_ROSTER, b""))

    def _query_guild_name(self, out: list[tuple[int, bytes]]) -> None:
        pw = PacketWriter()
        pw.write_int_le(self.guild_guid & 0xFFFFFFFF)
        out.append((self.CMSG_GUILD_QUERY, pw.build()))

    def _update_guild_roster(self, out: list[tuple[int, bytes]]) -> None:
        self.last_requested_guild_roster = time.time() * 1000
        out.append((self.CMSG_GUILD_ROSTER, b""))

    def _join_channels(self, out: list[tuple[int, bytes]]) -> None:
        for channel_cfg in global_state.config.channels:
            channel_name = channel_cfg.wow.channel
            if channel_name is None:
                continue
            channel_id = channel_cfg.wow.id or 0
            logger.info(f"Joining channel {channel_name}")
            payload = self._write_join_channel(channel_id, channel_name.encode("utf-8"))
            out.append((self.CMSG_JOIN_CHANNEL, payload))

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        pw = PacketWriter()
        pw.write_bytes(channel_name_bytes)
        pw.write_byte(0)
        pw.write_byte(0)
        return pw.build()

    def _handle_guild_query(self, msg: Packet) -> None:
        self.guild_info = self._parse_guild_query(msg)

    def _parse_guild_query(self, msg: Packet) -> GuildInfo:
        msg.skip(4)
        name = msg.read_string()
        ranks: dict[int, str] = {}
        for i in range(10):
            rank_name = msg.read_string()
            if rank_name:
                ranks[i] = rank_name
        return GuildInfo(name, ranks)

    def _handle_guild_event(self, msg: Packet) -> None:
        event = msg.read_byte()
        num_strings = msg.read_byte()
        messages = [msg.read_string() for _ in range(num_strings)]
        self._handle_guild_event_common(event, messages)

    def _handle_guild_event_common(self, event: int, messages: list[str]) -> None:
        ge = GuildEvents(global_state.expansion != WowExpansion.VANILLA)
        if all(m.strip() == "" for m in messages):
            return
        if event != ge.GE_MOTD and global_state.config.wow.character.lower() == messages[0].lower():
            return

        event_key_map = {
            ge.GE_PROMOTED: "promoted",
            ge.GE_DEMOTED: "demoted",
            ge.GE_MOTD: "motd",
            ge.GE_JOINED: "joined",
            ge.GE_LEFT: "left",
            ge.GE_REMOVED: "removed",
            ge.GE_SIGNED_ON: "online",
            ge.GE_SIGNED_OFF: "offline",
        }
        event_key = event_key_map.get(event)
        if event_key is None:
            return
        self.game_event_callback.guild_event(event_key, messages)

    def _handle_guild_roster(self, msg: Packet) -> None:
        self.guild_roster.clear()
        self.guild_roster.update(self._parse_guild_roster(msg))

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        count = msg.read_int_le()
        self.guild_motd = msg.read_string()
        msg.read_string()  # ginfo
        ranks_count = msg.read_int_le()
        for _ in range(ranks_count):
            msg.skip(4)
        roster: dict[int, GuildMember] = {}
        for _ in range(count):
            guid = msg.read_long_le()
            is_online = msg.read_boolean()
            name = msg.read_string()
            msg.skip(4)  # guild rank
            level = msg.read_byte()
            char_class = msg.read_byte()
            zone_id = msg.read_int_le()
            last_logoff = msg.read_float_le() if not is_online else 0
            msg.skip_string()
            msg.skip_string()
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)
        return roster

    def _handle_message_chat(self, msg: Packet) -> None:
        logger.debug(f"RECV CHAT: {bytes(msg.data[msg._pos:]).hex()}")
        chat_msg = self._parse_chat_message(msg)
        if chat_msg is not None:
            self._send_chat_message(chat_msg)

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        tp = msg.read_byte()
        lang = msg.read_int_le()
        if lang == -1:
            return None

        channel_name: str | None = None
        if tp == ChatEvents.CHAT_MSG_CHANNEL:
            channel_name = msg.read_string()
            msg.skip(4)

        if not self._check_channel_enabled(tp, channel_name):
            return None

        guid = msg.read_long_le()
        if tp != ChatEvents.CHAT_MSG_SYSTEM and guid == self.self_character_id:
            return None

        if tp in (ChatEvents.CHAT_MSG_SAY, ChatEvents.CHAT_MSG_YELL):
            msg.skip(8)  # target guid

        txt_len = msg.read_int_le()
        txt = msg.slice(txt_len - 1).decode("utf-8", errors="replace")
        msg.skip(1)  # null terminator
        return ChatMessage(guid, tp, txt, channel_name)

    def _check_channel_enabled(self, tp: int, channel_name: str | None) -> bool:
        return (tp, channel_name.lower() if channel_name else None) in global_state.wow_to_discord

    def _send_chat_message(self, chat_msg: ChatMessage) -> None:
        if chat_msg.guid == 0:
            self.game_event_callback.chat_message(None, chat_msg.message,
                                                  chat_msg.tp, chat_msg.channel)
        elif chat_msg.guid in self.player_roster:
            player = self.player_roster[chat_msg.guid]
            self.game_event_callback.chat_message(player.name, chat_msg.message,
                                                  chat_msg.tp, chat_msg.channel)
        else:
            if chat_msg.guid not in self._queued_messages:
                self._queued_messages[chat_msg.guid] = []
            self._queued_messages[chat_msg.guid].append(chat_msg)
            self.send_name_query(chat_msg.guid)

    def _handle_name_query(self, msg: Packet) -> None:
        nq = self._parse_name_query(msg)
        messages = self._queued_messages.pop(nq.guid, [])
        for chat_msg in messages:
            self.game_event_callback.chat_message(nq.name, chat_msg.message,
                                                  chat_msg.tp, chat_msg.channel)
        self.player_roster[nq.guid] = Player(nq.name, nq.char_class)

    def _parse_name_query(self, msg: Packet) -> NameQueryMessage:
        guid = msg.read_long_le()
        name = msg.read_string()
        msg.skip_string()  # realm name
        msg.skip(4)  # race
        msg.skip(4)  # gender
        char_class = msg.read_int_le() & 0xFF
        return NameQueryMessage(guid, name, char_class)

    def _handle_channel_notify(self, msg: Packet) -> None:
        cid = msg.read_byte()
        channel_name = msg.read_string()
        messages = {
            ChatNotify.CHAT_YOU_JOINED_NOTICE: f"Joined Channel: [{channel_name}]",
            ChatNotify.CHAT_WRONG_PASSWORD_NOTICE: f"Wrong password for {channel_name}.",
            ChatNotify.CHAT_MUTED_NOTICE: f"[{channel_name}] You do not have permission to speak.",
            ChatNotify.CHAT_BANNED_NOTICE: f"[{channel_name}] You are banned from that channel.",
            ChatNotify.CHAT_WRONG_FACTION_NOTICE: f"Wrong alliance for {channel_name}.",
            ChatNotify.CHAT_INVALID_NAME_NOTICE: "Invalid channel name",
            ChatNotify.CHAT_THROTTLED_NOTICE: f"[{channel_name}] The number of messages... is limited, please wait.",
            ChatNotify.CHAT_NOT_IN_AREA_NOTICE: f"[{channel_name}] You are not in the correct area.",
            ChatNotify.CHAT_NOT_IN_LFG_NOTICE: f"[{channel_name}] You must be queued in looking for group.",
        }
        err_msg = messages.get(cid)
        if err_msg:
            if cid == ChatNotify.CHAT_YOU_JOINED_NOTICE:
                logger.info(err_msg)
            else:
                logger.error(err_msg)

    def _handle_notification(self, msg: Packet) -> None:
        logger.info(f"Notification: {msg.read_string()}")

    def _handle_who(self, msg: Packet) -> None:
        pass  # WHO response handling is in the command module

    def _handle_server_message(self, msg: Packet) -> None:
        tp = msg.read_int_le()
        txt = msg.read_string()
        messages = {
            0x01: f"Shutdown in {txt}",
            0x02: f"Restart in {txt}",
            0x04: "Shutdown cancelled.",
            0x05: "Restart cancelled.",
        }
        message = messages.get(tp, txt)
        self.game_event_callback.chat_message(None, message,
                                              ChatEvents.CHAT_MSG_SYSTEM, None)

    def _handle_invalidate_player(self, msg: Packet) -> None:
        guid = msg.read_long_le()
        self.player_roster.pop(guid, None)

    def _handle_warden_data(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        if global_state.config.wow.platform.value == "Windows":
            logger.error("WARDEN ON WINDOWS IS NOT SUPPORTED!")
            return

    def _build_chat_message(self, tp: int, msg_bytes: bytes,
                            target_bytes: bytes | None) -> bytes:
        pw = PacketWriter()
        pw.write_int_le(tp)
        pw.write_int_le(self.language_id)
        if target_bytes:
            pw.write_bytes(target_bytes)
            pw.write_byte(0)
        pw.write_bytes(msg_bytes)
        pw.write_byte(0)
        return pw.build()

    def _build_who_message(self, name: str) -> bytes:
        pw = PacketWriter()
        pw.write_int_le(0)  # level min
        pw.write_int_le(100)  # level max
        pw.write_bytes(name.encode("utf-8"))
        pw.write_byte(0)
        pw.write_byte(0)
        pw.write_int_le(0xFFFFFFFF)  # race mask
        pw.write_int_le(0xFFFFFFFF)  # class mask
        pw.write_int_le(0)  # zones count
        pw.write_int_le(0)  # strings count
        return pw.build()

    def _build_guildies_online(self) -> str:
        character_name = global_state.config.wow.character.lower()
        online = [
            m for m in self.guild_roster.values()
            if m.is_online and m.name.lower() != character_name
        ]
        online.sort(key=lambda m: m.name.lower())

        if not online:
            return "Currently no guildies online."

        parts = [
            f"{m.name} ({m.level} {Classes.value_of(m.char_class)} in {GameResources.AREA.get(m.zone_id, 'Unknown Zone')})"
            for m in online
        ]
        count = len(online)
        guildie_word = "guildie" + ("s" if count != 1 else "")
        return f"Currently {count} {guildie_word} online:\n" + ", ".join(parts)

    def ping(self) -> bytes | None:
        """Build a ping packet."""
        latency = random.randint(90, 139)
        pw = PacketWriter()
        pw.write_int_le(self._ping_id)
        pw.write_int_le(latency)
        self._ping_id += 1
        return pw.build()


class GamePacketHandlerTBC(GamePacketHandler, GamePacketsTBC):
    """TBC-specific handler additions."""

    def _run_keep_alive(self, out: list[tuple[int, bytes]]) -> None:
        out.append((self.CMSG_KEEP_ALIVE, b""))

    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        mid = msg.id
        if mid == self.SMSG_GM_MESSAGECHAT:
            return self._handle_message_chat_inner(msg)
        if mid == self.SMSG_MOTD:
            if global_state.config.wow.enable_server_motd:
                out = self._parse_server_motd(msg)
                for cm in out:
                    self._send_chat_message(cm)
            return []
        if mid == self.SMSG_TIME_SYNC_REQ:
            return self._handle_time_sync_req(msg)
        return super().handle_packet(msg)

    def _handle_message_chat_inner(self, msg: Packet) -> list[tuple[int, bytes]]:
        logger.debug(f"RECV CHAT: {bytes(msg.data[msg._pos:]).hex()}")
        chat_msg = self._parse_chat_message(msg)
        if chat_msg is not None:
            self._send_chat_message(chat_msg)
        return []

    def _handle_time_sync_req(self, msg: Packet) -> list[tuple[int, bytes]]:
        counter = msg.read_int_le()
        uptime = int((time.time() * 1000) - self.connect_time)
        pw = PacketWriter()
        pw.write_int_le(counter)
        pw.write_int_le(uptime)
        return [(self.CMSG_TIME_SYNC_RESP, pw.build())]

    def _parse_server_motd(self, msg: Packet) -> list[ChatMessage]:
        line_count = msg.read_int_le()
        result = []
        for _ in range(line_count):
            message = msg.read_string()
            result.append(ChatMessage(0, ChatEvents.CHAT_MSG_SYSTEM, message, None))
        return result

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        characters_num = msg.read_byte()
        for _ in range(characters_num):
            guid = msg.read_long_le()
            name = msg.read_string()
            race = msg.read_byte()
            msg.skip(1)  # class
            msg.skip(1)  # gender
            msg.skip(1)  # skin
            msg.skip(1)  # face
            msg.skip(1)  # hair style
            msg.skip(1)  # hair color
            msg.skip(1)  # facial hair
            msg.skip(1)  # level
            msg.skip(4)  # zone
            msg.skip(4)  # map
            msg.skip(12)  # x + y + z
            guild_guid = msg.read_int_le()
            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)
            msg.skip(4)  # character flags
            msg.skip(1)  # first login
            msg.skip(12)  # pet info
            msg.skip(19 * 9)  # equipment info (TBC: 9 slots)
            msg.skip(9)  # bag display info
        return None

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        tp = msg.read_byte()
        lang = msg.read_int_le()
        if lang == -1:
            return None

        guid = msg.read_long_le()
        if tp != ChatEvents.CHAT_MSG_SYSTEM and guid == self.self_character_id:
            return None

        msg.skip(4)  # unkn
        channel_name: str | None = None
        if tp == ChatEvents.CHAT_MSG_CHANNEL:
            channel_name = msg.read_string()

        if not self._check_channel_enabled(tp, channel_name):
            return None

        msg.skip(8)  # skip guid again

        txt_len = msg.read_int_le()
        txt = msg.slice(txt_len - 1).decode("utf-8", errors="replace")
        msg.skip(1)  # null terminator
        return ChatMessage(guid, tp, txt, channel_name)

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        count = msg.read_int_le()
        self.guild_motd = msg.read_string()
        msg.read_string()  # ginfo
        ranks_count = msg.read_int_le()
        for _ in range(ranks_count):
            msg.skip(8 + 48)  # rank info + guild bank
        roster: dict[int, GuildMember] = {}
        for _ in range(count):
            guid = msg.read_long_le()
            is_online = msg.read_boolean()
            name = msg.read_string()
            msg.skip(4)  # guild rank
            level = msg.read_byte()
            char_class = msg.read_byte()
            msg.skip(1)  # TBC unkn
            zone_id = msg.read_int_le()
            last_logoff = msg.read_float_le() if not is_online else 0
            msg.skip_string()
            msg.skip_string()
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)
        return roster

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        pw = PacketWriter()
        pw.write_int_le(channel_id)
        pw.write_byte(0)
        pw.write_byte(1)
        pw.write_bytes(channel_name_bytes)
        pw.write_byte(0)
        pw.write_byte(0)
        return pw.build()


class GamePacketHandlerWotLK(GamePacketHandlerTBC, GamePacketsWotLK):
    """WotLK-specific handler additions."""

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        msg.skip(4)  # wotlk extra
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_int_le(global_state.game_build)
        pw.write_int_le(0)
        pw.write_bytes(account)
        pw.write_byte(0)
        pw.write_int(0)  # wotlk
        pw.write_int(client_seed)
        pw.write_int_le(0)  # wotlk
        pw.write_int_le(0)  # wotlk
        pw.write_int_le(self.realm_id)  # wotlk
        pw.write_long_le(3)  # wotlk

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        pw.write_bytes(md.digest())

        pw.write_bytes(self.addon_info)
        return AuthChallengeMessage(self.session_key, pw.build())

    def _parse_name_query(self, msg: Packet) -> NameQueryMessage:
        guid = 0
        mask = msg.read_byte()
        for i in range(8):
            if mask & (1 << i):
                guid |= (msg.read_byte() & 0xFF) << (i * 8)

        name_known = msg.read_byte()
        if name_known == 0:
            name = msg.read_string()
            msg.skip_string()  # realm name
            msg.skip(1)  # race
            msg.skip(1)  # gender
            char_class = msg.read_byte()
            return NameQueryMessage(guid, name, char_class)
        else:
            logger.error(f"RECV SMSG_NAME_QUERY - Name not known for guid {guid}")
            return NameQueryMessage(guid, "UNKNOWN", 0xFF)

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        characters_num = msg.read_byte()
        for _ in range(characters_num):
            guid = msg.read_long_le()
            name = msg.read_string()
            race = msg.read_byte()
            msg.skip(1)  # class
            msg.skip(1)  # gender
            msg.skip(1)  # skin
            msg.skip(1)  # face
            msg.skip(1)  # hair style
            msg.skip(1)  # hair color
            msg.skip(1)  # facial hair
            msg.skip(1)  # level
            msg.skip(4)  # zone
            msg.skip(4)  # map
            msg.skip(12)  # x + y + z
            guild_guid = msg.read_int_le()
            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)
            msg.skip(4)  # character flags
            msg.skip(4)  # character customize flags (WotLK)
            msg.skip(1)  # first login
            msg.skip(12)  # pet info
            msg.skip(19 * 9)  # equipment info
            msg.skip(4 * 9)  # bag display (WotLK: 4 bags)
        return None

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        tp = msg.read_byte()
        lang = msg.read_int_le()
        if lang == -1:
            return None
        guid = msg.read_long_le()
        if tp != ChatEvents.CHAT_MSG_SYSTEM and guid == self.self_character_id:
            return None
        msg.skip(4)

        if msg.id == self.SMSG_GM_MESSAGECHAT:
            msg.skip(4)
            msg.skip_string()

        channel_name: str | None = None
        if tp == ChatEvents.CHAT_MSG_CHANNEL:
            channel_name = msg.read_string()

        if tp != ChatEvents.CHAT_MSG_GUILD_ACHIEVEMENT and not self._check_channel_enabled(tp, channel_name):
            return None

        msg.skip(8)  # guid again
        txt_len = msg.read_int_le()
        txt = msg.slice(txt_len - 1).decode("utf-8", errors="replace")
        msg.skip(1)  # null terminator
        msg.skip(1)  # chat tag

        if tp == ChatEvents.CHAT_MSG_GUILD_ACHIEVEMENT:
            achievement_id = msg.read_int_le()
            self._handle_achievement_event(guid, achievement_id)
            return None

        return ChatMessage(guid, tp, txt, channel_name)

    def _handle_achievement_event(self, guid: int, achievement_id: int) -> None:
        member = self.guild_roster.get(guid)
        if member:
            self.game_event_callback.achievement(member.name, achievement_id)


class GamePacketHandlerCataclysm(GamePacketHandlerWotLK, GamePacketsCataclysm):
    """Cataclysm handler using bit-level (Cata+) message formats."""

    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        mid = msg.id
        if mid == self.WOW_CONNECTION:
            return [self._handle_wow_connection()]
        return super().handle_packet(msg)

    def _handle_wow_connection(self) -> tuple[int, bytes]:
        pw = PacketWriter()
        pw.write_bytes(b"RLD OF WARCRAFT CONNECTION - CLIENT TO SERVER")
        pw.write_byte(0)
        return (self.WOW_CONNECTION, pw.build())

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        msg.skip(32)  # 32 bytes random data
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        digest = md.digest()

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_zeros(9)
        pw.write_byte(digest[10])
        pw.write_byte(digest[18])
        pw.write_byte(digest[12])
        pw.write_byte(digest[5])
        pw.write_zeros(8)
        pw.write_byte(digest[15])
        pw.write_byte(digest[9])
        pw.write_byte(digest[19])
        pw.write_byte(digest[4])
        pw.write_byte(digest[7])
        pw.write_byte(digest[16])
        pw.write_byte(digest[3])
        pw.write_short_le(global_state.game_build)
        pw.write_byte(digest[8])
        pw.write_int_le(self.realm_id)
        pw.write_byte(0)
        pw.write_byte(digest[17])
        pw.write_byte(digest[6])
        pw.write_byte(digest[0])
        pw.write_byte(digest[1])
        pw.write_byte(digest[11])
        pw.write_int(client_seed)
        pw.write_byte(digest[2])
        pw.write_int_le(0)
        pw.write_byte(digest[14])
        pw.write_byte(digest[13])

        pw.write_int_le(len(self.addon_info))
        pw.write_bytes(self.addon_info)

        pw.write_byte(len(account) >> 5)
        pw.write_byte(len(account) << 3)
        pw.write_bytes(account)

        return AuthChallengeMessage(self.session_key, pw.build())

    def _parse_auth_response(self, msg: Packet) -> int:
        if msg.remaining() >= 17:
            msg.skip(16)
        elif msg.remaining() >= 2:
            msg.skip(1)
        else:
            return AuthResponseCodes.AUTH_FAILED
        return super()._parse_auth_response(msg)

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        msg.read_bits(24)  # unkn
        characters_num = msg.read_bits(17)

        guids = [[0] * 8 for _ in range(characters_num)]
        guild_guids = [[0] * 8 for _ in range(characters_num)]
        name_lengths = [0] * characters_num

        for i in range(characters_num):
            msg.read_bit_seq(guids[i], 3)
            msg.read_bit_seq(guild_guids[i], 1, 7, 2)
            name_lengths[i] = msg.read_bits(7)
            msg.read_bit_seq(guids[i], 4, 7)
            msg.read_bit_seq(guild_guids[i], 3)
            msg.read_bit_seq(guids[i], 5)
            msg.read_bit_seq(guild_guids[i], 6)
            msg.read_bit_seq(guids[i], 1)
            msg.read_bit_seq(guild_guids[i], 5, 4)
            msg.read_bit()  # is first login
            msg.read_bit_seq(guids[i], 0, 2, 6)
            msg.read_bit_seq(guild_guids[i], 0)

        for i in range(characters_num):
            msg.skip(1)  # char class
            msg.skip(207)  # inventory
            msg.skip(4)  # unkn
            msg.read_xor_byte_seq(guild_guids[i], 2)
            msg.skip(2)
            msg.read_xor_byte_seq(guild_guids[i], 3)
            msg.skip(9)
            msg.read_xor_byte_seq(guids[i], 4)
            msg.skip(4)  # map
            msg.read_xor_byte_seq(guild_guids[i], 5)
            msg.skip(4)
            msg.read_xor_byte_seq(guild_guids[i], 6)
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 3)
            msg.skip(9)
            msg.read_xor_byte_seq(guids[i], 7)
            msg.skip(1)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            msg.skip(1)
            msg.read_xor_byte_seq(guids[i], 0, 2)
            msg.read_xor_byte_seq(guild_guids[i], 1, 7)
            msg.skip(5)
            race = msg.read_byte()
            msg.skip(1)  # level
            msg.read_xor_byte_seq(guids[i], 6)
            msg.read_xor_byte_seq(guild_guids[i], 4, 0)
            msg.read_xor_byte_seq(guids[i], 5, 1)

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            guild_guid = struct.unpack("<Q", bytes(guild_guids[i]))[0]

            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)

            msg.skip(4)  # zone

        return None

    def _write_player_login(self) -> bytes:
        pw = PacketBitWriter()
        guid_bytes = list(struct.pack("<Q", self.self_character_id))
        pw.write_bit_seq(guid_bytes, 2, 3, 0, 6, 4, 5, 1, 7)
        pw.write_xor_byte_seq(guid_bytes, 2, 7, 0, 3, 5, 6, 1, 4)
        return pw.build()

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(channel_id)
        pw.write_bit(0)  # has voice
        pw.write_bit(0)  # zone update
        pw.write_bits(len(channel_name_bytes), 8)
        pw.write_bits(0, 8)
        pw.flush()
        pw.write_bytes(channel_name_bytes)
        return pw.build()

    def _query_guild_name(self, out: list[tuple[int, bytes]]) -> None:
        pw = PacketWriter()
        pw.write_long_le(self.guild_guid)
        pw.write_long_le(self.self_character_id)
        out.append((self.CMSG_GUILD_QUERY, pw.build()))

    def _parse_guild_query(self, msg: Packet) -> GuildInfo:
        msg.skip(4)  # first part of guid
        return super()._parse_guild_query(msg)

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        motd_length = msg.read_bits(11)
        count = msg.read_bits(18)

        guids = [[0] * 8 for _ in range(count)]
        p_note_lengths = [0] * count
        o_note_lengths = [0] * count
        name_lengths = [0] * count

        for i in range(count):
            msg.read_bit_seq(guids[i], 3, 4)
            msg.read_bits(2)  # bnet client flags
            p_note_lengths[i] = msg.read_bits(8)
            o_note_lengths[i] = msg.read_bits(8)
            msg.read_bit_seq(guids[i], 0)
            name_lengths[i] = msg.read_bits(7)
            msg.read_bit_seq(guids[i], 1, 2, 6, 5, 7)

        g_info_length = msg.read_bits(12)

        roster: dict[int, GuildMember] = {}
        for i in range(count):
            char_class = msg.read_byte()
            msg.skip(4)  # unkn
            msg.read_xor_byte_seq(guids[i], 0)
            msg.skip(40)  # weekly activity, achievements, professions
            msg.read_xor_byte_seq(guids[i], 2)
            flags = msg.read_byte()
            zone_id = msg.read_int_le()
            msg.skip(8)  # total activity
            msg.read_xor_byte_seq(guids[i], 7)
            msg.skip(4)  # guild rep
            msg.skip(p_note_lengths[i])  # public note
            msg.read_xor_byte_seq(guids[i], 3)
            level = msg.read_byte()
            msg.skip(4)  # unkn
            msg.read_xor_byte_seq(guids[i], 5, 4)
            msg.skip(1)  # unkn
            msg.read_xor_byte_seq(guids[i], 1)
            last_logoff = msg.read_float_le()
            msg.skip(o_note_lengths[i])  # officer note
            msg.read_xor_byte_seq(guids[i], 6)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            is_online = (flags & 0x01) == 0x01

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)

        msg.skip(g_info_length)
        self.guild_motd = msg.slice(motd_length).decode("utf-8", errors="replace")
        return roster

    def _build_chat_message(self, tp: int, msg_bytes: bytes,
                            target_bytes: bytes | None) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(self.language_id)
        if target_bytes is not None:
            pw.write_bits(len(target_bytes), 10)
        pw.write_bits(len(msg_bytes), 9)
        pw.flush()
        pw.write_bytes(msg_bytes)
        if target_bytes is not None:
            pw.write_bytes(target_bytes)
        return pw.build()

    def _parse_notification(self, msg: Packet) -> str:
        length = msg.read_bits(13)
        return msg.slice(length).decode("utf-8", errors="replace")

    def _handle_notification(self, msg: Packet) -> None:
        logger.info(f"Notification: {self._parse_notification(msg)}")


class GamePacketHandlerMoP(GamePacketHandlerCataclysm, GamePacketsMoP):
    """MoP-specific handler with additional guild packets and different bit layouts."""

    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        mid = msg.id
        if mid == self.SMSG_GUILD_MOTD:
            return self._handle_mop_guild_motd(msg)
        if mid == self.SMSG_GUILD_RANKS_UPDATE:
            self._handle_mop_guild_ranks_update(msg)
            return []
        if mid == self.SMSG_GUILD_INVITE_ACCEPT:
            self._handle_mop_guild_invite_accept(msg)
            return []
        if mid == self.SMSG_GUILD_MEMBER_LOGGED:
            self._handle_mop_guild_member_logged(msg)
            return []
        if mid == self.SMSG_GUILD_LEAVE:
            self._handle_mop_guild_leave(msg)
            return []
        return super().handle_packet(msg)

    def send_name_query(self, guid: int) -> None:
        pw = PacketBitWriter()
        guid_bytes = list(struct.pack("<Q", guid))
        pw.write_bit_seq(guid_bytes, 4)
        pw.write_bit(0)
        pw.write_bit_seq(guid_bytes, 6, 0, 7, 1)
        pw.write_bit(0)
        pw.write_bit_seq(guid_bytes, 5, 2, 3)
        pw.flush()
        pw.write_xor_byte_seq(guid_bytes, 7, 5, 1, 2, 6, 3, 0, 4)
        self.send(self.CMSG_NAME_QUERY, pw.build())

    def _parse_name_query(self, msg: Packet) -> NameQueryMessage:
        guid_mask = [0] * 8
        guid2_mask = [0] * 8
        guid3_mask = [0] * 8

        msg.read_bit_seq(guid_mask, 3, 6, 7, 2, 5, 4, 0, 1)
        msg.read_xor_byte_seq(guid_mask, 5, 4, 7, 6, 1, 2)

        has_name_data = msg.read_bit() == 0
        char_class = 0xFF
        if has_name_data:
            msg.skip(8)  # realm id, acc id
            char_class = msg.read_byte()
            msg.skip(3)  # race, level, gender

        msg.read_xor_byte_seq(guid_mask, 0, 3)

        guid = struct.unpack("<Q", bytes(guid_mask))[0]

        if not has_name_data:
            logger.error(f"RECV SMSG_NAME_QUERY - Name not known for guid {guid}")
            return NameQueryMessage(guid, "UNKNOWN", char_class)

        msg.reset_bit_reader()
        msg.read_bit_seq(guid2_mask, 2, 7)
        msg.read_bit_seq(guid3_mask, 7, 2, 0)
        msg.read_bit()
        msg.read_bit_seq(guid2_mask, 4)
        msg.read_bit_seq(guid3_mask, 5)
        msg.read_bit_seq(guid2_mask, 1, 3, 0)
        msg.read_bits(7 * 5)  # declined names
        msg.read_bit_seq(guid3_mask, 6, 3)
        msg.read_bit_seq(guid2_mask, 5)
        msg.read_bit_seq(guid3_mask, 1, 4)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid2_mask, 6)
        msg.reset_bit_reader()
        msg.read_xor_byte_seq(guid3_mask, 6, 0)

        name = msg.slice(name_length).decode("utf-8", errors="replace")
        return NameQueryMessage(guid, name, char_class)

    def _parse_invalidate_player(self, msg: Packet) -> int:
        guid_mask = [0] * 8
        msg.read_bit_seq(guid_mask, 6, 3, 1, 2, 7, 5, 0, 4)
        msg.read_xor_byte_seq(guid_mask, 7, 1, 2, 3, 6, 0, 4, 5)
        return struct.unpack("<Q", bytes(guid_mask))[0]  # type: ignore[no-any-return]

    def _handle_invalidate_player(self, msg: Packet) -> None:
        guid = self._parse_invalidate_player(msg)
        self.player_roster.pop(guid, None)

    def _build_who_message(self, name: str) -> bytes:
        bw = PacketBitWriter()
        bw.write_int_le(0xFFFFFFFF)  # class mask
        bw.write_int_le(0xFFFFFFFF)  # race mask
        bw.write_int_le(100)  # max level
        bw.write_int_le(0)  # min level
        bw.write_bit(1)  # show enemies
        bw.write_bit(1)  # exact name
        bw.write_bit(0)  # request server info
        bw.write_bits(0, 9)  # guild realm name length
        bw.write_bit(1)  # show arena players
        bw.write_bits(len(name), 6)  # name length
        bw.write_bits(0, 4)  # zones count
        bw.write_bits(0, 9)  # realm length
        bw.write_bits(0, 7)  # guild name length
        bw.write_bits(0, 3)  # word count
        bw.flush()
        bw.write_bytes(name.encode("utf-8"))
        return bw.build()

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        msg.skip(35)  # MoP: 35 bytes random data
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        digest = md.digest()

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_long_le(0)
        pw.write_byte(digest[18])
        pw.write_byte(digest[14])
        pw.write_byte(digest[3])
        pw.write_byte(digest[4])
        pw.write_byte(digest[0])
        pw.write_int_le(self.realm_id)
        pw.write_byte(digest[11])
        pw.write_int(client_seed)
        pw.write_byte(digest[19])
        pw.write_short_le(1)
        pw.write_byte(digest[2])
        pw.write_byte(digest[9])
        pw.write_byte(digest[12])
        pw.write_long_le(0)
        pw.write_int_le(0)
        pw.write_byte(digest[16])
        pw.write_byte(digest[5])
        pw.write_byte(digest[6])
        pw.write_byte(digest[8])
        pw.write_short_le(global_state.game_build)
        pw.write_byte(digest[17])
        pw.write_byte(digest[7])
        pw.write_byte(digest[13])
        pw.write_byte(digest[15])
        pw.write_byte(digest[1])
        pw.write_byte(digest[10])

        pw.write_int_le(len(self.addon_info))
        pw.write_bytes(self.addon_info)

        bw = PacketBitWriter()
        bw.write_bit(0)
        bw.write_bits(len(account), 11)
        bw.flush()
        pw.write_bytes(bw.build())
        pw.write_bytes(account)

        return AuthChallengeMessage(self.session_key, pw.build())

    def _parse_auth_response(self, msg: Packet) -> int:
        if msg.read_bit() == 1:
            return AuthResponseCodes.AUTH_OK
        return AuthResponseCodes.AUTH_FAILED

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        msg.read_bits(21)  # unkn
        characters_num = msg.read_bits(16)

        guids = [[0] * 8 for _ in range(characters_num)]
        guild_guids = [[0] * 8 for _ in range(characters_num)]
        name_lengths = [0] * characters_num

        for i in range(characters_num):
            msg.read_bit_seq(guild_guids[i], 4)
            msg.read_bit_seq(guids[i], 0)
            msg.read_bit_seq(guild_guids[i], 3)
            msg.read_bit_seq(guids[i], 3, 7)
            msg.read_bits(2)
            msg.read_bit_seq(guids[i], 6)
            msg.read_bit_seq(guild_guids[i], 6)
            name_lengths[i] = msg.read_bits(6)
            msg.read_bit_seq(guids[i], 1)
            msg.read_bit_seq(guild_guids[i], 1, 0)
            msg.read_bit_seq(guids[i], 4)
            msg.read_bit_seq(guild_guids[i], 7)
            msg.read_bit_seq(guids[i], 2, 5)
            msg.read_bit_seq(guild_guids[i], 2, 5)

        msg.read_bit()  # packet success flag

        for i in range(characters_num):
            msg.skip(4)  # unkn
            msg.read_xor_byte_seq(guids[i], 1)
            msg.skip(2)
            msg.read_xor_byte_seq(guild_guids[i], 2, 0, 6)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            msg.read_xor_byte_seq(guild_guids[i], 3)
            msg.skip(10)
            msg.read_xor_byte_seq(guild_guids[i], 5)
            msg.skip(207)  # inventory
            msg.skip(4)  # customization flags
            msg.read_xor_byte_seq(guids[i], 3, 5)
            msg.skip(4)  # pet family
            msg.read_xor_byte_seq(guild_guids[i], 4)
            msg.skip(4)  # map
            race = msg.read_byte()
            msg.skip(1)  # skin
            msg.read_xor_byte_seq(guild_guids[i], 1)
            msg.skip(1)  # level
            msg.read_xor_byte_seq(guids[i], 0, 2)
            msg.skip(3)  # hair color + gender + facial hair
            msg.skip(4)  # pet level
            msg.read_xor_byte_seq(guids[i], 4, 7)
            msg.skip(12)
            msg.read_xor_byte_seq(guids[i], 6)
            msg.skip(8)  # char flags + zone
            msg.read_xor_byte_seq(guild_guids[i], 7)
            msg.skip(4)

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            guild_guid = struct.unpack("<Q", bytes(guild_guids[i]))[0]

            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)

        return None

    def _write_player_login(self) -> bytes:
        bw = PacketBitWriter()
        guid_bytes = list(struct.pack("<Q", self.self_character_id))
        bw.write_int_le(0x43480000)  # unkn
        bw.write_bit_seq(guid_bytes, 1, 4, 7, 3, 2, 6, 5, 0)
        bw.write_xor_byte_seq(guid_bytes, 5, 1, 0, 6, 2, 4, 7, 3)
        return bw.build()

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(channel_id)
        pw.write_bit(0)  # unkn
        pw.write_bits(len(channel_name_bytes), 7)
        pw.write_bits(0, 7)
        pw.write_bit(0)  # unkn
        pw.flush()
        pw.write_bytes(channel_name_bytes)
        return pw.build()

    def _query_guild_name(self, out: list[tuple[int, bytes]]) -> None:
        player_bytes = list(struct.pack("<Q", self.self_character_id))
        guild_bytes = list(struct.pack("<Q", self.guild_guid))
        pw = PacketBitWriter()
        pw.write_bit_seq(player_bytes, 7, 3, 4)
        pw.write_bit_seq(guild_bytes, 3, 4)
        pw.write_bit_seq(player_bytes, 2, 6)
        pw.write_bit_seq(guild_bytes, 2, 5)
        pw.write_bit_seq(player_bytes, 1, 5)
        pw.write_bit_seq(guild_bytes, 7)
        pw.write_bit_seq(player_bytes, 0)
        pw.write_bit_seq(guild_bytes, 1, 6, 0)
        pw.flush()
        pw.write_xor_byte_seq(player_bytes, 7)
        pw.write_xor_byte_seq(guild_bytes, 2, 4, 7)
        pw.write_xor_byte_seq(player_bytes, 6, 0)
        pw.write_xor_byte_seq(guild_bytes, 6, 0, 3)
        pw.write_xor_byte_seq(player_bytes, 2)
        pw.write_xor_byte_seq(guild_bytes, 5)
        pw.write_xor_byte_seq(player_bytes, 3)
        pw.write_xor_byte_seq(guild_bytes, 1)
        pw.write_xor_byte_seq(player_bytes, 4, 1, 5)
        out.append((self.CMSG_GUILD_QUERY, pw.build()))

    def _parse_guild_query(self, msg: Packet) -> GuildInfo:
        guild_guid_arr = [0] * 8
        msg.read_bit_seq(guild_guid_arr, 5)
        msg.read_bit()
        ranks_num = msg.read_bits(21)
        msg.read_bits(4)  # guid repeated
        rank_lengths = [msg.read_bits(7) for _ in range(ranks_num)]
        msg.read_bits(4)  # guid repeated
        guild_name_length = msg.read_bits(7)
        msg.read_bit_seq(guild_guid_arr, 3, 7, 2, 1, 0, 4, 6)

        msg.skip(8)  # emblem border + style
        msg.read_xor_byte_seq(guild_guid_arr, 2, 7)
        msg.skip(8)  # emblem color + realmid

        ranks: dict[int, str] = {}
        for _ in range(ranks_num):
            msg.skip(4)  # rank index
            rank_id = msg.read_int_le()
            rank_name = msg.slice(rank_lengths[_]).decode("utf-8", errors="replace")
            ranks[rank_id] = rank_name

        name = msg.slice(guild_name_length).decode("utf-8", errors="replace")
        return GuildInfo(name, ranks)

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        has_sender_name = msg.read_bit() == 0
        msg.read_bit()  # hide in chat log
        if has_sender_name:
            msg.read_bits(11)  # sender name length (unused)
        msg.read_bit()  # unkn
        has_channel_name = msg.read_bit() == 0
        msg.read_bit()  # unkn
        msg.read_bit()  # send fake time?
        has_chat_tag = msg.read_bit() == 0
        has_realm_id = msg.read_bit() == 0

        group_guid_arr = [0] * 8
        msg.read_bit_seq(group_guid_arr, 0, 1, 5, 4, 3, 2, 6, 7)
        if has_chat_tag:
            msg.read_bits(9)
        msg.read_bit()

        receiver_guid_arr = [0] * 8
        msg.read_bit_seq(receiver_guid_arr, 7, 6, 1, 4, 0, 2, 3, 5)
        msg.read_bit()
        has_language = msg.read_bit() == 0
        has_prefix = msg.read_bit() == 0

        sender_guid_arr = [0] * 8
        msg.read_bit_seq(sender_guid_arr, 0, 3, 7, 2, 1, 5, 4, 6)

        has_achievement = msg.read_bit() == 0
        has_message = msg.read_bit() == 0

        channel_name_length = msg.read_bits(7) if has_channel_name else 0
        message_length = msg.read_bits(12) if has_message else 0

        if not has_message or message_length == 0:
            return None

        has_receiver = msg.read_bit() == 0
        addon_prefix_length = msg.read_bits(5) if has_prefix else 0
        msg.read_bit()  # realm id?
        if has_receiver:
            msg.read_bits(11)  # receiver length (unused)
        msg.read_bit()

        guild_guid_arr = [0] * 8
        msg.read_bit_seq(guild_guid_arr, 2, 5, 7, 4, 0, 1, 3, 6)
        msg.read_xor_byte_seq(guild_guid_arr, 4, 5, 7, 3, 2, 6, 0, 1)

        channel_name = msg.slice(channel_name_length).decode("utf-8", errors="replace") if has_channel_name else None
        if has_prefix:
            msg.skip(addon_prefix_length)

        msg.read_xor_byte_seq(sender_guid_arr, 4, 7, 1, 5, 0, 6, 2, 3)
        tp = msg.read_byte()

        sender_guid = struct.unpack("<Q", bytes(sender_guid_arr))[0]
        if tp != ChatEvents.CHAT_MSG_SYSTEM and sender_guid == self.self_character_id:
            return None
        if tp != ChatEvents.CHAT_MSG_GUILD_ACHIEVEMENT and not self._check_channel_enabled(tp, channel_name):
            return None

        achievement_id = msg.read_int_le() if has_achievement else None
        msg.read_xor_byte_seq(group_guid_arr, 1, 3, 4, 6, 0, 2, 5, 7)
        msg.read_xor_byte_seq(receiver_guid_arr, 4, 7, 1, 5, 0, 6, 2, 3)

        language = msg.read_byte() if has_language else 0
        if language == -1:
            return None
        if has_realm_id:
            msg.skip(4)

        txt = msg.slice(message_length).decode("utf-8", errors="replace")

        if has_achievement and achievement_id is not None:
            self._handle_achievement_event(sender_guid, achievement_id)
            return None

        return ChatMessage(sender_guid, tp, txt, channel_name)

    def _parse_server_motd(self, msg: Packet) -> list[ChatMessage]:
        line_count = msg.read_bits(4)
        message_lengths = [msg.read_bits(7) for _ in range(line_count)]
        result = []
        for ml in message_lengths:
            message = msg.slice(ml).decode("utf-8", errors="replace")
            result.append(ChatMessage(0, ChatEvents.CHAT_MSG_SYSTEM, message, None))
        return result

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        count = msg.read_bits(17)
        motd_length = msg.read_bits(10)

        guids = [[0] * 8 for _ in range(count)]
        p_note_lengths = [0] * count
        o_note_lengths = [0] * count
        name_lengths = [0] * count

        for i in range(count):
            o_note_lengths[i] = msg.read_bits(8)
            msg.read_bit_seq(guids[i], 5)
            msg.read_bit()  # scroll of resurrect
            p_note_lengths[i] = msg.read_bits(8)
            msg.read_bit_seq(guids[i], 7, 0, 6)
            name_lengths[i] = msg.read_bits(6)
            msg.read_bit()  # has authenticator
            msg.read_bit_seq(guids[i], 3, 4, 1, 2)

        g_info_length = msg.read_bits(11)

        roster: dict[int, GuildMember] = {}
        for i in range(count):
            char_class = msg.read_byte()
            msg.skip(4)  # total reputation
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            msg.read_xor_byte_seq(guids[i], 0)
            msg.skip(24)  # professions
            level = msg.read_byte()
            flags = msg.read_byte()
            zone_id = msg.read_int_le()
            msg.skip(4)  # rep cap
            msg.read_xor_byte_seq(guids[i], 3)
            msg.skip(8)  # total activity
            msg.skip(o_note_lengths[i])  # officer note
            last_logoff = msg.read_float_le()
            msg.skip(1)  # gender
            msg.skip(4)  # rank
            msg.skip(4)  # realm id
            msg.read_xor_byte_seq(guids[i], 5, 7)
            msg.skip(p_note_lengths[i])  # public note
            msg.read_xor_byte_seq(guids[i], 4)
            msg.skip(8)  # weekly activity
            msg.skip(4)  # achievement points
            msg.read_xor_byte_seq(guids[i], 6, 1, 2)
            is_online = (flags & 0x01) == 0x01

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)

        msg.skip(4)  # accounts number
        msg.skip(4)  # created date
        msg.skip(g_info_length)
        msg.skip(4)  # weekly rep cap
        self.guild_motd = msg.slice(motd_length).decode("utf-8", errors="replace")
        return roster

    def _parse_notification(self, msg: Packet) -> str:
        length = msg.read_bits(12)
        return msg.slice(length).decode("utf-8", errors="replace")

    def _build_chat_message(self, tp: int, msg_bytes: bytes,
                            target_bytes: bytes | None) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(self.language_id)
        if target_bytes is not None and tp == ChatEvents.CHAT_MSG_CHANNEL:
            pw.write_bits(len(target_bytes), 9)
        pw.write_bits(len(msg_bytes), 8)
        if tp == ChatEvents.CHAT_MSG_WHISPER and target_bytes is not None:
            pw.write_bits(len(target_bytes), 9)
        pw.flush()
        pw.write_bytes(msg_bytes)
        if target_bytes is not None:
            pw.write_bytes(target_bytes)
        return pw.build()

    # -- MoP-specific guild packet handlers --

    def _handle_mop_guild_motd(self, msg: Packet) -> list[tuple[int, bytes]]:
        length = msg.read_bits(10)
        motd = msg.slice(length).decode("utf-8", errors="replace")
        self.guild_motd = motd
        self._handle_guild_event_common(GuildEvents(True).GE_MOTD, [motd])
        return []

    def _handle_mop_guild_ranks_update(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        target_arr = [0] * 8
        msg.read_bit_seq(target_arr, 5, 6)
        msg.read_bit_seq(guid_arr, 0, 1)
        msg.read_bit_seq(target_arr, 3)
        msg.read_bit_seq(guid_arr, 4)
        msg.read_bit_seq(target_arr, 2)
        msg.read_bit_seq(guid_arr, 6, 3, 7)
        msg.read_bit_seq(target_arr, 4, 0, 1)
        msg.read_bit_seq(guid_arr, 2)
        msg.read_bit_seq(target_arr, 7)
        rank_order = msg.read_bit()
        msg.read_bit_seq(guid_arr, 5)

        msg.read_xor_byte_seq(target_arr, 2)
        msg.read_xor_byte_seq(guid_arr, 1)
        msg.read_xor_byte_seq(target_arr, 6, 1, 5)
        msg.read_xor_byte_seq(guid_arr, 0)
        rank = msg.read_int_le()
        msg.read_xor_byte_seq(guid_arr, 3, 7)
        msg.read_xor_byte_seq(target_arr, 7)
        msg.read_xor_byte_seq(guid_arr, 2)
        msg.read_xor_byte_seq(target_arr, 3, 4)
        msg.read_xor_byte_seq(guid_arr, 6, 5)
        msg.read_xor_byte_seq(target_arr, 0)
        msg.read_xor_byte_seq(guid_arr, 4)

        guid = struct.unpack("<Q", bytes(guid_arr))[0]
        target_guid = struct.unpack("<Q", bytes(target_arr))[0]

        name = self.guild_roster.get(guid)
        target_name = self.guild_roster.get(target_guid)

        if name is None or target_name is None:
            logger.error("GUID for SMSG_GUILD_RANKS_UPDATE not found in guild roster!")
            return

        rank_name = ""
        if self.guild_info and rank in self.guild_info.ranks:
            rank_name = self.guild_info.ranks[rank]
        else:
            logger.error(f"Rank ID {rank} for SMSG_GUILD_RANKS_UPDATE not found!")

        event = GuildEvents(True).GE_PROMOTED if rank_order == 1 else GuildEvents(True).GE_DEMOTED
        self._handle_guild_event_common(event, [name.name, target_name.name, rank_name])

    def _handle_mop_guild_invite_accept(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        msg.read_bit_seq(guid_arr, 6, 1, 3)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid_arr, 7, 4, 2, 5, 0)
        msg.read_xor_byte_seq(guid_arr, 2, 4, 1, 6, 5)
        msg.skip(4)
        msg.read_xor_byte_seq(guid_arr, 3, 0)
        name = msg.slice(name_length).decode("utf-8", errors="replace")
        msg.read_xor_byte_seq(guid_arr, 7)
        self._handle_guild_event_common(GuildEvents(True).GE_JOINED, [name])

    def _handle_mop_guild_member_logged(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        msg.read_bit_seq(guid_arr, 0, 6)
        msg.read_bit()
        msg.read_bit_seq(guid_arr, 2, 5, 3)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid_arr, 1, 7, 4)
        is_online = msg.read_bit() == 1
        msg.read_xor_byte_seq(guid_arr, 3, 2, 0)
        msg.skip(4)
        msg.read_xor_byte_seq(guid_arr, 6)
        name = msg.slice(name_length).decode("utf-8", errors="replace")
        msg.read_xor_byte_seq(guid_arr, 4, 5, 7, 1)

        ge = GuildEvents(True)
        event = ge.GE_SIGNED_ON if is_online else ge.GE_SIGNED_OFF
        self._handle_guild_event_common(event, [name])

    def _handle_mop_guild_leave(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        msg.read_bit_seq(guid_arr, 2)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid_arr, 6, 5)
        kicked = msg.read_bit() == 1

        kicker_name_length = 0
        kicker_guid_arr = None
        if kicked:
            msg.read_bits(2)
            kicker_name_length = msg.read_bits(6)
            kicker_guid_arr = [0] * 8
            msg.read_bit_seq(kicker_guid_arr, 1, 3, 4, 2, 5, 7, 6, 0)
            msg.read_bit()

        msg.read_bit_seq(guid_arr, 1, 0, 3, 4, 7)

        kicker_name = ""
        if kicked and kicker_guid_arr is not None:
            msg.read_xor_byte_seq(kicker_guid_arr, 1, 3, 5, 2, 0, 4, 6, 7)
            kicker_name = msg.slice(kicker_name_length).decode("utf-8", errors="replace")
            msg.skip(4)

        name = msg.slice(name_length).decode("utf-8", errors="replace")
        msg.read_xor_byte_seq(guid_arr, 1)
        msg.skip(4)
        msg.read_xor_byte_seq(guid_arr, 0, 4, 2, 3, 6, 5, 7)

        ge = GuildEvents(True)
        if kicked:
            self._handle_guild_event_common(ge.GE_REMOVED, [name, kicker_name])
        else:
            self._handle_guild_event_common(ge.GE_LEFT, [name])
