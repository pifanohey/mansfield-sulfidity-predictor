"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { fmtNum, fmtPct } from "@/lib/format";
import type { CalculationResponse } from "@/lib/types";

interface Props {
  results: CalculationResponse;
  ctoSLbHr: number;
  blSPctLab: number;
  blSPctUsed: number;
  wwFlowGpm: number;
  showerFlowGpm: number;
}

/* ── tiny helpers ── */
const f1 = (v: number) => fmtNum(v, 1);
const f2 = (v: number) => fmtNum(v, 2);

/* ── colour constants matching dark app theme ── */
const C = {
  blue:   "#38bdf8",   // sky-400
  green:  "#34d399",   // emerald-400
  pink:   "#f472b6",   // pink-400
  amber:  "#fbbf24",   // amber-400
  red:    "#f87171",   // red-400
  cyan:   "#5EEAD4",   // teal/cyan accent
  purple: "#a78bfa",   // violet-400
  orange: "#fb923c",   // orange-400
  muted:  "rgba(255,255,255,0.35)",
  text:   "rgba(255,255,255,0.85)",
  label:  "rgba(255,255,255,0.5)",
  border: "rgba(255,255,255,0.08)",
  bg:     "rgba(255,255,255,0.03)",
} as const;

export default function RecaustFlowDiagram({
  results, ctoSLbHr, blSPctLab, blSPctUsed,
  wwFlowGpm, showerFlowGpm,
}: Props) {
  const im = results.intermediate;
  const mk = results.makeup;
  const sf = results.sulfidity;

  /* values from intermediate / top-level */
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
  // Build per-fiberline demand list dynamically
  const fiberlineIds: string[] = (im.fiberline_ids as unknown as string[]) ?? [];
  const flDemands: Array<{ id: string; gpm: number }> = fiberlineIds.map((id) => ({
    id,
    gpm: (im[`${id}_wl_demand_gpm`] as number) ?? 0,
  }));
  // Fallback for legacy single-mill (Pine Hill)
  if (flDemands.length === 0) {
    const pineDemand = im.pine_wl_demand_gpm ?? 0;
    const semiDemand = im.semichem_wl_demand_gpm ?? 0;
    if (pineDemand > 0) flDemands.push({ id: "pine", gpm: pineDemand });
    if (semiDemand > 0) flDemands.push({ id: "semichem", gpm: semiDemand });
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

  const totalIn        = smeltGpm + wwSolved + showerFlowGpm + filtGpm;
  const totalRemoved   = dregsUF + semiGL;
  const surplus        = wlcOverflow - totalDemand;
  const surplusPct     = totalDemand > 0 ? (surplus / wlcOverflow) * 100 : 0;
  const demandBarPct   = wlcOverflow > 0 ? (totalDemand / wlcOverflow) * 100 : 0;
  const surplusBarPct  = wlcOverflow > 0 ? (surplus / wlcOverflow) * 100 : 0;

  /* smelt TTA from recovery boiler results */
  const smeltTTA       = results.recovery_boiler.tta_lb_hr;

  return (
    <Card className="mt-6">
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Recausticizing Circuit — Flow Diagram</CardTitle>
        <p className="text-xs text-muted-foreground">
          Full circuit from RB smelt through DT, GL clarifier, slaker, WLC to final WL
        </p>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {/* ═══ SVG FLOW DIAGRAM ═══ */}
        <svg viewBox="0 0 1100 680" className="mx-auto" style={{ maxWidth: 1100, width: "100%" }}>
          <defs>
            {/* arrowheads */}
            <marker id="ah" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.muted} />
            </marker>
            <marker id="ah-g" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.green} />
            </marker>
            <marker id="ah-p" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.pink} />
            </marker>
            <marker id="ah-v" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.purple} />
            </marker>
            <marker id="ah-r" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.red} />
            </marker>
            <marker id="ah-y" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.amber} />
            </marker>
            <marker id="ah-c" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.cyan} />
            </marker>
            <marker id="ah-o" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <polygon points="0 0,8 3,0 6" fill={C.orange} />
            </marker>
          </defs>

          {/* ═══ SECTION TITLE ═══ */}
          <text x="20" y="24" fontSize="11" fill={C.muted} fontWeight="600" letterSpacing="1" textDecoration="uppercase">INPUTS</text>

          {/* ═══ CTO / BL FEED ═══ */}
          <rect x="30" y="38" width="180" height="82" rx="8" ry="8" fill="rgba(251,146,60,0.06)" stroke={C.orange} strokeWidth="2" />
          <text x="120" y="56" fontSize="12" fontWeight="600" fill={C.orange} textAnchor="middle">CTO S → BL Feed</text>
          <text x="120" y="72" fontSize="11" fill={C.label} textAnchor="middle">CTO S: {f1(ctoSLbHr)} lb/hr</text>
          <text x="120" y="87" fontSize="11" fill={C.label} textAnchor="middle">BL S% (lab): {f2(blSPctLab)}%</text>
          <text x="120" y="102" fontSize="11" fill={C.green} fontWeight="600" textAnchor="middle">Adj BL S%: {f2(blSPctUsed)}%</text>
          <text x="120" y="115" fontSize="10" fill={C.muted} textAnchor="middle">
            {Math.abs(blSPctUsed - blSPctLab) < 0.005 ? "No CTO delta" : `Δ ${(blSPctUsed - blSPctLab) >= 0 ? "+" : ""}${(blSPctUsed - blSPctLab).toFixed(3)}%`}
          </text>
          <line x1="120" y1="120" x2="120" y2="140" stroke={C.orange} strokeWidth="2" strokeDasharray="4,3" markerEnd="url(#ah-o)" />

          {/* ═══ SMELT ═══ */}
          <rect x="30" y="140" width="180" height="72" rx="8" ry="8" fill="rgba(52,211,153,0.06)" stroke="rgba(52,211,153,0.4)" strokeWidth="2" />
          <text x="120" y="160" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">Recovery Boiler Smelt</text>
          <text x="120" y="177" fontSize="11" fill={C.blue} textAnchor="middle">{f1(smeltGpm)} gpm</text>
          <text x="120" y="193" fontSize="11" fill={C.pink} textAnchor="middle">Sulfidity: {f2(smeltSulf)}%</text>
          <text x="120" y="207" fontSize="11" fill={C.label} textAnchor="middle">TTA: {f1(smeltTTA)} lb Na₂O/hr</text>

          {/* ═══ WEAK WASH ═══ */}
          <rect x="30" y="240" width="180" height="56" rx="8" ry="8" fill="rgba(52,211,153,0.06)" stroke="rgba(52,211,153,0.4)" strokeWidth="2" />
          <text x="120" y="260" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">Weak Wash (solved)</text>
          <text x="120" y="277" fontSize="11" fill={C.blue} textAnchor="middle">{f1(wwSolved)} gpm</text>
          <text x="120" y="291" fontSize="11" fill={C.label} textAnchor="middle">Analytical solve for GL TTA target</text>

          {/* ═══ SHOWER ═══ */}
          <rect x="30" y="320" width="180" height="42" rx="8" ry="8" fill="rgba(52,211,153,0.06)" stroke="rgba(52,211,153,0.4)" strokeWidth="2" />
          <text x="120" y="338" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">Shower Water</text>
          <text x="120" y="354" fontSize="11" fill={C.blue} textAnchor="middle">{f1(showerFlowGpm)} gpm</text>

          {/* ═══ DREGS FILTRATE ═══ */}
          <rect x="30" y="385" width="180" height="42" rx="8" ry="8" fill="rgba(52,211,153,0.06)" stroke="rgba(52,211,153,0.4)" strokeWidth="2" />
          <text x="120" y="403" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">Dregs Filtrate (return)</text>
          <text x="120" y="419" fontSize="11" fill={C.blue} textAnchor="middle">{f1(filtGpm)} gpm</text>

          {/* ═══ INPUT ARROWS ═══ */}
          <line x1="210" y1="176" x2="330" y2="240" stroke="rgba(52,211,153,0.4)" strokeWidth="2" markerEnd="url(#ah-g)" />
          <line x1="210" y1="268" x2="330" y2="260" stroke="rgba(52,211,153,0.4)" strokeWidth="2" markerEnd="url(#ah-g)" />
          <line x1="210" y1="341" x2="330" y2="270" stroke="rgba(52,211,153,0.4)" strokeWidth="2" markerEnd="url(#ah-g)" />
          <line x1="210" y1="406" x2="330" y2="285" stroke="rgba(52,211,153,0.4)" strokeWidth="2" markerEnd="url(#ah-g)" />

          {/* ═══ DISSOLVING TANK ═══ */}
          <rect x="330" y="210" width="220" height="110" rx="8" ry="8" fill="rgba(56,189,248,0.06)" stroke="rgba(56,189,248,0.4)" strokeWidth="3" />
          <text x="440" y="235" fontSize="16" fontWeight="600" fill={C.text} textAnchor="middle">Dissolving Tank</text>
          <text x="440" y="255" fontSize="11" fill={C.label} textAnchor="middle">Total In: {f1(totalIn)} gpm</text>
          <text x="440" y="270" fontSize="11" fill={C.red} textAnchor="middle">Steam Lost: -{f1(steamGpm)} gpm ({f1(steamLbHr)} lb/hr)</text>
          <text x="440" y="290" fontSize="14" fontWeight="700" fill={C.blue} textAnchor="middle">GL Out: {f1(dtGlOut)} gpm</text>
          <text x="440" y="308" fontSize="11" fill={C.green} textAnchor="middle">TTA: {f1(glTTA)} g/L | Sulfidity: {f1(glSulfPct)}%</text>

          {/* ═══ STEAM ARROW ═══ */}
          <line x1="440" y1="210" x2="440" y2="160" stroke={C.red} strokeWidth="2" strokeDasharray="6,4" markerEnd="url(#ah-r)" />
          <text x="440" y="150" fontSize="11" fill={C.red} textAnchor="middle">Steam</text>

          {/* ═══ GL OUTPUT ARROW ═══ */}
          <line x1="550" y1="265" x2="620" y2="265" stroke={C.pink} strokeWidth="2" markerEnd="url(#ah-p)" />

          {/* ═══ GL CLARIFIER ═══ */}
          <rect x="620" y="218" width="200" height="95" rx="8" ry="8" fill="rgba(244,114,182,0.06)" stroke="rgba(244,114,182,0.4)" strokeWidth="2" />
          <text x="720" y="240" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">Green Liquor Clarifier</text>
          <text x="720" y="258" fontSize="11" fill={C.blue} textAnchor="middle">In: {f1(dtGlOut)} gpm</text>
          <text x="720" y="273" fontSize="11" fill={C.green} textAnchor="middle">TTA: {f1(glTTA)} g/L</text>
          <text x="720" y="288" fontSize="11" fill={C.label} textAnchor="middle">Na₂S: {f1(glNa2S)} g/L</text>
          <text x="720" y="303" fontSize="11" fill={C.pink} textAnchor="middle">Sulfidity: {f1(glSulfPct)}%</text>

          {/* ═══ SUBTRACTIONS ═══ */}
          <text x="620" y="350" fontSize="11" fill={C.muted} fontWeight="600" letterSpacing="1">SUBTRACTIONS</text>
          <rect x="620" y="362" width="200" height="36" rx="8" ry="8" fill="rgba(167,139,250,0.06)" stroke="rgba(167,139,250,0.4)" strokeWidth="2" />
          <text x="720" y="378" fontSize="12" fontWeight="600" fill={C.text} textAnchor="middle">Dregs UF</text>
          <text x="720" y="392" fontSize="11" fill={C.blue} textAnchor="middle">-{f1(dregsUF)} gpm</text>
          <line x1="720" y1="313" x2="720" y2="362" stroke={C.purple} strokeWidth="2" markerEnd="url(#ah-v)" />

          <rect x="620" y="408" width="200" height="36" rx="8" ry="8" fill="rgba(167,139,250,0.06)" stroke="rgba(167,139,250,0.4)" strokeWidth="2" />
          <text x="720" y="424" fontSize="12" fontWeight="600" fill={C.text} textAnchor="middle">Semichem GL</text>
          <text x="720" y="438" fontSize="11" fill={C.blue} textAnchor="middle">-{f1(semiGL)} gpm</text>
          <line x1="720" y1="398" x2="720" y2="408" stroke={C.purple} strokeWidth="2" markerEnd="url(#ah-v)" />

          <text x="720" y="468" fontSize="11" fill={C.purple} fontWeight="600" textAnchor="middle">Total removed: -{f1(totalRemoved)} gpm</text>

          {/* ═══ GL TO SLAKER ARROW ═══ */}
          <line x1="820" y1="265" x2="870" y2="265" stroke={C.amber} strokeWidth="2" markerEnd="url(#ah-y)" />

          {/* ═══ SLAKER ═══ */}
          <rect x="870" y="210" width="210" height="120" rx="8" ry="8" fill="rgba(251,191,36,0.06)" stroke="rgba(251,191,36,0.4)" strokeWidth="2" />
          <text x="975" y="234" fontSize="15" fontWeight="600" fill={C.text} textAnchor="middle">Slaker / Causticizers</text>
          <text x="975" y="254" fontSize="11" fill={C.blue} textAnchor="middle">GL In: {f1(glToSlaker)} gpm</text>
          <text x="975" y="270" fontSize="11" fill={C.amber} textAnchor="middle">Yield: {fmtNum(yieldFactor, 3)}</text>
          <text x="975" y="288" fontSize="11" fill={C.blue} textAnchor="middle">WL Out: {f1(wlFromSlaker)} gpm</text>
          <text x="975" y="304" fontSize="11" fill={C.green} textAnchor="middle">TTA: {f1(wlTTAslaker)} g/L</text>
          <text x="975" y="320" fontSize="11" fill={C.label} textAnchor="middle">NaOH: {f1(wlNaOHslaker)} | Na₂S: {f1(wlNa2Sslaker)} g/L</text>

          {/* ═══ SLAKER → WLC ARROW ═══ */}
          <line x1="975" y1="330" x2="975" y2="365" stroke={C.cyan} strokeWidth="2" markerEnd="url(#ah-c)" />

          {/* ═══ WLC + MAKEUP ═══ */}
          <rect x="870" y="365" width="210" height="130" rx="8" ry="8" fill="rgba(94,234,212,0.06)" stroke="rgba(94,234,212,0.4)" strokeWidth="2" />
          <text x="975" y="385" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">WL Clarifier + Makeup</text>
          <text x="975" y="401" fontSize="11" fill={C.purple} textAnchor="middle">-Grits (at slaker): -{f1(gritsGpm)} gpm</text>
          <text x="975" y="417" fontSize="11" fill={C.label} textAnchor="middle">+NaSH: {f1(nashGpm)} gpm ({f1(nashDry)} lb/hr dry)</text>
          <text x="975" y="433" fontSize="11" fill={C.label} textAnchor="middle">+NaOH: {f1(naohGpm)} gpm ({f1(naohDry)} lb/hr dry)</text>
          <text x="975" y="449" fontSize="11" fill={C.red} textAnchor="middle">-Mud UF: -{f1(mudUF)} gpm</text>
          <text x="975" y="469" fontSize="13" fontWeight="700" fill={C.blue} textAnchor="middle">WL Overflow: ~{f1(wlcOverflow)} gpm</text>
          <text x="975" y="487" fontSize="11" fill={C.pink} textAnchor="middle">Sulfidity: ~{f2(finalSulf)}%</text>

          {/* ═══ WLC → FINAL WL ARROW ═══ */}
          <line x1="975" y1="495" x2="975" y2="520" stroke={C.cyan} strokeWidth="2" markerEnd="url(#ah-c)" />

          {/* ═══ FINAL WL ═══ */}
          <rect x="870" y="520" width="210" height="88" rx="8" ry="8" fill="rgba(94,234,212,0.06)" stroke="rgba(94,234,212,0.4)" strokeWidth="2" />
          <text x="975" y="540" fontSize="13" fontWeight="600" fill={C.text} textAnchor="middle">Final WL to Digesters</text>
          <text x="975" y="557" fontSize="11" fontWeight="700" fill={C.cyan} textAnchor="middle">EA: {f2(finalEA)} g/L</text>
          <text x="975" y="573" fontSize="11" fill={C.green} textAnchor="middle">TTA: {f1(finalTTA)} | AA: {f1(finalAA)} g/L</text>
          <text x="975" y="589" fontSize="11" fill={C.label} textAnchor="middle">NaOH: {f1(finalNaOH)} | Na₂CO₃: {f1(finalNa2CO3)} g/L</text>
          <text x="975" y="604" fontSize="11" fill={C.pink} textAnchor="middle">Sulfidity: {f2(finalSulf)}%</text>

          {/* ═══ VOLUME BALANCE BOX ═══ */}
          <rect x="30" y="490" width="530" height="120" rx="8" ry="8" fill={C.bg} stroke={C.border} strokeWidth="1" />
          <text x="50" y="515" fontSize="13" fontWeight="600" fill={C.amber} textAnchor="start">Volume Balance Check</text>
          <text x="50" y="535" fontSize="11" fill={C.label} textAnchor="start">
            Smelt ({f1(smeltGpm)}) + WW ({f1(wwSolved)}) + Shower ({f1(showerFlowGpm)}) + Filtrate ({f1(filtGpm)}) = {f1(totalIn)} gpm in
          </text>
          <text x="50" y="553" fontSize="11" fill={C.label} textAnchor="start">
            GL Out ({f1(dtGlOut)}) + Steam ({f1(steamGpm)}) = {f1(dtGlOut + steamGpm)} gpm out ✓
          </text>
          <text x="50" y="573" fontSize="11" fill={C.label} textAnchor="start">
            GL ({f1(dtGlOut)}) - Dregs ({f1(dregsUF)}) - Semi GL ({f1(semiGL)}) ={" "}
            <tspan fill={C.amber} fontWeight="600">{f1(glToSlaker)} gpm to slaker</tspan>
          </text>
          <text x="50" y="593" fontSize="11" fill={C.label} textAnchor="start">
            Slaker ({f1(wlFromSlaker)}) - Grits ({f1(gritsGpm)}) + Makeup ({f1(nashGpm + naohGpm)}) - Mud ({f1(mudUF)}) ≈{" "}
            <tspan fill={C.amber} fontWeight="600">~{f1(wlcOverflow)} gpm WL overflow</tspan>
          </text>
        </svg>

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
