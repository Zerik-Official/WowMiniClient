"""
Vanilla game packet handler.
"""

from __future__ import annotations

import hashlib
import random
import struct
import time
from collections.abc import Callable
from typing import Any

from utils.logger import Tags, log
from common.chat import ChatEvents
from game.core.addon_info import ADDON_INFO
from game.core.buffer import Packet, PacketWriter
from common.types import WowExpansion, global_state
from game.core.command_handler import GameCommandHandler
from game.core.gm_commands import (
    LANG_ADDON,
    GmCommandExecutor,
    GmCommandMode,
    GmCommandResult,
)
from game.core.packets import (
    AuthResponseCodes,
    ChatNotify,
    Classes,
    GamePackets,
    GuildEvents,
    Races,
    ServerMessageType,
)
from game.core.resources import GameResources
from game.models import (
    AuthChallengeMessage,
    CharEnumMessage,
    ChatMessage,
    GuildInfo,
    GuildMember,
    NameQueryMessage,
    Player,
)


class GamePacketHandler(GamePackets, GameCommandHandler):
    """Vanilla game packet handler. Base class for all expansion handlers."""

    def __init__(self, realm_id: int, realm_name: str,
                 session_key: bytes,
                 game_event_callback: Any,
                 send_callback: Callable[[int, bytes], None]) -> None:
        """
        Initialise the game packet handler.

        Args:
            realm_id: Numeric realm identifier.
            realm_name: Human-readable realm name.
            session_key: Auth session key bytes.
            game_event_callback: External callback interface for game events.
            send_callback: Function to enqueue outgoing packets.
        """
        self.realm_id = realm_id
        self.realm_name = realm_name
        self.session_key = session_key
        self.game_event_callback = game_event_callback
        self.send = send_callback
        self.addon_info = ADDON_INFO.get(global_state.expansion, ADDON_INFO[WowExpansion.VANILLA])
        self.connect_time = time.time() * 1000

        self.self_character_id: int = 0
        self.language_id: int = 7
        self.in_world = False
        self.guild_guid: int = 0
        self.guild_info: GuildInfo | None = None
        self.guild_motd: str | None = None
        self.player_roster: dict[int, Player] = {}
        self.guild_roster: dict[int, GuildMember] = {}
        self.last_requested_guild_roster: float = 0.0
        self.received_char_enum = False
        self._queued_messages: dict[int, list[ChatMessage]] = {}
        self._ping_id = 0
        gm_cfg = global_state.config.gm_commands
        self.gm_commands = GmCommandExecutor(
            self._send_addon_whisper, self._send_self_whisper,
            mode=GmCommandMode(gm_cfg.mode), timeout=gm_cfg.timeout,
        )

    def handle_packet(self, msg: Packet) -> list[tuple[int, bytes]]:
        """
        Dispatch an incoming packet to its type-specific handler.

        Args:
            msg: Packet with opcode and raw payload data.

        Returns:
            List of (opcode, payload) tuples to be sent back to the server.
        """
        out: list[tuple[int, bytes]] = []
        mid = msg.id

        if mid == self.SMSG_AUTH_CHALLENGE:
            self._handle_auth_challenge(msg, out)
        elif mid == self.SMSG_AUTH_RESPONSE:
            self._handle_auth_response(msg, out)
        elif mid == self.SMSG_NAME_QUERY:
            self._handle_name_query(msg)
        elif mid == self.SMSG_CHAR_ENUM:
            self._handle_char_enum(msg, out)
        elif mid == self.SMSG_LOGIN_VERIFY_WORLD:
            self._handle_login_verify_world(out)
        elif mid == self.SMSG_GUILD_QUERY:
            self._handle_guild_query(msg)
        elif mid == self.SMSG_GUILD_EVENT:
            self._handle_guild_event(msg)
        elif mid == self.SMSG_GUILD_ROSTER:
            self._handle_guild_roster(msg)
        elif mid == self.SMSG_MESSAGECHAT or mid == getattr(self, 'SMSG_GM_MESSAGECHAT', -1):
            self._handle_message_chat(msg)
        elif mid == self.SMSG_CHANNEL_NOTIFY:
            self._handle_channel_notify(msg)
        elif mid == self.SMSG_NOTIFICATION:
            self._handle_notification(msg)
        elif mid == self.SMSG_WHO:
            self._handle_who(msg)
        elif mid == self.SMSG_SERVER_MESSAGE:
            self._handle_server_message(msg)
        elif mid == self.SMSG_INVALIDATE_PLAYER:
            self._handle_invalidate_player(msg)
        elif mid == self.SMSG_WARDEN_DATA:
            self._handle_warden_data(msg, out)
        elif mid == getattr(self, 'SMSG_CHAT_PLAYER_NOTFOUND', -1):
            self._handle_player_notfound(msg)

        return out

    def on_connected(self) -> None:
        """Log a successful connection to the game server."""
        log("INFO", Tags.GAME, "Connected to game server.")

    def disconnect(self) -> None:
        """
        Mark the session as disconnected and notify the event callback.

        Args:
            None.

        Returns:
            None.
        """
        self.in_world = False
        self.gm_commands.cancel("Disconnected from the game server.")
        self.game_event_callback.disconnected()

    MAX_WOW_MESSAGE_LENGTH: int = 255

    def send_message_to_wow(self, tp: int, message: str,
                            target: str | None = None,
                            language: int | None = None) -> None:
        """
        Send a chat message to the WoW game server.

        Args:
            tp: Chat message type constant (e.g. CHAT_MSG_GUILD).
            message: Text content of the message (truncated to 255 chars).
            target: Optional channel or target name for the message.
            language: Language id override (e.g. LANG_ADDON); defaults to
                the character's racial language.
        """
        message = message[:self.MAX_WOW_MESSAGE_LENGTH]
        payload = self._build_chat_message(tp, message.encode("utf-8"),
                                           target.encode("utf-8") if target else None,
                                           language)
        self.send(self.CMSG_MESSAGECHAT, payload)

    async def execute_gm_command(self, command: str) -> GmCommandResult:
        """
        Execute a GM command on the server and wait for its reply.

        Args:
            command: Command text, with or without a leading dot.

        Returns:
            GmCommandResult with status and reply lines.
        """
        return await self.gm_commands.execute(command)

    def _send_addon_whisper(self, message: str) -> None:
        """
        Whisper an addon message (LANG_ADDON) to the own character.

        Args:
            message: Addon text in ``Prefix\\tbody`` form.
        """
        self.send_message_to_wow(ChatEvents.CHAT_MSG_WHISPER, message,
                                 global_state.config.wow.character, LANG_ADDON)

    def _send_self_whisper(self, message: str) -> None:
        """
        Whisper a plain chat message to the own character.

        Args:
            message: Message text.
        """
        self.send_message_to_wow(ChatEvents.CHAT_MSG_WHISPER, message,
                                 global_state.config.wow.character)

    def _intercept_gm_response(self, tp: int, lang: int, text: str) -> bool:
        """
        Route GM command replies to the executor instead of the chat relay.

        Args:
            tp: Chat type constant.
            lang: Language id of the message.
            text: Message text.

        Returns:
            True if the message was consumed as a command reply.
        """
        if lang == LANG_ADDON and tp == ChatEvents.CHAT_MSG_WHISPER:
            return self.gm_commands.on_addon_message(text)
        if tp == ChatEvents.CHAT_MSG_SYSTEM:
            return self.gm_commands.on_system_message(text)
        return False

    def send_notification(self, message: str) -> None:
        """
        Send a guild notification message to WoW.

        Args:
            message: Notification text to send to guild chat.
        """
        self.send_message_to_wow(ChatEvents.CHAT_MSG_GUILD, message)

    def handle_who(self, arguments: str | None) -> str | None:
        """
        Process a WHO query and return the result string.

        Args:
            arguments: Optional search filter text. If None, returns
                a list of online guild members.

        Returns:
            Formatted WHO result string, or None if the query was
            sent to the server and no inline result is available.
        """
        if arguments:
            payload = self._build_who_message(arguments)
            self.send(self.CMSG_WHO, payload)
            return None
        return self._build_guildies_online()

    def handle_gmotd(self) -> str | None:
        """
        Return the guild Message of the Day.

        Returns:
            Guild MOTD string, or None if not yet received.
        """
        return self.guild_motd

    def send_name_query(self, guid: int) -> None:
        """
        Request the name for a character GUID from the server.

        Args:
            guid: 64-bit character GUID to look up.
        """
        pw = PacketWriter()
        pw.write_long_le(guid)
        self.send(self.CMSG_NAME_QUERY, pw.build())

    def send_logout(self) -> bytes | None:
        """
        Build a CMSG_LOGOUT_REQUEST packet.

        Returns:
            Encoded logout request packet bytes.
        """
        return struct.pack("<H", self.CMSG_LOGOUT_REQUEST)

    def _handle_auth_challenge(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        """
        Parse and respond to SMSG_AUTH_CHALLENGE.

        Args:
            msg: Incoming auth challenge packet.
            out: Accumulator list for outgoing packets.
        """
        auth_msg = self._parse_auth_challenge(msg)
        global_state.game_crypt.init(auth_msg.session_key)
        out.append((self.CMSG_AUTH_CHALLENGE, auth_msg.response))

    def _parse_auth_challenge(self, msg: Packet) -> AuthChallengeMessage:
        """
        Parse SMSG_AUTH_CHALLENGE and build CMSG_AUTH_SESSION.

        Args:
            msg: Incoming auth challenge packet.

        Returns:
            AuthChallengeMessage with session_key and response payload.
        """
        account = global_state.config.wow.account
        server_seed = msg.read_int()
        client_seed = random.randint(0, 0x7FFFFFFF)

        pw = PacketWriter()
        pw.write_short_le(0)
        pw.write_int_le(global_state.game_build)
        pw.write_int_le(0)
        pw.write_bytes(account)
        pw.write_byte(0)
        pw.write_int(client_seed)

        md = hashlib.sha1()
        md.update(account)
        md.update(b"\x00\x00\x00\x00")
        md.update(struct.pack(">I", client_seed))
        md.update(struct.pack(">I", server_seed))
        md.update(self.session_key)
        pw.write_bytes(md.digest())

        pw.write_bytes(self.addon_info)
        return AuthChallengeMessage(self.session_key, pw.build())

    def _handle_auth_response(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        """
        Handle SMSG_AUTH_RESPONSE and trigger character enum on success.

        Args:
            msg: Incoming auth response packet.
            out: Accumulator list for outgoing packets.
        """
        code = self._parse_auth_response(msg)
        if code == AuthResponseCodes.AUTH_OK:
            log("INFO", Tags.GAME, "Successfully logged in!")
            self._send_char_enum(out)
        elif code == AuthResponseCodes.AUTH_WAIT_QUEUE:
            if msg.remaining() >= 14:
                msg.skip(10)
            position = msg.read_int_le()
            log("INFO", Tags.GAME, f"Queue enabled. Position: {position}")
        else:
            log("ERROR", Tags.GAME, AuthResponseCodes.get_message(code))
            self.game_event_callback.error()

    def _parse_auth_response(self, msg: Packet) -> int:
        """
        Parse SMSG_AUTH_RESPONSE.

        Args:
            msg: Incoming auth response packet.

        Returns:
            Auth response code as integer.
        """
        return msg.read_byte()

    def _send_char_enum(self, out: list[tuple[int, bytes]]) -> None:
        """
        Enqueue CMSG_CHAR_ENUM if not already received.

        Args:
            out: Accumulator list for outgoing packets.
        """
        if not self.received_char_enum:
            out.append((self.CMSG_CHAR_ENUM, b""))

    def _handle_char_enum(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        """
        Parse SMSG_CHAR_ENUM and initiate player login.

        Args:
            msg: Incoming character list packet.
            out: Accumulator list for outgoing packets.
        """
        if self.received_char_enum:
            if self.in_world:
                return
            else:
                log("INFO", Tags.GAME, "Received character enum more than once. Trying again...")
        self.received_char_enum = True
        character = self._parse_char_enum(msg)
        if character is None:
            log("ERROR", Tags.GAME, f"Character {global_state.config.wow.character} not found!")
        else:
            log("INFO", Tags.GAME, f"Logging in with character {character.name}")
            self.self_character_id = character.guid
            self.language_id = Races.get_language(character.race)
            self.guild_guid = character.guild_guid
            payload = self._write_player_login()
            out.append((self.CMSG_PLAYER_LOGIN, payload))

    def _parse_char_enum(self, msg: Packet) -> CharEnumMessage | None:
        """
        Parse SMSG_CHAR_ENUM and find the configured character.

        Args:
            msg: Incoming character list packet.

        Returns:
            CharEnumMessage for the matching character, or None.
        """
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
            msg.skip(1)
            msg.skip(12)
            msg.skip(19 * 5)
            msg.skip(5)
        return None

    def _write_player_login(self) -> bytes:
        """
        Build CMSG_PLAYER_LOGIN payload for Vanilla.

        Returns:
            Serialised packet payload.
        """
        pw = PacketWriter()
        pw.write_long_le(self.self_character_id)
        return pw.build()

    def _handle_login_verify_world(self, out: list[tuple[int, bytes]]) -> None:
        """
        Handle SMSG_LOGIN_VERIFY_WORLD: mark in-world and join channels.

        Args:
            out: Accumulator list for outgoing packets.
        """
        if self.in_world:
            return
        log("INFO", Tags.GAME, "Successfully joined the world!")
        self.in_world = True
        self.game_event_callback.connected()
        self._run_keep_alive(out)
        self._run_guild_roster_executor(out)
        if self.guild_guid != 0:
            self._query_guild_name(out)
            self._update_guild_roster(out)
        self._join_channels(out)
        if global_state.config.gm_commands.enabled:
            self.gm_commands.start()

    def _run_keep_alive(self, out: list[tuple[int, bytes]]) -> None:
        """
        Send a keep-alive packet (no-op in Vanilla, overridden in TBC+).

        Args:
            out: Accumulator list for outgoing packets.
        """
        pass

    def _run_guild_roster_executor(self, out: list[tuple[int, bytes]]) -> None:
        """
        Request the initial guild roster.

        Args:
            out: Accumulator list for outgoing packets.
        """
        self.last_requested_guild_roster = time.time() * 1000
        out.append((self.CMSG_GUILD_ROSTER, b""))

    def _query_guild_name(self, out: list[tuple[int, bytes]]) -> None:
        """Build CMSG_GUILD_QUERY packet and append to output.

        Args:
            out: Accumulator list for outgoing packets.
        """
        pw = PacketWriter()
        pw.write_int_le(self.guild_guid & 0xFFFFFFFF)
        out.append((self.CMSG_GUILD_QUERY, pw.build()))

    def _update_guild_roster(self, out: list[tuple[int, bytes]]) -> None:
        """
        Request a fresh guild roster.

        Args:
            out: Accumulator list for outgoing packets.
        """
        self.last_requested_guild_roster = time.time() * 1000
        out.append((self.CMSG_GUILD_ROSTER, b""))

    def _join_channels(self, out: list[tuple[int, bytes]]) -> None:
        """
        Join all configured WoW channels.

        Args:
            out: Accumulator list for outgoing packets.
        """
        for channel_cfg in global_state.config.channels:
            channel_name = channel_cfg.wow.channel
            if channel_name is None:
                continue
            channel_id = channel_cfg.wow.id or 0
            log("INFO", Tags.GAME, f"Joining channel {channel_name}")
            payload = self._write_join_channel(channel_id, channel_name.encode("utf-8"))
            out.append((self.CMSG_JOIN_CHANNEL, payload))

    def _write_join_channel(self, channel_id: int,
                            channel_name_bytes: bytes) -> bytes:
        """
        Build CMSG_JOIN_CHANNEL payload for Vanilla.

        Args:
            channel_id: Numeric channel ID.
            channel_name_bytes: Channel name as UTF-8 bytes.

        Returns:
            Serialised packet payload.
        """
        pw = PacketWriter()
        pw.write_int_le(channel_id)
        pw.write_byte(0)
        pw.write_byte(0)
        pw.write_bytes(channel_name_bytes)
        pw.write_byte(0)
        pw.write_byte(0)
        return pw.build()

    def _handle_guild_query(self, msg: Packet) -> None:
        """
        Parse and store SMSG_GUILD_QUERY_RESPONSE.

        Args:
            msg: Incoming guild query response.
        """
        self.guild_info = self._parse_guild_query(msg)

    def _parse_guild_query(self, msg: Packet) -> GuildInfo:
        """
        Parse SMSG_GUILD_QUERY_RESPONSE for Vanilla.

        Args:
            msg: Incoming guild query response.

        Returns:
            GuildInfo with guild name and rank names.
        """
        msg.skip(4)
        name = msg.read_string()
        ranks: dict[int, str] = {}
        for i in range(10):
            rank_name = msg.read_string()
            if rank_name:
                ranks[i] = rank_name
        return GuildInfo(name, ranks)

    def _handle_guild_event(self, msg: Packet) -> None:
        """
        Parse and dispatch SMSG_GUILD_EVENT.

        Args:
            msg: Incoming guild event packet.
        """
        event = msg.read_byte()
        num_strings = msg.read_byte()
        messages = [msg.read_string() for _ in range(num_strings)]
        self._handle_guild_event_common(event, messages)

    def _handle_guild_event_common(self, event: int, messages: list[str]) -> None:
        """
        Format a guild event using the configured template and forward it.

        Args:
            event: Guild event type constant.
            messages: Event argument strings (e.g. player names).
        """
        ge = GuildEvents(global_state.expansion != WowExpansion.VANILLA)
        if all(m.strip() == "" for m in messages):
            return
        if event != ge.GE_MOTD and global_state.config.wow.character.lower() == messages[0].lower():
            return

        event_key_map: dict[int, str] = {}

        event_key_map[ge.GE_PROMOTED] = "ge_promoted"
        event_key_map[ge.GE_DEMOTED] = "ge_demoted"
        event_key_map[ge.GE_MOTD] = "ge_motd"
        event_key_map[ge.GE_JOINED] = "ge_joined"
        event_key_map[ge.GE_LEFT] = "ge_left"
        event_key_map[ge.GE_REMOVED] = "ge_removed"
        event_key_map[ge.GE_SIGNED_ON] = "ge_signed_on"
        event_key_map[ge.GE_SIGNED_OFF] = "ge_signed_off"

        event_key = event_key_map.get(event)
        if event_key is None:
            return

        _EVENT_TO_CFG: dict[str, str] = {
            "ge_promoted": "promoted", "ge_demoted": "demoted",
            "ge_motd": "motd", "ge_joined": "joined",
            "ge_left": "left", "ge_removed": "removed",
            "ge_signed_on": "online", "ge_signed_off": "offline",
        }
        cfg_key = _EVENT_TO_CFG.get(event_key)
        if not cfg_key:
            return
        notif = global_state.config.guild.notification_configs.get(cfg_key)
        if not notif or not notif.enabled:
            return
        template = notif.format

        name = messages[0] if len(messages) > 0 else ""
        msg = template.replace("%n", name)
        msg = msg.replace("%N", str(global_state.config.wow.character))

        target_name = messages[1] if len(messages) > 1 else ""
        msg = msg.replace("%t", target_name)

        rank_name = messages[2] if len(messages) > 2 else ""
        msg = msg.replace("%r", rank_name)

        msg = msg.replace("%c", self.guild_info.name if self.guild_info else "Unknown")

        log("INFO", Tags.GAME, f"Guild event: {msg}")
        self.game_event_callback.chat_message(None, msg, ChatEvents.CHAT_MSG_SYSTEM, None)

    def _handle_guild_roster(self, msg: Packet) -> None:
        """
        Parse and store SMSG_GUILD_ROSTER.

        Args:
            msg: Incoming guild roster packet.
        """
        self.guild_roster = self._parse_guild_roster(msg)
        log("DEBUG", Tags.GAME, f"Guild roster received with {len(self.guild_roster)} members.")
        self.game_event_callback.guild_roster_updated()

    def _parse_guild_roster(self, msg: Packet) -> dict[int, GuildMember]:
        """
        Parse SMSG_GUILD_ROSTER for Vanilla.

        Args:
            msg: Incoming guild roster packet.

        Returns:
            Dict mapping GUID to GuildMember.
        """
        count = msg.read_int_le()
        self.guild_motd = msg.read_string()
        msg.skip_string()
        rank_count = msg.read_int_le()
        msg.skip(4 * rank_count)
        roster: dict[int, GuildMember] = {}
        for _ in range(count):
            guid = msg.read_long_le()
            is_online = msg.read_boolean()
            name = msg.read_string()
            msg.skip(4)
            level = msg.read_byte()
            char_class = msg.read_byte()
            zone_id = msg.read_int_le()
            if is_online:
                last_logoff = 0.0
            else:
                last_logoff = msg.read_float_le()
            msg.skip_string()
            msg.skip_string()
            roster[guid] = GuildMember(name, is_online, char_class, level, zone_id, last_logoff)
        return roster

    def _handle_message_chat(self, msg: Packet) -> None:
        """
        Parse and forward a SMSG_MESSAGECHAT.

        Args:
            msg: Incoming chat message packet.
        """
        log("DEBUG", Tags.GAME, f"RECV CHAT: {bytes(msg.data[msg._pos:]).hex()}")
        chat_msg = self._parse_chat_message(msg)
        if chat_msg is not None:
            self._send_chat_message(chat_msg)

    def _parse_chat_message(self, msg: Packet) -> ChatMessage | None:
        """
        Parse SMSG_MESSAGECHAT for Vanilla.

        Args:
            msg: Incoming chat message packet.

        Returns:
            ChatMessage or None if the message should be filtered.
        """
        tp = msg.read_byte()
        lang = msg.read_int_le()

        channel_name: str | None = None
        if tp == ChatEvents.CHAT_MSG_CHANNEL:
            channel_name = msg.read_string()
            msg.skip(4)

        guid = msg.read_long_le()
        if tp in (ChatEvents.CHAT_MSG_SAY, ChatEvents.CHAT_MSG_YELL):
            msg.skip(8)

        txt_len = msg.read_int_le()
        txt = msg.slice(txt_len - 1).decode("utf-8", errors="replace")
        msg.skip(1)

        if self._intercept_gm_response(tp, lang, txt) or lang == LANG_ADDON:
            return None
        if not self._check_channel_enabled(tp, channel_name):
            log("DEBUG", Tags.GAME, f"Unhandled chat type tp=0x{tp:02X} channel={channel_name}")
            return None
        if tp != ChatEvents.CHAT_MSG_SYSTEM and guid == self.self_character_id:
            return None
        is_gm = getattr(self, 'SMSG_GM_MESSAGECHAT', None) is not None and msg.id == self.SMSG_GM_MESSAGECHAT
        return ChatMessage(guid, tp, txt, channel_name, is_gm=is_gm)

    def _check_channel_enabled(self, tp: int, channel_name: str | None) -> bool:
        """
        Check whether a chat type is routed to Discord.

        Args:
            tp: Chat type constant.
            channel_name: Channel name (for CHAT_MSG_CHANNEL).

        Returns:
            True if the channel is enabled in config.
        """
        return (tp, channel_name.lower() if channel_name else None) in global_state.wow_to_discord

    def _send_chat_message(self, chat_msg: ChatMessage) -> None:
        """
        Forward a ChatMessage to the event callback, resolving names.

        If the sender GUID is unknown, a name query is queued.

        Args:
            chat_msg: The parsed chat message.
        """
        if chat_msg.guid == 0:
            self.game_event_callback.chat_message(None, chat_msg.message,
                                                  chat_msg.tp, chat_msg.channel,
                                                  is_gm=chat_msg.is_gm)
        elif chat_msg.guid in self.player_roster:
            player = self.player_roster[chat_msg.guid]
            self.game_event_callback.chat_message(player.name, chat_msg.message,
                                                  chat_msg.tp, chat_msg.channel,
                                                  is_gm=chat_msg.is_gm)
        else:
            if chat_msg.guid not in self._queued_messages:
                self._queued_messages[chat_msg.guid] = []
            self._queued_messages[chat_msg.guid].append(chat_msg)
            self.send_name_query(chat_msg.guid)

    def _handle_name_query(self, msg: Packet) -> None:
        """
        Process SMSG_NAME_QUERY_RESPONSE and deliver queued messages.

        Args:
            msg: Incoming name query response.
        """
        nq = self._parse_name_query(msg)
        messages = self._queued_messages.pop(nq.guid, [])
        for chat_msg in messages:
            self.game_event_callback.chat_message(nq.name, chat_msg.message,
                                                  chat_msg.tp, chat_msg.channel,
                                                  is_gm=chat_msg.is_gm)
        self.player_roster[nq.guid] = Player(nq.name, nq.char_class)

    def _parse_name_query(self, msg: Packet) -> NameQueryMessage:
        """
        Parse SMSG_NAME_QUERY_RESPONSE for Vanilla.

        Args:
            msg: Incoming name query response.

        Returns:
            NameQueryMessage with guid, name, and class.
        """
        guid = msg.read_long_le()
        name = msg.read_string()
        msg.skip_string()
        msg.skip(4)
        msg.skip(4)
        char_class = msg.read_int_le() & 0xFF
        return NameQueryMessage(guid, name, char_class)

    def _handle_channel_notify(self, msg: Packet) -> None:
        """
        Log SMSG_CHANNEL_NOTIFY messages (join, ban, mute, etc.).

        Args:
            msg: Incoming channel notify packet.
        """
        cid = msg.read_byte()
        channel_name = msg.read_string()
        messages = {
            ChatNotify.CHAT_YOU_JOINED_NOTICE: f"Joined Channel: [{channel_name}]",
            ChatNotify.CHAT_WRONG_PASSWORD_NOTICE: f"Wrong password for {channel_name}.",
            ChatNotify.CHAT_MUTED_NOTICE: f"[{channel_name}] You do not have permission to speak.",
            ChatNotify.CHAT_BANNED_NOTICE: f"[{channel_name}] You are banned from that channel.",
            ChatNotify.CHAT_WRONG_FACTION_NOTICE: f"Wrong alliance for {channel_name}.",
            ChatNotify.CHAT_INVALID_NAME_NOTICE: "Invalid channel name",
            ChatNotify.CHAT_THROTTLED_NOTICE: f"[{channel_name}] The number of messages... is limited, please wait.",
            ChatNotify.CHAT_NOT_IN_AREA_NOTICE: f"[{channel_name}] You are not in the correct area.",
            ChatNotify.CHAT_NOT_IN_LFG_NOTICE: f"[{channel_name}] You must be queued in looking for group.",
        }
        err_msg = messages.get(cid)
        if err_msg:
            if cid == ChatNotify.CHAT_YOU_JOINED_NOTICE:
                log("INFO", Tags.GAME, err_msg)
            else:
                log("ERROR", Tags.GAME, err_msg)

    def _handle_notification(self, msg: Packet) -> None:
        """
        Log SMSG_NOTIFICATION.

        Args:
            msg: Incoming notification packet.
        """
        log("INFO", Tags.GAME, f"Notification: {msg.read_string()}")

    def _handle_who(self, msg: Packet) -> None:
        """
        Handle SMSG_WHO (no-op in base handler, may be overridden).

        Args:
            msg: Incoming WHO response packet.
        """
        pass

    def _handle_server_message(self, msg: Packet) -> None:
        """
        Parse and forward SMSG_SERVER_MESSAGE (shutdown/restart notices).

        Args:
            msg: Incoming server message packet.
        """
        tp = msg.read_int_le()
        txt = msg.read_string()
        messages = {
            ServerMessageType.SERVER_MSG_SHUTDOWN_TIME: f"Shutdown in {txt}",
            ServerMessageType.SERVER_MSG_RESTART_TIME: f"Restart in {txt}",
            ServerMessageType.SERVER_MSG_SHUTDOWN_CANCELLED: "Shutdown cancelled.",
            ServerMessageType.SERVER_MSG_RESTART_CANCELLED: "Restart cancelled.",
        }
        message = messages.get(tp, txt)
        self.game_event_callback.chat_message(None, message,
                                              ChatEvents.CHAT_MSG_SYSTEM, None)

    def _handle_invalidate_player(self, msg: Packet) -> None:
        """
        Remove a player from the local roster on SMSG_INVALIDATE_PLAYER.

        Args:
            msg: Incoming invalidate player packet.
        """
        guid = msg.read_long_le()
        self.player_roster.pop(guid, None)

    def _handle_player_notfound(self, msg: Packet) -> None:
        """
        Handle SMSG_CHAT_PLAYER_NOTFOUND (target player offline / does not exist).

        Forwards the target name to the Discord bot for error routing.

        Args:
            msg: Incoming packet containing the player name as a null-terminated string.
        """
        target = msg.read_string()
        self.game_event_callback.chat_player_notfound(target)

    def _handle_warden_data(self, msg: Packet, out: list[tuple[int, bytes]]) -> None:
        """
        Log a warning for unsupported Warden on Windows.

        Args:
            msg: Incoming Warden data packet.
            out: Accumulator list for outgoing packets.
        """
        if global_state.config.wow.platform.value == "Windows":
            log("ERROR", Tags.GAME, "WARDEN ON WINDOWS IS NOT SUPPORTED!")
            return

    def _build_chat_message(self, tp: int, msg_bytes: bytes,
                            target_bytes: bytes | None,
                            language: int | None = None) -> bytes:
        """
        Build a CMSG_MESSAGECHAT packet for Vanilla.

        Args:
            tp: Chat type constant.
            msg_bytes: Message content as UTF-8 bytes.
            target_bytes: Optional target/channel name as bytes.
            language: Language id override; defaults to ``language_id``.

        Returns:
            Serialised packet payload.
        """
        pw = PacketWriter()
        pw.write_int_le(tp)
        pw.write_int_le(self.language_id if language is None else language)
        if target_bytes:
            pw.write_bytes(target_bytes)
            pw.write_byte(0)
        pw.write_bytes(msg_bytes)
        pw.write_byte(0)
        return pw.build()

    def _build_who_message(self, name: str) -> bytes:
        """
        Build a CMSG_WHO packet for Vanilla.

        Args:
            name: Player name or filter string.

        Returns:
            Serialised packet payload.
        """
        pw = PacketWriter()
        pw.write_int_le(0)
        pw.write_int_le(100)
        pw.write_bytes(name.encode("utf-8"))
        pw.write_byte(0)
        pw.write_byte(0)
        pw.write_int_le(0xFFFFFFFF)
        pw.write_int_le(0xFFFFFFFF)
        pw.write_int_le(0)
        pw.write_int_le(0)
        return pw.build()

    def _build_guildies_online(self) -> str:
        """
        Build a formatted list of online guild members.

        Returns:
            Human-readable guild roster string.
        """
        character_name = global_state.config.wow.character.lower()
        online = [
            m for m in self.guild_roster.values()
            if m.is_online and m.name.lower() != character_name
        ]
        online.sort(key=lambda m: m.name.lower())

        if not online:
            return "Currently no guildies online."

        parts = [
            f"{m.name} ({m.level} {Classes.value_of(m.char_class)} in {GameResources.AREA.get(m.zone_id, 'Unknown Zone')})"
            for m in online
        ]
        count = len(online)
        guildie_word = "guildie" + ("s" if count != 1 else "")
        return f"Currently {count} {guildie_word} online:\n" + ", ".join(parts)

    def ping(self) -> bytes | None:
        """
        Build a CMSG_PING response with randomised latency.

        Returns:
            Encoded ping response packet bytes.
        """
        latency = random.randint(90, 139)
        pw = PacketWriter()
        pw.write_int_le(self._ping_id)
        pw.write_int_le(latency)
        self._ping_id += 1
        return pw.build()
