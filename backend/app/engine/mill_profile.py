"""Mill configuration loading from JSON config files."""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FiberlineConfig:
    """Configuration for a single fiberline."""
    id: str
    name: str
    type: str                     # "continuous" | "batch"
    cooking_type: str             # "chemical" | "semichem"
    uses_gl_charge: bool
    defaults: Dict[str, Any]

    @property
    def production_bdt_day(self) -> float:
        return self.defaults.get("production_bdt_day", 0.0)

    @property
    def yield_pct(self) -> float:
        return self.defaults.get("yield_pct", 0.5)

    @property
    def ea_pct(self) -> float:
        return self.defaults.get("ea_pct", 0.1)

    @property
    def gl_ea_pct(self) -> float:
        return self.defaults.get("gl_ea_pct", 0.0)

    @property
    def wood_moisture(self) -> float:
        return self.defaults.get("wood_moisture", 0.50)


@dataclass
class RecoveryBoilerConfig:
    """Configuration for a single recovery boiler."""
    id: str
    name: str
    paired_dt_id: str
    defaults: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DissolvingTankConfig:
    """Configuration for a single dissolving tank."""
    id: str
    name: str
    paired_rb_id: str
    defaults: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MillConfig:
    """Complete mill configuration."""
    mill_name: str
    makeup_chemical: str
    fiberlines: List[FiberlineConfig]
    tanks: List[Dict[str, Any]]
    defaults: Dict[str, Any] = field(default_factory=dict)
    recovery_boilers: List[RecoveryBoilerConfig] = field(default_factory=list)
    dissolving_tanks: List[DissolvingTankConfig] = field(default_factory=list)
    liquor_unit: str = "lb_per_ft3"  # "lb_per_ft3" or "lb_per_gal"


def _find_config_dir() -> Path:
    """Walk up from this file to find the mill_configs/ directory."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        candidate = parent / "mill_configs"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Cannot find mill_configs/ directory")


def load_mill_config(mill_id: str) -> MillConfig:
    """Load a mill configuration from its JSON file.

    Args:
        mill_id: The mill identifier (e.g., "pine_hill"). Corresponds to
                 the filename mill_configs/{mill_id}.json.

    Returns:
        A MillConfig dataclass with the parsed configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    config_dir = _find_config_dir()
    config_path = config_dir / f"{mill_id}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Mill config not found: {config_path}")
    with open(config_path) as f:
        data = json.load(f)
    fiberlines = [
        FiberlineConfig(
            id=fl["id"],
            name=fl["name"],
            type=fl["type"],
            cooking_type=fl["cooking_type"],
            uses_gl_charge=fl["uses_gl_charge"],
            defaults=fl.get("defaults", {}),
        )
        for fl in data["fiberlines"]
    ]
    recovery_boilers = [
        RecoveryBoilerConfig(
            id=rb["id"],
            name=rb["name"],
            paired_dt_id=rb["paired_dt_id"],
            defaults=rb.get("defaults", {}),
        )
        for rb in data.get("recovery_boilers", [])
    ]
    dissolving_tanks = [
        DissolvingTankConfig(
            id=dt["id"],
            name=dt["name"],
            paired_rb_id=dt["paired_rb_id"],
            defaults=dt.get("defaults", {}),
        )
        for dt in data.get("dissolving_tanks", [])
    ]
    return MillConfig(
        mill_name=data["mill_name"],
        makeup_chemical=data["makeup_chemical"],
        fiberlines=fiberlines,
        tanks=data.get("tanks", []),
        defaults=data.get("defaults", {}),
        recovery_boilers=recovery_boilers,
        dissolving_tanks=dissolving_tanks,
        liquor_unit=data.get("liquor_unit", "lb_per_ft3"),
    )


def get_mill_config() -> MillConfig:
    """Load the mill config identified by the MILL_CONFIG env var.

    Defaults to "pine_hill" if the env var is not set.
    """
    mill_id = os.environ.get("MILL_CONFIG", "pine_hill")
    return load_mill_config(mill_id)
