from __future__ import annotations

from app.engines.crop_matching import match_crops, recommend_amendments


def _by_name(results):
    return {r["crop"]: r for r in results}


def test_arid_profile_ranks_drought_crops_first(arid_env):
    results = match_crops(arid_env)
    scores = _by_name(results)
    top5 = [r["crop"] for r in results[:5]]
    assert any(c in top5 for c in ("pearl_millet", "sorghum"))
    assert scores["pearl_millet"]["score"] > scores["maize"]["score"]
    # Banana demands 900 mm hard-minimum rainfall -> rainfall criterion scores 0
    assert scores["banana"]["score"] < scores["sorghum"]["score"]
    assert "effective_rainfall_mm" in scores["banana"]["limiting_factors"]
    # Scores sorted descending
    assert [r["score"] for r in results] == sorted((r["score"] for r in results), reverse=True)


def test_irrigation_lifts_water_limited_crops(arid_env):
    dry = _by_name(match_crops(arid_env, supplemental_irrigation_mm=0))
    # 320 mm climatology + 900 mm irrigation = 1220 mm effective, inside the
    # banana optimum and under the tomato hard maximum (1400 mm)
    wet = _by_name(match_crops(arid_env, supplemental_irrigation_mm=900))
    assert wet["banana"]["score"] > dry["banana"]["score"]
    assert wet["tomato"]["score"] > dry["tomato"]["score"]


def test_frost_gate(arid_env):
    cold = dict(arid_env, coldest_month_min_temp_c=0.0, avg_temp_celsius=18.0)
    results = _by_name(match_crops(cold))
    # mango requires coldest month >= 10 C -> threshold scores ~0
    assert results["mango"]["score"] < results["sorghum"]["score"]


def test_missing_features_renormalize(arid_env):
    sparse = {k: None for k in arid_env}
    sparse.update({"avg_annual_rainfall_mm": 500.0, "avg_temp_celsius": 25.0,
                   "ph_water": 6.5})
    results = match_crops(sparse)
    assert all(0 <= r["score"] <= 100 for r in results)


def test_amendment_rules():
    recs = recommend_amendments({"ph_water": 8.3, "soil_organic_carbon": 6.0,
                                 "nitrogen_content": 0.8, "cec_mmolc_kg": 7.0,
                                 "clay_percentage": 8.0})
    text = " ".join(recs).lower()
    assert "alkaline" in text and "low soc" in text and "cec" in text and "sandy" in text
    assert recommend_amendments({"ph_water": 6.8, "soil_organic_carbon": 25.0,
                                 "nitrogen_content": 2.0, "cec_mmolc_kg": 20.0,
                                 "clay_percentage": 30.0})[0].startswith("No critical")
