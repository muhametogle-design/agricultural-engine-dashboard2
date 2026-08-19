from __future__ import annotations

import httpx
import pytest
import respx

from app.services.nasa_power import fetch_climatology
from tests.conftest import CENTER_LAT, CENTER_LON, make_power_payload


@respx.mock
async def test_climatology_aggregation(settings):
    respx.get(settings.nasa_power_base_url).mock(
        return_value=httpx.Response(200, json=make_power_payload())
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        p = await fetch_climatology(client, settings, CENTER_LAT, CENTER_LON)
    # 0.8 mm/day uniform -> 0.8 * 365.25
    assert p.avg_annual_rainfall_mm == pytest.approx(0.8 * 365.25, abs=0.01)
    # ET0 is DERIVED (FAO-56): the payload's absurd ET0 series (99) must be
    # ignored, and the result must sit in the physically plausible band for
    # the driver values (t2m 27.8, ws 3.1, rs 21, rh 74, elev 22 m).
    assert p.annual_et0_mm != pytest.approx(99.0 * 365.25)
    assert 1500 <= p.annual_et0_mm <= 2300
    assert p.avg_temp_celsius == 27.8
    assert p.coldest_month_min_temp_c == 21.0
    assert p.hottest_month_max_temp_c == 33.5
    assert len(p.monthly["PRECTOTCORR_mm_per_day"]) == 12
    assert len(p.monthly["ET0_mm_per_day_derived"]) == 12
    assert all(v is not None and 3.5 < v < 7.5 for v in p.monthly["ET0_mm_per_day_derived"])


@respx.mock
async def test_sentinel_months_fall_back_to_ann(settings):
    respx.get(settings.nasa_power_base_url).mock(
        return_value=httpx.Response(200, json=make_power_payload(null_prec_months=True))
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        p = await fetch_climatology(client, settings, CENTER_LAT, CENTER_LON)
    # all monthly -999 -> ANN rate 0.8 * 365.25
    assert p.avg_annual_rainfall_mm == pytest.approx(0.8 * 365.25, abs=0.01)


@respx.mock
async def test_malformed_payload_raises(settings):
    from app.core.errors import ExternalServiceError

    respx.get(settings.nasa_power_base_url).mock(
        return_value=httpx.Response(200, json={"unexpected": True})
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        with pytest.raises(ExternalServiceError):
            await fetch_climatology(client, settings, CENTER_LAT, CENTER_LON)
