<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# Security Policy

## Supported versions

geocog is pre-1.0. Security fixes are applied to the latest `0.x` release and
the `main` branch.

| Version | Supported |
|---------|-----------|
| `0.1.x` | ✅        |
| `< 0.1` | ❌        |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report vulnerabilities privately using GitHub's
[private vulnerability reporting](https://github.com/kartoza/geocog/security/advisories/new),
or by email to **security@kartoza.com** (subject: `geocog security`).

Please include:

- A description of the issue and its impact.
- Steps to reproduce (a proof of concept if possible).
- Affected version(s) and environment.

We aim to acknowledge reports within **3 business days** and to ship a fix or
mitigation for confirmed high-severity issues within **30 days**. We will credit
reporters who wish to be acknowledged once a fix is released.

## Security posture

geocog handles object-storage credentials, so a few properties are treated as
hard requirements:

- **Secrets never touch the repo.** Credentials live only in a `chmod 600`
  `.env` (git-ignored and Claude-ignored) and are never written to `~/.mc` or
  emitted to logs.
- **Vault at rest.** Saved connections are stored in an AES-GCM vault under
  `~/.config/geocog/connections.vault`, with the key derived from a master
  passphrase via PBKDF2 (600k iterations).
- **Supply chain.** Every release ships a CycloneDX SBOM. CI runs `pip-audit`,
  `bandit`, and secret scanning (`gitleaks`) on every pull request.
- **Range over streaming.** Public data flows target range-capable endpoints;
  whole-file streaming is a clearly-labelled test-only fallback.

If you find a gap in any of the above, we consider it a security issue — please
report it as described above.
