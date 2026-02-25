"use client";

import InputField from "./InputField";

interface Props {
  limeChargeRatio: number;
  caoInLime: number;
  caco3InLime: number;
  inertsInLime: number;
  gritsLoss: number;
  limeTemp: number;
  slakerTemp: number;
  intrusionWater: number;
  dilutionWater: number;
  wlcUnderflowSolids: number;
  wlcMudDensity: number;
  dregsLbBdt: number;
  glcUnderflowSolids: number;
  gritsLbBdt: number;
  gritsSolids: number;
  onChange: (key: string, value: number) => void;
}

export default function SlakerWLCSection({
  limeChargeRatio,
  caoInLime,
  caco3InLime,
  inertsInLime,
  gritsLoss,
  limeTemp,
  slakerTemp,
  intrusionWater,
  dilutionWater,
  wlcUnderflowSolids,
  wlcMudDensity,
  dregsLbBdt,
  glcUnderflowSolids,
  gritsLbBdt,
  gritsSolids,
  onChange,
}: Props) {
  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium text-muted-foreground">Slaker / Lime</h4>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <InputField
          label="Lime Charge Ratio"
          value={limeChargeRatio}
          onChange={(v) => onChange("lime_charge_ratio", v)}
          unit=""
          excelRef="Slaker!B26"
          step={0.01}
        />
        <InputField
          label="CaO in Lime"
          value={caoInLime}
          onChange={(v) => onChange("cao_in_lime_pct", v)}
          unit="%"
          excelRef="Slaker!B14"
          step={0.01}
        />
        <InputField
          label="CaCO3 in Lime"
          value={caco3InLime}
          onChange={(v) => onChange("caco3_in_lime_pct", v)}
          unit="%"
          excelRef="Slaker!B15"
          step={0.01}
        />
        <InputField
          label="Inerts in Lime"
          value={inertsInLime}
          onChange={(v) => onChange("inerts_in_lime_pct", v)}
          unit="%"
          excelRef="Slaker!B16"
          step={0.001}
        />
        <InputField
          label="Grits Loss"
          value={gritsLoss}
          onChange={(v) => onChange("grits_loss_pct", v)}
          unit="%"
          step={0.1}
        />
        <InputField
          label="Lime Temp"
          value={limeTemp}
          onChange={(v) => onChange("lime_temp_f", v)}
          unit="°F"
          excelRef="Slaker!G78"
          step={1}
        />
        <InputField
          label="Slaker Temp"
          value={slakerTemp}
          onChange={(v) => onChange("slaker_temp_f", v)}
          unit="°F"
          excelRef="Slaker!G79"
          step={0.1}
        />
      </div>

      <h4 className="text-sm font-medium text-muted-foreground">White Liquor Clarifier</h4>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <InputField
          label="Intrusion Water"
          value={intrusionWater}
          onChange={(v) => onChange("intrusion_water_gpm", v)}
          unit="gpm"
          excelRef="3_CC!U86"
          step={0.1}
        />
        <InputField
          label="Dilution Water"
          value={dilutionWater}
          onChange={(v) => onChange("dilution_water_gpm", v)}
          unit="gpm"
          excelRef="3_CC!Q73"
          step={0.001}
        />
        <InputField
          label="Underflow Solids"
          value={wlcUnderflowSolids}
          onChange={(v) => onChange("wlc_underflow_solids_pct", v)}
          unit="frac"
          excelRef="3_CC!P90"
          step={0.001}
        />
        <InputField
          label="Mud Density"
          value={wlcMudDensity}
          onChange={(v) => onChange("wlc_mud_density", v)}
          unit="SG"
          excelRef="3_CC!P92"
          step={0.01}
        />
      </div>

      <h4 className="text-sm font-medium text-muted-foreground">GL Clarifier</h4>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <InputField
          label="Dregs"
          value={dregsLbBdt}
          onChange={(v) => onChange("dregs_lb_bdt", v)}
          unit="lb/BDT"
          excelRef="3_CC!B63"
          step={0.001}
        />
        <InputField
          label="GLC Underflow Solids"
          value={glcUnderflowSolids}
          onChange={(v) => onChange("glc_underflow_solids_pct", v)}
          unit="frac"
          excelRef="3_CC!B65"
          step={0.001}
        />
        <InputField
          label="Grits"
          value={gritsLbBdt}
          onChange={(v) => onChange("grits_lb_bdt", v)}
          unit="lb/BDT"
          excelRef="3_CC!B73"
          step={0.01}
        />
        <InputField
          label="Grits Solids"
          value={gritsSolids}
          onChange={(v) => onChange("grits_solids_pct", v)}
          unit="frac"
          excelRef="3_CC!B75"
          step={0.01}
        />
      </div>
    </div>
  );
}
