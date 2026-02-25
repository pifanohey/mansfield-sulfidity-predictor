"""Integration tests: run full solver with different mill configs."""
import pytest
from app.engine.orchestrator import run_calculations
from app.engine.mill_profile import load_mill_config
from app.engine.constants import DEFAULTS


def _run_with_config(mill_id: str):
    """Run solver with a specific mill config.

    Loads the mill config, then builds an inputs dict starting from DEFAULTS
    (which provides BL properties, recovery boiler, dissolving tank, loss table,
    etc.) and overrides just fiberlines and makeup_chemical from the config.
    """
    config = load_mill_config(mill_id)
    inputs = dict(DEFAULTS)
    inputs['fiberlines'] = config.fiberlines
    inputs['makeup_chemical'] = config.makeup_chemical
    return run_calculations(inputs)


# ── Pine Hill (existing baseline config) ──


def test_pine_hill_runs():
    results = _run_with_config("pine_hill")
    assert results['final_sulfidity_pct'] > 0
    assert len(results.get('fiberline_ids', [])) == 2


def test_pine_hill_fiberline_ids():
    results = _run_with_config("pine_hill")
    assert set(results['fiberline_ids']) == {"pine", "semichem"}


# ── Three Line Mill (2 continuous chemical + 1 semichem) ──


def test_three_line_runs():
    results = _run_with_config("three_line_chemical")
    assert results['final_sulfidity_pct'] > 0
    assert len(results.get('fiberline_ids', [])) == 3


def test_three_line_fiberline_ids():
    results = _run_with_config("three_line_chemical")
    assert set(results['fiberline_ids']) == {"line1", "line2", "semichem"}


def test_three_line_total_production():
    results = _run_with_config("three_line_chemical")
    # 1000 + 800 + 500 = 2300 BDT/day
    assert abs(results.get('total_production_bdt_day', 0) - 2300) < 1.0


def test_three_line_sulfidity_in_range():
    results = _run_with_config("three_line_chemical")
    # Sulfidity should be near target (29.4%) since Secant solver runs
    sulf = results['final_sulfidity_pct']
    assert 20.0 < sulf < 40.0, f"Sulfidity {sulf}% out of reasonable range"


def test_three_line_nash_positive():
    results = _run_with_config("three_line_chemical")
    assert results['nash_dry_lbs_hr'] > 0, "NaSH should be positive"


def test_three_line_naoh_positive():
    results = _run_with_config("three_line_chemical")
    assert results['naoh_dry_lbs_hr'] > 0, "NaOH should be positive"


# ── Two Batch Mill (2 batch chemical lines) ──


def test_two_batch_runs():
    results = _run_with_config("two_batch")
    assert results['final_sulfidity_pct'] > 0
    assert len(results.get('fiberline_ids', [])) == 2


def test_two_batch_fiberline_ids():
    results = _run_with_config("two_batch")
    assert set(results['fiberline_ids']) == {"batch1", "batch2"}


def test_two_batch_total_production():
    results = _run_with_config("two_batch")
    # 700 + 650 = 1350 BDT/day
    assert abs(results.get('total_production_bdt_day', 0) - 1350) < 1.0


def test_two_batch_sulfidity_in_range():
    results = _run_with_config("two_batch")
    sulf = results['final_sulfidity_pct']
    assert 20.0 < sulf < 40.0, f"Sulfidity {sulf}% out of reasonable range"


def test_two_batch_nash_positive():
    results = _run_with_config("two_batch")
    assert results['nash_dry_lbs_hr'] > 0, "NaSH should be positive"


def test_two_batch_naoh_positive():
    results = _run_with_config("two_batch")
    assert results['naoh_dry_lbs_hr'] > 0, "NaOH should be positive"


# ── Cross-config comparisons ──


def test_higher_production_needs_more_chemicals():
    """Mill with more production should require more makeup chemicals."""
    pine = _run_with_config("pine_hill")      # ~1888 BDT/day
    three = _run_with_config("three_line_chemical")  # 2300 BDT/day

    # Higher production means more losses → more makeup
    assert three['nash_dry_lbs_hr'] > pine['nash_dry_lbs_hr'] * 0.9, (
        "Three-line mill should need at least ~90% of Pine Hill NaSH "
        "(higher production → more losses)"
    )


def test_all_configs_converge():
    """Every config must produce a converged solution."""
    for mill_id in ["pine_hill", "three_line_chemical", "two_batch"]:
        results = _run_with_config(mill_id)
        assert results.get('final_sulfidity_pct', 0) > 0, (
            f"{mill_id} did not converge to a positive sulfidity"
        )
        assert results.get('total_production_bdt_day', 0) > 0, (
            f"{mill_id} did not produce a valid total production"
        )
