"use client";

import { useEffect, useState, Component, type ReactNode } from "react";
import Header from "@/components/layout/Header";
import PageContainer from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import SulfiditySummary from "@/components/results/SulfiditySummary";
import MakeupTable from "@/components/results/MakeupTable";
import RecoveryBoilerResults from "@/components/results/RecoveryBoilerResults";
import MassBalanceTable from "@/components/results/MassBalanceTable";
import InventoryTable from "@/components/results/InventoryTable";
import SensitivityTable from "@/components/results/SensitivityTable";
import ElementTrackingTable from "@/components/results/ElementTrackingTable";
import CircuitFlowMap from "@/components/results/CircuitFlowMap";
import WLQualityTable from "@/components/results/WLQualityTable";
import RecaustFlowDiagram from "@/components/results/RecaustFlowDiagram";
import BLCompositionChart from "@/components/results/BLCompositionChart";
import GuidancePanel from "@/components/dashboard/GuidancePanel";
import { useAppState } from "@/hooks/useAppState";
import { saveSnapshot, exportPdf, exportExcel } from "@/lib/api";
import type { CalculationResponse } from "@/lib/types";
import { FileText, FileSpreadsheet, Save, RefreshCw } from "lucide-react";

class DiagramErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="mt-4 rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400">
          <p className="font-mono text-xs font-semibold uppercase tracking-wider">RecaustFlowDiagram error</p>
          <pre className="mt-2 whitespace-pre-wrap font-mono text-xs text-red-400/70">{this.state.error.message}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function ResultsPage() {
  const { inputs, results, loading, error, configReady, runCalculation } = useAppState();
  const [exporting, setExporting] = useState<"pdf" | "excel" | null>(null);

  useEffect(() => {
    if (configReady && !results) runCalculation();
  }, [configReady]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSave = async () => {
    if (results) {
      await saveSnapshot(inputs, results as unknown as Record<string, unknown>, "");
    }
  };

  const handleExport = async (format: "pdf" | "excel") => {
    if (!results) return;
    setExporting(format);
    try {
      const fn = format === "pdf" ? exportPdf : exportExcel;
      await fn(inputs, results as CalculationResponse);
    } catch (e) {
      console.error("Export failed:", e);
    } finally {
      setExporting(null);
    }
  };

  return (
    <>
      <PageContainer>
        <Header
          title="Results"
          breadcrumb="Workspace / Sulfidity Predictor"
          subtitle="Calculation results and analysis"
          badge="v1.0-stable"
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport("pdf")}
            disabled={!results || exporting !== null}
          >
            <FileText className="h-3.5 w-3.5" />
            {exporting === "pdf" ? "Exporting..." : "PDF"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport("excel")}
            disabled={!results || exporting !== null}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            {exporting === "excel" ? "Exporting..." : "Excel"}
          </Button>
          <Button variant="outline" size="sm" onClick={handleSave} disabled={!results}>
            <Save className="h-3.5 w-3.5" />
            Save
          </Button>
          <Button size="sm" onClick={() => runCalculation()} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Calculating..." : "Recalculate"}
          </Button>
        </Header>

        {error && (
          <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/5 p-3 font-mono text-xs text-red-400">
            {error}
          </div>
        )}

        {results ? (
          <Tabs defaultValue="sulfidity">
            <TabsList className="mb-4 flex-wrap">
              <TabsTrigger value="sulfidity">Sulfidity</TabsTrigger>
              <TabsTrigger value="wl">WL Quality</TabsTrigger>
              <TabsTrigger value="makeup">Makeup</TabsTrigger>
              <TabsTrigger value="rb">Recovery Boiler</TabsTrigger>
              <TabsTrigger value="balance">Mass Balance</TabsTrigger>
              <TabsTrigger value="inventory">Inventory</TabsTrigger>
              <TabsTrigger value="tracking">Na/S Tracking</TabsTrigger>
              <TabsTrigger value="bl-flow">BL Flow Chart</TabsTrigger>
              <TabsTrigger value="circuit">Circuit Map</TabsTrigger>
              <TabsTrigger value="sensitivity">Sensitivity</TabsTrigger>
              <TabsTrigger value="guidance">Guidance</TabsTrigger>
            </TabsList>

            <TabsContent value="sulfidity">
              <SulfiditySummary
                sulfidity={results.sulfidity}
                target={inputs.target_sulfidity_pct}
              />
            </TabsContent>

            <TabsContent value="wl">
              <WLQualityTable wlQuality={results.wl_quality} />
              <DiagramErrorBoundary>
                <RecaustFlowDiagram
                  results={results}
                  ctoSLbHr={results.mass_balance.cto_s_lbs_hr}
                  blSPctLab={results.bl_s_pct_lab}
                  blSPctUsed={results.bl_s_pct_used}
                  wwFlowGpm={inputs.ww_flow_gpm}
                  showerFlowGpm={inputs.shower_flow_gpm}
                />
              </DiagramErrorBoundary>
            </TabsContent>

            <TabsContent value="makeup">
              <MakeupTable
                makeup={results.makeup}
                totalProductionBdtDay={results.total_production_bdt_day}
                saltcakeLbHr={inputs.recovery_boiler?.saltcake_flow_lb_hr ?? 0}
              />
            </TabsContent>

            <TabsContent value="rb">
              <RecoveryBoilerResults
                rb={results.recovery_boiler}
                smeltSulfidity={results.sulfidity.smelt_pct}
                blNaPctLab={results.bl_na_pct_lab}
                blSPctLab={results.bl_s_pct_lab}
                blNaPctComputed={results.bl_na_pct_computed}
                blSPctComputed={results.bl_s_pct_computed}
                blNaPctUsed={results.bl_na_pct_used}
                blSPctUsed={results.bl_s_pct_used}
                solverIterations={results.solver?.iterations}
                dtSteamLbHr={results.dt_steam_evaporated_lb_hr}
                dtSteamGpm={results.dt_steam_evaporated_gpm}
                dtHeatFromSmelt={results.dt_heat_from_smelt_btu_hr}
                dtHeatToWarm={results.dt_heat_to_warm_liquor_btu_hr}
                dtNetHeat={results.dt_net_heat_for_steam_btu_hr}
                wwFlowSolved={results.ww_flow_solved_gpm}
                wwFlowInput={inputs.ww_flow_gpm}
                dregsFiltrateGpm={results.dregs_filtrate_gpm}
                outerLoopIterations={results.outer_loop_iterations}
              />
            </TabsContent>

            <TabsContent value="balance">
              <MassBalanceTable balance={results.mass_balance} />
            </TabsContent>

            <TabsContent value="inventory">
              <InventoryTable inventory={results.inventory} />
            </TabsContent>

            <TabsContent value="tracking">
              <ElementTrackingTable
                rows={results.unit_operations}
                lossTableDetail={results.loss_table_detail}
                chemicalAdditions={results.chemical_additions}
                totalSLossesLbHr={results.mass_balance.total_s_losses_lb_hr}
                naLossesElementLbHr={results.na_losses_element_lb_hr}
                saltcakeNaLbHr={results.saltcake_na_lb_hr}
                saltcakeSLbHr={results.saltcake_s_lb_hr}
              />
            </TabsContent>

            <TabsContent value="bl-flow">
              <BLCompositionChart
                data={{
                  ...results.forward_leg,
                  unit_operations: results.unit_operations,
                  rb_na_pct_mixed: results.recovery_boiler.bl_na_pct_mixed,
                  rb_s_pct_mixed: results.recovery_boiler.bl_s_pct_mixed,
                }}
              />
            </TabsContent>

            <TabsContent value="circuit">
              <CircuitFlowMap
                unitOperations={results.unit_operations}
                lossTableDetail={results.loss_table_detail}
                semichem_gl_gpm={results.intermediate?.semichem_gl_gpm}
                dregs_gpm={results.intermediate?.dregs_underflow_gpm}
                grits_gpm={results.intermediate?.grits_entrained_gpm}
                smelt_flow_gpm={results.intermediate?.smelt_flow_gpm}
                ww_flow_gpm={inputs.ww_flow_gpm}
                shower_flow_gpm={inputs.shower_flow_gpm}
              />
            </TabsContent>

            <TabsContent value="sensitivity">
              <SensitivityTable inputs={inputs} />
            </TabsContent>

            <TabsContent value="guidance">
              <GuidancePanel items={results.guidance} />
            </TabsContent>
          </Tabs>
        ) : (
          !loading && (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="font-mono text-sm text-muted-foreground">
                No results yet. Click &quot;Recalculate&quot; to run.
              </div>
            </div>
          )
        )}
      </PageContainer>
    </>
  );
}
