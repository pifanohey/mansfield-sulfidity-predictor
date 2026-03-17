"use client";

import InputField from "./InputField";
import type { TankLevels } from "@/lib/types";

interface TankConfig {
  id: string;
  name: string;
  max_level: number;
  gal_per_ft: number;
  group: string;
}

interface Props {
  levels: TankLevels;
  onChange: (key: string, value: number) => void;
  tanks?: TankConfig[];
}

export default function TankLevelSection({ levels, onChange, tanks }: Props) {
  if (!tanks || tanks.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No tanks configured for this mill.
      </p>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {tanks.map((tank) => (
        <InputField
          key={tank.id}
          label={tank.name}
          value={levels[tank.id] ?? 0}
          onChange={(v) => onChange(tank.id, v)}
          unit="ft"
          step={0.1}
          min={0}
          max={tank.max_level}
        />
      ))}
    </div>
  );
}
