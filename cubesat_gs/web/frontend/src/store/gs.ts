import { create } from "zustand";
import type { CommandRecordOut, FeedEntry, PassOut, PassStateOut, StatusOut, TelemetryLatest, WsMessage } from "@/api/types";

export type Alarm = { apid: number; field_name: string; value: unknown; alarm: "low" | "high" };
export type Toast = { id: number; kind: "alarm" | "info"; text: string };

const FEED_CAP = 2000;
const SERIES_CAP = 5000;

type State = {
  connected: boolean;
  status: StatusOut | null;
  feed: FeedEntry[];
  paused: boolean;
  pausedBuffer: FeedEntry[];
  telemetryLatest: Record<number, TelemetryLatest>;
  series: Record<string, [number, number][]>;
  alarmsActive: Alarm[];
  pendingCommand: CommandRecordOut | null;
  commandHistory: CommandRecordOut[];
  nextPass: PassOut | null;
  currentPass: PassStateOut | null;
  toasts: Toast[];
  gaps: number;
  setConnected: (c: boolean) => void;
  applyMessage: (m: WsMessage) => void;
  setPaused: (p: boolean) => void;
  flushPaused: () => void;
  dismissToast: (id: number) => void;
  reset: () => void;
};

let toastId = 0;

const initial = {
  connected: false,
  status: null,
  feed: [],
  paused: false,
  pausedBuffer: [],
  telemetryLatest: {},
  series: {},
  alarmsActive: [],
  pendingCommand: null,
  commandHistory: [],
  nextPass: null,
  currentPass: null,
  toasts: [],
  gaps: 0,
};

function alarmsFrom(latest: Record<number, TelemetryLatest>): Alarm[] {
  return Object.values(latest).flatMap((t) =>
    t.fields
      .filter((f) => f.alarm === "low" || f.alarm === "high")
      .map((f) => ({ apid: t.apid, field_name: f.name, value: f.value, alarm: f.alarm as "low" | "high" })),
  );
}

export const useGs = create<State>((set, get) => ({
  ...initial,
  setConnected: (connected) => set({ connected }),
  setPaused: (paused) => set({ paused }),
  flushPaused: () => set((s) => ({ feed: [...s.pausedBuffer, ...s.feed].slice(0, FEED_CAP), pausedBuffer: [], paused: false })),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  reset: () => set({ ...initial }),
  applyMessage: (m) => {
    const s = get();
    switch (m.type) {
      case "snapshot": {
        const latest: Record<number, TelemetryLatest> = {};
        for (const [k, v] of Object.entries(m.data.telemetry_latest)) latest[Number(k)] = v;
        set({
          status: m.data.status,
          feed: [...m.data.feed].reverse().slice(0, FEED_CAP),
          telemetryLatest: latest,
          alarmsActive: alarmsFrom(latest),
          pendingCommand: m.data.pending_command,
          nextPass: m.data.next_pass,
          currentPass: m.data.current_pass,
        });
        return;
      }
      case "status":
        set({ status: m.data, nextPass: m.data.passes.next, currentPass: m.data.passes.current });
        return;
      case "packet":
        if (s.paused) set({ pausedBuffer: [m.data, ...s.pausedBuffer].slice(0, FEED_CAP) });
        else set({ feed: [m.data, ...s.feed].slice(0, FEED_CAP) });
        return;
      case "telemetry": {
        const latest = { ...s.telemetryLatest, [m.data.apid]: m.data };
        const series = { ...s.series };
        const t = Date.parse(m.data.ts);
        for (const f of m.data.fields) {
          if (typeof f.value === "number") {
            const key = `${m.data.apid}:${f.name}`;
            const arr = series[key] ? [...series[key], [t, f.value] as [number, number]] : [[t, f.value] as [number, number]];
            series[key] = arr.length > SERIES_CAP ? arr.slice(arr.length - SERIES_CAP) : arr;
          }
        }
        set({ telemetryLatest: latest, series, alarmsActive: alarmsFrom(latest) });
        return;
      }
      case "alarm":
        set({
          toasts: [...s.toasts, { id: ++toastId, kind: "alarm" as const, text: `${m.data.field_name} ${m.data.alarm_type}: ${m.data.value} (limit ${m.data.threshold})` }].slice(-5),
        });
        return;
      case "gap":
        set({ gaps: s.gaps + m.data.missed });
        return;
      case "command":
        if (m.data.pending) set({ pendingCommand: m.data });
        else set({ pendingCommand: null, commandHistory: [m.data, ...s.commandHistory].slice(0, 500) });
        return;
      case "pass":
        if ("event" in m.data) {
          set({
            currentPass: null,
            toasts: [...s.toasts, { id: ++toastId, kind: "info" as const, text: m.data.event === "aos" ? `Pass started — max elevation ${m.data.pass.max_el.toFixed(0)}°` : "Pass ended" }].slice(-5),
          });
        } else {
          set({ currentPass: m.data });
        }
        return;
      case "pong":
        return;
    }
  },
}));
