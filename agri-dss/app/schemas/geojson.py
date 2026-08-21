"""GeoJSON geometry models with strict WGS84 validation (RFC 7946)."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

Lon = Annotated[float, Field(ge=-180.0, le=180.0)]
Lat = Annotated[float, Field(ge=-90.0, le=90.0)]


class GeoJSONPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[Lon, Lat]

    @property
    def lon(self) -> float:
        return self.coordinates[0]

    @property
    def lat(self) -> float:
        return self.coordinates[1]


class GeoJSONPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[tuple[Lon, Lat]]]

    @field_validator("coordinates")
    @classmethod
    def _validate_rings(cls, rings):
        if not rings:
            raise ValueError("polygon must have at least one ring")
        for ring in rings:
            if len(ring) < 4:
                raise ValueError("each ring must have at least 4 positions")
            if ring[0] != ring[-1]:
                raise ValueError("each ring must be closed (first position == last)")
        return rings

    def to_geojson(self) -> dict:
        return self.model_dump()
