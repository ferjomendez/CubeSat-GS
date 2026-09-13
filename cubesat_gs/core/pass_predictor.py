"""Satellite pass prediction with skyfield (SGP4). CPU work runs in a worker thread."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from skyfield.api import EarthSatellite, load, wgs84

from cubesat_gs.core.config import PassConfig, SatelliteConfig, StationConfig
from cubesat_gs.core.events import EventBus, now

log = logging.getLogger(__name__)

C_KM_S = 299_792.458
_CACHE_TTL = timedelta(hours=1)


class TLEError(ValueError):
    """TLE lines could not be parsed."""


@dataclass(frozen=True)
class Pass:
    id: str
    aos: datetime
    los: datetime
    tca: datetime
    max_el: float
    aos_az: float
    los_az: float
    duration_s: float


@dataclass(frozen=True)
class PassState:
    pass_id: str
    t: datetime
    az: float
    el: float
    range_km: float
    doppler_hz: float
    progress: float


def _pass_id(aos: datetime) -> str:
    return hashlib.sha1(aos.replace(microsecond=0).isoformat().encode()).hexdigest()[:8]


class PassPredictor:
    def __init__(self, bus: EventBus, station_cfg: StationConfig, satellite_cfg: SatelliteConfig,
                 passes_cfg: PassConfig, *, tctm_mhz: float,
                 clock: Callable[[], datetime] = now) -> None:
        self._bus = bus
        self._clock = clock
        self._ts = load.timescale(builtin=True)
        self._lat, self._lon, self._alt = station_cfg.latitude, station_cfg.longitude, station_cfg.altitude
        self._min_el = float(passes_cfg.min_elevation)
        self._days = int(passes_cfg.prediction_days)
        self._tctm_mhz = tctm_mhz
        self._name = satellite_cfg.name or "SAT"
        self._sat: EarthSatellite | None = None
        self.tle: tuple[str, str] | None = None
        self.reason: str | None = None
        self._cache: list[Pass] = []
        self._cache_at: datetime | None = None
        self._cache_days = 0
        self._cache_gen = 0
        self._lock = asyncio.Lock()
        self._observer = wgs84.latlon(self._lat, self._lon, elevation_m=self._alt)
        self._load_tle(satellite_cfg.tle_line1, satellite_cfg.tle_line2)

    # ---- configuration
    @property
    def enabled(self) -> bool:
        return self._sat is not None

    def _load_tle(self, l1: str, l2: str) -> None:
        l1, l2 = (l1 or "").strip(), (l2 or "").strip()
        if not l1 or not l2:
            self._sat, self.tle, self.reason = None, None, "TLE not configured"
            return
        try:
            sat = EarthSatellite(l1, l2, self._name, self._ts)
            if sat.model.error != 0:
                raise ValueError(sat.model.error_message)
            # a propagation sanity check catches structurally valid but garbage lines
            sat.at(self._ts.from_datetime(self._clock())).position.km
        except Exception as e:  # noqa: BLE001 - any parse/propagation failure
            self._sat, self.tle, self.reason = None, None, f"invalid TLE: {e}"
            return
        self._sat, self.tle, self.reason = sat, (l1, l2), None
        self._invalidate()

    def _invalidate(self) -> None:
        self._cache, self._cache_at = [], None
        self._cache_gen += 1

    async def set_tle(self, line1: str, line2: str) -> None:
        prev = (self._sat, self.tle, self.reason)
        await asyncio.to_thread(self._load_tle, line1, line2)
        if self._sat is None:
            reason = self.reason
            self._sat, self.tle, self.reason = prev  # a bad new TLE never discards a working one
            raise TLEError(reason or "invalid TLE")

    async def set_location(self, lat: float, lon: float, alt_m: float) -> None:
        self._lat, self._lon, self._alt = float(lat), float(lon), float(alt_m)
        self._observer = wgs84.latlon(self._lat, self._lon, elevation_m=self._alt)
        self._invalidate()

    async def set_min_elevation(self, deg: float) -> None:
        self._min_el = float(deg)
        self._invalidate()

    # ---- geometry (sync, single point)
    def state_at(self, t: datetime) -> tuple[float, float, float, float]:
        """(az_deg, el_deg, range_km, range_rate_km_s) at t. Requires enabled."""
        assert self._sat is not None
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        tt = self._ts.from_datetime(t.astimezone(timezone.utc))
        topo = (self._sat - self._observer).at(tt)
        alt, az, dist, _, _, rr = topo.frame_latlon_and_rates(self._observer)
        return az.degrees % 360.0, alt.degrees, dist.km, rr.km_per_s

    def doppler_hz(self, freq_mhz: float, t: datetime | None = None) -> float:
        if not self.enabled:
            return 0.0
        _, _, _, rr = self.state_at(t or self._clock())
        return -rr / C_KM_S * freq_mhz * 1e6

    def is_visible(self) -> bool:
        if not self.enabled:
            return False
        return self.state_at(self._clock())[1] >= self._min_el

    def next_pass(self) -> Pass | None:
        t = self._clock()
        for p in self._cache:
            if p.aos > t:
                return p
        return None

    def current(self) -> PassState | None:
        if not self.enabled:
            return None
        t = self._clock()
        for p in self._cache:
            if p.aos <= t <= p.los:
                az, el, rng, rr = self.state_at(t)
                return PassState(pass_id=p.id, t=t, az=az, el=el, range_km=rng,
                                 doppler_hz=-rr / C_KM_S * self._tctm_mhz * 1e6,
                                 progress=(t - p.aos).total_seconds() / max(p.duration_s, 1.0))
        return None

    # ---- search (thread)
    def _search(self, start: datetime, days: int) -> list[Pass]:
        assert self._sat is not None
        t0 = self._ts.from_datetime(start)
        t1 = self._ts.from_datetime(start + timedelta(days=days))
        times, events = self._sat.find_events(self._observer, t0, t1, altitude_degrees=self._min_el)
        out: list[Pass] = []
        aos = tca = None
        max_el = 0.0
        for ti, ev in zip(times, events):
            if ev == 0:
                aos, tca, max_el = ti.utc_datetime(), None, 0.0
            elif ev == 1 and aos is not None:
                tca = ti.utc_datetime()
                max_el = self.state_at(tca)[1]
            elif ev == 2 and aos is not None:
                los = ti.utc_datetime()
                if tca is None:
                    tca = aos + (los - aos) / 2
                    max_el = self.state_at(tca)[1]
                out.append(Pass(id=_pass_id(aos), aos=aos, los=los, tca=tca, max_el=max_el,
                                aos_az=self.state_at(aos)[0], los_az=self.state_at(los)[0],
                                duration_s=(los - aos).total_seconds()))
                aos = None
        return out

    async def upcoming(self, days: int | None = None, *, force: bool = False) -> list[Pass]:
        if not self.enabled:
            return []
        days = days or self._days
        t = self._clock()
        async with self._lock:
            fresh = (self._cache_at is not None and t - self._cache_at < _CACHE_TTL
                     and self._cache_days == days)
            if fresh and not force:
                return self._cache
            start = t - timedelta(minutes=15)  # include a pass already in progress
            gen = self._cache_gen
            passes = await asyncio.to_thread(self._search, start, days)
            if gen == self._cache_gen:
                self._cache, self._cache_at, self._cache_days = passes, t, days
            log.info("passes: %d passes in next %d day(s) above %.0f°", len(passes), days, self._min_el)
            return passes

    async def track(self, pass_id: str, step_s: int = 10) -> list[tuple[datetime, float, float, float, float]]:
        p = next((x for x in self._cache if x.id == pass_id), None)
        if p is None or not self.enabled:
            return []

        def _compute() -> list[tuple[datetime, float, float, float, float]]:
            pts = []
            t = p.aos
            while t < p.los:
                az, el, rng, rr = self.state_at(t)
                pts.append((t, az, el, rng, -rr / C_KM_S * self._tctm_mhz * 1e6))
                t += timedelta(seconds=step_s)
            az, el, rng, rr = self.state_at(p.los)
            pts.append((p.los, az, el, rng, -rr / C_KM_S * self._tctm_mhz * 1e6))
            return pts

        return await asyncio.to_thread(_compute)
