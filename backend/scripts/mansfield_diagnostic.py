"""
Mansfield Diagnostic: Compare config defaults → engine output → WinGEMS targets.
WinGEMS targets: NaSH dry = 1762 lb/hr, NaOH dry = 4634 lb/hr
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.engine.orchestrator import run_calculations
from app.engine.constants import DEFAULTS
from app.engine.mill_profile import load_mill_config

# ── Load Mansfield config ──
config = load_mill_config("mansfield")
print(f"Mill: {config.mill_name}")
print(f"Fiberlines: {[f.id for f in config.fiberlines]}")
print(f"Recovery Boilers: {[rb.id for rb in config.recovery_boilers]}")
print(f"Dissolving Tanks: {[dt.id for dt in config.dissolving_tanks]}")
print(f"Makeup: {config.makeup_chemical}")

# ── Build engine inputs from Mansfield config ──
# Start with Pine Hill DEFAULTS, then overlay Mansfield config defaults
inputs = dict(DEFAULTS)

# Override with Mansfield config defaults
for k, v in config.defaults.items():
    if not isinstance(v, (dict, list)):  # skip nested objects like tank_levels
        inputs[k] = v

# Set Mansfield fiberlines, RBs, DTs
inputs['fiberlines'] = config.fiberlines
inputs['recovery_boilers'] = config.recovery_boilers
inputs['dissolving_tanks'] = config.dissolving_tanks
inputs['makeup_chemical'] = config.makeup_chemical

# ── Print key inputs ──
print("\n" + "="*70)
print("KEY INPUTS (Mansfield config)")
print("="*70)

input_keys = [
    ('target_sulfidity_pct', '%'),
    ('causticity_pct', '%'),
    ('bl_na_pct', '% d.s.'),
    ('bl_s_pct', '% d.s.'),
    ('bl_k_pct', '% d.s.'),
    ('bl_flow_gpm', 'gpm'),
    ('bl_tds_pct', '%'),
    ('bl_temp_f', '°F'),
    ('wl_tta', 'g/L'),
    ('wl_ea', 'g/L'),
    ('wl_aa', 'g/L'),
    ('gl_tta', 'g/L'),
    ('gl_ea', 'g/L'),
    ('gl_aa', 'g/L'),
    ('cto_tpd', 'TPD'),
    ('cto_h2so4_per_ton', 'lb/ton'),
    ('cto_naoh_per_ton', 'lb/ton'),
    ('cooking_wl_sulfidity', 'fraction'),
    ('lime_charge_ratio', 'molar'),
    ('cao_in_lime_pct', '%'),
    ('lime_temp_f', '°F'),
    ('slaker_temp_f', '°F'),
    ('wlc_underflow_solids_pct', 'fraction'),
    ('wlc_mud_density', 'SG'),
    ('intrusion_water_gpm', 'gpm'),
    ('dilution_water_gpm', 'gpm'),
    ('dregs_lb_bdt', 'lb/BDT'),
    ('grits_lb_bdt', 'lb/BDT'),
    ('grits_loss_pct', '%'),
    ('target_sbl_tds_pct', '%'),
    ('ww_flow_gpm', 'gpm'),
    ('ww_tta_lb_ft3', 'lb/ft³'),
    ('ww_sulfidity', 'fraction'),
    ('shower_flow_gpm', 'gpm'),
    ('smelt_density_lb_ft3', 'lb/ft³'),
    ('gl_target_tta_lb_ft3', 'lb/ft³'),
]

for key, unit in input_keys:
    pine_hill = DEFAULTS.get(key, 'N/A')
    mansfield = inputs.get(key, 'N/A')
    diff = ""
    if isinstance(pine_hill, (int, float)) and isinstance(mansfield, (int, float)):
        if pine_hill != 0:
            pct = (mansfield - pine_hill) / pine_hill * 100
            if abs(pct) > 0.1:
                diff = f"  ({pct:+.1f}%)"
    print(f"  {key:35s} = {str(mansfield):>12s} {unit:10s}  [PH: {str(pine_hill):>10s}]{diff}")

# Fiberline details
print("\nFIBERLINES:")
for fl in config.fiberlines:
    d = fl.defaults
    print(f"  {fl.id:20s}: {d['production_bdt_day']:>8.1f} BDT/d, yield={d['yield_pct']:.4f}, "
          f"ea={d['ea_pct']:.4f}, moisture={d.get('wood_moisture', 'N/A')}")
    if fl.uses_gl_charge:
        print(f"    → GL charge: ea_pct={d.get('gl_ea_pct', 'N/A')}, gl_wl_ratio={d.get('gl_wl_ratio', 'N/A')}")

total_prod = sum(fl.defaults['production_bdt_day'] for fl in config.fiberlines)
print(f"  TOTAL PRODUCTION: {total_prod:.1f} BDT/day")

# RB details
print("\nRECOVERY BOILERS:")
for rb in config.recovery_boilers:
    d = rb.defaults
    print(f"  {rb.id}: flow={d['bl_flow_gpm']} gpm, TDS={d['bl_tds_pct']}%, "
          f"RE={d['reduction_eff_pct']}%, ash={d['ash_recycled_pct']}, saltcake={d['saltcake_flow_lb_hr']}")

# Loss table summary
s_total = sum(inputs.get(f'loss_{src}_s', 0) for src in [
    'pulp_washable_soda', 'pulp_bound_soda', 'pulp_mill_spills', 'evap_spill',
    'rb_ash', 'rb_stack', 'dregs_filter', 'grits', 'weak_wash_overflow', 'ncg',
    'recaust_spill', 'rb_dump_tank', 'kiln_scrubber', 'truck_out_gl', 'unaccounted'])
na_total = sum(inputs.get(f'loss_{src}_na', 0) for src in [
    'pulp_washable_soda', 'pulp_bound_soda', 'pulp_mill_spills', 'evap_spill',
    'rb_ash', 'rb_stack', 'dregs_filter', 'grits', 'weak_wash_overflow', 'ncg',
    'recaust_spill', 'rb_dump_tank', 'kiln_scrubber', 'truck_out_gl', 'unaccounted'])
print(f"\nLOSS TABLE TOTALS: S={s_total:.2f} lb/BDT, Na={na_total:.2f} lb Na₂O/BDT")

# ── RUN ENGINE ──
print("\n" + "="*70)
print("RUNNING MANSFIELD ENGINE...")
print("="*70)

results = run_calculations(inputs)

# ── KEY OUTPUTS ──
print("\n" + "="*70)
print("KEY OUTPUTS vs WinGEMS TARGETS")
print("="*70)

wingems = {
    'nash_dry_lbs_hr': 1762.0,
    'naoh_dry_lbs_hr': 4634.0,
}

output_keys = [
    ('final_sulfidity_pct', '%', None),
    ('nash_dry_lbs_hr', 'lb/hr', 1762.0),
    ('naoh_dry_lbs_hr', 'lb/hr', 4634.0),
    ('smelt_sulfidity_pct', '%', None),
    ('total_wl_demand_gpm', 'gpm', None),
    ('total_production_bdt_day', 'BDT/d', None),
    ('secant_converged', '', None),
    ('outer_converged', '', None),
    ('gl_flow_to_slaker_gpm', 'gpm', None),
    ('final_wl_tta_g_L', 'g/L', None),
    ('final_wl_na2s_g_L', 'g/L', None),
    ('final_wl_naoh_g_L', 'g/L', None),
    ('final_wl_ea_g_L', 'g/L', None),
    ('final_wl_sulfidity_pct', '%', None),
    ('gl_sulfidity', '', None),
    ('bl_na_pct_used', '%', None),
    ('bl_s_pct_used', '%', None),
    ('s_retention_strong', '', None),
    ('total_s_losses_lb_bdt', 'lb/BDT', None),
    ('total_na_losses_na2o_lb_bdt', 'lb Na₂O/BDT', None),
    ('na2so4_dead_load_na2o_lb_hr', 'lb Na₂O/hr', None),
]

for key, unit, target in output_keys:
    val = results.get(key, 'N/A')
    target_str = ""
    if target is not None and isinstance(val, (int, float)):
        gap = (val - target) / target * 100
        target_str = f"  [WinGEMS: {target:.0f}, gap: {gap:+.1f}%]"
    if isinstance(val, float):
        print(f"  {key:40s} = {val:>12.4f} {unit}{target_str}")
    else:
        print(f"  {key:40s} = {str(val):>12s} {unit}{target_str}")

# Per-fiberline results
print("\nPER-FIBERLINE WL DEMAND:")
fl_ids = results.get('fiberline_ids', [])
for fid in fl_ids:
    demand = results.get(f'{fid}_wl_demand_gpm', 0)
    print(f"  {fid:20s}: {demand:.2f} gpm")

# Per-RB results
print("\nPER-RB RESULTS:")
rb_ids = results.get('recovery_boiler_ids', [])
for rbid in rb_ids:
    sulf = results.get(f'{rbid}_smelt_sulfidity_pct', 0)
    re = results.get(f'{rbid}_reduction_eff_pct', 0)
    print(f"  {rbid}: smelt_sulf={sulf:.2f}%, RE={re:.2f}%")

# NaSH / NaOH per BDT
nash_per_bdt = results.get('nash_dry_lbs_hr', 0) * 24 / total_prod if total_prod > 0 else 0
naoh_per_bdt = results.get('naoh_dry_lbs_hr', 0) * 24 / total_prod if total_prod > 0 else 0
print(f"\nPER-BDT RATES:")
print(f"  NaSH: {nash_per_bdt:.2f} lb/BDT")
print(f"  NaOH: {naoh_per_bdt:.2f} lb/BDT")
if total_prod > 0:
    print(f"  WinGEMS NaSH: {1762*24/total_prod:.2f} lb/BDT")
    print(f"  WinGEMS NaOH: {4634*24/total_prod:.2f} lb/BDT")

# Intermediate values for debugging
print("\n" + "="*70)
print("INTERMEDIATE VALUES (debug)")
print("="*70)
debug_keys = [
    'cto_s_lb_hr', 'cto_na_lb_hr', 'cto_naoh_na_return_lb_hr',
    's_deficit_element_lb_hr', 'na_deficit_for_losses_lb_hr',
    'naoh_for_losses_lbs_hr', 'naoh_for_ea_demand_lbs_hr',
    'na_from_nash', 'na_from_naoh',
    'total_s_losses_lb_hr', 'total_na_losses_na2o_lb_hr',
    'saltcake_na_na2o_lb_hr', 'saltcake_s_lb_hr',
]
for key in debug_keys:
    val = results.get(key, 'N/A')
    if isinstance(val, float):
        print(f"  {key:40s} = {val:>12.4f}")
    else:
        print(f"  {key:40s} = {str(val):>12s}")
