import asyncio

import pytest

from cubesat_gs.core.events import EventBus, PacketReceived, SerialError, now


async def test_publish_calls_subscriber():
    bus = EventBus()
    got = []

    async def handler(ev: PacketReceived):
        got.append(ev)

    bus.subscribe(PacketReceived, handler)
    ev = PacketReceived(raw=b"\x00", rssi=None, snr=None, freq_mhz=435.5)
    bus.publish(ev)
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert got == [ev]
    assert ev.ts.tzinfo is not None


async def test_handler_exception_is_isolated():
    bus = EventBus()
    got = []

    async def bad(ev):
        raise RuntimeError("boom")

    async def good(ev):
        got.append(ev)

    bus.subscribe(SerialError, bad)
    bus.subscribe(SerialError, good)
    bus.publish(SerialError(message="x"))
    await asyncio.sleep(0.01)
    assert len(got) == 1


async def test_unsubscribe():
    bus = EventBus()
    got = []

    async def h(ev):
        got.append(ev)

    bus.subscribe(SerialError, h)
    bus.unsubscribe(SerialError, h)
    bus.publish(SerialError(message="x"))
    await asyncio.sleep(0.01)
    assert got == []


async def test_wait_for_with_predicate_and_timeout():
    bus = EventBus()

    async def later():
        await asyncio.sleep(0.01)
        bus.publish(PacketReceived(raw=b"\x01", rssi=None, snr=None, freq_mhz=1.0))
        bus.publish(PacketReceived(raw=b"\x02", rssi=None, snr=None, freq_mhz=1.0))

    asyncio.create_task(later())
    ev = await bus.wait_for(PacketReceived, lambda e: e.raw == b"\x02", timeout=1.0)
    assert ev.raw == b"\x02"

    with pytest.raises(asyncio.TimeoutError):
        await bus.wait_for(SerialError, timeout=0.01)
    # the temporary subscriber must be gone after timeout
    assert bus.subscriber_count(SerialError) == 0


def test_now_is_utc():
    assert now().utcoffset().total_seconds() == 0
