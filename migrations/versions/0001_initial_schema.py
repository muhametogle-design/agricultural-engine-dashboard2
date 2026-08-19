"""Baseline schema: clients, farm_fields, environmental cache, VES, master plans.

Matches db/init.sql as originally delivered (pre-auth). Fresh installs that
bootstrap from db/init.sql should `alembic stamp head` instead of replaying.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-11
"""
from __future__ import annotations

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute(
        """
        CREATE TABLE clients (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            full_name VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            email VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE farm_fields (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            field_name VARCHAR(100) NOT NULL,
            boundary GEOMETRY(Polygon, 4326) NOT NULL,
            center_point GEOMETRY(Point, 4326) NOT NULL,
            area_hectares NUMERIC(10, 2),
            perimeter_meters NUMERIC(10, 2),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT farm_fields_area_positive CHECK (area_hectares > 0),
            CONSTRAINT farm_fields_valid_boundary CHECK (ST_IsValid(boundary))
        )
        """
    )
    op.execute("CREATE INDEX idx_farm_fields_boundary ON farm_fields USING GIST(boundary)")
    op.execute("CREATE INDEX idx_farm_fields_client ON farm_fields(client_id)")
    op.execute(
        """
        CREATE TABLE field_environmental_data (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            field_id UUID REFERENCES farm_fields(id) ON DELETE CASCADE,
            ph_water NUMERIC(4, 2),
            clay_percentage NUMERIC(5, 2),
            sand_percentage NUMERIC(5, 2),
            silt_percentage NUMERIC(5, 2),
            soil_organic_carbon NUMERIC(6, 2),
            nitrogen_content NUMERIC(6, 2),
            cec_mmolc_kg NUMERIC(7, 2),
            avg_annual_rainfall_mm NUMERIC(8, 2),
            avg_temp_celsius NUMERIC(4, 2),
            annual_et0_mm NUMERIC(8, 2),
            raw_soilgrids_json JSONB,
            raw_nasa_power_json JSONB,
            fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT field_environmental_data_one_row_per_field UNIQUE (field_id),
            CONSTRAINT env_ph_range CHECK (ph_water IS NULL OR (ph_water >= 0 AND ph_water <= 14))
        )
        """
    )
    op.execute("CREATE INDEX idx_env_field ON field_environmental_data(field_id)")
    op.execute(
        """
        CREATE TABLE ves_groundwater_surveys (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            field_id UUID REFERENCES farm_fields(id) ON DELETE CASCADE,
            survey_point GEOMETRY(Point, 4326) NOT NULL,
            depth_layers_m NUMERIC[] NOT NULL,
            apparent_resistivity_ohmm NUMERIC[] NOT NULL,
            estimated_water_table_depth_m NUMERIC(6, 2),
            aquifer_quality_score NUMERIC(3, 2),
            operator_notes TEXT,
            surveyed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ves_arrays_equal_length
                CHECK (cardinality(depth_layers_m) = cardinality(apparent_resistivity_ohmm)),
            CONSTRAINT ves_arrays_nonempty CHECK (cardinality(depth_layers_m) >= 2),
            -- resistivity positivity enforced at the API boundary
            -- (Postgres CHECK constraints cannot contain subqueries)
            CONSTRAINT ves_score_range
                CHECK (aquifer_quality_score IS NULL OR (aquifer_quality_score BETWEEN 0 AND 1))
        )
        """
    )
    op.execute("CREATE INDEX idx_ves_surveys_point ON ves_groundwater_surveys USING GIST(survey_point)")
    op.execute("CREATE INDEX idx_ves_surveys_field ON ves_groundwater_surveys(field_id)")
    op.execute(
        """
        CREATE TABLE farm_master_plans (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            field_id UUID REFERENCES farm_fields(id) ON DELETE CASCADE,
            optimal_well_point GEOMETRY(Point, 4326),
            recommended_drilling_depth_m NUMERIC(6, 2),
            top_suitable_crops JSONB,
            soil_amendment_recommendations TEXT[],
            fencing_post_count INT,
            fencing_wire_rolls_required INT,
            fencing_total_cost_est NUMERIC(10, 2),
            layout_zones_geojson JSONB,
            generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute("CREATE INDEX idx_master_plans_well ON farm_master_plans USING GIST(optimal_well_point)")
    op.execute("CREATE INDEX idx_master_plans_field_latest ON farm_master_plans(field_id, generated_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS farm_master_plans")
    op.execute("DROP TABLE IF EXISTS ves_groundwater_surveys")
    op.execute("DROP TABLE IF EXISTS field_environmental_data")
    op.execute("DROP TABLE IF EXISTS farm_fields")
    op.execute("DROP TABLE IF EXISTS clients")
