"""Makeup chemical configurations for sulfidity prediction.

Each mill uses one primary makeup chemical. The solver uses these constants
to convert between dry chemical mass and elemental Na/S contributions.

Supported chemicals:
  - NaSH (sodium hydrosulfide) — most common, adds both Na and S
  - Saltcake (Na2SO4, sodium sulfate) — adds both Na and S, lower S yield
  - Emulsified sulfur (elemental S) — adds S only, no Na contribution
  - NaOH (caustic soda) — adds Na only, no S contribution

Usage:
    from app.engine.makeup_chemicals import get_makeup_config

    config = get_makeup_config("nash")
    s_added = dry_lb_hr * config["s_factor"]
    na2o_added = dry_lb_hr * config["na2o_factor"]
"""

from .constants import MW

MAKEUP_CHEMICALS = {
    "nash": {
        "name": "NaSH",
        "formula": "NaSH",
        "mw": MW['NaSH'],                                    # 56.06
        "na2o_factor": MW['Na2O'] / (2 * MW['NaSH']),        # 0.5529 — Na mass balance
        "na2o_per_unit": MW['Na2O'] / MW['NaSH'],            # 1.1060 — Na2S sulfidity tracking
        "s_factor": MW['S'] / MW['NaSH'],                    # 0.5719 — S mass per unit NaSH
        "na_factor": MW['Na'] / MW['NaSH'],                  # 0.4100 — Na mass per unit NaSH
        "adds_na": True,
        "adds_s": True,
    },
    "saltcake": {
        "name": "Saltcake (Na2SO4)",
        "formula": "Na2SO4",
        "mw": MW['Na2SO4'],                                  # 142.04
        "na2o_factor": MW['Na2O'] / MW['Na2SO4'],            # 0.4366
        "na2o_per_unit": MW['Na2O'] / MW['Na2SO4'],          # 0.4366 (2 Na atoms, matches Na2O)
        "s_factor": MW['S'] / MW['Na2SO4'],                  # 0.2257
        "na_factor": 2 * MW['Na'] / MW['Na2SO4'],            # 0.3236
        "adds_na": True,
        "adds_s": True,
    },
    "emulsified_sulfur": {
        "name": "Emulsified Sulfur",
        "formula": "S",
        "mw": MW['S'],                                       # 32.065
        "na2o_factor": 0.0,
        "na2o_per_unit": 0.0,
        "s_factor": 1.0,                                     # Pure sulfur
        "na_factor": 0.0,
        "adds_na": False,
        "adds_s": True,
    },
    "naoh": {
        "name": "NaOH (Caustic Soda)",
        "formula": "NaOH",
        "mw": MW['NaOH'],                                    # 40.0
        "na2o_factor": MW['Na2O'] / (2 * MW['NaOH']),        # 0.775
        "na2o_per_unit": MW['Na2O'] / (2 * MW['NaOH']),      # 0.775
        "s_factor": 0.0,
        "na_factor": MW['Na'] / MW['NaOH'],                  # 0.5745
        "adds_na": True,
        "adds_s": False,
    },
}


def get_makeup_config(chemical_id: str) -> dict:
    """Get makeup chemical configuration by ID.

    Args:
        chemical_id: One of "nash", "saltcake", "emulsified_sulfur", "naoh".

    Returns:
        Dict with keys: name, formula, mw, na2o_factor, na2o_per_unit,
        s_factor, na_factor, adds_na, adds_s.

    Raises:
        KeyError: If chemical_id is not a valid makeup chemical.
    """
    return MAKEUP_CHEMICALS[chemical_id]
