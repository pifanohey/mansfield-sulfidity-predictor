"""Tests for _combine_smelts() and _combine_dt_inputs() helpers."""
import pytest

from app.engine.orchestrator import _combine_smelts, _combine_dt_inputs
from app.engine.recovery_boiler import SmeltComposition, RecoveryBoilerInputs
from app.engine.mill_profile import DissolvingTankConfig


# ── Helper factories ─────────────────────────────────────────────────────────

def _make_smelt(**overrides):
    defaults = dict(
        na_lbs_hr=5000.0, k_lbs_hr=200.0, s_lbs_hr=1500.0,
        reduction_eff_pct=95.0, s_retention_strong=0.986,
        ash_na_na2o=100.0, ash_s_na2o_equiv=50.0, rb_losses_na2o_lbs_hr=300.0,
        potential_na_alkali=6000.0, potential_k_alkali=250.0,
        potential_s_alkali=3000.0, active_sulfide=2800.0, dead_load=150.0,
        tta_lbs_hr=8000.0, smelt_sulfidity_pct=35.0,
        dry_solids_lbs_hr=50000.0, bl_s_pct_fired=4.5,
    )
    defaults.update(overrides)
    return SmeltComposition(**defaults)


def _make_rb_inputs(**overrides):
    defaults = dict(
        bl_flow_gpm=340.0, bl_tds_pct=69.1, bl_temp_f=253.5,
        bl_na_pct_mixed=19.5, bl_s_pct_mixed=4.5, bl_k_pct=1.58,
        bl_density_lb_gal=10.5, dry_solids_lbs_hr=50000.0,
        virgin_solids_lbs_hr=46500.0, virgin_plus_ash_lbs_hr=50000.0,
        as_fired_solids_lbs_hr=52000.0, ash_solids_lbs_hr=3500.0,
        ash_na_na2o=100.0, ash_s_na2o=50.0,
        saltcake_na_lbs_hr=720.0, saltcake_s_lbs_hr=500.0,
        rb_losses_na2o_lbs_hr=300.0, na_lbs_hr=5000.0, k_lbs_hr=200.0,
        s_lbs_hr=1500.0, bl_s_pct_fired=4.5,
    )
    defaults.update(overrides)
    return RecoveryBoilerInputs(**defaults)


# ── _combine_smelts tests ────────────────────────────────────────────────────

class TestCombineSmelts:

    def test_single_item_identity(self):
        """Single-item list returns items unchanged."""
        s = _make_smelt()
        r = _make_rb_inputs()
        combined_rb, combined_s = _combine_smelts([s], [r])
        assert combined_s is s
        assert combined_rb is r

    def test_two_equal_halves_sum_extensive(self):
        """Two half-capacity RBs should sum to full extensive values."""
        s1 = _make_smelt(tta_lbs_hr=4000, active_sulfide=1400, dry_solids_lbs_hr=25000)
        s2 = _make_smelt(tta_lbs_hr=4000, active_sulfide=1400, dry_solids_lbs_hr=25000)
        r1 = _make_rb_inputs(bl_flow_gpm=170, dry_solids_lbs_hr=25000)
        r2 = _make_rb_inputs(bl_flow_gpm=170, dry_solids_lbs_hr=25000)
        combined_rb, combined_s = _combine_smelts([s1, s2], [r1, r2])
        assert combined_s.tta_lbs_hr == pytest.approx(8000.0)
        assert combined_s.active_sulfide == pytest.approx(2800.0)
        assert combined_s.dry_solids_lbs_hr == pytest.approx(50000.0)
        assert combined_rb.bl_flow_gpm == pytest.approx(340.0)

    def test_sulfidity_recomputed(self):
        """Combined sulfidity = total active_sulfide / total tta."""
        s1 = _make_smelt(tta_lbs_hr=6000, active_sulfide=2100, dry_solids_lbs_hr=30000, bl_s_pct_fired=4.0)
        s2 = _make_smelt(tta_lbs_hr=4000, active_sulfide=1400, dry_solids_lbs_hr=20000, bl_s_pct_fired=5.0)
        r1 = _make_rb_inputs(dry_solids_lbs_hr=30000)
        r2 = _make_rb_inputs(dry_solids_lbs_hr=20000)
        _, combined_s = _combine_smelts([s1, s2], [r1, r2])
        expected_sulf = (2100 + 1400) / (6000 + 4000) * 100
        assert combined_s.smelt_sulfidity_pct == pytest.approx(expected_sulf, rel=1e-4)

    def test_bl_s_pct_fired_weighted(self):
        """bl_s_pct_fired should be flow-weighted by dry solids."""
        s1 = _make_smelt(dry_solids_lbs_hr=30000, bl_s_pct_fired=4.0)
        s2 = _make_smelt(dry_solids_lbs_hr=20000, bl_s_pct_fired=5.0)
        r1 = _make_rb_inputs(dry_solids_lbs_hr=30000)
        r2 = _make_rb_inputs(dry_solids_lbs_hr=20000)
        _, combined_s = _combine_smelts([s1, s2], [r1, r2])
        expected = (4.0 * 30000 + 5.0 * 20000) / 50000
        assert combined_s.bl_s_pct_fired == pytest.approx(expected, rel=1e-4)


# ── _combine_dt_inputs tests ─────────────────────────────────────────────────

GLOBAL_DEFAULTS = {
    'ww_flow_gpm': 625.0,
    'ww_tta_lb_ft3': 1.07978,
    'ww_sulfidity': 0.2550,
    'shower_flow_gpm': 60.0,
    'smelt_density_lb_ft3': 110.0,
    'gl_target_tta_lb_ft3': 7.4,
    'gl_causticity': 0.1016,
}


class TestCombineDTInputs:

    def test_empty_list_returns_globals(self):
        result = _combine_dt_inputs([], {}, GLOBAL_DEFAULTS)
        assert result['ww_flow_gpm'] == 625.0
        assert result['gl_target_tta_lb_ft3'] == 7.4

    def test_single_dt_returns_globals(self):
        dt = DissolvingTankConfig(id="dt1", name="DT1", paired_rb_id="rb1")
        result = _combine_dt_inputs([dt], {}, GLOBAL_DEFAULTS)
        assert result['ww_flow_gpm'] == 625.0

    def test_two_dts_sum_flows(self):
        dt1 = DissolvingTankConfig(id="dt1", name="DT1", paired_rb_id="rb1",
                                   defaults={"ww_flow_gpm": 300.0, "shower_flow_gpm": 30.0})
        dt2 = DissolvingTankConfig(id="dt2", name="DT2", paired_rb_id="rb2",
                                   defaults={"ww_flow_gpm": 325.0, "shower_flow_gpm": 30.0})
        result = _combine_dt_inputs([dt1, dt2], {}, GLOBAL_DEFAULTS)
        assert result['ww_flow_gpm'] == pytest.approx(625.0)
        assert result['shower_flow_gpm'] == pytest.approx(60.0)

    def test_two_dts_weighted_avg_tta(self):
        dt1 = DissolvingTankConfig(id="dt1", name="DT1", paired_rb_id="rb1",
                                   defaults={"ww_flow_gpm": 400.0, "ww_tta_lb_ft3": 1.0})
        dt2 = DissolvingTankConfig(id="dt2", name="DT2", paired_rb_id="rb2",
                                   defaults={"ww_flow_gpm": 200.0, "ww_tta_lb_ft3": 1.2})
        result = _combine_dt_inputs([dt1, dt2], {}, GLOBAL_DEFAULTS)
        expected_tta = (1.0 * 400 + 1.2 * 200) / 600
        assert result['ww_tta_lb_ft3'] == pytest.approx(expected_tta, rel=1e-4)

    def test_overrides_applied(self):
        dt1 = DissolvingTankConfig(id="dt1", name="DT1", paired_rb_id="rb1",
                                   defaults={"ww_flow_gpm": 300.0})
        dt2 = DissolvingTankConfig(id="dt2", name="DT2", paired_rb_id="rb2",
                                   defaults={"ww_flow_gpm": 300.0})
        overrides = {"dt1": {"ww_flow_gpm": 350.0}}
        result = _combine_dt_inputs([dt1, dt2], overrides, GLOBAL_DEFAULTS)
        assert result['ww_flow_gpm'] == pytest.approx(650.0)

    def test_gl_target_from_global(self):
        dt1 = DissolvingTankConfig(id="dt1", name="DT1", paired_rb_id="rb1",
                                   defaults={"ww_flow_gpm": 300.0})
        dt2 = DissolvingTankConfig(id="dt2", name="DT2", paired_rb_id="rb2",
                                   defaults={"ww_flow_gpm": 300.0})
        result = _combine_dt_inputs([dt1, dt2], {}, GLOBAL_DEFAULTS)
        assert result['gl_target_tta_lb_ft3'] == 7.4
        assert result['gl_causticity'] == 0.1016
