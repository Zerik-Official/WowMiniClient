"""
Game protocol opcodes per expansion and supporting enums.
"""

from __future__ import annotations


class GamePackets:
    """Vanilla game protocol opcodes."""
    CMSG_CHAR_ENUM: int = 0x37
    SMSG_CHAR_ENUM: int = 0x3B
    CMSG_PLAYER_LOGIN: int = 0x3D
    CMSG_LOGOUT_REQUEST: int = 0x4B
    CMSG_NAME_QUERY: int = 0x50
    SMSG_NAME_QUERY: int = 0x51
    CMSG_GUILD_QUERY: int = 0x54
    SMSG_GUILD_QUERY: int = 0x55
    CMSG_WHO: int = 0x62
    SMSG_WHO: int = 0x63
    CMSG_GUILD_ROSTER: int = 0x89
    SMSG_GUILD_ROSTER: int = 0x8A
    SMSG_GUILD_EVENT: int = 0x92
    CMSG_MESSAGECHAT: int = 0x95
    SMSG_MESSAGECHAT: int = 0x96
    CMSG_JOIN_CHANNEL: int = 0x97
    SMSG_CHANNEL_NOTIFY: int = 0x99

    SMSG_NOTIFICATION: int = 0x01CB
    CMSG_PING: int = 0x01DC
    SMSG_AUTH_CHALLENGE: int = 0x01EC
    CMSG_AUTH_CHALLENGE: int = 0x01ED
    SMSG_AUTH_RESPONSE: int = 0x01EE
    SMSG_LOGIN_VERIFY_WORLD: int = 0x0236
    SMSG_SERVER_MESSAGE: int = 0x0291

    SMSG_WARDEN_DATA: int = 0x02E6
    CMSG_WARDEN_DATA: int = 0x02E7

    SMSG_INVALIDATE_PLAYER: int = 0x031C

    SMSG_TIME_SYNC_REQ: int = 0x0390
    CMSG_TIME_SYNC_RESP: int = 0x0391


class GamePacketsTBC(GamePackets):
    """TBC-specific opcode overrides."""
    SMSG_GM_MESSAGECHAT: int = 0x03B2
    SMSG_MOTD: int = 0x033D
    CMSG_KEEP_ALIVE: int = 0x0406


class GamePacketsWotLK(GamePacketsTBC):
    """WotLK-specific opcode overrides."""
    SMSG_GM_MESSAGECHAT: int = 0x03B3
    CMSG_KEEP_ALIVE: int = 0x0407


class GamePacketsCataclysm(GamePacketsWotLK):
    """Cataclysm-specific opcodes and CMSG_MESSAGECHAT subtypes."""
    CMSG_CHAR_ENUM: int = 0x0502
    SMSG_CHAR_ENUM: int = 0x10B0
    CMSG_PLAYER_LOGIN: int = 0x05B1
    CMSG_LOGOUT_REQUEST: int = 0x0A25
    CMSG_NAME_QUERY: int = 0x2224
    SMSG_NAME_QUERY: int = 0x6E04
    CMSG_WHO: int = 0x6C15
    SMSG_WHO: int = 0x6907
    CMSG_GUILD_QUERY: int = 0x4426
    SMSG_GUILD_QUERY: int = 0x0E06
    CMSG_GUILD_ROSTER: int = 0x1226
    SMSG_GUILD_ROSTER: int = 0x3DA3
    SMSG_GUILD_EVENT: int = 0x0705
    SMSG_MESSAGECHAT: int = 0x2026
    SMSG_GM_MESSAGECHAT: int = 0x6434
    CMSG_JOIN_CHANNEL: int = 0x0156
    SMSG_CHANNEL_NOTIFY: int = 0x0825

    SMSG_NOTIFICATION: int = 0x14A0
    CMSG_PING: int = 0x444D
    SMSG_AUTH_CHALLENGE: int = 0x4542
    CMSG_AUTH_CHALLENGE: int = 0x0449
    SMSG_AUTH_RESPONSE: int = 0x5DB6
    SMSG_LOGIN_VERIFY_WORLD: int = 0x2005
    SMSG_SERVER_MESSAGE: int = 0x6C04

    SMSG_WARDEN_DATA: int = 0x12E7
    CMSG_WARDEN_DATA: int = 0x12E8

    SMSG_INVALIDATE_PLAYER: int = 0x6325
    CMSG_KEEP_ALIVE: int = 0x0015

    SMSG_TIME_SYNC_REQ: int = 0x3CA4
    CMSG_TIME_SYNC_RESP: int = 0x3B0C

    SMSG_MOTD: int = 0x0A35

    WOW_CONNECTION: int = 0x4F57

    CMSG_MESSAGECHAT_AFK: int = 0x0D44
    CMSG_MESSAGECHAT_BATTLEGROUND: int = 0x2156
    CMSG_MESSAGECHAT_CHANNEL: int = 0x1D44
    CMSG_MESSAGECHAT_DND: int = 0x2946
    CMSG_MESSAGECHAT_EMOTE: int = 0x1156
    CMSG_MESSAGECHAT_GUILD: int = 0x3956
    CMSG_MESSAGECHAT_OFFICER: int = 0x1946
    CMSG_MESSAGECHAT_PARTY: int = 0x1D46
    CMSG_MESSAGECHAT_SAY: int = 0x1154
    CMSG_MESSAGECHAT_WHISPER: int = 0x0D56
    CMSG_MESSAGECHAT_YELL: int = 0x3544

    COMPRESSED_DATA_MASK: int = 0x8000


class GamePacketsMoP(GamePacketsCataclysm):
    """MoP-specific opcode overrides including guild events."""
    CMSG_MESSAGECHAT_AFK: int = 0x0EAB
    CMSG_MESSAGECHAT_CHANNEL: int = 0x00BB
    CMSG_MESSAGECHAT_DND: int = 0x002E
    CMSG_MESSAGECHAT_EMOTE: int = 0x103E
    CMSG_MESSAGECHAT_GUILD: int = 0x0CAE
    CMSG_MESSAGECHAT_OFFICER: int = 0x0ABF
    CMSG_MESSAGECHAT_PARTY: int = 0x109A
    CMSG_MESSAGECHAT_SAY: int = 0x0A9A
    CMSG_MESSAGECHAT_WHISPER: int = 0x123E
    CMSG_MESSAGECHAT_YELL: int = 0x04AA

    CMSG_CHAR_ENUM: int = 0x00E0
    SMSG_CHAR_ENUM: int = 0x11C3
    CMSG_PLAYER_LOGIN: int = 0x158F
    CMSG_LOGOUT_REQUEST: int = 0x1349
    CMSG_NAME_QUERY: int = 0x0328
    SMSG_NAME_QUERY: int = 0x169B
    CMSG_GUILD_QUERY: int = 0x1AB6
    SMSG_GUILD_QUERY: int = 0x1B79
    CMSG_WHO: int = 0x18A3
    SMSG_WHO: int = 0x161B
    CMSG_GUILD_ROSTER: int = 0x1459
    SMSG_GUILD_ROSTER: int = 0x0BE0
    SMSG_MESSAGECHAT: int = 0x1A9A
    CMSG_JOIN_CHANNEL: int = 0x148E
    SMSG_CHANNEL_NOTIFY: int = 0x0F06

    SMSG_NOTIFICATION: int = 0x0C2A
    CMSG_PING: int = 0x0012
    SMSG_AUTH_CHALLENGE: int = 0x0949
    CMSG_AUTH_CHALLENGE: int = 0x00B2
    SMSG_AUTH_RESPONSE: int = 0x0ABA
    SMSG_LOGIN_VERIFY_WORLD: int = 0x1C0F
    SMSG_SERVER_MESSAGE: int = 0x0302

    SMSG_WARDEN_DATA: int = 0x0C0A
    CMSG_WARDEN_DATA: int = 0x1816

    SMSG_INVALIDATE_PLAYER: int = 0x102E
    CMSG_KEEP_ALIVE: int = 0x1A87

    SMSG_TIME_SYNC_REQ: int = 0x1A8F
    CMSG_TIME_SYNC_RESP: int = 0x01DB

    SMSG_MOTD: int = 0x183B

    SMSG_GUILD_MOTD: int = 0x0B68
    SMSG_GUILD_RANKS_UPDATE: int = 0x0A60
    SMSG_GUILD_INVITE_ACCEPT: int = 0x0B69
    SMSG_GUILD_MEMBER_LOGGED: int = 0x0B70
    SMSG_GUILD_LEAVE: int = 0x0BF8

    SMSG_COMPRESSED_DATA: int = 0x1568


class Races:
    """Playable race constants."""
    RACE_HUMAN: int = 0x01
    RACE_ORC: int = 0x02
    RACE_DWARF: int = 0x03
    RACE_NIGHTELF: int = 0x04
    RACE_UNDEAD: int = 0x05
    RACE_TAUREN: int = 0x06
    RACE_GNOME: int = 0x07
    RACE_TROLL: int = 0x08
    RACE_GOBLIN: int = 0x09
    RACE_BLOODELF: int = 0x0A
    RACE_DRAENEI: int = 0x0B
    RACE_WORGEN: int = 0x16
    RACE_PANDAREN_NEUTRAL: int = 0x18
    RACE_PANDAREN_ALLIANCE: int = 0x19
    RACE_PANDAREN_HORDE: int = 0x1A

    @staticmethod
    def get_language(race: int) -> int:
        """
        Return the default language ID for a given race.

        Args:
            race: Race constant from Races.

        Returns:
            Language ID (0x01 for Horde, 0x07 for Alliance, 0x2A for Pandaren).
        """
        horde_races = {
            Races.RACE_ORC, Races.RACE_UNDEAD, Races.RACE_TAUREN,
            Races.RACE_TROLL, Races.RACE_BLOODELF, Races.RACE_GOBLIN,
            Races.RACE_PANDAREN_HORDE,
        }
        if race in horde_races:
            return 0x01
        if race == Races.RACE_PANDAREN_NEUTRAL:
            return 0x2A
        return 0x07

    @staticmethod
    def value_of(race: int) -> str:
        """
        Return the human-readable name for a race ID.

        Args:
            race: Race constant from Races.

        Returns:
            Race name string (e.g. "Human", "Orc"), or "Unknown".
        """
        mapping = {
            Races.RACE_HUMAN: "Human",
            Races.RACE_ORC: "Orc",
            Races.RACE_DWARF: "Dwarf",
            Races.RACE_NIGHTELF: "Night Elf",
            Races.RACE_UNDEAD: "Undead",
            Races.RACE_TAUREN: "Tauren",
            Races.RACE_GNOME: "Gnome",
            Races.RACE_TROLL: "Troll",
            Races.RACE_GOBLIN: "Goblin",
            Races.RACE_BLOODELF: "Blood Elf",
            Races.RACE_DRAENEI: "Draenei",
            Races.RACE_WORGEN: "Worgen",
            Races.RACE_PANDAREN_NEUTRAL: "Pandaren",
            Races.RACE_PANDAREN_ALLIANCE: "Alliance Pandaren",
            Races.RACE_PANDAREN_HORDE: "Horde Pandaren",
        }
        return mapping.get(race, "Unknown")


class Classes:
    """Playable class constants."""
    CLASS_WARRIOR: int = 0x01
    CLASS_PALADIN: int = 0x02
    CLASS_HUNTER: int = 0x03
    CLASS_ROGUE: int = 0x04
    CLASS_PRIEST: int = 0x05
    CLASS_DEATH_KNIGHT: int = 0x06
    CLASS_SHAMAN: int = 0x07
    CLASS_MAGE: int = 0x08
    CLASS_WARLOCK: int = 0x09
    CLASS_MONK: int = 0x0A
    CLASS_DRUID: int = 0x0B

    @staticmethod
    def value_of(char_class: int) -> str:
        """
        Return the human-readable name for a class ID.

        Args:
            char_class: Class constant from Classes.

        Returns:
            Class name string (e.g. "Warrior", "Mage"), or "Unknown".
        """
        mapping = {
            Classes.CLASS_WARRIOR: "Warrior",
            Classes.CLASS_PALADIN: "Paladin",
            Classes.CLASS_HUNTER: "Hunter",
            Classes.CLASS_ROGUE: "Rogue",
            Classes.CLASS_PRIEST: "Priest",
            Classes.CLASS_DEATH_KNIGHT: "Death Knight",
            Classes.CLASS_SHAMAN: "Shaman",
            Classes.CLASS_MAGE: "Mage",
            Classes.CLASS_WARLOCK: "Warlock",
            Classes.CLASS_MONK: "Monk",
            Classes.CLASS_DRUID: "Druid",
        }
        return mapping.get(char_class, "Unknown")


class Genders:
    """Gender constants."""
    GENDER_MALE: int = 0
    GENDER_FEMALE: int = 1
    GENDER_NONE: int = 2

    @staticmethod
    def value_of(gender: int) -> str:
        """
        Return the human-readable name for a gender ID.

        Args:
            gender: Gender constant from Genders.

        Returns:
            "Male", "Female", or "Unknown".
        """
        mapping = {
            Genders.GENDER_MALE: "Male",
            Genders.GENDER_FEMALE: "Female",
        }
        return mapping.get(gender, "Unknown")


class AuthResponseCodes:
    """Authentication result code constants."""
    AUTH_OK: int = 0x0C
    AUTH_FAILED: int = 0x0D
    AUTH_REJECT: int = 0x0E
    AUTH_BAD_SERVER_PROOF: int = 0x0F
    AUTH_UNAVAILABLE: int = 0x10
    AUTH_SYSTEM_ERROR: int = 0x11
    AUTH_BILLING_ERROR: int = 0x12
    AUTH_BILLING_EXPIRED: int = 0x13
    AUTH_VERSION_MISMATCH: int = 0x14
    AUTH_UNKNOWN_ACCOUNT: int = 0x15
    AUTH_INCORRECT_PASSWORD: int = 0x16
    AUTH_SESSION_EXPIRED: int = 0x17
    AUTH_SERVER_SHUTTING_DOWN: int = 0x18
    AUTH_ALREADY_LOGGING_IN: int = 0x19
    AUTH_LOGIN_SERVER_NOT_FOUND: int = 0x1A
    AUTH_WAIT_QUEUE: int = 0x1B
    AUTH_BANNED: int = 0x1C
    AUTH_ALREADY_ONLINE: int = 0x1D
    AUTH_NO_TIME: int = 0x1E
    AUTH_DB_BUSY: int = 0x1F
    AUTH_SUSPENDED: int = 0x20
    AUTH_PARENTAL_CONTROL: int = 0x21
    AUTH_LOCKED_ENFORCED: int = 0x22
    REALM_LIST_IN_PROGRESS: int = 0x23
    REALM_LIST_SUCCESS: int = 0x24
    REALM_LIST_FAILED: int = 0x25
    REALM_LIST_INVALID: int = 0x26
    REALM_LIST_REALM_NOT_FOUND: int = 0x27

    @staticmethod
    def value_of(auth_result: int) -> str:
        """
        Return the constant name for an auth result code.

        Args:
            auth_result: Numeric auth result from the server.

        Returns:
            Constant name (e.g. "AUTH_OK"), or hex string if unknown.
        """
        for name in dir(AuthResponseCodes):
            if (
                isinstance(getattr(AuthResponseCodes, name), int)
                and getattr(AuthResponseCodes, name) == auth_result
            ):
                return name
        return f"0x{auth_result:02X}"

    @staticmethod
    def get_message(auth_result: int) -> str:
        """
        Return a user-friendly message for an auth result code.

        Args:
            auth_result: Numeric auth result from the server.

        Returns:
            Human-readable message describing the result.
        """
        mapping = {
            AuthResponseCodes.AUTH_OK: "Success!",
            AuthResponseCodes.AUTH_UNKNOWN_ACCOUNT: "Invalid username!",
            AuthResponseCodes.AUTH_INCORRECT_PASSWORD:
                "Incorrect password for this username!",
            AuthResponseCodes.AUTH_VERSION_MISMATCH:
                "Invalid game version! Is your game_build in config correct?",
            AuthResponseCodes.AUTH_BANNED: "Your account has been banned!",
            AuthResponseCodes.AUTH_ALREADY_LOGGING_IN:
                "Your account is already online! Log it off or wait a minute.",
            AuthResponseCodes.AUTH_SUSPENDED: "Your account has been suspended!",
            AuthResponseCodes.AUTH_ALREADY_ONLINE:
                "Your account is already online! Log it off or wait a minute.",
        }
        return mapping.get(
            auth_result,
            f"Failed to login! Error code: {AuthResponseCodes.value_of(auth_result)}",
        )


class ChatNotify:
    """SMSG_CHANNEL_NOTIFY notification type constants."""
    CHAT_JOINED_NOTICE: int = 0x00
    CHAT_LEFT_NOTICE: int = 0x01
    CHAT_YOU_JOINED_NOTICE: int = 0x02
    CHAT_YOU_LEFT_NOTICE: int = 0x03
    CHAT_WRONG_PASSWORD_NOTICE: int = 0x04
    CHAT_NOT_MEMBER_NOTICE: int = 0x05
    CHAT_NOT_MODERATOR_NOTICE: int = 0x06
    CHAT_PASSWORD_CHANGED_NOTICE: int = 0x07
    CHAT_OWNER_CHANGED_NOTICE: int = 0x08
    CHAT_PLAYER_NOT_FOUND_NOTICE: int = 0x09
    CHAT_NOT_OWNER_NOTICE: int = 0x0A
    CHAT_CHANNEL_OWNER_NOTICE: int = 0x0B
    CHAT_MODE_CHANGE_NOTICE: int = 0x0C
    CHAT_ANNOUNCEMENTS_ON_NOTICE: int = 0x0D
    CHAT_ANNOUNCEMENTS_OFF_NOTICE: int = 0x0E
    CHAT_MODERATION_ON_NOTICE: int = 0x0F
    CHAT_MODERATION_OFF_NOTICE: int = 0x10
    CHAT_MUTED_NOTICE: int = 0x11
    CHAT_PLAYER_KICKED_NOTICE: int = 0x12
    CHAT_BANNED_NOTICE: int = 0x13
    CHAT_PLAYER_BANNED_NOTICE: int = 0x14
    CHAT_PLAYER_UNBANNED_NOTICE: int = 0x15
    CHAT_PLAYER_NOT_BANNED_NOTICE: int = 0x16
    CHAT_PLAYER_ALREADY_MEMBER_NOTICE: int = 0x17
    CHAT_INVITE_NOTICE: int = 0x18
    CHAT_INVITE_WRONG_FACTION_NOTICE: int = 0x19
    CHAT_WRONG_FACTION_NOTICE: int = 0x1A
    CHAT_INVALID_NAME_NOTICE: int = 0x1B
    CHAT_NOT_MODERATED_NOTICE: int = 0x1C
    CHAT_PLAYER_INVITED_NOTICE: int = 0x1D
    CHAT_PLAYER_INVITE_BANNED_NOTICE: int = 0x1E
    CHAT_THROTTLED_NOTICE: int = 0x1F
    CHAT_NOT_IN_AREA_NOTICE: int = 0x20
    CHAT_NOT_IN_LFG_NOTICE: int = 0x21
    CHAT_VOICE_ON_NOTICE: int = 0x22
    CHAT_VOICE_OFF_NOTICE: int = 0x23


class ServerMessageType:
    """SMSG_SERVER_MESSAGE sub-type constants."""
    SERVER_MSG_SHUTDOWN_TIME: int = 0x01
    SERVER_MSG_RESTART_TIME: int = 0x02
    SERVER_MSG_CUSTOM: int = 0x03
    SERVER_MSG_SHUTDOWN_CANCELLED: int = 0x04
    SERVER_MSG_RESTART_CANCELLED: int = 0x05


class ChatChannelIds:
    """Built-in channel ID constants."""
    GENERAL: int = 0x01
    TRADE: int = 0x02
    LOCAL_DEFENSE: int = 0x16
    WORLD_DEFENSE: int = 0x17
    GUILD_RECRUITMENT: int = 0x00
    LOOKING_FOR_GROUP: int = 0x1A

    @staticmethod
    def get_id(channel: str) -> int:
        """
        Return the numeric ID for a built-in channel name.

        Args:
            channel: Channel name (e.g. "general", "trade").

        Returns:
            Channel ID constant, or 0x00 for custom channels.
        """
        name = channel.split(" ", 1)[0].lower()
        mapping = {
            "general": ChatChannelIds.GENERAL,
            "trade": ChatChannelIds.TRADE,
            "localdefense": ChatChannelIds.LOCAL_DEFENSE,
            "worlddefense": ChatChannelIds.WORLD_DEFENSE,
            "guildrecruitment": ChatChannelIds.GUILD_RECRUITMENT,
            "lookingforgroup": ChatChannelIds.LOOKING_FOR_GROUP,
        }
        return mapping.get(name, 0x00)


class GuildEvents:
    """Guild event type constants, with different values pre- and post-Cataclysm."""

    def __init__(self, is_cata: bool = False) -> None:
        if is_cata:
            self.GE_PROMOTED = 0x01
            self.GE_DEMOTED = 0x02
            self.GE_MOTD = 0x03
            self.GE_JOINED = 0x04
            self.GE_LEFT = 0x05
            self.GE_REMOVED = 0x06
            self.GE_SIGNED_ON = 0x10
            self.GE_SIGNED_OFF = 0x11
        else:
            self.GE_PROMOTED = 0x00
            self.GE_DEMOTED = 0x01
            self.GE_MOTD = 0x02
            self.GE_JOINED = 0x03
            self.GE_LEFT = 0x04
            self.GE_REMOVED = 0x05
            self.GE_SIGNED_ON = 0x0C
            self.GE_SIGNED_OFF = 0x0D
