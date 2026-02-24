"""
Tank volume correlations for Pine Hill mill.

Formula: Volume (gallons) = (Level_ft * Tank_Constant) / Max_Level_ft
"""

from typing import Dict, Any


TANKS: Dict[str, Dict[str, Any]] = {
    'wlc_1': {
        'name': '#1 White Liquor Clarifier',
        'constant': 239360,
        'max_level': 16,
        'gal_per_ft': 239360 / 16,
        'group': 'white_liquor',
    },
    'wlc_2': {
        'name': '#2 White Liquor Clarifier',
        'constant': 239360,
        'max_level': 16,
        'gal_per_ft': 239360 / 16,
        'group': 'white_liquor',
    },
    'gl_1': {
        'name': '#1 Green Liquor Tank',
        'constant': 284320,
        'max_level': 16,
        'gal_per_ft': 284320 / 16,
        'group': 'green_liquor',
    },
    'gl_2': {
        'name': '#2 Green Liquor Tank',
        'constant': 108672,
        'max_level': 16,
        'gal_per_ft': 108672 / 16,
        'group': 'green_liquor',
    },
    'dump_tank': {
        'name': 'Dump Tank',
        'constant': 357200,
        'max_level': 38,
        'gal_per_ft': 357200 / 38,
        'group': 'green_liquor',
    },
    'wbl_1': {
        'name': '#1 Weak Black Liquor Tank',
        'constant': 853056,
        'max_level': 48,
        'gal_per_ft': 853056 / 48,
        'group': 'weak_black_liquor',
    },
    'wbl_2': {
        'name': '#2 Weak Black Liquor Tank',
        'constant': 853056,
        'max_level': 48,
        'gal_per_ft': 853056 / 48,
        'group': 'weak_black_liquor',
    },
    'cssc_weak': {
        'name': 'CSSC Weak Tank',
        'constant': 705022,
        'max_level': 48,
        'gal_per_ft': 705022 / 48,
        'group': 'weak_black_liquor',
    },
    'tank_50pct': {
        'name': '50% Solids Tank',
        'constant': 282000,
        'max_level': 30,
        'gal_per_ft': 282000 / 30,
        'group': 'strong_black_liquor',
    },
    'tank_55pct_1': {
        'name': '#1 55% Solids Tank',
        'constant': 211507,
        'max_level': 40,
        'gal_per_ft': 211507 / 40,
        'group': 'strong_black_liquor',
    },
    'tank_55pct_2': {
        'name': '#2 55% Solids Tank',
        'constant': 211507,
        'max_level': 40,
        'gal_per_ft': 211507 / 40,
        'group': 'strong_black_liquor',
    },
    'tank_65pct': {
        'name': '65% Solids Tank',
        'constant': 285295,
        'max_level': 42,
        'gal_per_ft': 285295 / 42,
        'group': 'strong_black_liquor',
    },
}

TANK_GROUPS = {
    'white_liquor': ['wlc_1', 'wlc_2'],
    'green_liquor': ['gl_1', 'gl_2', 'dump_tank'],
    'weak_black_liquor': ['wbl_1', 'wbl_2', 'cssc_weak'],
    'strong_black_liquor': ['tank_50pct', 'tank_55pct_1', 'tank_55pct_2', 'tank_65pct'],
}


def tank_volume_gallons(tank_name: str, level_ft: float) -> float:
    """Calculate tank volume in gallons from level in feet."""
    if tank_name not in TANKS:
        raise KeyError(f"Unknown tank: {tank_name}")
    tank = TANKS[tank_name]
    if level_ft < 0:
        raise ValueError(f"Level cannot be negative: {level_ft}")
    if level_ft > tank['max_level']:
        raise ValueError(
            f"Level {level_ft} ft exceeds max {tank['max_level']} ft for {tank['name']}"
        )
    return (level_ft * tank['constant']) / tank['max_level']


def get_all_tank_volumes(levels: Dict[str, float]) -> Dict[str, float]:
    """Calculate volumes for all tanks given a dictionary of levels."""
    volumes = {}
    for tank_name, level_ft in levels.items():
        if tank_name in TANKS:
            volumes[tank_name] = tank_volume_gallons(tank_name, level_ft)
    return volumes
