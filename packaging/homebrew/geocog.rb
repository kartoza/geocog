# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# Homebrew cask for geocog. Version and per-arch SHA256 checksums are updated by
# the release workflow (or by hand) and the file is pushed to the tap
# `kartoza/homebrew-geocog`, enabling:
#
#     brew install --cask kartoza/geocog/geocog
#
cask "geocog" do
  version "__VERSION__"

  on_arm do
    sha256 "__SHA256_ARM64__"
    url "https://github.com/kartoza/geocog/releases/download/v#{version}/geocog-#{version}-macos-arm64.dmg"
  end
  on_intel do
    sha256 "__SHA256_AMD64__"
    url "https://github.com/kartoza/geocog/releases/download/v#{version}/geocog-#{version}-macos-amd64.dmg"
  end

  name "geocog"
  desc "TUI + toolkit for the GeoTIFF → COG → object storage → GeoServer VRT workflow"
  homepage "https://github.com/kartoza/geocog"

  depends_on formula: "gdal"

  binary "geocog"

  caveats <<~EOS
    geocog also uses the MinIO client (mc) for uploads:
      brew install minio-mc
  EOS
end
