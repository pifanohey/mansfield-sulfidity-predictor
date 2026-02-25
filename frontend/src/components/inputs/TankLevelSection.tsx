"use client";

import InputField from "./InputField";
import type { TankLevels } from "@/lib/types";

const TANK_LABELS: Record<keyof TankLevels, { label: string; excelRef: string }> = {
  wlc_1: { label: "WLC #1", excelRef: "1_Inv!B5" },
  wlc_2: { label: "WLC #2", excelRef: "1_Inv!B6" },
  gl_1: { label: "GL #1", excelRef: "1_Inv!B7" },
  gl_2: { label: "GL #2", excelRef: "1_Inv!B8" },
  dump_tank: { label: "Dump Tank", excelRef: "1_Inv!B9" },
  wbl_1: { label: "WBL #1", excelRef: "1_Inv!B10" },
  wbl_2: { label: "WBL #2", excelRef: "1_Inv!B11" },
  cssc_weak: { label: "CSSC Weak", excelRef: "1_Inv!B12" },
  tank_50pct: { label: "50% Tank", excelRef: "1_Inv!B13" },
  tank_55pct_1: { label: "55% #1", excelRef: "1_Inv!B14" },
  tank_55pct_2: { label: "55% #2", excelRef: "1_Inv!B15" },
  tank_65pct: { label: "65% Tank", excelRef: "1_Inv!B16" },
};

interface Props {
  levels: TankLevels;
  onChange: (key: string, value: number) => void;
}

export default function TankLevelSection({ levels, onChange }: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {(Object.keys(TANK_LABELS) as Array<keyof TankLevels>).map((key) => (
        <InputField
          key={key}
          label={TANK_LABELS[key].label}
          value={levels[key]}
          onChange={(v) => onChange(key, v)}
          unit="ft"
          excelRef={TANK_LABELS[key].excelRef}
          step={0.1}
          min={0}
        />
      ))}
    </div>
  );
}
