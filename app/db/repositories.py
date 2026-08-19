"""PostGIS repository layer - the ONLY module that speaks SQL.

Tenancy model: every business row carries tenant_id (organization). All
lookups are tenant-scoped; cross-tenant access returns 404 (existence of
foreign tenant data is never disclosed). VES / environmental / plans inherit
scoping through their parent field, which routes resolve tenant-safely first.
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import asyncpg

from app.core.errors import ConflictError, NotFoundError


def _decode_geojson_columns(row: dict, columns: tuple[str, ...]) -> dict:
    for col in columns:
        if row.get(col) is not None and isinstance(row[col], str):
            row[col] = json.loads(row[col])
    return row


def _normalize(value: Any) -> Any:
    """asyncpg returns NUMERIC as Decimal (and numeric[] as list[Decimal]);
    engines expect plain floats. Normalize at the repository boundary."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _normalize_columns(row: dict, columns: tuple[str, ...]) -> dict:
    for col in columns:
        if col in row and row[col] is not None:
            row[col] = _normalize(row[col])
    return row


class TenantsRepo:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, name: str, slug: str) -> dict:
        try:
            row = await self.pool.fetchrow(
                "INSERT INTO tenants (name, slug) VALUES ($1, $2) RETURNING *", name, slug
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError(f"organization slug '{slug}' already taken") from exc
        return dict(row)

    async def get_by_slug(self, slug: str) -> dict | None:
        row = await self.pool.fetchrow("SELECT * FROM tenants WHERE slug = $1", slug)
        return dict(row) if row else None


class UsersRepo:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, tenant_id: UUID, full_name: str, email: str,
                     password_hash: str, role: str = "admin") -> dict:
        try:
            row = await self.pool.fetchrow(
                """
                INSERT INTO app_users (tenant_id, full_name, email, password_hash, role)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, tenant_id, full_name, email, role, is_active, created_at
                """,
                tenant_id, full_name, email, password_hash, role,
            )
        except asyncpg.UniqueViolationError as exc:
            raise ConflictError(f"a user with email '{email}' already exists") from exc
        return dict(row)

    async def get_by_email(self, email: str) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT * FROM app_users WHERE lower(email) = lower($1)", email
        )
        return dict(row) if row else None

    async def get(self, user_id: UUID) -> dict | None:
        row = await self.pool.fetchrow("SELECT * FROM app_users WHERE id = $1", user_id)
        return dict(row) if row else None


class ClientsRepo:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, tenant_id: UUID, full_name: str, phone: str | None,
                     email: str | None) -> dict:
        row = await self.pool.fetchrow(
            """
            INSERT INTO clients (tenant_id, full_name, phone, email)
            VALUES ($1, $2, $3, $4)
            RETURNING id, tenant_id, full_name, phone, email, created_at
            """,
            tenant_id, full_name, phone, email,
        )
        return dict(row)

    async def get(self, client_id: UUID, tenant_id: UUID) -> dict:
        row = await self.pool.fetchrow(
            """SELECT id, tenant_id, full_name, phone, email, created_at
               FROM clients WHERE id = $1 AND tenant_id = $2""",
            client_id, tenant_id,
        )
        if row is None:
            raise NotFoundError(f"client {client_id} not found")
        return dict(row)


class FieldsRepo:
    GEOJSON_COLS = ("boundary", "center_point")

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    _SELECT = """
        SELECT id, tenant_id, client_id, field_name,
               ST_AsGeoJSON(boundary)::text AS boundary,
               ST_AsGeoJSON(center_point)::text AS center_point,
               area_hectares, perimeter_meters, created_at
        FROM farm_fields
    """

    async def create(self, tenant_id: UUID, client_id: UUID, field_name: str,
                     boundary_geojson: dict) -> dict:
        try:
            row = await self.pool.fetchrow(
                """
                INSERT INTO farm_fields (tenant_id, client_id, field_name, boundary,
                                         center_point, area_hectares, perimeter_meters)
                SELECT $1, $2, $3, g, ST_Centroid(g),
                       ROUND((ST_Area(g::geography) / 10000.0)::numeric, 2),
                       ROUND(ST_Perimeter(g::geography)::numeric, 2)
                FROM (SELECT ST_SetSRID(ST_GeomFromGeoJSON($4), 4326) AS g) s
                RETURNING id, tenant_id, client_id, field_name,
                          ST_AsGeoJSON(boundary)::text AS boundary,
                          ST_AsGeoJSON(center_point)::text AS center_point,
                          area_hectares, perimeter_meters, created_at
                """,
                tenant_id, client_id, field_name, json.dumps(boundary_geojson),
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise NotFoundError(f"client {client_id} not found in this organization") from exc
        return _decode_geojson_columns(dict(row), self.GEOJSON_COLS)

    async def get(self, field_id: UUID, tenant_id: UUID) -> dict:
        row = await self.pool.fetchrow(
            self._SELECT + " WHERE id = $1 AND tenant_id = $2", field_id, tenant_id
        )
        if row is None:
            raise NotFoundError(f"field {field_id} not found")
        return _decode_geojson_columns(dict(row), self.GEOJSON_COLS)

    async def list_for_client(self, client_id: UUID, tenant_id: UUID) -> list[dict]:
        rows = await self.pool.fetch(
            self._SELECT + " WHERE client_id = $1 AND tenant_id = $2 ORDER BY created_at DESC",
            client_id, tenant_id,
        )
        return [_decode_geojson_columns(dict(r), self.GEOJSON_COLS) for r in rows]

    async def list_for_tenant(self, tenant_id: UUID, limit: int = 50) -> list[dict]:
        rows = await self.pool.fetch(
            self._SELECT + " WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2",
            tenant_id, limit,
        )
        return [_decode_geojson_columns(dict(r), self.GEOJSON_COLS) for r in rows]


class EnvironmentalRepo:
    NUMERIC_COLS = (
        "ph_water", "clay_percentage", "sand_percentage", "silt_percentage",
        "soil_organic_carbon", "nitrogen_content", "cec_mmolc_kg",
        "avg_annual_rainfall_mm", "avg_temp_celsius", "annual_et0_mm",
    )

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get(self, field_id: UUID) -> dict | None:
        row = await self.pool.fetchrow(
            """
            SELECT *, EXTRACT(EPOCH FROM (now() - fetched_at)) AS age_seconds
            FROM field_environmental_data WHERE field_id = $1
            """,
            field_id,
        )
        out = dict(row) if row else None
        if out:
            _normalize_columns(out, self.NUMERIC_COLS)
            out["age_seconds"] = float(out["age_seconds"])
        return out

    async def upsert(self, field_id: UUID, values: dict[str, Any]) -> dict:
        row = await self.pool.fetchrow(
            """
            INSERT INTO field_environmental_data (
                field_id, ph_water, clay_percentage, sand_percentage, silt_percentage,
                soil_organic_carbon, nitrogen_content, cec_mmolc_kg,
                avg_annual_rainfall_mm, avg_temp_celsius, annual_et0_mm,
                raw_soilgrids_json, raw_nasa_power_json
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13::jsonb)
            ON CONFLICT (field_id) DO UPDATE SET
                ph_water = EXCLUDED.ph_water,
                clay_percentage = EXCLUDED.clay_percentage,
                sand_percentage = EXCLUDED.sand_percentage,
                silt_percentage = EXCLUDED.silt_percentage,
                soil_organic_carbon = EXCLUDED.soil_organic_carbon,
                nitrogen_content = EXCLUDED.nitrogen_content,
                cec_mmolc_kg = EXCLUDED.cec_mmolc_kg,
                avg_annual_rainfall_mm = EXCLUDED.avg_annual_rainfall_mm,
                avg_temp_celsius = EXCLUDED.avg_temp_celsius,
                annual_et0_mm = EXCLUDED.annual_et0_mm,
                raw_soilgrids_json = EXCLUDED.raw_soilgrids_json,
                raw_nasa_power_json = EXCLUDED.raw_nasa_power_json,
                fetched_at = now()
            RETURNING *, 0.0 AS age_seconds
            """,
            field_id,
            values.get("ph_water"), values.get("clay_percentage"), values.get("sand_percentage"),
            values.get("silt_percentage"), values.get("soil_organic_carbon"),
            values.get("nitrogen_content"), values.get("cec_mmolc_kg"),
            values.get("avg_annual_rainfall_mm"), values.get("avg_temp_celsius"),
            values.get("annual_et0_mm"),
            json.dumps(values.get("raw_soilgrids_json")) if values.get("raw_soilgrids_json") else None,
            json.dumps(values.get("raw_nasa_power_json")) if values.get("raw_nasa_power_json") else None,
        )
        return dict(row)


class VesRepo:
    NUMERIC_COLS = ("depth_layers_m", "apparent_resistivity_ohmm",
                    "estimated_water_table_depth_m", "aquifer_quality_score")

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    _SELECT = """
        SELECT id, field_id, ST_X(survey_point) AS lon, ST_Y(survey_point) AS lat,
               depth_layers_m, apparent_resistivity_ohmm,
               estimated_water_table_depth_m, aquifer_quality_score,
               operator_notes, surveyed_at
        FROM ves_groundwater_surveys
    """

    async def create(
        self,
        field_id: UUID,
        lon: float,
        lat: float,
        depths: list[float],
        resistivities: list[float],
        water_table_m: float | None,
        score: float,
        notes: str | None,
    ) -> dict:
        try:
            row = await self.pool.fetchrow(
                """
                INSERT INTO ves_groundwater_surveys (
                    field_id, survey_point, depth_layers_m, apparent_resistivity_ohmm,
                    estimated_water_table_depth_m, aquifer_quality_score, operator_notes
                ) VALUES ($1, ST_SetSRID(ST_MakePoint($2, $3), 4326), $4::numeric[], $5::numeric[], $6, $7, $8)
                RETURNING id, field_id, ST_X(survey_point) AS lon, ST_Y(survey_point) AS lat,
                          depth_layers_m, apparent_resistivity_ohmm,
                          estimated_water_table_depth_m, aquifer_quality_score,
                          operator_notes, surveyed_at
                """,
                field_id, lon, lat, depths, resistivities, water_table_m, score, notes,
            )
        except asyncpg.ForeignKeyViolationError as exc:
            raise NotFoundError(f"field {field_id} not found") from exc
        return _normalize_columns(dict(row), self.NUMERIC_COLS)

    async def list_for_field(self, field_id: UUID) -> list[dict]:
        rows = await self.pool.fetch(self._SELECT + " WHERE field_id = $1 ORDER BY surveyed_at", field_id)
        return [_normalize_columns(dict(r), self.NUMERIC_COLS) for r in rows]


class PlansRepo:
    NUMERIC_COLS = ("recommended_drilling_depth_m", "fencing_total_cost_est")

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, field_id: UUID, plan: dict[str, Any]) -> dict:
        well = plan.get("optimal_well_point")  # GeoJSON Point dict or None
        row = await self.pool.fetchrow(
            """
            INSERT INTO farm_master_plans (
                field_id, optimal_well_point, recommended_drilling_depth_m,
                top_suitable_crops, soil_amendment_recommendations,
                fencing_post_count, fencing_wire_rolls_required, fencing_total_cost_est,
                layout_zones_geojson
            ) VALUES (
                $1,
                CASE WHEN $2::text IS NOT NULL
                     THEN ST_SetSRID(ST_GeomFromGeoJSON($2), 4326) END,
                $3, $4::jsonb, $5::text[], $6, $7, $8, $9::jsonb
            )
            RETURNING id, field_id,
                      ST_AsGeoJSON(optimal_well_point)::text AS optimal_well_point,
                      recommended_drilling_depth_m, top_suitable_crops,
                      soil_amendment_recommendations, fencing_post_count,
                      fencing_wire_rolls_required, fencing_total_cost_est,
                      layout_zones_geojson, generated_at
            """,
            field_id,
            json.dumps(well) if well else None,
            plan.get("recommended_drilling_depth_m"),
            json.dumps(plan.get("top_suitable_crops") or []),
            plan.get("soil_amendment_recommendations") or [],
            plan.get("fencing_post_count"),
            plan.get("fencing_wire_rolls_required"),
            plan.get("fencing_total_cost_est"),
            json.dumps(plan.get("layout_zones_geojson")) if plan.get("layout_zones_geojson") else None,
        )
        out = dict(row)
        _decode_geojson_columns(out, ("optimal_well_point", "top_suitable_crops", "layout_zones_geojson"))
        return _normalize_columns(out, self.NUMERIC_COLS)

    async def latest(self, field_id: UUID) -> dict | None:
        row = await self.pool.fetchrow(
            """
            SELECT id, field_id, ST_AsGeoJSON(optimal_well_point)::text AS optimal_well_point,
                   recommended_drilling_depth_m, top_suitable_crops,
                   soil_amendment_recommendations, fencing_post_count,
                   fencing_wire_rolls_required, fencing_total_cost_est,
                   layout_zones_geojson, generated_at
            FROM farm_master_plans
            WHERE field_id = $1
            ORDER BY generated_at DESC LIMIT 1
            """,
            field_id,
        )
        out = dict(row) if row else None
        if out:
            _decode_geojson_columns(out, ("optimal_well_point", "top_suitable_crops", "layout_zones_geojson"))
            _normalize_columns(out, self.NUMERIC_COLS)
        return out


class RepositoryBundle:
    """Aggregates all repositories; constructed per-request (cheap)."""

    def __init__(self, pool: asyncpg.Pool):
        self.tenants = TenantsRepo(pool)
        self.users = UsersRepo(pool)
        self.clients = ClientsRepo(pool)
        self.fields = FieldsRepo(pool)
        self.environmental = EnvironmentalRepo(pool)
        self.ves = VesRepo(pool)
        self.plans = PlansRepo(pool)
