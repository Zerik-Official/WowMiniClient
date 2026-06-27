"""
Game packet decoders per expansion.
Merged from GamePacketDecoder through GamePacketDecoderMoP.
"""

from __future__ import annotations

import struct
import zlib

from common.types import global_state
from game.core.packets import GamePackets, GamePacketsCataclysm, GamePacketsMoP
from utils.logger import Tags, log


class GamePacketDecoder(GamePackets):
    """Vanilla/TBC packet decoder with header parsing and decryption."""

    HEADER_LENGTH = 4

    def __init__(self) -> None:
        self._size = 0
        self._id = 0

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        """
        Parse raw TCP data into a list of decoded packets.

        Handles header parsing, decryption, and decompression.

        Args:
            data: Raw bytes received from the server.

        Returns:
            List of (opcode, payload) tuples for each complete packet.
        """
        packets: list[tuple[int, bytes]] = []
        buf = bytearray(data)
        while len(buf) >= self.HEADER_LENGTH:
            if self._size == 0 and self._id == 0:
                crypt = global_state.game_crypt
                header = bytes(buf[: self.HEADER_LENGTH])
                if crypt and crypt.is_init:
                    decrypted = crypt.decrypt(list(header))
                    self._id, self._size = self._parse_header_encrypted(decrypted)
                else:
                    self._id, self._size = self._parse_header(header)
                buf = buf[self.HEADER_LENGTH :]

            if self._size > 0 and len(buf) >= self._size:
                payload = bytes(buf[: self._size])
                buf = buf[self._size :]
                new_id, decompressed = self._decompress(self._id, payload)
                log("DEBUG", Tags.GAME, f"RECV PACKET: {new_id:04X} - {decompressed.hex()}")
                packets.append((new_id, decompressed))
                self._size = 0
                self._id = 0
            else:
                break
        return packets

    def _parse_header(self, header: bytes) -> tuple[int, int]:
        size = struct.unpack(">H", header[:2])[0] - 2
        id_ = struct.unpack("<H", header[2:4])[0]
        return id_, size

    def _parse_header_encrypted(self, decrypted: list[int]) -> tuple[int, int]:
        size = ((decrypted[0] & 0xFF) << 8 | decrypted[1] & 0xFF) - 2
        id_ = (decrypted[3] & 0xFF) << 8 | decrypted[2] & 0xFF
        return id_, size

    def _decompress(self, id_: int, data: bytes) -> tuple[int, bytes]:
        return id_, data


class GamePacketDecoderWotLK(GamePacketDecoder):
    """WotLK packet decoder with extended encrypted header format."""

    def _parse_header_encrypted(self, decrypted: list[int]) -> tuple[int, int]:
        if (decrypted[0] & 0x80) == 0x80:
            crypt = global_state.game_crypt
            if crypt:
                next_byte = crypt.decrypt([0])[0]
                size = (
                    ((decrypted[0] & 0x7F) << 16)
                    | ((decrypted[1] & 0xFF) << 8)
                    | (decrypted[2] & 0xFF)
                ) - 2
                id_ = ((next_byte & 0xFF) << 8) | (decrypted[3] & 0xFF)
                return id_, size
            return self._parse_header_encrypted(decrypted)
        size = ((decrypted[0] & 0xFF) << 8 | decrypted[1] & 0xFF) - 2
        id_ = (decrypted[3] & 0xFF) << 8 | decrypted[2] & 0xFF
        return id_, size


class GamePacketDecoderCataclysm(GamePacketDecoderWotLK, GamePacketsCataclysm):
    """Cataclysm packet decoder with zlib decompression."""

    def __init__(self) -> None:
        super().__init__()
        self._inflater = zlib.decompressobj()

    def _decompress(self, id_: int, data: bytes) -> tuple[int, bytes]:
        if self._is_compressed(id_):
            decompressed_size = struct.unpack("<I", data[:4])[0]
            compressed = data[4:]
            decompressed = self._inflater.decompress(compressed)
            new_id = id_ ^ self.COMPRESSED_DATA_MASK
            return new_id, decompressed[:decompressed_size]
        return id_, data

    @staticmethod
    def _is_compressed(id_: int) -> bool:
        return (
            id_ & GamePacketsCataclysm.COMPRESSED_DATA_MASK
        ) == GamePacketsCataclysm.COMPRESSED_DATA_MASK


class GamePacketDecoderMoP(GamePacketDecoderCataclysm, GamePacketsMoP):
    """MoP packet decoder with compact header and SMSG_COMPRESSED_DATA."""

    def __init__(self) -> None:
        super().__init__()
        self._inflater = zlib.decompressobj(-zlib.MAX_WBITS)

    def _parse_header(self, header: bytes) -> tuple[int, int]:
        size = struct.unpack("<H", header[:2])[0] - 2
        id_ = struct.unpack("<H", header[2:4])[0]
        return id_, size

    def _parse_header_encrypted(self, decrypted: list[int]) -> tuple[int, int]:
        raw = (
            (decrypted[3] << 24)
            | (decrypted[2] << 16)
            | (decrypted[1] << 8)
            | decrypted[0]
        )
        id_ = raw & 0x1FFF
        size = raw >> 13
        return id_, size

    def _decompress(self, id_: int, data: bytes) -> tuple[int, bytes]:
        if id_ == self.SMSG_COMPRESSED_DATA:
            decompressed_size = struct.unpack("<I", data[:4])[0]
            data = data[12:]
            decompressed = self._inflater.decompress(data)
            new_id = struct.unpack("<H", decompressed[:2])[0]
            payload = decompressed[4:]
            return new_id, payload[:decompressed_size]
        return id_, data
