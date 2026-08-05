# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
{
  description = "geocog — a small, fast TUI and toolkit that turns GeoTIFFs into cloud-hosted COGs and wraps them in a GeoServer-ready VRT";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        lib = pkgs.lib;

        # Runtime CLI tools the TUI/scripts shell out to.
        cliTools = [ pkgs.gdal pkgs.minio-client ];

        # Wrap an external script as a runnable app, injecting its runtime deps
        # onto PATH. Nothing is embedded in the flake and no store paths are
        # baked into the committed scripts; gdal/mc + CA certs are added here.
        mkApp = name: deps: script:
          pkgs.runCommand name
            { nativeBuildInputs = [ pkgs.makeWrapper ]; } ''
              install -Dm755 ${script} $out/bin/${name}
              wrapProgram $out/bin/${name} \
                --prefix PATH : ${lib.makeBinPath deps} \
                --set SSL_CERT_FILE ${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
            '';

        to-cog   = mkApp "to-cog"   [ pkgs.gdal ] ./scripts/to_cog.sh;
        make-vrt = mkApp "make-vrt" [ pkgs.gdal pkgs.coreutils ] ./scripts/make_vrt.sh;
        upload   = mkApp "upload"   [ pkgs.minio-client pkgs.coreutils ] ./scripts/upload_minio.sh;
        make-key = mkApp "make-key" [ pkgs.minio-client pkgs.coreutils pkgs.jq ] ./scripts/make_key.sh;
        docs     = mkApp "docs"     [ docsEnv ] ./scripts/docs.sh;

        # ---- Python: the geocog TUI -------------------------------------- #
        # Only the package sources go into the build (keep rasters/docs out).
        pysrc = lib.cleanSourceWith {
          src = ./.;
          filter = path: type:
            let rel = lib.removePrefix (toString ./. + "/") (toString path);
            in rel == "pyproject.toml"
               || rel == "README.md"
               || rel == "src" || lib.hasPrefix "src/" rel
               || rel == "tests" || lib.hasPrefix "tests/" rel;
        };

        geocog = pkgs.python3Packages.buildPythonApplication {
          pname = "geocog";
          version = "0.1.0";
          pyproject = true;
          src = pysrc;
          build-system = [ pkgs.python3Packages.setuptools ];
          dependencies = [ pkgs.python3Packages.textual pkgs.python3Packages.cryptography ];
          nativeCheckInputs = [ pkgs.python3Packages.pytestCheckHook ];
          # engine tests are pure; app tests only need textual (both offline).
          nativeBuildInputs = [ pkgs.makeWrapper ];
          postFixup = ''
            wrapProgram $out/bin/geocog \
              --prefix PATH : ${lib.makeBinPath cliTools} \
              --set SSL_CERT_FILE ${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
          '';
          meta = {
            description = "Small, fast TUI for the COG → MinIO → VRT workflow";
            mainProgram = "geocog";
          };
        };

        # Python env for the dev shell (TUI + tests + docs).
        docsEnv = pkgs.python3.withPackages (ps: [ ps.mkdocs-material ]);
        devPython = pkgs.python3.withPackages (ps: [
          ps.textual ps.cryptography ps.pytest ps.mkdocs-material
        ]);

        # Supply-chain / quality tooling used by pre-commit and CI.
        devTools = [
          pkgs.pre-commit   # git hook runner
          pkgs.reuse        # SPDX / REUSE licence linting
          pkgs.gitleaks     # secret scanning
          pkgs.ruff         # Python lint + format
        ];
      in {
        # `nix develop` -> gdal / mc / python(textual,pytest,mkdocs) + QA tools.
        devShells.default = pkgs.mkShell {
          packages = cliTools ++ devTools ++ [ pkgs.cacert devPython ];
          shellHook = ''
            export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
            export PYTHONPATH="$PWD/src:''${PYTHONPATH:-}"
            # Ensure the full-featured project python (textual/cryptography/pytest/
            # mkdocs) wins over the bare python pulled in by pre-commit/reuse.
            export PATH="${devPython}/bin:$PATH"
            echo "geocog dev shell — $(gdalinfo --version)"
            echo "  nix run .#geocog                   # the TUI (Convert/Upload/VRT)"
            echo "  nix run .#docs                     # serve the docs site"
            echo "  nix run .#docs -- build            # build the static site"
            echo "  pytest                             # run the test suite"
            echo "  pre-commit run --all-files         # lint / format / licence / secrets"
          '';
        };

        packages = {
          inherit to-cog make-vrt upload make-key docs geocog;
          default = geocog;
        };

        # nix run .#geocog                          # launch the TUI
        # nix run .#docs -- build                   # build the docs site
        # nix run .#make-key / .#to-cog / .#upload / .#make-vrt   (CLI steps)
        apps = {
          geocog   = { type = "app"; program = "${geocog}/bin/geocog"; };
          docs     = { type = "app"; program = "${docs}/bin/docs"; };
          make-key = { type = "app"; program = "${make-key}/bin/make-key"; };
          to-cog   = { type = "app"; program = "${to-cog}/bin/to-cog"; };
          upload   = { type = "app"; program = "${upload}/bin/upload"; };
          make-vrt = { type = "app"; program = "${make-vrt}/bin/make-vrt"; };
          default  = self.apps.${system}.geocog;
        };
      });
}
