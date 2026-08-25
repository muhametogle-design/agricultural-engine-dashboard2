"""Ogaden cross-border proxy: live geoBoundaries, disk cache, bundled fallback."""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import ogaden
from app.services.disk_cache import cache_path
from app.services.ogaden import GEOBOUNDARIES_ETH_ADM2

WEB_DIR = Path(__file__).resolve().parents[1] / "app" / "web"

GB_ZONE = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "properties": {"shapeName": "Jigjiga", "shapeID": "ETH-ADM2-001"},
         "geometry": {"type": "Polygon", "coordinates": [[[42.1, 8.9], [43.0, 9.6], [43.9, 10.1], [42.7, 10.4], [42.1, 8.9]]]}},
        {"type": "Feature", "properties": {"shapeName": "Korahe", "shapeID": "ETH-ADM2-002"},
         "geometry": {"type": "Polygon", "coordinates": [[[43.7, 7.0], [45.2, 7.3], [46.4, 8.1], [44.9, 8.8], [43.7, 7.0]]]}},
        {"type": "Feature", "properties": {"shapeName": "Gode", "shapeID": "ETH-ADM2-003"},
         "geometry": {"type": "Polygon", "coordinates": [[[42.5, 4.7], [44.0, 4.9], [45.8, 5.9], [44.2, 6.6], [42.5, 4.7]]]}},
        {"type": "Feature", "properties": {"shapeName": "Doollo", "shapeID": "ETH-ADM2-004"},
         "geometry": {"type": "Polygon", "coordinates": [[[45.5, 5.0], [47.0, 5.4], [48.1, 6.6], [46.4, 7.3], [45.5, 5.0]]]}},
        {"type": "Feature", "properties": {"shapeName": "Oromia", "shapeID": "ETH-ADM2-999"},  # must be filtered out
         "geometry": {"type": "Polygon", "coordinates": [[[38.0, 6.0], [39.0, 6.0], [39.0, 7.0], [38.0, 7.0], [38.0, 6.0]]]}},
    ],
}


@pytest.fixture(autouse=True)
def _fresh(tmp_path, monkeypatch):
    ogaden._MEMORY.clear()
    ogaden.CACHE_DIR = tmp_path  # route disk cache into a sandbox dir per test
    import app.services.disk_cache as dc
    monkeypatch.setattr(dc, "CACHE_DIR", tmp_path)
    yield
    ogaden._MEMORY.clear()


@respx.mock
async def test_boundaries_live_geoboundaries_filtered_and_cached():
    respx.get(url__eq=GEOBOUNDARIES_ETH_ADM2).mock(return_value=httpx.Response(200, json=GB_ZONE))
    async with httpx.AsyncClient() as client:
        data, source = await ogaden.get_ogaden_boundaries(client, WEB_DIR)
    assert source == "geoboundaries-live"
    zones = [f for f in data["features"] if f["properties"]["ADMIN_LEVEL"] == 2]
    woredas = [f for f in data["features"] if f["properties"]["ADMIN_LEVEL"] == 3]
    assert {z["properties"]["ZONE_NAME"] for z in zones} == {"Jigjiga", "Korahe", "Gode", "Doollo"}
    assert not any(z["properties"]["ZONE_NAME"] == "Oromia" for z in zones)  # non-Somali zone filtered
    assert woredas and all("WOREDA_NAME" in w["properties"] for w in woredas)
    assert {"Jijiga", "Warder", "Kalafo"} <= {w["properties"]["WOREDA_NAME"] for w in woredas}
    assert cache_path("ogaden_boundaries").exists() or (ogaden.CACHE_DIR / "ogaden_boundaries.json").exists()
    # second call served from cache without hitting the network
    async with httpx.AsyncClient() as client:
        _, source2 = await ogaden.get_ogaden_boundaries(client, WEB_DIR)
    assert source2 in ("cache", "disk-cache")


@respx.mock
async def test_boundaries_fall_back_when_live_unavailable():
    respx.get(url__eq=GEOBOUNDARIES_ETH_ADM2).mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        data, source = await ogaden.get_ogaden_boundaries(client, WEB_DIR)
    assert source == "bundled-snapshot"
    zones = {f["properties"]["ZONE_NAME"] for f in data["features"] if f["properties"]["ADMIN_LEVEL"] == 2}
    assert {"Jigjiga Zone", "Korahe Zone", "Gode Zone", "Doollo Zone"} <= zones
    assert any(f["properties"].get("WOREDA_NAME") == "Gode" for f in data["features"])


@respx.mock
async def test_hydrology_and_landcover_serve_bundled_full_sets():
    async with httpx.AsyncClient() as client:
        hyd, hsrc = await ogaden.get_ogaden_hydrology(client, WEB_DIR)
        lc, lsrc = await ogaden.get_ogaden_landcover(client, WEB_DIR)
    assert hsrc == "bundled-snapshot" and lsrc == "bundled-snapshot"
    rivers = {f["properties"]["RIVER_NAME"] for f in hyd["features"] if f["properties"]["feature_type"] == "ogaden_river"}
    assert any("Ganale" in r for r in rivers) and any("Shabelle" in r for r in rivers)
    assert any(f["properties"]["feature_type"] == "ogaden_basin" for f in hyd["features"])
    covers = {f["properties"]["LAND_COVER"] for f in lc["features"]}
    assert {"Rainfed Crop Fields", "Irrigated Fields", "Water Bodies"} <= covers
    assert all(f["properties"]["SOIL_TYPE"] for f in lc["features"])


def _get(client: TestClient, path: str):
    ogaden._MEMORY.clear()
    return client.get(path)


@respx.mock
def test_ogaden_routes_served_under_api_v1():
    respx.get(url__eq=GEOBOUNDARIES_ETH_ADM2).mock(return_value=httpx.Response(500))
    client = TestClient(create_app())
    r = _get(client, "/api/v1/ogaden/boundaries")
    assert r.status_code == 200
    assert r.headers["X-Ogaden-Source"] == "bundled-snapshot"
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert any(f["properties"].get("WOREDA_NAME") for f in body["features"])
    r2 = _get(client, "/api/v1/ogaden/hydrology")
    assert r2.status_code == 200 and r2.headers["X-Ogaden-Source"] == "bundled-snapshot"
    r3 = _get(client, "/api/v1/ogaden/landcover")
    assert r3.status_code == 200 and any("SOIL_TYPE" in f["properties"] for f in r3.json()["features"])
