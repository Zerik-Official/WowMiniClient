"""
WotLK game packet handler.
"""

from __future__ import annotations

import hashlib
import random
import struct

from common.chat import ChatEvents
from utils.logger import Tags, log
from game.core.buffer import Packet, PacketWriter
from common.types import global_state
from game.core.packets import GamePacketsWotLK
from game.core.tbc import GamePacketHandlerTBC
from game.models import (
    AuthChallengeMessage,
    CharEnumMessage,
    ChatMessage,
    NameQueryMessage,
)

class GamePacketHandlerWotLK(GamePacketHandlerTBC, GamePacketsWotLK):
    """WotLK game packet handler."""

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        account = global_state.config.wow.account
        msg.skip(4)
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_int_le(global_state.game_build)
        pw.write_int_le(0)
        pw.write_bytes(account)
        pw.write_byte(0)
        pw.write_int(0)
        pw.write_int(client_seed)
        pw.write_int_le(0)
        pw.write_int_le(0)
        pw.write_int_le(self.realm_id)
        pw.write_long_le(3)

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        pw.write_bytes(md.digest())

        pw.write_bytes(self.addon_info)
        return AuthChallengeMessage(self.session_key, pw.build())

    def _parse_name_query(self, msg: Packet) -> NameQueryMessage:
        guid = 0
        mask = msg.read_byte()
        for i in range(8):
            if mask & (1 << i):
                guid |= (msg.read_byte() & 0xFF) << (i * 8)

        name_known = msg.read_byte()
        if name_known == 0:
            name = msg.read_string()
            msg.skip_string()
            msg.skip(1)
            msg.skip(1)
            char_class = msg.read_byte()
            return NameQueryMessage(guid, name, char_class)
        else:
            log("ERROR", Tags.GAME, f"RECV SMSG_NAME_QUERY - Name not known for guid {guid}")
            return NameQueryMessage(guid, "UNKNOWN", 0xFF)

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        character_bytes = global_state.config.wow.character.lower().encode("utf-8")
        characters_num = msg.read_byte()
        for _ in range(characters_num):
            guid = msg.read_long_le()
            name = msg.read_string()
            race = msg.read_byte()
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(1)
            msg.skip(4)
            msg.skip(4)
            msg.skip(12)
            guild_guid = msg.read_int_le()
            if name.lower().encode("utf-8") == character_bytes:
                return CharEnumMessage(name, guid, race, guild_guid)
            msg.skip(4)
            msg.skip(4)
            msg.skip(1)
            msg.skip(12)
            msg.skip(19 * 9)
            msg.skip(4 * 9)
        return None

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        tp = msg.read_byte()
        lang = msg.read_int_le()
        if lang == -1:
            return None
        guid = msg.read_long_le()
        if tp != ChatEvents.CHAT_MSG_SYSTEM and guid == self.self_character_id:
            return None
        msg.skip(4)

        if msg.id == self.SMSG_GM_MESSAGECHAT:
            msg.skip(4)
            msg.skip_string()

        channel_name: str | None = None
        if tp == ChatEvents.CHAT_MSG_CHANNEL:
            channel_name = msg.read_string()

        if tp != ChatEvents.CHAT_MSG_GUILD_ACHIEVEMENT and not self._check_channel_enabled(tp, channel_name):
            return None

        msg.skip(8)
        txt_len = msg.read_int_le()
        txt = msg.slice(txt_len - 1).decode("utf-8", errors="replace")
        msg.skip(1)
        msg.skip(1)

        if tp == ChatEvents.CHAT_MSG_GUILD_ACHIEVEMENT:
            achievement_id = msg.read_int_le()
            self._handle_achievement_event(guid, achievement_id)
            return None

        return ChatMessage(guid, tp, txt, channel_name)

    def _handle_achievement_event(self, guid: int, achievement_id: int) -> None:
        member = self.guild_roster.get(guid)
        if member:
            self.game_event_callback.achievement(member.name, achievement_id)
