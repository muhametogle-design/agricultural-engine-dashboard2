from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AuthDep, ReposDep, SettingsDep
from app.core.spatial import square_field_from_point
from app.schemas.fields import FieldCreate, FieldOut, PointFieldInput

router = APIRouter(prefix="/fields", tags=["fields"])


@router.post("", response_model=FieldOut, status_code=status.HTTP_201_CREATED)
async def create_field(payload: FieldCreate, repos: ReposDep, settings: SettingsDep,
                       auth: AuthDep):
    """Register a field: mode `point` (GPS tap -> buffered square) or
    mode `polygon` (drawn boundary, GeoJSON EPSG:4326)."""
    if isinstance(payload.input, PointFieldInput):
        area = payload.input.area_ha or settings.default_point_field_ha
        boundary = square_field_from_point(payload.input.lon, payload.input.lat, area)
    else:
        boundary = payload.input.geometry.to_geojson()
    await repos.clients.get(payload.client_id, auth.tenant_id)  # explicit 404 over FK error
    return await repos.fields.create(auth.tenant_id, payload.client_id,
                                     payload.field_name, boundary)


@router.get("", response_model=list[FieldOut])
async def list_fields(repos: ReposDep, auth: AuthDep, limit: int = 50):
    return await repos.fields.list_for_tenant(auth.tenant_id, limit)


@router.get("/{field_id}", response_model=FieldOut)
async def get_field(field_id: UUID, repos: ReposDep, auth: AuthDep):
    return await repos.fields.get(field_id, auth.tenant_id)
