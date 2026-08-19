from __future__ import annotations

import math

from app.core.spatial import geom_from_geojson
from app.engines.terrain import NullTerrainProvider
from app.engines.well_siting import run_well_siting


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def test_ves_only_mce_prefers_productive_sounding(settings, square_polygon, ves_surveys):
    res = run_well_siting(square_polygon, ves_surveys, settings, NullTerrainProvider())
    assert res.optimal_lon is not None
    # With terrain unavailable the VES weight must renormalize to 1.0
    assert res.factor_weights_used == {"ves": 1.0}
    good = ves_surveys[0]
    bad = ves_surveys[1]
    opt = (res.optimal_lon, res.optimal_lat)
    assert _dist(opt, (good["lon"], good["lat"])) < _dist(opt, (bad["lon"], bad["lat"]))
    # Depth: nearest sounding water table (30 m) + 15 m margin
    assert res.recommended_drilling_depth_m == 45.0
    # Optimal point must lie inside the field
    pt = geom_from_geojson({"type": "Point", "coordinates": [res.optimal_lon, res.optimal_lat]})
    assert geom_from_geojson(square_polygon).covers(pt)
    assert 1 <= len(res.candidates) <= 5
    assert res.candidates[0]["composite_score"] == res.composite_score


class _FakeTerrain:
    """Flat 1% slope + flow accumulation rising toward +x."""

    def slope_flow_grids(self, boundary, xs, ys, epsg, cell_m):
        import numpy as np

        return np.full_like(xs, 1.0), (xs - xs.min())


def test_terrain_factors_included_when_available(settings, square_polygon, ves_surveys):
    res = run_well_siting(square_polygon, ves_surveys, settings, _FakeTerrain())
    assert set(res.factor_weights_used) == {"ves", "slope", "flowacc"}
    total = sum(res.factor_weights_used.values())
    assert abs(total - 1.0) < 1e-9
    # constant low slope -> slope factor saturated at 1.0
    assert res.factor_summary["slope"]["min"] == 1.0


def test_no_inputs_returns_no_site(settings, square_polygon):
    res = run_well_siting(square_polygon, [], settings, NullTerrainProvider())
    assert res.optimal_lon is None
    assert res.composite_score is None
    assert res.recommended_drilling_depth_m == settings.well_siting.default_drilling_depth_m
    assert "warning" in res.coverage
