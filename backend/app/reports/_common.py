"""Shared data extraction helpers for PDF and Excel report generators.

Converts ExportRequest fields into simple (label, value) row tuples
that both generators consume identically.
"""

from datetime import datetime
from typing import List, Tuple, Optional

from ..api.schemas import ExportRequest, SensitivityItem

Row = Tuple[str, str]


def fmt(v: float, decimals: int = 2) -> str:
    """Format a number with comma separators and fixed decimals."""
    return f"{v:,.{decimals}f}"


def fmt_pct(v: float, decimals: int = 2) -> str:
    """Format a percentage value."""
    return f"{v:.{decimals}f}%"


def get_key_inputs_rows(req: ExportRequest) -> List[Row]:
    """Cover page / summary key inputs."""
    inp = req.inputs
    rb = inp.recovery_boiler
    # Extract production from fiberlines array
    total_prod = sum(fl.production_bdt_day for fl in inp.fiberlines)
    pine_prod = next((fl.production_bdt_day for fl in inp.fiberlines if fl.id == "pine"), 0.0)
    semichem_prod = next((fl.production_bdt_day for fl in inp.fiberlines if fl.id == "semichem"), 0.0)
    return [
        ("Mill Name", req.mill_name),
        ("Report Date", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("", ""),
        ("Total Production", f"{fmt(total_prod)} BDT/day"),
        ("Pine Production", f"{fmt(pine_prod)} BDT/day"),
        ("Semichem Production", f"{fmt(semichem_prod)} BDT/day"),
        ("BL Flow", f"{fmt(rb.bl_flow_gpm) if rb else 'N/A'} gpm"),
        ("BL TDS", f"{fmt_pct(rb.bl_tds_pct) if rb else 'N/A'}"),
        ("Reduction Efficiency", f"{fmt_pct(rb.reduction_eff_pct) if rb else 'N/A'}"),
        ("Causticity", f"{fmt_pct(inp.causticity_pct)}"),
        ("Target Sulfidity", f"{fmt_pct(inp.target_sulfidity_pct)}"),
    ]


def get_sulfidity_rows(req: ExportRequest) -> List[Row]:
    s = req.results.sulfidity
    return [
        ("Current Sulfidity", fmt_pct(s.current_pct)),
        ("Latent Sulfidity", fmt_pct(s.latent_pct)),
        ("Final Sulfidity", fmt_pct(s.final_pct)),
        ("Smelt Sulfidity", fmt_pct(s.smelt_pct)),
        ("Trend", s.trend),
    ]


def get_wl_quality_rows(req: ExportRequest) -> List[Row]:
    wl = req.results.wl_quality
    return [
        ("TTA (g Na2O/L)", fmt(wl.tta_g_L)),
        ("AA (g Na2O/L)", fmt(wl.aa_g_L)),
        ("EA (g Na2O/L)", fmt(wl.ea_g_L)),
        ("Na2S (g Na2O/L)", fmt(wl.na2s_g_L)),
        ("TTA (lb/ft3)", fmt(wl.tta_lb_ft3, 3)),
        ("AA (lb/ft3)", fmt(wl.aa_lb_ft3, 3)),
        ("EA (lb/ft3)", fmt(wl.ea_lb_ft3, 3)),
        ("Na2S (lb/ft3)", fmt(wl.na2s_lb_ft3, 3)),
        ("Sulfidity", fmt_pct(wl.sulfidity_pct)),
        ("Causticity", fmt_pct(wl.causticity_pct)),
        ("WL Flow (produced)", f"{fmt(wl.wl_flow_gpm)} gpm"),
        ("WL Demand", f"{fmt(wl.wl_demand_gpm)} gpm"),
    ]


def get_makeup_rows(req: ExportRequest) -> List[Row]:
    m = req.results.makeup
    return [
        ("NaSH Dry", f"{fmt(m.nash_dry_lb_hr)} lb/hr"),
        ("NaSH Solution", f"{fmt(m.nash_solution_lb_hr)} lb/hr"),
        ("NaSH Flow", f"{fmt(m.nash_gpm)} gpm"),
        ("NaSH (as Na2O)", f"{fmt(m.nash_lb_bdt_na2o)} lb Na2O/BDT"),
        ("", ""),
        ("NaOH Dry", f"{fmt(m.naoh_dry_lb_hr)} lb/hr"),
        ("NaOH Solution", f"{fmt(m.naoh_solution_lb_hr)} lb/hr"),
        ("NaOH Flow", f"{fmt(m.naoh_gpm)} gpm"),
        ("NaOH (as Na2O)", f"{fmt(m.naoh_lb_bdt_na2o)} lb Na2O/BDT"),
        ("", ""),
        ("Saltcake (as Na2O)", f"{fmt(m.saltcake_lb_bdt_na2o)} lb Na2O/BDT"),
    ]


def get_recovery_boiler_rows(req: ExportRequest) -> List[Row]:
    rb = req.results.recovery_boiler
    r = req.results
    return [
        ("TTA", f"{fmt(rb.tta_lb_hr, 0)} lb/hr"),
        ("Active Sulfide", f"{fmt(rb.active_sulfide_lb_hr, 0)} lb/hr"),
        ("Dead Load", f"{fmt(rb.dead_load_lb_hr, 0)} lb/hr"),
        ("Na", f"{fmt(rb.na_lbs_hr, 0)} lb/hr"),
        ("S", f"{fmt(rb.s_lbs_hr, 0)} lb/hr"),
        ("BL Density", f"{fmt(rb.bl_density_lb_gal)} lb/gal"),
        ("Dry Solids", f"{fmt(rb.dry_solids_lbs_hr, 0)} lb/hr"),
        ("", ""),
        ("Potential Na Alkali", f"{fmt(rb.potential_na_alkali, 0)} lb Na2O/hr"),
        ("Potential K Alkali", f"{fmt(rb.potential_k_alkali, 0)} lb Na2O/hr"),
        ("Potential S Alkali", f"{fmt(rb.potential_s_alkali, 0)} lb Na2O/hr"),
        ("", ""),
        ("BL Na% (lab)", fmt_pct(r.bl_na_pct_lab)),
        ("BL S% (lab)", fmt_pct(r.bl_s_pct_lab)),
        ("BL Na% (computed)", fmt_pct(r.bl_na_pct_computed)),
        ("BL S% (computed)", fmt_pct(r.bl_s_pct_computed)),
        ("BL Na% (used)", fmt_pct(r.bl_na_pct_used)),
        ("BL S% (used)", fmt_pct(r.bl_s_pct_used)),
        ("BL Na% (mixed)", fmt_pct(rb.bl_na_pct_mixed)),
        ("BL S% (mixed)", fmt_pct(rb.bl_s_pct_mixed)),
    ]


def get_mass_balance_rows(req: ExportRequest) -> List[Row]:
    mb = req.results.mass_balance
    return [
        ("Na Losses", f"{fmt(mb.na_losses_lb_hr, 0)} lb Na2O/hr"),
        ("Na Deficit", f"{fmt(mb.na_deficit_lb_hr, 0)} lb Na2O/hr"),
        ("Total S Losses", f"{fmt(mb.total_s_losses_lb_hr, 0)} lb S/hr"),
        ("CTO S", f"{fmt(mb.cto_s_lbs_hr, 0)} lb S/hr"),
        ("Net S Balance", f"{fmt(mb.net_s_balance_lb_hr, 0)} lb S/hr"),
    ]


def get_inventory_rows(req: ExportRequest) -> List[Row]:
    inv = req.results.inventory
    return [
        ("WL TTA", f"{fmt(inv.wl_tta_tons)} tons Na2O"),
        ("WL Na2S", f"{fmt(inv.wl_na2s_tons)} tons Na2O"),
        ("GL TTA", f"{fmt(inv.gl_tta_tons)} tons Na2O"),
        ("GL Na2S", f"{fmt(inv.gl_na2s_tons)} tons Na2O"),
        ("BL Latent TTA", f"{fmt(inv.bl_latent_tta_tons)} tons Na2O"),
        ("BL Latent Na2S", f"{fmt(inv.bl_latent_na2s_tons)} tons Na2O"),
    ]


def get_unit_operations_headers() -> List[str]:
    return ["Stage", "Na (lb/hr)", "S (lb/hr)", "Na% DS", "S% DS",
            "TTA (ton Na2O/hr)", "Na2S (ton Na2O/hr)", "Flow (gpm)"]


def get_unit_operations_rows(req: ExportRequest) -> List[List[str]]:
    rows = []
    for op in req.results.unit_operations:
        rows.append([
            op.stage,
            fmt(op.na_lb_hr, 0),
            fmt(op.s_lb_hr, 0),
            fmt_pct(op.na_pct_ds) if op.na_pct_ds is not None else "-",
            fmt_pct(op.s_pct_ds) if op.s_pct_ds is not None else "-",
            fmt(op.tta_na2o_ton_hr, 2) if op.tta_na2o_ton_hr is not None else "-",
            fmt(op.na2s_na2o_ton_hr, 2) if op.na2s_na2o_ton_hr is not None else "-",
            fmt(op.flow_gpm, 0) if op.flow_gpm is not None else "-",
        ])
    return rows


def get_loss_table_headers() -> List[str]:
    return ["Source", "S (lb/hr)", "S (lb/BDT)", "Na2O (lb/hr)", "Na2O (lb/BDT)"]


def get_loss_table_rows(req: ExportRequest) -> List[List[str]]:
    rows = []
    for loss in req.results.loss_table_detail:
        rows.append([
            loss.source,
            fmt(loss.s_lb_hr),
            fmt(loss.s_lb_bdt),
            fmt(loss.na2o_lb_hr),
            fmt(loss.na2o_lb_bdt),
        ])
    return rows


def get_chemical_additions_headers() -> List[str]:
    return ["Source", "Na (lb/hr)", "S (lb/hr)"]


def get_chemical_additions_rows(req: ExportRequest) -> List[List[str]]:
    rows = []
    for ca in req.results.chemical_additions:
        rows.append([
            ca.source,
            fmt(ca.na_lb_hr, 0),
            fmt(ca.s_lb_hr, 0),
        ])
    return rows


def get_sensitivity_headers() -> List[str]:
    return ["Parameter", "Description", "Base Value", "Perturbed Value",
            "Final Sulfidity Base", "Final Sulfidity Perturbed", "Delta"]


def get_sensitivity_rows(items: Optional[List[SensitivityItem]]) -> List[List[str]]:
    if not items:
        return []
    rows = []
    for item in items:
        sulf_out = item.outputs.get("sulfidity", {})
        base_sulf = sulf_out.get("base", 0)
        pert_sulf = sulf_out.get("perturbed", 0)
        delta = pert_sulf - base_sulf
        rows.append([
            item.parameter,
            item.description,
            fmt(item.base_value, 3),
            fmt(item.perturbed_value, 3),
            fmt_pct(base_sulf),
            fmt_pct(pert_sulf),
            f"{delta:+.3f}%",
        ])
    return rows


def get_guidance_headers() -> List[str]:
    return ["Severity", "Category", "Title", "Description", "Action", "Impact"]


def get_guidance_rows(req: ExportRequest) -> List[List[str]]:
    rows = []
    for g in req.results.guidance:
        rows.append([
            g.severity,
            g.category,
            g.title,
            g.description,
            g.action,
            g.impact,
        ])
    return rows
