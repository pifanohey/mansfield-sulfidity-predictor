"use client";

import { useState, useMemo } from "react";
import { Zap, Save, TrendingUp, TrendingDown } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { fmtNum, fmtPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CalculationRequest, CalculationResponse, MillConfig } from "@/lib/types";
import { whatIf, saveTrend } from "@/lib/api";
import SulfidityTrend from "@/components/results/SulfidityTrend";

interface PredictorParam {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
}

/** Build predictor params dynamically from mill config fiberlines. */
function buildParams(millConfig: MillConfig | null): PredictorParam[] {
  const params: PredictorParam[] = [];

  // Per-RB reduction efficiency sliders (or single if 1 RB)
  const rbs = millConfig?.recovery_boilers ?? [];
  if (rbs.length > 1) {
    for (const rb of rbs) {
      params.push({
        key: `rb_${rb.id}_re`,
        label: `${rb.name} RE`,
        unit: "%",
        min: 75,
        max: 99,
        step: 0.5,
      });
    }
  } else {
    params.push({ key: "reduction_eff_pct", label: "Reduction Efficiency", unit: "%", min: 75, max: 99, step: 0.5 });
  }

  params.push({ key: "causticity_pct", label: "Causticity", unit: "%", min: 70, max: 90, step: 0.5 });

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
    { key: "saltcake_flow_lb_hr", label: "Saltcake Makeup", unit: "lb/hr", min: 0, max: 5000, step: 50 },
    { key: "nash_dry_override_lb_hr", label: "NaSH (dry)", unit: "lb/hr", min: 0, max: 3000, step: 10 },
    { key: "naoh_dry_override_lb_hr", label: "NaOH (dry)", unit: "lb/hr", min: 0, max: 5000, step: 10 },
  );

  return params;
}

function getBaseValue(
  inputs: CalculationRequest,
  baseResults: CalculationResponse | null,
  param: PredictorParam
): number {
  if (param.key === "reduction_eff_pct") {
    return inputs.recovery_boiler?.reduction_eff_pct ?? 95.0;
  }
  // Per-RB reduction efficiency: rb_<id>_re
  const rbMatch = param.key.match(/^rb_(.+)_re$/);
  if (rbMatch) {
    const rbId = rbMatch[1];
    return inputs.recovery_boilers?.find((rb) => rb.id === rbId)?.reduction_eff_pct ?? 95.0;
  }
  if (param.key === "saltcake_flow_lb_hr") {
    // Multi-RB: sum per-RB saltcake (Mansfield: 0+0=0)
    if (inputs.recovery_boilers?.length) {
      return inputs.recovery_boilers.reduce((sum, rb) => sum + (rb.saltcake_flow_lb_hr ?? 0), 0);
    }
    return inputs.recovery_boiler?.saltcake_flow_lb_hr ?? 2227.0;
  }
  if (param.key === "nash_dry_override_lb_hr" && baseResults) {
    return baseResults.makeup.nash_dry_lb_hr;
  }
  if (param.key === "naoh_dry_override_lb_hr" && baseResults) {
    return baseResults.makeup.naoh_dry_lb_hr;
  }
  // Dynamic fiberline production: fl_<id>_production
  const flMatch = param.key.match(/^fl_(.+)_production$/);
  if (flMatch) {
    const flId = flMatch[1];
    return inputs.fiberlines?.find((fl) => fl.id === flId)?.production_bdt_day ?? 0;
  }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (inputs as any)[param.key] ?? 0;
}

/** Build what-if overrides, translating fiberline production keys to a fiberlines array. */
function buildOverrides(
  inputs: CalculationRequest,
  overrides: Record<string, number>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  let needsFiberlineOverride = false;
  const flProductionOverrides: Record<string, number> = {};
  let needsRBOverride = false;
  const rbREOverrides: Record<string, number> = {};

  for (const [key, value] of Object.entries(overrides)) {
    const flMatch = key.match(/^fl_(.+)_production$/);
    const rbMatch = key.match(/^rb_(.+)_re$/);
    if (flMatch) {
      needsFiberlineOverride = true;
      flProductionOverrides[flMatch[1]] = value;
    } else if (rbMatch) {
      needsRBOverride = true;
      rbREOverrides[rbMatch[1]] = value;
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

  if (needsRBOverride && inputs.recovery_boilers) {
    const recovery_boilers = inputs.recovery_boilers.map((rb) => {
      if (rbREOverrides[rb.id] !== undefined) {
        return { ...rb, reduction_eff_pct: rbREOverrides[rb.id] };
      }
      return rb;
    });
    result["recovery_boilers"] = recovery_boilers;
  }

  return result;
}

interface TornadoRow {
  label: string;
  downside: number;
  upside: number;
  range: number;
  lowLabel: string;
  highLabel: string;
}

interface Props {
  inputs: CalculationRequest;
  baseResults: CalculationResponse | null;
  millConfig: MillConfig | null;
}

export default function SulfidityPredictor({ inputs, baseResults, millConfig }: Props) {
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [result, setResult] = useState<CalculationResponse | null>(null);
  const [tornadoData, setTornadoData] = useState<TornadoRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [baseSulfidity, setBaseSulfidity] = useState<number | null>(null);
  const [trendRefresh, setTrendRefresh] = useState(0);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const params = useMemo(() => buildParams(millConfig), [millConfig]);

  const handleSliderChange = (param: PredictorParam, value: number) => {
    setOverrides((prev) => ({ ...prev, [param.key]: value }));
  };

  const buildOverridesRaw = (): Record<string, number> => {
    const o: Record<string, number> = {};
    for (const param of params) {
      const base = getBaseValue(inputs, baseResults, param);
      if (param.key === "nash_dry_override_lb_hr" || param.key === "naoh_dry_override_lb_hr") {
        // Always send NaSH/NaOH — the predictor's core purpose
        o[param.key] = overrides[param.key] ?? base;
      } else if (overrides[param.key] !== undefined) {
        // Only send params the user explicitly changed
        o[param.key] = overrides[param.key];
      }
    }
    return o;
  };

  const runPredict = async () => {
    setLoading(true);
    setError(null);
    try {
      const currentOverrides = buildOverridesRaw();
      const mainRes = await whatIf(inputs, buildOverrides(inputs, currentOverrides));
      setResult(mainRes.scenario_results);
      const mainSulf = mainRes.scenario_results.sulfidity.final_pct;
      setBaseSulfidity(mainSulf);

      const promises: Promise<{ param: PredictorParam; lowVal: number; highVal: number; lowSulf: number; highSulf: number }>[] = [];

      for (const param of params) {
        const val = currentOverrides[param.key] ?? getBaseValue(inputs, baseResults, param);
        const delta = val > 0 ? val * 0.1 : param.max * 0.1;
        const lowVal = Math.max(param.min, val - delta);
        const highVal = Math.min(param.max, val + delta);

        if (Math.abs(highVal - lowVal) < param.step * 0.5) {
          promises.push(
            Promise.resolve({ param, lowVal: val, highVal: val, lowSulf: mainSulf, highSulf: mainSulf })
          );
          continue;
        }

        const lowOverrides = { ...currentOverrides, [param.key]: lowVal };
        const lowP = whatIf(inputs, buildOverrides(inputs, lowOverrides)).then((r) => r.scenario_results.sulfidity.final_pct);
        const highOverrides = { ...currentOverrides, [param.key]: highVal };
        const highP = whatIf(inputs, buildOverrides(inputs, highOverrides)).then((r) => r.scenario_results.sulfidity.final_pct);

        promises.push(
          Promise.all([lowP, highP]).then(([lowSulf, highSulf]) => ({
            param, lowVal, highVal, lowSulf, highSulf,
          }))
        );
      }

      const pertResults = await Promise.all(promises);
      const rows: TornadoRow[] = pertResults.map(({ param, lowVal, highVal, lowSulf, highSulf }) => {
        const deltaLow = lowSulf - mainSulf;
        const deltaHigh = highSulf - mainSulf;
        return {
          label: param.label,
          downside: Math.min(deltaLow, deltaHigh, 0),
          upside: Math.max(deltaLow, deltaHigh, 0),
          range: Math.abs(Math.max(deltaLow, deltaHigh, 0) - Math.min(deltaLow, deltaHigh, 0)),
          lowLabel: fmtNum(lowVal, param.step < 1 ? 1 : 0),
          highLabel: fmtNum(highVal, param.step < 1 ? 1 : 0),
        };
      });
      rows.sort((a, b) => b.range - a.range);
      setTornadoData(rows);
    } catch (e) {
      console.error("Prediction failed:", e);
      setError("Prediction failed. Check backend connection.");
    } finally {
      setLoading(false);
    }
  };

  const getSulfidityColor = (sulfidity: number): string => {
    const target = inputs.target_sulfidity_pct;
    const diff = Math.abs(sulfidity - target);
    if (diff < 0.5) return "text-emerald-400";
    if (diff < 1.5) return "text-amber-400";
    return "text-red-400";
  };

  const getDeltaBadge = (sulfidity: number) => {
    const target = inputs.target_sulfidity_pct;
    const diff = sulfidity - target;
    const absDiff = Math.abs(diff);
    const color = absDiff < 0.5 ? "bg-emerald-500/10 text-emerald-400" :
                  absDiff < 1.5 ? "bg-amber-500/10 text-amber-400" :
                  "bg-red-500/10 text-red-400";
    const Icon = diff >= 0 ? TrendingUp : TrendingDown;
    return (
      <span className={cn("inline-flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-xs", color)}>
        <Icon className="h-3 w-3" />
        {diff >= 0 ? "+" : ""}{diff.toFixed(2)}%
      </span>
    );
  };

  const handleSaveTrend = async () => {
    if (!result) return;
    setSaveStatus("saving");
    try {
      await saveTrend({
        predicted_sulfidity_pct: result.sulfidity.final_pct,
        smelt_sulfidity_pct: result.sulfidity.smelt_pct,
        nash_dry_lb_hr: result.makeup.nash_dry_lb_hr,
        naoh_dry_lb_hr: result.makeup.naoh_dry_lb_hr,
        target_sulfidity_pct: inputs.target_sulfidity_pct,
      });
      setTrendRefresh((n) => n + 1);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (e) {
      console.error("Save to trend failed:", e);
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 2000);
    }
  };

  const maxAbsDelta = tornadoData.length > 0
    ? Math.max(...tornadoData.map((r) => Math.max(Math.abs(r.downside), Math.abs(r.upside))), 0.01)
    : 1;

  return (
    <div className="space-y-4">
      {/* Sliders Card */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Independent Variables</CardTitle>
              <p className="mt-1 font-mono text-[10px] text-muted-foreground">
                NaSH &amp; NaOH are fixed (Secant solver bypassed) — sulfidity becomes the output
              </p>
            </div>
            <Button size="sm" onClick={runPredict} disabled={loading}>
              <Zap className="mr-1.5 h-3.5 w-3.5" />
              {loading ? "Predicting..." : "Predict"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {params.map((param) => {
            const base = getBaseValue(inputs, baseResults, param);
            const current = overrides[param.key] ?? base;
            const changed = current !== base;
            return (
              <div key={param.key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
                    {param.label}
                  </span>
                  <span className="font-mono text-sm tabular-nums text-white">
                    {fmtNum(current, param.step < 1 ? 1 : 0)}
                    <span className="ml-1 text-[10px] text-muted-foreground">{param.unit}</span>
                    {changed && (
                      <span className="ml-2 text-[10px] text-white/30">
                        base: {fmtNum(base, param.step < 1 ? 1 : 0)}
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

      {/* Predicted Results */}
      {result && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle>Predicted Results</CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={handleSaveTrend}
                disabled={saveStatus === "saving"}
              >
                <Save className="mr-1.5 h-3.5 w-3.5" />
                {saveStatus === "saved" ? "Saved!" : saveStatus === "saving" ? "Saving..." : saveStatus === "error" ? "Save Failed" : "Save to Trend"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {/* Big sulfidity display */}
            <div className="mb-6 rounded-xl border border-white/[0.06] bg-white/[0.02] py-6 text-center">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Final Sulfidity
              </p>
              <p className={cn("mt-2 font-mono text-5xl font-bold tabular-nums", getSulfidityColor(result.sulfidity.final_pct))}>
                {fmtPct(result.sulfidity.final_pct, 2)}
              </p>
              <div className="mt-2 flex items-center justify-center gap-3">
                <span className="font-mono text-xs text-muted-foreground">
                  Target: {fmtPct(inputs.target_sulfidity_pct, 1)}
                </span>
                {getDeltaBadge(result.sulfidity.final_pct)}
              </div>
            </div>

            {/* Key metrics */}
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Metric</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Base</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Predicted</th>
                  <th className="pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Delta</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { label: "Final Sulfidity", b: baseResults?.sulfidity.final_pct ?? 0, s: result.sulfidity.final_pct, unit: "%" },
                  { label: "Smelt Sulfidity", b: baseResults?.sulfidity.smelt_pct ?? 0, s: result.sulfidity.smelt_pct, unit: "%" },
                  { label: "NaSH (dry)", b: baseResults?.makeup.nash_dry_lb_hr ?? 0, s: result.makeup.nash_dry_lb_hr, unit: "lb/hr" },
                  { label: "NaOH (dry)", b: baseResults?.makeup.naoh_dry_lb_hr ?? 0, s: result.makeup.naoh_dry_lb_hr, unit: "lb/hr" },
                  { label: "Dead Load", b: baseResults?.recovery_boiler.dead_load_lb_hr ?? 0, s: result.recovery_boiler.dead_load_lb_hr, unit: "lb/hr" },
                  { label: "Na Balance", b: baseResults?.mass_balance.na_deficit_lb_hr ?? 0, s: result.mass_balance.na_deficit_lb_hr, unit: "lb/hr" },
                  { label: "Net S Balance", b: baseResults?.mass_balance.net_s_balance_lb_hr ?? 0, s: result.mass_balance.net_s_balance_lb_hr, unit: "lb/hr" },
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

      {/* Tornado Chart */}
      {tornadoData.length > 0 && baseSulfidity !== null && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Sensitivity Tornado</CardTitle>
            <p className="font-mono text-[10px] text-muted-foreground">
              Sulfidity impact of +/-10% change in each variable (sorted by impact)
            </p>
          </CardHeader>
          <CardContent>
            {/* Axis labels */}
            <div className="mb-1 flex items-center font-mono text-[10px] text-muted-foreground">
              <div className="w-36" />
              <div className="flex flex-1 justify-between px-1">
                <span>{fmtNum(baseSulfidity - maxAbsDelta, 2)}%</span>
                <span className="font-medium text-white">{fmtNum(baseSulfidity, 2)}%</span>
                <span>{fmtNum(baseSulfidity + maxAbsDelta, 2)}%</span>
              </div>
              <div className="w-24" />
            </div>

            {/* Tornado rows */}
            <div className="space-y-1.5">
              {tornadoData.map((row) => {
                const downsidePct = maxAbsDelta > 0 ? (Math.abs(row.downside) / maxAbsDelta) * 50 : 0;
                const upsidePct = maxAbsDelta > 0 ? (Math.abs(row.upside) / maxAbsDelta) * 50 : 0;

                return (
                  <div key={row.label} className="flex items-center gap-0">
                    <div className="w-36 truncate pr-2 text-right font-mono text-[11px] text-muted-foreground" title={row.label}>
                      {row.label}
                    </div>

                    <div className="relative h-7 flex-1 rounded-sm bg-white/[0.03]">
                      {/* Center line */}
                      <div className="absolute left-1/2 top-0 bottom-0 z-10 w-px bg-white/[0.1]" />

                      {/* Downside bar (teal, extends left) */}
                      {downsidePct > 0.1 && (
                        <div
                          className="absolute top-1 bottom-1 rounded-sm bg-cyan/60"
                          style={{ right: "50%", width: `${downsidePct}%` }}
                        />
                      )}

                      {/* Upside bar (amber, extends right) */}
                      {upsidePct > 0.1 && (
                        <div
                          className="absolute top-1 bottom-1 rounded-sm bg-amber-400/60"
                          style={{ left: "50%", width: `${upsidePct}%` }}
                        />
                      )}
                    </div>

                    <div className="w-24 pl-2 text-right font-mono text-[11px] tabular-nums">
                      {row.range < 0.005 ? (
                        <span className="text-white/20">--</span>
                      ) : (
                        <span>
                          <span className="text-cyan">{row.downside < 0 ? row.downside.toFixed(2) : ""}</span>
                          {row.downside < 0 && row.upside > 0 && " / "}
                          <span className="text-amber-400">{row.upside > 0 ? `+${row.upside.toFixed(2)}` : ""}</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div className="mt-4 flex items-center gap-4 font-mono text-[10px] text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded-sm bg-cyan/60" />
                <span>Sulfidity decrease</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded-sm bg-amber-400/60" />
                <span>Sulfidity increase</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Trend Chart */}
      <SulfidityTrend refreshTrigger={trendRefresh} />
    </div>
  );
}
