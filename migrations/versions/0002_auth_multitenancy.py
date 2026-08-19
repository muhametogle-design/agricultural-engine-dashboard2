"""Auth + multitenancy: tenants, app_users, tenant_id scoping columns.

Upgrade path note: tenant_id is added NULLABLE on existing deployments;
backfill organization ownership, then
  ALTER TABLE clients ALTER COLUMN tenant_id SET NOT NULL;
  ALTER TABLE farm_fields ALTER COLUMN tenant_id SET NOT NULL;
(db/init.sql, the fresh-install bootstrap, already ships them NOT NULL.)

Revision ID: 0002_auth_multitenancy
Revises: 0001_initial_schema
Create Date: 2026-08-11
"""
from __future__ import annotations

from alembic import op

revision = "0002_auth_multitenancy"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tenants (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(64) UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE app_users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            full_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'admin'
                CHECK (role IN ('admin', 'analyst', 'viewer')),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX app_users_email_key ON app_users (lower(email))")
    op.execute("CREATE INDEX idx_app_users_tenant ON app_users(tenant_id)")
    op.execute("ALTER TABLE clients ADD COLUMN tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE farm_fields ADD COLUMN tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE")
    op.execute("CREATE INDEX idx_clients_tenant ON clients(tenant_id)")
    op.execute("CREATE INDEX idx_farm_fields_tenant ON farm_fields(tenant_id)")


def downgrade() -> None:
    op.execute("ALTER TABLE farm_fields DROP COLUMN IF EXISTS tenant_id")
    op.execute("ALTER TABLE clients DROP COLUMN IF EXISTS tenant_id")
    op.execute("DROP TABLE IF EXISTS app_users")
    op.execute("DROP TABLE IF EXISTS tenants")
