"""Black-box endpoint tests for the cross-border portal proxies
(Somalia SWALIM + Ogaden), driven through the root ASGI app exactly as
`uvicorn main:app` serves them."""
from __future__ import annotations

from fastapi.testclient import TestClient

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from main import app

import app.services.swalim as swalim_service
import app.services.swalim_soil as swalim_soil_service
import app.services.ogaden as ogaden_service


@pytest.fixture(autouse=True)
def _isolated_caches(tmp_path, monkeypatch):
    """Runtime caches must never leak real (or stale synthetic) payloads across tests."""
    import app.services.disk_cache as dc
    for store in (swalim_service._CACHE, swalim_soil_service, ogaden_service):
        getattr(store, "_MEMORY", getattr(store, "_CACHE", {})).clear() if hasattr(store, "_MEMORY") or hasattr(store, "_CACHE") else None
    swalim_service._CACHE.clear()
    if hasattr(swalim_soil_service, "_CACHE"):
        swalim_soil_service._CACHE.clear()
    ogaden_service._MEMORY.clear()
    monkeypatch.setattr(dc, "CACHE_DIR", tmp_path)
    yield
    swalim_service._CACHE.clear()
    ogaden_service._MEMORY.clear()


client = TestClient(app)


def test_swalim_soil_ph_categorical_payload():
    """Verify Soil pH endpoint returns 200, valid GeoJSON FeatureCollection, and categorical properties without bbox envelopes."""
    response = client.get("/api/v1/swalim/soil-ph")
    assert response.status_code == 200

    data = response.json()
    assert data.get("type") == "FeatureCollection"
    assert len(data.get("features", [])) > 0

    # Validate feature geometry and properties schema
    for feature in data["features"]:
        geom_type = feature.get("geometry", {}).get("type")
        assert geom_type in ["Polygon", "MultiPolygon"], f"Invalid geometry type: {geom_type}"

        # Ensure outer bounding box grid envelopes are stripped
        props = feature.get("properties", {})
        assert props.get("is_extent") is not True
        assert props.get("layer_type") != "bbox"

        # Assert categorical pH attribute presence
        # (payload uses mixed-case "pH_VALUE"; PH_VALUE/ph kept as aliases)
        assert any(key in props for key in ["pH", "PH_VALUE", "pH_VALUE", "ph_class", "PH"])


def test_ogaden_boundaries_proxy():
    """Verify Ogaden endpoint returns proper administrative features and normalized names."""
    response = client.get("/api/v1/ogaden/boundaries")
    assert response.status_code == 200

    data = response.json()
    assert data.get("type") == "FeatureCollection"

    features = data.get("features", [])
    assert len(features) > 0
    sample_props = features[0].get("properties", {})
    assert any(k in sample_props for k in ["name", "WOREDA_NAME", "ZONE_NAME"])
    # provenance is always disclosed (live geoBoundaries / cache / bundled snapshot)
    assert response.headers.get("x-ogaden-source")


@respx.mock
def test_swalim_land_cover_proxy_live_only():
    """Land cover is served from the official SWALIM WFS only — no synthetic bundle exists.

    With the WFS unreachable the endpoint fails honestly (502) rather than
    serving placeholder hexagons; when reachable it streams real vectors."""
    respx.get(url__regex=r"spatial\.faoswalim\.org").mock(return_value=httpx.Response(503))
    offline = client.get("/api/v1/swalim/land_cover")
    assert offline.status_code == 502  # policy: no artificial substitute geometry

    sample = json.loads(Path(__file__).parent / "fixtures" / "swalim_landuse_sample.geojson"
                        .read_text() if False else (Path(__file__).parent / "fixtures" / "swalim_landuse_sample.geojson").read_text())
    respx.get(url__regex=r"spatial\.faoswalim\.org").mock(return_value=httpx.Response(200, json=sample))
    live = client.get("/api/v1/swalim/land_cover")
    assert live.status_code == 200
    data = live.json()
    assert data["type"] == "FeatureCollection" and data["features"]
    assert data["features"][0]["properties"].get("land_cover") == "Mangroves"
    assert live.headers.get("x-swalim-source") == "official-wfs"
