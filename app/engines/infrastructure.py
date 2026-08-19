"""Farm infrastructure engine: perimeter fencing bill of quantities.

Geometry inputs come from PostGIS (geodesic perimeter, corner count from
the exterior ring). BOM logic:
  * one gate per `gate_per_perimeter_m` (min 1) unless explicitly given;
  * strainer (heavy) posts at every corner + every `strainer_interval_m`;
  * line posts fill the remainder at `line_post_spacing_m`;
  * wire length = adjusted perimeter x strands x (1 + wastage);
  * costs from the configurable regional price list.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.config import FencingSettings


@dataclass
class FencingBOM:
    perimeter_m: float
    gates: int
    line_posts: int
    strainer_posts: int
    gate_posts: int
    total_posts: int
    wire_length_m: float
    wire_rolls: int
    cost_breakdown: dict = field(default_factory=dict)
    total_cost: float = 0.0
    assumptions: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "perimeter_m": self.perimeter_m,
            "gates": self.gates,
            "line_posts": self.line_posts,
            "strainer_posts": self.strainer_posts,
            "gate_posts": self.gate_posts,
            "total_posts": self.total_posts,
            "wire_rolls": self.wire_rolls,
            "wire_length_m": self.wire_length_m,
            "cost_breakdown": self.cost_breakdown,
            "total_cost": self.total_cost,
            "assumptions": self.assumptions,
        }


def fencing_bom(
    perimeter_m: float,
    corner_count: int,
    gates: int | None,
    settings: FencingSettings,
) -> FencingBOM:
    if perimeter_m <= 0:
        raise ValueError("perimeter must be positive")

    n_gates = gates if gates is not None else max(
        1, math.ceil(perimeter_m / settings.gate_per_perimeter_m)
    )
    adjusted_perimeter = max(perimeter_m - n_gates * settings.gate_width_m, 0.0)

    strainers = corner_count + math.ceil(adjusted_perimeter / settings.strainer_interval_m)
    line_posts = max(math.ceil(adjusted_perimeter / settings.line_post_spacing_m) - strainers, 0)
    gate_posts = 2 * n_gates
    total_posts = line_posts + strainers + gate_posts

    wire_length = adjusted_perimeter * settings.wire_strands * (1.0 + settings.wastage_fraction)
    wire_rolls = math.ceil(wire_length / settings.wire_roll_length_m)

    breakdown = {
        "line_posts": round(line_posts * settings.cost_line_post, 2),
        "strainer_posts": round(strainers * settings.cost_strainer_post, 2),
        "gate_posts": round(gate_posts * settings.cost_strainer_post, 2),
        "gates": round(n_gates * settings.cost_gate, 2),
        "wire_rolls": round(wire_rolls * settings.cost_wire_roll, 2),
    }
    if settings.include_labor:
        breakdown["labor"] = round(perimeter_m * settings.labor_per_meter, 2)
    total = round(sum(breakdown.values()), 2)

    return FencingBOM(
        perimeter_m=round(perimeter_m, 2),
        gates=n_gates,
        line_posts=line_posts,
        strainer_posts=strainers,
        gate_posts=gate_posts,
        total_posts=total_posts,
        wire_length_m=round(wire_length, 1),
        wire_rolls=wire_rolls,
        cost_breakdown=breakdown,
        total_cost=total,
        assumptions={
            "line_post_spacing_m": settings.line_post_spacing_m,
            "strainer_interval_m": settings.strainer_interval_m,
            "wire_strands": settings.wire_strands,
            "wire_roll_length_m": settings.wire_roll_length_m,
            "gate_width_m": settings.gate_width_m,
            "wastage_fraction": settings.wastage_fraction,
            "currency": "USD",
            "corner_count": corner_count,
        },
    )
