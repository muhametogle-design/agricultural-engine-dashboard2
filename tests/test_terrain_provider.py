"""RasterDemTerrainProvider against a synthetic plane: slope must read ~5%,
flow accumulation must increase toward the low (west) edge."""
from __future__ import annotations

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from app.core.spatial import geom_from_geojson, to_utm, utm_epsg
from app.engines.terrain import RasterDemTerrainProvider
from tests.conftest import CENTER_LAT, CENTER_LON, make_square_polygon


def _write_plane_dem(tmp_path) -> str:
    """WGS84 plane: elevation falls 5 m per 100 m from east to west."""
    res_deg = 1 / 111_000 * 5  # ~5 m pixels
    w = h = 140  # spans ±~0.00315 deg around the centre, amply covering the field
    west = CENTER_LON - w * res_deg / 2
    north = CENTER_LAT + h * res_deg / 2
    xs = west + (np.arange(w) + 0.5) * res_deg
    # 5% west-to-east rise: dz/dx = 0.05 = 5566 m per degree of longitude
    zs = 100.0 + (xs - west) * 5566.0
    dem = np.repeat(zs[None, :], h, axis=0).astype("float32")
    path = tmp_path / "plane.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
        crs="EPSG:4326", transform=from_origin(west, north, res_deg, res_deg),
        nodata=-32767.0,
    ) as dst:
        dst.write(dem, 1)
    return str(path)


def test_provider_slope_and_flow_on_plane(tmp_path, settings):
    dem = _write_plane_dem(tmp_path)
    provider = RasterDemTerrainProvider(dem)
    boundary = geom_from_geojson(make_square_polygon(size_deg=0.002))
    epsg = utm_epsg(CENTER_LON, CENTER_LAT)
    b_utm = to_utm(boundary, epsg)
    cell = 20.0
    minx, miny, maxx, maxy = b_utm.bounds
    xs = minx + np.arange(int((maxx - minx) / cell)) * cell + cell / 2
    ys = miny + np.arange(int((maxy - miny) / cell)) * cell + cell / 2
    gx, gy = np.meshgrid(xs, ys)
    slope, flow = provider.slope_flow_grids(b_utm, gx.ravel(), gy.ravel(), epsg, cell)
    assert slope is not None and flow is not None
    assert np.isfinite(slope).all()
    assert 3.5 <= float(np.mean(slope)) <= 7.0  # ~5% plane (nearest-sample jitter)
    # east edge higher -> water accumulates toward the west edge
    flow2d = flow.reshape(gx.shape)
    assert flow2d[:, 0].mean() > flow2d[:, -1].mean()
