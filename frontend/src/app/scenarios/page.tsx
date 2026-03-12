"use client";

import { useEffect } from "react";
import { FlaskConical } from "lucide-react";
import Header from "@/components/layout/Header";
import PageContainer from "@/components/layout/PageContainer";
import ScenarioBuilder from "@/components/scenarios/ScenarioBuilder";
import SulfidityPredictor from "@/components/scenarios/SulfidityPredictor";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAppState } from "@/hooks/useAppState";

export default function ScenariosPage() {
  const { results, loading, configReady, millConfig, buildFullRequest, runCalculation } = useAppState();

  useEffect(() => {
    if (configReady && !results) runCalculation();
  }, [configReady]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <PageContainer>
        <Header
          title="Scenarios"
          breadcrumb="Analysis"
          subtitle="What-if analysis and sulfidity prediction"
        />
        {results ? (
          <Tabs defaultValue="whatif">
            <TabsList>
              <TabsTrigger value="whatif">
                <FlaskConical className="mr-1.5 h-3.5 w-3.5" />
                What-If
              </TabsTrigger>
              <TabsTrigger value="predictor">Sulfidity Predictor</TabsTrigger>
            </TabsList>
            <TabsContent value="whatif">
              <ScenarioBuilder inputs={buildFullRequest()} baseResults={results} millConfig={millConfig} />
            </TabsContent>
            <TabsContent value="predictor">
              <SulfidityPredictor inputs={buildFullRequest()} baseResults={results} millConfig={millConfig} />
            </TabsContent>
          </Tabs>
        ) : loading ? (
          <div className="py-12 text-center font-mono text-sm text-muted-foreground">
            Loading base calculation...
          </div>
        ) : (
          <div className="py-12 text-center font-mono text-sm text-muted-foreground">
            Computing base results...
          </div>
        )}
      </PageContainer>
    </>
  );
}
