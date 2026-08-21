"""HWSD v2.0 offline soil sampling (FAO/IIASA Harmonized World Soil Database).

The HWSD v2.0 dataset ships as a 30 arc-second (~1 km) global raster of Soil
Mapping Unit (SMU) ids linked to a relational attribute database. This service
samples the raster at a point and resolves the topsoil attributes (HWSD2 layer
SEQUENCE 1 = 0-20 cm) through an exported attribute CSV, so the Laboratory
Analytics panel can auto-generate a regional baseline when no field-kit
measurements exist.

Design contract
---------------
* Manual laboratory entries always win — this is a fallback source.
* The service degrades gracefully: missing raster, missing rasterio, or a
  sample outside the grid all return ``None`` instead of raising.
* Numerical guards: HWSD attribute scaling is not uniform across releases, so
  values are sanity-clamped (pH > 14 is assumed to be stored x10, etc.).
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Optional

try:  # rasterio is a heavy optional; unavailable envs must still boot.
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform as crs_transform
except ImportError:  # pragma: no cover - depends on deployment image
    rasterio = None
    CRS = None
    crs_transform = None

from app.core.logging import get_logger

log = get_logger(__name__)

# HWSD v2 layer-attribute candidates (left-to-right first match wins).
COL_SMU = ["HWSD2_SMU_ID", "MU_GLOBAL", "SMU_ID", "MU_ID", "ID"]
COL_SEQ = ["SEQUENCE", "LAYER_NO", "TOPSOIL"]
COL_TOPDEP = ["TOPDEP", "TOP_DEP", "TOP_DEPTH"]
COL_PH = ["PH", "PH_WATER", "PH_H2O", "T_PH_H2O", "PH_CA_CL", "PH_CACL2", "ph"]
COL_N = ["TN", "N", "TOTAL_N", "NITROGEN", "T_N"]
COL_OC = ["OC", "SOC", "ORG_CARBON", "T_OC", "OC_TDJ"]
COL_CEC = ["ECEC", "CEC_SOIL", "CEC", "T_CEC_SOIL"]
COL_CLAY = ["CLAY", "T_CLAY"]
COL_SAND = ["SAND", "T_SAND"]
COL_SILT = ["SILT", "T_SILT"]
COL_GRAVEL = ["GRAVEL", "T_GRAVEL"]
COL_WRB = ["WRB4", "WRB", "FAO90", "SU_SYM90", "SOIL"]

NODATA_SENTINELS = {-32768, -32767, -9999.0, -999.0, -9.0, 255, 65535}


def _pick(row: dict, candidates: list[str]) -> Optional[str]:
    for key in candidates:
        if key in row and str(row[key]).strip() not in ("", "None"):
            return str(row[key]).strip()
    # case-insensitive fallback pass (CSV exports differ in casing)
    lower = {c.lower(): c for c in candidates}
    for key in row:
        lk = key.strip().lower()
        if lk in lower and str(row[key]).strip() not in ("", "None"):
            return str(row[key]).strip()
    return None


def _num(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    try:
        v = float(raw.replace(",", "."))
    except (ValueError, AttributeError):
        return None
    if v in NODATA_SENTINELS or v < -998:
        return None
    return v


def _norm_ph(raw: Optional[str]) -> Optional[float]:
    v = _num(raw)
    if v is None:
        return None
    if v > 14:  # HWSD exports frequently store pH x10
        v /= 10.0
    if not 3.0 <= v <= 14.0:
        return None
    return round(v, 1)


def _norm_pct(raw: Optional[str], ceiling: float) -> Optional[float]:
    """Percentage columns heal by descending scale factors until plausible."""
    v = _num(raw)
    if v is None:
        return None
    for f in (1.0, 0.1, 0.01):
        if 0 <= v * f <= ceiling:
            return round(v * f, 2)
    return None


class HWSDService:
    """Point-samples the HWSD raster and joins to topsoil attributes."""

    def __init__(self, raster_path: Optional[Path], attrs_path: Optional[Path] = None):
        self.raster_path = Path(raster_path) if raster_path else None
        self.attrs_path = Path(attrs_path) if attrs_path else None
        self._ds = None  # rasterio.DatasetReader, opened lazily
        self._attrs: Optional[dict[int, dict[str, Any]]] = None

    # ------------------------------------------------------------------ boot
    @property
    def available(self) -> bool:
        return bool(
            rasterio is not None
            and self.raster_path is not None
            and self.raster_path.exists()
        )

    def _dataset(self):
        if self._ds is None:
            self._ds = rasterio.open(self.raster_path)
            log.info("hwsd raster loaded: %s (%sx%s)", self.raster_path,
                     self._ds.width, self._ds.height)
        return self._ds

    def _attributes(self) -> dict[int, dict[str, Any]]:
        if self._attrs is not None:
            return self._attrs
        self._attrs = {}
        if not self.attrs_path or not self.attrs_path.exists():
            log.warning("hwsd attribute CSV missing: %s", self.attrs_path)
            return self._attrs
        with open(self.attrs_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                smu_raw = _pick(row, COL_SMU)
                smu = _num(smu_raw)
                if smu is None:
                    continue
                seq = _pick(row, COL_SEQ)
                # keep only the dominant soil unit (SEQUENCE 1)
                if seq is not None and _num(seq) not in (None, 1.0):
                    continue
                topdep = _pick(row, COL_TOPDEP)
                # and only the topsoil depth band (0-20 cm = TOPDEP 0)
                if topdep is not None and _num(topdep) not in (None, 0.0):
                    continue
                key = int(smu)
                if key in self._attrs:  # first topsoil row wins
                    continue
                self._attrs[key] = {
                    "ph": _norm_ph(_pick(row, COL_PH)),
                    "nitrogen_pct": _norm_pct(_pick(row, COL_N), 1.0),
                    "oc_pct": _norm_pct(_pick(row, COL_OC), 15.0),
                    "cec": _norm_pct(_pick(row, COL_CEC), 60.0),
                    "clay_pct": _norm_pct(_pick(row, COL_CLAY), 100.0),
                    "sand_pct": _norm_pct(_pick(row, COL_SAND), 100.0),
                    "silt_pct": _norm_pct(_pick(row, COL_SILT), 100.0),
                    "wrb": _pick(row, COL_WRB),
                }
        log.info("hwsd attribute table loaded: %d mapping units", len(self._attrs))
        return self._attrs

    # -------------------------------------------------------------- sampling
    def _read_smu(self, lon: float, lat: float) -> Optional[int]:
        ds = self._dataset()
        x, y = lon, lat
        if ds.crs and ds.crs != CRS.from_epsg(4326):
            xs, ys = crs_transform(CRS.from_epsg(4326), ds.crs, [lon], [lat])
            x, y = xs[0], ys[0]
        if not (ds.bounds.left <= x <= ds.bounds.right
                and ds.bounds.bottom <= y <= ds.bounds.top):
            return None
        value = next(ds.sample([(x, y)]))[0]
        smu = int(value)
        return smu if smu > 0 and smu not in NODATA_SENTINELS else None

    def sample(self, lat: float, lon: float) -> Optional[dict[str, Any]]:
        """Topsoil sample at WGS84 point; ``None`` when outside the grid.

        Land-cover placeholder pixels (e.g. SMU 7001 Technosols) carry no
        profile, so the search expands in growing square rings until it finds
        the nearest pixel whose mapping unit has topsoil data (<= ~4 km).
        """
        if not self.available:
            return None
        attrs_map = self._attributes()
        try:
            reslat, reslon = None, None
            chosen = self._read_smu(lon, lat)
            rings = 0
            if chosen is None or chosen not in attrs_map or attrs_map[chosen].get("ph") is None:
                chosen = None
                ds = self._dataset()
                deg = max(abs(ds.res[0]), abs(ds.res[1]))
                for ring in range(1, 5):      # 1 km grid -> ~4 km furthest
                    for dx in range(-ring, ring + 1):
                        for dy in (-ring, ring):
                            cand = self._read_smu(lon + dx * deg, lat + dy * deg)
                            if cand and cand in attrs_map and attrs_map[cand].get("ph") is not None:
                                chosen, reslon, reslat, rings = cand, lon + dx * deg, lat + dy * deg, ring
                                break
                        if chosen: break
                    if chosen: break
                    if not chosen:  # also probe the ring's vertical sides
                        for dy in range(-ring + 1, ring):
                            for dx in (-ring, ring):
                                cand = self._read_smu(lon + dx * deg, lat + dy * deg)
                                if cand and cand in attrs_map and attrs_map[cand].get("ph") is not None:
                                    chosen, reslon, reslat, rings = cand, lon + dx * deg, lat + dy * deg, ring
                                    break
                            if chosen: break
            if chosen is None:
                return None
            smu = chosen
        except Exception as exc:  # corrupt raster / IO issues must not 500
            log.warning("hwsd raster sample failed at (%s, %s): %s", lat, lon, exc)
            return None

        attrs = attrs_map.get(smu, {})
        oc = attrs.get("oc_pct")
        out = {
            "mu_id": smu,
            "ph": attrs.get("ph"),
            # Walkley-Black SOC -> SOM conversion (x1.724)
            "om_pct": round(oc * 1.724, 2) if oc else None,
            "nitrogen_pct": attrs.get("nitrogen_pct"),
            "cec": attrs.get("cec"),
            "clay_pct": attrs.get("clay_pct"),
            "sand_pct": attrs.get("sand_pct"),
            "silt_pct": attrs.get("silt_pct"),
            "wrb": attrs.get("wrb"),
            "layer": "0-20 cm (topsoil)",
            "source": "FAO/IIASA HWSD v2.0 (1 km)",
        }
        if rings:
            out["nearest_km"] = round(rings * max(abs(self._dataset().res[0]), abs(self._dataset().res[1])) * 111.0, 1)
        return out
