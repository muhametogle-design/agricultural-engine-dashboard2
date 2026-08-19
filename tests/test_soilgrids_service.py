from __future__ import annotations

import httpx
import pytest
import respx

from app.core.errors import NoCoverageError
from app.services import soilgrids
from tests.conftest import CENTER_LAT, CENTER_LON, make_soilgrids_payload


@pytest.fixture()
def http_client(settings):
    return httpx.AsyncClient(timeout=5.0)


@respx.mock
async def test_point_query_weighted_profile(settings, http_client):
    route = respx.get(settings.soilgrids_base_url).mock(
        return_value=httpx.Response(200, json=make_soilgrids_payload())
    )
    profile, raw = await soilgrids.fetch_soil_point(http_client, settings,
                                                    lat=CENTER_LAT, lon=CENTER_LON)
    assert route.called
    # thickness-weighted: clay (180*5+220*10+260*15)/30 = 233.33 g/kg -> 23.33 %
    assert profile["clay_percentage"] == pytest.approx(23.333, abs=1e-3)
    # pH (62*5+60*10+58*15)/30 = 59.33 -> /10
    assert profile["ph_water"] == pytest.approx(5.933, abs=1e-3)
    # nitrogen (140*5+110*10+70*15)/30 = 95 cg/kg -> 0.95 g/kg
    assert profile["nitrogen_content"] == pytest.approx(0.95, abs=1e-3)
    # cec (200*5+190*10+170*15)/30 = 181.67 mmol(c)/kg
    assert profile["cec_mmolc_kg"] == pytest.approx(181.667, abs=1e-3)
    assert "layers" in raw["properties"]


@respx.mock
async def test_point_query_partial_nulls(settings, http_client):
    payload = make_soilgrids_payload(
        per_depth_values={
            "phh2o": [62, None, 58],          # one missing band
            "clay": [None, None, None],        # fully missing property
        }
    )
    respx.get(settings.soilgrids_base_url).mock(return_value=httpx.Response(200, json=payload))
    profile, _ = await soilgrids.fetch_soil_point(http_client, settings, 2.0, 45.0)
    assert profile["ph_water"] == pytest.approx((62 * 5 + 58 * 15) / (20 * 10), abs=1e-3)
    assert profile["clay_percentage"] is None


@respx.mock
async def test_out_of_coverage_raises(settings, http_client):
    payload = make_soilgrids_payload(
        per_depth_values={
            "phh2o": [None, None, None], "clay": [None, None, None],
            "sand": [None, None, None], "silt": [None, None, None],
            "soc": [None, None, None], "nitrogen": [None, None, None],
            "cec": [None, None, None],
        }
    )
    respx.get(settings.soilgrids_base_url).mock(return_value=httpx.Response(200, json=payload))
    with pytest.raises(NoCoverageError):
        await soilgrids.fetch_soil(http_client, settings,
                                   {"type": "Polygon", "coordinates": [[[45.0, 2.0],
                                        [45.001, 2.0], [45.001, 2.001], [45.0, 2.001],
                                        [45.0, 2.0]]]},
                                   area_ha=0.5)


@respx.mock
async def test_polygon_aggregation(settings, http_client, square_polygon):
    route = respx.get(settings.soilgrids_base_url).mock(
        return_value=httpx.Response(200, json=make_soilgrids_payload())
    )
    result = await soilgrids.fetch_soil_polygon(http_client, settings, square_polygon)
    assert result.samples_used >= 1
    # sand (640*5+620*10+600*15)/30 = 613.33 g/kg -> 61.33 %
    assert result.values["sand_percentage"] == pytest.approx(61.333, abs=1e-3)
    assert result.raw["mode"] == "polygon_aggregation"
    assert route.call_count >= result.samples_used  # samples + exemplar centroid query


@respx.mock
async def test_retry_on_5xx_then_success(settings, http_client):
    ok = make_soilgrids_payload()
    route = respx.get(settings.soilgrids_base_url).mock(
        side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(200, json=ok)]
    )
    settings.http.max_retries = 3
    profile, _ = await soilgrids.fetch_soil_point(http_client, settings, 2.0, 45.0)
    assert profile["ph_water"] is not None
    assert route.call_count == 3


@respx.mock
async def test_4xx_fails_fast(settings, http_client):
    from app.core.errors import ExternalServiceError

    route = respx.get(settings.soilgrids_base_url).mock(return_value=httpx.Response(400))
    with pytest.raises(ExternalServiceError):
        await soilgrids.fetch_soil_point(http_client, settings, 2.0, 45.0)
    assert route.call_count == 1  # no retry on deterministic client error
