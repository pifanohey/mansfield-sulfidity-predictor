import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { fmtPct, trendLabel } from "@/lib/format";

interface SulfidityGaugeProps {
  current: number;
  latent: number;
  final: number;
  smelt: number;
  target: number;
  trend: string;
}

function ConfidenceRing({ value, target }: { value: number; target: number }) {
  const diff = Math.abs(value - target);
  const confidence = diff < 0.2 ? "High" : diff < 0.5 ? "Medium" : "Low";
  const pct = diff < 0.2 ? 90 : diff < 0.5 ? 65 : 35;
  const circumference = 2 * Math.PI * 42;
  const strokeDasharray = `${(pct / 100) * circumference} ${circumference}`;

  return (
    <div className="relative flex flex-col items-center">
      <svg width="110" height="110" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="hsl(232 15% 18%)"
          strokeWidth="6"
        />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="hsl(168 84% 64%)"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={strokeDasharray}
          transform="rotate(-90 50 50)"
          className="transition-all duration-700"
        />
        <text
          x="50"
          y="46"
          textAnchor="middle"
          className="fill-white text-[15px] font-bold"
          fontFamily="var(--font-mono)"
        >
          {confidence}
        </text>
        <text
          x="50"
          y="60"
          textAnchor="middle"
          className="fill-[hsl(230,10%,55%)] text-[8px] uppercase"
          fontFamily="var(--font-mono)"
          letterSpacing="0.12em"
        >
          CONFIDENCE
        </text>
      </svg>
    </div>
  );
}

function MetricRow({
  label,
  value,
  target,
  color,
}: {
  label: string;
  value: number;
  target: number;
  color: string;
}) {
  const diff = value - target;
  const diffStr = diff >= 0 ? `+${diff.toFixed(2)}%` : `${diff.toFixed(2)}%`;

  return (
    <div className="flex items-center justify-between border-b border-white/[0.04] py-2.5 last:border-0">
      <div className="flex items-center gap-2">
        <div className={cn("h-2 w-2 rounded-full", color)} />
        <span className="font-mono text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="font-mono text-sm font-medium text-white">
          {fmtPct(value)}
        </span>
        <span
          className={cn(
            "font-mono text-[11px]",
            diff > 0 ? "text-emerald-400" : diff < -0.5 ? "text-red-400" : "text-amber-400"
          )}
        >
          {diffStr}
        </span>
      </div>
    </div>
  );
}

export default function SulfidityGauge({
  current,
  latent,
  final: finalVal,
  smelt,
  target,
  trend,
}: SulfidityGaugeProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle>Predicted Sulfidity</CardTitle>
          <span
            className={cn(
              "rounded-md px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider",
              trend === "FALLING"
                ? "bg-amber-500/10 text-amber-400"
                : trend === "RISING"
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-cyan/10 text-cyan"
            )}
          >
            {trendLabel(trend)}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <span className="font-mono text-5xl font-bold text-white">
              {fmtPct(finalVal)}
            </span>
            <div className="mt-2 flex items-center gap-2">
              <span className="rounded-md bg-emerald-500/10 px-2 py-0.5 font-mono text-xs text-emerald-400">
                {"\u2197"} {(finalVal - smelt) >= 0 ? "+" : ""}{(finalVal - smelt).toFixed(2)}%
              </span>
              <span className="font-mono text-xs text-muted-foreground">
                vs smelt
              </span>
            </div>
            <p className="mt-3 max-w-[280px] text-xs leading-relaxed text-muted-foreground">
              {Math.abs(finalVal - target) < 0.1
                ? "Optimal range achieved. Sulfidity on target."
                : finalVal > target
                ? "Running above target. Consider reducing NaSH feed."
                : "Below target. Increase NaSH or check reduction efficiency."}
            </p>
          </div>
          <ConfidenceRing value={finalVal} target={target} />
        </div>

        <div className="mt-5 border-t border-white/[0.06] pt-4">
          <MetricRow label="Current (WL)" value={current} target={target} color="bg-blue-400" />
          <MetricRow label="Latent (BL)" value={latent} target={target} color="bg-purple-400" />
          <MetricRow label="Final (after makeup)" value={finalVal} target={target} color="bg-cyan" />
          <MetricRow label="Smelt (RB)" value={smelt} target={target} color="bg-amber-400" />
          <div className="mt-2 text-center font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
            Target: {fmtPct(target)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
