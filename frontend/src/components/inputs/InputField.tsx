"use client";

import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

interface InputFieldProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  unit?: string;
  excelRef?: string;
  step?: number;
  min?: number;
  max?: number;
}

export default function InputField({
  label,
  value,
  onChange,
  unit,
  excelRef,
  step = 0.01,
  min,
  max,
}: InputFieldProps) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <label className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
            {label}
          </label>
          {excelRef && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="cursor-help font-mono text-[9px] text-white/20">
                  [{excelRef}]
                </span>
              </TooltipTrigger>
              <TooltipContent>Excel ref: {excelRef}</TooltipContent>
            </Tooltip>
          )}
        </div>
        {unit && (
          <span className="font-mono text-[10px] text-muted-foreground">
            {unit}
          </span>
        )}
      </div>
      <Input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        step={step}
        min={min}
        max={max}
        className="h-8 text-xs"
      />
    </div>
  );
}
