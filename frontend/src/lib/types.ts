export interface TankLevels {
  wlc_1: number;
  wlc_2: number;
  gl_1: number;
  gl_2: number;
  dump_tank: number;
  wbl_1: number;
  wbl_2: number;
  cssc_weak: number;
  tank_50pct: number;
  tank_55pct_1: number;
  tank_55pct_2: number;
  tank_65pct: number;
}

export interface LiquorAnalysis {
  tta: number;
  ea: number;
  aa: number;
}

export interface RecoveryBoilerInputs {
  bl_flow_gpm: number;
  bl_tds_pct: number;
  bl_temp_f: number;
  reduction_eff_pct: number;
  ash_recycled_pct: number;
  saltcake_flow_lb_hr: number;
}

export interface LossTableSource {
  s_lb_bdt: number;
  na_lb_bdt: number;
}

export interface LossTable {
  pulp_washable_soda: LossTableSource;
  pulp_bound_soda: LossTableSource;
  pulp_mill_spills: LossTableSource;
  evap_spill: LossTableSource;
  rb_ash: LossTableSource;
  rb_stack: LossTableSource;
  dregs_filter: LossTableSource;
  grits: LossTableSource;
  weak_wash_overflow: LossTableSource;
  ncg: LossTableSource;
  recaust_spill: LossTableSource;
  truck_out_gl: LossTableSource;
  unaccounted: LossTableSource;
}

export interface CalculationRequest {
  tank_levels?: TankLevels;
  wl_analysis?: LiquorAnalysis;
  gl_analysis?: LiquorAnalysis;
  bl_na_pct: number;
  bl_s_pct: number;
  bl_k_pct: number;
  recovery_boiler?: RecoveryBoilerInputs;
  batch_production_bdt_day: number;
  cont_production_bdt_day: number;
  cooking_wl_sulfidity: number;
  // Fiberline parameters
  semichem_yield_pct: number;
  pine_yield_pct: number;
  semichem_ea_pct: number;
  pine_ea_pct: number;
  // Semichem GL charge (Excel 3_Chem G5-G17)
  semichem_gl_ea_pct: number;
  // Dissolving tank (Excel 2_RB I43-I75)
  ww_flow_gpm: number;
  ww_tta_lb_ft3: number;
  ww_sulfidity: number;
  shower_flow_gpm: number;
  smelt_density_lb_ft3: number;
  gl_target_tta_lb_ft3: number;
  gl_causticity: number;
  // Slaker / causticizer
  causticity_pct: number;
  lime_charge_ratio: number;
  cao_in_lime_pct: number;
  caco3_in_lime_pct: number;
  inerts_in_lime_pct: number;
  grits_loss_pct: number;
  lime_temp_f: number;
  slaker_temp_f: number;
  // WLC
  intrusion_water_gpm: number;
  dilution_water_gpm: number;
  wlc_underflow_solids_pct: number;
  wlc_mud_density: number;
  // GL clarifier (3_Chem B62-B80) — dregs/grits flows are CALCULATED
  dregs_lb_bdt: number;
  glc_underflow_solids_pct: number;
  grits_lb_bdt: number;
  grits_solids_pct: number;
  // CTO
  cto_h2so4_per_ton: number;
  cto_tpd: number;
  // Setpoints
  target_sulfidity_pct: number;
  // Makeup
  nash_concentration: number;
  naoh_concentration: number;
  nash_density: number;
  naoh_density: number;
  // Unified loss table
  loss_table?: LossTable;
  s_deficit_lbs_hr?: number;
  // NaSH/NaOH overrides (bypass Secant and dual-constraint)
  nash_dry_override_lb_hr?: number;
  naoh_dry_override_lb_hr?: number;
  // V2: Config-driven fiberline inputs (when present, backend uses V2 path)
  fiberlines?: Array<{
    id: string;
    production_bdt_day: number;
    yield_pct: number;
    ea_pct: number;
    gl_ea_pct?: number;
  }>;
}

export interface SulfidityOutput {
  current_pct: number;
  latent_pct: number;
  final_pct: number;
  smelt_pct: number;
  trend: string;
}

export interface MakeupOutput {
  nash_dry_lb_hr: number;
  nash_solution_lb_hr: number;
  nash_gpm: number;
  naoh_dry_lb_hr: number;
  naoh_solution_lb_hr: number;
  naoh_gpm: number;
  nash_lb_bdt_na2o: number;
  naoh_lb_bdt_na2o: number;
  saltcake_lb_bdt_na2o: number;
  // Additional fields for lb/BDT display
  saltcake_lb_hr?: number;
  nash_lb_bdt?: number;
  naoh_lb_bdt?: number;
  saltcake_lb_bdt?: number;
}

export interface RecoveryBoilerOutput {
  tta_lb_hr: number;
  active_sulfide_lb_hr: number;
  dead_load_lb_hr: number;
  na_lbs_hr: number;
  s_lbs_hr: number;
  bl_density_lb_gal: number;
  potential_na_alkali: number;
  potential_k_alkali: number;
  potential_s_alkali: number;
  dry_solids_lbs_hr: number;
  bl_na_pct_mixed: number;
  bl_s_pct_mixed: number;
  bl_s_pct_fired: number;
}

export interface InventoryOutput {
  wl_tta_tons: number;
  wl_na2s_tons: number;
  gl_tta_tons: number;
  gl_na2s_tons: number;
  bl_latent_tta_tons: number;
  bl_latent_na2s_tons: number;
}

export interface MassBalanceOutput {
  na_losses_lb_hr: number;
  na_deficit_lb_hr: number;
  total_s_losses_lb_hr: number;
  cto_s_lbs_hr: number;
  net_s_balance_lb_hr: number;
}

export interface ForwardLegOutput {
  // Pine fiberline
  pine_bl_organics_lb_hr: number;
  pine_bl_inorganic_solids_lb_hr: number;
  // Semichem fiberline
  semichem_bl_organics_lb_hr: number;
  semichem_bl_inorganic_solids_lb_hr: number;
  // CTO
  cto_na_lb_hr: number;
  cto_s_lbs_hr: number;
  // Mixed WBL
  wbl_total_flow_lb_hr: number;
  wbl_tds_pct: number;
  wbl_na_pct_ds: number;
  wbl_s_pct_ds: number;
  // SBL (after evaporator)
  sbl_flow_lb_hr: number;
  sbl_tds_pct: number;
  sbl_na_element_lb_hr: number;
  sbl_s_element_lb_hr: number;
  evaporator_water_removed_lb_hr: number;
  // RB inputs
  rb_virgin_solids_lbs_hr: number;
  rb_ash_solids_lbs_hr: number;
  bl_na_pct_used: number;
  bl_s_pct_used: number;
}

export interface UnitOperationRow {
  stage: string;
  na_lb_hr: number;
  s_lb_hr: number;
  na_pct_ds: number | null;
  s_pct_ds: number | null;
  tta_na2o_ton_hr: number | null;
  na2s_na2o_ton_hr: number | null;
  flow_gpm: number | null;
}

export interface LossDetailRow {
  source: string;
  s_lb_hr: number;
  s_lb_bdt: number;
  na2o_lb_hr: number;
  na2o_lb_bdt: number;
}

export interface ChemicalAdditionRow {
  source: string;
  na_lb_hr: number;
  s_lb_hr: number;
}

export interface GuidanceItem {
  severity: "red" | "yellow" | "green";
  category: string;
  title: string;
  description: string;
  action: string;
  impact?: string;
}

export interface WLQualityOutput {
  tta_g_L: number;
  aa_g_L: number;
  ea_g_L: number;
  na2s_g_L: number;
  tta_lb_ft3: number;
  aa_lb_ft3: number;
  ea_lb_ft3: number;
  na2s_lb_ft3: number;
  sulfidity_pct: number;
  causticity_pct: number;
  wl_flow_gpm: number;
  wl_demand_gpm: number;
}

export interface CalculationResponse {
  status: string;
  solver: { converged: boolean; iterations: number };
  sulfidity: SulfidityOutput;
  makeup: MakeupOutput;
  recovery_boiler: RecoveryBoilerOutput;
  inventory: InventoryOutput;
  mass_balance: MassBalanceOutput;
  wl_quality: WLQualityOutput;
  forward_leg: ForwardLegOutput;
  guidance: GuidanceItem[];
  production: Record<string, number>;
  intermediate: Record<string, number>;
  unit_operations: UnitOperationRow[];
  loss_table_detail: LossDetailRow[];
  chemical_additions: ChemicalAdditionRow[];
  na_losses_element_lb_hr: number;
  saltcake_na_lb_hr: number;
  saltcake_s_lb_hr: number;
  // Production totals
  total_production_bdt_day: number;
  // BL composition tracking (lab vs computed vs used)
  bl_na_pct_lab: number;
  bl_s_pct_lab: number;
  bl_na_pct_computed: number;
  bl_s_pct_computed: number;
  bl_na_pct_used: number;
  bl_s_pct_used: number;
  // DT energy balance + WW solve
  dt_steam_evaporated_lb_hr: number;
  dt_steam_evaporated_gpm: number;
  dt_heat_from_smelt_btu_hr: number;
  dt_heat_to_warm_liquor_btu_hr: number;
  dt_net_heat_for_steam_btu_hr: number;
  ww_flow_solved_gpm: number;
  dregs_filtrate_gpm: number;
  outer_loop_converged: boolean;
  outer_loop_iterations: number;
}

export interface WhatIfResponse {
  base_results: CalculationResponse;
  scenario_results: CalculationResponse;
  deltas: Record<string, number>;
}

export interface SensitivityItem {
  parameter: string;
  description: string;
  base_value: number;
  perturbed_value: number;
  outputs: Record<string, Record<string, number>>;
}

export interface SensitivityResponse {
  items: SensitivityItem[];
}

export interface Snapshot {
  id: number;
  timestamp: string;
  notes: string;
  inputs: Record<string, unknown>;
  results: Record<string, unknown>;
}

export interface TrendPointCreate {
  predicted_sulfidity_pct: number;
  smelt_sulfidity_pct: number;
  nash_dry_lb_hr: number;
  naoh_dry_lb_hr: number;
  target_sulfidity_pct: number;
}

export interface TrendPoint {
  id: number;
  mill_id: string;
  timestamp: string;
  predicted_sulfidity_pct: number;
  smelt_sulfidity_pct: number;
  nash_dry_lb_hr: number;
  naoh_dry_lb_hr: number;
  target_sulfidity_pct: number;
  lab_sulfidity_pct: number | null;
  notes: string;
}

export interface FiberlineInputState {
  production_bdt_day?: number;
  yield_pct?: number;
  ea_pct?: number;
  gl_ea_pct?: number;
}

export interface FiberlineConfig {
  id: string;
  name: string;
  type: "continuous" | "batch";
  cooking_type: "chemical" | "semichem";
  uses_gl_charge: boolean;
  defaults: {
    production_bdt_day: number;
    yield_pct: number;
    ea_pct: number;
    gl_ea_pct?: number;
    wood_moisture?: number;
  };
}

export interface MillConfig {
  mill_name: string;
  makeup_chemical: "nash" | "saltcake" | "emulsified_sulfur" | "naoh";
  fiberlines: FiberlineConfig[];
  tanks: Record<string, unknown>[];
  defaults: Record<string, number>;
}
