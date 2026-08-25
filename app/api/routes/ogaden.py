"""Ogaden / cross-border spatial proxy endpoints (Admin zones, upstream basins)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.config import HttpSettings
from app.services.http import create_async_client
from app.services.ogaden import get_ogaden_boundaries, get_ogaden_hydrology, get_ogaden_landcover

router = APIRouter(prefix="/ogaden", tags=["ogaden"])
WEB_DIR = Path(__file__).resolve().parents[2] / "web"


def _client(request: Request):
    client = getattr(request.app.state, "http_client", None)
    if client is not None:
        return client, False
    return create_async_client(HttpSettings()), True


@router.get("/boundaries")
async def ogaden_boundaries(request: Request, refresh: bool = Query(False)) -> JSONResponse:
    """Admin 2 zones (Jigjiga, Korahe, Doollo, Gode, ...) + Admin 3 woredas.

    Live geoBoundaries ETH/ADM2 filtered to the Somali Region, cached to
    /static/data/cache/, full extent, no feature limits."""
    client, owns = _client(request)
    try:
        data, source = await get_ogaden_boundaries(client, WEB_DIR)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ogaden boundaries unavailable: {exc}") from exc
    finally:
        if owns:
            await client.aclose()
    return JSONResponse(data, headers={
        "Cache-Control": "public, max-age=86400",
        "X-Ogaden-Source": source,
    })


@router.get("/hydrology")
async def ogaden_hydrology(request: Request, refresh: bool = Query(False)) -> JSONResponse:
    """Upstream Jubba (Ganale Dorya) & Shabelle (Webi Shabelle) networks + basins."""
    client, owns = _client(request)
    try:
        data, source = await get_ogaden_hydrology(client, WEB_DIR)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ogaden hydrology unavailable: {exc}") from exc
    finally:
        if owns:
            await client.aclose()
    return JSONResponse(data, headers={
        "Cache-Control": "public, max-age=86400",
        "X-Ogaden-Source": source,
    })


@router.get("/landcover")
async def ogaden_landcover(request: Request, refresh: bool = Query(False)) -> JSONResponse:
    """Cross-border land cover and soil categories (LAND_COVER / SOIL_TYPE)."""
    client, owns = _client(request)
    try:
        data, source = await get_ogaden_landcover(client, WEB_DIR)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ogaden land cover unavailable: {exc}") from exc
    finally:
        if owns:
            await client.aclose()
    return JSONResponse(data, headers={
        "Cache-Control": "public, max-age=86400",
        "X-Ogaden-Source": source,
    })
