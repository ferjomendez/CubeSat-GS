"""Operating-frequency modes and switching via the modem's FREQ command."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from enum import Enum

from cubesat_gs.core.config import FrequencyConfig
from cubesat_gs.core.events import ConnectionChanged, EventBus, FrequencyChanged

log = logging.getLogger(__name__)


class Mode(str, Enum):
    BEACON_LISTEN = "beacon_listen"
    TCTM = "tctm"
    CUSTOM = "custom"


class FrequencyManager:
    def __init__(self, bus: EventBus, serial, cfg: FrequencyConfig) -> None:
        self._bus = bus
        self._serial = serial
        self._cfg = cfg
        self._mode = Mode.TCTM
        self._mhz = cfg.tctm  # matches the ESP32 firmware boot default
        self._lock = asyncio.Lock()
        self.history: deque[FrequencyChanged] = deque(maxlen=100)

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def mhz(self) -> float:
        return self._mhz

    def start(self) -> None:
        self._bus.subscribe(ConnectionChanged, self._on_connection)

    def stop(self) -> None:
        self._bus.unsubscribe(ConnectionChanged, self._on_connection)

    def _target_mhz(self, mode: Mode, mhz: float | None) -> float:
        if mode is Mode.TCTM:
            return self._cfg.tctm
        if mode is Mode.BEACON_LISTEN:
            return self._cfg.beacon
        if mhz is None:
            raise ValueError("CUSTOM mode requires an explicit mhz")
        return float(mhz)

    async def set_mode(self, mode: Mode, mhz: float | None = None) -> None:
        target = self._target_mhz(mode, mhz)
        async with self._lock:
            await self._serial.set_frequency(target)  # raises on timeout; state unchanged
            self._mode, self._mhz = mode, target
            ev = FrequencyChanged(mode=mode, mhz=target)
            self.history.append(ev)
            log.info("frequency: %s -> %.3f MHz", mode.value, target)
            self._bus.publish(ev)

    async def _on_connection(self, ev: ConnectionChanged) -> None:
        if not ev.connected:
            return
        try:
            async with self._lock:
                await self._serial.set_frequency(self._mhz)
            log.info("frequency: re-applied %.3f MHz after connect", self._mhz)
        except Exception as e:  # noqa: BLE001 - modem may not answer yet; next set_mode will retry
            log.warning("frequency: could not re-apply %.3f MHz: %s", self._mhz, e)
