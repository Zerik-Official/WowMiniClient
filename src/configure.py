"""Entry point of the setup wizard that creates or edits wowchat.toml."""

# Standard library
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Final

# Third-party
from InquirerPy import inquirer
from InquirerPy.base.control import Choice

# Project imports
from configurator import web
from configurator.console import ConsoleWizard
from utils.banner import print_banner
from utils.logger import Tags, log

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
CONFIG_PATH: Final[Path] = PROJECT_ROOT / "wowchat.toml"


def parse_args() -> argparse.Namespace:
    """
    Parse the command line options of the wizard.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Create or edit wowchat.toml.")
    parser.add_argument("--mode", choices=("console", "web"), help="Skip the mode question.")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Path of the config file.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser in web mode.")
    return parser.parse_args()


def main() -> None:
    """Ask how to configure the client and run the chosen flow."""
    args = parse_args()
    config_path: Path = args.config.resolve()
    log("INFO", Tags.CONFIG, f"{'Editing' if config_path.exists() else 'Creating'} {config_path}")

    mode: str = args.mode or inquirer.select(
        message="How do you want to configure WowMiniClient?",
        choices=[
            Choice(value="web", name="In the browser (temporary local page)"),
            Choice(value="console", name="Here in the console"),
        ],
        default="web",
    ).execute()

    if mode == "web":
        web.run(config_path, open_browser=not args.no_browser)
    elif not ConsoleWizard(config_path).run():
        sys.exit(1)

    if config_path.exists():
        log("INFO", Tags.CONFIG, "Start the client with: python src/main.py")


if __name__ == "__main__":
    print_banner()
    try:
        main()
    except KeyboardInterrupt:
        log("WARNING", Tags.CONFIG, "Setup cancelled.")
