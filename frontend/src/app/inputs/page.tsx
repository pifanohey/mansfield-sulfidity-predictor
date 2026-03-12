"use client";

import { useRouter } from "next/navigation";
import Header from "@/components/layout/Header";
import PageContainer from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import TankLevelSection from "@/components/inputs/TankLevelSection";
import LabAnalysisSection from "@/components/inputs/LabAnalysisSection";
import RecoveryBoilerSection from "@/components/inputs/RecoveryBoilerSection";
import ProductionSection from "@/components/inputs/ProductionSection";
import SetpointSection from "@/components/inputs/SetpointSection";
import MakeupPropertiesSection from "@/components/inputs/MakeupPropertiesSection";
import BLCompositionSection from "@/components/inputs/BLCompositionSection";
import LossTableSection from "@/components/inputs/LossTableSection";
import DissolvingTankSection from "@/components/inputs/DissolvingTankSection";
import SlakerWLCSection from "@/components/inputs/SlakerWLCSection";
import WhiteWaterSection from "@/components/inputs/WhiteWaterSection";
import { useAppState } from "@/hooks/useAppState";
import type { FiberlineConfig } from "@/lib/types";
import {
  DEFAULT_TANK_LEVELS,
  DEFAULT_WL_ANALYSIS,
  DEFAULT_GL_ANALYSIS,
  DEFAULT_RB_INPUTS,
  DEFAULT_LOSS_TABLE,
} from "@/lib/defaults";
import { RotateCcw, Play } from "lucide-react";

const MAKEUP_LABELS: Record<string, string> = {
  nash: "NaSH",
  saltcake: "Saltcake (Na\u2082SO\u2084)",
  emulsified_sulfur: "Emulsified Sulfur",
  naoh: "NaOH (Caustic Soda)",
};

// Fallback fiberline configs matching the old hardcoded Pine/Semichem fields
const FALLBACK_FIBERLINES: FiberlineConfig[] = [
  {
    id: "pine",
    name: "Pine",
    type: "continuous",
    cooking_type: "chemical",
    uses_gl_charge: false,
    defaults: {
      production_bdt_day: 1250.69,
      yield_pct: 0.5694,
      ea_pct: 0.122,
    },
  },
  {
    id: "semichem",
    name: "Semichem",
    type: "batch",
    cooking_type: "semichem",
    uses_gl_charge: true,
    defaults: {
      production_bdt_day: 636.854,
      yield_pct: 0.7019,
      ea_pct: 0.0365,
      gl_ea_pct: 0.017,
    },
  },
];

export default function InputsPage() {
  const router = useRouter();
  const {
    inputs,
    results,
    loading,
    millConfig,
    fiberlineInputs,
    rbInputs,
    dtInputs,
    updateField,
    updateNestedField,
    updateFiberlineField,
    updateRBField,
    updateDTField,
    configReady,
    resetToDefaults,
    runCalculation,
  } = useAppState();

  const fiberlines = millConfig?.fiberlines ?? FALLBACK_FIBERLINES;
  const makeupLabel = millConfig
    ? MAKEUP_LABELS[millConfig.makeup_chemical] ?? millConfig.makeup_chemical
    : "NaSH";
  const millName = millConfig?.mill_name ?? "Mill";

  const handleCalculate = async () => {
    const res = await runCalculation();
    if (res) {
      router.push("/results");
    }
  };

  const handleLossTableChange = (sourceKey: string, field: string, value: number) => {
    const currentTable = inputs.loss_table ?? DEFAULT_LOSS_TABLE;
    const currentSource = currentTable[sourceKey as keyof typeof currentTable] ?? { s_lb_bdt: 0, na_lb_bdt: 0 };
    const updatedSource = { ...currentSource, [field]: value };
    const updatedTable = { ...currentTable, [sourceKey]: updatedSource };
    updateField("loss_table", updatedTable);
  };

  return (
    <>
      <PageContainer>
        <Header
          title="Input Parameters"
          breadcrumb={`${millName} / Sulfidity Predictor`}
          subtitle="Configure mill operating parameters for sulfidity prediction"
          badge="v2.0"
        >
          <Button variant="outline" size="sm" onClick={resetToDefaults}>
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </Button>
          <Button size="sm" onClick={handleCalculate} disabled={loading}>
            <Play className="h-3.5 w-3.5" />
            {loading ? "Calculating..." : "Calculate"}
          </Button>
        </Header>

        {/* Status Legend */}
        <div className="mb-5 flex flex-wrap gap-4 rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Active — Directly affects calculations
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-amber-400" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Computed — Model calculates from other inputs
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-blue-400" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
              Inventory — Used for tank metrics only
            </span>
          </div>
        </div>

        {!configReady && (
          <div className="mb-4 rounded-md border border-white/[0.06] bg-white/[0.02] px-3 py-2 font-mono text-[10px] text-muted-foreground">
            Loading mill configuration...
          </div>
        )}

        {configReady && !millConfig && (
          <div className="mb-4 rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 font-mono text-[10px] text-amber-400">
            Using fallback configuration — could not load mill config from server.
          </div>
        )}

        <Accordion type="multiple" defaultValue={[]}>
          <AccordionItem value="tanks">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <span>Tank Levels</span>
                <div className="h-1.5 w-1.5 rounded-full bg-blue-400" />
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="mb-3 rounded-md border border-blue-500/10 bg-blue-500/5 px-3 py-2 font-mono text-[10px] text-blue-400">
                Inventory metrics only — does not affect main calculations.
              </div>
              <TankLevelSection
                levels={inputs.tank_levels ?? DEFAULT_TANK_LEVELS}
                onChange={(k, v) => updateNestedField("tank_levels", k, v)}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="lab">
            <AccordionTrigger>Lab Analysis</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-5">
                <LabAnalysisSection
                  title="White Liquor"
                  analysis={inputs.wl_analysis ?? DEFAULT_WL_ANALYSIS}
                  onChange={(k, v) => updateNestedField("wl_analysis", k, v)}
                  excelPrefix="1_Inv!WL_"
                />
                <LabAnalysisSection
                  title="Green Liquor"
                  analysis={inputs.gl_analysis ?? DEFAULT_GL_ANALYSIS}
                  onChange={(k, v) => updateNestedField("gl_analysis", k, v)}
                  excelPrefix="1_Inv!GL_"
                />
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="bl">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <span>BL Composition</span>
                <div className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <BLCompositionSection
                blNaPct={inputs.bl_na_pct}
                blSPct={inputs.bl_s_pct}
                blKPct={inputs.bl_k_pct}
                onChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
                computedNaPct={results?.forward_leg?.bl_na_pct_used}
                computedSPct={results?.forward_leg?.bl_s_pct_used}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="rb">
            <AccordionTrigger>
              Recovery Boiler{millConfig && millConfig.recovery_boilers?.length > 1 ? `s (${millConfig.recovery_boilers.length})` : ""}
            </AccordionTrigger>
            <AccordionContent>
              <RecoveryBoilerSection
                rb={inputs.recovery_boiler ?? DEFAULT_RB_INPUTS}
                onChange={(k, v) => updateNestedField("recovery_boiler", k, v)}
                rbConfigs={millConfig?.recovery_boilers}
                rbInputs={rbInputs}
                onRBFieldChange={updateRBField}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="production">
            <AccordionTrigger>Production / Fiberline</AccordionTrigger>
            <AccordionContent>
              <ProductionSection
                fiberlines={fiberlines}
                fiberlineInputs={fiberlineInputs}
                cookingSulfidity={inputs.cooking_wl_sulfidity}
                onFiberlineChange={updateFiberlineField}
                onGlobalChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="whitewater">
            <AccordionTrigger>White Water (Paper Machine)</AccordionTrigger>
            <AccordionContent>
              <WhiteWaterSection
                washWaterNaPct={inputs.wash_water_na_pct ?? 0}
                washWaterSPct={inputs.wash_water_s_pct ?? 0}
                fiberlines={fiberlines}
                fiberlineInputs={fiberlineInputs}
                onChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
                onFiberlineChange={updateFiberlineField}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="setpoints">
            <AccordionTrigger>Setpoints</AccordionTrigger>
            <AccordionContent>
              <SetpointSection
                targetSulfidity={inputs.target_sulfidity_pct}
                causticity={inputs.causticity_pct}
                ctoH2so4PerTon={inputs.cto_h2so4_per_ton}
                ctoTpd={inputs.cto_tpd}
                onChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="dissolving">
            <AccordionTrigger>
              Dissolving Tank{millConfig && millConfig.dissolving_tanks?.length > 1 ? `s (${millConfig.dissolving_tanks.length})` : ""} / Weak Wash
            </AccordionTrigger>
            <AccordionContent>
              <DissolvingTankSection
                wwFlow={inputs.ww_flow_gpm}
                wwTtaLbFt3={inputs.ww_tta_lb_ft3}
                wwSulfidity={inputs.ww_sulfidity}
                showerFlow={inputs.shower_flow_gpm}
                smeltDensity={inputs.smelt_density_lb_ft3}
                glTargetTtaLbFt3={inputs.gl_target_tta_lb_ft3}
                glCausticity={inputs.gl_causticity}
                onChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
                dtConfigs={millConfig?.dissolving_tanks}
                dtInputs={dtInputs}
                onDTFieldChange={updateDTField}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="recaust">
            <AccordionTrigger>Recausticizing / WLC</AccordionTrigger>
            <AccordionContent>
              <SlakerWLCSection
                limeChargeRatio={inputs.lime_charge_ratio}
                caoInLime={inputs.cao_in_lime_pct}
                caco3InLime={inputs.caco3_in_lime_pct}
                inertsInLime={inputs.inerts_in_lime_pct}
                gritsLoss={inputs.grits_loss_pct}
                limeTemp={inputs.lime_temp_f}
                slakerTemp={inputs.slaker_temp_f}
                intrusionWater={inputs.intrusion_water_gpm}
                dilutionWater={inputs.dilution_water_gpm}
                wlcUnderflowSolids={inputs.wlc_underflow_solids_pct}
                wlcMudDensity={inputs.wlc_mud_density}
                dregsLbBdt={inputs.dregs_lb_bdt}
                glcUnderflowSolids={inputs.glc_underflow_solids_pct}
                gritsLbBdt={inputs.grits_lb_bdt}
                gritsSolids={inputs.grits_solids_pct}
                onChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="makeup">
            <AccordionTrigger>
              <div className="flex items-center gap-2">
                <span>Makeup Chemical Properties</span>
                {millConfig && (
                  <span className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[9px] text-muted-foreground">
                    {makeupLabel}
                  </span>
                )}
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <MakeupPropertiesSection
                nashConc={inputs.nash_concentration}
                naohConc={inputs.naoh_concentration}
                nashDensity={inputs.nash_density}
                naohDensity={inputs.naoh_density}
                onChange={(k, v) => updateField(k as keyof typeof inputs, v as never)}
              />
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="losses">
            <AccordionTrigger>Soda &amp; Sulfur Losses</AccordionTrigger>
            <AccordionContent>
              <LossTableSection
                lossTable={inputs.loss_table ?? DEFAULT_LOSS_TABLE}
                onChange={handleLossTableChange}
              />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </PageContainer>
    </>
  );
}
