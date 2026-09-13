import asyncio

import pytest

from cubesat_gs.core.config import FrequencyConfig
from cubesat_gs.core.events import ConnectionChanged, EventBus, FrequencyChanged
from cubesat_gs.core.frequency_manager import FrequencyManager, Mode
from cubesat_gs.core.serial_handler import SerialCommandTimeout


class FakeSerial:
    def __init__(self):
        self.calls = []
        self.fail = False

    async def set_frequency(self, mhz):
        self.calls.append(mhz)
        if self.fail:
            raise SerialCommandTimeout("FREQ")


@pytest.fixture
def fm():
    bus = EventBus()
    ser = FakeSerial()
    m = FrequencyManager(bus, ser, FrequencyConfig())
    m.start()
    return bus, ser, m


def test_initial_state(fm):
    bus, ser, m = fm
    assert m.mode is Mode.TCTM and m.mhz == 435.5


async def test_set_mode_beacon_and_custom(fm):
    bus, ser, m = fm
    got = []
    bus.subscribe(FrequencyChanged, lambda e: _append(got, e))
    await m.set_mode(Mode.BEACON_LISTEN)
    assert ser.calls == [437.25] and m.mode is Mode.BEACON_LISTEN and m.mhz == 437.25
    await m.set_mode(Mode.CUSTOM, mhz=436.0)
    assert m.mhz == 436.0
    await asyncio.sleep(0.01)
    assert [(e.mode, e.mhz) for e in got] == [(Mode.BEACON_LISTEN, 437.25), (Mode.CUSTOM, 436.0)]
    assert len(m.history) == 2


async def _append(lst, e):
    lst.append(e)


async def test_custom_requires_mhz(fm):
    bus, ser, m = fm
    with pytest.raises(ValueError):
        await m.set_mode(Mode.CUSTOM)


async def test_timeout_keeps_previous_state(fm):
    bus, ser, m = fm
    ser.fail = True
    with pytest.raises(SerialCommandTimeout):
        await m.set_mode(Mode.BEACON_LISTEN)
    assert m.mode is Mode.TCTM and m.mhz == 435.5


async def test_reapplies_on_connect(fm):
    bus, ser, m = fm
    await m.set_mode(Mode.BEACON_LISTEN)
    bus.publish(ConnectionChanged(connected=True, port="x"))
    await asyncio.sleep(0.01)
    assert ser.calls == [437.25, 437.25]
    bus.publish(ConnectionChanged(connected=False, port="x"))
    await asyncio.sleep(0.01)
    assert ser.calls == [437.25, 437.25]
