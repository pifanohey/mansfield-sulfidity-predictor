"use client";

import InputField from "./InputField";
import type { RecoveryBoilerInputs } from "@/lib/types";

interface Props {
  rb: RecoveryBoilerInputs;
  onChange: (key: string, value: number) => void;
}

const FIELDS: Array<{
  key: keyof RecoveryBoilerInputs;
  label: string;
  unit: string;
  excelRef: string;
  step?: number;
}> = [
  { key: "bl_flow_gpm", label: "BL Flow", unit: "gpm", excelRef: "2_RB!B3", step: 0.1 },
  { key: "bl_tds_pct", label: "BL TDS", unit: "%", excelRef: "2_RB!B11", step: 0.1 },
  { key: "bl_temp_f", label: "BL Temperature", unit: "°F", excelRef: "2_RB!B13", step: 0.1 },
  { key: "reduction_eff_pct", label: "Reduction Eff.", unit: "%", excelRef: "2_RB!B14", step: 0.1 },
  { key: "ash_recycled_pct", label: "Ash Recycled", unit: "frac", excelRef: "2_RB!B4", step: 0.01 },
  { key: "saltcake_flow_lb_hr", label: "Saltcake Flow", unit: "lb/hr", excelRef: "2_RB!B40", step: 1 },
];

export default function RecoveryBoilerSection({ rb, onChange }: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {FIELDS.map((f) => (
        <InputField
          key={f.key}
          label={f.label}
          value={rb[f.key]}
          onChange={(v) => onChange(f.key, v)}
          unit={f.unit}
          excelRef={f.excelRef}
          step={f.step}
          min={0}
        />
      ))}
    </div>
  );
}
