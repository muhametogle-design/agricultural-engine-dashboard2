from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["ops"])


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> dict:
    async with request.app.state.pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ready", "database": "up"}
