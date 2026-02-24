"""
Recovery boiler calculations — faithful to Excel 2_Recovery Boiler sheet.

Reference: 2_Recovery boiler sheet in Excel v4

Full calculation chain:
  B10: BL density (from TDS, temp with -0.1 offset)
  B8:  Dry solids t/day = (flow × density / 2000) × 60 × 24 × (TDS/100)
  B6:  Virgin+Ash kpph = (B8 × 2000) / 1000 / 24
  B5:  Virgin kpph = B6 × (1 - ash_recycled)
  B7:  As-fired kpph = B6 + saltcake/1000
  B47: Ash solids = B7 × ash_recycled × 1000
  B48: Ash Na (element) from Na2SO4 chemistry
  B49: Ash Na as Na2O
  B50: Ash S (element) from Na2SO4 chemistry
  B51: Ash S as Na2O equivalent
  B21: Na% d.s. Virgin+Ash = (inv_Na% × Virgin + Ash_Na) / (Virgin+Ash)
  B26: S% d.s. Virgin+Ash = (inv_S% × Virgin + Ash_S) / (Virgin+Ash)
  B23: Na lbs/hr = Na%_mixed × V+A × 1000 + Saltcake_Na
  B28: S lbs/hr = S%_mixed × V+A × 1000 + Saltcake_S
  B29-B31: Potential alkali (Na, K, S as Na2O)
  B32: Active sulfide = S_alkali × RE × S_ret - Ash_S_Na2O
  B33: Dead load = S_alkali × (1 - RE)
  B34: TTA = Na_alkali + K_alkali - Dead_load - RB_losses - Ash_Na_Na2O
  B35: Smelt sulfidity = B32/B34
"""

from dataclasses import dataclass
from typing import Tuple

from .constants import MW, CONV
from .density import calculate_bl_density


@dataclass
class RecoveryBoilerInputs:
    """Recovery boiler inputs calculated from BL flow and properties."""
    bl_flow_gpm: float
    bl_tds_pct: float
    bl_temp_f: float
    bl_na_pct_mixed: float       # B21 — CALCULATED Na% d.s. Virgin+Ash
    bl_s_pct_mixed: float        # B26 — CALCULATED S% d.s. Virgin+Ash
    bl_k_pct: float
    bl_density_lb_gal: float     # B10
    dry_solids_lbs_hr: float     # B6 × 1000 = Virgin+Ash lb/hr
    # Solids breakdown
    virgin_solids_lbs_hr: float   # B5 × 1000
    virgin_plus_ash_lbs_hr: float # B6 × 1000
    as_fired_solids_lbs_hr: float # B7 × 1000
    # Ash (computed from Na2SO4 chemistry)
    ash_solids_lbs_hr: float      # B47
    ash_na_na2o: float            # B49 — Ash Na as Na2O lb/hr
    ash_s_na2o: float             # B51 — Ash S as Na2O equiv lb/hr
    # Saltcake (computed from Na2SO4 chemistry)
    saltcake_na_lbs_hr: float     # B41 — Saltcake Na lb/hr (element)
    saltcake_s_lbs_hr: float      # B43 — Saltcake S lb/hr (element)
    # RB losses
    rb_losses_na2o_lbs_hr: float  # B18 = B16 × production/24
    # Element flows (total including saltcake)
    na_lbs_hr: float     # B23
    k_lbs_hr: float      # B25
    s_lbs_hr: float      # B28
    # S% fired (V+A+Saltcake) for S retention calculation
    bl_s_pct_fired: float  # B27


@dataclass
class SmeltComposition:
    """Recovery boiler smelt composition and calculated values."""
    na_lbs_hr: float
    k_lbs_hr: float
    s_lbs_hr: float
    reduction_eff_pct: float
    s_retention_strong: float
    ash_na_na2o: float
    ash_s_na2o_equiv: float
    rb_losses_na2o_lbs_hr: float
    potential_na_alkali: float = 0.0   # B29
    potential_k_alkali: float = 0.0    # B30
    potential_s_alkali: float = 0.0    # B31
    active_sulfide: float = 0.0        # B32
    dead_load: float = 0.0             # B33
    tta_lbs_hr: float = 0.0            # B34
    smelt_sulfidity_pct: float = 0.0   # B35
    # For S retention
    dry_solids_lbs_hr: float = 0.0
    bl_s_pct_fired: float = 0.0


def calculate_full_rb(
    bl_flow_gpm: float, bl_tds_pct: float, bl_temp_f: float,
    bl_na_pct_inv: float,           # Inventory Na% d.s. (1_Inv!X49, e.g. 19.50)
    bl_s_pct_inv: float,            # Inventory S% d.s. (1_Inv!X50, e.g. 3.93)
    bl_k_pct: float,
    reduction_eff_pct: float,
    s_retention_strong: float,
    ash_recycled_pct: float,        # B4 = 0.07 (7%)
    rb_losses_na2o_bdt: float,      # B16 = 3.60 lb Na2O/BDT
    total_production_bdt_day: float, # B2 = 1888
    saltcake_flow_lb_hr: float = 0.0, # B40 = 2227 lb Na2SO4/hr
) -> Tuple[RecoveryBoilerInputs, SmeltComposition]:
    """
    Calculate complete RB outputs using the full Excel calculation chain.

    Key difference from previous version:
    - ash_na_na2o, ash_s_na2o are CALCULATED from ash_recycled_pct
    - Na% d.s. and S% d.s. are CALCULATED from inventory values + ash mixing
    - saltcake Na/S are CALCULATED from saltcake_flow using Na2SO4 chemistry
    - RB losses are CALCULATED from per-BDT value × production
    """
    # ── Step 1: BL density (B10) ──
    bl_density = calculate_bl_density(bl_tds_pct, bl_temp_f, offset=-0.1)

    # ── Step 2: Dry solids (B8 = Virgin+Ash) ──
    # B8 t/day = (flow × density / 2000) × 60 × 24 × (TDS/100)
    # B6 kpph = (B8 × 2000) / 1000 / 24 = flow × density × TDS% × 10 × 0.06 / 1000
    dry_solids_lbs_hr = bl_flow_gpm * bl_density * bl_tds_pct * 10 * 0.06
    virgin_plus_ash_lbs_hr = dry_solids_lbs_hr  # B6 × 1000

    # ── Step 3: Saltcake Na/S from Na2SO4 chemistry ──
    Na_frac_Na2SO4 = 2 * MW['Na'] / MW['Na2SO4']  # = 45.96/142.04 = 0.3236
    S_frac_Na2SO4 = MW['S'] / MW['Na2SO4']          # = 32.065/142.04 = 0.2258
    Na2O_per_Na2SO4 = MW['Na2O'] / MW['Na2SO4']     # = 62/142.04 = 0.4366

    saltcake_na_lbs_hr = saltcake_flow_lb_hr * Na_frac_Na2SO4   # B41
    saltcake_s_lbs_hr = saltcake_flow_lb_hr * S_frac_Na2SO4     # B43

    # ── Step 4: As-fired solids (B7) ──
    as_fired_lbs_hr = virgin_plus_ash_lbs_hr + saltcake_flow_lb_hr  # B7 × 1000

    # ── Step 5: Virgin solids (B5) ──
    # B5 = B6 × (1 - ash_recycled) — ash fraction applied to V+A
    virgin_solids_lbs_hr = virgin_plus_ash_lbs_hr * (1 - ash_recycled_pct)

    # ══════════════════════════════════════════════════════════════════════
    # ASH LOOP EXPLANATION
    # The ESP (electrostatic precipitator) ash is recycled Na₂SO₄. It enters
    # via BL (mixed with virgin BL) but must be subtracted from smelt output:
    #
    #   1. Ash Na/S increase BL composition (lines 148-156 below: bl_na_pct_mixed)
    #   2. Ash Na/S are NOT converted to active alkali — they recirculate as
    #      unreduced Na₂SO₄, passing through the RB without chemical change
    #   3. Net effect: ash adds no NEW Na/S to the system (recirculation only)
    #   4. The fraction lost in ESP = true system loss (captured in loss table
    #      as loss_rb_ash_s and loss_rb_ash_na)
    #
    # Therefore, ash Na and ash S are:
    #   - Added to BL composition (step 7: bl_na_pct_mixed, bl_s_pct_mixed)
    #   - Subtracted from smelt active_sulfide and TTA (steps 11-12)
    # ══════════════════════════════════════════════════════════════════════

    # ── Step 6: Ash solids and composition (B47-B51) ──
    # B47: Ash solids = As-fired × ash_recycled (fraction of total fired solids)
    ash_solids_lbs_hr = as_fired_lbs_hr * ash_recycled_pct

    # Ash is Na2SO4 — compute Na and S contributions (element basis)
    ash_na_lbs_hr = ash_solids_lbs_hr * Na_frac_Na2SO4     # B48 — Na element
    ash_s_lbs_hr = ash_solids_lbs_hr * S_frac_Na2SO4       # B50 — S element
    # Convert to Na2O basis for TTA/sulfide calculations
    ash_na_na2o = ash_na_lbs_hr * CONV['Na_to_Na2O']       # B49 — Na as Na2O
    ash_s_na2o = ash_s_lbs_hr * CONV['S_to_Na2O']          # B51 — S as Na2O equiv

    # ── Step 7: Na% and S% d.s. Virgin+Ash (B21, B26) ──
    # B21 = (inv_Na% × Virgin + Ash_Na) / (Virgin+Ash)
    # B26 = (inv_S% × Virgin + Ash_S) / (Virgin+Ash)
    if virgin_plus_ash_lbs_hr > 0:
        na_from_virgin = (bl_na_pct_inv / 100) * virgin_solids_lbs_hr
        bl_na_pct_mixed = (na_from_virgin + ash_na_lbs_hr) / virgin_plus_ash_lbs_hr * 100

        s_from_virgin = (bl_s_pct_inv / 100) * virgin_solids_lbs_hr
        bl_s_pct_mixed = (s_from_virgin + ash_s_lbs_hr) / virgin_plus_ash_lbs_hr * 100
    else:
        bl_na_pct_mixed = bl_na_pct_inv
        bl_s_pct_mixed = bl_s_pct_inv

    # ── Step 8: Element flows (B23, B25, B28) ──
    na_lbs_hr = (bl_na_pct_mixed / 100) * virgin_plus_ash_lbs_hr + saltcake_na_lbs_hr
    k_lbs_hr = (bl_k_pct / 100) * virgin_plus_ash_lbs_hr
    s_lbs_hr = (bl_s_pct_mixed / 100) * virgin_plus_ash_lbs_hr + saltcake_s_lbs_hr

    # S% d.s. fired (B27 — including saltcake, for S retention)
    bl_s_pct_fired = (s_lbs_hr / as_fired_lbs_hr * 100) if as_fired_lbs_hr > 0 else bl_s_pct_mixed

    # ── Step 9: RB losses (B18) ──
    rb_losses_na2o_lbs_hr = rb_losses_na2o_bdt * total_production_bdt_day / 24

    # ── Step 10: Potential alkali (B29-B31) ──
    re = reduction_eff_pct / 100
    potential_na = na_lbs_hr * CONV['Na_to_Na2O']   # B29
    potential_k = k_lbs_hr * CONV['K_to_Na2O']      # B30
    potential_s = s_lbs_hr * CONV['S_to_Na2O']       # B31

    # ── Step 11: Active sulfide and dead load (B32, B33) ──
    active_sulfide = potential_s * re * s_retention_strong - ash_s_na2o  # B32
    active_sulfide = max(0.0, active_sulfide)
    dead_load = potential_s * (1 - re)  # B33

    # ── Step 12: TTA (B34) ──
    tta_lbs_hr = potential_na + potential_k - dead_load - rb_losses_na2o_lbs_hr - ash_na_na2o

    # ── Step 13: Smelt sulfidity (B35) ──
    smelt_sulfidity_pct = (active_sulfide / tta_lbs_hr * 100) if tta_lbs_hr > 0 else 0.0

    # ── Build result objects ──
    rb_inputs = RecoveryBoilerInputs(
        bl_flow_gpm=bl_flow_gpm,
        bl_tds_pct=bl_tds_pct,
        bl_temp_f=bl_temp_f,
        bl_na_pct_mixed=bl_na_pct_mixed,
        bl_s_pct_mixed=bl_s_pct_mixed,
        bl_k_pct=bl_k_pct,
        bl_density_lb_gal=bl_density,
        dry_solids_lbs_hr=dry_solids_lbs_hr,
        virgin_solids_lbs_hr=virgin_solids_lbs_hr,
        virgin_plus_ash_lbs_hr=virgin_plus_ash_lbs_hr,
        as_fired_solids_lbs_hr=as_fired_lbs_hr,
        ash_solids_lbs_hr=ash_solids_lbs_hr,
        ash_na_na2o=ash_na_na2o,
        ash_s_na2o=ash_s_na2o,
        saltcake_na_lbs_hr=saltcake_na_lbs_hr,
        saltcake_s_lbs_hr=saltcake_s_lbs_hr,
        rb_losses_na2o_lbs_hr=rb_losses_na2o_lbs_hr,
        na_lbs_hr=na_lbs_hr,
        k_lbs_hr=k_lbs_hr,
        s_lbs_hr=s_lbs_hr,
        bl_s_pct_fired=bl_s_pct_fired,
    )

    smelt = SmeltComposition(
        na_lbs_hr=na_lbs_hr,
        k_lbs_hr=k_lbs_hr,
        s_lbs_hr=s_lbs_hr,
        reduction_eff_pct=reduction_eff_pct,
        s_retention_strong=s_retention_strong,
        ash_na_na2o=ash_na_na2o,
        ash_s_na2o_equiv=ash_s_na2o,
        rb_losses_na2o_lbs_hr=rb_losses_na2o_lbs_hr,
        potential_na_alkali=potential_na,
        potential_k_alkali=potential_k,
        potential_s_alkali=potential_s,
        active_sulfide=active_sulfide,
        dead_load=dead_load,
        tta_lbs_hr=tta_lbs_hr,
        smelt_sulfidity_pct=smelt_sulfidity_pct,
        dry_solids_lbs_hr=dry_solids_lbs_hr,
        bl_s_pct_fired=bl_s_pct_fired,
    )
    return rb_inputs, smelt
