import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import type { RecoveryBoilerOutput } from "@/lib/types";

interface Props {
  rb: RecoveryBoilerOutput;
}

export default function RecoveryBoilerSummary({ rb }: Props) {
  const rows = [
    { label: "TTA", value: rb.tta_lb_hr, unit: "lb/hr" },
    { label: "Active Sulfide", value: rb.active_sulfide_lb_hr, unit: "lb/hr" },
    { label: "Dead Load", value: rb.dead_load_lb_hr, unit: "lb/hr" },
    { label: "BL Density", value: rb.bl_density_lb_gal, unit: "lb/gal", dec: 3 },
    { label: "Na Input", value: rb.na_lbs_hr, unit: "lb/hr" },
    { label: "S Input", value: rb.s_lbs_hr, unit: "lb/hr" },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle>Recovery Boiler</CardTitle>
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
                  {fmtNum(r.value, r.dec ?? 1)}
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
