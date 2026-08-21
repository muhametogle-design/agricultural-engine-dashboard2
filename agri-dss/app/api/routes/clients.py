from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import AuthDep, ReposDep
from app.schemas.clients import ClientCreate, ClientOut
from app.schemas.fields import FieldOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(payload: ClientCreate, repos: ReposDep, auth: AuthDep):
    return await repos.clients.create(auth.tenant_id, payload.full_name, payload.phone,
                                      payload.email and str(payload.email))


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(client_id: UUID, repos: ReposDep, auth: AuthDep):
    return await repos.clients.get(client_id, auth.tenant_id)


@router.get("/{client_id}/fields", response_model=list[FieldOut])
async def list_client_fields(client_id: UUID, repos: ReposDep, auth: AuthDep):
    await repos.clients.get(client_id, auth.tenant_id)  # 404 if unknown/foreign
    return await repos.fields.list_for_client(client_id, auth.tenant_id)
