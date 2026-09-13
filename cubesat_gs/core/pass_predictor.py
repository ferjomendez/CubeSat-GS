"""Satellite pass prediction with skyfield (SGP4). CPU work runs in a worker thread."""
from __future__ import annotations

import asyncio
import hashlib
import httpx
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from skyfield.api import EarthSatellite, load, wgs84

from cubesat_gs.core.config import PassConfig, SatelliteConfig, StationConfig
from cubesat_gs.core.events import EventBus, PassEnded, PassStarted, PassUpdate, now

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


def pass_to_dict(p: Pass | None) -> dict | None:
    """Convert a Pass to a dict with datetime fields as ISO strings."""
    if p is None:
        return None
    d = asdict(p)
    for k in ("aos", "los", "tca"):
        d[k] = d[k].isoformat()
    return d


def state_to_dict(s: PassState | None) -> dict | None:
    """Convert a PassState to a dict with datetime field as ISO string."""
    if s is None:
        return None
    d = asdict(s)
    d["t"] = d["t"].isoformat()
    return d


def parse_tle_text(text: str, name: str | None) -> tuple[str, str]:
    """Pick (line1, line2) for `name` (case-insensitive substring) from a 2/3-line TLE file, else the first."""
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    entries: list[tuple[str, str, str]] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("1 ") and i + 1 < len(lines) and lines[i + 1].startswith("2 "):
            title = lines[i - 1] if i > 0 and not lines[i - 1].startswith(("1 ", "2 ")) else ""
            entries.append((title, lines[i], lines[i + 1]))
            i += 2
        else:
            i += 1
    if not entries:
        raise TLEError("no TLE entries found")
    if name:
        key = name.strip().lower()
        for title, l1, l2 in entries:
            if key in title.lower():
                return l1, l2
    return entries[0][1], entries[0][2]


class PassPredictor:
    def __init__(self, bus: EventBus, station_cfg: StationConfig, satellite_cfg: SatelliteConfig,
                 passes_cfg: PassConfig, *, tctm_mhz: float,
                 clock: Callable[[], datetime] = now,
                 counters: Callable[[], dict] | None = None,
                 update_interval: float = 1.0,
                 http_client_factory: Callable[[], httpx.AsyncClient] | None = None) -> None:
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
        self._counters = counters or (lambda: {"packets_received": 0})
        self._update_interval = update_interval
        self._http_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=10.0))
        self._tle_source = satellite_cfg.tle_source or ""
        self._task: asyncio.Task | None = None
        self._active: Pass | None = None
        self._last_recompute: datetime | None = None
        self._last_tle_refresh_day: date | None = None
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

    # ---- scheduler
    async def start(self) -> None:
        """Start the pass scheduler task."""
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="pass-scheduler")
            await asyncio.sleep(0)  # yield control to let the task start

    async def stop(self) -> None:
        """Stop the pass scheduler task."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def refresh_tle(self, client: httpx.AsyncClient | None = None) -> tuple[str, str]:
        """Fetch and parse TLE from tle_source URL. Raises TLEError on failure."""
        if not self._tle_source:
            raise TLEError("satellite.tle_source is not set")
        own = client is None
        client = client or self._http_factory()
        try:
            r = await client.get(self._tle_source)
            r.raise_for_status()
            l1, l2 = parse_tle_text(r.text, self._name)
        except (httpx.HTTPError, TLEError) as e:
            raise TLEError(f"TLE fetch failed: {e}") from e
        finally:
            if own:
                await client.aclose()
        await self.set_tle(l1, l2)
        log.info("passes: TLE refreshed from %s", self._tle_source)
        return l1, l2

    async def _loop(self) -> None:
        """Main scheduler loop: runs _tick() repeatedly, handles exceptions."""
        while True:
            try:
                await self._tick()
            except Exception:  # noqa: BLE001 - the scheduler must survive anything
                log.exception("passes: scheduler tick failed")
            await asyncio.sleep(self._update_interval)

    async def _tick(self) -> None:
        """One scheduler tick: check TLE refresh, recompute passes, emit events."""
        if not self.enabled:
            return
        t = self._clock()
        if self._tle_source and t.hour == 3 and self._last_tle_refresh_day != t.date():
            self._last_tle_refresh_day = t.date()
            try:
                await self.refresh_tle()
            except TLEError as e:
                log.warning("passes: %s (keeping previous TLE)", e)
        if self._last_recompute is None or t - self._last_recompute >= _CACHE_TTL:
            await self.upcoming(force=True)
            self._last_recompute = t
        state = self.current()
        if state is not None and self._active is None:
            self._active = next(p for p in self._cache if p.id == state.pass_id)
            self._bus.publish(PassStarted(pass_=self._active))
        if state is not None:
            self._bus.publish(PassUpdate(state=state))
        if state is None and self._active is not None:
            ended, self._active = self._active, None
            self._bus.publish(PassEnded(pass_=ended, packets_received=int(self._counters().get("packets_received", 0))))
        await self._bus.drain()
