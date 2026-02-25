"use client";

import InputField from "./InputField";

interface Props {
  targetSulfidity: number;
  causticity: number;
  ctoH2so4PerTon: number;
  ctoTpd: number;
  onChange: (key: string, value: number | boolean) => void;
}

export default function SetpointSection({
  targetSulfidity,
  causticity,
  ctoH2so4PerTon,
  ctoTpd,
  onChange,
}: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <InputField
        label="Target Sulfidity"
        value={targetSulfidity}
        onChange={(v) => onChange("target_sulfidity_pct", v)}
        unit="%"
        excelRef="0_SULF!H39"
        step={0.1}
      />
      <InputField
        label="Causticity"
        value={causticity}
        onChange={(v) => onChange("causticity_pct", v)}
        unit="%"
        excelRef="3_CC!G67"
        step={0.1}
      />
      <InputField
        label="CTO H2SO4/ton"
        value={ctoH2so4PerTon}
        onChange={(v) => onChange("cto_h2so4_per_ton", v)}
        unit="lb/T"
        excelRef="CTO!C9"
        step={1}
      />
      <InputField
        label="CTO Production"
        value={ctoTpd}
        onChange={(v) => onChange("cto_tpd", v)}
        unit="TPD"
        excelRef="CTO!C10"
        step={1}
      />
    </div>
  );
}
