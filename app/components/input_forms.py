"""
Input form components for Streamlit app.
"""

import streamlit as st
from typing import Dict, Tuple

from ...config.tank_config import TANKS, TANK_GROUPS
from ...config.constants import DEFAULTS


def render_tank_inputs() -> Dict[str, float]:
    """
    Render tank level input form.

    Returns:
        Dictionary of tank_name: level_ft
    """
    st.subheader("Tank Levels")

    levels = {}

    # White Liquor Clarifiers
    st.markdown("**White Liquor Clarifiers**")
    col1, col2 = st.columns(2)
    with col1:
        levels['wlc_1'] = st.number_input(
            "#1 WLC (ft)",
            min_value=0.0,
            max_value=float(TANKS['wlc_1']['max_level']),
            value=10.0,
            step=0.5,
            key='wlc_1'
        )
    with col2:
        levels['wlc_2'] = st.number_input(
            "#2 WLC (ft)",
            min_value=0.0,
            max_value=float(TANKS['wlc_2']['max_level']),
            value=10.0,
            step=0.5,
            key='wlc_2'
        )

    # Green Liquor Tanks
    st.markdown("**Green Liquor Tanks**")
    col1, col2, col3 = st.columns(3)
    with col1:
        levels['gl_1'] = st.number_input(
            "#1 GL Tank (ft)",
            min_value=0.0,
            max_value=float(TANKS['gl_1']['max_level']),
            value=10.0,
            step=0.5,
            key='gl_1'
        )
    with col2:
        levels['gl_2'] = st.number_input(
            "#2 GL Tank (ft)",
            min_value=0.0,
            max_value=float(TANKS['gl_2']['max_level']),
            value=10.0,
            step=0.5,
            key='gl_2'
        )
    with col3:
        levels['dump_tank'] = st.number_input(
            "Dump Tank (ft)",
            min_value=0.0,
            max_value=float(TANKS['dump_tank']['max_level']),
            value=20.0,
            step=0.5,
            key='dump_tank'
        )

    # Black Liquor Tanks (collapsible)
    with st.expander("Black Liquor Tanks"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            levels['wbl_1'] = st.number_input(
                "#1 Weak BL (ft)",
                min_value=0.0,
                max_value=float(TANKS['wbl_1']['max_level']),
                value=30.0,
                step=1.0,
                key='wbl_1'
            )
        with col2:
            levels['wbl_2'] = st.number_input(
                "#2 Weak BL (ft)",
                min_value=0.0,
                max_value=float(TANKS['wbl_2']['max_level']),
                value=30.0,
                step=1.0,
                key='wbl_2'
            )
        with col3:
            levels['cssc_weak'] = st.number_input(
                "CSSC Weak (ft)",
                min_value=0.0,
                max_value=float(TANKS['cssc_weak']['max_level']),
                value=25.0,
                step=1.0,
                key='cssc_weak'
            )
        with col4:
            levels['tank_50pct'] = st.number_input(
                "50% Tank (ft)",
                min_value=0.0,
                max_value=float(TANKS['tank_50pct']['max_level']),
                value=15.0,
                step=1.0,
                key='tank_50pct'
            )

        col1, col2, col3 = st.columns(3)
        with col1:
            levels['tank_55pct_1'] = st.number_input(
                "#1 55% Tank (ft)",
                min_value=0.0,
                max_value=float(TANKS['tank_55pct_1']['max_level']),
                value=20.0,
                step=1.0,
                key='tank_55pct_1'
            )
        with col2:
            levels['tank_55pct_2'] = st.number_input(
                "#2 55% Tank (ft)",
                min_value=0.0,
                max_value=float(TANKS['tank_55pct_2']['max_level']),
                value=20.0,
                step=1.0,
                key='tank_55pct_2'
            )
        with col3:
            levels['tank_65pct'] = st.number_input(
                "65% Tank (ft)",
                min_value=0.0,
                max_value=float(TANKS['tank_65pct']['max_level']),
                value=20.0,
                step=1.0,
                key='tank_65pct'
            )

    return levels


def render_lab_analysis() -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Render lab analysis input forms for WL and GL.

    Returns:
        Tuple of (wl_analysis, gl_analysis) dictionaries
    """
    st.subheader("Lab Analysis (g Na2O/L)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**White Liquor**")
        wl_tta = st.number_input(
            "WL TTA",
            min_value=0.0,
            max_value=200.0,
            value=120.0,
            step=1.0,
            key='wl_tta'
        )
        wl_ea = st.number_input(
            "WL EA",
            min_value=0.0,
            max_value=150.0,
            value=90.0,
            step=1.0,
            key='wl_ea'
        )
        wl_aa = st.number_input(
            "WL AA",
            min_value=0.0,
            max_value=180.0,
            value=106.0,
            step=1.0,
            key='wl_aa'
        )
        wl_analysis = {'tta': wl_tta, 'ea': wl_ea, 'aa': wl_aa}

        # Calculate and display sulfidity
        if wl_tta > 0:
            wl_sulf = (2 * (wl_aa - wl_ea)) / wl_tta * 100
            st.metric("Calculated Sulfidity", f"{wl_sulf:.1f}%")

    with col2:
        st.markdown("**Green Liquor**")
        gl_tta = st.number_input(
            "GL TTA",
            min_value=0.0,
            max_value=200.0,
            value=117.0,
            step=1.0,
            key='gl_tta'
        )
        gl_ea = st.number_input(
            "GL EA",
            min_value=0.0,
            max_value=100.0,
            value=32.0,
            step=1.0,
            key='gl_ea'
        )
        gl_aa = st.number_input(
            "GL AA",
            min_value=0.0,
            max_value=150.0,
            value=54.0,
            step=1.0,
            key='gl_aa'
        )
        gl_analysis = {'tta': gl_tta, 'ea': gl_ea, 'aa': gl_aa}

        # Calculate and display sulfidity
        if gl_tta > 0:
            gl_sulf = (2 * (gl_aa - gl_ea)) / gl_tta * 100
            st.metric("Calculated Sulfidity", f"{gl_sulf:.1f}%")

    return wl_analysis, gl_analysis


def render_operating_params() -> Dict[str, float]:
    """
    Render operating parameters input form.

    Returns:
        Dictionary of operating parameters
    """
    st.subheader("Operating Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:
        target_sulfidity = st.number_input(
            "Target Sulfidity (%)",
            min_value=20.0,
            max_value=40.0,
            value=DEFAULTS['target_sulfidity_pct'],
            step=0.5,
            key='target_sulfidity'
        )

    with col2:
        reduction_eff = st.number_input(
            "Reduction Efficiency (%)",
            min_value=80.0,
            max_value=99.0,
            value=DEFAULTS['reduction_efficiency_pct'],
            step=0.5,
            key='reduction_eff'
        )

    with col3:
        causticity = st.number_input(
            "Causticity (%)",
            min_value=70.0,
            max_value=95.0,
            value=DEFAULTS['causticity_pct'],
            step=0.5,
            key='causticity'
        )

    return {
        'target_sulfidity_pct': target_sulfidity,
        'reduction_efficiency_pct': reduction_eff,
        'causticity_pct': causticity
    }


def render_bl_analysis() -> Dict[str, float]:
    """
    Render black liquor analysis input form.

    Returns:
        Dictionary of BL analysis parameters
    """
    st.subheader("Black Liquor Analysis")

    col1, col2, col3 = st.columns(3)

    with col1:
        na_pct = st.number_input(
            "Na (% dry solids)",
            min_value=15.0,
            max_value=25.0,
            value=18.97,
            step=0.1,
            key='bl_na_pct'
        )

    with col2:
        s_pct = st.number_input(
            "S (% dry solids)",
            min_value=2.0,
            max_value=8.0,
            value=3.93,
            step=0.1,
            key='bl_s_pct'
        )

    with col3:
        tds_pct = st.number_input(
            "TDS (%)",
            min_value=10.0,
            max_value=75.0,
            value=18.0,
            step=1.0,
            key='bl_tds_pct'
        )

    return {
        'na_pct': na_pct,
        's_pct': s_pct,
        'tds_pct': tds_pct
    }
