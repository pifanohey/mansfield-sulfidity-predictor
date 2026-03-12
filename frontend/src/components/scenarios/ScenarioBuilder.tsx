"use client";

import { useState, useMemo } from "react";
import { Play } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { fmtNum } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CalculationRequest, CalculationResponse, MillConfig } from "@/lib/types";
import { whatIf } from "@/lib/api";

interface ScenarioParam {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
}

/** Build scenario params dynamically from mill config fiberlines. */
function buildParams(millConfig: MillConfig | null): ScenarioParam[] {
  const params: ScenarioParam[] = [
    { key: "reduction_eff_pct", label: "Reduction Efficiency", unit: "%", min: 75, max: 99, step: 0.5 },
    { key: "target_sulfidity_pct", label: "Target Sulfidity", unit: "%", min: 20, max: 35, step: 0.1 },
    { key: "causticity_pct", label: "Causticity", unit: "%", min: 70, max: 90, step: 0.5 },
  ];

  // Add per-fiberline production sliders
  const fiberlines = millConfig?.fiberlines ?? [];
  for (const fl of fiberlines) {
    params.push({
      key: `fl_${fl.id}_production`,
      label: `${fl.name} Production`,
      unit: "BDT/day",
      min: Math.round((fl.defaults.production_bdt_day ?? 500) * 0.5),
      max: Math.round((fl.defaults.production_bdt_day ?? 1500) * 1.3),
      step: 10,
    });
  }

  params.push(
    { key: "cto_tpd", label: "CTO Production", unit: "TPD", min: 0, max: 150, step: 1 },
    { key: "loss_pulp_washable_soda_na", label: "Washable Soda Na Loss", unit: "lb Na₂O/BDT", min: 0, max: 30, step: 0.5 },
  );

  return params;
}

function getBaseValue(inputs: CalculationRequest, param: ScenarioParam): number {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const obj = inputs as any;

  if (param.key.startsWith("loss_") && param.key !== "loss_table") {
    const match = param.key.match(/^loss_(.+)_(s|na)$/);
    if (match && obj.loss_table) {
      const [, source, type] = match;
      const field = type === "s" ? "s_lb_bdt" : "na_lb_bdt";
      return obj.loss_table[source]?.[field] ?? 0;
    }
  }

  if (param.key === "reduction_eff_pct") {
    return obj.recovery_boiler?.reduction_eff_pct ?? 95.0;
  }

  // Dynamic fiberline production: fl_<id>_production
  const flMatch = param.key.match(/^fl_(.+)_production$/);
  if (flMatch) {
    const flId = flMatch[1];
    return inputs.fiberlines?.find((fl) => fl.id === flId)?.production_bdt_day ?? 0;
  }

  return obj[param.key] ?? 0;
}

/** Build what-if overrides, translating fiberline production keys to a fiberlines array. */
function buildOverrides(
  inputs: CalculationRequest,
  overrides: Record<string, number>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  let needsFiberlineOverride = false;
  const flProductionOverrides: Record<string, number> = {};

  for (const [key, value] of Object.entries(overrides)) {
    const flMatch = key.match(/^fl_(.+)_production$/);
    if (flMatch) {
      needsFiberlineOverride = true;
      flProductionOverrides[flMatch[1]] = value;
    } else {
      result[key] = value;
    }
  }

  if (needsFiberlineOverride && inputs.fiberlines) {
    const fiberlines = inputs.fiberlines.map((fl) => {
      if (flProductionOverrides[fl.id] !== undefined) {
        return { ...fl, production_bdt_day: flProductionOverrides[fl.id] };
      }
      return fl;
    });
    result["fiberlines"] = fiberlines;
  }

  return result;
}

interface Props {
  inputs: CalculationRequest;
  baseResults: CalculationResponse | null;
  millConfig: MillConfig | null;
}

export default function ScenarioBuilder({ inputs, baseResults, millConfig }: Props) {
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [scenarioResults, setScenarioResults] = useState<CalculationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const params = useMemo(() => buildParams(millConfig), [millConfig]);

  const handleSliderChange = (param: ScenarioParam, value: number) => {
    setOverrides((prev) => ({ ...prev, [param.key]: value }));
  };

  const runScenario = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await whatIf(inputs, buildOverrides(inputs, overrides));
      setScenarioResults(res.scenario_results);
    } catch (e) {
      console.error("What-if scenario failed:", e);
      setError("Scenario calculation failed. Check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle>What-If Parameters</CardTitle>
            <Button size="sm" onClick={runScenario} disabled={loading}>
              <Play className="mr-1.5 h-3.5 w-3.5" />
              {loading ? "Running..." : "Run Scenario"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {params.map((param) => {
            const base = getBaseValue(inputs, param);
            const current = overrides[param.key] ?? base;
            const changed = current !== base;
            return (
              <div key={param.key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
                    {param.label}
                  </span>
                  <span className="font-mono text-sm tabular-nums text-white">
                    {fmtNum(current, 1)}
                    <span className="ml-1 text-[10px] text-muted-foreground">{param.unit}</span>
                    {changed && (
                      <span className="ml-2 text-[10px] text-white/30">
                        base: {fmtNum(base, 1)}
                      </span>
                    )}
                  </span>
                </div>
                <Slider
                  value={[current]}
                  onValueChange={([v]) => handleSliderChange(param, v)}
                  min={param.min}
                  max={param.max}
                  step={param.step}
                />
              </div>
            );
          })}
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="py-4">
            <p className="text-center font-mono text-xs text-red-400">{error}</p>
          </CardContent>
        </Card>
      )}

      {baseResults && scenarioResults && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Metric</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Base</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Scenario</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Delta</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { label: "Final Sulfidity", b: baseResults.sulfidity.final_pct, s: scenarioResults.sulfidity.final_pct, unit: "%" },
                  { label: "Smelt Sulfidity", b: baseResults.sulfidity.smelt_pct, s: scenarioResults.sulfidity.smelt_pct, unit: "%" },
                  { label: "NaSH (dry)", b: baseResults.makeup.nash_dry_lb_hr, s: scenarioResults.makeup.nash_dry_lb_hr, unit: "lb/hr" },
                  { label: "NaOH (dry)", b: baseResults.makeup.naoh_dry_lb_hr, s: scenarioResults.makeup.naoh_dry_lb_hr, unit: "lb/hr" },
                  { label: "Dead Load", b: baseResults.recovery_boiler.dead_load_lb_hr, s: scenarioResults.recovery_boiler.dead_load_lb_hr, unit: "lb/hr" },
                  { label: "Na Deficit", b: baseResults.mass_balance.na_deficit_lb_hr, s: scenarioResults.mass_balance.na_deficit_lb_hr, unit: "lb/hr" },
                ].map((row) => {
                  const delta = row.s - row.b;
                  return (
                    <tr key={row.label} className="border-b border-white/[0.04] last:border-0">
                      <td className="py-2.5 font-mono text-xs text-muted-foreground">{row.label}</td>
                      <td className="py-2.5 text-right font-mono text-sm tabular-nums text-white/60">{fmtNum(row.b)}</td>
                      <td className="py-2.5 text-right font-mono text-sm tabular-nums text-white">{fmtNum(row.s)}</td>
                      <td className={cn(
                        "py-2.5 text-right font-mono text-xs tabular-nums",
                        delta > 0 ? "text-amber-400" : delta < 0 ? "text-cyan" : "text-white/30"
                      )}>
                        {delta >= 0 ? "+" : ""}{fmtNum(delta)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
