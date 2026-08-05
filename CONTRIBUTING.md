<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# Contributing to geocog

Thanks for your interest in improving **geocog**! This project turns GeoTIFFs
into cloud-hosted Cloud Optimized GeoTIFFs (COGs) and wraps them in a
GeoServer-ready VRT, delivered as a keyboard-driven TUI and matching CLI tools.

We welcome issues, pull requests, docs, and translations. By participating you
agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting started

Everything you need comes from the Nix flake — no globally installed GDAL,
Python, or `mc` required.

```bash
# Enter the reproducible dev shell (gdal + mc + python + QA tooling)
nix develop

# Run the TUI
nix run .#geocog

# Run the test suite
pytest

# Serve the docs locally
nix run .#docs
```

If `nix` complains about experimental features, enable them once in
`~/.config/nix/nix.conf`:

```
experimental-features = nix-command flakes
```

## Development workflow

We follow a small, predictable loop:

1. **Open an issue first.** New features start life as a GitHub issue with a
   user story, a context diagram, success criteria, and a size estimate.
2. **Branch** from `main` using a descriptive name
   (`feat/vrt-multiselect`, `fix/vault-perms`).
3. **Write tests.** A feature is not complete without tests — the engine is
   fully unit-tested and the TUI is exercised headlessly with Textual's
   `run_test`. Run `pytest` before *and* after your change.
4. **Keep it DRY and asynchronous.** Long-running work runs off the UI thread.
   Reuse the shared engine rather than duplicating pipeline logic.
5. **Lint and format.** `pre-commit run --all-files` runs Ruff, REUSE licence
   linting, secret scanning, and spell checking. All of it also runs in CI.
6. **Update the docs.** Code and docs ship together; a change isn't done until
   `SPECIFICATION.md` and the `docs/` site reflect it.
7. **Open a PR** that references the issue with GitHub's `fixes #NNN` syntax so
   it closes on merge. Prefer many small PRs over one large one.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/). This drives
both the version bump and the `CHANGELOG.md`:

- `fix:` → patch release
- `feat:` → minor release
- `feat!:` / `BREAKING CHANGE:` → major release

Do **not** use `--no-verify`; the pre-commit hooks enforce our quality gates.

## Security & secrets

- Never commit credentials. Secrets live only in a `chmod 600` `.env`
  (git-ignored) and are never written to `~/.mc` or logged.
- Report vulnerabilities privately — see [SECURITY.md](SECURITY.md).

## Licensing

geocog is MIT-licensed and [REUSE](https://reuse.software)-compliant. Every
source file carries an SPDX header; run `reuse lint` (bundled in the dev shell)
before pushing. By contributing you agree your work is released under the MIT
licence.

---

Made with 💗 by [Kartoza](https://kartoza.com) ·
[Donate!](https://github.com/sponsors/kartoza) ·
[GitHub](https://github.com/kartoza/geocog)
