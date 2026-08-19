"""asyncpg connection pool lifecycle management."""
from __future__ import annotations

import asyncpg

from app.core.logging import get_logger

log = get_logger(__name__)


async def create_pool(dsn: str) -> asyncpg.Pool:
    log.info("Creating Postgres connection pool")
    return await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10, command_timeout=30)


async def close_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()
