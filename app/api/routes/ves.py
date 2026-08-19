"""Partner machine ingestion: VES / resistivity soundings."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AuthDep, ReposDep, SettingsDep
from app.engines.ves_interpretation import interpret_ves, interpretation_to_dict
from app.schemas.ves import VESBulkCreate, VESCreate, VESOut

router = APIRouter(prefix="/fields/{field_id}/ves", tags=["ves"])


async def _ingest_one(field_id: UUID, payload: VESCreate, repos, settings) -> dict:
    interp = interpret_ves(
        payload.depth_layers_m, payload.apparent_resistivity_ohmm, settings.ves
    )
    row = await repos.ves.create(
        field_id=field_id,
        lon=payload.lon,
        lat=payload.lat,
        depths=payload.depth_layers_m,
        resistivities=payload.apparent_resistivity_ohmm,
        water_table_m=interp.water_table_m,
        score=interp.aquifer_quality_score,
        notes=payload.operator_notes,
    )
    row["interpretation"] = interpretation_to_dict(interp)
    return row


@router.post("", response_model=VESOut, status_code=status.HTTP_201_CREATED)
async def create_ves(field_id: UUID, payload: VESCreate, repos: ReposDep,
                     settings: SettingsDep, auth: AuthDep):
    await repos.fields.get(field_id, auth.tenant_id)
    return await _ingest_one(field_id, payload, repos, settings)


@router.post("/bulk", response_model=list[VESOut], status_code=status.HTTP_201_CREATED)
async def create_ves_bulk(field_id: UUID, payload: VESBulkCreate, repos: ReposDep,
                          settings: SettingsDep, auth: AuthDep):
    await repos.fields.get(field_id, auth.tenant_id)
    return [await _ingest_one(field_id, s, repos, settings) for s in payload.surveys]


@router.get("", response_model=list[VESOut])
async def list_ves(field_id: UUID, repos: ReposDep, auth: AuthDep):
    await repos.fields.get(field_id, auth.tenant_id)
    return await repos.ves.list_for_field(field_id)
