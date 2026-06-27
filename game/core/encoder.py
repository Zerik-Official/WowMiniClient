"""
Game packet encoders per expansion.
Merged from GamePacketEncoder, GamePacketEncoderCataclysm, GamePacketEncoderMoP.
"""

from __future__ import annotations

import logging
import struct

from common.types import global_state
from game.core.packets import GamePackets, GamePacketsCataclysm, GamePacketsMoP

logger = logging.getLogger(__name__)


class GamePacketEncoder(GamePackets):
    @staticmethod
    def encode(msg_id: int, payload: bytes) -> bytes:
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
