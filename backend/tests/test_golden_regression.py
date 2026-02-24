"""Regression test: V2 with Pine Hill config must match V1 results exactly."""
import json
import pytest
from app.engine.orchestrator import run_calculations
from app.engine.constants import DEFAULTS


@pytest.fixture(scope="module")
def golden():
    with open("tests/golden_snapshot_pine_hill.json") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def current():
    return run_calculations(dict(DEFAULTS))


CRITICAL_KEYS = [
    "final_sulfidity_pct",
    "nash_dry_lbs_hr",
    "naoh_dry_lbs_hr",
    "smelt_sulfidity_pct",
    "total_wl_demand_gpm",
    "final_wl_tta_g_L",
    "final_wl_na2s_g_L",
    "final_wl_naoh_g_L",
    "bl_na_pct_used",
    "bl_s_pct_used",
    "pine_wl_demand_gpm",
    "semichem_wl_demand_gpm",
]


@pytest.mark.parametrize("key", CRITICAL_KEYS)
def test_critical_output_matches_golden(golden, current, key):
    expected = float(golden[key])
    actual = float(current[key])
    if abs(expected) < 1e-6:
        assert abs(actual) < 1e-4, f"{key}: expected ~0, got {actual}"
    else:
        rel_error = abs(actual - expected) / abs(expected)
        assert rel_error < 0.0001, (
            f"{key}: expected {expected}, got {actual}, rel_error={rel_error:.6f}"
        )
