"""Telecommand registry, sending with retry, and response correlation."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CommandConfig
from cubesat_gs.core.events import CommandCompleted, EventBus, PacketReceived, now
from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.serial_handler import SerialCommandTimeout, SerialDisconnected

log = logging.getLogger(__name__)


class CommandBusyError(Exception):
    """Another command is still waiting for its response."""


class WrongModeError(Exception):
    """Frequency manager is not in TCTM mode."""


class UnknownCommandError(KeyError):
    """Command name not in the registry."""


@dataclass(frozen=True)
class CommandDef:
    name: str
    description: str
    apid: int
    payload: bytes
    response_apid: int | None
    timeout: float
    critical: bool


@dataclass
class CommandRecord:
    ts: datetime
    name: str
    raw_hex: str
    status: str  # acked | responded | timeout | failed | refused
    response_hex: str | None = None
    latency_ms: float | None = None
    attempts: int = 0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ts"] = self.ts.isoformat()
        return d


def _payload_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    s = "" if value is None else str(value)
    if s.lower().startswith("0x"):
        return bytes.fromhex(s[2:])
    return s.encode("utf-8")


def load_commands(path: str | Path, default_timeout: float) -> dict[str, CommandDef]:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out: dict[str, CommandDef] = {}
    for i, c in enumerate(data.get("commands") or []):
        if not isinstance(c, dict) or "name" not in c or "apid" not in c:
            raise ValueError(f"{path}: commands[{i}] needs 'name' and 'apid'")
        name = str(c["name"])
        if name in out:
            raise ValueError(f"{path}: duplicate command {name!r}")
        out[name] = CommandDef(
            name=name, description=str(c.get("description", "")), apid=int(c["apid"]),
            payload=_payload_bytes(c.get("payload", "")),
            response_apid=None if c.get("response_apid") is None else int(c["response_apid"]),
            timeout=float(c.get("timeout", default_timeout)), critical=bool(c.get("critical", False)),
        )
    return out


class TelecommandManager:
    def __init__(self, bus: EventBus, serial, freq_mgr, builder: ccsds.PacketBuilder,
                 cfg: CommandConfig, registry_path: str | Path) -> None:
        self._bus = bus
        self._serial = serial
        self._freq = freq_mgr
        self._builder = builder
        self._cfg = cfg
        self.commands = load_commands(registry_path, cfg.default_timeout)
        self.history: deque[CommandRecord] = deque(maxlen=cfg.history_size)
        self.pending: CommandRecord | None = None
        log.info("telecommand: %d commands loaded", len(self.commands))

    # ---- public
    async def send_command(self, name: str, *, confirm: bool = False,
                           payload_override: bytes | None = None) -> CommandRecord:
        cdef = self.commands.get(name)
        if cdef is None:
            raise UnknownCommandError(name)
        payload = cdef.payload if payload_override is None else payload_override
        if cdef.critical and not confirm:
            rec = CommandRecord(now(), name, payload.hex().upper(), "refused",
                                error="critical command requires confirm=True")
            self._finish(rec)
            return rec
        return await self._execute(cdef.name, self._builder.build(cdef.apid, payload),
                                   cdef.response_apid, cdef.timeout)

    async def send_raw(self, hex_str: str) -> CommandRecord:
        try:
            raw = bytes.fromhex(hex_str.replace(" ", ""))
        except ValueError as e:
            raise ValueError(f"invalid hex: {hex_str!r}") from e
        return await self._execute("RAW", raw, None, self._cfg.default_timeout)

    # ---- core
    async def _execute(self, name: str, raw: bytes, response_apid: int | None,
                       timeout: float) -> CommandRecord:
        if self._freq.mode is not Mode.TCTM:
            raise WrongModeError(f"frequency mode is {self._freq.mode.value}, need tctm")
        if self.pending is not None:
            raise CommandBusyError(f"{self.pending.name} still pending")
        rec = CommandRecord(now(), name, raw.hex().upper(), "failed")
        self.pending = rec
        try:
            for attempt in range(1, self._cfg.max_retries + 2):
                rec.attempts = attempt
                try:
                    await self._serial.send_tx(raw)
                except (SerialCommandTimeout, SerialDisconnected) as e:
                    rec.status, rec.error = "failed", f"{type(e).__name__}: {e}"
                    break
                t0 = time.monotonic()
                if response_apid is None:
                    rec.status = "acked"
                    break
                try:
                    ev = await self._bus.wait_for(
                        PacketReceived, lambda e: _apid_of(e.raw) == response_apid, timeout)
                except asyncio.TimeoutError:
                    rec.status, rec.error = "timeout", f"no APID {response_apid} within {timeout}s"
                    if attempt <= self._cfg.max_retries:
                        delay = self._cfg.retry_backoff ** attempt
                        log.warning("telecommand: %s attempt %d timed out, retrying in %.2fs", name, attempt, delay)
                        await asyncio.sleep(delay)
                    continue
                rec.status = "responded"
                rec.error = None
                rec.response_hex = ev.raw.hex().upper()
                rec.latency_ms = (time.monotonic() - t0) * 1000.0
                break
        finally:
            self.pending = None
        self._finish(rec)
        return rec

    def _finish(self, rec: CommandRecord) -> None:
        self.history.append(rec)
        log.info("telecommand: %s -> %s (attempts=%d, latency=%s)", rec.name, rec.status,
                 rec.attempts, rec.latency_ms)
        self._bus.publish(CommandCompleted(record=rec))


def _apid_of(raw: bytes) -> int | None:
    peek = ccsds.peek_apid_seq(raw)
    return None if peek is None else peek[0]
