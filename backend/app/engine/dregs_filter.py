"""
Dregs filter mass balance model.

The dregs filter separates GLC underflow slurry into:
  - Cake (36.5% solids) → lost to landfill
  - Filtrate → returns to weak wash tank

This module calculates the filtrate properties and how it affects weak wash TTA.

Mass balance:
  GLC underflow (7.7% solids, GL concentration)
  + Shower water (fresh, TTA=0)
  = Cake (36.5% solids, lost)
  + Filtrate (diluted, returns to WW)
"""

from dataclasses import dataclass


@dataclass
class DregsFilterResult:
    """Dregs filter mass balance results."""
    # Inputs
    glc_underflow_solids_lb_hr: float   # Dry dregs solids
    glc_underflow_total_lb_hr: float    # Total GLC underflow slurry
    glc_liquor_lb_hr: float             # GL liquor in underflow (at GL concentration)

    # Shower water
    shower_water_lb_hr: float           # Fresh water added to filter

    # Cake output (LOST)
    cake_total_lb_hr: float             # Total cake mass (36.5% solids)
    cake_solids_lb_hr: float            # Solids in cake (same as input)
    cake_liquor_lb_hr: float            # Liquor LOST in cake

    # Filtrate output (RETURNS to WW)
    filtrate_lb_hr: float               # Total filtrate mass
    filtrate_tta_g_L: float             # Filtrate TTA (diluted by shower)
    filtrate_gpm: float                 # Filtrate flow rate

    # Net liquor lost (for GL flow correction)
    net_liquor_lost_lb_hr: float        # Only cake liquor is lost
    net_liquor_lost_gpm: float          # For GL flow subtraction

    # Mass balance check
    mass_balance_error_pct: float       # Should be ~0


def calculate_dregs_filter(
    dregs_solids_lb_hr: float,
    glc_underflow_solids_pct: float,
    gl_tta_g_L: float,
    gl_density_lb_gal: float,
    shower_ratio: float = 6.0,
    cake_solids_pct: float = 0.365,
) -> DregsFilterResult:
    """
    Calculate dregs filter mass balance.

    Args:
        dregs_solids_lb_hr: Dry dregs solids flow (lb/hr)
        glc_underflow_solids_pct: GLC underflow solids fraction (0.077 = 7.7%)
        gl_tta_g_L: Green liquor TTA concentration (g/L)
        gl_density_lb_gal: Green liquor density (lb/gal)
        shower_ratio: Wash water per lb solids (default 6.0)
        cake_solids_pct: Filter cake solids fraction (0.365 = 36.5%)

    Returns:
        DregsFilterResult with all mass balance values
    """
    # GLC underflow calculation
    if glc_underflow_solids_pct > 0:
        glc_underflow_total = dregs_solids_lb_hr / glc_underflow_solids_pct
    else:
        glc_underflow_total = 0.0
    glc_liquor = glc_underflow_total - dregs_solids_lb_hr

    # Shower water
    shower_water = dregs_solids_lb_hr * shower_ratio

    # Cake output (lost)
    if cake_solids_pct > 0:
        cake_total = dregs_solids_lb_hr / cake_solids_pct
    else:
        cake_total = dregs_solids_lb_hr
    cake_liquor = cake_total - dregs_solids_lb_hr

    # Filtrate output (returns to WW)
    # Mass balance: glc_liquor + shower = cake_liquor + filtrate
    filtrate = glc_liquor + shower_water - cake_liquor

    # Filtrate TTA calculation
    # TTA in = glc_liquor × gl_tta + shower × 0
    # TTA out = cake_liquor × cake_tta + filtrate × filtrate_tta
    # Assume equilibrium: cake_liquor and filtrate have same TTA
    # So: glc_liquor × gl_tta = (cake_liquor + filtrate) × filtrate_tta
    total_liquor_out = cake_liquor + filtrate
    if total_liquor_out > 0:
        filtrate_tta = (glc_liquor * gl_tta_g_L) / total_liquor_out
    else:
        filtrate_tta = 0.0

    # Convert filtrate to gpm
    # Filtrate density is lower than GL (diluted) - approximate as 8.5 lb/gal
    filtrate_density = 8.5  # lb/gal (diluted liquor)
    filtrate_gpm = filtrate / (filtrate_density * 60) if filtrate_density > 0 else 0.0

    # Net liquor lost (only cake liquor)
    net_liquor_lost = cake_liquor
    net_liquor_lost_gpm = net_liquor_lost / (gl_density_lb_gal * 60) if gl_density_lb_gal > 0 else 0.0

    # Mass balance check
    mass_in = glc_underflow_total + shower_water
    mass_out = cake_total + filtrate
    mass_balance_error = abs(mass_in - mass_out) / mass_in * 100 if mass_in > 0 else 0.0

    return DregsFilterResult(
        glc_underflow_solids_lb_hr=dregs_solids_lb_hr,
        glc_underflow_total_lb_hr=glc_underflow_total,
        glc_liquor_lb_hr=glc_liquor,
        shower_water_lb_hr=shower_water,
        cake_total_lb_hr=cake_total,
        cake_solids_lb_hr=dregs_solids_lb_hr,
        cake_liquor_lb_hr=cake_liquor,
        filtrate_lb_hr=filtrate,
        filtrate_tta_g_L=filtrate_tta,
        filtrate_gpm=filtrate_gpm,
        net_liquor_lost_lb_hr=net_liquor_lost,
        net_liquor_lost_gpm=net_liquor_lost_gpm,
        mass_balance_error_pct=mass_balance_error,
    )


def calculate_mixed_ww_tta(
    ww_flow_gpm: float,
    ww_tta_g_L: float,
    filtrate_gpm: float,
    filtrate_tta_g_L: float,
    ww_density_lb_gal: float = 8.34,
    filtrate_density_lb_gal: float = 8.5,
) -> tuple[float, float]:
    """
    Calculate mixed weak wash properties when dregs filtrate returns.

    The filtrate from the dregs filter returns to the weak wash tank,
    increasing the overall WW TTA concentration.

    Args:
        ww_flow_gpm: Base weak wash flow (gpm)
        ww_tta_g_L: Base weak wash TTA (g/L)
        filtrate_gpm: Dregs filter filtrate flow (gpm)
        filtrate_tta_g_L: Filtrate TTA (g/L)
        ww_density_lb_gal: Weak wash density (lb/gal)
        filtrate_density_lb_gal: Filtrate density (lb/gal)

    Returns:
        tuple of (mixed_flow_gpm, mixed_tta_g_L)
    """
    # Convert to mass flows
    ww_mass_lb_hr = ww_flow_gpm * ww_density_lb_gal * 60
    filtrate_mass_lb_hr = filtrate_gpm * filtrate_density_lb_gal * 60

    # Total mass
    total_mass_lb_hr = ww_mass_lb_hr + filtrate_mass_lb_hr

    if total_mass_lb_hr <= 0:
        return (ww_flow_gpm, ww_tta_g_L)

    # TTA mass balance (weighted average)
    # TTA_mixed = (WW_mass × WW_TTA + Filtrate_mass × Filtrate_TTA) / Total_mass
    total_tta_mass = ww_mass_lb_hr * ww_tta_g_L + filtrate_mass_lb_hr * filtrate_tta_g_L
    mixed_tta = total_tta_mass / total_mass_lb_hr

    # Mixed flow (use average density)
    mixed_density = (ww_mass_lb_hr * ww_density_lb_gal + filtrate_mass_lb_hr * filtrate_density_lb_gal) / total_mass_lb_hr
    mixed_flow_gpm = total_mass_lb_hr / (mixed_density * 60)

    return (mixed_flow_gpm, mixed_tta)
