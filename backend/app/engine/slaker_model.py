"""
Slaker model — faithful reproduction of the Slaker Model sheet.

Reference: Slaker Model sheet in SULFIDITY_MODEL_CORRECTED_FINAL v4.xlsx

Implements:
  - Energy Balance (Heat): B59-B66 — steam generated from CaO slaking
  - Water Balance: B68-B71 — water consumed by slaking + steam evaporation
  - WL Flow Calculation: B74-B81 — mass balance → volume → yield_factor
  - Causticizing: B80-B82 — Na2CO3 converted, causticizing efficiency
  - White Liquor Outputs: B86-B98 — composition from concentration factor
  - Lime Mud Output: B102-B105

Key output: yield_factor (B81 = WL_volume / GL_volume) is CALCULATED from
the full energy → water → mass balance, not approximated.

The Excel yield factor (~1.0335) is the ratio of WL volume flow to GL volume
flow. It emerges from the mass balance:
  WL_mass = GL_mass + lime_mass - steam - slaker_grits_loss
  WL_volume = WL_mass × 907.185 / WL_density(1.135)
  yield_factor = WL_volume / GL_volume
"""

from dataclasses import dataclass
from .constants import MW, CONV
from .density import calculate_gl_density_hot


@dataclass
class SlakerResult:
    """Results from the slaker/causticizer model."""
    yield_factor: float           # B81 = WL_volume_flow / GL_volume_flow
    wl_flow_gpm: float            # B87 = WL volume flow in gpm
    gl_flow_gpm: float            # input GL flow

    # WL composition from slaker (all g Na2O/L)
    wl_tta_g_L: float             # B90
    wl_na2s_g_L: float            # B91
    wl_naoh_g_L: float            # B92
    wl_na2co3_g_L: float          # B93
    wl_ea_g_L: float              # B96
    wl_aa_g_L: float              # B95

    # WL mass flows (ton Na2O/hr)
    wl_tta_mass_ton_hr: float     # N69
    wl_na2s_mass_ton_hr: float    # K67
    wl_naoh_mass_ton_hr: float    # K71
    wl_na2co3_mass_ton_hr: float  # K68

    # Sulfidity
    wl_sulfidity: float           # N70 = K67 / N69

    # Lime mud — all solids settling in WLC
    lime_mud_caco3_lb_hr: float       # CaCO3 only
    lime_mud_total_lb_hr: float       # CaCO3 + excess Ca(OH)2 + inerts
    grits_loss_lb_hr: float

    # Energy/water/mass balance outputs (new)
    steam_generated_ton_hr: float   # B65
    water_consumed_ton_hr: float    # B68
    gl_mass_ton_hr: float           # B48
    wl_mass_ton_hr: float           # B74
    total_lime_ton_hr: float        # B13

    # First-principles causticizing outputs (new)
    gl_na2co3_g_L: float = 0.0        # Na2CO3 in GL (to be causticized)
    gl_na2co3_lb_hr: float = 0.0      # Na2CO3 mass flow in GL
    conversion_fraction: float = 0.0   # x = fraction of Na2CO3 converted
    lime_required_lb_hr: float = 0.0   # Lime required for target CE (CaO basis)
    lime_feed_lb_hr: float = 0.0       # Actual lime feed (accounts for quality)
    achieved_ce_pct: float = 0.0       # Causticity achieved (should match target)


def calculate_slaker_model(
    gl_flow_gpm: float,           # I58 = GL flow to slaker
    gl_tta_g_L: float,            # I67
    gl_na2s_g_L: float,           # I68
    gl_aa_g_L: float,             # I69
    gl_temp_f: float = 189.0,     # B9 — GL temperature entering slaker (°F)
    causticity: float = 0.81,     # B21/100
    lime_charge_ratio: float = 0.85,
    cao_in_lime_pct: float = 87.53,
    caco3_in_lime_pct: float = 1.96,
    inerts_in_lime_pct: float = 9.46,  # Corrected: was 0.0946, should be 9.46%
    grits_loss_pct: float = 1.0,
    lime_temp_f: float = 1100.0,
    slaker_temp_f: float = 210.5,
    lime_soda_na2o_pct: float = 0.17,  # Soda (Na₂O) content in lime (%)
) -> SlakerResult:
    """
    Slaker model with full energy/water/mass balance (Excel Slaker Model sheet).

    Computes yield_factor from:
      1. GL mass flow (from GL flow × GL density at temperature)
      2. Energy balance → steam generated
      3. Water balance → water consumed + evaporated
      4. Mass balance: WL_mass = GL_mass + lime - steam - grits_loss
      5. WL volume from mass and hardcoded density (1.135 kg/L)
      6. yield_factor = WL_volume / GL_volume
    """
    # Constants from Excel Slaker Model sheet
    KG_PER_TON = CONV['KG_PER_SHORT_TON']       # B37 = 907.185
    HEAT_SLAKING = CONV['HEAT_OF_SLAKING']       # B31 = 15300 cal/mol CaO
    GL_CP = CONV['GL_SPECIFIC_HEAT']             # B49 = 0.882 kcal/kg/°C
    LIME_CP = CONV['LIME_SPECIFIC_HEAT']         # B32 = 0.175 kcal/kg/°C
    STEAM_LH = CONV['STEAM_LATENT_HEAT']         # B36 = 538.5 kcal/kg
    WL_DENSITY = CONV['WL_DENSITY_KG_L']         # B76 = 1.135 kg/L

    MW_CaO = MW['CaO']         # 56.08
    MW_Na2CO3 = MW['Na2CO3']   # 106.0
    MW_Na2O = MW['Na2O']       # 62.0
    MW_CaCO3 = MW['CaCO3']    # 100.09
    MW_H2O = MW['H2O']        # 18.015

    # ── Temperature conversions ──
    gl_temp_c = (gl_temp_f - 32) / 1.8        # B9
    slaker_temp_c = (slaker_temp_f - 32) / 1.8  # B23
    lime_temp_c = (lime_temp_f - 32) / 1.8     # B18

    # ── GL composition breakdown (all g Na2O/L) ──
    gl_naoh_g_L = gl_aa_g_L - gl_na2s_g_L     # B40 = AA - Na2S
    gl_na2co3_g_L = gl_tta_g_L - gl_aa_g_L    # B41 = TTA - AA (dead load)

    # ══════════════════════════════════════════════════════════════════════════
    # FIRST-PRINCIPLES CAUSTICIZING
    # ══════════════════════════════════════════════════════════════════════════
    # Reaction: Na2CO3 + Ca(OH)2 → 2NaOH + CaCO3
    #
    # CE = NaOH / (NaOH + Na2CO3_remaining)
    #
    # Let x = fraction of Na2CO3 converted:
    #   NaOH_produced = 2 × x × Na2CO3_initial (stoichiometry, as Na2O)
    #   Na2CO3_remaining = Na2CO3_initial × (1 - x)
    #
    # At equilibrium:
    #   CE = 2x / (2x + (1-x)) = 2x / (1 + x)
    #
    # Solving for x:
    #   x = CE / (2 - CE)
    #
    # For CE = 81%: x = 0.81 / 1.19 = 0.681 (68.1% conversion)
    # ══════════════════════════════════════════════════════════════════════════

    # Calculate conversion fraction from target CE
    conversion_fraction = causticity / (2 - causticity) if causticity < 2 else 0.99

    # ── Causticizing (B82): Na2CO3 converted ──
    # Using first-principles: amount converted = x × initial_Na2CO3
    # Note: gl_na2co3_g_L is in Na2O basis, gl_naoh_g_L is also Na2O basis
    # The existing formula accounts for any NaOH already in GL
    na2co3_conv_na2o = causticity * (gl_tta_g_L - gl_na2s_g_L) - gl_naoh_g_L

    # Na2CO3 converted in actual g/L
    na2co3_conv_actual = na2co3_conv_na2o * (MW_Na2CO3 / MW_Na2O)

    # CaO consumed stoichiometrically by converted Na2CO3 (1:1 molar)
    cao_consumed_g_L = na2co3_conv_actual * (MW_CaO / MW_Na2CO3)

    # ── GL Volume and Mass (B47, B48) ──
    gl_volume_L_hr = gl_flow_gpm * 60 * 3.785   # B47
    gl_density_kg_L = calculate_gl_density_hot(gl_tta_g_L, gl_temp_f)
    gl_mass_ton_hr = gl_volume_L_hr * gl_density_kg_L / KG_PER_TON  # B48

    # ── CaO: charged vs consumed ──
    # Total Na2CO3 in GL (for stoichiometric lime calculation)
    total_na2co3_actual = gl_na2co3_g_L * (MW_Na2CO3 / MW_Na2O)
    stoich_cao_all = total_na2co3_actual * (MW_CaO / MW_Na2CO3)

    # CaO fed = stoich_for_ALL_Na2CO3 × lime_charge_ratio (B26)
    cao_fed_g_L = stoich_cao_all * lime_charge_ratio

    # All fed CaO slakes: CaO + H2O → Ca(OH)2
    # B54 = CaO that slakes (short ton/hr) — all fed CaO
    b54 = cao_fed_g_L * gl_volume_L_hr / (KG_PER_TON * 1000)

    # Total lime feed (B13) = CaO_fed / CaO_purity
    if cao_in_lime_pct > 0:
        total_lime = b54 / (cao_in_lime_pct / 100)
    else:
        total_lime = 0.0

    # CaO consumed by causticizing (subset of total)
    cao_consumed_ton = cao_consumed_g_L * gl_volume_L_hr / (KG_PER_TON * 1000)

    # Excess CaO = fed - consumed (goes to grits/mud as Ca(OH)2)
    cao_excess = max(0, b54 - cao_consumed_ton)

    # ── Energy Balance (B59-B66) ──
    # B60: ΔT GL to Slaker
    dt_gl = slaker_temp_c - gl_temp_c

    # B62: ΔT Lime to Slaker (negative since lime is hotter)
    dt_lime = slaker_temp_c - lime_temp_c

    # B59: Heat released by slaking = B54 × B37 × B31 / 56.08 (kcal/hr)
    heat_slaking = b54 * KG_PER_TON * HEAT_SLAKING / MW_CaO

    # B61: Heat to warm GL = B48 × B37 × B49 × B60 (kcal/hr)
    heat_warm_gl = gl_mass_ton_hr * KG_PER_TON * GL_CP * dt_gl

    # B63: Heat from lime cooling = B13 × B37 × B32 × B62 (kcal/hr, negative)
    heat_lime_cooling = total_lime * KG_PER_TON * LIME_CP * dt_lime

    # B64: Heat available for steam = B59 - B61 - B63
    heat_for_steam = heat_slaking - heat_warm_gl - heat_lime_cooling

    # B65: Steam generated = MAX(0, B64 / B36 / B37) (short ton/hr)
    steam_ton_hr = max(0.0, heat_for_steam / (STEAM_LH * KG_PER_TON))

    # ── Water Balance (B68-B71) ──
    # B68: H2O consumed by slaking = B54 × 0.321 (MW ratio: 18.02/56.08)
    water_consumed = b54 * (MW_H2O / MW_CaO)

    # B70: Total water loss = B68 + B69 (steam evaporated = B65)
    total_water_loss = water_consumed + steam_ton_hr

    # ── Slaker grits loss ──
    # Grits are coarse particles screened out at the slaker.
    # grits_loss_pct is the fraction of total lime feed lost as grits.
    inerts = total_lime * (inerts_in_lime_pct / 100)
    slaker_grits = total_lime * (grits_loss_pct / 100)

    # ── Lime Mud Solids (computed early for liquid volume calculation) ──
    # CaCO3 from causticizing: Na2CO3 + Ca(OH)2 → 2NaOH + CaCO3
    na2co3_conv_mass_early = (gl_volume_L_hr * na2co3_conv_na2o / 1e6
                              * CONV['METRIC_TO_SHORT'])
    caco3_from_reaction = na2co3_conv_mass_early * (MW_CaCO3 / MW_Na2O)
    caco3_from_lime = total_lime * (caco3_in_lime_pct / 100)
    total_caco3 = caco3_from_reaction + caco3_from_lime

    MW_CaOH2 = 74.09
    excess_caoh2 = cao_excess * (MW_CaOH2 / MW_CaO)

    # Total lime mud = CaCO3 + excess Ca(OH)2 + inerts (suspended solids)
    lime_mud_total = total_caco3 + excess_caoh2 + inerts

    # ── WL Flow Calculation (B74-B81) ──
    # B74: Total slurry mass = GL mass + lime - steam - grits_loss
    wl_mass = gl_mass_ton_hr + total_lime - steam_ton_hr - slaker_grits

    # WL slurry volume (liquid + suspended lime mud) — this is the physical
    # flow from the slaker to the WLC. The WLC settles the mud.
    wl_slurry_volume_L_hr = wl_mass * KG_PER_TON / WL_DENSITY

    # WL LIQUID volume — subtract lime mud solids from slurry mass.
    # TTA species are dissolved in the liquid phase only, so concentrations
    # must be based on liquid volume, not total slurry volume.
    wl_liquid_mass = wl_mass - lime_mud_total
    wl_liquid_volume_L_hr = wl_liquid_mass * KG_PER_TON / WL_DENSITY

    # B81: Yield factor = WL liquid volume / GL volume (concentration factor)
    if gl_volume_L_hr > 0:
        yield_factor = wl_liquid_volume_L_hr / gl_volume_L_hr
    else:
        yield_factor = 1.0

    # Clamp to reasonable range
    yield_factor = max(0.85, min(1.05, yield_factor))

    # B87: WL Flow (gpm) — SLURRY flow (physical stream to WLC)
    # The WLC receives the full slurry and removes mud in the underflow.
    wl_flow_gpm = wl_slurry_volume_L_hr / (60 * 3.785)

    # Liquid flow for concentration calculations only
    wl_liquid_flow_gpm = wl_liquid_volume_L_hr / (60 * 3.785)

    # ══════════════════════════════════════════════════════════════════════
    # STRICT MASS BALANCE: WL COMPOSITION
    # Conservation of Mass: Track mass flows, derive concentrations
    # This replaces the incorrect yield_factor multiplication approach
    # ══════════════════════════════════════════════════════════════════════

    # Conversion factor: gpm × g/L → ton Na₂O/hr
    conv = CONV['GPM_GL_TO_LB_HR'] / 2000

    # ── Step 1: GL Mass Flows (Input) ──
    gl_tta_mass = gl_tta_g_L * gl_flow_gpm * conv
    gl_na2s_mass = gl_na2s_g_L * gl_flow_gpm * conv
    gl_naoh_mass = gl_naoh_g_L * gl_flow_gpm * conv
    gl_na2co3_mass = gl_na2co3_g_L * gl_flow_gpm * conv

    # ── Step 2: Lime Soda Addition ──
    # Lime contains ~0.17% Na₂O (soda) that enters the WL
    lime_soda_mass = total_lime * (lime_soda_na2o_pct / 100)

    # ── Step 3: Species Mass Balance (Strict Conservation) ──
    # Na₂S: Inert through causticizing (no reaction)
    wl_na2s_mass = gl_na2s_mass

    # Na₂CO₃: Converted to NaOH via causticizing
    # na2co3_conv_na2o is the amount converted (g Na₂O/L equivalent)
    na2co3_conv_mass = na2co3_conv_na2o * gl_flow_gpm * conv
    wl_na2co3_mass = gl_na2co3_mass - na2co3_conv_mass

    # NaOH: Increased by conversion + lime soda
    wl_naoh_mass = gl_naoh_mass + na2co3_conv_mass + lime_soda_mass

    # TTA: Total = Na₂S + NaOH + Na₂CO₃ (all Na₂O basis)
    wl_tta_mass = wl_na2s_mass + wl_naoh_mass + wl_na2co3_mass

    # ── Step 4: Derive Concentrations from Mass / LIQUID Volume ──
    # Use liquid flow (excludes lime mud) for concentration calculations.
    # The slurry flow (wl_flow_gpm) is used for physical flow to WLC.
    if wl_liquid_flow_gpm > 0:
        wl_tta = wl_tta_mass / (wl_liquid_flow_gpm * conv)
        wl_na2s = wl_na2s_mass / (wl_liquid_flow_gpm * conv)
        wl_naoh = wl_naoh_mass / (wl_liquid_flow_gpm * conv)
        wl_na2co3 = wl_na2co3_mass / (wl_liquid_flow_gpm * conv)
    else:
        wl_tta = gl_tta_g_L
        wl_na2s = gl_na2s_g_L
        wl_naoh = gl_naoh_g_L
        wl_na2co3 = gl_na2co3_g_L

    # AA = NaOH + Na₂S
    wl_aa = wl_naoh + wl_na2s

    # EA = NaOH + 0.5 × Na₂S
    wl_ea = wl_naoh + 0.5 * wl_na2s

    # Sulfidity from mass ratio (correct basis)
    wl_sulfidity = wl_na2s_mass / wl_tta_mass if wl_tta_mass > 0 else 0.0

    # ── Lime Mud Output (B102-B105) ──
    # (lime mud solids already calculated above for liquid volume correction)
    lime_mud_caco3_lb_hr = total_caco3 * 2000
    lime_mud_total_lb_hr = lime_mud_total * 2000
    grits_lb_hr = slaker_grits * 2000

    # ══════════════════════════════════════════════════════════════════════════
    # FIRST-PRINCIPLES OUTPUTS
    # ══════════════════════════════════════════════════════════════════════════

    # GL Na2CO3 mass flow (lb/hr) - the carbonate entering the slaker
    # gl_na2co3_g_L is in Na2O basis, convert to actual Na2CO3
    gl_na2co3_actual_g_L = gl_na2co3_g_L * (MW_Na2CO3 / MW_Na2O)
    gl_na2co3_lb_hr = gl_na2co3_actual_g_L * gl_flow_gpm * CONV['GPM_GL_TO_LB_HR']

    # Lime required for target CE (CaO basis, lb/hr)
    # Stoichiometry: 1 mol CaO per mol Na2CO3 converted
    # CaO_required = x × Na2CO3 × (MW_CaO / MW_Na2CO3)
    lime_required_lb_hr = conversion_fraction * gl_na2co3_lb_hr * (MW_CaO / MW_Na2CO3)

    # Actual lime feed (accounting for lime quality)
    lime_feed_lb_hr = total_lime * 2000  # total_lime is in ton/hr

    # Achieved CE (should match input causticity)
    # CE = NaOH / (NaOH + Na2CO3) in WL
    achieved_ce_pct = (wl_naoh / (wl_naoh + wl_na2co3) * 100) if (wl_naoh + wl_na2co3) > 0 else 0.0

    return SlakerResult(
        yield_factor=yield_factor,
        wl_flow_gpm=wl_flow_gpm,
        gl_flow_gpm=gl_flow_gpm,
        wl_tta_g_L=wl_tta,
        wl_na2s_g_L=wl_na2s,
        wl_naoh_g_L=wl_naoh,
        wl_na2co3_g_L=wl_na2co3,
        wl_ea_g_L=wl_ea,
        wl_aa_g_L=wl_aa,
        wl_tta_mass_ton_hr=wl_tta_mass,
        wl_na2s_mass_ton_hr=wl_na2s_mass,
        wl_naoh_mass_ton_hr=wl_naoh_mass,
        wl_na2co3_mass_ton_hr=wl_na2co3_mass,
        wl_sulfidity=wl_sulfidity,
        lime_mud_caco3_lb_hr=lime_mud_caco3_lb_hr,
        lime_mud_total_lb_hr=lime_mud_total_lb_hr,
        grits_loss_lb_hr=grits_lb_hr,
        steam_generated_ton_hr=steam_ton_hr,
        water_consumed_ton_hr=water_consumed,
        gl_mass_ton_hr=gl_mass_ton_hr,
        wl_mass_ton_hr=wl_mass,
        total_lime_ton_hr=total_lime,
        # First-principles causticizing outputs
        gl_na2co3_g_L=gl_na2co3_g_L,
        gl_na2co3_lb_hr=gl_na2co3_lb_hr,
        conversion_fraction=conversion_fraction,
        lime_required_lb_hr=lime_required_lb_hr,
        lime_feed_lb_hr=lime_feed_lb_hr,
        achieved_ce_pct=achieved_ce_pct,
    )
