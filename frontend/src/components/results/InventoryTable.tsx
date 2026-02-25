"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import type { InventoryOutput } from "@/lib/types";

interface Props {
  inventory: InventoryOutput;
}

export default function InventoryTable({ inventory }: Props) {
  const rows = [
    { group: "White Liquor", tta: inventory.wl_tta_tons, na2s: inventory.wl_na2s_tons },
    { group: "Green Liquor", tta: inventory.gl_tta_tons, na2s: inventory.gl_na2s_tons },
    { group: "BL Latent", tta: inventory.bl_latent_tta_tons, na2s: inventory.bl_latent_na2s_tons },
  ];

  const totalTTA = rows.reduce((s, r) => s + r.tta, 0);
  const totalNa2S = rows.reduce((s, r) => s + r.na2s, 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Tank Inventory</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Group</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">TTA (tons)</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Na₂S (tons)</th>
              <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Sulfidity (%)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.group} className="border-b border-white/[0.04]">
                <td className="py-2.5 font-mono text-xs text-muted-foreground">{r.group}</td>
                <td className="py-2.5 text-right font-mono text-sm tabular-nums text-white">{fmtNum(r.tta, 2)}</td>
                <td className="py-2.5 text-right font-mono text-sm tabular-nums text-white">{fmtNum(r.na2s, 2)}</td>
                <td className="py-2.5 text-right font-mono text-sm tabular-nums text-white">
                  {r.tta > 0 ? fmtNum((r.na2s / r.tta) * 100, 2) : "--"}%
                </td>
              </tr>
            ))}
            <tr className="border-t border-white/[0.08]">
              <td className="py-2.5 font-mono text-xs font-semibold text-white">Total</td>
              <td className="py-2.5 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{fmtNum(totalTTA, 2)}</td>
              <td className="py-2.5 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{fmtNum(totalNa2S, 2)}</td>
              <td className="py-2.5 text-right font-mono text-sm font-semibold tabular-nums text-cyan">
                {totalTTA > 0 ? fmtNum((totalNa2S / totalTTA) * 100, 2) : "--"}%
              </td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
