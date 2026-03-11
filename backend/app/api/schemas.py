"""Pydantic request/response models for the API."""

from pydantic import BaseModel, Field
from typing import Dict, Optional, List, Any
from datetime import datetime


class TankLevels(BaseModel):
    wlc_1: float = 10.2
    wlc_2: float = 13.0
    gl_1: float = 11.1
    gl_2: float = 10.8
    dump_tank: float = 30.3
    wbl_1: float = 34.4
    wbl_2: float = 32.8
    cssc_weak: float = 36.4
    tank_50pct: float = 18.4
    tank_55pct_1: float = 18.0
    tank_55pct_2: float = 1.0
    tank_65pct: float = 39.4


class LiquorAnalysis(BaseModel):
    tta: float
    ea: float
    aa: float


class BLTankProperties(BaseModel):
    tds: Dict[str, float] = Field(default_factory=dict)
    temp: Dict[str, float] = Field(default_factory=dict)


class RecoveryBoilerInputs(BaseModel):
    bl_flow_gpm: float = 340.53
    bl_tds_pct: float = 69.1
    bl_temp_f: float = 253.5
    reduction_eff_pct: float = 95.0
    ash_recycled_pct: float = 0.07
    saltcake_flow_lb_hr: float = 2227.0


class RecoveryBoilerConfigInput(BaseModel):
    """Per-RB inputs from the frontend."""
    id: str
    bl_flow_gpm: Optional[float] = None
    bl_tds_pct: Optional[float] = None
    bl_temp_f: Optional[float] = None
    reduction_eff_pct: Optional[float] = None
    ash_recycled_pct: Optional[float] = None
    saltcake_flow_lb_hr: Optional[float] = None


class DissolvingTankInput(BaseModel):
    """Per-DT inputs from the frontend."""
    id: str
    ww_flow_gpm: Optional[float] = None
    ww_tta_lb_ft3: Optional[float] = None
    ww_sulfidity: Optional[float] = None
    shower_flow_gpm: Optional[float] = None
    smelt_density_lb_ft3: Optional[float] = None


class LossTableSource(BaseModel):
    """A single loss source with S and Na2O values (lb/BDT)."""
    s_lb_bdt: float = 0.0
    na_lb_bdt: float = 0.0


class LossTable(BaseModel):
    """Unified soda & sulfur loss table — 13 sources with mill defaults."""
    pulp_washable_soda: LossTableSource = LossTableSource(s_lb_bdt=3.0, na_lb_bdt=18.5)
    pulp_bound_soda: LossTableSource = LossTableSource(s_lb_bdt=0.0, na_lb_bdt=7.4)
    pulp_mill_spills: LossTableSource = LossTableSource(s_lb_bdt=0.0, na_lb_bdt=0.3)
    evap_spill: LossTableSource = LossTableSource(s_lb_bdt=2.4, na_lb_bdt=5.2)
    rb_ash: LossTableSource = LossTableSource(s_lb_bdt=1.3, na_lb_bdt=2.8)
    rb_stack: LossTableSource = LossTableSource(s_lb_bdt=0.3, na_lb_bdt=0.8)
    dregs_filter: LossTableSource = LossTableSource(s_lb_bdt=0.4, na_lb_bdt=2.4)
    grits: LossTableSource = LossTableSource(s_lb_bdt=0.2, na_lb_bdt=1.5)
    weak_wash_overflow: LossTableSource = LossTableSource(s_lb_bdt=0.1, na_lb_bdt=0.7)
    ncg: LossTableSource = LossTableSource(s_lb_bdt=8.5, na_lb_bdt=1.0)
    recaust_spill: LossTableSource = LossTableSource(s_lb_bdt=0.4, na_lb_bdt=2.2)
    rb_dump_tank: LossTableSource = LossTableSource(s_lb_bdt=0.0, na_lb_bdt=0.0)
    kiln_scrubber: LossTableSource = LossTableSource(s_lb_bdt=0.0, na_lb_bdt=0.0)
    truck_out_gl: LossTableSource = LossTableSource(s_lb_bdt=0.0, na_lb_bdt=0.0)
    unaccounted: LossTableSource = LossTableSource(s_lb_bdt=0.0, na_lb_bdt=0.0)


class FiberlineInput(BaseModel):
    """Per-fiberline inputs from the frontend."""
    id: str
    production_bdt_day: float
    yield_pct: float
    ea_pct: float
    gl_ea_pct: Optional[float] = None


class CalculationRequest(BaseModel):
    """Complete calculation request matching all Excel inputs."""
    # Dynamic fiberline inputs (required)
    fiberlines: List[FiberlineInput]

    # Tank levels
    tank_levels: Optional[TankLevels] = None

    # Lab analysis
    wl_analysis: Optional[LiquorAnalysis] = None
    gl_analysis: Optional[LiquorAnalysis] = None

    # BL properties
    bl_na_pct: float = 19.50
    bl_s_pct: float = 3.93
    bl_k_pct: float = 1.58
    bl_tank_properties: Optional[BLTankProperties] = None

    # Recovery boiler (legacy single-RB)
    recovery_boiler: Optional[RecoveryBoilerInputs] = None

    # Multi-RB / Multi-DT (V2 — overrides single-RB when present)
    recovery_boilers: Optional[List[RecoveryBoilerConfigInput]] = None
    dissolving_tanks: Optional[List[DissolvingTankInput]] = None

    # Cooking
    cooking_wl_sulfidity: float = 0.283

    # Dissolving tank inputs (Excel 2_RB I43-I75)
    ww_flow_gpm: float = 625.0
    ww_tta_lb_ft3: float = 1.07978
    ww_sulfidity: float = 0.2550
    shower_flow_gpm: float = 60.0
    smelt_density_lb_ft3: float = 110.0
    gl_target_tta_lb_ft3: float = 7.4
    gl_causticity: float = 0.1016

    # Slaker / causticizer
    causticity_pct: float = 81.0
    lime_charge_ratio: float = 0.85
    cao_in_lime_pct: float = 87.53
    caco3_in_lime_pct: float = 1.96
    inerts_in_lime_pct: float = 9.46
    grits_loss_pct: float = 1.0
    lime_temp_f: float = 1100.0
    slaker_temp_f: float = 210.5

    # WLC (White Liquor Clarifier)
    intrusion_water_gpm: float = 28.0
    dilution_water_gpm: float = 23.856
    wlc_underflow_solids_pct: float = 0.4097
    wlc_mud_density: float = 1.33

    # GL clarifier dregs (3_Chem B62-B70) + slaker grits (B71-B80)
    dregs_lb_bdt: float = 8.158
    glc_underflow_solids_pct: float = 0.077
    grits_lb_bdt: float = 8.53
    grits_solids_pct: float = 0.40

    # CTO
    cto_h2so4_per_ton: float = 398.0
    cto_tpd: float = 60.0
    cto_naoh_per_ton: float = 0.0  # lb NaOH/ton CTO (Na returns via brine)

    # Setpoints
    target_sulfidity_pct: float = 29.4

    # Makeup chemical properties
    nash_concentration: float = 0.40
    naoh_concentration: float = 0.50
    nash_density: float = 1.29
    naoh_density: float = 1.52

    # Unified loss table (replaces s_losses + loss_factor + rb_losses_na2o_bdt)
    loss_table: Optional[LossTable] = None

    # Optional overrides
    s_deficit_lbs_hr: Optional[float] = None
    nash_dry_override_lb_hr: Optional[float] = None
    naoh_dry_override_lb_hr: Optional[float] = None

    def to_engine_inputs(self) -> Dict[str, Any]:
        """Convert API request to engine input dict."""
        d: Dict[str, Any] = {}

        # Dynamic fiberline inputs → FiberlineConfig objects for the engine
        from ..engine.mill_profile import FiberlineConfig, get_mill_config
        mill = get_mill_config()
        configs = []
        for fl_input in self.fiberlines:
            mill_fl = next((mfl for mfl in mill.fiberlines if mfl.id == fl_input.id), None)
            if mill_fl:
                defaults = dict(mill_fl.defaults)
                defaults["production_bdt_day"] = fl_input.production_bdt_day
                defaults["yield_pct"] = fl_input.yield_pct
                defaults["ea_pct"] = fl_input.ea_pct
                if fl_input.gl_ea_pct is not None:
                    defaults["gl_ea_pct"] = fl_input.gl_ea_pct
                configs.append(FiberlineConfig(
                    id=mill_fl.id, name=mill_fl.name, type=mill_fl.type,
                    cooking_type=mill_fl.cooking_type,
                    uses_gl_charge=mill_fl.uses_gl_charge,
                    defaults=defaults,
                ))
        d['fiberlines'] = configs

        # Tank levels
        if self.tank_levels:
            d['tank_levels'] = self.tank_levels.model_dump()
        # WL/GL analysis
        if self.wl_analysis:
            d['wl_tta'] = self.wl_analysis.tta
            d['wl_ea'] = self.wl_analysis.ea
            d['wl_aa'] = self.wl_analysis.aa
        if self.gl_analysis:
            d['gl_tta'] = self.gl_analysis.tta
            d['gl_ea'] = self.gl_analysis.ea
            d['gl_aa'] = self.gl_analysis.aa

        # BL properties
        d['bl_na_pct'] = self.bl_na_pct
        d['bl_s_pct'] = self.bl_s_pct
        d['bl_k_pct'] = self.bl_k_pct
        if self.bl_tank_properties:
            d['bl_tank_tds'] = self.bl_tank_properties.tds
            d['bl_tank_temp'] = self.bl_tank_properties.temp

        # RB — only set flat keys when NOT using multi-RB config,
        # otherwise the flat values trigger per-RB override logic in the orchestrator
        if self.recovery_boiler and not self.recovery_boilers:
            rb = self.recovery_boiler
            d['bl_flow_gpm'] = rb.bl_flow_gpm
            d['bl_tds_pct'] = rb.bl_tds_pct
            d['bl_temp_f'] = rb.bl_temp_f
            d['reduction_eff_pct'] = rb.reduction_eff_pct
            d['ash_recycled_pct'] = rb.ash_recycled_pct
            d['saltcake_flow_lb_hr'] = rb.saltcake_flow_lb_hr

        # Cooking
        d['cooking_wl_sulfidity'] = self.cooking_wl_sulfidity

        # Dissolving tank
        d['ww_flow_gpm'] = self.ww_flow_gpm
        d['ww_tta_lb_ft3'] = self.ww_tta_lb_ft3
        d['ww_sulfidity'] = self.ww_sulfidity
        d['shower_flow_gpm'] = self.shower_flow_gpm
        d['smelt_density_lb_ft3'] = self.smelt_density_lb_ft3
        d['gl_target_tta_lb_ft3'] = self.gl_target_tta_lb_ft3
        d['gl_causticity'] = self.gl_causticity

        # Slaker / causticizer
        d['causticity_pct'] = self.causticity_pct
        d['lime_charge_ratio'] = self.lime_charge_ratio
        d['cao_in_lime_pct'] = self.cao_in_lime_pct
        d['caco3_in_lime_pct'] = self.caco3_in_lime_pct
        d['inerts_in_lime_pct'] = self.inerts_in_lime_pct
        d['grits_loss_pct'] = self.grits_loss_pct
        d['lime_temp_f'] = self.lime_temp_f
        d['slaker_temp_f'] = self.slaker_temp_f

        # WLC
        d['intrusion_water_gpm'] = self.intrusion_water_gpm
        d['dilution_water_gpm'] = self.dilution_water_gpm
        d['wlc_underflow_solids_pct'] = self.wlc_underflow_solids_pct
        d['wlc_mud_density'] = self.wlc_mud_density

        # GL clarifier
        d['dregs_lb_bdt'] = self.dregs_lb_bdt
        d['glc_underflow_solids_pct'] = self.glc_underflow_solids_pct
        d['grits_lb_bdt'] = self.grits_lb_bdt
        d['grits_solids_pct'] = self.grits_solids_pct

        # CTO
        d['cto_h2so4_per_ton'] = self.cto_h2so4_per_ton
        d['cto_tpd'] = self.cto_tpd
        d['cto_naoh_per_ton'] = self.cto_naoh_per_ton

        # Setpoints
        d['target_sulfidity_pct'] = self.target_sulfidity_pct

        # Makeup
        d['nash_concentration'] = self.nash_concentration
        d['naoh_concentration'] = self.naoh_concentration
        d['nash_density'] = self.nash_density
        d['naoh_density'] = self.naoh_density

        # Loss table → flat engine keys: loss_{source}_{s|na}
        if self.loss_table:
            lt = self.loss_table
            _LOSS_TABLE_KEYS = [
                'pulp_washable_soda', 'pulp_bound_soda', 'pulp_mill_spills',
                'evap_spill', 'rb_ash', 'rb_stack',
                'dregs_filter', 'grits', 'weak_wash_overflow',
                'ncg', 'recaust_spill', 'rb_dump_tank', 'kiln_scrubber',
                'truck_out_gl', 'unaccounted',
            ]
            for source_key in _LOSS_TABLE_KEYS:
                src: LossTableSource = getattr(lt, source_key)
                d[f'loss_{source_key}_s'] = src.s_lb_bdt
                d[f'loss_{source_key}_na'] = src.na_lb_bdt

        # Multi-RB config: merge user overrides with mill config defaults
        if self.recovery_boilers:
            from ..engine.mill_profile import RecoveryBoilerConfig
            rb_configs = []
            for rb_input in self.recovery_boilers:
                mill_rb = next((mrb for mrb in mill.recovery_boilers if mrb.id == rb_input.id), None)
                base_defaults = dict(mill_rb.defaults) if mill_rb else {}
                # Apply user overrides
                for fld in ['bl_flow_gpm', 'bl_tds_pct', 'bl_temp_f',
                            'reduction_eff_pct', 'ash_recycled_pct', 'saltcake_flow_lb_hr']:
                    val = getattr(rb_input, fld, None)
                    if val is not None:
                        base_defaults[fld] = val
                rb_configs.append(RecoveryBoilerConfig(
                    id=rb_input.id,
                    name=mill_rb.name if mill_rb else rb_input.id,
                    paired_dt_id=mill_rb.paired_dt_id if mill_rb else '',
                    defaults=base_defaults,
                ))
            d['recovery_boilers'] = rb_configs

        # Multi-DT config
        if self.dissolving_tanks:
            from ..engine.mill_profile import DissolvingTankConfig
            dt_configs = []
            for dt_input in self.dissolving_tanks:
                mill_dt = next((mdt for mdt in mill.dissolving_tanks if mdt.id == dt_input.id), None)
                base_defaults = dict(mill_dt.defaults) if mill_dt else {}
                for fld in ['ww_flow_gpm', 'ww_tta_lb_ft3', 'ww_sulfidity',
                            'shower_flow_gpm', 'smelt_density_lb_ft3']:
                    val = getattr(dt_input, fld, None)
                    if val is not None:
                        base_defaults[fld] = val
                dt_configs.append(DissolvingTankConfig(
                    id=dt_input.id,
                    name=mill_dt.name if mill_dt else dt_input.id,
                    paired_rb_id=mill_dt.paired_rb_id if mill_dt else '',
                    defaults=base_defaults,
                ))
            d['dissolving_tanks'] = dt_configs

        # Overrides
        if self.s_deficit_lbs_hr is not None:
            d['s_deficit_lbs_hr'] = self.s_deficit_lbs_hr
        if self.nash_dry_override_lb_hr is not None:
            d['nash_dry_override_lb_hr'] = self.nash_dry_override_lb_hr
        if self.naoh_dry_override_lb_hr is not None:
            d['naoh_dry_override_lb_hr'] = self.naoh_dry_override_lb_hr

        return d


class SulfidityOutput(BaseModel):
    current_pct: float
    latent_pct: float
    final_pct: float
    smelt_pct: float
    trend: str


class MakeupOutput(BaseModel):
    nash_dry_lb_hr: float
    nash_solution_lb_hr: float
    nash_gpm: float
    naoh_dry_lb_hr: float
    naoh_solution_lb_hr: float
    naoh_gpm: float
    nash_lb_bdt_na2o: float
    naoh_lb_bdt_na2o: float
    saltcake_lb_bdt_na2o: float


class RecoveryBoilerOutput(BaseModel):
    tta_lb_hr: float
    active_sulfide_lb_hr: float
    dead_load_lb_hr: float
    na_lbs_hr: float
    s_lbs_hr: float
    bl_density_lb_gal: float
    potential_na_alkali: float = 0.0
    potential_k_alkali: float = 0.0
    potential_s_alkali: float = 0.0
    dry_solids_lbs_hr: float = 0.0
    bl_na_pct_mixed: float = 0.0
    bl_s_pct_mixed: float = 0.0
    bl_s_pct_fired: float = 0.0


class InventoryOutput(BaseModel):
    wl_tta_tons: float
    wl_na2s_tons: float
    gl_tta_tons: float
    gl_na2s_tons: float
    bl_latent_tta_tons: float
    bl_latent_na2s_tons: float


class MassBalanceOutput(BaseModel):
    na_losses_lb_hr: float
    na_deficit_lb_hr: float
    total_s_losses_lb_hr: float = 0.0
    cto_s_lbs_hr: float = 0.0
    net_s_balance_lb_hr: float = 0.0


class UnitOperationRow(BaseModel):
    stage: str
    na_lb_hr: float = 0.0
    s_lb_hr: float = 0.0
    na_pct_ds: Optional[float] = None
    s_pct_ds: Optional[float] = None
    tta_na2o_ton_hr: Optional[float] = None
    na2s_na2o_ton_hr: Optional[float] = None
    flow_gpm: Optional[float] = None


class LossDetailRow(BaseModel):
    """Output row for unified soda & sulfur losses."""
    source: str
    s_lb_hr: float
    s_lb_bdt: float
    na2o_lb_hr: float
    na2o_lb_bdt: float


class ChemicalAdditionRow(BaseModel):
    source: str
    na_lb_hr: float
    s_lb_hr: float


class GuidanceItemOutput(BaseModel):
    severity: str
    category: str
    title: str
    description: str
    action: str
    impact: str = ''


class WLQualityOutput(BaseModel):
    """White liquor quality parameters."""
    # Final WL (after WLC + makeup) in g Na2O/L
    tta_g_L: float = 0.0
    aa_g_L: float = 0.0
    ea_g_L: float = 0.0
    na2s_g_L: float = 0.0
    # Final WL in lb/ft3
    tta_lb_ft3: float = 0.0
    aa_lb_ft3: float = 0.0
    ea_lb_ft3: float = 0.0
    na2s_lb_ft3: float = 0.0
    # Sulfidity
    sulfidity_pct: float = 0.0
    # Causticity
    causticity_pct: float = 0.0
    # Flows
    wl_flow_gpm: float = 0.0
    wl_demand_gpm: float = 0.0


class FiberlineBLResult(BaseModel):
    """Per-fiberline BL output in the forward leg."""
    id: str
    name: str
    organics_lb_hr: float = 0.0
    inorganic_solids_lb_hr: float = 0.0


class ForwardLegOutput(BaseModel):
    """Forward leg BL composition from fiberlines to recovery boiler."""
    # Dynamic per-fiberline results
    fiberline_bl: List[FiberlineBLResult] = Field(default_factory=list)
    # CTO
    cto_na_lb_hr: float = 0.0
    cto_s_lbs_hr: float = 0.0
    # Mixed WBL
    wbl_total_flow_lb_hr: float = 0.0
    wbl_tds_pct: float = 0.0
    wbl_na_pct_ds: float = 0.0
    wbl_s_pct_ds: float = 0.0
    # SBL (after evaporator)
    sbl_flow_lb_hr: float = 0.0
    sbl_tds_pct: float = 0.0
    sbl_na_element_lb_hr: float = 0.0
    sbl_s_element_lb_hr: float = 0.0
    evaporator_water_removed_lb_hr: float = 0.0
    # RB inputs
    rb_virgin_solids_lbs_hr: float = 0.0
    rb_ash_solids_lbs_hr: float = 0.0
    bl_na_pct_used: float = 0.0
    bl_s_pct_used: float = 0.0


class CalculationResponse(BaseModel):
    """Complete calculation response."""
    status: str = 'success'
    solver: Dict[str, Any] = Field(default_factory=dict)
    sulfidity: SulfidityOutput
    makeup: MakeupOutput
    recovery_boiler: RecoveryBoilerOutput
    inventory: InventoryOutput
    mass_balance: MassBalanceOutput
    wl_quality: WLQualityOutput = Field(default_factory=WLQualityOutput)
    forward_leg: ForwardLegOutput = Field(default_factory=ForwardLegOutput)
    guidance: List[GuidanceItemOutput] = Field(default_factory=list)
    production: Dict[str, float] = Field(default_factory=dict)
    intermediate: Dict[str, Any] = Field(default_factory=dict)
    unit_operations: List[UnitOperationRow] = Field(default_factory=list)
    loss_table_detail: List[LossDetailRow] = Field(default_factory=list)
    chemical_additions: List[ChemicalAdditionRow] = Field(default_factory=list)
    na_losses_element_lb_hr: float = 0.0
    saltcake_na_lb_hr: float = 0.0
    saltcake_s_lb_hr: float = 0.0
    # BL composition tracking
    bl_na_pct_lab: float = 0.0
    bl_s_pct_lab: float = 0.0
    bl_na_pct_computed: float = 0.0
    bl_s_pct_computed: float = 0.0
    bl_na_pct_used: float = 0.0
    bl_s_pct_used: float = 0.0
    total_production_bdt_day: float = 0.0
    outer_loop_converged: bool = True
    outer_loop_iterations: int = 1
    # DT energy balance + WW solve
    dt_steam_evaporated_lb_hr: float = 0.0
    dt_steam_evaporated_gpm: float = 0.0
    dt_heat_from_smelt_btu_hr: float = 0.0
    dt_heat_to_warm_liquor_btu_hr: float = 0.0
    dt_net_heat_for_steam_btu_hr: float = 0.0
    ww_flow_solved_gpm: float = 0.0
    dregs_filtrate_gpm: float = 0.0


class WhatIfRequest(BaseModel):
    base: CalculationRequest
    overrides: Dict[str, Any]


class WhatIfResponse(BaseModel):
    base_results: CalculationResponse
    scenario_results: CalculationResponse
    deltas: Dict[str, float]


class SensitivityItem(BaseModel):
    parameter: str
    description: str
    base_value: float
    perturbed_value: float
    outputs: Dict[str, Dict[str, float]]


class SensitivityResponse(BaseModel):
    items: List[SensitivityItem]


class SnapshotCreate(BaseModel):
    inputs: CalculationRequest
    results: Optional[Dict[str, Any]] = None
    notes: str = ''


class SnapshotResponse(BaseModel):
    id: int
    timestamp: datetime
    notes: str
    inputs: Dict[str, Any]
    results: Dict[str, Any]


class ExportRequest(BaseModel):
    """Bundle inputs + results for report export (avoids re-running solver)."""
    inputs: CalculationRequest
    results: CalculationResponse
    sensitivity_items: Optional[List[SensitivityItem]] = None
    mill_name: str = "Mill"  # Will be set from config


class MillConfigResponse(BaseModel):
    mill_id: str
    mill_name: str
    makeup_chemical: str = "nash"
    fiberlines: List[Dict[str, Any]] = Field(default_factory=list)
    recovery_boilers: List[Dict[str, Any]] = Field(default_factory=list)
    dissolving_tanks: List[Dict[str, Any]] = Field(default_factory=list)
    tanks: Dict[str, Any] = Field(default_factory=dict)
    defaults: Dict[str, Any] = Field(default_factory=dict)


class TrendPointCreate(BaseModel):
    predicted_sulfidity_pct: float
    smelt_sulfidity_pct: float
    nash_dry_lb_hr: float
    naoh_dry_lb_hr: float
    target_sulfidity_pct: float


class TrendPointUpdate(BaseModel):
    lab_sulfidity_pct: Optional[float] = None
    notes: Optional[str] = None


class TrendPointResponse(BaseModel):
    id: int
    mill_id: str
    timestamp: datetime
    predicted_sulfidity_pct: float
    smelt_sulfidity_pct: float
    nash_dry_lb_hr: float
    naoh_dry_lb_hr: float
    target_sulfidity_pct: float
    lab_sulfidity_pct: Optional[float] = None
    notes: str
