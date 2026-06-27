"""
Configuration parser that reads wowchat.toml and builds WowChatConfig.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from common.chat import ChatEvents
from common.types import (
    ChannelConfig,
    ChatDirection,
    DiscordChannelConfig,
    DiscordConfig,
    FiltersConfig,
    GuildConfig,
    GuildNotificationConfig,
    Platform,
    RealmListConfig,
    WowChannelConfig,
    WowChatConfig,
    WowConfig,
    WowExpansion,
)

_VERSION_TO_BUILD: dict[str, int] = {
    "1.6.1": 4544,
    "1.6.2": 4565,
    "1.6.3": 4620,
    "1.7.1": 4695,
    "1.8.4": 4878,
    "1.9.4": 5086,
    "1.10.2": 5302,
    "1.11.2": 5464,
    "1.12.1": 5875,
    "1.12.2": 6005,
    "1.12.3": 6141,
    "2.4.3": 8606,
    "3.2.2": 10505,
    "3.3.0": 11159,
    "3.3.2": 11403,
    "3.3.3": 11723,
    "3.3.5": 12340,
    "4.3.4": 15595,
    "5.4.8": 18414,
}


def _build_from_version(version: str) -> int:
    """
    Map a version string to its corresponding game build number.

    Args:
        version: WoW version string (e.g. "1.12.1", "3.3.5").

    Returns:
        Build number integer.

    Raises:
        ValueError: If the version is not recognised.
    """
    build = _VERSION_TO_BUILD.get(version)
    if build is None:
        msg = f"Build {version} not supported!"
        raise ValueError(msg)
    return build


def _account_to_upper_bytes(account: str) -> bytes:
    """
    Convert account name to uppercase UTF-8 bytes, as required by the auth protocol.

    Args:
        account: Raw account name string.

    Returns:
        UTF-8 encoded uppercase bytes.
    """
    return "".join(
        c.upper() if "a" <= c <= "z" else c for c in account
    ).encode("utf-8")


def _parse_realmlist(realmlist: str, realm: str) -> RealmListConfig:
    """
    Parse a "host:port" string into a RealmListConfig.

    Args:
        realmlist: Host and optional port (e.g. "127.0.0.1:3724").
        realm: Realm display name.

    Returns:
        Parsed RealmListConfig (default port 3724).
    """
    parts = realmlist.rsplit(":", 1)
    host = parts[0]
    port = int(parts[1]) if len(parts) > 1 else 3724
    return RealmListConfig(name=realm, host=host, port=port)


def _env_fallback(key: str, default: Any = None) -> Any:
    """
    Return the environment variable value if set, otherwise the default.

    Args:
        key: Environment variable name.
        default: Fallback value if not set.

    Returns:
        The environment variable value or default.
    """
    return os.environ.get(key, default)


_GUILD_DEFAULTS: dict[str, tuple[bool, str]] = {
    "promoted": (True, "`[%user] has promoted [%target] to [%rank].`"),
    "demoted": (True, "`[%user] has demoted [%target] to [%rank].`"),
    "online": (False, "`[%user] has come online.`"),
    "offline": (False, "`[%user] has gone offline.`"),
    "joined": (True, "`[%user] has joined the guild.`"),
    "left": (True, "`[%user] has left the guild.`"),
    "removed": (True, "`[%target] has been kicked out of the guild by [%user].`"),
    "motd": (True, "`Guild Message of the Day: %message`"),
    "achievement": (True, "%user has earned the achievement %achievement!"),
}


def _parse_guild_config(data: dict[str, Any] | None) -> GuildConfig:
    """
    Build GuildConfig from parsed TOML data, applying defaults.

    Args:
        data: Guild section from config, or None.

    Returns:
        Fully resolved GuildConfig.
    """
    if not data:
        return GuildConfig(
            notification_configs={
                key: GuildNotificationConfig(enabled=enabled, format=fmt, channel=None)
                for key, (enabled, fmt) in _GUILD_DEFAULTS.items()
            }
        )

    configs: dict[str, GuildNotificationConfig] = {}
    for key, (default_enabled, default_fmt) in _GUILD_DEFAULTS.items():
        entry = data.get(key)
        if entry:
            configs[key] = GuildNotificationConfig(
                enabled=entry.get("enabled", default_enabled),
                format=entry.get("format", default_fmt),
                channel=entry.get("channel"),
            )
        else:
            configs[key] = GuildNotificationConfig(
                enabled=default_enabled, format=default_fmt, channel=None
            )
    return GuildConfig(notification_configs=configs)


def _parse_filters(data: Any) -> FiltersConfig | None:
    """
    Build FiltersConfig from parsed TOML data.

    Args:
        data: Filters section, or None.

    Returns:
        FiltersConfig if section exists and enabled, otherwise None.
    """
    if not data:
        return None
    enabled = bool(data.get("enabled", False))
    patterns: list[str] = list(data.get("patterns", []))
    return FiltersConfig(enabled=enabled, patterns=patterns)


def _parse_channels(data: dict[str, Any]) -> list[ChannelConfig]:
    """
    Parse the chat channel relay configuration.

    Args:
        data: Chat section from config containing a "channels" list.

    Returns:
        List of ChannelConfig entries.
    """
    channels: list[ChannelConfig] = []
    for entry in data.get("channels", []):
        direction = ChatDirection(entry["direction"])
        wow_data = entry.get("wow", {})
        discord_data = entry.get("discord", {})

        wow_channel = WowChannelConfig(
            type=ChatEvents.parse(wow_data.get("type", "say")),
            channel=wow_data.get("channel"),
            id=wow_data.get("id"),
            format=wow_data.get("format", ""),
            filters=_parse_filters(wow_data.get("filters")),
        )
        discord_channel = DiscordChannelConfig(
            channel=discord_data.get("channel", ""),
            format=discord_data.get("format", ""),
            filters=_parse_filters(discord_data.get("filters")),
        )
        channels.append(
            ChannelConfig(
                chat_direction=direction,
                wow=wow_channel,
                discord=discord_channel,
            )
        )
    return channels


def load_config(path: str | Path) -> WowChatConfig:
    """
    Load and parse a TOML configuration file into WowChatConfig.

    Handles environment variable fallbacks for sensitive fields
    (token, account, password, character) and initialises ChatEvents
    based on the configured expansion.

    Args:
        path: Path to the .toml configuration file.

    Returns:
        Fully parsed WowChatConfig.
    """
    path = Path(path)

    with path.open("rb") as f:
        raw: dict[str, Any] = tomllib.load(f)

    discord_raw = raw.get("discord", {})
    wow_raw = raw.get("wow", {})
    guild_raw = raw.get("guild")
    chat_raw = raw.get("chat", {})
    filters_raw = raw.get("filters")

    version: str = str(wow_raw.get("version", "1.12.1"))
    expansion = WowExpansion.from_version(version)
    ChatEvents.init(expansion)

    build = _build_from_version(version)

    discord_cfg = DiscordConfig(
        token=_env_fallback("DISCORD_TOKEN", discord_raw.get("token", "")),
        enable_dot_commands=bool(
            discord_raw.get("enable_dot_commands", True)
        ),
        dot_commands_whitelist=set(
            str(s).lower() for s in discord_raw.get("dot_commands_whitelist", [])
        ),
        enable_commands_channels=set(
            str(s).lower() for s in discord_raw.get("enable_commands_channels", [])
        ),
        enable_tag_failed_notifications=bool(
            discord_raw.get("enable_tag_failed_notifications", True)
        ),
        item_database=discord_raw.get("item_database"),
    )

    realmlist_str: str = wow_raw.get("realmlist", "127.0.0.1:3724")
    realm_name: str = wow_raw.get("realm", "")

    wow_cfg = WowConfig(
        locale=str(wow_raw.get("locale", "enUS")),
        platform=Platform.from_string(str(wow_raw.get("platform", "Mac"))),
        version=version,
        expansion=expansion,
        realm_build=wow_raw.get("realm_build") or wow_raw.get("build") or build,
        game_build=wow_raw.get("game_build") or wow_raw.get("build") or build,
        realmlist=_parse_realmlist(realmlist_str, realm_name),
        account=_account_to_upper_bytes(
            _env_fallback("WOW_ACCOUNT", wow_raw.get("account", ""))
        ),
        password=_env_fallback("WOW_PASSWORD", wow_raw.get("password", "")),
        character=_env_fallback("WOW_CHARACTER", wow_raw.get("character", "")),
        enable_server_motd=bool(wow_raw.get("enable_server_motd", True)),
    )

    guild_cfg = _parse_guild_config(guild_raw)
    channels = _parse_channels(chat_raw)
    filters = _parse_filters(filters_raw)

    return WowChatConfig(
        discord=discord_cfg,
        wow=wow_cfg,
        guild=guild_cfg,
        channels=channels,
        filters=filters,
    )
