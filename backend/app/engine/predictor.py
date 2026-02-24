"""
FOPDT (First-Order Plus Dead-Time) sulfidity predictor.

Based on validated literature:
- "Dynamic Modelling of Process Chemistry in Kraft Pulp Mills" (U of Toronto)
- "Sodium and Sulfur Balance of a Kraft Pulp Mill" (Aalto University)
- "Control of Sulfidity in a Modern Kraft Pulp Mill" (Valmet/TAPPI)

This module predicts WHEN latent sulfidity will become current sulfidity.
The key insight is that static models show WHERE the system will end up,
but FOPDT shows HOW FAST it will get there.

Key equations:
    τ (tau) = Total_Liquor_Volume / Circulation_Rate
    S(t) = S_current + (S_latent - S_current) × (1 - e^(-t/τ))

Interpretation:
    τ = time for 63% of the change to occur
    3τ = time for 95% of the change (practical steady state)
"""

import math
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SulfidityPrediction:
    """FOPDT sulfidity prediction results."""
    tau_hours: float                 # Time constant (hours)
    time_to_63pct_hours: float       # Time for 63% of change
    time_to_95pct_hours: float       # Time for 95% of change (≈ steady state)
    current_sulfidity_pct: float     # Starting point
    latent_sulfidity_pct: float      # Endpoint (steady state)
    predicted_4hr_pct: float         # Prediction at 4 hours
    predicted_8hr_pct: float         # Prediction at 8 hours
    predicted_12hr_pct: float        # Prediction at 12 hours
    predicted_24hr_pct: float        # Prediction at 24 hours
    direction: str                   # 'rising', 'falling', 'stable'


def calculate_time_constant(
    wl_tank_volume_gal: float,
    gl_tank_volume_gal: float,
    circulation_rate_gpm: float,
) -> float:
    """
    Calculate τ (tau) - the system time constant.

    τ = Total_Liquor_Volume / Circulation_Rate

    The time constant represents how long it takes for the system
    to reach 63% of its final value after a step change.

    Args:
        wl_tank_volume_gal: Total WL tank volume (WLC1 + WLC2)
        gl_tank_volume_gal: Total GL tank volume (GL1 + GL2 + Dump Tank)
        circulation_rate_gpm: WL demand (flow through digesters)

    Returns:
        Time constant in hours
    """
    if circulation_rate_gpm <= 0:
        return 24.0  # Default 24 hours if no flow

    total_volume_gal = wl_tank_volume_gal + gl_tank_volume_gal
    tau_minutes = total_volume_gal / circulation_rate_gpm
    tau_hours = tau_minutes / 60

    return tau_hours


def predict_sulfidity_at_time(
    current: float,
    latent: float,
    tau_hours: float,
    time_hours: float,
) -> float:
    """
    FOPDT prediction at a specific time.

    S(t) = S_current + (S_latent - S_current) × (1 - e^(-t/τ))

    Args:
        current: Current sulfidity (%)
        latent: Latent sulfidity - steady state target (%)
        tau_hours: System time constant (hours)
        time_hours: Time point for prediction (hours)

    Returns:
        Predicted sulfidity at time t (%)
    """
    if tau_hours <= 0:
        return latent  # Instant response

    delta = latent - current
    decay_factor = 1 - math.exp(-time_hours / tau_hours)

    return current + delta * decay_factor


def calculate_sulfidity_prediction(
    current_sulfidity_pct: float,
    latent_sulfidity_pct: float,
    wl_tank_volume_gal: float,
    gl_tank_volume_gal: float,
    circulation_rate_gpm: float,
) -> SulfidityPrediction:
    """
    Calculate FOPDT sulfidity prediction.

    This function answers the question: "If I make a change now,
    when will I see it in my White Liquor sulfidity?"

    Args:
        current_sulfidity_pct: Current WL sulfidity from lab/inventory
        latent_sulfidity_pct: Latent sulfidity (steady-state target)
        wl_tank_volume_gal: Total WL tank volume
        gl_tank_volume_gal: Total GL tank volume
        circulation_rate_gpm: WL demand (circulation rate)

    Returns:
        SulfidityPrediction with time constant and predictions at
        4, 8, 12, and 24 hour intervals
    """
    tau = calculate_time_constant(
        wl_tank_volume_gal,
        gl_tank_volume_gal,
        circulation_rate_gpm,
    )

    # Predictions at key time points
    pred_4hr = predict_sulfidity_at_time(
        current_sulfidity_pct, latent_sulfidity_pct, tau, 4
    )
    pred_8hr = predict_sulfidity_at_time(
        current_sulfidity_pct, latent_sulfidity_pct, tau, 8
    )
    pred_12hr = predict_sulfidity_at_time(
        current_sulfidity_pct, latent_sulfidity_pct, tau, 12
    )
    pred_24hr = predict_sulfidity_at_time(
        current_sulfidity_pct, latent_sulfidity_pct, tau, 24
    )

    # Direction classification
    delta = latent_sulfidity_pct - current_sulfidity_pct
    if delta > 0.5:
        direction = 'rising'
    elif delta < -0.5:
        direction = 'falling'
    else:
        direction = 'stable'

    return SulfidityPrediction(
        tau_hours=tau,
        time_to_63pct_hours=tau,
        time_to_95pct_hours=3 * tau,
        current_sulfidity_pct=current_sulfidity_pct,
        latent_sulfidity_pct=latent_sulfidity_pct,
        predicted_4hr_pct=pred_4hr,
        predicted_8hr_pct=pred_8hr,
        predicted_12hr_pct=pred_12hr,
        predicted_24hr_pct=pred_24hr,
        direction=direction,
    )
