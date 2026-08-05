# Contributing

geocog is open source (MIT) and contributions are very welcome — code, docs,
translations, and bug reports alike.

The canonical contributor guide lives at the repository root:
**[CONTRIBUTING.md](https://github.com/kartoza/geocog/blob/main/CONTRIBUTING.md)**.

## The short version

```bash
nix develop                         # reproducible dev shell (gdal + mc + python)
pytest                              # run the test suite
nix run .#geocog                    # launch the TUI
pre-commit run --all-files          # lint / format / licence / secrets
```

- **Open an issue first** using the bug or feature template. Features are framed
  as user stories with success criteria.
- **Write tests.** A feature isn't done without them; the engine is unit-tested
  and the TUI is exercised headlessly.
- **Conventional Commits** drive the version bump and `CHANGELOG.md`.
- **Update the docs** in the same PR — code and docs ship together.
- Reference issues with `fixes #NNN` so they close on merge.

See also the [Architecture](architecture.md) page for the module map, and the
project [Code of Conduct](https://github.com/kartoza/geocog/blob/main/CODE_OF_CONDUCT.md).

---

Made with 💗 by [Kartoza](https://kartoza.com) ·
[Donate!](https://github.com/sponsors/kartoza) ·
[GitHub](https://github.com/kartoza/geocog)
