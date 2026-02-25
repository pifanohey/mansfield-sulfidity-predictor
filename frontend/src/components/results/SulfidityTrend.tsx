"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTrendData } from "@/hooks/useTrendData";
import type { TrendPoint } from "@/lib/types";

const RANGE_OPTIONS = [
  { label: "24h", hours: 24 },
  { label: "7d", hours: 168 },
  { label: "30d", hours: 720 },
  { label: "All", hours: 0 },
];

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    " " +
    d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: TrendPoint }>;
}

function ChartTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-white/[0.1] bg-[hsl(232,25%,14%)] p-3 font-mono text-xs shadow-xl">
      <div className="font-medium text-white">{formatTimestamp(p.timestamp)}</div>
      <div className="mt-1.5 text-cyan">
        Model: {p.predicted_sulfidity_pct.toFixed(2)}%
      </div>
      {p.lab_sulfidity_pct != null && (
        <>
          <div className="text-amber-400">
            Lab: {p.lab_sulfidity_pct.toFixed(2)}%
          </div>
          <div className="text-muted-foreground">
            Delta: {(p.predicted_sulfidity_pct - p.lab_sulfidity_pct).toFixed(2)}%
          </div>
        </>
      )}
      <div className="mt-1.5 text-muted-foreground">
        NaSH: {p.nash_dry_lb_hr.toFixed(0)} lb/hr | NaOH: {p.naoh_dry_lb_hr.toFixed(0)} lb/hr
      </div>
      {p.notes && <div className="mt-1 italic text-muted-foreground">{p.notes}</div>}
    </div>
  );
}

interface PointEditorProps {
  point: TrendPoint;
  onSave: (id: number, patch: { lab_sulfidity_pct?: number | null; notes?: string }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onClose: () => void;
}

function PointEditor({ point, onSave, onDelete, onClose }: PointEditorProps) {
  const [lab, setLab] = useState(point.lab_sulfidity_pct?.toString() ?? "");
  const [notes, setNotes] = useState(point.notes ?? "");
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(point.id, {
        lab_sulfidity_pct: lab.trim() === "" ? null : parseFloat(lab),
        notes,
      });
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setSaving(true);
    try {
      await onDelete(point.id);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs font-medium text-white">
          Edit Point — {formatTimestamp(point.timestamp)}
        </span>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-6 px-2 text-xs">
          Close
        </Button>
      </div>
      <div className="font-mono text-[10px] text-muted-foreground mb-2">
        Model: {point.predicted_sulfidity_pct.toFixed(2)}% | Smelt: {point.smelt_sulfidity_pct.toFixed(2)}%
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Lab Sulfidity %</Label>
          <Input
            type="number"
            step="0.01"
            placeholder="e.g. 29.2"
            value={lab}
            onChange={(e) => setLab(e.target.value)}
            className="mt-1 h-8"
          />
        </div>
        <div>
          <Label className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">Notes</Label>
          <Input
            type="text"
            placeholder="optional"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="mt-1 h-8"
          />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={handleSave} disabled={saving} className="h-7 text-xs">
          {saving ? "Saving..." : "Save"}
        </Button>
        <Button
          size="sm"
          variant={confirmDelete ? "destructive" : "outline"}
          onClick={handleDelete}
          disabled={saving}
          className="h-7 text-xs"
        >
          {confirmDelete ? "Confirm Delete" : "Delete"}
        </Button>
      </div>
    </div>
  );
}

interface Props {
  refreshTrigger?: unknown;
}

export default function SulfidityTrend({ refreshTrigger }: Props) {
  const { points, loading, hours, setHours, editPoint, removePoint } = useTrendData(refreshTrigger);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const selectedPoint = points.find((p) => p.id === selectedId) ?? null;

  const chartData = points.map((p) => ({
    ...p,
    lab: p.lab_sulfidity_pct,
  }));

  const allValues = points.flatMap((p) =>
    [p.predicted_sulfidity_pct, p.lab_sulfidity_pct, p.target_sulfidity_pct].filter(
      (v): v is number => v != null
    )
  );
  const yMin = allValues.length ? Math.floor(Math.min(...allValues) - 1) : 25;
  const yMax = allValues.length ? Math.ceil(Math.max(...allValues) + 1) : 35;

  const targetLine = points.length > 0 ? points[0].target_sulfidity_pct : 29.4;

  const handleDotClick = (data: TrendPoint) => {
    setSelectedId(data.id === selectedId ? null : data.id);
  };

  if (points.length === 0 && !loading) {
    return (
      <Card className="mt-4">
        <CardHeader className="pb-2">
          <CardTitle>Sulfidity Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs text-muted-foreground">
            No trend data yet. Run a prediction and save to start tracking.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mt-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle>Sulfidity Trend (Model vs Lab)</CardTitle>
          <div className="flex gap-1">
            {RANGE_OPTIONS.map((opt) => (
              <Button
                key={opt.label}
                variant={hours === opt.hours ? "default" : "outline"}
                size="sm"
                className="h-6 px-2 font-mono text-[10px]"
                onClick={() => setHours(opt.hours)}
              >
                {opt.label}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading && points.length === 0 ? (
          <div className="flex h-48 items-center justify-center font-mono text-xs text-muted-foreground">
            Loading...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
              onClick={(e) => {
                if (e?.activePayload?.[0]?.payload) {
                  handleDotClick(e.activePayload[0].payload as TrendPoint);
                }
              }}
              style={{ cursor: "pointer" }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)", fontFamily: "var(--font-mono)" }}
                interval="preserveStartEnd"
                stroke="rgba(255,255,255,0.06)"
              />
              <YAxis
                domain={[yMin, yMax]}
                tick={{ fontSize: 10, fill: "rgba(255,255,255,0.4)", fontFamily: "var(--font-mono)" }}
                unit="%"
                stroke="rgba(255,255,255,0.06)"
              />
              <Tooltip content={<ChartTooltip />} />
              <ReferenceLine
                y={targetLine}
                stroke="rgba(255,255,255,0.2)"
                strokeDasharray="6 4"
                label={{ value: "Target", position: "right", fontSize: 10, fill: "rgba(255,255,255,0.3)" }}
              />
              <Line
                type="monotone"
                dataKey="predicted_sulfidity_pct"
                stroke="#5EEAD4"
                strokeWidth={2}
                dot={{ r: 4, fill: "#5EEAD4", cursor: "pointer" }}
                activeDot={{ r: 6 }}
                name="Model"
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="lab"
                stroke="#F59E0B"
                strokeWidth={0}
                dot={{ r: 5, fill: "#F59E0B", stroke: "hsl(232,25%,10%)", strokeWidth: 2 }}
                activeDot={{ r: 7 }}
                name="Lab"
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {/* Legend */}
        <div className="mt-2 flex items-center gap-4 font-mono text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-4 rounded bg-cyan" /> Model Predicted
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-3 w-3 rounded-full bg-amber-400" /> Lab Measured
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-0.5 w-4 border-t border-dashed border-white/20" /> Target
          </span>
          <span className="ml-auto tabular-nums">{points.length} points</span>
        </div>

        {selectedPoint && (
          <PointEditor
            point={selectedPoint}
            onSave={editPoint}
            onDelete={removePoint}
            onClose={() => setSelectedId(null)}
          />
        )}
      </CardContent>
    </Card>
  );
}
