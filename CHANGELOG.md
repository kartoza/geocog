<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Full GitHub project scaffolding modelled on `kartoza/geotui`:
  - CI, docs-to-Pages, PR-artifacts, and release workflows.
  - Multi-format release artifacts: Python wheel/sdist, standalone binaries
    (Linux/macOS/Windows), `.deb`, `.rpm`, AppImage, and Snap.
  - Documentation site (MkDocs Material) with a combined **PDF** build published
    alongside the HTML site and attached to releases.
  - Community health files: `LICENSE`, `CONTRIBUTING`, `CODE_OF_CONDUCT`,
    `SECURITY`, issue/PR templates, `FUNDING`, and Dependabot.
  - Supply-chain hardening: CycloneDX SBOM on every PR and release, `pre-commit`
    (Ruff, REUSE/SPDX, gitleaks secret scanning, spell check), and REUSE
    compliance across the tree.
  - `PACKAGES.md`, project `CLAUDE.md`, `.exrc`, and `.nvim.lua`.
- i18n string catalogue scaffold (`src/geocog/i18n/`) with English source
  strings and an `os.environ`-driven language resolver.

### Changed

- **Renamed the package and CLI from `cogtui` to `geocog`** (repo
  `kartoza/geocog`). All imports, the config directory
  (`~/.config/geocog/`), flake apps, and docs were updated accordingly.
- `pyproject.toml` gained full packaging metadata, classifiers, optional
  dependency groups (`dev`, `docs`, `package`), and Ruff/coverage config.
- `flake.nix` dev shell now ships the QA toolchain (`pre-commit`, `reuse`,
  `gitleaks`, `ruff`).

## [0.1.0] — 2026-08-05

### Added

- Initial `geocog` (formerly `cogtui`) toolkit: a dual-pane Textual TUI plus
  matching CLI apps (`to-cog`, `upload`, `make-vrt`, `make-key`) for the
  GeoTIFF → COG → object-storage → GeoServer VRT workflow.
- AES-GCM encrypted connection vault.
- Nix flake providing a reproducible dev shell and runnable apps.
- MkDocs documentation site.

[Unreleased]: https://github.com/kartoza/geocog/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kartoza/geocog/releases/tag/v0.1.0
