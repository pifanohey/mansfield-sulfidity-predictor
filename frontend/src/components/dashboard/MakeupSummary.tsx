import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import type { MakeupOutput } from "@/lib/types";

interface MakeupSummaryProps {
  makeup: MakeupOutput;
}

export default function MakeupSummary({ makeup }: MakeupSummaryProps) {
  const rows = [
    { label: "NaSH (dry)", value: makeup.nash_dry_lb_hr, unit: "lb/hr" },
    { label: "NaSH (solution)", value: makeup.nash_gpm, unit: "gpm" },
    { label: "NaOH (dry)", value: makeup.naoh_dry_lb_hr, unit: "lb/hr" },
    { label: "NaOH (solution)", value: makeup.naoh_gpm, unit: "gpm" },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Makeup Requirements</CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full">
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.label}
                className="border-b border-white/[0.04] last:border-0"
              >
                <td className="py-2.5 font-mono text-xs text-muted-foreground">
                  {r.label}
                </td>
                <td className="py-2.5 text-right font-mono text-sm font-medium text-white">
                  {fmtNum(r.value)}
                </td>
                <td className="w-14 py-2.5 text-right font-mono text-[11px] text-muted-foreground">
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
