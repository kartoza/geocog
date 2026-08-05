# geocog

**COG → MinIO → VRT.** A small, fast, Midnight-Commander-style **dual-pane** TUI —
and a matching set of CLI tools — that turn ordinary GeoTIFFs into cloud-hosted
mosaics you can publish as a single GeoServer layer.

![geocog in COG-creation mode](img/geocog-mode1.svg){ .shadow }

## What it does

Two panes, three modes — switch with **F2 / F3 / F4**, act with **F5**:

1. **COG creation** — left pane: local rasters; right pane: an output folder.
   Select rasters, F5 writes COGs into the right-hand folder.
2. **COG upload** — left pane: local COGs; right pane: a tree of your registered
   S3 buckets. Highlight a bucket/folder, F5 uploads there.
3. **VRT creation** — left pane: a destination folder; right pane: a tree of
   cloud COGs (multi-select). Pick COGs, F5, name the VRT — it's written locally,
   referencing the cloud objects as a single image.

Bucket credentials live in an **encrypted vault** (AES-GCM, one master
passphrase), managed from the built-in **connection manager** (`c`).

## Install

=== "Nix (recommended)"

    ```bash
    nix run github:kartoza/geocog#geocog     # or, in a clone:
    nix run .#geocog
    ```

=== "pip"

    ```bash
    pip install geocog        # needs gdal + mc on PATH
    geocog
    ```

## The pipeline

The whole point is **range reads**: a COG served from a range-capable endpoint is
read tile-by-tile, not streamed whole. geocog always targets the S3 API host.

![COG over HTTP Range data flow](cog-range-flow.svg){ .shadow }

## Start here

<div class="grid cards" markdown>

- :material-download: **[Install](install.md)** — nix, pip, or dev shell
- :material-console: **[The TUI](tui.md)** — screens, keys, workflow
- :material-map: **[CLI walkthrough](dgt-cog-to-vrt.md)** — DGT tiles, end to end
- :material-server-network: **[Administrator guide](administrator.md)** — buckets, keys, publishing
- :material-lightbulb: **[COGs & HTTP Range](cog-range-requests.md)** — the why
- :material-code-braces: **[Architecture](architecture.md)** — how it's built

</div>

!!! tip "Offline reading"
    The whole manual is also available as a single
    **[PDF](https://kartoza.github.io/geocog/pdf/geocog.pdf)**, rebuilt on every
    release.

---

Made with 💗 by [Kartoza](https://kartoza.com) ·
[Donate!](https://github.com/sponsors/kartoza) ·
[GitHub](https://github.com/kartoza/geocog)
