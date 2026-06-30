"""
TBC game packet handler.
"""

from __future__ import annotations

import time

from game.core.buffer import Packet, PacketWriter
from common.types import global_state
from utils.logger import Tags, log
from game.core.packets import GamePacketsTBC
from game.core.vanilla import GamePacketHandler
from game.models import (
    CharEnumMessage,
    ChatMessage,
    GuildMember,
)

class GamePacketHandlerTBC(GamePacketHandler, GamePacketsTBC):
    """TBC game packet handler extending the Vanilla base."""

    def _run_keep_alive(self, out: list[tuple[int, bytes]]) -> None:
        """
        Send a CMSG_KEEP_ALIVE to prevent server timeout.

        Args:
            out: Accumulator list for outgoing packets.
        """
        out.append((self.CMSG_KEEP_ALIVE, b""))

    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        """
        Dispatch packets unique to the TBC expansion.

        Args:
            msg: Incoming packet with opcode and payload.

        Returns:
            List of (opcode, payload) tuples to send back to the server.
        """
        mid = msg.id
        if mid == self.SMSG_GM_MESSAGECHAT:
            return self._handle_message_chat_inner(msg)
        if mid == self.SMSG_MOTD:
            if global_state.config.wow.enable_server_motd:
                out = self._parse_server_motd(msg)
                for cm in out:
                    self._send_chat_message(cm)
            return []
        if mid == self.SMSG_TIME_SYNC_REQ:
            return self._handle_time_sync_req(msg)
        return super().handle_packet(msg)

    def _handle_message_chat_inner(self, msg: Packet) -> list[tuple[int, bytes]]:
        """
        Parse and forward a SMSG_GM_MESSAGECHAT (used for GM detection).

        Args:
            msg: Incoming chat message packet.

        Returns:
            Empty list (no outgoing packets).
        """
        log("DEBUG", Tags.GAME, f"RECV CHAT: {bytes(msg.data[msg._pos:]).hex()}")
        chat_msg = self._parse_chat_message(msg)
        if chat_msg is not None:
            self._send_chat_message(chat_msg)
        return []

    def _handle_time_sync_req(self, msg: Packet) -> list[tuple[int, bytes]]:
        """
        Respond to CMSG_TIME_SYNC_RESP with current uptime.

        Args:
            msg: Incoming time sync request.

        Returns:
            List with a single CMSG_TIME_SYNC_RESP packet.
        """
        counter = msg.read_int_le()
        uptime = int((time.time() * 1000) - self.connect_time)
        pw = PacketWriter()
        pw.write_int_le(counter)
        pw.write_int_le(uptime)
        return [(self.CMSG_TIME_SYNC_RESP, pw.build())]

    def _parse_server_motd(self, msg: Packet) -> list[ChatMessage]:
        """Parse SMSG_MOTD for TBC (integer line count, null-terminated strings).

        Args:
            msg: Incoming MOTD packet.

        Returns:
            List of ChatMessage (one per MOTD line).
        """
        line_count = msg.read_int_le()
        result = []
        for _ in range(line_count):
            line = msg.read_string()
            result.append(ChatMessage(0, 0, line))
        return result

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        return super()._parse_char_enum(msg)

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        return super()._parse_chat_message(msg)

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        return super()._parse_guild_roster(msg)

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        """
        Build CMSG_JOIN_CHANNEL for TBC (flat binary layout).

        Args:
            channel_id: Numeric channel ID.
            channel_name_bytes: Channel name as UTF-8 bytes.

        Returns:
            Serialised packet payload.
        """
        pw = PacketWriter()
        pw.write_int_le(channel_id)
        pw.write_byte(0)
        pw.write_byte(1)
        pw.write_bytes(channel_name_bytes)
        pw.write_byte(0)
        pw.write_byte(0)
        return pw.build()
