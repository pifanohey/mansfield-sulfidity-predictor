"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import type { MakeupOutput } from "@/lib/types";

interface Props {
  makeup: MakeupOutput;
  totalProductionBdtDay?: number;
  saltcakeLbHr?: number;
}

export default function MakeupTable({ makeup, totalProductionBdtDay = 1887.5, saltcakeLbHr = 2227 }: Props) {
  const nashLbBdt = totalProductionBdtDay > 0
    ? (makeup.nash_dry_lb_hr * 24) / totalProductionBdtDay
    : 0;
  const naohLbBdt = totalProductionBdtDay > 0
    ? (makeup.naoh_dry_lb_hr * 24) / totalProductionBdtDay
    : 0;
  const saltcakeLbBdt = totalProductionBdtDay > 0
    ? (saltcakeLbHr * 24) / totalProductionBdtDay
    : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Makeup Requirements</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Chemical</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Dry (lb/hr)</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Solution (lb/hr)</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Flow (gpm)</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">lb/BDT</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">lb Na₂O/BDT</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-white/[0.04]">
              <td className="py-2.5 font-mono text-xs font-medium text-white">NaSH</td>
              <td className="py-2.5 text-right font-mono text-sm text-cyan">{fmtNum(makeup.nash_dry_lb_hr)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-white">{fmtNum(makeup.nash_solution_lb_hr)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-white">{fmtNum(makeup.nash_gpm, 2)}</td>
              <td className="py-2.5 text-right font-mono text-xs font-medium text-white">{fmtNum(nashLbBdt, 2)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-muted-foreground">{fmtNum(makeup.nash_lb_bdt_na2o, 2)}</td>
            </tr>
            <tr className="border-b border-white/[0.04]">
              <td className="py-2.5 font-mono text-xs font-medium text-white">NaOH</td>
              <td className="py-2.5 text-right font-mono text-sm text-cyan">{fmtNum(makeup.naoh_dry_lb_hr)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-white">{fmtNum(makeup.naoh_solution_lb_hr)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-white">{fmtNum(makeup.naoh_gpm, 2)}</td>
              <td className="py-2.5 text-right font-mono text-xs font-medium text-white">{fmtNum(naohLbBdt, 2)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-muted-foreground">{fmtNum(makeup.naoh_lb_bdt_na2o, 2)}</td>
            </tr>
            <tr>
              <td className="py-2.5 font-mono text-xs font-medium text-white">Saltcake</td>
              <td className="py-2.5 text-right font-mono text-sm text-cyan">{fmtNum(saltcakeLbHr)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-white/20">--</td>
              <td className="py-2.5 text-right font-mono text-xs text-white/20">--</td>
              <td className="py-2.5 text-right font-mono text-xs font-medium text-white">{fmtNum(saltcakeLbBdt, 2)}</td>
              <td className="py-2.5 text-right font-mono text-xs text-muted-foreground">{fmtNum(makeup.saltcake_lb_bdt_na2o, 2)}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-4 font-mono text-[10px] text-muted-foreground">
          lb/BDT = (lb/hr x 24) / {fmtNum(totalProductionBdtDay, 1)} BDT/day. Saltcake is Na₂SO₄ recycled to RB.
        </p>
      </CardContent>
    </Card>
  );
}
