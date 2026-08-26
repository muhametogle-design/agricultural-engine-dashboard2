"""Anti-hull regression guard: every bundled polygon dataset must be authentic
high-detail vector boundaries (GADM 4.1 / OSM / SWALIM) — never synthetic
hexagons, octagons, convex hulls or centroid mockeries.

The old synthetic bundles were literally 5-, 6- and 8-vertex regular polygons
for EVERY feature. Real official data has a long detail tail (means 30-210
vertices, maxima 300-2700) even though tiny real islets can legitimately be
small rings — so the guard asserts aggregate detail + provenance, plus a
dominant-feature detail floor.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "app" / "web"


def load(rel: str) -> dict:
    return json.loads((WEB / rel).read_text(encoding="utf-8"))


def ring_sizes(fc: dict) -> list[int]:
    sizes: list[int] = []
    for f in fc.get("features", []):
        g = f.get("geometry") or {}
        c = g.get("coordinates") or []
        rings = c if g.get("type") == "Polygon" else [r for poly in c for r in poly]
        sizes += [len(r) for r in rings if isinstance(r, list) and r and isinstance(r[0], list)]
    return sizes


def primary_ring_sizes(fc: dict) -> list[int]:
    """Largest ring per feature = the dominant boundary outline.

    Real official vectors keep small islet rings too, so only the PRIMARY
    ring carries the hull/octagon signal: a synthetic bundle would have a
    primary ring of 5-8 vertices on EVERY feature."""
    out: list[int] = []
    for f in fc.get("features", []):
        g = f.get("geometry") or {}
        c = g.get("coordinates") or []
        if g.get("type") == "Polygon":
            rings = [c[0]] + c[1:]
        elif g.get("type") == "MultiPolygon":
            rings = [r for poly in c for r in poly]
        else:
            rings = []
        if rings:
            out.append(max(len(r) for r in rings if isinstance(r, list) and r and isinstance(r[0], list)))
    return out


@pytest.mark.parametrize("rel,min_feats,min_mean,min_max", [
    ("gadm/somalia_districts.geojson", 70, 25, 150),   # 74 real GADM ADM2 districts
    ("ogaden/boundaries.geojson", 8, 150, 280),        # 9 real Somali-Region zones
    ("soil_data.geojson", 16, 35, 400),                # 18 real ADM1 regions
    ("somalia_unified.geojson", 1, 40, 2000),          # real national outline
])
def test_bundled_polygons_are_high_detail_official_vectors(rel, min_feats, min_mean, min_max):
    fc = load(rel)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) >= min_feats
    assert all(f["geometry"]["type"] in ("Polygon", "MultiPolygon") for f in fc["features"])
    sizes = ring_sizes(fc)
    assert len(sizes) >= min_feats
    assert max(sizes) >= min_max, f"{rel}: max ring {max(sizes)} — looks like placeholder geometry"
    assert sum(sizes) / len(sizes) >= min_mean, f"{rel}: mean ring {sum(sizes)/len(sizes):.1f} — hull/octagon regression"
    # primary boundary rings must be detailed — placeholder hulls would sit at 5-8
    primaries = primary_ring_sizes(fc)
    assert len(primaries) == len(fc["features"])
    assert sum(1 for n in primaries if n > 12) / len(primaries) >= 0.6, f"{rel}: too many trivial primary rings"
    assert sorted(primaries)[len(primaries) // 2] >= 15, f"{rel}: median primary ring too small"
    # provenance must cite the official vector source
    blob = json.dumps(fc)
    assert any(tag in blob for tag in ("GADM", "OpenStreetMap", "SWALIM", "OSM")), f"{rel}: no official source provenance"


def test_districts_include_hargeisa_level_detail():
    fc = load("gadm/somalia_districts.geojson")
    districts = {f["properties"]["DISTRICT"] for f in fc["features"]}
    assert "Hargeysa" in districts
    assert len(districts) >= 70  # full national district coverage, not a sample


def test_hydrology_is_real_river_geometry_not_hulls():
    fc = load("ogaden/hydrology.geojson")
    feats = fc["features"]
    assert {f["geometry"]["type"] for f in feats} <= {"LineString", "MultiLineString"}
    names = {f["properties"]["RIVER_NAME"] for f in feats}
    assert {"Jubba River", "Webi Shabeelle", "Dawa River"} <= names
    assert all(f["properties"]["LENGTH_KM"] > 30 for f in feats)
    total_vertices = sum(len(f["geometry"]["coordinates"]) for f in feats
                         if f["geometry"]["type"] == "LineString")
    assert total_vertices > 1000  # dense real OSM line work
    assert not any(f["properties"].get("feature_type") == "ogaden_basin" for f in feats)


def test_banned_synthetic_bundles_stay_deleted():
    for rel in ("swalim/land_cover.geojson", "ogaden/landcover.geojson",
                "somalia_geology.geojson", "fao_soil_ph.geojson"):
        assert not (WEB / rel).exists(), f"{rel} resurfaced: placeholder geometry is banned"
