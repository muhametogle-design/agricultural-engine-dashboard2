"""Automatic importer: digitized Abbate et al. (1994) Somalia geology 1:1,500,000.

Source of honour: UNESCO IHP-WINS dataset "Digitized Geological map of Somalia -
1:1,500,000 - Abbate et al." (SHP zip / GPKG), EPSG:4210 (Arc 1960). The repo
already carries the attribute half of this dataset (Somalia_geology_1.5M.dbf,
a CAD hatch export with unit_code/unit_name/age_range); this importer completes
it with the official vector geometry the moment the downloaded archive is
placed in (or next to) the repository.

Design policy (Lead Spatial Data Architect directive):
- ONLY authentic vector boundaries are emitted; if no source archive exists the
  importer does nothing (placeholder geology is never generated).
- Output: app/web/somalia_geology.geojson (EPSG:4326) with unit_code, unit_name,
  age_range, a LITHOLOGY class derived from the unit name, and the original
  cartographic fill colour from the published SLD.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = REPO_ROOT / "app" / "web"
OUTPUT = WEB_DIR / "somalia_geology.geojson"
COLORS = WEB_DIR / "somalia_geology_colors.json"

# candidate inputs: UNESCO SHP zip / GPKG, or the loose shapefile set
# (Somalia_geology_1.5M.shp + .shx + .dbf + .prj) assembled in the repo
_ZIP_NAMES = [
    "soamlia_geology_1.5m.zip",
    "somalia_geology_1.5m.zip",
]
_GPKG_NAMES = [
    "somalia_geo_1.7_fixed_geometries_final.gpkg",
]
# the real Somalia_geology_1.5M.shp is ~34 MB; guard against truncated uploads
_MIN_SHP_BYTES = 100_000

_SHP_NAMES = [
    "Somalia_geology_1.5M.shp",
    "Somalia_geology_1.5m.shp",
    "somalia_geology_1.5m.shp",
]

_LITHOLOGY_RULES: list[tuple[tuple[str, ...], str]] = [
    (("limestone", "dolomite", "eerimo", "auradu", "karkar"), "Limestone / Dolomite"),
    (("sandstone", "quartzite", "yesomma", "arenite", "jesomma", "garbaharre"), "Sandstone / Quartzite"),
    (("basalt", "volcanic", "lava", "tuff", "trappean", "jessoma", "abdulkadir"), "Volcanic / Basalt"),
    (("alluvium", "sands, silts", "sands, silts and gravels", "deltaic", "dune", "coral",
      "limestone reef", "gravel", "silt", "clay", "gypsum", "evaporite", "eolian"), "Alluvium / Sediments"),
    (("basement", "granite", "gneiss", "migmatite", "precambrian", "crystalline", "schist",
      "amphibolite", "quartz-feldspar", "bur"), "Precambrian Basement / Granite"),
]


def lithology_class(unit_name: str) -> str:
    text = (unit_name or "").lower()
    for keys, label in _LITHOLOGY_RULES:
        if any(k in text for k in keys):
            return label
    return "Sedimentary / Other"


def _era_from_code(unit_code: str, age_range: str) -> str:
    if age_range:
        return age_range
    code = (unit_code or "").strip()
    if not code:
        return "Not specified"
    first = code[0].upper()
    return {"Q": "Quaternary", "T": "Tertiary / Neogene", "N": "Neogene",
            "P": "Paleogene / Paleozoic", "K": "Cretaceous", "J": "Jurassic",
            "M": "Mesozoic", "O": "Ordovician / Oligocene", "E": "Eocene",
            "X": "Precambrian basement", "D": "Devonian / Metamorphic"}.get(first, "Not specified")


def _candidate_roots() -> list[Path]:
    """Repo root plus any plausible drop folder (dataset dirs, downloads, ...)."""
    roots = [REPO_ROOT, REPO_ROOT / "downloads", REPO_ROOT / "data", REPO_ROOT / "uploads"]
    if not REPO_ROOT.is_dir():
        return roots
    for d in REPO_ROOT.iterdir():
        if not d.is_dir():
            continue
        n = d.name.lower()
        if any(k in n for k in ("geolog", "1.5", "soamlia", "somalia")) or \
                n in {"downloads", "data", "uploads"}:
            roots.append(d)
            for sub in d.iterdir():
                if sub.is_dir():
                    roots.append(sub)
    return roots


def find_source() -> Path | None:
    """Locate the official vectors: UNESCO zip / GPKG, or the loose .shp set."""
    roots = _candidate_roots()
    for name in _ZIP_NAMES + _GPKG_NAMES:
        for root in roots:
            candidate = root / name
            if candidate.is_file() and candidate.stat().st_size > 10_000:
                return candidate
    # loose shapefile: .shp plus its .dbf sibling (same folder, either casing)
    for root in roots:
        for name in _SHP_NAMES:
            shp = root / name
            if not (shp.is_file() and shp.stat().st_size > _MIN_SHP_BYTES):
                continue
            siblings = {p.name.lower() for p in root.iterdir() if p.is_file()}
            if any(s.endswith(".dbf") for s in siblings):
                return shp
    return None


def _load_frame(source: Path):
    import geopandas as gpd

    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as zf:
            shp_names = [n for n in zf.namelist() if n.lower().endswith(".shp")]
            gpkg_names = [n for n in zf.namelist() if n.lower().endswith(".gpkg")]
        if shp_names:
            return gpd.read_file(f"zip://{source}!{shp_names[0]}")
        if gpkg_names:
            return gpd.read_file(f"zip://{source}!{gpkg_names[0]}")
        raise ValueError("archive contains neither .shp nor .gpkg")
    return gpd.read_file(source)


def import_geology(force: bool = False, source: Path | None = None,
                   output: Path | None = None) -> Path | None:
    """Convert the official archive into the portal GeoJSON. Returns output path.

    Idempotent: skips when the output already exists unless the source is newer
    (or force=True). Returns None when no source archive is present."""
    source = source or find_source()
    out: Path = output or OUTPUT
    if source is None:
        return None
    if out.is_file() and not force and out.stat().st_mtime >= source.stat().st_mtime:
        return out

    gdf = _load_frame(source)
    cols = {c.lower(): c for c in gdf.columns}
    unit_code_c = cols.get("unit_code")
    unit_name_c = cols.get("unit_name") or cols.get("unit")
    age_c = cols.get("age_range") or cols.get("age")

    colors: dict[str, str] = {}
    if COLORS.is_file():
        try:
            colors = json.loads(COLORS.read_text(encoding="utf-8")).get("unit_colors", {})
        except (json.JSONDecodeError, OSError):
            colors = {}

    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4210")  # dataset documentation: Arc 1960 geographic
    if gdf.crs and gdf.crs.to_epsg() not in (4326, None):
        gdf = gdf.to_crs("EPSG:4326")

    features: list[dict[str, Any]] = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        code = str(getattr(row, unit_code_c, "") or "") if unit_code_c else ""
        name = str(getattr(row, unit_name_c, "") or "") if unit_name_c else ""
        age = str(getattr(row, age_c, "") or "") if age_c else ""
        features.append({
            "type": "Feature",
            "geometry": geom.__geo_interface__,
            "properties": {
                "feature_type": "somalia_geology",
                "formation_name": name or code or "Unnamed unit",
                "LITHOLOGY": lithology_class(name),
                "unit_code": code,
                "age_range": age,
                "era": _era_from_code(code, age),
                "SLD_COLOR": colors.get(code),
                "permeability_class": _permeability(lithology_class(name)),
                "groundwater_potential": _groundwater(lithology_class(name)),
                "source": "Abbate, Sagri & Sassi (1994) 1:1,500,000 via UNESCO IHP-WINS (official vector)",
            },
        })

    if not features:
        raise ValueError("no usable geometries in geology source")

    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source": "Abbate, Sagri & Sassi (1994) Geological Map of Somalia 1:1,500,000",
            "distributor": "UNESCO IHP-WINS (digitized SHP/GPKG)",
            "crs": "EPSG:4326 (converted from EPSG:4210 Arc 1960)",
            "features": len(features),
            "colors": "original cartographic SLD coding",
        },
        "features": features,
    }
    out.write_text(json.dumps(payload, separators=(",", ":")))
    return out


def _permeability(lith: str) -> str:
    return {
        "Limestone / Dolomite": "Moderate (karstic)",
        "Sandstone / Quartzite": "Moderate to high",
        "Volcanic / Basalt": "Low (fractured)",
        "Alluvium / Sediments": "High",
        "Precambrian Basement / Granite": "Low",
    }.get(lith, "Moderate")


def _groundwater(lith: str) -> str:
    return {
        "Limestone / Dolomite": "Moderate (karst springs)",
        "Sandstone / Quartzite": "Moderate to high",
        "Volcanic / Basalt": "Low to moderate",
        "Alluvium / Sediments": "High",
        "Precambrian Basement / Granite": "Low (weathered zones only)",
    }.get(lith, "Moderate")
