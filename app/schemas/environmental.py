from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EnvironmentalOut(BaseModel):
    field_id: UUID
    ph_water: float | None
    clay_percentage: float | None
    sand_percentage: float | None
    silt_percentage: float | None
    soil_organic_carbon: float | None   # g/kg
    nitrogen_content: float | None      # g/kg
    cec_mmolc_kg: float | None
    avg_annual_rainfall_mm: float | None
    avg_temp_celsius: float | None
    annual_et0_mm: float | None
    fetched_at: datetime
    age_seconds: float
    soil_samples_used: int = 0
    data_sources: list[str] = []
    client_note: str | None = None
