"""
WoW session manager handling the realm → game → reconnect cycle.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from game.core.connector import GameConnector
from game.handler import GamePacketHandler
from realm.connector import RealmConnector
from utils.logger import Tags, log
from utils.reconnect import ReconnectDelay

if TYPE_CHECKING:
    from common.types import WowChatConfig
    from modules.bot.client import DiscordBot


class WowSessionManager:
    """
    Manages the WoW client session lifecycle: realm auth, game connection,
    and automatic reconnection with exponential backoff.

    Args:
        config: Parsed application configuration.
        bot: Discord bot instance for event callbacks and command handler setup.
    """

    def __init__(self, config: WowChatConfig, bot: DiscordBot) -> None:
        self._config = config
        self._bot = bot

    async def run(self) -> None:
        """Infinite reconnection loop: realm auth → game → reconnect."""
        cfg = self._config
        await self._bot.wait_until_ready()

        delay = ReconnectDelay()
        realm_name = cfg.wow.realmlist.name
        character = cfg.wow.character

        while True:
            try:
                game_host, game_port, _, realm_id, session_key = (
                    await self._connect_realm(delay, realm_name, character)
                )
                delay.reset()
                await self._connect_game(
                    game_host, game_port, realm_name, realm_id, session_key,
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log("ERROR", Tags.MAIN,
                    f"Unexpected error in WoW loop ({type(e).__name__}: {e}), "
                    "reconnecting...")

            wait = delay.get_next()
            log("WARNING", Tags.MAIN,
                f"Reconnecting to {realm_name} in {wait}s...")
            await self._bot.send_system_event(
                "disconnected", realm_name=realm_name,
                character=character,
                error_detail=f"Reconnecting in {wait} seconds",
            )
            await asyncio.sleep(wait)

    async def _connect_realm(
        self, delay: ReconnectDelay, realm_name: str, character: str,
    ) -> tuple[str, int, str, int, bytes]:
        """
        Authenticate with the realm server, retrying on failure.

        Args:
            delay: Reconnect delay tracker for back-off.
            realm_name: Realm display name for log messages.
            character: Character name for log messages.

        Returns:
            Tuple of (game_host, game_port, _, realm_id, session_key).
        """
        cfg = self._config
        rl = cfg.wow.realmlist

        while True:
            connector = RealmConnector(
                host=rl.host, port=rl.port,
                account=cfg.wow.account, password=cfg.wow.password,
                version=cfg.wow.version,
                realm_build=cfg.wow.game_build or cfg.wow.realm_build or 5875,
                expansion=cfg.wow.expansion,
                platform=cfg.wow.platform, locale=cfg.wow.locale,
                realm_name=rl.name,
                on_success=lambda *a: None,
                on_error=lambda: None,
                on_disconnect=lambda: None,
            )
            await self._bot.send_system_event(
                "connecting", realm_name=realm_name, character=character,
            )
            try:
                result = await connector.connect()
                return result
            except ConnectionError:
                log("ERROR", Tags.MAIN, "Realm authentication failed, retrying...")
                await self._bot.send_system_event(
                    "error", realm_name=realm_name,
                    character=character,
                    error_detail="Falló autenticación con el servidor de reinos.",
                )
                wait = delay.get_next()
                await asyncio.sleep(wait)
            finally:
                connector.close()

    async def _connect_game(
        self, host: str, port: int, realm_name: str,
        realm_id: int, session_key: bytes,
    ) -> None:
        """
        Connect to the game world server and run until disconnected.

        Args:
            host: Game server hostname.
            port: Game server port.
            realm_name: Human-readable realm name.
            realm_id: Numeric realm identifier.
            session_key: 40-byte SRP session key.
        """
        bot = self._bot

        def _on_handler_ready(h: GamePacketHandler) -> None:
            bot.set_command_handler(h)

        connector = GameConnector(
            host, port, realm_name, realm_id, session_key, bot,
            on_handler_ready=_on_handler_ready,
        )
        await connector.connect()
