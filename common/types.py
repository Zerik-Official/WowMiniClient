from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final


class WowExpansion(StrEnum):
    """Supported World of Warcraft expansions."""

    VANILLA: str = "1.12.1"
    TBC: str = "2.4.3"
    WOTLK: str = "3.3.5"
    CATACLYSM: str = "4.3.4"
    MOP: str = "5.4.8"

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

    WINDOWS: Final[str] = "Windows"
    MAC: Final[str] = "Mac"

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

    BOTH: Final[str] = "both"
    WOW_TO_DISCORD: Final[str] = "wow_to_discord"
    DISCORD_TO_WOW: Final[str] = "discord_to_wow"


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
    bot_system_channel: str | None = None
    enable_dot_commands: bool = True
    dot_commands_whitelist: set[str] = field(default_factory=set)
    enable_commands_channels: set[str] = field(default_factory=set)
    enable_tag_failed_notifications: bool = True
    item_database: str | None = None
    raid_icons: dict[int, str] = field(default_factory=dict)
    gm_icon: str | None = None


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
