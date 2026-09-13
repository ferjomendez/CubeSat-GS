"""Central asyncio event bus and the event dataclasses shared by all modules."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

log = logging.getLogger(__name__)

E = TypeVar("E")
Handler = Callable[[Any], Awaitable[None]]


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- events

@dataclass(frozen=True)
class ConnectionChanged:
    connected: bool
    port: str
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class SerialError:
    message: str
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketReceived:
    raw: bytes
    rssi: float | None
    snr: float | None
    freq_mhz: float
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketSent:
    raw: bytes
    freq_mhz: float
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class ModemAck:
    kind: str  # "TX_DONE" | "FREQ_SET"
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class SequenceGap:
    apid: int
    expected: int
    received: int
    missed: int
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketDecoded:
    source: PacketReceived
    packet: Any      # ccsds.CCSDSPacket
    decoded: Any     # telemetry.DecodedPacket
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketMalformed:
    source: PacketReceived
    reason: str
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class AlarmRaised:
    source: PacketReceived
    apid: int
    field_name: str
    value: float
    threshold: float
    alarm_type: str  # "low" | "high"
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class CommandCompleted:
    record: Any  # telecommand.CommandRecord
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class FrequencyChanged:
    mode: Any    # frequency_manager.Mode
    mhz: float
    ts: datetime = field(default_factory=now)


# ---------------------------------------------------------------- bus

class EventBus:
    """Fan-out of events to async handlers. Handlers run as tasks; exceptions are logged, never raised."""

    def __init__(self) -> None:
        self._subs: dict[type, list[Handler]] = defaultdict(list)
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._subs[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        try:
            self._subs[event_type].remove(handler)
        except ValueError:
            pass

    def subscriber_count(self, event_type: type) -> int:
        return len(self._subs.get(event_type, []))

    def publish(self, event: Any) -> None:
        for handler in list(self._subs.get(type(event), [])):
            task = asyncio.ensure_future(self._run(handler, event))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _run(self, handler: Handler, event: Any) -> None:
        try:
            await handler(event)
        except Exception:  # noqa: BLE001 - isolation is the point
            log.exception("event handler %r failed for %r", handler, event)

    async def wait_for(self, event_type: type, predicate: Callable[[Any], bool] | None = None,
                       timeout: float | None = None) -> Any:
        """Await the next event of `event_type` matching `predicate`. Raises asyncio.TimeoutError."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()

        async def _once(ev: Any) -> None:
            if not fut.done() and (predicate is None or predicate(ev)):
                fut.set_result(ev)

        self.subscribe(event_type, _once)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self.unsubscribe(event_type, _once)

    async def drain(self) -> None:
        """Wait for all in-flight handler tasks (used by tests and shutdown)."""
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
