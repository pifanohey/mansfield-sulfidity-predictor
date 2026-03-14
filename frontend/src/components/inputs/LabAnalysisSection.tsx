"use client";

import InputField from "./InputField";
import type { LiquorAnalysis } from "@/lib/types";
import { useAppState } from "@/hooks/useAppState";
import { getLiquorUnitLabel, toDisplay, fromDisplay, type LiquorUnit } from "@/lib/units";

interface Props {
  title: string;
  analysis: LiquorAnalysis;
  onChange: (key: string, value: number) => void;
  excelPrefix: string;
}

export default function LabAnalysisSection({
  title,
  analysis,
  onChange,
  excelPrefix,
}: Props) {
  const { millConfig } = useAppState();
  const unit = (millConfig?.liquor_unit ?? "lb_per_ft3") as LiquorUnit;
  const label = getLiquorUnitLabel(unit);

  return (
    <div>
      <p className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-cyan">
        {title}
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <InputField
          label="TTA"
          value={toDisplay(analysis.tta, unit)}
          onChange={(v) => onChange("tta", fromDisplay(v, unit))}
          unit={label}
          excelRef={`${excelPrefix}TTA`}
        />
        <InputField
          label="EA"
          value={toDisplay(analysis.ea, unit)}
          onChange={(v) => onChange("ea", fromDisplay(v, unit))}
          unit={label}
          excelRef={`${excelPrefix}EA`}
        />
        <InputField
          label="AA"
          value={toDisplay(analysis.aa, unit)}
          onChange={(v) => onChange("aa", fromDisplay(v, unit))}
          unit={label}
          excelRef={`${excelPrefix}AA`}
        />
      </div>
    </div>
  );
}
