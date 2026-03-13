"""
Molecular weights, conversion factors, and default values.

Reference: SULFIDITY_MODEL_CORRECTED_FINAL v4.xlsx
All formulas traced and validated against Excel model.
"""

from .mill_profile import FiberlineConfig, RecoveryBoilerConfig, DissolvingTankConfig

# Molecular Weights (g/mol)
MW = {
    'Na': 22.98,
    'S': 32.065,
    'K': 39.1,
    'Na2O': 62.0,
    'Na2S': 78.05,
    'NaOH': 40.0,
    'NaSH': 56.06,
    'Na2CO3': 106.0,
    'Na2SO4': 142.04,
    'CaO': 56.08,
    'CaCO3': 100.09,
    'H2O': 18.015,
    'H2SO4': 98.079,
    'Ca(OH)2': 74.093,
}

# Conversion Factors - traced from Excel formulas
CONV = {
    # gpm * g/L -> lb/hr: (3.785 L/gal * 60 min/hr) / 453.592 g/lb = 0.5007
    'GPM_GL_TO_LB_HR': 0.5007,

    # Excel uses 0.00025 for gpm * lb/ft3 -> ton/hr:
    # gpm * lb/ft3 * 16.01 (kg/m3 per lb/ft3) * 0.00025
    # Actually: gpm * lb/ft3 * (ft3/7.48052 gal) * 60 min/hr / 2000 lb/ton
    # = gpm * lb/ft3 * 0.1336806 * 60 / 2000
    'FT3_PER_GAL': 0.1336806,   # B79 in Excel

    # Na2O to NaOH: 2*NaOH/Na2O = 80/62 = 1.2903
    'Na2O_to_NaOH': MW['NaOH'] * 2 / MW['Na2O'],

    # Na2O to Na2S: Na2S/Na2O = 78.05/62 = 1.2589
    'Na2O_to_Na2S': MW['Na2S'] / MW['Na2O'],

    # Na to Na2O: Na2O/(2*Na) = 62/(2*22.98) = 1.34899...
    'Na_to_Na2O': MW['Na2O'] / (2 * MW['Na']),

    # S to Na2O (as Na2S): Na2O/S = 62/32.065 = 1.9335
    'S_to_Na2O': MW['Na2O'] / MW['S'],

    # K to Na2O equivalent: Na2O/(2*K) = 62/(2*39.1) = 0.7928
    'K_to_Na2O': MW['Na2O'] / (2 * MW['K']),

    # NaSH to Na2O: Na2O/(2*NaSH) = 62/(2*56.06) = 0.5529
    # NaSH has 1 Na atom → contributes 0.5 mol Na2O per mol NaSH.
    # USE THIS for: Na mass balance, "lb Na2O added" display, Na deficit.
    'NaSH_to_Na2O': MW['Na2O'] / (2 * MW['NaSH']),

    # Na2S (as Na2O) per NaSH = 62/56.06 = 1.1060
    # In alkaline WL, NaSH's sulfide is tracked as Na2S (2 Na per S).
    # This factor converts NaSH → Na2S on Na2O basis for SULFIDITY calculations.
    # DO NOT use for Na mass balance or "lb Na2O added" — use NaSH_to_Na2O instead.
    'Na2O_per_NaSH': MW['Na2O'] / MW['NaSH'],

    # S fraction in NaSH: S/NaSH = 32.065/56.06 = 0.5720
    'S_in_NaSH': MW['S'] / MW['NaSH'],

    # Na fraction in NaSH: Na/NaSH = 22.98/56.06 = 0.4100 (exact)
    'Na_in_NaSH': MW['Na'] / MW['NaSH'],

    # NaOH to Na2O: Na2O/(2*NaOH) = 62/80 = 0.775
    'NaOH_to_Na2O': MW['Na2O'] / (2 * MW['NaOH']),

    # Na2SO4 to Na2O: Na2O/Na2SO4 = 62/142.04 = 0.4366
    'Na2SO4_to_Na2O': MW['Na2O'] / MW['Na2SO4'],

    # Compound mass conversion factors (Na2O basis → actual compound mass)
    # Used by fiberline BL generation to track full compound weights (incl. oxygen)
    'Na2S_to_compound': MW['Na2S'] / MW['Na2O'],          # 78.05/62 = 1.2589
    'NaOH_to_compound': 2 * MW['NaOH'] / MW['Na2O'],     # 80/62 = 1.2903
    'Na2CO3_to_compound': MW['Na2CO3'] / MW['Na2O'],      # 106/62 = 1.7097

    # S fraction in Na2SO4: S/Na2SO4 = 32.065/142.04 = 0.2258
    'S_in_Na2SO4': MW['S'] / MW['Na2SO4'],

    # lb/ft3 to g/L: 16.01846
    'LB_FT3_TO_GL': 16.01846,

    # Volume/mass conversions
    'L_to_gal': 0.264172,
    'gal_to_L': 3.78541,
    'lb_to_ton': 1 / 2000,
    'ton_to_lb': 2000,
    'kg_to_lb': 2.20462,
    'METRIC_TO_SHORT': 1.1023,

    # Slaker energy/water balance (Slaker Model sheet B31-B49)
    'KG_PER_SHORT_TON': 907.185,          # B37
    'HEAT_OF_SLAKING': 15300,             # B31 — cal/mol CaO (CaO+H2O→Ca(OH)2)
    'GL_SPECIFIC_HEAT': 0.882,            # B49 — kcal/kg/°C for green liquor
    'LIME_SPECIFIC_HEAT': 0.175,          # B32 — kcal/kg/°C for quicklime
    'STEAM_LATENT_HEAT': 538.5,           # B36 — kcal/kg at slaker temperature
    'WL_DENSITY_KG_L': 1.135,             # B76 — hardcoded WL density in Excel
}

# gal * g/L -> metric tons: 3.785 L/gal / 1e6 g/metric_ton
GAL_GL_TO_METRIC_TON = 0.000003785

# gpm * g/L -> ton/hr: 0.5007 / 2000
GPM_GL_TO_TON_HR = CONV['GPM_GL_TO_LB_HR'] / 2000

# Excel I46 conversion: gpm * lb/ft3 * 16.01 * 0.00025 = ton/hr
# 0.00025 = (ft3/gal) * 60 min/hr / 2000 lb/ton (approximate)
# Exact: 0.1336806 * 60 / 2000 = 0.004010418
GPM_LBFT3_TO_TON_HR = 0.00025  # Excel uses 0.00025 exactly

# Default Operating Parameters (Pine Hill Mill)
DEFAULTS = {
    # Targets/Setpoints
    'target_sulfidity_pct': 29.4,
    'reduction_efficiency_pct': 95.0,
    'causticity_pct': 81.0,

    # Makeup chemical properties - 0_SULF!B4-B7
    'nash_concentration': 0.40,
    'naoh_concentration': 0.50,
    'nash_density': 1.29,  # SG
    'naoh_density': 1.52,  # SG

    # BL composition — lab/inventory values for VIRGIN BL (before ash recycling)
    # The engine CALCULATES mixed Na%/S% (B21/B26) from these + ash recycling
    'bl_na_pct': 19.39,     # 1_Inv!X49 = Na% d.s. of virgin BL (65% tank)
    'bl_s_pct': 4.01,       # 1_Inv!X50 = S% d.s. of virgin BL
    'bl_k_pct': 1.58,

    # BL properties for tank inventory (different weak/strong values)
    'bl_na_pct_inv_weak': 18.87,    # Weak BL tanks (virgin solids)
    'bl_na_pct_inv_strong': 19.50,  # 65% tank (1_Inv!X49 = X58/100)
    'bl_s_pct_inv': 4.56,           # 1_Inv BL S% d.s. for weak BL tanks

    # BL to RB
    'bl_flow_gpm': 340.53,    # B3 (Liquor Flow Calc)
    'bl_tds_pct': 69.1,
    'bl_temp_f': 253.5,

    # RB ash/losses — CALCULATED from these inputs
    'ash_recycled_pct': 0.07,       # B4 = 7% ash recycled proportion

    # Saltcake — single flow input; Na/S computed from Na2SO4 chemistry
    'saltcake_flow_lb_hr': 2227.0,  # B40 = total Na2SO4 flow lb/hr

    # Fiberline configs (Pine Hill: 2 fiberlines)
    'fiberlines': [
        FiberlineConfig(
            id="pine", name="Pine", type="continuous",
            cooking_type="chemical", uses_gl_charge=False,
            defaults={
                "production_bdt_day": 1250.69,
                "yield_pct": 0.5694,
                "ea_pct": 0.122,
                "wood_moisture": 0.523,
            },
        ),
        FiberlineConfig(
            id="semichem", name="Semichem", type="batch",
            cooking_type="semichem", uses_gl_charge=True,
            defaults={
                "production_bdt_day": 636.854,
                "yield_pct": 0.7019,
                "ea_pct": 0.0365,
                "gl_ea_pct": 0.017,
                "wood_moisture": 0.461,
            },
        ),
    ],

    # Recovery boiler configs (Pine Hill: 1 RB)
    'recovery_boilers': [
        RecoveryBoilerConfig(
            id="rb1", name="Recovery Boiler", paired_dt_id="dt1",
            defaults={
                "bl_flow_gpm": 340.53,
                "bl_tds_pct": 69.1,
                "bl_temp_f": 253.5,
                "reduction_eff_pct": 95.0,
                "ash_recycled_pct": 0.07,
                "saltcake_flow_lb_hr": 2227.0,
            },
        ),
    ],

    # Dissolving tank configs (Pine Hill: 1 DT)
    'dissolving_tanks': [
        DissolvingTankConfig(
            id="dt1", name="Dissolving Tank", paired_rb_id="rb1",
            defaults={
                "ww_flow_gpm": 625.0,
                "ww_tta_lb_ft3": 1.07978,
                "ww_sulfidity": 0.2550,
                "shower_flow_gpm": 60.0,
                "smelt_density_lb_ft3": 110.0,
            },
        ),
    ],

    # WL lab analysis
    'wl_tta': 117.449,
    'wl_ea': 85.99,
    'wl_aa': 103.26,

    # GL lab analysis
    'gl_tta': 117.5,
    'gl_ea': 27.72,
    'gl_aa': 44.77,

    # ── Dissolving tank (2_RB I43-I75) ──
    'ww_flow_gpm': 625.0,            # I53 — INPUT (not calculated!)
    'ww_tta_lb_ft3': 1.07978,        # I50 — WW TTA in lb/ft3
    'ww_sulfidity': 0.2550,          # I48 — WW sulfidity fraction
    'shower_flow_gpm': 60.0,         # I54
    'smelt_density_lb_ft3': 110.0,   # I56
    'gl_target_tta_lb_ft3': 7.4,     # I49 — GL TTA target in lb/ft3
    'gl_causticity': 0.1016,         # I75 — GL causticity fraction NaOH/(NaOH+Na2CO3)

    # ── DT energy balance ──
    'smelt_temp_f': 1338.0,            # Smelt temperature entering DT (°F)
    'ww_temp_f': 180.0,               # Weak wash temperature (°F)
    'shower_temp_f': 140.0,           # Shower water temperature (°F)
    'dt_operating_temp_f': 212.0,     # DT operating temperature (°F, boiling)
    'smelt_cp_btu_lb_f': 0.223,       # Smelt specific heat (BTU/lb/°F), calibrated to ~1979 lb/hr steam
    'latent_heat_212_btu_lb': 970.0,  # Latent heat of vaporization at 212°F (BTU/lb)

    # Legacy dissolving tank fields (g/L basis, kept for API compatibility)
    'ww_tta': 17.3,              # Weak wash TTA (g Na2O/L) = 1.07978 * 16.01
    'ww_na2s': 4.41,             # Weak wash Na2S (g Na2O/L) = 17.3 * 0.255
    'gl_tta_target': 117.27,     # GL TTA target (g Na2O/L) = 7.325 * 16.01

    # (loss_factor removed — Na losses now computed from unified loss table)

    # ── CTO ──
    'cto_h2so4_per_ton': 360.0,  # C9 — lb H2SO4/T CTO
    'cto_tpd': 26.68,            # C10 — TPD

    # ── Wash water Na/S return (paper machine white water to brownstock washers) ──
    # White water carries residual Na and S back into the washing circuit.
    # Na and S concentrations are % by weight of the white water.
    # Per-fiberline wash_water_gpm is in each FiberlineConfig.defaults.
    # Pine Hill: no wash water data available → defaults to 0 gpm per fiberline.
    'wash_water_na_pct': 0.0,    # % by weight Na in wash water (0 = no WW return)
    'wash_water_s_pct': 0.0,     # % by weight S in wash water (0 = no WW return)

    # Cooking
    'cooking_wl_sulfidity': 0.283,

    # ── Slaker model ──
    'lime_charge_ratio': 0.85,      # B26 — molar CaO/Na2CO3 ratio
    'cao_in_lime_pct': 87.53,       # B14 — CaO% in lime
    'caco3_in_lime_pct': 1.96,      # B15
    'inerts_in_lime_pct': 9.46,     # B16
    'grits_loss_pct': 1.0,          # fraction of total lime lost as grits
    'lime_temp_f': 1100.0,          # G78 — lime kiln product temp
    'slaker_temp_f': 210.5,         # G79 — slaker operating temp
    'gl_temp_f': 189.0,             # B9 — GL temperature to slaker (°F)
    'slaker_volume_m3': 27.35,      # B122
    'n_causticizers': 3,            # B123
    'causticizer_volume_m3': 53.65, # B124

    # ── WLC (White Liquor Clarifier) ──
    'wlc_underflow_solids_pct': 0.4097,  # P90 — solids fraction in underflow
    'wlc_mud_density': 1.33,             # P92 — mud density SG
    'intrusion_water_gpm': 28.0,         # U86
    'dilution_water_gpm': 23.856,        # Q73

    # ── GL Clarifier (3_Chem B62-B80) — CALCULATED underflows ──
    'dregs_lb_bdt': 8.158,              # B63 — GL dregs lb/BDT pulp (input)
    'glc_underflow_solids_pct': 0.077,  # B65 — GLC underflow solids fraction (7.70%)
    'grits_lb_bdt': 8.53,              # B73 — Grits losses lb/BDT (input)
    'grits_solids_pct': 0.40,          # B75 — Grits solids fraction (40%)

    # Forward leg: fiberline BL generation
    # DEPRECATED: s_loss_digester_pct is superseded by loss_ncg_s in the unified loss table.
    # When loss_ncg_s > 0, it provides exact S loss from the loss table instead of this
    # arbitrary 2% estimate. Set to 0.0 to ensure loss table value is used.
    's_loss_digester_pct': 0.0,           # Deprecated: Use loss_ncg_s from loss table instead
    'target_sbl_tds_pct': 69.1,          # Evaporator target TDS% (matches bl_tds_pct)

    # Unified soda & sulfur loss table (lb/BDT pulp) — 13 sources × S + Na2O
    # Fiberline
    'loss_pulp_washable_soda_s': 3.0,  'loss_pulp_washable_soda_na': 18.5,
    'loss_pulp_bound_soda_s': 0.0,     'loss_pulp_bound_soda_na': 7.4,
    'loss_pulp_mill_spills_s': 0.0,    'loss_pulp_mill_spills_na': 0.3,
    # Evaporator
    'loss_evap_spill_s': 2.4,          'loss_evap_spill_na': 5.2,
    # Recovery Boiler
    'loss_rb_ash_s': 1.3,              'loss_rb_ash_na': 2.8,
    'loss_rb_stack_s': 0.3,            'loss_rb_stack_na': 0.8,
    # Recausticizing
    'loss_dregs_filter_s': 0.4,        'loss_dregs_filter_na': 2.4,
    'loss_grits_s': 0.2,               'loss_grits_na': 1.5,
    'loss_weak_wash_overflow_s': 0.1,  'loss_weak_wash_overflow_na': 0.7,
    'loss_ncg_s': 8.5,                 'loss_ncg_na': 1.0,
    'loss_recaust_spill_s': 0.4,       'loss_recaust_spill_na': 2.2,
    'loss_rb_dump_tank_s': 0.0,        'loss_rb_dump_tank_na': 0.0,
    'loss_kiln_scrubber_s': 0.0,       'loss_kiln_scrubber_na': 0.0,
    # Other
    'loss_truck_out_gl_s': 0.0,        'loss_truck_out_gl_na': 0.0,
    'loss_unaccounted_s': 0.0,         'loss_unaccounted_na': 0.0,

    # Tank levels (Pine Hill defaults)
    'tank_levels': {
        'wlc_1': 10.2,
        'wlc_2': 13.0,
        'gl_1': 11.1,
        'gl_2': 10.8,
        'dump_tank': 30.3,
        'wbl_1': 34.4,
        'wbl_2': 32.8,
        'cssc_weak': 36.4,
        'tank_50pct': 18.4,
        'tank_55pct_1': 18.0,
        'tank_55pct_2': 1.0,
        'tank_65pct': 39.4,
    },

    # BL tank properties
    'bl_tank_tds': {
        'wbl_1': 19.23, 'wbl_2': 19.23, 'cssc_weak': 19.23,
        'tank_50pct': 50.0, 'tank_55pct_1': 55.0,
        'tank_55pct_2': 50.0, 'tank_65pct': 69.1,
    },
    'bl_tank_temp': {
        'wbl_1': 205.0, 'wbl_2': 205.0, 'cssc_weak': 205.0,
        'tank_50pct': 205.0, 'tank_55pct_1': 205.0,
        'tank_55pct_2': 205.0, 'tank_65pct': 205.0,
    },
}
