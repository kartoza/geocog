# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Unit tests for the geocog engine (no gdal/mc required)."""

from __future__ import annotations

import base64
import os
import stat

import pytest

from geocog import engine


def _share_link(internal_url: str) -> str:
    blob = base64.urlsafe_b64encode(internal_url.encode()).decode().rstrip("=")
    return f"https://minio.do.kartoza.com/oauth_callback/api/v1/download-shared-object/{blob}"


def test_rewrite_share_link_extracts_bucket_key():
    internal = "http://127.0.0.1:9000/tim-deleteme/dgt/MDT.cog.tif?X-Amz-Algorithm=AWS4"
    url = _share_link(internal)
    assert (
        engine.rewrite_share_link(url)
        == "https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT.cog.tif"
    )


def test_rewrite_share_link_custom_endpoint():
    internal = "http://127.0.0.1:9000/bucket/key.tif?sig=1"
    out = engine.rewrite_share_link(
        _share_link(internal), api_endpoint="https://s3.example.com/"
    )
    assert out == "https://s3.example.com/bucket/key.tif"


def test_rewrite_share_link_rejects_non_share_url():
    assert engine.rewrite_share_link("https://example.com/a.tif") is None


@pytest.mark.parametrize(
    "src, expected",
    [
        ("https://host/a.cog.tif", "/vsicurl/https://host/a.cog.tif"),
        ("/vsis3/bucket/a.cog.tif", "/vsis3/bucket/a.cog.tif"),
        ("/vsicurl/https://x/y.tif", "/vsicurl/https://x/y.tif"),
    ],
)
def test_normalise_source_variants(src, expected):
    assert engine.normalise_source(src) == expected


def test_normalise_source_streaming():
    assert engine.normalise_source("https://h/a.tif", streaming=True) == (
        "/vsicurl_streaming/https://h/a.tif"
    )


def test_normalise_source_rewrites_share_link():
    internal = "http://127.0.0.1:9000/b/k.cog.tif?s=1"
    out = engine.normalise_source(_share_link(internal))
    assert out == "/vsicurl/https://api.minio.do.kartoza.com/b/k.cog.tif"


def test_normalise_source_local_file(tmp_path):
    f = tmp_path / "x.cog.tif"
    f.write_text("data")
    assert engine.normalise_source(str(f)) == str(f.resolve())


def test_cog_output_path():
    assert engine.cog_output_path("dgt/MDT-01.tiff").name == "MDT-01.cog.tif"


def test_discover_rasters_and_cogs(tmp_path):
    (tmp_path / "a.tif").write_text("x")
    (tmp_path / "b.tiff").write_text("x")
    (tmp_path / "c.cog.tif").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "d.tif").write_text("x")

    rasters = {p.name for p in engine.discover_rasters(tmp_path)}
    cogs = {p.name for p in engine.discover_cogs(tmp_path)}
    assert rasters == {"a.tif", "b.tiff", "d.tif"}
    assert cogs == {"c.cog.tif"}


def test_minio_config_roundtrip_and_perms(tmp_path):
    cfg = engine.MinioConfig(
        endpoint="https://api.example.com",
        access_key="AKID",
        secret_key="s3cr3t/with'quote",
        bucket="mybucket",
        prefix="dgt",
    )
    path = tmp_path / ".env"
    cfg.save(path)

    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600

    loaded = engine.MinioConfig.load(path)
    assert loaded == cfg


def test_minio_config_object_url():
    cfg = engine.MinioConfig(endpoint="https://api.x.com/", bucket="b", prefix="dgt")
    assert cfg.object_url("f.cog.tif") == "https://api.x.com/b/dgt/f.cog.tif"


def test_minio_config_load_missing_returns_default(tmp_path):
    cfg = engine.MinioConfig.load(tmp_path / "nope.env")
    assert cfg == engine.MinioConfig()


def test_make_dir(tmp_path):
    created = engine.make_dir(tmp_path, "newfolder")
    assert created.is_dir()
    with pytest.raises(FileExistsError):
        engine.make_dir(tmp_path, "newfolder")


def test_delete_path_file_and_dir(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    engine.delete_path(f)
    assert not f.exists()

    d = tmp_path / "sub"
    d.mkdir()
    (d / "inner.txt").write_text("y")
    engine.delete_path(d)
    assert not d.exists()
