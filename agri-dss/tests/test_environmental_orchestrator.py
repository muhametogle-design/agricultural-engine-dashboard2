from __future__ import annotations

import httpx
import pytest
import respx

from app.core.errors import ExternalServiceError
from app.services.environmental import collect_environmental
from tests.conftest import make_power_payload, make_soilgrids_payload


@respx.mock
async def test_collect_merges_sources(settings, square_polygon):
    respx.get(settings.soilgrids_base_url).mock(
        return_value=httpx.Response(200, json=make_soilgrids_payload())
    )
    respx.get(settings.nasa_power_base_url).mock(
        return_value=httpx.Response(200, json=make_power_payload())
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        bundle = await collect_environmental(client, settings, square_polygon, area_ha=4.8)
    assert bundle.data_sources == ["ISRIC SoilGrids v2.0", "NASA POWER climatology (AG)"]
    assert bundle.values["ph_water"] is not None
    assert bundle.values["avg_annual_rainfall_mm"] is not None
    assert bundle.warnings == []
    assert "raw_nasa_power_json" in bundle.values and "raw_soilgrids_json" in bundle.values


@respx.mock
async def test_climate_outage_degrades_gracefully(settings, square_polygon):
    respx.get(settings.soilgrids_base_url).mock(
        return_value=httpx.Response(200, json=make_soilgrids_payload())
    )
    respx.get(settings.nasa_power_base_url).mock(return_value=httpx.Response(400))
    async with httpx.AsyncClient(timeout=5.0) as client:
        bundle = await collect_environmental(client, settings, square_polygon, area_ha=4.8)
    assert bundle.data_sources == ["ISRIC SoilGrids v2.0"]
    assert bundle.values["avg_annual_rainfall_mm"] is None
    assert any("NASA POWER" in w for w in bundle.warnings)


@respx.mock
async def test_total_outage_fails(settings, square_polygon):
    respx.get(settings.soilgrids_base_url).mock(return_value=httpx.Response(400))
    respx.get(settings.nasa_power_base_url).mock(return_value=httpx.Response(400))
    async with httpx.AsyncClient(timeout=5.0) as client:
        with pytest.raises(ExternalServiceError):
            await collect_environmental(client, settings, square_polygon, area_ha=4.8)
