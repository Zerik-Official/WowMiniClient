"""
Game packet encoders per expansion.
Merged from GamePacketEncoder, GamePacketEncoderCataclysm, GamePacketEncoderMoP.
"""

from __future__ import annotations

import struct

from common.types import global_state
from game.core.packets import GamePackets, GamePacketsCataclysm, GamePacketsMoP
from utils.logger import Tags, log


class GamePacketEncoder(GamePackets):
    """Vanilla/TBC/WotLK packet encoder."""

    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
        """
        Encode a packet with header for the Vanilla/TBC/WotLK protocol.

        Args:
            msg_id: Opcode of the packet.
            payload: Raw packet payload bytes.

        Returns:
            Fully encoded packet including encrypted header.
        """
        crypt = global_state.game_crypt
        unencrypted = msg_id == GamePacketEncoder.CMSG_AUTH_CHALLENGE
        header_size = 4 if unencrypted else 6

        size = len(payload) + header_size
        header = bytearray(header_size)
        header[0:2] = struct.pack(">H", size - 2)
        header[2:4] = struct.pack("<H", msg_id)

        if not unencrypted and crypt and crypt.is_init:
            header[4:6] = b"\x00\x00"
            header = bytearray(crypt.encrypt(list(header)))

        log("DEBUG", Tags.GAME, f"SEND PACKET: {msg_id:04X} - {payload.hex()}")

        result = bytearray(header)
        result.extend(payload)
        return bytes(result)


class GamePacketEncoderCataclysm(GamePacketEncoder, GamePacketsCataclysm):
    """Cataclysm packet encoder with WOW_CONNECTION support."""

    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
        """
        Encode a packet with header for the Cataclysm protocol.

        Also handles the WOW_CONNECTION handshake packet.

        Args:
            msg_id: Opcode of the packet.
            payload: Raw packet payload bytes.

        Returns:
            Fully encoded packet including encrypted header.
        """
        crypt = global_state.game_crypt
        unencrypted = (msg_id == GamePacketEncoderCataclysm.CMSG_AUTH_CHALLENGE or
                       msg_id == GamePacketEncoderCataclysm.WOW_CONNECTION)
        header_size = 4 if unencrypted else 6

        size = len(payload) + header_size
        header = bytearray(header_size)
        header[0:2] = struct.pack(">H", size - 2)
        header[2:4] = struct.pack("<H", msg_id)

        if not unencrypted and crypt and crypt.is_init:
            header[4:6] = b"\x00\x00"
            header = bytearray(crypt.encrypt(list(header)))

        log("DEBUG", Tags.GAME, f"SEND PACKET: {msg_id:04X} - {payload.hex()}")

        result = bytearray(header)
        result.extend(payload)
        return bytes(result)


class GamePacketEncoderMoP(GamePacketEncoderCataclysm, GamePacketsMoP):
    """MoP packet encoder with compact 4-byte header."""

    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
        """
        Encode a packet with header for the Mists of Pandaria protocol.

        Uses a compact 4-byte header with size and opcode packed together.

        Args:
            msg_id: Opcode of the packet.
            payload: Raw packet payload bytes.

        Returns:
            Fully encoded packet including encrypted header.
        """
        crypt = global_state.game_crypt
        unencrypted = (msg_id == GamePacketEncoderMoP.CMSG_AUTH_CHALLENGE or
                       msg_id == GamePacketEncoderMoP.WOW_CONNECTION)

        size = len(payload)
        header = bytearray(4)

        if unencrypted:
            header[0:2] = struct.pack("<H", size + 2)
            header[2:4] = struct.pack("<H", msg_id)
        else:
            packed = (size << 13) | (msg_id & 0x1FFF)
            struct.pack_into("<I", header, 0, packed)
            if crypt and crypt.is_init:
                header = bytearray(crypt.encrypt(list(header)))

        log("DEBUG", Tags.GAME, f"SEND PACKET: {msg_id:04X} - {payload.hex()}")

        result = bytearray(header)
        result.extend(payload)
        return bytes(result)
