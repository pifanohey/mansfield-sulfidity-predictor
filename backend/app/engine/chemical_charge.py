"""
Chemical charge calculations — faithful reproduction of 3_Chemical Charge sheet.

Reference: 3_Chemical Charge in SULFIDITY_MODEL_CORRECTED_FINAL v4.xlsx

Implements:
- Semichem fiberline (C3-D25) and Pine fiberline (C29-D51)
- GL clarifier underflows (B62-B80)
- WLC (White Liquor Clarifier) section (T82-U112)
- Circular reference feedback: D41-D44 from U103-U107
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .constants import MW, CONV, DEFAULTS, GPM_GL_TO_TON_HR


@dataclass
class FiberlineResult:
    """Results for a single fiberline."""
    production_bdt_day: float
    wood_od_day: float
    ea_charge_pct: float
    wl_demand_gpm: float          # L11 or L37
    gl_to_digester_gpm: float     # G5 or 0 (only semichem uses GL)


@dataclass
class WLCResult:
    """White Liquor Clarifier results (T82-U112)."""
    total_wl_to_wlc_gpm: float       # U88
    underflow_gpm: float              # U89
    wl_overflow_gpm: float            # U91 — FINAL WL flow to digesters
    tta_lost_in_underflow_ton_hr: float  # U99
    na2s_lost_in_underflow_ton_hr: float  # U100
    final_tta_mass_ton_hr: float      # U101
    final_na2s_mass_ton_hr: float     # U102
    final_sulfidity_pct: float        # U103
    final_tta_g_L: float              # U104
    final_na2s_g_L: float             # U105
    final_ea_g_L: float               # U107
    final_aa_g_L: float               # U106


@dataclass
class ChemicalChargeResults:
    """Complete results from chemical charge calculations."""
    # Fiberlines
    semichem: FiberlineResult
    pine: FiberlineResult
    total_production_bdt_day: float
    total_wl_demand_gpm: float        # U110 = L11 + L37
    semichem_gl_gpm: float            # G5 — feeds into dissolving tank I58

    # GL clarifier
    dregs_underflow_gpm: float        # B69

    # WL from slaker (before WLC)
    wl_flow_from_slaker_gpm: float    # K65
    wl_tta_mass_ton_hr: float         # N69
    wl_na2s_mass_ton_hr: float        # K67
    wl_sulfidity_pct: float           # N70

    # WLC
    wlc: Optional[WLCResult]

    # Initial sulfidity (before makeup, before WLC)
    initial_sulfidity_pct: float


def calculate_fiberline(
    production_bdt_day: float,
    yield_pct: float,
    ea_pct: float,
    wl_ea_g_L: float = 85.0,
    gl_to_digester_gpm: float = 0.0,
) -> FiberlineResult:
    """
    Calculate fiberline WL demand for a single line.

    D9 = D7/D8 (wood OD/day)
    D12: EA% charge on OD wood
    L11/L37: WL demand (gpm) = (EA_needed_lb_hr) / (wl_EA_g_L * 0.5007)
    G5: GL flow for semichem — computed externally via ((G7*1000)/24/60)/3.785
    """
    if yield_pct <= 0:
        yield_pct = 0.5

    wood_od_day = production_bdt_day / yield_pct

    # WL demand: EA_charge * OD_wood -> lb EA/hr -> gpm via WL EA concentration
    ea_needed_lb_day = wood_od_day * ea_pct * 2000  # BDT -> lb, * EA fraction
    ea_needed_lb_hr = ea_needed_lb_day / 24

    if wl_ea_g_L > 0:
        wl_demand_gpm = ea_needed_lb_hr / (wl_ea_g_L * CONV['GPM_GL_TO_LB_HR'])
    else:
        wl_demand_gpm = 0.0

    return FiberlineResult(
        production_bdt_day=production_bdt_day,
        wood_od_day=wood_od_day,
        ea_charge_pct=ea_pct,
        wl_demand_gpm=wl_demand_gpm,
        gl_to_digester_gpm=gl_to_digester_gpm,
    )


def calculate_wlc(
    wl_flow_from_slaker_gpm: float,
    wl_tta_mass_ton_hr: float,
    wl_na2s_mass_ton_hr: float,
    wl_sulfidity: float,
    wl_tta_g_L: float,
    # Makeup additions (gpm)
    nash_gpm: float = 0.0,
    naoh_gpm: float = 0.0,
    # Makeup mass additions (ton Na2O/hr)
    tta_from_makeup_ton_hr: float = 0.0,
    na2s_from_makeup_ton_hr: float = 0.0,
    # NaOH mass tracking (ton Na2O/hr)
    wl_naoh_mass_ton_hr: float = 0.0,
    naoh_from_makeup_ton_hr: float = 0.0,
    # Grits removal (entrained WL liquor lost with grits at slaker)
    grits_entrained_gpm: float = 0.0,
    # Water inputs
    intrusion_water_gpm: float = 28.0,
    dilution_water_gpm: float = 23.856,
    # Underflow parameters
    underflow_solids_pct: float = 0.4097,
    mud_density: float = 1.33,
    lime_mud_lb_hr: float = 0.0,
    causticity: float = 0.81,
) -> WLCResult:
    """
    White Liquor Clarifier model (3_Chem T82-U112).

    U88: total WL to WLC = slaker_flow + NaSH_gpm + NaOH_gpm + intrusion + dilution
    U89: underflow gpm (from lime mud settling)
    U91: FINAL WL overflow = U88 - U89
    U99-U100: TTA/Na2S lost in underflow
    U101-U105: FINAL composition
    """
    # U88: Total flow into WLC
    # Grits are removed at the slaker — entrained WL liquor leaves with grits
    total_wl_to_wlc = (wl_flow_from_slaker_gpm - grits_entrained_gpm
                        + nash_gpm + naoh_gpm
                        + intrusion_water_gpm + dilution_water_gpm)

    # U89: Underflow is a slurry — lime_mud_lb_hr is only the dry CaCO3 solids.
    # Total slurry mass = dry_solids / solids_weight_fraction.
    # Then convert lb/hr to GPM using slurry density.
    if mud_density > 0 and lime_mud_lb_hr > 0 and underflow_solids_pct > 0:
        total_underflow_lb_hr = lime_mud_lb_hr / underflow_solids_pct
        underflow_gpm = total_underflow_lb_hr / (mud_density * 8.345 * 60)
    else:
        underflow_gpm = total_wl_to_wlc * 0.05  # ~5% underflow fallback

    # U91: WL overflow (to digesters)
    wl_overflow = total_wl_to_wlc - underflow_gpm

    # Total TTA and Na2S entering WLC (from slaker + makeup)
    total_tta = wl_tta_mass_ton_hr + tta_from_makeup_ton_hr
    total_na2s = wl_na2s_mass_ton_hr + na2s_from_makeup_ton_hr
    total_sulfidity = total_na2s / total_tta if total_tta > 0 else 0.0

    # U99: TTA lost in underflow
    # The underflow is a SLURRY — only the liquid portion carries dissolved chemicals.
    # underflow_solids_pct (P90 ≈ 0.4097) is the WEIGHT fraction of solids (CaCO3).
    # Convert to VOLUME fraction of liquid using density ratio:
    #   CaCO3 density ≈ 2.71 SG, WL density ≈ 1.135 SG
    #   vol_frac_liquid = ((1-w_s)/ρ_liq) / (w_s/ρ_solid + (1-w_s)/ρ_liq)
    if total_wl_to_wlc > 0 and underflow_solids_pct > 0:
        CACO3_DENSITY_SG = 2.71
        WL_DENSITY_SG = 1.135
        w_s = underflow_solids_pct
        vol_frac_liquid = ((1 - w_s) / WL_DENSITY_SG) / \
                          (w_s / CACO3_DENSITY_SG + (1 - w_s) / WL_DENSITY_SG)
        liquid_in_underflow = underflow_gpm * vol_frac_liquid
        underflow_fraction = liquid_in_underflow / total_wl_to_wlc
    else:
        underflow_fraction = 0.0

    tta_lost = total_tta * underflow_fraction
    # U100: Na2S lost = TTA_lost * sulfidity
    na2s_lost = tta_lost * total_sulfidity

    # U101: FINAL TTA mass = total - lost
    final_tta = total_tta - tta_lost
    # U102: FINAL Na2S mass = total - lost
    final_na2s = total_na2s - na2s_lost

    # U103: FINAL sulfidity
    final_sulfidity = (final_na2s / final_tta * 100) if final_tta > 0 else 0.0

    # U104: FINAL TTA g/L = (final_tta * 2000 * 453.6) / (wl_overflow * 3.785 * 60)
    if wl_overflow > 0:
        final_tta_g_L = (final_tta * 2000 * 453.6) / (wl_overflow * 3.785 * 60)
    else:
        final_tta_g_L = 0.0

    # U105: FINAL Na2S g/L
    final_na2s_g_L = final_tta_g_L * (final_sulfidity / 100)

    # NaOH: mass-tracked through WLC (not recomputed from CE)
    # CE describes the causticizing reaction equilibrium in the slaker.
    # After NaOH makeup addition, the actual causticity changes and CE
    # should not be re-applied to derive NaOH. Instead, track NaOH mass:
    #   total NaOH = slaker NaOH + makeup NaOH
    #   lost NaOH = total × underflow_fraction (same as TTA/Na2S)
    #   final NaOH = total - lost
    total_naoh_mass = wl_naoh_mass_ton_hr + naoh_from_makeup_ton_hr
    naoh_lost = total_naoh_mass * underflow_fraction
    final_naoh_mass = total_naoh_mass - naoh_lost

    conv_out = CONV['GPM_GL_TO_LB_HR'] / 2000  # gpm × g/L → ton/hr
    if wl_overflow > 0 and conv_out > 0:
        naoh_g_L = final_naoh_mass / (wl_overflow * conv_out)
    else:
        naoh_g_L = 0.0

    # U106: AA (g Na2O/L) = NaOH + Na2S
    final_aa_g_L = naoh_g_L + final_na2s_g_L

    # U107: EA (g Na2O/L) = NaOH + ½Na2S
    final_ea_g_L = naoh_g_L + 0.5 * final_na2s_g_L

    return WLCResult(
        total_wl_to_wlc_gpm=total_wl_to_wlc,
        underflow_gpm=underflow_gpm,
        wl_overflow_gpm=wl_overflow,
        tta_lost_in_underflow_ton_hr=tta_lost,
        na2s_lost_in_underflow_ton_hr=na2s_lost,
        final_tta_mass_ton_hr=final_tta,
        final_na2s_mass_ton_hr=final_na2s,
        final_sulfidity_pct=final_sulfidity,
        final_tta_g_L=final_tta_g_L,
        final_na2s_g_L=final_na2s_g_L,
        final_ea_g_L=final_ea_g_L,
        final_aa_g_L=final_aa_g_L,
    )


def calculate_chemical_charge(
    gl_flow_to_slaker_gpm: float,
    yield_factor: float,
    wl_tta_g_L: float,
    wl_na2s_g_L: float,
    batch_production_bdt_day: float,
    cont_production_bdt_day: float,
    # WL composition for demand calc
    wl_ea_g_L: float = 85.0,
    wl_sulfidity: float = 0.283,
    # GL composition (from dissolving tank, part of circular reference)
    gl_tta_g_L: float = 117.0,
    gl_na2s_g_L: float = 31.74,
    gl_aa_g_L: float = 43.65,
    # Fiberline parameters
    semichem_yield: float = 0.7019,
    pine_yield: float = 0.5694,
    semichem_ea_pct: float = 0.0365,
    pine_ea_pct: float = 0.122,
    # GL clarifier underflows
    dregs_underflow_gpm: float = 12.9,
    # Semichem GL charge (Excel 3_Chem G5-G17)
    # G13 = EA% from GL on OD wood; G7 = CALCULATED from GL EA and wood demand
    # G5 = ((G7×1000)/24/60)/3.785 — GL flow to semichem digester (gpm)
    semichem_gl_ea_pct: float = 0.017,
) -> ChemicalChargeResults:
    """
    Calculate chemical charge for both fiberlines.

    Returns WL flow, mass flows, fiberline demands, and GL clarifier underflows.
    The semichem fiberline uses both WL and GL for cooking:
    - WL provides EA at semichem_ea_pct (D12 = 0.0365)
    - GL provides EA at semichem_gl_ea_pct (G13 = 0.017)
    G7 (GL volume) is CALCULATED from GL EA concentration and wood demand.
    G5 feeds back into the dissolving tank I58 as part of the circular reference.
    """
    # ── Semichem GL charge (G5-G17) ──
    # G12 = wood OD (short ton/day) = batch_production / semichem_yield
    # G13 = GL EA% charge = 0.017
    # G11 = GL EA needed (short ton Na2O/day) = G12 × G13
    # G9 = GL EA (g Na2O/L) = GL AA - 0.5 × GL Na2S
    # G7 = (G11 × 907.185) / G9 (m³/day)
    # G5 = ((G7 × 1000) / 24 / 60) / 3.785 (gpm)
    wood_od_semichem = batch_production_bdt_day / semichem_yield if semichem_yield > 0 else 0.0
    gl_ea_needed_ton_day = wood_od_semichem * semichem_gl_ea_pct  # G11
    gl_ea_g_L = gl_aa_g_L - 0.5 * gl_na2s_g_L  # G9 = D64

    if gl_ea_g_L > 0 and semichem_gl_ea_pct > 0:
        g7 = (gl_ea_needed_ton_day * CONV['KG_PER_SHORT_TON']) / gl_ea_g_L  # m³/day
        semichem_gl_gpm = (g7 * 1000) / (24 * 60 * 3.785)  # G5
    else:
        semichem_gl_gpm = 0.0

    # WL flow from slaker
    wl_flow = gl_flow_to_slaker_gpm * yield_factor

    # WL mass flows
    conv = CONV['GPM_GL_TO_LB_HR'] / 2000  # gpm * g/L -> ton/hr
    wl_tta_mass = wl_flow * wl_tta_g_L * conv
    wl_na2s_mass = wl_flow * wl_na2s_g_L * conv

    initial_sulfidity = (wl_na2s_mass / wl_tta_mass * 100) if wl_tta_mass > 0 else 0.0
    total_production = batch_production_bdt_day + cont_production_bdt_day

    # Semichem fiberline — uses both WL and GL
    semichem = calculate_fiberline(
        production_bdt_day=batch_production_bdt_day,
        yield_pct=semichem_yield,
        ea_pct=semichem_ea_pct,
        wl_ea_g_L=wl_ea_g_L,
        gl_to_digester_gpm=semichem_gl_gpm,
    )

    # Pine fiberline — uses WL only
    pine = calculate_fiberline(
        production_bdt_day=cont_production_bdt_day,
        yield_pct=pine_yield,
        ea_pct=pine_ea_pct,
        wl_ea_g_L=wl_ea_g_L,
    )

    total_wl_demand = semichem.wl_demand_gpm + pine.wl_demand_gpm

    return ChemicalChargeResults(
        semichem=semichem,
        pine=pine,
        total_production_bdt_day=total_production,
        total_wl_demand_gpm=total_wl_demand,
        semichem_gl_gpm=semichem_gl_gpm,
        dregs_underflow_gpm=dregs_underflow_gpm,
        wl_flow_from_slaker_gpm=wl_flow,
        wl_tta_mass_ton_hr=wl_tta_mass,
        wl_na2s_mass_ton_hr=wl_na2s_mass,
        wl_sulfidity_pct=initial_sulfidity,
        wlc=None,
        initial_sulfidity_pct=initial_sulfidity,
    )
