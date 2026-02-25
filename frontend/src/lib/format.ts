export function fmtNum(v: number | undefined | null, decimals = 1): string {
  if (v == null || isNaN(v)) return "--";
  return v.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtPct(v: number | undefined | null, decimals = 2): string {
  if (v == null || isNaN(v)) return "--";
  return `${v.toFixed(decimals)}%`;
}

export function fmtDelta(v: number | undefined | null, decimals = 1): string {
  if (v == null || isNaN(v)) return "--";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(decimals)}`;
}

export function severityColor(severity: string): string {
  switch (severity) {
    case "red":
      return "border-red-500/40 bg-red-500/[0.06]";
    case "yellow":
      return "border-yellow-500/40 bg-yellow-500/[0.06]";
    case "green":
      return "border-emerald-500/40 bg-emerald-500/[0.06]";
    default:
      return "border-white/[0.06] bg-white/[0.02]";
  }
}

export function severityIcon(severity: string): string {
  switch (severity) {
    case "red":
      return "!!";
    case "yellow":
      return "!";
    case "green":
      return "OK";
    default:
      return "?";
  }
}

export function trendLabel(trend: string): string {
  switch (trend) {
    case "rising":
      return "RISING";
    case "falling":
      return "FALLING";
    case "steady":
      return "STEADY";
    default:
      return trend.toUpperCase();
  }
}

export function trendColor(trend: string): string {
  switch (trend) {
    case "rising":
      return "text-orange-400";
    case "falling":
      return "text-blue-400";
    case "steady":
      return "text-emerald-400";
    default:
      return "text-muted-foreground";
  }
}
