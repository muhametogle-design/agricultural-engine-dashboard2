"""Shared fixtures: synthetic payloads and field geometries."""
from __future__ import annotations

import pytest

from app.config import Settings

CENTER_LON, CENTER_LAT = 45.318, 2.046  # Banaadir region


@pytest.fixture()
def settings() -> Settings:
    return Settings()


def make_square_polygon(lon: float = CENTER_LON, lat: float = CENTER_LAT,
                        size_deg: float = 0.002) -> dict:
    """~220 m x 220 m square (~4.8 ha) as GeoJSON (EPSG:4326)."""
    h = size_deg / 2.0
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - h, lat - h], [lon + h, lat - h], [lon + h, lat + h],
            [lon - h, lat + h], [lon - h, lat - h],
        ]],
    }


@pytest.fixture()
def square_polygon() -> dict:
    return make_square_polygon()


def make_soilgrids_payload(
    per_depth_values: dict[str, list] | None = None,
    d_factors: dict[str, float] | None = None,
) -> dict:
    """Realistic SoilGrids v2 properties/query response.

    per_depth_values: raw (unscaled) means for [0-5, 5-15, 15-30] cm.
    """
    defaults = {"phh2o": [62, 60, 58], "clay": [180, 220, 260], "sand": [640, 620, 600],
                "silt": [180, 160, 140], "soc": [14, 10, 6], "nitrogen": [140, 110, 70],
                "cec": [200, 190, 170]}
    default_d = {"phh2o": 10, "clay": 10, "sand": 10, "silt": 10, "soc": 10,
                 "nitrogen": 100, "cec": 1}
    values = per_depth_values or defaults
    dfs = d_factors or default_d
    labels = ["0-5cm", "5-15cm", "15-30cm"]
    layers = []
    for prop, vals in values.items():
        layers.append({
            "name": prop,
            "unit_measure": {"d_factor": dfs[prop], "mapped_units": "x", "target_units": "y"},
            "depths": [
                {"label": lab, "range": {"top_depth": t, "bottom_depth": b, "unit_depth": "cm"},
                 "values": {"mean": v}}
                for lab, v, (t, b) in zip(labels, vals, [(0, 5), (5, 15), (15, 30)])
            ],
        })
    return {"type": "Feature", "properties": {"layers": layers}}


def make_power_payload(
    prec_rate: float = 0.8, t2m_ann: float = 27.8,
    null_prec_months: bool = False,
) -> dict:
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    prec = {m: (-999.0 if null_prec_months else prec_rate) for m in months}
    prec["ANN"] = prec_rate
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [CENTER_LON, CENTER_LAT, 22.0]},
        "properties": {
            "parameter": {
                "PRECTOTCORR": prec,
                "T2M": {**{m: t2m_ann for m in months}, "ANN": t2m_ann},
                "T2M_MIN": {**{m: 21.0 for m in months}, "ANN": 21.0},
                "T2M_MAX": {**{m: 33.5 for m in months}, "ANN": 33.5},
                # Absurd on purpose: POWER has no ET0 parameter; the service
                # must DERIVE ET0 and must never read a payload ET0 series.
                "ET0": {**{m: 99.0 for m in months}, "ANN": 99.0},
                "RH2M": {**{m: 74.0 for m in months}, "ANN": 74.0},
                "WS2M": {**{m: 3.1 for m in months}, "ANN": 3.1},
                "ALLSKY_SFC_SW_DWN": {**{m: 21.0 for m in months}, "ANN": 21.0},
            }
        },
    }


# A VES curve with a clear water-table knee at ~30 m (drop 200 -> 40 Ohm-m).
DEPTHS = [2.0, 5.0, 10.0, 20.0, 40.0, 80.0]
RHO_PRODUCTIVE = [800.0, 600.0, 400.0, 200.0, 40.0, 25.0]
# A curve that stays resistive (fresh basement - no water signature).
RHO_BARREN = [900.0, 1200.0, 1500.0, 1800.0, 2200.0, 2600.0]


@pytest.fixture()
def ves_surveys() -> list[dict]:
    """Two soundings: productive near the field center, barren at the corner."""
    import uuid

    return [
        {
            "id": uuid.uuid4(), "lon": CENTER_LON + 0.0004, "lat": CENTER_LAT + 0.0003,
            "aquifer_quality_score": 0.92, "estimated_water_table_depth_m": 30.0,
            "depth_layers_m": DEPTHS, "apparent_resistivity_ohmm": RHO_PRODUCTIVE,
        },
        {
            "id": uuid.uuid4(), "lon": CENTER_LON - 0.0008, "lat": CENTER_LAT - 0.0008,
            "aquifer_quality_score": 0.05, "estimated_water_table_depth_m": None,
            "depth_layers_m": DEPTHS, "apparent_resistivity_ohmm": RHO_BARREN,
        },
    ]


@pytest.fixture()
def arid_env() -> dict:
    """Cached-environmental feature row for a hot semi-arid site."""
    return {
        "ph_water": 7.6,
        "clay_percentage": 22.0,
        "sand_percentage": 61.0,
        "silt_percentage": 17.0,
        "soil_organic_carbon": 8.5,
        "nitrogen_content": 0.9,
        "cec_mmolc_kg": 14.0,
        "avg_annual_rainfall_mm": 320.0,
        "avg_temp_celsius": 27.8,
        "annual_et0_mm": 1650.0,
        "coldest_month_min_temp_c": 21.0,
    }
