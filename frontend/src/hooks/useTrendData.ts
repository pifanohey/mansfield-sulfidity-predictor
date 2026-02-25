"use client";

import { useState, useEffect, useCallback } from "react";
import type { TrendPoint } from "@/lib/types";
import { listTrends, updateTrend, deleteTrend } from "@/lib/api";

export function useTrendData(refreshTrigger?: unknown, initialHours = 168) {
  const [points, setPoints] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hours, setHours] = useState(initialHours);

  const fetchPoints = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTrends(hours);
      setPoints(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load trends");
    } finally {
      setLoading(false);
    }
  }, [hours]);

  // Fetch on mount, when hours changes, or when refreshTrigger changes
  useEffect(() => {
    fetchPoints();
  }, [fetchPoints, refreshTrigger]);

  const editPoint = useCallback(
    async (id: number, patch: { lab_sulfidity_pct?: number | null; notes?: string }) => {
      await updateTrend(id, patch);
      await fetchPoints();
    },
    [fetchPoints]
  );

  const removePoint = useCallback(
    async (id: number) => {
      await deleteTrend(id);
      await fetchPoints();
    },
    [fetchPoints]
  );

  return { points, loading, error, hours, setHours, refresh: fetchPoints, editPoint, removePoint };
}
