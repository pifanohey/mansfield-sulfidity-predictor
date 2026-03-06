"""
Cell-for-cell validation against Excel v4 reference values.

28+ tests covering all critical calculation paths.
"""

import json
import pytest
from pathlib import Path

from app.engine.density import calculate_bl_density
from app.engine.inventory import calculate_liquor_composition, calculate_tank_inventory
from app.engine.recovery_boiler import calculate_full_rb
from app.engine.makeup import (
    calculate_nash_requirement, calculate_naoh_requirement,
    calculate_solution_flow_rates, calculate_final_wl_composition,
)
from app.engine.mill_config import tank_volume_gallons
from app.engine.orchestrator import run_calculations

REF_PATH = Path(__file__).parent / "reference_data" / "excel_v4_values.json"

with open(REF_PATH) as f:
    REF = json.load(f)

INP = REF["inputs"]
EXP = REF["expected"]


def approx(expected, tolerance=None, rel=None):
    if tolerance is not None:
        return pytest.approx(expected, abs=tolerance)
    if rel is not None:
        return pytest.approx(expected, rel=rel)
    return pytest.approx(expected, rel=0.02)


# ── 1. BL Density ─────────────────────────────────────────────
class TestBLDensity:
    def test_bl_density_rb_offset(self):
        """B10: BL density with -0.1 offset."""
        result = calculate_bl_density(INP["bl_tds_pct"], INP["bl_temp_f"], offset=-0.1)
        assert result == approx(EXP["bl_density_lb_gal"], tolerance=0.01)


# ── 2. Liquor Composition ─────────────────────────────────────
class TestLiquorComposition:
    def test_wl_sulfidity(self):
        """F11: WL sulfidity fraction."""
        comp = calculate_liquor_composition(INP["wl_tta"], INP["wl_ea"], INP["wl_aa"])
        assert comp.sulfidity_tta_pct / 100 == approx(EXP["wl_sulfidity_frac"], tolerance=0.001)

    def test_wl_na2s(self):
        """F10: WL Na2S g/L."""
        comp = calculate_liquor_composition(INP["wl_tta"], INP["wl_ea"], INP["wl_aa"])
        assert comp.na2s_g_L == approx(EXP["wl_na2s_g_L"], tolerance=0.1)


# ── 3. Tank Volume ─────────────────────────────────────────────
class TestTankVolume:
    def test_wlc1_volume(self):
        """WLC#1 at 10.2 ft = 152,592 gal."""
        vol = tank_volume_gallons('wlc_1', 10.2)
        assert vol == approx(152592.0, tolerance=1.0)


# ── 4. Recovery Boiler (Full Calculated-Ash Chain) ─────────────
class TestRecoveryBoiler:
    @pytest.fixture
    def rb_result(self):
        """Call calculate_full_rb with Excel v4 inputs."""
        rb_inputs, smelt = calculate_full_rb(
            bl_flow_gpm=INP["bl_flow_gpm"],
            bl_tds_pct=INP["bl_tds_pct"],
            bl_temp_f=INP["bl_temp_f"],
            bl_na_pct_inv=INP["bl_na_pct_inv"],
            bl_s_pct_inv=INP["bl_s_pct_inv"],
            bl_k_pct=INP["bl_k_pct"],
            reduction_eff_pct=INP["reduction_eff_pct"],
            s_retention_strong=INP["s_retention_strong"],
            ash_recycled_pct=INP["ash_recycled_pct"],
            rb_losses_na2o_bdt=INP["rb_losses_na2o_bdt"],
            total_production_bdt_day=INP["total_production_bdt_day"],
            saltcake_flow_lb_hr=INP["saltcake_flow_lb_hr"],
        )
        return rb_inputs, smelt

    def test_bl_na_pct_mixed(self, rb_result):
        """B21: Na% d.s. Virgin+Ash (CALCULATED from inventory + ash)."""
        rb_inputs, _ = rb_result
        assert rb_inputs.bl_na_pct_mixed == approx(EXP["bl_na_pct_mixed"], tolerance=0.1)

    def test_bl_s_pct_mixed(self, rb_result):
        """B26: S% d.s. Virgin+Ash (CALCULATED from inventory + ash)."""
        rb_inputs, _ = rb_result
        assert rb_inputs.bl_s_pct_mixed == approx(EXP["bl_s_pct_mixed"], tolerance=0.1)

    def test_ash_na_na2o(self, rb_result):
        """B49: Ash Na as Na2O (CALCULATED from ash_recycled_pct)."""
        rb_inputs, _ = rb_result
        assert rb_inputs.ash_na_na2o == approx(EXP["ash_na_na2o"], tolerance=50)

    def test_na_input(self, rb_result):
        """B23: Na input lb/hr."""
        _, smelt = rb_result
        assert smelt.na_lbs_hr == approx(EXP["na_lbs_hr"], tolerance=200)

    def test_k_input(self, rb_result):
        """B25: K input lb/hr."""
        _, smelt = rb_result
        assert smelt.k_lbs_hr == approx(EXP["k_lbs_hr"], tolerance=50)

    def test_s_input(self, rb_result):
        """B28: S input lb/hr (including saltcake S)."""
        _, smelt = rb_result
        assert smelt.s_lbs_hr == approx(EXP["s_lbs_hr"], tolerance=50)

    def test_potential_na_alkali(self, rb_result):
        """B29: Potential Na alkali."""
        _, smelt = rb_result
        assert smelt.potential_na_alkali == approx(EXP["potential_na_alkali"], tolerance=200)

    def test_potential_k_alkali(self, rb_result):
        """B30: Potential K alkali."""
        _, smelt = rb_result
        assert smelt.potential_k_alkali == approx(EXP["potential_k_alkali"], tolerance=50)

    def test_potential_s_alkali(self, rb_result):
        """B31: Potential S alkali."""
        _, smelt = rb_result
        assert smelt.potential_s_alkali == approx(EXP["potential_s_alkali"], tolerance=100)

    def test_dead_load(self, rb_result):
        """B33: Dead load."""
        _, smelt = rb_result
        assert smelt.dead_load == approx(EXP["dead_load"], tolerance=50)

    def test_tta(self, rb_result):
        """B34: TTA lb/hr."""
        _, smelt = rb_result
        assert smelt.tta_lbs_hr == approx(EXP["tta_lbs_hr"], tolerance=200)

    def test_active_sulfide(self, rb_result):
        """B32: Active sulfide."""
        _, smelt = rb_result
        assert smelt.active_sulfide == approx(EXP["active_sulfide"], tolerance=100)

    def test_smelt_sulfidity(self, rb_result):
        """B35: Smelt sulfidity."""
        _, smelt = rb_result
        assert smelt.smelt_sulfidity_pct / 100 == approx(EXP["smelt_sulfidity_frac"], tolerance=0.01)


# ── 5. Makeup Calculations ────────────────────────────────────
class TestMakeup:
    def test_na2s_deficit(self):
        """H44: Na2S deficit (using S deficit approach)."""
        result = calculate_nash_requirement(
            target_sulfidity_pct=INP["target_sulfidity_frac"] * 100,
            wl_tta_mass_ton_hr=INP["wl_tta_mass_ton_hr"],
            wl_na2s_mass_ton_hr=INP["wl_na2s_mass_ton_hr"],
            na_deficit_lbs_hr=INP["na_deficit_lbs_hr"],
            s_deficit_lbs_hr=INP["s_deficit_lbs_hr"],
        )
        assert result['na2s_deficit_ton_hr'] == approx(EXP["na2s_deficit_ton_hr"], tolerance=0.05)

    def test_conversion_factor(self):
        """H45: Conversion factor."""
        result = calculate_nash_requirement(
            target_sulfidity_pct=INP["target_sulfidity_frac"] * 100,
            wl_tta_mass_ton_hr=INP["wl_tta_mass_ton_hr"],
            wl_na2s_mass_ton_hr=INP["wl_na2s_mass_ton_hr"],
            na_deficit_lbs_hr=INP["na_deficit_lbs_hr"],
            s_deficit_lbs_hr=INP["s_deficit_lbs_hr"],
        )
        assert result['conversion_factor'] == approx(EXP["conversion_factor"], tolerance=0.01)

    def test_nash_dry(self):
        """H46: NaSH dry lb/hr."""
        result = calculate_nash_requirement(
            target_sulfidity_pct=INP["target_sulfidity_frac"] * 100,
            wl_tta_mass_ton_hr=INP["wl_tta_mass_ton_hr"],
            wl_na2s_mass_ton_hr=INP["wl_na2s_mass_ton_hr"],
            na_deficit_lbs_hr=INP["na_deficit_lbs_hr"],
            s_deficit_lbs_hr=INP["s_deficit_lbs_hr"],
        )
        assert result['nash_dry_lbs_hr'] == approx(EXP["nash_dry_lbs_hr"], tolerance=10)

    def test_na_deficit_remaining(self):
        """H48: Na deficit remaining after NaSH."""
        nash = calculate_nash_requirement(
            target_sulfidity_pct=INP["target_sulfidity_frac"] * 100,
            wl_tta_mass_ton_hr=INP["wl_tta_mass_ton_hr"],
            wl_na2s_mass_ton_hr=INP["wl_na2s_mass_ton_hr"],
            na_deficit_lbs_hr=INP["na_deficit_lbs_hr"],
            s_deficit_lbs_hr=INP["s_deficit_lbs_hr"],
        )
        naoh = calculate_naoh_requirement(INP["na_deficit_lbs_hr"], nash['nash_dry_lbs_hr'])
        assert naoh['na_deficit_remaining'] == approx(EXP["na_deficit_remaining"], tolerance=20)

    def test_naoh_dry(self):
        """H47: NaOH dry lb/hr."""
        nash = calculate_nash_requirement(
            target_sulfidity_pct=INP["target_sulfidity_frac"] * 100,
            wl_tta_mass_ton_hr=INP["wl_tta_mass_ton_hr"],
            wl_na2s_mass_ton_hr=INP["wl_na2s_mass_ton_hr"],
            na_deficit_lbs_hr=INP["na_deficit_lbs_hr"],
            s_deficit_lbs_hr=INP["s_deficit_lbs_hr"],
        )
        naoh = calculate_naoh_requirement(INP["na_deficit_lbs_hr"], nash['nash_dry_lbs_hr'])
        assert naoh['naoh_dry_lbs_hr'] == approx(EXP["naoh_dry_lbs_hr"], tolerance=30)


# ── 6. Solution Flow Rates ────────────────────────────────────
class TestSolutionFlows:
    def test_nash_solution_lbs(self):
        """B46: NaSH solution lb/hr."""
        result = calculate_solution_flow_rates(
            INP["nash_dry_lbs_hr_for_flow"], INP["naoh_dry_lbs_hr_for_flow"],
            INP["nash_conc_pct"] / 100, INP["naoh_conc_pct"] / 100,
            INP["nash_density"], INP["naoh_density"],
        )
        assert result['nash_solution_lbs_hr'] == approx(EXP["nash_solution_lbs_hr"], tolerance=10)

    def test_nash_solution_gpm(self):
        """B47: NaSH solution gpm."""
        result = calculate_solution_flow_rates(
            INP["nash_dry_lbs_hr_for_flow"], INP["naoh_dry_lbs_hr_for_flow"],
            INP["nash_conc_pct"] / 100, INP["naoh_conc_pct"] / 100,
            INP["nash_density"], INP["naoh_density"],
        )
        assert result['nash_solution_gpm'] == approx(EXP["nash_solution_gpm"], tolerance=0.1)

    def test_naoh_solution_lbs(self):
        """B53: NaOH solution lb/hr."""
        result = calculate_solution_flow_rates(
            INP["nash_dry_lbs_hr_for_flow"], INP["naoh_dry_lbs_hr_for_flow"],
            INP["nash_conc_pct"] / 100, INP["naoh_conc_pct"] / 100,
            INP["nash_density"], INP["naoh_density"],
        )
        assert result['naoh_solution_lbs_hr'] == approx(EXP["naoh_solution_lbs_hr"], tolerance=10)

    def test_naoh_solution_gpm(self):
        """B54: NaOH solution gpm."""
        result = calculate_solution_flow_rates(
            INP["nash_dry_lbs_hr_for_flow"], INP["naoh_dry_lbs_hr_for_flow"],
            INP["nash_conc_pct"] / 100, INP["naoh_conc_pct"] / 100,
            INP["nash_density"], INP["naoh_density"],
        )
        assert result['naoh_solution_gpm'] == approx(EXP["naoh_solution_gpm"], tolerance=0.1)


# ── 7. Final WL Composition ───────────────────────────────────
class TestFinalWL:
    @pytest.fixture
    def final(self):
        return calculate_final_wl_composition(
            INP["initial_tta_ton_hr"], INP["initial_na2s_ton_hr"],
            INP["nash_dry_lbs_hr_for_flow"], INP["naoh_dry_lbs_hr_for_flow"],
        )

    def test_tta_from_nash(self, final):
        """B57: TTA from NaSH."""
        assert final['tta_from_nash_lbs_hr'] == approx(EXP["tta_from_nash_lbs_hr"], tolerance=10)

    def test_tta_from_naoh(self, final):
        """B58: TTA from NaOH."""
        assert final['tta_from_naoh_lbs_hr'] == approx(EXP["tta_from_naoh_lbs_hr"], tolerance=10)

    def test_na2s_from_nash(self, final):
        """B59: Na2S from NaSH."""
        assert final['na2s_from_nash_lbs_hr'] == approx(EXP["na2s_from_nash_lbs_hr"], tolerance=10)

    def test_final_tta(self, final):
        """B60: Final TTA ton/hr."""
        assert final['final_tta_ton_hr'] == approx(EXP["final_tta_ton_hr"], tolerance=0.1)

    def test_final_na2s(self, final):
        """B61: Final Na2S ton/hr."""
        assert final['final_na2s_ton_hr'] == approx(EXP["final_na2s_ton_hr"], tolerance=0.1)

    def test_final_sulfidity(self, final):
        """B63: Final sulfidity %."""
        assert final['final_sulfidity_pct'] == approx(EXP["final_sulfidity_pct"], tolerance=0.5)


# ── 8. End-to-End Orchestrator ─────────────────────────────────
class TestOrchestrator:
    def test_orchestrator_runs(self):
        """Orchestrator runs without error with defaults."""
        results = run_calculations({})
        assert 'final_sulfidity_pct' in results
        assert 'nash_dry_lbs_hr' in results
        assert 'smelt_sulfidity_pct' in results
        assert results['total_production_bdt_day'] > 0
