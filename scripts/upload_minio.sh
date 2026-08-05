#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# upload_minio.sh — upload file(s) to MinIO/S3 and print range-capable URLs.
#
# Credentials are read from ./.env (created on first run, chmod 600, gitignored)
# and any missing value is prompted for. mc is configured in a throwaway config
# dir so the secret is never written to ~/.mc.
#
# Usage:
#   upload_minio.sh [options] FILE [FILE ...]
#
# Options:
#   -b BUCKET     target bucket (overrides .env MINIO_BUCKET)
#   -p PREFIX     key prefix / "folder" (overrides .env MINIO_PREFIX)
#   --public      grant anonymous download on the target prefix (needed for
#                 credential-free /vsicurl access from the VRT)
#   -r, --reconfigure   re-prompt for every credential even if already set
#   -h, --help    show this help
#
set -euo pipefail

ENV_FILE=".env"
ALIAS="minio_upload"
DEFAULT_ENDPOINT="https://api.minio.do.kartoza.com"

PUBLIC=0
RECONFIG=0
BUCKET_OPT=""
PREFIX_OPT=""
FILES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -b) BUCKET_OPT="$2"; shift 2 ;;
    -p) PREFIX_OPT="$2"; shift 2 ;;
    --public) PUBLIC=1; shift ;;
    -r|--reconfigure) RECONFIG=1; shift ;;
    -h|--help) sed -n '3,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) FILES+=("$1"); shift ;;
  esac
done

# ----- load any previously saved values ------------------------------------ #
: "${MINIO_ENDPOINT:=}" "${MINIO_ACCESS_KEY:=}" "${MINIO_SECRET_KEY:=}"
: "${MINIO_BUCKET:=}"   "${MINIO_PREFIX:=}"
if [[ -f "$ENV_FILE" ]]; then
  set -a; # shellcheck disable=SC1090
  . "$ENV_FILE"; set +a
fi
[[ -n "$BUCKET_OPT" ]] && MINIO_BUCKET="$BUCKET_OPT"
[[ -n "$PREFIX_OPT" ]] && MINIO_PREFIX="$PREFIX_OPT"

# ----- prompt for anything still missing ----------------------------------- #
# prompt VAR "message" "default" [secret]
prompt() {
  local var="$1" msg="$2" def="${3:-}" secret="${4:-}" cur="${!1:-}" input
  # already set and not reconfiguring -> keep silently
  if [[ -n "$cur" && "$RECONFIG" -eq 0 ]]; then return; fi
  if [[ "$secret" == "secret" ]]; then
    local hint=""; [[ -n "$cur" ]] && hint=" [keep existing]"
    read -rsp "  ${msg}${hint}: " input; echo
    [[ -z "$input" ]] && input="$cur"
  else
    read -rp "  ${msg} [${cur:-$def}]: " input
    [[ -z "$input" ]] && input="${cur:-$def}"
  fi
  printf -v "$var" '%s' "$input"
}

echo "== MinIO connection (stored in ${ENV_FILE}, mode 600) =="
prompt MINIO_ENDPOINT   "S3 API endpoint" "$DEFAULT_ENDPOINT"
prompt MINIO_ACCESS_KEY "Access key"      ""
prompt MINIO_SECRET_KEY "Secret key"      "" secret
prompt MINIO_BUCKET     "Bucket"          "tim-deleteme"
prompt MINIO_PREFIX     "Key prefix"      ""

if [[ -z "$MINIO_ACCESS_KEY" || -z "$MINIO_SECRET_KEY" ]]; then
  echo "!! access key and secret key are required." >&2; exit 2
fi

# ----- persist to .env (single-quoted, chmod 600) -------------------------- #
q() { printf "%s='%s'\n" "$1" "${2//\'/\'\\\'\'}"; }
umask 177
{
  echo "# MinIO upload credentials for geocog — DO NOT COMMIT"
  q MINIO_ENDPOINT   "$MINIO_ENDPOINT"
  q MINIO_ACCESS_KEY "$MINIO_ACCESS_KEY"
  q MINIO_SECRET_KEY "$MINIO_SECRET_KEY"
  q MINIO_BUCKET     "$MINIO_BUCKET"
  q MINIO_PREFIX     "$MINIO_PREFIX"
} > "$ENV_FILE"
chmod 600 "$ENV_FILE"

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "==> Credentials saved to ${ENV_FILE}. No files given — nothing uploaded."
  exit 0
fi

# ----- upload via mc using a throwaway config dir -------------------------- #
MCDIR="$(mktemp -d)"
trap 'rm -rf "$MCDIR"' EXIT
mc="mc --config-dir $MCDIR"

$mc alias set "$ALIAS" "$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" >/dev/null
$mc mb --ignore-existing "$ALIAS/$MINIO_BUCKET" >/dev/null 2>&1 || true

DEST="$ALIAS/$MINIO_BUCKET"
[[ -n "$MINIO_PREFIX" ]] && DEST="$DEST/$MINIO_PREFIX"

echo "==> Uploading ${#FILES[@]} file(s) to ${MINIO_BUCKET}/${MINIO_PREFIX}"
$mc cp "${FILES[@]}" "$DEST/"

if [[ "$PUBLIC" -eq 1 ]]; then
  echo "==> Granting anonymous download on ${DEST#"$ALIAS"/}"
  $mc anonymous set download "$DEST" >/dev/null
fi

# ----- print the range-capable URLs, ready for make-vrt -------------------- #
BASE="${MINIO_ENDPOINT%/}/${MINIO_BUCKET}"
[[ -n "$MINIO_PREFIX" ]] && BASE="${BASE}/${MINIO_PREFIX}"
echo "==> Done. Source URLs:"
for f in "${FILES[@]}"; do
  echo "    ${BASE}/$(basename "$f")"
done
echo
if [[ "$PUBLIC" -eq 1 ]]; then
  echo "These are public + range-capable — feed them straight to make-vrt."
else
  echo "Bucket not made public (use --public). For private access, generate a"
  echo "presigned URL:  mc share download ${MINIO_BUCKET}/${MINIO_PREFIX}/<file>"
fi
