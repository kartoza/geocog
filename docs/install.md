# Install

geocog shells out to **GDAL** (`gdal_translate`, `gdalbuildvrt`, `gdalinfo`) and
**MinIO client** (`mc`). The Nix flake bundles both; with pip you provide them.

## Nix (recommended)

The flake wraps geocog with GDAL and `mc` already on its PATH — nothing else to
install.

```bash
# run without cloning
nix run github:kartoza/geocog#geocog

# or in a clone
nix run .#geocog
```

If Nix complains about experimental features, enable them once in
`~/.config/nix/nix.conf`:

```
experimental-features = nix-command flakes
```

## pip

```bash
pip install geocog
```

Then make sure `gdal` and `mc` are available on your PATH (e.g. your distro's
`gdal-bin` package and the MinIO `mc` client). Launch with:

```bash
geocog
```

## Development shell

```bash
nix develop          # gdal + mc + python(textual, pytest, mkdocs) on PATH
pytest               # run the test suite
nix run .#geocog     # launch the TUI
nix run .#docs       # serve these docs with live reload
```

## The CLI tools

The same pipeline is available as standalone commands, handy for scripting:

| Command | Step |
|---------|------|
| `nix run .#make-key` | mint a scoped MinIO key into `.env` (server admins) |
| `nix run .#to-cog -- FILE…` | GeoTIFF → COG |
| `nix run .#upload -- FILE…` | upload to MinIO |
| `nix run .#make-vrt -- SOURCE…` | build a VRT from COGs / share links |

See the [CLI walkthrough](dgt-cog-to-vrt.md) for a full end-to-end example.
