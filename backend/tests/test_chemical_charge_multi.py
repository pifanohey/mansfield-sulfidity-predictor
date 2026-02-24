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

    def test_backward_compat_pine_property(self, result):
        assert result.pine is result.fiberline_results["pine"]

    def test_backward_compat_semichem_property(self, result):
        assert result.semichem is result.fiberline_results["semichem"]

    def test_backward_compat_semichem_gl_gpm(self, result):
        assert result.semichem_gl_gpm == result.gl_charge_gpm["semichem"]


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

    def test_pine_property_falls_back_to_first(self, result):
        """With no 'pine' key, .pine falls back to first fiberline."""
        assert result.pine is result.fiberline_results["main"]

    def test_semichem_property_returns_none(self, result):
        assert result.semichem is None


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


# ── Test 4: Backward compatibility — V1 flat params ─────────────────────────

class TestBackwardCompat:
    """V1 path (fiberlines=None) must produce identical results to old API."""

    @pytest.fixture
    def result_v1(self) -> ChemicalChargeResults:
        """Call with flat params (V1 path)."""
        return calculate_chemical_charge(
            gl_flow_to_slaker_gpm=659.0,
            yield_factor=1.033,
            wl_tta_g_L=121.0,
            wl_na2s_g_L=32.5,
            batch_production_bdt_day=636.854,
            cont_production_bdt_day=1250.69,
            wl_ea_g_L=85.0,
            semichem_yield=0.7019,
            pine_yield=0.5694,
            semichem_ea_pct=0.0365,
            pine_ea_pct=0.122,
            dregs_underflow_gpm=12.9,
            semichem_gl_ea_pct=0.017,
            gl_aa_g_L=43.65,
            gl_na2s_g_L=31.74,
        )

    @pytest.fixture
    def result_v2(self) -> ChemicalChargeResults:
        """Call with fiberlines param (V2 path)."""
        return calculate_chemical_charge(
            fiberlines=[PINE_FL, SEMICHEM_FL],
            gl_flow_to_slaker_gpm=659.0,
            yield_factor=1.033,
            wl_tta_g_L=121.0,
            wl_na2s_g_L=32.5,
            wl_ea_g_L=85.0,
            gl_aa_g_L=43.65,
            gl_na2s_g_L=31.74,
            dregs_underflow_gpm=12.9,
        )

    def test_v1_has_pine_and_semichem(self, result_v1):
        assert result_v1.pine is not None
        assert result_v1.semichem is not None

    def test_v1_fiberline_results_dict(self, result_v1):
        assert "pine" in result_v1.fiberline_results
        assert "semichem" in result_v1.fiberline_results

    def test_v1_semichem_gl_gpm_property(self, result_v1):
        assert result_v1.semichem_gl_gpm > 0
        assert result_v1.semichem_gl_gpm == result_v1.gl_charge_gpm["semichem"]

    def test_total_production_matches(self, result_v1, result_v2):
        assert abs(result_v1.total_production_bdt_day - result_v2.total_production_bdt_day) < 0.01

    def test_total_wl_demand_matches(self, result_v1, result_v2):
        assert abs(result_v1.total_wl_demand_gpm - result_v2.total_wl_demand_gpm) < 0.01

    def test_pine_wl_demand_matches(self, result_v1, result_v2):
        assert abs(result_v1.pine.wl_demand_gpm - result_v2.pine.wl_demand_gpm) < 0.01

    def test_semichem_wl_demand_matches(self, result_v1, result_v2):
        assert abs(result_v1.semichem.wl_demand_gpm - result_v2.semichem.wl_demand_gpm) < 0.01

    def test_semichem_gl_gpm_matches(self, result_v1, result_v2):
        assert abs(result_v1.semichem_gl_gpm - result_v2.semichem_gl_gpm) < 0.01

    def test_initial_sulfidity_matches(self, result_v1, result_v2):
        assert abs(result_v1.initial_sulfidity_pct - result_v2.initial_sulfidity_pct) < 0.001

    def test_wl_flow_from_slaker_matches(self, result_v1, result_v2):
        assert abs(result_v1.wl_flow_from_slaker_gpm - result_v2.wl_flow_from_slaker_gpm) < 0.01
