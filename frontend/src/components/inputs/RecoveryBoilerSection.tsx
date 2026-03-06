"use client";

import InputField from "./InputField";
import type { RecoveryBoilerInputs, RecoveryBoilerConfig } from "@/lib/types";

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

interface Props {
  rb: RecoveryBoilerInputs;
  onChange: (key: string, value: number) => void;
  rbConfigs?: RecoveryBoilerConfig[];
  rbInputs?: Record<string, RecoveryBoilerInputs>;
  onRBFieldChange?: (rbId: string, key: string, value: number) => void;
}

export default function RecoveryBoilerSection({ rb, onChange, rbConfigs, rbInputs, onRBFieldChange }: Props) {
  // Single RB — render flat fields
  if (!rbConfigs || rbConfigs.length <= 1) {
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

  // Multi-RB — render per-RB editable sections
  return (
    <div className="space-y-5">
      {rbConfigs.map((rbc) => {
        const values = rbInputs?.[rbc.id] ?? {
          bl_flow_gpm: rbc.defaults.bl_flow_gpm ?? 0,
          bl_tds_pct: rbc.defaults.bl_tds_pct ?? 0,
          bl_temp_f: rbc.defaults.bl_temp_f ?? 0,
          reduction_eff_pct: rbc.defaults.reduction_eff_pct ?? 0,
          ash_recycled_pct: rbc.defaults.ash_recycled_pct ?? 0,
          saltcake_flow_lb_hr: rbc.defaults.saltcake_flow_lb_hr ?? 0,
        };
        return (
          <div key={rbc.id} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
            <h4 className="mb-3 font-mono text-xs font-medium text-white">
              {rbc.name}
              <span className="ml-2 text-[10px] text-muted-foreground">({rbc.id})</span>
            </h4>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {FIELDS.map((f) => (
                <InputField
                  key={`${rbc.id}-${f.key}`}
                  label={f.label}
                  value={values[f.key]}
                  onChange={(v) => onRBFieldChange?.(rbc.id, f.key, v)}
                  unit={f.unit}
                  excelRef={f.excelRef}
                  step={f.step}
                  min={0}
                />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
