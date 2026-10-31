"""Warden anti-cheat protocol opcodes."""


class WardenPackets:
    """Warden packet IDs for client-server communication."""

    WARDEN_CMSG_MODULE_MISSING: int = 0x00
    WARDEN_CMSG_MODULE_OK: int = 0x01
    WARDEN_CMSG_CHEAT_CHECKS_RESULT: int = 0x02
    WARDEN_CMSG_MEM_CHECKS_RESULT: int = 0x03
    WARDEN_CMSG_HASH_RESULT: int = 0x04
    WARDEN_CMSG_MODULE_FAILED: int = 0x05

    WARDEN_SMSG_MODULE_USE: int = 0x00
    WARDEN_SMSG_MODULE_CACHE: int = 0x01
    WARDEN_SMSG_CHEAT_CHECKS_REQUEST: int = 0x02
    WARDEN_SMSG_MODULE_INITIALIZE: int = 0x03
    WARDEN_SMSG_MEM_CHECKS_REQUEST: int = 0x04
    WARDEN_SMSG_HASH_REQUEST: int = 0x05
