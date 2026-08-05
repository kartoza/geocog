#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
#
# docs.sh — build or serve the geocog documentation site (Material for MkDocs).
#
# Usage:
#   docs.sh            # serve with live reload at http://127.0.0.1:8000
#   docs.sh build      # build the static site into ./site
#
set -euo pipefail
exec mkdocs "${@:-serve}"
