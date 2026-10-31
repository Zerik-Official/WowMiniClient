"""
SRP-6a client implementation for WoW realm authentication.
Port of JaNGOSAuth SRP client logic, matching the Scala reference.
"""

from __future__ import annotations

import hashlib
import os

from utils.logger import Tags, log


def _le_bytes(value: int, length: int) -> bytes:
    return value.to_bytes(length, "little")


def _be_bytes(value: int, length: int) -> bytes:
    return value.to_bytes(length, "big")


def _from_le(data: bytes) -> int:
    return int.from_bytes(data, "little")


def _from_be(data: bytes) -> int:
    return int.from_bytes(data, "big")


class SRPClient:
    """
    SRP-6a client matching the Scala/JaNGOS reference implementation.

    BigNumber.asByteArray() with default reverse=true produces LE bytes.
    BigNumber(array, reverse=true) interprets the array as little-endian.

    Args:
        account: Uppercase UTF-8 encoded account name bytes.
        password: Raw account password string.
    """

    def __init__(self, account: bytes, password: str) -> None:
        self._account = account
        self._password = password

        self.k = 3
        self.a = int.from_bytes(os.urandom(19), "big", signed=False)

        self.a_pub: int = 0
        self.x: int = 0
        self.proof: int = 0
        self.session_key: bytes = b""

    def step1(self, b: int, g: int, n: int, s: int) -> None:
        """
        Step 1 of SRP-6a: compute A, x, S, K, and M.

        All big integers converted to LE byte arrays for hashing,
        matching Scala's BigNumber.asByteArray() with default reverse=true.

        Args:
            b: Server public ephemeral value (B).
            g: Generator.
            n: Large safe prime (modulus).
            s: Salt.
        """
        password_upper = self._password.upper()

        self.a_pub = pow(g, self.a, n)

        log("DEBUG", Tags.CRYPTO,
            f"SRP g={g}, n={n}, a={self.a}, A={self.a_pub}")

        md = hashlib.sha1()
        md.update(_le_bytes(self.a_pub, 32))
        md.update(_le_bytes(b, 32))
        u = _from_le(md.digest())
        log("DEBUG", Tags.CRYPTO, f"SRP u={u}")

        md = hashlib.sha1()
        md.update(self._account)
        md.update(b":")
        md.update(password_upper.encode("utf-8"))
        p = md.digest()

        md = hashlib.sha1()
        md.update(_le_bytes(s, 32))
        md.update(p)
        self.x = _from_le(md.digest())
        log("DEBUG", Tags.CRYPTO, f"SRP x={self.x}")

        g_x = pow(g, self.x, n)
        k_g_x = (self.k * g_x) % n
        b_offset = (b - k_g_x) % n
        s_val = pow(b_offset, self.a + u * self.x, n)

        t = _le_bytes(s_val, 32)
        t1 = bytes(t[i] for i in range(0, 32, 2))
        t2 = bytes(t[i] for i in range(1, 32, 2))

        d1 = hashlib.sha1(t1).digest()
        d2 = hashlib.sha1(t2).digest()

        vk = bytearray(40)
        for i in range(20):
            vk[i * 2] = d1[i]
            vk[i * 2 + 1] = d2[i]
        self.session_key = bytes(vk)
        log("DEBUG", Tags.CRYPTO,
            f"SRP S={s_val}, K len={len(self.session_key)}")

        md = hashlib.sha1()
        md.update(_le_bytes(n, 32))
        n_hash = md.digest()

        md = hashlib.sha1()
        md.update(_le_bytes(g, 1))
        g_hash = md.digest()

        n_xor_g = bytes(n_hash[i] ^ g_hash[i] for i in range(20))

        md = hashlib.sha1()
        md.update(self._account)
        account_hash = md.digest()

        md = hashlib.sha1()
        md.update(n_xor_g)
        md.update(account_hash)
        md.update(_le_bytes(s, 32))
        md.update(_le_bytes(self.a_pub, 32))
        md.update(_le_bytes(b, 32))
        md.update(self.session_key)
        self.proof = _from_be(md.digest())
        log("DEBUG", Tags.CRYPTO, f"SRP M={self.proof}")

    def generate_hash_logon_proof(self) -> bytes:
        """
        Generate server proof hash: SHA1(A_LE || M_BE || K_LE).

        Scala: md.update(A.asByteArray(32)); md.update(M.asByteArray(20, false));
               md.update(K.asByteArray(40))

        Returns:
            20-byte SHA1 digest.
        """
        md = hashlib.sha1()
        md.update(_le_bytes(self.a_pub, 32))
        md.update(_be_bytes(self.proof, 20))
        md.update(self.session_key)
        return md.digest()
