#!/usr/bin/env python3
"""
Na Mass Balance Audit — First Principles

Traces sodium through every unit operation using mass conservation.
Computes Na losses per source independently (not derived from S losses).
Compares with the current loss_factor approach.

All Na values in lb Na2O/hr unless noted.
"""

import sys
sys.path.insert(0, '.')

from app.engine.orchestrator import run_calculations
from app.engine.constants import MW, CONV, DEFAULTS


def main():
    results = run_calculations(DEFAULTS)

    prod_bdt_day = results['total_production_bdt_day']
    prod_bdt_hr = prod_bdt_day / 24

    print("=" * 80)
    print("   Na MASS BALANCE AUDIT — FIRST PRINCIPLES")
    print("=" * 80)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 1: What the model currently computes
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── CURRENT MODEL (loss_factor = {:.4f}) ──".format(
        DEFAULTS.get('loss_factor', 0.0921)))
    print(f"  Na losses (Na2O):     {results['na_losses_lbs_hr']:.1f} lb/hr")
    print(f"  Na losses (element):  {results['na_losses_element_lb_hr']:.1f} lb/hr")
    print(f"  Saltcake Na (Na2O):   {results.get('rb_potential_na_alkali', 0):.1f} (potential)")

    saltcake_flow = DEFAULTS['saltcake_flow_lb_hr']
    saltcake_na2o = saltcake_flow * MW['Na2O'] / MW['Na2SO4']
    print(f"  Saltcake ({saltcake_flow:.0f} lb Na2SO4/hr):")
    print(f"    → Na2O: {saltcake_na2o:.1f} lb/hr")
    print(f"    → Na element: {saltcake_na2o * 2 * MW['Na'] / MW['Na2O']:.1f} lb/hr")

    print(f"  Na deficit (Na2O):    {results['na_deficit_lbs_hr']:.1f} lb/hr")
    print(f"  NaSH dry:             {results['nash_dry_lbs_hr']:.1f} lb/hr")
    print(f"  NaOH dry:             {results['naoh_dry_lbs_hr']:.1f} lb/hr")

    nash_dry = results['nash_dry_lbs_hr']
    naoh_dry = results['naoh_dry_lbs_hr']

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 2: Na ENTERING the cycle (from outside)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── Na ENTERING THE CYCLE (lb Na2O/hr) ──")

    # Saltcake (Na2SO4)
    saltcake_na2o_hr = saltcake_flow * MW['Na2O'] / MW['Na2SO4']  # 62/142.04
    print(f"  1. Saltcake:    {saltcake_na2o_hr:8.1f}   ({saltcake_flow:.0f} lb Na2SO4/hr)")

    # NaSH → Na2O
    nash_na2o = nash_dry * CONV['NaSH_to_Na2O']  # NaSH → Na2O conversion
    print(f"  2. NaSH makeup: {nash_na2o:8.1f}   ({nash_dry:.1f} lb NaSH/hr)")

    # NaOH → Na2O
    naoh_na2o = naoh_dry * CONV['NaOH_to_Na2O']  # NaOH → Na2O conversion
    print(f"  3. NaOH makeup: {naoh_na2o:8.1f}   ({naoh_dry:.1f} lb NaOH/hr)")

    # CTO brine (Na from neutralizing H2SO4 with NaOH)
    cto_h2so4_per_ton = DEFAULTS['cto_h2so4_per_ton']
    cto_tpd = DEFAULTS['cto_tpd']
    cto_h2so4_lb_hr = cto_h2so4_per_ton * cto_tpd / 24
    cto_na_element = cto_h2so4_lb_hr * (2 * MW['Na'] / MW['H2SO4'])
    cto_na2o = cto_na_element * MW['Na2O'] / (2 * MW['Na'])
    print(f"  4. CTO brine:   {cto_na2o:8.1f}   ({cto_h2so4_lb_hr:.0f} lb H2SO4/hr neutralized)")

    total_na_in = saltcake_na2o_hr + nash_na2o + naoh_na2o + cto_na2o
    print(f"  ─────────────────────────")
    print(f"  TOTAL Na IN:    {total_na_in:8.1f} lb Na2O/hr")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 3: Na LEAVING the cycle (losses) — FIRST PRINCIPLES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── Na LEAVING THE CYCLE — FIRST PRINCIPLES (lb Na2O/hr) ──")

    # 1. RB soda losses (directly specified)
    rb_losses_na2o_bdt = DEFAULTS['rb_losses_na2o_bdt']
    rb_losses_na2o_hr = rb_losses_na2o_bdt * prod_bdt_hr
    print(f"\n  1. RB SODA LOSSES (stack + ash):")
    print(f"     Input: {rb_losses_na2o_bdt} lb Na2O/BDT")
    print(f"     → {rb_losses_na2o_hr:.1f} lb Na2O/hr")
    print(f"     Mechanism: Na2SO4 + Na2CO3 particles in flue gas, Na in purged ESP ash")

    # 2. Dregs — GL entrained in dregs underflow
    dregs_gpm = results['dregs_underflow_gpm']
    gl_tta_g_L = results['gl_tta_g_L']
    dregs_na2o_hr = dregs_gpm * gl_tta_g_L * CONV['GPM_GL_TO_LB_HR']
    print(f"\n  2. DREGS FILTER:")
    print(f"     Dregs underflow liquor: {dregs_gpm:.2f} gpm")
    print(f"     GL TTA: {gl_tta_g_L:.2f} g/L (as Na2O)")
    print(f"     → {dregs_na2o_hr:.1f} lb Na2O/hr")
    print(f"     → {dregs_na2o_hr / prod_bdt_hr:.2f} lb Na2O/BDT")
    print(f"     Mechanism: GL liquor carried with CaCO3/CaO dregs solids")

    # 3. Grits — GL entrained in grits underflow
    grits_gpm = results['grits_underflow_gpm']
    grits_na2o_hr = grits_gpm * gl_tta_g_L * CONV['GPM_GL_TO_LB_HR']
    print(f"\n  3. GRITS:")
    print(f"     Grits underflow liquor: {grits_gpm:.2f} gpm")
    print(f"     GL TTA: {gl_tta_g_L:.2f} g/L (as Na2O)")
    print(f"     → {grits_na2o_hr:.1f} lb Na2O/hr")
    print(f"     → {grits_na2o_hr / prod_bdt_hr:.2f} lb Na2O/BDT")
    print(f"     Mechanism: GL liquor carried with grits (CaCO3 + inerts)")

    # 4. Evaporator spill — BL composition
    evap_spill_s_bdt = DEFAULTS['s_loss_evap_spill']
    # BL ratio: Na_pct / S_pct gives Na:S in BL
    bl_na_pct = results.get('bl_na_pct_used', DEFAULTS['bl_na_pct'])
    bl_s_pct = results.get('bl_s_pct_used', DEFAULTS['bl_s_pct'])
    if bl_s_pct > 0:
        na_s_ratio_bl = bl_na_pct / bl_s_pct
    else:
        na_s_ratio_bl = 5.0
    evap_na_element_bdt = evap_spill_s_bdt * na_s_ratio_bl
    evap_na2o_bdt = evap_na_element_bdt * MW['Na2O'] / (2 * MW['Na'])
    evap_na2o_hr = evap_na2o_bdt * prod_bdt_hr
    print(f"\n  4. EVAPORATOR SPILL:")
    print(f"     S loss declared: {evap_spill_s_bdt} lb S/BDT")
    print(f"     BL Na%/S% = {bl_na_pct:.2f}/{bl_s_pct:.2f} = {na_s_ratio_bl:.2f} (element ratio)")
    print(f"     → Na element: {evap_na_element_bdt:.2f} lb/BDT → Na2O: {evap_na2o_bdt:.2f} lb/BDT")
    print(f"     → {evap_na2o_hr:.1f} lb Na2O/hr")
    print(f"     Mechanism: BL spill/leak from evaporator system, carries Na in same ratio as BL")

    # 5. Weak wash overflow
    # WW is dilute — ww_tta_lb_ft3 = 1.08 means ~17.3 g/L as Na2O
    # If there's overflow, it carries Na at WW concentration
    # We don't have an explicit overflow flow rate, but the S loss is declared
    ww_s_bdt = DEFAULTS['s_loss_weak_wash_overflow']
    ww_tta = DEFAULTS['ww_tta_lb_ft3']  # lb/ft3
    ww_sulf = DEFAULTS['ww_sulfidity']   # fraction
    ww_na2s_lb_ft3 = ww_tta * ww_sulf
    if ww_na2s_lb_ft3 > 0:
        # S in WW as element: ww_na2s * (S/Na2O)
        ww_s_lb_ft3 = ww_na2s_lb_ft3 * MW['S'] / MW['Na2O']
        # Na in WW as element: ww_tta * (2*Na/Na2O)
        ww_na_lb_ft3 = ww_tta * 2 * MW['Na'] / MW['Na2O']
        ww_na_s_ratio = ww_na_lb_ft3 / ww_s_lb_ft3 if ww_s_lb_ft3 > 0 else 0
        ww_na_element_bdt = ww_s_bdt * ww_na_s_ratio
    else:
        ww_na_element_bdt = 0
    ww_na2o_bdt = ww_na_element_bdt * MW['Na2O'] / (2 * MW['Na'])
    ww_na2o_hr = ww_na2o_bdt * prod_bdt_hr
    print(f"\n  5. WEAK WASH OVERFLOW:")
    print(f"     S loss declared: {ww_s_bdt} lb S/BDT")
    print(f"     WW TTA: {ww_tta} lb/ft3, sulfidity: {ww_sulf:.1%}")
    print(f"     WW Na:S ratio (element): {ww_na_s_ratio:.2f}")
    print(f"     → {ww_na2o_hr:.1f} lb Na2O/hr ({ww_na2o_bdt:.3f} lb Na2O/BDT)")
    print(f"     Mechanism: WW overflow to sewer, carries all TTA species")

    # 6. NCG / Turpentine
    ncg_s_bdt = DEFAULTS['s_loss_ncg']
    ncg_na2o_hr = 0.0  # Organic sulfur compounds — essentially no Na
    print(f"\n  6. NCG / TURPENTINE:")
    print(f"     S loss declared: {ncg_s_bdt} lb S/BDT")
    print(f"     → Na loss: {ncg_na2o_hr:.1f} lb Na2O/hr")
    print(f"     Mechanism: Organic S (methyl mercaptan, DMS, DMDS, H2S) — no Na")

    # 7. Recausticizing spill — GL/WL composition
    recaust_s_bdt = DEFAULTS['s_loss_recaust_spill']
    # Recaust area uses GL → WL, so the spill is somewhere between GL and WL composition
    # Use GL composition as conservative estimate (lower Na:S than WL)
    gl_na2s_g_L = results['gl_na2s_g_L']
    if gl_na2s_g_L > 0:
        gl_s_element = gl_na2s_g_L * MW['S'] / MW['Na2O']
        gl_na_element = gl_tta_g_L * 2 * MW['Na'] / MW['Na2O']
        gl_na_s_ratio = gl_na_element / gl_s_element
        recaust_na_element_bdt = recaust_s_bdt * gl_na_s_ratio
    else:
        recaust_na_element_bdt = 0
    recaust_na2o_bdt = recaust_na_element_bdt * MW['Na2O'] / (2 * MW['Na'])
    recaust_na2o_hr = recaust_na2o_bdt * prod_bdt_hr
    print(f"\n  7. RECAUSTICIZING SPILL:")
    print(f"     S loss declared: {recaust_s_bdt} lb S/BDT")
    print(f"     GL Na:S ratio (element): {gl_na_s_ratio:.2f}")
    print(f"     → {recaust_na2o_hr:.1f} lb Na2O/hr ({recaust_na2o_bdt:.2f} lb Na2O/BDT)")
    print(f"     Mechanism: GL/WL spill from recausticizing area (slaker, clarifier)")

    # 8. RB Ash purge — ESP ash is mostly Na2SO4 + Na2CO3
    #    The S component is in the S loss table as rb_ash_purge.
    #    The Na component: if ash is ~Na2SO4, then Na:S = 2*Na/S = 1.434
    #    But ash also contains Na2CO3 (Na only, no S), so Na:S > 1.434
    rb_ash_s_bdt = DEFAULTS['s_loss_rb_ash_purge']
    # Ash purge Na is ALREADY INCLUDED in rb_losses_na2o_bdt (item 1)
    # Don't double count! The rb_losses_na2o_bdt covers all RB Na losses
    print(f"\n  8. RB ASH PURGE (Na):")
    print(f"     S loss declared: {rb_ash_s_bdt} lb S/BDT")
    print(f"     ⚠️  Na portion ALREADY INCLUDED in item #1 (RB soda losses = {rb_losses_na2o_bdt} lb Na2O/BDT)")
    print(f"     Not counted separately to avoid double-counting")

    # 9. RB Stack — same as ash purge
    rb_stack_s_bdt = DEFAULTS['s_loss_rb_stack']
    print(f"\n  9. RB STACK (Na):")
    print(f"     S loss declared: {rb_stack_s_bdt} lb S/BDT")
    print(f"     ⚠️  Na portion ALREADY INCLUDED in item #1 (RB soda losses)")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 4: Total Na losses from first principles
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── TOTAL Na LOSSES SUMMARY ──")

    sources = [
        ("RB soda losses (stack+ash Na)", rb_losses_na2o_hr),
        ("Dregs filter (GL entrainment)", dregs_na2o_hr),
        ("Grits (GL entrainment)", grits_na2o_hr),
        ("Evaporator spill", evap_na2o_hr),
        ("Weak wash overflow", ww_na2o_hr),
        ("NCG/Turpentine", ncg_na2o_hr),
        ("Recausticizing spill", recaust_na2o_hr),
    ]

    total_na_out = 0.0
    for name, val in sources:
        total_na_out += val
        pct = (val / sum(v for _, v in sources) * 100) if sum(v for _, v in sources) > 0 else 0
        print(f"  {name:40s} {val:8.1f} lb Na2O/hr  ({pct:5.1f}%)")

    print(f"  {'─' * 60}")
    print(f"  {'TOTAL Na LOSSES (first principles)':40s} {total_na_out:8.1f} lb Na2O/hr")
    print(f"  {'TOTAL Na LOSSES per BDT':40s} {total_na_out / prod_bdt_hr:8.2f} lb Na2O/BDT")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 5: Comparison
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── COMPARISON ──")
    model_na_losses = results['na_losses_lbs_hr']
    print(f"  Model (loss_factor × WL flow):  {model_na_losses:8.1f} lb Na2O/hr")
    print(f"  First principles sum:           {total_na_out:8.1f} lb Na2O/hr")
    print(f"  Ratio (model / first-princ):    {model_na_losses / total_na_out:8.3f}")
    print(f"  Difference:                     {model_na_losses - total_na_out:+8.1f} lb Na2O/hr")

    # What loss_factor SHOULD be to match first-principles
    wl_demand = results['total_wl_demand_gpm']
    final_wl_tta = results['final_wl_tta_g_L']
    wl_tta_flow = wl_demand * final_wl_tta * CONV['GPM_GL_TO_LB_HR']
    if wl_tta_flow > 0:
        implied_loss_factor = total_na_out / wl_tta_flow
        print(f"\n  Implied loss_factor to match:   {implied_loss_factor:.6f}")
        print(f"  Current loss_factor:            {DEFAULTS.get('loss_factor', 0.0921):.6f}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 6: Na mass balance check
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── Na MASS BALANCE (steady-state check) ──")
    print(f"  Total Na IN:   {total_na_in:8.1f} lb Na2O/hr")
    print(f"  Total Na OUT:  {total_na_out:8.1f} lb Na2O/hr")
    imbalance = total_na_in - total_na_out
    print(f"  Imbalance:     {imbalance:+8.1f} lb Na2O/hr (IN - OUT)")
    if total_na_in > 0:
        print(f"  Imbalance %:   {imbalance / total_na_in * 100:+.1f}%")
    if imbalance > 50:
        print(f"  ⚠️  Na SURPLUS: more Na entering than leaving")
        print(f"     → Na will accumulate in the system (TTA rising)")
    elif imbalance < -50:
        print(f"  ⚠️  Na DEFICIT: more Na leaving than entering")
        print(f"     → Na will deplete from system (TTA falling)")
    else:
        print(f"  ✓  Approximately balanced")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 7: S mass balance for comparison
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n── S MASS BALANCE (for comparison) ──")

    total_s_losses = results['total_s_losses_lb_hr']

    # S entering
    nash_s_element = nash_dry * MW['S'] / MW['NaSH']
    saltcake_s_element = saltcake_flow * MW['S'] / MW['Na2SO4']
    cto_s_element = cto_h2so4_lb_hr * MW['S'] / MW['H2SO4']
    total_s_in = nash_s_element + saltcake_s_element + cto_s_element

    print(f"  S IN:")
    print(f"    NaSH:     {nash_s_element:8.1f} lb S/hr")
    print(f"    Saltcake: {saltcake_s_element:8.1f} lb S/hr")
    print(f"    CTO:      {cto_s_element:8.1f} lb S/hr")
    print(f"    TOTAL:    {total_s_in:8.1f} lb S/hr")
    print(f"  S OUT:")
    print(f"    Declared: {total_s_losses:8.1f} lb S/hr")
    s_imbalance = total_s_in - total_s_losses
    print(f"  S Balance:  {s_imbalance:+8.1f} lb S/hr")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SECTION 8: Recommendations
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n" + "=" * 80)
    print("   RECOMMENDATIONS")
    print("=" * 80)

    print("""
    1. REPLACE loss_factor with itemized Na losses:
       Instead of: na_losses = WL_flow × WL_TTA × GPM_GL_TO_LB_HR × loss_factor
       Use: na_losses = sum(per-source Na losses computed from first principles)

       For sources with physical flow data (dregs, grits, RB):
       → Compute directly from flow × concentration

       For empirical sources (evap spill, recaust spill):
       → Use declared S loss × (Na:S ratio of the spilled liquor)

       For NCG/turpentine:
       → Na = 0 (organic S only)

    2. This makes loss_factor a CALCULATED OUTPUT, not an input.
       loss_factor = total_Na_losses / (WL_flow × WL_TTA × conversion)

    3. The Na and S loss tables should be PARALLEL:
       Each source has both a Na loss and an S loss.
       This ensures mass conservation is explicitly verified.

    4. RB soda losses (rb_losses_na2o_bdt) ALREADY covers the Na portion
       of RB ash purge and RB stack. So those S loss sources have Na
       losses already accounted for — don't double-count.
    """)


if __name__ == '__main__':
    main()
