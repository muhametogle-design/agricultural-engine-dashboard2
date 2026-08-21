from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import AuthDep, HttpDep, ReposDep, SettingsDep
from app.core.errors import NotFoundError
from app.schemas.environmental import EnvironmentalOut
from app.services.master_plan import ensure_environmental

router = APIRouter(prefix="/fields/{field_id}/environmental", tags=["environmental"])


@router.post("", response_model=EnvironmentalOut, status_code=status.HTTP_200_OK)
async def fetch_environmental(
    field_id: UUID,
    repos: ReposDep,
    settings: SettingsDep,
    http: HttpDep,
    auth: AuthDep,
    refresh: bool = Query(False, description="Ignore cache TTL and re-query the APIs"),
):
    """Fetch (or return cached) SoilGrids + NASA POWER data for the field."""
    field = await repos.fields.get(field_id, auth.tenant_id)
    row, warnings = await ensure_environmental(repos, settings, http, field, refresh=refresh)
    row["client_note"] = "; ".join(warnings) if warnings else None
    return row


@router.get("", response_model=EnvironmentalOut)
async def get_environmental(field_id: UUID, repos: ReposDep, auth: AuthDep):
    await repos.fields.get(field_id, auth.tenant_id)
    row = await repos.environmental.get(field_id)
    if row is None:
        raise NotFoundError("no environmental data cached for this field; POST to fetch")
    return row
