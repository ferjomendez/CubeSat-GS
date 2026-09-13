"""Full stack: GroundStation + in-process ModemSimulator + SQLite. No hardware, no network."""
import asyncio

import pytest

from cubesat_gs.core.config import load_config
from cubesat_gs.core.events import PacketDecoded, SequenceGap
from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.station import GroundStation
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial


async def _wait_until(pred, timeout=2.0):
    async def _w():
        while not pred():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_w(), timeout)


@pytest.fixture
async def gs(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    cfg = load_config(dotenv=False)
    cfg.serial.port = "sim://"
    cfg.serial.reconnect_interval = 0.05
    cfg.serial.timeouts.tx = 0.5
    cfg.serial.timeouts.freq = 0.5
    cfg.database.local_fallback_path = str(tmp_path / "gs.db")
    cfg.database.mongo_uri = None
    sim = ModemSimulator(beacon_interval=0.1)
    await sim.start()
    ser = SimulatedSerial(sim)
    station = GroundStation(cfg, open_connection=ser.open)
    await station.start()
    await _wait_until(lambda: station.serial.connected)
    yield station, sim, ser
    await station.stop()
    await sim.stop()


async def test_beacon_then_ping_end_to_end(gs):
    station, sim, _ser = gs
    decoded, gaps = [], []
    station.bus.subscribe(PacketDecoded, lambda e: _push(decoded, e))
    station.bus.subscribe(SequenceGap, lambda e: _push(gaps, e))

    # 1. initial mode was applied to the modem on connect
    assert sim.freq == 435.5 and station.freq.mode is Mode.TCTM

    # 2. listen for beacons
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    assert sim.freq == 437.25
    await _wait_until(lambda: len(decoded) >= 2)
    assert decoded[0].decoded.apid_name == "Beacon"
    assert decoded[0].decoded.as_dict()["message"] == "VLEO_BEACON_SYS_NOMINAL"
    assert station.decoder.last_values[10].as_dict()["message"] == "VLEO_BEACON_SYS_NOMINAL"

    # 3. back to TCTM and ping
    await station.freq.set_mode(Mode.TCTM)
    rec = await station.telecommand.send_command("PING")
    assert rec.status == "responded" and rec.latency_ms is not None
    await _wait_until(lambda: any(e.decoded.apid == 101 for e in decoded))
    pong = next(e for e in decoded if e.decoded.apid == 101)
    assert pong.decoded.as_dict()["response_data"] == "PONG_DATA_6.28"
    assert gaps == []  # global counter, no gaps

    # 4. everything persisted
    await asyncio.sleep(0.1)
    raw = await station.storage.query("raw_packets", limit=100)
    rx = [r for r in raw if r["direction"] == "rx"]
    tx = [r for r in raw if r["direction"] == "tx"]
    assert len(rx) >= 3 and len(tx) == 1 and tx[0]["apid"] == 100
    assert any(r["apid"] == 101 for r in rx)
    dec = await station.storage.query("decoded_telemetry", apid=101)
    assert dec[0]["field_value"] == "PONG_DATA_6.28" and dec[0]["packet_id"] is not None
    cmds = await station.storage.query("commands")
    assert cmds[0]["command_name"] == "PING" and cmds[0]["status"] == "responded"
    assert station.storage.session["packets_sent"] == 1
    assert station.storage.session["packets_received"] == len(rx)

    st = station.status()
    assert st["serial"]["connected"] is True and st["frequency"]["mode"] == "tctm"
    assert st["storage"]["mongo"] == "disabled"


async def _push(lst, e):
    lst.append(e)


async def test_survives_modem_unplug(gs):
    station, sim, ser = gs
    ser.close_from_modem_side()
    await _wait_until(lambda: not station.serial.connected)
    await _wait_until(lambda: station.serial.connected)
    await station.freq.set_mode(Mode.BEACON_LISTEN)  # modem answers on the new link
    assert sim.freq == 437.25
