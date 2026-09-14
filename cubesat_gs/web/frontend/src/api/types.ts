/**
 * Mirrors cubesat_gs/web/schemas.py: one interface per Pydantic model, same field names.
 * Datetimes are `string` (ISO 8601). A Pydantic `dict[int, X]` becomes `Record<string, X>` — JSON object keys are
 * always strings on the wire.
 *
 * Note on WsMessage: schemas.py's `WsMessage` is generic (`data: Any`). We mirror that shape verbatim as
 * `WsMessageOut` below, and instead export `WsMessage` as the discriminated union the frontend actually consumes
 * (narrowed by `type`), matching each `data` payload to the message it carries.
 */

export type Kind = "beacon" | "telemetry" | "command" | "malformed" | "unknown";
export type Direction = "rx" | "tx";
export type CommandStatus = "acked" | "responded" | "timeout" | "failed" | "refused";
export type WsType = "snapshot" | "status" | "packet" | "telemetry" | "alarm" | "gap" | "command" | "pass" | "pong";

export interface ErrorOut {
  error: string;
  detail: string | null;
}

export interface SerialStatus {
  connected: boolean;
  port: string | null;
}

export interface FrequencyStatus {
  mode: string;
  mhz: number;
}

export interface StorageStatus {
  mongo: "ok" | "degraded" | "disabled";
}

export interface PassOut {
  id: string;
  aos: string;
  los: string;
  tca: string;
  max_el: number;
  aos_az: number;
  los_az: number;
  duration_s: number;
}

export interface PassStateOut {
  pass_id: string;
  t: string;
  az: number;
  el: number;
  range_km: number;
  doppler_hz: number;
  progress: number;
}

export interface PassesStatus {
  enabled: boolean;
  reason: string | null;
  next: PassOut | null;
  current: PassStateOut | null;
}

export interface SessionOut {
  start_time: string;
  end_time: string | null;
  pass_id: string | null;
  packets_received: number;
  packets_sent: number;
  notes: string;
}

export interface CommandRecordOut {
  ts: string;
  name: string;
  raw_hex: string;
  status: CommandStatus;
  response_hex: string | null;
  latency_ms: number | null;
  attempts: number;
  error: string | null;
  pending: boolean;
}

export interface StatusOut {
  station: string;
  serial: SerialStatus;
  frequency: FrequencyStatus;
  pending_command: CommandRecordOut | null;
  storage: StorageStatus;
  session: SessionOut;
  passes: PassesStatus;
}

export interface HealthOut {
  mongo: string;
  pending_sync: number;
  sqlite_path: string;
  web: Record<string, number>;
}

export interface TelemetryField {
  name: string;
  value: unknown;
  unit: string | null;
  alarm: "nominal" | "low" | "high" | null;
}

export interface FeedEntry {
  id: string;
  ts: string;
  direction: Direction;
  apid: number | null;
  apid_name: string | null;
  seq: number | null;
  raw_hex: string;
  rssi: number | null;
  snr: number | null;
  freq_mhz: number;
  kind: Kind;
  summary: string;
  fields: TelemetryField[] | null;
}

export interface TelemetryLatest {
  apid: number;
  apid_name: string;
  ts: string;
  fields: TelemetryField[];
}

export interface TelemetryDefField {
  name: string;
  type: string;
  unit: string | null;
  alarm_low: number | null;
  alarm_high: number | null;
}

export interface TelemetryDefOut {
  apid: number;
  name: string;
  fields: TelemetryDefField[];
}

export interface TelemetryPoint {
  t: string;
  v: number;
}

export interface TelemetryHistoryOut {
  apid: number;
  field: string;
  unit: string | null;
  alarm_low: number | null;
  alarm_high: number | null;
  points: TelemetryPoint[];
  total_rows: number;
}

export interface PacketsPageOut {
  items: FeedEntry[];
  next_before: string | null;
}

export interface TelemetryLatestOut {
  latest: Record<string, TelemetryLatest>;
  definitions: TelemetryDefOut[];
}

export interface TelemetryDefsOut {
  yaml: string;
  definitions: TelemetryDefOut[];
}

export interface CommandDefOut {
  name: string;
  description: string;
  apid: number;
  payload_hex: string;
  payload_text: string | null;
  response_apid: number | null;
  timeout: number;
  critical: boolean;
}

export interface CommandHistoryOut {
  items: CommandRecordOut[];
  next_before: string | null;
}

export interface SendCommandIn {
  confirm?: boolean;
  payload_hex?: string | null;
}

export interface SendRawIn {
  hex: string;
  confirm?: boolean;
}

export interface FrequencyOut {
  mode: string;
  mhz: number;
  presets: Record<string, number>;
  history: Record<string, unknown>[];
}

export interface FrequencyIn {
  mode: "tctm" | "beacon_listen" | "custom";
  mhz?: number | null;
}

export interface PassesOut {
  enabled: boolean;
  reason: string | null;
  passes: PassOut[];
}

export interface TrackPoint {
  t: string;
  az: number;
  el: number;
  range_km: number;
  doppler_hz: number;
}

export interface PassHistoryOut {
  items: Record<string, unknown>[];
}

export interface TLEOut {
  line1: string;
  line2: string;
}

export interface SerialPortOut {
  device: string;
  description: string;
  vid: number | null;
  pid: number | null;
}

export interface ConfigOut {
  config: Record<string, unknown>;
  writable: string[];
  applies: Record<string, "live" | "restart">;
}

export interface ConfigIn {
  sections: Record<string, Record<string, unknown>>;
}

export interface ConfigPutOut {
  config: Record<string, unknown>;
  applied_live: string[];
  restart_required: boolean;
}

export interface ExportIn {
  collection: string;
  fmt?: "csv" | "json";
  start?: string | null;
  end?: string | null;
  apid?: number | null;
}

export interface DbStatsOut {
  counts: Record<string, number>;
  health: Record<string, unknown>;
}

export interface AlarmOut {
  ts: string;
  apid: number;
  field_name: string;
  value: number;
  threshold: number;
  alarm_type: "low" | "high";
}

export interface GapOut {
  ts: string;
  apid: number;
  expected: number;
  received: number;
  missed: number;
}

export interface SnapshotOut {
  status: StatusOut;
  feed: FeedEntry[];
  telemetry_latest: Record<string, TelemetryLatest>;
  pending_command: CommandRecordOut | null;
  next_pass: PassOut | null;
  current_pass: PassStateOut | null;
  alarms_active: Record<string, unknown>[];
}

/** Mirrors the generic Pydantic `WsMessage` (schemas.py) verbatim: `data` is untyped on that side. */
export interface WsMessageOut {
  type: WsType;
  ts: string;
  data: unknown;
}

/** A `pass` event delta: hub.py's `_on_pass_edge` broadcast, distinct from the `PassStateOut` ticks. */
export type PassEdge = { event: "aos" | "los"; pass: PassOut };

/** Discriminated union narrowing `WsMessageOut.data` by `type` — what the frontend actually consumes. */
export type WsMessage =
  | { type: "snapshot"; ts: string; data: SnapshotOut }
  | { type: "status"; ts: string; data: StatusOut }
  | { type: "packet"; ts: string; data: FeedEntry }
  | { type: "telemetry"; ts: string; data: TelemetryLatest }
  | { type: "alarm"; ts: string; data: AlarmOut }
  | { type: "gap"; ts: string; data: GapOut }
  | { type: "command"; ts: string; data: CommandRecordOut }
  | { type: "pass"; ts: string; data: PassStateOut | PassEdge }
  | { type: "pong"; ts: string; data: Record<string, never> };
