"""
Game packet header encryption for Vanilla through MoP.
Each expansion uses a different cipher scheme.
"""

from __future__ import annotations

import hmac

from crypto.rc4 import RC4


class GameHeaderCrypt:
    """
    Vanilla WoW packet header encryption.
    Simple XOR cipher with key-dependent feedback.

    Decrypt: data[i] = (encrypted[i] - recv_j) XOR key[recv_i]
    Encrypt: data[i] = (plain[i] XOR key[send_i]) + send_j
    """

    def __init__(self) -> None:
        self._initialized = False
        self._send_i = 0
        self._send_j = 0
        self._recv_i = 0
        self._recv_j = 0
        self._key: bytes = b""

    @property
    def is_initialized(self) -> bool:
        """Whether the cipher has been initialised with a key."""
        return self._initialized

    @property
    def is_init(self) -> bool:
        """Alias de is_initialized para compatibilidad con el decoder."""
        return self._initialized

    def decrypt(self, data: bytearray) -> bytearray:
        """
        Decrypt a packet header in-place.

        Args:
            data: Encrypted header bytes (modified in-place).

        Returns:
            The same bytearray, now decrypted.
        """
        if not self._initialized:
            return data

        for i in range(len(data)):
            self._recv_i %= len(self._key)
            x = ((data[i] - self._recv_j) ^ self._key[self._recv_i]) & 0xFF
            self._recv_i += 1
            self._recv_j = data[i]
            data[i] = x

        return data

    def encrypt(self, data: bytearray) -> bytearray:
        """
        Encrypt a packet header in-place.

        Args:
            data: Plain header bytes (modified in-place).

        Returns:
            The same bytearray, now encrypted.
        """
        if not self._initialized:
            return data

        for i in range(len(data)):
            self._send_i %= len(self._key)
            x = ((data[i] ^ self._key[self._send_i]) + self._send_j) & 0xFF
            self._send_i += 1
            data[i] = x
            self._send_j = x

        return data

    def init(self, key: bytes) -> None:
        """
        Initialise the cipher with a session key.

        Args:
            key: Cipher key bytes.
        """
        self._key = key
        self._send_i = 0
        self._send_j = 0
        self._recv_i = 0
        self._recv_j = 0
        self._initialized = True


class GameHeaderCryptTBC(GameHeaderCrypt):
    """
    TBC packet header encryption.
    HMAC-SHA1 transforms the session key before use in the XOR cipher.
    """

    _HMAC_SEED: bytes = bytes([
        0x38, 0xA7, 0x83, 0x15, 0xF8, 0x92, 0x25, 0x30,
        0x71, 0x98, 0x67, 0xB1, 0x8C, 0x04, 0xE2, 0xAA,
    ])

    def init(self, key: bytes) -> None:
        """
        Derive the actual key via HMAC-SHA1 and initialise the XOR cipher.

        Args:
            key: Session key from realm auth.
        """
        derived = hmac.new(self._HMAC_SEED, key, "sha1").digest()
        super().init(derived)


class GameHeaderCryptWotLK(GameHeaderCrypt):
    """
    WotLK (and Cataclysm) packet header encryption.
    HMAC-SHA1 derives separate RC4 keys for client and server,
    each primed with 1024 bytes of keystream discard.
    """

    _SERVER_HMAC_SEED: bytes = bytes([
        0xCC, 0x98, 0xAE, 0x04, 0xE8, 0x97, 0xEA, 0xCA,
        0x12, 0xDD, 0xC0, 0x93, 0x42, 0x91, 0x53, 0x57,
    ])
    _CLIENT_HMAC_SEED: bytes = bytes([
        0xC2, 0xB3, 0x72, 0x3C, 0xC6, 0xAE, 0xD9, 0xB5,
        0x34, 0x3C, 0x53, 0xEE, 0x2F, 0x43, 0x67, 0xCE,
    ])
    _DISCARD_BYTES = 1024

    def __init__(self) -> None:
        super().__init__()
        self._server_crypt: RC4 | None = None
        self._client_crypt: RC4 | None = None

    def decrypt(self, data: bytearray) -> bytearray:
        """Decrypt using the server RC4 stream."""
        if not self._initialized or self._server_crypt is None:
            return data
        return bytearray(self._server_crypt.crypt(bytes(data)))

    def encrypt(self, data: bytearray) -> bytearray:
        """Encrypt using the client RC4 stream."""
        if not self._initialized or self._client_crypt is None:
            return data
        return bytearray(self._client_crypt.crypt(bytes(data)))

    def init(self, key: bytes) -> None:
        """
        Derive RC4 keys via HMAC-SHA1 and discard 1024 bytes from each.

        Args:
            key: Session key from realm auth.
        """
        server_key = hmac.new(self._SERVER_HMAC_SEED, key, "sha1").digest()
        client_key = hmac.new(self._CLIENT_HMAC_SEED, key, "sha1").digest()

        self._server_crypt = RC4(server_key)
        self._server_crypt.crypt(b"\x00" * self._DISCARD_BYTES)

        self._client_crypt = RC4(client_key)
        self._client_crypt.crypt(b"\x00" * self._DISCARD_BYTES)

        self._initialized = True


class GameHeaderCryptMoP(GameHeaderCryptWotLK):
    """
    MoP packet header encryption.
    Same scheme as WotLK but with different HMAC seeds.
    """

    _SERVER_HMAC_SEED: bytes = bytes([
        0x08, 0xF1, 0x95, 0x9F, 0x47, 0xE5, 0xD2, 0xDB,
        0xA1, 0x3D, 0x77, 0x8F, 0x3F, 0x3E, 0xE7, 0x00,
    ])
    _CLIENT_HMAC_SEED: bytes = bytes([
        0x40, 0xAA, 0xD3, 0x92, 0x26, 0x71, 0x43, 0x47,
        0x3A, 0x31, 0x08, 0xA6, 0xE7, 0xDC, 0x98, 0x2A,
    ])
