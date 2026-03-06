"use client";

import InputField from "./InputField";
import type { DissolvingTankConfig } from "@/lib/types";
import type { DTInputState } from "@/hooks/useAppState";

interface Props {
  wwFlow: number;
  wwTtaLbFt3: number;
  wwSulfidity: number;
  showerFlow: number;
  smeltDensity: number;
  glTargetTtaLbFt3: number;
  glCausticity: number;
  onChange: (key: string, value: number) => void;
  dtConfigs?: DissolvingTankConfig[];
  dtInputs?: Record<string, DTInputState>;
  onDTFieldChange?: (dtId: string, key: string, value: number) => void;
}

const DT_FIELDS: Array<{
  key: keyof DTInputState;
  label: string;
  unit: string;
  excelRef: string;
  step: number;
}> = [
  { key: "ww_flow_gpm", label: "WW Flow", unit: "gpm", excelRef: "2_RB!I53", step: 1 },
  { key: "ww_tta_lb_ft3", label: "WW TTA", unit: "lb/ft³", excelRef: "2_RB!I50", step: 0.001 },
  { key: "ww_sulfidity", label: "WW Sulfidity", unit: "frac", excelRef: "2_RB!I48", step: 0.001 },
  { key: "shower_flow_gpm", label: "Shower Flow", unit: "gpm", excelRef: "2_RB!I54", step: 1 },
  { key: "smelt_density_lb_ft3", label: "Smelt Density", unit: "lb/ft³", excelRef: "2_RB!I56", step: 1 },
];

export default function DissolvingTankSection({
  wwFlow,
  wwTtaLbFt3,
  wwSulfidity,
  showerFlow,
  smeltDensity,
  glTargetTtaLbFt3,
  glCausticity,
  onChange,
  dtConfigs,
  dtInputs,
  onDTFieldChange,
}: Props) {
  const isMultiDT = dtConfigs && dtConfigs.length > 1;

  return (
    <div>
      {/* Global GL fields (always shown) */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <InputField
          label="GL TTA Target"
          value={glTargetTtaLbFt3}
          onChange={(v) => onChange("gl_target_tta_lb_ft3", v)}
          unit="lb/ft³"
          excelRef="2_RB!I49"
          step={0.001}
        />
        <InputField
          label="GL Causticity"
          value={glCausticity}
          onChange={(v) => onChange("gl_causticity", v)}
          unit="frac"
          excelRef="2_RB!I75"
          step={0.001}
        />
      </div>

      {/* Single DT — flat fields */}
      {!isMultiDT && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <InputField
            label="WW Flow"
            value={wwFlow}
            onChange={(v) => onChange("ww_flow_gpm", v)}
            unit="gpm"
            excelRef="2_RB!I53"
            step={1}
          />
          <InputField
            label="WW TTA"
            value={wwTtaLbFt3}
            onChange={(v) => onChange("ww_tta_lb_ft3", v)}
            unit="lb/ft³"
            excelRef="2_RB!I50"
            step={0.001}
          />
          <InputField
            label="WW Sulfidity"
            value={wwSulfidity}
            onChange={(v) => onChange("ww_sulfidity", v)}
            unit="frac"
            excelRef="2_RB!I48"
            step={0.001}
          />
          <InputField
            label="Shower Flow"
            value={showerFlow}
            onChange={(v) => onChange("shower_flow_gpm", v)}
            unit="gpm"
            excelRef="2_RB!I54"
            step={1}
          />
          <InputField
            label="Smelt Density"
            value={smeltDensity}
            onChange={(v) => onChange("smelt_density_lb_ft3", v)}
            unit="lb/ft³"
            excelRef="2_RB!I56"
            step={1}
          />
        </div>
      )}

      {/* Multi-DT — per-DT editable sections */}
      {isMultiDT && (
        <div className="mt-4 space-y-5">
          {dtConfigs.map((dtc) => {
            const values = dtInputs?.[dtc.id] ?? {
              ww_flow_gpm: dtc.defaults.ww_flow_gpm ?? 0,
              ww_tta_lb_ft3: dtc.defaults.ww_tta_lb_ft3 ?? 0,
              ww_sulfidity: dtc.defaults.ww_sulfidity ?? 0,
              shower_flow_gpm: dtc.defaults.shower_flow_gpm ?? 0,
              smelt_density_lb_ft3: dtc.defaults.smelt_density_lb_ft3 ?? 0,
            };
            return (
              <div key={dtc.id} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                <h4 className="mb-3 font-mono text-xs font-medium text-white">
                  {dtc.name}
                  <span className="ml-2 text-[10px] text-muted-foreground">({dtc.id})</span>
                </h4>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {DT_FIELDS.map((f) => (
                    <InputField
                      key={`${dtc.id}-${f.key}`}
                      label={f.label}
                      value={values[f.key]}
                      onChange={(v) => onDTFieldChange?.(dtc.id, f.key, v)}
                      unit={f.unit}
                      excelRef={f.excelRef}
                      step={f.step}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
