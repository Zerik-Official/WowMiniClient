"""
GM command execution over the AzerothCore/TrinityCore addon channel.

Commands are sent as a ``LANG_ADDON`` whisper to the bot's own character
using the ``AddonChannelCommandHandler`` protocol, which correlates each
reply with its request and reports an explicit OK/FAILED status. When the
server does not answer the addon ping (addon channel disabled or unknown
core), commands fall back to a plain ``.command`` whisper and the reply is
collected from the ``CHAT_MSG_SYSTEM`` lines that follow it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

from utils.logger import Tags, log

LANG_ADDON: int = 0xFFFFFFFF


class GmCommandMode(StrEnum):
    """How GM commands are delivered to the server."""

    AUTO = "auto"
    AZEROTH = "azeroth"
    TRINITY = "trinity"
    CHAT = "chat"


class GmCommandStatus(StrEnum):
    """Final state of an executed GM command."""

    OK = "ok"
    FAILED = "failed"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    REJECTED = "rejected"


@dataclass
class GmCommandResult:
    """Outcome of a GM command: status plus the server's reply lines."""

    command: str
    status: GmCommandStatus
    lines: list[str] = field(default_factory=list)
    via_addon: bool = False


@dataclass
class _PendingCommand:
    """In-flight command state shared between ``execute`` and packet hooks."""

    command: str
    echo: str
    via_addon: bool
    lines: list[str] = field(default_factory=list)
    activity: asyncio.Event = field(default_factory=asyncio.Event)
    status: GmCommandStatus | None = None


class GmCommandExecutor:
    """Sends GM commands and gathers their replies, one command at a time."""

    PREFIXES: dict[GmCommandMode, str] = {
        GmCommandMode.AZEROTH: "AzerothCore",
        GmCommandMode.TRINITY: "TrinityCore",
    }
    PROBE_ECHO = "0000"
    MAX_CHAT_LENGTH = 255
    ADDON_HEADER_LENGTH = 17

    def __init__(self, send_addon: Callable[[str], None],
                 send_chat: Callable[[str], None],
                 mode: GmCommandMode = GmCommandMode.AUTO,
                 timeout: float = 5.0,
                 quiet_period: float = 0.6,
                 probe_timeout: float = 3.0) -> None:
        """
        Args:
            send_addon: Sends a ``LANG_ADDON`` whisper to the own character.
            send_chat: Sends a normal whisper to the own character.
            mode: Delivery mode; ``AUTO`` probes the addon channel first.
            timeout: Maximum seconds to wait for a command reply.
            quiet_period: Seconds without new system lines that end a
                chat-mode reply.
            probe_timeout: Seconds to wait for the addon ping ACK.
        """
        self._send_addon = send_addon
        self._send_chat = send_chat
        self._mode = mode
        self._timeout = timeout
        self._quiet_period = quiet_period
        self._probe_timeout = probe_timeout

        self._prefix: str | None = self.PREFIXES.get(mode)
        self._started = False
        self._probe_done = asyncio.Event()
        self._lock = asyncio.Lock()
        self._pending: _PendingCommand | None = None
        self._counter = 0

    @property
    def prefix(self) -> str | None:
        """Addon prefix in use, or None when falling back to chat mode."""
        return self._prefix

    def start(self) -> None:
        """
        Prepare the executor once the character is in the world.

        In ``AUTO`` mode, pings both cores through the addon channel; the
        first ACK selects the prefix. Without an ACK within
        ``probe_timeout`` the executor falls back to chat mode.
        """
        if self._started:
            return
        self._started = True
        if self._mode != GmCommandMode.AUTO:
            self._probe_done.set()
            return
        for prefix in self.PREFIXES.values():
            self._send_addon(f"{prefix}\tp{self.PROBE_ECHO}")
        asyncio.get_running_loop().call_later(self._probe_timeout, self._end_probe)

    def _end_probe(self) -> None:
        """Finish the addon probe, logging the selected delivery mode."""
        if self._probe_done.is_set():
            return
        self._probe_done.set()
        log("INFO", Tags.COMMAND,
            "Addon command channel not available, using chat commands.")

    async def execute(self, command: str) -> GmCommandResult:
        """
        Run a GM command and wait for the server reply.

        Args:
            command: Command text, with or without a leading ``.`` or ``!``.

        Returns:
            GmCommandResult with the final status and the reply lines.
        """
        command = command.strip()
        if command[:1] in (".", "!"):
            command = command[1:]
        if not command:
            return GmCommandResult(command, GmCommandStatus.REJECTED,
                                   ["Empty command."])
        if not self._started:
            return GmCommandResult(command, GmCommandStatus.REJECTED,
                                   ["Character is not in the world yet."])

        async with self._lock:
            await self._probe_done.wait()
            if self._prefix is not None:
                return await self._execute_addon(command, self._prefix)
            return await self._execute_chat(command)

    async def _execute_addon(self, command: str, prefix: str) -> GmCommandResult:
        """
        Run a command through the addon channel protocol.

        Args:
            command: Command text without leading dot.
            prefix: Core addon prefix (``AzerothCore`` or ``TrinityCore``).

        Returns:
            GmCommandResult with OK/FAILED, or TIMEOUT if no final reply.
        """
        max_length = self.MAX_CHAT_LENGTH - self.ADDON_HEADER_LENGTH
        if len(command.encode("utf-8")) > max_length:
            return GmCommandResult(command, GmCommandStatus.REJECTED,
                                   [f"Command exceeds {max_length} bytes."], True)

        pending = _PendingCommand(command, self._next_echo(), via_addon=True)
        self._pending = pending
        try:
            self._send_addon(f"{prefix}\ti{pending.echo}{command}")
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self._timeout
            while pending.status is None:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    pending.status = GmCommandStatus.TIMEOUT
                    break
                try:
                    await asyncio.wait_for(pending.activity.wait(), remaining)
                except TimeoutError:
                    pending.status = GmCommandStatus.TIMEOUT
                pending.activity.clear()
        finally:
            self._pending = None
        return GmCommandResult(command, pending.status, pending.lines, True)

    async def _execute_chat(self, command: str) -> GmCommandResult:
        """
        Run a command as a ``.command`` whisper and collect system lines.

        The reply ends after ``quiet_period`` seconds without new lines, or
        at ``timeout`` if nothing arrives.

        Args:
            command: Command text without leading dot.

        Returns:
            GmCommandResult with COMPLETED, or TIMEOUT if nothing arrived.
        """
        text = f".{command}"
        if len(text.encode("utf-8")) > self.MAX_CHAT_LENGTH:
            return GmCommandResult(
                command, GmCommandStatus.REJECTED,
                [f"Command exceeds {self.MAX_CHAT_LENGTH - 1} bytes."],
            )

        pending = _PendingCommand(command, "", via_addon=False)
        self._pending = pending
        try:
            self._send_chat(text)
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self._timeout
            while pending.status is None:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                wait = min(remaining, self._quiet_period) if pending.lines else remaining
                try:
                    await asyncio.wait_for(pending.activity.wait(), wait)
                except TimeoutError:
                    if pending.lines:
                        break
                pending.activity.clear()
        finally:
            self._pending = None
        if pending.status is None:
            pending.status = (GmCommandStatus.COMPLETED if pending.lines
                              else GmCommandStatus.TIMEOUT)
        return GmCommandResult(command, pending.status, pending.lines, False)

    def _next_echo(self) -> str:
        """
        Return the next 4-character correlation id (``0001``-``9999``).

        Returns:
            Zero-padded counter string, never equal to the probe echo.
        """
        self._counter = self._counter % 9999 + 1
        return f"{self._counter:04d}"

    def on_addon_message(self, text: str) -> bool:
        """
        Consume an addon whisper if it belongs to the command protocol.

        Args:
            text: Raw addon message text (``Prefix\\tbody``).

        Returns:
            True if the message used a known command prefix.
        """
        prefix, sep, body = text.partition("\t")
        if not sep or prefix not in self.PREFIXES.values():
            return False
        if len(body) < 5:
            return True
        opcode, echo, payload = body[0], body[1:5], body[5:]

        if echo == self.PROBE_ECHO:
            if opcode == "a" and not self._probe_done.is_set():
                self._prefix = prefix
                self._probe_done.set()
                log("INFO", Tags.COMMAND, f"Addon command channel detected: {prefix}")
            return True

        pending = self._pending
        if pending is None or not pending.via_addon or echo != pending.echo:
            return True
        if opcode == "m":
            pending.lines.append(payload)
        elif opcode == "o":
            pending.status = GmCommandStatus.OK
        elif opcode == "f":
            pending.status = GmCommandStatus.FAILED
        pending.activity.set()
        return True

    def on_system_message(self, text: str) -> bool:
        """
        Capture a ``CHAT_MSG_SYSTEM`` line while a chat-mode command runs.

        Args:
            text: System message text.

        Returns:
            True if the line was captured as a command reply.
        """
        pending = self._pending
        if pending is None or pending.via_addon:
            return False
        pending.lines.append(text)
        pending.activity.set()
        return True

    def cancel(self, reason: str) -> None:
        """
        Fail the in-flight command, e.g. when the connection drops.

        Args:
            reason: Line appended to the command output explaining the failure.
        """
        pending = self._pending
        if pending is None or pending.status is not None:
            return
        pending.lines.append(reason)
        pending.status = GmCommandStatus.FAILED
        pending.activity.set()
