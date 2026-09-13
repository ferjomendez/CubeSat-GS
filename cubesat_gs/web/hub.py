"""WebSocketHub: one more EventBus subscriber that fans events out to browsers as JSON deltas."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict, deque
from typing import Any

from starlette.websockets import WebSocketDisconnect

from cubesat_gs.core import ccsds
from cubesat_gs.core.events import (AlarmRaised, CommandCompleted, CommandStarted, ConnectionChanged,
                                    FrequencyChanged, PacketDecoded, PacketMalformed, PacketReceived,
                                    PacketSent, PassEnded, PassStarted, PassUpdate, SequenceGap, now)
from cubesat_gs.core.pass_predictor import pass_to_dict, state_to_dict
from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.schemas import ws_message

log = logging.getLogger(__name__)

_KIND_BY_APID = {ccsds.APID_BEACON: "beacon", ccsds.APID_TM_RESPONSE: "telemetry"}


def _fields(decoded) -> list[dict]:
    return [{"name": f.name, "value": f.value, "unit": f.unit, "alarm": f.alarm} for f in decoded.fields]


def summarize(kind: str, fields: list[dict] | None, reason: str | None = None, name: str | None = None) -> str:
    if kind == "malformed":
        return reason or "malformed"
    if kind == "command":
        return name or "TX"
    if fields:
        for f in fields:
            if isinstance(f["value"], str) and f["name"] != "raw_hex":
                return f["value"]
        return f"{len(fields)} fields"
    return "unknown APID"


class _Client:
    def __init__(self, ws, queue_size: int) -> None:
        self.ws = ws
        self.queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=queue_size)


class WebSocketHub:
    def __init__(self, station: GroundStation, *, ring_size: int = 500, queue_size: int = 500,
                 status_poll: float = 5.0, pending_ttl: float = 2.0) -> None:
        self._station = station
        self._bus = station.bus
        self._queue_size = queue_size
        self._status_poll = status_poll
        self._pending_ttl = pending_ttl
        self.feed: deque[dict] = deque(maxlen=ring_size)
        self._clients: set[_Client] = set()
        self._pending: OrderedDict[int, tuple[PacketReceived, dict]] = OrderedDict()
        self._seq = 0
        self._tasks: list[asyncio.Task] = []
        self._last_storage_state: str | None = None
        self._last_command_name: str | None = None

    # ---- lifecycle
    def _handlers(self):
        return ((ConnectionChanged, self._on_status_change), (FrequencyChanged, self._on_status_change),
                (PacketReceived, self._on_rx), (PacketDecoded, self._on_decoded),
                (PacketMalformed, self._on_malformed), (PacketSent, self._on_tx),
                (AlarmRaised, self._on_alarm), (SequenceGap, self._on_gap),
                (CommandStarted, self._on_command_started), (CommandCompleted, self._on_command),
                (PassStarted, self._on_pass_edge), (PassEnded, self._on_pass_edge), (PassUpdate, self._on_pass_update))

    async def start(self) -> None:
        for et, h in self._handlers():
            self._bus.subscribe(et, h)
        self._tasks = [asyncio.create_task(self._status_poll_loop(), name="hub-status"),
                       asyncio.create_task(self._pending_sweep(), name="hub-pending")]

    async def stop(self) -> None:
        for et, h in self._handlers():
            self._bus.unsubscribe(et, h)
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._tasks.clear()
        for c in list(self._clients):
            c.queue.put_nowait(None)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    # ---- broadcast
    def _broadcast(self, type_: str, data: Any) -> None:
        if not self._clients:
            return
        text = json.dumps(ws_message(type_, data), default=str)
        for c in list(self._clients):
            try:
                c.queue.put_nowait(text)
            except asyncio.QueueFull:
                log.warning("ws: dropping slow client")
                self._clients.discard(c)
                asyncio.ensure_future(self._close(c, 1013))  # handle()'s finally cancels the sender

    async def _close(self, c: _Client, code: int) -> None:
        try:
            await c.ws.close(code=code)
        except Exception:  # noqa: BLE001
            pass

    def snapshot(self) -> dict:
        st = self._station
        latest = {apid: {"apid": apid, "apid_name": d.apid_name, "ts": now().isoformat(), "fields": _fields(d)}
                  for apid, d in st.decoder.last_values.items()}
        alarms = [{"apid": apid, "field_name": f["name"], "value": f["value"], "alarm": f["alarm"]}
                  for apid, d in latest.items() for f in d["fields"] if f["alarm"] in ("low", "high")]
        status = st.status()
        return {"status": status, "feed": list(self.feed), "telemetry_latest": latest,
                "pending_command": status["pending_command"], "next_pass": status["passes"]["next"],
                "current_pass": status["passes"]["current"], "alarms_active": alarms}

    async def handle(self, ws) -> None:
        await ws.accept()
        c = _Client(ws, self._queue_size)
        self._clients.add(c)
        await ws.send_text(json.dumps(ws_message("snapshot", self.snapshot()), default=str))
        sender = asyncio.create_task(self._sender(c))
        try:
            while True:
                try:
                    raw = await ws.receive_text()
                except WebSocketDisconnect:
                    break
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("type") == "ping":
                    c.queue.put_nowait(json.dumps(ws_message("pong", {})))
        finally:
            self._clients.discard(c)
            if not c.queue.full():
                c.queue.put_nowait(None)
            sender.cancel()
            try:
                await sender
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    async def _sender(self, c: _Client) -> None:
        while True:
            text = await c.queue.get()
            if text is None:
                return
            try:
                await c.ws.send_text(text)
            except Exception:  # noqa: BLE001 - client gone
                self._clients.discard(c)
                return

    # ---- feed assembly
    def _new_id(self) -> str:
        self._seq += 1
        return f"{int(now().timestamp() * 1000)}-{self._seq}"

    async def _on_rx(self, ev: PacketReceived) -> None:
        peek = ccsds.peek_apid_seq(ev.raw)
        entry = {"id": self._new_id(), "ts": ev.ts.isoformat(), "direction": "rx",
                 "apid": peek[0] if peek else None, "apid_name": None, "seq": peek[1] if peek else None,
                 "raw_hex": ev.raw.hex().upper(), "rssi": ev.rssi, "snr": ev.snr, "freq_mhz": ev.freq_mhz,
                 "kind": "unknown", "summary": "", "fields": None, "_at": now()}
        self._pending[id(ev)] = (ev, entry)
        while len(self._pending) > 1000:
            _, (_, stale) = self._pending.popitem(last=False)
            self._emit_entry(stale)

    def _emit_entry(self, entry: dict) -> None:
        entry.pop("_at", None)
        if not entry["summary"]:
            entry["summary"] = summarize(entry["kind"], entry["fields"])
        self.feed.append(entry)
        self._broadcast("packet", entry)

    async def _on_decoded(self, ev: PacketDecoded) -> None:
        item = self._pending.pop(id(ev.source), None)
        if item is None:
            return
        _, entry = item
        d = ev.decoded
        entry["apid"], entry["apid_name"], entry["seq"] = ev.packet.apid, d.apid_name, ev.packet.sequence_count
        entry["fields"] = _fields(d)
        entry["kind"] = "unknown" if d.unknown_apid else _KIND_BY_APID.get(ev.packet.apid, "telemetry")
        entry["summary"] = summarize(entry["kind"], entry["fields"])
        self._emit_entry(entry)
        self._broadcast("telemetry", {"apid": ev.packet.apid, "apid_name": d.apid_name,
                                      "ts": ev.source.ts.isoformat(), "fields": entry["fields"]})

    async def _on_malformed(self, ev: PacketMalformed) -> None:
        item = self._pending.pop(id(ev.source), None)
        if item is None:
            return
        _, entry = item
        entry["kind"], entry["summary"] = "malformed", summarize("malformed", None, reason=ev.reason)
        self._emit_entry(entry)

    async def _on_tx(self, ev: PacketSent) -> None:
        peek = ccsds.peek_apid_seq(ev.raw)
        name = self._last_command_name
        self._emit_entry({"id": self._new_id(), "ts": ev.ts.isoformat(), "direction": "tx",
                          "apid": peek[0] if peek else None, "apid_name": None, "seq": peek[1] if peek else None,
                          "raw_hex": ev.raw.hex().upper(), "rssi": None, "snr": None, "freq_mhz": ev.freq_mhz,
                          "kind": "command", "summary": summarize("command", None, name=name or f"TX {len(ev.raw)} B"),
                          "fields": None})

    async def _pending_sweep(self) -> None:
        while True:
            await asyncio.sleep(self._pending_ttl / 2)
            cutoff = now().timestamp() - self._pending_ttl
            for key, (_, entry) in list(self._pending.items()):
                if entry["_at"].timestamp() < cutoff:
                    del self._pending[key]
                    self._emit_entry(entry)

    # ---- other deltas
    async def _on_alarm(self, ev: AlarmRaised) -> None:
        self._broadcast("alarm", {"ts": ev.ts.isoformat(), "apid": ev.apid, "field_name": ev.field_name,
                                  "value": ev.value, "threshold": ev.threshold, "alarm_type": ev.alarm_type})

    async def _on_gap(self, ev: SequenceGap) -> None:
        self._broadcast("gap", {"ts": ev.ts.isoformat(), "apid": ev.apid, "expected": ev.expected,
                                "received": ev.received, "missed": ev.missed})

    async def _on_command_started(self, ev: CommandStarted) -> None:
        self._last_command_name = ev.name
        self._broadcast("command", {"ts": ev.ts.isoformat(), "name": ev.name, "raw_hex": ev.raw_hex,
                                    "status": "acked", "response_hex": None, "latency_ms": None,
                                    "attempts": 0, "error": None, "pending": True})

    async def _on_command(self, ev: CommandCompleted) -> None:
        self._last_command_name = None
        d = ev.record.as_dict()
        d["pending"] = False
        self._broadcast("command", d)
        self._broadcast("status", self._station.status())

    async def _on_status_change(self, ev) -> None:
        self._broadcast("status", self._station.status())

    async def _on_pass_edge(self, ev) -> None:
        kind = "aos" if isinstance(ev, PassStarted) else "los"
        self._broadcast("pass", {"event": kind, "pass": pass_to_dict(ev.pass_)})
        self._broadcast("status", self._station.status())

    async def _on_pass_update(self, ev: PassUpdate) -> None:
        self._broadcast("pass", state_to_dict(ev.state))

    async def _status_poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._status_poll)
            state = self._station.storage.state
            if state != self._last_storage_state:
                self._last_storage_state = state
                self._broadcast("status", self._station.status())


def feed_entry_from_row(row: dict, decoded_rows: list[dict] | None = None) -> dict:
    """Shape a raw_packets DB row (+ its decoded_telemetry rows) like a live FeedEntry."""
    apid = row.get("apid")
    fields = [{"name": d["field_name"], "value": d["field_value"], "unit": d.get("unit"),
               "alarm": d.get("alarm_status")} for d in (decoded_rows or [])] or None
    direction = row.get("direction", "rx")
    if direction == "tx":
        kind = "command"
    elif apid is None:
        kind = "malformed"
    elif fields:
        kind = _KIND_BY_APID.get(apid, "telemetry")
    else:
        kind = "unknown"
    apid_name = decoded_rows[0].get("apid_name") if decoded_rows else None
    return {"id": str(row["id"]), "ts": row["timestamp"], "direction": direction, "apid": apid,
            "apid_name": apid_name, "seq": row.get("sequence_count"), "raw_hex": row.get("raw_hex", ""),
            "rssi": row.get("rssi"), "snr": row.get("snr"), "freq_mhz": row.get("frequency_mhz", 0.0),
            "kind": kind, "summary": summarize(kind, fields, name=f"TX {len(row.get('raw_hex', '')) // 2} B"),
            "fields": fields}
