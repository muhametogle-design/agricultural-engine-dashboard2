from __future__ import annotations

from app.engines.infrastructure import fencing_bom


def test_bom_exact_arithmetic(settings):
    s = settings.fencing
    bom = fencing_bom(perimeter_m=400.0, corner_count=4, gates=None, settings=s)
    assert bom.gates == 1                          # 400 m / 400 m-per-gate
    adjusted = 400.0 - 1 * s.gate_width_m          # 396.4
    assert bom.strainer_posts == 4 + 7             # corners + ceil(396.4/60)
    assert bom.line_posts == 100 - 11              # ceil(396.4/4) minus strainers
    assert bom.gate_posts == 2
    assert bom.total_posts == bom.line_posts + bom.strainer_posts + 2
    expected_wire = adjusted * s.wire_strands * (1 + s.wastage_fraction)
    assert bom.wire_length_m == round(expected_wire, 1)
    assert bom.wire_rolls == 5                     # ceil(1680.7 / 400)


def test_explicit_gates_and_cost_total(settings):
    s = settings.fencing
    bom = fencing_bom(perimeter_m=1000.0, corner_count=4, gates=3, settings=s)
    assert bom.gates == 3
    total = sum(bom.cost_breakdown.values())
    assert bom.total_cost == round(total, 2)
    assert "labor" in bom.cost_breakdown           # include_labor=True by default
    assert bom.assumptions["wire_strands"] == 4


def test_zero_perimeter_rejected(settings):
    import pytest

    with pytest.raises(ValueError):
        fencing_bom(0.0, 4, None, settings.fencing)
