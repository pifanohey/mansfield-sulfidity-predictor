"""
Chart components for Streamlit app.
"""

import streamlit as st
from typing import Dict, List, Optional
import json


def render_trend_chart(
    timestamps: List[str],
    current_sulfidity: List[float],
    latent_sulfidity: List[float],
    target_sulfidity: float
):
    """
    Render sulfidity trend chart.

    Args:
        timestamps: List of timestamp strings
        current_sulfidity: List of current sulfidity values
        latent_sulfidity: List of latent sulfidity values
        target_sulfidity: Target sulfidity line
    """
    st.subheader("Sulfidity Trend")

    # Create data for chart
    import pandas as pd

    if len(timestamps) > 0:
        df = pd.DataFrame({
            'Time': timestamps,
            'Current': current_sulfidity,
            'Latent': latent_sulfidity,
            'Target': [target_sulfidity] * len(timestamps)
        })

        st.line_chart(df.set_index('Time'))
    else:
        st.info("No trend data available yet. Data will appear after multiple readings.")


def render_tank_levels_chart(tank_levels: Dict[str, float], tank_maxes: Dict[str, float]):
    """
    Render tank levels as a bar chart.

    Args:
        tank_levels: Dictionary of tank_name: level_ft
        tank_maxes: Dictionary of tank_name: max_level_ft
    """
    st.subheader("Tank Levels")

    import pandas as pd

    # Calculate percentages
    data = []
    for tank, level in tank_levels.items():
        max_level = tank_maxes.get(tank, 100)
        pct = (level / max_level) * 100 if max_level > 0 else 0
        # Format tank name for display
        display_name = tank.replace('_', ' ').upper()
        data.append({
            'Tank': display_name,
            'Level %': pct,
            'Level (ft)': level
        })

    df = pd.DataFrame(data)

    # Color code by fill level
    st.bar_chart(df.set_index('Tank')['Level %'])


def render_mass_balance_sankey(
    na_flows: Dict[str, float],
    s_flows: Dict[str, float]
):
    """
    Render mass balance as a simple flow diagram.

    Note: Full Sankey requires plotly. This is a simplified text version.

    Args:
        na_flows: Dictionary of Na flow names: values (lb/hr)
        s_flows: Dictionary of S flow names: values (lb/hr)
    """
    st.subheader("Mass Balance Flow")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Sodium Flows (lb Na2O/hr)**")
        for name, value in na_flows.items():
            if value > 0:
                st.text(f"  + {name}: {value:,.0f}")
            else:
                st.text(f"  - {name}: {abs(value):,.0f}")

    with col2:
        st.markdown("**Sulfur Flows (lb S/hr)**")
        for name, value in s_flows.items():
            if value > 0:
                st.text(f"  + {name}: {value:,.0f}")
            else:
                st.text(f"  - {name}: {abs(value):,.0f}")


def render_makeup_optimization_chart(
    nash_scenarios: List[float],
    naoh_scenarios: List[float],
    sulfidity_results: List[float],
    target_sulfidity: float
):
    """
    Render makeup optimization scenarios.

    Args:
        nash_scenarios: List of NaSH rates to evaluate
        naoh_scenarios: List of NaOH rates (corresponding)
        sulfidity_results: Resulting sulfidity for each scenario
        target_sulfidity: Target sulfidity line
    """
    st.subheader("Makeup Optimization")

    import pandas as pd

    df = pd.DataFrame({
        'NaSH (lb/hr)': nash_scenarios,
        'NaOH (lb/hr)': naoh_scenarios,
        'Resulting Sulfidity (%)': sulfidity_results
    })

    st.dataframe(df)

    # Highlight optimal scenario
    diffs = [abs(s - target_sulfidity) for s in sulfidity_results]
    optimal_idx = diffs.index(min(diffs))
    st.success(
        f"Optimal: NaSH = {nash_scenarios[optimal_idx]:.0f} lb/hr, "
        f"NaOH = {naoh_scenarios[optimal_idx]:.0f} lb/hr "
        f"(Sulfidity = {sulfidity_results[optimal_idx]:.2f}%)"
    )


def render_recovery_boiler_summary(
    smelt_sulfidity: float,
    reduction_efficiency: float,
    tta_lb_hr: float,
    active_sulfide_lb_hr: float,
    dead_load_lb_hr: float
):
    """
    Render recovery boiler calculation summary.

    Args:
        smelt_sulfidity: Calculated smelt sulfidity (%)
        reduction_efficiency: RB reduction efficiency (%)
        tta_lb_hr: TTA generated (lb/hr)
        active_sulfide_lb_hr: Active Na2S generated (lb/hr)
        dead_load_lb_hr: Dead load (unreduced sulfate) (lb/hr)
    """
    st.subheader("Recovery Boiler Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Smelt Sulfidity", f"{smelt_sulfidity:.2f}%")
        st.metric("Reduction Efficiency", f"{reduction_efficiency:.1f}%")

    with col2:
        st.metric("TTA Generated", f"{tta_lb_hr:,.0f} lb/hr")
        st.metric("Active Sulfide (Na2S)", f"{active_sulfide_lb_hr:,.0f} lb/hr")

    # Dead load indicator
    dead_load_pct = (dead_load_lb_hr / tta_lb_hr * 100) if tta_lb_hr > 0 else 0
    if dead_load_pct < 10:
        st.success(f"Dead Load: {dead_load_lb_hr:,.0f} lb/hr ({dead_load_pct:.1f}%) - Good")
    elif dead_load_pct < 15:
        st.warning(f"Dead Load: {dead_load_lb_hr:,.0f} lb/hr ({dead_load_pct:.1f}%) - Elevated")
    else:
        st.error(f"Dead Load: {dead_load_lb_hr:,.0f} lb/hr ({dead_load_pct:.1f}%) - High")
