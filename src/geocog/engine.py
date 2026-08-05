# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Pipeline engine for geocog.

Pure-Python wrappers around the ``gdal`` and ``mc`` command-line tools plus the
MinIO share-link handling. This module has **no Textual dependency** so it can
be unit-tested on its own and reused as a library.
"""

from __future__ import annotations

import base64
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_API_ENDPOINT = "https://api.minio.do.kartoza.com"
RASTER_EXTS = (".tif", ".tiff")
COG_SUFFIX = ".cog.tif"
SHARE_MARKER = "/download-shared-object/"

LogFn = Callable[[str], None]


class EngineError(RuntimeError):
    """Raised when an external tool is missing or exits non-zero."""


# --------------------------------------------------------------------------- #
# Tool discovery + subprocess plumbing
# --------------------------------------------------------------------------- #
def which(tool: str) -> str | None:
    return shutil.which(tool)


def require(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise EngineError(f"'{tool}' not found on PATH — run inside `nix develop`")
    return path


def missing_tools(tools: Sequence[str]) -> list[str]:
    return [t for t in tools if shutil.which(t) is None]


def _run(cmd: Sequence[str], log: LogFn | None = None, env: dict | None = None) -> str:
    """Run ``cmd``, streaming combined output to ``log`` line by line.

    Returns the full captured output. Raises :class:`EngineError` on failure.
    The command itself is never logged, so secrets in argv are not echoed.
    """
    try:
        proc = subprocess.Popen(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
    except FileNotFoundError as exc:  # pragma: no cover - guarded by require()
        raise EngineError(str(exc)) from exc

    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        if log:
            log(line)
    rc = proc.wait()
    if rc != 0:
        raise EngineError(f"{Path(cmd[0]).name} exited with status {rc}")
    return "\n".join(lines)


def _curl_env() -> dict:
    """Environment tuned for /vsicurl against object stores."""
    return dict(
        os.environ,
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_USE_HEAD="NO",
        GDAL_HTTP_MAX_RETRY="3",
        GDAL_HTTP_RETRY_DELAY="2",
    )


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def make_dir(parent: str | Path, name: str) -> Path:
    """Create a single subdirectory; error if it already exists."""
    target = Path(parent) / name
    target.mkdir(parents=False, exist_ok=False)
    return target


def delete_path(path: str | Path) -> None:
    """Delete a file or (recursively) a directory."""
    p = Path(path)
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()


def is_raster(p: str | Path) -> bool:
    """A GeoTIFF that is not already a COG."""
    p = Path(p)
    return p.suffix.lower() in RASTER_EXTS and not p.name.lower().endswith(COG_SUFFIX)


def is_cog(p: str | Path) -> bool:
    return Path(p).name.lower().endswith(COG_SUFFIX)


def collect_matching(root: str | Path, match: Callable[[Path], bool]) -> list[Path]:
    """All files under ``root`` (recursive) for which ``match`` is true."""
    try:
        return sorted(p for p in Path(root).rglob("*") if p.is_file() and match(p))
    except OSError:
        return []


def discover_rasters(root: str | Path) -> list[Path]:
    """Local GeoTIFFs that are *not* already COGs."""
    return collect_matching(root, is_raster)


def discover_cogs(root: str | Path) -> list[Path]:
    return collect_matching(root, is_cog)


# --------------------------------------------------------------------------- #
# Step 1 — GeoTIFF -> COG
# --------------------------------------------------------------------------- #
def band_dtype(path: str | Path) -> str:
    out = _run([require("gdalinfo"), str(path)])
    m = re.search(r"Type=(\w+)", out)
    return m.group(1) if m else ""


def cog_output_path(path: str | Path) -> Path:
    path = Path(path)
    return path.with_name(path.stem + COG_SUFFIX)


def to_cog(
    path: str | Path, outdir: str | Path | None = None, log: LogFn | None = None
) -> Path:
    """Convert one raster to a COG, written to ``outdir`` (default: beside input)."""
    path = Path(path)
    out = cog_output_path(path)
    if outdir is not None:
        out = Path(outdir) / out.name
    dtype = band_dtype(path)
    predictor = "3" if dtype in ("Float32", "Float64") else "2"
    _run(
        [
            require("gdal_translate"),
            str(path),
            str(out),
            "-of",
            "COG",
            "-co",
            "COMPRESS=DEFLATE",
            "-co",
            f"PREDICTOR={predictor}",
            "-co",
            "BLOCKSIZE=512",
            "-co",
            "OVERVIEW_RESAMPLING=AVERAGE",
            "-co",
            "NUM_THREADS=ALL_CPUS",
            "-co",
            "BIGTIFF=IF_SAFER",
        ],
        log=log,
    )
    return out


# --------------------------------------------------------------------------- #
# MinIO share links + source normalisation
# --------------------------------------------------------------------------- #
def _b64url_decode(blob: str) -> bytes:
    blob = blob.split("?", 1)[0]
    blob += "=" * (-len(blob) % 4)
    return base64.urlsafe_b64decode(blob)


def rewrite_share_link(
    url: str, api_endpoint: str = DEFAULT_API_ENDPOINT
) -> str | None:
    """Turn a MinIO console share link into a range-capable S3 API URL.

    The base64url blob decodes to the internal presigned URL
    ``http://127.0.0.1:9000/<bucket>/<key>?<sig>``; we keep only ``<bucket>/<key>``
    and point it at the public S3 API host. Returns ``None`` if the URL is not a
    share link or cannot be decoded.
    """
    if SHARE_MARKER not in url:
        return None
    blob = url.split(SHARE_MARKER, 1)[1]
    try:
        internal = _b64url_decode(blob).decode("utf-8", "replace")
    except Exception:
        return None
    after_scheme = internal.split("://", 1)[-1]
    if "/" not in after_scheme:
        return None
    path = after_scheme.split("/", 1)[1].split("?", 1)[0]
    if not path:
        return None
    return f"{api_endpoint.rstrip('/')}/{path}"


def normalise_source(
    s: str, streaming: bool = False, api_endpoint: str = DEFAULT_API_ENDPOINT
) -> str:
    """Map a user-supplied source to something GDAL can open."""
    http_vsi = "/vsicurl_streaming/" if streaming else "/vsicurl/"
    s = s.strip()
    if SHARE_MARKER in s:
        api = rewrite_share_link(s, api_endpoint)
        return http_vsi + (api or s)
    if s.startswith(("http://", "https://")):
        return http_vsi + s
    if s.startswith(
        (
            "/vsicurl/",
            "/vsicurl_streaming/",
            "/vsis3/",
            "/vsigs/",
            "/vsiaz/",
            "/vsizip/",
            "/vsitar/",
        )
    ):
        return s
    p = Path(s)
    if p.is_file():
        return str(p.resolve())
    return s


# --------------------------------------------------------------------------- #
# Step 3 — build the VRT
# --------------------------------------------------------------------------- #
def build_vrt(
    sources: Iterable[str],
    out: str | Path,
    streaming: bool = False,
    api_endpoint: str = DEFAULT_API_ENDPOINT,
    log: LogFn | None = None,
) -> Path:
    norm = [normalise_source(s, streaming, api_endpoint) for s in sources if s.strip()]
    if not norm:
        raise EngineError("no sources given")
    if log:
        for n in norm:
            log(f"  source: {n.split('?', 1)[0]}")
    _run(
        [require("gdalbuildvrt"), "-resolution", "highest", str(out), *norm],
        log=log,
        env=_curl_env(),
    )
    return Path(out)


def gdalinfo_summary(path: str | Path) -> str:
    out = _run([require("gdalinfo"), str(path)], env=_curl_env())
    wanted = ("Size is", "Pixel Size", "NoData", "EPSG", "Overviews", "Band ", "Driver")
    keep = [ln.strip() for ln in out.splitlines() if any(w in ln for w in wanted)]
    return "\n".join(keep[:24])


# --------------------------------------------------------------------------- #
# MinIO configuration + upload
# --------------------------------------------------------------------------- #
ENV_FILE = ".env"


@dataclass
class MinioConfig:
    endpoint: str = DEFAULT_API_ENDPOINT
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "tim-deleteme"
    prefix: str = ""

    _KEYS = {
        "MINIO_ENDPOINT": "endpoint",
        "MINIO_ACCESS_KEY": "access_key",
        "MINIO_SECRET_KEY": "secret_key",
        "MINIO_BUCKET": "bucket",
        "MINIO_PREFIX": "prefix",
    }

    @classmethod
    def load(cls, path: str | Path = ENV_FILE) -> MinioConfig:
        cfg = cls()
        p = Path(path)
        if not p.exists():
            return cfg
        for raw in p.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            attr = cls._KEYS.get(key.strip())
            if not attr:
                continue
            # Values are written POSIX-shell-quoted (so bash can source .env);
            # decode them the same way the shell would.
            try:
                tokens = shlex.split(val.strip())
            except ValueError:
                tokens = [val.strip().strip("'\"")]
            setattr(cfg, attr, tokens[0] if tokens else "")
        return cfg

    def save(self, path: str | Path = ENV_FILE) -> Path:
        p = Path(path)

        def q(v: str) -> str:
            return "'" + v.replace("'", "'\\''") + "'"

        lines = ["# MinIO credentials for geocog — DO NOT COMMIT"]
        for env_key, attr in self._KEYS.items():
            lines.append(f"{env_key}={q(getattr(self, attr))}")
        p.write_text("\n".join(lines) + "\n")
        os.chmod(p, 0o600)
        return p

    def object_url(self, filename: str) -> str:
        base = self.endpoint.rstrip("/") + "/" + self.bucket
        if self.prefix:
            base += "/" + self.prefix.strip("/")
        return f"{base}/{filename}"


def mc_upload(
    files: Sequence[str | Path],
    cfg: MinioConfig,
    public: bool = False,
    log: LogFn | None = None,
) -> list[str]:
    """Upload ``files`` to MinIO with ``mc``; return the resulting object URLs.

    ``mc`` runs against a throwaway config dir, so credentials never touch
    ``~/.mc``. The alias-set command (which carries the secret) is not logged.
    """
    if not files:
        raise EngineError("no files selected to upload")
    if not cfg.access_key or not cfg.secret_key:
        raise EngineError("access key and secret key are required")
    mc = require("mc")
    with tempfile.TemporaryDirectory() as cfgdir:
        base = [mc, "--config-dir", cfgdir]
        _run(
            [
                *base,
                "alias",
                "set",
                "geocog",
                cfg.endpoint,
                cfg.access_key,
                cfg.secret_key,
            ]
        )
        try:
            _run([*base, "mb", "--ignore-existing", f"geocog/{cfg.bucket}"], log=log)
        except EngineError:
            pass
        dest = f"geocog/{cfg.bucket}"
        if cfg.prefix:
            dest += "/" + cfg.prefix.strip("/")
        _run([*base, "cp", *[str(f) for f in files], dest + "/"], log=log)
        if public:
            if log:
                log(f"granting anonymous download on {dest.split('/', 1)[1]}")
            _run([*base, "anonymous", "set", "download", dest], log=log)
    return [cfg.object_url(Path(f).name) for f in files]
