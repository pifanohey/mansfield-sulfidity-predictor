import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KPICardProps {
  label: string;
  value: string;
  unit?: string;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export default function KPICard({
  label,
  value,
  unit,
  subtitle,
  trend,
  className,
}: KPICardProps) {
  return (
    <Card className={cn("", className)}>
      <CardContent className="p-5">
        <p className="font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">
          {label}
        </p>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-mono text-2xl font-semibold text-white">
            {value}
          </span>
          {unit && (
            <span className="font-mono text-xs text-muted-foreground">
              {unit}
            </span>
          )}
          {trend && trend !== "neutral" && (
            <span
              className={cn(
                "font-mono text-xs font-medium",
                trend === "up"
                  ? "text-amber-400"
                  : "text-cyan"
              )}
            >
              {trend === "up" ? "\u2191" : "\u2193"}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="mt-1.5 font-mono text-[11px] text-muted-foreground">
            {subtitle}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
