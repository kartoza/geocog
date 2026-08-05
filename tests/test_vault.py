# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Tests for the encrypted connection vault and S3 listing parser."""

from __future__ import annotations

import os
import stat

import pytest

from geocog import s3
from geocog.vault import BadPassphrase, Connection, Vault, VaultError


def test_vault_roundtrip_and_perms(tmp_path):
    path = tmp_path / "c.vault"
    vault = Vault(path)
    conns = [
        Connection("kartoza", "https://api.minio.do.kartoza.com", "AKID", "s3cr3t/x"),
        Connection("other", "https://s3.example.com", "A2", "p2"),
    ]
    vault.save(conns, "hunter2")

    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    loaded = Vault(path).load("hunter2")
    assert loaded == conns


def test_vault_wrong_passphrase(tmp_path):
    path = tmp_path / "c.vault"
    Vault(path).save([Connection("k", "https://e")], "right")
    with pytest.raises(BadPassphrase):
        Vault(path).load("wrong")


def test_vault_rejects_foreign_file(tmp_path):
    path = tmp_path / "c.vault"
    path.write_bytes(b"not a vault at all........................")
    with pytest.raises(VaultError):
        Vault(path).load("x")


def test_vault_exists(tmp_path):
    path = tmp_path / "c.vault"
    v = Vault(path)
    assert not v.exists()
    v.save([], "pw")
    assert v.exists()


def test_parse_ls_buckets_and_objects():
    output = "\n".join(
        [
            '{"type":"folder","key":"bucket-a/"}',
            '{"type":"folder","key":"bucket-b/"}',
            '{"type":"file","key":"scene.cog.tif","size":123}',
            '{"status":"error","error":{"message":"nope"}}',
            "",
        ]
    )
    entries = s3.parse_ls(output)
    names = [(e.name, e.is_dir) for e in entries]
    # folders sort before files, alphabetically
    assert names == [("bucket-a", True), ("bucket-b", True), ("scene.cog.tif", False)]


def test_object_url():
    conn = Connection("k", "https://api.x.com/")
    assert (
        s3.object_url(conn, "b", "dgt/a.cog.tif") == "https://api.x.com/b/dgt/a.cog.tif"
    )
