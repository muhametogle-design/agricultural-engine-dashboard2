"""Reference evapotranspiration (ET0) via FAO-56 Penman-Monteith.

NASA POWER's climatology endpoint does NOT serve ET0 directly, so the
ingestion service derives it from POWER drivers: T2M/T2M_MAX/T2M_MIN,
RH2M, WS2M (2-m wind) and ALLSKY_SFC_SW_DWN (Rs), plus station elevation
(POWER returns it in the response geometry). Monthly-mean formulation with
G=0 per FAO-56 (Allen et al., 1998).

All radiation terms are MJ m-2 day-1; result is mm/day.
"""
from __future__ import annotations

import math

# Day-of-year for the 15th of each month (non-leap year)
MID_MONTH_DOY = [15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349]

_SIGMA = 4.903e-9  # Stefan-Boltzmann MJ K-4 m-2 day-1


def _saturation_vapor_pressure(t_c: float) -> float:
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def _atmospheric_pressure(elevation_m: float) -> float:
    return 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26


def _extraterrestrial_radiation(lat_deg: float, doy: int) -> float:
    phi = math.radians(lat_deg)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * doy / 365.0)
    delta = 0.409 * math.sin(2.0 * math.pi * doy / 365.0 - 1.39)
    omega_s = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    return ((24.0 * 60.0 / math.pi) * 0.0820 * dr
            * (omega_s * math.sin(phi) * math.sin(delta)
               + math.cos(phi) * math.cos(delta) * math.sin(omega_s)))


def monthly_et0_fao56(
    lat_deg: float,
    doy: int,
    elevation_m: float,
    t2m: float | None,
    tmax: float | None,
    tmin: float | None,
    rh_percent: float | None,
    u2_ms: float | None,
    rs_mj: float | None,
) -> float | None:
    """One month's ET0 (mm/day). None if any driver is missing."""
    if None in (t2m, tmax, tmin, rh_percent, u2_ms, rs_mj):
        return None
    rh_frac = max(min(rh_percent / 100.0, 1.0), 0.01)

    es = (_saturation_vapor_pressure(tmax) + _saturation_vapor_pressure(tmin)) / 2.0
    ea = es * rh_frac
    delta = (4098.0 * _saturation_vapor_pressure(t2m)) / (t2m + 237.3) ** 2
    gamma = 0.000665 * _atmospheric_pressure(elevation_m)

    ra = _extraterrestrial_radiation(lat_deg, doy)
    rso = (0.75 + 2e-5 * elevation_m) * ra
    rns = (1.0 - 0.23) * rs_mj
    tmax_k4 = (tmax + 273.16) ** 4
    tmin_k4 = (tmin + 273.16) ** 4
    rs_ratio = max(min(rs_mj / rso, 1.0), 0.05) if rso > 0 else 0.5
    rnl = (_SIGMA * (tmax_k4 + tmin_k4) / 2.0
           * (0.34 - 0.14 * math.sqrt(max(ea, 1e-6)))
           * (1.35 * rs_ratio - 0.35))
    rn = rns - rnl  # G (soil heat flux) = 0 for monthly steps

    numerator = 0.408 * delta * rn + gamma * (900.0 / (t2m + 273.0)) * u2_ms * (es - ea)
    denominator = delta + gamma * (1.0 + 0.34 * u2_ms)
    return max(round(numerator / denominator, 3), 0.0)
