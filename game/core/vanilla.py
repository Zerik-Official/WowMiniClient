"""
Vanilla game packet handler.
"""

from __future__ import annotations

import hashlib
import random
import struct
import time
from collections.abc import Callable
from typing import Any

from utils.logger import Tags, log
from common.chat import ChatEvents
from game.core.buffer import Packet, PacketWriter
from common.types import WowExpansion, global_state
from game.core.command_handler import GameCommandHandler
from game.core.packets import (
    AuthResponseCodes,
    ChatNotify,
    Classes,
    GamePackets,
    GuildEvents,
    Races,
    ServerMessageType,
)
from game.core.resources import GameResources
from game.models import (
    AuthChallengeMessage,
    CharEnumMessage,
    ChatMessage,
    GuildInfo,
    GuildMember,
    NameQueryMessage,
    Player,
)

ADDON_INFO_VANILLA = bytes([
    0x56, 0x01, 0x00, 0x00, 0x78, 0x9C, 0x75, 0xCC, 0xBD, 0x0E, 0xC2, 0x30, 0x0C, 0x04, 0xE0, 0xF2,
    0xBC, 0x0C, 0x61, 0x40, 0x95, 0xC8, 0x42, 0xC3, 0x8C, 0x4C, 0xE2, 0x22, 0x0B, 0xC7, 0xA9, 0x8C,
    0xCB, 0x4F, 0x9F, 0x1E, 0x16, 0x24, 0x06, 0x73, 0xEB, 0x77, 0x77, 0x81, 0x69, 0x59, 0x40, 0xCB,
    0x69, 0x33, 0x67, 0xA3, 0x26, 0xC7, 0xBE, 0x5B, 0xD5, 0xC7, 0x7A, 0xDF, 0x7D, 0x12, 0xBE, 0x16,
    0xC0, 0x8C, 0x71, 0x24, 0xE4, 0x12, 0x49, 0xA8, 0xC2, 0xE4, 0x95, 0x48, 0x0A, 0xC9, 0xC5, 0x3D,
    0xD8, 0xB6, 0x7A, 0x06, 0x4B, 0xF8, 0x34, 0x0F, 0x15, 0x46, 0x73, 0x67, 0xBB, 0x38, 0xCC, 0x7A,
    0xC7, 0x97, 0x8B, 0xBD, 0xDC, 0x26, 0xCC, 0xFE, 0x30, 0x42, 0xD6, 0xE6, 0xCA, 0x01, 0xA8, 0xB8,
    0x90, 0x80, 0x51, 0xFC, 0xB7, 0xA4, 0x50, 0x70, 0xB8, 0x12, 0xF3, 0x3F, 0x26, 0x41, 0xFD, 0xB5,
    0x37, 0x90, 0x19, 0x66, 0x8F,
])

ADDON_INFO_TBC = bytes([
    0xD0, 0x01, 0x00, 0x00, 0x78, 0x9C, 0x75, 0xCF, 0x3B, 0x0E, 0xC2, 0x30, 0x0C, 0x80, 0xE1, 0x72,
    0x0F, 0x2E, 0x43, 0x18, 0x50, 0xA5, 0x66, 0xA1, 0x65, 0x46, 0x26, 0x71, 0x2B, 0xAB, 0x89, 0x53,
    0x19, 0x87, 0x47, 0x4F, 0x0F, 0x0B, 0x62, 0x71, 0xBD, 0x7E, 0xD6, 0x6F, 0xD9, 0x25, 0x5A, 0x57,
    0x90, 0x78, 0x3D, 0xD4, 0xA0, 0x54, 0xF8, 0xD2, 0x36, 0xBB, 0xFC, 0xDC, 0x77, 0xCD, 0x77, 0xDC,
    0xCF, 0x1C, 0xA8, 0x26, 0x1C, 0x09, 0x53, 0xF4, 0xC4, 0x94, 0x61, 0xB1, 0x96, 0x88, 0x23, 0xF1,
    0x64, 0x06, 0x8E, 0x25, 0xDF, 0x40, 0xBB, 0x32, 0x6D, 0xDA, 0x80, 0x2F, 0xB5, 0x50, 0x60, 0x54,
    0x33, 0x79, 0xF2, 0x7D, 0x95, 0x07, 0xBE, 0x6D, 0xAC, 0x94, 0xA2, 0x03, 0x9E, 0x4D, 0x6D, 0xF9,
    0xBE, 0x60, 0xB0, 0xB3, 0xAD, 0x62, 0xEE, 0x4B, 0x98, 0x51, 0xB7, 0x7E, 0xF1, 0x10, 0x04, 0x29,
    0x98, 0x72, 0x06, 0x8A, 0x26, 0x0C, 0x90, 0x90, 0xED, 0x7B, 0x83, 0x40, 0xC4, 0x7E, 0xA6, 0x94,
    0xB6, 0x98, 0x18, 0xC5, 0x36, 0xCA, 0xE8, 0x81, 0x61, 0x42, 0xF9, 0xEB, 0x07, 0x63, 0xAB, 0x8B,
    0xEC,
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
])

ADDON_INFO_CATA = bytes([
    0xE0, 0x03, 0x00, 0x00, 0x78, 0x9C, 0x75, 0x93, 0x61, 0x6E, 0xC3, 0x20, 0x0C, 0x85, 0xBF, 0x73,
    0x8A, 0x5D, 0x7A, 0x4F, 0xB4, 0x2A, 0x51, 0x57, 0x4D, 0xAB, 0xD4, 0xFE, 0x77, 0x32, 0xA9, 0x8B,
    0x22, 0x4C, 0x4A, 0x18, 0x4D, 0xBB, 0xDB, 0x2F, 0x41, 0x93, 0xA6, 0x26, 0xCA, 0xF0, 0x79, 0xEF,
    0x19, 0xBF, 0x3C, 0x3F, 0x39, 0xC8, 0x45, 0xF4, 0xF2, 0x3B, 0x88, 0x7E, 0x68, 0x6C, 0xCF, 0xF0,
    0x84, 0x03, 0xFA, 0x70, 0x3E, 0x64, 0x0F, 0xC3, 0xF0, 0x78, 0x3C, 0x66, 0x7F, 0xB8, 0x98, 0x0E,
    0x90, 0x1D, 0xB7, 0xE7, 0x04, 0x47, 0x0F, 0x3A, 0x99, 0x4D, 0x5A, 0xFC, 0x5A, 0x64, 0x5B, 0x91,
    0x06, 0x39, 0x75, 0x3C, 0x26, 0x70, 0x08, 0x0E, 0xAF, 0x84, 0xCE, 0x56, 0xE4, 0x11, 0xE0, 0xA2,
    0x26, 0x22, 0x8F, 0xC9, 0xB7, 0x7A, 0x03, 0x07, 0xA6, 0x0D, 0x90, 0x1E, 0xF5, 0xA9, 0x76, 0xE0,
    0xD0, 0x58, 0x10, 0x0D, 0x75, 0xE0, 0x22, 0x6C, 0x71, 0xD2, 0x2B, 0x1D, 0x45, 0xAB, 0x2A, 0x58,
    0xD0, 0x18, 0x10, 0x82, 0xC6, 0xE1, 0xA4, 0xC9, 0x78, 0x68, 0x20, 0x1C, 0xB9, 0x4D, 0xB2, 0x1A,
    0x3F, 0x83, 0x0E, 0x47, 0x30, 0xE1, 0x04, 0x64, 0xF7, 0x02, 0x83, 0xDE, 0xFC, 0xBC, 0x2F, 0x85,
    0xAF, 0xA4, 0x1F, 0xFD, 0x8C, 0xCD, 0xDC, 0xD6, 0xCC, 0x4E, 0x83, 0x2F, 0xDE, 0xF0, 0xEC, 0x03,
    0xCA, 0x2B, 0xCF, 0xE2, 0xC1, 0x29, 0x92, 0xDC, 0xDD, 0xC6, 0x4E, 0x9D, 0x3D, 0x2F, 0xA2, 0x39,
    0xBA, 0xA1, 0x79, 0x51, 0xCD, 0xB2, 0xA0, 0x9E, 0x91, 0x7C, 0x26, 0x67, 0xB7, 0xE0, 0xFB, 0x34,
    0xED, 0xD8, 0x07, 0x61, 0xB7, 0x16, 0xA8, 0xE4, 0xE0, 0xA7, 0x11, 0x8D, 0x7E, 0xA3, 0x43, 0xC0,
    0x61, 0xE3, 0xE2, 0xA4, 0x90, 0x4C, 0xE1, 0x2A, 0xA9, 0xD8, 0xC4, 0x90, 0xA4, 0x72, 0xB4, 0xAA,
    0xE3, 0xDC, 0x0A, 0x58, 0x54, 0xF9, 0x91, 0xB9, 0x8F, 0xB5, 0x7B, 0x96, 0xF4, 0x25, 0x0B, 0x30,
    0xC2, 0x3A, 0xE1, 0x05, 0x4B, 0xB0, 0x0A, 0x29, 0x31, 0xFC, 0xEC, 0x80, 0x5A, 0x17, 0x69, 0xFA,
    0xF9, 0xD6, 0xE4, 0xA8, 0x55, 0x27, 0xBC, 0xB2, 0xB4, 0xA9, 0x49, 0xEB, 0x75, 0x23, 0x74, 0x4E,
    0xD6, 0x34, 0x60, 0x01, 0x1E, 0x5A, 0xD4, 0xD6, 0x97, 0x9A, 0x7B, 0xD4, 0xED, 0xED, 0xD5, 0xDA,
    0xAA, 0x7A, 0x72, 0xFA, 0xB3, 0x46, 0x4C, 0x1E, 0x45, 0x65, 0x17, 0x26, 0x5B, 0x05, 0x96, 0x78,
    0xA6, 0xEE, 0xC0, 0xA5, 0x54, 0xFF, 0xBF, 0xCD, 0x38, 0x85, 0x5D, 0xC7, 0x64, 0x50, 0xA1, 0x6B,
    0x47, 0xBD, 0xDF, 0x66, 0x0E, 0xDD, 0xEF, 0xE2, 0xFF, 0x55, 0x7C, 0xC5, 0xEF, 0x1B, 0x7A, 0xEB,
    0x96, 0xC4,
])

ADDON_INFO_MOP = bytes([
    0x30, 0x05, 0x00, 0x00, 0x78, 0x9C, 0x75, 0x93, 0x61, 0x6E, 0xC3, 0x20, 0x0C, 0x85, 0xD9, 0x63,
    0x77, 0xD8, 0x25, 0xDA, 0x6E, 0x45, 0x9D, 0x8A, 0xC4, 0x0A, 0xED, 0xDF, 0xC9, 0x24, 0x2E, 0x58,
    0x84, 0x18, 0x99, 0xC0, 0xD6, 0x5E, 0x7E, 0x0B, 0x9A, 0x34, 0x6D, 0x92, 0xC3, 0x4F, 0xBE, 0x67,
    0x27, 0x7E, 0x79, 0x7E, 0xCA, 0xB2, 0x6C, 0xEB, 0xE8, 0x7E, 0x07, 0xB1, 0xEF, 0x1B, 0xD3, 0x11,
    0x2E, 0x38, 0xA0, 0x0F, 0xE7, 0x43, 0xF6, 0x30, 0x7C, 0x3C, 0x1E, 0xB3, 0x7F, 0x5C, 0x4C, 0x07,
    0xC8, 0x8E, 0xDB, 0x5B, 0x82, 0xA3, 0x07, 0x9D, 0xCC, 0x26, 0x10, 0x7B, 0x95, 0x6D, 0x41, 0x1A,
    0x94, 0xA9, 0xE3, 0x31, 0x81, 0x43, 0x70, 0x78, 0x25, 0x74, 0xB6, 0x20, 0x4F, 0x03, 0x8C, 0x9A,
    0x88, 0xBC, 0x25, 0xDF, 0xEA, 0x0D, 0x1C, 0x98, 0xBE, 0x00, 0xE9, 0x51, 0x9F, 0x6A, 0x07, 0x0E,
    0xBD, 0x05, 0xD1, 0x50, 0x07, 0x2E, 0xC2, 0x16, 0x27, 0xBD, 0xD2, 0x51, 0xB4, 0xAA, 0x82, 0x05,
    0xED, 0x05, 0x84, 0xA0, 0x71, 0x38, 0x69, 0x32, 0x1E, 0x1A, 0x08, 0x47, 0x6E, 0x93, 0xAC, 0xC6,
    0xCF, 0xA0, 0xC3, 0x11, 0x4C, 0x38, 0x01, 0xD9, 0xBD, 0xC0, 0xA0, 0x37, 0x3F, 0xEF, 0x4B, 0xE1,
    0x2B, 0xE9, 0x47, 0x3F, 0x63, 0x33, 0xB7, 0x35, 0xB3, 0xD3, 0xE0, 0x8B, 0x37, 0x3C, 0xFB, 0x80,
    0xF2, 0xCA, 0xB3, 0x78, 0x70, 0x8A, 0x24, 0x77, 0xB7, 0xB1, 0x53, 0x67, 0xCF, 0x8B, 0x68, 0x8E,
    0x6E, 0x68, 0x5E, 0x54, 0xB3, 0x2C, 0x28, 0x67, 0x24, 0x9F, 0xC9, 0xD9, 0x2D, 0xF8, 0x3E, 0x4D,
    0x77, 0xEC, 0x83, 0xB0, 0x4B, 0x0B, 0x54, 0x72, 0xF0, 0xD3, 0x88, 0x46, 0xBF, 0xD1, 0x21, 0xE0,
    0xB0, 0x71, 0x71, 0x52, 0x48, 0xA6, 0x70, 0x95, 0x54, 0x6C, 0x62, 0x48, 0x52, 0x39, 0x5A, 0x55,
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


class GamePacketHandler(GamePackets, GameCommandHandler):
    """Vanilla game packet handler. Base class for all expansion handlers."""

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
        Dispatch an incoming packet to its type-specific handler.

        Args:
            msg: Packet with opcode and raw payload data.

        Returns:
            List of (opcode, payload) tuples to be sent back to the server.
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
        """Log a successful connection to the game server."""
        log("INFO", Tags.GAME, "Connected to game server.")

    def disconnect(self) -> None:
        """
        Mark the session as disconnected and notify the event callback.

        Args:
            None.

        Returns:
            None.
        """
        self.in_world = False
        self.game_event_callback.disconnected()

    def send_message_to_wow(self, tp: int, message: str,
                            target: str | None = None) -> None:
        """
        Send a chat message to the WoW game server.

        Args:
            tp: Chat message type constant (e.g. CHAT_MSG_GUILD).
            message: Text content of the message.
            target: Optional channel or target name for the message.
        """
        payload = self._build_chat_message(tp, message.encode("utf-8"),
                                           target.encode("utf-8") if target else None)
        self.send(self.CMSG_MESSAGECHAT, payload)

    def send_notification(self, message: str) -> None:
        """
        Send a guild notification message to WoW.

        Args:
            message: Notification text to send to guild chat.
        """
        self.send_message_to_wow(ChatEvents.CHAT_MSG_GUILD, message)

    def handle_who(self, arguments: str | None) -> str | None:
        """
        Process a WHO query and return the result string.

        Args:
            arguments: Optional search filter text. If None, returns
                a list of online guild members.

        Returns:
            Formatted WHO result string, or None if the query was
            sent to the server and no inline result is available.
        """
        if arguments:
            payload = self._build_who_message(arguments)
            self.send(self.CMSG_WHO, payload)
            return None
        return self._build_guildies_online()

    def handle_gmotd(self) -> str | None:
        """
        Return the guild Message of the Day.

        Returns:
            Guild MOTD string, or None if not yet received.
        """
        return self.guild_motd

    def send_name_query(self, guid: int) -> None:
        """
        Request the name for a character GUID from the server.

        Args:
            guid: 64-bit character GUID to look up.
        """
        pw = PacketWriter()
        pw.write_long_le(guid)
        self.send(self.CMSG_NAME_QUERY, pw.build())

    def send_logout(self) -> bytes | None:
        """
        Build a CMSG_LOGOUT_REQUEST packet.

        Returns:
            Encoded logout request packet bytes.
        """
        return struct.pack("<H", self.CMSG_LOGOUT_REQUEST)

    def _handle_auth_challenge(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        auth_msg = self._parse_auth_challenge(msg)
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
            log("INFO", Tags.GAME, "Successfully logged in!")
            self._send_char_enum(out)
        elif code == AuthResponseCodes.AUTH_WAIT_QUEUE:
            if msg.remaining() >= 14:
                msg.skip(10)
            position = msg.read_int_le()
            log("INFO", Tags.GAME, f"Queue enabled. Position: {position}")
        else:
            log("ERROR", Tags.GAME, AuthResponseCodes.get_message(code))
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
                log("INFO", Tags.GAME, "Received character enum more than once. Trying again...")
        self.received_char_enum = True
        character = self._parse_char_enum(msg)
        if character is None:
            log("ERROR", Tags.GAME, f"Character {global_state.config.wow.character} not found!")
        else:
            log("INFO", Tags.GAME, f"Logging in with character {character.name}")
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
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(4)
            msg.skip(4)
            msg.skip(12)
            guild_guid = msg.read_int_le()
            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)
            msg.skip(4)
            msg.skip(1)
            msg.skip(12)
            msg.skip(19 * 5)
            msg.skip(5)
        return None

    def _write_player_login(self) -> bytes:
        pw = PacketWriter()
        pw.write_long_le(self.self_character_id)
        return pw.build()

    def _handle_login_verify_world(self, out: list[tuple[int, bytes]]) -> None:
        if self.in_world:
            return
        log("INFO", Tags.GAME, "Successfully joined the world!")
        self.in_world = True
        self.game_event_callback.connected()
        self._run_keep_alive(out)
        self._run_guild_roster_executor(out)
        if self.guild_guid != 0:
            self._query_guild_name(out)
            self._update_guild_roster(out)
        self._join_channels(out)

    def _run_keep_alive(self, out: list[tuple[int, bytes]]) -> None:
        pass

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
            log("INFO", Tags.GAME, f"Joining channel {channel_name}")
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

        event_key_map = {}

        event_key_map[ge.GE_PROMOTED] = "ge_promoted"
        event_key_map[ge.GE_DEMOTED] = "ge_demoted"
        event_key_map[ge.GE_MOTD] = "ge_motd"
        event_key_map[ge.GE_JOINED] = "ge_joined"
        event_key_map[ge.GE_LEFT] = "ge_left"
        event_key_map[ge.GE_REMOVED] = "ge_removed"
        event_key_map[ge.GE_SIGNED_ON] = "ge_signed_on"
        event_key_map[ge.GE_SIGNED_OFF] = "ge_signed_off"

        event_key = event_key_map.get(event)
        if event_key is None:
            return

        template = global_state.config.guild.localized(self.guild_info.name if self.guild_info else "Unknown", event_key)
        if not template:
            return

        name = messages[0] if len(messages) > 0 else ""
        msg = template.replace("%n", name)
        msg = msg.replace("%N", str(global_state.config.wow.character))

        target_name = messages[1] if len(messages) > 1 else ""
        msg = msg.replace("%t", target_name)

        rank_name = messages[2] if len(messages) > 2 else ""
        msg = msg.replace("%r", rank_name)

        msg = msg.replace("%c", self.guild_info.name if self.guild_info else "Unknown")

        log("INFO", Tags.GAME, f"Guild event: {msg}")
        self.game_event_callback.chat_message(None, msg, ChatEvents.CHAT_MSG_SYSTEM, None)

    def _handle_guild_roster(self, msg: Packet) -> None:
        self.guild_roster = self._parse_guild_roster(msg)
        log("DEBUG", Tags.GAME, f"Guild roster received with {len(self.guild_roster)} members.")
        self.game_event_callback.guild_roster_updated()

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        msg.skip(1)
        count = msg.read_int_le()
        msg.skip(1)
        roster: dict[int, GuildMember] = {}
        for _ in range(count):
            guid = msg.read_long_le()
            name = msg.read_string()
            msg.skip(4)
            char_class = msg.read_byte()
            msg.skip(1)
            level = msg.read_byte()
            zone_id = msg.read_int_le()
            last_logoff = msg.read_float_le()
            msg.skip_string()
            msg.skip_string()
            flags = msg.read_int_le()
            msg.skip(1)
            is_online = (flags & 0x01) != 0
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)
        return roster

    def _handle_message_chat(self, msg: Packet) -> None:
        log("DEBUG", Tags.GAME, f"RECV CHAT: {bytes(msg.data[msg._pos:]).hex()}")
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
            msg.skip(8)

        txt_len = msg.read_int_le()
        txt = msg.slice(txt_len - 1).decode("utf-8", errors="replace")
        msg.skip(1)
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
        msg.skip_string()
        msg.skip(4)
        msg.skip(4)
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
                log("INFO", Tags.GAME, err_msg)
            else:
                log("ERROR", Tags.GAME, err_msg)

    def _handle_notification(self, msg: Packet) -> None:
        log("INFO", Tags.GAME, f"Notification: {msg.read_string()}")

    def _handle_who(self, msg: Packet) -> None:
        pass

    def _handle_server_message(self, msg: Packet) -> None:
        tp = msg.read_int_le()
        txt = msg.read_string()
        messages = {
            ServerMessageType.SERVER_MSG_SHUTDOWN_TIME: f"Shutdown in {txt}",
            ServerMessageType.SERVER_MSG_RESTART_TIME: f"Restart in {txt}",
            ServerMessageType.SERVER_MSG_SHUTDOWN_CANCELLED: "Shutdown cancelled.",
            ServerMessageType.SERVER_MSG_RESTART_CANCELLED: "Restart cancelled.",
        }
        message = messages.get(tp, txt)
        self.game_event_callback.chat_message(None, message,
                                              ChatEvents.CHAT_MSG_SYSTEM, None)

    def _handle_invalidate_player(self, msg: Packet) -> None:
        guid = msg.read_long_le()
        self.player_roster.pop(guid, None)

    def _handle_warden_data(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        if global_state.config.wow.platform.value == "Windows":
            log("ERROR", Tags.GAME, "WARDEN ON WINDOWS IS NOT SUPPORTED!")
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
        pw.write_int_le(0)
        pw.write_int_le(100)
        pw.write_bytes(name.encode("utf-8"))
        pw.write_byte(0)
        pw.write_byte(0)
        pw.write_int_le(0xFFFFFFFF)
        pw.write_int_le(0xFFFFFFFF)
        pw.write_int_le(0)
        pw.write_int_le(0)
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
        """
        Build a CMSG_PING response with randomised latency.

        Returns:
            Encoded ping response packet bytes.
        """
        latency = random.randint(90, 139)
        pw = PacketWriter()
        pw.write_int_le(self._ping_id)
        pw.write_int_le(latency)
        self._ping_id += 1
        return pw.build()
