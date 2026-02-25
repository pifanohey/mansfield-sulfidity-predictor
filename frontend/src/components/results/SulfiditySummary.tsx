"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtPct, trendLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SulfidityOutput } from "@/lib/types";

interface Props {
  sulfidity: SulfidityOutput;
  target: number;
}

export default function SulfiditySummary({ sulfidity, target }: Props) {
  const rows = [
    { label: "Current (WL)", value: sulfidity.current_pct, color: "bg-blue-400" },
    { label: "Latent (BL)", value: sulfidity.latent_pct, color: "bg-purple-400" },
    { label: "Final (after makeup)", value: sulfidity.final_pct, color: "bg-cyan" },
    { label: "Smelt (RB)", value: sulfidity.smelt_pct, color: "bg-amber-400" },
    { label: "Target", value: target, color: "bg-white/20" },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle>Sulfidity Summary</CardTitle>
          <span
            className={cn(
              "rounded-md px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider",
              sulfidity.trend === "FALLING"
                ? "bg-amber-500/10 text-amber-400"
                : sulfidity.trend === "RISING"
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-cyan/10 text-cyan"
            )}
          >
            {trendLabel(sulfidity.trend)}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                Metric
              </th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                Value
              </th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                vs Target
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const delta = r.value - target;
              return (
                <tr key={r.label} className="border-b border-white/[0.04] last:border-0">
                  <td className="py-3">
                    <div className="flex items-center gap-2">
                      <div className={cn("h-2 w-2 rounded-full", r.color)} />
                      <span className="font-mono text-xs text-muted-foreground">{r.label}</span>
                    </div>
                  </td>
                  <td className="py-3 text-right font-mono text-sm font-medium text-white">
                    {fmtPct(r.value)}
                  </td>
                  <td
                    className={cn(
                      "py-3 text-right font-mono text-xs",
                      r.label === "Target"
                        ? "text-white/20"
                        : Math.abs(delta) < 0.1
                        ? "text-emerald-400"
                        : delta > 0.5
                        ? "text-amber-400"
                        : delta < -0.5
                        ? "text-red-400"
                        : "text-cyan"
                    )}
                  >
                    {r.label === "Target" ? "--" : `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
