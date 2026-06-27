"""
Discord bot relaying WoW chat ↔ Discord and handling dot commands.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import discord

from common.types import WowChatConfig, global_state
from game.core.command_handler import GameCommandHandler
from game.core.resources import GameResources
from utils.logger import Tags, log

_DOT_COMMAND_RE = re.compile(r"^\.(\w+)\s*(.*)")


def _fmt(template: str, **kwargs: str | None) -> str:
    """Replace %key placeholders with values, dropping unused ones."""
    result = template
    for key, val in kwargs.items():
        placeholder = f"%{key}"
        if val is not None:
            result = result.replace(placeholder, val)
        else:
            result = result.replace(placeholder, "")
    return result


_GUILD_EVENT_ARGS: dict[str, tuple[str, ...]] = {
    "promoted": ("user", "target", "rank"),
    "demoted": ("user", "target", "rank"),
    "joined": ("user",),
    "left": ("user",),
    "removed": ("user", "target"),
    "online": ("user",),
    "offline": ("user",),
    "motd": ("user", "message"),
}


class DiscordBot(discord.Client):
    """
    Discord client that relays chat messages and handles dot commands.

    Args:
        config: Parsed application configuration.
    """

    def __init__(self, config: WowChatConfig, **kwargs: Any) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **kwargs)
        self._config = config
        self._command_handler: GameCommandHandler | None = None
        self._connected_channel: Any = None

    # -- Handler wiring ------------------------------------------------

    def set_command_handler(self, handler: GameCommandHandler) -> None:
        """Set the handler for sending messages to the WoW game server."""
        self._command_handler = handler

    # -- Game event callbacks (called from game loop) ------------------

    def connected(self) -> None:
        """Called when the WoW client enters the world."""
        log("INFO", Tags.DISCORD, "Connected to WoW world.")

    def disconnected(self) -> None:
        """Called when the WoW client disconnects."""
        log("WARNING", Tags.DISCORD, "Disconnected from WoW.")
        self._command_handler = None

    def error(self) -> None:
        """Called on WoW authentication failure."""
        ch = self._connected_channel
        if ch:
            asyncio.create_task(
                ch.send(":warning: Failed to authenticate with WoW server.")
            )

    def chat_message(
        self,
        sender_name: str | None,
        message: str,
        tp: int,
        channel_name: str | None,
    ) -> None:
        """Relay a WoW chat message to the appropriate Discord channel."""
        key = (tp, channel_name.lower() if channel_name else None)
        targets = global_state.wow_to_discord.get(key)
        if not targets:
            return
        for discord_channel_name, dcc in targets:
            formatted = _fmt(dcc.format, user=sender_name, message=message)
            asyncio.create_task(
                self._send_to_channel(discord_channel_name, formatted)
            )

    def guild_event(self, event_key: str, messages: list[str]) -> None:
        """Relay a guild event to the configured Discord channels."""
        targets = global_state.guild_events_to_discord.get(event_key)
        if not targets:
            return
        notif = self._config.guild.notification_configs.get(event_key)
        if not notif or not notif.enabled:
            return

        arg_names = _GUILD_EVENT_ARGS.get(event_key, ())
        kwargs: dict[str, str | None] = dict(
            zip(arg_names, messages + [None] * len(arg_names))
        )
        formatted = _fmt(notif.format, **kwargs)

        for channel_name in targets:
            asyncio.create_task(self._send_to_channel(channel_name, formatted))

    def achievement(self, member_name: str, achievement_id: int) -> None:
        """Relay a guild achievement event to Discord."""
        notif = self._config.guild.notification_configs.get("achievement")
        if not notif or not notif.enabled:
            return
        achievement_name = GameResources.ACHIEVEMENT.get(
            achievement_id, f"#{achievement_id}"
        )
        formatted = _fmt(
            notif.format,
            user=member_name,
            achievement=achievement_name,
        )
        targets = global_state.guild_events_to_discord.get("achievement")
        if not targets:
            return
        for channel_name in targets:
            asyncio.create_task(self._send_to_channel(channel_name, formatted))

    # -- Discord event handlers ---------------------------------------

    async def on_ready(self) -> None:
        """Log when the bot connects to Discord."""
        name = self.user.name if self.user else "Unknown"
        uid = self.user.id if self.user else 0
        log("INFO", Tags.DISCORD, f"Logged in as {name} (ID: {uid})")

    async def on_message(self, message: Any) -> None:
        """Route Discord messages to WoW or handle commands."""
        if message.author == self.user:
            return
        if message.author.bot:
            return

        channel_name = message.channel.name
        wow_configs = global_state.discord_to_wow.get(channel_name)
        if not wow_configs:
            return

        dc = self._config.discord
        if dc.enable_dot_commands:
            cmd_match = _DOT_COMMAND_RE.match(message.content)
            if cmd_match:
                await self._handle_dot_command(
                    cmd_match, message.channel, message.author.display_name,
                )
                return

        handler = self._command_handler
        if handler is None:
            return

        for wcc in wow_configs:
            formatted = _fmt(
                wcc.format,
                user=message.author.display_name,
                message=message.content,
            )
            handler.send_message_to_wow(wcc.type, formatted, wcc.channel)

    # -- Internal helpers ---------------------------------------------

    async def _handle_dot_command(
        self,
        match: re.Match[str],
        channel: Any,
        author_name: str,
    ) -> None:
        """Process a dot command (e.g. .who, .gmotd)."""
        command = match.group(1).lower()
        args = match.group(2).strip() or None
        handler = self._command_handler
        if handler is None:
            return

        if command == "who":
            result = handler.handle_who(args)
        elif command == "gmotd":
            result = handler.handle_gmotd()
        else:
            await channel.send(
                ":grey_question: Unknown command. Available: `.who`, `.gmotd`"
            )
            return

        if result:
            await channel.send(
                f"**{author_name}** requested:\n{result}"
            )

    async def _send_to_channel(self, channel_name: str, content: str) -> None:
        """Send a message to a Discord channel by name."""
        for guild in self.guilds:
            for ch in guild.text_channels:
                if ch.name == channel_name:
                    await ch.send(content)
                    return
        log("DEBUG", Tags.DISCORD, f"Channel #{channel_name} not found.")
