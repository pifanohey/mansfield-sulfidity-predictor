"use client";

import InputField from "./InputField";
import type { RecoveryBoilerInputs, RecoveryBoilerConfig } from "@/lib/types";

interface SingleRBProps {
  rb: RecoveryBoilerInputs;
  onChange: (key: string, value: number) => void;
  label?: string;
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

function SingleRBFields({ rb, onChange, label }: SingleRBProps) {
  return (
    <div>
      {label && (
        <h4 className="mb-2 font-mono text-xs font-medium text-muted-foreground">{label}</h4>
      )}
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
    </div>
  );
}

interface Props {
  rb: RecoveryBoilerInputs;
  onChange: (key: string, value: number) => void;
  rbConfigs?: RecoveryBoilerConfig[];
}

export default function RecoveryBoilerSection({ rb, onChange, rbConfigs }: Props) {
  // Single RB (legacy or single-RB mill) — render flat
  if (!rbConfigs || rbConfigs.length <= 1) {
    return <SingleRBFields rb={rb} onChange={onChange} />;
  }

  // Multi-RB: show per-RB sections using config defaults (read-only display)
  // User edits go to the flat inputs which serve as global overrides
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 font-mono text-[10px] text-muted-foreground">
        {rbConfigs.length} Recovery Boilers configured. Global inputs below apply to all RBs.
        Per-RB defaults are loaded from mill configuration.
      </div>
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
      <div className="mt-3 space-y-2">
        {rbConfigs.map((rbc) => (
          <div key={rbc.id} className="rounded-md border border-white/[0.04] bg-white/[0.01] px-3 py-2">
            <span className="font-mono text-[10px] text-muted-foreground">{rbc.name}</span>
            <span className="ml-2 font-mono text-[9px] text-muted-foreground/60">
              BL: {rbc.defaults.bl_flow_gpm} gpm | TDS: {rbc.defaults.bl_tds_pct}% | RE: {rbc.defaults.reduction_eff_pct}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
