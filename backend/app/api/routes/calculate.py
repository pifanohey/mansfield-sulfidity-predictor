"""Calculation API endpoints."""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

from ..schemas import (
    CalculationRequest, CalculationResponse, WhatIfRequest, WhatIfResponse,
    SensitivityResponse, SensitivityItem,
    SulfidityOutput, MakeupOutput, RecoveryBoilerOutput,
    InventoryOutput, MassBalanceOutput, GuidanceItemOutput,
    WLQualityOutput, ForwardLegOutput, FiberlineBLResult,
    UnitOperationRow, LossDetailRow, ChemicalAdditionRow,
)
from ...engine.orchestrator import run_calculations
from ...engine.guidance import generate_guidance
from ...engine.sensitivity import run_sensitivity_analysis
from ...engine.mill_profile import get_mill_config

router = APIRouter(prefix="/api", tags=["calculate"])


LB_FT3_TO_GL = 16.01846


def _build_response(results: Dict[str, Any], inputs: Dict[str, Any]) -> CalculationResponse:
    guidance_items = generate_guidance(results, inputs)

    # WL quality: convert g/L to lb/ft3
    final_tta_gL = results.get('final_wl_tta_g_L', 0)
    final_aa_gL = results.get('final_wl_aa_g_L', 0)
    final_ea_gL = results.get('final_wl_ea_g_L', 0)
    final_na2s_gL = results.get('final_wl_na2s_g_L', 0)

    # Build per-fiberline BL results from dynamic engine keys
    fiberline_bl_list: list = []
    fiberline_ids = results.get('fiberline_ids', [])
    if fiberline_ids:
        try:
            mill_cfg = get_mill_config()
            fl_name_map = {fl.id: fl.name for fl in mill_cfg.fiberlines}
        except Exception:
            fl_name_map = {}
        for fl_id in fiberline_ids:
            fiberline_bl_list.append(FiberlineBLResult(
                id=fl_id,
                name=fl_name_map.get(fl_id, fl_id),
                organics_lb_hr=results.get(f'{fl_id}_bl_organics_lb_hr', 0.0),
                inorganic_solids_lb_hr=results.get(f'{fl_id}_bl_inorganic_solids_lb_hr', 0.0),
            ))

    # Build per-fiberline intermediate keys
    per_fl_intermediates: dict = {}
    for fl_id in fiberline_ids:
        wl_key = f'{fl_id}_wl_demand_gpm'
        gl_key = f'{fl_id}_gl_gpm'
        if wl_key in results:
            per_fl_intermediates[wl_key] = results[wl_key]
        if gl_key in results:
            per_fl_intermediates[gl_key] = results[gl_key]

    return CalculationResponse(
        status='converged' if results.get('solver_converged', True) else 'not_converged',
        solver={
            'converged': results.get('solver_converged', True),
            'iterations': results.get('solver_iterations', 0),
        },
        sulfidity=SulfidityOutput(
            current_pct=results.get('current_sulfidity_pct', 0),
            latent_pct=results.get('latent_sulfidity_pct', 0),
            final_pct=results.get('final_sulfidity_pct', 0),
            smelt_pct=results.get('smelt_sulfidity_pct', 0),
            trend=results.get('sulfidity_trend', 'stable'),
        ),
        makeup=MakeupOutput(
            nash_dry_lb_hr=results.get('nash_dry_lbs_hr', 0),
            nash_solution_lb_hr=results.get('nash_solution_lbs_hr', 0),
            nash_gpm=results.get('nash_solution_gpm', 0),
            naoh_dry_lb_hr=results.get('naoh_dry_lbs_hr', 0),
            naoh_solution_lb_hr=results.get('naoh_solution_lbs_hr', 0),
            naoh_gpm=results.get('naoh_solution_gpm', 0),
            nash_lb_bdt_na2o=results.get('nash_dry_lb_bdt_na2o', 0),
            naoh_lb_bdt_na2o=results.get('naoh_dry_lb_bdt_na2o', 0),
            saltcake_lb_bdt_na2o=results.get('saltcake_lb_bdt_na2o', 0),
        ),
        recovery_boiler=RecoveryBoilerOutput(
            tta_lb_hr=results.get('rb_tta_lbs_hr', 0),
            active_sulfide_lb_hr=results.get('rb_active_sulfide', 0),
            dead_load_lb_hr=results.get('rb_dead_load', 0),
            na_lbs_hr=results.get('rb_na_lbs_hr', 0),
            s_lbs_hr=results.get('rb_s_lbs_hr', 0),
            bl_density_lb_gal=results.get('bl_density', 0),
            potential_na_alkali=results.get('rb_potential_na_alkali', 0),
            potential_k_alkali=results.get('rb_potential_k_alkali', 0),
            potential_s_alkali=results.get('rb_potential_s_alkali', 0),
            dry_solids_lbs_hr=results.get('rb_dry_solids_lbs_hr', 0),
            bl_na_pct_mixed=results.get('rb_na_pct_mixed', 0),
            bl_s_pct_mixed=results.get('rb_s_pct_mixed', 0),
            bl_s_pct_fired=results.get('rb_s_pct_fired', 0),
        ),
        inventory=InventoryOutput(
            wl_tta_tons=results.get('total_wl_tta_tons', 0),
            wl_na2s_tons=results.get('total_wl_na2s_tons', 0),
            gl_tta_tons=results.get('total_gl_tta_tons', 0),
            gl_na2s_tons=results.get('total_gl_na2s_tons', 0),
            bl_latent_tta_tons=results.get('total_bl_latent_tta_tons', 0),
            bl_latent_na2s_tons=results.get('total_bl_latent_na2s_tons', 0),
        ),
        mass_balance=MassBalanceOutput(
            na_losses_lb_hr=results.get('na_losses_lbs_hr', 0),
            na_deficit_lb_hr=results.get('na_deficit_lbs_hr', 0),
            total_s_losses_lb_hr=results.get('total_s_losses_lb_hr', 0),
            cto_s_lbs_hr=results.get('cto_s_lbs_hr', 0),
            net_s_balance_lb_hr=results.get('net_s_balance_lb_hr', 0),
        ),
        wl_quality=WLQualityOutput(
            tta_g_L=final_tta_gL,
            aa_g_L=final_aa_gL,
            ea_g_L=final_ea_gL,
            na2s_g_L=final_na2s_gL,
            tta_lb_ft3=final_tta_gL / LB_FT3_TO_GL if LB_FT3_TO_GL > 0 else 0,
            aa_lb_ft3=final_aa_gL / LB_FT3_TO_GL if LB_FT3_TO_GL > 0 else 0,
            ea_lb_ft3=final_ea_gL / LB_FT3_TO_GL if LB_FT3_TO_GL > 0 else 0,
            na2s_lb_ft3=final_na2s_gL / LB_FT3_TO_GL if LB_FT3_TO_GL > 0 else 0,
            sulfidity_pct=results.get('final_sulfidity_pct', 0),
            causticity_pct=inputs.get('causticity_pct', 81.0),
            wl_flow_gpm=results.get('wlc_overflow_gpm', results.get('wl_flow_from_slaker', 0)),
            wl_demand_gpm=results.get('total_wl_demand_gpm', 0),
        ),
        forward_leg=ForwardLegOutput(
            fiberline_bl=fiberline_bl_list,
            cto_na_lb_hr=results.get('cto_na_lb_hr', 0),
            cto_s_lbs_hr=results.get('cto_s_lbs_hr', 0),
            wbl_total_flow_lb_hr=results.get('wbl_total_flow_lb_hr', 0),
            wbl_tds_pct=results.get('wbl_tds_pct', 0),
            wbl_na_pct_ds=results.get('wbl_na_pct_ds', 0),
            wbl_s_pct_ds=results.get('wbl_s_pct_ds', 0),
            sbl_flow_lb_hr=results.get('sbl_flow_lb_hr', 0),
            sbl_tds_pct=results.get('sbl_tds_pct', 0),
            sbl_na_element_lb_hr=results.get('sbl_na_element_lb_hr', 0),
            sbl_s_element_lb_hr=results.get('sbl_s_element_lb_hr', 0),
            evaporator_water_removed_lb_hr=results.get('evaporator_water_removed_lb_hr', 0),
            rb_virgin_solids_lbs_hr=results.get('rb_virgin_solids_lbs_hr', 0),
            rb_ash_solids_lbs_hr=results.get('rb_ash_solids_lbs_hr', 0),
            bl_na_pct_used=results.get('bl_na_pct_used', 0),
            bl_s_pct_used=results.get('bl_s_pct_used', 0),
        ),
        guidance=[
            GuidanceItemOutput(
                severity=g.severity, category=g.category,
                title=g.title, description=g.description,
                action=g.action, impact=g.impact,
            ) for g in guidance_items
        ],
        production={
            'total_bdt_day': results.get('total_production_bdt_day', 0),
            'wl_flow_from_slaker_gpm': results.get('wl_flow_from_slaker', 0),
            'initial_sulfidity_pct': results.get('initial_sulfidity_pct', 0),
        },
        intermediate={
            'na2s_deficit_ton_hr': results.get('na2s_deficit_ton_hr', 0),
            'nash_conversion_factor': results.get('nash_conversion_factor', 0),
            'na_from_nash': results.get('na_from_nash', 0),
            'na_deficit_remaining': results.get('na_deficit_remaining', 0),
            'wl_tta_mass_ton_hr': results.get('wl_tta_mass_ton_hr', 0),
            'wl_na2s_mass_ton_hr': results.get('wl_na2s_mass_ton_hr', 0),
            'final_tta_ton_hr': results.get('final_tta_ton_hr', 0),
            'final_na2s_ton_hr': results.get('final_na2s_ton_hr', 0),
            # Computed values (formerly inputs, now calculated by engine)
            'smelt_flow_gpm': results.get('smelt_flow_gpm', 0),
            'gl_flow_to_slaker_gpm': results.get('gl_flow_to_slaker_gpm', 0),
            'yield_factor': results.get('yield_factor', 0),
            'expansion_factor': results.get('expansion_factor', 0),
            's_retention_weak': results.get('s_retention_weak', 0),
            's_retention_strong': results.get('s_retention_strong', 0),
            'gl_tta_g_L': results.get('gl_tta_g_L', 0),
            'gl_na2s_g_L': results.get('gl_na2s_g_L', 0),
            'wl_tta_slaker_g_L': results.get('wl_tta_slaker_g_L', 0),
            'wl_na2s_slaker_g_L': results.get('wl_na2s_slaker_g_L', 0),
            'wlc_overflow_gpm': results.get('wlc_overflow_gpm', 0),
            'total_wl_demand_gpm': results.get('total_wl_demand_gpm', 0),
            'final_wl_tta_g_L': results.get('final_wl_tta_g_L', 0),
            'final_wl_na2s_g_L': results.get('final_wl_na2s_g_L', 0),
            'final_wl_ea_g_L': results.get('final_wl_ea_g_L', 0),
            'cto_s_increment_pct': results.get('cto_s_increment_pct', 0),
            # GL clarifier / slaker / WLC fields for flow diagram
            'dregs_underflow_gpm': results.get('dregs_underflow_gpm', 0),
            'semichem_gl_gpm': results.get('semichem_gl_gpm', 0),
            'grits_entrained_gpm': results.get('grits_entrained_gpm', 0),
            'wlc_underflow_gpm': results.get('wlc_underflow_gpm', 0),
            'wl_flow_from_slaker_gpm': results.get('wl_flow_from_slaker', 0),
            'gl_aa_g_L': results.get('gl_aa_g_L', 0),
            'gl_sulfidity': results.get('gl_sulfidity', 0),
            'gl_sulfidity_pct': results.get('gl_sulfidity_pct', 0),
            'fiberline_ids': results.get('fiberline_ids', []),
            'wl_naoh_slaker_g_L': results.get('wl_naoh_slaker_g_L', 0),
            'wl_aa_slaker_g_L': results.get('wl_aa_slaker_g_L', 0),
            'wl_ea_slaker_g_L': results.get('wl_ea_slaker_g_L', 0),
            'pine_wl_demand_gpm': results.get('pine_wl_demand_gpm', 0),
            'semichem_wl_demand_gpm': results.get('semichem_wl_demand_gpm', 0),
            'final_wl_aa_g_L': results.get('final_wl_aa_g_L', 0),
            'final_wl_naoh_g_L': results.get('final_wl_naoh_g_L', 0),
            'final_wl_na2co3_g_L': results.get('final_wl_na2co3_g_L', 0),
            'dissolving_tank_flow': results.get('dissolving_tank_flow', 0),
            # Process flow flag
            'makeup_after_wlc': results.get('makeup_after_wlc', False),
            # WLC clean overflow (before makeup) — only present when makeup_after_wlc=True
            'wlc_clean_overflow_gpm': results.get('wlc_clean_overflow_gpm', 0),
            'wlc_clean_tta_g_L': results.get('wlc_clean_tta_g_L', 0),
            'wlc_clean_na2s_g_L': results.get('wlc_clean_na2s_g_L', 0),
            'wlc_clean_ea_g_L': results.get('wlc_clean_ea_g_L', 0),
            'wlc_clean_sulfidity_pct': results.get('wlc_clean_sulfidity_pct', 0),
            **per_fl_intermediates,
        },
        unit_operations=[
            UnitOperationRow(**row)
            for row in results.get('unit_operations', [])
        ],
        loss_table_detail=[
            LossDetailRow(**row)
            for row in results.get('loss_table_detail', [])
        ],
        chemical_additions=[
            ChemicalAdditionRow(**row)
            for row in results.get('chemical_additions', [])
        ],
        na_losses_element_lb_hr=results.get('na_losses_element_lb_hr', 0),
        saltcake_na_lb_hr=results.get('saltcake_na_lb_hr', 0),
        saltcake_s_lb_hr=results.get('saltcake_s_lb_hr', 0),
        bl_na_pct_lab=results.get('bl_na_pct_lab', 0),
        bl_s_pct_lab=results.get('bl_s_pct_lab', 0),
        bl_na_pct_computed=results.get('bl_na_pct_computed', 0),
        bl_s_pct_computed=results.get('bl_s_pct_computed', 0),
        bl_na_pct_used=results.get('bl_na_pct_used', 0),
        bl_s_pct_used=results.get('bl_s_pct_used', 0),
        total_production_bdt_day=results.get('total_production_bdt_day', 0),
        outer_loop_converged=results.get('outer_loop_converged', True),
        outer_loop_iterations=results.get('outer_loop_iterations', 1),
        dt_steam_evaporated_lb_hr=results.get('dt_steam_evaporated_lb_hr', 0),
        dt_steam_evaporated_gpm=results.get('dt_steam_evaporated_gpm', 0),
        dt_heat_from_smelt_btu_hr=results.get('dt_heat_from_smelt_btu_hr', 0),
        dt_heat_to_warm_liquor_btu_hr=results.get('dt_heat_to_warm_liquor_btu_hr', 0),
        dt_net_heat_for_steam_btu_hr=results.get('dt_net_heat_for_steam_btu_hr', 0),
        ww_flow_solved_gpm=results.get('ww_flow_solved_gpm', 0),
        dregs_filtrate_gpm=results.get('dregs_filtrate_gpm', 0),
    )


@router.post("/calculate", response_model=CalculationResponse)
def calculate(request: CalculationRequest):
    engine_inputs = request.to_engine_inputs()
    try:
        results = run_calculations(engine_inputs)
    except Exception as e:
        logger.exception("Engine error in /calculate")
        raise HTTPException(status_code=422, detail=f"Calculation failed: {e}")
    return _build_response(results, engine_inputs)


def _coerce_overrides(overrides: Dict[str, Any], base_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw override dicts to engine-compatible objects where needed."""
    from ...engine.mill_profile import FiberlineConfig, RecoveryBoilerConfig, DissolvingTankConfig, get_mill_config
    result = dict(overrides)
    needs_mill = ('fiberlines' in result and result['fiberlines']) or \
                 ('recovery_boilers' in result and result['recovery_boilers'])
    mill = get_mill_config() if needs_mill else None

    # Fiberlines: convert plain dicts to FiberlineConfig objects
    if 'fiberlines' in result and result['fiberlines']:
        fl_map = {fl.id: fl for fl in mill.fiberlines}
        configs = []
        for fl_dict in result['fiberlines']:
            fl_id = fl_dict.get('id', '') if isinstance(fl_dict, dict) else fl_dict.id
            mill_fl = fl_map.get(fl_id)
            if mill_fl:
                defaults = dict(mill_fl.defaults)
                if isinstance(fl_dict, dict):
                    for k in ('production_bdt_day', 'yield_pct', 'ea_pct', 'gl_ea_pct'):
                        if k in fl_dict and fl_dict[k] is not None:
                            defaults[k] = fl_dict[k]
                configs.append(FiberlineConfig(
                    id=mill_fl.id, name=mill_fl.name, type=mill_fl.type,
                    cooking_type=mill_fl.cooking_type,
                    uses_gl_charge=mill_fl.uses_gl_charge,
                    defaults=defaults,
                ))
            elif not isinstance(fl_dict, dict):
                configs.append(fl_dict)  # already a FiberlineConfig
        result['fiberlines'] = configs

    # Recovery boilers: convert plain dicts to RecoveryBoilerConfig objects
    if 'recovery_boilers' in result and result['recovery_boilers']:
        rb_map = {rb.id: rb for rb in mill.recovery_boilers}
        rb_configs = []
        for rb_dict in result['recovery_boilers']:
            rb_id = rb_dict.get('id', '') if isinstance(rb_dict, dict) else rb_dict.id
            mill_rb = rb_map.get(rb_id)
            if mill_rb:
                defaults = dict(mill_rb.defaults)
                if isinstance(rb_dict, dict):
                    for k in ('bl_flow_gpm', 'bl_tds_pct', 'bl_temp_f',
                              'reduction_eff_pct', 'ash_recycled_pct', 'saltcake_flow_lb_hr'):
                        if k in rb_dict and rb_dict[k] is not None:
                            defaults[k] = rb_dict[k]
                rb_configs.append(RecoveryBoilerConfig(
                    id=mill_rb.id, name=mill_rb.name,
                    paired_dt_id=mill_rb.paired_dt_id,
                    defaults=defaults,
                ))
            elif not isinstance(rb_dict, dict):
                rb_configs.append(rb_dict)
        result['recovery_boilers'] = rb_configs

    return result


@router.post("/calculate/what-if", response_model=WhatIfResponse)
def calculate_what_if(request: WhatIfRequest):
    base_inputs = request.base.to_engine_inputs()
    try:
        base_results = run_calculations(base_inputs)
    except Exception as e:
        logger.exception("Engine error in /calculate/what-if (base)")
        raise HTTPException(status_code=422, detail=f"Base calculation failed: {e}")

    scenario_inputs = {**base_inputs, **_coerce_overrides(request.overrides, base_inputs)}
    try:
        scenario_results = run_calculations(scenario_inputs)
    except Exception as e:
        logger.exception("Engine error in /calculate/what-if (scenario)")
        raise HTTPException(status_code=422, detail=f"Scenario calculation failed: {e}")

    deltas = {}
    for key in ['final_sulfidity_pct', 'nash_dry_lbs_hr', 'naoh_dry_lbs_hr',
                'smelt_sulfidity_pct', 'current_sulfidity_pct', 'latent_sulfidity_pct']:
        b = base_results.get(key, 0)
        s = scenario_results.get(key, 0)
        deltas[key] = round(s - b, 4)

    return WhatIfResponse(
        base_results=_build_response(base_results, base_inputs),
        scenario_results=_build_response(scenario_results, scenario_inputs),
        deltas=deltas,
    )


@router.post("/calculate/sensitivity", response_model=SensitivityResponse)
def calculate_sensitivity(request: CalculationRequest):
    engine_inputs = request.to_engine_inputs()
    try:
        results = run_sensitivity_analysis(engine_inputs)
    except Exception as e:
        logger.exception("Engine error in /calculate/sensitivity")
        raise HTTPException(status_code=422, detail=f"Sensitivity analysis failed: {e}")
    return SensitivityResponse(items=[
        SensitivityItem(
            parameter=r.parameter,
            description=r.description,
            base_value=r.base_value,
            perturbed_value=r.perturbed_value,
            outputs=r.outputs,
        ) for r in results
    ])


@router.get("/mill-config")
async def get_config():
    """Return mill configuration including fiberlines, RBs, DTs, tanks, and defaults."""
    config = get_mill_config()
    return {
        "mill_name": config.mill_name,
        "makeup_chemical": config.makeup_chemical,
        "liquor_unit": config.liquor_unit,
        "fiberlines": [
            {
                "id": fl.id,
                "name": fl.name,
                "type": fl.type,
                "cooking_type": fl.cooking_type,
                "uses_gl_charge": fl.uses_gl_charge,
                "defaults": fl.defaults,
            }
            for fl in config.fiberlines
        ],
        "recovery_boilers": [
            {
                "id": rb.id,
                "name": rb.name,
                "paired_dt_id": rb.paired_dt_id,
                "defaults": rb.defaults,
            }
            for rb in config.recovery_boilers
        ],
        "dissolving_tanks": [
            {
                "id": dt.id,
                "name": dt.name,
                "paired_rb_id": dt.paired_rb_id,
                "defaults": dt.defaults,
            }
            for dt in config.dissolving_tanks
        ],
        "tanks": config.tanks,
        "defaults": config.defaults,
    }
