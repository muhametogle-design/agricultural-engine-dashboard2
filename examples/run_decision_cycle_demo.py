"""End-to-end engine dry-run WITHOUT the database or external APIs:
synthetic field -> VES interpretation -> well siting -> crop matching ->
fencing BOM -> master layout -> consolidated JSON report.

Run:  python examples/run_decision_cycle_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root

from app.config import get_settings
from app.engines import crop_matching, infrastructure, well_siting, zoning
from app.engines.terrain import NullTerrainProvider
from app.engines.ves_interpretation import interpret_ves

CENTER = (45.318, 2.046)

FIELD = {
    "type": "Polygon",
    "coordinates": [[
        [45.317, 2.045], [45.319, 2.045], [45.319, 2.047],
        [45.317, 2.047], [45.317, 2.045],
    ]],
}

# Synthetic partner-machine soundings: (lon, lat, depths_m, rho_ohmm)
SOUNDINGS = [
    (45.3184, 2.0463, [2, 5, 10, 20, 40, 80], [800, 600, 400, 200, 40, 25]),   # productive
    (45.3176, 2.0458, [2, 5, 10, 20, 40, 80], [300, 220, 150, 90, 55, 30]),    # moderate
    (45.3172, 2.0466, [2, 5, 10, 20, 40, 80], [900, 1200, 1500, 1800, 2200, 2600]),  # barren
]

# Cached-style environmental row (as returned by the ingestion chain)
ENV = {
    "ph_water": 7.6, "clay_percentage": 22.0, "sand_percentage": 61.0,
    "silt_percentage": 17.0, "soil_organic_carbon": 8.5, "nitrogen_content": 0.9,
    "cec_mmolc_kg": 14.0, "avg_annual_rainfall_mm": 320.0, "avg_temp_celsius": 27.8,
    "annual_et0_mm": 1650.0, "coldest_month_min_temp_c": 21.0,
}


def main() -> None:
    settings = get_settings()

    ves_records = []
    for lon, lat, depths, rho in SOUNDINGS:
        it = interpret_ves(depths, rho, settings.ves)
        ves_records.append({
            "lon": lon, "lat": lat,
            "aquifer_quality_score": it.aquifer_quality_score,
            "estimated_water_table_depth_m": it.water_table_m,
            "interpretation_notes": it.notes,
        })

    siting = well_siting.run_well_siting(FIELD, ves_records, settings, NullTerrainProvider())
    crops = crop_matching.match_crops(ENV, supplemental_irrigation_mm=300.0)
    amendments = crop_matching.recommend_amendments(ENV)
    bom = infrastructure.fencing_bom(perimeter_m=884.0, corner_count=4, gates=None,
                                   settings=settings.fencing)
    well = (siting.optimal_lon, siting.optimal_lat) if siting.optimal_lon else None
    layout = zoning.generate_master_layout(FIELD, well, settings)

    report = {
        "field_summary": {"name": "demo-shamba", "area_ha": 4.85, "perimeter_m": 884.0},
        "environmental": ENV,
        "ves_interpretations": ves_records,
        "well_siting": {
            "optimal_well_point": siting.optimal_point_geojson(),
            "recommended_drilling_depth_m": siting.recommended_drilling_depth_m,
            "composite_score": siting.composite_score,
            "factor_weights_used": siting.factor_weights_used,
            "candidate_sites": siting.candidates,
            "coverage": siting.coverage,
        },
        "top_crops": crops[:6],
        "soil_amendment_recommendations": amendments,
        "fencing": bom.to_dict(),
        "layout_zones_metadata": layout["metadata"],
        "layout_zone_names": [f["properties"]["zone"] for f in layout["features"]],
        "zones_count": len(layout["features"]),
    }
    out = Path(__file__).with_name("sample_master_plan_report.json")
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"report written -> {out}")
    print(json.dumps({k: report[k] for k in ("well_siting",)}, indent=2, default=str)[:900])


if __name__ == "__main__":
    main()
