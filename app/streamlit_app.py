"""
Pine Hill Mill - Sulfidity Predictor
Main Streamlit Application

Reference: SULFIDITY_MODEL_V5_CORRECTED_FINAL v2.xlsx

This application follows the integrated mass balance approach where
all calculations flow from TRUE user inputs through the complete
liquor cycle model.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sulfidity_predictor.config.constants import DEFAULTS, MW, CONV
from sulfidity_predictor.config.tank_config import TANKS, tank_volume_gallons
from sulfidity_predictor.models import (
    calculate_liquor_composition,
    calculate_tank_inventory,
    calculate_bl_inventory,
    calculate_sulfidity_metrics,
    calculate_full_rb_from_bl,
    calculate_makeup_summary,
    calculate_bl_density,
)
from sulfidity_predictor.solvers.circular_solver import solve_makeup_circular


# Page configuration
st.set_page_config(
    page_title="Pine Hill Sulfidity Predictor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .section-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2E5077;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        border-bottom: 2px solid #2E5077;
        padding-bottom: 0.25rem;
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .output-label {
        font-weight: bold;
        color: #555;
    }
    .output-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #1E3A5F;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    st.markdown('<p class="main-header">Pine Hill Mill - Sulfidity Predictor</p>',
                unsafe_allow_html=True)
    st.markdown("*Integrated mass balance model for sulfidity control*")

    # Create two columns - inputs on left, outputs on right
    col_inputs, col_outputs = st.columns([1, 1.2])

    with col_inputs:
        inputs = render_unified_inputs()

    with col_outputs:
        if inputs:
            render_outputs(inputs)


def render_unified_inputs():
    """Render the unified input form grouped by process area.

    All inputs match EXACTLY what's in the Excel model:
    SULFIDITY_MODEL_V5_CORRECTED_FINAL v2.xlsx
    """
    st.markdown('<p class="section-header">INPUTS</p>', unsafe_allow_html=True)

    inputs = {}

    # === SECTION 1: ALL TANK LEVELS (from 1_Inventory sheet) ===
    with st.expander("1. Tank Levels (1_Inventory)", expanded=True):
        # --- White Liquor Tanks ---
        st.markdown("**White Liquor Tanks**")
        col1, col2 = st.columns(2)
        with col1:
            inputs['wlc_1_level'] = st.number_input(
                "WLC #1 Level (ft) [F1]", 0.0, 16.0, 10.2, 0.5, key='wlc1')
        with col2:
            inputs['wlc_2_level'] = st.number_input(
                "WLC #2 Level (ft) [I1]", 0.0, 16.0, 13.0, 0.5, key='wlc2')

        st.markdown("---")

        # --- Green Liquor Tanks ---
        st.markdown("**Green Liquor Tanks**")
        col1, col2, col3 = st.columns(3)
        with col1:
            inputs['gl_1_level'] = st.number_input(
                "GL #1 Level (ft) [F14]", 0.0, 16.0, 11.1, 0.5, key='gl1')
        with col2:
            inputs['gl_2_level'] = st.number_input(
                "GL #2 Level (ft) [I14]", 0.0, 16.0, 10.8, 0.5, key='gl2')
        with col3:
            inputs['dump_tank_level'] = st.number_input(
                "Dump Tank Level (ft) [L14]", 0.0, 38.0, 30.3, 0.5, key='dump')

        st.markdown("---")

        # --- Black Liquor Tanks (ALL 7 TANKS) ---
        st.markdown("**Black Liquor Tanks**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            inputs['wbl_1_level'] = st.number_input(
                "WBL #1 Level (ft) [F40]", 0.0, 48.0, 34.4, 1.0, key='wbl1')
            inputs['wbl_2_level'] = st.number_input(
                "WBL #2 Level (ft) [I40]", 0.0, 48.0, 32.8, 1.0, key='wbl2')
        with col2:
            inputs['cssc_weak_level'] = st.number_input(
                "CSSC Weak Level (ft) [L40]", 0.0, 48.0, 36.4, 1.0, key='cssc_weak')
            inputs['tank_50_level'] = st.number_input(
                "50% Tank Level (ft) [O40]", 0.0, 48.0, 18.4, 1.0, key='tank50')
        with col3:
            inputs['tank_55_1_level'] = st.number_input(
                "55% #1 Level (ft) [R40]", 0.0, 48.0, 18.0, 1.0, key='tank55_1')
            inputs['tank_55_2_level'] = st.number_input(
                "55% #2 Level (ft) [U40]", 0.0, 48.0, 1.0, 1.0, key='tank55_2')
        with col4:
            inputs['tank_65_level'] = st.number_input(
                "65% Tank Level (ft) [X40]", 0.0, 48.0, 39.4, 1.0, key='tank65')

    # === SECTION 2: LAB ANALYSIS (from 1_Inventory sheet) ===
    with st.expander("2. Lab Analysis (1_Inventory)", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**White Liquor Analysis (g Na2O/L)**")
            inputs['wl_tta'] = st.number_input(
                "WL TTA [F4]", 80.0, 150.0, 117.449, 0.001, format="%.3f", key='wl_tta')
            inputs['wl_ea'] = st.number_input(
                "WL EA [F5]", 60.0, 120.0, 85.99, 0.01, format="%.2f", key='wl_ea')
            inputs['wl_aa'] = st.number_input(
                "WL AA [F6]", 70.0, 130.0, 103.26, 0.01, format="%.2f", key='wl_aa')
            inputs['wl_tta_slaker'] = st.number_input(
                "WL TTA from Slaker [N71]", 0.0, 150.0, 120.784, 0.001, format="%.3f",
                help="Slaker output TTA. If 0, uses WL TTA above. For exact Excel match, use N71.",
                key='wl_tta_slaker')
            inputs['wl_na2s_override'] = st.number_input(
                "WL Na2S from Slaker [N76]", 0.0, 60.0, 32.756, 0.001, format="%.3f",
                help="Slaker output Na2S. If 0, calculates from TTA/EA/AA. For exact Excel match, use N76.",
                key='wl_na2s_ovr')

        with col2:
            st.markdown("**Green Liquor Analysis (g Na2O/L)**")
            inputs['gl_tta'] = st.number_input(
                "GL TTA [F17]", 80.0, 150.0, 117.5, 0.1, key='gl_tta')
            inputs['gl_ea'] = st.number_input(
                "GL EA [F18]", 20.0, 60.0, 27.72, 0.01, format="%.2f", key='gl_ea')
            inputs['gl_aa'] = st.number_input(
                "GL AA [F19]", 30.0, 80.0, 44.77, 0.01, format="%.2f", key='gl_aa')

    # === SECTION 3: BLACK LIQUOR PROPERTIES (individual tank TDS) ===
    with st.expander("3. Black Liquor Properties (1_Inventory)", expanded=True):
        st.markdown("**Common BL Properties**")
        col1, col2, col3 = st.columns(3)
        with col1:
            inputs['bl_na_pct'] = st.number_input(
                "Na in BL Solids (%) [AD10]", 15.0, 25.0, 20.43, 0.01, format="%.2f", key='bl_na')
        with col2:
            inputs['bl_s_pct'] = st.number_input(
                "S in BL Solids (%) [AD28]", 2.0, 8.0, 5.50, 0.01, format="%.2f", key='bl_s')
        with col3:
            inputs['bl_k_pct'] = st.number_input(
                "K in BL Solids (%) [2_RB!L24]", 0.5, 6.0, 5.435, 0.001, format="%.3f", key='bl_k')

        st.markdown("---")
        st.markdown("**Individual Tank TDS and Temperature**")

        # WBL Tanks
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("*WBL #1*")
            inputs['wbl_1_tds'] = st.number_input(
                "WBL #1 TDS (%)", 10.0, 30.0, 19.23, 0.01, format="%.2f", key='wbl1_tds')
            inputs['wbl_1_temp'] = st.number_input(
                "WBL #1 Temp (F)", 150.0, 250.0, 205.0, 1.0, key='wbl1_temp')
        with col2:
            st.markdown("*WBL #2*")
            inputs['wbl_2_tds'] = st.number_input(
                "WBL #2 TDS (%)", 10.0, 30.0, 19.23, 0.01, format="%.2f", key='wbl2_tds')
            inputs['wbl_2_temp'] = st.number_input(
                "WBL #2 Temp (F)", 150.0, 250.0, 205.0, 1.0, key='wbl2_temp')
        with col3:
            st.markdown("*CSSC Weak*")
            inputs['cssc_weak_tds'] = st.number_input(
                "CSSC Weak TDS (%)", 10.0, 40.0, 19.23, 0.01, format="%.2f", key='cssc_tds')
            inputs['cssc_weak_temp'] = st.number_input(
                "CSSC Weak Temp (F)", 150.0, 250.0, 205.0, 1.0, key='cssc_temp')
        with col4:
            st.markdown("*50% Tank*")
            inputs['tank_50_tds'] = st.number_input(
                "50% Tank TDS (%)", 45.0, 55.0, 50.0, 0.5, key='tank50_tds')
            inputs['tank_50_temp'] = st.number_input(
                "50% Tank Temp (F)", 180.0, 280.0, 205.0, 1.0, key='tank50_temp')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("*55% #1*")
            inputs['tank_55_1_tds'] = st.number_input(
                "55% #1 TDS (%)", 50.0, 60.0, 55.0, 0.5, key='tank55_1_tds')
            inputs['tank_55_1_temp'] = st.number_input(
                "55% #1 Temp (F)", 180.0, 280.0, 205.0, 1.0, key='tank55_1_temp')
        with col2:
            st.markdown("*55% #2*")
            inputs['tank_55_2_tds'] = st.number_input(
                "55% #2 TDS (%)", 50.0, 60.0, 50.0, 0.5, key='tank55_2_tds')
            inputs['tank_55_2_temp'] = st.number_input(
                "55% #2 Temp (F)", 180.0, 280.0, 205.0, 1.0, key='tank55_2_temp')
        with col3:
            st.markdown("*65% Tank (to RB)*")
            inputs['tank_65_tds'] = st.number_input(
                "65% Tank TDS (%)", 60.0, 75.0, 69.1, 0.1, key='tank65_tds')
            inputs['tank_65_temp'] = st.number_input(
                "65% Tank Temp (F)", 200.0, 300.0, 205.0, 1.0, key='tank65_temp')

    # === SECTION 4: RECOVERY BOILER (from 2_Recovery boiler sheet) ===
    with st.expander("4. Recovery Boiler (2_Recovery boiler)", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**RB Operating Parameters**")
            inputs['bl_flow_gpm'] = st.number_input(
                "BL Flow to RB (gpm) [B6]", 100.0, 500.0, 157.66, 0.01, format="%.2f", key='bl_flow')
            inputs['bl_tds_to_rb'] = st.number_input(
                "BL TDS to RB (%) [B11]", 60.0, 80.0, 69.1, 0.1, key='bl_tds_rb')
            inputs['reduction_eff_pct'] = st.number_input(
                "Reduction Efficiency (%) [B14]", 80.0, 99.0, 95.0, 0.5, key='re')
            inputs['s_retention'] = st.number_input(
                "S Retention Factor [B15]", 0.90, 1.00, 0.986, 0.001, format="%.3f", key='s_ret')

        with col2:
            st.markdown("**RB Ash & Losses**")
            inputs['ash_na_na2o'] = st.number_input(
                "Ash Na (lb Na2O/hr) [B18]", 0.0, 2000.0, 283.13, 0.01, format="%.2f", key='ash_na')
            inputs['ash_s_na2o'] = st.number_input(
                "Ash S (lb Na2O equiv/hr)", 0.0, 1000.0, 200.0, 10.0, key='ash_s')
            inputs['rb_losses_na'] = st.number_input(
                "RB Na Losses (lb/hr)", 0.0, 3000.0, 209.88, 0.01, format="%.2f", key='rb_loss')
            inputs['saltcake_na_lbs_hr'] = st.number_input(
                "Saltcake (lb Na2SO4/hr) [2_RB!B40]", 0.0, 5000.0, 2227.0, 1.0, key='saltcake')

        st.markdown("---")
        st.markdown("**Crude Tall Oil (CTO) Sulfur [S Ret!F43]**")
        inputs['cto_s_lbs_hr'] = st.number_input(
            "CTO S (lb S/hr) [B27]", 0.0, 1000.0, 279.52, 0.01, format="%.2f", key='cto_s',
            help="CTO Sulfur contribution from S Retention Factor sheet F43. "
                 "Formula: (CTO_TPD × H2SO4/ton × S/H2SO4 × Red_Eff × S_Ret / 2000) × 2000/24")

    # === SECTION 5: DIGESTERS/FIBERLINE (from 3_Chemical Charge sheet) ===
    with st.expander("5. Digesters / Fiberline (3_Chemical Charge)", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Production Rates**")
            inputs['batch_production'] = st.number_input(
                "Batch Digester (BDT/day) [D7]", 0.0, 2000.0, 636.854, 0.001, format="%.3f", key='batch')
            inputs['cont_production'] = st.number_input(
                "Continuous Digester (BDT/day) [D33]", 0.0, 2000.0, 1250.69, 0.01, format="%.2f", key='cont')
            inputs['cooking_wl_sulfidity'] = st.number_input(
                "Cooking WL Sulfidity (fraction) [D15]", 0.20, 0.40, 0.283, 0.001,
                format="%.3f", key='cook_sulf')

        with col2:
            st.markdown("**Causticizer/Slaker**")
            inputs['gl_flow_to_slaker'] = st.number_input(
                "GL Flow to Slaker (gpm) [D59]", 400.0, 900.0, 659.03, 0.01, format="%.2f", key='gl_flow')
            inputs['yield_factor'] = st.number_input(
                "Slaker Yield Factor [G64]", 1.00, 1.10, 1.0335, 0.0001,
                format="%.4f", key='yield')
            inputs['wl_to_digesters_gpm'] = st.number_input(
                "WL to Digesters (gpm) [U110]", 400.0, 800.0, 577.84, 0.01, format="%.2f", key='wl_dig')
            inputs['loss_factor'] = st.number_input(
                "Na Loss Factor [0_SULF!B24]", 0.05, 0.15, 0.0921, 0.0001,
                format="%.4f", key='loss_factor')
            inputs['na_deficit_override'] = st.number_input(
                "Na Deficit Override [H40] (0=calc)", 0.0, 10000.0, 0.0, 0.01, format="%.2f", key='na_def_ovr',
                help="Direct input for Na Deficit (lb Na2O/hr). Set to 0 to calculate from inputs. "
                     "For exact Excel match, enter 2470.31")

    # === SECTION 6: OPERATING SETPOINTS ===
    with st.expander("6. Operating Setpoints", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            inputs['target_sulfidity_pct'] = st.number_input(
                "Target Sulfidity (%) [1_Inv!C22]", 20.0, 40.0, 29.4, 0.1, key='target_sulf')
            inputs['causticity_pct'] = st.number_input(
                "Causticity (%) [3_Chem!G70]", 70.0, 95.0, 81.0, 0.1, key='caust')

        with col2:
            st.markdown("*WL Flow Summary*")
            wl_from_slaker = inputs.get('gl_flow_to_slaker', 658.6) * inputs.get('yield_factor', 1.0335)
            st.info(f"WL from Slaker: {wl_from_slaker:.1f} gpm")

    # === SECTION 7: MAKEUP CHEMICAL PROPERTIES (from 0_SULFIDITY CONTROL) ===
    with st.expander("7. Makeup Chemical Properties (0_SULF)", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**NaSH**")
            inputs['nash_conc_pct'] = st.number_input(
                "NaSH Concentration (%) [B4]", 30.0, 50.0, 40.0, 0.1, key='nash_conc')
            inputs['nash_density'] = st.number_input(
                "NaSH Density (SG) [B6]", 1.10, 1.50, 1.29, 0.01, format="%.2f", key='nash_dens')

        with col2:
            st.markdown("**NaOH**")
            inputs['naoh_conc_pct'] = st.number_input(
                "NaOH Concentration (%) [B5]", 40.0, 60.0, 50.0, 0.1, key='naoh_conc')
            inputs['naoh_density'] = st.number_input(
                "NaOH Density (SG) [B7]", 1.40, 1.60, 1.52, 0.01, format="%.2f", key='naoh_dens')

    return inputs


def render_outputs(inputs):
    """Render the calculated outputs matching Excel model sections."""
    st.markdown('<p class="section-header">OUTPUTS</p>', unsafe_allow_html=True)

    try:
        results = run_calculations(inputs)

        # === PRIMARY OUTPUTS - Makeup Requirements (0_SULF!H46-H49) ===
        st.markdown("### Makeup Requirements (0_SULF)")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**NaSH**")
            st.metric("NaSH (dry lb/hr) [H46]", f"{results['nash_dry_lbs_hr']:.1f}")
            st.metric("NaSH (solution lb/hr) [B46]", f"{results['nash_solution_lbs_hr']:.1f}")
            st.metric("NaSH Flow (gpm) [B47]", f"{results['nash_solution_gpm']:.2f}")
            st.metric("NaSH Concentration (%)", f"{inputs['nash_conc_pct']:.0f}")

        with col2:
            st.markdown("**NaOH**")
            st.metric("NaOH (dry lb/hr) [H47]", f"{results['naoh_dry_lbs_hr']:.1f}")
            st.metric("NaOH (solution lb/hr)", f"{results['naoh_solution_lbs_hr']:.1f}")
            st.metric("NaOH Flow (gpm) [B54]", f"{results['naoh_solution_gpm']:.2f}")
            st.metric("NaOH Concentration (%)", f"{inputs['naoh_conc_pct']:.0f}")

        # === PER-BDT OUTPUTS (0_SULF!H53-H57) ===
        st.markdown("### Per-BDT Summary (0_SULF)")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("NaSH (lb Na2O/BDT) [H53]",
                      f"{results['nash_dry_lb_bdt_na2o']:.2f}")
        with col2:
            st.metric("NaOH (lb Na2O/BDT) [H54]",
                      f"{results['naoh_dry_lb_bdt_na2o']:.2f}")
        with col3:
            st.metric("Saltcake (lb Na2O/BDT) [H57]",
                      f"{results['saltcake_lb_bdt_na2o']:.2f}")

        # === SULFIDITY SUMMARY (1_Inventory!C17-C19) ===
        st.markdown("### Sulfidity Summary (1_Inventory)")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            current_sulf = results['current_sulfidity_pct']
            delta = current_sulf - inputs['target_sulfidity_pct']
            st.metric("Current Sulfidity (%) [C17]",
                      f"{current_sulf:.2f}",
                      f"{delta:+.2f} vs target")

        with col2:
            st.metric("Latent Sulfidity (%) [C18]",
                      f"{results['latent_sulfidity_pct']:.2f}")

        with col3:
            st.metric("Initial Sulfidity (%)",
                      f"{results['initial_sulfidity_pct']:.2f}")

        with col4:
            st.metric("Final Sulfidity (%) [B63]",
                      f"{results['final_sulfidity_pct']:.2f}")

        # === LIQUOR ANALYSIS (calculated) ===
        with st.expander("Liquor Analysis (Calculated)", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**White Liquor**")
                st.write(f"WL Sulfidity: {results['wl_sulfidity_pct']:.2f}%")
                st.write(f"WL Na2S: {results['wl_na2s_g_L']:.2f} g/L")
            with col2:
                st.markdown("**Green Liquor**")
                st.write(f"GL Sulfidity: {results['gl_sulfidity_pct']:.2f}%")

        # === RECOVERY BOILER SUMMARY (2_RB!B29-B35) ===
        with st.expander("Recovery Boiler Summary (2_RB)", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Smelt Composition**")
                st.write(f"Smelt Sulfidity [B35]: {results['smelt_sulfidity_pct']:.2f}%")
                st.write(f"TTA from RB [B34]: {results['rb_tta_lbs_hr']:,.0f} lb Na2O/hr")
                st.write(f"Active Sulfide [B32]: {results['rb_active_sulfide']:,.0f} lb Na2O/hr")

            with col2:
                st.markdown("**Mass Inputs**")
                st.write(f"Dead Load [B33]: {results['rb_dead_load']:,.0f} lb Na2O/hr")
                st.write(f"Na Input: {results['rb_na_lbs_hr']:,.0f} lb/hr")
                st.write(f"S Input: {results['rb_s_lbs_hr']:,.0f} lb/hr")
                st.write(f"BL Density: {results['bl_density']:.3f} lb/gal")

        # === TANK INVENTORY TOTALS (1_Inventory) ===
        with st.expander("Tank Inventory Totals (1_Inventory)", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**White Liquor Tanks**")
                st.write(f"Total WL TTA: {results['total_wl_tta_tons']:.2f} tons Na2O")
                st.write(f"Total WL Na2S: {results['total_wl_na2s_tons']:.2f} tons Na2O")

            with col2:
                st.markdown("**Green Liquor Tanks**")
                st.write(f"Total GL TTA: {results['total_gl_tta_tons']:.2f} tons Na2O")
                st.write(f"Total GL Na2S: {results['total_gl_na2s_tons']:.2f} tons Na2O")

            with col3:
                st.markdown("**Black Liquor Tanks (Latent)**")
                st.write(f"Latent TTA: {results['total_bl_latent_tta_tons']:.2f} tons Na2O")
                st.write(f"Latent Na2S: {results['total_bl_latent_na2s_tons']:.2f} tons Na2O")

        # === FIBERLINE DATA (3_Chem) ===
        with st.expander("Fiberline Data (3_Chemical Charge)", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**WL Flows**")
                st.write(f"WL from Slaker: {results['wl_flow_from_slaker']:.1f} gpm")
                st.write(f"WL to Digesters: {inputs['wl_to_digesters_gpm']:.1f} gpm")
                st.write(f"GL to Slaker: {inputs['gl_flow_to_slaker']:.1f} gpm")

            with col2:
                st.markdown("**Production**")
                st.write(f"Batch: {inputs['batch_production']:.0f} BDT/day")
                st.write(f"Continuous: {inputs['cont_production']:.0f} BDT/day")
                st.write(f"Total: {results['total_production_bdt_day']:.0f} BDT/day")

        # === INTERMEDIATE VALUES (for Excel validation) ===
        with st.expander("Validation Values (Compare with Excel)", expanded=False):
            st.markdown("**Na Balance (0_SULF)**")
            st.write(f"Na Losses: {results['na_losses_lbs_hr']:,.1f} lb Na2O/hr")
            st.write(f"Na Deficit [H40]: {results['na_deficit_lbs_hr']:,.1f} lb Na2O/hr")
            st.write(f"Na from NaSH: {results['na_from_nash']:,.1f} lb Na2O/hr")
            st.write(f"Na Deficit Remaining [H48]: {results['na_deficit_remaining']:,.1f} lb Na2O/hr")

            st.markdown("**Conversion Factors**")
            st.write(f"H45 (NaSH factor): {results['nash_conversion_factor']:.4f}")
            st.write(f"Na2S Deficit [H44]: {results['na2s_deficit_ton_hr']:.4f} ton Na2O/hr")
            st.write(f"CTO S [B27]: {results.get('cto_s_lbs_hr', 0):.2f} lb S/hr")

            st.markdown("**WL Mass Flows (3_Chem!N69, N77)**")
            st.write(f"WL TTA Mass: {results['wl_tta_mass_ton_hr']:.3f} ton Na2O/hr")
            st.write(f"WL Na2S Mass: {results['wl_na2s_mass_ton_hr']:.3f} ton Na2O/hr")

            st.markdown("**Final WL Composition (0_SULF!B60-B63)**")
            st.write(f"Final TTA Mass: {results['final_tta_ton_hr']:.3f} ton Na2O/hr")
            st.write(f"Final Na2S Mass: {results['final_na2s_ton_hr']:.3f} ton Na2O/hr")

    except Exception as e:
        st.error(f"Calculation Error: {str(e)}")
        st.exception(e)


def run_calculations(inputs):
    """Run the complete calculation flow following the Excel model EXACTLY.

    This function implements all calculations from:
    - 1_Inventory (tank volumes, inventories, sulfidity)
    - 2_Recovery boiler (smelt composition)
    - 3_Chemical Charge (fiberline flows)
    - S Rention Factor (S losses)
    - 0_SULFIDITY CONTROL MAKEUP (NaSH/NaOH requirements)
    """
    results = {}

    # === STEP 1: Create Liquor Compositions (1_Inventory!F4-F8) ===
    wl_comp = calculate_liquor_composition(
        inputs['wl_tta'], inputs['wl_ea'], inputs['wl_aa'])
    gl_comp = calculate_liquor_composition(
        inputs['gl_tta'], inputs['gl_ea'], inputs['gl_aa'])

    # Store for output display
    results['wl_sulfidity_pct'] = wl_comp.sulfidity_tta_pct
    results['gl_sulfidity_pct'] = gl_comp.sulfidity_tta_pct
    results['wl_na2s_g_L'] = wl_comp.na2s_g_L

    # === STEP 2: Calculate Tank Inventories - WHITE LIQUOR ===
    wl_tanks = []
    for tank_name, level_key in [('wlc_1', 'wlc_1_level'), ('wlc_2', 'wlc_2_level')]:
        inv = calculate_tank_inventory(tank_name, inputs[level_key], wl_comp)
        wl_tanks.append(inv)

    # === STEP 3: Calculate Tank Inventories - GREEN LIQUOR ===
    gl_tanks = []
    for tank_name, level_key in [('gl_1', 'gl_1_level'), ('gl_2', 'gl_2_level'),
                                  ('dump_tank', 'dump_tank_level')]:
        inv = calculate_tank_inventory(tank_name, inputs[level_key], gl_comp)
        gl_tanks.append(inv)

    # === STEP 4: Calculate Tank Inventories - ALL BLACK LIQUOR TANKS ===
    # Each tank has its own TDS and temperature from user input
    bl_tanks = []

    # BL tank configuration: (tank_config_name, level_key, tds_key, temp_key)
    bl_tank_configs = [
        ('wbl_1', 'wbl_1_level', 'wbl_1_tds', 'wbl_1_temp'),
        ('wbl_2', 'wbl_2_level', 'wbl_2_tds', 'wbl_2_temp'),
        ('cssc_weak', 'cssc_weak_level', 'cssc_weak_tds', 'cssc_weak_temp'),
        ('tank_50pct', 'tank_50_level', 'tank_50_tds', 'tank_50_temp'),
        ('tank_55pct_1', 'tank_55_1_level', 'tank_55_1_tds', 'tank_55_1_temp'),
        ('tank_55pct_2', 'tank_55_2_level', 'tank_55_2_tds', 'tank_55_2_temp'),
        ('tank_65pct', 'tank_65_level', 'tank_65_tds', 'tank_65_temp'),
    ]

    for tank_name, level_key, tds_key, temp_key in bl_tank_configs:
        inv = calculate_bl_inventory(
            tank_name, inputs[level_key],
            tds_pct=inputs[tds_key],
            temp_f=inputs[temp_key],
            na_pct=inputs['bl_na_pct'],
            s_pct=inputs['bl_s_pct'],
            reduction_eff_pct=inputs['reduction_eff_pct'],
            s_retention=inputs['s_retention']
        )
        bl_tanks.append(inv)

    # Store tank inventory totals for validation
    results['total_wl_tta_tons'] = sum(t.tta_tons for t in wl_tanks)
    results['total_wl_na2s_tons'] = sum(t.na2s_tons for t in wl_tanks)
    results['total_gl_tta_tons'] = sum(t.tta_tons for t in gl_tanks)
    results['total_gl_na2s_tons'] = sum(t.na2s_tons for t in gl_tanks)
    results['total_bl_latent_tta_tons'] = sum(t.latent_tta_tons for t in bl_tanks)
    results['total_bl_latent_na2s_tons'] = sum(t.latent_na2s_tons for t in bl_tanks)

    # === STEP 5: Calculate Recovery Boiler Outputs FIRST (2_RB!B29-B35) ===
    # This must come before sulfidity calculation so we can include RB outputs
    # Use bl_tds_to_rb (the RB feed) and 65% tank temperature
    rb_inputs, smelt = calculate_full_rb_from_bl(
        bl_flow_gpm=inputs['bl_flow_gpm'],
        bl_tds_pct=inputs['bl_tds_to_rb'],  # BL TDS going to RB
        bl_temp_f=inputs['tank_65_temp'],    # 65% tank temp (RB feed)
        bl_na_pct=inputs['bl_na_pct'],
        bl_s_pct=inputs['bl_s_pct'],
        bl_k_pct=inputs['bl_k_pct'],
        reduction_eff_pct=inputs['reduction_eff_pct'],
        s_retention=inputs['s_retention'],
        ash_na_na2o=inputs['ash_na_na2o'],
        ash_s_na2o_equiv=inputs['ash_s_na2o'],
        rb_losses_na=inputs['rb_losses_na'],
        saltcake_na_lbs_hr=inputs['saltcake_na_lbs_hr']
    )

    results['smelt_sulfidity_pct'] = smelt.smelt_sulfidity_pct
    results['rb_tta_lbs_hr'] = smelt.tta_lbs_hr
    results['rb_active_sulfide'] = smelt.active_sulfide
    results['rb_dead_load'] = smelt.dead_load
    results['rb_na_lbs_hr'] = smelt.na_lbs_hr
    results['rb_s_lbs_hr'] = smelt.s_lbs_hr
    results['bl_density'] = rb_inputs.bl_density_lb_gal

    # === STEP 7: Calculate WL Mass Flows (3_Chem!N69, N77) ===
    # WL flow from slaker = GL flow to slaker × yield factor (K65 = I58 × G64)
    wl_flow_from_slaker = inputs['gl_flow_to_slaker'] * inputs['yield_factor']
    results['wl_flow_from_slaker'] = wl_flow_from_slaker

    # WL TTA mass flow (ton Na2O/hr) = WL_flow * WL_TTA * conversion (N69)
    # For exact Excel match, use slaker output TTA (N71) instead of input WL TTA
    gpm_gl_to_ton_hr = CONV['GPM_GL_TO_LB_HR'] / 2000

    # Use slaker output TTA if provided, else use input WL TTA
    wl_tta_slaker = inputs.get('wl_tta_slaker', 0.0)
    if wl_tta_slaker > 0:
        wl_tta_for_mass = wl_tta_slaker
    else:
        wl_tta_for_mass = inputs['wl_tta']
    wl_tta_mass_ton_hr = wl_flow_from_slaker * wl_tta_for_mass * gpm_gl_to_ton_hr
    results['wl_tta_for_mass_g_L'] = wl_tta_for_mass

    # WL Na2S: use override if provided (for exact Excel match), else calculate
    wl_na2s_override = inputs.get('wl_na2s_override', 0.0)
    if wl_na2s_override > 0:
        wl_na2s_g_L = wl_na2s_override
    else:
        wl_na2s_g_L = wl_comp.na2s_g_L
    wl_na2s_mass_ton_hr = wl_flow_from_slaker * wl_na2s_g_L * gpm_gl_to_ton_hr
    results['wl_na2s_g_L_used'] = wl_na2s_g_L

    results['wl_tta_mass_ton_hr'] = wl_tta_mass_ton_hr
    results['wl_na2s_mass_ton_hr'] = wl_na2s_mass_ton_hr

    # Initial sulfidity before makeup (3_Chem!P79)
    if wl_tta_mass_ton_hr > 0:
        initial_sulfidity = (wl_na2s_mass_ton_hr / wl_tta_mass_ton_hr) * 100
    else:
        initial_sulfidity = 0.0
    results['initial_sulfidity_pct'] = initial_sulfidity

    # === STEP 8: Calculate Na Deficit (0_SULF!H40) ===
    # Excel H40 = B23 - B29 (Na losses - Na from saltcake)
    # For exact Excel match, use the override input. Otherwise calculate.

    na_deficit_override = inputs.get('na_deficit_override', 0.0)

    if na_deficit_override > 0:
        # Use direct input for exact Excel matching
        na_deficit_lbs_hr = na_deficit_override
        # Calculate approximate Na losses for display
        na_fraction_in_saltcake = (2 * MW['Na']) / MW['Na2SO4']
        na_from_saltcake_as_na = inputs['saltcake_na_lbs_hr'] * na_fraction_in_saltcake
        na_losses_lbs_hr = na_deficit_lbs_hr + na_from_saltcake_as_na
    else:
        # Calculate from inputs with causticity effect
        loss_factor = inputs.get('loss_factor', 0.0921)
        wl_to_digesters_base = inputs.get('wl_to_digesters_gpm', 577.84)
        causticity = inputs.get('causticity_pct', 81.0) / 100
        reduction_eff = inputs.get('reduction_eff_pct', 95.0) / 100

        # Causticity effect: Lower CE requires more WL flow to meet EA demand
        # Activity = (CE × (100 - Sulfidity) + Sulfidity) / 100
        # Reference CE = 0.8753 (Excel default), at this CE activity ≈ 0.89
        wl_activity = (causticity * (100 - initial_sulfidity) + initial_sulfidity) / 100
        reference_ce = 0.8753
        reference_activity = (reference_ce * (100 - initial_sulfidity) + initial_sulfidity) / 100
        ce_adjustment = reference_activity / wl_activity if wl_activity > 0 else 1.0

        # Adjust WL to digesters based on causticity
        wl_to_digesters = wl_to_digesters_base * ce_adjustment
        results['wl_activity'] = wl_activity
        results['ce_adjustment'] = ce_adjustment

        # Excel B23: Na losses = U110 × U104 × 0.5007 × B24
        na_losses_lbs_hr = wl_to_digesters * wl_tta_for_mass * CONV['GPM_GL_TO_LB_HR'] * loss_factor

        # Na from saltcake (0_SULF!B29)
        na_fraction_in_saltcake = (2 * MW['Na']) / MW['Na2SO4']
        na_from_saltcake_as_na = inputs['saltcake_na_lbs_hr'] * na_fraction_in_saltcake

        # Na deficit = Na losses - Na from saltcake (H40 = B23 - B29)
        na_deficit_lbs_hr = na_losses_lbs_hr - na_from_saltcake_as_na
        na_deficit_lbs_hr = max(0, na_deficit_lbs_hr)

    results['na_losses_lbs_hr'] = na_losses_lbs_hr
    results['na_from_saltcake_as_na'] = na_from_saltcake_as_na
    results['na_deficit_lbs_hr'] = na_deficit_lbs_hr

    # === STEP 9: Calculate Makeup Requirements (0_SULF!H44-H49) ===
    total_production = inputs['batch_production'] + inputs['cont_production']
    results['total_production_bdt_day'] = total_production

    # Convert saltcake from Na2SO4 to Na2O basis for per-BDT calculation
    # H57 = B40 * (Na2O/Na2SO4) * 24 / production
    saltcake_as_na2o = inputs['saltcake_na_lbs_hr'] * CONV['Na2SO4_to_Na2O']
    results['saltcake_as_na2o'] = saltcake_as_na2o

    # === CTO Sulfur (S Retention Factor!F43 / 0_SULF!B27) ===
    # Direct input from user - calculated in Excel as:
    # F43 = (F70/24)*2000 where F70 = F67*F68*F69
    # Uses CTO-specific S retention factor from S Retention Factor sheet
    cto_s_lbs_hr = inputs.get('cto_s_lbs_hr', 279.52)
    results['cto_s_lbs_hr'] = cto_s_lbs_hr

    makeup = calculate_makeup_summary(
        target_sulfidity_pct=inputs['target_sulfidity_pct'],
        wl_tta_mass_ton_hr=wl_tta_mass_ton_hr,
        wl_na2s_mass_ton_hr=wl_na2s_mass_ton_hr,
        na_deficit_lbs_hr=na_deficit_lbs_hr,
        total_production_bdt_day=total_production,
        saltcake_na_lbs_hr=saltcake_as_na2o,  # Pass as Na2O
        cto_s_lbs_hr=cto_s_lbs_hr,  # CTO sulfur contribution
        nash_concentration=inputs['nash_conc_pct'] / 100,
        naoh_concentration=inputs['naoh_conc_pct'] / 100,
        nash_density=inputs['nash_density'],
        naoh_density=inputs['naoh_density']
    )

    # Store makeup results
    results['nash_dry_lbs_hr'] = makeup.nash_dry_lbs_hr
    results['nash_solution_lbs_hr'] = makeup.nash_solution_lbs_hr
    results['nash_solution_gpm'] = makeup.nash_solution_gpm
    results['naoh_dry_lbs_hr'] = makeup.naoh_dry_lbs_hr
    results['naoh_solution_lbs_hr'] = makeup.naoh_solution_lbs_hr
    results['naoh_solution_gpm'] = makeup.naoh_solution_gpm

    results['nash_dry_lb_bdt_na2o'] = makeup.nash_dry_lb_bdt_na2o
    results['naoh_dry_lb_bdt_na2o'] = makeup.naoh_dry_lb_bdt_na2o
    results['saltcake_lb_bdt_na2o'] = makeup.saltcake_lb_bdt_na2o

    results['na2s_deficit_ton_hr'] = makeup.na2s_deficit_ton_hr
    results['nash_conversion_factor'] = makeup.nash_conversion_factor
    results['na_from_nash'] = makeup.na_from_nash
    results['na_deficit_remaining'] = makeup.na_deficit_remaining

    results['final_tta_ton_hr'] = makeup.final_tta_ton_hr
    results['final_na2s_ton_hr'] = makeup.final_na2s_ton_hr
    results['final_sulfidity_pct'] = makeup.final_sulfidity_pct

    # === STEP 10: Calculate Current and Latent Sulfidity (1_Inventory!C17-C18) ===
    # Excel C18 formula uses:
    # - RB Active Sulfide (B32) in lb/hr → tons/day: (B32/2000)*24
    # - RB TTA (B34) in lb/hr → tons/day: (B34/2000)*24
    # - Makeup Na2S (U102) in ton/hr → tons/day: U102*24
    # - Makeup TTA (U101) in ton/hr → tons/day: U101*24
    # Note: U101 and U102 are FINAL values after underflow losses, not the initial makeup

    # Convert RB outputs from lb/hr to tons/day: (lb/hr / 2000) * 24
    rb_active_sulfide_tons_day = (smelt.active_sulfide / 2000) * 24
    rb_tta_tons_day = (smelt.tta_lbs_hr / 2000) * 24

    # For Excel compatibility, U101 = final TTA - underflow losses
    # U102 = final Na2S - underflow losses
    # Underflow losses factor ≈ P95/U97 (TTA lost / TTA to WLC)
    # Simplified: use final makeup values directly (ton/hr * 24 = tons/day)
    # U101 = U97 - U99 where U99 is underflow TTA loss
    # For now, estimate underflow as ~17% of flow (based on Excel P95/U97 ratio)
    underflow_fraction = 0.165  # ~16.5% underflow loss
    makeup_tta_tons_day = makeup.final_tta_ton_hr * (1 - underflow_fraction) * 24
    makeup_na2s_tons_day = makeup.final_na2s_ton_hr * (1 - underflow_fraction) * 24

    # Calculate sulfidity metrics with all components
    metrics = calculate_sulfidity_metrics(
        wl_tanks, gl_tanks, bl_tanks,
        rb_active_sulfide_tons_day=rb_active_sulfide_tons_day,
        rb_tta_tons_day=rb_tta_tons_day,
        digester_na2s_tons_day=makeup_na2s_tons_day,
        digester_tta_tons_day=makeup_tta_tons_day
    )
    results['current_sulfidity_pct'] = metrics.current_sulfidity_pct
    results['latent_sulfidity_pct'] = metrics.latent_sulfidity_pct
    results['sulfidity_trend'] = metrics.sulfidity_trend

    # Store RB contributions for display
    results['rb_active_sulfide_tons_day'] = rb_active_sulfide_tons_day
    results['rb_tta_tons_day'] = rb_tta_tons_day
    results['makeup_na2s_tons_day'] = makeup_na2s_tons_day
    results['makeup_tta_tons_day'] = makeup_tta_tons_day

    return results


if __name__ == "__main__":
    main()
