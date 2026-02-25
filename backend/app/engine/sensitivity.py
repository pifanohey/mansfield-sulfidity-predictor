"""
Auto-perturbation sensitivity analysis.

Runs the calculation engine with perturbed inputs to show
directional sensitivity at the current operating point.

With the outer loop enabled, BL Na%/S% lab inputs are initial guesses
overridden by the forward leg — perturbing them has negligible effect.
Instead, we perturb physical parameters that change the system:
  - RE, Target Sulfidity, CE (process chemistry)
  - Production, CTO, Na losses (mass balance drivers)
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
import copy

logger = logging.getLogger(__name__)

from .orchestrator import run_calculations
from .constants import DEFAULTS

# Map input keys to DEFAULTS keys where they differ
_KEY_TO_DEFAULT = {
    'reduction_eff_pct': 'reduction_efficiency_pct',
}

# Pine production default from fiberline configs
_pine_prod_default = next(
    (fl.production_bdt_day for fl in DEFAULTS['fiberlines'] if fl.id == 'pine'), 1250.69
)


@dataclass
class SensitivityResult:
    """Result of a single perturbation."""
    parameter: str
    description: str
    base_value: float
    perturbed_value: float
    outputs: Dict[str, Dict[str, float]]  # output_name -> {base, perturbed, delta, delta_pct}


# Define perturbations: (input_key, description, delta_value)
# Only parameters that produce meaningful changes with outer loop enabled.
# Special key '__fiberline_pine_production' is handled in the sensitivity runner.
PERTURBATIONS = [
    ('reduction_eff_pct', 'RE -2%', -2.0),
    ('reduction_eff_pct', 'RE +2%', 2.0),
    ('target_sulfidity_pct', 'Target +1%', 1.0),
    ('target_sulfidity_pct', 'Target -1%', -1.0),
    ('causticity_pct', 'CE -6% (75%)', -6.0),
    ('__fiberline_pine_production', 'Pine prod +10%', round(_pine_prod_default * 0.10, 1)),
    ('cto_tpd', 'CTO +20 TPD', 20.0),
    ('loss_pulp_washable_soda_na', 'Wash Na loss +5 lb/BDT', 5.0),
]

# Outputs to track
TRACKED_OUTPUTS = [
    'final_sulfidity_pct',
    'nash_dry_lbs_hr',
    'naoh_dry_lbs_hr',
    'smelt_sulfidity_pct',
    'bl_s_pct_used',
    'bl_na_pct_used',
]


def run_sensitivity_analysis(
    base_inputs: Dict[str, Any],
    perturbations: List[tuple] = None,
) -> List[SensitivityResult]:
    """
    Run the calculation engine with perturbations to compute sensitivity.

    Returns a list of SensitivityResult for each perturbation.
    """
    if perturbations is None:
        perturbations = PERTURBATIONS

    # Run base case
    base_results = run_calculations(base_inputs)

    results = []
    for param_key, description, delta in perturbations:
        perturbed_inputs = copy.deepcopy(base_inputs)

        # Special handling for fiberline production perturbation
        if param_key == '__fiberline_pine_production':
            fl_configs = perturbed_inputs.get('fiberlines', copy.deepcopy(DEFAULTS['fiberlines']))
            pine_fl = next((fl for fl in fl_configs if fl.id == 'pine'), None)
            base_val = pine_fl.production_bdt_day if pine_fl else _pine_prod_default
            new_val = base_val + delta
            if pine_fl:
                pine_fl.defaults['production_bdt_day'] = new_val
            perturbed_inputs['fiberlines'] = fl_configs
        else:
            default_key = _KEY_TO_DEFAULT.get(param_key, param_key)
            base_val = perturbed_inputs.get(param_key, DEFAULTS.get(default_key, 0.0))
            new_val = base_val + delta
            perturbed_inputs[param_key] = new_val

        try:
            perturbed_results = run_calculations(perturbed_inputs)
        except Exception:
            logger.warning("Sensitivity perturbation failed: %s (%s)", description, param_key, exc_info=True)
            continue

        outputs = {}
        for out_key in TRACKED_OUTPUTS:
            b = base_results.get(out_key, 0.0)
            p = perturbed_results.get(out_key, 0.0)
            d = p - b
            d_pct = (d / b * 100) if b != 0 else 0.0
            outputs[out_key] = {
                'base': round(b, 2),
                'perturbed': round(p, 2),
                'delta': round(d, 2),
                'delta_pct': round(d_pct, 2),
            }

        results.append(SensitivityResult(
            parameter=param_key,
            description=description,
            base_value=base_val,
            perturbed_value=new_val,
            outputs=outputs,
        ))

    return results
