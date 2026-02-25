"use client";

import { useMemo } from "react";
import type { GuidanceItem, CalculationResponse } from "@/lib/types";

export function useGuidance(results: CalculationResponse | null) {
  const grouped = useMemo(() => {
    if (!results?.guidance) return { red: [], yellow: [], green: [] };
    const red: GuidanceItem[] = [];
    const yellow: GuidanceItem[] = [];
    const green: GuidanceItem[] = [];
    for (const g of results.guidance) {
      if (g.severity === "red") red.push(g);
      else if (g.severity === "yellow") yellow.push(g);
      else green.push(g);
    }
    return { red, yellow, green };
  }, [results]);

  return { guidance: results?.guidance ?? [], grouped };
}
