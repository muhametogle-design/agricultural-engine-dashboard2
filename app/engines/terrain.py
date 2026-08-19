"""Terrain factor providers for the well-siting MCE.

A field rarely ships with a DEM, so terrain is a PLUGGABLE provider:

  * NullTerrainProvider       - no terrain data: slope/flow factors report
                                "unavailable" and the MCE re-normalizes weights;
  * RasterDemTerrainProvider  - local DEM GeoTIFF (rasterio, optional dep):
                                gradient-based slope (%) + D8 flow accumulation.

The D8 implementation is a dependency-free approximation intended for
screening. At production scale swap in richdem/whiteboxtools behind the
same protocol.
"""
from __future__ import annotations

from typing import Protocol

import numpy as np
from pyproj import Transformer
from shapely.geometry.base import BaseGeometry

from app.core.errors import ConfigError


class TerrainProvider(Protocol):
    def slope_flow_grids(
        self,
        boundary_utm: BaseGeometry,
        xs: np.ndarray,
        ys: np.ndarray,
        epsg: int,
        cell_m: float,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Return (slope_percent, flow_accumulation_cells) arrays or (None, None)."""
        ...


class NullTerrainProvider:
    def slope_flow_grids(self, boundary_utm, xs, ys, epsg, cell_m):
        return None, None


def _d8_flow_accumulation(dem: np.ndarray) -> np.ndarray:
    """D8 contributing-cell count. NaN cells act as sinks (no outflow)."""
    ny, nx = dem.shape
    acc = np.ones((ny, nx), dtype=float)
    order = np.argsort(dem, axis=None)[::-1]  # highest first
    for flat in order:
        y, x = divmod(int(flat), nx)
        z = dem[y, x]
        if np.isnan(z):
            continue
        best = None
        best_z = z
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                yy, xx = y + dy, x + dx
                if 0 <= yy < ny and 0 <= xx < nx:
                    zn = dem[yy, xx]
                    if not np.isnan(zn) and zn < best_z:
                        best_z, best = zn, (yy, xx)
        if best is not None:
            acc[best] += acc[y, x]
    return acc


class RasterDemTerrainProvider:
    def __init__(self, dem_path: str):
        try:
            import rasterio  # noqa: F401
        except ImportError as exc:
            raise ConfigError(
                "rasterio is required for DEM terrain analysis; "
                "install the optional dependency or unset AGRI_TERRAIN__DEM_PATH"
            ) from exc
        self.dem_path = dem_path

    def slope_flow_grids(self, boundary_utm, xs, ys, epsg, cell_m):
        import rasterio
        from shapely.geometry import box

        minx, miny, maxx, maxy = boundary_utm.bounds
        pad = 3 * cell_m
        tile_xs = np.arange(minx - pad, maxx + pad, cell_m)
        tile_ys = np.arange(miny - pad, maxy + pad, cell_m)
        gx, gy = np.meshgrid(tile_xs, tile_ys)

        with rasterio.open(self.dem_path) as ds:
            tf = Transformer.from_crs(f"EPSG:{epsg}", ds.crs, always_xy=True)
            lonlat_x, lonlat_y = tf.transform(gx.ravel(), gy.ravel())
            samples = np.array(
                [s[0] if s.size else np.nan
                 for s in ds.sample(zip(lonlat_x.tolist(), lonlat_y.tolist()), masked=True)],
                dtype=float,
            ).reshape(gx.shape)
            nodata = ds.nodata
        if nodata is not None:
            samples[samples == nodata] = np.nan

        dem = np.where(np.isfinite(samples), samples, np.nan)
        gy_grad, gx_grad = np.gradient(np.nan_to_num(dem, nan=np.nanmedian(dem)), cell_m)
        slope_tile = np.hypot(gx_grad, gy_grad) * 100.0  # rise/run -> percent
        flow_tile = _d8_flow_accumulation(dem)

        # Sample the tiles at the analysis grid points (nearest cell)
        ix = np.clip(((xs - tile_xs[0]) / cell_m).round().astype(int), 0, len(tile_xs) - 1)
        iy = np.clip(((ys - tile_ys[0]) / cell_m).round().astype(int), 0, len(tile_ys) - 1)
        return slope_tile[iy, ix], flow_tile[iy, ix]


def build_terrain_provider(dem_path: str | None) -> TerrainProvider:
    return RasterDemTerrainProvider(dem_path) if dem_path else NullTerrainProvider()
