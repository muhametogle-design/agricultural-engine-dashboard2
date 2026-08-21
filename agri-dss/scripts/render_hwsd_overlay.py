"""Render the HWSD v2.0 Somalia clip into a colorized topsoil-pH PNG overlay.

Reads the SMU raster + attribute CSV from data/hwsd/, joins topsoil
(SEQUENCE 1, TOPDEP 0) pH_water per mapping unit, applies the SSB pH palette
and writes an RGBA PNG sized to the clip bounds for a Leaflet imageOverlay.

Usage:  python scripts/render_hwsd_overlay.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parent.parent
RASTER = ROOT / "data" / "hwsd" / "hwsd2_somalia.tif"
ATTRS = ROOT / "data" / "hwsd" / "hwsd2_layers.csv"
OUT = ROOT / "app" / "web" / "hwsd_ph_overlay.png"

# SSB pH palette (r, g, b) — semi-transparent so the basemap shows through.
ALPHA = 150
BINS = [  # upper bound, colour
    (5.5, (45, 156, 60)),    # strong acid  -> deep green
    (6.5, (123, 192, 67)),   # acid         -> green
    (7.0, (200, 218, 72)),   # neutral      -> lime
    (7.5, (244, 208, 63)),   # mild alkali  -> yellow
    (8.0, (243, 156, 18)),   # alkali       -> orange
    (8.5, (230, 126, 34)),   # strong alkali-> burnt orange
    (14.0, (192, 57, 43)),   # extreme      -> red
]

def load_ph_map() -> dict[int, float]:
    lut: dict[int, float] = {}
    with open(ATTRS, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row.get("SEQUENCE") != "1" or row.get("TOPDEP") != "0":
                continue
            smu = int(row["HWSD2_SMU_ID"])
            try:
                ph = float(row["PH_WATER"])
            except (TypeError, ValueError):
                continue
            if ph > 14:
                ph /= 10.0
            if 3.0 <= ph <= 14.0:
                lut.setdefault(smu, ph)
    return lut


def main() -> None:
    lut = load_ph_map()
    with rasterio.open(RASTER) as ds:
        grid = ds.read(1)
        bounds, crs = ds.bounds, ds.crs
    ph = np.full(grid.shape, np.nan, dtype="float32")
    for smu, val in lut.items():
        ph[grid == smu] = val

    rgba = np.zeros((*grid.shape, 4), dtype="uint8")
    coloured = ~np.isnan(ph)
    for ub, (r, g, b) in BINS:
        mask = coloured & (ph <= ub)
        rgba[..., 0][mask] = r
        rgba[..., 1][mask] = g
        rgba[..., 2][mask] = b
        rgba[..., 3][mask] = ALPHA
        coloured &= ~mask
    nodata = grid == 0
    rgba[nodata] = 0  # fully transparent outside land

    profile = {
        "driver": "PNG", "dtype": "uint8", "count": 4,
        "width": grid.shape[1], "height": grid.shape[0],
        "compress": "deflate",
    }
    with rasterio.open(OUT, "w", **profile) as out:
        out.write(np.moveaxis(rgba, -1, 0))
    filled = (~np.isnan(ph)).sum()
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB); "
          f"{filled}/{ph.size} px coloured; bounds={bounds}")


if __name__ == "__main__":
    main()
