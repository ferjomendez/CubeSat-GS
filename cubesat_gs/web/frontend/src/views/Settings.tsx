import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError, downloadExport } from "@/api/client";
import type { ConfigOut, ConfigPutOut, DbStatsOut, SerialPortOut, TelemetryDefsOut, TLEOut } from "@/api/types";
import { AlarmBadge } from "@/components/AlarmBadge";
import { ConfigSection, type ConfigSaveResult } from "@/components/ConfigSection";
import { Panel } from "@/components/Panel";
import { Value } from "@/components/Value";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

/** Mirrors `sqlite_backend.COLLECTIONS` — the collections the export endpoint accepts. */
const COLLECTIONS = ["raw_packets", "decoded_telemetry", "commands", "sessions", "alarms", "passes"] as const;

const READ_ONLY_SECTIONS: { key: string; title: string }[] = [
  { key: "database", title: "Database" },
  { key: "logging", title: "Logging" },
  { key: "web", title: "Web" },
  { key: "ccsds", title: "CCSDS" },
  { key: "telemetry", title: "Telemetry" },
];

/** Reports an `ApiError` (422 `invalid_value` / `invalid_tle`) as a human toast. */
function toastApiError(err: unknown, fallback: string) {
  if (err instanceof ApiError) toast.error(err.detail ?? err.error);
  else toast.error(fallback);
}

const asRecord = (v: unknown): Record<string, unknown> => (v && typeof v === "object" ? (v as Record<string, unknown>) : {});

/**
 * Satellite section: name, a single "paste both TLE lines" textarea (split on newline into
 * `tle_line1`/`tle_line2`, validated as exactly two non-empty lines starting with "1 "/"2 "), a TLE
 * source URL, and a "Refresh TLE now" action that fetches a fresh TLE from that URL. Hand-rolled
 * rather than a generic `ConfigSection` because of that split/validate step and the extra button.
 */
function SatelliteSection({
  values,
  applies,
  onSave,
}: {
  values: Record<string, unknown>;
  applies: Record<string, "live" | "restart">;
  onSave: (section: string, changed: Record<string, unknown>) => Promise<ConfigSaveResult>;
}) {
  const name = "satellite";
  const savedTle = `${String(values.tle_line1 ?? "")}\n${String(values.tle_line2 ?? "")}`.trim();

  const [nameDraft, setNameDraft] = useState(String(values.name ?? ""));
  const [tleDraft, setTleDraft] = useState(savedTle);
  const [sourceDraft, setSourceDraft] = useState(String(values.tle_source ?? ""));
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!dirty) {
      setNameDraft(String(values.name ?? ""));
      setTleDraft(`${String(values.tle_line1 ?? "")}\n${String(values.tle_line2 ?? "")}`.trim());
      setSourceDraft(String(values.tle_source ?? ""));
    }
  }, [values, dirty]);

  const parseTle = (): { line1: string; line2: string } | null => {
    const lines = tleDraft.split("\n").map((l) => l.trim()).filter((l) => l.length > 0);
    if (lines.length !== 2 || !lines[0].startsWith("1 ") || !lines[1].startsWith("2 ")) return null;
    return { line1: lines[0], line2: lines[1] };
  };

  const tleTouched = tleDraft.trim() !== savedTle;
  const parsed = parseTle();
  const tleError = tleTouched && !parsed ? 'TLE must be exactly two lines, starting with "1 " and "2 "' : null;

  const changed = (): Record<string, unknown> => {
    const out: Record<string, unknown> = {};
    if (nameDraft !== String(values.name ?? "")) out.name = nameDraft;
    if (sourceDraft !== String(values.tle_source ?? "")) out.tle_source = sourceDraft;
    if (tleTouched && parsed) {
      out.tle_line1 = parsed.line1;
      out.tle_line2 = parsed.line2;
    }
    return out;
  };

  const payload = changed();
  const canSave = Object.keys(payload).length > 0 && !saving && !tleError;

  const applyBadge = (key: string) => {
    const kind = applies[`${name}.${key}`];
    return kind ? <AlarmBadge tone={kind === "live" ? "nominal" : "warn"} text={kind} /> : null;
  };

  const save = async () => {
    setSaving(true);
    try {
      const result = await onSave(name, payload);
      const fullKeys = Object.keys(payload).map((k) => `${name}.${k}`);
      const allLive = fullKeys.length > 0 && fullKeys.every((k) => result.appliedLive.includes(k));
      setMessage(allLive ? "Applied live" : "Saved — restart the ground station to apply");
      setDirty(false);
      window.setTimeout(() => setMessage(null), 4000);
    } catch {
      // Already toasted by `onSave`.
    } finally {
      setSaving(false);
    }
  };

  const refresh = async () => {
    setRefreshing(true);
    try {
      const tle = await api.post<TLEOut>("/api/passes/refresh-tle");
      setTleDraft(`${tle.line1}\n${tle.line2}`);
      setDirty(true);
      toast("TLE refreshed — review and save");
    } catch (err) {
      toastApiError(err, "Failed to refresh TLE");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Panel title="Satellite" bodyClassName="flex flex-col gap-3 p-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor="satellite-name">Name</Label>
            {applyBadge("name")}
          </div>
          <Input
            id="satellite-name"
            className="h-8"
            value={nameDraft}
            onChange={(e) => {
              setDirty(true);
              setNameDraft(e.target.value);
            }}
          />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Label htmlFor="satellite-tle-source">TLE URL</Label>
            {applyBadge("tle_source")}
          </div>
          <Input
            id="satellite-tle-source"
            className="h-8"
            value={sourceDraft}
            onChange={(e) => {
              setDirty(true);
              setSourceDraft(e.target.value);
            }}
          />
        </div>
        <div className="col-span-2 space-y-1 sm:col-span-3">
          <div className="flex items-center gap-2">
            <Label htmlFor="satellite-tle">TLE (2 lines)</Label>
            {applyBadge("tle_line1")}
          </div>
          <Textarea
            id="satellite-tle"
            rows={2}
            className="font-mono"
            value={tleDraft}
            onChange={(e) => {
              setDirty(true);
              setTleDraft(e.target.value);
            }}
          />
          {tleError && <p className="label text-alarm">{tleError}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          disabled={!canSave}
          onClick={() => void save()}
          className="label rounded border border-line px-2 py-1 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
        >
          Save Satellite
        </button>
        <button
          type="button"
          disabled={!sourceDraft.trim() || refreshing}
          onClick={() => void refresh()}
          className="label rounded border border-line px-2 py-1 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
        >
          {refreshing ? "Refreshing…" : "Refresh TLE now"}
        </button>
        {message && <span className="label text-info">{message}</span>}
      </div>
    </Panel>
  );
}

/** Runtime DB stats/health (read-only) plus the collection export form. */
function DatabasePanel({ stats }: { stats: DbStatsOut | undefined }) {
  const [collection, setCollection] = useState<string>(COLLECTIONS[0]);
  const [fmt, setFmt] = useState<"csv" | "json">("csv");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [apid, setApid] = useState("");
  const [downloading, setDownloading] = useState(false);

  const download = async () => {
    setDownloading(true);
    try {
      await downloadExport(
        {
          collection,
          fmt,
          start: start ? new Date(start).toISOString() : undefined,
          end: end ? new Date(end).toISOString() : undefined,
          apid: apid.trim() ? Number(apid) : undefined,
        },
        `${collection}.${fmt}`,
      );
    } catch (err) {
      toastApiError(err, "Export failed");
    } finally {
      setDownloading(false);
    }
  };

  const health = stats?.health ?? {};

  return (
    <Panel title="Database" bodyClassName="flex flex-col gap-3 p-3">
      <table className="w-full max-w-sm text-left text-[13px]">
        <thead>
          <tr className="label">
            <th className="px-2 py-1">Collection</th>
            <th className="px-2 py-1">Rows</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(stats?.counts ?? {}).map(([k, v]) => (
            <tr key={k} className="row">
              <td className="px-2 font-mono">{k}</td>
              <td className="px-2">
                <Value v={v} digits={0} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="label">
        Mongo {String(health.mongo ?? "—")} · Pending sync <Value v={Number(health.pending_sync ?? 0)} digits={0} />
      </p>

      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="export-collection">Collection</Label>
          <Select value={collection} onValueChange={setCollection}>
            <SelectTrigger id="export-collection" className="h-8 w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {COLLECTIONS.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="export-format">Format</Label>
          <Select value={fmt} onValueChange={(v) => setFmt(v as "csv" | "json")}>
            <SelectTrigger id="export-format" className="h-8 w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="export-start">Start</Label>
          <Input id="export-start" type="datetime-local" className="h-8" value={start} onChange={(e) => setStart(e.target.value)} />
        </div>
        <div className="space-y-1">
          <Label htmlFor="export-end">End</Label>
          <Input id="export-end" type="datetime-local" className="h-8" value={end} onChange={(e) => setEnd(e.target.value)} />
        </div>
        <div className="space-y-1">
          <Label htmlFor="export-apid">APID</Label>
          <Input id="export-apid" type="number" className="h-8 w-24" value={apid} onChange={(e) => setApid(e.target.value)} />
        </div>
        <button
          type="button"
          disabled={downloading}
          onClick={() => void download()}
          className="label rounded border border-line px-2 py-1 hover:border-info disabled:cursor-not-allowed disabled:opacity-40"
        >
          {downloading ? "Downloading…" : `Download ${fmt.toUpperCase()}`}
        </button>
      </div>
    </Panel>
  );
}

/** Settings: nine sections over `gs_config.yaml` — six writable, five read-only, plus telemetry defs and DB/export. */
export default function Settings() {
  const queryClient = useQueryClient();

  const { data: config } = useQuery({ queryKey: ["config"], queryFn: () => api.get<ConfigOut>("/api/config") });
  const { data: ports } = useQuery({ queryKey: ["serial-ports"], queryFn: () => api.get<SerialPortOut[]>("/api/config/serial-ports") });
  const { data: defs } = useQuery({ queryKey: ["telemetry-definitions"], queryFn: () => api.get<TelemetryDefsOut>("/api/telemetry/definitions") });
  const { data: stats } = useQuery({ queryKey: ["db-stats"], queryFn: () => api.get<DbStatsOut>("/api/db/stats") });

  const handleSave = async (section: string, changed: Record<string, unknown>): Promise<ConfigSaveResult> => {
    try {
      const res = await api.put<ConfigPutOut>("/api/config", { sections: { [section]: changed } });
      queryClient.setQueryData<ConfigOut>(["config"], (prev) => (prev ? { ...prev, config: res.config } : prev));
      return { appliedLive: res.applied_live, restartRequired: res.restart_required };
    } catch (err) {
      toastApiError(err, `Failed to save ${section}`);
      throw err;
    }
  };

  if (!config) return <Panel title="Settings">Loading…</Panel>;

  const cfg = config.config;
  const applies = config.applies;
  const serial = asRecord(cfg.serial);

  const currentPort = String(serial.port ?? "auto");
  const portOptions = [
    { value: "auto", label: "Auto-detect" },
    ...(ports ?? []).map((p) => ({ value: p.device, label: p.description ? `${p.device} — ${p.description}` : p.device })),
  ];
  if (currentPort !== "auto" && !portOptions.some((o) => o.value === currentPort)) {
    portOptions.push({ value: currentPort, label: currentPort });
  }

  return (
    <div className="flex flex-col gap-2">
      <ConfigSection
        name="serial"
        title="Serial"
        values={serial}
        applies={applies}
        onSave={handleSave}
        fields={[
          { key: "port", label: "Port", type: "select", options: portOptions },
          { key: "baudrate", label: "Baud rate", type: "number" },
          { key: "reconnect_interval", label: "Reconnect interval (s)", type: "number" },
        ]}
      />
      <ConfigSection
        name="frequencies"
        title="Frequencies"
        values={asRecord(cfg.frequencies)}
        applies={applies}
        onSave={handleSave}
        fields={[
          { key: "tctm", label: "TC/TM (MHz)", type: "number", step: "0.001" },
          { key: "beacon", label: "Beacon (MHz)", type: "number", step: "0.001" },
        ]}
      />
      <ConfigSection
        name="station"
        title="Station"
        values={asRecord(cfg.station)}
        applies={applies}
        onSave={handleSave}
        fields={[
          { key: "name", label: "Name", type: "text" },
          { key: "latitude", label: "Latitude (°)", type: "number", step: "0.0001" },
          { key: "longitude", label: "Longitude (°)", type: "number", step: "0.0001" },
          { key: "altitude", label: "Altitude (m)", type: "number", step: "1" },
        ]}
      />
      <SatelliteSection values={asRecord(cfg.satellite)} applies={applies} onSave={handleSave} />
      <ConfigSection
        name="passes"
        title="Passes"
        values={asRecord(cfg.passes)}
        applies={applies}
        onSave={handleSave}
        fields={[
          { key: "min_elevation", label: "Min elevation (°)", type: "number", step: "1" },
          { key: "prediction_days", label: "Prediction days", type: "number", step: "1" },
        ]}
      />
      <ConfigSection
        name="commands"
        title="Commands"
        values={asRecord(cfg.commands)}
        applies={applies}
        onSave={handleSave}
        fields={[
          { key: "default_timeout", label: "Default timeout (s)", type: "number", step: "1" },
          { key: "max_retries", label: "Max retries", type: "number", step: "1" },
          { key: "retry_backoff", label: "Backoff multiplier", type: "number", step: "0.1" },
        ]}
      />

      <Panel title="Read-only settings" bodyClassName="flex flex-col gap-3 p-3 text-dim opacity-70">
        <p className="label">Edit gs_config.yaml and restart to change these.</p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {READ_ONLY_SECTIONS.map(({ key, title }) => (
            <div key={key}>
              <div className="label mb-1">{title}</div>
              <dl className="space-y-0.5 text-[13px]">
                {Object.entries(asRecord(cfg[key])).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <dt>{k}</dt>
                    <dd className="font-mono">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Telemetry definitions" bodyClassName="p-3">
        <pre className="max-h-64 overflow-auto font-mono text-[12px] text-dim">{defs?.yaml ?? ""}</pre>
      </Panel>

      <DatabasePanel stats={stats} />
    </div>
  );
}
