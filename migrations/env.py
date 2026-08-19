"""Alembic environment: async (asyncpg) engine, DSN from application settings.

Fresh installs are bootstrapped by db/init.sql (consolidated schema); run
`alembic stamp head` once on such databases so later migrations apply cleanly.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import get_settings

config = context.config
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass


def _async_url() -> str:
    dsn = get_settings().database_dsn
    for prefix in ("postgresql://", "postgres://"):
        if dsn.startswith(prefix):
            return "postgresql+asyncpg://" + dsn[len(prefix):]
    return dsn


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=None,
                      compare_type=False, transaction_per_migration=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _async_url()
    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.",
                                           poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


asyncio.run(run_migrations_online())
