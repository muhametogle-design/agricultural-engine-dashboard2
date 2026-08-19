"""Seed the demo workspace: tenant, API user, client, field, VES soundings,
and a LIVE SoilGrids + NASA POWER ingestion (requires network).

Usage:  AGRI_DATABASE_DSN=... python scripts/seed_demo.py
Idempotent: the demo tenant is dropped (cascade) before re-creation.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg

from app.config import get_settings
from app.core.security import hash_password
from app.db.repositories import RepositoryBundle
from app.engines.ves_interpretation import interpret_ves
from app.services.environmental import collect_environmental
from app.services.http import create_async_client

DEMO_ORG = "Banaadir Agri Services"
DEMO_SLUG = "banaadir-agri-services"
DEMO_EMAIL = "demo@agri-dss.app"
DEMO_PASSWORD = "demo-pass-2026"

# ~4.9 ha block near the Afgooye corridor, Banaadir
FIELD_POLY = {
    "type": "Polygon",
    "coordinates": [[
        [45.3170, 2.0450], [45.3192, 2.0450], [45.3192, 2.0472],
        [45.3170, 2.0472], [45.3170, 2.0450],
    ]],
}

DEPTH = [2.0, 5.0, 10.0, 20.0, 40.0, 80.0]
SOUNDINGS = [
    (45.3184, 2.0463, [800, 600, 400, 200, 40, 25], "VES-01 NE block - conductive knee @ ~30m"),
    (45.3176, 2.0458, [300, 220, 150, 90, 55, 30], "VES-02 SW block - moderate saturation"),
    (45.3172, 2.0466, [900, 1200, 1500, 1800, 2200, 2600], "VES-03 NW block - resistive basement"),
]


async def main() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_dsn)
    repos = RepositoryBundle(pool)

    await pool.execute("DELETE FROM tenants WHERE slug = $1", DEMO_SLUG)  # cascade wipe
    tenant = await repos.tenants.create(DEMO_ORG, DEMO_SLUG)
    user = await repos.users.create(tenant["id"], "Demo Agronomist", DEMO_EMAIL,
                                    hash_password(DEMO_PASSWORD), "admin")
    client = await repos.clients.create(tenant["id"], "Amina Yusuf Warsame",
                                        "+252-61-555-0100", "amina.yusuf@example.so")
    field = await repos.fields.create(tenant["id"], client["id"],
                                      "Afgooye Corridor Block 7", FIELD_POLY)
    print(f"field: {field['id']}  area={field['area_hectares']} ha  "
          f"perimeter={field['perimeter_meters']} m")

    for lon, lat, rho, notes in [
        (lon, lat, rho, notes) for lon, lat, rho, notes in SOUNDINGS
    ]:
        interp = interpret_ves(DEPTH, rho, settings.ves)
        await repos.ves.create(field["id"], lon, lat, DEPTH, rho,
                               interp.water_table_m, interp.aquifer_quality_score, notes)
        print(f"  VES ({lon},{lat}) score={interp.aquifer_quality_score} "
              f"water_table={interp.water_table_m} m")

    if os.environ.get("SEED_SKIP_LIVE_FETCH"):
        print("SEED_SKIP_LIVE_FETCH set - skipping live environmental ingestion")
    else:
        http = create_async_client(settings.http)
        bundle = await collect_environmental(
            http, settings, FIELD_POLY, float(field["area_hectares"])
        )
        await repos.environmental.upsert(field["id"], bundle.values)
        await http.aclose()
        print(f"environmental ingested from {bundle.data_sources}: "
              f"pH={bundle.values.get('ph_water')}, clay={bundle.values.get('clay_percentage')}%, "
              f"rain={bundle.values.get('avg_annual_rainfall_mm')} mm/y, "
              f"ET0={bundle.values.get('annual_et0_mm')} mm/y")

    await pool.close()
    print("\nSeed complete.")
    print(f"  login:    {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print(f"  tenant:   {tenant['id']}  ({DEMO_SLUG})")
    print(f"  field_id: {field['id']}")


if __name__ == "__main__":
    asyncio.run(main())
