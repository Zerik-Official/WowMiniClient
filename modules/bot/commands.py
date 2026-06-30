"""
Discord dot-command dispatch for .who, .gmotd, .r (whisper reply), etc.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from common.chat import ChatEvents
from game.core.command_handler import GameCommandHandler

_DOT_COMMAND_RE = re.compile(r"^\.(\w+)\s*(.*)")


async def handle_dot_command(
    match: re.Match[str],
    channel: Any,
    author_name: str,
    handler: GameCommandHandler | None,
    echo_callback: Callable[[str, int, str | None], None] | None = None,
) -> None:
    """
    Execute a dot command by dispatching to the WoW command handler.

    Supported commands: .who/.w (player search), .gmotd/.motd (guild MOTD),
    .r/.responder/.reply/.whisper (whisper reply to a player).

    Args:
        match: Regex match from _DOT_COMMAND_RE.
        channel: Discord channel to send response messages to.
        author_name: Display name of the user who issued the command.
        handler: Game command handler for WoW interaction, or None if not connected.
        echo_callback: Optional callback to echo outgoing messages back to Discord.
    """
    if handler is None:
        return

    command = match.group(1).lower()
    args = match.group(2).strip() or None

    if command in ("who", "w"):
        result = handler.handle_who(args)
    elif command in ("gmotd", "motd"):
        result = handler.handle_gmotd()
    elif command in ("r", "responder", "reply", "whisper"):
        if not args or " " not in args:
            await channel.send(":grey_question: Usa: `.r nombre mensaje`")
            return
        target, _, text = args.partition(" ")
        handler.send_message_to_wow(
            ChatEvents.CHAT_MSG_WHISPER, text, target,
        )
        if echo_callback:
            echo_callback(text, ChatEvents.CHAT_MSG_WHISPER, target)
        return
    else:
        await channel.send(
            ":grey_question: Unknown command. `.who`, `.gmotd`, `.r nombre msg`"
        )
        return

    if result:
        await channel.send(
            f"**{author_name}** requested:\n{result}"
        )
