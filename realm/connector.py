"""
Asyncio-based realm authentication connector.

Manages the full WoW realm login flow:
  1. CMD_AUTH_LOGON_CHALLENGE  -> server responds with B, g, N, salt
  2. SRP-6a proof computation
  3. CMD_AUTH_LOGON_PROOF      -> server validates proof
  4. CMD_REALM_LIST            -> server returns realm list
"""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections.abc import Callable

from common.bytes import string_to_int, to_hex_string
from common.types import Platform, WowExpansion
from crypto.srp import SRPClient
from realm.packets import (
    BUILD_CRC_HASHES,
    CMD_AUTH_LOGON_CHALLENGE,
    CMD_AUTH_LOGON_PROOF,
    CMD_REALM_LIST,
    AuthResult,
    RealmListEntry,
)
from utils.logger import Tags, log

RealmAuthCallback = Callable[
    [str, int, str, int, bytes], None
]


def _to_array(data: bytes, reverse: bool = True) -> bytes:
    """Read bytes, optionally reversing them (matching Scala toArray)."""
    return data[::-1] if reverse else data


def _build_crc_hash(realm_build: int, platform: Platform) -> bytes:
    """Look up the CRC hash for the given build and platform."""
    return BUILD_CRC_HASHES.get(
        (realm_build, platform), b"\x00" * 20
    )


def _read_cstring(data: bytes, offset: int) -> tuple[str, int]:
    """
    Read a null-terminated string from a byte buffer.

    Args:
        data: Raw byte buffer.
        offset: Starting position.

    Returns:
        Tuple of (decoded string, new offset after the null terminator).
    """
    end = data.find(b"\x00", offset)
    text = data[offset:end].decode("utf-8", errors="replace")
    return text, end + 1


def _parse_realm_list(data: bytes, is_vanilla: bool) -> list[RealmListEntry]:
    """
    Parse realm list entries from the server response.

    Args:
        data: Raw realm list payload.
        is_vanilla: Whether parsing for Vanilla (different format).

    Returns:
        List of realm entries.
    """
    realms: list[RealmListEntry] = []
    offset = 0

    offset += 4

    if is_vanilla:
        num_realms = data[offset]
        offset += 1

        for _ in range(num_realms):
            offset += 4 
            realm_flags = data[offset]
            offset += 1

            name, offset = _read_cstring(data, offset)
            if realm_flags & 0x04:
                name = re.sub(r" \(\d+,\d+,\d+\)", "", name)

            address, offset = _read_cstring(data, offset)
            offset += 4
            offset += 1
            offset += 1
            realm_id = data[offset]
            offset += 1

            realms.append(RealmListEntry(name, address, realm_id))
    else:
        num_realms = int.from_bytes(data[offset:offset + 2], "little")
        offset += 2

        for _ in range(num_realms):
            offset += 1
            offset += 1
            realm_flags = data[offset]
            offset += 1

            name, offset = _read_cstring(data, offset)
            address, offset = _read_cstring(data, offset)
            offset += 4
            offset += 1
            offset += 1
            realm_id = data[offset]
            offset += 1

            if realm_flags & 0x04:
                offset += 5

            realms.append(RealmListEntry(name, address, realm_id))

    return realms


class RealmConnector:
    """
    WoW realm authentication connector using asyncio.

    Args:
        host: Realm list server hostname.
        port: Realm list server port.
        account: Uppercase UTF-8 account name bytes.
        password: Account password.
        version: Game version string.
        realm_build: Realm build number.
        expansion: Target expansion.
        platform: Client platform.
        locale: Game locale.
        realm_name: Target realm name.
        on_success: Called on successful auth with (host, port, name, id, key).
        on_error: Called on auth failure.
        on_disconnect: Called on unexpected disconnect.
    """

    def __init__(
        self,
        host: str,
        port: int,
        account: bytes,
        password: str,
        version: str,
        realm_build: int,
        expansion: WowExpansion,
        platform: Platform,
        locale: str,
        realm_name: str,
        on_success: RealmAuthCallback,
        on_error: Callable[[], None],
        on_disconnect: Callable[[], None],
    ) -> None:
        self._host = host
        self._port = port
        self._account = account
        self._password = password
        self._version = version
        self._realm_build = realm_build
        self._expansion = expansion
        self._platform = platform
        self._locale = locale
        self._realm_name = realm_name
        self._on_success = on_success
        self._on_error = on_error
        self._on_disconnect = on_disconnect

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._session_key: bytes = b""

    @property
    def _r(self) -> asyncio.StreamReader:
        assert self._reader is not None
        return self._reader

    @property
    def _w(self) -> asyncio.StreamWriter:
        assert self._writer is not None
        return self._writer

    async def connect(self) -> None:
        """Open TCP connection and run the auth state machine."""
        try:
            log("INFO", Tags.REALM, f"Connecting to {self._host}:{self._port}")
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=10,
            )
            await self._send_challenge()
        except TimeoutError:
            log("ERROR", Tags.REALM, f"Connection timeout to {self._host}:{self._port}")
            self._on_error()
        except OSError as e:
            log("ERROR", Tags.REALM,
                f"Connection error to {self._host}:{self._port}: {e}")
            self._on_error()
        except Exception as e:
            log("ERROR", Tags.REALM, f"Unexpected error: {e}")
            self._on_error()

    async def _send_challenge(self) -> None:
        """Build and send the CMD_AUTH_LOGON_CHALLENGE packet."""
        log("DEBUG", Tags.REALM,
            f"Account bytes ({len(self._account)}): {self._account.hex(' ')}")
        version_parts = [int(x) for x in self._version.split(".")]
        platform_str = "Win" if self._platform == Platform.WINDOWS else "OSX"

        is_vanilla = self._expansion == WowExpansion.VANILLA
        protocol_byte = 3 if is_vanilla else 8
        account_len = len(self._account)

        payload = bytearray()
        payload.append(protocol_byte)
        payload += (30 + account_len).to_bytes(2, "little")
        payload += string_to_int("WoW").to_bytes(4, "little")
        payload.append(version_parts[0])
        payload.append(version_parts[1])
        payload.append(version_parts[2])
        payload += self._realm_build.to_bytes(2, "little")
        payload += string_to_int("x86").to_bytes(4, "little")
        payload += string_to_int(platform_str).to_bytes(4, "little")
        payload += string_to_int(self._locale).to_bytes(4, "little")
        payload += (0).to_bytes(4, "little")
        payload += bytes([127, 0, 0, 1])
        payload.append(account_len)
        payload += self._account

        self._w.write(bytes([CMD_AUTH_LOGON_CHALLENGE]) + payload)
        await self._w.drain()

        await self._read_challenge_response()

    async def _read_challenge_response(self) -> None:
        """Read and parse the CMD_AUTH_LOGON_CHALLENGE response."""
        buf = await self._r.readexactly(3)
        cmd, error, result = buf[0], buf[1], buf[2]

        log("DEBUG", Tags.REALM,
            f"Challenge header: cmd=0x{cmd:02X} error=0x{error:02X} result=0x{result:02X}")

        if not AuthResult.is_success(result):
            log("ERROR", Tags.REALM,
                f"Challenge failed: cmd=0x{cmd:02X} error=0x{error:02X} "
                f"result=0x{result:02X} ({AuthResult.get_message(result)})"
            )
            self._on_error()
            self._on_disconnect()
            return

        data = await self._r.readexactly(115)

        log("DEBUG", Tags.REALM,
            f"Challenge response (115 bytes): {data.hex(' ')}")

        b_bytes = _to_array(data[:32])
        g_len = data[32]
        g_bytes = _to_array(data[33:33 + g_len])
        n_len = data[33 + g_len]
        log("DEBUG", Tags.REALM,
            f"PARSE: g_len={g_len} n_len={n_len}")
        log("DEBUG", Tags.REALM,
            f"PARSE: n raw slice idx=[{34+g_len}:{34+g_len+n_len}] = data[{35}:{35+n_len}]")
        n_raw = data[34 + g_len:34 + g_len + n_len]
        log("DEBUG", Tags.REALM,
            f"PARSE: n raw len={len(n_raw)} hex={n_raw.hex(' ')}")
        n_bytes = _to_array(n_raw)
        log("DEBUG", Tags.REALM,
            f"PARSE: n rev len={len(n_bytes)} hex={n_bytes.hex(' ')}")
        offset = 34 + g_len + n_len
        salt_bytes = _to_array(data[offset:offset + 32])

        security_flag = (await self._r.readexactly(1))[0]

        token: str | None = None
        if security_flag == 0x04:
            await self._r.readexactly(1)
            token = await asyncio.get_event_loop().run_in_executor(
                None, input,
                "Token two-factor authentication is enabled. Input the token: ",
            )
        elif security_flag != 0x00:
            self._on_error()
            self._on_disconnect()
            return

        b_int = int.from_bytes(b_bytes, "big")
        g_int = int.from_bytes(g_bytes, "big")
        n_int = int.from_bytes(n_bytes, "big")
        s_int = int.from_bytes(salt_bytes, "big")

        log("DEBUG", Tags.REALM,
            f"SRP B={b_int}, g={g_int}, N={n_int}, s={s_int}")
        log("DEBUG", Tags.REALM,
            f"SRP N hex={n_int.to_bytes(32, 'big').hex(' ')}")
        log("DEBUG", Tags.REALM,
            f"SRP B len={len(b_bytes)}, g_len={g_len}, n_len={n_len}")

        srp = SRPClient(self._account, self._password)
        srp.step1(b_int, g_int, n_int, s_int)

        self._session_key = srp.session_key
        a_array = srp.a_pub.to_bytes(32, "little")
        m_array = srp.proof.to_bytes(20, "big")

        md = hashlib.sha1()
        md.update(a_array)
        md.update(
            _build_crc_hash(self._realm_build, self._platform)
        )
        crc_hash = md.digest()

        proof_payload = bytearray()
        proof_payload += a_array
        proof_payload += m_array
        proof_payload += crc_hash
        proof_payload.append(0)
        proof_payload.append(security_flag)
        if token:
            token_bytes = token.encode("utf-8")
            proof_payload.append(len(token_bytes))
            proof_payload += token_bytes

        log("DEBUG", Tags.REALM,
            f"Proof A (32): {a_array.hex(' ')}")
        log("DEBUG", Tags.REALM,
            f"Proof M (20): {m_array.hex(' ')}")
        log("DEBUG", Tags.REALM,
            f"Proof CRC (20): {crc_hash.hex(' ')}")
        log("DEBUG", Tags.REALM,
            f"Proof security_flag={security_flag} "
            f"full payload ({len(proof_payload)}B): "
            f"{bytes(proof_payload).hex(' ')}")

        self._w.write(bytes([CMD_AUTH_LOGON_PROOF]) + proof_payload)
        await self._w.drain()

        await self._read_proof_response(srp)

    async def _read_proof_response(self, srp: SRPClient) -> None:
        """Validate the server proof and request the realm list."""
        buf = await self._r.readexactly(2)
        cmd, result = buf[0], buf[1]
        log("DEBUG", Tags.REALM,
            f"Proof response header: cmd=0x{cmd:02X} result=0x{result:02X}")

        if not AuthResult.is_success(result):
            log("ERROR", Tags.REALM,
                f"Proof failed: cmd=0x{cmd:02X} result=0x{result:02X} "
                f"({AuthResult.get_message(result)})"
            )
            # Read remaining error payload if this is TBC+
            if self._expansion != WowExpansion.VANILLA:
                try:
                    extra = await asyncio.wait_for(
                        self._r.readexactly(2), timeout=2
                    )
                    log("DEBUG", Tags.REALM,
                        f"Proof error extra bytes: {to_hex_string(extra, add_spaces=True)}")
                except (asyncio.IncompleteReadError, TimeoutError):
                    pass
            self._on_error()
            self._on_disconnect()
            return

        proof_size = 25 if self._expansion == WowExpansion.VANILLA else 31
        remaining = await self._r.readexactly(proof_size - 1)

        log("DEBUG", Tags.REALM,
            f"Session key (40B): {srp.session_key.hex(' ')}")

        server_proof = _to_array(remaining[:20], reverse=False)
        local_proof = srp.generate_hash_logon_proof()

        log("DEBUG", Tags.REALM,
            f"Server proof (20): {server_proof.hex(' ')}")
        log("DEBUG", Tags.REALM,
            f"Local proof  (20): {local_proof.hex(' ')}")

        if server_proof != local_proof:
            log("ERROR", Tags.REALM, "Proof mismatch! Disconnecting.")
            self._on_disconnect()
            return

        self._w.write(
            bytes([CMD_REALM_LIST]) + (0).to_bytes(4, "little")
        )
        await self._w.drain()

        await self._read_realm_list()

    async def _read_realm_list(self) -> None:
        """Parse the realm list and locate the configured realm."""
        header = await self._r.readexactly(3)
        size = int.from_bytes(header[1:3], "little")

        data = await self._r.readexactly(size)

        is_vanilla = self._expansion == WowExpansion.VANILLA
        realms = _parse_realm_list(data, is_vanilla)

        matched = [
            r for r in realms
            if r.name.lower() == self._realm_name.lower()
        ]

        if not matched:
            self._on_error()
            return

        entry = matched[0]
        parts = entry.address.split(":")
        game_host = parts[0].strip()
        game_port = int(parts[1]) & 0xFFFF

        self._on_success(
            game_host, game_port, entry.name, entry.realm_id,
            self._session_key,
        )
