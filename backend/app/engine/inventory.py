"""
Tank inventory and liquor composition calculations.

Reference: 1_INVENTORY sheet in Excel v4
"""

from dataclasses import dataclass
from typing import List, Optional

from .constants import CONV, GAL_GL_TO_METRIC_TON
from .mill_config import tank_volume_gallons
from .density import calculate_bl_density


@dataclass
class LiquorComposition:
    """Liquor composition from lab analysis (all in g Na2O/L)."""
    tta: float
    ea: float
    aa: float

    @property
    def sulfidity_tta_pct(self) -> float:
        """Sulfidity on TTA basis (%). Excel: 2*(AA-EA)/TTA * 100"""
        if self.tta == 0:
            return 0.0
        return (2 * (self.aa - self.ea)) / self.tta * 100

    @property
    def na2s_g_L(self) -> float:
        """Na2S concentration (g Na2O/L). Excel: sulfidity_fraction * TTA"""
        return (self.sulfidity_tta_pct / 100) * self.tta

    @property
    def naoh_g_L(self) -> float:
        """NaOH concentration (g Na2O/L) = 2*EA - AA."""
        return 2 * self.ea - self.aa

    @property
    def na2co3_g_L(self) -> float:
        """Na2CO3 (dead load) concentration (g Na2O/L) = TTA - AA."""
        return self.tta - self.aa


@dataclass
class TankInventory:
    """Tank inventory with mass calculations."""
    tank_name: str
    level_ft: float
    volume_gal: float
    liquor: LiquorComposition

    @property
    def tta_tons(self) -> float:
        """TTA mass in metric tons Na2O. Excel: volume * TTA * 0.000003785"""
        return self.volume_gal * self.liquor.tta * GAL_GL_TO_METRIC_TON

    @property
    def na2s_tons(self) -> float:
        """Na2S mass in metric tons Na2O."""
        return self.volume_gal * self.liquor.na2s_g_L * GAL_GL_TO_METRIC_TON


@dataclass
class LatentBLInventory:
    """Black liquor tank with latent sulfidity calculation."""
    tank_name: str
    level_ft: float
    volume_gal: float
    tds_pct: float
    temp_f: float
    density_lb_gal: float
    na_pct: float
    s_pct: float
    k_pct: float
    reduction_eff: float  # fraction
    s_retention: float    # fraction

    @property
    def _dry_solids_lbs(self) -> float:
        total_mass_lbs = self.volume_gal * self.density_lb_gal
        return total_mass_lbs * self.tds_pct / 100

    @property
    def latent_tta_tons(self) -> float:
        """Latent TTA if processed (metric tons Na2O).
        Excel: DS × (Na% × Na_to_Na2O + K% × K_to_Na2O)"""
        ds = self._dry_solids_lbs
        na_as_na2o = ds * self.na_pct / 100 * CONV['Na_to_Na2O']
        k_as_na2o = ds * self.k_pct / 100 * CONV['K_to_Na2O']
        return (na_as_na2o + k_as_na2o) / 2000

    @property
    def latent_na2s_tons(self) -> float:
        """Latent Na2S if processed (metric tons Na2O basis).
        Excel: DS × S% × RE × S_retention × S_to_Na2O"""
        ds = self._dry_solids_lbs
        s_lbs = ds * self.s_pct / 100
        na2s_as_na2o_lbs = s_lbs * CONV['S_to_Na2O'] * self.reduction_eff * self.s_retention
        return na2s_as_na2o_lbs / 2000


def calculate_liquor_composition(tta: float, ea: float, aa: float) -> LiquorComposition:
    return LiquorComposition(tta=tta, ea=ea, aa=aa)


def calculate_tank_inventory(
    tank_name: str, level_ft: float, liquor: LiquorComposition
) -> TankInventory:
    volume_gal = tank_volume_gallons(tank_name, level_ft)
    return TankInventory(
        tank_name=tank_name, level_ft=level_ft,
        volume_gal=volume_gal, liquor=liquor
    )


def calculate_bl_inventory(
    tank_name: str, level_ft: float, tds_pct: float, temp_f: float,
    na_pct: float, s_pct: float, k_pct: float,
    reduction_eff_pct: float, s_retention: float = 0.986
) -> LatentBLInventory:
    volume_gal = tank_volume_gallons(tank_name, level_ft)
    density_lb_gal = calculate_bl_density(tds_pct, temp_f)
    return LatentBLInventory(
        tank_name=tank_name, level_ft=level_ft, volume_gal=volume_gal,
        tds_pct=tds_pct, temp_f=temp_f, density_lb_gal=density_lb_gal,
        na_pct=na_pct, s_pct=s_pct, k_pct=k_pct,
        reduction_eff=reduction_eff_pct / 100, s_retention=s_retention
    )


@dataclass
class SulfidityMetrics:
    """Current and latent sulfidity metrics."""
    current_na2s_tons: float
    current_tta_tons: float
    current_sulfidity_pct: float
    latent_na2s_tons: float
    latent_tta_tons: float
    latent_sulfidity_pct: float
    sulfidity_trend: str


def calculate_sulfidity_metrics(
    wl_tanks: List[TankInventory],
    gl_tanks: List[TankInventory],
    bl_tanks: Optional[List[LatentBLInventory]] = None,
    makeup_na2s_tons_day: float = 0.0,
    makeup_tta_tons_day: float = 0.0,
    s_losses_na2o_tons_day: float = 0.0,
) -> SulfidityMetrics:
    """
    Calculate current and latent sulfidity.

    Current: (WL_Na2S + GL_Na2S) / (WL_TTA + GL_TTA)
    Latent: (tanks + NaSH_Na2S_daily - S_losses_daily) /
            (tanks + (NaSH_TTA + NaOH_TTA)_daily)

    No separate RB term — BL_latent already captures the RB contribution
    (BL inventory projected through recovery cycle).
    """
    current_na2s = sum(t.na2s_tons for t in wl_tanks + gl_tanks)
    current_tta = sum(t.tta_tons for t in wl_tanks + gl_tanks)
    current_sulfidity = (current_na2s / current_tta * 100) if current_tta > 0 else 0.0

    latent_na2s = current_na2s
    latent_tta = current_tta

    if bl_tanks:
        latent_na2s += sum(t.latent_na2s_tons for t in bl_tanks)
        latent_tta += sum(t.latent_tta_tons for t in bl_tanks)

    # Daily additions: NaSH adds Na2S; NaSH + NaOH add TTA
    latent_na2s += makeup_na2s_tons_day
    latent_tta += makeup_tta_tons_day

    # Daily S losses reduce Na2S (S leaves the cycle via evap, NCG, etc.)
    latent_na2s -= s_losses_na2o_tons_day

    latent_sulfidity = (latent_na2s / latent_tta * 100) if latent_tta > 0 else 0.0

    diff = latent_sulfidity - current_sulfidity
    if diff > 0.5:
        trend = 'rising'
    elif diff < -0.5:
        trend = 'falling'
    else:
        trend = 'stable'

    return SulfidityMetrics(
        current_na2s_tons=current_na2s,
        current_tta_tons=current_tta,
        current_sulfidity_pct=current_sulfidity,
        latent_na2s_tons=latent_na2s,
        latent_tta_tons=latent_tta,
        latent_sulfidity_pct=latent_sulfidity,
        sulfidity_trend=trend
    )
