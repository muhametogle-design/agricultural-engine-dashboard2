"""HWSD v2.0 service: raster point-sampling + attribute normalization."""
from __future__ import annotations

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.crs import CRS  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from app.services.hwsd import HWSDService  # noqa: E402
from app.services.hwsd import _norm_pct, _norm_ph  # noqa: E402


@pytest.fixture()
def mini_dataset(tmp_path):
    """2x2 SMU raster over Laascaanood + attribute CSV (pH stored x10)."""
    tif = tmp_path / "hw.tif"
    grid = np.array([[101, 102], [101, 0]], dtype=np.uint16)
    # bounds: lon 45.0-45.2, lat 2.0-2.2 (cell 0.1 deg), origin NW
    with rasterio.open(
        tif, "w", driver="GTiff", width=2, height=2, count=1, dtype="uint16",
        crs=CRS.from_epsg(4326), transform=from_origin(45.0, 2.2, 0.1, 0.1),
    ) as ds:
        ds.write(grid, 1)
        ds.nodata = 0

    csv_path = tmp_path / "layers.csv"
    csv_path.write_text(
        "HWSD2_SMU_ID,SEQUENCE,PH,N,OC,CEC,CLAY,SAND,SILT,WRB4\n"
        "101,1,78,0.04,0.55,14,22,60,18,FLc\n"
        "101,2,80,0.02,0.30,16,25,58,17,FLc\n"
        "102,1,69,0.06,0.80,18,30,50,20,LXc\n",
        encoding="utf-8",
    )
    return tif, csv_path


def test_normalizers():
    assert _norm_ph("78") == 7.8      # x10 storage heals
    assert _norm_ph("6.9") == 6.9
    assert _norm_ph("150") is None    # implausible after healing
    assert _norm_ph(None) is None
    assert _norm_pct("0.55", 15.0) == 0.55
    assert _norm_pct("77", 100.0) == 77.0
    assert _norm_pct("-999", 100.0) is None


def test_sample_join_and_topsoil_only(mini_dataset):
    tif, csv_path = mini_dataset
    svc = HWSDService(tif, csv_path)
    assert svc.available

    hit = svc.sample(lat=2.15, lon=45.05)  # SMU 101, topsoil SEQUENCE 1
    assert hit["mu_id"] == 101
    assert hit["ph"] == 7.8                # 78 healed to 7.8
    assert hit["layer"].startswith("0-20")
    assert hit["wrb"] == "FLc"
    assert hit["om_pct"] == round(0.55 * 1.724, 2)

    hit2 = svc.sample(lat=2.15, lon=45.15)  # SMU 102
    assert hit2["ph"] == 6.9 and hit2["clay_pct"] == 30.0


def test_sample_outside_grid_and_nodata(mini_dataset):
    tif, csv_path = mini_dataset
    svc = HWSDService(tif, csv_path)
    assert svc.sample(lat=9.9, lon=50.0) is None            # outside extents
    healed = svc.sample(lat=2.05, lon=45.15)               # nodata cell -> nearest profiled pixel
    assert healed is not None and healed["ph"] == 7.8 and healed["nearest_km"] > 0


def test_unavailable_when_files_missing(tmp_path):
    svc = HWSDService(tmp_path / "nope.tif", None)
    assert not svc.available
    assert svc.sample(lat=2.1, lon=45.2) is None
