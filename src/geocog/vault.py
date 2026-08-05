# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Encrypted connection vault for geocog.

Bucket connections (name, endpoint, access key, secret key) are stored in a
single AES-GCM encrypted file unlocked by one master passphrase. The key is
derived with PBKDF2-HMAC-SHA256 (600k iterations). File layout:

    MAGIC(4) || salt(16) || nonce(12) || ciphertext

The plaintext is a JSON list of connections. MAGIC is used as the AEAD
associated data so a truncated/altered header fails authentication.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"CTV1"
ITERATIONS = 600_000
SALT_LEN = 16
NONCE_LEN = 12


class VaultError(Exception):
    pass


class BadPassphrase(VaultError):
    pass


@dataclass
class Connection:
    name: str
    endpoint: str = "https://api.minio.do.kartoza.com"
    access_key: str = ""
    secret_key: str = ""


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "geocog" / "connections.vault"


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), salt, ITERATIONS, dklen=32
    )


@dataclass
class Vault:
    path: Path = field(default_factory=default_path)

    def __post_init__(self) -> None:
        self.path = Path(self.path)

    def exists(self) -> bool:
        return self.path.is_file()

    def load(self, passphrase: str) -> list[Connection]:
        raw = self.path.read_bytes()
        if raw[:4] != MAGIC:
            raise VaultError("not a geocog vault file")
        salt = raw[4 : 4 + SALT_LEN]
        nonce = raw[4 + SALT_LEN : 4 + SALT_LEN + NONCE_LEN]
        ciphertext = raw[4 + SALT_LEN + NONCE_LEN :]
        key = _derive_key(passphrase, salt)
        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, MAGIC)
        except InvalidTag as exc:
            raise BadPassphrase("incorrect passphrase") from exc
        return [Connection(**item) for item in json.loads(plaintext)]

    def save(self, connections: list[Connection], passphrase: str) -> Path:
        salt = os.urandom(SALT_LEN)
        nonce = os.urandom(NONCE_LEN)
        key = _derive_key(passphrase, salt)
        payload = json.dumps([asdict(c) for c in connections]).encode("utf-8")
        ciphertext = AESGCM(key).encrypt(nonce, payload, MAGIC)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_bytes(MAGIC + salt + nonce + ciphertext)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)
        os.chmod(self.path, 0o600)
        return self.path
