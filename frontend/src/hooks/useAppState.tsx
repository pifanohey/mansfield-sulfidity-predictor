"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { CalculationRequest, CalculationResponse, MillConfig } from "@/lib/types";
import type { FiberlineInputState } from "@/components/inputs/ProductionSection";
import { DEFAULT_INPUTS } from "@/lib/defaults";
import { calculate } from "@/lib/api";

interface AppState {
  inputs: CalculationRequest;
  results: CalculationResponse | null;
  loading: boolean;
  error: string | null;
  millConfig: MillConfig | null;
  fiberlineInputs: Record<string, FiberlineInputState>;
  updateField: <K extends keyof CalculationRequest>(
    key: K,
    value: CalculationRequest[K]
  ) => void;
  updateNestedField: (section: string, key: string, value: unknown) => void;
  updateFiberlineField: (fiberlineId: string, key: string, value: number) => void;
  setMillConfig: (config: MillConfig) => void;
  resetToDefaults: () => void;
  runCalculation: (inputs?: CalculationRequest) => Promise<CalculationResponse | null>;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [inputs, setInputs] = useState<CalculationRequest>({ ...DEFAULT_INPUTS });
  const [results, setResults] = useState<CalculationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [millConfig, setMillConfig] = useState<MillConfig | null>(null);
  const [fiberlineInputs, setFiberlineInputs] = useState<Record<string, FiberlineInputState>>({});

  const updateField = useCallback(
    <K extends keyof CalculationRequest>(key: K, value: CalculationRequest[K]) => {
      setInputs((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const updateNestedField = useCallback(
    (section: string, key: string, value: unknown) => {
      setInputs((prev) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const existing = (prev as any)[section];
        if (existing && typeof existing === "object") {
          return { ...prev, [section]: { ...existing, [key]: value } };
        }
        return { ...prev, [section]: { [key]: value } };
      });
    },
    []
  );

  const updateFiberlineField = useCallback(
    (fiberlineId: string, key: string, value: number) => {
      setFiberlineInputs((prev) => ({
        ...prev,
        [fiberlineId]: {
          ...prev[fiberlineId],
          [key]: value,
        },
      }));
    },
    []
  );

  const resetToDefaults = useCallback(() => {
    setInputs({ ...DEFAULT_INPUTS });
    setFiberlineInputs({});
    setResults(null);
  }, []);

  const runCalculation = useCallback(
    async (overrideInputs?: CalculationRequest) => {
      let inp = overrideInputs ?? inputs;

      // If mill config is available, build the V2 fiberlines array
      if (millConfig && !overrideInputs) {
        const fiberlines = millConfig.fiberlines.map((fl) => ({
          id: fl.id,
          production_bdt_day:
            fiberlineInputs[fl.id]?.production_bdt_day ?? fl.defaults.production_bdt_day,
          yield_pct:
            fiberlineInputs[fl.id]?.yield_pct ?? fl.defaults.yield_pct,
          ea_pct:
            fiberlineInputs[fl.id]?.ea_pct ?? fl.defaults.ea_pct,
          gl_ea_pct: fl.uses_gl_charge
            ? (fiberlineInputs[fl.id]?.gl_ea_pct ?? fl.defaults.gl_ea_pct)
            : undefined,
        }));
        inp = { ...inp, fiberlines };
      }

      setLoading(true);
      setError(null);
      try {
        const res = await calculate(inp);
        setResults(res);
        return res;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Calculation failed";
        setError(msg);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [inputs, millConfig, fiberlineInputs]
  );

  return (
    <AppStateContext.Provider
      value={{
        inputs,
        results,
        loading,
        error,
        millConfig,
        fiberlineInputs,
        updateField,
        updateNestedField,
        updateFiberlineField,
        setMillConfig,
        resetToDefaults,
        runCalculation,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return ctx;
}
