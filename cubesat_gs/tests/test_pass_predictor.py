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
