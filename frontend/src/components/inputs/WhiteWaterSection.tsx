"use client";

import InputField from "./InputField";
import type { FiberlineConfig, FiberlineInputState } from "@/lib/types";

interface Props {
  washWaterNaPct: number;
  washWaterSPct: number;
  fiberlines: FiberlineConfig[];
  fiberlineInputs: Record<string, FiberlineInputState>;
  onChange: (key: string, value: number) => void;
  onFiberlineChange: (fiberlineId: string, key: string, value: number) => void;
}

export default function WhiteWaterSection({
  washWaterNaPct,
  washWaterSPct,
  fiberlines,
  fiberlineInputs,
  onChange,
  onFiberlineChange,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 font-mono text-[10px] text-muted-foreground">
        Paper machine white water returning Na and S to brownstock washers.
      </div>

      {/* Global concentrations */}
      <div>
        <h4 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Concentrations
        </h4>
        <div className="grid gap-3 sm:grid-cols-2">
          <InputField
            label="Na Concentration"
            value={washWaterNaPct}
            onChange={(v) => onChange("wash_water_na_pct", v)}
            unit="% wt"
            step={0.001}
          />
          <InputField
            label="S Concentration"
            value={washWaterSPct}
            onChange={(v) => onChange("wash_water_s_pct", v)}
            unit="% wt"
            step={0.001}
          />
        </div>
      </div>

      {/* Per-fiberline wash water flow */}
      <div>
        <h4 className="mb-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          Flow per Fiberline
        </h4>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {fiberlines.map((fl) => (
            <InputField
              key={fl.id}
              label={fl.name}
              value={
                fiberlineInputs[fl.id]?.wash_water_gpm ??
                fl.defaults.wash_water_gpm ??
                0
              }
              onChange={(v) => onFiberlineChange(fl.id, "wash_water_gpm", v)}
              unit="gpm"
              step={1}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
