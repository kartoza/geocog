<!--
SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
SPDX-License-Identifier: MIT
-->

# winget packaging

geocog is published to the Windows Package Manager community repository
([microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)) under the
identifier **`Kartoza.geocog`**, so users can:

```powershell
winget install Kartoza.geocog
```

## How it's published

The release workflow's `publish-winget` job uses
[`wingetcreate`](https://github.com/microsoft/winget-create) to generate the
three-file YAML manifest from the released MSI URL and submit a pull request to
`winget-pkgs`. It runs only when a `WINGET_TOKEN` secret (a GitHub PAT that can
push to your fork of `winget-pkgs`) is configured.

- **First-ever submission** is done once with `wingetcreate new` (manual), which
  seeds the package in the community repo.
- **Every subsequent release** is automated via `wingetcreate update`.

Manifests are generated on demand rather than committed here, so they never go
stale against the released installer.
