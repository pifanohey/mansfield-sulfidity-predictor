"""
Decision guidance engine - 7 rule sets.

Provides actionable recommendations based on calculation results.
Updated for outer-loop-enabled model where BL Na%/S% are computed
from the forward leg (not directly adjustable inputs).

Rule sets:
  1. Sulfidity targeting — final vs target, smelt gap
  2. Recovery Boiler — RE, dead load
  3. Causticizer — CE impact on NaOH
  4. Makeup optimization — NaSH/NaOH levels, constraint mode
  5. Losses — NCG, total S losses, S retention
  6. Dead Load Cycle — RE/CE coupling, death spiral detection
  7. Mass balance — Na balance status, net S surplus/deficit
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from .constants import DEFAULTS


@dataclass
class GuidanceItem:
    """A single guidance recommendation."""
    severity: str  # 'red', 'yellow', 'green'
    category: str  # rule set category
    title: str
    description: str
    action: str
    impact: str = ''


def generate_guidance(results: Dict[str, Any], inputs: Dict[str, Any]) -> List[GuidanceItem]:
    """Generate all guidance items from calculation results."""
    items: List[GuidanceItem] = []
    items.extend(_rule_set_1_sulfidity(results, inputs))
    items.extend(_rule_set_2_recovery_boiler(results, inputs))
    items.extend(_rule_set_3_causticizer(results, inputs))
    items.extend(_rule_set_4_makeup_optimization(results, inputs))
    items.extend(_rule_set_5_losses(results, inputs))
    items.extend(_rule_set_6_dead_load_cycle(results, inputs))
    items.extend(_rule_set_7_mass_balance(results, inputs))
    # Sort: red first, then yellow, then green
    priority = {'red': 0, 'yellow': 1, 'green': 2}
    items.sort(key=lambda x: priority.get(x.severity, 3))
    return items


def _rule_set_1_sulfidity(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """Sulfidity targeting: final vs target, smelt gap."""
    items = []
    final = results.get('final_sulfidity_pct', 0)
    smelt = results.get('smelt_sulfidity_pct', 0)
    target = inputs.get('target_sulfidity_pct', 29.4)

    # Final sulfidity vs target (Secant solver should hit target)
    gap = final - target
    if abs(gap) > 1.0:
        items.append(GuidanceItem(
            severity='red', category='Sulfidity',
            title='Final sulfidity missed target',
            description=f'Final {final:.2f}% vs Target {target:.1f}% (gap {gap:+.2f}%).',
            action='Solver may not have converged. Check inputs and retry.',
        ))
    elif abs(gap) > 0.3:
        items.append(GuidanceItem(
            severity='yellow', category='Sulfidity',
            title='Final sulfidity slightly off target',
            description=f'Final {final:.2f}% vs Target {target:.1f}% (gap {gap:+.2f}%).',
            action='Review convergence. May need tighter tolerance or more iterations.',
        ))
    else:
        items.append(GuidanceItem(
            severity='green', category='Sulfidity',
            title='On target',
            description=f'Final sulfidity {final:.2f}% = Target {target:.1f}%.',
            action='No action needed.',
        ))

    # Smelt-to-target gap indicates how much NaSH must compensate
    smelt_gap = target - smelt
    if smelt_gap > 2.0:
        items.append(GuidanceItem(
            severity='yellow', category='Sulfidity',
            title='Large smelt-to-target gap',
            description=f'Smelt {smelt:.1f}% is {smelt_gap:.1f}% below target {target:.1f}%. '
                       f'NaSH must bridge the entire gap.',
            action='Improving RE or reducing target would lower NaSH demand.',
        ))

    return items


def _rule_set_2_recovery_boiler(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """Recovery boiler health: RE, dead load."""
    items = []
    dead_load = results.get('rb_dead_load', 0)
    tta = results.get('rb_tta_lbs_hr', 1)
    re = inputs.get('reduction_eff_pct', DEFAULTS.get('reduction_efficiency_pct', 95))

    dead_load_pct = (dead_load / tta * 100) if tta > 0 else 0
    if dead_load_pct > 10:
        items.append(GuidanceItem(
            severity='red', category='Recovery Boiler',
            title='High dead load',
            description=f'Dead load is {dead_load_pct:.1f}% of TTA (RE {re:.0f}%).',
            action='Immediate RE investigation needed. Check RB combustion.',
        ))
    elif dead_load_pct > 5:
        items.append(GuidanceItem(
            severity='yellow', category='Recovery Boiler',
            title='Elevated dead load',
            description=f'Dead load is {dead_load_pct:.1f}% of TTA (RE {re:.0f}%).',
            action='RE may be declining. Monitor RB combustion conditions.',
        ))
    else:
        items.append(GuidanceItem(
            severity='green', category='Recovery Boiler',
            title='Recovery Boiler OK',
            description=f'RE {re:.0f}%, Dead Load {dead_load_pct:.1f}% of TTA.',
            action='No action needed.',
        ))

    return items


def _rule_set_3_causticizer(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """Causticizer: CE and its impact on NaOH."""
    items = []
    ce = inputs.get('causticity_pct', 81)
    naoh_constraint = results.get('naoh_constraint', 'losses')

    if ce < 75:
        items.append(GuidanceItem(
            severity='red', category='Causticizer',
            title='Very low CE',
            description=f'CE at {ce:.0f}%. EA demand likely binding NaOH constraint.',
            action='Urgent: Check lime quality, dosage, slaker temperature. '
                   'Consider lime kiln operation.',
        ))
    elif ce < 78:
        sev = 'red' if naoh_constraint == 'EA_demand' else 'yellow'
        items.append(GuidanceItem(
            severity=sev, category='Causticizer',
            title='Low CE' + (' driving EA constraint' if naoh_constraint == 'EA_demand' else ''),
            description=f'CE at {ce:.0f}%. NaOH constraint: {naoh_constraint}.',
            action='Check lime quality, dosage, slaker temperature.',
        ))

    return items


def _rule_set_4_makeup_optimization(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """Makeup chemical rates and constraint mode."""
    items = []
    nash = results.get('nash_dry_lbs_hr', 0)
    naoh = results.get('naoh_dry_lbs_hr', 0)
    naoh_constraint = results.get('naoh_constraint', 'losses')
    total_prod = results.get('total_production_bdt_day', 1888)

    # Normalize to lb/BDT for mill-size-independent thresholds
    nash_per_bdt = (nash * 24 / total_prod) if total_prod > 0 else 0
    naoh_per_bdt = (naoh * 24 / total_prod) if total_prod > 0 else 0

    # NaSH: typical range ~15-20 lb/BDT; >25 is high
    if nash_per_bdt > 25:
        items.append(GuidanceItem(
            severity='yellow', category='Makeup',
            title='High NaSH consumption',
            description=f'NaSH at {nash:.0f} lb/hr ({nash_per_bdt:.1f} lb/BDT).',
            action='Review S losses (especially NCG), RE, and target sulfidity.',
        ))

    # NaOH: typical range ~25-35 lb/BDT; >45 is high
    if naoh_per_bdt > 45:
        items.append(GuidanceItem(
            severity='yellow', category='Makeup',
            title='High NaOH consumption',
            description=f'NaOH at {naoh:.0f} lb/hr ({naoh_per_bdt:.1f} lb/BDT). '
                       f'Constraint: {naoh_constraint}.',
            action='Check CE (if EA constraint) or Na losses (if losses constraint).',
        ))

    # Report NaOH constraint mode
    if naoh_constraint == 'EA_demand':
        items.append(GuidanceItem(
            severity='yellow', category='Makeup',
            title='NaOH sized by EA demand (not losses)',
            description=f'CE is low enough that EA demand exceeds Na loss makeup.',
            action='Improving CE would reduce NaOH requirement.',
        ))

    return items


def _rule_set_5_losses(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """Loss table: NCG, total S losses, S retention."""
    items = []

    # NCG S loss — read from flattened inputs or DEFAULTS
    ncg_s = inputs.get('loss_ncg_s', DEFAULTS.get('loss_ncg_s', 8.5))
    total_s_loss_bdt = results.get('total_s_losses_lb_bdt', 0)
    s_retention_weak = results.get('s_retention_weak', 0)

    if ncg_s > 10:
        items.append(GuidanceItem(
            severity='yellow', category='Losses',
            title='High NCG S losses',
            description=f'NCG S loss at {ncg_s:.1f} lb S/BDT (default 8.5).',
            action='Verify NCG collection and incineration systems.',
        ))

    # S retention below 80% is concerning
    if 0 < s_retention_weak < 0.80:
        items.append(GuidanceItem(
            severity='yellow', category='Losses',
            title='Low S retention',
            description=f'Weak S retention at {s_retention_weak*100:.1f}% (< 80%).',
            action='Run detailed loss audit. Major S losses somewhere in circuit.',
        ))

    return items


def _rule_set_6_dead_load_cycle(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """
    Dead Load Cycle health monitoring.

    The Dead Load Cycle couples RE and CE through Na₂SO₄ accumulation:
    - Low RE -> High Na₂SO₄ -> Hydraulic limit on slaker -> Low CE
    - Low CE -> More Na₂CO₃ in BL -> Lower heating value -> Low RE

    When both engage, the system enters a "death spiral" that's hard to recover from.
    """
    items = []

    ce = inputs.get('causticity_pct', 81)
    re = inputs.get('reduction_eff_pct', DEFAULTS.get('reduction_efficiency_pct', 95))
    dead_load = results.get('rb_dead_load', 0)
    tta = results.get('rb_tta_lbs_hr', 1)
    nash_dry = results.get('nash_dry_lbs_hr', 0)
    naoh_dry = results.get('naoh_dry_lbs_hr', 0)

    dead_load_pct = (dead_load / tta * 100) if tta > 0 else 0

    CE_THRESHOLD = 78
    RE_THRESHOLD = 93

    hydraulic_limit = ce < CE_THRESHOLD
    thermal_limit = re < RE_THRESHOLD

    if hydraulic_limit and thermal_limit:
        items.append(GuidanceItem(
            severity='red',
            category='Dead Load Cycle',
            title='DEATH SPIRAL DETECTED',
            description=f'CE={ce:.0f}% (< {CE_THRESHOLD}%) AND RE={re:.0f}% (< {RE_THRESHOLD}%). '
                       f'Dead Load={dead_load_pct:.1f}% of TTA. System in positive feedback loop.',
            action='EMERGENCY: Stop ALL sulfur inputs (NaSH, saltcake if possible). '
                   'NaOH ONLY to maintain TTA. Investigate RB combustion urgently.',
            impact=f'Current NaSH={nash_dry:.0f} lb/hr should be ZERO. '
                   f'Current NaOH={naoh_dry:.0f} lb/hr may need increase.',
        ))
    elif thermal_limit:
        items.append(GuidanceItem(
            severity='red',
            category='Dead Load Cycle',
            title='Thermal Limit - Low RE',
            description=f'RE={re:.0f}% (< {RE_THRESHOLD}%) but CE={ce:.0f}% still OK. '
                       f'Dead Load={dead_load_pct:.1f}% of TTA. RB struggling thermally.',
            action='Reduce or stop NaSH (reduces S input to RB). '
                   'Maintain TTA with NaOH. Check RB combustion: air/liquor ratio, '
                   'liquor temperature, dry solids %.',
            impact=f'If NaSH continues at {nash_dry:.0f} lb/hr, CE will drop next (hydraulic limit).',
        ))
    elif hydraulic_limit:
        items.append(GuidanceItem(
            severity='yellow',
            category='Dead Load Cycle',
            title='Hydraulic Limit - Low CE',
            description=f'CE={ce:.0f}% (< {CE_THRESHOLD}%) but RE={re:.0f}% still OK. '
                       f'Slaker may be hydraulically overloaded.',
            action='Switch to NaOH-only makeup (reduces flow demand on slaker). '
                   'Check lime quality and dosage. Consider slaker capacity.',
            impact=f'NaOH provides Na without flow penalty. '
                   f'Current NaSH={nash_dry:.0f} lb/hr adds volume; consider reducing.',
        ))
    else:
        if dead_load_pct > 5:
            items.append(GuidanceItem(
                severity='yellow',
                category='Dead Load Cycle',
                title='Elevated Dead Load',
                description=f'Dead Load={dead_load_pct:.1f}% of TTA (> 5%). '
                           f'RE={re:.0f}%, CE={ce:.0f}% still healthy.',
                action='Monitor trend. If dead load continues rising, '
                       'thermal or hydraulic limits may approach.',
            ))
        else:
            items.append(GuidanceItem(
                severity='green',
                category='Dead Load Cycle',
                title='Loop Health OK',
                description=f'RE={re:.0f}%, CE={ce:.0f}%, Dead Load={dead_load_pct:.1f}% of TTA. '
                           'Dead Load Cycle operating normally.',
                action='Maintain current NaSH/NaOH strategy.',
            ))

    return items


def _rule_set_7_mass_balance(results: Dict, inputs: Dict) -> List[GuidanceItem]:
    """Na and S mass balance health."""
    items = []

    na_status = results.get('na_balance_status', 'steady_state')
    na_accum = results.get('na_accumulation_lb_hr', 0)
    net_s = results.get('net_s_balance_lb_hr', 0)
    nash = results.get('nash_dry_lbs_hr', 0)

    # Na balance
    if na_status == 'depleting_inventory':
        items.append(GuidanceItem(
            severity='red', category='Mass Balance',
            title='Na inventory depleting',
            description=f'Na accumulation {na_accum:+.0f} lb/hr. '
                       f'Losing Na faster than adding.',
            action='Increase NaOH or saltcake. Check Na losses.',
        ))
    elif na_status == 'building_inventory':
        items.append(GuidanceItem(
            severity='yellow', category='Mass Balance',
            title='Na inventory building',
            description=f'Na accumulation {na_accum:+.0f} lb/hr. '
                       f'Adding Na faster than losing.',
            action='May be intentional. If persistent, reduce NaOH or saltcake.',
        ))

    # Net S balance
    if net_s > 200:
        items.append(GuidanceItem(
            severity='yellow', category='Mass Balance',
            title='S surplus',
            description=f'Net S balance {net_s:+.0f} lb/hr. '
                       f'More S entering than leaving.',
            action='S will accumulate, raising sulfidity over time. '
                   'Consider reducing NaSH or target sulfidity.',
            impact=f'NaSH at {nash:.0f} lb/hr; Secant solver may be oversizing slightly.',
        ))
    elif net_s < -200:
        items.append(GuidanceItem(
            severity='yellow', category='Mass Balance',
            title='S deficit',
            description=f'Net S balance {net_s:+.0f} lb/hr. '
                       f'More S leaving than entering.',
            action='S will deplete, lowering sulfidity over time. '
                   'Consider increasing NaSH, saltcake, or CTO.',
        ))

    return items
