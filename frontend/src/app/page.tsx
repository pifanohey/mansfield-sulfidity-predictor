"use client";

import { useEffect } from "react";
import Header from "@/components/layout/Header";
import PageContainer from "@/components/layout/PageContainer";
import KPICard from "@/components/dashboard/KPICard";
import SulfidityGauge from "@/components/dashboard/SulfidityGauge";
import MakeupSummary from "@/components/dashboard/MakeupSummary";
import RecoveryBoilerSummary from "@/components/dashboard/RecoveryBoilerSummary";
import GuidancePanel from "@/components/dashboard/GuidancePanel";
import { Button } from "@/components/ui/button";
import { useAppState } from "@/hooks/useAppState";
import { fmtNum, fmtPct } from "@/lib/format";
import { RefreshCw } from "lucide-react";

export default function DashboardPage() {
  const { inputs, results, loading, error, configReady, runCalculation } = useAppState();

  useEffect(() => {
    if (configReady && !results) runCalculation();
  }, [configReady]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <PageContainer>
        <Header
          title="Overview"
          breadcrumb="Workspace / Sulfidity Predictor"
          subtitle="Real-time sulfidity monitoring and prediction dashboard"
          badge="v1.0-stable"
        >
          <Button
            variant="outline"
            size="sm"
            onClick={() => runCalculation()}
            disabled={loading}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Calculating..." : "Recalculate"}
          </Button>
        </Header>

        {error && (
          <div className="mb-4 rounded-lg border border-red-500/20 bg-red-500/5 p-3 font-mono text-xs text-red-400">
            {error}
          </div>
        )}

        {results && (
          <div className="space-y-5">
            {/* KPI Row */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KPICard
                label="Final Sulfidity"
                value={fmtPct(results.sulfidity.final_pct)}
                subtitle={`Target: ${fmtPct(inputs.target_sulfidity_pct)}`}
              />
              <KPICard
                label="NaSH (dry)"
                value={fmtNum(results.makeup.nash_dry_lb_hr)}
                unit="lb/hr"
                subtitle={`${fmtNum(results.makeup.nash_gpm, 2)} gpm`}
              />
              <KPICard
                label="NaOH (dry)"
                value={fmtNum(results.makeup.naoh_dry_lb_hr)}
                unit="lb/hr"
                subtitle={`${fmtNum(results.makeup.naoh_gpm, 2)} gpm`}
              />
              <KPICard
                label="Production"
                value={fmtNum(results.production?.total_bdt_day ?? 0)}
                unit="BDT/day"
                subtitle="Total"
              />
            </div>

            {/* Main Content */}
            <div className="grid gap-4 lg:grid-cols-2">
              <SulfidityGauge
                current={results.sulfidity.current_pct}
                latent={results.sulfidity.latent_pct}
                final={results.sulfidity.final_pct}
                smelt={results.sulfidity.smelt_pct}
                target={inputs.target_sulfidity_pct}
                trend={results.sulfidity.trend}
              />
              <GuidancePanel items={results.guidance} />
            </div>

            {/* Bottom Row */}
            <div className="grid gap-4 lg:grid-cols-2">
              <MakeupSummary makeup={results.makeup} />
              <RecoveryBoilerSummary rb={results.recovery_boiler} />
            </div>
          </div>
        )}

        {!results && !loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="font-mono text-sm text-muted-foreground">
              Click &quot;Recalculate&quot; to run with mill defaults.
            </div>
          </div>
        )}
      </PageContainer>
    </>
  );
}
