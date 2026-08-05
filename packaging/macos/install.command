#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# Double-click this file in the mounted geocog disk image to install the
# `geocog` command to /usr/local/bin.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="/usr/local/bin"

echo "Installing geocog to ${DEST} (you may be prompted for your password)…"
sudo mkdir -p "${DEST}"
sudo cp "${HERE}/geocog" "${DEST}/geocog"
sudo chmod 755 "${DEST}/geocog"
# Clear the quarantine flag so Gatekeeper doesn't block the unsigned binary.
sudo xattr -d com.apple.quarantine "${DEST}/geocog" 2>/dev/null || true

echo
echo "✅ Installed. Run:  geocog"
echo
echo "Note: geocog needs GDAL and the MinIO client (mc) on your PATH for"
echo "conversion/upload/VRT steps, e.g.:  brew install gdal minio-mc"
read -r -p "Press Return to close…" _
