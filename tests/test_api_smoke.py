"""API wiring smoke tests: in-memory persistence fakes + auth override
(no Postgres needed). Auth flows themselves are covered in test_auth_api.py."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pyproj import Geod
from shapely.geometry import shape

from app.api import deps
from app.core.errors import NotFoundError
from app.main import create_app

TENANT = uuid.uuid4()


class FakeClients:
    def __init__(self):
        self.store: dict = {}

    async def create(self, tenant_id, full_name, phone, email):
        cid = uuid.uuid4()
        self.store[cid] = {
            "id": cid, "tenant_id": tenant_id, "full_name": full_name,
            "phone": phone, "email": email,
            "created_at": datetime.now(timezone.utc),
        }
        return self.store[cid]

    async def get(self, client_id, tenant_id):
        row = self.store.get(client_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise NotFoundError(f"client {client_id} not found")
        return row


class FakeFields:
    def __init__(self):
        self.store: dict = {}
        self._geod = Geod(ellps="WGS84")

    async def create(self, tenant_id, client_id, field_name, boundary_geojson):
        fid = uuid.uuid4()
        geom = shape(boundary_geojson)
        area_m2, perim_m = self._geod.geometry_area_perimeter(geom)
        row = {
            "id": fid, "tenant_id": tenant_id, "client_id": client_id,
            "field_name": field_name, "boundary": boundary_geojson,
            "center_point": {"type": "Point", "coordinates": [geom.centroid.x, geom.centroid.y]},
            "area_hectares": round(abs(area_m2) / 10_000, 2),
            "perimeter_meters": round(perim_m, 2),
            "created_at": datetime.now(timezone.utc),
        }
        self.store[fid] = row
        return row

    async def get(self, field_id, tenant_id):
        row = self.store.get(field_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise NotFoundError(f"field {field_id} not found")
        return row


class FakeRepos:
    def __init__(self):
        self.clients = FakeClients()
        self.fields = FakeFields()


def _client_with_fakes() -> TestClient:
    app = create_app()
    fake = FakeRepos()  # shared across requests within one test
    auth = deps.AuthUser(user_id=uuid.uuid4(), tenant_id=TENANT,
                         email="tester@agri.app", role="admin")
    app.dependency_overrides[deps.repos] = lambda: fake
    app.dependency_overrides[deps.get_current_user] = lambda: auth
    app.state.pool = None
    app.state.terrain = None
    return TestClient(app)


def test_healthz():
    assert _client_with_fakes().get("/healthz").json() == {"status": "ok"}


def test_point_mode_field_creation():
    client = _client_with_fakes()
    r = client.post("/api/v1/clients", json={"full_name": "Amina Yusuf"})
    assert r.status_code == 201
    client_id = r.json()["id"]

    r = client.post(
        "/api/v1/fields",
        json={
            "client_id": client_id,
            "field_name": "shamba-1",
            "input": {"mode": "point", "lon": 45.318, "lat": 2.046, "area_ha": 1.0},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["boundary"]["type"] == "Polygon"
    assert body["area_hectares"] == 1.0
    assert body["tenant_id"] == str(TENANT)
    assert 390 < body["perimeter_meters"] < 420  # ~100 m geodesic sides

    r = client.get(f"/api/v1/fields/{body['id']}")
    assert r.status_code == 200
    assert r.json()["center_point"]["type"] == "Point"


def test_polygon_validation_rejects_open_ring():
    client = _client_with_fakes()
    r = client.post(
        "/api/v1/fields",
        json={
            "client_id": str(uuid.uuid4()),
            "field_name": "bad",
            "input": {"mode": "polygon", "geometry": {
                "type": "Polygon",
                "coordinates": [[[45.0, 2.0], [45.01, 2.0], [45.01, 2.01]]],  # open ring
            }},
        },
    )
    assert r.status_code == 422


def test_unknown_client_404():
    client = _client_with_fakes()
    r = client.post(
        "/api/v1/fields",
        json={
            "client_id": str(uuid.uuid4()),
            "field_name": "x",
            "input": {"mode": "point", "lon": 45.3, "lat": 2.0},
        },
    )
    assert r.status_code == 404
    assert r.json()["type"] == "urn:agri-dss:not_found"
