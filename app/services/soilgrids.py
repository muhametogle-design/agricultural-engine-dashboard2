"""ISRIC SoilGrids v2.0 client.

Upstream of the partner draft `GISDataIngestionService.fetch_soil_data`.
Production changes:
  * missing values (SoilGrids returns literal None over water/no-data) are
    handled per depth band instead of crashing the whole parse;
  * the 0-30 cm profile is a THICKNESS-WEIGHTED mean (5/10/15 cm), not just
    the 0-5 cm top band;
  * conversion factors are read from the payload's `unit_measure.d_factor`,
    falling back to the ISRIC-documented constants;
  * polygons are supported by stratified interior sampling + aggregation
    (the v2 API itself is point-only).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
import numpy as np
from shapely.geometry import Point

from app.config import Settings
from app.core.errors import NoCoverageError
from app.core.logging import get_logger
from app.core.spatial import (
    geom_from_geojson,
    sample_points_in_polygon,
    to_utm,
    utm_epsg,
    utm_point_to_wgs84,
)
from app.services.http import get_json

log = get_logger(__name__)

# ISRIC-documented fallbacks: mapped value = raw / d_factor (applied to reach
# the schema's storage unit: pH, %, g/kg, mmol(c)/kg).
DEFAULT_D_FACTORS: dict[str, float] = {
    "phh2o": 10.0,    # pH x10      -> pH
    "clay": 10.0,     # g/kg        -> %
    "sand": 10.0,     # g/kg        -> %
    "silt": 10.0,     # g/kg        -> %
    "soc": 10.0,      # dg/kg       -> g/kg
    "nitrogen": 100.0,  # cg/kg     -> g/kg
    "cec": 1.0,       # mmol(c)/kg  -> mmol(c)/kg
}

# Storage column per SoilGrids property name
COLUMN_MAP = {
    "phh2o": "ph_water",
    "clay": "clay_percentage",
    "sand": "sand_percentage",
    "silt": "silt_percentage",
    "soc": "soil_organic_carbon",
    "nitrogen": "nitrogen_content",
    "cec": "cec_mmolc_kg",
}


@dataclass
class SoilProfile:
    values: dict[str, float | None]  # keyed by storage column name
    samples_used: int
    raw: dict[str, Any] = field(default_factory=dict)


def _extract_point_profile(payload: dict, settings: Settings) -> dict[str, float | None]:
    """Thickness-weighted 0-30 cm profile from one SoilGrids response."""
    layers = payload.get("properties", {}).get("layers", [])
    by_name = {layer.get("name"): layer for layer in layers}
    profile: dict[str, float | None] = {}

    for prop in settings.soil.properties:
        column = COLUMN_MAP.get(prop)
        if column is None:
            continue
        layer = by_name.get(prop)
        if not layer:
            profile[column] = None
            continue
        d_factor = float(
            (layer.get("unit_measure") or {}).get("d_factor")
            or DEFAULT_D_FACTORS.get(prop, 1.0)
        )
        depths = {d.get("label"): d for d in layer.get("depths", [])}
        weighted_sum = 0.0
        weight_total = 0.0
        for label, thickness in zip(settings.soil.depths, settings.soil.depth_thickness_cm):
            entry = depths.get(label)
            raw_val = ((entry or {}).get("values") or {}).get("mean")
            if raw_val is None:
                continue
            weighted_sum += (float(raw_val) / d_factor) * thickness
            weight_total += thickness
        profile[column] = round(weighted_sum / weight_total, 3) if weight_total > 0 else None
    return profile


async def fetch_soil_point(
    client: httpx.AsyncClient, settings: Settings, lat: float, lon: float
) -> tuple[dict[str, float | None], dict]:
    """Point query - the building block. (lat, lon) in EPSG:4326."""
    payload = await get_json(
        client,
        settings.soilgrids_base_url,
        params={
            "lon": lon,
            "lat": lat,
            "property": settings.soil.properties,
            "depth": settings.soil.depths,
            "value": "mean",
        },
        settings=settings.http,
    )
    return _extract_point_profile(payload, settings), payload


async def fetch_soil_polygon(
    client: httpx.AsyncClient, settings: Settings, boundary_geojson: dict
) -> SoilProfile:
    """Polygon aggregation via stratified interior sampling + mean.

    Coverage rule: at least one sample must return data, otherwise the field
    is outside SoilGrids coverage and NoCoverageError is raised.
    """
    boundary = geom_from_geojson(boundary_geojson)
    centroid = boundary.centroid
    epsg = utm_epsg(centroid.x, centroid.y)
    boundary_utm = to_utm(boundary, epsg)

    n = settings.soil.polygon_sample_points
    pts_utm = sample_points_in_polygon(boundary_utm, n)
    latlons = [utm_point_to_wgs84(float(x), float(y), epsg) for x, y in pts_utm]

    sem = asyncio.Semaphore(settings.http.max_concurrency)

    async def _sample(lon: float, lat: float):
        async with sem:
            try:
                profile, _ = await fetch_soil_point(client, settings, lat, lon)
                return profile
            except Exception as exc:  # tolerate per-point failure
                log.warning("soilgrids sample failed at (%.5f, %.5f): %s", lat, lon, exc)
                return None

    results = await asyncio.gather(*(_sample(lon, lat) for lon, lat in latlons))
    valid = [r for r in results if r is not None]
    if not valid:
        raise NoCoverageError("SoilGrids returned no data for any sample point in this field")

    columns = list(COLUMN_MAP.values())
    aggregated: dict[str, float | None] = {}
    for col in columns:
        vals = [v[col] for v in valid if v.get(col) is not None]
        aggregated[col] = round(float(np.mean(vals)), 3) if vals else None

    # One exemplar raw response retained for audit; full set is voluminous.
    _, exemplar_raw = await fetch_soil_point(client, settings, centroid.y, centroid.x)
    raw = {
        "mode": "polygon_aggregation",
        "sample_count": len(latlons),
        "valid_samples": len(valid),
        "sample_points_lonlat": [[round(lon, 6), round(lat, 6)] for lon, lat in latlons],
        "exemplar_raw_response": exemplar_raw,
    }
    log.info("soilgrids polygon aggregation: %d/%d valid samples", len(valid), len(latlons))
    return SoilProfile(values=aggregated, samples_used=len(valid), raw=raw)


async def fetch_soil(
    client: httpx.AsyncClient, settings: Settings, boundary_geojson: dict, area_ha: float
) -> SoilProfile:
    """Dispatcher: small/point-like fields use a single centroid query."""
    if area_ha <= 1.0:
        geom = geom_from_geojson(boundary_geojson)
        c = geom.centroid
        profile, raw = await fetch_soil_point(client, settings, c.y, c.x)
        if all(v is None for v in profile.values()):
            raise NoCoverageError("SoilGrids returned no data at the field centroid "
                                  f"({c.y:.5f}, {c.x:.5f})")
        return SoilProfile(values=profile, samples_used=1,
                           raw={"mode": "point_centroid", "raw_response": raw})
    return await fetch_soil_polygon(client, settings, boundary_geojson)
