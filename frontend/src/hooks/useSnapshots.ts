"use client";

import { useState, useCallback } from "react";
import type { Snapshot, CalculationRequest } from "@/lib/types";
import { listSnapshots, saveSnapshot, deleteSnapshot } from "@/lib/api";

export function useSnapshots() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSnapshots = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSnapshots();
      setSnapshots(data);
    } catch (e) {
      console.error("Failed to fetch snapshots:", e);
      setError("Failed to load snapshots.");
    } finally {
      setLoading(false);
    }
  }, []);

  const save = useCallback(
    async (
      inputs: CalculationRequest,
      results?: Record<string, unknown>,
      notes?: string
    ) => {
      const snap = await saveSnapshot(inputs, results, notes);
      setSnapshots((prev) => [snap, ...prev]);
      return snap;
    },
    []
  );

  const remove = useCallback(async (id: number) => {
    await deleteSnapshot(id);
    setSnapshots((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { snapshots, loading, error, fetchSnapshots, save, remove };
}
