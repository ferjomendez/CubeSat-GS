import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import type { PassesOut, PassHistoryOut, PassOut, TrackPoint } from "@/api/types";
import { Countdown } from "@/components/Countdown";
import { Panel } from "@/components/Panel";
import { PassInstrument } from "@/components/PassInstrument";
import { Value } from "@/components/Value";
import { fmtDuration } from "@/lib/format";
import { local, utc } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useGs } from "@/store/gs";

const asString = (v: unknown, fallback = "—"): string => (v == null ? fallback : String(v));
const asNumber = (v: unknown): number | null => (typeof v === "number" ? v : v == null ? null : Number(v));

/** History rows come back as loose dicts (`PassHistoryOut.items: Record<string, unknown>[]`). */
function historyDuration(item: Record<string, unknown>): number | null {
  const aos = asNumber(item.aos) ?? (typeof item.aos === "string" ? Date.parse(item.aos) : null);
  const los = asNumber(item.los) ?? (typeof item.los === "string" ? Date.parse(item.los) : null);
  if (aos == null || los == null) return null;
  return (los - aos) / 1000;
}

/**
 * Pass tracker: a sky-plot instrument for the selected pass, its detail panel, a selectable
 * upcoming-passes table (the pass currently overhead highlighted), and pass history.
 */
export default function PassTracker() {
  const currentPass = useGs((s) => s.currentPass);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["passes"],
    queryFn: () => api.get<PassesOut>("/api/passes"),
    refetchInterval: 60_000,
  });

  const passes: PassOut[] = data?.passes ?? [];
  const selected = passes.find((p) => p.id === selectedId) ?? passes[0] ?? null;
  const currentForSelected = selected && currentPass?.pass_id === selected.id ? currentPass : null;

  const { data: track } = useQuery({
    queryKey: ["track", selected?.id],
    queryFn: () => api.get<TrackPoint[]>(`/api/passes/${selected!.id}/track`),
    enabled: selected != null,
  });

  const { data: history } = useQuery({
    queryKey: ["pass-history"],
    queryFn: () => api.get<PassHistoryOut>("/api/passes/history"),
  });

  if (!data) return <Panel title="Pass tracker">Loading…</Panel>;

  if (!data.enabled) {
    return (
      <Panel title="Pass tracker" bodyClassName="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="text-dim">
          No passes — {data.reason ?? "pass prediction is unavailable"}. Add a TLE in{" "}
          <Link to="/settings" className="text-info hover:underline">
            Settings
          </Link>
          .
        </p>
      </Panel>
    );
  }

  return (
    <div className="grid grid-cols-12 gap-2">
      <Panel title="Sky plot" className="col-span-7" bodyClassName="p-3">
        <PassInstrument next={selected} current={currentForSelected} track={track} size={320} />
      </Panel>

      <Panel title="Selected pass" className="col-span-5" bodyClassName="p-3">
        {selected ? (
          <div className="label grid grid-cols-2 gap-2">
            <span>AOS (UTC)</span>
            <span className="font-mono tabular-nums text-fg">{utc(selected.aos)}</span>
            <span>AOS (local)</span>
            <span className="font-mono tabular-nums text-fg">{local(selected.aos)}</span>
            <span>LOS (UTC)</span>
            <span className="font-mono tabular-nums text-fg">{utc(selected.los)}</span>
            <span>LOS (local)</span>
            <span className="font-mono tabular-nums text-fg">{local(selected.los)}</span>
            <span>TCA (UTC)</span>
            <span className="font-mono tabular-nums text-fg">{utc(selected.tca)}</span>
            <span>Duration</span>
            <span className="font-mono tabular-nums text-fg">{fmtDuration(selected.duration_s)}</span>
            <span>Max elevation</span>
            <Value v={selected.max_el} unit="°" digits={0} className="text-fg" />
            <span>AOS az / LOS az</span>
            <span className="font-mono tabular-nums text-fg">
              {selected.aos_az.toFixed(0)}° / {selected.los_az.toFixed(0)}°
            </span>
          </div>
        ) : (
          <p className="text-dim">No pass selected</p>
        )}
      </Panel>

      <Panel title="Upcoming" className="col-span-12" bodyClassName="overflow-auto">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="label">
              <th className="px-2 py-1">AOS (UTC)</th>
              <th className="px-2 py-1">Max el</th>
              <th className="px-2 py-1">Duration</th>
              <th className="px-2 py-1">Countdown</th>
            </tr>
          </thead>
          <tbody>
            {passes.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-dim px-2 py-6 text-center">
                  No upcoming passes in the prediction window
                </td>
              </tr>
            ) : (
              passes.map((p) => {
                const isCurrent = currentPass?.pass_id === p.id;
                const isSelected = selected?.id === p.id;
                return (
                  <tr
                    key={p.id}
                    className={cn(
                      "row cursor-pointer hover:bg-raised",
                      isCurrent && "bg-info-dim",
                      isSelected && "border-l-2 border-l-info",
                    )}
                    onClick={() => setSelectedId(p.id)}
                  >
                    <td className="px-2 font-mono tabular-nums" title={local(p.aos)}>
                      {utc(p.aos)}
                    </td>
                    <td className="px-2">
                      <Value v={p.max_el} unit="°" digits={0} />
                    </td>
                    <td className="px-2 font-mono tabular-nums">{fmtDuration(p.duration_s)}</td>
                    <td className="px-2 font-mono tabular-nums">
                      {isCurrent ? <span className="text-info">In progress</span> : <Countdown iso={p.aos} />}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </Panel>

      <Panel title="Pass history" className="col-span-12" bodyClassName="overflow-auto">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="label">
              <th className="px-2 py-1">AOS (UTC)</th>
              <th className="px-2 py-1">Duration</th>
              <th className="px-2 py-1">Max el</th>
              <th className="px-2 py-1">Packets rx/tx</th>
              <th className="px-2 py-1">Commands</th>
            </tr>
          </thead>
          <tbody>
            {(history?.items.length ?? 0) === 0 ? (
              <tr>
                <td colSpan={5} className="text-dim px-2 py-6 text-center">
                  No completed passes yet
                </td>
              </tr>
            ) : (
              (history?.items ?? []).map((item, i) => {
                const aos = item.aos;
                const durationS = historyDuration(item);
                return (
                  <tr key={i} className="row">
                    <td className="px-2 font-mono tabular-nums">{typeof aos === "string" ? utc(aos) : asString(aos)}</td>
                    <td className="px-2 font-mono tabular-nums">{durationS != null ? fmtDuration(durationS) : "—"}</td>
                    <td className="px-2">
                      <Value v={asNumber(item.max_el)} unit="°" digits={0} />
                    </td>
                    <td className="px-2 font-mono tabular-nums">
                      {asString(item.packets_received, "0")}/{asString(item.packets_sent, "0")}
                    </td>
                    <td className="px-2 font-mono tabular-nums">{asString(item.commands_sent, "0")}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </Panel>
    </div>
  );
}
