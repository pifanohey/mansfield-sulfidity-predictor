"""Test fixtures with Pine Hill default values."""
import pytest
from app.engine.constants import DEFAULTS


@pytest.fixture
def pine_hill_defaults():
    """Return a copy of Pine Hill default operating parameters."""
    return dict(DEFAULTS)


@pytest.fixture
def excel_v4_rb_inputs():
    """Recovery boiler inputs matching Excel v4 (new calculated-ash API)."""
    return {
        'bl_flow_gpm': 340.53,
        'bl_tds_pct': 69.1,
        'bl_temp_f': 253.5,
        'bl_na_pct_inv': 19.50,         # Inventory Na% d.s. (virgin BL)
        'bl_s_pct_inv': 3.93,           # Inventory S% d.s. (virgin BL)
        'bl_k_pct': 1.58,
        'reduction_eff_pct': 95.0,
        's_retention_strong': 0.9861,
        'ash_recycled_pct': 0.07,        # B4 = 7% ash recycled
        'rb_losses_na2o_bdt': 3.60,      # B16 = lb Na2O/BDT soda loss
        'total_production_bdt_day': 1887.544,
        'saltcake_flow_lb_hr': 2227.0,   # B40 = lb Na2SO4/hr
    }


@pytest.fixture
def excel_v4_makeup_inputs():
    """Makeup calculation inputs matching Excel v4."""
    return {
        'target_sulfidity_pct': 29.4,
        'wl_tta_mass_ton_hr': 20.598,
        'wl_na2s_mass_ton_hr': 5.586,
        'na_deficit_lbs_hr': 2470.31,
        's_deficit_lbs_hr': 563.13,
        'cto_s_lbs_hr': 279.52,
        'total_production_bdt_day': 1887.544,
    }


@pytest.fixture
def excel_v4_expected():
    """Expected values from Excel v4 for validation."""
    return {
        # BL Density (2_RB!B10)
        'bl_density': 11.1666,
        # RB computed composition
        'bl_na_pct_mixed': 20.43,
        'bl_s_pct_mixed': 5.26,
        'ash_na_na2o': 4885.17,
        # RB outputs
        'na_lbs_hr': 32932.72,
        'k_lbs_hr': 2490.95,
        's_lbs_hr': 8791.38,
        'potential_na_alkali': 44426.21,
        'potential_k_alkali': 1974.93,
        'potential_s_alkali': 16998.77,
        'active_sulfide': 11039.22,
        'dead_load': 849.94,
        'tta_lbs_hr': 40382.90,
        'smelt_sulfidity_frac': 0.2734,
        # Makeup outputs
        'na2s_deficit_ton_hr': 0.5628,
        'conversion_factor': 1.498,
        'nash_dry_lbs_hr': 751.36,
        'naoh_dry_lbs_hr': 2650.81,
        'na_deficit_remaining': 2054.38,
        # Solution flows
        'nash_solution_lbs_hr': 1878.40,
        'nash_solution_gpm': 2.9082,
        'naoh_solution_lbs_hr': 5301.63,
        'naoh_solution_gpm': 6.9661,
        # Final WL
        'final_tta_ton_hr': 21.8333,
        'final_na2s_ton_hr': 6.002,
        'final_sulfidity_pct': 27.49,
        # WL composition
        'wl_sulfidity_frac': 0.2941,
        'wl_na2s_g_L': 34.54,
    }
