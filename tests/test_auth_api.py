"""Full auth loop with REAL security functions over in-memory repos:
register -> login -> bearer usage -> rejection paths."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api import deps
from app.core.security import hash_password
from app.main import create_app


class FakeTenants:
    def __init__(self):
        self.store: dict = {}

    async def create(self, name, slug):
        if any(t["slug"] == slug for t in self.store.values()):
            from app.core.errors import ConflictError

            raise ConflictError("slug taken")
        tid = uuid.uuid4()
        self.store[tid] = {"id": tid, "name": name, "slug": slug,
                           "created_at": datetime.now(timezone.utc)}
        return self.store[tid]

    async def get_by_slug(self, slug):
        return next((t for t in self.store.values() if t["slug"] == slug), None)


class FakeUsers:
    def __init__(self):
        self.store: dict = {}

    async def create(self, tenant_id, full_name, email, password_hash, role="admin"):
        if any(u["email"].lower() == email.lower() for u in self.store.values()):
            from app.core.errors import ConflictError

            raise ConflictError(f"a user with email '{email}' already exists")
        uid = uuid.uuid4()
        self.store[uid] = {
            "id": uid, "tenant_id": tenant_id, "full_name": full_name, "email": email,
            "password_hash": password_hash, "role": role, "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        return self.store[uid]

    async def get_by_email(self, email):
        return next((u for u in self.store.values()
                     if u["email"].lower() == email.lower()), None)

    async def get(self, user_id):
        return self.store.get(user_id)


class FakeRepos:
    def __init__(self):
        self.tenants = FakeTenants()
        self.users = FakeUsers()


def _client() -> tuple[TestClient, "FakeRepos"]:
    app = create_app()
    fake = FakeRepos()
    app.dependency_overrides[deps.repos] = lambda: fake
    app.state.pool = None
    app.state.terrain = None
    return TestClient(app), fake


def _register(client: TestClient) -> dict:
    r = client.post("/api/v1/auth/register", json={
        "organization_name": "HoA Survey Partners",
        "full_name": "Fartun Ali", "email": "fartun@hoa.app",
        "password": "s3cure-demo-pass",
    })
    assert r.status_code == 201, r.text
    return r.json()


def test_register_login_bearer_roundtrip():
    client, _ = _client()
    reg = _register(client)
    assert reg["user"]["role"] == "admin"
    assert reg["token_type"] == "bearer"

    # Duplicate registration rejected
    r = client.post("/api/v1/auth/register", json={
        "organization_name": "Other Org", "full_name": "X Y",
        "email": "fartun@hoa.app", "password": "another-pass-123",
    })
    assert r.status_code == 409

    # Wrong password -> identical 401 as unknown email (no enumeration)
    r = client.post("/api/v1/auth/login",
                    json={"email": "fartun@hoa.app", "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["type"] == "urn:agri-dss:authentication_failed"

    # Correct login
    r = client.post("/api/v1/auth/login",
                    json={"email": "fartun@hoa.app", "password": "s3cure-demo-pass"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Bearer token authorizes /me; missing header is rejected
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "fartun@hoa.app"
    assert client.get("/api/v1/auth/me").status_code == 401

    # Protected business endpoint without token -> 401 problem JSON
    r = client.get(f"/api/v1/fields/{uuid.uuid4()}")
    assert r.status_code == 401


def test_deactivated_user_rejected_with_valid_token():
    client, fake = _client()
    reg = _register(client)
    token = reg["access_token"]
    # Flip the user inactive behind the token's back
    user = next(iter(fake.users.store.values()))
    user["is_active"] = False
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert "deactivated" in r.json()["detail"]
