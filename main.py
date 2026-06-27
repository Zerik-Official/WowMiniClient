#!/usr/bin/env python3
"""
Entry point for WowMiniClient.

Loads config, populates routing maps, starts Discord bot and realm
authentication, then on success launches the game connector.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from bot.client import DiscordBot
from common.config import load_config
from common.types import ChatDirection, WowChatConfig, global_state
from game.connector import GameConnector
from game.handler import GamePacketHandler
from realm.connector import RealmConnector
from utils.logger import Tags, log


def _build_channel_maps(config: WowChatConfig) -> None:
    """Populate global routing maps from parsed channel configs."""
    for entry in config.channels:
        direction = entry.chat_direction
        if direction in (ChatDirection.BOTH, ChatDirection.DISCORD_TO_WOW):
            global_state.discord_to_wow[entry.discord.channel].add(entry.wow)
        if direction in (ChatDirection.BOTH, ChatDirection.WOW_TO_DISCORD):
            key = (entry.wow.type, entry.wow.channel)
            global_state.wow_to_discord[key].add(
                (entry.discord.channel, entry.discord),
            )

    guild = config.guild
    if guild:
        for event_key, notif in guild.notification_configs.items():
            if notif.enabled:
                channel = notif.channel or "guild-chat"
                global_state.guild_events_to_discord[event_key].add(channel)


class App:
    """Application state holding config, bot, and realm connector."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self.config: WowChatConfig | None = None
        self.bot: DiscordBot | None = None
        self.realm_connector: RealmConnector | None = None

    def _on_auth_success(
        self, host: str, port: int, name: str, realm_id: int,
        session_key: bytes,
    ) -> None:
        """Handle successful realm auth and start the game connector."""
        bot = self.bot
        if bot is None:
            log("CRITICAL", Tags.MAIN, "Bot not initialized.")
            return

        def _on_handler_ready(h: GamePacketHandler) -> None:
            bot.set_command_handler(h)

        connector = GameConnector(
            host, port, name, realm_id, session_key, bot,
            on_handler_ready=_on_handler_ready,
        )
        asyncio.create_task(connector.connect())

    @staticmethod
    def _on_auth_error() -> None:
        log("ERROR", Tags.REALM, "Realm authentication failed.")
        sys.exit(1)

    @staticmethod
    def _on_disconnect() -> None:
        log("WARNING", Tags.REALM, "Disconnected from realm server.")

    async def run(self) -> None:
        """Load config, start Discord bot and realm auth concurrently."""
        if not self.config_path.exists():
            log("ERROR", Tags.MAIN, f"Config not found: {self.config_path}")
            sys.exit(1)

        self.config = load_config(self.config_path)
        cfg = self.config
        global_state.config = cfg
        global_state.expansion = cfg.wow.expansion
        global_state.realm_build = cfg.wow.realm_build or 0
        global_state.game_build = cfg.wow.game_build or 0
        _build_channel_maps(cfg)

        build_num = cfg.wow.game_build or cfg.wow.realm_build or 0
        log(
            "INFO", Tags.MAIN,
            f"Starting WowMiniClient for {cfg.wow.expansion.value} "
            f"(build {build_num})",
        )

        # Discord bot
        self.bot = DiscordBot(cfg)
        bot_task = asyncio.create_task(
            self.bot.start(cfg.discord.token, reconnect=True)
        )

        # Give the bot a moment to connect
        await asyncio.sleep(2)

        # Realm auth
        rl = cfg.wow.realmlist
        self.realm_connector = RealmConnector(
            host=rl.host,
            port=rl.port,
            account=cfg.wow.account,
            password=cfg.wow.password,
            version=cfg.wow.version,
            realm_build=cfg.wow.game_build or cfg.wow.realm_build or 5875,
            expansion=cfg.wow.expansion,
            platform=cfg.wow.platform,
            locale=cfg.wow.locale,
            realm_name=rl.name,
            on_success=self._on_auth_success,
            on_error=self._on_auth_error,
            on_disconnect=self._on_disconnect,
        )
        await self.realm_connector.connect()

        # Keep running until bot disconnects
        await bot_task


def main() -> None:
    """Parse config and run the application."""
    app = App("wowchat.toml")
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        log("INFO", Tags.MAIN, "Shutdown requested.")
    except Exception as exc:
        log("CRITICAL", Tags.MAIN, f"Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
