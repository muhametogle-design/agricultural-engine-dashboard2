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
from app.services.ogaden import GEOBOUNDARIES_ETH_ADM2, SWALIM_LANDUSE_WFS

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
    assert woredas == []  # woredas are NEVER synthesized: official ADM3 vectors only, served live
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
    feats = data["features"]
    zones = {f["properties"]["ZONE_NAME"] for f in feats if f["properties"]["ADMIN_LEVEL"] == 2}
    # real GADM 4.1 Somali-Region zones (official vector boundaries)
    assert {"Korahe", "Shabelle", "Faafan (Jigjiga)", "Doollo (Wardheer)", "Afder", "Liben"} <= zones
    assert len(zones) >= 9
    assert not any(f["properties"].get("WOREDA_NAME") for f in feats)  # no synthetic woredas
    assert all(f["properties"]["feature_type"] == "ogaden_admin_boundary" for f in feats)
    assert all(f["geometry"]["type"] in ("Polygon", "MultiPolygon") for f in feats)


@respx.mock
async def test_hydrology_serves_real_osm_rivers_only():
    async with httpx.AsyncClient() as client:
        hyd, hsrc = await ogaden.get_ogaden_hydrology(client, WEB_DIR)
    assert hsrc == "bundled-snapshot"
    rivers = {f["properties"]["RIVER_NAME"] for f in hyd["features"] if f["properties"]["feature_type"] == "ogaden_river"}
    # real OSM reaches from the official user dataset
    assert {"Jubba River", "Webi Shabeelle", "Dawa River"} <= rivers
    assert not any(f["properties"]["feature_type"] == "ogaden_basin" for f in hyd["features"])  # hulls banned
    assert all(f["geometry"]["type"] in ("LineString", "MultiLineString") for f in hyd["features"])
    assert all(f["properties"]["LENGTH_KM"] > 0 for f in hyd["features"])


@respx.mock
async def test_landcover_live_only_swialim_wfs():
    sample = json.loads((Path(__file__).parent / "fixtures" / "swalim_landuse_sample.geojson").read_text())
    respx.get(url__eq=SWALIM_LANDUSE_WFS).mock(return_value=httpx.Response(200, json=sample))
    async with httpx.AsyncClient() as client:
        lc, lsrc = await ogaden.get_ogaden_landcover(client, WEB_DIR)
    assert lsrc == "swalim-wfs-live"
    assert lc["features"][0]["properties"]["LAND_COVER"] == "Mangroves"
    assert lc["features"][0]["geometry"]["type"] == "MultiPolygon"
    assert "swalim" in json.dumps(lc).lower()


@respx.mock
async def test_landcover_refuses_synthetic_substitute_when_offline():
    respx.get(url__eq=SWALIM_LANDUSE_WFS).mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as client:
        with pytest.raises(RuntimeError, match="no bundled/synthetic substitute"):
            await ogaden.get_ogaden_landcover(client, WEB_DIR)


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
    assert {f["properties"]["ADMIN_LEVEL"] for f in body["features"]} == {2}  # real zones only
    assert not any(f["properties"].get("WOREDA_NAME") for f in body["features"])
    r2 = _get(client, "/api/v1/ogaden/hydrology")
    assert r2.status_code == 200 and r2.headers["X-Ogaden-Source"] == "bundled-snapshot"
    assert {f["geometry"]["type"] for f in r2.json()["features"]} <= {"LineString", "MultiLineString"}
    respx.get(url__eq=SWALIM_LANDUSE_WFS).mock(return_value=httpx.Response(503))
    r3 = _get(client, "/api/v1/ogaden/landcover")
    assert r3.status_code == 502  # honest failure: no synthetic substitute permitted
