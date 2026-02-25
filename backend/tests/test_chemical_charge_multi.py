"""Tests for multi-fiberline chemical charge calculation (V2 path)."""
import pytest

from app.engine.chemical_charge import (
    calculate_chemical_charge,
    ChemicalChargeResults,
    FiberlineResult,
)
from app.engine.mill_profile import FiberlineConfig


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_fiberline(
    id: str,
    name: str = "",
    type: str = "continuous",
    cooking_type: str = "chemical",
    uses_gl_charge: bool = False,
    production_bdt_day: float = 1000.0,
    yield_pct: float = 0.55,
    ea_pct: float = 0.12,
    gl_ea_pct: float = 0.0,
) -> FiberlineConfig:
    """Convenience builder for FiberlineConfig."""
    return FiberlineConfig(
        id=id,
        name=name or id,
        type=type,
        cooking_type=cooking_type,
        uses_gl_charge=uses_gl_charge,
        defaults={
            "production_bdt_day": production_bdt_day,
            "yield_pct": yield_pct,
            "ea_pct": ea_pct,
            "gl_ea_pct": gl_ea_pct,
        },
    )


# ── Pine Hill defaults (matches pine_hill.json) ─────────────────────────────

PINE_FL = _make_fiberline(
    id="pine",
    name="Pine (Continuous)",
    type="continuous",
    cooking_type="chemical",
    uses_gl_charge=False,
    production_bdt_day=1250.69,
    yield_pct=0.5694,
    ea_pct=0.122,
)

SEMICHEM_FL = _make_fiberline(
    id="semichem",
    name="Semichem (Batch)",
    type="batch",
    cooking_type="semichem",
    uses_gl_charge=True,
    production_bdt_day=636.854,
    yield_pct=0.7019,
    ea_pct=0.0365,
    gl_ea_pct=0.017,
)

# Shared kwargs for GL/WL composition (same as defaults used by V1 path)
COMMON_KWARGS = dict(
    gl_flow_to_slaker_gpm=659.0,
    yield_factor=1.033,
    wl_tta_g_L=121.0,
    wl_na2s_g_L=32.5,
    wl_ea_g_L=85.0,
    gl_tta_g_L=117.0,
    gl_na2s_g_L=31.74,
    gl_aa_g_L=43.65,
    dregs_underflow_gpm=12.9,
)


# ── Test 1: Two fiberlines (Pine Hill defaults) ─────────────────────────────

class TestTwoFiberlines:
    """V2 path with Pine Hill's standard pine + semichem."""

    @pytest.fixture
    def result(self) -> ChemicalChargeResults:
        return calculate_chemical_charge(
            fiberlines=[PINE_FL, SEMICHEM_FL],
            **COMMON_KWARGS,
        )

    def test_both_ids_present(self, result):
        assert "pine" in result.fiberline_results
        assert "semichem" in result.fiberline_results

    def test_total_wl_demand_positive(self, result):
        assert result.total_wl_demand_gpm > 0

    def test_total_production_matches_sum(self, result):
        fl_sum = sum(r.production_bdt_day for r in result.fiberline_results.values())
        assert abs(result.total_production_bdt_day - fl_sum) < 0.01

    def test_total_wl_demand_matches_sum(self, result):
        wl_sum = sum(r.wl_demand_gpm for r in result.fiberline_results.values())
        assert abs(result.total_wl_demand_gpm - wl_sum) < 0.001

    def test_semichem_has_gl_charge(self, result):
        assert result.gl_charge_gpm["semichem"] > 0

    def test_pine_no_gl_charge(self, result):
        assert result.gl_charge_gpm["pine"] == 0.0

    def test_semichem_gl_charge_matches_dict(self, result):
        assert result.gl_charge_gpm["semichem"] > 0


# ── Test 2: Single fiberline ─────────────────────────────────────────────────

class TestSingleFiberline:
    """V2 path with a single chemical fiberline."""

    @pytest.fixture
    def result(self) -> ChemicalChargeResults:
        single = _make_fiberline(
            id="main",
            production_bdt_day=2000.0,
            yield_pct=0.55,
            ea_pct=0.13,
            uses_gl_charge=False,
        )
        return calculate_chemical_charge(
            fiberlines=[single],
            **COMMON_KWARGS,
        )

    def test_single_id_present(self, result):
        assert "main" in result.fiberline_results
        assert len(result.fiberline_results) == 1

    def test_total_equals_single(self, result):
        fl = result.fiberline_results["main"]
        assert abs(result.total_production_bdt_day - fl.production_bdt_day) < 0.01
        assert abs(result.total_wl_demand_gpm - fl.wl_demand_gpm) < 0.001

    def test_no_gl_charge(self, result):
        assert result.gl_charge_gpm["main"] == 0.0


# ── Test 3: Three fiberlines (2 chemical + 1 semichem) ───────────────────────

class TestThreeFiberlines:
    """V2 path with three fiberlines — two chemical, one semichem."""

    @pytest.fixture
    def result(self) -> ChemicalChargeResults:
        fls = [
            _make_fiberline(
                id="line_a",
                production_bdt_day=800.0,
                yield_pct=0.56,
                ea_pct=0.12,
                uses_gl_charge=False,
            ),
            _make_fiberline(
                id="line_b",
                production_bdt_day=600.0,
                yield_pct=0.58,
                ea_pct=0.115,
                uses_gl_charge=False,
            ),
            _make_fiberline(
                id="semichem_line",
                cooking_type="semichem",
                type="batch",
                production_bdt_day=500.0,
                yield_pct=0.70,
                ea_pct=0.04,
                uses_gl_charge=True,
                gl_ea_pct=0.02,
            ),
        ]
        return calculate_chemical_charge(
            fiberlines=fls,
            **COMMON_KWARGS,
        )

    def test_all_three_present(self, result):
        assert len(result.fiberline_results) == 3
        assert "line_a" in result.fiberline_results
        assert "line_b" in result.fiberline_results
        assert "semichem_line" in result.fiberline_results

    def test_total_production_is_sum(self, result):
        expected = 800.0 + 600.0 + 500.0
        assert abs(result.total_production_bdt_day - expected) < 0.01

    def test_total_wl_demand_is_sum(self, result):
        wl_sum = sum(r.wl_demand_gpm for r in result.fiberline_results.values())
        assert abs(result.total_wl_demand_gpm - wl_sum) < 0.001

    def test_only_semichem_line_has_gl(self, result):
        assert result.gl_charge_gpm["line_a"] == 0.0
        assert result.gl_charge_gpm["line_b"] == 0.0
        assert result.gl_charge_gpm["semichem_line"] > 0


