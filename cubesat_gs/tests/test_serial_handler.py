import asyncio

import pytest

from cubesat_gs.core.config import SerialConfig, SerialTimeouts
from cubesat_gs.core.events import (ConnectionChanged, EventBus, ModemAck, PacketReceived,
                                    PacketSent, SerialError)
from cubesat_gs.core.serial_handler import (SerialCommandTimeout, SerialDisconnected, SerialHandler,
                                            parse_rx_line)
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial


def _cfg():
    return SerialConfig(port="sim://", reconnect_interval=0.05, timeouts=SerialTimeouts(tx=0.2, freq=0.2))


class Collector:
    def __init__(self, bus, *types):
        self.events = []
        for t in types:
            bus.subscribe(t, self._on)

    async def _on(self, ev):
        self.events.append(ev)

    def of(self, t):
        return [e for e in self.events if isinstance(e, t)]

    async def wait(self, t, n=1, timeout=1.0):
        async def _w():
            while len(self.of(t)) < n:
                await asyncio.sleep(0.005)
        await asyncio.wait_for(_w(), timeout)


@pytest.fixture
async def stack():
    bus = EventBus()
    sim = ModemSimulator(beacon_interval=1000)
    ser = SimulatedSerial(sim)
    h = SerialHandler(bus, _cfg(), get_freq=lambda: 435.5, open_connection=ser.open)
    col = Collector(bus, ConnectionChanged, SerialError, PacketReceived, PacketSent, ModemAck)
    await h.start()
    await col.wait(ConnectionChanged)
    yield bus, sim, ser, h, col
    await h.stop()


# ---- pure parser

def test_parse_rx_line_variants():
    assert parse_rx_line("RX:000AC00000036162") == (bytes.fromhex("000AC00000036162"), None, None)
    assert parse_rx_line("RX:000ac00000036162") == (bytes.fromhex("000AC00000036162"), None, None)
    raw, rssi, snr = parse_rx_line("RX:0A|RSSI:-97.5|SNR:8.25")
    assert (raw, rssi, snr) == (b"\x0a", -97.5, 8.25)
    raw, rssi, snr = parse_rx_line("RX:0A|SNR:bad|FOO:1")
    assert (raw, rssi, snr) == (b"\x0a", None, None)
    with pytest.raises(ValueError):
        parse_rx_line("RX:0G")


# ---- handler

async def test_connects_and_publishes(stack):
    bus, sim, ser, h, col = stack
    assert h.connected is True
    assert col.of(ConnectionChanged)[0].connected is True


async def test_rx_packet_event_with_and_without_rssi(stack):
    bus, sim, ser, h, col = stack
    sim.inject_rx(b"\x00\x0a\xc0\x00\x00\x03ab")
    sim.inject_rx(b"\x00\x0a\xc0\x00\x00\x03cd", rssi=-100.0, snr=5.5)
    await col.wait(PacketReceived, 2)
    p1, p2 = col.of(PacketReceived)
    assert p1.raw.endswith(b"ab") and p1.rssi is None and p1.freq_mhz == 435.5
    assert p2.raw.endswith(b"cd") and p2.rssi == -100.0 and p2.snr == 5.5


async def test_bad_hex_line_publishes_error(stack):
    bus, sim, ser, h, col = stack
    sim._out.put_nowait("RX:ZZ")
    await col.wait(SerialError)
    assert "hex" in col.of(SerialError)[0].message.lower()


async def test_send_tx_waits_for_ack_and_publishes_sent(stack):
    bus, sim, ser, h, col = stack
    await h.send_tx(b"\x10\x64\xc0\x00\x00\x05PING")
    assert sim.received_tx == [b"\x10\x64\xc0\x00\x00\x05PING"]
    assert col.of(PacketSent)[0].raw == b"\x10\x64\xc0\x00\x00\x05PING"
    assert col.of(ModemAck)[0].kind == "TX_DONE"


async def test_set_frequency(stack):
    bus, sim, ser, h, col = stack
    await h.set_frequency(437.25)
    assert sim.freq == 437.25
    assert col.of(ModemAck)[-1].kind == "FREQ_SET"


async def test_timeout_when_modem_silent(stack):
    bus, sim, ser, h, col = stack
    sim.silent = True
    with pytest.raises(SerialCommandTimeout):
        await h.set_frequency(437.25)
    sim.silent = False
    await h.set_frequency(435.5)  # queue keeps working afterwards


async def test_only_one_outstanding_command(stack):
    bus, sim, ser, h, col = stack
    sim.silent = True
    t1 = asyncio.create_task(h.send_tx(b"\x01"))
    t2 = asyncio.create_task(h.send_tx(b"\x02"))
    await asyncio.sleep(0.05)
    assert sim.received_tx == [b"\x01"]  # second not written until first resolves
    await asyncio.sleep(0.3)
    assert sim.received_tx == [b"\x01", b"\x02"]
    with pytest.raises(SerialCommandTimeout):
        await t1
    with pytest.raises(SerialCommandTimeout):
        await t2


async def test_reconnect_after_eof(stack):
    bus, sim, ser, h, col = stack
    sim.silent = True
    pending = asyncio.create_task(h.send_tx(b"\x01"))
    await asyncio.sleep(0.02)
    ser.close_from_modem_side()
    await col.wait(ConnectionChanged, 3)  # True, False, True
    flags = [e.connected for e in col.of(ConnectionChanged)]
    assert flags == [True, False, True]
    assert ser.open_count == 2
    with pytest.raises(SerialDisconnected):
        await pending
    sim.silent = False
    await h.set_frequency(437.25)  # works on the new connection


async def test_open_failure_retries():
    bus = EventBus()
    sim = ModemSimulator(beacon_interval=1000)
    ser = SimulatedSerial(sim)
    ser.fail_next_open = True
    h = SerialHandler(bus, _cfg(), get_freq=lambda: 435.5, open_connection=ser.open)
    col = Collector(bus, ConnectionChanged)
    await h.start()
    await col.wait(ConnectionChanged, 2)
    assert [e.connected for e in col.of(ConnectionChanged)] == [False, True]
    await h.stop()
