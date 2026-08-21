from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AuthDep, HttpDep, ReposDep, SettingsDep, TerrainDep
from app.core.errors import NotFoundError
from app.schemas.plans import MasterPlanOptions, MasterPlanReport
from app.services.master_plan import generate_master_plan

router = APIRouter(prefix="/fields/{field_id}/master-plan", tags=["master-plan"])


@router.post("", response_model=MasterPlanReport, status_code=status.HTTP_201_CREATED)
async def create_master_plan(
    field_id: UUID,
    repos: ReposDep,
    settings: SettingsDep,
    http: HttpDep,
    terrain: TerrainDep,
    auth: AuthDep,
    options: MasterPlanOptions | None = None,
):
    """Run the full decision pipeline and persist the plan. All engines run
    over the field's cached/persisted inputs; environmental data is
    auto-fetched if the cache is empty or stale."""
    return await generate_master_plan(
        repos, settings, http, terrain, field_id, options or MasterPlanOptions(),
        tenant_id=auth.tenant_id,
    )


@router.get("")
async def get_latest_master_plan(field_id: UUID, repos: ReposDep, auth: AuthDep):
    await repos.fields.get(field_id, auth.tenant_id)
    row = await repos.plans.latest(field_id)
    if row is None:
        raise NotFoundError("no master plan generated yet; POST to run the pipeline")
    return row
