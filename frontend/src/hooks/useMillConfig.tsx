"use client";

import { useState, useEffect } from "react";
import type { MillConfig } from "@/lib/types";
import { fetchMillConfig } from "@/lib/api";

export function useMillConfig() {
  const [config, setConfig] = useState<MillConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMillConfig()
      .then(setConfig)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return { config, loading };
}
