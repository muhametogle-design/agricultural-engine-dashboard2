"""Rule-based crop matching engine.

Each crop rule (YAML) declares criteria in one of two shapes:
  * window    (hard_min, opt_min, opt_max, hard_max) -> trapezoidal score
  * threshold (min)                                  -> ramp from 0.6*min to min

Criterion weights normalize per crop. The environmental feature vector is
the cached field profile; `effective_rainfall_mm` = climatology rainfall +
operator-supplied irrigation. Output ranks all candidate crops, tags
limiting factors, and emits soil amendment recommendations for the report.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from app.config import CROP_RULES_PATH
from app.core.logging import get_logger

log = get_logger(__name__)

WINDOW_FIELDS = ("hard_min", "opt_min", "opt_max", "hard_max")

RATINGS = [(80.0, "highly_suitable"), (60.0, "suitable"), (40.0, "marginal"), (0.0, "unsuitable")]


@lru_cache(maxsize=1)
def load_rules(path: str = str(CROP_RULES_PATH)) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        rules = yaml.safe_load(fh)
    if not isinstance(rules, dict) or "crops" not in rules:
        raise ValueError("crop rules file malformed: missing 'crops'")
    for crop in rules["crops"]:
        if "name" not in crop or "criteria" not in crop:
            raise ValueError(f"crop rule missing name/criteria: {crop}")
    return rules


def _window_score(value: float, c: dict) -> float:
    if value <= c["hard_min"] or value >= c["hard_max"]:
        return 0.0
    if c["opt_min"] <= value <= c["opt_max"]:
        return 1.0
    if value < c["opt_min"]:
        return (value - c["hard_min"]) / max(c["opt_min"] - c["hard_min"], 1e-9)
    return (c["hard_max"] - value) / max(c["hard_max"] - c["opt_max"], 1e-9)


def _threshold_score(value: float, c: dict) -> float:
    if value >= c["min"]:
        return 1.0
    floor = 0.6 * c["min"]
    if value <= floor:
        return 0.0
    return (value - floor) / max(c["min"] - floor, 1e-9)


def _minmax_score(value: float, c: dict) -> float:
    """{min, max} texture window with soft 15% shoulders."""
    lo, hi = c["min"], c["max"]
    span = hi - lo
    soft = 0.15 * span
    if lo <= value <= hi:
        return 1.0
    if value < lo - soft or value > hi + soft:
        return 0.0
    if value < lo:
        return (value - (lo - soft)) / max(soft, 1e-9)
    return ((hi + soft) - value) / max(soft, 1e-9)


def score_crop(crop: dict, features: dict[str, float | None]) -> dict:
    criteria = crop["criteria"]
    total_w = sum(float(c.get("weight", 1.0)) for c in criteria.values())
    weight_sum, acc = 0.0, 0.0
    limiting: list[tuple[str, float]] = []

    for name, c in criteria.items():
        w = float(c.get("weight", 1.0)) / total_w
        value = features.get(name)
        if value is None:
            continue  # unknown feature: excluded, weights renormalize
        if "min" in c and "max" in c and not set(WINDOW_FIELDS) & set(c):
            s = _minmax_score(float(value), c)
        elif set(WINDOW_FIELDS) & set(c):
            s = _window_score(float(value), c)
        else:
            s = _threshold_score(float(value), c)
        acc += w * s
        weight_sum += w
        if s < 0.6:
            limiting.append((name, round(s, 3)))

    score = round(100.0 * acc / weight_sum, 1) if weight_sum > 0 else 0.0
    rating = next(label for bound, label in RATINGS if score >= bound)
    limiting.sort(key=lambda t: t[1])
    return {
        "crop": crop["name"],
        "category": crop.get("category"),
        "score": score,
        "rating": rating,
        "limiting_factors": [n for n, _ in limiting],
        "notes": crop.get("notes", []),
        "fixes_nitrogen": crop.get("fixes_nitrogen", False),
        "irrigated_default": crop.get("irrigated_default", False),
    }


def match_crops(
    env: dict[str, float | None],
    supplemental_irrigation_mm: float = 0.0,
    rules_path: str = str(CROP_RULES_PATH),
) -> list[dict]:
    """`env` keys: ph_water, clay_percentage, soil_organic_carbon, cec_mmolc_kg,
    nitrogen_content, avg_annual_rainfall_mm, avg_temp_celsius,
    coldest_month_min_temp_c, annual_et0_mm."""
    rainfall = env.get("avg_annual_rainfall_mm")
    features: dict[str, float | None] = {
        "effective_rainfall_mm": (rainfall + supplemental_irrigation_mm) if rainfall is not None else None,
        "temp_mean_c": env.get("avg_temp_celsius"),
        "coldest_month_min_c": env.get("coldest_month_min_temp_c"),
        "ph": env.get("ph_water"),
        "clay_pct": env.get("clay_percentage"),
        "soc_gkg": env.get("soil_organic_carbon"),
        "cec_mmolc_kg": env.get("cec_mmolc_kg"),
    }
    results = [score_crop(c, features) for c in load_rules(rules_path)["crops"]]
    results.sort(key=lambda r: r["score"], reverse=True)
    log.info("crop matching: top=%s (%.1f)", results[0]["crop"], results[0]["score"])
    return results


def recommend_amendments(env: dict[str, float | None]) -> list[str]:
    """Soil amendment recommendations for the master plan (TEXT[] column)."""
    out: list[str] = []
    ph = env.get("ph_water")
    soc = env.get("soil_organic_carbon")
    n = env.get("nitrogen_content")
    cec = env.get("cec_mmolc_kg")
    clay = env.get("clay_percentage")

    if ph is not None and ph < 5.5:
        out.append(f"Acidic soil (pH {ph:.1f}): apply agricultural lime per soil test; "
                   "band P fertilizer to reduce fixation.")
    if ph is not None and ph > 8.0:
        out.append(f"Alkaline soil (pH {ph:.1f}): incorporate elemental sulfur/organic matter; "
                   "use ammonium-based N and foliar micronutrients (Fe, Zn, Mn).")
    if soc is not None and soc < 10:
        out.append(f"Low SOC ({soc:.1f} g/kg): 5-10 t/ha compost or farmyard manure; "
                   "retain residues and rotate with legumes.")
    if n is not None and n < 1.0 and (soc is None or soc >= 10):
        out.append(f"Low total N ({n:.2f} g/kg): starter N at planting; "
                   "include a legume phase in the rotation.")
    if cec is not None and cec < 10:
        out.append(f"Low CEC ({cec:.1f} mmol(c)/kg): split fertilizer applications; "
                   "build organic matter to improve nutrient retention.")
    if clay is not None and clay > 45:
        out.append(f"Heavy clay ({clay:.0f}%): consider gypsum where sodicity is confirmed; "
                   "avoid trafficking when wet; use raised beds for vegetables.")
    if clay is not None and clay < 10:
        out.append(f"Very sandy soil ({clay:.0f}% clay): frequent light irrigation; "
                   "mulch and organic matter additions to lift water-holding capacity.")
    if not out:
        out.append("No critical soil constraints detected from SoilGrids profile; "
                   "confirm with a composite field soil test.")
    return out
