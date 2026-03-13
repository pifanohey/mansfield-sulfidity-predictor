"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum } from "@/lib/format";
import type { CalculationResponse } from "@/lib/types";

interface Props {
  results: CalculationResponse;
  ctoSLbHr: number;
  blSPctLab: number;
  blSPctUsed: number;
  wwFlowGpm: number;
  showerFlowGpm: number;
}

const f1 = (v: number) => fmtNum(v, 1);
const f2 = (v: number) => fmtNum(v, 2);

/* ── Reusable sub-components matching CircuitFlowMap style ── */

function FlowCard({ title, children, accent }: {
  title: string;
  children: React.ReactNode;
  accent?: "cyan" | "amber" | "pink" | "green" | "purple" | "orange" | "red";
}) {
  const borderColor = accent
    ? { cyan: "border-cyan/20", amber: "border-amber-400/20", pink: "border-pink-400/20",
        green: "border-emerald-400/20", purple: "border-violet-400/20",
        orange: "border-orange-400/20", red: "border-red-400/20" }[accent]
    : "border-white/[0.08]";
  return (
    <div className={`rounded-lg border ${borderColor} bg-white/[0.03] p-3 min-w-[170px]`}>
      <div className="mb-1.5 font-mono text-[10px] font-bold uppercase tracking-[0.15em] text-white truncate">
        {title}
      </div>
      <div className="space-y-0.5 font-mono text-xs tabular-nums">
        {children}
      </div>
    </div>
  );
}

function InputCard({ title, children, accent }: {
  title: string;
  children: React.ReactNode;
  accent?: "cyan" | "amber" | "pink" | "green" | "purple" | "orange" | "red";
}) {
  const borderColor = accent
    ? { cyan: "border-cyan/20", amber: "border-amber-400/20", pink: "border-pink-400/20",
        green: "border-emerald-400/20", purple: "border-violet-400/20",
        orange: "border-orange-400/20", red: "border-red-400/20" }[accent]
    : "border-white/[0.08]";
  return (
    <div className={`rounded-lg border ${borderColor} bg-white/[0.03] p-2.5 min-w-[140px]`}>
      <div className="mb-1 font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-white truncate">
        {title}
      </div>
      <div className="space-y-0.5 font-mono text-[11px] tabular-nums">
        {children}
      </div>
    </div>
  );
}

function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <span className={color ?? "text-white"}>{value}</span>
    </div>
  );
}

function SmallRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className={color ?? "text-white"}>{value}</span>
    </div>
  );
}

function Arrow({ direction }: { direction: "right" | "down" | "left" | "up" }) {
  const arrows = { right: "\u2192", down: "\u2193", left: "\u2190", up: "\u2191" };
  return (
    <div className="flex items-center justify-center text-xl text-white/20 font-bold px-1">
      {arrows[direction]}
    </div>
  );
}

export default function RecaustFlowDiagram({
  results, ctoSLbHr, blSPctLab, blSPctUsed,
  wwFlowGpm, showerFlowGpm,
}: Props) {
  const im = results.intermediate;
  const mk = results.makeup;
  const sf = results.sulfidity;

  const smeltGpm       = im.smelt_flow_gpm ?? 0;
  const wwSolved       = results.ww_flow_solved_gpm ?? wwFlowGpm;
  const filtGpm        = results.dregs_filtrate_gpm ?? 0;
  const steamGpm       = results.dt_steam_evaporated_gpm ?? 0;
  const steamLbHr      = results.dt_steam_evaporated_lb_hr ?? 0;
  const dtGlOut        = im.dissolving_tank_flow ?? 0;
  const glTTA          = im.gl_tta_g_L ?? 0;
  const glNa2S         = im.gl_na2s_g_L ?? 0;
  const glSulfPct      = im.gl_sulfidity_pct ?? ((im.gl_sulfidity ?? 0) * 100);
  const dregsUF        = im.dregs_underflow_gpm ?? 0;
  const semiGL         = im.semichem_gl_gpm ?? 0;
  const gritsGpm       = im.grits_entrained_gpm ?? 0;
  const glToSlaker     = im.gl_flow_to_slaker_gpm ?? 0;
  const yieldFactor    = im.yield_factor ?? 0;
  const wlFromSlaker   = im.wl_flow_from_slaker_gpm ?? 0;
  const wlTTAslaker    = im.wl_tta_slaker_g_L ?? 0;
  const wlNaOHslaker   = im.wl_naoh_slaker_g_L ?? 0;
  const wlNa2Sslaker   = im.wl_na2s_slaker_g_L ?? 0;
  const mudUF          = im.wlc_underflow_gpm ?? 0;
  const wlcOverflow    = im.wlc_overflow_gpm ?? 0;
  const totalDemand    = im.total_wl_demand_gpm ?? 0;

  const fiberlineIds: string[] = (im.fiberline_ids as unknown as string[]) ?? [];
  const flDemands: Array<{ id: string; gpm: number }> = fiberlineIds.map((id) => ({
    id,
    gpm: (im[`${id}_wl_demand_gpm`] as number) ?? 0,
  }));
  if (flDemands.length === 0) {
    for (const key of Object.keys(im)) {
      const m = key.match(/^(.+)_wl_demand_gpm$/);
      if (m) {
        const val = (im[key] as number) ?? 0;
        if (val > 0) flDemands.push({ id: m[1], gpm: val });
      }
    }
  }

  const finalTTA       = im.final_wl_tta_g_L ?? 0;
  const finalNa2S      = im.final_wl_na2s_g_L ?? 0;
  const finalEA        = im.final_wl_ea_g_L ?? 0;
  const finalAA        = im.final_wl_aa_g_L ?? 0;
  const finalNaOH      = im.final_wl_naoh_g_L ?? 0;
  const finalNa2CO3    = im.final_wl_na2co3_g_L ?? 0;
  const nashDry        = mk.nash_dry_lb_hr;
  const naohDry        = mk.naoh_dry_lb_hr;
  const nashGpm        = mk.nash_gpm;
  const naohGpm        = mk.naoh_gpm;
  const smeltSulf      = sf.smelt_pct;
  const finalSulf      = sf.final_pct;
  const smeltTTA       = results.recovery_boiler.tta_lb_hr;

  const totalIn        = smeltGpm + wwSolved + showerFlowGpm + filtGpm;
  const totalRemoved   = dregsUF + semiGL;
  const surplus        = wlcOverflow - totalDemand;
  const surplusPct     = totalDemand > 0 ? (surplus / wlcOverflow) * 100 : 0;
  const demandBarPct   = wlcOverflow > 0 ? (totalDemand / wlcOverflow) * 100 : 0;
  const surplusBarPct  = wlcOverflow > 0 ? (surplus / wlcOverflow) * 100 : 0;

  const makeupAfterWlc = !!(im.makeup_after_wlc);
  const wlcCleanOverflow = im.wlc_clean_overflow_gpm ?? 0;
  const wlcCleanTTA      = im.wlc_clean_tta_g_L ?? 0;
  const wlcCleanSulf     = im.wlc_clean_sulfidity_pct ?? 0;

  return (
    <Card className="mt-6">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Recausticizing Circuit — Flow Diagram</CardTitle>
        <p className="text-xs text-muted-foreground">
          Full circuit from RB smelt through DT, GL clarifier, slaker, WLC to final WL
          {makeupAfterWlc && " — Makeup added after WLC overflow"}
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">

          {/* ═══ SECTION 1: DT INPUT STREAMS ═══ */}
          <div className="font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-amber-400 mb-2">
            Inputs
          </div>
          <div className="flex items-start gap-2 flex-wrap mb-1">
            {/* CTO / BL Feed */}
            <InputCard title="CTO S → BL Feed" accent="orange">
              <SmallRow label="CTO S:" value={`${f1(ctoSLbHr)} lb/hr`} />
              <SmallRow label="BL S% (lab):" value={`${f2(blSPctLab)}%`} />
              <SmallRow label="Adj BL S%:" value={`${f2(blSPctUsed)}%`} color="text-emerald-400" />
              <div className="text-[9px] text-muted-foreground text-center pt-0.5">
                {Math.abs(blSPctUsed - blSPctLab) < 0.005
                  ? "No CTO delta"
                  : `\u0394 ${(blSPctUsed - blSPctLab) >= 0 ? "+" : ""}${(blSPctUsed - blSPctLab).toFixed(3)}%`}
              </div>
            </InputCard>

            {/* Recovery Boiler Smelt */}
            <InputCard title="Recovery Boiler Smelt" accent="red">
              <SmallRow label="Flow:" value={`${f1(smeltGpm)} gpm`} color="text-cyan" />
              <SmallRow label="Sulfidity:" value={`${f2(smeltSulf)}%`} color="text-pink-400" />
              <SmallRow label="TTA:" value={`${f1(smeltTTA)} lb Na\u2082O/hr`} />
            </InputCard>

            {/* Weak Wash (solved) */}
            <InputCard title="Weak Wash (solved)" accent="green">
              <SmallRow label="Flow:" value={`${f1(wwSolved)} gpm`} color="text-cyan" />
              <div className="text-[9px] text-muted-foreground">
                Analytical solve for GL TTA target
              </div>
            </InputCard>

            {/* Shower Water */}
            <InputCard title="Shower Water" accent="purple">
              <SmallRow label="Flow:" value={`${f1(showerFlowGpm)} gpm`} color="text-cyan" />
            </InputCard>

            {/* Dregs Filtrate Return */}
            <InputCard title="Dregs Filtrate (return)" accent="amber">
              <SmallRow label="Flow:" value={`${f1(filtGpm)} gpm`} color="text-cyan" />
            </InputCard>
          </div>

          {/* Converging arrow */}
          <div className="flex items-center gap-2 my-1 ml-4">
            <div className="text-lg text-white/20 font-bold">{"\u2193"}</div>
            <div className="font-mono text-[10px] text-muted-foreground italic">
              All streams feed into Dissolving Tank ({f1(totalIn)} gpm total)
            </div>
          </div>

          {/* ═══ SECTION 2: DT → GLC → SLAKER ═══ */}
          <div className="flex items-start gap-1 mb-1">
            {/* Dissolving Tank */}
            <div>
              <FlowCard title="Dissolving Tank" accent="cyan">
                <Row label="Total In:" value={`${f1(totalIn)} gpm`} />
                <Row label="Steam:" value={`-${f1(steamGpm)} gpm (${f1(steamLbHr)} lb/hr)`} color="text-red-400" />
                <Row label="GL Out:" value={`${f1(dtGlOut)} GPM`} color="text-cyan" />
                <Row label="TTA:" value={`${f1(glTTA)} g/L`} color="text-emerald-400" />
                <Row label="Sulfidity:" value={`${f1(glSulfPct)}%`} color="text-pink-400" />
              </FlowCard>
            </div>

            <Arrow direction="right" />

            {/* GL Clarifier */}
            <div>
              <FlowCard title="Green Liquor Clarifier" accent="pink">
                <Row label="In:" value={`${f1(dtGlOut)} gpm`} />
                <Row label="TTA:" value={`${f1(glTTA)} g/L`} color="text-emerald-400" />
                <Row label="Na\u2082S:" value={`${f1(glNa2S)} g/L`} />
                <Row label="Sulfidity:" value={`${f1(glSulfPct)}%`} color="text-pink-400" />
              </FlowCard>
              <div className="text-center mt-1.5 leading-tight font-mono">
                <div className="text-[10px] font-medium text-violet-400">Subtractions</div>
                <div className="text-[10px] text-violet-400/70">Dregs UF: -{f1(dregsUF)} gpm</div>
                {semiGL > 0 && (
                  <div className="text-[10px] text-violet-400/70">Semichem GL: -{f1(semiGL)} gpm</div>
                )}
                <div className="text-[10px] text-violet-400/70">Total removed: -{f1(totalRemoved)} gpm</div>
              </div>
            </div>

            <Arrow direction="right" />

            {/* Slaker */}
            <div>
              <FlowCard title="Slaker / Causticizers" accent="amber">
                <Row label="GL In:" value={`${f1(glToSlaker)} gpm`} />
                <Row label="Yield:" value={fmtNum(yieldFactor, 3)} color="text-amber-400" />
                <Row label="WL Out:" value={`${f1(wlFromSlaker)} gpm`} />
                <Row label="TTA:" value={`${f1(wlTTAslaker)} g/L`} color="text-emerald-400" />
                <Row label="NaOH:" value={`${f1(wlNaOHslaker)} g/L`} />
                <Row label="Na\u2082S:" value={`${f1(wlNa2Sslaker)} g/L`} />
              </FlowCard>
            </div>
          </div>

          {/* ═══ TRANSITION: Slaker → WLC path ═══ */}
          <div className="flex items-center gap-2 my-1 ml-4">
            <div className="text-lg text-white/20 font-bold">{"\u2193"}</div>
            <div className="font-mono text-[10px] text-muted-foreground italic">
              WL from slaker: {f1(wlFromSlaker)} GPM
            </div>
          </div>

          {/* ═══ SECTION 3: WLC → MAKEUP → FINAL WL ═══ */}
          <div className="flex items-start gap-1">
            {makeupAfterWlc ? (
              <>
                {/* Mansfield flow: WLC (clean) → Makeup Addition → Final WL */}
                <div>
                  <FlowCard title="WL Clarifier" accent="cyan">
                    <div className="text-[10px] text-muted-foreground text-center mb-0.5">(no makeup added)</div>
                    <Row label="-Grits:" value={`-${f1(gritsGpm)} gpm`} color="text-violet-400" />
                    <Row label="-Mud UF:" value={`-${f1(mudUF)} gpm`} color="text-red-400" />
                    <div className="border-t border-white/[0.06] mt-1 pt-1">
                      <Row label="Overflow:" value={`${f1(wlcCleanOverflow)} GPM`} color="text-cyan" />
                      <Row label="TTA:" value={`${f1(wlcCleanTTA)} g/L`} color="text-emerald-400" />
                      <Row label="Sulfidity:" value={`${f2(wlcCleanSulf)}%`} color="text-pink-400" />
                    </div>
                  </FlowCard>
                </div>

                <Arrow direction="right" />

                <div>
                  <FlowCard title="Makeup Addition" accent="amber">
                    <div className="text-[10px] text-muted-foreground text-center mb-0.5">(post-WLC injection)</div>
                    <Row label="+NaSH:" value={`${f1(nashGpm)} gpm (${f1(nashDry)} lb/hr)`} color="text-amber-400" />
                    <Row label="+NaOH:" value={`${f1(naohGpm)} gpm (${f1(naohDry)} lb/hr)`} color="text-amber-400" />
                    <div className="border-t border-white/[0.06] mt-1 pt-1">
                      <Row label="WL Out:" value={`${f1(wlcOverflow)} GPM`} color="text-cyan" />
                      <Row label="Sulfidity:" value={`${f2(finalSulf)}%`} color="text-pink-400" />
                    </div>
                  </FlowCard>
                </div>

                <Arrow direction="right" />

                <div>
                  <FlowCard title="Final WL to Digesters" accent="green">
                    <Row label="EA:" value={`${f2(finalEA)} g/L`} color="text-cyan" />
                    <Row label="TTA:" value={`${f1(finalTTA)} g/L`} color="text-emerald-400" />
                    <Row label="AA:" value={`${f1(finalAA)} g/L`} />
                    <Row label="NaOH:" value={`${f1(finalNaOH)} g/L`} />
                    <Row label="Na\u2082CO\u2083:" value={`${f1(finalNa2CO3)} g/L`} />
                    <Row label="Sulfidity:" value={`${f2(finalSulf)}%`} color="text-pink-400" />
                  </FlowCard>
                </div>
              </>
            ) : (
              <>
                {/* Pine Hill flow: WLC + Makeup → Final WL */}
                <div>
                  <FlowCard title="WL Clarifier + Makeup" accent="cyan">
                    <Row label="-Grits:" value={`-${f1(gritsGpm)} gpm`} color="text-violet-400" />
                    <Row label="+NaSH:" value={`${f1(nashGpm)} gpm (${f1(nashDry)} lb/hr)`} />
                    <Row label="+NaOH:" value={`${f1(naohGpm)} gpm (${f1(naohDry)} lb/hr)`} />
                    <Row label="-Mud UF:" value={`-${f1(mudUF)} gpm`} color="text-red-400" />
                    <div className="border-t border-white/[0.06] mt-1 pt-1">
                      <Row label="Overflow:" value={`~${f1(wlcOverflow)} GPM`} color="text-cyan" />
                      <Row label="Sulfidity:" value={`~${f2(finalSulf)}%`} color="text-pink-400" />
                    </div>
                  </FlowCard>
                </div>

                <Arrow direction="right" />

                <div>
                  <FlowCard title="Final WL to Digesters" accent="green">
                    <Row label="EA:" value={`${f2(finalEA)} g/L`} color="text-cyan" />
                    <Row label="TTA:" value={`${f1(finalTTA)} g/L`} color="text-emerald-400" />
                    <Row label="AA:" value={`${f1(finalAA)} g/L`} />
                    <Row label="NaOH:" value={`${f1(finalNaOH)} g/L`} />
                    <Row label="Na\u2082CO\u2083:" value={`${f1(finalNa2CO3)} g/L`} />
                    <Row label="Sulfidity:" value={`${f2(finalSulf)}%`} color="text-pink-400" />
                  </FlowCard>
                </div>
              </>
            )}
          </div>

          {/* ═══ VOLUME BALANCE ═══ */}
          <div className="mt-4 pt-3 border-t border-white/[0.06]">
            <div className="font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-amber-400 mb-2">Volume Balance Check</div>
            <div className="space-y-0.5 font-mono text-[11px] text-muted-foreground">
              <div>
                Smelt ({f1(smeltGpm)}) + WW ({f1(wwSolved)}) + Shower ({f1(showerFlowGpm)}) + Filtrate ({f1(filtGpm)}) = {f1(totalIn)} gpm in
              </div>
              <div>
                GL Out ({f1(dtGlOut)}) + Steam ({f1(steamGpm)}) = {f1(dtGlOut + steamGpm)} gpm out
              </div>
              <div>
                GL ({f1(dtGlOut)}) - Dregs ({f1(dregsUF)}) - Semi GL ({f1(semiGL)}) ={" "}
                <span className="text-amber-400 font-semibold">{f1(glToSlaker)} gpm to slaker</span>
              </div>
              {makeupAfterWlc ? (
                <div>
                  Slaker ({f1(wlFromSlaker)}) - Grits ({f1(gritsGpm)}) - Mud ({f1(mudUF)}) = {f1(wlcCleanOverflow)} WLC overflow + Makeup ({f1(nashGpm + naohGpm)}) ={" "}
                  <span className="text-amber-400 font-semibold">~{f1(wlcOverflow)} gpm WL</span>
                </div>
              ) : (
                <div>
                  Slaker ({f1(wlFromSlaker)}) - Grits ({f1(gritsGpm)}) + Makeup ({f1(nashGpm + naohGpm)}) - Mud ({f1(mudUF)}) ={" "}
                  <span className="text-amber-400 font-semibold">~{f1(wlcOverflow)} gpm WL overflow</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ═══ WL BALANCE BARS ═══ */}
        <div className="mx-auto mt-4 max-w-[700px]">
          <h4 className="mb-3 text-center font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">WL Produced vs WL Demanded</h4>

          <BarRow label="WL Produced" value={wlcOverflow} pct={100} color="bg-gradient-to-r from-cyan/80 to-cyan" valueColor="text-cyan" />
          <BarRow label="Total WL Demand" value={totalDemand} pct={demandBarPct} color="bg-gradient-to-r from-amber-400/80 to-amber-400" valueColor="text-amber-400" />
          {flDemands.map((fl, i) => {
            const flBarPct = wlcOverflow > 0 ? (fl.gpm / wlcOverflow) * 100 : 0;
            const colors = [
              "bg-gradient-to-r from-emerald-400/80 to-emerald-400",
              "bg-gradient-to-r from-violet-400/80 to-violet-400",
              "bg-gradient-to-r from-orange-400/80 to-orange-400",
              "bg-gradient-to-r from-pink-400/80 to-pink-400",
            ];
            const textColors = ["text-emerald-400", "text-violet-400", "text-orange-400", "text-pink-400"];
            return (
              <BarRow
                key={fl.id}
                label={fl.id.replace(/_/g, " ")}
                value={fl.gpm}
                pct={flBarPct}
                color={colors[i % colors.length]}
                valueColor={textColors[i % textColors.length]}
                sub
              />
            );
          })}

          <div className="mt-1 border-t border-white/[0.06] pt-2">
            <BarRow label="Surplus" value={surplus} pct={surplusBarPct} color="bg-gradient-to-r from-blue-400/80 to-blue-400" valueColor="text-blue-400" prefix="+" />
          </div>

          <div className="mt-3 text-center">
            <span className="inline-block rounded-lg border border-emerald-500/30 bg-emerald-500/[0.06] px-5 py-2 font-mono text-xs font-semibold text-emerald-400">
              Balanced: {f1(wlcOverflow)} gpm produced &gt; {f1(totalDemand)} gpm demand — surplus {f1(surplus)} gpm ({f1(surplusPct)}%)
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── BarRow sub-component ── */
function BarRow({ label, value, pct, color, valueColor, sub, prefix }: {
  label: string; value: number; pct: number; color: string;
  valueColor: string; sub?: boolean; prefix?: string;
}) {
  return (
    <div className="flex items-center gap-0 my-1">
      <span className={`w-36 text-right pr-3 font-mono ${sub ? "text-muted-foreground text-[10px]" : "text-white text-[11px]"}`}>
        {label}
      </span>
      <div className="flex-1 h-7 rounded-md bg-white/[0.04] relative overflow-hidden">
        <div
          className={`h-full rounded-md flex items-center justify-end pr-2 font-mono text-[10px] font-semibold text-white ${color}`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        >
          {pct > 8 ? `${fmtNum(value, 1)}` : ""}
        </div>
      </div>
      <span className={`w-24 pl-2.5 font-mono text-[11px] font-semibold ${valueColor}`}>
        {prefix}{fmtNum(value, 1)} gpm
      </span>
    </div>
  );
}
