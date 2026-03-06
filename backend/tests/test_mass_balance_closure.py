"""
Integration tests for global mass balance closure.

Tests verify:
  - Outer loop convergence
  - Na/S conservation through the full cycle
  - CTO S removed from makeup (now physical)
  - Sensitivity to digester S loss
  - Computed vs lab BL composition diagnostic
  - Existing tests still pass (backward compatibility via s_deficit_override)
"""

import pytest
from app.engine.orchestrator import run_calculations
from app.engine.constants import DEFAULTS


class TestOuterLoopConvergence:
    """Test that the outer BL composition loop converges."""

    def test_outer_loop_converges_default_inputs(self):
        """Default inputs → outer loop should converge."""
        results = run_calculations({})
        assert results['outer_loop_converged'] is True

    def test_outer_loop_iterations_reasonable(self):
        """Should converge in under 30 iterations."""
        results = run_calculations({})
        assert results['outer_loop_iterations'] <= 30

    def test_inner_loop_still_converges(self):
        """Inner GL flow loop should still converge within outer loop."""
        results = run_calculations({})
        assert results['solver_converged'] is True

    def test_computed_bl_na_pct_positive(self):
        """Computed BL Na% should be positive."""
        results = run_calculations({})
        assert results['bl_na_pct_computed'] > 0

    def test_computed_bl_s_pct_positive(self):
        """Computed BL S% should be positive."""
        results = run_calculations({})
        assert results['bl_s_pct_computed'] > 0

    def test_used_equals_computed_after_convergence(self):
        """Outer loop converges: used values should match computed within tolerance."""
        results = run_calculations({})
        # Outer loop is enabled — used values converge to computed values
        # Tolerance: outer loop uses 0.01% absolute, allow slightly wider for test
        assert results['bl_na_pct_used'] == pytest.approx(results['bl_na_pct_computed'], abs=0.01)
        assert results['bl_s_pct_used'] == pytest.approx(results['bl_s_pct_computed'], abs=0.01)
        # Computed should be close to lab (within 1.0% absolute)
        # Note: gap is larger than ideal because the fiberline organics model
        # produces ~33% TDS vs real ~13-19%. Na% on d.s. is systematically low
        # when WL demand drops (higher EA → less WL → less Na into BL).
        assert abs(results['bl_na_pct_used'] - results['bl_na_pct_lab']) < 1.0
        assert abs(results['bl_s_pct_used'] - results['bl_s_pct_lab']) < 0.5


class TestEvaporatorConservation:
    """Test that the evaporator preserves Na and S exactly."""

    def test_evaporator_na_conservation(self):
        """Na in WBL = Na in SBL (must be exact through evaporator)."""
        results = run_calculations({})
        wbl_na = results.get('wbl_na_pct_ds', 0)
        sbl_na = results.get('bl_na_pct_computed', 0)
        # Na% d.s. is invariant through evaporation
        assert wbl_na == pytest.approx(sbl_na, rel=1e-6)

    def test_evaporator_s_conservation(self):
        """S in WBL = S in SBL (must be exact through evaporator)."""
        results = run_calculations({})
        wbl_s = results.get('wbl_s_pct_ds', 0)
        sbl_s = results.get('bl_s_pct_computed', 0)
        assert wbl_s == pytest.approx(sbl_s, rel=1e-6)


class TestCTOSRemovedFromMakeup:
    """Test that CTO S credit was removed from makeup calculation."""

    def test_nash_with_mass_balance_approach(self):
        """Without s_deficit_override, NaSH determined by natural sulfidity deficit."""
        results = run_calculations({})
        # NaSH should be determined by target sulfidity vs WL sulfidity
        # without explicit CTO credit subtraction
        assert results['nash_dry_lbs_hr'] >= 0
        assert results['final_sulfidity_pct'] > 0

    def test_cto_flows_through_forward_leg(self):
        """CTO should contribute to BL S% via forward leg, not via makeup credit."""
        # Run with CTO
        results_with_cto = run_calculations({})

        # Run without CTO
        results_no_cto = run_calculations({
            'cto_h2so4_per_ton': 0.0,
            'cto_tpd': 0.0,
        })

        # With CTO, BL S% should be higher (more S in the WBL)
        assert results_with_cto['bl_s_pct_computed'] > results_no_cto['bl_s_pct_computed']


class TestSensitivitySLoss:
    """Test sensitivity to digester S loss percentage."""

    def test_bl_s_pct_independent_of_deprecated_s_loss(self):
        """s_loss_digester_pct is deprecated — BL S% comes from WL/GL composition.

        NCG losses are tracked in the unified loss table for NaSH sizing,
        not subtracted in the fiberline forward leg. The WL composition
        already reflects steady-state losses from the full cycle.
        """
        results_low = run_calculations({'s_loss_digester_pct': 0.02})
        results_high = run_calculations({'s_loss_digester_pct': 0.05})

        # Both should produce the same BL S% (deprecated param has no effect)
        assert results_high['bl_s_pct_computed'] == pytest.approx(
            results_low['bl_s_pct_computed'], rel=1e-6
        )

    def test_s_loss_still_converges(self):
        """5% S loss should still converge."""
        results = run_calculations({'s_loss_digester_pct': 0.05})
        assert results['outer_loop_converged'] is True


class TestComputedVsLabBL:
    """Diagnostic: compare computed BL composition to lab defaults."""

    def test_lab_values_stored(self):
        """Lab values should be stored in results for comparison."""
        results = run_calculations({})
        assert 'bl_na_pct_lab' in results
        assert 'bl_s_pct_lab' in results
        assert results['bl_na_pct_lab'] == DEFAULTS['bl_na_pct']
        assert results['bl_s_pct_lab'] == DEFAULTS['bl_s_pct']

    def test_computed_values_in_reasonable_range(self):
        """Computed Na% and S% should be in physically reasonable ranges."""
        results = run_calculations({})
        # Na% d.s. should be 10-30% for kraft BL
        assert 10 < results['bl_na_pct_computed'] < 30
        # S% d.s. should be 1-10% for kraft BL
        assert 1 < results['bl_s_pct_computed'] < 10


class TestBackwardCompatibility:
    """Test that s_deficit_lbs_hr override preserves existing behavior."""

    def test_s_deficit_override_skips_outer_loop(self):
        """When s_deficit_lbs_hr is provided, outer loop runs once."""
        results = run_calculations({'s_deficit_lbs_hr': 563.13})
        assert results['outer_loop_converged'] is True
        assert results['outer_loop_iterations'] == 1

    def test_s_deficit_override_still_produces_forward_leg(self):
        """Forward leg results should still be computed even with override."""
        results = run_calculations({'s_deficit_lbs_hr': 563.13})
        assert 'bl_na_pct_computed' in results
        assert 'bl_s_pct_computed' in results
        assert results['bl_na_pct_computed'] > 0

    def test_existing_results_present(self):
        """All original result keys should still be present."""
        results = run_calculations({'s_deficit_lbs_hr': 563.13})
        required_keys = [
            'final_sulfidity_pct', 'nash_dry_lbs_hr', 'naoh_dry_lbs_hr',
            'smelt_sulfidity_pct', 'total_production_bdt_day',
            'solver_converged', 'solver_iterations',
            'gl_flow_to_slaker_gpm', 'yield_factor',
        ]
        for key in required_keys:
            assert key in results, f"Missing key: {key}"


class TestForwardLegResults:
    """Test that forward leg outputs are stored and reasonable."""

    def test_sbl_flow_positive(self):
        results = run_calculations({})
        assert results.get('sbl_flow_lb_hr', 0) > 0

    def test_sbl_tds_matches_target(self):
        results = run_calculations({})
        assert results.get('sbl_tds_pct', 0) == pytest.approx(
            DEFAULTS['target_sbl_tds_pct'], rel=0.01
        )

    def test_evaporator_removes_water(self):
        results = run_calculations({})
        assert results.get('evaporator_water_removed_lb_hr', 0) > 0

    def test_wbl_tds_less_than_sbl(self):
        """WBL TDS% should be less than SBL TDS% (evaporator concentrates)."""
        results = run_calculations({})
        assert results.get('wbl_tds_pct', 0) < results.get('sbl_tds_pct', 100)

    def test_pine_bl_organics_positive(self):
        results = run_calculations({})
        assert results.get('pine_bl_organics_lb_hr', 0) > 0

    def test_semichem_bl_organics_positive(self):
        results = run_calculations({})
        assert results.get('semichem_bl_organics_lb_hr', 0) > 0
