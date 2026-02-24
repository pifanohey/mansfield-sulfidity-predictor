"""
Evaporator model — removes water to target TDS%.

All solids (inorganic + organic) are conserved. Na% d.s. and S% d.s.
are invariant through evaporation (only water changes).

Reference: PRD §5.3 — Evaporator outputs virgin SBL; RB adds ash separately.
"""

from dataclasses import dataclass

from .fiberline import MixedWBLOutput


@dataclass
class EvaporatorOutput:
    """Strong Black Liquor output from evaporator."""
    sbl_flow_lb_hr: float         # Total SBL mass flow
    sbl_tds_pct: float            # Should match target
    sbl_na_pct_ds: float          # = wbl_na_pct_ds (unchanged)
    sbl_s_pct_ds: float           # = wbl_s_pct_ds (unchanged)
    water_removed_lb_hr: float    # For energy balance (future)
    na_element_lb_hr: float       # Conservation check
    s_element_lb_hr: float        # Conservation check
    total_solids_lb_hr: float     # Conservation check


def calculate_evaporator(
    wbl: MixedWBLOutput,
    target_tds_pct: float = 69.1,
) -> EvaporatorOutput:
    """
    Remove water from WBL to reach target TDS%.

    Solids are fully conserved. Na% and S% on dry solids are invariant
    (only water is removed). This produces virgin SBL — the RB code
    adds ash and saltcake internally.

    Args:
        wbl: Mixed weak black liquor from WBL mixer
        target_tds_pct: Target total dissolved solids (default matches bl_tds_pct)
    """
    solids = wbl.total_solids_lb_hr

    if target_tds_pct <= 0 or target_tds_pct >= 100 or solids <= 0:
        return EvaporatorOutput(
            sbl_flow_lb_hr=0, sbl_tds_pct=0, sbl_na_pct_ds=0, sbl_s_pct_ds=0,
            water_removed_lb_hr=0, na_element_lb_hr=0, s_element_lb_hr=0,
            total_solids_lb_hr=0,
        )

    # Water needed to achieve target TDS%
    water_needed = solids * (100 - target_tds_pct) / target_tds_pct
    water_removed = wbl.water_lb_hr - water_needed

    return EvaporatorOutput(
        sbl_flow_lb_hr=solids + water_needed,
        sbl_tds_pct=target_tds_pct,
        sbl_na_pct_ds=wbl.na_pct_ds,   # UNCHANGED — only water removed
        sbl_s_pct_ds=wbl.s_pct_ds,     # UNCHANGED — only water removed
        water_removed_lb_hr=water_removed,
        na_element_lb_hr=wbl.na_element_lb_hr,
        s_element_lb_hr=wbl.s_element_lb_hr,
        total_solids_lb_hr=solids,
    )
