import type { CalculationRequest, TankLevels, LiquorAnalysis, RecoveryBoilerInputs, LossTable } from "./types";

export const DEFAULT_TANK_LEVELS: TankLevels = {
  wlc_1: 10.2,
  wlc_2: 13.0,
  gl_1: 11.1,
  gl_2: 10.8,
  dump_tank: 30.3,
  wbl_1: 34.4,
  wbl_2: 32.8,
  cssc_weak: 36.4,
  tank_50pct: 18.4,
  tank_55pct_1: 18.0,
  tank_55pct_2: 1.0,
  tank_65pct: 39.4,
};

// WL/GL analysis defaults in lb/ft³ (DCS units)
// Converted to g/L before sending to backend: g/L = lb/ft³ × 16.01846
export const DEFAULT_WL_ANALYSIS: LiquorAnalysis = {
  tta: 7.3321,
  ea: 5.3682,
  aa: 6.4463,
};

export const DEFAULT_GL_ANALYSIS: LiquorAnalysis = {
  tta: 7.3353,
  ea: 1.7305,
  aa: 2.7949,
};

export const DEFAULT_RB_INPUTS: RecoveryBoilerInputs = {
  bl_flow_gpm: 340.53,
  bl_tds_pct: 69.1,
  bl_temp_f: 253.5,
  reduction_eff_pct: 95.0,
  ash_recycled_pct: 0.07,
  saltcake_flow_lb_hr: 2227.0,
};

export const DEFAULT_LOSS_TABLE: LossTable = {
  pulp_washable_soda: { s_lb_bdt: 3.0, na_lb_bdt: 18.5 },
  pulp_bound_soda: { s_lb_bdt: 0.0, na_lb_bdt: 7.4 },
  pulp_mill_spills: { s_lb_bdt: 0.0, na_lb_bdt: 0.3 },
  evap_spill: { s_lb_bdt: 2.4, na_lb_bdt: 5.2 },
  rb_ash: { s_lb_bdt: 1.3, na_lb_bdt: 2.8 },
  rb_stack: { s_lb_bdt: 0.3, na_lb_bdt: 0.8 },
  dregs_filter: { s_lb_bdt: 0.4, na_lb_bdt: 2.4 },
  grits: { s_lb_bdt: 0.2, na_lb_bdt: 1.5 },
  weak_wash_overflow: { s_lb_bdt: 0.1, na_lb_bdt: 0.7 },
  ncg: { s_lb_bdt: 8.5, na_lb_bdt: 1.0 },
  recaust_spill: { s_lb_bdt: 0.4, na_lb_bdt: 2.2 },
  truck_out_gl: { s_lb_bdt: 0.0, na_lb_bdt: 0.0 },
  unaccounted: { s_lb_bdt: 0.0, na_lb_bdt: 0.0 },
};

export const DEFAULT_INPUTS: CalculationRequest = {
  tank_levels: DEFAULT_TANK_LEVELS,
  wl_analysis: DEFAULT_WL_ANALYSIS,
  gl_analysis: DEFAULT_GL_ANALYSIS,
  bl_na_pct: 19.39,
  bl_s_pct: 4.01,
  bl_k_pct: 1.58,
  recovery_boiler: DEFAULT_RB_INPUTS,
  cooking_wl_sulfidity: 0.283,
  // V2: Config-driven fiberlines
  fiberlines: [
    {
      id: "pine",
      production_bdt_day: 1250.69,
      yield_pct: 0.5694,
      ea_pct: 0.122,
    },
    {
      id: "semichem",
      production_bdt_day: 636.854,
      yield_pct: 0.7019,
      ea_pct: 0.0365,
      gl_ea_pct: 0.017,
    },
  ],
  // Dissolving tank
  ww_flow_gpm: 625.0,
  ww_tta_lb_ft3: 1.07978,
  ww_sulfidity: 0.2550,
  shower_flow_gpm: 60.0,
  smelt_density_lb_ft3: 110.0,
  gl_target_tta_lb_ft3: 7.4,
  gl_causticity: 0.1016,
  // Slaker / causticizer
  causticity_pct: 81.0,
  lime_charge_ratio: 0.85,
  cao_in_lime_pct: 87.53,
  caco3_in_lime_pct: 1.96,
  inerts_in_lime_pct: 9.46,
  grits_loss_pct: 1.0,
  lime_temp_f: 1100.0,
  slaker_temp_f: 210.5,
  // WLC
  intrusion_water_gpm: 28.0,
  dilution_water_gpm: 23.856,
  wlc_underflow_solids_pct: 0.4097,
  wlc_mud_density: 1.33,
  // GL clarifier
  dregs_lb_bdt: 8.158,
  glc_underflow_solids_pct: 0.077,
  grits_lb_bdt: 8.53,
  grits_solids_pct: 0.40,
  // CTO / Setpoints
  cto_h2so4_per_ton: 360.0,
  cto_tpd: 26.68,
  target_sulfidity_pct: 29.4,
  // Makeup
  nash_concentration: 0.40,
  naoh_concentration: 0.50,
  nash_density: 1.29,
  naoh_density: 1.52,
  loss_table: DEFAULT_LOSS_TABLE,
};
