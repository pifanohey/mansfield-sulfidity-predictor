"use client";

import { useState, useEffect } from "react";
import type { MillConfig } from "@/lib/types";
import { fetchMillConfig } from "@/lib/api";

export function useMillConfig() {
  const [config, setConfig] = useState<MillConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMillConfig()
      .then(setConfig)
      .catch((err) => {
        console.error("Failed to load mill config:", err);
        setError(err instanceof Error ? err.message : "Failed to load mill config");
      })
      .finally(() => setLoading(false));
  }, []);

  return { config, loading, error };
}
