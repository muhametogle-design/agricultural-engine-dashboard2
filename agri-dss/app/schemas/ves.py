"""Partner machine (VES / resistivity) ingestion contracts."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.geojson import Lat, Lon


class VESCreate(BaseModel):
    lon: Lon
    lat: Lat
    depth_layers_m: list[float] = Field(min_length=3, max_length=200)
    apparent_resistivity_ohmm: list[float] = Field(min_length=3, max_length=200)
    operator_notes: str | None = None

    @model_validator(mode="after")
    def _check_curve(self):
        if len(self.depth_layers_m) != len(self.apparent_resistivity_ohmm):
            raise ValueError("depth_layers_m and apparent_resistivity_ohmm must have equal length")
        if any(d <= 0 for d in self.depth_layers_m):
            raise ValueError("depth values must be positive")
        if any(b <= a for a, b in zip(self.depth_layers_m, self.depth_layers_m[1:])):
            raise ValueError("depth_layers_m must be strictly increasing")
        if any(r <= 0 for r in self.apparent_resistivity_ohmm):
            raise ValueError("resistivity values must be positive (Ohm-m)")
        return self


class VESBulkCreate(BaseModel):
    surveys: list[VESCreate] = Field(min_length=1, max_length=500)


class VESOut(BaseModel):
    id: UUID
    field_id: UUID
    lon: float
    lat: float
    depth_layers_m: list[float]
    apparent_resistivity_ohmm: list[float]
    estimated_water_table_depth_m: float | None
    aquifer_quality_score: float | None
    operator_notes: str | None
    surveyed_at: datetime
    interpretation: dict | None = None  # populated on ingest for immediate feedback
