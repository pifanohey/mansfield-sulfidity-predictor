"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import type { UnitOperationRow, LossDetailRow } from "@/lib/types";

interface Props {
  unitOperations: UnitOperationRow[];
  lossTableDetail: LossDetailRow[];
  semichem_gl_gpm?: number;
  dregs_gpm?: number;
  grits_gpm?: number;
  smelt_flow_gpm?: number;
  ww_flow_gpm?: number;
  shower_flow_gpm?: number;
}

function StageCard({ row }: { row: UnitOperationRow }) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-3 min-w-[180px]">
      <div className="mb-1.5 font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-white truncate">
        {row.stage}
      </div>
      <div className="space-y-0.5 font-mono text-xs tabular-nums">
        {row.tta_na2o_ton_hr != null && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">TTA:</span>
            <span className="text-white">{fmtNum(row.tta_na2o_ton_hr, 2)} t Na₂O/hr</span>
          </div>
        )}
        {row.na2s_na2o_ton_hr != null && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Na₂S:</span>
            <span className="text-white">{fmtNum(row.na2s_na2o_ton_hr, 2)} t Na₂O/hr</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-muted-foreground">Na:</span>
          <span className="text-white">{fmtNum(row.na_lb_hr, 0)} lb/hr</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">S:</span>
          <span className="text-white">{fmtNum(row.s_lb_hr, 0)} lb/hr</span>
        </div>
        {row.flow_gpm != null && (
          <div className="flex justify-between">
            <span className="text-muted-foreground">Flow:</span>
            <span className="text-cyan">{fmtNum(row.flow_gpm, 0)} GPM</span>
          </div>
        )}
      </div>
    </div>
  );
}

function Arrow({ direction }: { direction: "right" | "down" | "left" | "up" }) {
  const arrows = {
    right: "\u2192",
    down: "\u2193",
    left: "\u2190",
    up: "\u2191",
  };
  return (
    <div className="flex items-center justify-center text-xl text-white/20 font-bold px-1">
      {arrows[direction]}
    </div>
  );
}

function LossAnnotation({ area, losses }: { area: string; losses: LossDetailRow[] }) {
  const areaLosses = losses.filter((l) => {
    const areaMap: Record<string, string[]> = {
      Fiberline: ["Pulp Washable Soda", "Pulp Bound Soda", "Pulp Mill Spills"],
      Evaporator: ["Evaps Spill/Boilout/Pond"],
      "Recovery Boiler": ["RB Ash", "RB Stack"],
      Recausticizing: ["Dregs Filter", "Grits", "Weak Wash Overflow", "Recaust Spill"],
      "NCG System": ["NCG"],
    };
    return areaMap[area]?.includes(l.source);
  });
  if (areaLosses.length === 0) return null;

  const totalS = areaLosses.reduce((s, l) => s + l.s_lb_hr, 0);
  const totalNa = areaLosses.reduce((s, l) => s + l.na2o_lb_hr, 0);

  return (
    <div className="text-center mt-1.5 leading-tight font-mono">
      <div className="text-[10px] font-medium text-red-400">{area} Losses</div>
      <div className="text-[10px] text-red-400/70">S: {fmtNum(totalS, 0)} lb/hr</div>
      <div className="text-[10px] text-red-400/70">Na₂O: {fmtNum(totalNa, 0)} lb/hr</div>
    </div>
  );
}

export default function CircuitFlowMap({
  unitOperations,
  lossTableDetail,
  semichem_gl_gpm,
  dregs_gpm,
  grits_gpm,
  smelt_flow_gpm,
  ww_flow_gpm,
  shower_flow_gpm,
}: Props) {
  if (!unitOperations || unitOperations.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle>Kraft Mill Circuit Flow Map</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs text-muted-foreground">No data available. Run calculation first.</p>
        </CardContent>
      </Card>
    );
  }

  const findStage = (prefix: string) =>
    unitOperations.find((r) => r.stage.startsWith(prefix));

  const wlToDigesters = findStage("White Liquor (to");
  const mixedWBL = findStage("Mixed");
  const evaporator = findStage("Evaporator");
  const smelt = findStage("Recovery Boiler");
  const dissolvingTank = findStage("Dissolving Tank");
  const greenLiquor = findStage("Green Liquor");
  const slaker = findStage("Slaker");
  const wlFromSlaker = findStage("White Liquor (from");

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Kraft Mill Circuit Flow Map</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          {/* Top row: Forward path (Digesters → Evap → RB) */}
          <div className="flex items-start gap-1 mb-2">
            <div>
              {wlToDigesters && <StageCard row={wlToDigesters} />}
              <LossAnnotation area="Fiberline" losses={lossTableDetail} />
            </div>
            <Arrow direction="right" />
            <div>
              {mixedWBL && <StageCard row={mixedWBL} />}
              <LossAnnotation area="NCG System" losses={lossTableDetail} />
            </div>
            <Arrow direction="right" />
            <div>
              {evaporator && <StageCard row={evaporator} />}
              <LossAnnotation area="Evaporator" losses={lossTableDetail} />
            </div>
            <Arrow direction="right" />
            <div>
              {smelt && <StageCard row={smelt} />}
              <LossAnnotation area="Recovery Boiler" losses={lossTableDetail} />
            </div>
          </div>

          {/* Connection: RB → DT (down-right) */}
          <div className="flex justify-between items-center px-8 my-1">
            <div className="font-mono text-[10px] text-muted-foreground italic">
              {wlFromSlaker && (
                <span>WL: {fmtNum(wlFromSlaker.flow_gpm, 0)} GPM</span>
              )}
            </div>
            <div className="font-mono text-[10px] text-muted-foreground italic">
              Smelt {"\u2193"}
            </div>
          </div>

          {/* Bottom row: Return path (WL ← Slaker ← GL ← DT) */}
          <div className="flex items-start gap-1">
            <div>
              {wlFromSlaker && <StageCard row={wlFromSlaker} />}
            </div>
            <Arrow direction="left" />
            <div>
              {slaker && <StageCard row={slaker} />}
              <LossAnnotation area="Recausticizing" losses={lossTableDetail} />
            </div>
            <Arrow direction="left" />
            <div>
              {greenLiquor && <StageCard row={greenLiquor} />}
              {(dregs_gpm || grits_gpm || semichem_gl_gpm) && (
                <div className="text-center mt-1.5 leading-tight font-mono">
                  <div className="text-[10px] font-medium text-cyan">GL Subtractions</div>
                  {dregs_gpm && <div className="text-[10px] text-cyan/70">Dregs: {fmtNum(dregs_gpm, 1)} gpm</div>}
                  {grits_gpm && <div className="text-[10px] text-cyan/70">Grits: {fmtNum(grits_gpm, 1)} gpm</div>}
                  {semichem_gl_gpm && <div className="text-[10px] text-cyan/70">Semichem: {fmtNum(semichem_gl_gpm, 0)} gpm</div>}
                </div>
              )}
            </div>
            <Arrow direction="left" />
            <div>
              {dissolvingTank && <StageCard row={dissolvingTank} />}
              {(smelt_flow_gpm || ww_flow_gpm || shower_flow_gpm) && (
                <div className="text-center mt-1.5 leading-tight font-mono">
                  <div className="text-[10px] font-medium text-amber-400">DT Inputs</div>
                  {smelt_flow_gpm && <div className="text-[10px] text-amber-400/70">Smelt: {fmtNum(smelt_flow_gpm, 0)} gpm</div>}
                  {ww_flow_gpm && <div className="text-[10px] text-amber-400/70">WW: {fmtNum(ww_flow_gpm, 0)} gpm</div>}
                  {shower_flow_gpm && <div className="text-[10px] text-amber-400/70">Shower: {fmtNum(shower_flow_gpm, 0)} gpm</div>}
                </div>
              )}
            </div>
          </div>

          {/* BL source detail — dynamic from unit operations */}
          {(() => {
            const knownPrefixes = ["White Liquor", "Mixed", "Evaporator", "Recovery Boiler", "Dissolving Tank", "Green Liquor", "Slaker"];
            const blSources = unitOperations.filter(
              (r) => !knownPrefixes.some((p) => r.stage.startsWith(p))
            );
            if (blSources.length === 0) return null;
            return (
              <div className="mt-4 pt-3 border-t border-white/[0.06]">
                <div className="font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground mb-2">BL Sources:</div>
                <div className="flex gap-2 flex-wrap">
                  {blSources.map((bl) => (
                    <div key={bl.stage} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5 font-mono text-xs min-w-[160px]">
                      <div className="font-medium text-white mb-1 truncate" title={bl.stage}>{bl.stage}</div>
                      <div className="text-muted-foreground">Na: {fmtNum(bl.na_lb_hr, 0)} lb/hr, S: {fmtNum(bl.s_lb_hr, 0)} lb/hr</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      </CardContent>
    </Card>
  );
}
