"""Unit tests for game packet decoders: stream reassembly and header parsing."""

from __future__ import annotations

import struct
from collections.abc import Iterator

import pytest

from common.types import global_state
from crypto.header import GameHeaderCryptWotLK
from game.core.decoder import GamePacketDecoder, GamePacketDecoderWotLK

SESSION_KEY = bytes(range(40))


@pytest.fixture(autouse=True)
def _reset_crypt() -> Iterator[None]:
    """Ensure no header crypt leaks between tests."""
    global_state.game_crypt = None
    yield
    global_state.game_crypt = None


def _plain(opcode: int, payload: bytes) -> bytes:
    """Build an unencrypted server packet (big-endian size, LE opcode)."""
    return struct.pack(">H", len(payload) + 2) + struct.pack("<H", opcode) + payload


def _server_crypt_wotlk() -> GameHeaderCryptWotLK:
    """Build a crypt that mimics the server side (encrypts with server key)."""
    server = GameHeaderCryptWotLK()
    server.init(SESSION_KEY)
    server._client_crypt = server._server_crypt
    return server


def _wotlk_encrypted(server: GameHeaderCryptWotLK, opcode: int,
                     payload: bytes) -> bytes:
    """Build a WotLK server packet with a 4- or 5-byte encrypted header."""
    size = len(payload) + 2
    if size > 0x7FFF:
        header = bytearray([
            0x80 | ((size >> 16) & 0x7F), (size >> 8) & 0xFF, size & 0xFF,
            opcode & 0xFF, (opcode >> 8) & 0xFF,
        ])
    else:
        header = bytearray(struct.pack(">H", size) + struct.pack("<H", opcode))
    return bytes(server.encrypt(header)) + payload


def test_packet_split_across_reads() -> None:
    """A packet split over several reads is reassembled, not dropped."""
    decoder = GamePacketDecoder()
    raw = _plain(0x96, b"hello world")
    assert decoder.feed(raw[:3]) == []
    assert decoder.feed(raw[3:9]) == []
    assert decoder.feed(raw[9:]) == [(0x96, b"hello world")]


def test_multiple_packets_with_trailing_partial() -> None:
    """Leftover bytes of a following packet are kept for the next read."""
    decoder = GamePacketDecoder()
    raw = _plain(0x01, b"a") + _plain(0x02, b"bb") + _plain(0x03, b"ccc")
    cut = len(raw) - 2
    assert decoder.feed(raw[:cut]) == [(0x01, b"a"), (0x02, b"bb")]
    assert decoder.feed(raw[cut:]) == [(0x03, b"ccc")]


def test_empty_payload_does_not_stall() -> None:
    """Zero-length packets are emitted and do not block later packets."""
    decoder = GamePacketDecoder()
    raw = _plain(0x10, b"") + _plain(0x11, b"x")
    assert decoder.feed(raw) == [(0x10, b""), (0x11, b"x")]


def test_wotlk_encrypted_byte_by_byte() -> None:
    """Encrypted WotLK stream decodes correctly when fed one byte at a time."""
    server = _server_crypt_wotlk()
    client = GameHeaderCryptWotLK()
    client.init(SESSION_KEY)
    global_state.game_crypt = client

    big = bytes(0x8000)
    raw = (_wotlk_encrypted(server, 0x96, b"chat")
           + _wotlk_encrypted(server, 0x1A9, big)
           + _wotlk_encrypted(server, 0x99, b"")
           + _wotlk_encrypted(server, 0x3B, b"z"))

    decoder = GamePacketDecoderWotLK()
    packets: list[tuple[int, bytes]] = []
    for i in range(len(raw)):
        packets.extend(decoder.feed(raw[i:i + 1]))

    assert packets == [(0x96, b"chat"), (0x1A9, big), (0x99, b""), (0x3B, b"z")]
