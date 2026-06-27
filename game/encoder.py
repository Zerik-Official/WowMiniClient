"""
Game packet encoders per expansion.
Merged from GamePacketEncoder, GamePacketEncoderCataclysm, GamePacketEncoderMoP.
"""

from __future__ import annotations

import logging
import struct

from common.types import global_state
from game.packets import GamePackets, GamePacketsCataclysm, GamePacketsMoP

logger = logging.getLogger(__name__)


class GamePacketEncoder(GamePackets):
    """Base packet encoder. 4-byte header (unencrypted) or 6-byte (encrypted)."""

    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
        """
        Encode a packet for sending.

        Args:
            msg_id: Opcode.
            payload: Packet body bytes.

        Returns:
            Encoded binary packet (header + body).
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

        logger.debug("SEND PACKET: %04X - %s", msg_id, payload.hex())

        result = bytearray(header)
        result.extend(payload)
        return bytes(result)


class GamePacketEncoderCataclysm(GamePacketEncoder, GamePacketsCataclysm):
    """Cataclysm encoder: also allows WOW_CONNECTION as unencrypted."""

    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
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

        logger.debug("SEND PACKET: %04X - %s", msg_id, payload.hex())

        result = bytearray(header)
        result.extend(payload)
        return bytes(result)


class GamePacketEncoderMoP(GamePacketEncoderCataclysm, GamePacketsMoP):
    """MoP encoder: 4-byte bit-packed header (size << 13 | id & 0x1FFF)."""

    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
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

        logger.debug("SEND PACKET: %04X - %s", msg_id, payload.hex())

        result = bytearray(header)
        result.extend(payload)
        return bytes(result)
