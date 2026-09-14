import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/api/client";
import type { TelemetryDefsOut, TelemetryField, TelemetryHistoryOut } from "@/api/types";
import { AlarmBadge } from "@/components/AlarmBadge";
import { Panel } from "@/components/Panel";
import { TimeSeries, mergePoints, windowRange, type SeriesWindow } from "@/components/TimeSeries";
import { Value } from "@/components/Value";
import { fmtValue } from "@/lib/format";
import { age } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useGs } from "@/store/gs";

type Selection = { apid: number; field: string } | null;
type WindowKey = "1h" | "6h" | "24h" | "custom";
const WINDOWS: WindowKey[] = ["1h", "6h", "24h", "custom"];

const ALARM_TONE: Record<"nominal" | "low" | "high", "nominal" | "warn" | "alarm"> = { nominal: "nominal", low: "warn", high: "alarm" };

function FieldRow({ field, selected, onSelect }: { field: TelemetryField; selected: boolean; onSelect?: () => void }) {
  const tone = ALARM_TONE[field.alarm ?? "nominal"];
  const body = (
    <>
      <span className="truncate">{field.name}</span>
      <span className="font-mono tabular-nums text-right">
        {fmtValue(field.value)}
        {field.unit ? <span className="text-dim ml-1">{field.unit}</span> : null}
      </span>
      <AlarmBadge tone={tone} text={field.alarm ?? "nominal"} />
    </>
  );
  const rowClass = cn("row grid grid-cols-[1fr_auto_64px] items-center gap-2 px-2 text-[13px]", selected && "bg-raised");
  return onSelect ? (
    <button type="button" onClick={onSelect} className={cn(rowClass, "w-full text-left hover:bg-raised")}>
      {body}
    </button>
  ) : (
    <div className={rowClass}>{body}</div>
  );
}

/** Left: one Panel per decoded APID with its fields. Right: a chart of the selected numeric field. */
export function Telemetry() {
  const telemetryLatest = useGs((s) => s.telemetryLatest);
  const series = useGs((s) => s.series);

  const [selection, setSelection] = useState<Selection>(null);
  const [windowKey, setWindowKey] = useState<WindowKey>("1h");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  const { data: defs } = useQuery({
    queryKey: ["telemetry-definitions"],
    queryFn: () => api.get<TelemetryDefsOut>("/api/telemetry/definitions"),
    staleTime: 60_000,
  });

  const apids = useMemo(() => Object.values(telemetryLatest).sort((a, b) => a.apid - b.apid), [telemetryLatest]);

  const fieldDef = useMemo(() => {
    if (!selection || !defs) return undefined;
    const d = defs.definitions.find((d) => d.apid === selection.apid);
    return d?.fields.find((f) => f.name === selection.field);
  }, [defs, selection]);

  const window: SeriesWindow = useMemo(() => {
    if (windowKey !== "custom") return windowKey;
    const end = customEnd ? new Date(customEnd).toISOString() : new Date().toISOString();
    const start = customStart ? new Date(customStart).toISOString() : new Date(Date.parse(end) - 3_600_000).toISOString();
    return { start, end };
  }, [windowKey, customStart, customEnd]);

  const live = selection ? series[`${selection.apid}:${selection.field}`] ?? [] : [];
  const { start, end } = windowRange(window);

  const { data: history } = useQuery({
    queryKey: ["telemetry-history", selection?.apid, selection?.field, start, end],
    queryFn: () => api.get<TelemetryHistoryOut>("/api/telemetry/history", { apid: selection?.apid, field: selection?.field, start, end, max_points: 600 }),
    enabled: selection != null,
    staleTime: 30_000,
  });

  const plotted = selection ? mergePoints(history, live) : [];
  const values = plotted.map(([, v]) => v);
  const min = values.length ? Math.min(...values) : null;
  const max = values.length ? Math.max(...values) : null;
  const last = values.length ? values[values.length - 1] : null;
  const selectedField = selection ? telemetryLatest[selection.apid]?.fields.find((f) => f.name === selection.field) : undefined;
  const unit = fieldDef?.unit ?? selectedField?.unit ?? null;

  return (
    <div className="grid grid-cols-12 gap-2">
      <div className="col-span-4 flex flex-col gap-2">
        {apids.length === 0 ? (
          <Panel title="Telemetry" bodyClassName="flex h-32 items-center justify-center">
            <p className="text-dim">No telemetry decoded yet</p>
          </Panel>
        ) : (
          apids.map((t) => (
            <Panel key={t.apid} title={`${t.apid_name} · APID ${t.apid}`} actions={<span className="label">{age(t.ts)} ago</span>}>
              <div>
                {t.fields.map((f) => (
                  <FieldRow
                    key={f.name}
                    field={f}
                    selected={selection?.apid === t.apid && selection?.field === f.name}
                    onSelect={typeof f.value === "number" ? () => setSelection({ apid: t.apid, field: f.name }) : undefined}
                  />
                ))}
              </div>
            </Panel>
          ))
        )}
      </div>

      <div className="col-span-8">
        <Panel
          title={selection ? `${selection.field} (${unit ?? "—"})` : "Chart"}
          className="h-full"
          bodyClassName="flex flex-col p-3"
          actions={
            selection && (
              <div className="flex gap-1" role="group" aria-label="Window">
                {WINDOWS.map((w) => (
                  <button
                    key={w}
                    type="button"
                    aria-pressed={windowKey === w}
                    className={cn("label rounded border border-line px-2 py-0.5", windowKey === w && "border-info text-info")}
                    onClick={() => setWindowKey(w)}
                  >
                    {w === "custom" ? "Custom" : w}
                  </button>
                ))}
              </div>
            )
          }
        >
          {!selection ? (
            <div className="text-dim flex h-full items-center justify-center">Select a numeric field to chart it</div>
          ) : (
            <div className="flex h-full flex-col gap-3">
              {windowKey === "custom" && (
                <div className="flex items-center gap-2">
                  <label className="label flex items-center gap-1">
                    From
                    <input
                      type="datetime-local"
                      className="bg-bg border-line rounded border px-1 font-mono text-[12px]"
                      value={customStart}
                      onChange={(e) => setCustomStart(e.target.value)}
                    />
                  </label>
                  <label className="label flex items-center gap-1">
                    To
                    <input
                      type="datetime-local"
                      className="bg-bg border-line rounded border px-1 font-mono text-[12px]"
                      value={customEnd}
                      onChange={(e) => setCustomEnd(e.target.value)}
                    />
                  </label>
                </div>
              )}
              <div className="flex items-baseline gap-4">
                <Value v={last} unit={unit ?? undefined} digits={3} className="text-2xl" />
                <span className="label">
                  min <Value v={min} digits={3} />
                </span>
                <span className="label">
                  max <Value v={max} digits={3} />
                </span>
              </div>
              <div className="min-h-0 flex-1">
                <TimeSeries
                  apid={selection.apid}
                  field={selection.field}
                  unit={unit}
                  window={window}
                  live={live}
                  alarmLow={fieldDef?.alarm_low}
                  alarmHigh={fieldDef?.alarm_high}
                />
              </div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
