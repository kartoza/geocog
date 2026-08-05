# Release & signing setup

This page is for maintainers. It explains how a release is cut, every GitHub
Actions **secret** the release pipeline can use, where to obtain each one, and
what happens when a secret is absent.

## How a release is cut

Releases are tag-driven. Pushing a `v*` tag runs
[`release.yml`](https://github.com/kartoza/geocog/blob/main/.github/workflows/release.yml):

```bash
# 1. Land your change on main (Conventional Commits drive the version bump).
# 2. Update CHANGELOG.md: move Unreleased → the new version.
# 3. Bump the version in pyproject.toml (and snap/snapcraft.yaml if pinned).
git tag -a v0.1.0 -m "geocog 0.1.0"
git push origin v0.1.0
```

The workflow then builds every artifact — wheel/sdist, standalone binaries
(Linux/macOS×2/Windows), `.deb`, `.rpm`, AppImage, Snap, **macOS `.dmg`**,
**Windows `.msi`**, the docs **PDF**, and a CycloneDX **SBOM** — attaches them to
a generated GitHub Release, then runs the package-manager publish jobs.

!!! info "Everything works unsigned"
    None of the secrets below are required to produce a release. When a secret
    is unset, that step **skips cleanly** (unsigned artifact / no publish) and
    logs why. Add secrets to progressively unlock signing and managed installs.

Set all secrets under **Settings → Secrets and variables → Actions → New
repository secret**.

## Secrets at a glance

| Secret | Unlocks | Required for |
|--------|---------|--------------|
| `MACOS_CERT_BASE64` | imports your Developer ID cert into a temp keychain | macOS signing |
| `MACOS_CERT_PASSWORD` | (password for the `.p12` above) | macOS signing |
| `MACOS_SIGN_IDENTITY` | codesigned macOS binary + DMG | Gatekeeper-friendly macOS |
| `MACOS_NOTARY_APPLE_ID` | notarized + stapled DMG | no Gatekeeper prompt at all |
| `MACOS_NOTARY_TEAM_ID` | (Apple Developer team id) | notarization |
| `MACOS_NOTARY_PASSWORD` | (app-specific password) | notarization |
| `WINDOWS_CERT_BASE64` | Authenticode-signed MSI | SmartScreen-friendly Windows |
| `WINDOWS_CERT_PASSWORD` | (password for the cert above) | signing |
| `CHOCO_API_KEY` | `choco install geocog` | Chocolatey publish |
| `WINGET_TOKEN` | `winget install Kartoza.geocog` | winget submission |
| `HOMEBREW_TAP_TOKEN` | `brew install --cask …` | Homebrew tap push |
| _(PyPI trusted publisher)_ | `pip install geocog` | PyPI (no secret; see below) |

## Code signing

### macOS — signing (`MACOS_CERT_*`, `MACOS_SIGN_IDENTITY`) and notarization (`MACOS_NOTARY_*`)

To sign and notarize you need a paid **Apple Developer Program** membership
(US$99/yr). The `build-dmg` job is fully turnkey — it imports your certificate
into a throwaway keychain on the runner, signs, and notarizes.

1. **Signing certificate** — in Xcode (or the Apple Developer portal) create a
   **Developer ID Application** certificate, export it as a `.p12`, then encode
   it for the secret:
   ```bash
   base64 -i DeveloperIDApplication.p12 | pbcopy   # → MACOS_CERT_BASE64
   ```
   - `MACOS_CERT_BASE64` — the base64 `.p12`.
   - `MACOS_CERT_PASSWORD` — the `.p12` export password.
   - `MACOS_SIGN_IDENTITY` — the certificate common name, e.g.
     `Developer ID Application: Kartoza (Pty) Ltd (TEAMID123)`.

   The workflow's **"Import signing certificate into a temporary keychain"**
   step creates a temp keychain, imports the `.p12`, and authorises `codesign`
   — no keychain setup needed on your side.

2. **Notarization** — create an **app-specific password** for your Apple ID
   (<https://appleid.apple.com> → Sign-In and Security), then set:
   - `MACOS_NOTARY_APPLE_ID` — your Apple ID email.
   - `MACOS_NOTARY_TEAM_ID` — your 10-character Developer Team ID.
   - `MACOS_NOTARY_PASSWORD` — the app-specific password.

   The job calls `xcrun notarytool submit … --wait` then `stapler staple` on the
   DMG. (These direct credentials work on ephemeral hosted runners; no
   pre-stored `notarytool` profile is needed.)

Without the `MACOS_CERT_*`/`MACOS_SIGN_IDENTITY` secrets the DMG ships unsigned
and users clear Gatekeeper with `xattr -d com.apple.quarantine`.

### Windows — `WINDOWS_CERT_BASE64` and `WINDOWS_CERT_PASSWORD`

Obtain a **code-signing certificate** from a CA (DigiCert, Sectigo, SSL.com …).
EV or OV certificates give the best SmartScreen reputation; cloud-HSM signing is
increasingly required — check with your CA.

```bash
# Export your cert+key as a PFX, then base64-encode it for the secret:
base64 -w0 geocog-codesign.pfx > cert.b64
```

- `WINDOWS_CERT_BASE64` — the contents of `cert.b64`.
- `WINDOWS_CERT_PASSWORD` — the PFX export password.

Without these, the MSI is unsigned and users click "More info → Run anyway".

## Package managers

### Chocolatey — `CHOCO_API_KEY`

1. Create an account at <https://community.chocolatey.org/> and register the
   `geocog` package id (first push seeds it; it then goes through moderation).
2. Copy your API key from your account page → **API Keys**.
3. Set `CHOCO_API_KEY`. The `publish-chocolatey` job packs the `.nupkg` from the
   released MSI and `choco push`es it.

### winget — `WINGET_TOKEN`

1. Fork [`microsoft/winget-pkgs`](https://github.com/microsoft/winget-pkgs).
2. Create a **fine-grained PAT** (or classic PAT with `public_repo`) that can
   push to your fork, and set it as `WINGET_TOKEN`.
3. **One-time seeding:** run `wingetcreate new` locally to create the initial
   `Kartoza.geocog` manifest PR. After that, the `publish-winget` job runs
   `wingetcreate update … --submit` on every release.

### Homebrew — `HOMEBREW_TAP_TOKEN`

1. Create the tap repository **`kartoza/homebrew-geocog`** (public).
2. Create a PAT that can push to it and set it as `HOMEBREW_TAP_TOKEN`.
3. The `publish-homebrew-cask` job renders `Casks/geocog.rb` from the released
   DMGs (per-arch checksums) and pushes it, enabling
   `brew install --cask kartoza/geocog/geocog`.

## PyPI (optional, no secret)

Publishing to PyPI uses a **Trusted Publisher** (OIDC) — no API token to store.
Configure it once at
`https://pypi.org/manage/project/geocog/settings/publishing/` for the
`kartoza/geocog` repo + `release.yml`, then uncomment the `publish-pypi` job in
the release workflow.

---

Made with 💗 by [Kartoza](https://kartoza.com) ·
[Donate!](https://github.com/sponsors/kartoza) ·
[GitHub](https://github.com/kartoza/geocog)
