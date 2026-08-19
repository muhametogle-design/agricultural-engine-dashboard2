"""FastAPI dependency injectors - the indirection points tests use to swap
in fakes without touching route code."""
from __future__ import annotations

import uuid
from typing import Annotated

import httpx
from fastapi import Depends, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.core.security import AuthenticationError, decode_access_token
from app.db.repositories import RepositoryBundle
from app.engines.terrain import TerrainProvider


def settings_dep() -> Settings:
    return get_settings()


def repos(request: Request) -> RepositoryBundle:
    return RepositoryBundle(request.app.state.pool)


def http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def terrain(request: Request) -> TerrainProvider:
    return request.app.state.terrain


SettingsDep = Annotated[Settings, Depends(settings_dep)]
ReposDep = Annotated[RepositoryBundle, Depends(repos)]
HttpDep = Annotated[httpx.AsyncClient, Depends(http_client)]
TerrainDep = Annotated[TerrainProvider, Depends(terrain)]


class AuthUser(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str


async def get_current_user(
    request: Request,
    repos_: ReposDep,
    settings_: SettingsDep,
) -> AuthUser:
    """Bearer-token authentication with live user re-validation
    (deactivated users are rejected immediately despite a valid JWT)."""
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("missing bearer token")
    claims = decode_access_token(settings_, token)
    user = await repos_.users.get(claims.sub)
    if user is None:
        raise AuthenticationError("user no longer exists")
    if not user["is_active"]:
        raise AuthenticationError("user is deactivated")
    return AuthUser(user_id=user["id"], tenant_id=user["tenant_id"],
                    email=user["email"], role=user["role"])


AuthDep = Annotated[AuthUser, Depends(get_current_user)]
