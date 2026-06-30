"""
Byte and hex conversion utilities for WoW protocol data.
"""

import struct


def short_to_bytes(value: int) -> bytes:
    """
    Pack an integer as a big-endian 16-bit unsigned short.

    Args:
        value: Integer to pack (only lower 16 bits are used).

    Returns:
        A 2-byte big-endian representation.
    """
    return struct.pack(">H", value & 0xFFFF)


def short_to_bytes_le(value: int) -> bytes:
    """
    Pack an integer as a little-endian 16-bit unsigned short.

    Args:
        value: Integer to pack (only lower 16 bits are used).

    Returns:
        A 2-byte little-endian representation.
    """
    return struct.pack("<H", value & 0xFFFF)


def int_to_bytes(value: int) -> bytes:
    """
    Pack an integer as a big-endian 32-bit unsigned int.

    Args:
        value: Integer to pack (only lower 32 bits are used).

    Returns:
        A 4-byte big-endian representation.
    """
    return struct.pack(">I", value & 0xFFFFFFFF)


def int_to_bytes_le(value: int) -> bytes:
    """
    Pack an integer as a little-endian 32-bit unsigned int.

    Args:
        value: Integer to pack (only lower 32 bits are used).

    Returns:
        A 4-byte little-endian representation.
    """
    return struct.pack("<I", value & 0xFFFFFFFF)


def long_to_bytes(value: int) -> bytes:
    """
    Pack an integer as a big-endian 64-bit unsigned long.

    Args:
        value: Integer to pack (only lower 64 bits are used).

    Returns:
        An 8-byte big-endian representation.
    """
    return struct.pack(">Q", value & 0xFFFFFFFFFFFFFFFF)


def long_to_bytes_le(value: int) -> bytes:
    """
    Pack an integer as a little-endian 64-bit unsigned long.

    Args:
        value: Integer to pack (only lower 64 bits are used).

    Returns:
        An 8-byte little-endian representation.
    """
    return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)


def bytes_to_long(data: bytes) -> int:
    """
    Unpack bytes as a big-endian unsigned integer.

    Args:
        data: Bytes to unpack.

    Returns:
        Unpacked integer.
    """
    return int.from_bytes(data, byteorder="big", signed=False)


def bytes_to_long_le(data: bytes) -> int:
    """
    Unpack bytes as a little-endian unsigned integer.

    Args:
        data: Bytes to unpack.

    Returns:
        Unpacked integer.
    """
    return int.from_bytes(data, byteorder="little", signed=False)


def string_to_int(text: str) -> int:
    """
    Convert a string to an integer by interpreting its UTF-8 bytes as big-endian.

    Args:
        text: Input string.

    Returns:
        Integer representation of the string's bytes.
    """
    return bytes_to_long(text.encode("utf-8"))


def to_hex_string(
    data: bytes, add_spaces: bool = False, resolve_plaintext: bool = True
) -> str:
    """
    Format bytes as a hexadecimal string, optionally resolving printable chars.

    Args:
        data: Bytes to format.
        add_spaces: Whether to add space separators between bytes.
        resolve_plaintext: When True, printable ASCII characters are shown as
            the character followed by a space instead of hex.

    Returns:
        Formatted hex string.
    """
    parts: list[str] = []
    for byte in data:
        if resolve_plaintext and 0x20 <= byte < 0x7F:
            parts.append(f"{chr(byte)} ")
        else:
            parts.append(f"{byte:02X}")
        if add_spaces:
            parts.append(" ")
    return "".join(parts).strip()


def to_binary_string(data: bytes) -> str:
    """
    Format bytes as a binary string, 4 bytes per line.

    Args:
        data: Bytes to format.

    Returns:
        Binary representation with line breaks every 4 bytes.
    """
    parts: list[str] = []
    for i, byte in enumerate(data):
        if i != 0 and i % 4 == 0:
            parts.append("\n")
        parts.append(f"{byte:08b} ")
    return "".join(parts).strip()
