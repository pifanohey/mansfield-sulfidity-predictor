"use client";

import InputField from "./InputField";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, Calculator } from "lucide-react";

interface Props {
  blNaPct: number;
  blSPct: number;
  blKPct: number;
  onChange: (key: string, value: number) => void;
  // Optional: computed values from results
  computedNaPct?: number;
  computedSPct?: number;
}

export default function BLCompositionSection({
  blNaPct,
  blSPct,
  blKPct,
  onChange,
  computedNaPct,
  computedSPct,
}: Props) {
  return (
    <div className="space-y-4">
      {/* Info banner explaining computed values */}
      <div className="flex items-start gap-2 rounded-md border border-amber-400/20 bg-amber-400/[0.04] p-3 text-sm">
        <AlertCircle className="h-4 w-4 text-amber-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="font-medium text-amber-300">BL Na% and S% are computed by the model</p>
          <p className="text-amber-400/70 mt-1">
            Lab values below serve as initial guesses. The model calculates actual values
            from the forward leg (WL → Digesters → Evaporator → SBL).
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {/* BL Na% with computed indicator */}
        <div className="space-y-1">
          <InputField
            label="BL Na % (Lab)"
            value={blNaPct}
            onChange={(v) => onChange("bl_na_pct", v)}
            unit="%"
            excelRef="2_RB!B6"
            step={0.01}
          />
          {computedNaPct !== undefined && (
            <div className="flex items-center gap-1.5 text-xs">
              <Calculator className="h-3 w-3 text-emerald-400" />
              <span className="text-muted-foreground">Computed:</span>
              <Badge variant="secondary" className="font-mono text-xs">
                {computedNaPct.toFixed(2)}%
              </Badge>
            </div>
          )}
        </div>

        {/* BL S% with computed indicator */}
        <div className="space-y-1">
          <InputField
            label="BL S % (Lab)"
            value={blSPct}
            onChange={(v) => onChange("bl_s_pct", v)}
            unit="%"
            excelRef="2_RB!B7"
            step={0.01}
          />
          {computedSPct !== undefined && (
            <div className="flex items-center gap-1.5 text-xs">
              <Calculator className="h-3 w-3 text-emerald-400" />
              <span className="text-muted-foreground">Computed:</span>
              <Badge variant="secondary" className="font-mono text-xs">
                {computedSPct.toFixed(2)}%
              </Badge>
            </div>
          )}
        </div>

        {/* BL K% - active input, no computed override */}
        <div className="space-y-1">
          <InputField
            label="BL K %"
            value={blKPct}
            onChange={(v) => onChange("bl_k_pct", v)}
            unit="%"
            excelRef="2_RB!B8"
            step={0.01}
          />
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="w-3 h-3 rounded-full bg-emerald-400 flex-shrink-0" />
            <span>Active input</span>
          </div>
        </div>
      </div>
    </div>
  );
}
