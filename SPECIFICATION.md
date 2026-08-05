<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# SPECIFICATION — geocog

## Purpose

Turn ordinary GeoTIFFs into cloud-hosted Cloud Optimized GeoTIFFs (COGs) and wrap
one or more of them in a single small GDAL VRT that GeoServer can publish as one
seamless coverage. Delivered as a keyboard-driven TUI (`geocog`) plus matching
CLI tools, sharing one engine.

## Users & stories

- **GIS operator** — "I have GeoTIFFs; I want them in MinIO and published in
  GeoServer without memorising gdal flags." → Convert → Upload → VRT in the TUI.
- **Server admin** — "I run MinIO via OIDC; I need a scoped upload key." →
  `make-key`, or Console → Access Keys.
- **Automator** — "I want the same pipeline in a script." → `to-cog`, `upload`,
  `make-vrt` CLIs.

## Functional requirements

The TUI is **dual-pane** (local left, destination/S3 right) with three modes
switched by F2/F3/F4; F5 runs the active mode.

1. **Mode 1 — COG creation** — left: local rasters (COGs hidden); right: a local
   output folder. F5 writes COGs (`-of COG`, 512 px tiles, overviews, DEFLATE,
   type-aware predictor) into the right-pane folder.
2. **Mode 2 — COG upload** — left: local `*.cog.tif`; right: lazy S3 tree
   (connections → buckets → folders). Highlight a bucket/folder, F5 uploads the
   selected COGs there via `mc`; returns object URLs.
3. **Mode 3 — VRT creation** — left: local destination folder; right: S3 tree,
   multi-select COG files/folders (folders expand to every COG inside). F5 →
   name popover → `gdalbuildvrt` writes the VRT locally referencing the cloud
   COGs; console share links are rewritten to range-capable URLs.
4. **Connections & vault** — a connection manager (key `c`) adds/edits/deletes
   bucket connections (name, endpoint, access key, secret key). They are stored
   in an AES-GCM vault at `~/.config/geocog/connections.vault`, key derived from
   a master passphrase via PBKDF2 (600k). Connections are the top nodes of the
   S3 tree. (The standalone CLI still uses `make-key` + `.env`.)

## Non-functional requirements

- **Small / fast / simple**: three tabs, number-key + F5 navigation; long tasks
  run off the UI thread.
- **Secure**: secrets only in `.env` (git-ignored, Claude-ignored, `chmod 600`);
  never written to `~/.mc`; never logged.
- **Range over streaming**: always target range-capable endpoints; streaming is a
  clearly-labelled test-only fallback. See `docs/cog-range-requests.md`.
- **Reproducible**: Nix flake provides GDAL + `mc` + Python; `nix build .#geocog`
  runs the test suite in-sandbox.
- **Accessible/branded**: Kartoza palette (navy/teal/orange); keyboard-first.

## Architecture

- `src/geocog/engine.py` — UI-free COG/VRT pipeline (unit-tested).
- `src/geocog/vault.py` — AES-GCM encrypted connection vault.
- `src/geocog/s3.py` — `mc`-driven bucket listing/upload (pure ls parser).
- `src/geocog/browser.py`, `s3tree.py` — local browser + lazy S3 tree widgets.
- `src/geocog/screens.py` — passphrase / connections / VRT-name modals.
- `src/geocog/app.py` + `app.tcss` — dual-pane Textual UI, threaded/async workers.
- `src/geocog/i18n/` — string catalogue (`en.json`) + language resolver `t()`.
- `scripts/*.sh` — the equivalent CLI steps (same tools, same behaviour).
- `flake.nix` — apps `geocog`, `to-cog`, `upload`, `make-vrt`, `make-key`, `docs`.

## Internationalisation

User-visible strings are keyed and resolved through `geocog.i18n.t(key)`, with
`en.json` as the source-of-truth catalogue and fallback. The active language is
read from `GEOCOG_LANG`/`LANG`. Translations are added as sibling `<lang>.json`
files; no English text is hard-coded at call sites.

## Documentation

- MkDocs Material site under `docs/`, split into User / Administrator / Concepts
  / Developer guides. Base build uses `mkdocs.yml` (Nix-provided
  `mkdocs-material`).
- A combined **PDF** is produced from `mkdocs.pdf.yml` (adds `mkdocs-with-pdf`,
  installed via the `docs` pip extra) and published to `site/pdf/geocog.pdf`,
  attached to every release.
- Both the HTML site and the PDF are deployed to GitHub Pages on push to `main`.

## Packaging & release

- **Versioning**: SemVer, driven by Conventional Commits; changes recorded in
  `CHANGELOG.md` (Keep a Changelog).
- **CI** (`ci.yml`): `nix build .#geocog` (tests in-sandbox), strict docs build,
  and a quality gate (Ruff, REUSE/SPDX, gitleaks).
- **PR artifacts** (`pr-artifacts.yml`): preview wheel/sdist + binaries, a
  CycloneDX SBOM, and a security scan (pip-audit, bandit) posted to the PR.
- **Release** (`release.yml`, on `v*` tags): wheel + sdist, standalone binaries
  (Linux/macOS-x86_64/macOS-arm64/Windows), `.deb`, `.rpm`, AppImage, Snap, docs
  PDF, and SBOM — all attached to a generated GitHub Release.
- **Reproducible**: `nix build` runs the test suite in-sandbox; the dev shell
  ships the full QA toolchain.

## Testing

- Engine: share-link rewrite, source normalisation, `.env` round-trip + perms,
  discovery.
- App: headless boot, tab switching, URL injection (Textual `run_test`).
- Definition of done: compiles, `pytest` green, `pre-commit` clean, docs +
  `CHANGELOG.md` updated, version bumped.

## Out of scope (v0.1)

- Publishing to GeoServer (see kartoza/geotui); reprojection of mixed-CRS inputs.
- Signed OS packages and a PyPI trusted publisher (workflow stubs present,
  disabled until credentials/signing keys are configured).
