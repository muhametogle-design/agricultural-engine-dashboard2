"""Field registration: accepts EITHER a drawn polygon OR a tapped GPS point."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.geojson import GeoJSONPolygon, Lat, Lon


class PointFieldInput(BaseModel):
    """Mode 1: user taps a GPS point; server materializes a square field."""

    mode: Literal["point"] = "point"
    lon: Lon
    lat: Lat
    area_ha: float | None = Field(default=None, gt=0.05, le=10_000)


class PolygonFieldInput(BaseModel):
    """Mode 2: user draws a boundary polygon on the map."""

    mode: Literal["polygon"] = "polygon"
    geometry: GeoJSONPolygon


FieldInput = Annotated[Union[PointFieldInput, PolygonFieldInput], Field(discriminator="mode")]


class FieldCreate(BaseModel):
    client_id: UUID
    field_name: str = Field(min_length=1, max_length=100)
    input: FieldInput


class FieldOut(BaseModel):
    id: UUID
    tenant_id: UUID
    client_id: UUID
    field_name: str
    boundary: dict
    center_point: dict
    area_hectares: float
    perimeter_meters: float
    created_at: datetime
