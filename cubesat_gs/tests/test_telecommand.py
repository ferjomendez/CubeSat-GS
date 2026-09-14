import asyncio
import time
from pathlib import Path

import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CommandConfig
from cubesat_gs.core.events import CommandCompleted, EventBus, PacketReceived
from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.serial_handler import SerialCommandTimeout
from cubesat_gs.core.telecommand import (CommandBusyError, TelecommandManager, UnknownCommandError,
                                         WrongModeError, load_commands)

REGISTRY = Path(__file__).resolve().parents[1] / "config" / "commands.yaml"

CRIT_YAML = """
commands:
  - {name: PING, apid: 100, payload: "PING", response_apid: 101, timeout: 0.1}
  - {name: REBOOT, apid: 100, payload: "0x01FF", response_apid: null, critical: true}
"""


class FakeSerial:
    """Records TX and optionally replies on the bus like the satellite would."""

    def __init__(self, bus, reply=True, fail=False):
        self.bus, self.reply, self.fail = bus, reply, fail
        self.sent = []

    async def send_tx(self, raw):
        self.sent.append(raw)
        if self.fail:
            raise SerialCommandTimeout("TX")
        if self.reply:
            pong = ccsds.build(101, b"PONG_DATA_6.28", sequence_count=0, packet_type=0)
            asyncio.get_running_loop().call_later(
                0.01, self.bus.publish, PacketReceived(raw=pong, rssi=None, snr=None, freq_mhz=435.5))


class FakeFreq:
    mode = Mode.TCTM


def _mgr(tmp_path, bus=None, serial=None, yaml_text=None, **cfg):
    bus = bus or EventBus()
    serial = serial or FakeSerial(bus)
    path = REGISTRY
    if yaml_text:
        path = tmp_path / "cmds.yaml"
        path.write_text(yaml_text, encoding="utf-8")
    conf = CommandConfig(max_retries=cfg.pop("max_retries", 1),
                         retry_backoff=cfg.pop("retry_backoff", 0.01), **cfg)
    return bus, serial, TelecommandManager(bus, serial, FakeFreq(), ccsds.PacketBuilder(), conf, path)


def test_load_shipped_registry():
    cmds = load_commands(REGISTRY, default_timeout=10)
    assert cmds["PING"].apid == 100 and cmds["PING"].payload == b"PING"
    assert cmds["PING"].response_apid == 101 and cmds["PING"].critical is False


def test_load_hex_payload_and_defaults(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text(CRIT_YAML, encoding="utf-8")
    cmds = load_commands(p, default_timeout=7)
    assert cmds["REBOOT"].payload == b"\x01\xff" and cmds["REBOOT"].timeout == 7
    assert cmds["REBOOT"].critical is True and cmds["REBOOT"].response_apid is None


async def test_ping_happy_path(tmp_path):
    bus, ser, m = _mgr(tmp_path)
    done = []
    bus.subscribe(CommandCompleted, lambda e: _push(done, e))
    rec = await m.send_command("PING")
    assert rec.status == "responded" and rec.attempts == 1
    assert rec.response_hex.upper().startswith("0065")
    assert rec.latency_ms is not None and rec.latency_ms >= 0
    assert ser.sent[0].hex().upper() == "1064C000000550494E47"
    assert m.pending is None and m.history[-1] is rec
    await asyncio.sleep(0.01)
    assert done and done[0].record is rec


async def _push(lst, e):
    lst.append(e)


async def test_timeout_then_retry_then_success(tmp_path):
    bus = EventBus()
    ser = FakeSerial(bus, reply=False)
    bus, ser, m = _mgr(tmp_path, bus=bus, serial=ser, yaml_text=CRIT_YAML, max_retries=2)

    async def flip():
        await asyncio.sleep(0.05)  # before attempt 2 is sent (attempt 1 times out at 0.1s)
        ser.reply = True

    asyncio.create_task(flip())
    rec = await m.send_command("PING")
    assert rec.status == "responded" and rec.attempts == 2
    assert len(ser.sent) == 2


BACKOFF_YAML = """
commands:
  - {name: PING, apid: 100, payload: "PING", response_apid: 101, timeout: 0.05}
"""


async def test_retry_backoff_delays(tmp_path):
    """F9: the retry backoff sleep (retry_backoff ** attempt) must actually elapse."""
    bus = EventBus()
    ser = FakeSerial(bus, reply=False)  # never replies: every attempt times out
    bus, ser, m = _mgr(tmp_path, bus=bus, serial=ser, yaml_text=BACKOFF_YAML,
                      max_retries=2, retry_backoff=0.05)
    t0 = time.monotonic()
    rec = await m.send_command("PING")
    elapsed = time.monotonic() - t0
    assert rec.status == "timeout" and rec.attempts == 3
    min_expected = 0.05 * 3 + 0.05 + 0.0025  # three timeouts + delays 0.05**1, 0.05**2
    assert min_expected <= elapsed < 1.0


async def test_timeout_exhausted(tmp_path):
    bus = EventBus()
    ser = FakeSerial(bus, reply=False)
    bus, ser, m = _mgr(tmp_path, bus=bus, serial=ser, yaml_text=CRIT_YAML, max_retries=1)
    rec = await m.send_command("PING")
    assert rec.status == "timeout" and rec.attempts == 2 and rec.response_hex is None


async def test_serial_failure(tmp_path):
    bus = EventBus()
    ser = FakeSerial(bus, fail=True)
    bus, ser, m = _mgr(tmp_path, bus=bus, serial=ser, yaml_text=CRIT_YAML)
    rec = await m.send_command("PING")
    assert rec.status == "failed" and "TX" in rec.error


async def test_critical_requires_confirm_and_fire_and_forget(tmp_path):
    bus, ser, m = _mgr(tmp_path, yaml_text=CRIT_YAML)
    rec = await m.send_command("REBOOT")
    assert rec.status == "refused" and ser.sent == []
    rec = await m.send_command("REBOOT", confirm=True)
    assert rec.status == "acked" and ser.sent[0][6:] == b"\x01\xff"


async def test_busy_wrong_mode_unknown(tmp_path):
    bus = EventBus()
    ser = FakeSerial(bus, reply=False)
    bus, ser, m = _mgr(tmp_path, bus=bus, serial=ser, yaml_text=CRIT_YAML, max_retries=0)
    t = asyncio.create_task(m.send_command("PING"))
    await asyncio.sleep(0.01)
    with pytest.raises(CommandBusyError):
        await m.send_command("PING")
    await t
    m._freq.mode = Mode.BEACON_LISTEN
    with pytest.raises(WrongModeError):
        await m.send_command("PING")
    m._freq.mode = Mode.TCTM
    with pytest.raises(UnknownCommandError):
        await m.send_command("NOPE")


async def test_send_raw_and_payload_override(tmp_path):
    bus, ser, m = _mgr(tmp_path, yaml_text=CRIT_YAML)
    rec = await m.send_raw("DEADBEEF", confirm=True)
    assert rec.name == "RAW" and rec.status == "acked" and ser.sent[-1] == b"\xde\xad\xbe\xef"
    with pytest.raises(ValueError):
        await m.send_raw("XYZ", confirm=True)
    rec = await m.send_command("PING", payload_override=b"PING2")
    assert ser.sent[-1][6:] == b"PING2" and rec.status == "responded"
