"""NASA POWER climatology client (AG community).

Upstream of the partner draft `fetch_climate_data`. Production changes:
  * reference ET0 is DERIVED via FAO-56 Penman-Monteith (app.engines.et0)
    from POWER drivers - the POWER APIs do not expose an ET0 parameter;
  * POWER's missing-data sentinel (-999) is converted to None everywhere;
  * annual rainfall is the sum of (monthly mean daily rate x days-in-month),
    replacing the draft's `ANN < 20` unit heuristic. ANN-based fallback
    (rate x 365.25) is used only if the monthly series is absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger
from app.engines.et0 import MID_MONTH_DOY, monthly_et0_fao56
from app.services.http import get_json

log = get_logger(__name__)

MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS_IN_MONTH = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # leap-adjusted Feb


@dataclass
class ClimateProfile:
    avg_annual_rainfall_mm: float | None
    avg_temp_celsius: float | None
    annual_et0_mm: float | None
    coldest_month_min_temp_c: float | None
    hottest_month_max_temp_c: float | None
    mean_rh_percent: float | None
    monthly: dict[str, list[float | None]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


def _clean(value: Any, sentinel: float) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f <= sentinel else f


def _monthly(series: dict, sentinel: float) -> list[float | None]:
    return [_clean(series.get(k), sentinel) for k in MONTH_KEYS]


def _annual_from_rate(series: dict, sentinel: float) -> float | None:
    """mm/day climatology rates -> mm/year via days-in-month sum."""
    months = _monthly(series, sentinel)
    valid = [(m, d) for m, d in zip(months, DAYS_IN_MONTH) if m is not None]
    if len(valid) >= 11:  # tolerate a single missing month
        return round(sum(m * d for m, d in valid), 2)
    ann = _clean(series.get("ANN"), sentinel)
    return round(ann * 365.25, 2) if ann is not None else None


async def fetch_climatology(
    client: httpx.AsyncClient, settings: Settings, lat: float, lon: float
) -> ClimateProfile:
    payload = await get_json(
        client,
        settings.nasa_power_base_url,
        params={
            "parameters": settings.climate.parameters,
            "community": settings.climate.community,
            "longitude": lon,
            "latitude": lat,
            "format": "JSON",
        },
        settings=settings.http,
    )
    sentinel = settings.climate.sentinel_value
    try:
        parameter = payload["properties"]["parameter"]
    except KeyError as exc:
        raise ExternalServiceError("NASA POWER response missing properties.parameter",
                                   detail={"head": str(payload)[:400]}) from exc

    def series(name: str) -> dict:
        return parameter.get(name, {})

    t2m = series("T2M")
    t2m_min_months = _monthly(series("T2M_MIN"), sentinel)
    t2m_max_months = _monthly(series("T2M_MAX"), sentinel)
    rh_months = _monthly(series("RH2M"), sentinel)

    avg_temp = _clean(t2m.get("ANN"), sentinel)
    if avg_temp is None:
        m = [v for v in _monthly(t2m, sentinel) if v is not None]
        avg_temp = round(sum(m) / len(m), 2) if m else None

    # --- FAO-56 ET0 derivation from drivers --------------------------------
    elevation = 0.0
    try:
        elevation = float(payload["geometry"]["coordinates"][2])
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    t2m_months = _monthly(t2m, sentinel)
    ws_months = _monthly(series("WS2M"), sentinel)
    rs_months = _monthly(series("ALLSKY_SFC_SW_DWN"), sentinel)
    et0_months = [
        monthly_et0_fao56(
            lat_deg=lat, doy=MID_MONTH_DOY[i], elevation_m=elevation,
            t2m=t2m_months[i], tmax=t2m_max_months[i], tmin=t2m_min_months[i],
            rh_percent=rh_months[i], u2_ms=ws_months[i], rs_mj=rs_months[i],
        )
        for i in range(12)
    ]
    annual_et0 = None
    if all(v is not None for v in et0_months):
        annual_et0 = round(sum(v * d for v, d in zip(et0_months, DAYS_IN_MONTH)), 2)

    profile = ClimateProfile(
        avg_annual_rainfall_mm=_annual_from_rate(series("PRECTOTCORR"), sentinel),
        avg_temp_celsius=round(avg_temp, 2) if avg_temp is not None else None,
        annual_et0_mm=annual_et0,
        coldest_month_min_temp_c=min((v for v in t2m_min_months if v is not None), default=None),
        hottest_month_max_temp_c=max((v for v in t2m_max_months if v is not None), default=None),
        mean_rh_percent=round(sum(v for v in rh_months if v is not None)
                              / max(len([v for v in rh_months if v is not None]), 1), 1)
        if any(v is not None for v in rh_months) else None,
        monthly={
            "PRECTOTCORR_mm_per_day": _monthly(series("PRECTOTCORR"), sentinel),
            "T2M_c": t2m_months,
            "T2M_MIN_c": t2m_min_months,
            "T2M_MAX_c": t2m_max_months,
            "ET0_mm_per_day_derived": et0_months,
        },
        raw=payload,
    )
    log.info("nasa power climatology (%.3f, %.3f): rain=%s mm/y, T=%s C, ET0=%s mm/y",
             lat, lon, profile.avg_annual_rainfall_mm,
             profile.avg_temp_celsius, profile.annual_et0_mm)
    return profile
