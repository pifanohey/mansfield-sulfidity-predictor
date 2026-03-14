"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum, fmtPct } from "@/lib/format";
import type { WLQualityOutput } from "@/lib/types";
import { useAppState } from "@/hooks/useAppState";
import { getLiquorUnitLabel, gLToDisplay, type LiquorUnit } from "@/lib/units";

interface Props {
  wlQuality: WLQualityOutput;
}

export default function WLQualityTable({ wlQuality }: Props) {
  const { millConfig } = useAppState();
  const unit = (millConfig?.liquor_unit ?? "lb_per_ft3") as LiquorUnit;
  const label = getLiquorUnitLabel(unit);

  const compositionRows = [
    { label: "TTA", gL: wlQuality.tta_g_L, display: gLToDisplay(wlQuality.tta_g_L, unit) },
    { label: "AA", gL: wlQuality.aa_g_L, display: gLToDisplay(wlQuality.aa_g_L, unit) },
    { label: "EA", gL: wlQuality.ea_g_L, display: gLToDisplay(wlQuality.ea_g_L, unit) },
    { label: "Na\u2082S", gL: wlQuality.na2s_g_L, display: gLToDisplay(wlQuality.na2s_g_L, unit) },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>White Liquor Composition</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                  Parameter
                </th>
                <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                  {label}
                </th>
                <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-white/20">
                  g Na₂O/L
                </th>
              </tr>
            </thead>
            <tbody>
              {compositionRows.map((row) => (
                <tr key={row.label} className="border-b border-white/[0.04] last:border-0">
                  <td className="py-2.5 font-mono text-xs text-muted-foreground">{row.label}</td>
                  <td className="py-2.5 text-right font-mono text-sm font-medium text-cyan">
                    {fmtNum(row.display, 4)}
                  </td>
                  <td className="py-2.5 text-right font-mono text-xs text-white/25">
                    {fmtNum(row.gL, 2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>Liquor Properties</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                Sulfidity
              </p>
              <p className="mt-1 font-mono text-lg font-semibold text-white">
                {fmtPct(wlQuality.sulfidity_pct)}
              </p>
            </div>
            <div className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                Causticity
              </p>
              <p className="mt-1 font-mono text-lg font-semibold text-white">
                {fmtPct(wlQuality.causticity_pct)}
              </p>
            </div>
            <div className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                WL Flow (slaker)
              </p>
              <p className="mt-1 font-mono text-lg font-semibold text-cyan">
                {fmtNum(wlQuality.wl_flow_gpm, 1)}
                <span className="ml-1 text-xs text-muted-foreground">GPM</span>
              </p>
            </div>
            <div className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                WL Demand
              </p>
              <p className="mt-1 font-mono text-lg font-semibold text-cyan">
                {fmtNum(wlQuality.wl_demand_gpm, 1)}
                <span className="ml-1 text-xs text-muted-foreground">GPM</span>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
