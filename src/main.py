"""Entry point that loads the config and starts the Discord bot and WoW session."""

# Standard library
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
from typing import Final

# Project imports
from common.config import load_config
from common.routing import build_channel_maps
from common.types import WowChatConfig, global_state
from game.session import WowSessionManager
from modules.bot.client import DiscordBot
from utils.banner import print_banner
from utils.logger import Tags, log

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
CONFIG_PATH: Final[Path] = PROJECT_ROOT / "wowchat.toml"


class App:
    """Application orchestrator holding config, bot, and WoW session manager."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path)
        self.config: WowChatConfig | None = None
        self.bot: DiscordBot | None = None

    async def run(self) -> None:
        """Load config, start Discord bot and WoW reconnection loop."""
        if not self.config_path.exists():
            log("ERROR", Tags.MAIN, f"Config not found: {self.config_path}")
            log("INFO", Tags.MAIN, "Run 'python src/configure.py' to create it.")
            sys.exit(1)

        self.config = load_config(self.config_path)
        cfg = self.config
        global_state.config = cfg
        global_state.expansion = cfg.wow.expansion
        global_state.realm_build = cfg.wow.realm_build or 0
        global_state.game_build = cfg.wow.game_build or 0
        build_channel_maps(cfg)

        build_num = cfg.wow.game_build or cfg.wow.realm_build or 0
        log(
            "INFO", Tags.MAIN,
            f"Starting WowMiniClient for {cfg.wow.expansion.value} "
            f"(build {build_num})",
        )

        self.bot = DiscordBot(cfg)
        session = WowSessionManager(cfg, self.bot)

        bot_task = asyncio.create_task(self._run_discord(cfg.discord.token))
        wow_task = asyncio.create_task(session.run())

        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        finally:
            wow_task.cancel()
            try:
                await wow_task
            except asyncio.CancelledError:
                pass

    async def _run_discord(self, token: str) -> None:
        """Run the Discord bot, reconnecting on network errors."""
        while True:
            try:
                await self.bot.start(token, reconnect=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log("ERROR", Tags.DISCORD, f"Discord connection error: {exc}")
                await asyncio.sleep(10)


def main() -> None:
    """Parse config and run the application."""
    app = App(CONFIG_PATH)
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        log("INFO", Tags.MAIN, "Shutdown requested.")
    except Exception as exc:
        log("CRITICAL", Tags.MAIN, f"Unexpected error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    print_banner()
    main()
