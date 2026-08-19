"""Console smoke: page is served and genuinely interactive-capable."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_console_served():
    app = create_app()
    app.state.pool = None
    app.state.terrain = None
    client = TestClient(app)
    r = client.get("/console")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    for marker in ("L.map(", "/api/v1", "master-plan", "leaflet", "auth/login"):
        assert marker in r.text


def test_dashboard_served():
    app = create_app()
    app.state.pool = None
    app.state.terrain = None
    client = TestClient(app)
    r = client.get("/dashboard")
    assert r.status_code == 200
    for marker in ("Native trees", "Ziziphus mauritiana", "base-active", "Soil engine",
                   "Soil amendment required", "ringAreaM2", "renderSim",
                   "World_Imagery", "mt{s}.google.com"):
        assert marker in r.text


def test_landing_links():
    app = create_app()
    app.state.pool = None
    app.state.terrain = None
    client = TestClient(app)
    r = client.get("/")
    assert "/console" in r.text and "/dashboard" in r.text
