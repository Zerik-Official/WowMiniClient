from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


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


@dataclass
class DiscordChannelConfig:
    """Discord-side channel relay configuration."""

    channel: str
    format: str
    filters: FiltersConfig | None = None


@dataclass
class WowChannelConfig:
    """WoW-side channel relay configuration."""

    type: int
    channel: str | None = None
    id: int | None = None
    format: str = ""
    filters: FiltersConfig | None = None


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


@dataclass
class Packet:
    """
    WoW network packet with bit-level reading support for Cataclysm+.
    """

    id: int
    data: bytearray = field(default_factory=bytearray)
    _bit_pos: int = 7
    _current_byte: int = 0

    def read_string(self) -> str:
        """
        Read a null-terminated UTF-8 string from the packet data.

        Returns:
            Decoded string.
        """
        end = self.data.find(b"\x00")
        if end == -1:
            result = bytes(self.data)
            self.data.clear()
        else:
            result = bytes(self.data[:end])
            del self.data[: end + 1]
        return result.decode("utf-8", errors="replace")

    def skip_string(self) -> Packet:
        """
        Skip a null-terminated string without reading it.

        Returns:
            Self for method chaining.
        """
        end = self.data.find(b"\x00")
        if end == -1:
            self.data.clear()
        else:
            del self.data[: end + 1]
        return self

    def reset_bit_reader(self) -> None:
        """Reset the bit-level reader state."""
        self._bit_pos = 7
        self._current_byte = 0

    def read_bit(self) -> int:
        """
        Read a single bit from the packet (used by Cataclysm+ parsing).

        Returns:
            0 or 1.
        """
        self._bit_pos += 1
        if self._bit_pos > 7:
            self._bit_pos = 0
            self._current_byte = self.data.pop(0)
        return (self._current_byte >> (7 - self._bit_pos)) & 1

    def read_bits(self, length: int) -> int:
        """
        Read an unsigned integer composed of multiple bits.

        Args:
            length: Number of bits to read.

        Returns:
            Integer value assembled from bits (MSB first).
        """
        result = 0
        for i in range(length - 1, -1, -1):
            result |= self.read_bit() << i
        return result

    def read_bit_seq(self, mask: list[int], *indices: int) -> None:
        """
        Read bits into specific positions of a mask array.

        Args:
            mask: Byte array to write bits into.
            indices: Positions in the mask to fill.
        """
        for i in indices:
            mask[i] = self.read_bit()

    def read_xor_byte(self, mask: int) -> int:
        """
        Read a byte XORed with a mask value.

        Args:
            mask: XOR mask (0 skips the read).

        Returns:
            XORed byte value.
        """
        if mask != 0:
            return mask ^ self.data.pop(0)
        return mask

    def read_xor_byte_seq(self, mask: list[int], *indices: int) -> None:
        """
        Read and XOR multiple bytes into specific positions of a mask array.

        Args:
            mask: Byte array to XOR values into.
            indices: Positions in the mask to fill.
        """
        for i in indices:
            mask[i] = self.read_xor_byte(mask[i])


class _Global:
    """
    Shared application-wide mutable state.

    Avoids a singleton pattern in favor of a single module-level instance.
    """

    def __init__(self) -> None:
        self.config: WowChatConfig

        self.discord_to_wow: dict[str, set[WowChannelConfig]] = defaultdict(set)
        self.wow_to_discord: dict[
            tuple[int, str | None], set[tuple[str, DiscordChannelConfig]]
        ] = defaultdict(set)
        self.guild_events_to_discord: dict[str, set[str]] = defaultdict(set)

        self.realm_build: int = 0
        self.game_build: int = 0
        self.expansion: WowExpansion = WowExpansion.VANILLA


global_state = _Global()
