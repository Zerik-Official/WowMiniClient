"""
MoP game packet handler.
"""

from __future__ import annotations

import hashlib
import logging
import random
import struct

from common.chat import ChatEvents
from common.types import Packet, PacketBitWriter, PacketWriter, global_state
from game.core.packets import (
    AuthResponseCodes,
    GamePacketsMoP,
    GuildEvents,
)
from game.core.cata import GamePacketHandlerCataclysm
from game.models import (
    AuthChallengeMessage,
    CharEnumMessage,
    ChatMessage,
    GuildInfo,
    GuildMember,
    NameQueryMessage,
    Player,
)

logger = logging.getLogger(__name__)


class GamePacketHandlerMoP(GamePacketHandlerCataclysm, GamePacketsMoP):
    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        mid = msg.id
        if mid == self.SMSG_GUILD_MOTD:
            return self._handle_mop_guild_motd(msg)
        if mid == self.SMSG_GUILD_RANKS_UPDATE:
            self._handle_mop_guild_ranks_update(msg)
            return []
        if mid == self.SMSG_GUILD_INVITE_ACCEPT:
            self._handle_mop_guild_invite_accept(msg)
            return []
        if mid == self.SMSG_GUILD_MEMBER_LOGGED:
            self._handle_mop_guild_member_logged(msg)
            return []
        if mid == self.SMSG_GUILD_LEAVE:
            self._handle_mop_guild_leave(msg)
            return []
        return super().handle_packet(msg)

    def send_name_query(self, guid: int) -> None:
        pw = PacketBitWriter()
        guid_bytes = list(struct.pack("<Q", guid))
        pw.write_bit_seq(guid_bytes, 4)
        pw.write_bit(0)
        pw.write_bit_seq(guid_bytes, 6, 0, 7, 1)
        pw.write_bit(0)
        pw.write_bit_seq(guid_bytes, 5, 2, 3)
        pw.flush()
        pw.write_xor_byte_seq(guid_bytes, 7, 5, 1, 2, 6, 3, 0, 4)
        self.send(self.CMSG_NAME_QUERY, pw.build())

    def _parse_name_query(self, msg: Packet) -> NameQueryMessage:
        guid_mask = [0] * 8
        guid2_mask = [0] * 8
        guid3_mask = [0] * 8

        msg.read_bit_seq(guid_mask, 3, 6, 7, 2, 5, 4, 0, 1)
        msg.read_xor_byte_seq(guid_mask, 5, 4, 7, 6, 1, 2)

        has_name_data = msg.read_bit() == 0
        char_class = 0xFF
        if has_name_data:
            msg.skip(8)
            char_class = msg.read_byte()
            msg.skip(3)

        msg.read_xor_byte_seq(guid_mask, 0, 3)

        guid = struct.unpack("<Q", bytes(guid_mask))[0]

        if not has_name_data:
            logger.error(f"RECV SMSG_NAME_QUERY - Name not known for guid {guid}")
            return NameQueryMessage(guid, "UNKNOWN", char_class)

        msg.reset_bit_reader()
        msg.read_bit_seq(guid2_mask, 2, 7)
        msg.read_bit_seq(guid3_mask, 7, 2, 0)
        msg.read_bit()
        msg.read_bit_seq(guid2_mask, 4)
        msg.read_bit_seq(guid3_mask, 5)
        msg.read_bit_seq(guid2_mask, 1, 3, 0)
        msg.read_bits(7 * 5)
        msg.read_bit_seq(guid3_mask, 6, 3)
        msg.read_bit_seq(guid2_mask, 5)
        msg.read_bit_seq(guid3_mask, 1, 4)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid2_mask, 6)
        msg.reset_bit_reader()
        msg.read_xor_byte_seq(guid3_mask, 6, 0)

        name = msg.slice(name_length).decode("utf-8", errors="replace")
        return NameQueryMessage(guid, name, char_class)

    def _parse_invalidate_player(self, msg: Packet) -> int:
        guid_mask = [0] * 8
        msg.read_bit_seq(guid_mask, 6, 3, 1, 2, 7, 5, 0, 4)
        msg.read_xor_byte_seq(guid_mask, 7, 1, 2, 3, 6, 0, 4, 5)
        return struct.unpack("<Q", bytes(guid_mask))[0]

    def _handle_invalidate_player(self, msg: Packet) -> None:
        guid = self._parse_invalidate_player(msg)
        self.player_roster.pop(guid, None)

    def _build_who_message(self, name: str) -> bytes:
        bw = PacketBitWriter()
        bw.write_int_le(0xFFFFFFFF)
        bw.write_int_le(0xFFFFFFFF)
        bw.write_int_le(100)
        bw.write_int_le(0)
        bw.write_bit(1)
        bw.write_bit(1)
        bw.write_bit(0)
        bw.write_bits(0, 9)
        bw.write_bit(1)
        bw.write_bits(len(name), 6)
        bw.write_bits(0, 4)
        bw.write_bits(0, 9)
        bw.write_bits(0, 7)
        bw.write_bits(0, 3)
        bw.flush()
        bw.write_bytes(name.encode("utf-8"))
        return bw.build()

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        msg.skip(35)
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
        pw.write_long_le(0)
        pw.write_byte(digest[18])
        pw.write_byte(digest[14])
        pw.write_byte(digest[3])
        pw.write_byte(digest[4])
        pw.write_byte(digest[0])
        pw.write_int_le(self.realm_id)
        pw.write_byte(digest[11])
        pw.write_int(client_seed)
        pw.write_byte(digest[19])
        pw.write_short_le(1)
        pw.write_byte(digest[2])
        pw.write_byte(digest[9])
        pw.write_byte(digest[12])
        pw.write_long_le(0)
        pw.write_int_le(0)
        pw.write_byte(digest[16])
        pw.write_byte(digest[5])
        pw.write_byte(digest[6])
        pw.write_byte(digest[8])
        pw.write_short_le(global_state.game_build)
        pw.write_byte(digest[17])
        pw.write_byte(digest[7])
        pw.write_byte(digest[13])
        pw.write_byte(digest[15])
        pw.write_byte(digest[1])
        pw.write_byte(digest[10])

        pw.write_int_le(len(self.addon_info))
        pw.write_bytes(self.addon_info)

        bw = PacketBitWriter()
        bw.write_bit(0)
        bw.write_bits(len(account), 11)
        bw.flush()
        pw.write_bytes(bw.build())
        pw.write_bytes(account)

        return AuthChallengeMessage(self.session_key, pw.build())

    def _parse_auth_response(self, msg: Packet) -> int:
        if msg.read_bit() == 1:
            return AuthResponseCodes.AUTH_OK
        return AuthResponseCodes.AUTH_FAILED

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        msg.read_bits(21)
        characters_num = msg.read_bits(16)

        guids = [[0] * 8 for _ in range(characters_num)]
        guild_guids = [[0] * 8 for _ in range(characters_num)]
        name_lengths = [0] * characters_num

        for i in range(characters_num):
            msg.read_bit_seq(guild_guids[i], 4)
            msg.read_bit_seq(guids[i], 0)
            msg.read_bit_seq(guild_guids[i], 3)
            msg.read_bit_seq(guids[i], 3, 7)
            msg.read_bits(2)
            msg.read_bit_seq(guids[i], 6)
            msg.read_bit_seq(guild_guids[i], 6)
            name_lengths[i] = msg.read_bits(6)
            msg.read_bit_seq(guids[i], 1)
            msg.read_bit_seq(guild_guids[i], 1, 0)
            msg.read_bit_seq(guids[i], 4)
            msg.read_bit_seq(guild_guids[i], 7)
            msg.read_bit_seq(guids[i], 2, 5)
            msg.read_bit_seq(guild_guids[i], 2, 5)

        msg.read_bit()

        for i in range(characters_num):
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 1)
            msg.skip(2)
            msg.read_xor_byte_seq(guild_guids[i], 2, 0, 6)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            msg.read_xor_byte_seq(guild_guids[i], 3)
            msg.skip(10)
            msg.read_xor_byte_seq(guild_guids[i], 5)
            msg.skip(207)
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 3, 5)
            msg.skip(4)
            msg.read_xor_byte_seq(guild_guids[i], 4)
            msg.skip(4)
            race = msg.read_byte()
            msg.skip(1)
            msg.read_xor_byte_seq(guild_guids[i], 1)
            msg.skip(1)
            msg.read_xor_byte_seq(guids[i], 0, 2)
            msg.skip(3)
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 4, 7)
            msg.skip(12)
            msg.read_xor_byte_seq(guids[i], 6)
            msg.skip(8)
            msg.read_xor_byte_seq(guild_guids[i], 7)
            msg.skip(4)

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            guild_guid = struct.unpack("<Q", bytes(guild_guids[i]))[0]

            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)

        return None

    def _write_player_login(self) -> bytes:
        bw = PacketBitWriter()
        guid_bytes = list(struct.pack("<Q", self.self_character_id))
        bw.write_int_le(0x43480000)
        bw.write_bit_seq(guid_bytes, 1, 4, 7, 3, 2, 6, 5, 0)
        bw.write_xor_byte_seq(guid_bytes, 5, 1, 0, 6, 2, 4, 7, 3)
        return bw.build()

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(channel_id)
        pw.write_bit(0)
        pw.write_bits(len(channel_name_bytes), 7)
        pw.write_bits(0, 7)
        pw.write_bit(0)
        pw.flush()
        pw.write_bytes(channel_name_bytes)
        return pw.build()

    def _query_guild_name(self, out: list[tuple[int, bytes]]) -> None:
        player_bytes = list(struct.pack("<Q", self.self_character_id))
        guild_bytes = list(struct.pack("<Q", self.guild_guid))
        pw = PacketBitWriter()
        pw.write_bit_seq(player_bytes, 7, 3, 4)
        pw.write_bit_seq(guild_bytes, 3, 4)
        pw.write_bit_seq(player_bytes, 2, 6)
        pw.write_bit_seq(guild_bytes, 2, 5)
        pw.write_bit_seq(player_bytes, 1, 5)
        pw.write_bit_seq(guild_bytes, 7)
        pw.write_bit_seq(player_bytes, 0)
        pw.write_bit_seq(guild_bytes, 1, 6, 0)
        pw.flush()
        pw.write_xor_byte_seq(player_bytes, 7)
        pw.write_xor_byte_seq(guild_bytes, 2, 4, 7)
        pw.write_xor_byte_seq(player_bytes, 6, 0)
        pw.write_xor_byte_seq(guild_bytes, 6, 0, 3)
        pw.write_xor_byte_seq(player_bytes, 2)
        pw.write_xor_byte_seq(guild_bytes, 5)
        pw.write_xor_byte_seq(player_bytes, 3)
        pw.write_xor_byte_seq(guild_bytes, 1)
        pw.write_xor_byte_seq(player_bytes, 4, 1, 5)
        out.append((self.CMSG_GUILD_QUERY, pw.build()))

    def _parse_guild_query(self, msg: Packet) -> GuildInfo:
        guild_guid_arr = [0] * 8
        msg.read_bit_seq(guild_guid_arr, 5)
        msg.read_bit()
        ranks_num = msg.read_bits(21)
        msg.read_bits(4)
        rank_lengths = [msg.read_bits(7) for _ in range(ranks_num)]
        msg.read_bits(4)
        guild_name_length = msg.read_bits(7)
        msg.read_bit_seq(guild_guid_arr, 3, 7, 2, 1, 0, 4, 6)

        msg.skip(8)
        msg.read_xor_byte_seq(guild_guid_arr, 2, 7)
        msg.skip(8)

        ranks: dict[int, str] = {}
        for _ in range(ranks_num):
            msg.skip(4)
            rank_id = msg.read_int_le()
            rank_name = msg.slice(rank_lengths[_]).decode("utf-8", errors="replace")
            ranks[rank_id] = rank_name

        name = msg.slice(guild_name_length).decode("utf-8", errors="replace")
        return GuildInfo(name, ranks)

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        has_sender_name = msg.read_bit() == 0
        msg.read_bit()
        if has_sender_name:
            msg.read_bits(11)
        msg.read_bit()
        has_channel_name = msg.read_bit() == 0
        msg.read_bit()
        msg.read_bit()
        has_chat_tag = msg.read_bit() == 0
        has_realm_id = msg.read_bit() == 0

        group_guid_arr = [0] * 8
        msg.read_bit_seq(group_guid_arr, 0, 1, 5, 4, 3, 2, 6, 7)
        if has_chat_tag:
            msg.read_bits(9)
        msg.read_bit()

        receiver_guid_arr = [0] * 8
        msg.read_bit_seq(receiver_guid_arr, 7, 6, 1, 4, 0, 2, 3, 5)
        msg.read_bit()
        has_language = msg.read_bit() == 0
        has_prefix = msg.read_bit() == 0

        sender_guid_arr = [0] * 8
        msg.read_bit_seq(sender_guid_arr, 0, 3, 7, 2, 1, 5, 4, 6)

        has_achievement = msg.read_bit() == 0
        has_message = msg.read_bit() == 0

        channel_name_length = msg.read_bits(7) if has_channel_name else 0
        message_length = msg.read_bits(12) if has_message else 0

        if not has_message or message_length == 0:
            return None

        has_receiver = msg.read_bit() == 0
        addon_prefix_length = msg.read_bits(5) if has_prefix else 0
        msg.read_bit()
        if has_receiver:
            msg.read_bits(11)
        msg.read_bit()

        guild_guid_arr = [0] * 8
        msg.read_bit_seq(guild_guid_arr, 2, 5, 7, 4, 0, 1, 3, 6)
        msg.read_xor_byte_seq(guild_guid_arr, 4, 5, 7, 3, 2, 6, 0, 1)

        channel_name = msg.slice(channel_name_length).decode("utf-8", errors="replace") if has_channel_name else None
        if has_prefix:
            msg.skip(addon_prefix_length)

        msg.read_xor_byte_seq(sender_guid_arr, 4, 7, 1, 5, 0, 6, 2, 3)
        tp = msg.read_byte()

        sender_guid = struct.unpack("<Q", bytes(sender_guid_arr))[0]
        if tp != ChatEvents.CHAT_MSG_SYSTEM and sender_guid == self.self_character_id:
            return None
        if tp != ChatEvents.CHAT_MSG_GUILD_ACHIEVEMENT and not self._check_channel_enabled(tp, channel_name):
            return None

        achievement_id = msg.read_int_le() if has_achievement else None
        msg.read_xor_byte_seq(group_guid_arr, 1, 3, 4, 6, 0, 2, 5, 7)
        msg.read_xor_byte_seq(receiver_guid_arr, 4, 7, 1, 5, 0, 6, 2, 3)

        language = msg.read_byte() if has_language else 0
        if language == -1:
            return None
        if has_realm_id:
            msg.skip(4)

        txt = msg.slice(message_length).decode("utf-8", errors="replace")

        if has_achievement and achievement_id is not None:
            self._handle_achievement_event(sender_guid, achievement_id)
            return None

        return ChatMessage(sender_guid, tp, txt, channel_name)

    def _parse_server_motd(self, msg: Packet) -> list[ChatMessage]:
        line_count = msg.read_bits(4)
        message_lengths = [msg.read_bits(7) for _ in range(line_count)]
        result = []
        for ml in message_lengths:
            message = msg.slice(ml).decode("utf-8", errors="replace")
            result.append(ChatMessage(0, ChatEvents.CHAT_MSG_SYSTEM, message, None))
        return result

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        count = msg.read_bits(17)
        motd_length = msg.read_bits(10)

        guids = [[0] * 8 for _ in range(count)]
        p_note_lengths = [0] * count
        o_note_lengths = [0] * count
        name_lengths = [0] * count

        for i in range(count):
            o_note_lengths[i] = msg.read_bits(8)
            msg.read_bit_seq(guids[i], 5)
            msg.read_bit()
            p_note_lengths[i] = msg.read_bits(8)
            msg.read_bit_seq(guids[i], 7, 0, 6)
            name_lengths[i] = msg.read_bits(6)
            msg.read_bit()
            msg.read_bit_seq(guids[i], 3, 4, 1, 2)

        g_info_length = msg.read_bits(11)

        roster: dict[int, GuildMember] = {}
        for i in range(count):
            char_class = msg.read_byte()
            msg.skip(4)
            name = msg.slice(name_lengths[i]).decode("utf-8", errors="replace")
            msg.read_xor_byte_seq(guids[i], 0)
            msg.skip(24)
            level = msg.read_byte()
            flags = msg.read_byte()
            zone_id = msg.read_int_le()
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 3)
            msg.skip(8)
            msg.skip(o_note_lengths[i])
            last_logoff = msg.read_float_le()
            msg.skip(1)
            msg.skip(4)
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 5, 7)
            msg.skip(p_note_lengths[i])
            msg.read_xor_byte_seq(guids[i], 4)
            msg.skip(8)
            msg.skip(4)
            msg.read_xor_byte_seq(guids[i], 6, 1, 2)
            is_online = (flags & 0x01) == 0x01

            guid = struct.unpack("<Q", bytes(guids[i]))[0]
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)

        msg.skip(4)
        msg.skip(4)
        msg.skip(g_info_length)
        msg.skip(4)
        self.guild_motd = msg.slice(motd_length).decode("utf-8", errors="replace")
        return roster

    def _parse_notification(self, msg: Packet) -> str:
        length = msg.read_bits(12)
        return msg.slice(length).decode("utf-8", errors="replace")

    def _build_chat_message(self, tp: int, msg_bytes: bytes,
                            target_bytes: bytes | None) -> bytes:
        pw = PacketBitWriter()
        pw.write_int_le(self.language_id)
        if target_bytes is not None and tp == ChatEvents.CHAT_MSG_CHANNEL:
            pw.write_bits(len(target_bytes), 9)
        pw.write_bits(len(msg_bytes), 8)
        if tp == ChatEvents.CHAT_MSG_WHISPER and target_bytes is not None:
            pw.write_bits(len(target_bytes), 9)
        pw.flush()
        pw.write_bytes(msg_bytes)
        if target_bytes is not None:
            pw.write_bytes(target_bytes)
        return pw.build()

    def _handle_mop_guild_motd(self, msg: Packet) -> list[tuple[int, bytes]]:
        length = msg.read_bits(10)
        motd = msg.slice(length).decode("utf-8", errors="replace")
        self.guild_motd = motd
        self._handle_guild_event_common(GuildEvents(True).GE_MOTD, [motd])
        return []

    def _handle_mop_guild_ranks_update(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        target_arr = [0] * 8
        msg.read_bit_seq(target_arr, 5, 6)
        msg.read_bit_seq(guid_arr, 0, 1)
        msg.read_bit_seq(target_arr, 3)
        msg.read_bit_seq(guid_arr, 4)
        msg.read_bit_seq(target_arr, 2)
        msg.read_bit_seq(guid_arr, 6, 3, 7)
        msg.read_bit_seq(target_arr, 4, 0, 1)
        msg.read_bit_seq(guid_arr, 2)
        msg.read_bit_seq(target_arr, 7)
        rank_order = msg.read_bit()
        msg.read_bit_seq(guid_arr, 5)

        msg.read_xor_byte_seq(target_arr, 2)
        msg.read_xor_byte_seq(guid_arr, 1)
        msg.read_xor_byte_seq(target_arr, 6, 1, 5)
        msg.read_xor_byte_seq(guid_arr, 0)
        rank = msg.read_int_le()
        msg.read_xor_byte_seq(guid_arr, 3, 7)
        msg.read_xor_byte_seq(target_arr, 7)
        msg.read_xor_byte_seq(guid_arr, 2)
        msg.read_xor_byte_seq(target_arr, 3, 4)
        msg.read_xor_byte_seq(guid_arr, 6, 5)
        msg.read_xor_byte_seq(target_arr, 0)
        msg.read_xor_byte_seq(guid_arr, 4)

        guid = struct.unpack("<Q", bytes(guid_arr))[0]
        target_guid = struct.unpack("<Q", bytes(target_arr))[0]

        name = self.guild_roster.get(guid)
        target_name = self.guild_roster.get(target_guid)

        if name is None or target_name is None:
            logger.error("GUID for SMSG_GUILD_RANKS_UPDATE not found in guild roster!")
            return

        rank_name = ""
        if self.guild_info and rank in self.guild_info.ranks:
            rank_name = self.guild_info.ranks[rank]
        else:
            logger.error(f"Rank ID {rank} for SMSG_GUILD_RANKS_UPDATE not found!")

        event = GuildEvents(True).GE_PROMOTED if rank_order == 1 else GuildEvents(True).GE_DEMOTED
        self._handle_guild_event_common(event, [name.name, target_name.name, rank_name])

    def _handle_mop_guild_invite_accept(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        msg.read_bit_seq(guid_arr, 6, 1, 3)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid_arr, 7, 4, 2, 5, 0)
        msg.read_xor_byte_seq(guid_arr, 2, 4, 1, 6, 5)
        msg.skip(4)
        msg.read_xor_byte_seq(guid_arr, 3, 0)
        name = msg.slice(name_length).decode("utf-8", errors="replace")
        msg.read_xor_byte_seq(guid_arr, 7)
        self._handle_guild_event_common(GuildEvents(True).GE_JOINED, [name])

    def _handle_mop_guild_member_logged(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        msg.read_bit_seq(guid_arr, 0, 6)
        msg.read_bit()
        msg.read_bit_seq(guid_arr, 2, 5, 3)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid_arr, 1, 7, 4)
        is_online = msg.read_bit() == 1
        msg.read_xor_byte_seq(guid_arr, 3, 2, 0)
        msg.skip(4)
        msg.read_xor_byte_seq(guid_arr, 6)
        name = msg.slice(name_length).decode("utf-8", errors="replace")
        msg.read_xor_byte_seq(guid_arr, 4, 5, 7, 1)

        ge = GuildEvents(True)
        event = ge.GE_SIGNED_ON if is_online else ge.GE_SIGNED_OFF
        self._handle_guild_event_common(event, [name])

    def _handle_mop_guild_leave(self, msg: Packet) -> None:
        guid_arr = [0] * 8
        msg.read_bit_seq(guid_arr, 2)
        name_length = msg.read_bits(6)
        msg.read_bit_seq(guid_arr, 6, 5)
        kicked = msg.read_bit() == 1

        kicker_name_length = 0
        kicker_guid_arr = None
        if kicked:
            msg.read_bits(2)
            kicker_name_length = msg.read_bits(6)
            kicker_guid_arr = [0] * 8
            msg.read_bit_seq(kicker_guid_arr, 1, 3, 4, 2, 5, 7, 6, 0)
            msg.read_bit()

        msg.read_bit_seq(guid_arr, 1, 0, 3, 4, 7)

        kicker_name = ""
        if kicked and kicker_guid_arr is not None:
            msg.read_xor_byte_seq(kicker_guid_arr, 1, 3, 5, 2, 0, 4, 6, 7)
            kicker_name = msg.slice(kicker_name_length).decode("utf-8", errors="replace")
            msg.skip(4)

        name = msg.slice(name_length).decode("utf-8", errors="replace")
        msg.read_xor_byte_seq(guid_arr, 1)
        msg.skip(4)
        msg.read_xor_byte_seq(guid_arr, 0, 4, 2, 3, 6, 5, 7)

        ge = GuildEvents(True)
        if kicked:
            self._handle_guild_event_common(ge.GE_REMOVED, [name, kicker_name])
        else:
            self._handle_guild_event_common(ge.GE_LEFT, [name])
