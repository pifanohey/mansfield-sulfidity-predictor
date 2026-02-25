"use client";

import InputField from "./InputField";

interface Props {
  wwFlow: number;
  wwTtaLbFt3: number;
  wwSulfidity: number;
  showerFlow: number;
  smeltDensity: number;
  glTargetTtaLbFt3: number;
  glCausticity: number;
  onChange: (key: string, value: number) => void;
}

export default function DissolvingTankSection({
  wwFlow,
  wwTtaLbFt3,
  wwSulfidity,
  showerFlow,
  smeltDensity,
  glTargetTtaLbFt3,
  glCausticity,
  onChange,
}: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
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
  );
}
