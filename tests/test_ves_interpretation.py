from __future__ import annotations

import pytest

from app.engines.ves_interpretation import (
    classify_resistivity,
    estimate_water_table,
    interpret_ves,
)
from tests.conftest import DEPTHS, RHO_BARREN, RHO_PRODUCTIVE


def test_classify_bands(settings):
    ves = settings.ves
    assert classify_resistivity(3.0, ves) == ("saline_clay", 0.05)
    assert classify_resistivity(15.0, ves) == ("clayey_low_potential", 0.25)
    assert classify_resistivity(50.0, ves) == ("productive_saturated", 1.0)
    assert classify_resistivity(120.0, ves) == ("weathered_fractured", 0.7)
    assert classify_resistivity(400.0, ves) == ("hard_marginal", 0.35)
    assert classify_resistivity(5000.0, ves) == ("fresh_bedrock", 0.05)


def test_water_table_detection(settings):
    wt = estimate_water_table(DEPTHS, RHO_PRODUCTIVE, settings.ves.water_table_drop_ratio)
    assert wt == pytest.approx(30.0)
    assert estimate_water_table(DEPTHS, RHO_BARREN, settings.ves.water_table_drop_ratio) is None


def test_productive_curve_scores_high(settings):
    it = interpret_ves(DEPTHS, RHO_PRODUCTIVE, settings.ves)
    assert it.water_table_m == pytest.approx(30.0)
    # saturated section = 30..80 m -> 50 m of productive strata
    assert it.saturated_thickness_m == pytest.approx(50.0)
    # weighted band score 1.0, thickness factor 50/60 -> 0.9167
    assert it.aquifer_quality_score == pytest.approx(0.9167, abs=1e-3)
    assert len(it.strata) == len(DEPTHS)


def test_barren_curve_is_damped_and_low(settings):
    it = interpret_ves(DEPTHS, RHO_BARREN, settings.ves)
    assert it.water_table_m is None
    assert it.aquifer_quality_score < 0.2
    assert any("damped" in n for n in it.notes)


def test_score_bounded_zero_one(settings):
    for curve in (RHO_PRODUCTIVE, RHO_BARREN, [5] * len(DEPTHS)):
        it = interpret_ves(DEPTHS, curve, settings.ves)
        assert 0.0 <= it.aquifer_quality_score <= 1.0
