"""
NaSH and NaOH makeup calculations.

Reference: 0_SULFIDITY CONTROL MAKEUP sheet in Excel v4

FIX #3: NaSH formula supports both approaches:
  - Mass balance: H44 = Target*(H42+H40/2000) - (H43+CTO_S*1.9329/2000)
  - S deficit (v4): H44 = H41/1000
FIX #4: Uses exact MW constants, not rounded 0.411
"""

from dataclasses import dataclass
from typing import Dict, Optional

from .constants import MW, CONV, DEFAULTS


@dataclass
class MakeupRequirements:
    """Complete NaSH and NaOH makeup requirements."""
    # NaSH
    na2s_deficit_ton_hr: float
    nash_conversion_factor: float
    nash_dry_lbs_hr: float
    nash_solution_lbs_hr: float
    nash_solution_gpm: float
    # NaOH
    na_from_nash: float
    na_deficit_remaining: float
    naoh_dry_lbs_hr: float
    naoh_solution_lbs_hr: float
    naoh_solution_gpm: float
    # Per-BDT
    nash_dry_lb_bdt_na2o: float
    naoh_dry_lb_bdt_na2o: float
    saltcake_lb_bdt_na2o: float
    # Final WL
    final_tta_ton_hr: float
    final_na2s_ton_hr: float
    final_sulfidity_pct: float


def calculate_nash_requirement(
    target_sulfidity_pct: float,
    wl_tta_mass_ton_hr: float,
    wl_na2s_mass_ton_hr: float,
    na_deficit_lbs_hr: float,
    cto_s_lbs_hr: float = 0.0,
    s_deficit_lbs_hr: Optional[float] = None,
    s_deficit_na2o_lbs_hr: Optional[float] = None,
    s_deficit_element_lbs_hr: Optional[float] = None,
) -> Dict[str, float]:
    """
    Calculate required NaSH for steady-state S mass balance.

    RIGOROUS STEADY-STATE APPROACH
    ==============================
    At steady state, S entering the system must equal S leaving:

        S_in = S_out
        NaSH_S + Saltcake_S + CTO_S = Total_S_losses

    Therefore:
        NaSH_S = Total_S_losses - Saltcake_S - CTO_S = S_deficit (element)
        NaSH = S_deficit / (S/NaSH) = S_deficit / 0.572

    This is the ONLY way to close the S mass balance. The resulting sulfidity
    is determined by the system (slaker output + NaSH contribution - WLC losses),
    not independently controlled.

    The target_sulfidity_pct parameter is retained for compatibility but the
    actual sulfidity will be whatever results from the S-balanced NaSH addition.

    Calculation paths (in priority order):
    1. s_deficit_element_lbs_hr (NEW): Direct S element mass balance
       NaSH = s_deficit_element / S_in_NaSH (rigorous steady-state)
    2. s_deficit_lbs_hr (v4 override): H44 = H41/1000 (backward compatibility)
    3. s_deficit_na2o_lbs_hr: Convert from Na2O basis to element, then apply #1
    4. Na deficit fallback: Legacy approach (not recommended)
    """
    # S fraction in NaSH: S/NaSH = 32.065/56.06 = 0.572
    s_in_nash = CONV['S_in_NaSH']

    # Na2O per NaSH (for na2s_deficit reporting): Na2O/NaSH = 1.106
    conversion_factor = CONV['Na2O_per_NaSH']

    if s_deficit_element_lbs_hr is not None:
        # ══════════════════════════════════════════════════════════════════
        # RIGOROUS STEADY-STATE: Size NaSH directly from S element balance
        # NaSH × (S/NaSH) = S_deficit
        # NaSH = S_deficit / 0.572
        # ══════════════════════════════════════════════════════════════════
        nash_dry_lbs_hr = s_deficit_element_lbs_hr / s_in_nash
        # Convert to Na2O basis for reporting (NaSH × Na2O/NaSH)
        na2s_deficit_ton_hr = nash_dry_lbs_hr * conversion_factor / 2000

    elif s_deficit_lbs_hr is not None:
        # V4 approach: direct S deficit override (backward compatibility)
        # Assumes s_deficit_lbs_hr is in some intermediate unit
        na2s_deficit_ton_hr = s_deficit_lbs_hr / 1000
        nash_dry_lbs_hr = (na2s_deficit_ton_hr / conversion_factor) * 2000

    elif s_deficit_na2o_lbs_hr is not None:
        # Convert Na2O basis to element basis, then apply rigorous approach
        # S_element = S_na2o × (S/Na2O) = S_na2o / 1.9335
        s_deficit_element = s_deficit_na2o_lbs_hr / CONV['S_to_Na2O']
        nash_dry_lbs_hr = s_deficit_element / s_in_nash
        na2s_deficit_ton_hr = nash_dry_lbs_hr * conversion_factor / 2000

    else:
        # Legacy Na deficit fallback (not recommended - doesn't close S balance)
        target_sulf = target_sulfidity_pct / 100
        adjusted_tta = wl_tta_mass_ton_hr + (na_deficit_lbs_hr / 2000)
        na2s_deficit_ton_hr = (target_sulf * adjusted_tta) - wl_na2s_mass_ton_hr
        if conversion_factor > 0 and na2s_deficit_ton_hr > 0:
            nash_dry_lbs_hr = (na2s_deficit_ton_hr / conversion_factor) * 2000
        else:
            nash_dry_lbs_hr = 0.0

    nash_dry_lbs_hr = max(0.0, nash_dry_lbs_hr)

    return {
        'na2s_deficit_ton_hr': na2s_deficit_ton_hr,
        'conversion_factor': conversion_factor,
        'nash_dry_lbs_hr': nash_dry_lbs_hr,
    }


def calculate_naoh_requirement(
    na_deficit_lbs_hr: float, nash_dry_lbs_hr: float
) -> Dict[str, float]:
    """
    Calculate required NaOH after Na from NaSH.

    FIX: Uses exact CONV['NaSH_to_Na2O'] = 62/(2*56.06) instead of rounded 0.411.
    """
    na_from_nash = nash_dry_lbs_hr * CONV['NaSH_to_Na2O']
    na_deficit_remaining = na_deficit_lbs_hr - na_from_nash
    naoh_to_na2o = CONV['NaOH_to_Na2O']

    if naoh_to_na2o > 0 and na_deficit_remaining > 0:
        naoh_dry_lbs_hr = na_deficit_remaining / naoh_to_na2o
    else:
        naoh_dry_lbs_hr = 0.0

    return {
        'na_from_nash': na_from_nash,
        'na_deficit_remaining': na_deficit_remaining,
        'naoh_dry_lbs_hr': max(0.0, naoh_dry_lbs_hr),
    }


def calculate_solution_flow_rates(
    nash_dry_lbs_hr: float, naoh_dry_lbs_hr: float,
    nash_concentration: Optional[float] = None,
    naoh_concentration: Optional[float] = None,
    nash_density: Optional[float] = None,
    naoh_density: Optional[float] = None,
) -> Dict[str, float]:
    """Calculate solution flow rates from dry chemical rates."""
    nash_conc = nash_concentration or DEFAULTS['nash_concentration']
    naoh_conc = naoh_concentration or DEFAULTS['naoh_concentration']
    nash_dens = nash_density or DEFAULTS['nash_density']
    naoh_dens = naoh_density or DEFAULTS['naoh_density']

    nash_sol_lbs = nash_dry_lbs_hr / nash_conc if nash_conc > 0 else 0.0
    naoh_sol_lbs = naoh_dry_lbs_hr / naoh_conc if naoh_conc > 0 else 0.0

    nash_dens_lb_gal = nash_dens * 8.345
    naoh_dens_lb_gal = naoh_dens * 8.345

    nash_gpm = nash_sol_lbs / nash_dens_lb_gal / 60 if nash_dens_lb_gal > 0 else 0.0
    naoh_gpm = naoh_sol_lbs / naoh_dens_lb_gal / 60 if naoh_dens_lb_gal > 0 else 0.0

    return {
        'nash_solution_lbs_hr': nash_sol_lbs,
        'nash_solution_gpm': nash_gpm,
        'naoh_solution_lbs_hr': naoh_sol_lbs,
        'naoh_solution_gpm': naoh_gpm,
    }


def calculate_per_bdt_outputs(
    nash_dry_lbs_hr: float, naoh_dry_lbs_hr: float,
    saltcake_na_lbs_hr: float, total_production_bdt_day: float,
) -> Dict[str, float]:
    """Per-BDT outputs for NaSH, NaOH, saltcake."""
    if total_production_bdt_day <= 0:
        return {'nash_dry_lb_bdt_na2o': 0.0, 'naoh_dry_lb_bdt_na2o': 0.0,
                'saltcake_lb_bdt_na2o': 0.0}

    nash_lb_day = nash_dry_lbs_hr * 24
    nash_dry_lb_bdt = nash_lb_day / total_production_bdt_day
    nash_dry_lb_bdt_na2o = nash_dry_lb_bdt * CONV['NaSH_to_Na2O']

    naoh_as_na2o = naoh_dry_lbs_hr * CONV['NaOH_to_Na2O']
    naoh_dry_lb_bdt_na2o = (naoh_as_na2o * 24) / total_production_bdt_day

    saltcake_lb_bdt_na2o = (saltcake_na_lbs_hr * 24) / total_production_bdt_day

    return {
        'nash_dry_lb_bdt_na2o': nash_dry_lb_bdt_na2o,
        'naoh_dry_lb_bdt_na2o': naoh_dry_lb_bdt_na2o,
        'saltcake_lb_bdt_na2o': saltcake_lb_bdt_na2o,
    }


def calculate_final_wl_composition(
    initial_tta_ton_hr: float, initial_na2s_ton_hr: float,
    nash_dry_lbs_hr: float, naoh_dry_lbs_hr: float,
) -> Dict[str, float]:
    """
    Calculate final WL composition after makeup additions.

    NaSH CHEMISTRY NOTE — TWO DIFFERENT Na₂O FACTORS
    ═══════════════════════════════════════════════════
    NaSH has 1 Na atom (MW 56.06). Two conversion factors exist:

    1. Na₂O ADDED (mass balance): NaSH × 0.5529 = NaSH × Na₂O/(2×NaSH)
       NaSH brings 1 Na per molecule → 0.5 mol Na₂O equiv per mol NaSH.
       Use this for: TTA contribution, Na mass balance, "lb Na₂O/BDT" display.

    2. Na₂S tracking (sulfidity): NaSH × 1.1060 = NaSH × Na₂O/NaSH
       In alkaline WL, NaSH's sulfide (HS⁻) is tracked as Na₂S (which has 2 Na).
       The 1.1060 factor accounts for the NaSH+NaOH→Na₂S equilibrium where
       NaSH "borrows" Na from NaOH to form full Na₂S. This is an internal
       redistribution — TTA is unchanged, but Na₂S goes up and NaOH goes down.
       Use this ONLY for Na₂S/sulfidity calculations.
    """
    # TTA from NaSH: NaSH × Na₂O/(2×NaSH) = NaSH × 0.5529
    tta_from_nash = nash_dry_lbs_hr * CONV['NaSH_to_Na2O']
    # TTA from NaOH: NaOH × Na₂O/(2×NaOH) = NaOH × 0.775
    tta_from_naoh = naoh_dry_lbs_hr * CONV['NaOH_to_Na2O']
    # Na₂S from NaSH: NaSH × Na₂O/NaSH = NaSH × 1.106
    na2s_from_nash = nash_dry_lbs_hr * CONV['Na2O_per_NaSH']

    final_tta = initial_tta_ton_hr + (tta_from_nash + tta_from_naoh) / 2000
    final_na2s = initial_na2s_ton_hr + na2s_from_nash / 2000
    final_sulfidity = (final_na2s / final_tta * 100) if final_tta > 0 else 0.0

    return {
        'tta_from_nash_lbs_hr': tta_from_nash,
        'tta_from_naoh_lbs_hr': tta_from_naoh,
        'na2s_from_nash_lbs_hr': na2s_from_nash,
        'final_tta_ton_hr': final_tta,
        'final_na2s_ton_hr': final_na2s,
        'final_sulfidity_pct': final_sulfidity,
    }


def calculate_makeup_summary(
    target_sulfidity_pct: float,
    wl_tta_mass_ton_hr: float,
    wl_na2s_mass_ton_hr: float,
    na_deficit_lbs_hr: float,
    total_production_bdt_day: float,
    saltcake_na_lbs_hr: float = 0.0,
    cto_s_lbs_hr: float = 0.0,
    s_deficit_lbs_hr: Optional[float] = None,
    s_deficit_na2o_lbs_hr: Optional[float] = None,
    s_deficit_element_lbs_hr: Optional[float] = None,
    nash_concentration: Optional[float] = None,
    naoh_concentration: Optional[float] = None,
    nash_density: Optional[float] = None,
    naoh_density: Optional[float] = None,
) -> MakeupRequirements:
    """Calculate complete makeup requirements."""
    nash_result = calculate_nash_requirement(
        target_sulfidity_pct, wl_tta_mass_ton_hr, wl_na2s_mass_ton_hr,
        na_deficit_lbs_hr, cto_s_lbs_hr, s_deficit_lbs_hr,
        s_deficit_na2o_lbs_hr, s_deficit_element_lbs_hr,
    )
    naoh_result = calculate_naoh_requirement(
        na_deficit_lbs_hr, nash_result['nash_dry_lbs_hr']
    )
    flow_result = calculate_solution_flow_rates(
        nash_result['nash_dry_lbs_hr'], naoh_result['naoh_dry_lbs_hr'],
        nash_concentration, naoh_concentration, nash_density, naoh_density,
    )
    bdt_result = calculate_per_bdt_outputs(
        nash_result['nash_dry_lbs_hr'], naoh_result['naoh_dry_lbs_hr'],
        saltcake_na_lbs_hr, total_production_bdt_day,
    )
    final_result = calculate_final_wl_composition(
        wl_tta_mass_ton_hr, wl_na2s_mass_ton_hr,
        nash_result['nash_dry_lbs_hr'], naoh_result['naoh_dry_lbs_hr'],
    )

    return MakeupRequirements(
        na2s_deficit_ton_hr=nash_result['na2s_deficit_ton_hr'],
        nash_conversion_factor=nash_result['conversion_factor'],
        nash_dry_lbs_hr=nash_result['nash_dry_lbs_hr'],
        nash_solution_lbs_hr=flow_result['nash_solution_lbs_hr'],
        nash_solution_gpm=flow_result['nash_solution_gpm'],
        na_from_nash=naoh_result['na_from_nash'],
        na_deficit_remaining=naoh_result['na_deficit_remaining'],
        naoh_dry_lbs_hr=naoh_result['naoh_dry_lbs_hr'],
        naoh_solution_lbs_hr=flow_result['naoh_solution_lbs_hr'],
        naoh_solution_gpm=flow_result['naoh_solution_gpm'],
        nash_dry_lb_bdt_na2o=bdt_result['nash_dry_lb_bdt_na2o'],
        naoh_dry_lb_bdt_na2o=bdt_result['naoh_dry_lb_bdt_na2o'],
        saltcake_lb_bdt_na2o=bdt_result['saltcake_lb_bdt_na2o'],
        final_tta_ton_hr=final_result['final_tta_ton_hr'],
        final_na2s_ton_hr=final_result['final_na2s_ton_hr'],
        final_sulfidity_pct=final_result['final_sulfidity_pct'],
    )
