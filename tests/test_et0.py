"""FAO-56 ET0 engine: physical sanity bounds and driver monotonicity."""
from __future__ import annotations

import pytest

from app.engines.et0 import MID_MONTH_DOY, monthly_et0_fao56

# Hot, semi-arid coastal site (Afgooye corridor conditions, June)
HOT = dict(lat_deg=2.05, doy=166, elevation_m=17.0, t2m=27.8, tmax=33.5,
           tmin=21.0, rh_percent=74.0, u2_ms=3.1, rs_mj=21.0)
# Cool highland dry season
COOL = dict(lat_deg=9.6, doy=15, elevation_m=2350.0, t2m=15.0, tmax=21.0,
            tmin=9.0, rh_percent=55.0, u2_ms=1.5, rs_mj=15.0)


def test_hot_site_et0_in_expected_range():
    et0 = monthly_et0_fao56(**HOT)
    assert et0 is not None
    # analytic value for these inputs ~5.0 mm/day; allow generous band
    assert 4.0 <= et0 <= 6.5


def test_cool_site_lower_than_hot_site():
    assert monthly_et0_fao56(**COOL) < monthly_et0_fao56(**HOT)


def test_wind_and_radiation_monotonicity():
    base = monthly_et0_fao56(**HOT)
    windy = monthly_et0_fao56(**{**HOT, "u2_ms": 6.0})
    sunny = monthly_et0_fao56(**{**HOT, "rs_mj": 28.0})
    assert windy > base and sunny > base


def test_missing_driver_yields_none():
    assert monthly_et0_fao56(**{**HOT, "rs_mj": None}) is None
    assert monthly_et0_fao56(**{**HOT, "u2_ms": None}) is None


def test_mid_month_doy_table():
    assert MID_MONTH_DOY == [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]
