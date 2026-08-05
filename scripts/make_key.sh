#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# make_key.sh — create a scoped MinIO service account (access key) for uploads.
#
# You authenticate ONCE with your MinIO root/admin credentials. Those are used
# only in memory (a throwaway mc config dir, wiped on exit) and are NEVER
# written to disk. The resulting scoped key — limited to read/write on one
# bucket — is printed and, by default, saved to .env for `nix run .#upload`.
#
# Usage:
#   make_key.sh [options]
#
# Options:
#   --name NAME     service-account display name        (default: cog-uploader)
#   --no-public     do NOT grant anonymous download on the bucket/prefix
#   --no-env        print the key but do not write it to .env
#   -h, --help      show this help
#
set -euo pipefail

ENV_FILE=".env"
DEFAULT_ENDPOINT="https://api.minio.do.kartoza.com"
NAME="cog-uploader"
SET_PUBLIC=1
WRITE_ENV=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --no-public) SET_PUBLIC=0; shift ;;
    --no-env) WRITE_ENV=0; shift ;;
    -h|--help) sed -n '3,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

# ----- gather connection + target (root creds are NOT persisted) ----------- #
read -rp "  S3 API endpoint [${DEFAULT_ENDPOINT}]: " ENDPOINT
ENDPOINT="${ENDPOINT:-$DEFAULT_ENDPOINT}"
read -rp "  Root / admin user: " ROOT_USER
read -rsp "  Root / admin password: " ROOT_PW; echo
read -rp "  Bucket [tim-deleteme]: " BUCKET
BUCKET="${BUCKET:-tim-deleteme}"
read -rp "  Public download prefix [dgt]: " PREFIX
PREFIX="${PREFIX:-dgt}"

if [[ -z "$ROOT_USER" || -z "$ROOT_PW" ]]; then
  echo "!! root user and password are required." >&2; exit 2
fi

# ----- throwaway workspace: mc config + policy, all wiped on exit ---------- #
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
MC="mc --config-dir $WORK"

POLICY="$WORK/policy.json"
cat > "$POLICY" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::${BUCKET}"] },
    { "Effect": "Allow",
      "Action": ["s3:PutObject","s3:GetObject","s3:DeleteObject",
                 "s3:AbortMultipartUpload","s3:ListMultipartUploadParts"],
      "Resource": ["arn:aws:s3:::${BUCKET}/*"] }
  ]
}
EOF

echo "==> Authenticating as admin ..."
$MC alias set admin "$ENDPOINT" "$ROOT_USER" "$ROOT_PW" >/dev/null
if ! $MC admin info admin >/dev/null 2>&1; then
  echo "!! could not reach/authenticate at ${ENDPOINT} with those credentials." >&2
  exit 1
fi

$MC mb --ignore-existing "admin/$BUCKET" >/dev/null 2>&1 || true

echo "==> Creating scoped service account '${NAME}' (bucket: ${BUCKET})"
OUT="$($MC admin user svcaccount add admin "$ROOT_USER" \
        --policy "$POLICY" --name "$NAME" --json)"
AK="$(printf '%s' "$OUT" | jq -r '.accessKey // .access_key // empty')"
SK="$(printf '%s' "$OUT" | jq -r '.secretKey // .secret_key // empty')"
if [[ -z "$AK" || -z "$SK" ]]; then
  echo "!! failed to parse the new key from mc output:" >&2
  printf '%s\n' "$OUT" >&2
  exit 1
fi

if [[ "$SET_PUBLIC" -eq 1 ]]; then
  DEST="admin/$BUCKET"; [[ -n "$PREFIX" ]] && DEST="$DEST/$PREFIX"
  echo "==> Granting anonymous download on ${DEST#admin/}"
  $MC anonymous set download "$DEST" >/dev/null
fi

# ----- save the SCOPED key (never the root creds) to .env ------------------ #
if [[ "$WRITE_ENV" -eq 1 ]]; then
  q() { printf "%s='%s'\n" "$1" "${2//\'/\'\\\'\'}"; }
  umask 177
  {
    echo "# MinIO scoped upload key for geocog — DO NOT COMMIT"
    q MINIO_ENDPOINT   "$ENDPOINT"
    q MINIO_ACCESS_KEY "$AK"
    q MINIO_SECRET_KEY "$SK"
    q MINIO_BUCKET     "$BUCKET"
    q MINIO_PREFIX     "$PREFIX"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

echo
echo "==> Scoped key created."
echo "    Access Key : ${AK}"
echo "    Secret Key : ${SK}"
if [[ "$WRITE_ENV" -eq 1 ]]; then
  echo "    Saved to   : ${ENV_FILE} (mode 600). Now: nix run .#upload -- dgt/*.cog.tif"
else
  echo "    (not saved) Paste these into: nix run .#upload"
fi
echo "    Revoke with: mc admin user svcaccount rm <admin-alias> ${AK}"
