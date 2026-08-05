<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# CLAUDE.md — project guide for geocog

Project-specific guidance for AI assistants and contributors. This complements
(does not replace) the global standards.

## What this is

`geocog` turns ordinary GeoTIFFs into cloud-hosted **Cloud Optimized GeoTIFFs
(COGs)** and wraps one or more of them in a single small GDAL **VRT** that
GeoServer can publish as one seamless coverage. It ships as a keyboard-driven
Textual **TUI** (`geocog`) plus matching CLI apps, all sharing one engine.

## Golden rules for this repo

- **Everything runs through the Nix flake.** Never assume a global GDAL, `mc`,
  or Python. Use `nix develop` / `nix run .#<app>`.
- **Secrets are sacred.** Credentials live only in a `chmod 600` `.env`
  (git-ignored) and the AES-GCM vault. Never write them to `~/.mc`, never log
  them, never commit them.
- **Range over streaming.** Always target range-capable endpoints
  (`api.minio.do.kartoza.com/<bucket>/<key>`). Streaming is a test-only
  fallback and must stay clearly labelled.
- **One engine, no duplication.** UI, CLI, and tests all call `engine.py`. Do
  not fork pipeline logic into the UI layer.
- **Off the UI thread.** Long GDAL/`mc` operations run as Textual workers.
- **i18n from day one.** Route user-visible strings through `geocog.i18n.t`.

## Layout

```
src/geocog/      # engine + TUI (see PACKAGES.md for the module map)
scripts/*.sh     # the equivalent CLI steps (same tools, same behaviour)
flake.nix        # dev shell + apps: geocog, to-cog, upload, make-vrt, make-key, docs
docs/            # MkDocs Material source (user / admin / developer guides)
tests/           # pytest: pure-engine tests + headless Textual app tests
```

## Definition of done

Compiles, `pytest` is green, `pre-commit run --all-files` is clean,
`SPECIFICATION.md` + `docs/` updated, `CHANGELOG.md` has an entry, version
bumped per Conventional Commits.

## Commands

```bash
nix run .#geocog                    # the TUI
pytest                              # tests
nix run .#docs                      # serve docs
nix run .#docs -- build             # build static site
pre-commit run --all-files          # lint / format / licence / secrets
nix build .#geocog -L               # build + run tests in the nix sandbox
```
