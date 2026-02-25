"use client";

import { useState } from "react";
import { Activity } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { fmtNum, fmtDelta } from "@/lib/format";
import type { CalculationRequest, SensitivityItem } from "@/lib/types";
import { sensitivity as fetchSensitivity } from "@/lib/api";

interface Props {
  inputs: CalculationRequest;
}

export default function SensitivityTable({ inputs }: Props) {
  const [items, setItems] = useState<SensitivityItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchSensitivity(inputs);
      setItems(res.items);
    } catch (e) {
      console.error("Sensitivity analysis failed:", e);
      setError("Sensitivity analysis failed. Check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const OUTPUT_KEYS = [
    "final_sulfidity_pct",
    "nash_dry_lbs_hr",
    "naoh_dry_lbs_hr",
    "smelt_sulfidity_pct",
    "bl_s_pct_used",
    "bl_na_pct_used",
  ];
  const OUTPUT_LABELS: Record<string, string> = {
    final_sulfidity_pct: "Final Sulf %",
    nash_dry_lbs_hr: "NaSH lb/hr",
    naoh_dry_lbs_hr: "NaOH lb/hr",
    smelt_sulfidity_pct: "Smelt Sulf %",
    bl_s_pct_used: "BL S%",
    bl_na_pct_used: "BL Na%",
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle>Sensitivity Analysis</CardTitle>
          <Button size="sm" onClick={run} disabled={loading}>
            <Activity className="mr-1.5 h-3.5 w-3.5" />
            {loading ? "Running..." : "Run Analysis"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error ? (
          <p className="py-4 text-center font-mono text-xs text-red-400">{error}</p>
        ) : items.length === 0 ? (
          <p className="py-4 text-center font-mono text-xs text-muted-foreground">
            Click &quot;Run Analysis&quot; to compute sensitivity at the current operating point.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Perturbation</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">From</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">To</th>
                  {OUTPUT_KEYS.map((k) => (
                    <th key={k} className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
                      {OUTPUT_LABELS[k]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.parameter + item.perturbed_value} className="border-b border-white/[0.04] last:border-0">
                    <td className="py-2 font-mono text-xs text-muted-foreground">{item.description}</td>
                    <td className="py-2 text-right font-mono text-xs tabular-nums text-white/60">{fmtNum(item.base_value, 2)}</td>
                    <td className="py-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(item.perturbed_value, 2)}</td>
                    {OUTPUT_KEYS.map((k) => {
                      const delta = item.outputs[k]?.delta;
                      return (
                        <td key={k} className="py-2 text-right font-mono text-xs tabular-nums text-white">
                          {delta != null ? fmtDelta(delta, 2) : "--"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
