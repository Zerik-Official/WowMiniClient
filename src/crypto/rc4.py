"""
RC4 stream cipher implementation used for WotLK+ header encryption and Warden.
"""


class RC4:
    """
    Pure-Python RC4 stream cipher.

    Used by GameHeaderCryptWotLK (and MoP) for packet header encryption
    and by WardenHandler for anti-cheat payload encryption.

    Args:
        key: The cipher key bytes.
    """

    def __init__(self, key: bytes) -> None:
        self._sbox = self._init_sbox(key)
        self._i = 0
        self._j = 0

    @staticmethod
    def _init_sbox(key: bytes) -> list[int]:
        """
        Key-scheduling algorithm (KSA).

        Args:
            key: Cipher key bytes.

        Returns:
            Initialised 256-byte S-box.
        """
        sbox = list(range(256))
        j = 0
        for i in range(256):
            j = (j + sbox[i] + key[i % len(key)]) % 256
            sbox[i], sbox[j] = sbox[j], sbox[i]
        return sbox

    def crypt(self, data: bytes) -> bytes:
        """
        Encrypt or decrypt data using the RC4 stream.

        Args:
            data: Input bytes to XOR with the keystream.

        Returns:
            Transformed bytes (encryption and decryption are identical).
        """
        out = bytearray(len(data))
        for n, byte in enumerate(data):
            self._i = (self._i + 1) % 256
            self._j = (self._j + self._sbox[self._i]) % 256
            sbox = self._sbox
            sbox[self._i], sbox[self._j] = sbox[self._j], sbox[self._i]
            rand = sbox[(sbox[self._i] + sbox[self._j]) % 256]
            out[n] = rand ^ byte
        return bytes(out)
