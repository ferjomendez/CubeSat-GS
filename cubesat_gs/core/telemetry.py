"""YAML-driven telemetry decoder with alarm evaluation."""
from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CCSDSConfig
from cubesat_gs.core.events import (AlarmRaised, EventBus, PacketDecoded, PacketMalformed,
                                    PacketReceived, SequenceGap)

log = logging.getLogger(__name__)

_NUMERIC = {
    "uint8": ">B", "int8": ">b", "uint16": ">H", "int16": ">h",
    "uint32": ">I", "int32": ">i", "float32": ">f",
}
_TYPES = set(_NUMERIC) | {"string", "bytes"}


class TelemetryDefError(ValueError):
    """Invalid telemetry_defs.yaml."""


@dataclass(frozen=True)
class FieldDef:
    name: str
    type: str
    unit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    alarm_low: float | None = None
    alarm_high: float | None = None
    length: int | None = None
    encoding: str = "utf-8"


@dataclass(frozen=True)
class ApidDef:
    apid: int
    name: str
    fields: tuple[FieldDef, ...]


@dataclass
class DecodedField:
    name: str
    value: Any
    unit: str | None
    alarm: str | None  # "nominal" | "low" | "high" | None (no thresholds)
    raw: bytes


@dataclass
class DecodedPacket:
    apid: int
    apid_name: str
    fields: list[DecodedField] = field(default_factory=list)
    unknown_apid: bool = False
    partial: bool = False
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {f.name: f.value for f in self.fields}


def _parse_field(apid_key: str, raw: dict) -> FieldDef:
    where = f"{apid_key}.fields[{raw.get('name', '?')}]"
    if not isinstance(raw, dict) or "name" not in raw or "type" not in raw:
        raise TelemetryDefError(f"{where}: each field needs 'name' and 'type'")
    t = str(raw["type"])
    if t not in _TYPES:
        raise TelemetryDefError(f"{where}: unknown type {t!r}")
    if t in _NUMERIC and "length" in raw:
        raise TelemetryDefError(f"{where}: 'length' is only valid for string/bytes")
    if t not in _NUMERIC and ("scale" in raw or "offset" in raw):
        raise TelemetryDefError(f"{where}: 'scale'/'offset' only valid for numeric types")
    if t not in _NUMERIC and (raw.get("alarm_low") is not None or raw.get("alarm_high") is not None):
        raise TelemetryDefError(f"{where}: 'alarm_low'/'alarm_high' only valid for numeric types")
    alarm_low = alarm_high = None
    if raw.get("alarm_low") is not None:
        try:
            alarm_low = float(raw["alarm_low"])
        except (TypeError, ValueError) as e:
            raise TelemetryDefError(f"{where}: 'alarm_low' must be a number, got {raw['alarm_low']!r}") from e
    if raw.get("alarm_high") is not None:
        try:
            alarm_high = float(raw["alarm_high"])
        except (TypeError, ValueError) as e:
            raise TelemetryDefError(f"{where}: 'alarm_high' must be a number, got {raw['alarm_high']!r}") from e
    length = None
    if raw.get("length") is not None:
        try:
            length = int(raw["length"])
        except (TypeError, ValueError) as e:
            raise TelemetryDefError(f"{where}: 'length' must be an integer, got {raw['length']!r}") from e
        if length < 0:
            raise TelemetryDefError(f"{where}: 'length' must be >= 0, got {length}")
    return FieldDef(
        name=str(raw["name"]), type=t, unit=raw.get("unit"),
        scale=float(raw.get("scale", 1.0)), offset=float(raw.get("offset", 0.0)),
        alarm_low=alarm_low, alarm_high=alarm_high,
        length=length, encoding=str(raw.get("encoding", "utf-8")),
    )


def load_definitions(path: str | Path) -> dict[int, ApidDef]:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    defs: dict[int, ApidDef] = {}
    for key, body in data.items():
        if not str(key).startswith("apid_"):
            raise TelemetryDefError(f"top-level key {key!r} must look like apid_<n>")
        try:
            apid = int(str(key)[5:])
        except ValueError as e:
            raise TelemetryDefError(f"bad apid in key {key!r}") from e
        body = body or {}
        fields = tuple(_parse_field(str(key), f) for f in (body.get("fields") or []))
        defs[apid] = ApidDef(apid=apid, name=str(body.get("name", f"APID {apid}")), fields=fields)
    return defs


def _alarm(value: float, fd: FieldDef) -> str | None:
    if fd.alarm_low is None and fd.alarm_high is None:
        return None
    if fd.alarm_low is not None and value < fd.alarm_low:
        return "low"
    if fd.alarm_high is not None and value > fd.alarm_high:
        return "high"
    return "nominal"


def decode_payload(apid_def: ApidDef, payload: bytes) -> DecodedPacket:
    out = DecodedPacket(apid=apid_def.apid, apid_name=apid_def.name)
    pos = 0
    for fd in apid_def.fields:
        if fd.type in _NUMERIC:
            fmt = _NUMERIC[fd.type]
            size = struct.calcsize(fmt)
            chunk = payload[pos:pos + size]
            if len(chunk) < size:
                out.partial, out.error = True, f"payload exhausted at field {fd.name!r}"
                break
            value = struct.unpack(fmt, chunk)[0] * fd.scale + fd.offset
            if fd.type != "float32" and fd.scale == 1.0 and fd.offset == 0.0:
                value = int(value)
            out.fields.append(DecodedField(fd.name, value, fd.unit, _alarm(value, fd), chunk))
        else:
            chunk = payload[pos:] if fd.length is None else payload[pos:pos + fd.length]
            if fd.length is not None and len(chunk) < fd.length:
                out.partial, out.error = True, f"payload exhausted at field {fd.name!r}"
                break
            size = len(chunk)
            value: Any = chunk.decode(fd.encoding, errors="replace") if fd.type == "string" else bytes(chunk)
            out.fields.append(DecodedField(fd.name, value, fd.unit, None, chunk))
        pos += size
    return out


class TelemetryDecoder:
    def __init__(self, bus: EventBus, defs_path: str | Path, ccsds_cfg: CCSDSConfig) -> None:
        self._bus = bus
        self._cfg = ccsds_cfg
        self.definitions = load_definitions(defs_path)
        self._tracker = ccsds.SequenceTracker(ccsds_cfg.sequence_scope)  # type: ignore[arg-type]
        self.last_values: dict[int, DecodedPacket] = {}
        log.info("telemetry: loaded %d APID definitions", len(self.definitions))

    def start(self) -> None:
        self._bus.subscribe(PacketReceived, self._on_packet)

    def stop(self) -> None:
        self._bus.unsubscribe(PacketReceived, self._on_packet)

    def decode(self, packet: ccsds.CCSDSPacket) -> DecodedPacket:
        apid_def = self.definitions.get(packet.apid)
        if apid_def is None:
            return DecodedPacket(
                apid=packet.apid, apid_name="UNKNOWN", unknown_apid=True,
                fields=[DecodedField("raw_hex", packet.payload.hex(), None, None, packet.payload)],
            )
        return decode_payload(apid_def, packet.payload)

    async def _on_packet(self, ev: PacketReceived) -> None:
        try:
            packet = ccsds.parse(ev.raw, length_includes_crc=self._cfg.length_includes_crc)
        except ccsds.CCSDSError as e:
            log.warning("telemetry: malformed packet %s: %s", ev.raw.hex(), e)
            self._bus.publish(PacketMalformed(source=ev, reason=str(e)))
            return
        missed = self._tracker.observe(packet)
        if missed:
            expected = (packet.sequence_count - missed) & 0x3FFF
            log.warning("telemetry: APID %d gap: expected seq %d, got %d (%d missed)",
                        packet.apid, expected, packet.sequence_count, missed)
            self._bus.publish(SequenceGap(apid=packet.apid, expected=expected,
                                          received=packet.sequence_count, missed=missed))
        decoded = self.decode(packet)
        self.last_values[packet.apid] = decoded
        self._bus.publish(PacketDecoded(source=ev, packet=packet, decoded=decoded))
        for f in decoded.fields:
            if f.alarm in ("low", "high"):
                fd = next(x for x in self.definitions[packet.apid].fields if x.name == f.name)
                threshold = fd.alarm_low if f.alarm == "low" else fd.alarm_high
                self._bus.publish(AlarmRaised(source=ev, apid=packet.apid, field_name=f.name,
                                              value=f.value, threshold=float(threshold),
                                              alarm_type=f.alarm))
