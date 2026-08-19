"""Authentication & tenant bootstrap: organization registration, login, me."""
from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, status

from app.api.deps import AuthDep, ReposDep, SettingsDep
from app.core.errors import ConflictError
from app.core.security import AuthenticationError, create_access_token, hash_password, verify_password
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, repos: ReposDep, settings: SettingsDep):
    """Bootstrap an organization with its first admin user; returns a token."""
    if await repos.users.get_by_email(payload.email):
        raise ConflictError(f"a user with email '{payload.email}' already exists")
    slug = _slugify(payload.organization_name)
    if await repos.tenants.get_by_slug(slug):
        slug = f"{slug}-{secrets.token_hex(3)}"
    tenant = await repos.tenants.create(payload.organization_name, slug)
    user = await repos.users.create(
        tenant_id=tenant["id"], full_name=payload.full_name,
        email=str(payload.email), password_hash=hash_password(payload.password), role="admin",
    )
    token, expires = create_access_token(
        settings, user_id=user["id"], tenant_id=user["tenant_id"],
        email=user["email"], role=user["role"],
    )
    return TokenResponse(access_token=token, expires_in=expires, user=UserOut(**user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, repos: ReposDep, settings: SettingsDep):
    user = await repos.users.get_by_email(str(payload.email))
    # Deliberately identical error for unknown email and wrong password
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise AuthenticationError("invalid email or password")
    if not user["is_active"]:
        raise AuthenticationError("user is deactivated")
    token, expires = create_access_token(
        settings, user_id=user["id"], tenant_id=user["tenant_id"],
        email=user["email"], role=user["role"],
    )
    user_out = UserOut(**{k: user[k] for k in
                          ("id", "tenant_id", "full_name", "email", "role", "is_active", "created_at")})
    return TokenResponse(access_token=token, expires_in=expires, user=user_out)


@router.get("/me", response_model=UserOut)
async def me(auth: AuthDep, repos: ReposDep):
    user = await repos.users.get(auth.user_id)
    return {k: user[k] for k in ("id", "tenant_id", "full_name", "email", "role", "is_active", "created_at")}
