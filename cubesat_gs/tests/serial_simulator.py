"""Simulates the ESP32 LoRa modem + the satellite from the serial side.

Satellite side: legacy OBC_sim.py (PING/PONG, beacons) and the cFS OBC TELECOM/OBC_HK apps
(github.com/vaquitson/uai_obc) as described in its mision_doc/functionality.md.

Usable in-process (SimulatedSerial) or as a TCP server (see main() — added in Task 14)
so the GS can connect with serial.port = "socket://localhost:<port>".
"""
from __future__ import annotations

import asyncio
import logging
import struct
from typing import Literal

from cubesat_gs.core import ccsds, cfs

log = logging.getLogger(__name__)

BEACON_PAYLOAD = b"VLEO_BEACON_SYS_NOMINAL"
PONG_PAYLOAD = b"PONG_DATA_6.28"

# cFS OBC message ids / function codes (uai_obc apps/*/config)
TELECOM_CMD_MID, TELECOM_SEND_HK_MID = 0x187A, 123
TELECOM_HK_TLM_MID, TELECOM_OPEN_TLM_MID = 124, 125
TELECOM_OPEN_TLM_CC = 2
OBC_HK_CMD_MID, OBC_HK_SEND_HK_MID, OBC_HK_HK_MID = 100, 101, 102
OBC_HK_REPLIES = {  # function code -> (tlm MsgId, little-endian payload)
    104: (103, struct.pack("<ffif", 47.5, 31.25, 262144, 12.5)),
    105: (104, struct.pack("<f", 47.5)),
    106: (105, struct.pack("<fi", 31.25, 262144)),
    107: (106, struct.pack("<f", 12.5)),
}


class ModemSimulator:
    def __init__(self, *, beacon_interval: float = 10.0, length_includes_crc: bool = True,
                 sequence_scope: Literal["global", "per_apid"] = "global", fake_rssi: bool = False,
                 tctm_mhz: float = 435.5, beacon_mhz: float = 437.25) -> None:
        self.beacon_interval = beacon_interval
        self.length_includes_crc = length_includes_crc
        self.sequence_scope = sequence_scope
        self.fake_rssi = fake_rssi
        self.tctm_mhz = tctm_mhz
        self.beacon_mhz = beacon_mhz

        self.freq: float = tctm_mhz
        self.received_tx: list[bytes] = []
        # cFS OBC radio state: listens on uplink, downlinks only after TELECOM_OPEN_TLM
        self.obc_uplink_mhz: float = tctm_mhz
        self.obc_downlink_mhz: float = tctm_mhz
        self.obc_downlink_on = False
        self.obc_cmd_counter = 0
        self.obc_time = 1000
        self._cfs_counters: dict[int, int] = {}
        self.beacons_sent = 0
        self.silent = False  # when True, the modem emits nothing (dead/failing modem)
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
            valid_hex = True
            try:
                raw = bytes.fromhex(line[3:])
            except ValueError:
                log.warning("sim: bad hex in %r", line)
                valid_hex = False
            if valid_hex:
                self.received_tx.append(raw)
                if self.freq == self.tctm_mhz and b"PING" in raw[ccsds.HEADER_LEN:]:
                    self._spawn(self._reply_pong())
                elif self.freq == self.obc_uplink_mhz:
                    self._cfs_uplink(raw)
            self._emit("OK:TX_DONE")
        elif line.startswith("FREQ:"):
            try:
                self.freq = float(line[5:])
            except ValueError:
                return  # real firmware stays silent on failure
            self._emit("OK:FREQ_SET")
        else:
            log.debug("sim: ignoring %r", line)

    async def read_line(self) -> str:
        return await self._out.get()

    def _emit(self, line: str) -> None:
        """Emit a line to the output queue, subject to silent mode."""
        if not self.silent:
            self._out.put_nowait(line)

    # ---- RF side
    def inject_rx(self, raw: bytes, rssi: float | None = None, snr: float | None = None) -> None:
        line = "RX:" + raw.hex().upper()
        if self.fake_rssi:
            rssi = -97.5 if rssi is None else rssi
            snr = 8.25 if snr is None else snr
        if rssi is not None and snr is not None:
            line += f"|RSSI:{rssi}|SNR:{snr}"
        self._emit(line)

    def emit_beacon(self) -> None:
        self.inject_rx(self._build(ccsds.APID_BEACON, BEACON_PAYLOAD))
        self.beacons_sent += 1

    def _build(self, apid: int, payload: bytes) -> bytes:
        key = apid if self.sequence_scope == "per_apid" else None
        seq = self._counters.get(key, 0)
        self._counters[key] = (seq + 1) & 0x3FFF
        return ccsds.build(apid, payload, sequence_count=seq, packet_type=0,
                           length_includes_crc=self.length_includes_crc)

    # ---- cFS OBC
    def _cfs_uplink(self, raw: bytes) -> None:
        if len(raw) < 8 or cfs.checksum(raw) != 0:
            return
        msg_id, fc, body = int.from_bytes(raw[0:2], "big"), raw[6] & 0x7F, raw[8:]
        if msg_id == TELECOM_CMD_MID and fc == TELECOM_OPEN_TLM_CC and len(body) >= 32:
            self.obc_cmd_counter += 1
            down, up = _c_str(body[0:16]), _c_str(body[16:32])
            try:
                self.obc_downlink_mhz = cfs.parse_freq(down)
                if up:
                    self.obc_uplink_mhz = cfs.parse_freq(up)
                status = 0
            except ValueError:
                status = 1
            self.obc_downlink_on = True
            self._spawn(self._downlink(TELECOM_OPEN_TLM_MID, struct.pack("<I", status)))
        elif msg_id == TELECOM_SEND_HK_MID:
            self.obc_cmd_counter += 1
            payload = bytes([0, self.obc_cmd_counter & 0xFF]) + _c_freq(self.obc_downlink_mhz) +                 _c_freq(self.obc_uplink_mhz)
            self._spawn(self._downlink(TELECOM_HK_TLM_MID, payload))
        elif msg_id == OBC_HK_SEND_HK_MID:
            self._spawn(self._downlink(OBC_HK_HK_MID, bytes([self.obc_cmd_counter & 0xFF, 0])))
        elif msg_id == OBC_HK_CMD_MID and fc in OBC_HK_REPLIES:
            self._spawn(self._downlink(*OBC_HK_REPLIES[fc]))

    def cfs_tlm(self, msg_id: int, payload: bytes) -> bytes:
        """A cFE telemetry packet: primary header + time + spare + payload, standard length, per-MID seq."""
        self.obc_time += 1
        seq = self._cfs_counters.get(msg_id, 0)
        self._cfs_counters[msg_id] = (seq + 1) & 0x3FFF
        ptype, sec, apid = cfs.split_msg_id(msg_id)
        body = struct.pack(">IH", self.obc_time, 0x8000) + bytes(4) + payload
        return ccsds.build(apid, body, sequence_count=seq, packet_type=ptype, sec_header_flag=sec,
                           length_includes_crc=False)

    async def _downlink(self, msg_id: int, payload: bytes) -> None:
        await asyncio.sleep(0.05)
        # heard only when downlink is open and the GS modem listens on the OBC's downlink frequency
        if self.obc_downlink_on and self.freq == self.obc_downlink_mhz:
            self.inject_rx(self.cfs_tlm(msg_id, payload))

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


def _c_str(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("ascii", errors="replace")


def _c_freq(mhz: float) -> bytes:
    return f"{mhz:.3f}".replace(".", ",").encode().ljust(16, b"\x00")


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


# ---------------------------------------------------------------- TCP transport (serial.port = "socket://host:port")

async def serve_tcp(sim: ModemSimulator, host: str, port: int) -> tuple[asyncio.AbstractServer, int]:
    """Serve the modem protocol over TCP. One client at a time gets the output stream."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        log.info("sim: client connected %s", peer)

        async def pump() -> None:
            while True:
                line = await sim.read_line()
                writer.write(line.encode() + b"\n")
                await writer.drain()

        pump_task = asyncio.create_task(pump())
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                await sim.handle_line(data.decode(errors="ignore"))
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            pump_task.cancel()
            writer.close()
            log.info("sim: client disconnected %s", peer)

    server = await asyncio.start_server(handle, host, port)
    bound = server.sockets[0].getsockname()[1]
    await sim.start()
    return server, bound


async def _main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="ESP32 LoRa modem + OBC simulator over TCP")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--beacon-interval", type=float, default=10.0)
    ap.add_argument("--rssi", action="store_true", help="append |RSSI|SNR to RX lines")
    ap.add_argument("--per-apid-seq", action="store_true", help="standard per-APID sequence counters")
    ap.add_argument("--standard-length", action="store_true", help="data_length excludes CRC (strict CCSDS)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sim = ModemSimulator(beacon_interval=a.beacon_interval, fake_rssi=a.rssi,
                         sequence_scope="per_apid" if a.per_apid_seq else "global",
                         length_includes_crc=not a.standard_length)
    server, port = await serve_tcp(sim, a.host, a.port)
    log.info("sim: listening on %s:%d — set serial.port: \"socket://%s:%d\"", a.host, port, a.host, port)
    try:
        await server.serve_forever()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await sim.stop()
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
