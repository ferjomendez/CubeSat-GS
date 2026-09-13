"""Pydantic models for every REST and WebSocket payload. The frontend's types.ts mirrors these."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from cubesat_gs.core.events import now

Kind = Literal["beacon", "telemetry", "command", "malformed", "unknown"]
Direction = Literal["rx", "tx"]
CommandStatus = Literal["acked", "responded", "timeout", "failed", "refused"]


class ErrorOut(BaseModel):
    error: str
    detail: str | None = None


class SerialStatus(BaseModel):
    connected: bool
    port: str | None


class FrequencyStatus(BaseModel):
    mode: str
    mhz: float


class StorageStatus(BaseModel):
    mongo: Literal["ok", "degraded", "disabled"]


class PassOut(BaseModel):
    id: str
    aos: datetime
    los: datetime
    tca: datetime
    max_el: float
    aos_az: float
    los_az: float
    duration_s: float


class PassStateOut(BaseModel):
    pass_id: str
    t: datetime
    az: float
    el: float
    range_km: float
    doppler_hz: float
    progress: float


class PassesStatus(BaseModel):
    enabled: bool
    reason: str | None
    next: PassOut | None
    current: PassStateOut | None


class SessionOut(BaseModel):
    start_time: datetime
    end_time: datetime | None
    pass_id: str | None
    packets_received: int
    packets_sent: int
    notes: str


class CommandRecordOut(BaseModel):
    ts: datetime
    name: str
    raw_hex: str
    status: CommandStatus
    response_hex: str | None
    latency_ms: float | None
    attempts: int
    error: str | None
    pending: bool = False


class StatusOut(BaseModel):
    station: str
    serial: SerialStatus
    frequency: FrequencyStatus
    pending_command: CommandRecordOut | None
    storage: StorageStatus
    session: SessionOut
    passes: PassesStatus


class HealthOut(BaseModel):
    mongo: str
    pending_sync: int
    sqlite_path: str
    web: dict[str, int]


class TelemetryField(BaseModel):
    name: str
    value: Any
    unit: str | None
    alarm: Literal["nominal", "low", "high"] | None


class FeedEntry(BaseModel):
    id: str
    ts: datetime
    direction: Direction
    apid: int | None
    apid_name: str | None
    seq: int | None
    raw_hex: str
    rssi: float | None
    snr: float | None
    freq_mhz: float
    kind: Kind
    summary: str
    fields: list[TelemetryField] | None


class TelemetryLatest(BaseModel):
    apid: int
    apid_name: str
    ts: datetime
    fields: list[TelemetryField]


class TelemetryDefField(BaseModel):
    name: str
    type: str
    unit: str | None
    alarm_low: float | None
    alarm_high: float | None


class TelemetryDefOut(BaseModel):
    apid: int
    name: str
    fields: list[TelemetryDefField]


class TelemetryPoint(BaseModel):
    t: datetime
    v: float


class TelemetryHistoryOut(BaseModel):
    apid: int
    field: str
    unit: str | None
    alarm_low: float | None
    alarm_high: float | None
    points: list[TelemetryPoint]
    total_rows: int


class CommandDefOut(BaseModel):
    name: str
    description: str
    apid: int
    payload_hex: str
    payload_text: str | None
    response_apid: int | None
    timeout: float
    critical: bool


class SendCommandIn(BaseModel):
    confirm: bool = False
    payload_hex: str | None = None


class SendRawIn(BaseModel):
    hex: str
    confirm: bool = False


class FrequencyOut(BaseModel):
    mode: str
    mhz: float
    presets: dict[str, float]
    history: list[dict[str, Any]]


class FrequencyIn(BaseModel):
    mode: Literal["tctm", "beacon_listen", "custom"]
    mhz: float | None = None


class PassesOut(BaseModel):
    enabled: bool
    reason: str | None
    passes: list[PassOut]


class TrackPoint(BaseModel):
    t: datetime
    az: float
    el: float
    range_km: float
    doppler_hz: float


class SerialPortOut(BaseModel):
    device: str
    description: str
    vid: int | None
    pid: int | None


class ConfigOut(BaseModel):
    config: dict[str, Any]
    writable: list[str]
    applies: dict[str, Literal["live", "restart"]]


class ConfigIn(BaseModel):
    sections: dict[str, dict[str, Any]]


class ConfigPutOut(BaseModel):
    config: dict[str, Any]
    applied_live: list[str]
    restart_required: bool


class ExportIn(BaseModel):
    collection: str
    fmt: Literal["csv", "json"] = "csv"
    start: datetime | None = None
    end: datetime | None = None
    apid: int | None = None


class AlarmOut(BaseModel):
    ts: datetime
    apid: int
    field_name: str
    value: float
    threshold: float
    alarm_type: Literal["low", "high"]


class GapOut(BaseModel):
    ts: datetime
    apid: int
    expected: int
    received: int
    missed: int


class SnapshotOut(BaseModel):
    status: StatusOut
    feed: list[FeedEntry]
    telemetry_latest: dict[int, TelemetryLatest]
    pending_command: CommandRecordOut | None
    next_pass: PassOut | None
    current_pass: PassStateOut | None
    alarms_active: list[dict[str, Any]]


WsType = Literal["snapshot", "status", "packet", "telemetry", "alarm", "gap", "command", "pass", "pong"]


class WsMessage(BaseModel):
    type: WsType
    ts: datetime = Field(default_factory=now)
    data: Any


def ws_message(type_: WsType, data: Any) -> dict:
    """Build the wire dict for a WS message (data already JSON-serialisable)."""
    return {"type": type_, "ts": now().isoformat(), "data": data}
