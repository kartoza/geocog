#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# to_cog.sh — convert local raster(s) into Cloud Optimized GeoTIFF (COG).
#
# Step 1 of the workflow: take an ordinary GeoTIFF and rewrite it as a COG
# (internally tiled + overviews + compression) so it can be range-read
# efficiently once hosted in object storage and referenced from a VRT.
#
# Usage:
#   to_cog.sh INPUT [INPUT ...]
#
# For each INPUT (e.g. scene.tif) a sibling COG is written as scene.cog.tif.
# The compression predictor is chosen automatically from the pixel type.
#
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: to_cog.sh INPUT [INPUT ...]" >&2
  exit 2
fi

for IN in "$@"; do
  if [[ ! -f "$IN" ]]; then
    echo "!! skip: not a file: $IN" >&2
    continue
  fi

  # Derive OUT: strip a trailing .tif/.tiff, add .cog.tif
  base="${IN%.*}"
  OUT="${base}.cog.tif"

  # Pick a compression predictor from the band data type:
  #   floating point -> 3, integer/byte -> 2 (horizontal differencing).
  DTYPE="$(gdalinfo "$IN" 2>/dev/null | sed -n 's/.*Type=\([A-Za-z0-9]*\).*/\1/p' | head -n1)"
  case "$DTYPE" in
    Float32|Float64) PRED=3 ;;
    "")              PRED=2 ;;   # unknown; safe default
    *)               PRED=2 ;;
  esac

  echo "==> ${IN}  (type=${DTYPE:-?}, predictor=${PRED})"
  echo "    -> ${OUT}"

  gdal_translate "$IN" "$OUT" \
    -of COG \
    -co COMPRESS=DEFLATE \
    -co PREDICTOR="$PRED" \
    -co BLOCKSIZE=512 \
    -co OVERVIEW_RESAMPLING=AVERAGE \
    -co NUM_THREADS=ALL_CPUS \
    -co BIGTIFF=IF_SAFER

  # Confirm the COG driver actually laid it out as a COG.
  if gdalinfo "$OUT" 2>/dev/null | grep -qi 'LAYOUT=COG'; then
    echo "    ok: valid COG layout"
  else
    echo "    !! warning: COG layout marker not found — inspect ${OUT}" >&2
  fi
done

echo "==> Done. Next: upload the .cog.tif to object storage, then run make-vrt."
