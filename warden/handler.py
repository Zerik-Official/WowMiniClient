"""
Warden anti-cheat reply handlers for Vanilla through Cataclysm (and MoP variant).
"""

from __future__ import annotations

import hashlib
import logging
import struct
import zlib

from crypto.rc4 import RC4
from crypto.sha1randx import SHA1Randx
from warden.packets import WardenPackets

logger = logging.getLogger(__name__)


class WardenHandler:
    """Base Warden reply handler for Vanilla through Cataclysm."""

    WARDEN_MODULE_LENGTH = 16

    def __init__(self, session_key: bytes) -> None:
        sha1rand = SHA1Randx(session_key)
        self._client_crypt = RC4(sha1rand.generate(16))
        self._server_crypt = RC4(sha1rand.generate(16))
        self._module_crypt: RC4 | None = None
        self._module_name = ""
        self._module_seed = bytearray(16)
        self._module_length = 0
        self._module_data = bytearray()

    def handle(self, data: bytes) -> tuple[int, bytes | None]:
        """
        Process an incoming Warden packet and generate a response.

        Args:
            data: Raw warden packet bytes (not yet decrypted).

        Returns:
            Tuple of (warden_opcode_id, response_bytes_or_None).
        """
        decrypted = self._server_crypt.crypt(data)
        logger.debug("WARDEN PACKET (%d): %s", len(decrypted), decrypted.hex())

        opcode = decrypted[0]
        payload = decrypted[1:]

        handler = {
            WardenPackets.WARDEN_SMSG_MODULE_USE: self._handle_module_use,
            WardenPackets.WARDEN_SMSG_MODULE_CACHE: self._handle_module_cache,
            WardenPackets.WARDEN_SMSG_CHEAT_CHECKS_REQUEST: self._handle_cheat_checks,
            WardenPackets.WARDEN_SMSG_HASH_REQUEST: self._handle_hash_request,
        }.get(opcode)

        if handler is None:
            return opcode, None

        response = handler(payload)
        return opcode, response

    def _encrypt_and_finalize(self, response: bytes) -> bytes:
        """Encrypt the response with the client crypt."""
        return self._form_response(self._client_crypt.crypt(response))

    def _form_response(self, out: bytes) -> bytes:
        """No-op wrapper; overridden in MoP to add length prefix."""
        return out

    def _get_encrypted_length(self, data: bytes) -> int:
        """Return the usable encrypted length. Overridden in MoP."""
        return len(data)

    def _handle_module_use(self, data: bytes) -> bytes | None:
        self._module_name = data[: self.WARDEN_MODULE_LENGTH].hex().upper()
        seed_start = self.WARDEN_MODULE_LENGTH
        seed_end = seed_start + 16
        self._module_seed = bytearray(data[seed_start:seed_end])
        len_start = seed_end
        len_end = len_start + 4
        self._module_length = struct.unpack("<I", data[len_start:len_end])[0]
        self._module_crypt = RC4(bytes(self._module_seed))
        return self._encrypt_and_finalize(bytes([WardenPackets.WARDEN_CMSG_MODULE_OK]))

    def _handle_module_cache(self, data: bytes) -> bytes | None:
        length = struct.unpack("<H", data[:2])[0]
        compressed = data[2:2 + length]
        self._module_data.extend(compressed)

        if len(self._module_data) >= self._module_length:
            module_arr = bytes(self._module_data[:self._module_length])
            if self._module_crypt:
                unencrypted = self._module_crypt.crypt(module_arr)
            else:
                unencrypted = module_arr
            raw = unencrypted[4:]
            inflater = zlib.decompressobj()
            inflater.decompress(raw)

            self._module_data.clear()
            ok_byte = bytes([WardenPackets.WARDEN_CMSG_MODULE_OK])
            return self._encrypt_and_finalize(ok_byte)
        return None

    def _handle_cheat_checks(self, data: bytes) -> bytes | None:
        str_length = data[0]
        str_data = data[1:1 + str_length]
        null_pos = str_data.find(b"\x00")
        if null_pos >= 0:
            str_data = str_data[:null_pos]

        result = bytearray()
        result.append(WardenPackets.WARDEN_CMSG_CHEAT_CHECKS_RESULT)
        self._form_cheat_checks_digest(result, str_data)
        encrypted = self._client_crypt.crypt(bytes(result))
        return self._form_response(encrypted)

    def _form_cheat_checks_digest(self, out: bytearray, key: bytes) -> None:
        md_sha1 = hashlib.sha1()
        md_sha1.update(key)
        md_sha1.update(struct.pack("<I", 0xFEEDFACE))
        out.extend(md_sha1.digest())

        md_md5 = hashlib.md5()
        md_md5.update(key)
        out.extend(md_md5.digest())

    def _handle_hash_request(self, data: bytes) -> bytes | None:
        client_key = list(struct.unpack("<4I", data[:16]))

        server_key = [0] * 4
        server_key[0] = client_key[0]
        client_key[0] ^= 0xDEADBEEF
        server_key1 = client_key[1]
        client_key[1] -= 0x35014542
        server_key2 = client_key[2]
        client_key[2] += 0x5313F22
        client_key[3] *= 0x1337F00D
        server_key[1] = server_key1 - 0x6A028A84
        server_key[2] = server_key2 + 0xA627E44
        server_key[3] = 0x1337F00D * client_key[3]

        client_key_bytes = struct.pack("<4I", *client_key)
        md = hashlib.sha1()
        md.update(client_key_bytes)

        result = bytearray()
        result.append(WardenPackets.WARDEN_CMSG_HASH_RESULT)
        result.extend(md.digest())

        encrypted = self._client_crypt.crypt(bytes(result))

        self._client_crypt = RC4(client_key_bytes)

        server_key_bytes = struct.pack("<4I", *server_key)
        self._server_crypt = RC4(server_key_bytes)

        return self._form_response(encrypted)


class WardenHandlerMoP18414(WardenHandler):
    """MoP Warden handler with 32-byte module names and SHA-256."""

    WARDEN_MODULE_LENGTH = 32

    def _get_encrypted_length(self, data: bytes) -> int:
        return struct.unpack("<I", data[:4])[0]  # type: ignore[no-any-return]

    def _form_response(self, out: bytes) -> bytes:
        length_prefix = struct.pack("<I", len(out))
        return length_prefix + out

    def _form_cheat_checks_digest(self, out: bytearray, key: bytes) -> None:
        md_sha1 = hashlib.sha1()
        md_sha1.update(key)
        out.extend(md_sha1.digest())

        md_sha256 = hashlib.sha256()
        md_sha256.update(key)
        out.extend(md_sha256.digest())
