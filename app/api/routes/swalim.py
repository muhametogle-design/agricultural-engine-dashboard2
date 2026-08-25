"""Official FAO SWALIM spatial-layer proxy endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.config import HttpSettings
from app.services.http import create_async_client
from app.services.swalim import LAYER_TYPES, get_swalim_layer
from app.services.swalim_soil import get_swalim_soil_ph

router = APIRouter(tags=["swalim"])
STATIC_DIR = Path(__file__).resolve().parents[2] / "web" / "swalim"
SOIL_SNAPSHOT = STATIC_DIR.parent / "soil_data.geojson"


@router.get("/swalim/soil-ph")
async def swalim_soil_ph(
    request: Request,
    refresh: bool = Query(False, description="Ignore the server-side cache and re-query the official WFS"),
) -> JSONResponse:
    """Somalia Soil pH Map: live official FAO SWALIM WFS polygons, harmonized
    into clean GeoJSON with the portal soil-reaction color scheme.

    The proxy fetch runs server-side (browser CORS never applies), is cached
    in-process for one hour, and degrades to the packaged snapshot when the
    SWALIM service is unreachable. Provenance is disclosed via X-SWALIM-Source
    and the FeatureCollection metadata block.
    """
    owns_client = False
    client = getattr(request.app.state, "http_client", None)
    if client is None:  # e.g. lifespan not run (static/test deployments)
        client = create_async_client(HttpSettings())
        owns_client = True
    try:
        data, source = await get_swalim_soil_ph(client, SOIL_SNAPSHOT, force_refresh=refresh)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SWALIM soil pH layer unavailable: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()
    return JSONResponse(data, headers={
        "Cache-Control": "public, max-age=3600",
        "X-SWALIM-Source": source,
    })


@router.get("/swalim/{layer_name}")
async def swalim_layer(layer_name: str, request: Request) -> JSONResponse:
    """Serve an allow-listed SWALIM layer with WFS retrieval and local fallback."""
    if layer_name not in LAYER_TYPES:
        raise HTTPException(status_code=404, detail={
            "message": "Unknown SWALIM layer",
            "available_layers": sorted(LAYER_TYPES),
        })
    owns_client = False
    client = getattr(request.app.state, "http_client", None)
    if client is None:  # lifespan not run (bare ASGI / test deployments)
        client = create_async_client(HttpSettings())
        owns_client = True
    try:
        data, source = await get_swalim_layer(layer_name, client, STATIC_DIR)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SWALIM layer unavailable: {exc}") from exc
    finally:
        if owns_client:
            await client.aclose()
    return JSONResponse(data, headers={
        "Cache-Control": "public, max-age=3600",
        "X-SWALIM-Source": source,
    })
