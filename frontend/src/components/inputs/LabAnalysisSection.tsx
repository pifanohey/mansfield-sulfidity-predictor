"use client";

import InputField from "./InputField";
import type { LiquorAnalysis } from "@/lib/types";

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
  return (
    <div>
      <p className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-cyan">
        {title}
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <InputField
          label="TTA"
          value={analysis.tta}
          onChange={(v) => onChange("tta", v)}
          unit="lb/ft³"
          excelRef={`${excelPrefix}TTA`}
        />
        <InputField
          label="EA"
          value={analysis.ea}
          onChange={(v) => onChange("ea", v)}
          unit="lb/ft³"
          excelRef={`${excelPrefix}EA`}
        />
        <InputField
          label="AA"
          value={analysis.aa}
          onChange={(v) => onChange("aa", v)}
          unit="lb/ft³"
          excelRef={`${excelPrefix}AA`}
        />
      </div>
    </div>
  );
}
