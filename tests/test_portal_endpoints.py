"""Black-box endpoint tests for the cross-border portal proxies
(Somalia SWALIM + Ogaden), driven through the root ASGI app exactly as
`uvicorn main:app` serves them."""
from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

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


def test_swalim_land_cover_proxy():
    """Land cover must be served through the proxy allow-list (live WFS or bundled fallback)."""
    response = client.get("/api/v1/swalim/land_cover")
    assert response.status_code == 200

    data = response.json()
    assert data.get("type") == "FeatureCollection"
    assert len(data.get("features", [])) > 0
    assert response.headers.get("x-swalim-source")
