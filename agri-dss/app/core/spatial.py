"""CRS utilities, analysis grids, point sampling and IDW interpolation.

Separation of concerns: all geometry arrives as WGS84 GeoJSON (EPSG:4326);
every metric operation (distance, area, slope, grids) is executed in a local
UTM zone chosen automatically from the field centroid.

Note: the far-north Norway/Svalbard UTM special cases are intentionally not
handled (agricultural focus is the tropics/sub-tropics).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry


@lru_cache(maxsize=256)
def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180.0) // 6.0) + 1
    zone = min(max(zone, 1), 60)
    return (32600 if lat >= 0 else 32700) + zone


@lru_cache(maxsize=512)
def _transformer(from_epsg: int, to_epsg: int) -> Transformer:
    return Transformer.from_crs(CRS.from_epsg(from_epsg), CRS.from_epsg(to_epsg), always_xy=True)


def to_utm(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    from shapely.ops import transform

    tf = _transformer(4326, epsg)
    return transform(tf.transform, geom)


def from_utm(geom: BaseGeometry, epsg: int) -> BaseGeometry:
    from shapely.ops import transform

    tf = _transformer(epsg, 4326)
    return transform(tf.transform, geom)


def circle_polygon_wgs84(lon: float, lat: float, radius_m: float, resolution: int = 64) -> dict:
    """Geodesically-buffered circular polygon returned as GeoJSON (EPSG:4326)."""
    epsg = utm_epsg(lon, lat)
    p_utm = to_utm(Point(lon, lat), epsg)
    poly_4326 = from_utm(p_utm.buffer(radius_m, resolution=resolution), epsg)
    return mapping(poly_4326)


def square_field_from_point(lon: float, lat: float, area_ha: float) -> dict:
    """Tap-a-point field creation: axis-aligned square of `area_ha` around the tap."""
    side_m = (area_ha * 10_000.0) ** 0.5
    epsg = utm_epsg(lon, lat)
    p = to_utm(Point(lon, lat), epsg)
    half = side_m / 2.0
    poly = Polygon(
        [(p.x - half, p.y - half), (p.x + half, p.y - half),
         (p.x + half, p.y + half), (p.x - half, p.y + half), (p.x - half, p.y - half)]
    )
    return mapping(from_utm(poly, epsg))


def geom_from_geojson(geojson: dict) -> BaseGeometry:
    return shape(geojson)


def adaptive_grid(
    boundary_utm: BaseGeometry, target_cells: int, max_cells: int
) -> tuple[np.ndarray, np.ndarray, float]:
    """Centroids of an analysis grid clipped to the boundary.

    Returns (xs, ys, cell_size_m). Cell size adapts so the number of cells
    stays within [~target_cells, max_cells].
    """
    minx, miny, maxx, maxy = boundary_utm.bounds
    span = max(maxx - minx, maxy - miny)
    # First guess: assume ~62% of the bbox is inside the field.
    cell = span / max((target_cells / 0.62) ** 0.5, 1.0)
    for _ in range(6):
        nx = max(int((maxx - minx) / cell), 1)
        ny = max(int((maxy - miny) / cell), 1)
        xs = minx + (np.arange(nx) + 0.5) * cell
        ys = miny + (np.arange(ny) + 0.5) * cell
        gx, gy = np.meshgrid(xs, ys)
        gx, gy = gx.ravel(), gy.ravel()
        # Vectorized containment test
        from shapely import contains_xy

        mask = contains_xy(boundary_utm, gx, gy)
        n = int(mask.sum())
        if n == 0:
            cell *= 0.5
            continue
        if n > max_cells:
            cell *= (n / max_cells) ** 0.5 * 1.02
            continue
        return gx[mask], gy[mask], cell
    return gx[mask], gy[mask], cell


def sample_points_in_polygon(boundary_utm: BaseGeometry, n_target: int) -> np.ndarray:
    """Stratified point samples (grid centroids) for polygon API aggregation."""
    xs, ys, _ = adaptive_grid(boundary_utm, target_cells=n_target, max_cells=n_target * 2)
    pts = np.column_stack([xs, ys])
    if len(pts) > n_target:
        idx = np.linspace(0, len(pts) - 1, n_target).round().astype(int)
        pts = pts[idx]
    return pts


def idw_interpolate(
    px: np.ndarray,
    py: np.ndarray,
    values: np.ndarray,
    gx: np.ndarray,
    gy: np.ndarray,
    power: float = 2.0,
) -> np.ndarray:
    """Inverse-distance-weighted interpolation of survey values onto a grid.

    Exact-hit handling: a grid point within a quarter cell of a sample takes
    the sample value directly (avoids division-by-zero spikes).
    """
    px = np.asarray(px, dtype=float)
    py = np.asarray(py, dtype=float)
    values = np.asarray(values, dtype=float)
    dx = gx[:, None] - px[None, :]
    dy = gy[:, None] - py[None, :]
    dist = np.hypot(dx, dy)
    min_dist = dist.min(axis=1)
    near = min_dist < 1e-6
    with np.errstate(divide="ignore"):
        w = 1.0 / np.power(dist, power)
    w[~np.isfinite(w)] = 0.0
    wsum = w.sum(axis=1)
    out = np.where(wsum > 0, (w * values[None, :]).sum(axis=1) / np.maximum(wsum, 1e-12), np.nan)
    if near.any():
        out[near] = values[dist[near].argmin(axis=1)]
    return out


def utm_point_to_wgs84(x: float, y: float, epsg: int) -> tuple[float, float]:
    tf = _transformer(epsg, 4326)
    lon, lat = tf.transform(x, y)
    return lon, lat
