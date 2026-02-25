"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fmtNum, fmtPct } from "@/lib/format";
import type { RecoveryBoilerOutput } from "@/lib/types";
import { CheckCircle, ArrowRight, Droplets } from "lucide-react";

interface Props {
  rb: RecoveryBoilerOutput;
  smeltSulfidity: number;
  blNaPctLab?: number;
  blSPctLab?: number;
  blNaPctComputed?: number;
  blSPctComputed?: number;
  blNaPctUsed?: number;
  blSPctUsed?: number;
  solverIterations?: number;
  dtSteamLbHr?: number;
  dtSteamGpm?: number;
  dtHeatFromSmelt?: number;
  dtHeatToWarm?: number;
  dtNetHeat?: number;
  wwFlowSolved?: number;
  wwFlowInput?: number;
  dregsFiltrateGpm?: number;
  outerLoopIterations?: number;
}

export default function RecoveryBoilerResults({
  rb,
  smeltSulfidity,
  blNaPctLab,
  blSPctLab,
  blNaPctComputed,
  blSPctComputed,
  blNaPctUsed,
  blSPctUsed,
  solverIterations,
  dtSteamLbHr,
  dtSteamGpm,
  dtHeatFromSmelt,
  dtHeatToWarm,
  dtNetHeat,
  wwFlowSolved,
  wwFlowInput,
  dregsFiltrateGpm,
  outerLoopIterations,
}: Props) {
  const deadLoadPct = rb.tta_lb_hr > 0 ? (rb.dead_load_lb_hr / rb.tta_lb_hr) * 100 : 0;
  const showBLComparison = blNaPctLab !== undefined && blNaPctComputed !== undefined;
  const outerLoopDisabled = (outerLoopIterations ?? 1) === 1 &&
    blNaPctLab !== undefined && blNaPctUsed !== undefined &&
    Math.abs((blNaPctLab ?? 0) - (blNaPctUsed ?? 0)) < 0.001;

  return (
    <div className="space-y-4">
      {showBLComparison && (
        <Card className="border-emerald-500/20 bg-emerald-500/[0.04]">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              BL Composition Convergence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="font-mono text-[10px] text-muted-foreground mb-3">
              {outerLoopDisabled
                ? "Lab values used directly (outer loop disabled)."
                : "Forward leg computes BL composition (WL \u2192 Digesters \u2192 Evaporator \u2192 SBL). Lab values are initial guesses."}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Parameter</th>
                    <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Lab Input</th>
                    <th className="pb-2.5 text-center w-8"></th>
                    <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Computed</th>
                    <th className="pb-2.5 text-center w-8"></th>
                    <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Used in RB</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-white/[0.04]">
                    <td className="py-2.5 font-mono text-xs text-muted-foreground">BL Na %</td>
                    <td className="py-2.5 text-right">
                      <Badge variant="outline" className="font-mono text-xs">{fmtNum(blNaPctLab, 2)}%</Badge>
                    </td>
                    <td className="py-2.5 text-center">
                      <ArrowRight className="h-3 w-3 text-white/20 mx-auto" />
                    </td>
                    <td className="py-2.5 text-right">
                      <Badge variant="secondary" className="font-mono text-xs">{fmtNum(blNaPctComputed, 2)}%</Badge>
                    </td>
                    <td className="py-2.5 text-center">
                      <ArrowRight className="h-3 w-3 text-white/20 mx-auto" />
                    </td>
                    <td className="py-2.5 text-right">
                      <Badge className="font-mono text-xs bg-emerald-600">{fmtNum(blNaPctUsed, 2)}%</Badge>
                    </td>
                  </tr>
                  <tr>
                    <td className="py-2.5 font-mono text-xs text-muted-foreground">BL S %</td>
                    <td className="py-2.5 text-right">
                      <Badge variant="outline" className="font-mono text-xs">{fmtNum(blSPctLab, 2)}%</Badge>
                    </td>
                    <td className="py-2.5 text-center">
                      <ArrowRight className="h-3 w-3 text-white/20 mx-auto" />
                    </td>
                    <td className="py-2.5 text-right">
                      <Badge variant="secondary" className="font-mono text-xs">{fmtNum(blSPctComputed, 2)}%</Badge>
                    </td>
                    <td className="py-2.5 text-center">
                      <ArrowRight className="h-3 w-3 text-white/20 mx-auto" />
                    </td>
                    <td className="py-2.5 text-right">
                      <Badge className="font-mono text-xs bg-emerald-600">{fmtNum(blSPctUsed, 2)}%</Badge>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            {outerLoopIterations !== undefined && (
              <div className="mt-3 font-mono text-[10px] text-muted-foreground">
                {outerLoopDisabled
                  ? "Outer loop: disabled (1 iteration, lab values used)"
                  : <>Outer loop converged in <span className="font-medium text-white">{outerLoopIterations}</span> iterations</>}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Recovery Boiler Results</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                BL Fired Composition
              </h4>
              <table className="w-full">
                <tbody>
                  {[
                    { label: "Dry Solids", value: fmtNum(rb.dry_solids_lbs_hr, 0), unit: "lb/hr" },
                    { label: "Na% d.s. (V+A)", value: `${fmtNum(rb.bl_na_pct_mixed, 2)}%`, bold: true },
                    { label: "S% d.s. (V+A)", value: `${fmtNum(rb.bl_s_pct_mixed, 2)}%`, bold: true },
                    { label: "S% fired (V+A+Salt)", value: `${fmtNum(rb.bl_s_pct_fired, 2)}%` },
                    { label: "BL Density", value: fmtNum(rb.bl_density_lb_gal, 3), unit: "lb/gal" },
                  ].map((r) => (
                    <tr key={r.label} className="border-b border-white/[0.04] last:border-0">
                      <td className="py-2 font-mono text-xs text-muted-foreground">{r.label}</td>
                      <td className={`py-2 text-right font-mono text-sm tabular-nums ${r.bold ? "font-medium text-white" : "text-white"}`}>{r.value}</td>
                      {r.unit && <td className="w-12 py-2 text-right font-mono text-[10px] text-muted-foreground">{r.unit}</td>}
                      {!r.unit && <td className="w-12 py-2" />}
                    </tr>
                  ))}
                </tbody>
              </table>
              <h4 className="mt-4 mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                Alkali Balance
              </h4>
              <table className="w-full">
                <tbody>
                  {[
                    { label: "Potential Na Alkali", value: rb.potential_na_alkali },
                    { label: "Potential K Alkali", value: rb.potential_k_alkali },
                    { label: "Potential S Alkali", value: rb.potential_s_alkali },
                  ].map((r) => (
                    <tr key={r.label} className="border-b border-white/[0.04] last:border-0">
                      <td className="py-2 font-mono text-xs text-muted-foreground">{r.label}</td>
                      <td className="py-2 text-right font-mono text-sm tabular-nums text-white">{fmtNum(r.value)}</td>
                      <td className="w-12 py-2 text-right font-mono text-[10px] text-muted-foreground">lb/hr</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div>
              <h4 className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                Smelt Composition
              </h4>
              <table className="w-full">
                <tbody>
                  {[
                    { label: "TTA", value: fmtNum(rb.tta_lb_hr), unit: "lb/hr" },
                    { label: "Active Sulfide", value: fmtNum(rb.active_sulfide_lb_hr), unit: "lb/hr" },
                    { label: "Dead Load", value: `${fmtNum(rb.dead_load_lb_hr)} (${fmtPct(deadLoadPct)} of TTA)`, unit: "lb/hr" },
                    { label: "Smelt Sulfidity", value: fmtPct(smeltSulfidity), bold: true },
                  ].map((r) => (
                    <tr key={r.label} className="border-b border-white/[0.04] last:border-0">
                      <td className="py-2 font-mono text-xs text-muted-foreground">{r.label}</td>
                      <td className={`py-2 text-right font-mono text-sm tabular-nums ${r.bold ? "font-medium text-cyan" : "text-white"}`}>{r.value}</td>
                      {r.unit && <td className="w-12 py-2 text-right font-mono text-[10px] text-muted-foreground">{r.unit}</td>}
                      {!r.unit && <td className="w-12 py-2" />}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </CardContent>
      </Card>

      {(dtSteamLbHr !== undefined && dtSteamLbHr > 0) && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <Droplets className="h-4 w-4 text-cyan" />
              Dissolving Tank Energy Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h4 className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                  Flow Balance
                </h4>
                <table className="w-full">
                  <tbody>
                    {[
                      { label: "WW Flow (solved)", value: fmtNum(wwFlowSolved), unit: "gpm", bold: true },
                      { label: "WW Flow (input)", value: fmtNum(wwFlowInput), unit: "gpm" },
                      { label: "Dregs Filtrate Return", value: fmtNum(dregsFiltrateGpm), unit: "gpm" },
                      { label: "Steam Evaporated", value: `${fmtNum(dtSteamLbHr, 0)} lb/hr (${fmtNum(dtSteamGpm)} gpm)` },
                    ].map((r) => (
                      <tr key={r.label} className="border-b border-white/[0.04] last:border-0">
                        <td className="py-2 font-mono text-xs text-muted-foreground">{r.label}</td>
                        <td className={`py-2 text-right font-mono text-sm tabular-nums ${r.bold ? "font-medium text-white" : "text-white"}`}>{r.value}</td>
                        {r.unit && <td className="w-12 py-2 text-right font-mono text-[10px] text-muted-foreground">{r.unit}</td>}
                        {!r.unit && <td className="w-12 py-2" />}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div>
                <h4 className="mb-2 font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                  Heat Balance
                </h4>
                <table className="w-full">
                  <tbody>
                    {[
                      { label: "Heat from Smelt", value: fmtNum((dtHeatFromSmelt ?? 0) / 1e6, 2), unit: "MM BTU/hr" },
                      { label: "Heat to Warm Liquor", value: fmtNum((dtHeatToWarm ?? 0) / 1e6, 2), unit: "MM BTU/hr" },
                      { label: "Net Heat for Steam", value: fmtNum((dtNetHeat ?? 0) / 1e6, 2), unit: "MM BTU/hr", bold: true },
                    ].map((r) => (
                      <tr key={r.label} className="border-b border-white/[0.04] last:border-0">
                        <td className="py-2 font-mono text-xs text-muted-foreground">{r.label}</td>
                        <td className={`py-2 text-right font-mono text-sm tabular-nums ${r.bold ? "font-medium text-white" : "text-white"}`}>{r.value}</td>
                        <td className="w-20 py-2 text-right font-mono text-[10px] text-muted-foreground">{r.unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
