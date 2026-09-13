"""Async serial interface to the ESP32 LoRa modem (or the simulator)."""
from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import Awaitable, Callable

from cubesat_gs.core.config import SerialConfig
from cubesat_gs.core.events import (ConnectionChanged, EventBus, ModemAck, PacketReceived,
                                    PacketSent, SerialError)

log = logging.getLogger(__name__)

OpenConnection = Callable[[str, int], Awaitable[tuple[asyncio.StreamReader, object]]]

# USB-UART bridge vendor IDs commonly found on ESP32 dev boards
_KNOWN_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}


class SerialCommandTimeout(Exception):
    """The modem did not acknowledge a command in time."""


class SerialDisconnected(Exception):
    """The connection dropped while a command was in flight."""


def parse_rx_line(line: str) -> tuple[bytes, float | None, float | None]:
    """'RX:<hex>[|RSSI:<f>|SNR:<f>]' -> (raw, rssi, snr). Raises ValueError on bad hex."""
    body = line[3:].strip()
    parts = body.split("|")
    try:
        raw = bytes.fromhex(parts[0])
    except ValueError as e:
        raise ValueError(f"invalid hex in RX line: {parts[0]!r}") from e
    rssi = snr = None
    for tok in parts[1:]:
        key, _, val = tok.partition(":")
        try:
            if key.upper() == "RSSI":
                rssi = float(val)
            elif key.upper() == "SNR":
                snr = float(val)
        except ValueError:
            log.debug("serial: unparsable %s value %r", key, val)
    return raw, rssi, snr


def detect_port() -> str | None:
    """First plausible USB serial device: prefers known USB-UART VIDs, else any ttyUSB/ttyACM/COM."""
    from serial.tools import list_ports
    candidates = []
    for p in list_ports.comports():
        dev = p.device
        if sys.platform.startswith("win"):
            ok = dev.upper().startswith("COM")
        else:
            ok = dev.startswith("/dev/ttyUSB") or dev.startswith("/dev/ttyACM")
        if ok:
            candidates.append(p)
    if not candidates:
        return None
    for p in candidates:
        if p.vid in _KNOWN_VIDS:
            return p.device
    return candidates[0].device


async def default_open_connection(url: str, baudrate: int):
    if url.startswith("socket://"):
        host, _, port = url[len("socket://"):].partition(":")
        return await asyncio.open_connection(host or "localhost", int(port or 5000))
    import serial_asyncio
    return await serial_asyncio.open_serial_connection(url=url, baudrate=baudrate)


@dataclass
class _Cmd:
    line: str
    ack_kind: str
    timeout: float
    done: asyncio.Future
    ack: asyncio.Future


class SerialHandler:
    def __init__(self, bus: EventBus, cfg: SerialConfig, get_freq: Callable[[], float],
                 open_connection: OpenConnection | None = None) -> None:
        self._bus = bus
        self._cfg = cfg
        self._get_freq = get_freq
        self._open = open_connection or default_open_connection
        self._queue: asyncio.Queue[_Cmd] = asyncio.Queue()
        self._inflight: _Cmd | None = None
        self._connected = False
        self._port: str | None = None
        self._run_task: asyncio.Task | None = None
        self._writer = None
        self._stopping = False
        self._announced: bool | None = None  # last published connection state

    # ---- public
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str | None:
        return self._port

    async def start(self) -> None:
        self._stopping = False
        self._run_task = asyncio.create_task(self._run(), name="serial-run")

    async def stop(self) -> None:
        self._stopping = True
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
            self._run_task = None
        while not self._queue.empty():
            cmd = self._queue.get_nowait()
            if not cmd.done.done():
                cmd.done.set_exception(SerialDisconnected("handler stopped"))
        self._close_writer()
        self._set_connected(False)

    async def send_tx(self, raw: bytes) -> None:
        await self._submit("TX:" + raw.hex().upper(), "TX_DONE", self._cfg.timeouts.tx)
        self._bus.publish(PacketSent(raw=bytes(raw), freq_mhz=self._get_freq()))

    async def set_frequency(self, mhz: float) -> None:
        await self._submit(f"FREQ:{mhz:.3f}", "FREQ_SET", self._cfg.timeouts.freq)

    # ---- command queue
    async def _submit(self, line: str, ack_kind: str, timeout: float) -> None:
        if self._stopping:
            raise SerialDisconnected("handler stopped")
        loop = asyncio.get_running_loop()
        cmd = _Cmd(line, ack_kind, timeout, loop.create_future(), loop.create_future())
        await self._queue.put(cmd)
        if self._stopping and not cmd.done.done():
            # stop() may have already drained the queue before this cmd was put onto it;
            # nothing will ever consume it now, so it would otherwise hang forever. In
            # practice stop() drains and fails every queued cmd.done itself, so this branch
            # is not reachable from the existing tests -- cancel() rather than
            # set_exception() so an exception nobody awaits can't log "Future exception was
            # never retrieved" if this ever does fire.
            cmd.done.cancel()
            raise SerialDisconnected("handler stopped")
        await cmd.done

    async def _writer_loop(self, writer) -> None:
        while True:
            cmd = await self._queue.get()
            if cmd.done.done():
                continue
            self._inflight = cmd
            try:
                writer.write((cmd.line + "\n").encode())
                await writer.drain()
                # Not asyncio.wait_for(cmd.ack, cmd.timeout): on 3.11 that can lose a
                # cancellation that lands in the same loop step as the ack (gh-86296),
                # wedging this loop forever. asyncio.wait() never swallows cancellation.
                done, _ = await asyncio.wait({cmd.ack}, timeout=cmd.timeout)
                if not done:
                    raise asyncio.TimeoutError
            except asyncio.TimeoutError:
                log.warning("serial: no %s within %.1fs for %r", cmd.ack_kind, cmd.timeout, cmd.line)
                if not cmd.done.done():
                    cmd.done.set_exception(SerialCommandTimeout(cmd.line))
            except asyncio.CancelledError:
                if not cmd.done.done():
                    cmd.done.set_exception(SerialDisconnected(cmd.line))
                raise
            except Exception as e:  # noqa: BLE001 - write failure = link is gone
                if not cmd.done.done():
                    cmd.done.set_exception(SerialDisconnected(str(e)))
                raise
            else:
                if not cmd.done.done():
                    cmd.done.set_result(None)
            finally:
                self._inflight = None

    # ---- reader
    async def _reader_loop(self, reader: asyncio.StreamReader) -> None:
        while True:
            data = await reader.readline()
            if not data:
                raise ConnectionError("EOF from modem")
            line = data.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        if line.startswith("RX:"):
            try:
                raw, rssi, snr = parse_rx_line(line)
            except ValueError as e:
                self._bus.publish(SerialError(message=str(e)))
                return
            self._bus.publish(PacketReceived(raw=raw, rssi=rssi, snr=snr, freq_mhz=self._get_freq()))
        elif line.startswith("OK:"):
            kind = line[3:].strip()
            cmd = self._inflight
            if cmd is not None and cmd.ack_kind == kind and not cmd.ack.done():
                cmd.ack.set_result(None)
            else:
                log.debug("serial: unexpected ack %r", line)
            self._bus.publish(ModemAck(kind=kind))
        else:
            log.debug("serial: modem says %r", line)

    # ---- connection lifecycle
    async def _run(self) -> None:
        while not self._stopping:
            port = self._cfg.port
            if port == "auto":
                port = detect_port()
            if port is None:
                self._set_connected(False, "auto")
                await asyncio.sleep(self._cfg.reconnect_interval)
                continue
            try:
                reader, writer = await self._open(port, self._cfg.baudrate)
            except Exception as e:  # noqa: BLE001 - OSError, SerialException, ConnectionRefusedError...
                log.warning("serial: cannot open %s: %s", port, e)
                self._set_connected(False, port)
                await asyncio.sleep(self._cfg.reconnect_interval)
                continue

            self._writer = writer
            self._port = port
            self._set_connected(True, port)
            writer_task = asyncio.create_task(self._writer_loop(writer), name="serial-writer")
            try:
                await self._reader_loop(reader)
            except (ConnectionError, OSError) as e:
                log.warning("serial: link lost on %s: %s", port, e)
            finally:
                writer_task.cancel()
                try:
                    await asyncio.wait_for(writer_task, timeout=1.0)
                except asyncio.TimeoutError:
                    log.warning("serial: writer task did not stop within 1.0s on %s", port)
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
                self._close_writer()
                self._set_connected(False, port)
            await asyncio.sleep(self._cfg.reconnect_interval)

    def _close_writer(self) -> None:
        w, self._writer = self._writer, None
        if w is not None:
            try:
                w.close()
            except Exception:  # noqa: BLE001
                pass

    def _set_connected(self, value: bool, port: str | None = None) -> None:
        """Publish ConnectionChanged only on an actual transition (first call always publishes)."""
        self._connected = value
        if value == self._announced:
            return
        self._announced = value
        self._bus.publish(ConnectionChanged(connected=value, port=port or self._port or ""))
