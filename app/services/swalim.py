"""Cached proxy for official FAO SWALIM OGC WFS and packaged GeoJSON layers."""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.disk_cache import read_cache as disk_read
from app.services.disk_cache import read_stale as disk_stale
from app.services.disk_cache import write_cache as disk_write

SWALIM_WFS = "https://spatial.faoswalim.org/geoserver/ows"
LAYER_TYPES = {
    "river_basins": "geonode:SOM_WAT_BASINS_FAOSWALIM_USGS",
    "hydrology": "geonode:SOM_Rivers_FAOSWALIM",
    "water_points": "geonode:SOM_Water_Sources_FAOSWALIM",
    "land_degradation": "geonode:SOM_Land_Degradation_FAOSWALIM",
    # National land use / land cover systems (FAO landcover Somalia 2000 base);
    # override with AGRI_SWALIM_LAND_COVER_URL if SWALIM republishes the layer.
    "land_cover": "geonode:som_landuse_system_faoswalim2007",
    "flood_risk": "geonode:SOM_Juba_Shabelle_River_Floods_Deyr_2019",
}
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_LOCK = asyncio.Lock()


def _wfs_url(layer_name: str) -> str:
    override = os.getenv(f"AGRI_SWALIM_{layer_name.upper()}_URL")
    if override:
        return override
    return SWALIM_WFS + "?" + urlencode({
        "service": "WFS", "version": "1.0.0", "request": "GetFeature",
        "typename": LAYER_TYPES[layer_name], "outputFormat": "application/json",
        "srsName": "EPSG:4326", "maxFeatures": "50000",  # full national extent, unpaginated
    })


def _validate(data: Any, layer_name: str) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ValueError(f"SWALIM {layer_name} response is not a GeoJSON FeatureCollection")
    return data


async def get_swalim_layer(
    layer_name: str,
    client: httpx.AsyncClient,
    static_dir: Path,
    cache_ttl_s: int = 3600,
) -> tuple[dict[str, Any], str]:
    """Return one allow-listed SWALIM layer, preferring official WFS then static fallback."""
    if layer_name not in LAYER_TYPES:
        raise KeyError(layer_name)
    now = time.monotonic()
    cached = _CACHE.get(layer_name)
    if cached and now - cached[0] < cache_ttl_s:
        return cached[1], "cache"

    async with _LOCK:
        cached = _CACHE.get(layer_name)
        if cached and now - cached[0] < cache_ttl_s:
            return cached[1], "cache"
        payload = disk_read(f"swalim_{layer_name}", cache_ttl_s)
        if payload is not None:
            _CACHE[layer_name] = (time.monotonic(), payload)
            return payload, "disk-cache"
        try:
            response = await client.get(_wfs_url(layer_name), timeout=30.0)
            response.raise_for_status()
            data = _validate(response.json(), layer_name)
            source = "official-wfs"
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            stale = disk_stale(f"swalim_{layer_name}")
            if stale is not None:
                _CACHE[layer_name] = (time.monotonic(), stale)
                return stale, "stale-disk-cache"
            path = static_dir / f"{layer_name}.geojson"
            if not path.is_file():
                raise
            data = _validate(json.loads(path.read_text(encoding="utf-8")), layer_name)
            source = "static-fallback"
        else:
            disk_write(f"swalim_{layer_name}", data)
        _CACHE[layer_name] = (time.monotonic(), data)
        return data, source
