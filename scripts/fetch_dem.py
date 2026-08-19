"""Fetch public terrain elevation tiles (AWS elevation-tiles-prod, Cobertura
SRTM/COP) for a bbox and merge into a single GeoTIFF usable by the
RasterDemTerrainProvider (AGRI_TERRAIN__DEM_PATH).

Usage: python scripts/fetch_dem.py --bbox 45.314,2.042,45.322,2.050 --zoom 15
Falls back to a synthetic surface (explicitly flagged) if the network fails.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

TILES = "https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif"


def _tile_ix(lon: float, lat: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def fetch(bbox, zoom, out: Path) -> bool:
    import httpx
    import rasterio
    from rasterio.merge import merge

    minx, miny, maxx, maxy = bbox
    x0, y1 = _tile_ix(minx, miny, zoom)
    x1, y0 = _tile_ix(maxx, maxy, zoom)
    SAFE_NODATA = -32767.0  # representable in float32; source tiles use -FLT_MAX

    datasets = []
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                url = TILES.format(z=zoom, x=x, y=y)
                r = c.get(url)
                r.raise_for_status()
                t = Path(f"/tmp/dem_tile_{x}_{y}.tif")
                t.write_bytes(r.content)
                # normalize exotic source nodata (-FLT_MAX) into a safe value,
                # otherwise rasterio.merge masks everything and fills zeros
                with rasterio.open(t) as raw:
                    arr = raw.read(1)
                    meta = raw.meta.copy()
                # clamp nodata sentinels AND bathymetry artifacts (-9830 fill)
                arr = np.where(arr < -1000.0, SAFE_NODATA, arr)
                meta.update(dtype="float32", nodata=SAFE_NODATA)
                with rasterio.open(t, "w", **meta) as cleaned:
                    cleaned.write(arr.astype(np.float32), 1)
                datasets.append(rasterio.open(t))
    src_nodata = SAFE_NODATA
    mosaic, transform = merge(datasets, nodata=src_nodata)
    meta = datasets[0].meta.copy()
    meta.update(driver="GTiff", height=mosaic.shape[1], width=mosaic.shape[2],
                transform=transform, compress="deflate")
    out.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out, "w", **meta) as dst:
        dst.write(mosaic.astype(np.float32))
    for d in datasets:
        d.close()
    valid = mosaic if src_nodata is None else np.ma.masked_equal(mosaic, src_nodata)
    print(f"DEM written: {out} {mosaic.shape} crs={meta['crs']}")
    print(f"elevation range: {float(valid.min()):.1f} .. {float(valid.max()):.1f} m, nodata={src_nodata}")
    return True


def synthetic(bbox, out: Path) -> None:
    """Deterministic test surface: N-S tilt + a meandering channel running E-W."""
    import rasterio
    from rasterio.transform import from_bounds

    out.parent.mkdir(parents=True, exist_ok=True)
    minx, miny, maxx, maxy = bbox
    res = 0.0003  # ~33 m pixels
    w = int((maxx - minx) / res); h = int((maxy - miny) / res)
    xs = (np.arange(w) + 0.5) * res + minx
    ys = (np.arange(h) + 0.5) * res + miny
    gx, gy = np.meshgrid(xs, ys)
    elev = 40.0 - 900.0 * (gy - miny)                       # falls to the north
    channel_y = (miny + maxy) / 2 + 0.0006 * np.sin((gx - minx) / res / 12)
    elev -= 7.0 * np.exp(-((gy - channel_y) / 0.0011) ** 2)  # incised drainage line
    with rasterio.open(out, "w", driver="GTiff", height=h, width=w, count=1,
                       dtype="float32", crs="EPSG:4326",
                       transform=from_bounds(minx, miny, maxx, maxy, w, h),
                       nodata=-32767.0) as dst:
        dst.write(elev.astype(np.float32), 1)
    print(f"SYNTHETIC DEM written: {out} ({w}x{h}) - flagged for testing only")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", default="45.314,2.042,45.322,2.050")
    ap.add_argument("--zoom", type=int, default=15)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]
                                         / "data" / "dem_field.tif"))
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args()
    bbox = [float(v) for v in args.bbox.split(",")]
    out = Path(args.out)
    if args.synthetic:
        synthetic(bbox, out)
        sys.exit(0)
    try:
        fetch(bbox, args.zoom, out)
    except Exception as exc:  # noqa: BLE001
        print(f"tile fetch failed ({exc}); writing synthetic DEM", file=sys.stderr)
        synthetic(bbox, out)
