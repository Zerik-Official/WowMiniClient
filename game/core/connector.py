"""
GameConnector: creates expansion-appropriate handler, decoder, encoder, and crypt.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from game.core.buffer import Packet
from common.types import WowExpansion, global_state
from crypto.header import (
    GameHeaderCrypt,
    GameHeaderCryptMoP,
    GameHeaderCryptTBC,
    GameHeaderCryptWotLK,
)
from game.core.decoder import (
    GamePacketDecoder,
    GamePacketDecoderCataclysm,
    GamePacketDecoderMoP,
    GamePacketDecoderWotLK,
)
from game.core.encoder import (
    GamePacketEncoder,
    GamePacketEncoderCataclysm,
    GamePacketEncoderMoP,
)
from game.handler import (
    GamePacketHandler,
    GamePacketHandlerCataclysm,
    GamePacketHandlerMoP,
    GamePacketHandlerTBC,
    GamePacketHandlerWotLK,
)
from utils.logger import Tags, log


class GameConnector:
    """Async TCP connector to the WoW game world server."""

    def __init__(self, host: str, port: int, realm_name: str,
                 realm_id: int, session_key: bytes,
                 game_event_callback: Any,
                 on_handler_ready: Callable[..., None] | None = None) -> None:
        self.host = host
        self.port = port
        self.realm_name = realm_name
        self.realm_id = realm_id
        self.session_key = session_key
        self.game_event_callback = game_event_callback
        self._on_handler_ready = on_handler_ready

        self._writer: asyncio.StreamWriter | None = None
        self._handler: GamePacketHandler | None = None
        self._decoder: GamePacketDecoder | None = None
        self._encoder: Any = None

    async def connect(self) -> None:
        """
        Connect to the game world server and enter the message loop.

        Selects the appropriate handler, decoder, encoder, and crypt
        based on the configured expansion. Runs until the connection
        is closed or an error occurs.

        Raises:
            ValueError: If the expansion is not supported.
        """
        log("INFO", Tags.GAME, f"Connecting to game server {self.realm_name} ({self.host}:{self.port})"
        )

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=10,
        )
        self._writer = writer

        expansion = global_state.expansion

        if expansion == WowExpansion.VANILLA:
            crypt = GameHeaderCrypt()
            self._decoder = GamePacketDecoder()
            self._encoder = GamePacketEncoder
            def send_cb(oid: int, payload: bytes) -> None:
                self._send(oid, payload)
            self._handler = GamePacketHandler(
                self.realm_id, self.realm_name, self.session_key,
                self.game_event_callback, send_cb,
            )
        elif expansion == WowExpansion.TBC:
            crypt = GameHeaderCryptTBC()
            self._decoder = GamePacketDecoder()
            self._encoder = GamePacketEncoder
            def send_cb(oid: int, payload: bytes) -> None:
                self._send(oid, payload)
            self._handler = GamePacketHandlerTBC(
                self.realm_id, self.realm_name, self.session_key,
                self.game_event_callback, send_cb,
            )
        elif expansion == WowExpansion.WOTLK:
            crypt = GameHeaderCryptWotLK()
            self._decoder = GamePacketDecoderWotLK()
            self._encoder = GamePacketEncoder
            def send_cb(oid: int, payload: bytes) -> None:
                self._send(oid, payload)
            self._handler = GamePacketHandlerWotLK(
                self.realm_id, self.realm_name, self.session_key,
                self.game_event_callback, send_cb,
            )
        elif expansion == WowExpansion.CATACLYSM:
            crypt = GameHeaderCryptWotLK()
            self._decoder = GamePacketDecoderCataclysm()
            self._encoder = GamePacketEncoderCataclysm
            def send_cb(oid: int, payload: bytes) -> None:
                self._send(oid, payload)
            self._handler = GamePacketHandlerCataclysm(
                self.realm_id, self.realm_name, self.session_key,
                self.game_event_callback, send_cb,
            )
        elif expansion == WowExpansion.MOP:
            crypt = GameHeaderCryptMoP()
            self._decoder = GamePacketDecoderMoP()
            self._encoder = GamePacketEncoderMoP
            def send_cb(oid: int, payload: bytes) -> None:
                self._send(oid, payload)
            self._handler = GamePacketHandlerMoP(
                self.realm_id, self.realm_name, self.session_key,
                self.game_event_callback, send_cb,
            )
        else:
            msg = f"Unsupported expansion: {expansion}"
            raise ValueError(msg)

        global_state.game_crypt = crypt
        if self._on_handler_ready and self._handler:
            self._on_handler_ready(self._handler)
        self._handler.on_connected()

        ping_task = asyncio.create_task(self._ping_loop())
        try:
            while True:
                data = await asyncio.wait_for(reader.read(65536), timeout=60)
                if not data:
                    log("WARNING", Tags.GAME, "Game server closed the connection.")
                    break
                packets = self._decoder.feed(data)
                for opcode, payload in packets:
                    msg = Packet(opcode, payload)
                    responses = self._handler.handle_packet(msg)
                    for oid, pl in responses:
                        self._send(oid, pl)
        except (asyncio.CancelledError, ConnectionError, TimeoutError) as e:
            log("ERROR", Tags.GAME, f"Game connection lost: {e}")
        finally:
            ping_task.cancel()
            self._handler.disconnect()

    async def _ping_loop(self) -> None:
        await asyncio.sleep(30)
        while True:
            if self._handler and self._handler.in_world:
                payload = self._handler.ping()
                if payload is not None:
                    self._send(self._handler.CMSG_PING, payload)
            await asyncio.sleep(30)

    def _send(self, msg_id: int, payload: bytes) -> None:
        if self._writer is None:
            return
        data = self._encoder.encode(msg_id, payload)
        self._writer.write(data)

    def disconnect(self) -> None:
        """Close the connection to the game server."""
        if self._writer:
            self._writer.close()
            self._writer = None
