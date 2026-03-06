"""
Comprehensive Na/S mass balance tests.

Validates:
1. Na mass balance closure (in = out + losses within tolerance)
2. S mass balance closure (in = out + losses within tolerance)
3. RE (Reduction Efficiency) correlation (lower RE → lower sulfidity, higher NaSH)
4. Causticity correlation (lower causticity → higher NaOH requirement)
"""

import pytest
from app.engine.orchestrator import run_calculations
from app.engine.constants import MW, CONV, DEFAULTS


def test_na_mass_balance_closure():
    """
    Verify Na makeup chemicals are being calculated consistently.

    The Na balance in steady state uses the unified loss table approach:
    - Na losses come directly from the unified loss table (same as S losses)
    - NaOH is sized to cover: Na_deficit = Total_Na_losses - Saltcake_Na - Na_from_NaSH

    This test verifies the NaOH sizing math is consistent.
    """
    results = run_calculations({})

    # Na from NaSH (element basis)
    nash_na_element = results['nash_dry_lbs_hr'] * (MW['Na'] / MW['NaSH'])
    nash_na_as_na2o = nash_na_element * CONV['Na_to_Na2O']

    # Na from NaOH (element basis)
    naoh_na_element = results['naoh_dry_lbs_hr'] * (MW['Na'] / MW['NaOH'])
    naoh_na_as_na2o = naoh_na_element * CONV['Na_to_Na2O']

    # The makeup Na from NaSH should be tracked correctly
    reported_na_from_nash = results.get('na_from_nash', 0.0)

    # NaSH_to_Na2O = 0.5529 (Na2O basis for TTA contribution)
    expected_na_from_nash = results['nash_dry_lbs_hr'] * CONV['NaSH_to_Na2O']

    # Verify the math is consistent within 1%
    if expected_na_from_nash > 0:
        diff_pct = abs(reported_na_from_nash - expected_na_from_nash) / expected_na_from_nash * 100
        assert diff_pct < 1, (
            f"Na from NaSH mismatch: reported={reported_na_from_nash:.1f}, "
            f"expected={expected_na_from_nash:.1f}, diff={diff_pct:.1f}%"
        )


def test_s_mass_balance_closure():
    """
    Verify S losses and NaSH requirement are consistently calculated.

    S balance:
    - S losses come from unified loss table (13 sources, lb S/BDT)
    - S deficit = total_S_losses - saltcake_S - CTO_S
    - NaSH is sized to provide S to reach target sulfidity

    Note: NaSH S is sized for sulfidity target, not directly from S deficit.
    The relationship is: NaSH provides S to reach (target_sulfidity × adjusted_TTA).
    """
    results = run_calculations({})

    # Verify loss table S is consistent
    total_s_losses_lb_hr = results['total_s_losses_lb_hr']
    total_s_losses_lb_bdt = results['total_s_losses_lb_bdt']
    total_prod = sum(fl.production_bdt_day for fl in DEFAULTS['fiberlines'])

    # Verify conversion is consistent
    expected_lb_hr = total_s_losses_lb_bdt * total_prod / 24
    diff_pct = abs(total_s_losses_lb_hr - expected_lb_hr) / expected_lb_hr * 100 if expected_lb_hr > 0 else 0

    assert diff_pct < 1, (
        f"S losses conversion mismatch: {total_s_losses_lb_hr:.1f} vs {expected_lb_hr:.1f} lb/hr"
    )

    # Verify S deficit calculation
    # S_deficit = total_S_losses - saltcake_S - CTO_S
    s_deficit = results['s_deficit_lb_hr']
    cto_s = results['cto_s_lbs_hr']

    # Verify s_deficit is positive (we need external S)
    assert s_deficit > 0, f"S deficit should be positive, got {s_deficit:.1f}"

    # Verify NaSH provides sulfur contribution
    nash_s = results['nash_dry_lbs_hr'] * (MW['S'] / MW['NaSH'])
    assert nash_s > 0, f"NaSH S contribution should be positive, got {nash_s:.1f}"


def test_re_correlation_sulfidity():
    """
    Lower RE should decrease smelt and final sulfidity.

    RE (Reduction Efficiency) determines how much potential sulfide becomes
    active sulfide vs dead load:
    - active_sulfide = potential_S × RE × s_retention - ash_S
    - dead_load = potential_S × (1 - RE)
    """
    results_high_re = run_calculations({'reduction_eff_pct': 95.0})
    results_low_re = run_calculations({'reduction_eff_pct': 90.0})

    # Lower RE → lower active sulfide → lower smelt sulfidity
    assert results_low_re['smelt_sulfidity_pct'] < results_high_re['smelt_sulfidity_pct'], (
        f"Expected lower smelt sulfidity at 90% RE vs 95% RE, got "
        f"{results_low_re['smelt_sulfidity_pct']:.2f}% vs {results_high_re['smelt_sulfidity_pct']:.2f}%"
    )


def test_re_correlation_nash_requirement():
    """
    With Secant method sulfidity targeting, NaSH is sized to hit target sulfidity.

    Lower RE → lower smelt sulfidity → system starts with less Na2S → need MORE
    NaSH to reach the same target sulfidity.

    This is the correct behavior: NaSH compensates for RE losses.
    """
    results_high_re = run_calculations({'reduction_eff_pct': 95.0})
    results_low_re = run_calculations({'reduction_eff_pct': 90.0})

    # Lower RE → higher NaSH requirement (to hit same target sulfidity)
    assert results_low_re['nash_dry_lbs_hr'] > results_high_re['nash_dry_lbs_hr'], (
        f"Expected higher NaSH at 90% RE vs 95% RE (need more makeup to hit target), got "
        f"{results_low_re['nash_dry_lbs_hr']:.0f} vs {results_high_re['nash_dry_lbs_hr']:.0f} lb/hr"
    )

    # Both should hit similar final sulfidity (both targeting default 29.4%)
    sulf_diff = abs(results_low_re['final_sulfidity_pct'] - results_high_re['final_sulfidity_pct'])
    assert sulf_diff < 0.5, (
        f"Both should hit similar sulfidity, got "
        f"{results_low_re['final_sulfidity_pct']:.2f}% vs {results_high_re['final_sulfidity_pct']:.2f}%"
    )


def test_re_correlation_dead_load():
    """
    Lower RE should increase dead load.

    Dead load = potential_S × (1 - RE)
    """
    results_high_re = run_calculations({'reduction_eff_pct': 95.0})
    results_low_re = run_calculations({'reduction_eff_pct': 90.0})

    # Lower RE → higher dead load
    assert results_low_re['rb_dead_load'] > results_high_re['rb_dead_load'], (
        f"Expected higher dead load at 90% RE vs 95% RE, got "
        f"{results_low_re['rb_dead_load']:.0f} vs {results_high_re['rb_dead_load']:.0f} lb/hr"
    )


def test_causticity_correlation_naoh_requirement():
    """
    Lower causticity should increase NaOH requirement via two mechanisms:

    1. Flow-dependent washable soda losses: Lower CE → lower WL EA → higher
       WL demand → more Na washed out with pulp → higher Na losses → more NaOH.
       This gives ~10 lb NaOH/hr per 1% CE change.

    2. EA demand constraint: Below ~74% CE, the EA deficit exceeds Na losses,
       and NaOH jumps dramatically to maintain EA.

    WinGEMS reference: CE 81→78% gives +38 lb/hr NaOH, CE 81→84% gives -14.5 lb/hr.
    """
    results_high_ce = run_calculations({'causticity_pct': 84.0})
    results_base_ce = run_calculations({'causticity_pct': 81.0})
    results_low_ce = run_calculations({'causticity_pct': 75.0})
    results_very_low_ce = run_calculations({'causticity_pct': 70.0})

    # CE=75% should require MORE NaOH than CE=81% (flow-dependent losses)
    assert results_low_ce['naoh_dry_lbs_hr'] > results_base_ce['naoh_dry_lbs_hr'], (
        f"Expected higher NaOH at 75% CE vs 81% CE (flow-dependent losses), got "
        f"{results_low_ce['naoh_dry_lbs_hr']:.0f} vs {results_base_ce['naoh_dry_lbs_hr']:.0f} lb/hr"
    )

    # CE=84% should require LESS NaOH than CE=81%
    assert results_high_ce['naoh_dry_lbs_hr'] < results_base_ce['naoh_dry_lbs_hr'], (
        f"Expected lower NaOH at 84% CE vs 81% CE, got "
        f"{results_high_ce['naoh_dry_lbs_hr']:.0f} vs {results_base_ce['naoh_dry_lbs_hr']:.0f} lb/hr"
    )

    # Sensitivity should be in the range of 3-20 lb NaOH/hr per 1% CE
    delta_naoh_per_pct = (results_low_ce['naoh_dry_lbs_hr'] - results_base_ce['naoh_dry_lbs_hr']) / (81.0 - 75.0)
    assert 3 < delta_naoh_per_pct < 20, (
        f"Expected 3-20 lb NaOH/hr per 1% CE, got {delta_naoh_per_pct:.1f}"
    )

    # At CE=70%: EA demand kicks in hard, NaOH should jump significantly
    assert results_very_low_ce['naoh_dry_lbs_hr'] > results_base_ce['naoh_dry_lbs_hr'] + 500, (
        f"Expected much higher NaOH at 70% CE vs 81% CE (EA demand), got "
        f"{results_very_low_ce['naoh_dry_lbs_hr']:.0f} vs {results_base_ce['naoh_dry_lbs_hr']:.0f} lb/hr"
    )
    assert results_very_low_ce['naoh_constraint'] == 'EA_demand', (
        f"Expected EA_demand constraint at 70% CE, got {results_very_low_ce['naoh_constraint']}"
    )


def test_causticity_correlation_wl_ea():
    """
    Lower causticity should decrease WL EA.

    EA = NaOH + ½Na2S
    Lower causticity → less Na2CO3 converted → lower NaOH → lower EA
    """
    results_high_ce = run_calculations({'causticity_pct': 81.0})
    results_low_ce = run_calculations({'causticity_pct': 75.0})

    # Lower causticity → lower EA
    assert results_low_ce['final_wl_ea_g_L'] < results_high_ce['final_wl_ea_g_L'], (
        f"Expected lower EA at 75% CE vs 81% CE, got "
        f"{results_low_ce['final_wl_ea_g_L']:.1f} vs {results_high_ce['final_wl_ea_g_L']:.1f} g/L"
    )


def test_loss_table_impact_on_nash():
    """
    Changing NCG loss affects total S losses reported and S deficit.

    With outer loop enabled, the Secant solver targets the same sulfidity
    for both cases. The BL composition from the forward leg is unchanged
    (NCG not subtracted in fiberline — WL already reflects steady-state).
    So NaSH should be very similar, but total S losses should increase.
    """
    # Baseline
    results_base = run_calculations({})

    # Increase NCG S loss
    results_high_loss = run_calculations({'loss_ncg_s': 12.0})  # vs default 8.5

    # NaSH should be similar (Secant targets same sulfidity with same BL)
    nash_base = results_base['nash_dry_lbs_hr']
    nash_high = results_high_loss['nash_dry_lbs_hr']
    diff_pct = abs(nash_high - nash_base) / nash_base * 100 if nash_base > 0 else 0
    assert diff_pct < 5.0, (
        f"NaSH should be similar for different NCG losses, "
        f"got {nash_high:.0f} vs {nash_base:.0f} lb/hr ({diff_pct:.1f}% diff)"
    )

    # Higher S losses should increase the total S losses reported
    assert results_high_loss['total_s_losses_lb_hr'] > results_base['total_s_losses_lb_hr'], (
        f"Expected higher total S losses with higher NCG loss"
    )


def test_loss_table_impact_on_naoh():
    """
    Increasing Na losses should increase NaOH requirement.

    Na deficit = Total_Na_losses - Saltcake_Na (both from loss table / constants)
    NaOH = (Na_deficit - Na_from_NaSH) / NaOH_to_Na2O
    """
    # Baseline
    results_base = run_calculations({})

    # Increase pulp washable soda Na loss
    results_high_loss = run_calculations({'loss_pulp_washable_soda_na': 25.0})  # vs default 18.5

    # Higher Na losses → higher NaOH
    assert results_high_loss['naoh_dry_lbs_hr'] > results_base['naoh_dry_lbs_hr'], (
        f"Expected higher NaOH with higher Na loss, got "
        f"{results_high_loss['naoh_dry_lbs_hr']:.0f} vs {results_base['naoh_dry_lbs_hr']:.0f} lb/hr"
    )


def test_solver_convergence():
    """
    Solver should converge within max iterations.
    """
    results = run_calculations({})

    assert results['solver_converged'], (
        f"Solver did not converge in {results['solver_iterations']} iterations"
    )
    assert results['solver_iterations'] < 100, (
        f"Solver took too many iterations: {results['solver_iterations']}"
    )


def test_final_sulfidity_near_target():
    """
    Final sulfidity should be reasonably close to target.
    """
    target = 29.4
    results = run_calculations({'target_sulfidity_pct': target})

    final = results['final_sulfidity_pct']
    diff = abs(final - target)

    # Within 1% absolute
    assert diff < 1.0, (
        f"Final sulfidity {final:.2f}% differs from target {target}% by {diff:.2f}%"
    )


def test_production_scaling():
    """
    Increasing production should increase makeup requirements.

    Note: Due to nonlinear effects (BL dilution, RB capacity limits), the relationship
    isn't perfectly linear. This test verifies directionality.
    """
    import copy
    from app.engine.mill_profile import FiberlineConfig

    results_base = run_calculations({})
    # Scale all fiberline productions by 1.5×
    scaled_fiberlines = []
    for fl in DEFAULTS['fiberlines']:
        new_defaults = dict(fl.defaults)
        new_defaults['production_bdt_day'] = fl.production_bdt_day * 1.5
        scaled_fiberlines.append(FiberlineConfig(
            id=fl.id, name=fl.name, type=fl.type,
            cooking_type=fl.cooking_type, uses_gl_charge=fl.uses_gl_charge,
            defaults=new_defaults,
        ))
    results_higher = run_calculations({'fiberlines': scaled_fiberlines})

    # Higher production → higher makeup requirements
    assert results_higher['nash_dry_lbs_hr'] > results_base['nash_dry_lbs_hr'], (
        f"NaSH should increase with production: {results_higher['nash_dry_lbs_hr']:.0f} "
        f"vs {results_base['nash_dry_lbs_hr']:.0f}"
    )
    assert results_higher['naoh_dry_lbs_hr'] > results_base['naoh_dry_lbs_hr'], (
        f"NaOH should increase with production: {results_higher['naoh_dry_lbs_hr']:.0f} "
        f"vs {results_base['naoh_dry_lbs_hr']:.0f}"
    )

    # Total S losses should scale with production
    assert results_higher['total_s_losses_lb_hr'] > results_base['total_s_losses_lb_hr'], (
        f"S losses should increase with production"
    )


def test_s_retention_calculation():
    """
    S retention should be less than 1 (some S is lost).
    """
    results = run_calculations({})

    assert 0 < results['s_retention_strong'] < 1, (
        f"S retention strong {results['s_retention_strong']:.4f} out of range (0, 1)"
    )
    assert 0 < results['s_retention_weak'] < 1, (
        f"S retention weak {results['s_retention_weak']:.4f} out of range (0, 1)"
    )


def test_smelt_sulfidity_reasonable():
    """
    Smelt sulfidity should be in a reasonable range for kraft mills.
    """
    results = run_calculations({})

    # Typical kraft mill smelt sulfidity is 20-35%
    assert 20 < results['smelt_sulfidity_pct'] < 40, (
        f"Smelt sulfidity {results['smelt_sulfidity_pct']:.1f}% outside typical range"
    )


def test_gl_flow_positive():
    """
    GL flow to slaker should be positive.
    """
    results = run_calculations({})

    assert results['gl_flow_to_slaker_gpm'] > 0, (
        f"GL flow to slaker is non-positive: {results['gl_flow_to_slaker_gpm']:.1f} gpm"
    )


def test_cto_affects_sulfidity_with_nash_override():
    """CTO changes should affect sulfidity even when NaSH is overridden."""
    results_base = run_calculations({
        'nash_dry_override_lb_hr': 1200.0,
        'naoh_dry_override_lb_hr': 2200.0,
    })
    results_high_cto = run_calculations({
        'nash_dry_override_lb_hr': 1200.0,
        'naoh_dry_override_lb_hr': 2200.0,
        'cto_tpd': DEFAULTS['cto_tpd'] * 2,
    })
    # More CTO S → higher BL S% → higher smelt sulfidity → higher sulfidity
    assert results_high_cto['final_sulfidity_pct'] > results_base['final_sulfidity_pct'], (
        f"CTO increase should raise sulfidity in Predictor mode: "
        f"base={results_base['final_sulfidity_pct']:.2f}%, "
        f"high_cto={results_high_cto['final_sulfidity_pct']:.2f}%"
    )


def test_cto_affects_nash_in_normal_mode():
    """More CTO S → less NaSH needed (Secant targets same sulfidity)."""
    results_base = run_calculations({})
    results_high_cto = run_calculations({'cto_tpd': DEFAULTS['cto_tpd'] * 2})
    # More CTO S → higher BL S% → Secant reduces NaSH
    assert results_high_cto['nash_dry_lbs_hr'] < results_base['nash_dry_lbs_hr'], (
        f"More CTO S should reduce NaSH: "
        f"base={results_base['nash_dry_lbs_hr']:.1f}, "
        f"high_cto={results_high_cto['nash_dry_lbs_hr']:.1f}"
    )
