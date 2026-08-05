# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# PyInstaller spec for a single-file `geocog` binary.
#   pyinstaller geocog.spec
#
# Note: GDAL and the MinIO client (`mc`) are runtime dependencies that are NOT
# bundled here — they must be present on PATH. The self-contained option is the
# Nix flake (`nix run .#geocog`).

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("textual",):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

datas += [
    ("src/geocog/app.tcss", "geocog"),
    ("src/geocog/i18n", "geocog/i18n"),
]

a = Analysis(
    ["src/geocog/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="geocog",
    console=True,
    onefile=True,
    strip=False,
    upx=True,
)
