# Administrator Guide

This page is for the people who run the object storage and GeoServer that
geocog publishes into: minting keys, preparing buckets, wiring up range-capable
endpoints, and backing up user connection data.

## 1. Prepare a bucket

geocog uploads COGs with the MinIO client (`mc`). Any S3-compatible store works
(MinIO, AWS S3, Ceph RGW). For a public, range-served mosaic you need:

- A bucket (e.g. `dgt`).
- Anonymous **download** access on the objects (so the VRT can read over
  `/vsicurl/` without credentials), or a presigned/`/vsis3/` path for private
  data.

## 2. Mint a scoped upload key

Prefer a **bucket-scoped** key over root credentials. geocog ships a helper that
writes the key straight into a `chmod 600` `.env` and never stores the root
credentials:

```bash
nix run .#make-key      # root creds used in-memory only, never written to disk
```

Alternatively, create an Access Key in the MinIO Console and paste it into the
TUI's connection manager (key `c`), which stores it in the encrypted vault.

!!! warning "Secrets hygiene"
    Credentials live only in a `chmod 600` `.env` (git-ignored) or the AES-GCM
    vault. geocog never writes secrets to `~/.mc` and never logs them. Never
    commit a `.env`.

## 3. Serve with HTTP Range — the critical bit

A COG is only efficient if the **endpoint** honours HTTP `Range` requests, so
GDAL reads individual tiles instead of the whole file. "COG" describes the
*file*; Range support is a property of the *server*. Both must be true.

For the Kartoza MinIO deployment, the range-capable host is the **S3 API**
endpoint:

```
https://api.minio.do.kartoza.com/<bucket>/<object>     # ✅ 206 + Content-Range
```

Do **not** use the Console "share" link
(`minio.do.kartoza.com/api/v1/download-shared-object/<blob>`) as a VRT source —
it streams the whole file per read and the signed blob expires. geocog rewrites
such links to the range-capable form automatically. See
[COGs & HTTP Range](cog-range-requests.md) for the full rationale.

## 4. Publish the VRT in GeoServer

The VRT geocog writes is a few-KB XML file holding only pointers to the cloud
COGs. Upload it to GeoServer as a **GDAL VRT** coverage store to publish the
whole mosaic as a single layer. (Full GeoServer automation is out of scope here —
see [kartoza/geotui](https://github.com/kartoza/geotui).)

## 5. Back up & restore connection data

User connections are stored in an AES-GCM vault:

```
~/.config/geocog/connections.vault
```

- **Back up:** copy the `connections.vault` file to secure storage. It is
  encrypted at rest (key derived from the master passphrase via PBKDF2, 600k
  iterations), so the file alone is useless without the passphrase.
- **Restore:** copy the file back to the same path on the target machine and
  unlock it with the original passphrase.
- **Rotate:** re-enter the passphrase in the connection manager to re-encrypt.

!!! note
    Keep the passphrase and the vault backup in **separate** locations. Losing
    the passphrase means the stored connections cannot be recovered — re-add
    them from your key source.

---

Made with 💗 by [Kartoza](https://kartoza.com) ·
[Donate!](https://github.com/sponsors/kartoza) ·
[GitHub](https://github.com/kartoza/geocog)
