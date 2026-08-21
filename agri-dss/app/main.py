"""Application factory: lifespan-managed resources + routers + error mapping."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.deps import get_settings
from app.api.routes import analysis, auth, clients, environmental, fields, health, lab, plans, ves
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.db.pool import close_pool, create_pool
from app.engines.terrain import build_terrain_provider
from app.services.http import create_async_client
from app.services.hwsd import HWSDService

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    app.state.settings = settings
    app.state.pool = await create_pool(settings.database_dsn)
    app.state.http_client = create_async_client(settings.http)
    app.state.terrain = build_terrain_provider(settings.dem_path)
    app.state.hwsd = HWSDService(settings.hwsd_raster, settings.hwsd_attrs)
    log.info("agri-dss %s up; terrain=%s hwsd=%s", __version__,
             type(app.state.terrain).__name__, app.state.hwsd.available)
    yield
    await app.state.http_client.aclose()
    await close_pool(app.state.pool)


LANDING_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Agri-DSS</title><style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#0e1512;color:#dbe7df;font:16px/1.5 system-ui,sans-serif}}
.card{{background:#16211c;border:1px solid #2a3a31;border-radius:14px;padding:32px 40px;max-width:480px}}
h1{{margin:0 0 4px;color:#5fd08a;font-size:22px}} p{{color:#8fa79a;margin:4px 0 20px}}
a.btn{{display:block;text-align:center;background:#5fd08a;color:#0b120e;font-weight:700;
padding:12px;border-radius:10px;text-decoration:none;margin:8px 0}}
a.btn.alt{{background:transparent;color:#5fd08a;border:1px solid #5fd08a}}
code{{background:#0b120e;padding:2px 6px;border-radius:6px;font-size:13px}}
</style></head><body><div class="card">
<h1>Agricultural Spatial DSS</h1>
<p>version {version} — live sandbox: PostGIS + SoilGrids · NASA POWER · terrain DEM</p>
<a class="btn" href="/console">Open the map console →</a>
<a class="btn" href="/dashboard">Open the unified dashboard →</a>
<a class="btn alt" href="/docs">API reference (Swagger)</a>
<p style="margin-top:18px">demo login: <code>demo@agri-dss.app</code> / <code>demo-pass-2026</code></p>
</div></body></html>"""


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agricultural Spatial DSS",
        version=__version__,
        description="Well siting, crop matching and farm infrastructure decision support.",
        lifespan=lifespan,
    )

    # Browser-facing API: permissive for the demo/preview; lock this down to
    # the partner web-map origin list for production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"urn:agri-dss:{exc.code}",
                "title": exc.code.replace("_", " "),
                "status": exc.status_code,
                "detail": exc.message,
                **({"extra": exc.detail} if exc.detail else {}),
            },
        )

    app.include_router(health.router)
    api_prefix = "/api/v1"
    for r in (auth.router, clients.router, fields.router, environmental.router,
              ves.router, analysis.router, plans.router, lab.router):
        app.include_router(r, prefix=api_prefix)

    @app.get("/api")
    async def api_info() -> dict:
        return {"service": "agri-dss", "version": __version__, "docs": "/docs",
                "console": "/console"}

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def landing() -> HTMLResponse:
        html = (LANDING_HTML.replace("{version}", __version__)
                            .replace("{{", "{").replace("}}", "}"))
        return HTMLResponse(html)

    console_path = Path(__file__).resolve().parent / "web" / "console.html"

    @app.get("/console", response_class=HTMLResponse, include_in_schema=False)
    async def console() -> HTMLResponse:
        return HTMLResponse(console_path.read_text(encoding="utf-8"))

    dashboard_path = Path(__file__).resolve().parent / "web" / "dashboard.html"

    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))

    lims_path = Path(__file__).resolve().parent / "web" / "lims.html"

    @app.get("/lims", response_class=HTMLResponse, include_in_schema=False)
    async def lims() -> HTMLResponse:
        return HTMLResponse(lims_path.read_text(encoding="utf-8"))

    web_dir = Path(__file__).resolve().parent / "web"
    app.mount("/web", StaticFiles(directory=web_dir), name="web")

    return app


app = create_app()
