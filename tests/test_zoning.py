from __future__ import annotations

import pytest
from shapely.geometry import shape
from shapely.ops import unary_union

from app.core.spatial import geom_from_geojson
from app.engines.zoning import generate_master_layout
from tests.conftest import make_square_polygon


def _union_area(features):
    return unary_union([shape(f["geometry"]) for f in features]).area


def test_layout_partitions_field(settings, square_polygon):
    fc = generate_master_layout(square_polygon, None, settings)
    zones = {f["properties"]["zone"] for f in fc["features"]}
    assert {"homestead", "orchard", "production", "roads_service"} <= zones
    target = geom_from_geojson(square_polygon)
    cover = _union_area(fc["features"])
    # Partition must cover the field (3% tolerance for UTM round-trip)
    assert cover == pytest.approx(target.area, rel=0.03)
    for f in fc["features"]:
        props = f["properties"]
        assert props["area_ha"] > 0
        assert 0 < props["allocation_actual_pct"] <= 100
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")
    # area bookkeeping consistent
    total = sum(f["properties"]["area_ha"] for f in fc["features"])
    assert abs(total - fc["metadata"]["total_area_ha"]) < 0.05 * fc["metadata"]["total_area_ha"]


def test_well_pad_carved(settings, square_polygon):
    fc = generate_master_layout(square_polygon, (45.318, 2.046), settings)
    zones = {f["properties"]["zone"] for f in fc["features"]}
    assert "well_site" in zones
    pad = next(f for f in fc["features"] if f["properties"]["zone"] == "well_site")
    expected_ha = (settings.zoning.well_pad_side_m**2) / 10_000
    assert pad["properties"]["area_ha"] == pytest.approx(expected_ha, rel=0.1)
    assert fc["metadata"]["well_pad_carved"] is True
    # Partition still covers the field after carving
    target = geom_from_geojson(square_polygon)
    assert _union_area(fc["features"]) == pytest.approx(target.area, rel=0.03)


def test_rotated_field_supported(settings):
    import math

    angle = math.radians(33)
    cx, cy = 45.318, 2.046
    h = 0.001
    pts = [(-h, -h), (h, -h), (h, h), (-h, h), (-h, -h)]
    ring = [[
        cx + x * math.cos(angle) - y * math.sin(angle),
        cy + x * math.sin(angle) + y * math.cos(angle),
    ] for x, y in pts]
    fc = generate_master_layout({"type": "Polygon", "coordinates": [ring]}, None, settings)
    assert len(fc["features"]) >= 3
    target = geom_from_geojson({"type": "Polygon", "coordinates": [ring]})
    assert _union_area(fc["features"]) == pytest.approx(target.area, rel=0.05)
