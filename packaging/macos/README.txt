geocog for macOS
================

To install:
  1. Double-click "install.command" to copy `geocog` into /usr/local/bin.
     (If macOS blocks it, right-click → Open, or run:
      xattr -d com.apple.quarantine install.command)
  2. Open Terminal and run:  geocog

Or install manually:
  chmod +x geocog
  sudo cp geocog /usr/local/bin/geocog
  xattr -d com.apple.quarantine /usr/local/bin/geocog

Runtime prerequisites (not bundled):
  geocog shells out to GDAL and the MinIO client for the actual raster work:
      brew install gdal minio-mc

The fully self-contained option is Nix:
      nix run github:kartoza/geocog#geocog

Made with love by Kartoza — https://kartoza.com
