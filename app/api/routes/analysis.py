"""Single-engine analysis endpoints (work on cached/persisted inputs)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import AuthDep, HttpDep, ReposDep, SettingsDep, TerrainDep
from app.engines import crop_matching, infrastructure, well_siting, zoning
from app.schemas.geojson import Lat, Lon
from app.services.master_plan import coldest_month_min_from_raw, ensure_environmental

router = APIRouter(prefix="/fields/{field_id}", tags=["analysis"])


class CropMatchRequest(BaseModel):
    supplemental_irrigation_mm: float = Field(default=0.0, ge=0, le=5000)
    refresh_environmental: bool = False


class ZoningRequest(BaseModel):
    well_point: tuple[Lon, Lat] | None = Field(
        default=None, description="(lon, lat); uses centroid-less layout if omitted"
    )


class InfrastructureRequest(BaseModel):
    gates: int | None = Field(default=None, ge=1, le=100)


@router.post("/well-siting")
async def run_well_siting_endpoint(field_id: UUID, repos: ReposDep,
                                   settings: SettingsDep, terrain: TerrainDep,
                                   auth: AuthDep):
    field = await repos.fields.get(field_id, auth.tenant_id)
    surveys = await repos.ves.list_for_field(field_id)
    result = well_siting.run_well_siting(field["boundary"], surveys, settings, terrain)
    return {
        "optimal_well_point": result.optimal_point_geojson(),
        "recommended_drilling_depth_m": result.recommended_drilling_depth_m,
        "composite_score": result.composite_score,
        "factor_weights_used": result.factor_weights_used,
        "candidate_sites": result.candidates,
        "factor_summary": result.factor_summary,
        "coverage": result.coverage,
        "method": result.method,
    }


@router.post("/crop-matching")
async def run_crop_matching(field_id: UUID, payload: CropMatchRequest, repos: ReposDep,
                            settings: SettingsDep, http: HttpDep, auth: AuthDep):
    field = await repos.fields.get(field_id, auth.tenant_id)
    env_row, warnings = await ensure_environmental(
        repos, settings, http, field, refresh=payload.refresh_environmental
    )
    env = {k: (float(env_row[k]) if env_row.get(k) is not None else None) for k in (
        "ph_water", "clay_percentage", "sand_percentage", "silt_percentage",
        "soil_organic_carbon", "nitrogen_content", "cec_mmolc_kg",
        "avg_annual_rainfall_mm", "avg_temp_celsius", "annual_et0_mm")}
    env["coldest_month_min_temp_c"] = coldest_month_min_from_raw(env_row.get("raw_nasa_power_json"))
    return {
        "environmental_features": env,
        "supplemental_irrigation_mm": payload.supplemental_irrigation_mm,
        "ranked_crops": crop_matching.match_crops(env, payload.supplemental_irrigation_mm),
        "soil_amendment_recommendations": crop_matching.recommend_amendments(env),
        "warnings": warnings,
    }


@router.post("/infrastructure")
async def run_infrastructure(field_id: UUID, payload: InfrastructureRequest, repos: ReposDep,
                             settings: SettingsDep, auth: AuthDep):
    field = await repos.fields.get(field_id, auth.tenant_id)
    corner_count = max(len(field["boundary"]["coordinates"][0]) - 1, 0)
    bom = infrastructure.fencing_bom(
        float(field["perimeter_meters"]), corner_count, payload.gates, settings.fencing
    )
    return bom.to_dict()


@router.post("/zoning")
async def run_zoning(field_id: UUID, payload: ZoningRequest, repos: ReposDep,
                     settings: SettingsDep, auth: AuthDep):
    field = await repos.fields.get(field_id, auth.tenant_id)
    well = (payload.well_point[0], payload.well_point[1]) if payload.well_point else None
    return zoning.generate_master_layout(field["boundary"], well, settings)
