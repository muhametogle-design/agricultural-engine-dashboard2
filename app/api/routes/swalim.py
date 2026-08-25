"""Official FAO SWALIM spatial-layer proxy endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.swalim import LAYER_TYPES, get_swalim_layer

router = APIRouter(tags=["swalim"])
STATIC_DIR = Path(__file__).resolve().parents[2] / "web" / "swalim"


@router.get("/swalim/{layer_name}")
async def swalim_layer(layer_name: str, request: Request) -> JSONResponse:
    """Serve an allow-listed SWALIM layer with WFS retrieval and local fallback."""
    if layer_name not in LAYER_TYPES:
        raise HTTPException(status_code=404, detail={
            "message": "Unknown SWALIM layer",
            "available_layers": sorted(LAYER_TYPES),
        })
    try:
        data, source = await get_swalim_layer(
            layer_name, request.app.state.http_client, STATIC_DIR
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"SWALIM layer unavailable: {exc}") from exc
    return JSONResponse(data, headers={
        "Cache-Control": "public, max-age=3600",
        "X-SWALIM-Source": source,
    })
