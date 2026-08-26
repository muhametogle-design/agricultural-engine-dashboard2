"""Server-side disk cache for proxied spatial payloads (/static/data/cache/).

External GeoJSON is downloaded once, persisted to disk, and re-used across
restarts — so a cold start after a SWALIM/geoBoundaries outage still serves
the last good full-extent payload (disaster fallback) instead of nothing.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
CACHE_DIR = WEB_DIR / "static" / "data" / "cache"


def cache_path(key: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in key)
    return CACHE_DIR / f"{safe}.json"


def read_cache(key: str, ttl_s: int) -> dict[str, Any] | None:
    """Fresh cache entry or None (missing/expired/corrupt)."""
    path = cache_path(key)
    if not path.is_file():
        return None
    if time.time() - path.stat().st_mtime > ttl_s:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def read_stale(key: str) -> dict[str, Any] | None:
    """Last good payload regardless of age (outage fallback)."""
    path = cache_path(key)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def write_cache(key: str, payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(key)
    try:
        fd, tmp = tempfile.mkstemp(dir=CACHE_DIR, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        os.replace(tmp, path)
    except OSError:
        pass  # cache writes must never break request serving
