# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""S3/MinIO operations for geocog, driven by the ``mc`` client.

Each call configures ``mc`` in a throwaway config dir (alias ``c``) so a
connection's secret is never written to ``~/.mc``.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .engine import COG_SUFFIX, EngineError, LogFn, _run, require
from .vault import Connection


@dataclass(frozen=True)
class S3Entry:
    name: str  # leaf name (no trailing slash)
    is_dir: bool


def parse_ls(output: str) -> list[S3Entry]:
    """Parse ``mc ls --json`` output into entries (pure, unit-tested)."""
    entries: list[S3Entry] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("status") == "error":
            continue
        key = obj.get("key") or obj.get("name") or ""
        is_dir = obj.get("type") == "folder" or key.endswith("/")
        name = key.rstrip("/")
        if name:
            entries.append(S3Entry(name, is_dir))
    entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
    return entries


class _Alias:
    """Context manager yielding an ``mc`` base command with alias ``c`` set."""

    def __init__(self, conn: Connection):
        self.conn = conn

    def __enter__(self) -> list[str]:
        self.dir = tempfile.mkdtemp()
        mc = require("mc")
        _run(
            [
                mc,
                "--config-dir",
                self.dir,
                "alias",
                "set",
                "c",
                self.conn.endpoint,
                self.conn.access_key,
                self.conn.secret_key,
            ]
        )
        return [mc, "--config-dir", self.dir]

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


def list_entries(conn: Connection, path: str = "") -> list[S3Entry]:
    """List one level. ``path`` empty → buckets; else ``bucket/prefix``."""
    target = "c/" + path
    with _Alias(conn) as base:
        out = _run([*base, "ls", "--json", target])
    return parse_ls(out)


def list_cogs_recursive(conn: Connection, bucket: str, prefix: str = "") -> list[str]:
    """Return keys (relative to *bucket*) of every COG under bucket/prefix."""
    prefix = prefix.strip("/")
    target = f"c/{bucket}/{prefix}".rstrip("/")
    with _Alias(conn) as base:
        out = _run([*base, "ls", "--recursive", "--json", target])
    keys: list[str] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        rel = obj.get("key", "")
        if not rel or rel.endswith("/"):
            continue
        full = f"{prefix}/{rel}" if prefix else rel
        if full.lower().endswith(COG_SUFFIX):
            keys.append(full)
    return sorted(keys)


def object_url(conn: Connection, bucket: str, key: str) -> str:
    return f"{conn.endpoint.rstrip('/')}/{bucket}/{key.lstrip('/')}"


def make_bucket(conn: Connection, name: str) -> None:
    with _Alias(conn) as base:
        _run([*base, "mb", f"c/{name}"])


def make_folder(conn: Connection, bucket: str, prefix: str, name: str) -> None:
    """Create a folder marker (``<prefix>/<name>/.keep``) so the prefix exists."""
    key = "/".join(
        part for part in [prefix.strip("/"), name.strip("/"), ".keep"] if part
    )
    with _Alias(conn) as base:
        with tempfile.NamedTemporaryFile() as empty:
            _run([*base, "cp", empty.name, f"c/{bucket}/{key}"])


def remove(
    conn: Connection,
    bucket: str,
    path: str,
    recursive: bool = False,
    log: LogFn | None = None,
) -> None:
    target = f"c/{bucket}/{path}".rstrip("/")
    args = ["rm", "--force"]
    if recursive:
        args.append("--recursive")
    with _Alias(conn) as base:
        _run([*base, *args, target], log=log)


def remove_bucket(conn: Connection, bucket: str, log: LogFn | None = None) -> None:
    with _Alias(conn) as base:
        _run([*base, "rb", "--force", f"c/{bucket}"], log=log)


def upload(
    files: Sequence[str | Path],
    conn: Connection,
    bucket: str,
    prefix: str = "",
    public: bool = False,
    log: LogFn | None = None,
) -> list[str]:
    """Upload ``files`` to bucket/prefix; return their object URLs."""
    if not files:
        raise EngineError("no files selected to upload")
    prefix = prefix.strip("/")
    dest = f"c/{bucket}" + (f"/{prefix}" if prefix else "")
    with _Alias(conn) as base:
        _run([*base, "cp", *[str(f) for f in files], dest + "/"], log=log)
        if public:
            if log:
                log(f"granting anonymous download on {bucket}/{prefix}")
            _run([*base, "anonymous", "set", "download", dest])
    return [
        object_url(conn, bucket, f"{prefix}/{Path(f).name}" if prefix else Path(f).name)
        for f in files
    ]
