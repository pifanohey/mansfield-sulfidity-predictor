"use client";

import InputField from "./InputField";
import type { FiberlineConfig } from "@/lib/types";

export interface FiberlineInputState {
  production_bdt_day?: number;
  yield_pct?: number;
  ea_pct?: number;
  gl_ea_pct?: number;
}

interface Props {
  fiberlines: FiberlineConfig[];
  fiberlineInputs: Record<string, FiberlineInputState>;
  cookingSulfidity: number;
  onFiberlineChange: (fiberlineId: string, key: string, value: number) => void;
  onGlobalChange: (key: string, value: number) => void;
}

export default function ProductionSection({
  fiberlines,
  fiberlineInputs,
  cookingSulfidity,
  onFiberlineChange,
  onGlobalChange,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <InputField
          label="Cooking WL Sulfidity"
          value={cookingSulfidity}
          onChange={(v) => onGlobalChange("cooking_wl_sulfidity", v)}
          unit="frac"
          step={0.001}
        />
      </div>

      {fiberlines.map((fl) => (
        <div key={fl.id}>
          <h4 className="mb-2 font-mono text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {fl.name} ({fl.type} / {fl.cooking_type})
          </h4>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <InputField
              label="Production"
              value={fiberlineInputs[fl.id]?.production_bdt_day ?? fl.defaults.production_bdt_day}
              onChange={(v) => onFiberlineChange(fl.id, "production_bdt_day", v)}
              unit="BDT/day"
            />
            <InputField
              label="Yield"
              value={fiberlineInputs[fl.id]?.yield_pct ?? fl.defaults.yield_pct}
              onChange={(v) => onFiberlineChange(fl.id, "yield_pct", v)}
              unit="frac"
              step={0.001}
            />
            <InputField
              label="EA Charge"
              value={fiberlineInputs[fl.id]?.ea_pct ?? fl.defaults.ea_pct}
              onChange={(v) => onFiberlineChange(fl.id, "ea_pct", v)}
              unit="frac"
              step={0.001}
            />
            {fl.uses_gl_charge && (
              <InputField
                label="GL EA"
                value={fiberlineInputs[fl.id]?.gl_ea_pct ?? fl.defaults.gl_ea_pct ?? 0}
                onChange={(v) => onFiberlineChange(fl.id, "gl_ea_pct", v)}
                unit="frac"
                step={0.001}
              />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
