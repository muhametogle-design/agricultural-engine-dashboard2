"""Frontend-development server: full API without PostGIS/DEM dependencies.

Runs the real FastAPI app with the database pool stubbed out so the map
dashboard, SWALIM proxies and static assets can be exercised on a laptop:

    ./.venv/bin/python scripts/dev_serve.py            # http://0.0.0.0:8000
    ./.venv/uvicorn scripts.dev_serve:app --port 8000  # equivalent

Authenticated DB-backed endpoints will fail; the spatial proxy layer
(/api/v1/swalim/soil-ph, /api/v1/swalim/{layer}, pages and assets) works.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root

import uvicorn

import app.main as main_module


async def _no_pool(dsn: str = "", **_: object) -> None:
    """Stand-in for asyncpg pool creation (no database in dev mode)."""
    return None


main_module.create_pool = _no_pool  # type: ignore[assignment]

app = main_module.create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
