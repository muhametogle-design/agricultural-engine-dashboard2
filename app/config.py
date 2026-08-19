"""Centralized, environment-driven application configuration."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
CROP_RULES_PATH = PACKAGE_DIR / "engines" / "rules" / "crop_rules.yaml"


class HttpSettings(BaseModel):
    timeout_s: float = 25.0
    max_retries: int = 3
    max_concurrency: int = 8  # caps parallel SoilGrids point queries for polygons
    user_agent: str = "agri-dss/0.1 (agricultural decision support)"


class SoilSettings(BaseModel):
    """SoilGrids v2 query definition. Depth weights drive the 0-30 cm mean."""

    properties: list[str] = Field(
        default_factory=lambda: ["phh2o", "clay", "sand", "silt", "soc", "nitrogen", "cec"]
    )
    depths: list[str] = Field(default_factory=lambda: ["0-5cm", "5-15cm", "15-30cm"])
    # Thickness (cm) of each depth band -> weighted mean over the root zone.
    depth_thickness_cm: list[float] = Field(default_factory=lambda: [5.0, 10.0, 15.0])
    polygon_sample_points: int = 9  # stratified point samples per polygon


class ClimateSettings(BaseModel):
    # Drivers required by the FAO-56 derivation (app/engines/et0.py).
    # NOTE: POWER's climatology/monthly/daily APIs do NOT expose an `ET0`
    # parameter - we derive reference evapotranspiration ourselves.
    parameters: str = "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN"
    community: str = "AG"
    sentinel_value: float = -999.0  # POWER missing-data sentinel


class WellSitingSettings(BaseModel):
    # MCE weights; re-normalized automatically when a factor is unavailable.
    w_ves: float = 0.50
    w_slope: float = 0.25
    w_flowacc: float = 0.25
    idw_power: float = 2.0
    target_grid_cells: int = 1600  # analysis cells per field (adaptive size)
    max_grid_cells: int = 4000
    slope_full_score_pct: float = 2.0  # <= 2 % slope -> score 1
    slope_zero_score_pct: float = 15.0  # >= 15 % slope -> score 0
    min_drilling_depth_m: float = 30.0
    max_drilling_depth_m: float = 200.0
    well_penetration_margin_m: float = 15.0  # drill below estimated water table
    default_drilling_depth_m: float = 80.0   # used when no VES coverage
    min_ves_points: int = 1


class VesInterpretationSettings(BaseModel):
    """Resistivity bands -> aquifer prospectivity score (Ohm-m).

    Tuned generically; MUST be calibrated with the local hydrogeologist:
    clay/saline (low), saturated sands (productive), weathered/fractured
    basement, then fresh bedrock.
    """

    bands: list[tuple[float, str, float]] = Field(
        default_factory=lambda: [
            (5.0, "saline_clay", 0.05),
            (20.0, "clayey_low_potential", 0.25),
            (80.0, "productive_saturated", 1.00),
            (200.0, "weathered_fractured", 0.70),
            (600.0, "hard_marginal", 0.35),
            (float("inf"), "fresh_bedrock", 0.05),
        ]
    )
    water_table_drop_ratio: float = 0.45  # rho[i+1]/rho[i] below this = sharp drop
    reference_thickness_m: float = 60.0   # saturated thickness that maps to score 1


class FencingSettings(BaseModel):
    line_post_spacing_m: float = 4.0
    strainer_interval_m: float = 60.0
    wire_strands: int = 4
    wire_roll_length_m: float = 400.0
    gate_width_m: float = 3.6
    gate_per_perimeter_m: float = 400.0  # auto-gates: at least 1 per this length
    wastage_fraction: float = 0.06
    # Indicative costs (USD) - override per deployment region
    cost_line_post: float = 4.50
    cost_strainer_post: float = 12.00
    cost_gate: float = 85.00
    cost_wire_roll: float = 55.00
    include_labor: bool = True
    labor_per_meter: float = 0.80


class ZoningBand(BaseModel):
    max_area_ha: float
    allocations: dict[str, float]  # fractions, should sum ~<=1; remainder -> production


class ZoningSettings(BaseModel):
    well_pad_side_m: float = 30.0
    road_width_m: float = 6.0
    bands: list[ZoningBand] = Field(
        default_factory=lambda: [
            ZoningBand(
                max_area_ha=1.0,
                allocations={"homestead": 0.08, "orchard": 0.12, "roads_service": 0.04},
            ),
            ZoningBand(
                max_area_ha=10.0,
                allocations={"homestead": 0.04, "orchard": 0.15, "roads_service": 0.04},
            ),
            ZoningBand(
                max_area_ha=float("inf"),
                allocations={"homestead": 0.02, "orchard": 0.20, "roads_service": 0.05},
            ),
        ]
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGRI_", env_nested_delimiter="__", extra="ignore")

    database_dsn: str = "postgresql://postgres:postgres@localhost:5432/agri_dss"
    soilgrids_base_url: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    env_cache_ttl_s: int = 30 * 24 * 3600
    default_point_field_ha: float = 1.0
    jwt_secret: str = "dev-only-secret-change-me-0123456789abcdef"  # >=32 bytes for HS256
    jwt_expiry_hours: int = 12
    dem_path: Optional[str] = Field(default=None, validation_alias="AGRI_TERRAIN__DEM_PATH")
    # Offline HWSD v2.0 (FAO/IIASA) sampling for the Laboratory auto-fill.
    # Point both at files inside the /data volume (see data/hwsd/README.md).
    hwsd_raster: Optional[str] = None
    hwsd_attrs: Optional[str] = None

    http: HttpSettings = Field(default_factory=HttpSettings)
    soil: SoilSettings = Field(default_factory=SoilSettings)
    climate: ClimateSettings = Field(default_factory=ClimateSettings)
    well_siting: WellSitingSettings = Field(default_factory=WellSitingSettings)
    ves: VesInterpretationSettings = Field(default_factory=VesInterpretationSettings)
    fencing: FencingSettings = Field(default_factory=FencingSettings)
    zoning: ZoningSettings = Field(default_factory=ZoningSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()
