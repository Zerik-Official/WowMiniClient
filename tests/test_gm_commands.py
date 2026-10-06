"""Unit tests for GM command execution over the addon channel and chat."""

from __future__ import annotations

import asyncio
import struct
from collections.abc import Callable

from common.chat import ChatEvents
from common.types import WowExpansion
from game.core.buffer import Packet
from game.core.gm_commands import (
    LANG_ADDON,
    GmCommandExecutor,
    GmCommandMode,
    GmCommandStatus,
)
from game.core.wotlk import GamePacketHandlerWotLK


class _FakeServer:
    """Records sent messages and replies through a scripted responder."""

    def __init__(self) -> None:
        self.addon: list[str] = []
        self.chat: list[str] = []
        self.executor: GmCommandExecutor | None = None
        self.on_addon: Callable[[str], None] | None = None
        self.on_chat: Callable[[str], None] | None = None

    def send_addon(self, text: str) -> None:
        """Record an addon whisper and schedule the scripted reply."""
        self.addon.append(text)
        if self.on_addon:
            asyncio.get_running_loop().call_soon(self.on_addon, text)

    def send_chat(self, text: str) -> None:
        """Record a chat whisper and schedule the scripted reply."""
        self.chat.append(text)
        if self.on_chat:
            asyncio.get_running_loop().call_soon(self.on_chat, text)


def _make(mode: GmCommandMode, **kwargs: float) -> tuple[_FakeServer, GmCommandExecutor]:
    """Build a fake server wired to a new executor."""
    server = _FakeServer()
    executor = GmCommandExecutor(server.send_addon, server.send_chat, mode=mode, **kwargs)
    server.executor = executor
    return server, executor


def _azeroth_responder(server: _FakeServer, final: str,
                       lines: list[str]) -> Callable[[str], None]:
    """Reply like AzerothCore: ACK pings, emit lines and a final opcode."""
    def respond(text: str) -> None:
        assert server.executor is not None
        prefix, _, body = text.partition("\t")
        if prefix != "AzerothCore":
            return
        echo = body[1:5]
        server.executor.on_addon_message(f"AzerothCore\ta{echo}")
        if body[0] == "i":
            for line in lines:
                server.executor.on_addon_message(f"AzerothCore\tm{echo}{line}")
            server.executor.on_addon_message(f"AzerothCore\t{final}{echo}")
    return respond


def test_auto_detects_azeroth_and_runs_command() -> None:
    """AUTO mode picks the core that ACKs the ping and returns OK with lines."""
    async def run() -> None:
        server, executor = _make(GmCommandMode.AUTO, probe_timeout=1.0)
        server.on_addon = _azeroth_responder(server, "o", ["Account CLAUDE banned."])
        executor.start()
        result = await executor.execute(".ban account CLAUDE -1 Migracion Duplicada")

        assert executor.prefix == "AzerothCore"
        assert server.addon[:2] == ["AzerothCore\tp0000", "TrinityCore\tp0000"]
        assert server.addon[2] == "AzerothCore\ti0001ban account CLAUDE -1 Migracion Duplicada"
        assert result.status == GmCommandStatus.OK
        assert result.lines == ["Account CLAUDE banned."]
        assert result.via_addon
    asyncio.run(run())


def test_addon_failed_status() -> None:
    """An ``f`` reply marks the command as FAILED and keeps its lines."""
    async def run() -> None:
        server, executor = _make(GmCommandMode.AZEROTH)
        server.on_addon = _azeroth_responder(server, "f", ["There is no such command."])
        executor.start()
        result = await executor.execute("foo")
        assert result.status == GmCommandStatus.FAILED
        assert result.lines == ["There is no such command."]
    asyncio.run(run())


def test_addon_ignores_foreign_echo() -> None:
    """Replies with another echo do not resolve the pending command."""
    async def run() -> None:
        server, executor = _make(GmCommandMode.TRINITY, timeout=0.2)

        def respond(text: str) -> None:
            executor.on_addon_message("TrinityCore\to9999")
        server.on_addon = respond
        executor.start()
        result = await executor.execute("server info")
        assert result.status == GmCommandStatus.TIMEOUT
    asyncio.run(run())


def test_chat_fallback_collects_system_lines() -> None:
    """Without an addon ACK, system lines after the command form the reply."""
    async def run() -> None:
        server, executor = _make(GmCommandMode.AUTO, probe_timeout=0.05,
                                 quiet_period=0.05)

        def respond(text: str) -> None:
            executor.on_system_message("Line 1")
            executor.on_system_message("Line 2")
        server.on_chat = respond
        executor.start()
        result = await executor.execute("server info")

        assert executor.prefix is None
        assert server.chat == [".server info"]
        assert result.status == GmCommandStatus.COMPLETED
        assert result.lines == ["Line 1", "Line 2"]
    asyncio.run(run())


def test_chat_timeout_without_reply() -> None:
    """Chat mode reports TIMEOUT when no system line arrives."""
    async def run() -> None:
        _, executor = _make(GmCommandMode.CHAT, timeout=0.1)
        executor.start()
        result = await executor.execute("server info")
        assert result.status == GmCommandStatus.TIMEOUT
    asyncio.run(run())


def test_rejects_too_long_and_not_started() -> None:
    """Over-long commands and commands before ``start`` are rejected."""
    async def run() -> None:
        server, executor = _make(GmCommandMode.AZEROTH)
        result = await executor.execute("server info")
        assert result.status == GmCommandStatus.REJECTED

        executor.start()
        result = await executor.execute("a" * 239)
        assert result.status == GmCommandStatus.REJECTED
        assert server.addon == []
    asyncio.run(run())


def test_system_message_passthrough_when_idle() -> None:
    """System messages are not consumed when no command is running."""
    _, executor = _make(GmCommandMode.CHAT)
    assert executor.on_system_message("Server restart in 5 min") is False
    assert executor.on_addon_message("DBM\tsomething") is False


def _wotlk_chat_packet(tp: int, lang: int, guid: int, text: str) -> Packet:
    """Build a WotLK SMSG_MESSAGECHAT payload for a non-channel message."""
    raw = text.encode("utf-8") + b"\x00"
    payload = (struct.pack("<BIQI", tp, lang, guid, 0) + struct.pack("<Q", guid)
               + struct.pack("<I", len(raw)) + raw + b"\x00")
    return Packet(GamePacketHandlerWotLK.SMSG_MESSAGECHAT, payload)


def test_wotlk_parser_routes_addon_reply_from_self() -> None:
    """Addon whispers from the own character reach the executor."""
    async def run() -> None:
        ChatEvents.init(WowExpansion.WOTLK)
        server, executor = _make(GmCommandMode.AZEROTH, timeout=1.0)
        handler = GamePacketHandlerWotLK.__new__(GamePacketHandlerWotLK)
        handler.gm_commands = executor
        handler.self_character_id = 42

        def respond(text: str) -> None:
            echo = text.partition("\t")[2][1:5]
            for reply in (f"AzerothCore\tm{echo}Done.", f"AzerothCore\to{echo}"):
                packet = _wotlk_chat_packet(ChatEvents.CHAT_MSG_WHISPER, LANG_ADDON, 42, reply)
                assert handler._parse_chat_message(packet) is None
        server.on_addon = respond
        executor.start()
        result = await executor.execute("server info")
        assert result.status == GmCommandStatus.OK
        assert result.lines == ["Done."]
    asyncio.run(run())
