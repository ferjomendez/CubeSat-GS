import asyncio
import threading
from datetime import datetime, timedelta, timezone

import pytest

from cubesat_gs.core.config import PassConfig, SatelliteConfig, StationConfig
from cubesat_gs.core.events import EventBus
from cubesat_gs.core.pass_predictor import PassPredictor, TLEError

L1 = "1 25544U 98067A   24007.51787037  .00017371  00000+0  31288-3 0  9994"
L2 = "2 25544  51.6412 203.6489 0004735  97.8797 262.2814 15.49897836434892"
NOW = datetime(2024, 1, 7, 12, 0, tzinfo=timezone.utc)
FIRST_AOS = datetime(2024, 1, 8, 0, 8, 54, tzinfo=timezone.utc)
FIRST_LOS = datetime(2024, 1, 8, 0, 14, 12, tzinfo=timezone.utc)


def _pp(tle=(L1, L2), t=NOW):
    clock = {"t": t}
    pp = PassPredictor(EventBus(), StationConfig(latitude=-33.35, longitude=-70.67, altitude=500),
                       SatelliteConfig(name="ISS", tle_line1=tle[0], tle_line2=tle[1]),
                       PassConfig(min_elevation=10, prediction_days=1), tctm_mhz=435.5,
                       clock=lambda: clock["t"])
    return pp, clock


def test_disabled_without_tle():
    pp, _ = _pp(tle=("", ""))
    assert pp.enabled is False and "TLE" in pp.reason
    assert pp.current() is None and pp.is_visible() is False and pp.next_pass() is None


async def test_bad_tle_reports_reason_and_raises_on_set():
    pp, _ = _pp(tle=("garbage", "lines"))
    assert pp.enabled is False and pp.reason
    with pytest.raises(TLEError):
        await pp.set_tle("1 bad", "2 bad")
    assert pp.enabled is False
    good, _ = _pp()
    with pytest.raises(TLEError):
        await good.set_tle("1 bad", "2 bad")
    assert good.enabled and good.tle == (L1, L2)  # previous TLE kept


async def test_upcoming_matches_pinned_values():
    pp, _ = _pp()
    assert pp.enabled
    passes = await pp.upcoming()
    assert len(passes) == 4
    p = passes[0]
    assert abs((p.aos - FIRST_AOS).total_seconds()) < 2
    assert abs((p.los - FIRST_LOS).total_seconds()) < 2
    assert p.max_el == pytest.approx(21.3, abs=0.2)
    assert passes[2].max_el == pytest.approx(44.8, abs=0.2)
    assert p.duration_s == pytest.approx((p.los - p.aos).total_seconds())
    assert 0 <= p.aos_az < 360 and 0 <= p.los_az < 360
    assert p.aos < p.tca < p.los
    assert len(p.id) == 8 and p.id == passes[0].id  # stable id
    assert pp.next_pass().id == p.id


async def test_current_progress_and_visibility(monkeypatch):
    pp, clock = _pp()
    passes = await pp.upcoming()
    p = passes[0]
    clock["t"] = p.tca
    st = pp.current()
    assert st is not None and st.pass_id == p.id
    assert st.el == pytest.approx(p.max_el, abs=0.3)
    assert 0.4 < st.progress < 0.6 and st.range_km > 400
    assert pp.is_visible()
    clock["t"] = p.los + timedelta(minutes=1)
    assert pp.current() is None and not pp.is_visible()


async def test_doppler_sign_flips_through_tca():
    pp, clock = _pp()
    p = (await pp.upcoming())[0]
    before = pp.doppler_hz(435.5, p.tca - timedelta(seconds=60))
    after = pp.doppler_hz(435.5, p.tca + timedelta(seconds=60))
    assert before == pytest.approx(4008, abs=30)
    assert after == pytest.approx(-4124, abs=30)


async def test_track_shape():
    pp, _ = _pp()
    p = (await pp.upcoming())[0]
    pts = await pp.track(p.id, step_s=30)
    assert 9 <= len(pts) <= 13  # ~318 s / 30 s + endpoints
    t, az, el, rng, dop = pts[0]
    assert abs((t - p.aos).total_seconds()) < 1 and el == pytest.approx(10.0, abs=0.5)
    assert max(pt[2] for pt in pts) == pytest.approx(p.max_el, abs=1.0)
    assert await pp.track("nope") == []


async def test_cache_and_invalidation():
    pp, _ = _pp()
    a = await pp.upcoming()
    b = await pp.upcoming()
    assert a is b
    await pp.set_min_elevation(40)
    c = await pp.upcoming()
    assert len(c) == 1 and c[0].max_el == pytest.approx(44.8, abs=0.2)
    await pp.set_location(0.0, 0.0, 0.0)
    assert (await pp.upcoming()) is not c


def test_state_at_with_naive_datetime():
    pp, _ = _pp()
    # Test that naive datetime (no tzinfo) is treated as UTC
    naive = FIRST_AOS.replace(tzinfo=None)
    aware = FIRST_AOS
    az_naive, el_naive, rng_naive, rr_naive = pp.state_at(naive)
    az_aware, el_aware, rng_aware, rr_aware = pp.state_at(aware)
    assert az_naive == pytest.approx(az_aware)
    assert el_naive == pytest.approx(el_aware)
    assert rng_naive == pytest.approx(rng_aware)
    assert rr_naive == pytest.approx(rr_aware)


async def test_cache_race_condition_on_config_change():
    """Verify that stale results are not cached when config changes during search.

    Without the generation counter fix, stale results from an in-flight search
    would overwrite the cache after set_min_elevation() increments the counter,
    causing the cache to become out-of-sync with configuration.
    """
    pp, clock = _pp()

    # Wrap _search to count calls and block on first call until released
    search_call_count = {"count": 0}
    block_event = threading.Event()
    original_search = pp._search

    def search_wrapper(start, days):
        search_call_count["count"] += 1
        # Block on first call until released (threading.Event works in threads)
        if search_call_count["count"] == 1:
            block_event.wait()
        return original_search(start, days)

    pp._search = search_wrapper

    # Start upcoming() as a task (will block in _search)
    task = asyncio.create_task(pp.upcoming())
    await asyncio.sleep(0.02)  # Let it enter _search in thread

    # Invalidate cache while task is blocked
    await pp.set_min_elevation(30)

    # Release the blocked _search call
    block_event.set()

    # Wait for the task to complete
    result1 = await task

    # Verify stale cache was NOT written: _cache_at should still be None
    # (cache was invalidated by set_min_elevation, and the search result
    # should have been discarded due to generation counter)
    assert pp._cache_at is None, "Stale cache was incorrectly written"
    assert search_call_count["count"] == 1

    # Call upcoming again and verify it runs _search again
    result2 = await pp.upcoming()
    assert search_call_count["count"] == 2, "Second upcoming() should trigger _search again"
    assert pp._cache_at is not None, "Cache should be set after second search"


import httpx

from cubesat_gs.core.events import PassEnded, PassStarted, PassUpdate
from cubesat_gs.core.pass_predictor import pass_to_dict, state_to_dict


async def _wait_for(pred, timeout=2.0):
    """Poll a condition with deadline; raise AssertionError if not met in time."""
    deadline = asyncio.get_running_loop().time() + timeout
    while not pred():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.01)


async def test_scheduler_emits_aos_update_los():
    bus = EventBus()
    got = []

    async def on(ev):
        got.append(ev)

    for t in (PassStarted, PassUpdate, PassEnded):
        bus.subscribe(t, on)
    clock = {"t": NOW}
    counters = {"packets_received": 7, "packets_sent": 0, "commands_sent": 0}
    pp = PassPredictor(bus, StationConfig(latitude=-33.35, longitude=-70.67, altitude=500),
                       SatelliteConfig(name="ISS", tle_line1=L1, tle_line2=L2),
                       PassConfig(min_elevation=10, prediction_days=1), tctm_mhz=435.5,
                       clock=lambda: clock["t"], counters=lambda: counters, update_interval=0.02)
    await pp.start()
    p = (await pp.upcoming())[0]
    clock["t"] = p.aos + timedelta(seconds=1)
    await _wait_for(lambda: any(isinstance(e, PassStarted) and e.pass_.id == p.id for e in got))
    await _wait_for(lambda: sum(isinstance(e, PassUpdate) for e in got) >= 2)
    clock["t"] = p.los + timedelta(seconds=1)
    await _wait_for(lambda: any(isinstance(e, PassEnded) for e in got))
    ended = [e for e in got if isinstance(e, PassEnded)]
    assert len(ended) == 1 and ended[0].packets_received == 7
    await pp.stop()


async def test_refresh_tle_picks_named_entry():
    text = ("OTHER SAT\n1 00001U 00000A   24007.50000000  .00000000  00000+0  00000-0 0  9998\n"
            "2 00001  51.0000 200.0000 0001000  90.0000 270.0000 15.50000000000000\n"
            f"ISS (ZARYA)\n{L1}\n{L2}\n")

    def handler(request):
        assert request.url.host == "tle.example"
        return httpx.Response(200, text=text)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    pp, _ = _pp(tle=("", ""))
    pp._tle_source = "https://tle.example/sats.txt"
    l1, l2 = await pp.refresh_tle(client=client)
    assert (l1, l2) == (L1, L2) and pp.enabled
    await client.aclose()


async def test_refresh_tle_failure_keeps_old():
    def handler(request):
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    pp, _ = _pp()
    pp._tle_source = "https://tle.example/sats.txt"
    with pytest.raises(TLEError):
        await pp.refresh_tle(client=client)
    assert pp.tle == (L1, L2)
    await client.aclose()


async def test_to_dict_helpers():
    pp, clock = _pp()
    p = (await pp.upcoming())[0]
    d = pass_to_dict(p)
    assert d["id"] == p.id and d["aos"] == p.aos.isoformat() and d["max_el"] == p.max_el
    clock["t"] = p.tca
    s = state_to_dict(pp.current())
    assert s["pass_id"] == p.id and set(s) == {"pass_id", "t", "az", "el", "range_km", "doppler_hz", "progress"}
    assert state_to_dict(None) is None


async def test_scheduler_recomputes_on_invalidation():
    """Verify cache is recomputed immediately when invalidated, not waiting for hourly timer."""
    bus = EventBus()
    clock = {"t": NOW}
    pp = PassPredictor(bus, StationConfig(latitude=-33.35, longitude=-70.67, altitude=500),
                       SatelliteConfig(name="ISS", tle_line1=L1, tle_line2=L2),
                       PassConfig(min_elevation=10, prediction_days=1), tctm_mhz=435.5,
                       clock=lambda: clock["t"], update_interval=0.02)
    await pp.start()
    # Wait for scheduler to populate cache
    await _wait_for(lambda: pp.next_pass() is not None)
    old_count = len(pp._cache)
    # Change min elevation to 30° (filter out lower passes)
    await pp.set_min_elevation(30)
    # Wait for scheduler to recompute cache (should happen immediately, not wait 1 hour)
    await _wait_for(lambda: len(pp._cache) < old_count)
    await pp.stop()
