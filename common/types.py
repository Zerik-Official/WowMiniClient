from __future__ import annotations

import struct
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WowExpansion(StrEnum):
    """Supported World of Warcraft expansions."""

    VANILLA = "1.12.1"
    TBC = "2.4.3"
    WOTLK = "3.3.5"
    CATACLYSM = "4.3.4"
    MOP = "5.4.8"

    @staticmethod
    def from_version(version: str) -> WowExpansion:
        """
        Resolve an expansion from a version string.

        Args:
            version: Game version string (e.g. "1.12.1", "3.3.5").

        Returns:
            The matching WowExpansion enum member.

        Raises:
            ValueError: If the version is not supported.
        """
        if version.startswith("1."):
            return WowExpansion.VANILLA
        if version.startswith("2."):
            return WowExpansion.TBC
        if version.startswith("3."):
            return WowExpansion.WOTLK
        if version == "4.3.4":
            return WowExpansion.CATACLYSM
        if version == "5.4.8":
            return WowExpansion.MOP
        msg = f"Version {version} not supported!"
        raise ValueError(msg)


class Platform(StrEnum):
    """Client platform (Windows or Mac)."""

    WINDOWS = "Windows"
    MAC = "Mac"

    @staticmethod
    def from_string(value: str) -> Platform:
        """
        Parse a platform string into a Platform enum.

        Args:
            value: Platform string ("win", "windows", "mac", etc.).

        Returns:
            The matching Platform member.
        """
        if value.lower() in ("win", "windows"):
            return Platform.WINDOWS
        return Platform.MAC


class ChatDirection(StrEnum):
    """Direction of chat message relay."""

    BOTH = "both"
    WOW_TO_DISCORD = "wow_to_discord"
    DISCORD_TO_WOW = "discord_to_wow"


@dataclass
class FiltersConfig:
    """Message filtering rules."""

    enabled: bool
    patterns: list[str]


@dataclass(frozen=True)
class DiscordChannelConfig:
    """Discord-side channel relay configuration."""

    channel: str
    format: str
    filters: FiltersConfig | None = field(default=None, compare=False, hash=False)


@dataclass(frozen=True)
class WowChannelConfig:
    """WoW-side channel relay configuration."""

    type: int
    channel: str | None = None
    id: int | None = None
    format: str = ""
    filters: FiltersConfig | None = field(default=None, compare=False, hash=False)


@dataclass
class ChannelConfig:
    """Bidirectional channel relay mapping."""

    chat_direction: ChatDirection
    wow: WowChannelConfig
    discord: DiscordChannelConfig


@dataclass
class GuildNotificationConfig:
    """Configuration for a specific guild event notification."""

    enabled: bool
    format: str
    channel: str | None = None


@dataclass
class GuildConfig:
    """Guild event notification settings."""

    notification_configs: dict[str, GuildNotificationConfig] = field(
        default_factory=dict
    )


@dataclass
class RealmListConfig:
    """Realm list server connection parameters."""

    name: str
    host: str
    port: int


@dataclass
class DiscordConfig:
    """Discord bot configuration."""

    token: str
    enable_dot_commands: bool = True
    dot_commands_whitelist: set[str] = field(default_factory=set)
    enable_commands_channels: set[str] = field(default_factory=set)
    enable_tag_failed_notifications: bool = True
    item_database: str | None = None


@dataclass
class WowConfig:
    """WoW client configuration (account, realm, character)."""

    locale: str
    platform: Platform
    version: str
    expansion: WowExpansion
    realm_build: int | None
    game_build: int | None
    realmlist: RealmListConfig
    account: bytes
    password: str
    character: str
    enable_server_motd: bool


@dataclass
class WowChatConfig:
    """Root configuration holding all sub-configurations."""

    discord: DiscordConfig
    wow: WowConfig
    guild: GuildConfig
    channels: list[ChannelConfig]
    filters: FiltersConfig | None = None


class Packet:
    """
    WoW network packet with sequential reading and bit-level support.
    """

    def __init__(self, id: int, data: bytes = b"") -> None:
        self.id = id
        self.data = bytearray(data)
        self._pos = 0
        self._bit_pos = 7
        self._current_byte = 0

    def remaining(self) -> int:
        """Return the number of unread bytes."""
        return len(self.data) - self._pos

    def read_byte(self) -> int:
        """Read a single byte."""
        val = self.data[self._pos]
        self._pos += 1
        return val

    def read_short(self) -> int:
        """Read a big-endian 16-bit unsigned short."""
        val = struct.unpack_from(">H", self.data, self._pos)[0]
        self._pos += 2
        return val  # type: ignore[no-any-return]

    def read_short_le(self) -> int:
        """Read a little-endian 16-bit unsigned short."""
        val = struct.unpack_from("<H", self.data, self._pos)[0]
        self._pos += 2
        return val  # type: ignore[no-any-return]

    def read_int(self) -> int:
        """Read a big-endian 32-bit unsigned int."""
        val = struct.unpack_from(">I", self.data, self._pos)[0]
        self._pos += 4
        return val  # type: ignore[no-any-return]

    def read_int_le(self) -> int:
        """Read a little-endian 32-bit unsigned int."""
        val = struct.unpack_from("<I", self.data, self._pos)[0]
        self._pos += 4
        return val  # type: ignore[no-any-return]

    def read_long_le(self) -> int:
        """Read a little-endian 64-bit unsigned long."""
        val = struct.unpack_from("<Q", self.data, self._pos)[0]
        self._pos += 8
        return val  # type: ignore[no-any-return]

    def read_float_le(self) -> float:
        """Read a little-endian 32-bit float."""
        val = struct.unpack_from("<f", self.data, self._pos)[0]
        self._pos += 4
        return val  # type: ignore[no-any-return]

    def read_boolean(self) -> bool:
        """Read a single byte as boolean."""
        return self.read_byte() != 0

    def read_string(self) -> str:
        """
        Read a null-terminated UTF-8 string from the current position.

        Returns:
            Decoded string.
        """
        end = self.data.find(b"\x00", self._pos)
        if end == -1:
            result = bytes(self.data[self._pos :])
            self._pos = len(self.data)
        else:
            result = bytes(self.data[self._pos : end])
            self._pos = end + 1
        return result.decode("utf-8", errors="replace")

    def skip(self, n: int) -> None:
        """Advance the read position by *n* bytes."""
        self._pos += n

    def skip_string(self) -> None:
        """Skip past the next null-terminated string."""
        end = self.data.find(b"\x00", self._pos)
        if end == -1:
            self._pos = len(self.data)
        else:
            self._pos = end + 1

    def reset_bit_reader(self) -> None:
        """Reset the bit-level reader state."""
        self._bit_pos = 7
        self._current_byte = 0

    def read_bit(self) -> int:
        """
        Read a single bit (used by Cataclysm+ parsing).

        Returns:
            0 or 1.
        """
        self._bit_pos += 1
        if self._bit_pos > 7:
            self._bit_pos = 0
            self._current_byte = self.read_byte()
        return (self._current_byte >> (7 - self._bit_pos)) & 1

    def read_bits(self, length: int) -> int:
        """
        Read an unsigned integer composed of multiple bits (MSB first).

        Args:
            length: Number of bits to read.

        Returns:
            Integer value.
        """
        result = 0
        for i in range(length - 1, -1, -1):
            result |= self.read_bit() << i
        return result

    def read_bit_seq(self, mask: list[int], *indices: int) -> None:
        """Read bits into specific indices of *mask*."""
        for i in indices:
            mask[i] = self.read_bit()

    def read_xor_byte(self, mask: int) -> int:
        """Read a byte XORed with *mask* (0 = skip)."""
        if mask != 0:
            return mask ^ self.read_byte()
        return mask

    def read_xor_byte_seq(self, mask: list[int], *indices: int) -> None:
        """Read and XOR bytes into specific indices of *mask*."""
        for i in indices:
            mask[i] = self.read_xor_byte(mask[i])

    def slice(self, size: int) -> bytes:
        """Read and return *size* bytes as a new bytes object."""
        result = bytes(self.data[self._pos : self._pos + size])
        self._pos += size
        return result


class PacketWriter:
    """Helper for building packet payloads with sequential writes."""

    def __init__(self) -> None:
        self.data = bytearray()

    def write_byte(self, val: int) -> None:
        """Write a single byte."""
        self.data.append(val & 0xFF)

    def write_short(self, val: int) -> None:
        """Write a big-endian 16-bit unsigned short."""
        self.data.extend(struct.pack(">H", val & 0xFFFF))

    def write_short_le(self, val: int) -> None:
        """Write a little-endian 16-bit unsigned short."""
        self.data.extend(struct.pack("<H", val & 0xFFFF))

    def write_int(self, val: int) -> None:
        """Write a big-endian 32-bit unsigned int."""
        self.data.extend(struct.pack(">I", val & 0xFFFFFFFF))

    def write_int_le(self, val: int) -> None:
        """Write a little-endian 32-bit unsigned int."""
        self.data.extend(struct.pack("<I", val & 0xFFFFFFFF))

    def write_long_le(self, val: int) -> None:
        """Write a little-endian 64-bit unsigned long."""
        self.data.extend(struct.pack("<Q", val & 0xFFFFFFFFFFFFFFFF))

    def write_float_le(self, val: float) -> None:
        """Write a little-endian 32-bit float."""
        self.data.extend(struct.pack("<f", val))

    def write_bytes(self, val: bytes) -> None:
        """Write raw bytes."""
        self.data.extend(val)

    def write_zeros(self, n: int) -> None:
        """Write *n* zero bytes."""
        self.data.extend(b"\x00" * n)

    def build(self) -> bytes:
        """Return the accumulated payload bytes."""
        return bytes(self.data)


class PacketBitWriter:
    """Bit-level writer for Cataclysm+ message building."""

    def __init__(self) -> None:
        self.data = bytearray()
        self._bit_pos = 8
        self._current_byte = 0

    def write_bit(self, bit: int) -> None:
        """Write a single bit."""
        self._bit_pos -= 1
        if bit:
            self._current_byte |= 1 << self._bit_pos
        if self._bit_pos == 0:
            self.flush()

    def write_bits(self, value: int, bit_count: int) -> None:
        """Write multiple bits (MSB first)."""
        for i in range(bit_count - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def write_bit_seq(self, mask: list[int], *indices: int) -> None:
        """Write bits from specific indices of *mask*."""
        for i in indices:
            self.write_bit(mask[i])

    def write_xor_byte(self, byte: int) -> None:
        """Write a byte XORed with 1 if non-zero."""
        if byte != 0:
            self.write_byte((byte ^ 1) & 0xFF)

    def write_xor_byte_seq(self, mask: list[int], *indices: int) -> None:
        """Write XOR bytes from specific indices of *mask*."""
        for i in indices:
            self.write_xor_byte(mask[i])

    def write_byte(self, val: int) -> None:
        """Write a raw byte (flushes pending bits first)."""
        self.flush()
        self.data.append(val & 0xFF)

    def write_int_le(self, val: int) -> None:
        """Write a little-endian 32-bit int (flushes bits first)."""
        self.flush()
        self.data.extend(struct.pack("<I", val & 0xFFFFFFFF))

    def write_bytes(self, val: bytes) -> None:
        """Write raw bytes (flushes bits first)."""
        self.flush()
        self.data.extend(val)

    def flush(self) -> None:
        """Flush remaining bits as a byte."""
        if self._bit_pos < 8:
            self.data.append(self._current_byte & 0xFF)
            self._bit_pos = 8
            self._current_byte = 0

    def build(self) -> bytes:
        """Flush and return the accumulated bytes."""
        self.flush()
        return bytes(self.data)


class _Global:
    """
    Shared application-wide mutable state.

    Avoids a singleton pattern in favor of a single module-level instance.
    """

    def __init__(self) -> None:
        self.config: WowChatConfig = None  # type: ignore[assignment]

        self.discord_to_wow: dict[str, set[WowChannelConfig]] = defaultdict(set)
        self.wow_to_discord: dict[
            tuple[int, str | None], set[tuple[str, DiscordChannelConfig]]
        ] = defaultdict(set)
        self.wow_channel_filters: dict[tuple[int, str | None], FiltersConfig] = {}
        self.guild_events_to_discord: dict[str, set[str]] = defaultdict(set)

        self.realm_build: int = 0
        self.game_build: int = 0
        self.expansion: WowExpansion = WowExpansion.VANILLA
        self.game_crypt: Any = None


global_state = _Global()
