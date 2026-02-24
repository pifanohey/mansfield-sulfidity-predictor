"""
Dashboard display components for Streamlit app.
"""

import streamlit as st
from typing import Dict, Optional


def render_sulfidity_gauge(
    current_sulfidity: float,
    target_sulfidity: float,
    latent_sulfidity: Optional[float] = None
):
    """
    Render sulfidity gauge with current vs target.

    Args:
        current_sulfidity: Current WL sulfidity (%)
        target_sulfidity: Target sulfidity (%)
        latent_sulfidity: Optional latent sulfidity (%)
    """
    st.subheader("Sulfidity Status")

    # Determine status color
    diff = abs(current_sulfidity - target_sulfidity)
    if diff <= 0.5:
        status = "ON TARGET"
        color = "green"
    elif diff <= 1.5:
        status = "NEAR TARGET"
        color = "orange"
    else:
        if current_sulfidity > target_sulfidity:
            status = "HIGH"
        else:
            status = "LOW"
        color = "red"

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Current Sulfidity",
            f"{current_sulfidity:.2f}%",
            delta=f"{current_sulfidity - target_sulfidity:.2f}%"
        )

    with col2:
        st.metric(
            "Target Sulfidity",
            f"{target_sulfidity:.1f}%"
        )

    with col3:
        if latent_sulfidity is not None:
            trend_delta = latent_sulfidity - current_sulfidity
            trend_label = "rising" if trend_delta > 0.5 else "falling" if trend_delta < -0.5 else "stable"
            st.metric(
                "Latent Sulfidity",
                f"{latent_sulfidity:.2f}%",
                delta=f"{trend_delta:.2f}% ({trend_label})"
            )

    # Status indicator
    if color == "green":
        st.success(f"Status: {status}")
    elif color == "orange":
        st.warning(f"Status: {status}")
    else:
        st.error(f"Status: {status}")


def render_makeup_summary(
    nash_dry_lb_hr: float,
    naoh_dry_lb_hr: float,
    nash_gpm: float,
    naoh_gpm: float,
    final_sulfidity: float
):
    """
    Render makeup requirements summary.

    Args:
        nash_dry_lb_hr: NaSH requirement (dry lb/hr)
        naoh_dry_lb_hr: NaOH requirement (dry lb/hr)
        nash_gpm: NaSH solution flow (gpm)
        naoh_gpm: NaOH solution flow (gpm)
        final_sulfidity: Predicted final sulfidity (%)
    """
    st.subheader("Makeup Requirements")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**NaSH (40% solution)**")
        st.metric("Dry Rate", f"{nash_dry_lb_hr:.1f} lb/hr")
        st.metric("Solution Flow", f"{nash_gpm:.2f} gpm")

    with col2:
        st.markdown("**NaOH (50% solution)**")
        st.metric("Dry Rate", f"{naoh_dry_lb_hr:.1f} lb/hr")
        st.metric("Solution Flow", f"{naoh_gpm:.2f} gpm")

    st.metric("Predicted Final Sulfidity", f"{final_sulfidity:.2f}%")


def render_mass_balance_summary(
    na_in_lb_hr: float,
    na_out_lb_hr: float,
    s_in_lb_hr: float,
    s_out_lb_hr: float
):
    """
    Render mass balance summary.

    Args:
        na_in_lb_hr: Na input rate (lb/hr)
        na_out_lb_hr: Na output/loss rate (lb/hr)
        s_in_lb_hr: S input rate (lb/hr)
        s_out_lb_hr: S output/loss rate (lb/hr)
    """
    st.subheader("Mass Balance")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Sodium Balance (lb Na2O/hr)**")
        na_balance = na_in_lb_hr - na_out_lb_hr
        na_balance_pct = (na_balance / na_in_lb_hr * 100) if na_in_lb_hr > 0 else 0
        st.metric("Na In", f"{na_in_lb_hr:.0f}")
        st.metric("Na Out/Loss", f"{na_out_lb_hr:.0f}")
        st.metric("Balance", f"{na_balance:.0f} ({na_balance_pct:.1f}%)")

    with col2:
        st.markdown("**Sulfur Balance (lb S/hr)**")
        s_balance = s_in_lb_hr - s_out_lb_hr
        s_balance_pct = (s_balance / s_in_lb_hr * 100) if s_in_lb_hr > 0 else 0
        st.metric("S In", f"{s_in_lb_hr:.0f}")
        st.metric("S Out/Loss", f"{s_out_lb_hr:.0f}")
        st.metric("Balance", f"{s_balance:.0f} ({s_balance_pct:.1f}%)")


def render_inventory_summary(
    tank_volumes: Dict[str, float],
    tta_mass_tons: float,
    na2s_mass_tons: float
):
    """
    Render tank inventory summary.

    Args:
        tank_volumes: Dictionary of tank_name: volume_gallons
        tta_mass_tons: Total TTA mass (tons Na2O)
        na2s_mass_tons: Total Na2S mass (tons Na2O)
    """
    st.subheader("Tank Inventory Summary")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_wl_gal = sum(
            v for k, v in tank_volumes.items()
            if k.startswith('wlc')
        )
        st.metric("Total WL Volume", f"{total_wl_gal:,.0f} gal")

    with col2:
        total_gl_gal = sum(
            v for k, v in tank_volumes.items()
            if k.startswith('gl') or k == 'dump_tank'
        )
        st.metric("Total GL Volume", f"{total_gl_gal:,.0f} gal")

    with col3:
        total_bl_gal = sum(
            v for k, v in tank_volumes.items()
            if 'bl' in k.lower() or 'pct' in k.lower() or k == 'cssc_weak'
        )
        st.metric("Total BL Volume", f"{total_bl_gal:,.0f} gal")

    # Alkali inventory
    st.markdown("**Alkali Inventory**")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total TTA", f"{tta_mass_tons:.2f} tons Na2O")
    with col2:
        st.metric("Total Na2S", f"{na2s_mass_tons:.2f} tons Na2O")


def render_warnings(warnings: list):
    """
    Render validation warnings.

    Args:
        warnings: List of warning messages
    """
    if warnings:
        with st.expander(f"Warnings ({len(warnings)})", expanded=True):
            for warning in warnings:
                st.warning(warning)


def render_errors(errors: list):
    """
    Render validation errors.

    Args:
        errors: List of error messages
    """
    if errors:
        st.error("Validation Errors:")
        for error in errors:
            st.error(f"- {error}")
