"""Live FAO SWALIM soil-pH proxy: official WFS polygons -> harmonized GeoJSON.

The official FAO SWALIM GeoServer (https://spatial.faoswalim.org/geoserver/ows)
publishes Somalia soil maps as classification polygons (soil series, land units,
WRB 2022 reference groups). The laboratory pH measurements behind those surveys
are published in SWALIM reports, not as WFS attributes. This service therefore:

1. Fetches the live soil polygons straight from the official WFS endpoint
   (server-side, so browser CORS never applies) with retry/timeout handling.
2. Harmonizes a screening ``pH_VALUE`` from the published WRB/soil-series
   classification of each polygon, classifies it with the portal soil-reaction
   scheme and attaches texture + crop-suitability advisories.
3. Caches the merged FeatureCollection in-process (TTL) and falls back to the
   packaged normalized snapshot when the WFS is unreachable.

pH values are screening estimates derived from the soil classification and are
flagged as such in the response metadata — they are not a substitute for
laboratory confirmation.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from app.services.swalim import SWALIM_WFS

# ---------------------------------------------------------------------------
# Official layer catalogue (WFS type names). Failures of individual candidate
# layers are tolerated; override with AGRI_SWALIM_SOIL_PH_LAYERS="a,b".
# ---------------------------------------------------------------------------
SOIL_PH_LAYERS: dict[str, str] = {
    # National Somalia soil map 1:250k (SWALIM 2020). The CSW metadata advertises
    # geonode:som_soil_250k (bbox = whole country) but the public WFS has not
    # exposed it recently; kept as a tolerated candidate so it lights up the
    # moment SWALIM re-publishes it. National coverage is otherwise guaranteed
    # by the packaged generalized base (see get_swalim_soil_ph).
    "som_soil_250k": "geonode:som_soil_250k",
    # National-north semi-detailed soil map 1:100k (soil series + prefix).
    "soil_100k_n": "geonode:soil_100k_n_faoswalim",
    # Semi-detailed riverine soil surveys 1:25k (land units + WRB 2022).
    "afgooye_soil": "geonode:afgooye_final_soil_map_utm38n",
    "belet_weyne_soil": "geonode:belet_weyne_final_soil_map_utm38n",
    "jowhar_soil": "geonode:jowhar_final_soil_map_utm38n",
    "kismaayo_soil": "geonode:kismaayo_final_soil_map_utm38n",
    "luuq_soil": "geonode:luuq_final_soil_map_utm38n",
}

# Portal soil-reaction highlight scheme (labels, intervals and exact hexes).
PH_CLASSES: list[dict[str, Any]] = [
    {"label": "Ultra / Strongly Acidic", "min": None, "max": 5.5, "color": "#B91C1C", "range": "pH < 5.5"},
    {"label": "Moderately Acidic", "min": 5.5, "max": 6.5, "color": "#F59E0B", "range": "pH 5.5 – 6.4"},
    {"label": "Neutral", "min": 6.5, "max": 7.4, "color": "#84CC16", "range": "pH 6.5 – 7.3"},
    {"label": "Slightly Alkaline", "min": 7.4, "max": 7.9, "color": "#10B981", "range": "pH 7.4 – 7.8"},
    {"label": "Moderately Alkaline", "min": 7.9, "max": 8.5, "color": "#06B6D4", "range": "pH 7.9 – 8.4"},
    {"label": "Strongly Alkaline", "min": 8.5, "max": None, "color": "#6366F1", "range": "pH > 8.4"},
]

# Representative topsoil pH per WRB reference group / qualifier, aligned with
# the FAO-HWSD Somalia screening values used across this repository. WRB
# reference groups dominate; qualifiers only apply when no group is named.
_WRB_PH: list[tuple[str, float]] = [
    # Reference groups (checked first: "Calcaric Fluvisols" is a Fluvisol).
    ("solonchak", 8.8),
    ("fluvisol", 7.1),
    ("arenosol", 6.7),
    ("chromic vertisol", 5.6),
    ("vertisol", 6.2),
    ("cambisol", 6.2),
    ("luvisol", 6.4),
    ("planosol", 6.0),
    ("gleysol", 6.6),
    ("regosol", 6.6),
    ("leptosol", 6.9),
    ("calcisol", 7.9),
    ("gypsisol", 7.9),
    # Qualifier fallbacks (no reference group in the classification text).
    ("salic", 8.8),
    ("gypsic", 7.9),
    ("calcic", 7.9),
    ("calcaric", 7.9),
]
_DEFAULT_PH = 7.2

_WRB_TEXTURE: list[tuple[str, str]] = [
    ("vertisol", "Clay (cracking)"),
    ("solonchak", "Saline silty clay"),
    ("fluvisol", "Silt loam (alluvium)"),
    ("arenosol", "Sand"),
    ("calcisol", "Loam"),
    ("gypsisol", "Gypsiferous loam"),
    ("cambisol", "Sandy loam"),
    ("regosol", "Sandy loam"),
    ("leptosol", "Gravelly sandy loam"),
    ("gleysol", "Mottled silt loam"),
]
_DEFAULT_TEXTURE = "Variable (survey land unit)"

_SALINE = re.compile(r"salic|solonchak|salt|salin", re.I)
_FRAME_KEYS = ("is_frame", "extent_outline", "is_bbox", "layer_frame", "tile_boundary")
_FRAME_HINT = re.compile(r"extent|frame|bbox|tile", re.I)

_CACHE_KEY = "soil-ph"
_CACHE: dict[str, tuple[float, dict[str, Any], str]] = {}
_LOCK = asyncio.Lock()


def classify_ph(value: float) -> dict[str, Any]:
    """Return the portal reaction class (label/color) for a pH value."""
    for cls in PH_CLASSES:
        if (cls["min"] is None or value >= cls["min"]) and (cls["max"] is None or value < cls["max"]):
            return cls
    return PH_CLASSES[-1]


def _derive_ph(classification_text: str) -> float:
    text = (classification_text or "").lower()
    for keyword, ph in _WRB_PH:
        if keyword in text:
            return ph
    return _DEFAULT_PH


def _derive_texture(classification_text: str) -> str:
    text = (classification_text or "").lower()
    for keyword, texture in _WRB_TEXTURE:
        if keyword in text:
            return texture
    return _DEFAULT_TEXTURE


def suitability_warnings(ph: float, classification_text: str = "") -> list[str]:
    """Crop/land-use advisories keyed to the harmonized reaction class."""
    text = (classification_text or "").lower()
    warnings: list[str] = []
    if ph < 5.5:
        warnings.append(
            "Strong acidity: lime before cropping; Al/Mn toxicity risk for maize, "
            "sorghum and most legumes; cowpea and teff are more tolerant."
        )
    elif ph < 6.5:
        warnings.append(
            "Moderately acidic reaction: phosphorus and molybdenum availability drops; "
            "lime-responsive crops (maize, lucerne) will benefit from amelioration."
        )
    elif ph < 7.4:
        warnings.append("Near-ideal reaction: full nutrient availability for most crops.")
    elif ph < 7.9:
        warnings.append("Slight alkalinity: monitor iron, zinc and manganese availability.")
    elif ph < 8.5:
        warnings.append(
            "Moderate alkalinity: phosphorus fixation and micronutrient lock-out "
            "risk; gypsum helps on sodic patches; test EC before irrigating."
        )
    else:
        warnings.append(
            "Strong alkalinity / sodicity risk: restrict to salt-tolerant uses "
            "(date palm, ber/jujube, salvadora forage) and reclaim before field crops."
        )
    if _SALINE.search(text):
        warnings.append(
            "Saline unit flagged by the survey classification: check EC and "
            "groundwater quality; avoid salinity-sensitive crops (beans, citrus)."
        )
    return warnings


def _is_bbox_geometry(geometry: Any) -> bool:
    """True for perfect axis-aligned 4-corner rectangles (grid/envelope bounds)."""
    if not isinstance(geometry, dict):
        return False
    gtype, coords = geometry.get("type"), geometry.get("coordinates")
    rings_out: list[list] = []
    if gtype == "Polygon":
        rings_out = coords or []
    elif gtype == "MultiPolygon":
        rings_out = [ring for poly in (coords or []) for ring in poly]
    for ring in rings_out:
        pts = [tuple(pt) for pt in (ring or [])][:-1]  # drop closure point
        if len(pts) == 4:
            xs = {pt[0] for pt in pts}
            ys = {pt[1] for pt in pts}
            if len(xs) == 2 and len(ys) == 2:
                return True
    return False


def _is_thematic_polygon(geometry: Any) -> bool:
    """Only internal Polygon / MultiPolygon geometries are ever rendered."""
    return isinstance(geometry, dict) and geometry.get("type") in ("Polygon", "MultiPolygon")


def _frame_like(props: dict[str, Any]) -> bool:
    if any(props.get(key) for key in _FRAME_KEYS):
        return True
    kind = str(props.get("feature_type") or props.get("TYPE") or props.get("kind") or props.get("role") or "")
    return bool(_FRAME_HINT.search(kind))


def _wfs_url(typename: str, max_features: int) -> str:
    return SWALIM_WFS + "?" + urlencode({
        "service": "WFS", "version": "1.0.0", "request": "GetFeature",
        "typename": typename, "outputFormat": "application/json",
        "srsName": "EPSG:4326", "maxFeatures": str(max_features),
    })


def _active_layers() -> dict[str, str]:
    override = os.getenv("AGRI_SWALIM_SOIL_PH_LAYERS")
    if override:
        names = [n.strip() for n in override.split(",") if n.strip()]
        return {f"custom_{i}": n for i, n in enumerate(names)}
    return SOIL_PH_LAYERS


def _swalim_text(props: dict[str, Any]) -> str:
    return " ".join(
        str(props.get(key) or "")
        for key in ("wrb_2022", "wrB_2022", "soil", "prefix", "lu_desc", "lu", "subsystem", "system")
    )


def transform_swalim_feature(feature: dict[str, Any], source_layer: str) -> dict[str, Any] | None:
    """Normalize one official SWALIM soil polygon into the portal pH schema."""
    props = feature.get("properties") or {}
    if _frame_like(props) or _is_bbox_geometry(feature.get("geometry")) or not _is_thematic_polygon(feature.get("geometry")):
        return None
    text = _swalim_text(props)
    wrb = str(props.get("wrb_2022") or "").strip() or None
    series = str(props.get("soil") or "").strip() or None
    prefix = str(props.get("prefix") or "").strip() or None
    series_name = series or (wrb or (prefix or "SWALIM soil unit")).strip()
    ph = _derive_ph(text)
    cls = classify_ph(ph)
    unit_name = str(props.get("lu_desc") or "").strip() or series_name
    return {
        "type": "Feature",
        "geometry": feature.get("geometry"),
        "properties": {
            "feature_type": "swalim_soil_ph",
            "source_layer": source_layer,
            "unit_name": unit_name,
            "unit_code": props.get("lu") or props.get("subsystem"),
            "series_name": series_name,
            "wrb_class": wrb,
            "pH_VALUE": ph,
            "PH_CLASS": cls["label"],
            "PH_COLOR": cls["color"],
            "SOIL_TEXTURE": _derive_texture(text),
            "DRAINAGE_CLASS": "Not surveyed",
            "AREA_HA": round(props["area_ha"], 1) if isinstance(props.get("area_ha"), (int, float)) else None,
            "SUITABILITY_WARNINGS": suitability_warnings(ph, text),
        },
    }


def _transform_fallback_feature(feature: dict[str, Any], source_tag: str = "packaged_snapshot") -> dict[str, Any] | None:
    """Normalize a packaged-snapshot polygon into the same live schema."""
    props = feature.get("properties") or {}
    if _frame_like(props) or _is_bbox_geometry(feature.get("geometry")) or not _is_thematic_polygon(feature.get("geometry")):
        return None
    ph = props.get("pH_VALUE") if isinstance(props.get("pH_VALUE"), (int, float)) else props.get("ph")
    try:
        ph = float(ph)
    except (TypeError, ValueError):
        ph = _DEFAULT_PH
    cls = classify_ph(ph)
    classification_text = f"{props.get('SOIL_TYPE', '')} {props.get('FAO_UNIT', '')}"
    texture = props.get("SOIL_TEXTURE") or _derive_texture(classification_text)
    warnings = suitability_warnings(ph, classification_text)
    ec = props.get("SALINITY_EC")
    if (isinstance(ec, (int, float)) and ec >= 4.0  # moderately saline threshold (dS/m)
            and not any("saline" in w.lower() for w in warnings)):
        warnings.append(
            "Saline unit flagged by measured EC >= 4 dS/m: check groundwater quality; "
            "avoid salinity-sensitive crops (beans, citrus)."
        )
    return {
        "type": "Feature",
        "geometry": feature.get("geometry"),
        "properties": {
            "feature_type": "swalim_soil_ph",
            "source_layer": source_tag,
            "unit_name": props.get("unit") or "Somalia soil unit",
            "unit_code": props.get("FAO_UNIT"),
            "series_name": props.get("SOIL_TYPE") or props.get("FAO_UNIT") or "SWALIM soil unit",
            "wrb_class": props.get("SOIL_TYPE") or props.get("FAO_UNIT"),
            "pH_VALUE": ph,
            "PH_CLASS": cls["label"],  # always the portal 6-class label (matches legend)
            "PH_COLOR": cls["color"],
            "SOIL_TEXTURE": texture,
            "DRAINAGE_CLASS": props.get("DRAINAGE_CLASS") or "Not surveyed",
            "AREA_HA": None,
            "SALINITY_EC": props.get("SALINITY_EC"),
            "SUITABILITY_WARNINGS": warnings,
        },
    }


def _collection(features: list[dict[str, Any]], source: str, layers: dict[str, int]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": "FAO SWALIM Somalia Soil pH Map (harmonized)",
        "metadata": {
            "source": source,
            "service": "FAO SWALIM spatial portal (official OGC WFS)",
            "wfs_endpoint": SWALIM_WFS,
            "layers": layers,
            "feature_count": len(features),
            "ph_classes": PH_CLASSES,
            "provenance_note": (
                "National coverage = generalized national base + official SWALIM WFS detail "
                "insets (maxFeatures=50000, unpaginated). pH_VALUE is a screening estimate "
                "harmonized from the SWALIM WRB / soil-series classification; confirm with "
                "laboratory analysis."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "features": features,
    }


async def get_swalim_soil_ph(
    client: httpx.AsyncClient,
    fallback_geojson: Path,
    cache_ttl_s: int = 3600,
    force_refresh: bool = False,
    max_features: int = 50000,
) -> tuple[dict[str, Any], str]:
    """Merged SWALIM soil-pH layer with TTL cache: national generalized base +
    official WFS detail insets, guaranteeing 100% Somalia extent."""
    now = time.monotonic()
    cached = _CACHE.get(_CACHE_KEY)
    if cached and not force_refresh and now - cached[0] < cache_ttl_s:
        return cached[1], "cache"

    async with _LOCK:
        cached = _CACHE.get(_CACHE_KEY)
        if cached and not force_refresh and time.monotonic() - cached[0] < cache_ttl_s:
            return cached[1], "cache"

        features: list[dict[str, Any]] = []
        layer_counts: dict[str, int] = {}
        for key, typename in _active_layers().items():
            try:
                response = await client.get(_wfs_url(typename, max_features), timeout=30.0)
                response.raise_for_status()
                payload = response.json()
                raw = payload.get("features") if isinstance(payload, dict) else None
                if raw is None:
                    raise ValueError(f"{typename}: not a GeoJSON FeatureCollection")
                kept = 0
                for feature in raw:
                    transformed = transform_swalim_feature(feature, typename)
                    if transformed is not None and transformed.get("geometry"):
                        features.append(transformed)
                        kept += 1
                layer_counts[typename] = kept
            except (httpx.HTTPError, ValueError, json.JSONDecodeError):
                continue  # tolerate per-layer outages; merge whatever published

        try:
            snapshot = json.loads(fallback_geojson.read_text(encoding="utf-8"))
            base_features = [
                t for t in (_transform_fallback_feature(f, source_tag="national_base")
                            for f in snapshot.get("features", []))
                if t is not None and t.get("geometry")
            ]
        except (OSError, json.JSONDecodeError) as exc:
            base_features = []
            if not features:
                raise ValueError(f"SWALIM WFS unreachable and snapshot unreadable: {exc}") from exc

        # National generalized base first (renders beneath), live WFS detail insets
        # on top: full-country coverage plus official survey polygons where published.
        layer_counts = {"national_base": len(base_features), **layer_counts}
        features = base_features + features

        if len(features) > len(base_features):
            source = "official-wfs"
        elif base_features:
            source = "static-fallback"
        else:
            raise ValueError("SWALIM WFS unreachable and no snapshot features available")
        data = _collection(features, source, layer_counts)

        _CACHE[_CACHE_KEY] = (time.monotonic(), data, source)
        return data, source
