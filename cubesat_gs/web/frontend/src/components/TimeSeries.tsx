import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api } from "@/api/client";
import type { TelemetryHistoryOut } from "@/api/types";
import { utc } from "@/lib/time";
import { lttb } from "@/lib/lttb";

const MAX_POINTS = 600;

export type SeriesWindow = "1h" | "6h" | "24h" | { start: string; end: string };

const WINDOW_MS: Record<"1h" | "6h" | "24h", number> = { "1h": 3_600_000, "6h": 6 * 3_600_000, "24h": 24 * 3_600_000 };

/**
 * Resolves a `SeriesWindow` to concrete ISO bounds — shared with callers that need the same `queryKey` for cache reuse.
 * `end` is floored to the minute so the result stays stable across re-renders for the lifetime of an open window.
 */
export function windowRange(window: SeriesWindow): { start: string; end: string } {
  if (typeof window === "object") return window;
  const end = Math.floor(Date.now() / 60_000) * 60_000;
  return { start: new Date(end - WINDOW_MS[window]).toISOString(), end: new Date(end).toISOString() };
}

/** Merges fetched history with live points newer than the last history point, thinned to `maxPoints`. */
export function mergePoints(history: TelemetryHistoryOut | undefined, live: [number, number][], maxPoints = MAX_POINTS): [number, number][] {
  const hist: [number, number][] = (history?.points ?? []).map((p) => [Date.parse(p.t), p.v]);
  const lastHistoryT = hist.length ? hist[hist.length - 1][0] : -Infinity;
  const merged = [...hist, ...live.filter(([t]) => t > lastHistoryT)];
  return lttb(merged, maxPoints);
}

function TooltipContent({ active, payload }: { active?: boolean; payload?: { value: number; payload: { t: number } }[] }) {
  if (!active || !payload || payload.length === 0) return null;
  const { value, payload: pt } = payload[0];
  return (
    <div className="panel border-line px-2 py-1 text-[12px]">
      <div className="text-dim font-mono">{utc(new Date(pt.t).toISOString())}</div>
      <div className="font-mono tabular-nums">{value}</div>
    </div>
  );
}

/**
 * Time-series line chart for one telemetry field: fetches `/api/telemetry/history` for the window,
 * merges live points newer than the last history point, thins to <= MAX_POINTS with `lttb`.
 */
export function TimeSeries({
  apid,
  field,
  unit,
  start,
  end,
  live,
  alarmLow,
  alarmHigh,
}: {
  apid: number;
  field: string;
  unit?: string | null;
  start: string;
  end: string;
  live: [number, number][];
  alarmLow?: number | null;
  alarmHigh?: number | null;
}) {
  const { data } = useQuery({
    queryKey: ["telemetry-history", apid, field, start, end],
    queryFn: () => api.get<TelemetryHistoryOut>("/api/telemetry/history", { apid, field, start, end, max_points: MAX_POINTS }),
    staleTime: 30_000,
  });

  const points = useMemo(() => mergePoints(data, live).map(([t, v]) => ({ t, v })), [data, live]);

  if (points.length === 0) {
    return <div className="text-dim flex h-full items-center justify-center">No data in this window</div>;
  }

  const values = points.map((p) => p.v);
  const min = Math.min(...values, alarmLow ?? Infinity);
  const max = Math.max(...values, alarmHigh ?? -Infinity);
  const pad = (max - min) * 0.08 || 1;
  const domain: [number, number] = [min - pad, max + pad];

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={points} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="hsl(var(--line))" strokeDasharray="2 4" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(t: number) => utc(new Date(t).toISOString()).slice(11, 16)}
          tick={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fill: "hsl(var(--text-dim))" }}
          stroke="hsl(var(--line))"
        />
        <YAxis
          domain={domain}
          tick={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fill: "hsl(var(--text-dim))" }}
          stroke="hsl(var(--line))"
          width={48}
          unit={unit ?? undefined}
        />
        <Tooltip content={<TooltipContent />} />
        {alarmLow != null && (
          <ReferenceLine y={alarmLow} stroke="hsl(var(--alarm))" strokeDasharray="4 3" label={{ value: "low", position: "insideBottomLeft", fill: "hsl(var(--alarm))", fontSize: 11 }} />
        )}
        {alarmHigh != null && (
          <ReferenceLine y={alarmHigh} stroke="hsl(var(--alarm))" strokeDasharray="4 3" label={{ value: "high", position: "insideTopLeft", fill: "hsl(var(--alarm))", fontSize: 11 }} />
        )}
        <Line type="monotone" dataKey="v" stroke="hsl(var(--info))" strokeWidth={1.5} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
