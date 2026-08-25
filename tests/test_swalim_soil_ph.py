"""FAO SWALIM soil-pH proxy: reaction scheme, WRB harmonization, resilience."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.services import swalim_soil
from app.services.swalim import SWALIM_WFS

SNAPSHOT = Path(__file__).resolve().parents[1] / "app" / "web" / "soil_data.geojson"

WFS_FEATURE = {
    "type": "Feature",
    "id": "afgooye_final_soil_map_utm38n.1",
    "geometry": {"type": "Polygon", "coordinates": [[[45.07, 2.11], [45.08, 2.11], [45.082, 2.116], [45.078, 2.122], [45.071, 2.121], [45.07, 2.11]]]},
    "properties": {
        "ogc_fid": 1, "area_ha": 159557.021652, "system": "Q", "subsystem": "Q31",
        "lu": "Q31_3", "lu_desc": "Levee embankment and fluvial terraces, irrigated cultivations",
        "wrb_2022": "Calcaric Fluvisols (Episodic, Loamic) and Haplic Fluvisols (Calcaric, Arenic)",
    },
}
WFS_FRAME_FEATURE = {
    "type": "Feature",
    "geometry": {"type": "Polygon", "coordinates": [[[40.0, -2.0], [52.0, -2.0], [52.0, 12.0], [40.0, 12.0], [40.0, -2.0]]]},
    "properties": {"feature_type": "layer_extent_frame"},
}


@pytest.fixture(autouse=True)
def _fresh_cache():
    swalim_soil._CACHE.clear()


def _mock_all_wfs(status: int = 200, payload: dict | None = None):
    route = respx.route(url__startswith=SWALIM_WFS)
    if status == 200 and payload is not None:
        return route.mock(return_value=httpx.Response(200, json=payload))
    return route.mock(return_value=httpx.Response(status))


# ── portal reaction scheme: labels, intervals, exact hexes ─────────────────
@pytest.mark.parametrize("value,label,color", [
    (4.2, "Ultra / Strongly Acidic", "#B91C1C"),
    (5.49, "Ultra / Strongly Acidic", "#B91C1C"),
    (5.5, "Moderately Acidic", "#F59E0B"),
    (6.4, "Moderately Acidic", "#F59E0B"),
    (6.5, "Neutral", "#84CC16"),
    (7.3, "Neutral", "#84CC16"),
    (7.4, "Slightly Alkaline", "#10B981"),
    (7.8, "Slightly Alkaline", "#10B981"),
    (7.9, "Moderately Alkaline", "#06B6D4"),
    (8.4, "Moderately Alkaline", "#06B6D4"),
    (8.5, "Strongly Alkaline", "#6366F1"),
    (9.6, "Strongly Alkaline", "#6366F1"),
])
def test_ph_classification_scheme(value, label, color):
    cls = swalim_soil.classify_ph(value)
    assert cls["label"] == label
    assert cls["color"] == color


def test_wrb_harmonization():
    assert swalim_soil._derive_ph("Calcaric Fluvisols (Episodic, Loamic)") == 7.1
    assert swalim_soil._derive_ph("Haplic Regosol") == 6.6
    assert swalim_soil._derive_ph("Gypsic Solonchaks") == 8.8
    assert swalim_soil._derive_ph("Chromic Vertisols") == 5.6
    assert swalim_soil._derive_ph("Eutric Vertisols") == 6.2
    assert swalim_soil._derive_ph("Unrecorded land unit") == 7.2


def test_suitability_warnings():
    acidic = swalim_soil.suitability_warnings(5.2)
    assert any("lime" in w.lower() for w in acidic)
    alkaline = swalim_soil.suitability_warnings(8.9)
    assert any("salt-tolerant" in w.lower() for w in alkaline)
    saline = swalim_soil.suitability_warnings(8.8, "Gypsic Solonchaks, saline subunit")
    assert any("saline" in w.lower() for w in saline)
    assert "Near-ideal" in swalim_soil.suitability_warnings(7.0)[0]


def test_transform_uses_official_attributes():
    out = swalim_soil.transform_swalim_feature(WFS_FEATURE, "afgooye_soil")
    assert out is not None
    p = out["properties"]
    assert p["pH_VALUE"] == 7.1
    assert p["PH_CLASS"] == "Neutral"
    assert p["PH_COLOR"] == "#84CC16"
    assert p["SOIL_TEXTURE"] == "Silt loam (alluvium)"
    assert p["AREA_HA"] == 159557.0
    assert p["unit_code"] == "Q31_3"
    assert p["SUITABILITY_WARNINGS"]


def test_transform_strips_frame_features():
    assert swalim_soil.transform_swalim_feature(WFS_FRAME_FEATURE, "afgooye_soil") is None
    framed = {**WFS_FEATURE, "properties": {**WFS_FEATURE["properties"], "is_frame": True}}
    assert swalim_soil.transform_swalim_feature(framed, "afgooye_soil") is None


def test_transform_strips_bbox_geometry_and_non_polygons():
    # Perfect axis-aligned 4-corner rectangle = spatial envelope / grid bound.
    bbox_polygon = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[40.9, -1.66], [51.45, -1.66], [51.45, 12.05], [40.9, 12.05], [40.9, -1.66]]]},
        "properties": {**WFS_FEATURE["properties"]},
    }
    assert swalim_soil._is_bbox_geometry(bbox_polygon["geometry"]) is True
    assert swalim_soil.transform_swalim_feature(bbox_polygon, "afgooye_soil") is None
    # LineString / Point carriers are never rendered as thematic polygons.
    line = {**WFS_FEATURE, "geometry": {"type": "LineString", "coordinates": [[45.07, 2.11], [45.08, 2.12]]}}
    assert swalim_soil.transform_swalim_feature(line, "afgooye_soil") is None
    # A genuine irregular thematic polygon is kept.
    assert swalim_soil._is_bbox_geometry(WFS_FEATURE["geometry"]) is False


# ── service: live merge, per-layer outage tolerance, cache, fallback ────────
@respx.mock
async def test_service_merges_wfs_and_tolerates_layer_outages():
    first = next(iter(swalim_soil.SOIL_PH_LAYERS.values()))
    respx.get(url__eq=swalim_soil._wfs_url(first, 50000)).mock(
        return_value=httpx.Response(200, json={"type": "FeatureCollection", "features": [WFS_FEATURE, WFS_FRAME_FEATURE]})
    )
    _mock_all_wfs(status=500)  # every other candidate layer is down

    async with httpx.AsyncClient() as client:
        data, source = await swalim_soil.get_swalim_soil_ph(client, SNAPSHOT)
        assert source == "official-wfs"
        # national generalized base (7) + live WFS inset (1); base renders beneath
        assert len(data["features"]) == 8
        assert data["metadata"]["layers"] == {"national_base": 7, first: 1}
        assert data["features"][0]["properties"]["source_layer"] == "national_base"
        assert data["features"][-1]["properties"]["source_layer"] == first
        assert len(data["metadata"]["ph_classes"]) == 6
        assert "National coverage" in data["metadata"]["provenance_note"]
        calls = respx.calls.call_count
        data2, source2 = await swalim_soil.get_swalim_soil_ph(client, SNAPSHOT)
        assert source2 == "cache" and data2 == data
        assert respx.calls.call_count == calls  # served from the in-process cache


@respx.mock
async def test_service_falls_back_to_packaged_snapshot():
    _mock_all_wfs(status=503)
    async with httpx.AsyncClient() as client:
        data, source = await swalim_soil.get_swalim_soil_ph(client, SNAPSHOT)
        assert source == "static-fallback"
        assert len(data["features"]) == 7  # packaged Somalia soil snapshot
        for feature in data["features"]:
            p = feature["properties"]
            assert isinstance(p["pH_VALUE"], float)
            assert p["PH_COLOR"].startswith("#")
            assert p["SUITABILITY_WARNINGS"]


@respx.mock
async def test_service_raises_when_wfs_and_snapshot_both_unavailable(tmp_path):
    _mock_all_wfs(status=500)
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await swalim_soil.get_swalim_soil_ph(client, tmp_path / "missing.geojson")


# ── route: /api/v1/swalim/soil-ph ──────────────────────────────────────────
@respx.mock
def test_soil_ph_route_proxies_official_wfs():
    _mock_all_wfs(payload={"type": "FeatureCollection", "features": [WFS_FEATURE]})
    client = TestClient(create_app())  # no lifespan: route must self-heal its http client
    r = client.get("/api/v1/swalim/soil-ph")
    assert r.status_code == 200
    assert r.headers["X-SWALIM-Source"] == "official-wfs"
    assert r.headers["Cache-Control"] == "public, max-age=3600"
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["metadata"]["wfs_endpoint"] == SWALIM_WFS
    assert len(body["features"]) == 14  # 7 national base + 1 WFS inset per mocked catalogue layer
    wfs_insets = [f for f in body["features"] if f["properties"]["source_layer"] != "national_base"]
    assert wfs_insets[0]["properties"]["PH_CLASS"] == "Neutral"


@respx.mock
def test_soil_ph_route_falls_back_and_supports_refresh():
    _mock_all_wfs(status=502)
    client = TestClient(create_app())
    r = client.get("/api/v1/swalim/soil-ph")
    assert r.status_code == 200
    assert r.headers["X-SWALIM-Source"] == "static-fallback"
    body = r.json()
    assert len(body["features"]) == 7
    assert all(f["properties"]["source_layer"] == "national_base" for f in body["features"])
    # ?refresh=true bypasses the cache and re-queries the (still down) WFS
    r2 = client.get("/api/v1/swalim/soil-ph?refresh=true")
    assert r2.headers["X-SWALIM-Source"] == "static-fallback"
