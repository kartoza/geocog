<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# PACKAGES

An annotated map of the software architecture: the Python modules that make up
geocog, the runtime tools they drive, and the packages that build and ship it.

## Application modules (`src/geocog/`)

| Module | Responsibility |
|--------|----------------|
| `engine.py` | UI-free core pipeline: GeoTIFF → COG conversion, source normalisation, share-link → range-URL rewriting, `gdalbuildvrt` wrapping, and `.env` round-tripping. Fully unit-tested. |
| `vault.py` | AES-GCM encrypted connection vault at `~/.config/geocog/connections.vault`; key derived from a master passphrase via PBKDF2 (600k). |
| `s3.py` | `mc`-driven bucket/folder listing and upload (pure `ls` parser, no SDK). |
| `browser.py` | Local file/folder browser widget (left pane). |
| `s3tree.py` | Lazy S3 tree widget (connections → buckets → folders, right pane). |
| `screens.py` | Modal dialogs: passphrase, connection manager, VRT-name, confirm. |
| `app.py` + `app.tcss` | Dual-pane Textual UI with threaded/async workers; three modes (Convert/Upload/VRT) plus styling. |
| `i18n/` | String catalogue (`en.json`) and language resolver for translatable UI text. |
| `__main__.py` | `python -m geocog` entry point. |

## Runtime dependencies (Python)

| Package | Why |
|---------|-----|
| [`textual`](https://textual.textualize.io/) | The TUI framework (widgets, screens, async workers). |
| [`cryptography`](https://cryptography.io/) | AES-GCM + PBKDF2 for the connection vault. |

## Runtime tools (shelled out to, provided by the flake)

| Tool | Why |
|------|-----|
| [GDAL](https://gdal.org) | `gdal_translate -of COG`, `gdalbuildvrt`, `gdalinfo` — the raster work. |
| [MinIO Client (`mc`)](https://min.io/docs/minio/linux/reference/minio-mc.html) | Bucket listing, upload, and scoped-key minting. |

## CLI apps (`scripts/*.sh`, exposed via the flake)

| App | Step |
|-----|------|
| `nix run .#to-cog` | GeoTIFF → COG (local). |
| `nix run .#upload` | Push COG(s) to object storage via `mc`. |
| `nix run .#make-key` | Mint a bucket-scoped upload key into `.env`. |
| `nix run .#make-vrt` | Wrap cloud COG(s) in a single GeoServer-ready VRT. |
| `nix run .#docs` | Serve / build the documentation site. |
| `nix run .#geocog` | Launch the TUI (drives all of the above). |

## Build, test & docs tooling

| Package | Role |
|---------|------|
| `setuptools` / `build` | PEP 517 wheel + sdist build backend. |
| `pytest` / `pytest-cov` | Test suite and coverage. |
| `ruff` | Lint + format. |
| `mkdocs-material` | Documentation site theme. |
| `mkdocs-with-pdf` | Combined PDF export of the docs. |
| `pyinstaller` | Standalone single-file binaries for the release matrix. |
| `cyclonedx-bom` | CycloneDX SBOM generation. |
| `pre-commit`, `reuse`, `gitleaks` | Quality + supply-chain gates. |

## Packaging targets (release artifacts)

Python wheel & sdist · standalone binaries (Linux/macOS-x86_64/macOS-arm64/Windows)
· Debian `.deb` · RPM `.rpm` · AppImage · Snap · CycloneDX SBOM.

See [`.github/workflows/release.yml`](.github/workflows/release.yml).
