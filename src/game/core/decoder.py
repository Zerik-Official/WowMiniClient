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
    """
    Vanilla/TBC packet decoder with header parsing and decryption.
    """

    HEADER_LENGTH = 4

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._has_header = False
        self._decrypted_header: list[int] | None = None
        self._size = 0
        self._id = 0

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        """
        Parse raw TCP data into a list of decoded packets.

        Handles header parsing, decryption, and decompression. Incomplete
        headers or payloads stay buffered until more data arrives.

        Args:
            data: Raw bytes received from the server.

        Returns:
            List of (opcode, payload) tuples for each complete packet.
        """
        packets: list[tuple[int, bytes]] = []
        self._buffer.extend(data)
        while True:
            if not self._has_header and not self._read_header():
                break
            if len(self._buffer) < self._size:
                break

            payload = bytes(self._buffer[: self._size])
            del self._buffer[: self._size]
            new_id, decompressed = self._decompress(self._id, payload)
            log("DEBUG", Tags.GAME, f"RECV PACKET: {new_id:04X} - {decompressed.hex()}")
            packets.append((new_id, decompressed))
            self._has_header = False
            self._size = 0
            self._id = 0
        return packets

    def _read_header(self) -> bool:
        """
        Consume and parse the next packet header from the buffer.

        Encrypted headers are decrypted exactly once; if an extended header
        needs extra bytes that have not arrived yet, the decrypted part is
        kept so the stream cipher never processes the same bytes twice.

        Returns:
            True if a full header was parsed, False if more data is needed.
        """
        crypt = global_state.game_crypt
        if crypt is None or not crypt.is_init:
            if len(self._buffer) < self.HEADER_LENGTH:
                return False
            header = bytes(self._buffer[: self.HEADER_LENGTH])
            del self._buffer[: self.HEADER_LENGTH]
            self._id, self._size = self._parse_header(header)
            self._has_header = True
            return True

        if self._decrypted_header is None:
            if len(self._buffer) < self.HEADER_LENGTH:
                return False
            header = bytearray(self._buffer[: self.HEADER_LENGTH])
            del self._buffer[: self.HEADER_LENGTH]
            self._decrypted_header = list(crypt.decrypt(header))

        extra_length = self._extra_header_length(self._decrypted_header)
        if len(self._buffer) < extra_length:
            return False
        extra: list[int] = []
        if extra_length:
            extra = list(crypt.decrypt(bytearray(self._buffer[:extra_length])))
            del self._buffer[:extra_length]

        self._id, self._size = self._parse_header_encrypted(
            self._decrypted_header, extra,
        )
        self._decrypted_header = None
        self._has_header = True
        return True

    def _extra_header_length(self, decrypted: list[int]) -> int:
        """
        Number of encrypted header bytes that follow the first four.

        Args:
            decrypted: 4-byte decrypted header as integer list.

        Returns:
            Extra header byte count (always 0 before WotLK).
        """
        return 0

    def _parse_header(self, header: bytes) -> tuple[int, int]:
        """
        Parse a 4-byte plain header into opcode and size.

        Args:
            header: 4-byte header bytes.

        Returns:
            Tuple of (opcode, payload_size).
        """
        size = struct.unpack(">H", header[:2])[0] - 2
        id_ = struct.unpack("<H", header[2:4])[0]
        return id_, size

    def _parse_header_encrypted(self, decrypted: list[int],
                                extra: list[int]) -> tuple[int, int]:
        """
        Parse a decrypted 4-byte header into opcode and size.

        Args:
            decrypted: 4-byte decrypted header as integer list.
            extra: Decrypted extended header bytes (unused before WotLK).

        Returns:
            Tuple of (opcode, payload_size).
        """
        size = ((decrypted[0] & 0xFF) << 8 | decrypted[1] & 0xFF) - 2
        id_ = (decrypted[3] & 0xFF) << 8 | decrypted[2] & 0xFF
        return id_, size

    def _decompress(self, id_: int, data: bytes) -> tuple[int, bytes]:
        """
        Pass-through decompression (no compression in Vanilla/TBC).

        Args:
            id_: Original opcode.
            data: Payload bytes.

        Returns:
            Unmodified (opcode, data) tuple.
        """
        return id_, data


class GamePacketDecoderWotLK(GamePacketDecoder):
    """WotLK packet decoder with extended encrypted header format."""

    def _extra_header_length(self, decrypted: list[int]) -> int:
        """
        WotLK headers carry one extra byte when the size exceeds 0x7FFF.

        Args:
            decrypted: 4-byte decrypted header as integer list.

        Returns:
            1 if the high bit of the first byte is set, otherwise 0.
        """
        return 1 if (decrypted[0] & 0x80) == 0x80 else 0

    def _parse_header_encrypted(self, decrypted: list[int],
                                extra: list[int]) -> tuple[int, int]:
        """
        Parse a potentially 5-byte encrypted header for WotLK.

        When the high bit of the first byte is set, the header is 5 bytes
        and the fifth (decrypted) byte holds the upper opcode bits.
        Otherwise it follows the standard 4-byte format.

        Args:
            decrypted: 4-byte decrypted header as integer list.
            extra: Decrypted fifth header byte, or empty for 4-byte headers.

        Returns:
            Tuple of (opcode, payload_size).
        """
        if extra:
            size = (
                ((decrypted[0] & 0x7F) << 16)
                | ((decrypted[1] & 0xFF) << 8)
                | (decrypted[2] & 0xFF)
            ) - 2
            id_ = ((extra[0] & 0xFF) << 8) | (decrypted[3] & 0xFF)
            return id_, size
        size = ((decrypted[0] & 0xFF) << 8 | decrypted[1] & 0xFF) - 2
        id_ = (decrypted[3] & 0xFF) << 8 | decrypted[2] & 0xFF
        return id_, size


class GamePacketDecoderCataclysm(GamePacketDecoderWotLK, GamePacketsCataclysm):
    """Cataclysm packet decoder with zlib decompression."""

    def __init__(self) -> None:
        super().__init__()
        self._inflater = zlib.decompressobj()

    def _decompress(self, id_: int, data: bytes) -> tuple[int, bytes]:
        """
        Decompress zlib-compressed Cataclysm data packets.

        Packets with the COMPRESSED_DATA_MASK bit set are zlib-compressed.
        The first 4 bytes contain the uncompressed size.

        Args:
            id_: Raw opcode (may have compression mask).
            data: Payload bytes, possibly compressed.

        Returns:
            Tuple of (unmasked opcode, decompressed payload).
        """
        if self._is_compressed(id_):
            decompressed_size = struct.unpack("<I", data[:4])[0]
            compressed = data[4:]
            decompressed = self._inflater.decompress(compressed)
            new_id = id_ ^ self.COMPRESSED_DATA_MASK
            return new_id, decompressed[:decompressed_size]
        return id_, data

    @staticmethod
    def _is_compressed(id_: int) -> bool:
        """
        Check if the opcode has the Cataclysm compression bit set.

        Args:
            id_: Raw opcode.

        Returns:
            True if the compression flag is set.
        """
        return (
            id_ & GamePacketsCataclysm.COMPRESSED_DATA_MASK
        ) == GamePacketsCataclysm.COMPRESSED_DATA_MASK


class GamePacketDecoderMoP(GamePacketDecoderCataclysm, GamePacketsMoP):
    """MoP packet decoder with compact header and SMSG_COMPRESSED_DATA."""

    def __init__(self) -> None:
        super().__init__()
        self._inflater = zlib.decompressobj(-zlib.MAX_WBITS)

    def _parse_header(self, header: bytes) -> tuple[int, int]:
        """
        Parse a MoP 4-byte plain header (little-endian).

        Args:
            header: 4-byte header bytes.

        Returns:
            Tuple of (opcode, payload_size).
        """
        size = struct.unpack("<H", header[:2])[0] - 2
        id_ = struct.unpack("<H", header[2:4])[0]
        return id_, size

    def _extra_header_length(self, decrypted: list[int]) -> int:
        """
        MoP headers are always exactly 4 bytes.

        Args:
            decrypted: 4-byte decrypted header as integer list.

        Returns:
            Always 0.
        """
        return 0

    def _parse_header_encrypted(self, decrypted: list[int],
                                extra: list[int]) -> tuple[int, int]:
        """
        Parse a MoP 4-byte encrypted header (compact layout).

        Opcode is stored in the lower 13 bits; size occupies the remaining
        19 bits.

        Args:
            decrypted: 4-byte decrypted header as integer list.
            extra: Unused; MoP has no extended header.

        Returns:
            Tuple of (opcode, payload_size).
        """
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
        """
        Decompress a MoP SMSG_COMPRESSED_DATA packet.

        Uses a raw inflater (no zlib/gzip header). The server prepends the
        opcode and uncompressed size in the decompressed data.

        Args:
            id_: Opcode.
            data: Payload bytes (12-byte header + compressed data).

        Returns:
            Tuple of (inner opcode, decompressed payload).
        """
        if id_ == self.SMSG_COMPRESSED_DATA:
            decompressed_size = struct.unpack("<I", data[:4])[0]
            data = data[12:]
            decompressed = self._inflater.decompress(data)
            new_id = struct.unpack("<H", decompressed[:2])[0]
            payload = decompressed[4:]
            return new_id, payload[:decompressed_size]
        return id_, data
