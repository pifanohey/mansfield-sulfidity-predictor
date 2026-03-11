"""
Fiberline Black Liquor generation and WBL mixing.

Computes BL output from each digester line (the forward leg of the mass balance).
chemical_charge.py computes WL demand; this module computes what comes *out*.

Design decisions:
  - Solids tracked as compound masses (not elements) per PRD §4.4
  - CTO enters physically as WBL mixer input (not accounting credit) per PRD §4.1
  - S loss in digester modeled as proportional Na2S loss to NCG/turpentine
"""

from dataclasses import dataclass
from typing import List

from .constants import MW, CONV


@dataclass
class FiberlineBLOutput:
    """Black liquor output from a single fiberline (digester)."""
    wbl_flow_lb_hr: float         # Total WBL mass flow
    wbl_tds_pct: float            # Total dissolved solids %
    wbl_na_pct_ds: float          # Na element % on dry solids
    wbl_s_pct_ds: float           # S element % on dry solids
    na_element_lb_hr: float       # Na element flow (for mass balance)
    s_element_lb_hr: float        # S element flow (for mass balance)
    inorganic_solids_lb_hr: float # Inorganic compound mass (incl. oxygen)
    organics_lb_hr: float         # Dissolved wood organics
    total_solids_lb_hr: float     # inorganic + organics
    water_lb_hr: float            # Total water (WL water + wood water)


@dataclass
class MixedWBLOutput:
    """Combined WBL from all fiberlines + CTO brine."""
    total_flow_lb_hr: float
    total_solids_lb_hr: float
    water_lb_hr: float
    na_element_lb_hr: float
    s_element_lb_hr: float
    na_pct_ds: float              # Na% on dry solids
    s_pct_ds: float               # S% on dry solids
    tds_pct: float                # Total dissolved solids %


def calculate_fiberline_bl(
    production_bdt_day: float,
    yield_pct: float,
    wl_flow_gpm: float,
    wl_na2s_g_L: float,
    wl_naoh_g_L: float,
    wl_na2co3_g_L: float,
    wood_moisture_pct: float = 0.523,
    s_loss_digester_pct: float = 0.02,  # Deprecated: use ncg_s_lb_bdt instead
    # NCG S loss from loss table (replaces s_loss_digester_pct)
    ncg_s_lb_bdt: float = 0.0,
    total_production_bdt_day: float = 0.0,
    # Optional GL charge (semichem uses GL + WL for cooking)
    gl_flow_gpm: float = 0.0,
    gl_na2s_g_L: float = 0.0,
    gl_naoh_g_L: float = 0.0,
    gl_na2co3_g_L: float = 0.0,
) -> FiberlineBLOutput:
    """
    Calculate Black Liquor output from a single fiberline.

    WL and optional GL species are in g Na2O/L (from slaker/dissolving tank).
    Converts to actual compound mass to properly account for oxygen weight.
    Semichem fiberline receives both WL and GL for cooking — the GL inorganics
    (especially Na2S) must be included or BL S% will be understated.

    Args:
        production_bdt_day: Pulp production (bone-dry ton/day)
        yield_pct: Pulp yield fraction (e.g., 0.5694 for pine)
        wl_flow_gpm: WL consumed by this fiberline (from chemical_charge)
        wl_na2s_g_L: WL Na2S in g Na2O/L
        wl_naoh_g_L: WL NaOH in g Na2O/L
        wl_na2co3_g_L: WL Na2CO3 in g Na2O/L
        wood_moisture_pct: Moisture fraction of green wood
        s_loss_digester_pct: Fraction of S lost to NCG/turpentine
        gl_flow_gpm: GL consumed by this fiberline (0 for pine, ~99 for semichem)
        gl_na2s_g_L: GL Na2S in g Na2O/L
        gl_naoh_g_L: GL NaOH in g Na2O/L (AA - Na2S)
        gl_na2co3_g_L: GL Na2CO3 in g Na2O/L (TTA - AA)
        ncg_s_lb_bdt: NCG S loss from loss table (lb S/BDT). When > 0, this replaces
            the arbitrary s_loss_digester_pct with exact loss table value.
        total_production_bdt_day: Total production (BDT/day) for loss allocation.
            Used to convert lb/BDT to lb/hr and allocate proportionally to this fiberline.
    """
    if yield_pct <= 0 or production_bdt_day <= 0:
        return FiberlineBLOutput(
            wbl_flow_lb_hr=0, wbl_tds_pct=0, wbl_na_pct_ds=0, wbl_s_pct_ds=0,
            na_element_lb_hr=0, s_element_lb_hr=0, inorganic_solids_lb_hr=0,
            organics_lb_hr=0, total_solids_lb_hr=0, water_lb_hr=0,
        )

    # ── Wood dissolution ──
    wood_od_ton_day = production_bdt_day / yield_pct
    dissolved_wood_ton_day = wood_od_ton_day - production_bdt_day
    organics_lb_hr = dissolved_wood_ton_day * 2000 / 24

    # ── Wood water contribution ──
    if wood_moisture_pct < 1.0:
        wood_green_ton_day = wood_od_ton_day / (1 - wood_moisture_pct)
    else:
        wood_green_ton_day = wood_od_ton_day
    wood_water_lb_hr = (wood_green_ton_day - wood_od_ton_day) * 2000 / 24

    # ── Inorganic pass-through (compound masses, NOT elements) ──
    # WL species in g Na2O/L → convert to actual compound lb/hr
    # CONV['GPM_GL_TO_LB_HR'] converts gpm × g/L → lb/hr
    wl_lb_hr_factor = wl_flow_gpm * CONV['GPM_GL_TO_LB_HR']

    na2s_compound_lb_hr = wl_na2s_g_L * wl_lb_hr_factor * CONV['Na2S_to_compound']
    naoh_compound_lb_hr = wl_naoh_g_L * wl_lb_hr_factor * CONV['NaOH_to_compound']
    na2co3_compound_lb_hr = wl_na2co3_g_L * wl_lb_hr_factor * CONV['Na2CO3_to_compound']

    # ── GL inorganic contribution (semichem uses GL for cooking) ──
    if gl_flow_gpm > 0:
        gl_lb_hr_factor = gl_flow_gpm * CONV['GPM_GL_TO_LB_HR']
        na2s_compound_lb_hr += gl_na2s_g_L * gl_lb_hr_factor * CONV['Na2S_to_compound']
        naoh_compound_lb_hr += gl_naoh_g_L * gl_lb_hr_factor * CONV['NaOH_to_compound']
        na2co3_compound_lb_hr += gl_na2co3_g_L * gl_lb_hr_factor * CONV['Na2CO3_to_compound']

    # ── S element from Na2S (for Na%/S% calculation) ──
    s_in_na2s_lb_hr = na2s_compound_lb_hr * (MW['S'] / MW['Na2S'])

    # NOTE: NCG S losses are NOT subtracted here. The WL/GL composition already
    # reflects steady-state conditions where NCG (and all other) losses have been
    # occurring. The WL Na2S concentration is the RESULT of the cycle including
    # all losses. Subtracting NCG again would double-count:
    #   1st count: WL Na2S is lower than it would be without NCG (cycle effect)
    #   2nd count: explicit subtraction here
    # NCG losses are tracked in the unified loss table for NaSH/NaOH sizing only.
    s_lost_lb_hr = 0.0

    # ── Inorganic solids (compound mass, includes oxygen) ──
    inorganic_solids_lb_hr = na2s_compound_lb_hr + naoh_compound_lb_hr + na2co3_compound_lb_hr

    # ── Total dry solids ──
    total_solids_lb_hr = inorganic_solids_lb_hr + organics_lb_hr

    # ── Liquor water (total liquor mass - dissolved inorganic solids) ──
    # WL total mass: gpm × density_lb_gal × 60 min/hr
    # density_kg_L × 8.345 = density_lb_gal (1 kg/L water = 8.345 lb/gal)
    wl_total_mass_lb_hr = wl_flow_gpm * CONV['WL_DENSITY_KG_L'] * 8.345 * 60
    wl_water_lb_hr = wl_total_mass_lb_hr - (
        wl_na2s_g_L * wl_lb_hr_factor * CONV['Na2S_to_compound']
        + wl_naoh_g_L * wl_lb_hr_factor * CONV['NaOH_to_compound']
        + wl_na2co3_g_L * wl_lb_hr_factor * CONV['Na2CO3_to_compound']
    )

    # GL water contribution (GL density ~1.15 kg/L)
    gl_water_lb_hr = 0.0
    if gl_flow_gpm > 0:
        GL_DENSITY_KG_L = 1.15
        gl_total_mass_lb_hr = gl_flow_gpm * GL_DENSITY_KG_L * 8.345 * 60
        gl_water_lb_hr = gl_total_mass_lb_hr - (
            gl_na2s_g_L * gl_lb_hr_factor * CONV['Na2S_to_compound']
            + gl_naoh_g_L * gl_lb_hr_factor * CONV['NaOH_to_compound']
            + gl_na2co3_g_L * gl_lb_hr_factor * CONV['Na2CO3_to_compound']
        )
    liquor_water_lb_hr = wl_water_lb_hr + gl_water_lb_hr

    # ── Na and S as elements (for Na%, S% d.s. calculation) ──
    na_from_na2s = na2s_compound_lb_hr * (2 * MW['Na'] / MW['Na2S'])
    na_from_naoh = naoh_compound_lb_hr * (MW['Na'] / MW['NaOH'])
    na_from_na2co3 = na2co3_compound_lb_hr * (2 * MW['Na'] / MW['Na2CO3'])
    na_element_lb_hr = na_from_na2s + na_from_naoh + na_from_na2co3

    s_element_lb_hr = s_in_na2s_lb_hr - s_lost_lb_hr

    # ── WBL stream properties ──
    total_water_lb_hr = liquor_water_lb_hr + wood_water_lb_hr
    total_flow_lb_hr = total_solids_lb_hr + total_water_lb_hr

    wbl_tds_pct = (total_solids_lb_hr / total_flow_lb_hr * 100) if total_flow_lb_hr > 0 else 0.0
    wbl_na_pct_ds = (na_element_lb_hr / total_solids_lb_hr * 100) if total_solids_lb_hr > 0 else 0.0
    wbl_s_pct_ds = (s_element_lb_hr / total_solids_lb_hr * 100) if total_solids_lb_hr > 0 else 0.0

    return FiberlineBLOutput(
        wbl_flow_lb_hr=total_flow_lb_hr,
        wbl_tds_pct=wbl_tds_pct,
        wbl_na_pct_ds=wbl_na_pct_ds,
        wbl_s_pct_ds=wbl_s_pct_ds,
        na_element_lb_hr=na_element_lb_hr,
        s_element_lb_hr=s_element_lb_hr,
        inorganic_solids_lb_hr=inorganic_solids_lb_hr,
        organics_lb_hr=organics_lb_hr,
        total_solids_lb_hr=total_solids_lb_hr,
        water_lb_hr=total_water_lb_hr,
    )


def mix_wbl_streams(
    bl_outputs: List[FiberlineBLOutput],
    cto_na_lb_hr: float = 0.0,
    cto_s_lb_hr: float = 0.0,
    cto_water_lb_hr: float = 0.0,
    dead_load_s_lb_hr: float = 0.0,
) -> MixedWBLOutput:
    """
    Combine WBL streams from one or more fiberlines and add CTO brine.

    CTO is modeled as Na2SO4 brine — its Na and S add to the mixed stream.
    CTO solids = Na2SO4 compound mass from Na + S.

    Dead load Na2SO4 (unreduced S from RB) cycles through DT → GL → WLC → WL →
    digester → BL but is not part of TTA (not tracked by liquor chemistry).
    The steady-state dead load is computed analytically by the orchestrator as:

        d = max(0, (S_tracked + CTO_S - S_losses) × (1-RE) / RE)

    This formula accounts for S losses draining the dead load each cycle,
    preventing artificial S accumulation in the forward leg. At high RE (95%),
    dead load is small. At low RE (82%), it significantly raises BL S%.

    Args:
        bl_outputs: List of fiberline BL outputs to mix
        cto_na_lb_hr: CTO Na element contribution (lb/hr)
        cto_s_lb_hr: CTO S element contribution (lb/hr)
        cto_water_lb_hr: CTO brine water (lb/hr)
        dead_load_s_lb_hr: Steady-state dead load Na2SO4 S (lb S/hr).
            Computed analytically by orchestrator to account for cycle losses.
    """
    # CTO enters as Na2SO4: compute compound mass from elements
    # Na2SO4 has 2 Na + 1 S + 4 O
    # cto_na_lb_hr and cto_s_lb_hr are element masses
    # Na2SO4_mass = cto_na × (Na2SO4 / (2×Na)) or cto_s × (Na2SO4 / S)
    # Use S-based since that's the primary tracking variable
    if cto_s_lb_hr > 0:
        cto_na2so4_lb_hr = cto_s_lb_hr * (MW['Na2SO4'] / MW['S'])
    else:
        cto_na2so4_lb_hr = 0.0

    # Dead load Na2SO4: convert S element to compound mass and Na element.
    # Na2SO4 has 2 Na atoms and 1 S atom.
    dl_na2so4_lb_hr = dead_load_s_lb_hr * (MW['Na2SO4'] / MW['S'])
    dl_na_lb_hr = dead_load_s_lb_hr * (2 * MW['Na'] / MW['S'])

    total_na = sum(bl.na_element_lb_hr for bl in bl_outputs) + cto_na_lb_hr + dl_na_lb_hr
    total_s = sum(bl.s_element_lb_hr for bl in bl_outputs) + cto_s_lb_hr + dead_load_s_lb_hr
    total_solids = sum(bl.total_solids_lb_hr for bl in bl_outputs) + cto_na2so4_lb_hr + dl_na2so4_lb_hr
    total_water = sum(bl.water_lb_hr for bl in bl_outputs) + cto_water_lb_hr

    total_flow = total_solids + total_water

    na_pct_ds = (total_na / total_solids * 100) if total_solids > 0 else 0.0
    s_pct_ds = (total_s / total_solids * 100) if total_solids > 0 else 0.0
    tds_pct = (total_solids / total_flow * 100) if total_flow > 0 else 0.0

    return MixedWBLOutput(
        total_flow_lb_hr=total_flow,
        total_solids_lb_hr=total_solids,
        water_lb_hr=total_water,
        na_element_lb_hr=total_na,
        s_element_lb_hr=total_s,
        na_pct_ds=na_pct_ds,
        s_pct_ds=s_pct_ds,
        tds_pct=tds_pct,
    )
