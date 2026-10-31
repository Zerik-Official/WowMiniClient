"""Option lists, defaults and normalization shared by the console and web setup flows."""

# Standard library
from __future__ import annotations
import copy
from typing import Any, Final

# Project imports
from common.config import _GM_COMMAND_MODES, _GUILD_DEFAULTS, _VERSION_TO_BUILD

SUPPORTED_VERSIONS: Final[list[str]] = list(_VERSION_TO_BUILD)
DEFAULT_VERSION: Final[str] = "3.3.5"

LOCALES: Final[list[str]] = [
    "enUS", "enGB", "esES", "esMX", "deDE", "frFR",
    "ruRU", "ptBR", "itIT", "koKR", "zhCN", "zhTW",
]
PLATFORMS: Final[list[str]] = ["Mac", "Windows"]
GM_MODES: Final[list[str]] = sorted(_GM_COMMAND_MODES)

CHAT_TYPES: Final[list[str]] = [
    "Guild", "Officer", "Say", "Yell", "Emote", "Whisper",
    "Party", "Raid", "Battleground", "System", "Channel",
]
DIRECTIONS: Final[dict[str, str]] = {
    "both": "Both ways",
    "wow_to_discord": "WoW to Discord",
    "discord_to_wow": "Discord to WoW",
}

GUILD_EVENTS: Final[dict[str, str]] = {
    "online": "Member comes online",
    "offline": "Member goes offline",
    "joined": "Member joins the guild",
    "left": "Member leaves the guild",
    "removed": "Member is kicked",
    "promoted": "Member is promoted",
    "demoted": "Member is demoted",
    "motd": "Message of the day changes",
    "achievement": "Member earns an achievement",
}

RAID_ICON_SLOTS: Final[list[str]] = [str(i) for i in range(1, 9)]

MANAGED_SECTIONS: Final[tuple[str, ...]] = (
    "discord", "wow", "guild", "chat", "filters", "gm_commands",
)

REQUIRED_FIELDS: Final[dict[str, str]] = {
    "discord.token": "DISCORD_TOKEN",
    "wow.realmlist": "",
    "wow.realm": "",
    "wow.account": "WOW_ACCOUNT",
    "wow.password": "WOW_PASSWORD",
    "wow.character": "WOW_CHARACTER",
}


def default_channel(chat_type: str = "Guild", discord_channel: str = "guild-chat") -> dict[str, Any]:
    """
    Build a chat relay entry with the default formats.

    Args:
        chat_type: WoW chat type name.
        discord_channel: Discord channel name.

    Returns:
        Raw channel entry as stored in ``[[chat.channels]]``.
    """
    return {
        "direction": "both",
        "wow": {"type": chat_type, "format": "%message"},
        "discord": {"channel": discord_channel, "format": "[%user]: %message"},
    }


def default_config() -> dict[str, Any]:
    """
    Build a complete raw configuration with sensible defaults for a new user.

    Returns:
        Raw configuration dictionary with every managed section.
    """
    return {
        "discord": {
            "token": "",
            "bot_system_channel": "bot-system",
            "enable_dot_commands": True,
            "dot_commands_whitelist": [],
            "enable_commands_channels": [],
            "enable_tag_failed_notifications": True,
            "item_database": "",
            "gm_icon": "",
            "raid_icons": {"enabled": False},
        },
        "wow": {
            "locale": "enUS",
            "platform": "Mac",
            "realmlist": "127.0.0.1:3724",
            "realm": "",
            "account": "",
            "password": "",
            "character": "",
            "version": DEFAULT_VERSION,
            "enable_server_motd": True,
        },
        "guild": {
            key: {"enabled": enabled, "format": fmt}
            for key, (enabled, fmt) in _GUILD_DEFAULTS.items()
        },
        "chat": {
            "channels": [
                default_channel("Guild", "guild-chat"),
                default_channel("Officer", "officer-chat"),
            ],
        },
        "filters": {"enabled": False, "patterns": []},
        "gm_commands": {
            "enabled": False,
            "channel": "gm-commands",
            "allowed_roles": [],
            "mode": "auto",
            "timeout": 5.0,
            "blocked_commands": [],
        },
    }


def with_defaults(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Fill missing managed keys of a loaded configuration with defaults.

    Args:
        raw: Raw configuration loaded from disk.

    Returns:
        New dictionary where every managed section has all of its keys.
    """
    merged: dict[str, Any] = copy.deepcopy(raw)
    defaults = default_config()
    for section in MANAGED_SECTIONS:
        current = merged.get(section)
        if not isinstance(current, dict):
            merged[section] = defaults[section]
            continue
        for key, value in defaults[section].items():
            current.setdefault(key, value)
    for key, value in defaults["guild"].items():
        merged["guild"].setdefault(key, value)
    return merged


def get_path(raw: dict[str, Any], dotted: str) -> Any:
    """
    Read a nested value using a dotted path such as ``wow.realm``.

    Args:
        raw: Raw configuration dictionary.
        dotted: Dotted key path.

    Returns:
        The value found, or None when any segment is missing.
    """
    node: Any = raw
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _prune(value: Any) -> Any:
    """
    Remove None values and empty strings that TOML cannot or should not store.

    Args:
        value: Any raw configuration value.

    Returns:
        The value without empty optional entries.
    """
    if isinstance(value, dict):
        return {
            key: _prune(item)
            for key, item in value.items()
            if item is not None and item != ""
        }
    if isinstance(value, list):
        return [_prune(item) for item in value if item is not None and item != ""]
    return value


def _clean_list(values: Any) -> list[str]:
    """
    Turn a list or a comma separated string into a list of trimmed strings.

    Args:
        values: List of values or a comma separated string.

    Returns:
        Non-empty trimmed strings.
    """
    if isinstance(values, str):
        values = values.split(",")
    return [str(item).strip() for item in values or [] if str(item).strip()]


def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Coerce types coming from the console or the web form into TOML-ready values.

    Args:
        raw: Raw configuration with possibly loose types.

    Returns:
        Normalized configuration ready to be written.
    """
    data: dict[str, Any] = with_defaults(raw)

    discord: dict[str, Any] = data["discord"]
    for key in ("dot_commands_whitelist", "enable_commands_channels"):
        discord[key] = _clean_list(discord.get(key))
    icons: dict[str, Any] = discord.get("raid_icons") or {}
    discord["raid_icons"] = {"enabled": bool(icons.get("enabled", False))} | {
        slot: str(icons[slot]).strip()
        for slot in RAID_ICON_SLOTS
        if str(icons.get(slot) or "").strip()
    }

    gm: dict[str, Any] = data["gm_commands"]
    gm["allowed_roles"] = [int(role) for role in _clean_list(gm.get("allowed_roles"))]
    gm["blocked_commands"] = _clean_list(gm.get("blocked_commands"))
    gm["timeout"] = float(gm.get("timeout") or 5.0)

    data["filters"]["patterns"] = _clean_list(data["filters"].get("patterns"))

    channels: list[dict[str, Any]] = []
    for entry in data["chat"].get("channels", []):
        wow: dict[str, Any] = dict(entry.get("wow", {}))
        if str(wow.get("type", "")).lower() != "channel":
            wow.pop("channel", None)
        filters = wow.get("filters")
        if isinstance(filters, dict):
            patterns = _clean_list(filters.get("patterns"))
            if patterns:
                wow["filters"] = {"enabled": bool(filters.get("enabled", True)), "patterns": patterns}
            else:
                wow.pop("filters", None)
        channels.append({
            "direction": entry.get("direction", "both"),
            "wow": wow,
            "discord": dict(entry.get("discord", {})),
        })
    data["chat"]["channels"] = channels

    return _prune(data)


def missing_required(raw: dict[str, Any], environ: dict[str, str]) -> list[str]:
    """
    List required fields that are empty and not provided by an environment variable.

    Args:
        raw: Raw configuration dictionary.
        environ: Environment variables to check for fallbacks.

    Returns:
        Dotted paths of the missing fields.
    """
    missing: list[str] = []
    for dotted, env_name in REQUIRED_FIELDS.items():
        if str(get_path(raw, dotted) or "").strip():
            continue
        if env_name and environ.get(env_name):
            continue
        missing.append(dotted)
    return missing


def to_form(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Prepare a configuration for JSON transport to the browser.

    Discord role IDs exceed the safe integer range of JavaScript, so they are
    sent as strings.

    Args:
        raw: Raw configuration dictionary.

    Returns:
        Copy of the configuration safe to embed in the web page.
    """
    data: dict[str, Any] = with_defaults(raw)
    data["gm_commands"]["allowed_roles"] = [
        str(role) for role in data["gm_commands"].get("allowed_roles", [])
    ]
    return data


def merge_managed(existing: dict[str, Any], updated: dict[str, Any]) -> dict[str, Any]:
    """
    Replace the managed sections of a configuration and keep any other section.

    Args:
        existing: Configuration currently on disk.
        updated: Normalized configuration produced by the wizard.

    Returns:
        Configuration that preserves unmanaged top-level sections.
    """
    merged: dict[str, Any] = {
        key: value for key, value in existing.items() if key not in MANAGED_SECTIONS
    }
    for section in MANAGED_SECTIONS:
        if section in updated:
            merged[section] = updated[section]
    return merged
