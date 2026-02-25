"""
Master orchestrator — closed-loop iterative solver.

Inner loop: converges GL_flow_to_slaker (I58) — existing circular reference.
Outer loop: converges bl_na_pct and bl_s_pct via forward leg (fiberline → evaporator).

Reference: Excel iterative calculation (100 iterations, max change 0.001)
Circular reference path: 2_RB!I58 -> I63 -> I66 -> I67 -> 3_Chem!D66 -> 3_Chem!G5 -> 2_RB!I58
"""

from typing import Dict, Any, List

from .constants import MW, CONV, DEFAULTS, GPM_GL_TO_TON_HR
from .density import calculate_bl_density, calculate_gl_density
from .inventory import (
    LiquorComposition, TankInventory, LatentBLInventory, SulfidityMetrics,
    calculate_liquor_composition, calculate_tank_inventory,
    calculate_bl_inventory, calculate_sulfidity_metrics,
)
from .recovery_boiler import calculate_full_rb, SmeltComposition, RecoveryBoilerInputs
from .chemical_charge import (
    calculate_chemical_charge, calculate_fiberline,
    calculate_wlc, ChemicalChargeResults, WLCResult,
)
from .s_retention import calculate_s_retention, calculate_losses_detailed, SodaSulfurLosses, LOSS_SOURCES
from .makeup import calculate_makeup_summary, calculate_nash_requirement, calculate_naoh_requirement, calculate_solution_flow_rates
from .dissolving_tank import calculate_dissolving_tank, calculate_ww_flow_for_tta_target
from .dregs_filter import calculate_dregs_filter
from .slaker_model import calculate_slaker_model
from .mill_config import TANKS, TANK_GROUPS
from .mill_profile import FiberlineConfig
from .fiberline import calculate_fiberline_bl, mix_wbl_streams
from .evaporator import calculate_evaporator


def _run_inner_loop(
    smelt, saltcake_na, saltcake_s, cto_s,
    ww_flow, ww_tta_lb_ft3, ww_sulfidity, shower_flow, smelt_density,
    gl_target_tta_lb_ft3, gl_causticity, dregs_gpm,
    grits_entrained_gpm,  # Entrained WL liquor lost with grits at slaker
    gl_temp, causticity, lime_charge_ratio, cao_in_lime, caco3_in_lime,
    inerts_in_lime, grits_loss, lime_temp, slaker_temp,
    fiberline_configs, total_prod, lab_wl_ea, cooking_sulf,
    target_sulf_pct,
    total_na_losses_as_na2o_lb_hr,
    washable_soda_na_lb_hr,   # Washable soda Na losses (lb Na2O/hr) — flow-dependent portion
    s_deficit_element_lb_hr,  # S deficit in element basis (lb S/hr)
    s_deficit_na2o_lb_hr,     # S deficit in Na2O basis (deprecated)
    nash_conc, naoh_conc, nash_dens, naoh_dens,
    intrusion_water, dilution_water, wlc_underflow_solids, wlc_mud_density,
    s_deficit_override,
    nash_override=None,  # Override NaSH (lb/hr) for Secant iteration
    naoh_dry_override=None,  # Override NaOH (lb/hr) — bypasses dual-constraint
    # Dregs filter parameters (for WW flow solve)
    dregs_solids_lb_hr=0.0,
    glc_underflow_solids_pct=0.077,
    gl_density_lb_gal=8.6,
    # DT energy balance
    smelt_temp_f=1338.0,
    ww_temp_f=180.0,
    shower_temp_f=140.0,
    dt_operating_temp_f=212.0,
    smelt_cp=0.29,
    latent_heat=970.0,
):
    """Run the existing inner convergence loop (GL flow to slaker).

    Returns a dict with all inner-loop results needed by the outer loop
    and by the results assembly.

    If nash_override is provided, uses that NaSH value instead of calculating
    from S deficit. This enables Secant method iteration for sulfidity targeting.
    """
    MAX_ITER = 100
    TOLERANCE = 0.001

    total_gl_to_digesters = 0.0
    gl_flow_prev = 660.0
    iter_wl_tta_g_L = DEFAULTS.get('wl_tta', 120.0)

    nash_dry = 0.0
    naoh_dry = 0.0
    nash_gpm = 0.0
    naoh_gpm = 0.0
    final_tta_ton_hr = 0.0
    final_na2s_ton_hr = 0.0
    final_sulfidity = 0.0
    na_losses = 0.0
    na_deficit = 0.0
    wlc_result = None
    slaker_result = None
    dt_result = None
    chem_result = None
    makeup = None
    ww_flow_solved = ww_flow  # Will be overwritten by analytical solve
    dregs_filtrate_gpm = 0.0

    converged = False
    iterations = 0
    prev_wlc_stage2 = None  # Previous iteration's Stage 2 WLC result

    for iteration in range(MAX_ITER):
        # ══════════════════════════════════════════════════════════════════════
        # TWO-STAGE WLC APPROACH: CE now affects NaOH makeup via WL demand
        # Stage 1: NaSH + WLC (get final_ea_g_L reflecting CE)
        # Stage 2: Use final_ea_g_L for WL demand → Na loss factor → NaOH
        # ══════════════════════════════════════════════════════════════════════

        # Step 1: Dregs filter → WW flow solve → Dissolving Tank → GL composition
        # Dregs filter filtrate returns to WW tank, raising WW TTA.
        # Use previous iteration's GL TTA for dregs filter (bootstrap: 0 for first iter).
        filtrate_tta_g_L = 0.0
        if dt_result is not None and dregs_solids_lb_hr > 0:
            df_result = calculate_dregs_filter(
                dregs_solids_lb_hr=dregs_solids_lb_hr,
                glc_underflow_solids_pct=glc_underflow_solids_pct,
                gl_tta_g_L=dt_result.gl_tta_g_L,
                gl_density_lb_gal=gl_density_lb_gal,
            )
            dregs_filtrate_gpm = df_result.filtrate_gpm
            filtrate_tta_g_L = df_result.filtrate_tta_g_L

        # Solve WW flow analytically to hit GL TTA setpoint (mass balance closure)
        ww_flow_solved, dt_result = calculate_ww_flow_for_tta_target(
            smelt_tta_lbs_hr=smelt.tta_lbs_hr,
            smelt_active_sulfide=smelt.active_sulfide,
            smelt_dead_load=smelt.dead_load,
            smelt_sulfidity_pct=smelt.smelt_sulfidity_pct,
            ww_tta_lb_ft3=ww_tta_lb_ft3,
            ww_sulfidity=ww_sulfidity,
            shower_flow_gpm=shower_flow,
            smelt_density_lb_ft3=smelt_density,
            gl_target_tta_lb_ft3=gl_target_tta_lb_ft3,
            gl_causticity=gl_causticity,
            underflow_dregs_gpm=dregs_gpm,
            semichem_gl_gpm=total_gl_to_digesters,
            dregs_filtrate_gpm=dregs_filtrate_gpm,
            filtrate_tta_g_L=filtrate_tta_g_L,
            smelt_temp_f=smelt_temp_f,
            ww_temp_f=ww_temp_f,
            shower_temp_f=shower_temp_f,
            dt_temp_f=dt_operating_temp_f,
            smelt_cp=smelt_cp,
            latent_heat=latent_heat,
        )
        gl_flow = dt_result.gl_flow_to_slaker_gpm

        # Step 2: Slaker → WL from slaker
        slaker_result = calculate_slaker_model(
            gl_flow_gpm=gl_flow,
            gl_tta_g_L=dt_result.gl_tta_g_L,
            gl_na2s_g_L=dt_result.gl_na2s_g_L,
            gl_aa_g_L=dt_result.gl_aa_g_L,
            gl_temp_f=gl_temp,
            causticity=causticity,
            lime_charge_ratio=lime_charge_ratio,
            cao_in_lime_pct=cao_in_lime,
            caco3_in_lime_pct=caco3_in_lime,
            inerts_in_lime_pct=inerts_in_lime,
            grits_loss_pct=grits_loss,
            lime_temp_f=lime_temp,
            slaker_temp_f=slaker_temp,
        )

        # Calculate WL mass flows from slaker (needed for NaSH sizing)
        conv_factor = CONV['GPM_GL_TO_LB_HR'] / 2000  # gpm × g/L → ton/hr
        wl_tta_mass_from_slaker = slaker_result.wl_flow_gpm * slaker_result.wl_tta_g_L * conv_factor
        wl_na2s_mass_from_slaker = slaker_result.wl_flow_gpm * slaker_result.wl_na2s_g_L * conv_factor

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 1: NaSH CALCULATION
        # ─────────────────────────────────────────────────────────────────────
        # Two modes:
        # 1. nash_override provided: Use that value (Secant iteration for target sulfidity)
        # 2. Otherwise: Calculate from S deficit (initial guess for Secant)
        if nash_override is not None:
            # Secant iteration mode: use the provided NaSH value
            nash_dry = nash_override
        else:
            # Initial guess from S deficit mass balance
            nash_result = calculate_nash_requirement(
                target_sulfidity_pct=target_sulf_pct,
                wl_tta_mass_ton_hr=wl_tta_mass_from_slaker,
                wl_na2s_mass_ton_hr=wl_na2s_mass_from_slaker,
                na_deficit_lbs_hr=0.0,  # Not used for S deficit approach
                cto_s_lbs_hr=cto_s,
                s_deficit_lbs_hr=s_deficit_override,
                s_deficit_na2o_lbs_hr=None,  # Deprecated - use element basis
                s_deficit_element_lbs_hr=s_deficit_element_lb_hr,  # Rigorous approach
            )
            nash_dry = nash_result['nash_dry_lbs_hr']

        # Calculate NaSH solution flow
        nash_flow_result = calculate_solution_flow_rates(
            nash_dry_lbs_hr=nash_dry,
            naoh_dry_lbs_hr=0.0,
            nash_concentration=nash_conc,
            naoh_concentration=naoh_conc,
            nash_density=nash_dens,
            naoh_density=naoh_dens,
        )
        nash_gpm = nash_flow_result['nash_solution_gpm']

        # TTA and Na2S contributions from NaSH
        tta_from_nash = nash_dry * CONV['NaSH_to_Na2O'] / 2000
        na2s_from_nash = nash_dry * CONV['Na2O_per_NaSH'] / 2000

        # ─────────────────────────────────────────────────────────────────────
        # WLC STAGE 1: NaSH only → get final_ea_g_L reflecting CE
        # ─────────────────────────────────────────────────────────────────────
        wlc_stage1 = calculate_wlc(
            wl_flow_from_slaker_gpm=slaker_result.wl_flow_gpm,
            wl_tta_mass_ton_hr=wl_tta_mass_from_slaker,
            wl_na2s_mass_ton_hr=wl_na2s_mass_from_slaker,
            wl_sulfidity=slaker_result.wl_sulfidity,
            wl_tta_g_L=slaker_result.wl_tta_g_L,
            nash_gpm=nash_gpm,
            naoh_gpm=0.0,  # NaOH not added yet
            tta_from_makeup_ton_hr=tta_from_nash,
            na2s_from_makeup_ton_hr=na2s_from_nash,
            wl_naoh_mass_ton_hr=slaker_result.wl_naoh_mass_ton_hr,
            naoh_from_makeup_ton_hr=0.0,  # No NaOH makeup in Stage 1
            grits_entrained_gpm=grits_entrained_gpm,
            intrusion_water_gpm=intrusion_water,
            dilution_water_gpm=dilution_water,
            underflow_solids_pct=wlc_underflow_solids,
            mud_density=wlc_mud_density,
            lime_mud_lb_hr=slaker_result.lime_mud_total_lb_hr,
            causticity=causticity,
        )

        # ─────────────────────────────────────────────────────────────────────
        # STAGE 2: Chemical Charge using CALCULATED EA from WLC (reflects CE!)
        # ─────────────────────────────────────────────────────────────────────
        # Use previous iteration's Stage 2 (final) EA for demand. This captures
        # the NaOH makeup contribution to EA, which reduces WL demand. On the
        # first iteration, fall back to Stage 1 EA (NaSH only).
        if prev_wlc_stage2 is not None and prev_wlc_stage2.final_ea_g_L > 0:
            wl_ea_for_demand = prev_wlc_stage2.final_ea_g_L
        else:
            wl_ea_for_demand = wlc_stage1.final_ea_g_L if wlc_stage1.final_ea_g_L > 0 else lab_wl_ea

        chem_result = calculate_chemical_charge(
            fiberlines=fiberline_configs,
            gl_flow_to_slaker_gpm=gl_flow,
            yield_factor=slaker_result.yield_factor,
            wl_tta_g_L=slaker_result.wl_tta_g_L,
            wl_na2s_g_L=slaker_result.wl_na2s_g_L,
            wl_ea_g_L=wl_ea_for_demand,
            wl_sulfidity=cooking_sulf,
            gl_tta_g_L=dt_result.gl_tta_g_L,
            gl_na2s_g_L=dt_result.gl_na2s_g_L,
            gl_aa_g_L=dt_result.gl_aa_g_L,
            dregs_underflow_gpm=dregs_gpm,
        )

        # ═══════════════════════════════════════════════════════════════════════
        # DUAL-CONSTRAINT NaOH SIZING
        # ═══════════════════════════════════════════════════════════════════════
        # NaOH must satisfy TWO constraints:
        #   1. Cover Na LOSSES (mass balance - replace Na leaving the system)
        #   2. Cover EA DEMAND (digesters need enough alkali to cook the wood)
        #
        # NaOH = max(NaOH_for_losses, NaOH_for_EA_demand)
        #
        # This captures the CE → NaOH correlation:
        #   - At high CE: EA is sufficient → NaOH sized by losses
        #   - At low CE: EA deficit → NaOH_for_EA_demand becomes the constraint
        # ═══════════════════════════════════════════════════════════════════════

        # --- Constraint 1: NaOH for Na LOSSES (mass balance) ---
        # Na_losses from unified loss table (static, based on production)
        # Saltcake Na in element basis, convert to Na2O
        saltcake_na_as_na2o = saltcake_na * MW['Na2O'] / (2 * MW['Na'])
        na_from_nash_na2o = nash_dry * CONV['NaSH_to_Na2O']

        na_deficit_for_losses = max(0.0, total_na_losses_as_na2o_lb_hr - saltcake_na_as_na2o - na_from_nash_na2o)
        naoh_for_losses = na_deficit_for_losses / CONV['NaOH_to_Na2O'] if CONV['NaOH_to_Na2O'] > 0 else 0.0

        # --- Constraint 2: NaOH for EA DEMAND (digester requirement) ---
        # ══════════════════════════════════════════════════════════════════════════
        # FIRST-PRINCIPLES EA DEMAND
        # Digesters need a specific EA charge (% on OD wood) to cook pulp.
        # If WL EA concentration is insufficient (due to low CE), NaOH makeup
        # must compensate to avoid increasing WL flow beyond capacity.
        #
        # The approach: Compare EA concentration at actual CE vs baseline CE (81%).
        # At lower CE, less Na2CO3 is converted to NaOH, so EA concentration drops.
        # NaOH makeup restores EA to baseline level.
        #
        # This captures the economic impact of operating at low causticity:
        # - Option 1: Increase WL flow (costly, may exceed capacity)
        # - Option 2: Add NaOH makeup (chemical cost)
        # ══════════════════════════════════════════════════════════════════════════

        # Calculate EA demand per fiberline (loop over configs)
        total_ea_required_lb_hr = 0.0
        ea_from_gl_total = 0.0
        ea_per_fiberline = {}
        for fl in fiberline_configs:
            wood_lb_hr = (fl.production_bdt_day * 2000 / fl.yield_pct) / 24 if fl.yield_pct > 0 else 0.0
            ea_fl = fl.ea_pct * wood_lb_hr
            total_ea_required_lb_hr += ea_fl
            ea_per_fiberline[fl.id] = ea_fl
            if fl.uses_gl_charge:
                ea_from_gl_total += fl.gl_ea_pct * wood_lb_hr

        # Backward compat keys (kept for result assembly & tests)
        ea_required_pine_lb_hr = ea_per_fiberline.get('pine', 0.0)
        ea_required_semi_wl_lb_hr = ea_per_fiberline.get('semichem', 0.0)
        ea_from_gl_to_semi_lb_hr = ea_from_gl_total  # Backward compat name

        # ══════════════════════════════════════════════════════════════════════════
        # EA DEFICIT CALCULATION: Baseline CE vs Actual CE
        # ══════════════════════════════════════════════════════════════════════════
        # At baseline CE (81%), the slaker produces a certain EA concentration.
        # At lower CE, EA concentration drops (less NaOH from causticizing).
        # NaOH makeup compensates for the concentration deficit.
        #
        # Using slaker output TTA and Na2S:
        #   EA = NaOH + 0.5 × Na2S
        #   NaOH = CE × (TTA - Na2S) (from causticizing definition)
        #   So: EA = CE × (TTA - Na2S) + 0.5 × Na2S
        #
        # EA deficit = (EA_baseline - EA_actual)
        #            = (0.81 - CE) × (TTA - Na2S)
        BASELINE_CE = 0.81

        slaker_na2s_g_L = slaker_result.wl_na2s_g_L
        # Non-sulfide alkali: TTA - Na₂S = NaOH + Na₂CO₃ (invariant to CE)
        non_sulfide_alkali_g_L = slaker_result.wl_tta_g_L - slaker_na2s_g_L

        # EA concentration at baseline CE vs actual CE
        ea_at_baseline_ce_g_L = BASELINE_CE * non_sulfide_alkali_g_L + 0.5 * slaker_na2s_g_L
        ea_at_actual_ce_g_L = causticity * non_sulfide_alkali_g_L + 0.5 * slaker_na2s_g_L

        # EA concentration deficit due to CE below baseline
        ea_deficit_g_L = max(0.0, ea_at_baseline_ce_g_L - ea_at_actual_ce_g_L)

        # Use baseline WL demand (what flow would be at 81% CE) for fair comparison
        # At lower CE, WL demand increases to compensate, but we want to show
        # the NaOH that would maintain baseline flow (avoiding capacity issues)
        total_wl_demand = chem_result.total_wl_demand_gpm

        # EA deficit in mass terms
        ea_deficit_lb_hr = ea_deficit_g_L * total_wl_demand * CONV['GPM_GL_TO_LB_HR']

        # For reporting: actual EA from slaker and NaSH
        slaker_ea_g_L = slaker_result.wl_ea_g_L
        ea_from_slaker_lb_hr = slaker_ea_g_L * total_wl_demand * CONV['GPM_GL_TO_LB_HR']
        ea_from_nash_lb_hr = nash_dry * CONV['NaSH_to_Na2O'] * 0.5
        ea_from_wlc_stage1_lb_hr = wlc_stage1.final_ea_g_L * total_wl_demand * CONV['GPM_GL_TO_LB_HR']

        # NaOH to cover EA deficit (NaOH contributes 100% to EA as Na2O)
        naoh_for_ea_demand = ea_deficit_lb_hr / CONV['NaOH_to_Na2O'] if CONV['NaOH_to_Na2O'] > 0 else 0.0

        # ─── CE flow-sensitivity: adjust washable soda Na for WL demand change ───
        # Lower CE → lower WL EA → higher WL demand → more Na washed out with pulp
        # WL demand ∝ 1/EA, so flow_ratio = EA_baseline / EA_actual
        WASHABLE_SODA_FLOW_SENSITIVITY = 0.5

        # EA concentration at baseline CE vs actual CE (already computed above)
        if ea_at_actual_ce_g_L > 0:
            flow_ratio = ea_at_baseline_ce_g_L / ea_at_actual_ce_g_L
        else:
            flow_ratio = 1.0

        # Adjust Na losses for CE-driven WL demand change
        ce_na_adjustment_lb_hr = washable_soda_na_lb_hr * WASHABLE_SODA_FLOW_SENSITIVITY * (flow_ratio - 1)
        adjusted_na_losses = total_na_losses_as_na2o_lb_hr + ce_na_adjustment_lb_hr

        # Recompute NaOH for losses with CE-adjusted Na losses
        na_deficit_for_losses = max(0.0, adjusted_na_losses - saltcake_na_as_na2o - na_from_nash_na2o)
        naoh_for_losses = na_deficit_for_losses / CONV['NaOH_to_Na2O'] if CONV['NaOH_to_Na2O'] > 0 else 0.0

        # --- Final NaOH: override or maximum of both constraints ---
        if naoh_dry_override is not None:
            naoh_dry = naoh_dry_override
        else:
            naoh_dry = max(naoh_for_losses, naoh_for_ea_demand)

        # Track which constraint is active (for reporting)
        na_losses = adjusted_na_losses  # CE-adjusted Na losses for reporting
        na_deficit = na_deficit_for_losses  # For compatibility

        # ═══════════════════════════════════════════════════════════════════════
        # NA INVENTORY TRACKING
        # ═══════════════════════════════════════════════════════════════════════
        # At steady state: Na_in = Na_out
        # If Na_in > Na_out: Building inventory (not sustainable if EA constraint)
        # If Na_in < Na_out: Depleting inventory (will run out)
        #
        # Na_in = Saltcake_Na + NaSH_Na + NaOH_Na (all makeup sources)
        # Na_out = Total_Na_losses (from loss table)
        # ═══════════════════════════════════════════════════════════════════════

        # Na entering the system (element basis, lb/hr)
        na_in_from_saltcake = saltcake_na  # Already element basis
        na_in_from_nash = nash_dry * MW['Na'] / MW['NaSH']
        na_in_from_naoh = naoh_dry * MW['Na'] / MW['NaOH']
        total_na_in_lb_hr = na_in_from_saltcake + na_in_from_nash + na_in_from_naoh

        # Na leaving the system (element basis, lb/hr)
        # Use CE-adjusted losses so Na balance stays consistent with NaOH sizing
        total_na_out_lb_hr = adjusted_na_losses * (2 * MW['Na'] / MW['Na2O'])

        # Na accumulation rate (positive = building, negative = depleting)
        na_accumulation_lb_hr = total_na_in_lb_hr - total_na_out_lb_hr

        # Determine steady-state status
        STEADY_STATE_TOLERANCE = 50  # lb/hr tolerance
        if abs(na_accumulation_lb_hr) < STEADY_STATE_TOLERANCE:
            na_balance_status = 'steady_state'
        elif na_accumulation_lb_hr > 0:
            na_balance_status = 'building_inventory'
        else:
            na_balance_status = 'depleting_inventory'

        # Calculate NaOH solution flow
        naoh_flow_result = calculate_solution_flow_rates(
            nash_dry_lbs_hr=0.0,
            naoh_dry_lbs_hr=naoh_dry,
            nash_concentration=nash_conc,
            naoh_concentration=naoh_conc,
            nash_density=nash_dens,
            naoh_density=naoh_dens,
        )
        naoh_gpm = naoh_flow_result['naoh_solution_gpm']

        # TTA contribution from NaOH
        tta_from_naoh = naoh_dry * CONV['NaOH_to_Na2O'] / 2000

        # ─────────────────────────────────────────────────────────────────────
        # WLC STAGE 2: Final WLC with NaSH + NaOH
        # ─────────────────────────────────────────────────────────────────────
        wlc_result = calculate_wlc(
            wl_flow_from_slaker_gpm=slaker_result.wl_flow_gpm,
            wl_tta_mass_ton_hr=wl_tta_mass_from_slaker,
            wl_na2s_mass_ton_hr=wl_na2s_mass_from_slaker,
            wl_sulfidity=slaker_result.wl_sulfidity,
            wl_tta_g_L=slaker_result.wl_tta_g_L,
            nash_gpm=nash_gpm,
            naoh_gpm=naoh_gpm,
            tta_from_makeup_ton_hr=tta_from_nash + tta_from_naoh,
            na2s_from_makeup_ton_hr=na2s_from_nash,
            wl_naoh_mass_ton_hr=slaker_result.wl_naoh_mass_ton_hr,
            naoh_from_makeup_ton_hr=tta_from_naoh,  # NaOH makeup as ton Na2O/hr
            grits_entrained_gpm=grits_entrained_gpm,
            intrusion_water_gpm=intrusion_water,
            dilution_water_gpm=dilution_water,
            underflow_solids_pct=wlc_underflow_solids,
            mud_density=wlc_mud_density,
            lime_mud_lb_hr=slaker_result.lime_mud_total_lb_hr,
            causticity=causticity,
        )

        # Build makeup summary for compatibility with rest of code
        makeup = calculate_makeup_summary(
            target_sulfidity_pct=target_sulf_pct,
            wl_tta_mass_ton_hr=wl_tta_mass_from_slaker,
            wl_na2s_mass_ton_hr=wl_na2s_mass_from_slaker,
            na_deficit_lbs_hr=na_deficit,
            total_production_bdt_day=total_prod,
            saltcake_na_lbs_hr=saltcake_na,
            cto_s_lbs_hr=cto_s,
            s_deficit_lbs_hr=s_deficit_override,
            s_deficit_na2o_lbs_hr=s_deficit_na2o_lb_hr,
            nash_concentration=nash_conc,
            naoh_concentration=naoh_conc,
            nash_density=nash_dens,
            naoh_density=naoh_dens,
        )

        # Update iteration variables
        prev_wlc_stage2 = wlc_result  # Store for next iteration's EA demand calc
        iter_wl_tta_g_L = wlc_result.final_tta_g_L
        total_gl_to_digesters = sum(chem_result.gl_charge_gpm.values())

        final_tta_ton_hr = wlc_result.final_tta_mass_ton_hr
        final_na2s_ton_hr = wlc_result.final_na2s_mass_ton_hr
        final_sulfidity = wlc_result.final_sulfidity_pct

        # Convergence check on GL flow
        if abs(gl_flow - gl_flow_prev) < TOLERANCE:
            converged = True
            iterations = iteration + 1
            break

        gl_flow_prev = gl_flow
    else:
        iterations = MAX_ITER

    return {
        'converged': converged,
        'iterations': iterations,
        'dt_result': dt_result,
        'slaker_result': slaker_result,
        'chem_result': chem_result,
        'wlc_result': wlc_result,
        'makeup': makeup,
        'nash_dry': nash_dry,
        'naoh_dry': naoh_dry,
        'nash_gpm': nash_gpm,
        'naoh_gpm': naoh_gpm,
        'final_tta_ton_hr': final_tta_ton_hr,
        'final_na2s_ton_hr': final_na2s_ton_hr,
        'final_sulfidity': final_sulfidity,
        'na_losses': na_losses,
        'na_deficit': na_deficit,
        # Dual-constraint NaOH tracking
        'naoh_for_losses': naoh_for_losses,
        'naoh_for_ea_demand': naoh_for_ea_demand,
        'ea_required_lb_hr': total_ea_required_lb_hr,
        'ea_from_wl_lb_hr': ea_from_wlc_stage1_lb_hr,
        'ea_deficit_lb_hr': ea_deficit_lb_hr,
        # First-principles EA tracking
        'ea_required_pine_lb_hr': ea_required_pine_lb_hr,
        'ea_required_semi_wl_lb_hr': ea_required_semi_wl_lb_hr,
        'ea_from_gl_to_semi_lb_hr': ea_from_gl_to_semi_lb_hr,
        'ea_from_slaker_lb_hr': ea_from_slaker_lb_hr,
        'ea_from_nash_lb_hr': ea_from_nash_lb_hr,
        # Na inventory tracking
        'na_in_lb_hr': total_na_in_lb_hr,
        'na_out_lb_hr': total_na_out_lb_hr,
        'na_accumulation_lb_hr': na_accumulation_lb_hr,
        'na_balance_status': na_balance_status,
        # CE flow-sensitivity adjustment
        'ce_na_adjustment_lb_hr': ce_na_adjustment_lb_hr,
        'adjusted_na_losses_lb_hr': adjusted_na_losses,
        # WW flow solve & dregs filter
        'ww_flow_solved_gpm': ww_flow_solved,
        'dregs_filtrate_gpm': dregs_filtrate_gpm,
    }


def run_calculations(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete iterative calculation flow.

    Outer loop (new): converges on bl_na_pct and bl_s_pct via forward leg.
    Inner loop (existing): converges on GL_flow_to_slaker (I58).

    When s_deficit_lbs_hr is provided (existing tests), the outer loop runs
    once (forward leg still computed but doesn't feed back to BL guess),
    preserving backward compatibility.

    TARGET vs FINAL SULFIDITY
    -------------------------
    The `target_sulfidity_pct` input sets the desired sulfidity for NaSH sizing.
    The Secant solver adjusts NaSH to hit target sulfidity within ~0.15%,
    accounting for S losses, saltcake/CTO returns, and WLC dilution effects.

    When `nash_dry_override_lb_hr` is provided, the Secant solver is bypassed
    and NaSH is fixed at the user's value — sulfidity becomes the output.
    Similarly, `naoh_dry_override_lb_hr` bypasses the dual-constraint NaOH model.
    """
    results: Dict[str, Any] = {}

    # ══════════════════════════════════════════════════════════════════
    # Extract all inputs with defaults
    # ══════════════════════════════════════════════════════════════════

    bl_flow = inputs.get('bl_flow_gpm', DEFAULTS['bl_flow_gpm'])
    bl_tds = inputs.get('bl_tds_pct', DEFAULTS['bl_tds_pct'])
    bl_temp = inputs.get('bl_temp_f', DEFAULTS['bl_temp_f'])
    bl_na_pct = inputs.get('bl_na_pct', DEFAULTS['bl_na_pct'])
    bl_s_pct = inputs.get('bl_s_pct', DEFAULTS['bl_s_pct'])
    bl_na_pct_lab = bl_na_pct  # Preserve original lab input for diagnostics
    bl_s_pct_lab = bl_s_pct
    bl_k_pct = inputs.get('bl_k_pct', DEFAULTS['bl_k_pct'])
    re_pct = inputs.get('reduction_eff_pct', DEFAULTS['reduction_efficiency_pct'])

    ash_recycled_pct = inputs.get('ash_recycled_pct', DEFAULTS['ash_recycled_pct'])
    saltcake_flow = inputs.get('saltcake_flow_lb_hr', DEFAULTS['saltcake_flow_lb_hr'])

    ww_flow = inputs.get('ww_flow_gpm', DEFAULTS['ww_flow_gpm'])
    ww_tta_lb_ft3 = inputs.get('ww_tta_lb_ft3', DEFAULTS['ww_tta_lb_ft3'])
    ww_sulfidity = inputs.get('ww_sulfidity', DEFAULTS['ww_sulfidity'])
    shower_flow = inputs.get('shower_flow_gpm', DEFAULTS['shower_flow_gpm'])
    smelt_density = inputs.get('smelt_density_lb_ft3', DEFAULTS['smelt_density_lb_ft3'])
    gl_target_tta_lb_ft3 = inputs.get('gl_target_tta_lb_ft3', DEFAULTS['gl_target_tta_lb_ft3'])
    gl_causticity = inputs.get('gl_causticity', DEFAULTS['gl_causticity'])

    # DT energy balance
    smelt_temp_f = inputs.get('smelt_temp_f', DEFAULTS['smelt_temp_f'])
    ww_temp_f = inputs.get('ww_temp_f', DEFAULTS['ww_temp_f'])
    shower_temp_f = inputs.get('shower_temp_f', DEFAULTS['shower_temp_f'])
    dt_operating_temp_f = inputs.get('dt_operating_temp_f', DEFAULTS['dt_operating_temp_f'])
    smelt_cp = inputs.get('smelt_cp_btu_lb_f', DEFAULTS['smelt_cp_btu_lb_f'])
    latent_heat = inputs.get('latent_heat_212_btu_lb', DEFAULTS['latent_heat_212_btu_lb'])

    # ── Build fiberline configs (V2 or V1 backward compat) ──
    if 'fiberlines' in inputs:
        fiberline_configs: List[FiberlineConfig] = inputs['fiberlines']
    else:
        fiberline_configs = [
            FiberlineConfig(
                id="pine", name="Pine", type="continuous",
                cooking_type="chemical", uses_gl_charge=False,
                defaults={
                    "production_bdt_day": inputs.get('cont_production_bdt_day', DEFAULTS['cont_production_bdt_day']),
                    "yield_pct": inputs.get('pine_yield_pct', DEFAULTS['pine_yield_pct']),
                    "ea_pct": inputs.get('pine_ea_pct', DEFAULTS['pine_ea_pct']),
                    "wood_moisture": inputs.get('wood_moisture_pine', DEFAULTS['wood_moisture_pine']),
                },
            ),
            FiberlineConfig(
                id="semichem", name="Semichem", type="batch",
                cooking_type="semichem", uses_gl_charge=True,
                defaults={
                    "production_bdt_day": inputs.get('batch_production_bdt_day', DEFAULTS['batch_production_bdt_day']),
                    "yield_pct": inputs.get('semichem_yield_pct', DEFAULTS['semichem_yield_pct']),
                    "ea_pct": inputs.get('semichem_ea_pct', DEFAULTS['semichem_ea_pct']),
                    "gl_ea_pct": inputs.get('semichem_gl_ea_pct', DEFAULTS['semichem_gl_ea_pct']),
                    "wood_moisture": inputs.get('wood_moisture_semichem', DEFAULTS['wood_moisture_semichem']),
                },
            ),
        ]
    total_prod = sum(fl.production_bdt_day for fl in fiberline_configs)

    # Backward compat locals (used by forward leg wood_moisture and other code)
    wood_moisture_pine = inputs.get('wood_moisture_pine', DEFAULTS['wood_moisture_pine'])
    wood_moisture_semichem = inputs.get('wood_moisture_semichem', DEFAULTS['wood_moisture_semichem'])

    causticity = inputs.get('causticity_pct', DEFAULTS['causticity_pct']) / 100
    lime_charge_ratio = inputs.get('lime_charge_ratio', DEFAULTS['lime_charge_ratio'])
    cao_in_lime = inputs.get('cao_in_lime_pct', DEFAULTS['cao_in_lime_pct'])
    caco3_in_lime = inputs.get('caco3_in_lime_pct', DEFAULTS['caco3_in_lime_pct'])
    inerts_in_lime = inputs.get('inerts_in_lime_pct', DEFAULTS['inerts_in_lime_pct'])
    grits_loss = inputs.get('grits_loss_pct', DEFAULTS['grits_loss_pct'])
    lime_temp = inputs.get('lime_temp_f', DEFAULTS['lime_temp_f'])
    slaker_temp = inputs.get('slaker_temp_f', DEFAULTS['slaker_temp_f'])
    gl_temp = inputs.get('gl_temp_f', DEFAULTS['gl_temp_f'])

    intrusion_water = inputs.get('intrusion_water_gpm', DEFAULTS['intrusion_water_gpm'])
    dilution_water = inputs.get('dilution_water_gpm', DEFAULTS['dilution_water_gpm'])
    wlc_underflow_solids = inputs.get('wlc_underflow_solids_pct', DEFAULTS['wlc_underflow_solids_pct'])
    wlc_mud_density = inputs.get('wlc_mud_density', DEFAULTS['wlc_mud_density'])

    dregs_lb_bdt = inputs.get('dregs_lb_bdt', DEFAULTS['dregs_lb_bdt'])
    glc_solids_pct = inputs.get('glc_underflow_solids_pct', DEFAULTS['glc_underflow_solids_pct'])
    grits_lb_bdt = inputs.get('grits_lb_bdt', DEFAULTS['grits_lb_bdt'])
    grits_solids_pct = inputs.get('grits_solids_pct', DEFAULTS['grits_solids_pct'])

    # CTO chemistry — computed from H2SO4/ton and TPD inputs
    cto_h2so4_per_ton = inputs.get('cto_h2so4_per_ton', DEFAULTS['cto_h2so4_per_ton'])
    cto_tpd = inputs.get('cto_tpd', DEFAULTS['cto_tpd'])

    # CTO: H2SO4 is the ONLY external input (provides S, no Na)
    # The Na in CTO brine comes from soap (entrained BL) - NOT a new addition
    # Reaction: 2 NaSoap + H2SO4 → Tall Oil + Na2SO4
    #   - S comes from H2SO4 (external input)
    #   - Na comes from soap (already in BL, recirculation)
    cto_total_h2so4_lb_hr = cto_h2so4_per_ton * cto_tpd / 24
    cto_s_lb_hr = cto_total_h2so4_lb_hr * (MW['S'] / MW['H2SO4'])
    cto_na_lb_hr = 0.0  # H2SO4 contains no Na - soap Na is recirculation, not new input
    # CTO brine water: approximate — small relative to WBL water
    cto_water_lb_hr = inputs.get('cto_water_lb_hr', 500.0)

    target_sulf_pct = inputs.get('target_sulfidity_pct', DEFAULTS['target_sulfidity_pct'])
    cooking_sulf = inputs.get('cooking_wl_sulfidity', DEFAULTS['cooking_wl_sulfidity'])

    nash_conc = inputs.get('nash_concentration', DEFAULTS['nash_concentration'])
    naoh_conc = inputs.get('naoh_concentration', DEFAULTS['naoh_concentration'])
    nash_dens = inputs.get('nash_density', DEFAULTS['nash_density'])
    naoh_dens = inputs.get('naoh_density', DEFAULTS['naoh_density'])

    # Build unified loss table from inputs (26 keys: loss_{source}_{s|na})
    loss_kwargs = {}
    for prefix, _, _ in LOSS_SOURCES:
        for suffix in ('s', 'na'):
            key = f'loss_{prefix}_{suffix}'
            field = f'{prefix}_{suffix}'
            loss_kwargs[field] = inputs.get(key, DEFAULTS.get(key, 0.0))
    loss_breakdown = SodaSulfurLosses(**loss_kwargs)

    # Derive rb_losses_na2o_bdt from the loss table (replaces separate input)
    rb_losses_na2o_bdt = loss_breakdown.rb_na_lb_bdt

    # Forward leg parameters
    s_loss_digester = inputs.get('s_loss_digester_pct', DEFAULTS['s_loss_digester_pct'])
    target_sbl_tds = inputs.get('target_sbl_tds_pct', DEFAULTS['target_sbl_tds_pct'])
    wood_moisture_pine = inputs.get('wood_moisture_pine', DEFAULTS['wood_moisture_pine'])
    wood_moisture_semichem = inputs.get('wood_moisture_semichem', DEFAULTS['wood_moisture_semichem'])

    # S deficit override — when provided, bypasses outer loop convergence
    s_deficit_override = inputs.get('s_deficit_lbs_hr', None)

    # NaSH/NaOH overrides — fixed values that bypass Secant and dual-constraint
    nash_dry_override = inputs.get('nash_dry_override_lb_hr', None)
    naoh_dry_override = inputs.get('naoh_dry_override_lb_hr', None)

    # Outer loop toggle — enabled by default (forward leg matches lab within 0.03 pts)
    enable_outer_loop = inputs.get('enable_outer_loop', True)

    # ══════════════════════════════════════════════════════════════════
    # Step 1: Liquor compositions from lab (for tank inventory)
    # ══════════════════════════════════════════════════════════════════
    wl_comp = calculate_liquor_composition(
        inputs.get('wl_tta', DEFAULTS['wl_tta']),
        inputs.get('wl_ea', DEFAULTS['wl_ea']),
        inputs.get('wl_aa', DEFAULTS['wl_aa']),
    )
    gl_comp = calculate_liquor_composition(
        inputs.get('gl_tta', DEFAULTS['gl_tta']),
        inputs.get('gl_ea', DEFAULTS['gl_ea']),
        inputs.get('gl_aa', DEFAULTS['gl_aa']),
    )

    lab_wl_ea = inputs.get('wl_ea', DEFAULTS['wl_ea'])

    # ── GL Clarifier: dregs underflow (3_Chem B62-B70) ──
    # Dregs are removed from the GL stream before it goes to the slaker.
    # The underflow contains both solids (dregs) and entrained GL liquor.
    # Na/S in the entrained liquor is accounted for in the loss table (loss_dregs_filter_s/na).
    #
    # Flow calculation:
    #   1. dregs_ton_hr = dry solids rate based on lb/BDT input
    #   2. dregs_total_underflow = dregs / solids_fraction (slurry mass)
    #   3. dregs_liquor_ton_hr = slurry - solids = entrained GL liquor lost
    #   4. dregs_gpm = convert liquor mass to volumetric flow using GL density
    gl_density_lb_gal = calculate_gl_density(gl_comp.tta)

    dregs_ton_hr = (dregs_lb_bdt * total_prod) / 2000 / 24
    if glc_solids_pct > 0:
        dregs_total_underflow = dregs_ton_hr / glc_solids_pct
    else:
        dregs_total_underflow = 0.0
    dregs_liquor_ton_hr = dregs_total_underflow - dregs_ton_hr
    dregs_gpm = dregs_liquor_ton_hr * 2000 / (gl_density_lb_gal * 60) if gl_density_lb_gal > 0 else 0.0

    # ── Slaker grits: entrained WL liquor lost with grits (3_Chem B71-B80) ──
    # Grits are coarse unreacted lime particles screened out at the slaker.
    # The solid lime mass is already handled by slaker_model.py (grits_loss_pct).
    # Here we compute the entrained WL liquor lost with the grits underflow.
    # This flow is subtracted from WL entering the WLC (not from GL).
    grits_ton_hr = (grits_lb_bdt * total_prod) / 2000 / 24
    if grits_solids_pct > 0:
        grits_total_underflow = grits_ton_hr / grits_solids_pct
    else:
        grits_total_underflow = 0.0
    grits_liquor_ton_hr = grits_total_underflow - grits_ton_hr
    grits_entrained_gpm = grits_liquor_ton_hr * 2000 / (gl_density_lb_gal * 60) if gl_density_lb_gal > 0 else 0.0

    # ══════════════════════════════════════════════════════════════════
    # OUTER LOOP: BL composition convergence
    # Feeds computed BL Na%/S% from the forward leg back to the RB.
    # Converges when |ΔNa%| < 0.01 AND |ΔS%| < 0.01 (absolute %).
    # Note: fiberline organics model gives ~33% TDS vs real ~13-19%.
    # Na%/S% on a d.s. basis should still be reasonable since organic
    # overestimation affects numerator and denominator similarly.
    # ══════════════════════════════════════════════════════════════════

    sbl_output = None
    mixed_wbl = None
    bl_outputs = {}  # Keyed by fiberline id

    OUTER_MAX_ITER = 20
    OUTER_TOL = 0.01  # Converge when |ΔNa%| < 0.01 AND |ΔS%| < 0.01
    outer_converged = False
    outer_iterations = 0

    # Total Na losses from loss table (Na2O basis, lb/hr) — used by Na loss factor
    # Note: loss_breakdown.total_na_lb_bdt is in lb Na2O/BDT (already Na2O basis)
    total_na_losses_as_na2o_lb_hr = loss_breakdown.total_na_lb_bdt * total_prod / 24

    # Washable soda Na losses (lb Na2O/hr) — the flow-dependent portion
    washable_soda_na_lb_hr = loss_breakdown.pulp_washable_soda_na * total_prod / 24

    # Dregs solids flow for dregs filter (used inside inner loop for WW flow solve)
    dregs_solids_lb_hr = dregs_lb_bdt * total_prod / 24

    # ── CTO S delta adjustment for initial BL composition ──
    # CTO S enters via WBL mixer (forward leg, end of outer loop iteration).
    # Without this adjustment, the first iteration uses lab BL S% that doesn't
    # reflect CTO changes. In Predictor mode (1 iteration), this is the ONLY
    # correction. In What-If mode, the outer loop corrects via forward leg.
    default_cto_s = DEFAULTS['cto_h2so4_per_ton'] * DEFAULTS['cto_tpd'] / 24 * (MW['S'] / MW['H2SO4'])
    delta_cto_s = cto_s_lb_hr - default_cto_s
    if abs(delta_cto_s) > 0.1:
        bl_density_for_adj = calculate_bl_density(bl_tds, bl_temp)
        dry_solids_est = bl_flow * bl_density_for_adj * bl_tds * 10 * 0.06
        if dry_solids_est > 0:
            bl_s_pct += delta_cto_s / dry_solids_est * 100

    for outer_iter in range(OUTER_MAX_ITER):
        outer_iterations = outer_iter + 1

        # ── Step 2: Recovery Boiler ──
        s_ret_strong_init = 0.9861

        rb_inputs, smelt = calculate_full_rb(
            bl_flow_gpm=bl_flow, bl_tds_pct=bl_tds, bl_temp_f=bl_temp,
            bl_na_pct_inv=bl_na_pct, bl_s_pct_inv=bl_s_pct,
            bl_k_pct=bl_k_pct,
            reduction_eff_pct=re_pct, s_retention_strong=s_ret_strong_init,
            ash_recycled_pct=ash_recycled_pct,
            rb_losses_na2o_bdt=rb_losses_na2o_bdt,
            total_production_bdt_day=total_prod,
            saltcake_flow_lb_hr=saltcake_flow,
        )

        s_ret_results = calculate_s_retention(
            total_production_bdt_day=total_prod,
            dry_solids_lbs_hr=rb_inputs.dry_solids_lbs_hr,
            bl_s_pct_fired=rb_inputs.bl_s_pct_fired,
            saltcake_s_lb_hr=rb_inputs.saltcake_s_lbs_hr,
            cto_s_lb_hr=cto_s_lb_hr,
            losses=loss_breakdown,
        )

        s_ret_strong = s_ret_results.s_retention_strong
        s_ret_weak = s_ret_results.s_retention_weak

        if abs(s_ret_strong - s_ret_strong_init) > 0.001:
            rb_inputs, smelt = calculate_full_rb(
                bl_flow_gpm=bl_flow, bl_tds_pct=bl_tds, bl_temp_f=bl_temp,
                bl_na_pct_inv=bl_na_pct, bl_s_pct_inv=bl_s_pct,
                bl_k_pct=bl_k_pct,
                reduction_eff_pct=re_pct, s_retention_strong=s_ret_strong,
                ash_recycled_pct=ash_recycled_pct,
                rb_losses_na2o_bdt=rb_losses_na2o_bdt,
                total_production_bdt_day=total_prod,
                saltcake_flow_lb_hr=saltcake_flow,
            )

        # Saltcake Na/S contributions (element basis, lb/hr)
        saltcake_na_element_lb_hr = rb_inputs.saltcake_na_lbs_hr
        saltcake_s_element_lb_hr = rb_inputs.saltcake_s_lbs_hr

        # S deficit: total S losses minus S already returned via saltcake and CTO
        total_s_losses_element_lb_hr = loss_breakdown.total_s_lb_bdt * total_prod / 24
        s_deficit_element_lb_hr = total_s_losses_element_lb_hr - saltcake_s_element_lb_hr - cto_s_lb_hr
        s_deficit_as_na2o_lb_hr = max(0.0, s_deficit_element_lb_hr * (MW['Na2O'] / MW['S']))

        # ══════════════════════════════════════════════════════════════════════════
        # Step 3: SECANT METHOD ITERATION FOR SULFIDITY TARGETING
        # ══════════════════════════════════════════════════════════════════════════
        SECANT_MAX_ITER = 20
        SECANT_TOLERANCE = 0.01

        # Build inner_loop_kwargs each outer iteration (smelt changes)
        inner_loop_kwargs = dict(
            smelt=smelt, saltcake_na=saltcake_na_element_lb_hr, saltcake_s=saltcake_s_element_lb_hr,
            cto_s=cto_s_lb_hr,
            ww_flow=ww_flow, ww_tta_lb_ft3=ww_tta_lb_ft3,
            ww_sulfidity=ww_sulfidity, shower_flow=shower_flow,
            smelt_density=smelt_density,
            gl_target_tta_lb_ft3=gl_target_tta_lb_ft3,
            gl_causticity=gl_causticity,
            dregs_gpm=dregs_gpm, grits_entrained_gpm=grits_entrained_gpm,
            gl_temp=gl_temp, causticity=causticity,
            lime_charge_ratio=lime_charge_ratio,
            cao_in_lime=cao_in_lime, caco3_in_lime=caco3_in_lime,
            inerts_in_lime=inerts_in_lime, grits_loss=grits_loss,
            lime_temp=lime_temp, slaker_temp=slaker_temp,
            fiberline_configs=fiberline_configs,
            total_prod=total_prod, lab_wl_ea=lab_wl_ea,
            cooking_sulf=cooking_sulf,
            target_sulf_pct=target_sulf_pct,
            total_na_losses_as_na2o_lb_hr=total_na_losses_as_na2o_lb_hr,
            washable_soda_na_lb_hr=washable_soda_na_lb_hr,
            s_deficit_element_lb_hr=s_deficit_element_lb_hr,
            s_deficit_na2o_lb_hr=s_deficit_as_na2o_lb_hr,
            nash_conc=nash_conc, naoh_conc=naoh_conc,
            nash_dens=nash_dens, naoh_dens=naoh_dens,
            intrusion_water=intrusion_water, dilution_water=dilution_water,
            wlc_underflow_solids=wlc_underflow_solids,
            wlc_mud_density=wlc_mud_density,
            s_deficit_override=s_deficit_override,
            naoh_dry_override=naoh_dry_override,
            # Dregs filter parameters for WW flow solve
            dregs_solids_lb_hr=dregs_solids_lb_hr,
            glc_underflow_solids_pct=glc_solids_pct,
            gl_density_lb_gal=gl_density_lb_gal,
            # DT energy balance
            smelt_temp_f=smelt_temp_f,
            ww_temp_f=ww_temp_f,
            shower_temp_f=shower_temp_f,
            dt_operating_temp_f=dt_operating_temp_f,
            smelt_cp=smelt_cp,
            latent_heat=latent_heat,
        )

        if nash_dry_override is not None:
            # Fixed NaSH mode: skip Secant, run inner loop once with user's value
            inner = _run_inner_loop(**inner_loop_kwargs, nash_override=nash_dry_override)
            secant_converged = False
            secant_iterations = 0
        else:
            # ── First run: get initial NaSH from S deficit (no override) ──
            inner_0 = _run_inner_loop(**inner_loop_kwargs, nash_override=None)
            nash_0 = inner_0['nash_dry']
            sulf_0 = inner_0['final_sulfidity']
            f_0 = sulf_0 - target_sulf_pct

            secant_converged = abs(f_0) < SECANT_TOLERANCE
            secant_iterations = 1
            inner = inner_0

            if not secant_converged:
                # ── Second run: perturb NaSH by 5% for second Secant point ──
                nash_1 = nash_0 * 1.05 if nash_0 > 0 else 100.0
                inner_1 = _run_inner_loop(**inner_loop_kwargs, nash_override=nash_1)
                sulf_1 = inner_1['final_sulfidity']
                f_1 = sulf_1 - target_sulf_pct
                secant_iterations = 2

                if abs(f_1) < SECANT_TOLERANCE:
                    secant_converged = True
                    inner = inner_1
                else:
                    # ── Secant iteration ──
                    nash_prev, nash_curr = nash_0, nash_1
                    f_prev, f_curr = f_0, f_1

                    for secant_iter in range(SECANT_MAX_ITER - 2):
                        # Secant formula
                        if abs(f_curr - f_prev) < 1e-10:
                            nash_next = (nash_prev + nash_curr) / 2
                        else:
                            nash_next = nash_curr - f_curr * (nash_curr - nash_prev) / (f_curr - f_prev)

                        nash_next = max(0.0, min(nash_next, nash_0 * 10))

                        inner_next = _run_inner_loop(**inner_loop_kwargs, nash_override=nash_next)
                        sulf_next = inner_next['final_sulfidity']
                        f_next = sulf_next - target_sulf_pct
                        secant_iterations += 1

                        if abs(f_next) < SECANT_TOLERANCE:
                            secant_converged = True
                            inner = inner_next
                            break

                        nash_prev, nash_curr = nash_curr, nash_next
                        f_prev, f_curr = f_curr, f_next
                        inner = inner_next
                    else:
                        inner = inner_next

        dt_result = inner['dt_result']
        slaker_result = inner['slaker_result']
        chem_result = inner['chem_result']
        wlc_result_inner = inner['wlc_result']

        # ── Step 4: Forward leg (fiberline BL → mixer → evaporator) ──
        final_wl_na2s_g_L = wlc_result_inner.final_na2s_g_L
        final_wl_aa_g_L = wlc_result_inner.final_aa_g_L
        final_wl_naoh_g_L = final_wl_aa_g_L - final_wl_na2s_g_L
        final_wl_na2co3_g_L = wlc_result_inner.final_tta_g_L - final_wl_aa_g_L

        gl_naoh_g_L = dt_result.gl_aa_g_L - dt_result.gl_na2s_g_L
        gl_na2co3_g_L = dt_result.gl_tta_g_L - dt_result.gl_aa_g_L

        bl_outputs = {}
        for fl in fiberline_configs:
            gl_kwargs = {}
            if fl.uses_gl_charge:
                gl_kwargs = dict(
                    gl_flow_gpm=chem_result.gl_charge_gpm.get(fl.id, 0.0),
                    gl_na2s_g_L=dt_result.gl_na2s_g_L,
                    gl_naoh_g_L=gl_naoh_g_L,
                    gl_na2co3_g_L=gl_na2co3_g_L,
                )
            bl_outputs[fl.id] = calculate_fiberline_bl(
                production_bdt_day=fl.production_bdt_day,
                yield_pct=fl.yield_pct,
                wl_flow_gpm=chem_result.fiberline_results[fl.id].wl_demand_gpm,
                wl_na2s_g_L=final_wl_na2s_g_L,
                wl_naoh_g_L=final_wl_naoh_g_L,
                wl_na2co3_g_L=final_wl_na2co3_g_L,
                wood_moisture_pct=fl.wood_moisture,
                s_loss_digester_pct=s_loss_digester,
                ncg_s_lb_bdt=loss_breakdown.ncg_s,
                total_production_bdt_day=total_prod,
                **gl_kwargs,
            )

        mixed_wbl = mix_wbl_streams(
            bl_outputs=list(bl_outputs.values()),
            cto_na_lb_hr=cto_na_lb_hr,
            cto_s_lb_hr=cto_s_lb_hr,
            cto_water_lb_hr=cto_water_lb_hr,
        )

        sbl_output = calculate_evaporator(mixed_wbl, target_tds_pct=target_sbl_tds)

        # ── Outer loop convergence check ──
        new_na_pct = sbl_output.sbl_na_pct_ds
        new_s_pct = sbl_output.sbl_s_pct_ds

        if abs(new_na_pct - bl_na_pct) < OUTER_TOL and abs(new_s_pct - bl_s_pct) < OUTER_TOL:
            outer_converged = True
            break

        # Skip outer loop iteration when override is set or outer loop is disabled
        # NaSH override: outer loop feedback is uncompensated (Secant bypassed),
        # causing runaway BL S% drift. Use fixed BL composition for short-term what-if.
        if s_deficit_override is not None or not enable_outer_loop or nash_dry_override is not None:
            outer_converged = True
            break

        # Update BL composition for next iteration
        bl_na_pct = new_na_pct
        bl_s_pct = new_s_pct
    else:
        # Max iterations without convergence — use last values
        outer_converged = False

    # ══════════════════════════════════════════════════════════════════
    # Store results
    # ══════════════════════════════════════════════════════════════════

    # Extract inner loop values
    dt_result = inner['dt_result']
    slaker_result = inner['slaker_result']
    chem_result = inner['chem_result']
    wlc_result = inner['wlc_result']
    makeup = inner['makeup']
    nash_dry = inner['nash_dry']
    naoh_dry = inner['naoh_dry']
    nash_gpm = inner['nash_gpm']
    naoh_gpm = inner['naoh_gpm']
    final_tta_ton_hr = inner['final_tta_ton_hr']
    final_na2s_ton_hr = inner['final_na2s_ton_hr']
    final_sulfidity = inner['final_sulfidity']
    na_losses = inner['na_losses']
    na_deficit = inner['na_deficit']

    # Solver convergence
    results['solver_converged'] = inner['converged']
    results['solver_iterations'] = inner['iterations']

    # Outer loop convergence
    results['outer_loop_converged'] = outer_converged
    results['outer_loop_iterations'] = outer_iterations

    # Secant method convergence (sulfidity targeting)
    results['secant_converged'] = secant_converged
    results['secant_iterations'] = secant_iterations
    results['target_sulfidity_pct'] = target_sulf_pct
    results['secant_bypassed'] = nash_dry_override is not None
    results['naoh_bypassed'] = naoh_dry_override is not None

    # Recovery Boiler
    results['smelt_sulfidity_pct'] = smelt.smelt_sulfidity_pct
    results['rb_tta_lbs_hr'] = smelt.tta_lbs_hr
    results['rb_active_sulfide'] = smelt.active_sulfide
    results['rb_dead_load'] = smelt.dead_load
    results['rb_na_lbs_hr'] = smelt.na_lbs_hr
    results['rb_s_lbs_hr'] = smelt.s_lbs_hr
    results['rb_k_lbs_hr'] = smelt.k_lbs_hr
    results['bl_density'] = rb_inputs.bl_density_lb_gal
    results['rb_potential_na_alkali'] = smelt.potential_na_alkali
    results['rb_potential_k_alkali'] = smelt.potential_k_alkali
    results['rb_potential_s_alkali'] = smelt.potential_s_alkali
    results['s_retention_weak'] = s_ret_weak
    results['s_retention_strong'] = s_ret_strong
    results['rb_na_pct_mixed'] = rb_inputs.bl_na_pct_mixed
    results['rb_s_pct_mixed'] = rb_inputs.bl_s_pct_mixed
    results['rb_s_pct_fired'] = rb_inputs.bl_s_pct_fired
    results['rb_dry_solids_lbs_hr'] = rb_inputs.dry_solids_lbs_hr
    results['rb_ash_na_na2o'] = rb_inputs.ash_na_na2o
    results['rb_ash_s_na2o'] = rb_inputs.ash_s_na2o
    results['rb_ash_solids_lbs_hr'] = rb_inputs.ash_solids_lbs_hr
    results['rb_virgin_solids_lbs_hr'] = rb_inputs.virgin_solids_lbs_hr
    results['rb_losses_na2o_lbs_hr'] = rb_inputs.rb_losses_na2o_lbs_hr

    # Dissolving tank
    if dt_result:
        results['smelt_flow_gpm'] = dt_result.smelt_flow_gpm
        results['gl_flow_to_slaker_gpm'] = dt_result.gl_flow_to_slaker_gpm
        results['dissolving_tank_flow'] = dt_result.total_dissolving_flow_gpm
        results['gl_tta_g_L'] = dt_result.gl_tta_g_L
        results['gl_na2s_g_L'] = dt_result.gl_na2s_g_L
        results['gl_aa_g_L'] = dt_result.gl_aa_g_L
        # GL EA = NaOH + ½Na2S; NaOH = AA - Na2S
        gl_naoh = dt_result.gl_aa_g_L - dt_result.gl_na2s_g_L
        results['gl_ea_g_L'] = gl_naoh + 0.5 * dt_result.gl_na2s_g_L
        results['gl_sulfidity'] = dt_result.gl_sulfidity
        results['expansion_factor'] = dt_result.expansion_factor
        # DT energy balance
        results['dt_steam_evaporated_lb_hr'] = dt_result.steam_evaporated_lb_hr
        results['dt_steam_evaporated_gpm'] = dt_result.steam_evaporated_gpm
        results['dt_heat_from_smelt_btu_hr'] = dt_result.heat_from_smelt_btu_hr
        results['dt_heat_to_warm_liquor_btu_hr'] = dt_result.heat_to_warm_liquor_btu_hr
        results['dt_net_heat_for_steam_btu_hr'] = dt_result.net_heat_for_steam_btu_hr

    # WW flow solve (mass-balance-closed dissolving tank)
    results['ww_flow_solved_gpm'] = inner['ww_flow_solved_gpm']
    results['ww_flow_input_gpm'] = ww_flow  # Original fixed input for reference
    results['dregs_filtrate_gpm'] = inner['dregs_filtrate_gpm']

    # GL Clarifier
    results['dregs_underflow_gpm'] = dregs_gpm
    results['grits_entrained_gpm'] = grits_entrained_gpm

    # Slaker
    if slaker_result:
        results['yield_factor'] = slaker_result.yield_factor
        results['wl_tta_slaker_g_L'] = slaker_result.wl_tta_g_L
        results['wl_na2s_slaker_g_L'] = slaker_result.wl_na2s_g_L
        results['wl_aa_slaker_g_L'] = slaker_result.wl_aa_g_L
        results['wl_ea_slaker_g_L'] = slaker_result.wl_ea_g_L
        # Add NaOH and Na2CO3 breakdown (causticizing result)
        results['wl_naoh_slaker_g_L'] = slaker_result.wl_naoh_g_L
        results['wl_na2co3_slaker_g_L'] = slaker_result.wl_na2co3_g_L
        results['slaker_steam_ton_hr'] = slaker_result.steam_generated_ton_hr
        results['slaker_water_consumed_ton_hr'] = slaker_result.water_consumed_ton_hr
        results['slaker_gl_mass_ton_hr'] = slaker_result.gl_mass_ton_hr
        results['slaker_wl_mass_ton_hr'] = slaker_result.wl_mass_ton_hr
        results['slaker_total_lime_ton_hr'] = slaker_result.total_lime_ton_hr
        results['slaker_lime_mud_caco3_lb_hr'] = slaker_result.lime_mud_caco3_lb_hr
        results['slaker_lime_mud_total_lb_hr'] = slaker_result.lime_mud_total_lb_hr
        results['slaker_grits_lb_hr'] = slaker_result.grits_loss_lb_hr

    # Chemical charge
    if chem_result:
        results['wl_flow_from_slaker'] = chem_result.wl_flow_from_slaker_gpm
        results['wl_tta_mass_ton_hr'] = chem_result.wl_tta_mass_ton_hr
        results['wl_na2s_mass_ton_hr'] = chem_result.wl_na2s_mass_ton_hr
        results['initial_sulfidity_pct'] = chem_result.initial_sulfidity_pct
        results['total_production_bdt_day'] = chem_result.total_production_bdt_day
        results['total_wl_demand_gpm'] = chem_result.total_wl_demand_gpm

        # Per-fiberline results (dynamic)
        results['fiberline_ids'] = [fl.id for fl in fiberline_configs]
        for fl_id, fl_result in chem_result.fiberline_results.items():
            results[f'{fl_id}_wl_demand_gpm'] = fl_result.wl_demand_gpm
        for fl_id, gl_gpm in chem_result.gl_charge_gpm.items():
            results[f'{fl_id}_gl_gpm'] = gl_gpm

        # Backward compat keys (keep for tests and API consumers)
        results['semichem_gl_gpm'] = chem_result.gl_charge_gpm.get('semichem', 0.0)
        pine_fl = chem_result.fiberline_results.get('pine')
        results['pine_wl_demand_gpm'] = pine_fl.wl_demand_gpm if pine_fl else list(chem_result.fiberline_results.values())[0].wl_demand_gpm
        semichem_fl = chem_result.fiberline_results.get('semichem')
        if semichem_fl:
            results['semichem_wl_demand_gpm'] = semichem_fl.wl_demand_gpm

    # WLC
    if wlc_result:
        results['wlc_overflow_gpm'] = wlc_result.wl_overflow_gpm
        results['wlc_underflow_gpm'] = wlc_result.underflow_gpm
        results['final_wl_tta_g_L'] = wlc_result.final_tta_g_L
        results['final_wl_na2s_g_L'] = wlc_result.final_na2s_g_L
        results['final_wl_aa_g_L'] = wlc_result.final_aa_g_L
        results['final_wl_ea_g_L'] = wlc_result.final_ea_g_L
        # Add NaOH and Na2CO3 breakdown for final WL (after makeup)
        # NaOH = AA - Na2S, Na2CO3 = TTA - AA
        results['final_wl_naoh_g_L'] = wlc_result.final_aa_g_L - wlc_result.final_na2s_g_L
        results['final_wl_na2co3_g_L'] = wlc_result.final_tta_g_L - wlc_result.final_aa_g_L

    # Makeup
    results['nash_dry_lbs_hr'] = nash_dry
    results['naoh_dry_lbs_hr'] = naoh_dry
    results['nash_solution_gpm'] = nash_gpm
    results['naoh_solution_gpm'] = naoh_gpm

    # Recalculate solution lb/hr from final dry values (Secant-adjusted)
    nash_conc = inputs.get('nash_concentration', DEFAULTS['nash_concentration'])
    naoh_conc = inputs.get('naoh_concentration', DEFAULTS['naoh_concentration'])
    results['nash_solution_lbs_hr'] = nash_dry / nash_conc if nash_conc > 0 else 0.0
    results['naoh_solution_lbs_hr'] = naoh_dry / naoh_conc if naoh_conc > 0 else 0.0

    # Recalculate per-BDT values from FINAL NaSH/NaOH (after Secant adjustment)
    # These were wrong when using makeup object (which has pre-Secant values)
    nash_lb_day = nash_dry * 24
    nash_lb_bdt = nash_lb_day / total_prod if total_prod > 0 else 0.0
    results['nash_dry_lb_bdt_na2o'] = nash_lb_bdt * CONV['NaSH_to_Na2O']

    naoh_as_na2o = naoh_dry * CONV['NaOH_to_Na2O']
    results['naoh_dry_lb_bdt_na2o'] = (naoh_as_na2o * 24) / total_prod if total_prod > 0 else 0.0

    # Saltcake per-BDT (unchanged - not affected by Secant)
    results['saltcake_lb_bdt_na2o'] = (saltcake_na_element_lb_hr * CONV['Na_to_Na2O'] * 24) / total_prod if total_prod > 0 else 0.0

    results['saltcake_na_lb_hr'] = saltcake_na_element_lb_hr  # Na element from Na2SO4 (external makeup)
    results['saltcake_s_lb_hr'] = saltcake_s_element_lb_hr    # S element from Na2SO4 (external makeup)
    results['na2s_deficit_ton_hr'] = makeup.na2s_deficit_ton_hr if makeup else 0.0
    results['nash_conversion_factor'] = makeup.nash_conversion_factor if makeup else 0.0
    # Recalculate na_from_nash from final NaSH (Secant-adjusted), not from makeup object
    results['na_from_nash'] = nash_dry * CONV['NaSH_to_Na2O']
    results['na_deficit_remaining'] = na_deficit - results['na_from_nash']

    # Final WL
    results['final_tta_ton_hr'] = final_tta_ton_hr
    results['final_na2s_ton_hr'] = final_na2s_ton_hr
    results['final_sulfidity_pct'] = final_sulfidity

    # Na/S losses
    results['na_losses_lbs_hr'] = na_losses  # Loss-factor-based (for NaOH sizing)
    results['na_deficit_lbs_hr'] = na_deficit
    results['total_s_losses_lb_hr'] = total_s_losses_element_lb_hr  # S element (lb/hr)
    results['total_s_losses_lb_bdt'] = loss_breakdown.total_s_lb_bdt
    results['s_deficit_lb_hr'] = s_deficit_element_lb_hr           # S element (lb/hr)
    results['s_deficit_na2o_lb_hr'] = s_deficit_as_na2o_lb_hr      # Na2O basis (lb/hr)
    results['s_from_digesters_na2o_lb_hr'] = s_ret_results.s_from_digesters_na2o_lb_hr
    results['net_s_balance_lb_hr'] = s_ret_results.net_s_balance_lb_hr
    results['cto_s_lbs_hr'] = cto_s_lb_hr
    results['cto_h2so4_per_ton'] = cto_h2so4_per_ton
    results['cto_tpd'] = cto_tpd
    results['cto_na_lb_hr'] = cto_na_lb_hr

    # Per-source losses (13 rows with S + Na2O columns)
    results['loss_table_detail'] = calculate_losses_detailed(total_prod, loss_breakdown)

    # Total Na losses (Na2O basis) — from loss table (for balance display)
    results['total_na_losses_na2o_lb_hr'] = total_na_losses_as_na2o_lb_hr
    results['total_na_losses_na2o_lb_bdt'] = loss_breakdown.total_na_lb_bdt

    # Dual-constraint NaOH sizing (for economic analysis)
    results['naoh_for_losses_lb_hr'] = inner['naoh_for_losses']
    results['naoh_for_ea_demand_lb_hr'] = inner['naoh_for_ea_demand']
    results['ea_required_lb_hr'] = inner['ea_required_lb_hr']
    results['ea_from_wl_lb_hr'] = inner['ea_from_wl_lb_hr']
    results['ea_deficit_lb_hr'] = inner['ea_deficit_lb_hr']
    results['naoh_constraint'] = 'EA_demand' if inner['naoh_for_ea_demand'] > inner['naoh_for_losses'] else 'losses'

    # CE flow-sensitivity adjustment diagnostics
    results['ce_na_adjustment_lb_hr'] = inner['ce_na_adjustment_lb_hr']
    results['adjusted_na_losses_lb_hr'] = inner['adjusted_na_losses_lb_hr']

    # First-principles EA tracking
    results['ea_required_pine_lb_hr'] = inner['ea_required_pine_lb_hr']
    results['ea_required_semi_wl_lb_hr'] = inner['ea_required_semi_wl_lb_hr']
    results['ea_from_gl_to_semi_lb_hr'] = inner['ea_from_gl_to_semi_lb_hr']
    results['ea_from_slaker_lb_hr'] = inner['ea_from_slaker_lb_hr']
    results['ea_from_nash_lb_hr'] = inner['ea_from_nash_lb_hr']

    # Na inventory tracking
    results['na_in_lb_hr'] = inner['na_in_lb_hr']
    results['na_out_lb_hr'] = inner['na_out_lb_hr']
    results['na_accumulation_lb_hr'] = inner['na_accumulation_lb_hr']
    results['na_balance_status'] = inner['na_balance_status']

    # First-principles causticizing outputs (from slaker)
    if slaker_result:
        results['gl_na2co3_g_L'] = slaker_result.gl_na2co3_g_L
        results['gl_na2co3_lb_hr'] = slaker_result.gl_na2co3_lb_hr
        results['causticizing_conversion_fraction'] = slaker_result.conversion_fraction
        results['lime_required_lb_hr'] = slaker_result.lime_required_lb_hr
        results['lime_feed_lb_hr'] = slaker_result.lime_feed_lb_hr
        results['achieved_ce_pct'] = slaker_result.achieved_ce_pct

    # Chemical additions (element lb/hr) — ALL external inputs
    # Note: Saltcake (2227 lb/hr Na2SO4) is EXTERNAL makeup added to RB.
    #       This is different from Ash Recycled (7%) which is INTERNAL recirculation.
    nash_na_element = nash_dry * MW['Na'] / MW['NaSH']
    nash_s_element = nash_dry * MW['S'] / MW['NaSH']
    naoh_na_element = naoh_dry * MW['Na'] / MW['NaOH']

    # Chemical additions — ALL external inputs to the circuit (element lb/hr)
    # Saltcake (Na₂SO₄) is EXTERNAL makeup added to RB.
    # Ash recycled (7%) is INTERNAL recirculation of ESP dust — NOT in this list.
    results['chemical_additions'] = [
        {'source': 'NaSH', 'na_lb_hr': nash_na_element, 's_lb_hr': nash_s_element},
        {'source': 'NaOH', 'na_lb_hr': naoh_na_element, 's_lb_hr': 0.0},
        {'source': 'CTO Brine', 'na_lb_hr': cto_na_lb_hr, 's_lb_hr': cto_s_lb_hr},
        {'source': 'Saltcake', 'na_lb_hr': saltcake_na_element_lb_hr, 's_lb_hr': saltcake_s_element_lb_hr},
    ]

    # True net S balance: all S inputs minus all S losses
    # Positive = surplus (more in than out), Negative = deficit (more out than in)
    # Overrides the pre-NaSH value from s_retention (which is the S deficit used for NaSH sizing)
    total_s_in = nash_s_element + saltcake_s_element_lb_hr + cto_s_lb_hr
    total_s_out = total_s_losses_element_lb_hr
    results['net_s_balance_lb_hr'] = total_s_in - total_s_out

    # Na losses in element lb/hr (existing na_losses is Na2O basis)
    results['na_losses_element_lb_hr'] = na_losses * (2 * MW['Na'] / MW['Na2O'])

    # Forward leg results
    results['bl_na_pct_lab'] = bl_na_pct_lab       # Original lab input (unchanged)
    results['bl_s_pct_lab'] = bl_s_pct_lab         # Original lab input (unchanged)
    results['bl_na_pct_computed'] = sbl_output.sbl_na_pct_ds if sbl_output else bl_na_pct_lab
    results['bl_s_pct_computed'] = sbl_output.sbl_s_pct_ds if sbl_output else bl_s_pct_lab
    results['bl_na_pct_used'] = bl_na_pct           # Converged value (used by RB in final iteration)
    results['bl_s_pct_used'] = bl_s_pct             # Converged value (used by RB in final iteration)

    if sbl_output:
        results['sbl_flow_lb_hr'] = sbl_output.sbl_flow_lb_hr
        results['sbl_tds_pct'] = sbl_output.sbl_tds_pct
        results['sbl_na_element_lb_hr'] = sbl_output.na_element_lb_hr
        results['sbl_s_element_lb_hr'] = sbl_output.s_element_lb_hr
        results['evaporator_water_removed_lb_hr'] = sbl_output.water_removed_lb_hr

    if mixed_wbl:
        results['wbl_na_pct_ds'] = mixed_wbl.na_pct_ds
        results['wbl_s_pct_ds'] = mixed_wbl.s_pct_ds
        results['wbl_tds_pct'] = mixed_wbl.tds_pct
        results['wbl_total_flow_lb_hr'] = mixed_wbl.total_flow_lb_hr

    # Per-fiberline BL results (dynamic)
    for fl_id, bl_out in bl_outputs.items():
        results[f'{fl_id}_bl_organics_lb_hr'] = bl_out.organics_lb_hr
        results[f'{fl_id}_bl_inorganic_solids_lb_hr'] = bl_out.inorganic_solids_lb_hr
    # Backward compat keys
    if 'pine' in bl_outputs:
        results['pine_bl_organics_lb_hr'] = bl_outputs['pine'].organics_lb_hr
        results['pine_bl_inorganic_solids_lb_hr'] = bl_outputs['pine'].inorganic_solids_lb_hr
    if 'semichem' in bl_outputs:
        results['semichem_bl_organics_lb_hr'] = bl_outputs['semichem'].organics_lb_hr
        results['semichem_bl_inorganic_solids_lb_hr'] = bl_outputs['semichem'].inorganic_solids_lb_hr

    # ══════════════════════════════════════════════════════════════════
    # Step 6: Tank inventories (outside iteration — uses lab values)
    # ══════════════════════════════════════════════════════════════════

    tank_levels = inputs.get('tank_levels', DEFAULTS['tank_levels'])

    wl_tanks = []
    for tn in TANK_GROUPS['white_liquor']:
        if tn in tank_levels:
            wl_tanks.append(calculate_tank_inventory(tn, tank_levels[tn], wl_comp))
    gl_tanks = []
    for tn in TANK_GROUPS['green_liquor']:
        if tn in tank_levels:
            gl_tanks.append(calculate_tank_inventory(tn, tank_levels[tn], gl_comp))

    bl_tank_tds = inputs.get('bl_tank_tds', DEFAULTS['bl_tank_tds'])
    bl_tank_temp = inputs.get('bl_tank_temp', DEFAULTS['bl_tank_temp'])
    bl_na_pct_inv_weak = inputs.get('bl_na_pct_inv_weak', DEFAULTS['bl_na_pct_inv_weak'])
    bl_na_pct_inv_strong = inputs.get('bl_na_pct_inv_strong', DEFAULTS['bl_na_pct_inv_strong'])
    bl_s_pct_inv = inputs.get('bl_s_pct_inv', DEFAULTS['bl_s_pct_inv'])

    # CTO S increment: CTO S added to WBL stream increases S% d.s.
    # Computed as CTO_S_lb_hr / dry_solids_to_RB_lb_hr × 100
    if rb_inputs.dry_solids_lbs_hr > 0:
        cto_s_increment_pct = cto_s_lb_hr / rb_inputs.dry_solids_lbs_hr * 100
    else:
        cto_s_increment_pct = 0.0
    results['cto_s_increment_pct'] = cto_s_increment_pct

    bl_tanks = []
    for group in ['weak_black_liquor', 'strong_black_liquor']:
        # Weak BL: all losses ahead (evap + RB) → s_ret_weak
        # Strong BL: already concentrated, only RB losses ahead → s_ret_strong
        ret = s_ret_weak if group == 'weak_black_liquor' else s_ret_strong
        for tn in TANK_GROUPS[group]:
            if tn in tank_levels:
                na_pct_inv = bl_na_pct_inv_strong if tn == 'tank_65pct' else bl_na_pct_inv_weak
                # Add CTO S increment to lab S% for inventory
                adjusted_s_pct = bl_s_pct_inv + cto_s_increment_pct
                bl_tanks.append(calculate_bl_inventory(
                    tn, tank_levels[tn],
                    tds_pct=bl_tank_tds.get(tn, 19.23),
                    temp_f=bl_tank_temp.get(tn, 205.0),
                    na_pct=na_pct_inv, s_pct=adjusted_s_pct, k_pct=bl_k_pct,
                    reduction_eff_pct=re_pct, s_retention=ret,
                ))

    results['total_wl_tta_tons'] = sum(t.tta_tons for t in wl_tanks)
    results['total_wl_na2s_tons'] = sum(t.na2s_tons for t in wl_tanks)
    results['total_gl_tta_tons'] = sum(t.tta_tons for t in gl_tanks)
    results['total_gl_na2s_tons'] = sum(t.na2s_tons for t in gl_tanks)
    results['total_bl_latent_tta_tons'] = sum(t.latent_tta_tons for t in bl_tanks)
    results['total_bl_latent_na2s_tons'] = sum(t.latent_na2s_tons for t in bl_tanks)

    # ══════════════════════════════════════════════════════════════════
    # Step 7: Current and latent sulfidity
    # ══════════════════════════════════════════════════════════════════

    rb_active_sulfide_tons_day = (smelt.active_sulfide / 2000) * 24
    rb_tta_tons_day = (smelt.tta_lbs_hr / 2000) * 24

    nash_na2s_tons_day = nash_dry * CONV['Na2O_per_NaSH'] * 24 / 2000
    nash_tta_tons_day = nash_dry * CONV['NaSH_to_Na2O'] * 24 / 2000
    naoh_tta_tons_day = naoh_dry * CONV['NaOH_to_Na2O'] * 24 / 2000

    s_losses_na2o_tons_day = s_ret_results.total_s_losses_lb_hr * CONV['S_to_Na2O'] * 24 / 2000

    metrics = calculate_sulfidity_metrics(
        wl_tanks, gl_tanks, bl_tanks,
        makeup_na2s_tons_day=nash_na2s_tons_day,
        makeup_tta_tons_day=nash_tta_tons_day + naoh_tta_tons_day,
        s_losses_na2o_tons_day=s_losses_na2o_tons_day,
    )

    results['current_sulfidity_pct'] = metrics.current_sulfidity_pct
    results['latent_sulfidity_pct'] = metrics.latent_sulfidity_pct
    results['sulfidity_trend'] = metrics.sulfidity_trend
    results['rb_active_sulfide_tons_day'] = rb_active_sulfide_tons_day
    results['rb_tta_tons_day'] = rb_tta_tons_day

    results['wl_sulfidity_pct'] = wl_comp.sulfidity_tta_pct
    results['gl_sulfidity_pct'] = gl_comp.sulfidity_tta_pct
    results['wl_na2s_g_L'] = wl_comp.na2s_g_L

    # ══════════════════════════════════════════════════════════════════
    # Step 8: Unit operation Na/S tracking (with TTA/Na2S/flow for circuit map)
    # ══════════════════════════════════════════════════════════════════
    unit_ops = []

    # Helper: g/L × GPM → ton Na2O/hr
    def _gl_to_ton(g_L, gpm):
        return g_L * gpm * CONV['GPM_GL_TO_LB_HR'] / 2000

    # White Liquor (entering digesters)
    if slaker_result and chem_result:
        wl_total_gpm = chem_result.total_wl_demand_gpm
        wl_factor = wl_total_gpm * CONV['GPM_GL_TO_LB_HR']
        wl_na_total = slaker_result.wl_tta_g_L * wl_factor * (2 * MW['Na'] / MW['Na2O'])
        wl_s_total = slaker_result.wl_na2s_g_L * wl_factor * (MW['S'] / MW['Na2O'])
        # Use final WL values (after WLC) for TTA/Na2S
        final_wl_tta_g_L = wlc_result.final_tta_g_L if wlc_result else slaker_result.wl_tta_g_L
        final_wl_na2s_g_L = wlc_result.final_na2s_g_L if wlc_result else slaker_result.wl_na2s_g_L
        unit_ops.append({
            'stage': 'White Liquor (to digesters)',
            'na_lb_hr': round(wl_na_total, 1),
            's_lb_hr': round(wl_s_total, 1),
            'na_pct_ds': None,
            's_pct_ds': None,
            'tta_na2o_ton_hr': round(_gl_to_ton(final_wl_tta_g_L, wl_total_gpm), 4),
            'na2s_na2o_ton_hr': round(_gl_to_ton(final_wl_na2s_g_L, wl_total_gpm), 4),
            'flow_gpm': round(wl_total_gpm, 1),
        })

    # Per-fiberline Digester → WBL
    for fl in fiberline_configs:
        bl_out = bl_outputs.get(fl.id)
        if bl_out:
            unit_ops.append({
                'stage': f'{fl.name} Digester BL',
                'na_lb_hr': round(bl_out.na_element_lb_hr, 1),
                's_lb_hr': round(bl_out.s_element_lb_hr, 1),
                'na_pct_ds': round(bl_out.wbl_na_pct_ds, 2),
                's_pct_ds': round(bl_out.wbl_s_pct_ds, 2),
                'tta_na2o_ton_hr': round(bl_out.na2s_na2o_lb_hr / 2000 if hasattr(bl_out, 'na2s_na2o_lb_hr') else 0, 4),
                'na2s_na2o_ton_hr': round(bl_out.na2s_na2o_lb_hr / 2000 if hasattr(bl_out, 'na2s_na2o_lb_hr') else 0, 4),
                'flow_gpm': None,
            })

    # CTO Brine — Na2SO4 compound mass is the "dry solids"
    cto_na2so4_lb_hr = cto_s_lb_hr * (MW['Na2SO4'] / MW['S']) if cto_s_lb_hr > 0 else 0
    cto_na_pct = (cto_na_lb_hr / cto_na2so4_lb_hr * 100) if cto_na2so4_lb_hr > 0 else None
    cto_s_pct = (cto_s_lb_hr / cto_na2so4_lb_hr * 100) if cto_na2so4_lb_hr > 0 else None
    unit_ops.append({
        'stage': 'CTO Brine',
        'na_lb_hr': round(cto_na_lb_hr, 1),
        's_lb_hr': round(cto_s_lb_hr, 1),
        'na_pct_ds': round(cto_na_pct, 2) if cto_na_pct is not None else None,
        's_pct_ds': round(cto_s_pct, 2) if cto_s_pct is not None else None,
        'tta_na2o_ton_hr': round(cto_na2so4_lb_hr * (MW['Na2O'] / MW['Na2SO4']) / 2000, 4) if cto_na2so4_lb_hr > 0 else 0.0,
        'na2s_na2o_ton_hr': 0.0,
        'flow_gpm': None,
    })

    # Mixed WBL (after mixer)
    if mixed_wbl:
        unit_ops.append({
            'stage': 'Mixed WBL',
            'na_lb_hr': round(mixed_wbl.na_element_lb_hr, 1),
            's_lb_hr': round(mixed_wbl.s_element_lb_hr, 1),
            'na_pct_ds': round(mixed_wbl.na_pct_ds, 2),
            's_pct_ds': round(mixed_wbl.s_pct_ds, 2),
            'tta_na2o_ton_hr': None,
            'na2s_na2o_ton_hr': None,
            'flow_gpm': None,
        })

    # Evaporator → SBL
    if sbl_output:
        unit_ops.append({
            'stage': 'Evaporator (SBL)',
            'na_lb_hr': round(sbl_output.na_element_lb_hr, 1),
            's_lb_hr': round(sbl_output.s_element_lb_hr, 1),
            'na_pct_ds': round(sbl_output.sbl_na_pct_ds, 2),
            's_pct_ds': round(sbl_output.sbl_s_pct_ds, 2),
            'tta_na2o_ton_hr': None,
            'na2s_na2o_ton_hr': None,
            'flow_gpm': None,
        })

    # Recovery Boiler → Smelt
    smelt_s_element = (smelt.active_sulfide + smelt.dead_load) * MW['S'] / MW['Na2O']
    smelt_na_element = smelt.na_lbs_hr - (
        smelt.ash_na_na2o + smelt.rb_losses_na2o_lbs_hr
    ) * 2 * MW['Na'] / MW['Na2O']
    unit_ops.append({
        'stage': 'Recovery Boiler (Smelt)',
        'na_lb_hr': round(smelt_na_element, 1),
        's_lb_hr': round(smelt_s_element, 1),
        'na_pct_ds': None,
        's_pct_ds': None,
        'tta_na2o_ton_hr': round(smelt.tta_lbs_hr / 2000, 4),
        'na2s_na2o_ton_hr': round(smelt.active_sulfide / 2000, 4),
        'flow_gpm': None,
    })

    # Green Liquor
    if dt_result:
        gl_factor = dt_result.gl_flow_to_slaker_gpm * CONV['GPM_GL_TO_LB_HR']
        gl_na_total = dt_result.gl_tta_g_L * gl_factor * (2 * MW['Na'] / MW['Na2O'])
        gl_s_total = dt_result.gl_na2s_g_L * gl_factor * (MW['S'] / MW['Na2O'])
        unit_ops.append({
            'stage': 'Green Liquor',
            'na_lb_hr': round(gl_na_total, 1),
            's_lb_hr': round(gl_s_total, 1),
            'na_pct_ds': None,
            's_pct_ds': None,
            'tta_na2o_ton_hr': round(_gl_to_ton(dt_result.gl_tta_g_L, dt_result.gl_flow_to_slaker_gpm), 4),
            'na2s_na2o_ton_hr': round(_gl_to_ton(dt_result.gl_na2s_g_L, dt_result.gl_flow_to_slaker_gpm), 4),
            'flow_gpm': round(dt_result.gl_flow_to_slaker_gpm, 1),
        })

    # White Liquor (from slaker)
    if slaker_result:
        slaker_wl_gpm = slaker_result.wl_flow_gpm
        slaker_factor = slaker_wl_gpm * CONV['GPM_GL_TO_LB_HR']
        slaker_na = slaker_result.wl_tta_g_L * slaker_factor * (2 * MW['Na'] / MW['Na2O'])
        slaker_s = slaker_result.wl_na2s_g_L * slaker_factor * (MW['S'] / MW['Na2O'])
        unit_ops.append({
            'stage': 'White Liquor (from slaker)',
            'na_lb_hr': round(slaker_na, 1),
            's_lb_hr': round(slaker_s, 1),
            'na_pct_ds': None,
            's_pct_ds': None,
            'tta_na2o_ton_hr': round(_gl_to_ton(slaker_result.wl_tta_g_L, slaker_wl_gpm), 4),
            'na2s_na2o_ton_hr': round(_gl_to_ton(slaker_result.wl_na2s_g_L, slaker_wl_gpm), 4),
            'flow_gpm': round(slaker_wl_gpm, 1),
        })

    results['unit_operations'] = unit_ops

    return results
