"""
Cataclysm game packet handler.
"""

from __future__ import annotations

import hashlib
import logging
import random
import struct

from common.types import Packet, PacketBitWriter, PacketWriter, global_state
from game.core.packets import (
    AuthResponseCodes,
    GamePacketsCataclysm,
    GuildEvents,
)
from game.core.wotlk import GamePacketHandlerWotLK
from game.models import (
    AuthChallengeMessage,
    CharEnumMessage,
    ChatMessage,
    GuildInfo,
    GuildMember,
)

logger = logging.getLogger(__name__)


class GamePacketHandlerCataclysm(GamePacketHandlerWotLK, GamePacketsCataclysm):
    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        mid = msg.id
        if mid == self.WOW_CONNECTION:
            return [self._handle_wow_connection()]
        return super().handle_packet(msg)

    def _handle_wow_connection(self) -> tuple[int, bytes]:
        pw = PacketWriter()
        pw.write_bytes(b"RLD OF WARCRAFT CONNECTION - CLIENT TO SERVER")
        pw.write_byte(0)
        return (self.WOW_CONNECTION, pw.build())

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        msg.skip(32)
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        digest = md.digest()

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_zeros(9)
        pw.write_byte(digest[10])
        pw.write_byte(digest[18])
        pw.write_byte(digest[12])
        pw.write_byte(digest[5])
        pw.write_zeros(8)
        pw.write_byte(digest[15])
        pw.write_byte(digest[9])
        pw.write_byte(digest[19])
        pw.write_byte(digest[4])
        pw.write_byte(digest[7])
        pw.write_byte(digest[16])
        pw.write_byte(digest[3])
        pw.write_short_le(global_state.game_build)
        pw.write_byte(digest[8])
        pw.write_int_le(self.realm_id)
        pw.write_byte(0)
        pw.write_byte(digest[17])
        pw.write_byte(digest[6])
        pw.write_byte(digest[0])
        pw.write_byte(digest[1])
        pw.write_byte(digest[11])
        pw.write_int(client_seed)
        pw.write_byte(digest[2])
        pw.write_int_le(0)
        pw.write_byte(digest[14])
        pw.write_byte(digest[13])

        pw.write_int_le(len(self.addon_info))
        pw.write_bytes(self.addon_info)

        pw.write_byte(len(account) >> 5)
        pw.write_byte(len(account) << 3)
        pw.write_bytes(account)

        return AuthChallengeMessage(self.session_key, pw.build())

    def _parse_auth_response(self, msg: Packet) -> int:
        if msg.remaining() >= 17:
            msg.skip(16)
        elif msg.remaining() >= 2:
            msg.skip(1)
        else:
            return AuthResponseCodes.AUTH_FAILED
        return super()._parse_auth_response(msg)

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        msg.read_bits(24)
        characters_num = msg.read_bits(17)

        guids = [[0] * 8 for _ in range(characters_num)]
        guild_guids = [[0] * 8 for _ in range(characters_num)]
        name_lengths = [0] * characters_num

        for i in range(characters_num):
            msg.read_bit_seq(guids[i], 3)
            msg.read_bit_seq(guild_guids[i], 1, 7, 2)
            name_lengths[i] = msg.read_bits(7)
            msg.read_bit_seq(guids[i], 4, 7)
            msg.read_bit_seq(guild_guids[i], 3)
            msg.read_bit_seq(guids[i], 5)
            msg.read_bit_seq(guild_guids[i], 6)
            msg.read_bit_seq(guids[i], 1)
            msg.read_bit_seq(guild_guids[i], 5, 4)
            msg.read_bit()
            msg.read_bit_seq(guids[i], 0, 2, 6)
            msg.read_bit_seq(guild_guids[i], 0)

        for i in range(characters_num):
            msg.skip(1)
            msg.skip(207)
            msg.skip(4)
            msg.read_xor_byte_seq(guild_guids[i], 2)
            msg.skip(2)
            msg.read_xor_byte_seq(guild_guids[i], 3)
            msg.skip(9)
            msg.read_xor_byte_seq(guids[i], 4)
            msg.skip(4)
            msg.read_xor_byte_seq(guild_guids[i], 5)
            msg.skip(4)
            msg.read_xor_byte_seq(guild_guids[i], 6)
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 3)
            msg.skip(9)
            msg.read_xor_byte_seq(guids[i], 7)
            msg.skip(1)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            msg.skip(1)
            msg.read_xor_byte_seq(guids[i], 0, 2)
            msg.read_xor_byte_seq(guild_guids[i], 1, 7)
            msg.skip(5)
            race = msg.read_byte()
            msg.skip(1)
            msg.read_xor_byte_seq(guids[i], 6)
            msg.read_xor_byte_seq(guild_guids[i], 4, 0)
            msg.read_xor_byte_seq(guids[i], 5, 1)

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            guild_guid = struct.unpack("<Q", bytes(guild_guids[i]))[0]

            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)

            msg.skip(4)

        return None

    def _write_player_login(self) -> bytes:
        pw = PacketBitWriter()
        guid_bytes = list(struct.pack("<Q", self.self_character_id))
        pw.write_bit_seq(guid_bytes, 2, 3, 0, 6, 4, 5, 1, 7)
        pw.write_xor_byte_seq(guid_bytes, 2, 7, 0, 3, 5, 6, 1, 4)
        return pw.build()

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(channel_id)
        pw.write_bit(0)
        pw.write_bit(0)
        pw.write_bits(len(channel_name_bytes), 8)
        pw.write_bits(0, 8)
        pw.flush()
        pw.write_bytes(channel_name_bytes)
        return pw.build()

    def _query_guild_name(self, out: list[tuple[int, bytes]]) -> None:
        pw = PacketWriter()
        pw.write_long_le(self.guild_guid)
        pw.write_long_le(self.self_character_id)
        out.append((self.CMSG_GUILD_QUERY, pw.build()))

    def _parse_guild_query(self, msg: Packet) -> GuildInfo:
        msg.skip(4)
        return super()._parse_guild_query(msg)

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        motd_length = msg.read_bits(11)
        count = msg.read_bits(18)

        guids = [[0] * 8 for _ in range(count)]
        p_note_lengths = [0] * count
        o_note_lengths = [0] * count
        name_lengths = [0] * count

        for i in range(count):
            msg.read_bit_seq(guids[i], 3, 4)
            msg.read_bits(2)
            p_note_lengths[i] = msg.read_bits(8)
            o_note_lengths[i] = msg.read_bits(8)
            msg.read_bit_seq(guids[i], 0)
            name_lengths[i] = msg.read_bits(7)
            msg.read_bit_seq(guids[i], 1, 2, 6, 5, 7)

        g_info_length = msg.read_bits(12)

        roster: dict[int, GuildMember] = {}
        for i in range(count):
            char_class = msg.read_byte()
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 0)
            msg.skip(40)
            msg.read_xor_byte_seq(guids[i], 2)
            flags = msg.read_byte()
            zone_id = msg.read_int_le()
            msg.skip(8)
            msg.read_xor_byte_seq(guids[i], 7)
            msg.skip(4)
            msg.skip(p_note_lengths[i])
            msg.read_xor_byte_seq(guids[i], 3)
            level = msg.read_byte()
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 5, 4)
            msg.skip(1)
            msg.read_xor_byte_seq(guids[i], 1)
            last_logoff = msg.read_float_le()
            msg.skip(o_note_lengths[i])
            msg.read_xor_byte_seq(guids[i], 6)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            is_online = (flags & 0x01) == 0x01

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)

        msg.skip(g_info_length)
        self.guild_motd = msg.slice(motd_length).decode("utf-8", errors="replace")
        return roster

    def _build_chat_message(self, tp: int, msg_bytes: bytes,
                            target_bytes: bytes | None) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(self.language_id)
        if target_bytes is not None:
            pw.write_bits(len(target_bytes), 10)
        pw.write_bits(len(msg_bytes), 9)
        pw.flush()
        pw.write_bytes(msg_bytes)
        if target_bytes is not None:
            pw.write_bytes(target_bytes)
        return pw.build()

    def _parse_notification(self, msg: Packet) -> str:
        length = msg.read_bits(13)
        return msg.slice(length).decode("utf-8", errors="replace")

    def _handle_notification(self, msg: Packet) -> None:
        logger.info(f"Notification: {self._parse_notification(msg)}")
