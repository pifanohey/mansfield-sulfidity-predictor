"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { MassBalanceOutput } from "@/lib/types";

interface Props {
  balance: MassBalanceOutput;
}

export default function MassBalanceTable({ balance }: Props) {
  const rows = [
    { label: "Na Losses", value: balance.na_losses_lb_hr, unit: "lb Na₂O/hr" },
    { label: "Na Deficit", value: balance.na_deficit_lb_hr, unit: "lb Na₂O/hr" },
    { label: "Total S Losses", value: balance.total_s_losses_lb_hr, unit: "lb S/hr" },
    { label: "CTO S Recovery", value: balance.cto_s_lbs_hr, unit: "lb S/hr" },
    { label: "Net S Balance", value: balance.net_s_balance_lb_hr, unit: "lb S/hr", highlight: true },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Mass Balance</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full">
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.label}
                className="border-b border-white/[0.04] last:border-0"
              >
                <td className={cn(
                  "py-2.5 font-mono text-xs",
                  r.highlight ? "font-medium text-white" : "text-muted-foreground"
                )}>
                  {r.label}
                </td>
                <td className={cn(
                  "py-2.5 text-right font-mono text-sm",
                  r.highlight ? "font-semibold text-cyan" : "text-white"
                )}>
                  {fmtNum(r.value)}
                </td>
                <td className="w-24 py-2.5 text-right font-mono text-[10px] text-muted-foreground">
                  {r.unit}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
