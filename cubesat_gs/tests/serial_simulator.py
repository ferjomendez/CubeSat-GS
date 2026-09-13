"""Simulates the ESP32 LoRa modem + OBC_sim.py from the serial side.

Usable in-process (SimulatedSerial) or as a TCP server (see main() — added in Task 14)
so the GS can connect with serial.port = "socket://localhost:<port>".
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from cubesat_gs.core import ccsds

log = logging.getLogger(__name__)

BEACON_PAYLOAD = b"VLEO_BEACON_SYS_NOMINAL"
PONG_PAYLOAD = b"PONG_DATA_6.28"


class ModemSimulator:
    def __init__(self, *, beacon_interval: float = 10.0, length_includes_crc: bool = True,
                 sequence_scope: Literal["global", "per_apid"] = "global", fake_rssi: bool = False,
                 ping_apid: int = ccsds.APID_TELECOMMAND, tctm_mhz: float = 435.5,
                 beacon_mhz: float = 437.25) -> None:
        self.beacon_interval = beacon_interval
        self.length_includes_crc = length_includes_crc
        self.sequence_scope = sequence_scope
        self.fake_rssi = fake_rssi
        self.ping_apid = ping_apid
        self.tctm_mhz = tctm_mhz
        self.beacon_mhz = beacon_mhz

        self.freq: float = tctm_mhz
        self.received_tx: list[bytes] = []
        self.beacons_sent = 0
        self.silent = False  # when True, never send OK:* (simulates a dead/failing modem)
        self._counters: dict[int | None, int] = {}
        self._out: asyncio.Queue[str] = asyncio.Queue()
        self._beacon_task: asyncio.Task | None = None
        self._pending: set[asyncio.Task] = set()

    # ---- lifecycle
    async def start(self) -> None:
        if self._beacon_task is None:
            self._beacon_task = asyncio.create_task(self._beacon_loop())

    async def stop(self) -> None:
        for t in [self._beacon_task, *self._pending]:
            if t is not None:
                t.cancel()
        self._beacon_task = None
        self._pending.clear()

    # ---- serial side
    async def handle_line(self, line: str) -> None:
        line = line.strip()
        if line.startswith("TX:"):
            try:
                raw = bytes.fromhex(line[3:])
            except ValueError:
                log.warning("sim: bad hex in %r", line)
                return
            self.received_tx.append(raw)
            if self.silent:
                return
            self._out.put_nowait("OK:TX_DONE")
            if self.freq == self.tctm_mhz and b"PING" in raw[ccsds.HEADER_LEN:]:
                self._spawn(self._reply_pong())
        elif line.startswith("FREQ:"):
            try:
                self.freq = float(line[5:])
            except ValueError:
                return  # real firmware stays silent on failure
            if not self.silent:
                self._out.put_nowait("OK:FREQ_SET")
        else:
            log.debug("sim: ignoring %r", line)

    async def read_line(self) -> str:
        return await self._out.get()

    # ---- RF side
    def inject_rx(self, raw: bytes, rssi: float | None = None, snr: float | None = None) -> None:
        line = "RX:" + raw.hex().upper()
        if self.fake_rssi:
            rssi = -97.5 if rssi is None else rssi
            snr = 8.25 if snr is None else snr
        if rssi is not None and snr is not None:
            line += f"|RSSI:{rssi}|SNR:{snr}"
        self._out.put_nowait(line)

    def emit_beacon(self) -> None:
        self.inject_rx(self._build(ccsds.APID_BEACON, BEACON_PAYLOAD))
        self.beacons_sent += 1

    def _build(self, apid: int, payload: bytes) -> bytes:
        key = apid if self.sequence_scope == "per_apid" else None
        seq = self._counters.get(key, 0)
        self._counters[key] = (seq + 1) & 0x3FFF
        return ccsds.build(apid, payload, sequence_count=seq, packet_type=0,
                           length_includes_crc=self.length_includes_crc)

    async def _reply_pong(self) -> None:
        await asyncio.sleep(0.05)
        self.inject_rx(self._build(ccsds.APID_TM_RESPONSE, PONG_PAYLOAD))

    async def _beacon_loop(self) -> None:
        while True:
            await asyncio.sleep(self.beacon_interval)
            if self.freq == self.beacon_mhz:
                self.emit_beacon()

    def _spawn(self, coro) -> None:
        t = asyncio.create_task(coro)
        self._pending.add(t)
        t.add_done_callback(self._pending.discard)


class SimulatedWriter:
    """Minimal asyncio.StreamWriter stand-in that feeds lines into the simulator."""

    def __init__(self, sim: ModemSimulator) -> None:
        self._sim = sim
        self._buf = b""
        self._closed = False

    def write(self, data: bytes) -> None:
        self._buf += data
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            asyncio.get_running_loop().create_task(self._sim.handle_line(line.decode(errors="ignore")))

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self._closed = True

    def is_closing(self) -> bool:
        return self._closed

    async def wait_closed(self) -> None:
        return None


class SimulatedSerial:
    """Factory compatible with SerialHandler's `open_connection(url, baudrate)` argument."""

    def __init__(self, sim: ModemSimulator) -> None:
        self.sim = sim
        self._reader: asyncio.StreamReader | None = None
        self._pump: asyncio.Task | None = None
        self.open_count = 0
        self.fail_next_open = False

    async def open(self, url: str, baudrate: int) -> tuple[asyncio.StreamReader, SimulatedWriter]:
        if self.fail_next_open:
            self.fail_next_open = False
            raise OSError("simulated open failure")
        self.open_count += 1
        self._reader = asyncio.StreamReader()
        self._pump = asyncio.create_task(self._pump_output(self._reader))
        return self._reader, SimulatedWriter(self.sim)

    async def _pump_output(self, reader: asyncio.StreamReader) -> None:
        try:
            while True:
                line = await self.sim.read_line()
                reader.feed_data(line.encode() + b"\n")
        except asyncio.CancelledError:
            pass

    def close_from_modem_side(self) -> None:
        if self._pump:
            self._pump.cancel()
        if self._reader:
            self._reader.feed_eof()
