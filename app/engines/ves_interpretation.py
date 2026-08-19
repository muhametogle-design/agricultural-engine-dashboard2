"""VES (Vertical Electrical Sounding) curve interpretation.

Consumes Schlumberger-style apparent-resistivity soundings from the partner
survey machine (Ohm-m vs depth) and derives:

  * per-stratum classification (resistivity bands, configurable - calibrate
    with the local hydrogeologist for the actual geology);
  * estimated water table depth: the deepest sharp resistivity DROP
    (contract into a conductive, saturated unit) is taken as the water
    table proxy;
  * aquifer quality score in [0, 1]: thickness-weighted band score over the
    saturated section, scaled by how much saturated thickness exists
    relative to a reference thickness. Curves with no detected water table
    are damped (x0.6) to encode interpretation uncertainty.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import VesInterpretationSettings


@dataclass
class Stratum:
    top_m: float
    bottom_m: float
    resistivity_ohmm: float
    classification: str
    score: float


@dataclass
class VESInterpretation:
    aquifer_quality_score: float
    water_table_m: float | None
    saturated_thickness_m: float
    strata: list[Stratum] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def classify_resistivity(rho: float, settings: VesInterpretationSettings) -> tuple[str, float]:
    for upper, label, score in settings.bands:
        if rho < upper:
            return label, score
    label, score = settings.bands[-1][1], settings.bands[-1][2]
    return label, score


def estimate_water_table(
    depths: list[float], resistivities: list[float], drop_ratio: float
) -> float | None:
    """First strong downward contract in rho below the near-surface noise zone."""
    best_knee: float | None = None
    best_ratio = 1.0
    for i in range(len(depths) - 1):
        if depths[i] < 3.0:  # ignore topsoil/dry-zone noise
            continue
        ratio = resistivities[i + 1] / resistivities[i]
        if ratio < drop_ratio and ratio < best_ratio:
            best_ratio = ratio
            best_knee = (depths[i] + depths[i + 1]) / 2.0
    return best_knee


def interpret_ves(
    depths: list[float],
    resistivities: list[float],
    settings: VesInterpretationSettings,
) -> VESInterpretation:
    """Depth arrays are strictly increasing (validated at the API boundary)."""
    # Stratum for sample i spans previous depth -> its depth; the top sample
    # owns 0 -> d0.
    strata: list[Stratum] = []
    prev = 0.0
    for d, rho in zip(depths, resistivities):
        label, score = classify_resistivity(rho, settings)
        strata.append(Stratum(top_m=prev, bottom_m=d, resistivity_ohmm=rho,
                              classification=label, score=score))
        prev = d

    water_table = estimate_water_table(depths, resistivities, settings.water_table_drop_ratio)
    notes: list[str] = []

    if water_table is not None:
        saturated = [s for s in strata if s.top_m >= water_table - 1e-9 or s.bottom_m > water_table]
        # Clip the stratum straddling the water table
        clipped: list[Stratum] = []
        for s in saturated:
            top = max(s.top_m, water_table)
            if s.bottom_m > top:
                clipped.append(Stratum(top, s.bottom_m, s.resistivity_ohmm,
                                       s.classification, s.score))
        saturated = clipped
        dampener = 1.0
    else:
        saturated = strata
        dampener = 0.6
        notes.append("no clear water table signature; score damped x0.6 for uncertainty")

    thickness = sum(s.bottom_m - s.top_m for s in saturated)
    if thickness <= 0:
        return VESInterpretation(0.0, water_table, 0.0, strata, notes + ["no saturated section"])

    weighted = sum(s.score * (s.bottom_m - s.top_m) for s in saturated) / thickness
    thickness_factor = min(1.0, thickness / settings.reference_thickness_m)
    score = round(weighted * (0.5 + 0.5 * thickness_factor) * dampener, 4)
    notes.append(
        f"saturated section {thickness:.1f} m, mean band score {weighted:.2f}, "
        f"thickness factor {thickness_factor:.2f}"
    )
    return VESInterpretation(score, water_table, round(thickness, 2), strata, notes)


def interpretation_to_dict(it: VESInterpretation) -> dict:
    return {
        "aquifer_quality_score": it.aquifer_quality_score,
        "estimated_water_table_depth_m": it.water_table_m,
        "saturated_thickness_m": it.saturated_thickness_m,
        "strata": [
            {
                "top_m": s.top_m,
                "bottom_m": s.bottom_m,
                "resistivity_ohmm": s.resistivity_ohmm,
                "classification": s.classification,
                "score": s.score,
            }
            for s in it.strata
        ],
        "notes": it.notes,
    }
