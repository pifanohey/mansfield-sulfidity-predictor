"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import type {
  CalculationRequest,
  CalculationResponse,
  MillConfig,
  FiberlineInputState,
  RecoveryBoilerInputs,
} from "@/lib/types";
import { DEFAULT_INPUTS } from "@/lib/defaults";
import { calculate, fetchMillConfig } from "@/lib/api";

export interface DTInputState {
  ww_flow_gpm: number;
  ww_tta_lb_ft3: number;
  ww_sulfidity: number;
  shower_flow_gpm: number;
  smelt_density_lb_ft3: number;
}

interface AppState {
  inputs: CalculationRequest;
  results: CalculationResponse | null;
  loading: boolean;
  error: string | null;
  configReady: boolean;
  millConfig: MillConfig | null;
  fiberlineInputs: Record<string, FiberlineInputState>;
  rbInputs: Record<string, RecoveryBoilerInputs>;
  dtInputs: Record<string, DTInputState>;
  updateField: <K extends keyof CalculationRequest>(
    key: K,
    value: CalculationRequest[K]
  ) => void;
  updateNestedField: (section: string, key: string, value: unknown) => void;
  updateFiberlineField: (fiberlineId: string, key: string, value: number) => void;
  updateRBField: (rbId: string, key: string, value: number) => void;
  updateDTField: (dtId: string, key: string, value: number) => void;
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
  const [configReady, setConfigReady] = useState(false);
  const [millConfig, setMillConfigRaw] = useState<MillConfig | null>(null);
  const [fiberlineInputs, setFiberlineInputs] = useState<Record<string, FiberlineInputState>>({});
  const [rbInputs, setRBInputs] = useState<Record<string, RecoveryBoilerInputs>>({});
  const [dtInputs, setDTInputs] = useState<Record<string, DTInputState>>({});
  const configLoadedRef = useRef(false);

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

  const updateRBField = useCallback(
    (rbId: string, key: string, value: number) => {
      setRBInputs((prev) => ({
        ...prev,
        [rbId]: {
          ...prev[rbId],
          [key]: value,
        },
      }));
    },
    []
  );

  const updateDTField = useCallback(
    (dtId: string, key: string, value: number) => {
      setDTInputs((prev) => ({
        ...prev,
        [dtId]: {
          ...prev[dtId],
          [key]: value,
        },
      }));
    },
    []
  );

  const applyMillDefaults = useCallback((config: MillConfig) => {
    const d = config.defaults;
    if (!d) return;

    const GL_TO_LB_FT3 = 1 / 16.01846;

    // Initialize per-RB inputs from config defaults
    const newRBInputs: Record<string, RecoveryBoilerInputs> = {};
    for (const rb of config.recovery_boilers) {
      newRBInputs[rb.id] = {
        bl_flow_gpm: rb.defaults.bl_flow_gpm ?? d.bl_flow_gpm ?? 340.53,
        bl_tds_pct: rb.defaults.bl_tds_pct ?? d.bl_tds_pct ?? 69.1,
        bl_temp_f: rb.defaults.bl_temp_f ?? d.bl_temp_f ?? 253.5,
        reduction_eff_pct: rb.defaults.reduction_eff_pct ?? d.reduction_efficiency_pct ?? 95.0,
        ash_recycled_pct: rb.defaults.ash_recycled_pct ?? d.ash_recycled_pct ?? 0.07,
        saltcake_flow_lb_hr: rb.defaults.saltcake_flow_lb_hr ?? d.saltcake_flow_lb_hr ?? 0,
      };
    }
    setRBInputs(newRBInputs);

    // Initialize per-DT inputs from config defaults
    const newDTInputs: Record<string, DTInputState> = {};
    for (const dt of config.dissolving_tanks) {
      newDTInputs[dt.id] = {
        ww_flow_gpm: dt.defaults.ww_flow_gpm ?? d.ww_flow_gpm ?? 625.0,
        ww_tta_lb_ft3: dt.defaults.ww_tta_lb_ft3 ?? d.ww_tta_lb_ft3 ?? 1.07978,
        ww_sulfidity: dt.defaults.ww_sulfidity ?? d.ww_sulfidity ?? 0.255,
        shower_flow_gpm: dt.defaults.shower_flow_gpm ?? d.shower_flow_gpm ?? 60.0,
        smelt_density_lb_ft3: dt.defaults.smelt_density_lb_ft3 ?? d.smelt_density_lb_ft3 ?? 110.0,
      };
    }
    setDTInputs(newDTInputs);

    setInputs((prev) => {
      const updates: Partial<CalculationRequest> = {};

      // BL composition
      if (d.bl_na_pct != null) updates.bl_na_pct = d.bl_na_pct;
      if (d.bl_s_pct != null) updates.bl_s_pct = d.bl_s_pct;
      if (d.bl_k_pct != null) updates.bl_k_pct = d.bl_k_pct;

      // Recovery boiler (global/flat — used for single-RB mills)
      if (d.bl_flow_gpm != null || d.bl_tds_pct != null) {
        updates.recovery_boiler = {
          bl_flow_gpm: d.bl_flow_gpm ?? prev.recovery_boiler?.bl_flow_gpm ?? 340.53,
          bl_tds_pct: d.bl_tds_pct ?? prev.recovery_boiler?.bl_tds_pct ?? 69.1,
          bl_temp_f: d.bl_temp_f ?? prev.recovery_boiler?.bl_temp_f ?? 253.5,
          reduction_eff_pct: d.reduction_efficiency_pct ?? prev.recovery_boiler?.reduction_eff_pct ?? 95.0,
          ash_recycled_pct: d.ash_recycled_pct ?? prev.recovery_boiler?.ash_recycled_pct ?? 0.07,
          saltcake_flow_lb_hr: d.saltcake_flow_lb_hr ?? prev.recovery_boiler?.saltcake_flow_lb_hr ?? 2227.0,
        };
      }

      // Dissolving tank (global/flat — used for single-DT mills)
      if (d.ww_flow_gpm != null) updates.ww_flow_gpm = d.ww_flow_gpm;
      if (d.ww_tta_lb_ft3 != null) updates.ww_tta_lb_ft3 = d.ww_tta_lb_ft3;
      if (d.ww_sulfidity != null) updates.ww_sulfidity = d.ww_sulfidity;
      if (d.shower_flow_gpm != null) updates.shower_flow_gpm = d.shower_flow_gpm;
      if (d.smelt_density_lb_ft3 != null) updates.smelt_density_lb_ft3 = d.smelt_density_lb_ft3;
      if (d.gl_target_tta_lb_ft3 != null) updates.gl_target_tta_lb_ft3 = d.gl_target_tta_lb_ft3;
      if (d.gl_causticity != null) updates.gl_causticity = d.gl_causticity;

      // WL/GL analysis (config stores g/L, frontend stores lb/ft³)
      if (d.wl_tta != null) {
        updates.wl_analysis = {
          tta: d.wl_tta * GL_TO_LB_FT3,
          ea: (d.wl_ea ?? 0) * GL_TO_LB_FT3,
          aa: (d.wl_aa ?? 0) * GL_TO_LB_FT3,
        };
      }
      if (d.gl_tta != null) {
        updates.gl_analysis = {
          tta: d.gl_tta * GL_TO_LB_FT3,
          ea: (d.gl_ea ?? 0) * GL_TO_LB_FT3,
          aa: (d.gl_aa ?? 0) * GL_TO_LB_FT3,
        };
      }

      // Setpoints
      if (d.target_sulfidity_pct != null) updates.target_sulfidity_pct = d.target_sulfidity_pct;
      if (d.causticity_pct != null) updates.causticity_pct = d.causticity_pct;
      if (d.cooking_wl_sulfidity != null) updates.cooking_wl_sulfidity = d.cooking_wl_sulfidity;

      // CTO
      if (d.cto_h2so4_per_ton != null) updates.cto_h2so4_per_ton = d.cto_h2so4_per_ton;
      if (d.cto_tpd != null) updates.cto_tpd = d.cto_tpd;
      if (d.cto_naoh_per_ton != null) updates.cto_naoh_per_ton = d.cto_naoh_per_ton;

      // Makeup
      if (d.nash_concentration != null) updates.nash_concentration = d.nash_concentration;
      if (d.naoh_concentration != null) updates.naoh_concentration = d.naoh_concentration;
      if (d.nash_density != null) updates.nash_density = d.nash_density;
      if (d.naoh_density != null) updates.naoh_density = d.naoh_density;

      // Recausticizing
      if (d.lime_charge_ratio != null) updates.lime_charge_ratio = d.lime_charge_ratio;
      if (d.cao_in_lime_pct != null) updates.cao_in_lime_pct = d.cao_in_lime_pct;
      if (d.caco3_in_lime_pct != null) updates.caco3_in_lime_pct = d.caco3_in_lime_pct;
      if (d.inerts_in_lime_pct != null) updates.inerts_in_lime_pct = d.inerts_in_lime_pct;
      if (d.grits_loss_pct != null) updates.grits_loss_pct = d.grits_loss_pct;
      if (d.lime_temp_f != null) updates.lime_temp_f = d.lime_temp_f;
      if (d.slaker_temp_f != null) updates.slaker_temp_f = d.slaker_temp_f;
      if (d.intrusion_water_gpm != null) updates.intrusion_water_gpm = d.intrusion_water_gpm;
      if (d.dilution_water_gpm != null) updates.dilution_water_gpm = d.dilution_water_gpm;
      if (d.wlc_underflow_solids_pct != null) updates.wlc_underflow_solids_pct = d.wlc_underflow_solids_pct;
      if (d.wlc_mud_density != null) updates.wlc_mud_density = d.wlc_mud_density;
      if (d.dregs_lb_bdt != null) updates.dregs_lb_bdt = d.dregs_lb_bdt;
      if (d.glc_underflow_solids_pct != null) updates.glc_underflow_solids_pct = d.glc_underflow_solids_pct;
      if (d.grits_lb_bdt != null) updates.grits_lb_bdt = d.grits_lb_bdt;
      if (d.grits_solids_pct != null) updates.grits_solids_pct = d.grits_solids_pct;

      // Loss table (config uses loss_<source>_s / loss_<source>_na keys)
      const lossKeys = [
        'pulp_washable_soda', 'pulp_bound_soda', 'pulp_mill_spills', 'evap_spill',
        'rb_ash', 'rb_stack', 'dregs_filter', 'grits', 'weak_wash_overflow', 'ncg',
        'recaust_spill', 'rb_dump_tank', 'kiln_scrubber', 'truck_out_gl', 'unaccounted',
      ] as const;
      const hasAnyLoss = lossKeys.some(
        (k) => (d as Record<string, unknown>)[`loss_${k}_s`] != null
      );
      if (hasAnyLoss && prev.loss_table) {
        const lt = { ...prev.loss_table };
        for (const k of lossKeys) {
          const sVal = (d as Record<string, unknown>)[`loss_${k}_s`];
          const naVal = (d as Record<string, unknown>)[`loss_${k}_na`];
          if (sVal != null || naVal != null) {
            lt[k] = {
              s_lb_bdt: (sVal as number) ?? lt[k].s_lb_bdt,
              na_lb_bdt: (naVal as number) ?? lt[k].na_lb_bdt,
            };
          }
        }
        updates.loss_table = lt;
      }

      return { ...prev, ...updates };
    });
  }, []);

  const setMillConfig = useCallback((config: MillConfig) => {
    setMillConfigRaw(config);
    applyMillDefaults(config);
  }, [applyMillDefaults]);

  // Auto-load mill config on mount so all pages get correct defaults
  useEffect(() => {
    if (configLoadedRef.current) return;
    configLoadedRef.current = true;
    fetchMillConfig()
      .then((config) => {
        setMillConfigRaw(config);
        applyMillDefaults(config);
        setConfigReady(true);
      })
      .catch((err) => {
        console.error("Failed to load mill config:", err);
        setConfigReady(true); // proceed with defaults on error
      });
  }, [applyMillDefaults]);

  const resetToDefaults = useCallback(() => {
    setInputs({ ...DEFAULT_INPUTS });
    setFiberlineInputs({});
    setRBInputs({});
    setDTInputs({});
    setResults(null);
  }, []);

  const runCalculation = useCallback(
    async (overrideInputs?: CalculationRequest) => {
      let inp = overrideInputs ?? inputs;

      // If mill config is available, build the V2 arrays
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

        // Multi-RB: send per-RB overrides from editable state
        if (millConfig.recovery_boilers?.length > 1) {
          const recovery_boilers = millConfig.recovery_boilers.map((rb) => ({
            id: rb.id,
            bl_flow_gpm: rbInputs[rb.id]?.bl_flow_gpm,
            bl_tds_pct: rbInputs[rb.id]?.bl_tds_pct,
            bl_temp_f: rbInputs[rb.id]?.bl_temp_f,
            reduction_eff_pct: rbInputs[rb.id]?.reduction_eff_pct,
            ash_recycled_pct: rbInputs[rb.id]?.ash_recycled_pct,
            saltcake_flow_lb_hr: rbInputs[rb.id]?.saltcake_flow_lb_hr,
          }));
          inp = { ...inp, recovery_boilers };
        }

        // Multi-DT: send per-DT overrides from editable state
        if (millConfig.dissolving_tanks?.length > 1) {
          const dissolving_tanks = millConfig.dissolving_tanks.map((dt) => ({
            id: dt.id,
            ww_flow_gpm: dtInputs[dt.id]?.ww_flow_gpm,
            ww_tta_lb_ft3: dtInputs[dt.id]?.ww_tta_lb_ft3,
            ww_sulfidity: dtInputs[dt.id]?.ww_sulfidity,
            shower_flow_gpm: dtInputs[dt.id]?.shower_flow_gpm,
            smelt_density_lb_ft3: dtInputs[dt.id]?.smelt_density_lb_ft3,
          }));
          inp = { ...inp, dissolving_tanks };
        }
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
    [inputs, millConfig, fiberlineInputs, rbInputs, dtInputs]
  );

  return (
    <AppStateContext.Provider
      value={{
        inputs,
        results,
        loading,
        error,
        configReady,
        millConfig,
        fiberlineInputs,
        rbInputs,
        dtInputs,
        updateField,
        updateNestedField,
        updateFiberlineField,
        updateRBField,
        updateDTField,
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
