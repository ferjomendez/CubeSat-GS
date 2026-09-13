import asyncio
import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial


async def test_freq_ack_and_state():
    sim = ModemSimulator(beacon_interval=1000)
    await sim.handle_line("FREQ:437.25")
    assert await sim.read_line() == "OK:FREQ_SET"
    assert sim.freq == 437.25


async def test_tx_ack_records_and_ping_replies_on_tctm():
    sim = ModemSimulator(beacon_interval=1000)
    ping = ccsds.build(100, b"PING", sequence_count=0)
    await sim.handle_line("TX:" + ping.hex())
    assert await sim.read_line() == "OK:TX_DONE"
    assert sim.received_tx == [ping]
    line = await asyncio.wait_for(sim.read_line(), 1.0)
    assert line.startswith("RX:")
    pkt = ccsds.parse(bytes.fromhex(line[3:]))
    assert pkt.apid == 101 and pkt.payload == b"PONG_DATA_6.28"
    assert line[3:] == line[3:].upper()  # ESP32 prints uppercase hex


async def test_no_ping_reply_on_beacon_freq():
    sim = ModemSimulator(beacon_interval=1000)
    await sim.handle_line("FREQ:437.25")
    await sim.read_line()
    await sim.handle_line("TX:" + ccsds.build(100, b"PING", sequence_count=0).hex())
    assert await sim.read_line() == "OK:TX_DONE"
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sim.read_line(), 0.2)


async def test_beacon_only_on_beacon_freq_and_global_seq():
    sim = ModemSimulator(beacon_interval=0.05)
    await sim.start()
    try:
        await asyncio.sleep(0.12)  # on 435.5: nothing
        assert sim.beacons_sent == 0
        await sim.handle_line("FREQ:437.25")
        assert await sim.read_line() == "OK:FREQ_SET"
        l1 = await asyncio.wait_for(sim.read_line(), 1.0)
        l2 = await asyncio.wait_for(sim.read_line(), 1.0)
        p1, p2 = (ccsds.parse(bytes.fromhex(l[3:])) for l in (l1, l2))
        assert p1.apid == 10 and p1.payload == b"VLEO_BEACON_SYS_NOMINAL"
        assert p2.sequence_count == p1.sequence_count + 1
    finally:
        await sim.stop()


async def test_fake_rssi_suffix_and_inject():
    sim = ModemSimulator(beacon_interval=1000, fake_rssi=True)
    sim.inject_rx(b"\x00\x0a\xc0\x00\x00\x03ab")
    line = await sim.read_line()
    assert line == "RX:000AC00000036162|RSSI:-97.5|SNR:8.25"


async def test_simulated_serial_streams():
    sim = ModemSimulator(beacon_interval=1000)
    ser = SimulatedSerial(sim)
    reader, writer = await ser.open("sim://", 115200)
    writer.write(b"FREQ:437.25\n")
    await writer.drain()
    assert (await reader.readline()) == b"OK:FREQ_SET\n"
    ser.close_from_modem_side()
    assert (await reader.readline()) == b""  # EOF
