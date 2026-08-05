# SPDX-FileCopyrightText: 2026 Kartoza (Pty) Ltd <info@kartoza.com>
# SPDX-License-Identifier: MIT
"""Tiny i18n string catalogue for geocog.

User-visible strings are looked up by key so translations can be added as
sibling ``<lang>.json`` files without touching call sites. English (``en``) is
the source-of-truth catalogue and the fallback for any missing key.
"""

from __future__ import annotations

import json
import os
from functools import cache
from pathlib import Path

_HERE = Path(__file__).parent
_DEFAULT_LANG = "en"


@cache
def _catalogue(lang: str) -> dict[str, str]:
    path = _HERE / f"{lang}.json"
    if not path.exists():
        path = _HERE / f"{_DEFAULT_LANG}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lang() -> str:
    """Resolve the active language from ``GEOCOG_LANG`` or ``LANG``."""
    raw = os.environ.get("GEOCOG_LANG") or os.environ.get("LANG", _DEFAULT_LANG)
    return raw.split(".")[0].split("_")[0].lower() or _DEFAULT_LANG


def t(key: str, /, **kwargs: object) -> str:
    """Translate ``key`` for the active language, falling back to English.

    Unknown keys return the key itself so nothing crashes on a missing string.
    ``kwargs`` are applied with :meth:`str.format` for interpolation.
    """
    cat = _catalogue(_lang())
    text = cat.get(key) or _catalogue(_DEFAULT_LANG).get(key, key)
    return text.format(**kwargs) if kwargs else text
