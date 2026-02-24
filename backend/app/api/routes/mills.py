"""Mill configuration endpoints."""

from fastapi import APIRouter
from ..schemas import MillConfigResponse, CalculationRequest
from ...engine.constants import DEFAULTS
from ...engine.mill_config import TANKS, TANK_GROUPS

router = APIRouter(prefix="/api/mills", tags=["mills"])


@router.get("/{mill_id}/config", response_model=MillConfigResponse)
def get_mill_config(mill_id: str = "pine_hill"):
    return MillConfigResponse(
        mill_id=mill_id,
        mill_name="Pine Hill Mill",
        tanks={
            name: {
                'display_name': cfg['name'],
                'capacity_gal': cfg['constant'],
                'max_level_ft': cfg['max_level'],
                'gal_per_ft': cfg['gal_per_ft'],
                'group': cfg['group'],
            }
            for name, cfg in TANKS.items()
        },
        defaults=DEFAULTS,
    )


@router.get("/{mill_id}/defaults", response_model=CalculationRequest)
def get_mill_defaults(mill_id: str = "pine_hill"):
    return CalculationRequest()
