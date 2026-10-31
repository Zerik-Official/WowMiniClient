"""Interactive console setup flow built on InquirerPy."""

# Standard library
from __future__ import annotations
import copy
from pathlib import Path
from typing import Any

# Third-party
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator

# Project imports
from configurator.schema import (
    CHAT_TYPES,
    DIRECTIONS,
    GM_MODES,
    GUILD_EVENTS,
    LOCALES,
    PLATFORMS,
    SUPPORTED_VERSIONS,
    default_channel,
)
from configurator.store import ConfigValidationError, load_raw, save
from utils.logger import Tags, log


def _required(value: str) -> bool:
    """
    Check that a text answer is not blank.

    Args:
        value: Answer typed by the user.

    Returns:
        True when the answer contains visible characters.
    """
    return bool(value.strip())


def _split(value: str) -> list[str]:
    """
    Split a comma separated answer into trimmed items.

    Args:
        value: Comma separated text.

    Returns:
        Non-empty trimmed items.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


def _describe_channel(entry: dict[str, Any]) -> str:
    """
    Build a one-line summary of a chat relay entry.

    Args:
        entry: Raw ``[[chat.channels]]`` entry.

    Returns:
        Human readable summary.
    """
    wow: dict[str, Any] = entry.get("wow", {})
    label = str(wow.get("type", "?"))
    if wow.get("channel"):
        label = f"{label} ({wow['channel']})"
    direction = DIRECTIONS.get(str(entry.get("direction")), str(entry.get("direction")))
    return f"{label}  <->  #{entry.get('discord', {}).get('channel', '?')}  [{direction}]"


class ConsoleWizard:
    """Asks the user for every setting in the terminal and writes wowchat.toml."""

    def __init__(self, config_path: Path) -> None:
        """
        Prepare the wizard with the current configuration as defaults.

        Args:
            config_path: Destination of wowchat.toml.
        """
        self.config_path: Path = config_path
        self.raw: dict[str, Any] = copy.deepcopy(load_raw(config_path))

    def _secret(self, message: str, current: str) -> str:
        """
        Ask for a secret value, keeping the current one when the answer is empty.

        Args:
            message: Prompt text.
            current: Value already stored.

        Returns:
            New secret, or the current one when nothing was typed.
        """
        hint = " (leave empty to keep the current one)" if current else ""
        answer: str = inquirer.secret(
            message=f"{message}{hint}:",
            validate=None if current else _required,
            invalid_message="This field is required.",
        ).execute()
        return answer or current

    def ask_discord(self) -> None:
        """Ask for the Discord bot settings."""
        discord: dict[str, Any] = self.raw["discord"]
        discord["token"] = self._secret("Discord bot token", str(discord.get("token", "")))
        discord["bot_system_channel"] = inquirer.text(
            message="Channel for bot status messages:",
            default=str(discord.get("bot_system_channel") or ""),
        ).execute()
        discord["enable_dot_commands"] = inquirer.confirm(
            message="Allow dot commands such as .who and .gmotd from Discord?",
            default=bool(discord.get("enable_dot_commands", True)),
        ).execute()
        discord["item_database"] = inquirer.text(
            message="Item database URL for item links (optional):",
            default=str(discord.get("item_database") or ""),
        ).execute()

    def ask_wow(self) -> None:
        """Ask for the WoW server and character settings."""
        wow: dict[str, Any] = self.raw["wow"]
        wow["version"] = inquirer.select(
            message="Game version of the server:",
            choices=SUPPORTED_VERSIONS,
            default=str(wow.get("version", "3.3.5")),
        ).execute()
        wow["realmlist"] = inquirer.text(
            message="Realmlist (host:port):",
            default=str(wow.get("realmlist", "")),
            validate=_required,
            invalid_message="This field is required.",
        ).execute()
        wow["realm"] = inquirer.text(
            message="Realm name exactly as shown in the realm list:",
            default=str(wow.get("realm", "")),
            validate=_required,
            invalid_message="This field is required.",
        ).execute()
        wow["account"] = inquirer.text(
            message="Account name:",
            default=str(wow.get("account", "")),
            validate=_required,
            invalid_message="This field is required.",
        ).execute()
        wow["password"] = self._secret("Account password", str(wow.get("password", "")))
        wow["character"] = inquirer.text(
            message="Character that will log in:",
            default=str(wow.get("character", "")),
            validate=_required,
            invalid_message="This field is required.",
        ).execute()
        wow["locale"] = inquirer.select(
            message="Client locale:",
            choices=LOCALES,
            default=str(wow.get("locale", "enUS")),
        ).execute()
        wow["platform"] = inquirer.select(
            message="Reported platform:",
            choices=PLATFORMS,
            default=str(wow.get("platform", "Mac")),
        ).execute()
        wow["enable_server_motd"] = inquirer.confirm(
            message="Relay the server message of the day?",
            default=bool(wow.get("enable_server_motd", True)),
        ).execute()

    def _ask_channel(self) -> dict[str, Any]:
        """
        Ask for a new chat relay entry.

        Returns:
            Raw ``[[chat.channels]]`` entry.
        """
        chat_type: str = inquirer.select(message="WoW chat type:", choices=CHAT_TYPES).execute()
        entry = default_channel(chat_type, "")
        if chat_type == "Channel":
            entry["wow"]["channel"] = inquirer.text(
                message="Custom WoW channel name:",
                validate=_required,
                invalid_message="This field is required.",
            ).execute()
        entry["direction"] = inquirer.select(
            message="Relay direction:",
            choices=[Choice(value=key, name=name) for key, name in DIRECTIONS.items()],
        ).execute()
        entry["discord"]["channel"] = inquirer.text(
            message="Discord channel name (without #):",
            validate=_required,
            invalid_message="This field is required.",
        ).execute().lstrip("#")
        entry["discord"]["format"] = inquirer.text(
            message="Format in Discord (%user, %message, %target):",
            default="[%user]: %message",
        ).execute()
        if entry["direction"] != "wow_to_discord":
            entry["wow"]["format"] = inquirer.text(
                message="Format in WoW (%message):",
                default="%message",
            ).execute()
        return entry

    def ask_channels(self) -> None:
        """Let the user review, add and remove chat relay entries."""
        channels: list[dict[str, Any]] = self.raw["chat"]["channels"]
        while True:
            choices: list[Any] = [
                Choice(value=index, name=f"Remove: {_describe_channel(entry)}")
                for index, entry in enumerate(channels)
            ]
            if choices:
                choices.append(Separator())
            choices += [Choice(value="add", name="Add a channel"), Choice(value="done", name="Continue")]
            action: Any = inquirer.select(
                message=f"Chat relays ({len(channels)} configured):",
                choices=choices,
                default="done",
            ).execute()
            if action == "done":
                return
            if action == "add":
                channels.append(self._ask_channel())
            else:
                channels.pop(int(action))

    def ask_guild(self) -> None:
        """Ask which guild events are posted to Discord."""
        guild: dict[str, Any] = self.raw["guild"]
        enabled: list[str] = inquirer.checkbox(
            message="Guild events posted to Discord (space to toggle):",
            choices=[
                Choice(value=key, name=label, enabled=bool(guild[key].get("enabled")))
                for key, label in GUILD_EVENTS.items()
            ],
        ).execute()
        for key in GUILD_EVENTS:
            guild[key]["enabled"] = key in enabled

    def ask_gm_commands(self) -> None:
        """Ask for the GM command channel settings."""
        gm: dict[str, Any] = self.raw["gm_commands"]
        gm["enabled"] = inquirer.confirm(
            message="Run GM commands from a Discord channel?",
            default=bool(gm.get("enabled", False)),
        ).execute()
        if not gm["enabled"]:
            return
        gm["channel"] = inquirer.text(
            message="Discord channel for GM commands:",
            default=str(gm.get("channel") or "gm-commands"),
            validate=_required,
            invalid_message="This field is required.",
        ).execute().lstrip("#")
        gm["allowed_roles"] = _split(inquirer.text(
            message="Discord role IDs allowed to run commands (comma separated):",
            default=", ".join(str(role) for role in gm.get("allowed_roles", [])),
            validate=lambda value: all(item.isdigit() for item in _split(value)),
            invalid_message="Use numeric role IDs separated by commas.",
        ).execute())
        gm["mode"] = inquirer.select(
            message="Command transport:",
            choices=GM_MODES,
            default=str(gm.get("mode", "auto")),
        ).execute()
        gm["blocked_commands"] = _split(inquirer.text(
            message="Blocked commands (comma separated, optional):",
            default=", ".join(gm.get("blocked_commands", [])),
        ).execute())

    def run(self) -> bool:
        """
        Walk through every section and save the result.

        Returns:
            True when the configuration was written.
        """
        self.ask_discord()
        self.ask_wow()
        self.ask_channels()
        self.ask_guild()
        self.ask_gm_commands()
        while True:
            if not inquirer.confirm(message=f"Save to {self.config_path}?", default=True).execute():
                log("WARNING", Tags.CONFIG, "Setup cancelled, nothing was written.")
                return False
            try:
                save(self.raw, self.config_path)
            except ConfigValidationError as exc:
                log("ERROR", Tags.CONFIG, str(exc))
                if not inquirer.confirm(message="Review the answers again?", default=True).execute():
                    return False
                self.ask_discord()
                self.ask_wow()
                continue
            log("SUCCESS", Tags.CONFIG, f"Configuration saved to {self.config_path}")
            return True
