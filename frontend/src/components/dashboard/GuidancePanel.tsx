import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { GuidanceItem } from "@/lib/types";

interface GuidancePanelProps {
  items: GuidanceItem[];
}

function AlertCard({ item }: { item: GuidanceItem }) {
  const severityConfig = {
    red: { label: "CRITICAL", color: "text-red-400", bg: "bg-red-500/10" },
    yellow: { label: "WARNING", color: "text-amber-400", bg: "bg-amber-500/10" },
    green: { label: "OK", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  };

  const config = severityConfig[item.severity] || severityConfig.green;

  return (
    <div className="rounded-lg border border-white/[0.04] bg-white/[0.02] p-3">
      <div className="flex items-start justify-between">
        <span className={cn("font-mono text-[10px] font-bold uppercase tracking-wider", config.color)}>
          {config.label}
        </span>
        <span className="font-mono text-[10px] text-muted-foreground">
          {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
      <p className="mt-1.5 text-sm font-medium text-white">{item.title}</p>
      {item.description && (
        <p className="mt-1 text-xs text-muted-foreground">{item.description}</p>
      )}
      {item.action && (
        <p className="mt-1.5 font-mono text-[11px] text-cyan">
          {"\u2192"} {item.action}
        </p>
      )}
    </div>
  );
}

export default function GuidancePanel({ items }: GuidancePanelProps) {
  if (items.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle>Process Alerts</CardTitle>
          <span className="rounded-md bg-white/[0.06] px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
            {items.length} active
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {items.map((item, i) => (
          <AlertCard key={i} item={item} />
        ))}
      </CardContent>
    </Card>
  );
}
