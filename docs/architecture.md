# Architecture

geocog is deliberately small: a pure-Python **engine** that shells out to proven
CLI tools, and a thin **Textual** UI on top.

```
src/geocog/
├── engine.py    # COG/VRT pipeline — no Textual import, fully unit-tested
├── vault.py     # AES-GCM encrypted connection vault (PBKDF2)
├── s3.py        # mc-driven bucket listing / upload (pure ls parser)
├── browser.py   # local file/folder browser widget (FileBrowser)
├── s3tree.py    # lazy S3 tree widget (connections → buckets → objects)
├── screens.py   # modal dialogs: passphrase, connections, VRT name
├── app.py       # dual-pane App: 3 modes, threaded/async workers
├── app.tcss     # Kartoza-brand stylesheet
└── __main__.py  # python -m geocog
```

## Engine

`engine.py` has **no UI dependency**, so it is testable and reusable as a library:

- `discover_rasters` / `discover_cogs` — scan a folder
- `to_cog` — `gdal_translate -of COG` with a type-aware predictor
- `rewrite_share_link` / `normalise_source` — MinIO share-link → range-capable URL
- `build_vrt` — `gdalbuildvrt` over normalised sources
- `MinioConfig` — load/save the shared `.env` (POSIX-quoted, `chmod 600`)
- `mc_upload` — upload via a throwaway `mc` config dir; returns object URLs

Every external command runs through one `_run` helper that streams output to a
callback and raises `EngineError` on failure. The command line is never logged,
so secrets in argv are never echoed.

## App

`app.py` maps each pipeline step to a Textual `TabPane`. Long-running work
(convert / upload / build) runs in `@work(thread=True)` workers that marshal log
lines back to the UI with `call_from_thread`, so the interface never blocks.

The same tools power the [CLI scripts](https://github.com/kartoza/geocog/tree/main/scripts),
so behaviour is identical whether you use the TUI or the `nix run .#…` commands.

## Testing

```bash
pytest
```

- `tests/test_engine.py` — share-link rewriting, source normalisation, `.env`
  round-trip and permissions, discovery. No network, no gdal/mc.
- `tests/test_app.py` — boots the app headless with Textual's `run_test`,
  exercises tab switching and the “add uploaded URLs” action.

The Nix build (`nix build .#geocog`) runs the suite in-sandbox.

## Packaging

- `pyproject.toml` — `pip install geocog`, entry point `geocog`.
- `flake.nix` — `buildPythonApplication` wrapped so GDAL + `mc` are on PATH;
  exposed as `nix run .#geocog`.

---

Made with 💗 by [Kartoza](https://kartoza.com) · Donate · [GitHub](https://github.com/kartoza/geocog)
