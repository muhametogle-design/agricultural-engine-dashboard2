"""Well-siting decision engine: weighted multi-criteria evaluation (MCE).

Factors (each re-scaled to [0, 1]) on an adaptive UTM analysis grid:
  f_ves    - aquifer prospectivity: IDW surface of VES aquifer-quality scores
  f_slope  - drillability/infiltration: full score <=2% slope, zero >=15%
  f_flow   - groundwater convergence: percentile rank of D8 flow accumulation

Weights re-normalize over AVAILABLE factors (e.g. no DEM -> VES-only).
The composite argmax, filtered by a separation constraint, yields the
optimal well point plus ranked alternatives. Drilling depth derives from
the nearest sounding's estimated water table plus a penetration margin.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.config import Settings
from app.core.logging import get_logger
from app.core.spatial import (
    _transformer,
    adaptive_grid,
    geom_from_geojson,
    idw_interpolate,
    to_utm,
    utm_epsg,
    utm_point_to_wgs84,
)
from app.engines.terrain import TerrainProvider

log = get_logger(__name__)


@dataclass
class WellSitingResult:
    optimal_lon: float | None
    optimal_lat: float | None
    composite_score: float | None
    recommended_drilling_depth_m: float | None
    factor_weights_used: dict
    candidates: list[dict] = field(default_factory=list)
    factor_summary: dict = field(default_factory=dict)
    coverage: dict = field(default_factory=dict)
    method: str = "weighted_linear_combination_mce_v1"

    def optimal_point_geojson(self) -> dict | None:
        if self.optimal_lon is None:
            return None
        return {"type": "Point", "coordinates": [self.optimal_lon, self.optimal_lat]}


def _slope_score(slope_pct: np.ndarray, full: float, zero: float) -> np.ndarray:
    return np.clip((zero - slope_pct) / max(zero - full, 1e-9), 0.0, 1.0)


def _flow_score(flowacc: np.ndarray) -> np.ndarray:
    """Percentile rank of log1p(flow accumulation) in [0, 1]; NaN preserved."""
    logged = np.log1p(np.where(np.isfinite(flowacc), flowacc, np.nan))
    valid = np.isfinite(logged)
    out = np.full(logged.shape, np.nan)
    if not valid.any():
        return out
    vals = logged[valid]
    ranks = np.empty(len(vals), dtype=float)
    ranks[vals.argsort()] = np.arange(len(vals), dtype=float) / max(len(vals) - 1, 1)
    out[valid] = ranks
    return out


def run_well_siting(
    boundary_geojson: dict,
    ves_surveys: list[dict],
    settings: Settings,
    terrain: TerrainProvider,
) -> WellSitingResult:
    boundary = geom_from_geojson(boundary_geojson)
    centroid = boundary.centroid
    epsg = utm_epsg(centroid.x, centroid.y)
    boundary_utm = to_utm(boundary, epsg)

    cfg = settings.well_siting
    xs, ys, cell_m = adaptive_grid(boundary_utm, cfg.target_grid_cells, cfg.max_grid_cells)
    n_cells = len(xs)
    log.info("well siting grid: %d cells @ %.1f m", n_cells, cell_m)

    factors: dict[str, np.ndarray] = {}
    weights: dict[str, float] = {}

    # --- Factor 1: VES aquifer prospectivity (IDW over sounding scores) ---
    usable = [v for v in ves_surveys if v.get("aquifer_quality_score") is not None]
    if len(usable) >= cfg.min_ves_points:
        tf = _transformer(4326, epsg)
        px = np.array([tf.transform(v["lon"], v["lat"])[0] for v in usable])
        py = np.array([tf.transform(v["lon"], v["lat"])[1] for v in usable])
        vals = np.array([float(v["aquifer_quality_score"]) for v in usable])
        factors["ves"] = idw_interpolate(px, py, vals, xs, ys, power=cfg.idw_power)
        weights["ves"] = cfg.w_ves
    # --- Factors 2+3: terrain ---
    slope, flow = terrain.slope_flow_grids(boundary_utm, xs, ys, epsg, cell_m)
    if slope is not None and np.isfinite(slope).any():
        s = np.nan_to_num(slope, nan=cfg.slope_zero_score_pct)
        factors["slope"] = _slope_score(s, cfg.slope_full_score_pct, cfg.slope_zero_score_pct)
        weights["slope"] = cfg.w_slope
    if flow is not None and np.isfinite(flow).any():
        f = _flow_score(flow)
        factors["flowacc"] = np.nan_to_num(f, nan=0.5)
        weights["flowacc"] = cfg.w_flowacc

    coverage = {
        "ves_surveys_used": len(usable),
        "terrain_factors_available": ("slope" in factors),
        "analysis_grid": {"cells": n_cells, "cell_size_m": round(cell_m, 2), "epsg": epsg},
    }

    if not factors:
        log.warning("well siting: no factors available (no VES, no terrain)")
        return WellSitingResult(
            None, None, None, cfg.default_drilling_depth_m, {},
            coverage={**coverage, "warning": "no decision factors available"},
        )

    wsum = sum(weights.values())
    weights = {k: v / wsum for k, v in weights.items()}
    composite = np.zeros(n_cells)
    for name, f in factors.items():
        composite += weights[name] * np.nan_to_num(f, nan=0.0)

    # Candidate extraction with spatial separation
    separation_m = 3.0 * cell_m
    available = np.ones(n_cells, dtype=bool)
    candidates: list[dict] = []
    for _ in range(5):
        masked = np.where(available, composite, -np.inf)
        idx = int(np.argmax(masked))
        if not np.isfinite(masked[idx]):
            break
        lon, lat = utm_point_to_wgs84(float(xs[idx]), float(ys[idx]), epsg)
        candidates.append({
            "lon": round(lon, 7), "lat": round(lat, 7),
            "composite_score": round(float(composite[idx]), 4),
            "factor_scores": {k: round(float(np.nan_to_num(v, nan=0.0)[idx]), 4)
                              for k, v in factors.items()},
        })
        d = np.hypot(xs - xs[idx], ys - ys[idx])
        available &= d > separation_m

    best = candidates[0]
    depth = cfg.default_drilling_depth_m
    if usable:
        nearest = min(
            usable,
            key=lambda v: (v["lon"] - best["lon"]) ** 2 + (v["lat"] - best["lat"]) ** 2,
        )
        wt = nearest.get("estimated_water_table_depth_m")
        if wt is not None:
            wt = float(wt)
            depth = float(np.clip(wt + cfg.well_penetration_margin_m,
                                  cfg.min_drilling_depth_m, cfg.max_drilling_depth_m))

    factor_summary = {
        name: {
            "min": round(float(np.nanmin(np.nan_to_num(f, nan=np.nan))), 4),
            "mean": round(float(np.nanmean(np.nan_to_num(f, nan=np.nan))), 4),
            "max": round(float(np.nanmax(np.nan_to_num(f, nan=np.nan))), 4),
        }
        for name, f in factors.items()
    }

    return WellSitingResult(
        optimal_lon=best["lon"],
        optimal_lat=best["lat"],
        composite_score=best["composite_score"],
        recommended_drilling_depth_m=round(depth, 1),
        factor_weights_used=weights,
        candidates=candidates,
        factor_summary=factor_summary,
        coverage=coverage,
    )
