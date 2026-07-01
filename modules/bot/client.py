"""
Discord bot relaying WoW chat ↔ Discord and handling dot commands.
"""

from __future__ import annotations

import asyncio
import datetime
import re
import time
from typing import Any

import discord

from common.chat import ChatEvents
from common.formatters import _GUILD_EVENT_ARGS, fmt
from common.types import WowChatConfig, global_state
from game.core.command_handler import GameCommandHandler
from game.core.resources import GameResources
from modules.bot.commands import  handle_dot_command
from utils.logger import Tags, log
from utils.markup import convert_wow_markup, replace_raid_icons

_DOT_COMMAND_RE = re.compile(r"^\.(\w+)\s*(.*)")

class _RateLimiter:
    """Simple rate limiter that ensures a minimum interval between actions."""

    def __init__(self, min_interval: float = 0.15) -> None:
        self._min_interval = min_interval
        self._last = 0.0

    async def wait(self) -> None:
        """Sleep if needed to maintain the minimum interval since the last call."""
        now = time.monotonic()
        wait = self._min_interval - (now - self._last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last = time.monotonic()


class DiscordBot(discord.Client):
    """
    Discord client that relays WoW chat messages and handles dot commands.

    Acts as the event callback for the WoW game session, routing chat messages,
    guild events, and achievements to the appropriate Discord channels.
    Also handles incoming Discord messages and dot commands (.who, .gmotd, .r).

    Args:
        config: Parsed application configuration containing Discord and WoW settings.
    """

    def __init__(self, config: WowChatConfig, **kwargs: Any) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **kwargs)
        self._config = config
        self._command_handler: GameCommandHandler | None = None
        self._connected_channel: Any = None
        self._rate_limiter = _RateLimiter()
        self._pending_whispers: dict[str, tuple[str, float]] = {}

    def set_command_handler(self, handler: GameCommandHandler) -> None:
        """
        Set the handler for sending messages to the WoW game server.

        Args:
            handler: Command handler instance connected to an active game session.
        """
        self._command_handler = handler

    def connected(self) -> None:
        """Log and send a system embed when the WoW client enters the world."""
        log("INFO", Tags.DISCORD, "Connected to WoW world.")
        cfg = self._config
        asyncio.create_task(
            self.send_system_event(
                "connected",
                realm_name=cfg.wow.realmlist.name,
                character=cfg.wow.character,
            )
        )

    def disconnected(self) -> None:
        """Log and clear state when the WoW client disconnects."""
        log("WARNING", Tags.DISCORD, "Disconnected from WoW.")
        self._command_handler = None

    def guild_roster_updated(self) -> None:
        """Stub: called when the WoW guild roster is refreshed."""

    def error(self) -> None:
        """Notify the connected Discord channel of an authentication failure."""
        ch = self._connected_channel
        if ch:
            asyncio.create_task(
                ch.send(":warning: Failed to authenticate with WoW server.")
            )

    async def send_system_event(
        self,
        kind: str,
        *,
        realm_name: str = "",
        character: str = "",
        error_detail: str = "",
        extra_fields: dict[str, str] | None = None,
    ) -> None:
        """
        Send a richly formatted system embed to the bot-system channel.

        Args:
            kind: Event type - ``"connecting"``, ``"connected"``,
                ``"disconnected"``, or ``"error"``.
            realm_name: WoW realm name for the embed.
            character: Character name for the embed.
            error_detail: Error message text for error events.
            extra_fields: Optional additional Discord embed field pairs.
        """
        channel_name = self._config.discord.bot_system_channel
        if not channel_name:
            return
        ch = self._resolve_channel(channel_name)
        if ch is None:
            return

        embed = discord.Embed(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        if kind == "connecting":
            embed.title = "🔄 Connecting..."
            embed.colour = discord.Colour.gold()
            embed.description = (
                f"Connecting to **{realm_name}** "
                f"as **{character}**..."
            )
        elif kind == "connected":
            embed.title = "✅ Connected"
            embed.colour = discord.Colour.green()
            embed.description = (
                f"Connected to **{realm_name}** "
                f"as **{character}**."
            )
        elif kind == "disconnected":
            embed.title = "⚠️ Disconnected"
            embed.colour = discord.Colour.orange()
            embed.description = (
                f"Lost connection to **{realm_name}**."
            )
            if extra_fields:
                for k, v in extra_fields.items():
                    embed.add_field(name=k, value=v, inline=True)
            embed.add_field(
                name="Next reconnection",
                value=error_detail or "soon",
                inline=False,
            )
        elif kind == "error":
            embed.title = "❌ Connection Error"
            embed.colour = discord.Colour.red()
            embed.description = error_detail or "An unexpected error occurred."
        else:
            return

        if realm_name:
            embed.add_field(name="Server", value=realm_name, inline=True)
        if character:
            embed.add_field(name="Character", value=character, inline=True)
        if extra_fields and kind not in ("disconnected",):
            for k, v in extra_fields.items():
                embed.add_field(name=k, value=v, inline=True)

        embed.set_footer(text="WowMiniClient")
        await ch.send(embed=embed)

    def chat_message(
        self,
        sender_name: str | None,
        message: str,
        tp: int,
        channel_name: str | None,
        is_gm: bool = False,
    ) -> None:
        """
        Relay a WoW chat message to the appropriate Discord channel.

        Applies markup conversion, raid icon replacement, and GM icon prefixing.
        Skips messages that match configured filters.

        Args:
            sender_name: Player name or None for system messages.
            message: Raw chat message text from the WoW server.
            tp: Chat type constant (e.g. CHAT_MSG_SAY, CHAT_MSG_GUILD).
            channel_name: Custom channel name (e.g. \"taberna\") or None.
            is_gm: True if the message came via SMSG_GM_MESSAGECHAT.
        """
        key = (tp, channel_name.lower() if channel_name else None)
        targets = global_state.wow_to_discord.get(key)
        if not targets:
            return
        wow_filters = global_state.wow_channel_filters.get(key)
        message = convert_wow_markup(message, self._config.discord.item_database)
        message = replace_raid_icons(message, self._config.discord.raid_icons)
        for discord_channel_name, dcc in targets:
            if self._is_filtered(message, wow_filters) or self._is_filtered(message, dcc.filters):
                continue
            formatted = fmt(dcc.format, user=sender_name, message=message)
            if is_gm and self._config.discord.gm_icon:
                formatted = f"{self._config.discord.gm_icon} {formatted}"
            asyncio.create_task(
                self._send_to_channel(discord_channel_name, formatted)
            )

    def _echo_own_message(self, text: str, tp: int,
                          channel_name: str | None = None) -> None:
        player = global_state.config.wow.character
        if not player:
            return
        key = (tp, None)
        targets = global_state.wow_to_discord.get(key)
        if not targets:
            return
        for discord_channel_name, dcc in targets:
            formatted = fmt(
                dcc.format,
                user=player,
                message=text,
                target=channel_name or "",
            )
            asyncio.create_task(
                self._send_to_channel(discord_channel_name, formatted)
            )

    def register_pending_whisper(self, target: str, channel_name: str) -> None:
        self._pending_whispers[target.lower()] = (channel_name, time.monotonic())

    def chat_player_notfound(self, target: str) -> None:
        now = time.monotonic()
        key = target.lower()
        entry = self._pending_whispers.pop(key, None)
        stale = [k for k, (_, ts) in self._pending_whispers.items() if now - ts > 30]
        for k in stale:
            self._pending_whispers.pop(k, None)
        channel_name = entry[0] if entry else None
        if not channel_name:
            key = (ChatEvents.CHAT_MSG_WHISPER, None)
            targets = global_state.wow_to_discord.get(key)
            if targets:
                channel_name = targets[0][0]
        if channel_name:
            asyncio.create_task(
                self._send_to_channel(
                    channel_name,
                    f":warning: Player **{target}** is not online or does not exist.",
                )
            )

    def _is_filtered(self, message: str, filters: Any) -> bool:
        """
        Check if a message matches any configured filter pattern.

        Args:
            message: Text to check.
            filters: FiltersConfig object with patterns list, or None.

        Returns:
            True if filters are enabled and any pattern matches the message.
        """
        if not filters or not filters.enabled:
            return False
        return any(re.search(p, message) for p in filters.patterns)

    def guild_event(self, event_key: str, messages: list[str]) -> None:
        """
        Relay a guild event (promote, demote, join, leave, etc.) to Discord.

        Args:
            event_key: Type of guild event (e.g. \"promoted\", \"joined\").
            messages: Values for the event's format placeholders.
        """
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
        formatted = fmt(notif.format, **kwargs)

        for channel_name in targets:
            asyncio.create_task(self._send_to_channel(channel_name, formatted))

    def achievement(self, member_name: str, achievement_id: int) -> None:
        """
        Relay a guild achievement unlock to Discord.

        Args:
            member_name: Player who earned the achievement.
            achievement_id: Numeric achievement ID for name lookup.
        """
        notif = self._config.guild.notification_configs.get("achievement")
        if not notif or not notif.enabled:
            return
        achievement_name = GameResources.ACHIEVEMENT.get(
            achievement_id, f"#{achievement_id}"
        )
        formatted = fmt(
            notif.format,
            user=member_name,
            achievement=achievement_name,
        )
        targets = global_state.guild_events_to_discord.get("achievement")
        if not targets:
            return
        for channel_name in targets:
            asyncio.create_task(self._send_to_channel(channel_name, formatted))

    async def on_ready(self) -> None:
        """Log bot identity when Discord connection is established."""
        name = self.user.name if self.user else "Unknown"
        uid = self.user.id if self.user else 0
        log("INFO", Tags.DISCORD, f"Logged in as {name} (ID: {uid})")

    async def on_message(self, message: Any) -> None:
        """
        Route Discord messages to WoW or handle dot commands.

        Ignores messages from the bot itself or other bots. If the message
        starts with a dot and dot commands are enabled, dispatches to the
        command handler. Otherwise sends the text to WoW as configured.

        Args:
            message: Incoming Discord message object.
        """
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
                ch_name = message.channel.name
                await handle_dot_command(
                    cmd_match, message.channel, message.author.display_name,
                    self._command_handler, self._echo_own_message,
                    lambda target, _: self.register_pending_whisper(target, ch_name),
                )
                return

        handler = self._command_handler
        if handler is None:
            return

        for wcc in wow_configs:
            formatted = fmt(wcc.format, message=message.content)
            handler.send_message_to_wow(wcc.type, formatted, wcc.channel)
            self._echo_own_message(message.content, wcc.type, wcc.channel)

    async def _send_to_channel(self, channel_name: str, content: str) -> None:
        """
        Send a message to a Discord text channel looked up by name.

        Rate-limited to avoid hitting Discord API rate limits.

        Args:
            channel_name: Name of the Discord channel (e.g. \"guild-chat\").
            content: Formatted message text to send.
        """
        await self._rate_limiter.wait()
        ch = self._resolve_channel(channel_name)
        if ch:
            await ch.send(content)

    def _resolve_channel(self, channel_name: str) -> Any | None:
        """
        Find a Discord text channel by name across all guilds.

        Args:
            channel_name: Name of the Discord channel.

        Returns:
            The matching text channel, or None if not found.
        """
        for guild in self.guilds:
            for ch in guild.text_channels:
                if ch.name == channel_name:
                    return ch
        log("DEBUG", Tags.DISCORD, f"Channel #{channel_name} not found.")
        return None
