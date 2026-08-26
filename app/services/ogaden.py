"""Ogaden / Ethiopian Somali Region cross-border spatial proxy.

Live sources:
  * Admin 2 zones: geoBoundaries gbOpen ETH/ADM2 (full national Ethiopian
    zones; filtered to the Somali Regional State zones named by the portal
    spec — Jigjiga, Korahe, Doollo, Gode — plus neighbouring Somali-region
    zones when present).

Bundled (honest, generalized) sources for layers with no open live endpoint:
  * Admin 3 woredas of the four named zones (real woreda names, generalized
    geometry).
  * Upstream Jubba (Ganale Dorya) and Shabelle (Webi Shabelle) networks and
    basin extents.
  * Cross-border land cover / soil categories.

Everything is served through the same pipeline: memory -> disk cache
(/static/data/cache/) -> live WFS/GeoJSON -> last-good disk payload ->
bundled snapshot. Provenance is disclosed per response.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx

from app.services.disk_cache import read_cache, read_stale, write_cache

GEOBOUNDARIES_ETH_ADM2 = (
    "https://raw.githubusercontent.com/wmgeolab/geoBoundaries/main/releaseData/"
    "gbOpen/ETH/ADM2/geoBoundaries-ETH-ADM2.geojson"
)
OGADEN_DIR_NAME = "ogaden"

# Somali Regional State zone names as they appear in geoBoundaries ADM2.
_ZONE_MATCHES = (
    "jigjiga", "jijiga", "faafan", "jarar", "jaraar", "korahe", "qorahey",
    "gode", "doollo", "dollo", "shabelle", "nogob", "fiiq", "siti", "shinile",
    "afder", "liben", "korahey",
    "erer", "awbare", "dobeweyn", "togotale", "somali",
)

_MEMORY: dict[str, tuple[float, dict[str, Any], str]] = {}
_LOCK = asyncio.Lock()
TTL_S = 24 * 3600


def _zone_is_ogaden(shape_name: str) -> bool:
    lowered = (shape_name or "").lower()
    return any(match in lowered for match in _ZONE_MATCHES)


def _transform_zone(feature: dict[str, Any]) -> dict[str, Any] | None:
    props = feature.get("properties") or {}
    name = props.get("shapeName") or props.get("ZONE_NAME") or props.get("name")
    if not name:
        return None
    return {
        "type": "Feature",
        "geometry": feature.get("geometry"),
        "properties": {
            "feature_type": "ogaden_admin2_zone",
            "ADMIN_LEVEL": 2,
            "ZONE_NAME": name,
            "ZONE_ID": props.get("shapeISO") or props.get("shapeID") or name,
            "source_layer": "geoboundaries_eth_adm2",
        },
    }


def _collection(name: str, features: list[dict[str, Any]], source: str, note: str) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": name,
        "metadata": {
            "source": source,
            "feature_count": len(features),
            "provenance_note": note,
        },
        "features": features,
    }


def _bundled(static_root: Path, key: str) -> list[dict[str, Any]]:
    path = static_root / OGADEN_DIR_NAME / f"{key}.geojson"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [f for f in payload.get("features", []) if isinstance(f, dict)]
    except (OSError, json.JSONDecodeError):
        return []


async def _resolve(
    key: str,
    client: httpx.AsyncClient,
    static_root: Path,
    live_fetch=None,
) -> tuple[dict[str, Any], str]:
    """Shared pipeline: memory -> disk -> live -> stale disk -> bundled."""
    now = time.monotonic()
    cached = _MEMORY.get(key)
    if cached and now - cached[0] < TTL_S:
        return cached[1], "cache"

    async with _LOCK:
        cached = _MEMORY.get(key)
        if cached and time.monotonic() - cached[0] < TTL_S:
            return cached[1], "cache"

        payload = read_cache(f"ogaden_{key}", TTL_S)
        if payload is not None:
            _MEMORY[key] = (time.monotonic(), payload, "disk-cache")
            return payload, "disk-cache"

        source, features, note = "bundled-snapshot", None, ""
        if live_fetch is not None:
            try:
                features, source, note = await live_fetch(client)
            except (httpx.HTTPError, ValueError, json.JSONDecodeError):
                features = None

        if features is None:
            stale = read_stale(f"ogaden_{key}")
            if stale is not None:
                _MEMORY[key] = (time.monotonic(), stale, "stale-disk-cache")
                return stale, "stale-disk-cache"
            features = _bundled(static_root, key)
            source, note = "bundled-snapshot", _bundled_note(key)

        data = _collection(_titles[key], features, source, note)
        write_cache(f"ogaden_{key}", data)
        _MEMORY[key] = (time.monotonic(), data, source)
        return data, source


_titles = {
    "boundaries": "Ogaden / Somali Region — Admin 2 Zones (official vector boundaries)",
    "hydrology": "Upstream Jubba & Shabelle — Real River Networks (OSM)",
    "landcover": "Cross-border Land Cover — official SWALIM land-use systems",
}


def _bundled_note(key: str) -> str:
    return {
        "boundaries": ("Bundled official GADM 4.1 ETH ADM2 Somali-Region zones — real "
                       "vector boundaries. Woredas (ADM3) are never synthesized: they are "
                       "served live from geoBoundaries only when the network allows."),
        "hydrology": ("Bundled real OpenStreetMap river reaches (Jubba / Webi Shabeelle / "
                      "Dawa). Synthetic basin hulls were removed rather than approximated."),
        "landcover": ("No bundled land cover: this layer is served live from the official "
                      "FAO SWALIM land-use systems WFS only (no artificial substitutes)."),
    }[key]


async def _live_boundaries(client: httpx.AsyncClient):
    response = await client.get(GEOBOUNDARIES_ETH_ADM2, timeout=60.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("geoBoundaries ADM2 response is not a FeatureCollection")
    zones = [t for t in (_transform_zone(f) for f in payload.get("features", []))
             if t is not None and t["geometry"]]
    ogaden = [f for f in zones if _zone_is_ogaden(f["properties"]["ZONE_NAME"])]
    if not ogaden:
        raise ValueError("no Somali Region zones matched in geoBoundaries ADM2")
    return ogaden, "geoboundaries-live", (
        "Live geoBoundaries gbOpen ETH/ADM2 zones filtered to the Somali Regional "
        "State (Ogaden). Only official vector boundaries are rendered; woredas come "
        "exclusively from official ADM3 sources when reachable."
    )


async def get_ogaden_boundaries(client: httpx.AsyncClient, static_root: Path):
    """Admin 2 zones (live) + Admin 3 woredas (bundled) as one collection."""
    key = "boundaries"

    async def fetch(client_: httpx.AsyncClient):
        zones, source, note = await _live_boundaries(client_)
        features = zones + [
            f for f in _bundled(static_root, key)
            if (f.get("properties") or {}).get("ADMIN_LEVEL") == 3
        ]
        return features, source, note

    data, source = await _resolve(key, client, static_root, live_fetch=fetch)
    if source in ("geoboundaries-live", "cache", "disk-cache"):
        pass  # woredas already merged inside the cached collection
    return data, source


SWALIM_LANDUSE_WFS = (
    "https://spatial.faoswalim.org/geoserver/ows?service=wfs&version=1.0.0"
    "&request=GetFeature&typename=geonode:som_landuse_system_faoswalim2007"
    "&outputFormat=application/json&maxFeatures=50000"
)


async def get_ogaden_hydrology(client: httpx.AsyncClient, static_root: Path):
    return await _resolve("hydrology", client, static_root)


async def _live_landcover(client: httpx.AsyncClient):
    """Official SWALIM land-use systems (166 real vector polygons)."""
    response = await client.get(SWALIM_LANDUSE_WFS, timeout=60.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
        raise ValueError("SWALIM land-use WFS response is not a FeatureCollection")
    features = []
    for f in payload.get("features", []):
        props = f.get("properties") or {}
        land_cover = props.get("land_cover") or props.get("LAND_COVER")
        if not land_cover or not f.get("geometry"):
            continue
        features.append({
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "feature_type": "ogaden_landcover",
                "LAND_COVER": land_cover,
                "LANDUSE": props.get("landuse"),
                "REGION": "Somalia / cross-border systems (SWALIM 2007)",
                "source_layer": "swalim_landuse_systems",
            },
        })
    if not features:
        raise ValueError("no land-use features returned")
    return features, "swalim-wfs-live", (
        "Live official FAO SWALIM land-use systems WFS "
        "(geonode:som_landuse_system_faoswalim2007) — authentic vector polygons."
    )


async def get_ogaden_landcover(client: httpx.AsyncClient, static_root: Path):
    data, source = await _resolve("landcover", client, static_root,
                                  live_fetch=_live_landcover)
    if source == "bundled-snapshot" and not data.get("features"):
        # No synthetic substitute is permitted for this layer.
        raise RuntimeError(
            "Cross-border land cover requires the live SWALIM WFS "
            "(no bundled/synthetic substitute exists by policy)."
        )
    return data, source
