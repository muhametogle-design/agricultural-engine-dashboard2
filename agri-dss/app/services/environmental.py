"""Environmental orchestration: SoilGrids + NASA POWER -> one cacheable bundle.

Fault policy: the two sources are independent; a single-source outage does
not block the other (master plans degrade gracefully, warnings recorded).
The bundle only fails hard if BOTH sources fail.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import Settings
from app.core.errors import ExternalServiceError
from app.core.logging import get_logger
from app.core.spatial import geom_from_geojson
from app.services import nasa_power, soilgrids

log = get_logger(__name__)


@dataclass
class EnvironmentalBundle:
    values: dict[str, float | None]          # maps 1:1 to field_environmental_data columns
    soil_samples_used: int
    data_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


async def collect_environmental(
    client: httpx.AsyncClient,
    settings: Settings,
    boundary_geojson: dict,
    area_ha: float,
) -> EnvironmentalBundle:
    centroid = geom_from_geojson(boundary_geojson).centroid

    soil_result, climate_result = await asyncio.gather(
        soilgrids.fetch_soil(client, settings, boundary_geojson, area_ha),
        nasa_power.fetch_climatology(client, settings, centroid.y, centroid.x),
        return_exceptions=True,
    )

    # Pre-seed every cache column with None: a partial outage must still
    # produce a complete, well-typed record for the environmental cache table.
    values: dict[str, float | None] = {
        k: None for k in (
            "ph_water", "clay_percentage", "sand_percentage", "silt_percentage",
            "soil_organic_carbon", "nitrogen_content", "cec_mmolc_kg",
            "avg_annual_rainfall_mm", "avg_temp_celsius", "annual_et0_mm",
        )
    }
    sources: list[str] = []
    warnings: list[str] = []
    samples = 0

    if isinstance(soil_result, Exception):
        warnings.append(f"SoilGrids unavailable: {soil_result}")
        log.warning("soil ingestion failed: %s", soil_result)
    else:
        values.update(soil_result.values)
        values["raw_soilgrids_json"] = soil_result.raw  # type: ignore[assignment]
        samples = soil_result.samples_used
        sources.append("ISRIC SoilGrids v2.0")

    if isinstance(climate_result, Exception):
        warnings.append(f"NASA POWER unavailable: {climate_result}")
        log.warning("climate ingestion failed: %s", climate_result)
    else:
        values.update(
            {
                "avg_annual_rainfall_mm": climate_result.avg_annual_rainfall_mm,
                "avg_temp_celsius": climate_result.avg_temp_celsius,
                "annual_et0_mm": climate_result.annual_et0_mm,
                "raw_nasa_power_json": climate_result.raw,  # type: ignore[assignment]
            }
        )
        sources.append("NASA POWER climatology (AG)")

    if not sources:
        raise ExternalServiceError("All environmental data sources failed", detail={"warnings": warnings})

    return EnvironmentalBundle(values=values, soil_samples_used=samples,
                               data_sources=sources, warnings=warnings)
