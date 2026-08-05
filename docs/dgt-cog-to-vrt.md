# DGT tiles → COG → MinIO → VRT → GeoServer

A hands-on walkthrough using the five Portuguese **DGT MDT** (50 cm Digital
Terrain Model) tiles in `dgt/`. We convert them to Cloud Optimized GeoTIFFs,
upload them to MinIO, expose range-capable URLs, and wrap them in a single
small VRT that GeoServer can publish as one seamless coverage.

Every command uses this folder's Nix flake — no globally installed GDAL, no
ad-hoc `nix shell`.

## The data

| Tile | Easting (m) | Northing (m) | Size | Type | NoData |
|------|-------------|--------------|------|------|--------|
| `MDT-50cm-258273-…` | 58000–59000 | −27000…−28000 | 2000² | Float32 | −999 |
| `MDT-50cm-263273-…` | 63000–64000 | −27000…−28000 | 2000² | Float32 | −999 |
| `MDT-50cm-260271-…` | 60000–61000 | −29000…−30000 | 2000² | Float32 | −999 |
| `MDT-50cm-258269-…` | 58000–59000 | −31000…−32000 | 2000² | Float32 | −999 |
| `MDT-50cm-263269-…` | 63000–64000 | −31000…−32000 | 2000² | Float32 | −999 |

All share CRS **ETRS89 / Portugal TM06 (EPSG:3763)** — required for a VRT
mosaic. They are **not contiguous**: four corners plus a centre tile, with
empty space between them (a quincunx). The VRT stitches them into one image and
fills the gaps with NoData.

```
        E58  E59  E60  E61  E62  E63      (easting, km →)
N-27   [273] .    .    .    .   [273]
N-28    .    .    .    .    .    .
N-29    .    .   [271] .    .    .
N-30    .    .    .    .    .    .
N-31   [269] .    .    .    .   [269]      (↓ northing)
```

Resulting mosaic: **12000 × 10000 px, 6 km × 5 km**, from a ~3 KB VRT.

## Prerequisites

Nix with flakes enabled. If commands complain about experimental features, add
to `~/.config/nix/nix.conf`:

```
experimental-features = nix-command flakes
```

## Step 0 — Get an access key

`mc`/uploads need a **static access key + secret**. How you obtain one depends
on how you log into MinIO.

### If you sign in via Kartoza IdP (OIDC / SSO)

You have no root password — the IdP only hands you a *temporary* STS token
(the expiring `…-Security-Token` you see inside share links), which `mc` can't
use. Instead, mint a persistent key from the Console UI:

1. Log into **https://minio.do.kartoza.com** via Kartoza IdP.
2. Left nav → **Access Keys** → **Create access key**.
3. *(Optional, recommended)* toggle a custom policy and paste
   [`scripts/minio-upload-policy.json`](https://github.com/kartoza/geocog/blob/main/scripts/minio-upload-policy.json)
   to scope the key to the `tim-deleteme` bucket. You can only *narrow* your
   IdP-mapped policy, never exceed it.
4. **Create**, then copy the **Access Key** and **Secret Key** (secret shown
   once). `nix run .#upload` will prompt for them; the endpoint stays
   `https://api.minio.do.kartoza.com`.

> Making the bucket public (`--public` / `mc anonymous set download`) needs
> `s3:PutBucketPolicy`. If your IdP policy lacks it, either ask an admin to set
> it once, or skip public and hand `make-vrt` **presigned** URLs instead:
> `mc share download --expire 168h <alias>/tim-deleteme/dgt/<file>.cog.tif`.

### If you administer the server (root / password login)

Mint a bucket-scoped service account straight into `.env` in one shot — root
creds are used in memory only and never stored:

```bash
nix run .#make-key            # prompts for endpoint / root user+pass / bucket / prefix
```

This creates a service account limited to read/write on the bucket, optionally
grants anonymous download on the prefix, and writes the **scoped** key to
`.env`. (This path needs a root/password admin login — it does **not** work with
an OIDC-only account; use the Console route above for that.)

## Step 1 — Convert the tiles to COG

```bash
nix run .#to-cog -- dgt/*.tiff
```

For each `dgt/NAME.tiff` this writes `dgt/NAME.cog.tif`: internally tiled
(512 px blocks), overviews added, DEFLATE compression. The predictor is chosen
automatically from the pixel type (here **3**, because the data is Float32) and
the `-999` NoData value is carried through. Each file is checked for a valid
COG layout.

## Step 2 — Upload to MinIO

The `upload` helper prompts for your MinIO credentials **once**, stores them in
a `0600` `.env` file (which is **git-ignored *and* Claude-ignored** — see
`.claude/settings.json`), and pushes the files with `mc`. The secret is only
kept in `.env`; `mc` runs against a throwaway config dir, so nothing leaks into
`~/.mc`.

```bash
nix run .#upload -- --public -p dgt dgt/*.cog.tif
```

You'll be asked for:

```
  S3 API endpoint [https://api.minio.do.kartoza.com]:
  Access key: ……
  Secret key: ……            (hidden)
  Bucket [tim-deleteme]:
  Key prefix [dgt]:
```

- `--public` grants **anonymous download** on the `dgt/` prefix, so the VRT can
  read the COGs over `/vsicurl/` without credentials. Omit it for a private
  bucket (see Step 3).
- On success it prints the ready-to-use source URLs.

Re-run any time; saved values are reused. Use `-r` to re-enter credentials.

## Step 3 — Share: get range-capable URLs

A COG is only efficient if the **server honours HTTP `Range`**. On Kartoza's
MinIO:

- ✅ **Use** `https://api.minio.do.kartoza.com/<bucket>/<key>` — the S3 API host,
  which returns `206 Partial Content`. This is what `--public` exposes.
- ❌ **Do not use** `minio.do.kartoza.com/.../download-shared-object/<blob>` —
  the Console share link streams the whole file per read (no Range) and expires.

**Public bucket** (used `--public` above): the URLs are simply

```
https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT-50cm-258273-04-2024_v01.cog.tif
… (one per tile)
```

**Private bucket**: mint a presigned URL against the S3 API host, or use
`/vsis3/` with credentials from `.env`:

```bash
# presigned (valid for a week)
mc share download --expire 168h minio_upload/tim-deleteme/dgt/<file>.cog.tif

# or /vsis3 at VRT-build / GeoServer time
export AWS_S3_ENDPOINT=api.minio.do.kartoza.com AWS_HTTPS=YES AWS_VIRTUAL_HOSTING=FALSE
export AWS_ACCESS_KEY_ID=…  AWS_SECRET_ACCESS_KEY=…
```

## Step 4 — Build one VRT against the cloud COGs

Pass all five URLs (or run with no args and paste one per line):

```bash
nix run .#make-vrt -- -o dgt_mdt_cloud.vrt \
  https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT-50cm-258273-04-2024_v01.cog.tif \
  https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT-50cm-263273-04-2024_v01.cog.tif \
  https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT-50cm-260271-04-2024_v01.cog.tif \
  https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT-50cm-258269-04-2024_v01.cog.tif \
  https://api.minio.do.kartoza.com/tim-deleteme/dgt/MDT-50cm-263269-04-2024_v01.cog.tif
```

HTTP sources are wrapped as `/vsicurl/…` and written with `relativeToVRT="0"`
(absolute), which is what GeoServer needs for remote objects. The output is a
few-KB XML file holding only pointers.

> **Pasting MinIO share links directly.** You can also hand `make-vrt` a raw
> console share link (`https://minio.do.kartoza.com/…/download-shared-object/<blob>`).
> It base64-decodes the blob, extracts `<bucket>/<key>`, and rewrites it to the
> range-capable `https://api.minio.do.kartoza.com/<bucket>/<key>` automatically.
> This only works for **public** objects — the share link's own signature is
> locked to `127.0.0.1` and can't be reused, so a private object still needs a
> presigned-from-`api` URL or `/vsis3/` credentials. (Override the target host
> with `MINIO_API_ENDPOINT=…` if your deployment differs.)

Check it (reads only tile headers/overviews, not the whole rasters):

```bash
nix develop --command gdalinfo dgt_mdt_cloud.vrt
```

You should see `Size is 12000, 10000`, `EPSG:3763`, `NoData Value=-999`, and
five sources placed at their true positions.

## Step 5 — Publish in GeoServer

1. **Store** → *Add new store* → **GDAL VRT** (raster). Point it at
   `dgt_mdt_cloud.vrt` (upload the file to the GeoServer data dir, or a path it
   can read).
2. Publish the layer; set the declared SRS to **EPSG:3763**.
3. For the elevation to render, set a style / min-max or a raster colour ramp;
   NoData `-999` renders transparent.
4. GeoServer will range-read tiles straight from MinIO on demand.

> Tip: enable GDAL support in GeoServer (the `gdal` community extension /
> `imageio-ext` with the VRT and COG drivers) so it can open `/vsicurl/`
> sources.

## Gotchas

- **Same CRS required.** `gdalbuildvrt` will not reproject; mixed projections
  must be warped first (`gdal_translate`/`gdalwarp`) before the VRT step.
- **Same band count & type.** These tiles are all single-band Float32 — fine.
- **Range endpoint.** Always the `api.` host; never the console share link.
- **Adding tiles later.** Upload the new COG(s), then re-run `make-vrt` with the
  full URL list. The VRT extent grows to include them automatically.

---

Made with 💗 by [Kartoza](https://kartoza.com) | Donate! | GitHub
