"""Laboratory endpoints — HWSD v2.0 automatic soil baseline sampling."""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

router = APIRouter(tags=["laboratory"])


@router.get("/lab/hwsd/sample")
async def hwsd_sample(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
) -> dict:
    """Topsoil sample from the offline HWSD v2.0 raster.

    Always 200: ``available`` tells the client whether the dataset is mounted;
    ``sample`` is null when the point falls outside the grid or on a nodata cell.
    """
    svc = request.app.state.hwsd
    if not svc.available:
        return {"available": False,
                "reason": "HWSD dataset not mounted (AGRI_HWSD_RASTER unset)"}
    return {"available": True, "sample": svc.sample(lat=lat, lon=lon)}
