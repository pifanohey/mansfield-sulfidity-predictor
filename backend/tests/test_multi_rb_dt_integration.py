"""Integration tests for multi-RB/DT architecture via orchestrator."""
import pytest
from app.engine.orchestrator import run_calculations
from app.engine.constants import DEFAULTS
from app.engine.mill_profile import (
    RecoveryBoilerConfig, DissolvingTankConfig, load_mill_config,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _pine_hill_inputs():
    """Standard Pine Hill inputs (single RB/DT)."""
    return dict(DEFAULTS)


def _mansfield_inputs():
    """Build Mansfield inputs from mill config JSON."""
    cfg = load_mill_config("mansfield")
    d = dict(cfg.defaults)
    d['fiberlines'] = cfg.fiberlines
    d['recovery_boilers'] = cfg.recovery_boilers
    d['dissolving_tanks'] = cfg.dissolving_tanks
    return d


# ── Single RB backward compatibility ───────────────────────────────────────

class TestSingleRBBackwardCompat:
    """Single-RB mills (Pine Hill) must produce identical results
    whether using legacy flat inputs or explicit single-item RB/DT lists."""

    @pytest.fixture(scope="class")
    def legacy_results(self):
        """Run with DEFAULTS (includes single-item RB/DT lists)."""
        return run_calculations(_pine_hill_inputs())

    @pytest.fixture(scope="class")
    def explicit_results(self):
        """Run with explicit single-item RB/DT config objects."""
        inp = _pine_hill_inputs()
        # Force explicit single-item lists (same as DEFAULTS, but reconstructed)
        inp['recovery_boilers'] = [RecoveryBoilerConfig(
            id="rb1", name="Recovery Boiler", paired_dt_id="dt1",
            defaults={
                "bl_flow_gpm": 340.53, "bl_tds_pct": 69.1, "bl_temp_f": 253.5,
                "reduction_eff_pct": 95.0, "ash_recycled_pct": 0.07,
                "saltcake_flow_lb_hr": 2227.0,
            },
        )]
        inp['dissolving_tanks'] = [DissolvingTankConfig(
            id="dt1", name="Dissolving Tank", paired_rb_id="rb1",
            defaults={
                "ww_flow_gpm": 625.0, "ww_tta_lb_ft3": 1.07978,
                "ww_sulfidity": 0.2550, "shower_flow_gpm": 60.0,
                "smelt_density_lb_ft3": 110.0,
            },
        )]
        return run_calculations(inp)

    def test_sulfidity_matches(self, legacy_results, explicit_results):
        assert legacy_results['final_sulfidity_pct'] == pytest.approx(
            explicit_results['final_sulfidity_pct'], rel=1e-4
        )

    def test_nash_matches(self, legacy_results, explicit_results):
        assert legacy_results['nash_dry_lbs_hr'] == pytest.approx(
            explicit_results['nash_dry_lbs_hr'], rel=1e-4
        )

    def test_naoh_matches(self, legacy_results, explicit_results):
        assert legacy_results['naoh_dry_lbs_hr'] == pytest.approx(
            explicit_results['naoh_dry_lbs_hr'], rel=1e-4
        )

    def test_wl_demand_matches(self, legacy_results, explicit_results):
        assert legacy_results['total_wl_demand_gpm'] == pytest.approx(
            explicit_results['total_wl_demand_gpm'], rel=1e-4
        )


# ── Multi-RB convergence (Mansfield) ───────────────────────────────────────

class TestMansfieldMultiRB:
    """Mansfield mill: 2 RBs, 2 DTs, 3 fiberlines — must converge."""

    @pytest.fixture(scope="class")
    def results(self):
        return run_calculations(_mansfield_inputs())

    def test_converges(self, results):
        assert results['secant_converged'] is True

    def test_hits_target_sulfidity(self, results):
        assert results['final_sulfidity_pct'] == pytest.approx(25.80, abs=0.05)

    def test_nash_positive(self, results):
        assert results['nash_dry_lbs_hr'] > 0

    def test_naoh_positive(self, results):
        assert results['naoh_dry_lbs_hr'] > 0

    def test_three_fiberlines(self, results):
        ids = results.get('fiberline_ids', [])
        assert len(ids) == 3
        assert 'kraft_pine1' in ids
        assert 'kraft_pine2' in ids
        assert 'semichem' in ids

    def test_two_rb_ids(self, results):
        rb_ids = results.get('recovery_boiler_ids', [])
        assert len(rb_ids) == 2
        assert 'rb1' in rb_ids
        assert 'rb2' in rb_ids

    def test_per_rb_results_present(self, results):
        """Per-RB smelt results should be in the output."""
        assert 'rb1_smelt_sulfidity_pct' in results
        assert 'rb2_smelt_sulfidity_pct' in results

    def test_per_rb_sulfidity_reasonable(self, results):
        for rb_id in ['rb1', 'rb2']:
            sulf = results.get(f'{rb_id}_smelt_sulfidity_pct', 0)
            assert 10 < sulf < 50, f"{rb_id} smelt sulfidity {sulf}% out of range"

    def test_total_production(self, results):
        # 1421 + 411 + 783 = 2615 BDT/day
        assert results['total_production_bdt_day'] == pytest.approx(2615.0, rel=0.01)


# ── Half-capacity equivalence ──────────────────────────────────────────────

class TestHalfCapacityEquivalence:
    """Two identical half-capacity RBs should produce similar results
    to a single full-capacity RB."""

    @pytest.fixture(scope="class")
    def single_rb_results(self):
        inp = _pine_hill_inputs()
        return run_calculations(inp)

    @pytest.fixture(scope="class")
    def dual_rb_results(self):
        inp = _pine_hill_inputs()
        half_flow = 340.53 / 2
        half_saltcake = 2227.0 / 2
        inp['recovery_boilers'] = [
            RecoveryBoilerConfig(
                id="rb1", name="RB #1", paired_dt_id="dt1",
                defaults={
                    "bl_flow_gpm": half_flow, "bl_tds_pct": 69.1,
                    "bl_temp_f": 253.5, "reduction_eff_pct": 95.0,
                    "ash_recycled_pct": 0.07, "saltcake_flow_lb_hr": half_saltcake,
                },
            ),
            RecoveryBoilerConfig(
                id="rb2", name="RB #2", paired_dt_id="dt2",
                defaults={
                    "bl_flow_gpm": half_flow, "bl_tds_pct": 69.1,
                    "bl_temp_f": 253.5, "reduction_eff_pct": 95.0,
                    "ash_recycled_pct": 0.07, "saltcake_flow_lb_hr": half_saltcake,
                },
            ),
        ]
        inp['dissolving_tanks'] = [
            DissolvingTankConfig(
                id="dt1", name="DT #1", paired_rb_id="rb1",
                defaults={
                    "ww_flow_gpm": 312.5, "ww_tta_lb_ft3": 1.07978,
                    "ww_sulfidity": 0.2550, "shower_flow_gpm": 30.0,
                    "smelt_density_lb_ft3": 110.0,
                },
            ),
            DissolvingTankConfig(
                id="dt2", name="DT #2", paired_rb_id="rb2",
                defaults={
                    "ww_flow_gpm": 312.5, "ww_tta_lb_ft3": 1.07978,
                    "ww_sulfidity": 0.2550, "shower_flow_gpm": 30.0,
                    "smelt_density_lb_ft3": 110.0,
                },
            ),
        ]
        return run_calculations(inp)

    def test_sulfidity_close(self, single_rb_results, dual_rb_results):
        """Final sulfidity should be very close for equivalent capacity."""
        assert single_rb_results['final_sulfidity_pct'] == pytest.approx(
            dual_rb_results['final_sulfidity_pct'], abs=0.1
        )

    def test_nash_close(self, single_rb_results, dual_rb_results):
        assert single_rb_results['nash_dry_lbs_hr'] == pytest.approx(
            dual_rb_results['nash_dry_lbs_hr'], rel=0.01
        )

    def test_naoh_close(self, single_rb_results, dual_rb_results):
        assert single_rb_results['naoh_dry_lbs_hr'] == pytest.approx(
            dual_rb_results['naoh_dry_lbs_hr'], rel=0.01
        )

    def test_wl_demand_close(self, single_rb_results, dual_rb_results):
        assert single_rb_results['total_wl_demand_gpm'] == pytest.approx(
            dual_rb_results['total_wl_demand_gpm'], rel=0.01
        )


# ── Different RE across RBs ───────────────────────────────────────────────

class TestAsymmetricRBs:
    """Two RBs with different reduction efficiencies should produce
    a blended smelt sulfidity between the two individual values."""

    @pytest.fixture(scope="class")
    def results(self):
        inp = _pine_hill_inputs()
        inp['recovery_boilers'] = [
            RecoveryBoilerConfig(
                id="rb1", name="RB High RE", paired_dt_id="dt1",
                defaults={
                    "bl_flow_gpm": 200.0, "bl_tds_pct": 69.1,
                    "bl_temp_f": 253.5, "reduction_eff_pct": 98.0,
                    "ash_recycled_pct": 0.07, "saltcake_flow_lb_hr": 1300.0,
                },
            ),
            RecoveryBoilerConfig(
                id="rb2", name="RB Low RE", paired_dt_id="dt2",
                defaults={
                    "bl_flow_gpm": 140.53, "bl_tds_pct": 69.1,
                    "bl_temp_f": 253.5, "reduction_eff_pct": 80.0,
                    "ash_recycled_pct": 0.07, "saltcake_flow_lb_hr": 927.0,
                },
            ),
        ]
        inp['dissolving_tanks'] = [
            DissolvingTankConfig(
                id="dt1", name="DT #1", paired_rb_id="rb1",
                defaults={
                    "ww_flow_gpm": 375.0, "ww_tta_lb_ft3": 1.07978,
                    "ww_sulfidity": 0.2550, "shower_flow_gpm": 36.0,
                    "smelt_density_lb_ft3": 110.0,
                },
            ),
            DissolvingTankConfig(
                id="dt2", name="DT #2", paired_rb_id="rb2",
                defaults={
                    "ww_flow_gpm": 250.0, "ww_tta_lb_ft3": 1.07978,
                    "ww_sulfidity": 0.2550, "shower_flow_gpm": 24.0,
                    "smelt_density_lb_ft3": 110.0,
                },
            ),
        ]
        return run_calculations(inp)

    def test_converges(self, results):
        assert results['secant_converged'] is True

    def test_rb1_higher_sulfidity_than_rb2(self, results):
        """Higher RE → higher smelt sulfidity."""
        s1 = results.get('rb1_smelt_sulfidity_pct', 0)
        s2 = results.get('rb2_smelt_sulfidity_pct', 0)
        assert s1 > s2

    def test_combined_sulfidity_between(self, results):
        """Combined smelt sulfidity should be between individual values."""
        s1 = results.get('rb1_smelt_sulfidity_pct', 0)
        s2 = results.get('rb2_smelt_sulfidity_pct', 0)
        combined = results['smelt_sulfidity_pct']
        assert min(s1, s2) <= combined <= max(s1, s2)
