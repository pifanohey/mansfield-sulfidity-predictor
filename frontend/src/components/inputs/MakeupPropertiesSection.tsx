"use client";

import InputField from "./InputField";

interface Props {
  nashConc: number;
  naohConc: number;
  nashDensity: number;
  naohDensity: number;
  onChange: (key: string, value: number) => void;
}

export default function MakeupPropertiesSection({
  nashConc,
  naohConc,
  nashDensity,
  naohDensity,
  onChange,
}: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <InputField
        label="NaSH Concentration"
        value={nashConc}
        onChange={(v) => onChange("nash_concentration", v)}
        unit="frac"
        excelRef="0_SULF!B44"
        step={0.01}
      />
      <InputField
        label="NaOH Concentration"
        value={naohConc}
        onChange={(v) => onChange("naoh_concentration", v)}
        unit="frac"
        excelRef="0_SULF!B51"
        step={0.01}
      />
      <InputField
        label="NaSH Density"
        value={nashDensity}
        onChange={(v) => onChange("nash_density", v)}
        unit="kg/L"
        excelRef="0_SULF!B45"
        step={0.01}
      />
      <InputField
        label="NaOH Density"
        value={naohDensity}
        onChange={(v) => onChange("naoh_density", v)}
        unit="kg/L"
        excelRef="0_SULF!B52"
        step={0.01}
      />
    </div>
  );
}
