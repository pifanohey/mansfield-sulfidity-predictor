"use client";

import type { LossTable, LossTableSource } from "@/lib/types";

const LOSS_ROWS: Array<{
  key: keyof LossTable;
  label: string;
  area: string;
}> = [
  { key: "pulp_washable_soda", label: "Pulp Washable Soda", area: "Fiberline" },
  { key: "pulp_bound_soda", label: "Pulp Bound Soda", area: "Fiberline" },
  { key: "pulp_mill_spills", label: "Pulp Mill Spills", area: "Fiberline" },
  { key: "evap_spill", label: "Evaps Spill/Boilout/Pond", area: "Evaporator" },
  { key: "rb_ash", label: "RB Ash", area: "Recovery Boiler" },
  { key: "rb_stack", label: "RB Stack", area: "Recovery Boiler" },
  { key: "dregs_filter", label: "Dregs Filter", area: "Recausticizing" },
  { key: "grits", label: "Grits", area: "Recausticizing" },
  { key: "weak_wash_overflow", label: "Weak Wash Overflow", area: "Recausticizing" },
  { key: "ncg", label: "NCG", area: "NCG System" },
  { key: "recaust_spill", label: "Recaust Spill", area: "Recausticizing" },
  { key: "rb_dump_tank", label: "RB Dump Tank", area: "Recovery Boiler" },
  { key: "kiln_scrubber", label: "Kiln Scrubber", area: "Lime Kiln" },
  { key: "truck_out_gl", label: "Truck Out Green Liquor", area: "Other" },
  { key: "unaccounted", label: "Unaccounted", area: "Other" },
];

interface Props {
  lossTable: LossTable;
  onChange: (sourceKey: string, field: string, value: number) => void;
}

export default function LossTableSection({ lossTable, onChange }: Props) {
  const totalS = LOSS_ROWS.reduce((sum, r) => sum + (lossTable[r.key]?.s_lb_bdt ?? 0), 0);
  const totalNa = LOSS_ROWS.reduce((sum, r) => sum + (lossTable[r.key]?.na_lb_bdt ?? 0), 0);

  let lastArea = "";

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/[0.06]">
            <th className="pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground">Source</th>
            <th className="pb-2.5 px-2 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground w-28">S (lb/BDT)</th>
            <th className="pb-2.5 px-2 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground w-28">Na₂O (lb/BDT)</th>
            <th className="pb-2.5 px-2 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground w-32">Area</th>
          </tr>
        </thead>
        <tbody>
          {LOSS_ROWS.map((row) => {
            const src: LossTableSource = lossTable[row.key] ?? { s_lb_bdt: 0, na_lb_bdt: 0 };
            const showArea = row.area !== lastArea;
            lastArea = row.area;
            return (
              <tr key={row.key} className="border-b border-white/[0.04]">
                <td className="py-1.5 pr-4 font-mono text-xs text-muted-foreground">{row.label}</td>
                <td className="py-1.5 px-1">
                  <input
                    type="number"
                    step={0.1}
                    min={0}
                    value={src.s_lb_bdt}
                    onChange={(e) =>
                      onChange(row.key, "s_lb_bdt", parseFloat(e.target.value) || 0)
                    }
                    className="w-full rounded-md border border-white/[0.06] bg-white/[0.03] px-2 py-1 text-right font-mono text-sm tabular-nums text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
                  />
                </td>
                <td className="py-1.5 px-1">
                  <input
                    type="number"
                    step={0.1}
                    min={0}
                    value={src.na_lb_bdt}
                    onChange={(e) =>
                      onChange(row.key, "na_lb_bdt", parseFloat(e.target.value) || 0)
                    }
                    className="w-full rounded-md border border-white/[0.06] bg-white/[0.03] px-2 py-1 text-right font-mono text-sm tabular-nums text-white focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/50"
                  />
                </td>
                <td className="py-1.5 px-2 font-mono text-[10px] text-muted-foreground">
                  {showArea ? row.area : ""}
                </td>
              </tr>
            );
          })}
          <tr className="border-t border-white/[0.08]">
            <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-white">Total</td>
            <td className="py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{totalS.toFixed(1)}</td>
            <td className="py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{totalNa.toFixed(1)}</td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
