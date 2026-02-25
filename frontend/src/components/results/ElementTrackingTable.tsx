"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { UnitOperationRow, LossDetailRow, ChemicalAdditionRow } from "@/lib/types";

interface Props {
  rows: UnitOperationRow[];
  lossTableDetail: LossDetailRow[];
  chemicalAdditions: ChemicalAdditionRow[];
  totalSLossesLbHr: number;
  naLossesElementLbHr: number;
  saltcakeNaLbHr?: number;
  saltcakeSLbHr?: number;
}

export default function ElementTrackingTable({
  rows,
  lossTableDetail,
  chemicalAdditions,
  totalSLossesLbHr,
  naLossesElementLbHr,
  saltcakeNaLbHr = 0,
  saltcakeSLbHr = 0,
}: Props) {
  if (!rows || rows.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Na / S Element Tracking</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs text-muted-foreground">No data available. Run calculation first.</p>
        </CardContent>
      </Card>
    );
  }

  const totalSLossBdt = lossTableDetail?.reduce((sum, r) => sum + r.s_lb_bdt, 0) ?? 0;
  const totalNaLossBdt = lossTableDetail?.reduce((sum, r) => sum + r.na2o_lb_bdt, 0) ?? 0;
  const totalNaLossLbHr = lossTableDetail?.reduce((sum, r) => sum + r.na2o_lb_hr, 0) ?? 0;
  const saltcakeRow = chemicalAdditions?.find((r) => r.source === "Saltcake");
  const externalChemicals = chemicalAdditions?.filter((r) => r.source !== "Saltcake") ?? [];
  const externalNa = externalChemicals.reduce((sum, r) => sum + r.na_lb_hr, 0);
  const externalS = externalChemicals.reduce((sum, r) => sum + r.s_lb_hr, 0);
  const saltcakeNa = saltcakeRow?.na_lb_hr ?? saltcakeNaLbHr;
  const saltcakeS = saltcakeRow?.s_lb_hr ?? saltcakeSLbHr;
  const totalAdditionsNa = externalNa + saltcakeNa;
  const totalAdditionsS = externalS + saltcakeS;
  const netNa = totalAdditionsNa - naLossesElementLbHr;
  const netS = totalAdditionsS - totalSLossesLbHr;

  const TH = "pb-2.5 text-right font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground";
  const TH_L = "pb-2.5 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground";

  return (
    <div className="space-y-4">
      {lossTableDetail && lossTableDetail.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Soda &amp; Sulfur Losses by Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className={TH_L}>Source</th>
                    <th className={TH}>S (lb/hr)</th>
                    <th className={TH}>S (lb/BDT)</th>
                    <th className={TH}>Na₂O (lb/hr)</th>
                    <th className={TH}>Na₂O (lb/BDT)</th>
                  </tr>
                </thead>
                <tbody>
                  {lossTableDetail.map((row, idx) => (
                    <tr key={idx} className="border-b border-white/[0.04]">
                      <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">{row.source}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(row.s_lb_hr)}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white/60">{fmtNum(row.s_lb_bdt, 2)}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(row.na2o_lb_hr)}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white/60">{fmtNum(row.na2o_lb_bdt, 2)}</td>
                    </tr>
                  ))}
                  <tr className="border-t border-white/[0.08]">
                    <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-white">Total Losses</td>
                    <td className="py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{fmtNum(totalSLossesLbHr)}</td>
                    <td className="py-2.5 px-2 text-right font-mono text-xs font-semibold tabular-nums text-cyan/60">{fmtNum(totalSLossBdt, 2)}</td>
                    <td className="py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{fmtNum(totalNaLossLbHr)}</td>
                    <td className="py-2.5 px-2 text-right font-mono text-xs font-semibold tabular-nums text-cyan/60">{fmtNum(totalNaLossBdt, 2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {chemicalAdditions && chemicalAdditions.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Chemical Additions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className={TH_L}>Source</th>
                    <th className={TH}>Na (lb/hr)</th>
                    <th className={TH}>S (lb/hr)</th>
                  </tr>
                </thead>
                <tbody>
                  {chemicalAdditions.map((row, idx) => (
                    <tr key={idx} className="border-b border-white/[0.04]">
                      <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">{row.source}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(row.na_lb_hr)}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(row.s_lb_hr)}</td>
                    </tr>
                  ))}
                  <tr className="border-t border-white/[0.08]">
                    <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-white">Total Additions</td>
                    <td className="py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{fmtNum(totalAdditionsNa)}</td>
                    <td className="py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums text-cyan">{fmtNum(totalAdditionsS)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {lossTableDetail && lossTableDetail.length > 0 && chemicalAdditions && chemicalAdditions.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Net Balance (Additions - Losses)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className={TH_L}></th>
                    <th className={TH}>Na (lb/hr)</th>
                    <th className={TH}>S (lb/hr)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-white/[0.04]">
                    <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">Total Losses</td>
                    <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(naLossesElementLbHr)}</td>
                    <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(totalSLossesLbHr)}</td>
                  </tr>
                  <tr className="border-b border-white/[0.04]">
                    <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">External Chemicals (NaSH + NaOH + CTO)</td>
                    <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(externalNa)}</td>
                    <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(externalS)}</td>
                  </tr>
                  <tr className="border-b border-white/[0.04]">
                    <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">Saltcake Makeup (Na₂SO₄)</td>
                    <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(saltcakeNa)}</td>
                    <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(saltcakeS)}</td>
                  </tr>
                  <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                    <td className="py-2 pr-4 font-mono text-xs font-medium text-white">Total Additions</td>
                    <td className="py-2 px-2 text-right font-mono text-sm tabular-nums font-medium text-white">{fmtNum(totalAdditionsNa)}</td>
                    <td className="py-2 px-2 text-right font-mono text-sm tabular-nums font-medium text-white">{fmtNum(totalAdditionsS)}</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 pr-4 font-mono text-xs font-semibold text-white">Net Balance</td>
                    <td className={cn("py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums", netNa >= 0 ? "text-emerald-400" : "text-red-400")}>
                      {fmtNum(netNa)}
                    </td>
                    <td className={cn("py-2.5 px-2 text-right font-mono text-sm font-semibold tabular-nums", netS >= 0 ? "text-emerald-400" : "text-red-400")}>
                      {fmtNum(netS)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="mt-3 font-mono text-[10px] text-muted-foreground">
              Saltcake (Na₂SO₄) is external makeup added to the RB, distinct from ash recycled (ESP dust recirculation at 7%).
            </p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Na / S Element Tracking by Unit Operation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className={TH_L}>Unit Operation</th>
                  <th className={TH}>Na (lb/hr)</th>
                  <th className={TH}>S (lb/hr)</th>
                  <th className={TH}>Na% d.s.</th>
                  <th className={TH}>S% d.s.</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => {
                  const isCto = row.stage === "CTO Brine";
                  const isSummary = row.stage.startsWith("Mixed") || row.stage.startsWith("Evaporator");
                  return (
                    <tr
                      key={idx}
                      className={cn(
                        "border-b border-white/[0.04]",
                        isCto && "bg-amber-400/[0.04]",
                        isSummary && "font-medium"
                      )}
                    >
                      <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">{row.stage}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(row.na_lb_hr)}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white">{fmtNum(row.s_lb_hr)}</td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white/60">
                        {row.na_pct_ds != null ? fmtNum(row.na_pct_ds, 2) : "--"}
                      </td>
                      <td className="py-2 px-2 text-right font-mono text-xs tabular-nums text-white/60">
                        {row.s_pct_ds != null ? fmtNum(row.s_pct_ds, 2) : "--"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="mt-3 font-mono text-[10px] text-muted-foreground">
            Na% and S% are on dry solids basis (applicable to BL streams only).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
