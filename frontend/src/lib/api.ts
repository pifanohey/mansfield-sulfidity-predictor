import type {
  CalculationRequest,
  CalculationResponse,
  LiquorAnalysis,
  WhatIfResponse,
  SensitivityResponse,
  SensitivityItem,
  Snapshot,
  MillConfig,
  TrendPointCreate,
  TrendPoint,
} from "./types";

const BASE = "/api";

// Frontend stores WL/GL analysis in lb/ft³ (DCS units).
// Engine expects g/L. Convert before every API call.
const LB_FT3_TO_GL = 16.01846;

function analysisToGL(a: LiquorAnalysis): LiquorAnalysis {
  return {
    tta: a.tta * LB_FT3_TO_GL,
    ea: a.ea * LB_FT3_TO_GL,
    aa: a.aa * LB_FT3_TO_GL,
  };
}

function convertInputsForApi(inputs: CalculationRequest): CalculationRequest {
  return {
    ...inputs,
    wl_analysis: inputs.wl_analysis ? analysisToGL(inputs.wl_analysis) : undefined,
    gl_analysis: inputs.gl_analysis ? analysisToGL(inputs.gl_analysis) : undefined,
  };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export async function calculate(
  inputs: CalculationRequest
): Promise<CalculationResponse> {
  return request<CalculationResponse>("/calculate", {
    method: "POST",
    body: JSON.stringify(convertInputsForApi(inputs)),
  });
}

export async function whatIf(
  base: CalculationRequest,
  overrides: Record<string, unknown>
): Promise<WhatIfResponse> {
  return request<WhatIfResponse>("/calculate/what-if", {
    method: "POST",
    body: JSON.stringify({ base: convertInputsForApi(base), overrides }),
  });
}

export async function sensitivity(
  inputs: CalculationRequest
): Promise<SensitivityResponse> {
  return request<SensitivityResponse>("/calculate/sensitivity", {
    method: "POST",
    body: JSON.stringify(convertInputsForApi(inputs)),
  });
}

export async function saveSnapshot(
  inputs: CalculationRequest,
  results?: Record<string, unknown>,
  notes?: string
): Promise<Snapshot> {
  return request<Snapshot>("/snapshots", {
    method: "POST",
    body: JSON.stringify({ inputs, results, notes: notes ?? "" }),
  });
}

export async function listSnapshots(
  millId = "pine_hill",
  limit = 50
): Promise<Snapshot[]> {
  return request<Snapshot[]>(
    `/snapshots?mill_id=${millId}&limit=${limit}`
  );
}

export async function getSnapshot(id: number): Promise<Snapshot> {
  return request<Snapshot>(`/snapshots/${id}`);
}

export async function deleteSnapshot(id: number): Promise<void> {
  await request(`/snapshots/${id}`, { method: "DELETE" });
}

export async function getMillConfig(
  millId = "pine_hill"
): Promise<MillConfig> {
  return request<MillConfig>(`/mills/${millId}/config`);
}

/** Fetch V2 mill config (fiberlines, makeup_chemical, defaults) */
export async function fetchMillConfig(): Promise<MillConfig> {
  return request<MillConfig>("/mill-config");
}

// ── Trend Points ─────────────────────────────────────────────────

export async function saveTrend(data: TrendPointCreate): Promise<TrendPoint> {
  return request<TrendPoint>("/trends", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listTrends(hours = 168): Promise<TrendPoint[]> {
  return request<TrendPoint[]>(`/trends?hours=${hours}`);
}

export async function updateTrend(
  id: number,
  patch: { lab_sulfidity_pct?: number | null; notes?: string }
): Promise<TrendPoint> {
  return request<TrendPoint>(`/trends/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export async function deleteTrend(id: number): Promise<void> {
  await request(`/trends/${id}`, { method: "DELETE" });
}

// ── Report Export ─────────────────────────────────────────────────

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function fetchExportBlob(
  endpoint: string,
  inputs: CalculationRequest,
  results: CalculationResponse,
  sensitivityItems?: SensitivityItem[],
  millName?: string,
): Promise<Blob> {
  const res = await fetch(`${BASE}/export/${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      inputs,
      results,
      sensitivity_items: sensitivityItems ?? null,
      mill_name: millName ?? "Pine Hill Mill",
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Export ${res.status}: ${text}`);
  }
  return res.blob();
}

export async function exportExcel(
  inputs: CalculationRequest,
  results: CalculationResponse,
  sensitivityItems?: SensitivityItem[],
  millName?: string,
): Promise<void> {
  const blob = await fetchExportBlob("excel", inputs, results, sensitivityItems, millName);
  downloadBlob(blob, "sulfidity_report.xlsx");
}

export async function exportPdf(
  inputs: CalculationRequest,
  results: CalculationResponse,
  sensitivityItems?: SensitivityItem[],
  millName?: string,
): Promise<void> {
  const blob = await fetchExportBlob("pdf", inputs, results, sensitivityItems, millName);
  downloadBlob(blob, "sulfidity_report.pdf");
}
