"""Warden anti-cheat reply handlers for Vanilla through Cataclysm (and MoP variant)."""

from __future__ import annotations

import hashlib
import struct
import zlib

from crypto.rc4 import RC4
from crypto.sha1randx import SHA1Randx
from utils.logger import Tags, log
from warden.packets import WardenPackets


class WardenHandler:
    """
    Base Warden reply handler for Vanilla through Cataclysm.

    Manages the cryptographic handshake, module loading, cheat check responses,
    and hash rekeying required by the Warden anti-cheat system.
    """

    WARDEN_MODULE_LENGTH: int = 16

    def __init__(self, session_key: bytes) -> None:
        """
        Initialize the handler with a session key.

        Derives client and server RC4 ciphers from the session key via
        SHA1Randx.

        Args:
            session_key: 16-byte session key established during authentication.
        """
        sha1rand = SHA1Randx(session_key)
        self._client_crypt: RC4 = RC4(sha1rand.generate(16))
        self._server_crypt: RC4 = RC4(sha1rand.generate(16))
        self._module_crypt: RC4 | None = None
        self._module_name: str = ""
        self._module_seed: bytearray = bytearray(16)
        self._module_length: int = 0
        self._module_data: bytearray = bytearray()

    def handle(self, data: bytes) -> tuple[int, bytes | None]:
        """
        Process an incoming Warden packet and generate a response.

        Decrypts the packet, dispatches to the appropriate handler based on
        opcode, and returns the response.

        Args:
            data: Raw Warden packet bytes (not yet decrypted).

        Returns:
            Tuple of (warden_opcode, response_bytes_or_None).
        """
        decrypted = self._server_crypt.crypt(data)
        log("DEBUG", Tags.WARDEN, f"WARDEN PACKET ({len(decrypted)}): {decrypted.hex()}")

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
        """
        Encrypt the response with the client crypt.

        Args:
            response: Plaintext response bytes.

        Returns:
            Encrypted, finalized bytes ready for transmission.
        """
        return self._form_response(self._client_crypt.crypt(response))

    def _form_response(self, out: bytes) -> bytes:
        """
        No-op wrapper; overridden in MoP to add length prefix.

        Args:
            out: Encrypted response bytes.

        Returns:
            Response bytes as-is.
        """
        return out

    def _get_encrypted_length(self, data: bytes) -> int:
        """
        Return the usable encrypted length. Overridden in MoP.

        Args:
            data: Raw packet bytes.

        Returns:
            Length of the encrypted payload.
        """
        return len(data)

    def _handle_module_use(self, data: bytes) -> bytes | None:
        """
        Handle WARDEN_SMSG_MODULE_USE.

        Extracts the module name, seed, and length; creates the module cipher;
        and responds with WARDEN_CMSG_MODULE_OK.

        Args:
            data: Payload containing module name (16 bytes), seed (16 bytes),
                  and length (4 bytes, little-endian).

        Returns:
            Encrypted module-OK response.
        """
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
        """
        Handle WARDEN_SMSG_MODULE_CACHE.

        Accumulates compressed module chunks. Once the full module has been
        received, decompresses it and responds with WARDEN_CMSG_MODULE_OK.

        Args:
            data: Payload containing a 2-byte length prefix followed by
                  compressed module data.

        Returns:
            Encrypted module-OK response once the module is complete,
            or None if more chunks are expected.
        """
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
        """
        Handle WARDEN_SMSG_CHEAT_CHECKS_REQUEST.

        Builds a digest response (SHA-1 + MD5 over the provided key string)
        and returns it encrypted.

        Args:
            data: Payload containing a 1-byte string length followed by a
                  null-terminated key string.

        Returns:
            Encrypted cheat-check result bytes.
        """
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
        """
        Append SHA-1 and MD5 digests of the key to the output.

        Args:
            out: Mutable bytearray to write digests into.
            key: Key bytes to hash.
        """
        md_sha1 = hashlib.sha1()
        md_sha1.update(key)
        md_sha1.update(struct.pack("<I", 0xFEEDFACE))
        out.extend(md_sha1.digest())

        md_md5 = hashlib.md5()
        md_md5.update(key)
        out.extend(md_md5.digest())

    def _handle_hash_request(self, data: bytes) -> bytes | None:
        """
        Handle WARDEN_SMSG_HASH_REQUEST.

        Performs a key exchange: transforms client and server keys using
        predefined constants, sends the client hash response, then rekeys
        both ciphers with the new keys.

        Args:
            data: Payload containing 4 little-endian 32-bit integers (client key).

        Returns:
            Encrypted hash-result bytes.
        """
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

    WARDEN_MODULE_LENGTH: int = 32

    def _get_encrypted_length(self, data: bytes) -> int:
        """
        Return the usable encrypted length from the first 4 bytes.

        MoP prefixes the packet with a 4-byte length field.

        Args:
            data: Raw packet bytes.

        Returns:
            Encrypted payload length.
        """
        return struct.unpack("<I", data[:4])[0]  # type: ignore[no-any-return]

    def _form_response(self, out: bytes) -> bytes:
        """
        Prepend a 4-byte little-endian length prefix to the response.

        Args:
            out: Encrypted response bytes.

        Returns:
            Length-prefixed response bytes.
        """
        length_prefix = struct.pack("<I", len(out))
        return length_prefix + out

    def _form_cheat_checks_digest(self, out: bytearray, key: bytes) -> None:
        """
        Append SHA-1 and SHA-256 digests of the key to the output.

        MoP replaces the second MD5 hash with SHA-256.

        Args:
            out: Mutable bytearray to write digests into.
            key: Key bytes to hash.
        """
        md_sha1 = hashlib.sha1()
        md_sha1.update(key)
        out.extend(md_sha1.digest())

        md_sha256 = hashlib.sha256()
        md_sha256.update(key)
        out.extend(md_sha256.digest())
