"""Master plan / decision report contracts."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MasterPlanOptions(BaseModel):
    refresh_environmental: bool = False       # ignore cache TTL and re-fetch APIs
    supplemental_irrigation_mm: float = Field(default=0.0, ge=0)  # crop water balance
    gates: int | None = Field(default=None, ge=1, le=100)         # auto if omitted
    run_zoning: bool = True
    run_well_siting: bool = True


class WellSitingReport(BaseModel):
    optimal_well_point: dict | None
    recommended_drilling_depth_m: float | None
    composite_score: float | None
    factor_weights_used: dict
    candidate_sites: list[dict]
    factor_summary: dict
    coverage: dict
    method: str


class CropSuitability(BaseModel):
    crop: str
    score: float
    rating: str
    limiting_factors: list[str]
    notes: list[str]


class FencingReport(BaseModel):
    perimeter_m: float
    gates: int
    line_posts: int
    strainer_posts: int
    gate_posts: int = 0
    total_posts: int
    wire_rolls: int
    wire_length_m: float
    cost_breakdown: dict
    total_cost: float
    assumptions: dict


class MasterPlanReport(BaseModel):
    plan_id: UUID | None = None
    field_id: UUID
    generated_at: datetime | None = None
    field_summary: dict
    environmental: dict
    soil_amendment_recommendations: list[str]
    well_siting: WellSitingReport | None
    crop_matching: list[CropSuitability]
    fencing: FencingReport
    layout_zones: dict | None
    warnings: list[str] = []
