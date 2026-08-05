#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# make_vrt.sh — build ONE small GDAL VRT that references one or more
# (typically cloud-hosted) COGs and presents them as a single image.
#
# The VRT is a few KB of XML; it holds no pixel data, only pointers to the
# sources. Upload the resulting .vrt to GeoServer (GDAL VRT store) to publish
# the mosaic as one layer.
#
# Usage:
#   make_vrt.sh [-o OUTPUT.vrt] [-s] [SOURCE ...]
#
#   -s / --streaming  Wrap HTTP sources as /vsicurl_streaming/ instead of
#                     /vsicurl/. Use this when the endpoint does NOT honour
#                     HTTP Range requests (e.g. a MinIO Console share-proxy
#                     link): GDAL then reads the whole file sequentially.
#                     Fine for a quick test; unsuitable for GeoServer at scale.
#
#   SOURCE may be:
#     https://host/path.tif        -> wrapped as /vsicurl/https://...
#     a MinIO console share link    -> auto-rewritten to the range-capable S3
#       (…/download-shared-object/<blob>)  API URL (needs a public object)
#     /vsicurl/... /vsis3/... etc  -> used verbatim (GDAL virtual file system)
#     ./local/scene.cog.tif        -> resolved to an absolute path
#
#   With no SOURCE arguments the script prompts interactively, one source per
#   line, finishing on a blank line.
#
set -euo pipefail

OUT="mosaic.vrt"
STREAMING=0
SOURCES=()

# S3 API host used to rebuild MinIO console "share" links into range-capable
# URLs. Override for a different deployment.
API_ENDPOINT="${MINIO_API_ENDPOINT:-https://api.minio.do.kartoza.com}"

# ----- parse arguments ----------------------------------------------------- #
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output) OUT="$2"; shift 2 ;;
    -s|--streaming) STREAMING=1; shift ;;   # for HTTP endpoints without Range
    -h|--help)
      sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) SOURCES+=("$1"); shift ;;
  esac
done

# ----- interactive prompt when no sources were passed ---------------------- #
if [[ ${#SOURCES[@]} -eq 0 ]]; then
  echo "Enter one COG source per line (URL, /vsi… path, or local file)."
  echo "Press ENTER on an empty line when finished."
  while true; do
    printf "  cog> "
    IFS= read -r line || break
    [[ -z "$line" ]] && break
    SOURCES+=("$line")
  done
fi

if [[ ${#SOURCES[@]} -eq 0 ]]; then
  echo "!! no sources given; nothing to do." >&2
  exit 2
fi

# ----- normalise each source into something GDAL can open ------------------ #
# Rewrite a MinIO console share link
#   https://HOST/[oauth_callback/]api/v1/download-shared-object/<base64url-blob>
# into a range-capable S3 API URL. The blob base64url-decodes to the internal
# presigned URL http://127.0.0.1:9000/<bucket>/<key>?<sig>; we keep only the
# <bucket>/<key> and point it at the S3 API host (the signature is host-locked
# to 127.0.0.1 and cannot be reused, so this needs a public object or creds).
rewrite_share_link() {
  local url="$1" blob internal path
  blob="${url##*/download-shared-object/}"
  blob="${blob%%\?*}"                 # drop any trailing query on the outer URL
  blob="${blob//-/+}"; blob="${blob//_//}"   # base64url -> base64
  while (( ${#blob} % 4 )); do blob+='='; done
  internal="$(printf '%s' "$blob" | base64 -d 2>/dev/null)" || return 1
  path="${internal#*://}"             # strip scheme
  path="${path#*/}"                   # strip host[:port] -> bucket/key?query
  path="${path%%\?*}"                 # strip presign query
  [[ -n "$path" ]] || return 1
  printf '%s/%s' "${API_ENDPOINT%/}" "$path"
}

normalise() {
  local s="$1" api
  local http_vsi="/vsicurl/"
  [[ "$STREAMING" -eq 1 ]] && http_vsi="/vsicurl_streaming/"
  case "$s" in
    *"/download-shared-object/"*)
      if api="$(rewrite_share_link "$s")"; then
        echo "    (share link rewritten -> ${api})" >&2
        printf '%s%s' "$http_vsi" "$api"
      else
        echo "    !! could not decode share link; using verbatim (may not support Range)" >&2
        printf '%s%s' "$http_vsi" "$s"
      fi ;;
    http://*|https://*)      printf '%s%s' "$http_vsi" "$s" ;;
    /vsicurl/*|/vsis3/*|/vsigs/*|/vsiaz/*|/vsizip/*|/vsitar/*)
                             printf '%s' "$s" ;;
    *)
      if [[ -f "$s" ]]; then realpath "$s"; else printf '%s' "$s"; fi ;;
  esac
}

NORM=()
echo "==> Sources:"
for s in "${SOURCES[@]}"; do
  n="$(normalise "$s")"
  NORM+=("$n")
  echo "    - ${n%%\?*}"
done

# ----- /vsicurl tuning: many object stores don't answer HEAD ---------------- #
export GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR
export CPL_VSIL_CURL_USE_HEAD="${CPL_VSIL_CURL_USE_HEAD:-NO}"
export GDAL_HTTP_MAX_RETRY="${GDAL_HTTP_MAX_RETRY:-3}"
export GDAL_HTTP_RETRY_DELAY="${GDAL_HTTP_RETRY_DELAY:-2}"

# ----- build the VRT ------------------------------------------------------- #
echo "==> Building ${OUT}"
gdalbuildvrt -resolution highest "$OUT" "${NORM[@]}"

echo "==> Done: ${OUT}"
echo "    Preview:  gdalinfo ${OUT}"
echo "    Publish:  upload ${OUT} to GeoServer as a GDAL VRT coverage store."
