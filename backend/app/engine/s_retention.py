"""
Sulfur retention factor and loss calculations.

Reference: S Rention Factor sheet in Excel v4

S retention factors are CALCULATED (not fixed inputs):
  G4 = (dry_solids_to_RB / production) * 2000   # lb DS/BDT
  G5 = G4 * S%_fired                             # lb S/BDT throughput
  G6 = 1 - (sum_all_losses / G5)                 # weak BL retention
  G7 = 1 - (ash+stack_losses / G5)               # strong/fired retention
"""

from dataclasses import dataclass, fields
from typing import Dict, List, Optional, Tuple

from .constants import MW, CONV


# Ordered list of (field_prefix, display_name, unit_operation_area)
LOSS_SOURCES: List[Tuple[str, str, str]] = [
    ('pulp_washable_soda', 'Pulp Washable Soda', 'Fiberline'),
    ('pulp_bound_soda', 'Pulp Bound Soda', 'Fiberline'),
    ('pulp_mill_spills', 'Pulp Mill Spills', 'Fiberline'),
    ('evap_spill', 'Evaps Spill/Boilout/Pond', 'Evaporator'),
    ('rb_ash', 'RB Ash', 'Recovery Boiler'),
    ('rb_stack', 'RB Stack', 'Recovery Boiler'),
    ('dregs_filter', 'Dregs Filter', 'Recausticizing'),
    ('grits', 'Grits', 'Recausticizing'),
    ('weak_wash_overflow', 'Weak Wash Overflow', 'Recausticizing'),
    ('ncg', 'NCG', 'NCG System'),
    ('recaust_spill', 'Recaust Spill', 'Recausticizing'),
    ('rb_dump_tank', 'RB Dump Tank', 'Recovery Boiler'),
    ('kiln_scrubber', 'Kiln Scrubber', 'Lime Kiln'),
    ('truck_out_gl', 'Truck Out Green Liquor', 'Other'),
    ('unaccounted', 'Unaccounted', 'Other'),
]


@dataclass
class SodaSulfurLosses:
    """Unified soda & sulfur loss table — user-editable inputs.
    All values in lb/BDT pulp. Converted to lb/hr by multiplying
    by total_production_bdt_day / 24."""
    # Fiberline
    pulp_washable_soda_s: float = 3.0
    pulp_washable_soda_na: float = 18.5
    pulp_bound_soda_s: float = 0.0
    pulp_bound_soda_na: float = 7.4
    pulp_mill_spills_s: float = 0.0
    pulp_mill_spills_na: float = 0.3
    # Evaporator
    evap_spill_s: float = 2.4
    evap_spill_na: float = 5.2
    # Recovery Boiler
    rb_ash_s: float = 1.3
    rb_ash_na: float = 2.8
    rb_stack_s: float = 0.3
    rb_stack_na: float = 0.8
    # Recausticizing
    dregs_filter_s: float = 0.4
    dregs_filter_na: float = 2.4
    grits_s: float = 0.2
    grits_na: float = 1.5
    weak_wash_overflow_s: float = 0.1
    weak_wash_overflow_na: float = 0.7
    ncg_s: float = 8.5
    ncg_na: float = 1.0
    recaust_spill_s: float = 0.4
    recaust_spill_na: float = 2.2
    rb_dump_tank_s: float = 0.0
    rb_dump_tank_na: float = 0.0
    kiln_scrubber_s: float = 0.0
    kiln_scrubber_na: float = 0.0
    # Other
    truck_out_gl_s: float = 0.0
    truck_out_gl_na: float = 0.0
    unaccounted_s: float = 0.0
    unaccounted_na: float = 0.0

    @property
    def total_s_lb_bdt(self) -> float:
        """Sum all *_s fields."""
        return sum(getattr(self, f'{prefix}_s') for prefix, _, _ in LOSS_SOURCES)

    @property
    def total_na_lb_bdt(self) -> float:
        """Sum all *_na fields."""
        return sum(getattr(self, f'{prefix}_na') for prefix, _, _ in LOSS_SOURCES)

    @property
    def fiberline_s_lb_bdt(self) -> float:
        """Fiberline S losses — already modeled in forward leg via s_loss_digester_pct."""
        return self.pulp_washable_soda_s + self.pulp_bound_soda_s + self.pulp_mill_spills_s

    @property
    def non_fiberline_s_lb_bdt(self) -> float:
        """All S losses except fiberline. These are applied at the RB via s_retention_strong
        because they aren't individually modeled in the physical simulation."""
        return self.total_s_lb_bdt - self.fiberline_s_lb_bdt

    @property
    def rb_s_lb_bdt(self) -> float:
        """RB losses S only (ash + stack)."""
        return self.rb_ash_s + self.rb_stack_s

    @property
    def rb_na_lb_bdt(self) -> float:
        """RB losses Na2O only (ash + stack) — replaces rb_losses_na2o_bdt."""
        return self.rb_ash_na + self.rb_stack_na


@dataclass
class SRetentionResults:
    """Results from S retention factor calculations."""
    # Computed retention factors
    s_retention_weak: float           # G6: weak BL / overall retention
    s_retention_strong: float         # G7: strong/fired (RB only) retention
    s_throughput_lb_bdt: float        # G5: lb S/BDT through RB
    ds_per_bdt: float                 # G4: lb DS/BDT

    # Loss flows
    total_s_losses_lb_hr: float
    total_s_losses_lb_bdt: float
    s_from_digesters_na2o_lb_hr: float
    s_from_saltcake_lb_hr: float
    s_from_cto_lb_hr: float
    net_s_balance_lb_hr: float
    total_production_bdt_day: float
    loss_breakdown: SodaSulfurLosses


def calculate_s_retention_factors(
    dry_solids_lbs_hr: float,
    total_production_bdt_day: float,
    bl_s_pct_fired: float,
    losses: SodaSulfurLosses,
) -> Dict[str, float]:
    """
    Calculate S retention factors from losses and S throughput.

    Excel S_Ret sheet:
      G4 = (dry_solids_lbs_hr * 24 / total_production_bdt_day)  # lb DS/BDT
      G5 = G4 * S%_fired / 100                                  # lb S/BDT throughput
      G6 = 1 - (total_losses / G5)                               # weak BL retention
      G7 = 1 - (rb_losses / G5)                                  # strong/fired retention
    """
    if total_production_bdt_day <= 0 or dry_solids_lbs_hr <= 0:
        return {
            'ds_per_bdt': 0.0,
            's_throughput_lb_bdt': 0.0,
            's_retention_weak': 0.9045,
            's_retention_strong': 0.9861,
        }

    # G4: lb dry solids per BDT pulp
    ds_per_bdt = (dry_solids_lbs_hr * 24) / total_production_bdt_day

    # G5: lb S per BDT through the RB
    s_throughput = ds_per_bdt * bl_s_pct_fired / 100

    if s_throughput <= 0:
        return {
            'ds_per_bdt': ds_per_bdt,
            's_throughput_lb_bdt': 0.0,
            's_retention_weak': 0.9045,
            's_retention_strong': 0.9861,
        }

    # G6: Weak BL S retention = 1 - (all losses / throughput)
    s_ret_weak = 1.0 - (losses.total_s_lb_bdt / s_throughput)
    s_ret_weak = max(0.0, min(1.0, s_ret_weak))

    # G7: Strong/fired S retention = 1 - (RB losses only / throughput)
    s_ret_strong = 1.0 - (losses.rb_s_lb_bdt / s_throughput)
    s_ret_strong = max(0.0, min(1.0, s_ret_strong))

    return {
        'ds_per_bdt': ds_per_bdt,
        's_throughput_lb_bdt': s_throughput,
        's_retention_weak': s_ret_weak,
        's_retention_strong': s_ret_strong,
    }


def calculate_s_retention(
    total_production_bdt_day: float,
    dry_solids_lbs_hr: float,
    bl_s_pct_fired: float,
    saltcake_s_lb_hr: float = 0.0,
    cto_s_lb_hr: float = 0.0,
    losses: Optional[SodaSulfurLosses] = None,
) -> SRetentionResults:
    """
    Calculate S retention factors and related values.

    Key change from old code: retention factors are COMPUTED from
    dry solids, S%, and losses — not fixed inputs.
    """
    if losses is None:
        losses = SodaSulfurLosses()

    if total_production_bdt_day == 0:
        return SRetentionResults(
            s_retention_weak=0.9045,
            s_retention_strong=0.9861,
            s_throughput_lb_bdt=0.0,
            ds_per_bdt=0.0,
            total_s_losses_lb_hr=0, total_s_losses_lb_bdt=0,
            s_from_digesters_na2o_lb_hr=0, s_from_saltcake_lb_hr=0,
            s_from_cto_lb_hr=0, net_s_balance_lb_hr=0,
            total_production_bdt_day=0,
            loss_breakdown=losses,
        )

    # Compute retention factors
    ret_factors = calculate_s_retention_factors(
        dry_solids_lbs_hr, total_production_bdt_day,
        bl_s_pct_fired, losses,
    )

    total_s_loss_lb_bdt = losses.total_s_lb_bdt
    total_s_losses_lb_hr = (total_s_loss_lb_bdt * total_production_bdt_day) / 24

    # S from digesters as Na2O (for makeup calculation)
    s_from_digesters_na2o = total_s_losses_lb_hr * (MW['Na2O'] / (2 * MW['S']))

    # S contributions from saltcake and CTO (using computed strong retention)
    re_frac = 0.95  # This gets overridden by the caller typically
    s_ret_strong = ret_factors['s_retention_strong']
    s_from_saltcake = saltcake_s_lb_hr
    s_from_cto = cto_s_lb_hr

    # Net S balance = losses - additions
    net_s_balance = total_s_losses_lb_hr - s_from_saltcake - s_from_cto

    return SRetentionResults(
        s_retention_weak=ret_factors['s_retention_weak'],
        s_retention_strong=ret_factors['s_retention_strong'],
        s_throughput_lb_bdt=ret_factors['s_throughput_lb_bdt'],
        ds_per_bdt=ret_factors['ds_per_bdt'],
        total_s_losses_lb_hr=total_s_losses_lb_hr,
        total_s_losses_lb_bdt=total_s_loss_lb_bdt,
        s_from_digesters_na2o_lb_hr=s_from_digesters_na2o,
        s_from_saltcake_lb_hr=s_from_saltcake,
        s_from_cto_lb_hr=s_from_cto,
        net_s_balance_lb_hr=net_s_balance,
        total_production_bdt_day=total_production_bdt_day,
        loss_breakdown=losses,
    )


def calculate_losses_detailed(
    total_production_bdt_day: float,
    losses: Optional[SodaSulfurLosses] = None,
) -> List[Dict[str, float]]:
    """Calculate detailed losses by source — 13 rows with both S and Na2O columns."""
    if losses is None:
        losses = SodaSulfurLosses()

    rows = []
    for prefix, display_name, area in LOSS_SOURCES:
        s_lb_bdt = getattr(losses, f'{prefix}_s')
        na_lb_bdt = getattr(losses, f'{prefix}_na')
        s_lb_hr = (s_lb_bdt * total_production_bdt_day) / 24
        na_lb_hr = (na_lb_bdt * total_production_bdt_day) / 24
        rows.append({
            'source': display_name,
            's_lb_hr': s_lb_hr,
            's_lb_bdt': s_lb_bdt,
            'na2o_lb_hr': na_lb_hr,
            'na2o_lb_bdt': na_lb_bdt,
        })

    return rows
