"""Master plan orchestration - the single entry point that runs every
engine over one field, persists the result to farm_master_plans, and
assembles the JSON decision report."""
from __future__ import annotations

import asyncio
from uuid import UUID

import httpx

from app.config import Settings
from app.core.logging import get_logger
from app.db.repositories import RepositoryBundle
from app.engines import crop_matching, infrastructure, well_siting, zoning
from app.engines.terrain import TerrainProvider
from app.schemas.plans import MasterPlanOptions
from app.services.environmental import collect_environmental

log = get_logger(__name__)


def coldest_month_min_from_raw(raw_power: dict | None, sentinel: float = -999.0) -> float | None:
    """Recover the coldest-month T2M_MIN from the cached POWER payload."""
    try:
        series = raw_power["properties"]["parameter"]["T2M_MIN"]
    except (KeyError, TypeError):
        return None
    vals = [v for k, v in series.items() if k != "ANN" and isinstance(v, (int, float)) and v > sentinel]
    return round(min(vals), 2) if vals else None


async def ensure_environmental(
    repos: RepositoryBundle,
    settings: Settings,
    http_client: httpx.AsyncClient,
    field: dict,
    *,
    refresh: bool = False,
) -> tuple[dict, list[str]]:
    """Cache-first environmental profile. Returns (row, warnings)."""
    cached = await repos.environmental.get(field["id"])
    if (
        cached is not None
        and not refresh
        and float(cached.get("age_seconds") or 0) <= settings.env_cache_ttl_s
    ):
        return cached, []

    bundle = await collect_environmental(
        http_client, settings, field["boundary"], float(field["area_hectares"])
    )
    row = await repos.environmental.upsert(field["id"], bundle.values)
    row.update(
        {
            "age_seconds": 0.0,
            "soil_samples_used": bundle.soil_samples_used,
            "data_sources": bundle.data_sources,
        }
    )
    return row, bundle.warnings


async def generate_master_plan(
    repos: RepositoryBundle,
    settings: Settings,
    http_client: httpx.AsyncClient,
    terrain: TerrainProvider,
    field_id: UUID,
    options: MasterPlanOptions,
    *,
    tenant_id: UUID,
) -> dict:
    field = await repos.fields.get(field_id, tenant_id)
    warnings: list[str] = []

    # --- 1. Environmental profile (cached or freshly ingested) ---------------
    env_row, env_warnings = await ensure_environmental(
        repos, settings, http_client, field, refresh=options.refresh_environmental
    )
    warnings.extend(env_warnings)
    env = {k: env_row.get(k) for k in (
        "ph_water", "clay_percentage", "sand_percentage", "silt_percentage",
        "soil_organic_carbon", "nitrogen_content", "cec_mmolc_kg",
        "avg_annual_rainfall_mm", "avg_temp_celsius", "annual_et0_mm")}
    env = {k: (float(v) if v is not None else None) for k, v in env.items()}
    env["coldest_month_min_temp_c"] = coldest_month_min_from_raw(env_row.get("raw_nasa_power_json"))

    # --- 2. Decision engines (independent -> concurrent) ---------------------
    ves_rows = await repos.ves.list_for_field(field_id)

    well_result = None
    if options.run_well_siting:
        well_result = await asyncio.to_thread(
            well_siting.run_well_siting, field["boundary"], ves_rows, settings, terrain
        )
        if well_result.coverage.get("ves_surveys_used", 0) == 0:
            warnings.append("No VES soundings ingested; well siting used terrain/defaults only.")

    crops = await asyncio.to_thread(
        crop_matching.match_crops, env, options.supplemental_irrigation_mm
    )
    top_crops = [c for c in crops if c["score"] >= 40][:8]

    ring = field["boundary"]["coordinates"][0]
    corner_count = max(len(ring) - 1, 0)
    bom = infrastructure.fencing_bom(
        float(field["perimeter_meters"]), corner_count, options.gates, settings.fencing
    )

    layout = None
    if options.run_zoning:
        well_lonlat = (
            (well_result.optimal_lon, well_result.optimal_lat)
            if well_result and well_result.optimal_lon is not None else None
        )
        layout = await asyncio.to_thread(
            zoning.generate_master_layout, field["boundary"], well_lonlat, settings
        )

    amendments = crop_matching.recommend_amendments(env)

    # --- 3. Persist ----------------------------------------------------------
    plan_row = await repos.plans.create(
        field_id,
        {
            "optimal_well_point": well_result.optimal_point_geojson() if well_result else None,
            "recommended_drilling_depth_m": well_result.recommended_drilling_depth_m if well_result else None,
            "top_suitable_crops": top_crops,
            "soil_amendment_recommendations": amendments,
            "fencing_post_count": bom.total_posts,
            "fencing_wire_rolls_required": bom.wire_rolls,
            "fencing_total_cost_est": bom.total_cost,
            "layout_zones_geojson": layout,
        },
    )

    # --- 4. Report ------------------------------------------------------------
    return {
        "plan_id": plan_row["id"],
        "field_id": field_id,
        "generated_at": plan_row["generated_at"],
        "field_summary": {
            "field_name": field["field_name"],
            "area_hectares": float(field["area_hectares"]),
            "perimeter_meters": float(field["perimeter_meters"]),
            "center_point": field["center_point"],
        },
        "environmental": {
            **env,
            "fetched_at": env_row.get("fetched_at"),
            "data_sources": env_row.get("data_sources", ["cache"]),
        },
        "soil_amendment_recommendations": amendments,
        "well_siting": (
            {
                "optimal_well_point": well_result.optimal_point_geojson(),
                "recommended_drilling_depth_m": well_result.recommended_drilling_depth_m,
                "composite_score": well_result.composite_score,
                "factor_weights_used": well_result.factor_weights_used,
                "candidate_sites": well_result.candidates,
                "factor_summary": well_result.factor_summary,
                "coverage": well_result.coverage,
                "method": well_result.method,
            }
            if well_result else None
        ),
        "crop_matching": crops,
        "fencing": bom.to_dict(),
        "layout_zones": layout,
        "warnings": warnings,
    }
