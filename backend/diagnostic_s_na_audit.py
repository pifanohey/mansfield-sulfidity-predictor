"""
Diagnostic: trace every S and Na entry/exit point through the Kraft loop.

Identifies where each loss source IS or ISN'T physically modeled,
and quantifies any accounting gaps.
"""
import sys
sys.path.insert(0, '.')

from app.engine.orchestrator import run_calculations
from app.engine.constants import MW, CONV, DEFAULTS
from app.engine.s_retention import calculate_s_losses_detailed, SLossBreakdown

# Run with defaults (outer loop converges)
inputs = {}
results = run_calculations(inputs)

total_prod = sum(fl.production_bdt_day for fl in DEFAULTS['fiberlines'])
saltcake_flow = DEFAULTS['saltcake_flow_lb_hr']

print("=" * 80)
print("S / Na AUDIT — Full Loop Trace (default inputs)")
print(f"Total production: {total_prod:.1f} BDT/day")
print("=" * 80)

# ──────────────────────────────────────────────────────────────────────────────
# 1. S ADDITIONS (entering the loop)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SECTION 1: S ADDITIONS (element lb/hr)")
print("=" * 80)

nash_dry = results['nash_dry_lbs_hr']
naoh_dry = results['naoh_dry_lbs_hr']

nash_s = nash_dry * MW['S'] / MW['NaSH']
nash_na = nash_dry * MW['Na'] / MW['NaSH']
naoh_na = naoh_dry * MW['Na'] / MW['NaOH']
saltcake_s = saltcake_flow * MW['S'] / MW['Na2SO4']
saltcake_na = saltcake_flow * 2 * MW['Na'] / MW['Na2SO4']
cto_s = results['cto_s_lbs_hr']
cto_na = results['cto_na_lb_hr']

print(f"  NaSH:     Na = {nash_na:8.1f}   S = {nash_s:8.1f}  (nash_dry = {nash_dry:.1f} lb/hr)")
print(f"  NaOH:     Na = {naoh_na:8.1f}   S = {0:8.1f}  (naoh_dry = {naoh_dry:.1f} lb/hr)")
print(f"  Saltcake: Na = {saltcake_na:8.1f}   S = {saltcake_s:8.1f}  (flow = {saltcake_flow:.0f} lb Na2SO4/hr)")
print(f"  CTO:      Na = {cto_na:8.1f}   S = {cto_s:8.1f}")
total_add_na = nash_na + naoh_na + saltcake_na + cto_na
total_add_s = nash_s + saltcake_s + cto_s
print(f"  ─────────────────────────────────────────")
print(f"  TOTAL:    Na = {total_add_na:8.1f}   S = {total_add_s:8.1f}")

# ──────────────────────────────────────────────────────────────────────────────
# 2. S LOSSES (the 8 declared sources)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SECTION 2: DECLARED S LOSSES (from input assumptions)")
print("=" * 80)

loss_breakdown = SLossBreakdown()
s_detail = calculate_s_losses_detailed(total_prod, loss_breakdown)

sources = [
    ('Evaporator Spill', 'evap_spill_loss', loss_breakdown.evap_spill_loss),
    ('RB Ash Purge',     'rb_ash_purge',     loss_breakdown.rb_ash_purge),
    ('RB Stack',         'rb_stack',          loss_breakdown.rb_stack),
    ('Dregs Filter',     'dregs_filter',      loss_breakdown.dregs_filter),
    ('Grits',            'grits',             loss_breakdown.grits),
    ('Weak Wash Overflow','weak_wash_overflow',loss_breakdown.weak_wash_overflow),
    ('NCG/Turpentine',   'ncg',              loss_breakdown.ncg),
    ('Recaust Spill',    'recaust_spill',     loss_breakdown.recaust_spill),
]

total_s_loss_lb_hr = 0
for name, key, lb_bdt in sources:
    lb_hr = s_detail[key]
    total_s_loss_lb_hr += lb_hr
    print(f"  {name:25s}  {lb_bdt:6.3f} lb/BDT  →  {lb_hr:8.1f} lb S/hr")

print(f"  ─────────────────────────────────────────────────────────")
print(f"  TOTAL                     {loss_breakdown.total_lb_bdt:6.3f} lb/BDT  →  {total_s_loss_lb_hr:8.1f} lb S/hr")

# Na losses
na_losses_na2o = results['na_losses_lbs_hr']
na_losses_element = results['na_losses_element_lb_hr']
print(f"\n  Na losses: {na_losses_na2o:.1f} lb Na2O/hr = {na_losses_element:.1f} lb Na/hr (element)")

# ──────────────────────────────────────────────────────────────────────────────
# 3. NET BALANCE
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SECTION 3: NET BALANCE (Additions - Losses)")
print("=" * 80)
net_na = total_add_na - na_losses_element
net_s = total_add_s - total_s_loss_lb_hr
print(f"  Na: {total_add_na:8.1f} (in) - {na_losses_element:8.1f} (out) = {net_na:+8.1f} {'SURPLUS' if net_na >= 0 else 'DEFICIT'}")
print(f"  S:  {total_add_s:8.1f} (in) - {total_s_loss_lb_hr:8.1f} (out) = {net_s:+8.1f} {'SURPLUS' if net_s >= 0 else 'DEFICIT'}")
print(f"\n  Engine net_s_balance_lb_hr = {results['net_s_balance_lb_hr']:.1f}")
print(f"    (Note: engine value excludes NaSH S from additions)")

# ──────────────────────────────────────────────────────────────────────────────
# 4. PHYSICAL MODEL — WHERE IS EACH LOSS ACTUALLY MODELED?
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SECTION 4: PHYSICAL MODEL — HOW EACH LOSS IS HANDLED")
print("=" * 80)

# S retention factors
s_ret_strong = results.get('s_retention_strong', 0)
s_ret_weak = results.get('s_retention_weak', 0)
print(f"\n  S retention strong (RB only): {s_ret_strong:.4f}")
print(f"  S retention weak (all losses): {s_ret_weak:.4f}")

# RB: S entering vs S in smelt
rb_s_in = results.get('rb_s_lbs_hr', 0)   # Total S entering RB (element)
rb_potential_s = results.get('rb_potential_s_alkali', 0)  # As Na2O
rb_active_sulfide = results.get('rb_active_sulfide', 0)  # As Na2O
rb_dead_load = results.get('rb_dead_load', 0)  # As Na2O (unreduced Na2SO4)
rb_ash_s_na2o = results.get('rb_ash_s_na2o', 0)

print(f"\n  ── Recovery Boiler ──")
print(f"  S entering RB (element):     {rb_s_in:8.1f} lb/hr")
print(f"  S potential alkali (Na2O):    {rb_potential_s:8.1f} lb/hr")
print(f"  Active sulfide (Na2O):        {rb_active_sulfide:8.1f} lb/hr  (= pot_s × RE × s_ret_strong - ash_s)")
print(f"  Dead load (Na2O):             {rb_dead_load:8.1f} lb/hr  (= pot_s × (1-RE), unreduced)")
print(f"  Ash S (Na2O):                 {rb_ash_s_na2o:8.1f} lb/hr  (recycled back)")
s_lost_rb_na2o = rb_potential_s * 0.95 * (1 - s_ret_strong)
print(f"  S lost at RB (Na2O):          {s_lost_rb_na2o:8.1f} lb/hr  (= pot_s × RE × (1-s_ret_strong))")
s_lost_rb_element = s_lost_rb_na2o * MW['S'] / MW['Na2O']
rb_ash_s_lb_hr = s_detail['rb_ash_purge']
rb_stack_s_lb_hr = s_detail['rb_stack']
print(f"  S lost at RB (element):       {s_lost_rb_element:8.1f} lb/hr")
print(f"  Declared RB losses (element): {rb_ash_s_lb_hr + rb_stack_s_lb_hr:8.1f} lb/hr  (ash={rb_ash_s_lb_hr:.1f} + stack={rb_stack_s_lb_hr:.1f})")
print(f"  >>> {'MATCH' if abs(s_lost_rb_element - (rb_ash_s_lb_hr + rb_stack_s_lb_hr)) < 5 else 'MISMATCH'}: RB retention vs declared losses")

# Dissolving tank: S in smelt vs S in GL
print(f"\n  ── Dissolving Tank / GL Clarifier ──")
smelt_active_sulfide_na2o = rb_active_sulfide
smelt_s_element = smelt_active_sulfide_na2o * MW['S'] / MW['Na2O']

# Get unit operations for comparison
unit_ops = results.get('unit_operations', [])
gl_row = next((r for r in unit_ops if r['stage'] == 'Green Liquor'), None)
wl_slaker_row = next((r for r in unit_ops if r['stage'] == 'White Liquor (from slaker)'), None)
wl_digest_row = next((r for r in unit_ops if r['stage'] == 'White Liquor (to digesters)'), None)

if gl_row:
    print(f"  S in GL to slaker:            {gl_row['s_lb_hr']:8.1f} lb/hr")
    # How much S went to dregs+grits?
    gl_flow = results.get('gl_flow_to_slaker_gpm', 0)
    dissolving_flow = results.get('dissolving_tank_flow', 0)
    dregs_gpm = results.get('dregs_underflow_gpm', 0)
    grits_gpm = results.get('grits_underflow_gpm', 0)
    semichem_gl = results.get('semichem_gl_gpm', 0)
    print(f"  Dissolving tank total flow:    {dissolving_flow:8.1f} gpm")
    print(f"  GL to slaker flow:             {gl_flow:8.1f} gpm")
    print(f"  Dregs underflow:               {dregs_gpm:8.1f} gpm")
    print(f"  Grits underflow:               {grits_gpm:8.1f} gpm")
    print(f"  Semichem GL draw:              {semichem_gl:8.1f} gpm (returns via BL)")
    divert_frac = (dregs_gpm + grits_gpm) / dissolving_flow if dissolving_flow > 0 else 0
    # S diverted to dregs+grits (proportional to flow)
    # Total dissolving S = active_sulfide/2000 + WW_S
    ww_tta = DEFAULTS['ww_tta_lb_ft3']
    ww_sulf = DEFAULTS['ww_sulfidity']
    ww_flow = DEFAULTS['ww_flow_gpm']
    ww_s_ton_hr = ww_flow * ww_tta * 16.01 * 0.00025 * ww_sulf
    total_dissolving_s = smelt_active_sulfide_na2o / 2000 + ww_s_ton_hr
    s_in_dregs_grits = total_dissolving_s * divert_frac * 2000 * MW['S'] / MW['Na2O']
    declared_dregs_s = s_detail['dregs_filter']
    declared_grits_s = s_detail['grits']
    print(f"  S diverted to dregs+grits:     {s_in_dregs_grits:8.1f} lb S/hr  (implicit, from flow reduction)")
    print(f"  Declared dregs+grits losses:   {declared_dregs_s + declared_grits_s:8.1f} lb S/hr")
    print(f"  >>> {'CLOSE' if abs(s_in_dregs_grits - (declared_dregs_s + declared_grits_s)) < 20 else 'GAP'}: flow-based vs declared losses")

# Fiberline: S loss in digesters
print(f"\n  ── Fiberline (Digesters) ──")
if wl_digest_row:
    print(f"  S in WL to digesters:          {wl_digest_row['s_lb_hr']:8.1f} lb/hr")

pine_s = results.get('pine_bl_inorganic_solids_lb_hr', 0)
semichem_s = results.get('semichem_bl_inorganic_solids_lb_hr', 0)
pine_row = next((r for r in unit_ops if r['stage'] == 'Pine Digester BL'), None)
semichem_row = next((r for r in unit_ops if r['stage'] == 'Semichem Digester BL'), None)

if pine_row and semichem_row:
    total_bl_s = pine_row['s_lb_hr'] + semichem_row['s_lb_hr']
    s_digester_pct = DEFAULTS['s_loss_digester_pct']
    wl_s_in = wl_digest_row['s_lb_hr'] if wl_digest_row else 0
    s_lost_digester_modeled = wl_s_in * s_digester_pct / (1 - s_digester_pct) if s_digester_pct < 1 else 0
    print(f"  Pine BL S out:                 {pine_row['s_lb_hr']:8.1f} lb/hr")
    print(f"  Semichem BL S out:             {semichem_row['s_lb_hr']:8.1f} lb/hr")
    print(f"  Total BL S out:                {total_bl_s:8.1f} lb/hr")
    print(f"  S lost in digester model:      {wl_s_in - total_bl_s:8.1f} lb/hr  (2% of Na2S entering)")
    s_lost_digester_bdt = (wl_s_in - total_bl_s) * 24 / total_prod
    print(f"  S lost in digester (lb/BDT):   {s_lost_digester_bdt:8.3f} lb/BDT")
    declared_ncg_bdt = loss_breakdown.ncg
    print(f"  Declared NCG/turp loss:        {declared_ncg_bdt:8.3f} lb/BDT  ({s_detail['ncg']:.1f} lb/hr)")
    print(f"  >>> GAP: Digester model loses {s_lost_digester_bdt:.3f} but declared NCG is {declared_ncg_bdt:.3f} lb/BDT")

# CTO
cto_row = next((r for r in unit_ops if r['stage'] == 'CTO Brine'), None)
if cto_row:
    print(f"\n  ── CTO Brine ──")
    print(f"  CTO S into WBL mixer:          {cto_row['s_lb_hr']:8.1f} lb/hr")

# Mixed WBL
mixed_row = next((r for r in unit_ops if r['stage'] == 'Mixed WBL'), None)
if mixed_row:
    print(f"\n  ── Mixed WBL ──")
    print(f"  Mixed WBL S:                   {mixed_row['s_lb_hr']:8.1f} lb/hr")
    print(f"  Mixed WBL Na:                  {mixed_row['na_lb_hr']:8.1f} lb/hr")

# Evaporator
evap_row = next((r for r in unit_ops if r['stage'] == 'Evaporator (SBL)'), None)
if evap_row and mixed_row:
    print(f"\n  ── Evaporator ──")
    print(f"  SBL S out:                     {evap_row['s_lb_hr']:8.1f} lb/hr")
    print(f"  S change in evaporator:        {evap_row['s_lb_hr'] - mixed_row['s_lb_hr']:8.1f} lb/hr  (should be 0)")
    declared_evap_spill_s = s_detail['evap_spill_loss']
    print(f"  Declared evap spill loss:      {declared_evap_spill_s:8.1f} lb S/hr")
    print(f"  >>> MISSING: Evaporator model conserves S perfectly — spill NOT modeled")

# RB smelt row
smelt_row = next((r for r in unit_ops if r['stage'] == 'Recovery Boiler (Smelt)'), None)
if smelt_row and evap_row:
    print(f"\n  ── Recovery Boiler (tracking table) ──")
    print(f"  Tracking table 'Smelt' S:      {smelt_row['s_lb_hr']:8.1f} lb/hr")
    print(f"  SBL S feeding RB:              {evap_row['s_lb_hr']:8.1f} lb/hr")
    print(f"  NOTE: smelt.s_lbs_hr is S ENTERING RB (BL+saltcake), not S IN smelt")
    print(f"  Actual smelt S (active+dead):  ~{(rb_active_sulfide + rb_dead_load) * MW['S'] / MW['Na2O']:.1f} lb/hr (element)")

# ──────────────────────────────────────────────────────────────────────────────
# 5. LOSS-BY-LOSS AUDIT
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SECTION 5: LOSS-BY-LOSS AUDIT — Modeled vs Declared")
print("=" * 80)

print(f"""
  Loss Source             lb S/BDT   lb S/hr    Physically Modeled?
  ────────────────────    ────────   ────────   ─────────────────────────────────────
  Evaporator Spill          {loss_breakdown.evap_spill_loss:6.3f}    {s_detail['evap_spill_loss']:7.1f}    NO  — evaporator conserves S perfectly
  RB Ash Purge              {loss_breakdown.rb_ash_purge:6.3f}    {s_detail['rb_ash_purge']:7.1f}    YES — via s_retention_strong
  RB Stack                  {loss_breakdown.rb_stack:6.3f}    {s_detail['rb_stack']:7.1f}    YES — via s_retention_strong
  Dregs Filter              {loss_breakdown.dregs_filter:6.3f}    {s_detail['dregs_filter']:7.1f}    PARTIAL — GL flow reduced by dregs underflow
  Grits                     {loss_breakdown.grits:6.3f}    {s_detail['grits']:7.1f}    PARTIAL — GL flow reduced by grits underflow
  Weak Wash Overflow        {loss_breakdown.weak_wash_overflow:6.3f}    {s_detail['weak_wash_overflow']:7.1f}    NO  — WW is fixed-flow input
  NCG/Turpentine            {loss_breakdown.ncg:6.3f}    {s_detail['ncg']:7.1f}    PARTIAL — digester model uses 2% (~0.2 lb/BDT)
  Recaust Spill             {loss_breakdown.recaust_spill:6.3f}    {s_detail['recaust_spill']:7.1f}    NO  — not modeled anywhere
  ────────────────────    ────────   ────────
  TOTAL                    {loss_breakdown.total_lb_bdt:6.3f}    {total_s_loss_lb_hr:7.1f}
""")

# Quantify the gap
modeled_rb = s_detail['rb_ash_purge'] + s_detail['rb_stack']
if wl_digest_row and pine_row and semichem_row:
    modeled_digester = wl_digest_row['s_lb_hr'] - (pine_row['s_lb_hr'] + semichem_row['s_lb_hr'])
else:
    modeled_digester = 0

# dregs+grits implicit removal (proportional to flow fraction)
modeled_dregs_grits = s_in_dregs_grits if 's_in_dregs_grits' in dir() else 0

total_modeled = modeled_rb + modeled_digester + modeled_dregs_grits
total_unmodeled = total_s_loss_lb_hr - total_modeled

print(f"  S losses physically modeled:   {total_modeled:8.1f} lb/hr")
print(f"  S losses NOT modeled:          {total_unmodeled:8.1f} lb/hr")
print(f"  Gap as % of total losses:      {total_unmodeled / total_s_loss_lb_hr * 100:.1f}%")

# ──────────────────────────────────────────────────────────────────────────────
# 6. RECOMMENDATIONS
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("SECTION 6: FINDINGS & IMPACT")
print("=" * 80)
print(f"""
  FINDING 1: NCG/Turpentine is the LARGEST gap
    Declared: {loss_breakdown.ncg:.3f} lb/BDT = {s_detail['ncg']:.1f} lb/hr
    Modeled:  ~{modeled_digester:.1f} lb/hr (2% digester loss)
    Gap:      {s_detail['ncg'] - modeled_digester:.1f} lb/hr — S stays in the loop when it shouldn't

  FINDING 2: Evaporator Spill is the 2nd largest unmodeled loss
    Declared: {loss_breakdown.evap_spill_loss:.3f} lb/BDT = {s_detail['evap_spill_loss']:.1f} lb/hr
    Modeled:  0 lb/hr — evaporator conserves S perfectly
    Gap:      {s_detail['evap_spill_loss']:.1f} lb/hr

  FINDING 3: Recaust Spill and WW Overflow are small but unmodeled
    Combined: {s_detail['recaust_spill'] + s_detail['weak_wash_overflow']:.1f} lb/hr

  FINDING 4: Smelt row in tracking table shows S INTO RB, not S IN smelt
    smelt.s_lbs_hr = {smelt_row['s_lb_hr']:.1f} lb/hr (total S entering RB)
    Actual smelt S ≈ {(rb_active_sulfide + rb_dead_load) * MW['S'] / MW['Na2O']:.1f} lb/hr (active+dead)

  IMPACT: With the outer loop active, the physical model retains ~{total_unmodeled:.0f} lb/hr
  more S than should exist. This inflates computed BL S% and makes the net
  balance appear more negative (more losses) than the model actually implements.

  The S LOSSES TABLE is correct as a diagnostic (shows declared losses).
  The TRACKING TABLE is correct (shows physical model flows).
  But they are INCONSISTENT — the tracking table shows more S than the
  losses table says should remain.
""")

# Summary of all unit operations for reference
print("=" * 80)
print("APPENDIX: Full Unit Operations Tracking Table")
print("=" * 80)
print(f"  {'Stage':35s}  {'Na lb/hr':>10s}  {'S lb/hr':>10s}  {'Na% ds':>8s}  {'S% ds':>8s}")
print(f"  {'─'*35}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*8}")
for row in unit_ops:
    na_pct = f"{row['na_pct_ds']:.2f}" if row.get('na_pct_ds') is not None else "--"
    s_pct = f"{row['s_pct_ds']:.2f}" if row.get('s_pct_ds') is not None else "--"
    print(f"  {row['stage']:35s}  {row['na_lb_hr']:10.1f}  {row['s_lb_hr']:10.1f}  {na_pct:>8s}  {s_pct:>8s}")
