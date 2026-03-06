"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";

interface FiberlineBLResult {
  id: string;
  name: string;
  organics_lb_hr: number;
  inorganic_solids_lb_hr: number;
}

interface BLCompositionData {
  fiberline_bl: FiberlineBLResult[];
  cto_na_lb_hr: number;
  cto_s_lbs_hr: number;
  wbl_total_flow_lb_hr: number;
  wbl_tds_pct: number;
  wbl_na_pct_ds: number;
  wbl_s_pct_ds: number;
  sbl_flow_lb_hr: number;
  sbl_tds_pct: number;
  sbl_na_element_lb_hr: number;
  sbl_s_element_lb_hr: number;
  evaporator_water_removed_lb_hr: number;
  rb_virgin_solids_lbs_hr: number;
  rb_ash_solids_lbs_hr: number;
  bl_na_pct_used: number;
  bl_s_pct_used: number;
  rb_na_pct_mixed?: number;
  rb_s_pct_mixed?: number;
  unit_operations?: Array<{
    stage: string;
    na_lb_hr: number;
    s_lb_hr: number;
    na_pct_ds: number | null;
    s_pct_ds: number | null;
  }>;
}

interface Props {
  data: BLCompositionData;
}

const BOX_COLORS = {
  green:  { border: "border-emerald-500/30", bg: "bg-emerald-500/[0.06]", title: "text-emerald-400 bg-emerald-500/10", divider: "border-emerald-500/20" },
  blue:   { border: "border-cyan/30",        bg: "bg-cyan/[0.06]",        title: "text-cyan bg-cyan/10",              divider: "border-cyan/20" },
  orange: { border: "border-amber-400/30",   bg: "bg-amber-400/[0.06]",   title: "text-amber-400 bg-amber-400/10",    divider: "border-amber-400/20" },
  purple: { border: "border-purple-400/30",  bg: "bg-purple-400/[0.06]",  title: "text-purple-400 bg-purple-400/10",  divider: "border-purple-400/20" },
  red:    { border: "border-red-400/30",     bg: "bg-red-400/[0.06]",     title: "text-red-400 bg-red-400/10",        divider: "border-red-400/20" },
  slate:  { border: "border-white/[0.1]",    bg: "bg-white/[0.03]",       title: "text-white bg-white/[0.06]",        divider: "border-white/[0.08]" },
} as const;

type BoxColor = keyof typeof BOX_COLORS;

function ProcessBox({
  title,
  color,
  children,
}: {
  title: string;
  color: BoxColor;
  children: React.ReactNode;
}) {
  const c = BOX_COLORS[color];
  return (
    <div className={`rounded-lg border ${c.border} ${c.bg} overflow-hidden`}>
      <div className={`px-3 py-1.5 font-mono text-[10px] font-bold uppercase tracking-[0.15em] ${c.title}`}>
        {title}
      </div>
      <div className="p-3 space-y-1">
        {children}
      </div>
    </div>
  );
}

function DataRow({ label, value, unit, highlight }: {
  label: string;
  value: number | string;
  unit?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`flex justify-between gap-2 font-mono ${highlight ? 'font-semibold text-white' : 'text-muted-foreground'}`}>
      <span className="text-[11px]">{label}:</span>
      <span className="text-[11px] tabular-nums">
        {typeof value === 'number' ? fmtNum(value, value > 1000 ? 0 : 2) : value}
        {unit && <span className="text-white/30 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

function FlowArrow({ direction, label }: { direction: "down" | "right"; label?: string }) {
  return (
    <div className={`flex ${direction === 'down' ? 'flex-col' : 'flex-row'} items-center justify-center ${direction === 'down' ? 'py-1' : 'px-2'}`}>
      <div className="text-2xl text-white/20">
        {direction === 'down' ? '\u2193' : '\u2192'}
      </div>
      {label && (
        <span className="font-mono text-[10px] text-muted-foreground italic whitespace-nowrap">{label}</span>
      )}
    </div>
  );
}

function MergeArrows() {
  return (
    <div className="flex items-center justify-center py-1">
      <div className="flex items-end gap-8 text-lg text-white/20">
        <div>{'\u2198'}</div>
        <div>{'\u2193'}</div>
        <div>{'\u2199'}</div>
      </div>
    </div>
  );
}

export default function BLCompositionChart({ data }: Props) {
  const fiberlines = data.fiberline_bl ?? [];
  const ops = data.unit_operations || [];
  const mixedWBL = ops.find(o => o.stage.includes('Mixed'));
  const rbSmelt = ops.find(o => o.stage.includes('Recovery'));

  const FL_COLORS: BoxColor[] = ["green", "blue", "purple", "red"];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Black Liquor Composition Flow</CardTitle>
        <p className="font-mono text-[10px] text-muted-foreground">
          Tracking BL composition from fiberlines through evaporator to recovery boiler
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <div className="min-w-[700px]">

            {/* Row 1: Fiberlines + CTO (sources) */}
            <div className={`grid gap-4 mb-2`} style={{ gridTemplateColumns: `repeat(${fiberlines.length + 1}, minmax(0, 1fr))` }}>
              {fiberlines.map((fl, i) => {
                const total = fl.organics_lb_hr + fl.inorganic_solids_lb_hr;
                const blOp = ops.find(o => o.stage.includes(fl.name));
                const color = FL_COLORS[i % FL_COLORS.length];
                return (
                  <ProcessBox key={fl.id} title={fl.name} color={color}>
                    <DataRow label="Organics" value={fl.organics_lb_hr} unit="lb/hr" />
                    <DataRow label="Inorganics" value={fl.inorganic_solids_lb_hr} unit="lb/hr" />
                    <div className="border-t border-white/10 my-1" />
                    <DataRow label="Total Solids" value={total} unit="lb/hr" highlight />
                    {blOp && (
                      <>
                        <DataRow label="Na element" value={blOp.na_lb_hr} unit="lb/hr" />
                        <DataRow label="S element" value={blOp.s_lb_hr} unit="lb/hr" />
                        {blOp.na_pct_ds != null && <DataRow label="Na % d.s." value={`${blOp.na_pct_ds.toFixed(2)}%`} />}
                        {blOp.s_pct_ds != null && <DataRow label="S % d.s." value={`${blOp.s_pct_ds.toFixed(2)}%`} />}
                      </>
                    )}
                  </ProcessBox>
                );
              })}

              <ProcessBox title="CTO Brine" color="orange">
                <DataRow label="Na element" value={data.cto_na_lb_hr} unit="lb/hr" />
                <DataRow label="S element" value={data.cto_s_lbs_hr} unit="lb/hr" />
                <div className="border-t border-amber-400/20 my-1" />
                <div className="font-mono text-[10px] text-amber-400/60 italic">
                  Enters as Na₂SO₄ brine
                </div>
              </ProcessBox>
            </div>

            <MergeArrows />

            {/* Row 2: WBL Mixer */}
            <div className="flex justify-center mb-2">
              <div className="w-80">
                <ProcessBox title="WBL Mixer" color="purple">
                  <DataRow label="Total Flow" value={data.wbl_total_flow_lb_hr} unit="lb/hr" highlight />
                  <DataRow label="TDS" value={`${data.wbl_tds_pct.toFixed(2)}%`} />
                  <div className="border-t border-purple-400/20 my-1" />
                  {mixedWBL && (
                    <>
                      <DataRow label="Na element" value={mixedWBL.na_lb_hr} unit="lb/hr" />
                      <DataRow label="S element" value={mixedWBL.s_lb_hr} unit="lb/hr" />
                    </>
                  )}
                  <DataRow label="Na % d.s." value={`${data.wbl_na_pct_ds.toFixed(2)}%`} />
                  <DataRow label="S % d.s." value={`${data.wbl_s_pct_ds.toFixed(2)}%`} />
                </ProcessBox>
              </div>
            </div>

            <FlowArrow direction="down" label={`Water: ${fmtNum(data.evaporator_water_removed_lb_hr, 0)} lb/hr removed`} />

            {/* Row 3: Evaporator */}
            <div className="flex justify-center mb-2">
              <div className="w-80">
                <ProcessBox title="Evaporator \u2192 SBL" color="red">
                  <DataRow label="SBL Flow" value={data.sbl_flow_lb_hr} unit="lb/hr" highlight />
                  <DataRow label="TDS" value={`${data.sbl_tds_pct.toFixed(2)}%`} highlight />
                  <div className="border-t border-red-400/20 my-1" />
                  <DataRow label="Na element" value={data.sbl_na_element_lb_hr} unit="lb/hr" />
                  <DataRow label="S element" value={data.sbl_s_element_lb_hr} unit="lb/hr" />
                  <DataRow label="Na % d.s." value={`${data.wbl_na_pct_ds.toFixed(2)}%`} />
                  <DataRow label="S % d.s." value={`${data.wbl_s_pct_ds.toFixed(2)}%`} />
                  <div className="font-mono text-[10px] text-red-400/60 italic mt-1">
                    Na% and S% unchanged (only water removed)
                  </div>
                </ProcessBox>
              </div>
            </div>

            <FlowArrow direction="down" label="To Recovery Boiler" />

            {/* Row 4: Recovery Boiler */}
            <div className="flex justify-center">
              <div className="w-96">
                <ProcessBox title="Recovery Boiler Feed" color="slate">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="font-mono text-[10px] font-medium text-white mb-1">Virgin BL Solids</div>
                      <DataRow label="Mass" value={data.rb_virgin_solids_lbs_hr} unit="lb/hr" />
                    </div>
                    <div>
                      <div className="font-mono text-[10px] font-medium text-white mb-1">Ash Recycled</div>
                      <DataRow label="Mass" value={data.rb_ash_solids_lbs_hr} unit="lb/hr" />
                    </div>
                  </div>
                  <div className="border-t border-white/[0.08] my-2" />
                  <div className="font-mono text-[10px] font-medium text-white mb-1">Virgin BL (from forward leg)</div>
                  <div className="grid grid-cols-2 gap-2">
                    <DataRow label="Na % d.s." value={`${data.bl_na_pct_used.toFixed(2)}%`} />
                    <DataRow label="S % d.s." value={`${data.bl_s_pct_used.toFixed(2)}%`} />
                  </div>
                  {data.rb_na_pct_mixed !== undefined && data.rb_na_pct_mixed > 0 && (
                    <>
                      <div className="font-mono text-[10px] font-medium text-white mt-2 mb-1">Mixed BL (Virgin + Ash)</div>
                      <div className="grid grid-cols-2 gap-2">
                        <DataRow label="Na % d.s." value={`${data.rb_na_pct_mixed.toFixed(2)}%`} highlight />
                        <DataRow label="S % d.s." value={`${(data.rb_s_pct_mixed ?? 0).toFixed(2)}%`} highlight />
                      </div>
                    </>
                  )}
                  {rbSmelt && (
                    <>
                      <div className="border-t border-white/[0.08] my-2" />
                      <div className="font-mono text-[10px] font-medium text-white mb-1">Smelt Output</div>
                      <DataRow label="Na to smelt" value={rbSmelt.na_lb_hr} unit="lb/hr" />
                      <DataRow label="S to smelt" value={rbSmelt.s_lb_hr} unit="lb/hr" />
                    </>
                  )}
                </ProcessBox>
              </div>
            </div>

            {/* Mass Balance Summary */}
            <div className="mt-6 pt-4 border-t border-white/[0.06]">
              <div className="font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-muted-foreground mb-3">Mass Balance Summary</div>
              <div className={`grid grid-cols-2 md:grid-cols-${Math.min(fiberlines.length + 2, 6)} gap-3`}>
                {fiberlines.map((fl, i) => {
                  const total = fl.organics_lb_hr + fl.inorganic_solids_lb_hr;
                  const color = FL_COLORS[i % FL_COLORS.length];
                  const colorMap: Record<BoxColor, { border: string; bg: string; text: string; dim: string }> = {
                    green:  { border: "border-emerald-500/20", bg: "bg-emerald-500/[0.06]", text: "text-emerald-400", dim: "text-emerald-400/60" },
                    blue:   { border: "border-cyan/20",        bg: "bg-cyan/[0.06]",        text: "text-cyan",        dim: "text-cyan/60" },
                    purple: { border: "border-purple-400/20",  bg: "bg-purple-400/[0.06]",  text: "text-purple-400",  dim: "text-purple-400/60" },
                    red:    { border: "border-red-400/20",     bg: "bg-red-400/[0.06]",     text: "text-red-400",     dim: "text-red-400/60" },
                    orange: { border: "border-amber-400/20",   bg: "bg-amber-400/[0.06]",   text: "text-amber-400",   dim: "text-amber-400/60" },
                    slate:  { border: "border-white/[0.1]",    bg: "bg-white/[0.03]",       text: "text-white",       dim: "text-white/40" },
                  };
                  const c = colorMap[color];
                  return (
                    <div key={fl.id} className={`rounded-lg border ${c.border} ${c.bg} p-3 text-center`}>
                      <div className={`font-mono text-lg font-bold ${c.text}`}>{fmtNum(total, 0)}</div>
                      <div className={`font-mono text-[10px] ${c.dim}`}>{fl.name} Solids (lb/hr)</div>
                    </div>
                  );
                })}
                <div className="rounded-lg border border-amber-400/20 bg-amber-400/[0.06] p-3 text-center">
                  <div className="font-mono text-lg font-bold text-amber-400">{fmtNum(data.cto_na_lb_hr + data.cto_s_lbs_hr, 0)}</div>
                  <div className="font-mono text-[10px] text-amber-400/60">CTO Elements (lb/hr)</div>
                </div>
                <div className="rounded-lg border border-red-400/20 bg-red-400/[0.06] p-3 text-center">
                  <div className="font-mono text-lg font-bold text-red-400">{fmtNum(data.evaporator_water_removed_lb_hr, 0)}</div>
                  <div className="font-mono text-[10px] text-red-400/60">Water Removed (lb/hr)</div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </CardContent>
    </Card>
  );
}
