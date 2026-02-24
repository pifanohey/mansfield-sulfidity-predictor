"""
Black liquor, white liquor, and green liquor density calculations.

Reference: 1_Inventory!F45 and 2_Recovery boiler!B10
"""


def calculate_bl_density(tds_pct: float, temp_f: float, offset: float = 0.0) -> float:
    """
    Calculate black liquor density using mill correlation.

    Formula: 8.33 * 0.99 * (997 + 649*TDS/100) * (1 - 0.000369*dT - 0.00000194*dT^2) / 1000 + offset
    where dT = (temp_F - 32)/1.8 - 25

    2_RB!B10 uses offset = -0.1

    Returns: density in lb/gal
    """
    temp_c = (temp_f - 32) / 1.8
    delta_t = temp_c - 25
    base = 997 + 649 * tds_pct / 100
    temp_correction = 1 - 0.000369 * delta_t - 0.00000194 * delta_t ** 2
    return 8.33 * 0.99 * base * temp_correction / 1000 + offset


def calculate_wl_density(tta_g_l: float) -> float:
    """Estimate white liquor density from TTA concentration. Returns lb/gal."""
    return 8.5 + 0.012 * tta_g_l


def calculate_gl_density(tta_g_l: float) -> float:
    """Estimate green liquor density from TTA concentration at ~25°C. Returns lb/gal."""
    return 8.6 + 0.0115 * tta_g_l


def calculate_gl_density_hot(tta_g_l: float, temp_f: float) -> float:
    """
    GL density with temperature correction for the slaker model.

    The room-temp GL density formula overestimates at elevated temperatures.
    Calibrated to match Excel Slaker Model: at TTA=117 g/L and 189°F → ~9.43 lb/gal
    (= 1.130 kg/L), giving GL mass B48 = 186.31 short ton/hr.

    Returns: density in kg/L
    """
    density_cold_lb_gal = 8.6 + 0.0115 * tta_g_l  # at ~77°F / 25°C
    temp_c = (temp_f - 32) / 1.8
    temp_correction = 1 - 0.000839 * (temp_c - 25)
    density_lb_gal = density_cold_lb_gal * temp_correction
    # Convert lb/gal to kg/L: 1 lb/gal = 1/8.345 kg/L
    return density_lb_gal / 8.345
