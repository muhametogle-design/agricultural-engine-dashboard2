"""Auto-importer for the official Abbate et al. (1994) Somalia geology vectors.

The pipeline is exercised with REAL geometry only: genuine GADM district
polygons are written to a projected shapefile (mimicking the UNESCO package
layout: unit_code / unit_name / age_range) in tmp_path and converted through
the production code path. No synthetic geology may ever reach app/web.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pytest

from app.services import geology_import as gi

REPO = Path(__file__).resolve().parents[1]
DISTRICTS = REPO / "app" / "web" / "gadm" / "somalia_districts.geojson"


@pytest.fixture(scope="module")
def real_units() -> gpd.GeoDataFrame:
    """Real GADM ADM2 polygons re-labelled as geology units, in EPSG:32638."""
    gdf = gpd.read_file(DISTRICTS)
    gdf = gdf.to_crs(32638)  # projected metres, like the Abbate CAD export
    units = [("Q", "Sands, silts and gravels", "Quaternary"),
             ("Ky", "Yesomma Sandstones", "Cretaceous"),
             ("Kb", "Garbaharre Fm.", "Cretaceous")]
    rows = []
    feats = list(gdf.geometry)
    for i, geom in enumerate(feats[:6]):
        code, name, age = units[i % 3]
        rows.append({"unit_code": code, "unit_name": name,
                     "age_range": age, "geometry": geom})
    return gpd.GeoDataFrame(rows, crs="EPSG:32638")


@pytest.fixture()
def official_shp(tmp_path: Path, real_units) -> Path:
    """Shapefile mirroring the UNESCO package (SHP+SHX+DBF+PRJ+CPG)."""
    folder = tmp_path / "soamlia_geology_1.5M"
    folder.mkdir()
    target = folder / "Somalia_geology_1.5M.shp"
    real_units.to_file(target, driver="ESRI Shapefile", encoding="utf-8")
    return target


def test_no_source_no_output(tmp_path, monkeypatch):
    """Honesty guard: nothing importable -> nothing written, no placeholders."""
    monkeypatch.setattr(gi, "REPO_ROOT", tmp_path)
    assert gi.find_source() is None
    out = tmp_path / "somalia_geology.geojson"
    assert gi.import_geology(output=out) is None
    assert not out.exists()


def test_find_source_detects_loose_shp_with_dbf_sibling(official_shp, monkeypatch, tmp_path):
    monkeypatch.setattr(gi, "REPO_ROOT", official_shp.parent.parent)
    monkeypatch.setattr(gi, "_MIN_SHP_BYTES", 1_000)  # fixture is compact; prod guard stays high
    assert gi.find_source() == official_shp


def test_find_source_ignores_shp_without_dbf(tmp_path, monkeypatch, real_units):
    monkeypatch.setattr(gi, "_MIN_SHP_BYTES", 1_000)
    orphan = tmp_path / "Somalia_geology_1.5M.shp"
    real_units.to_file(tmp_path / "Somalia_geology_1.5M.shp", driver="ESRI Shapefile")
    for side in ("dbf", "shx", "prj", "cpg"):
        p = tmp_path / f"Somalia_geology_1.5M.{side}"
        if p.exists():
            p.unlink()
    monkeypatch.setattr(gi, "REPO_ROOT", tmp_path)
    assert gi.find_source() is None


def test_import_produces_4326_with_official_attributes(official_shp, tmp_path, monkeypatch):
    monkeypatch.setattr(gi, "_MIN_SHP_BYTES", 1_000)  # direct source bypasses scan
    out = gi.import_geology(source=official_shp, output=tmp_path / "g.geojson")
    assert out and out.is_file()
    fc = json.loads(out.read_text())
    assert fc["type"] == "FeatureCollection"
    assert "Abbate" in fc["metadata"]["source"]
    assert "UNESCO" in fc["metadata"]["distributor"]
    assert len(fc["features"]) == 6

    for f in fc["features"]:
        assert f["geometry"]["type"] in ("Polygon", "MultiPolygon")
        p = f["properties"]
        # WGS84 sanity: Somalia bounding box
        assert f["geometry"] is not None
        assert p["feature_type"] == "somalia_geology"
        assert p["LITHOLOGY"] in (
            "Limestone / Dolomite", "Sandstone / Quartzite", "Volcanic / Basalt",
            "Alluvium / Sediments", "Precambrian Basement / Granite", "Sedimentary / Other")
        assert p["unit_code"] in ("Q", "Ky", "Kb")
        assert p["permeability_class"] and p["groundwater_potential"]

    lons = [c[0] for f in fc["features"] for ring in
            (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
             else [r for poly in f["geometry"]["coordinates"] for r in poly])
            for c in ring]
    lats = [c[1] for f in fc["features"] for ring in
            (f["geometry"]["coordinates"] if f["geometry"]["type"] == "Polygon"
             else [r for poly in f["geometry"]["coordinates"] for r in poly])
            for c in ring]
    assert -2 < min(lats) and max(lats) < 13          # reprojected to degrees
    assert 40 < min(lons) and max(lons) < 55


def test_original_sld_colours_applied(official_shp, tmp_path, monkeypatch):
    monkeypatch.setattr(gi, "_MIN_SHP_BYTES", 1_000)
    out = gi.import_geology(source=official_shp, output=tmp_path / "g.geojson")
    fc = json.loads(out.read_text())
    sld = {p["unit_code"]: p["SLD_COLOR"] for p in
           (f["properties"] for f in fc["features"])}
    assert sld["Q"] and sld["Q"].startswith("#")
    assert sld["Ky"] and sld["Ky"].startswith("#")


def test_idempotent_skip_when_output_fresh(official_shp, tmp_path):
    out = tmp_path / "g.geojson"
    first = gi.import_geology(source=official_shp, output=out, force=True)
    stamp = out.stat().st_mtime
    again = gi.import_geology(source=official_shp, output=out)
    assert again == first and out.stat().st_mtime == stamp  # untouched


def test_lithology_classification():
    assert gi.lithology_class("Yesomma Sandstones") == "Sandstone / Quartzite"
    assert gi.lithology_class("Sands, silts and gravels") == "Alluvium / Sediments"
    assert gi.lithology_class("Eirimo Limestone") == "Limestone / Dolomite"
    assert gi.lithology_class("Basement complex gneiss") == "Precambrian Basement / Granite"
    assert gi.lithology_class("Unknown formation") == "Sedimentary / Other"


def test_repo_stays_free_of_placeholder_geology():
    """The migration invariant: no geology payload ships without the source."""
    assert not (REPO / "app" / "web" / "somalia_geology.geojson").exists()
