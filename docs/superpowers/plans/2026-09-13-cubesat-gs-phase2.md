# CubeSat GS Phase 2 (Web Backend, Dashboard, Pass Predictor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A FastAPI backend (`cubesat_gs/web/`) exposing REST + one snapshot/delta WebSocket over the Phase 1 ground station, a satellite pass predictor (`core/pass_predictor.py`), and a React/TypeScript mission-control dashboard built into `web/static/` and served by the same process (`python cubesat_gs/main.py --sim`).

**Architecture:** The web layer is one more subscriber of the Phase 1 `EventBus`: `WebSocketHub` turns bus events into typed JSON deltas for every connected browser and keeps a ring buffer for the connect-time snapshot. REST routes call Phase 1 objects (`GroundStation`, `Storage`, `TelecommandManager`, `FrequencyManager`, `PassPredictor`) directly. uvicorn runs inside the existing asyncio loop (no threads). The frontend is a single Zustand store hydrated by the snapshot and mutated by deltas; TanStack Query handles paged history.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, websockets, httpx, ruamel.yaml, skyfield/sgp4, pytest + pytest-asyncio; Node 24, Vite 5, React 18, TypeScript, Tailwind 3, shadcn/ui, Recharts, TanStack Query 5, Zustand, react-router 6, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-13-cubesat-gs-phase2-design.md` (binding). Phase 1 spec: `docs/superpowers/specs/2026-09-13-cubesat-gs-phase1-design.md`.

## Global Constraints

- Python 3.11 as `python`; all commands from the git root; tests via `python -m pytest -q -W error` (must stay pristine). `pytest.ini` sets `asyncio_mode = auto`.
- Single asyncio event loop, no threads (except `asyncio.to_thread` for skyfield CPU work). `EventBus.publish` is fire-and-forget: production code never adds `sleep(0)` hops; tests poll with a deadline.
- Tests are fully offline: no real Mongo, no network (httpx calls are mocked with `httpx.MockTransport`), no hardware (`ModemSimulator` + `SimulatedSerial`).
- Branch `phase2-web` off `main`. Commit messages plain text. **Never add `Co-Authored-By` or "Generated with" trailers.** No secrets in tracked files; `mongo_uri` never appears in any API response.
- Windows Git Bash: quote paths (they contain spaces), forward slashes.
- API: everything under `/api`, errors are `{"error": str, "detail": str | null}`; status mapping `CommandBusyError→409`, `WrongModeError→400`, `UnknownCommandError→404`, `SerialCommandTimeout→504`, `SerialDisconnected→503`, `ValueError→422`, critical-without-confirm→403.
- WS messages: `{"type": str, "ts": iso-8601 UTC, "data": {...}}`; bytes as uppercase hex.
- Config writable sections: `serial`, `frequencies`, `station`, `satellite`, `passes`, and `commands.{default_timeout,max_retries,retry_backoff}`. Read-only: `database`, `logging`, `web`, `ccsds`, `telemetry`.
- Frontend: dark only; four semantic colours (`nominal` green, `warn` amber, `alarm` red, `info` blue); JetBrains Mono (tabular) for numbers/hex/timestamps; condensed grotesk for labels; store caps feed 2000, series 5000/field; built bundle committed to `cubesat_gs/web/static/`.
- Pinned test values (computed with skyfield 1.55): ISS TLE
  `1 25544U 98067A   24007.51787037  .00017371  00000+0  31288-3 0  9994` /
  `2 25544  51.6412 203.6489 0004735  97.8797 262.2814 15.49897836434892`;
  observer −33.35, −70.67, 500 m; `now = 2024-01-07T12:00:00Z`; 24 h, min el 10° → **4 passes**,
  first AOS `2024-01-08T00:08:54Z`, LOS `00:14:12Z`, max el 21.3°; third pass max el 44.8°;
  Doppler at 435.5 MHz: +4008 Hz at TCA−60 s, −4124 Hz at TCA+60 s.

## File Map

| File | Responsibility |
|---|---|
| `cubesat_gs/core/events.py` (modify) | add `PassStarted`, `PassEnded`, `PassUpdate`, `CommandStarted` |
| `cubesat_gs/core/pass_predictor.py` | `Pass`, `PassState`, `PassPredictor` (skyfield), scheduler task |
| `cubesat_gs/storage/sqlite_backend.py`, `mongo_backend.py`, `exporter.py`, `database.py` (modify) | `passes` collection, pass rows, `session.pass_id` |
| `cubesat_gs/core/station.py` (modify) | `.passes`, status includes passes |
| `cubesat_gs/web/schemas.py` | Pydantic models + `ws_message()` helper |
| `cubesat_gs/web/deps.py` | `get_station`, exception→HTTP mapping, `ApiError` |
| `cubesat_gs/web/hub.py` | `WebSocketHub`, `FeedEntry` assembly, ring buffer |
| `cubesat_gs/web/app.py` | `create_app(station)`, lifespan, `/ws`, static SPA |
| `cubesat_gs/web/routes/*.py` | status, feed, telemetry, commands, frequency, passes, config, export |
| `cubesat_gs/web/lttb.py` | largest-triangle-three-buckets downsampling |
| `cubesat_gs/web/config_writer.py` | ruamel round-trip write, validation, live-apply |
| `cubesat_gs/main.py` (modify) | `--no-web`, in-loop uvicorn |
| `cubesat_gs/tests/conftest.py` | `web_stack` fixture: station+sim+app+client |
| `cubesat_gs/tests/test_pass_predictor.py`, `test_storage_passes.py`, `test_web_*.py`, `test_schema_sync.py` | backend tests |
| `cubesat_gs/web/frontend/**` | Vite project (see Task 11) |
| `cubesat_gs/web/static/**` | committed build output |
| `README.md` (modify) | Phase 2 run/dev instructions |

---

### Task 1: Events, `passes` collection, dependencies

**Files:**
- Modify: `cubesat_gs/core/events.py`, `cubesat_gs/storage/sqlite_backend.py`, `cubesat_gs/storage/mongo_backend.py`, `cubesat_gs/storage/exporter.py`, `cubesat_gs/storage/database.py`, `cubesat_gs/requirements.txt`, `.gitignore`
- Test: `cubesat_gs/tests/test_storage_passes.py`

**Interfaces:**
- Produces: events `PassStarted(pass_: Any)`, `PassEnded(pass_: Any, packets_received: int)`, `PassUpdate(state: Any)`, `CommandStarted(name: str, raw_hex: str)`; `COLLECTIONS` includes `"passes"`; `COLUMNS["passes"] = ["id","pass_id","aos","los","max_el","packets_received","packets_sent","commands_sent"]`; `Storage` subscribes to `PassStarted`/`PassEnded`, writes `passes` rows, sets `session["pass_id"]` during a pass and clears it at LOS; `Storage.pass_counters -> dict` (packets received/sent/commands since AOS).

- [ ] **Step 1: Branch and deps**

```bash
git checkout -b phase2-web main
```
Append to `cubesat_gs/requirements.txt`:
```
fastapi>=0.115
uvicorn[standard]>=0.30
websockets>=12
httpx>=0.27
ruamel.yaml>=0.18
skyfield>=1.49
sgp4>=2.23
```
Append to `.gitignore`:
```
cubesat_gs/web/frontend/node_modules/
cubesat_gs/web/frontend/dist/
cubesat_gs/data/exports/
```
Run: `python -m pip install -r cubesat_gs/requirements.txt`

- [ ] **Step 2: Write the failing tests**

`cubesat_gs/tests/test_storage_passes.py`:
```python
import asyncio
from datetime import datetime, timedelta, timezone

from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import (CommandCompleted, EventBus, PacketReceived, PassEnded,
                                    PassStarted, now)
from cubesat_gs.core.telecommand import CommandRecord
from cubesat_gs.storage.database import Storage
from cubesat_gs.storage.exporter import COLUMNS
from cubesat_gs.storage.sqlite_backend import COLLECTIONS

BEACON = bytes.fromhex("000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C")


class FakePass:
    id = "abc12345"
    aos = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    los = aos + timedelta(minutes=6)
    max_el = 42.5


async def test_passes_collection_registered():
    assert "passes" in COLLECTIONS
    assert COLUMNS["passes"] == ["id", "pass_id", "aos", "los", "max_el", "packets_received",
                                 "packets_sent", "commands_sent"]


async def test_pass_rows_and_session_pass_id(tmp_path):
    bus = EventBus()
    st = Storage(bus, DatabaseConfig(local_fallback_path=str(tmp_path / "gs.db")), tmp_path,
                 sync_interval=1000)
    await st.start()
    assert st.session["pass_id"] is None
    bus.publish(PassStarted(pass_=FakePass()))
    await asyncio.sleep(0.05)
    assert st.session["pass_id"] == "abc12345"
    bus.publish(PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25))
    bus.publish(PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25))
    bus.publish(CommandCompleted(record=CommandRecord(now(), "PING", "10", "responded", None, 1.0, 1)))
    await asyncio.sleep(0.05)
    assert st.pass_counters == {"packets_received": 2, "packets_sent": 0, "commands_sent": 1}
    bus.publish(PassEnded(pass_=FakePass(), packets_received=2))
    await asyncio.sleep(0.05)
    assert st.session["pass_id"] is None
    rows = await st.query("passes")
    assert len(rows) == 1
    r = rows[0]
    assert r["pass_id"] == "abc12345" and r["max_el"] == 42.5
    assert r["packets_received"] == 2 and r["commands_sent"] == 1 and r["packets_sent"] == 0
    assert r["aos"].startswith("2026-09-13T12:00:00") and r["los"].startswith("2026-09-13T12:06:00")
    assert (await st.stats())["passes"] == 1
    await st.stop()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_storage_passes.py -q`
Expected: FAIL with `ImportError: cannot import name 'PassEnded'`

- [ ] **Step 4: Implement**

`cubesat_gs/core/events.py` — append after `FrequencyChanged`:
```python
@dataclass(frozen=True)
class PassStarted:
    pass_: Any   # pass_predictor.Pass
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PassEnded:
    pass_: Any
    packets_received: int
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PassUpdate:
    state: Any   # pass_predictor.PassState
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class CommandStarted:
    name: str
    raw_hex: str
    ts: datetime = field(default_factory=now)
```

`cubesat_gs/storage/sqlite_backend.py`: change `COLLECTIONS` to
`("raw_packets", "decoded_telemetry", "commands", "sessions", "alarms", "passes")` and
`TIME_FIELD = {"sessions": "start_time", "passes": "aos"}`.

`cubesat_gs/storage/mongo_backend.py`: no change needed (time-field index loops over `COLLECTIONS`; `_TTL_COLLECTIONS`/`_APID_COLLECTIONS` unchanged).

`cubesat_gs/storage/exporter.py`: add to `COLUMNS`:
```python
    "passes": ["id", "pass_id", "aos", "los", "max_el", "packets_received", "packets_sent", "commands_sent"],
```

`cubesat_gs/storage/database.py`:
- imports: add `PassEnded, PassStarted` to the events import.
- `_SYNC_ORDER = ("raw_packets", "sessions", "passes", "commands", "decoded_telemetry", "alarms")`.
- `__init__`: add `self.pass_counters: dict[str, int] = {"packets_received": 0, "packets_sent": 0, "commands_sent": 0}` and `self._pass_ref: Ref | None = None`.
- `start()`: session dict gains `"pass_id": None` (it already has it — verify; the Phase 1 dict includes `pass_id: None`).
- `_handlers()`: add `(PassStarted, self._on_pass_started), (PassEnded, self._on_pass_ended)`.
- In `_on_packet_received`, after `self.session["packets_received"] += 1`: `self.pass_counters["packets_received"] += 1` only if `self.session.get("pass_id")`; same for `_on_packet_sent` (`packets_sent`) and `_on_command` (`commands_sent`, only when `r.status != "refused"`).
- New handlers:
```python
    async def _on_pass_started(self, ev: PassStarted) -> None:
        p = ev.pass_
        self.session["pass_id"] = p.id
        self.pass_counters = {"packets_received": 0, "packets_sent": 0, "commands_sent": 0}
        self._pass_ref = await self.write("passes", {
            "pass_id": p.id, "aos": p.aos, "los": p.los, "max_el": p.max_el,
            "packets_received": 0, "packets_sent": 0, "commands_sent": 0})
        await self._flush_session()

    async def _on_pass_ended(self, ev: PassEnded) -> None:
        if self._pass_ref is not None:
            await self._update(self._pass_ref, "passes", dict(self.pass_counters))
        self._pass_ref = None
        self.session["pass_id"] = None
        await self._flush_session()
```
- `_flush_session()`: include `"pass_id"` in the flushed keys tuple.

- [ ] **Step 5: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_storage_passes.py -q && python -m pytest -q -W error`
Expected: 2 passed; full suite green (existing `test_exporter`/`test_storage` unaffected — `stats()` now has 6 keys; check `test_storage.py::test_sqlite_only_flow` asserts only specific keys).

- [ ] **Step 6: Commit**

```bash
git add .gitignore cubesat_gs/requirements.txt cubesat_gs/core/events.py cubesat_gs/storage cubesat_gs/tests/test_storage_passes.py
git commit -m "Add pass events, passes collection and Phase 2 dependencies"
```

---

### Task 2: Pass predictor core (skyfield)

**Files:**
- Create: `cubesat_gs/core/pass_predictor.py`
- Test: `cubesat_gs/tests/test_pass_predictor.py`

**Interfaces:**
- Consumes: `StationConfig(latitude, longitude, altitude)`, `SatelliteConfig(name, tle_line1, tle_line2, tle_source)`, `PassConfig(min_elevation, prediction_days)`, `EventBus`.
- Produces:
```python
@dataclass(frozen=True)
class Pass: id: str; aos: datetime; los: datetime; tca: datetime; max_el: float; aos_az: float; los_az: float; duration_s: float
@dataclass(frozen=True)
class PassState: pass_id: str; t: datetime; az: float; el: float; range_km: float; doppler_hz: float; progress: float
class TLEError(ValueError)
class PassPredictor:
    def __init__(self, bus, station_cfg, satellite_cfg, passes_cfg, *, tctm_mhz: float, clock: Callable[[], datetime] = now)
    enabled: bool; reason: str | None; tle: tuple[str, str] | None
    async def set_tle(self, line1: str, line2: str) -> None        # raises TLEError; recomputes
    async def set_location(self, lat: float, lon: float, alt_m: float) -> None
    async def set_min_elevation(self, deg: float) -> None
    async def upcoming(self, days: int | None = None, *, force: bool = False) -> list[Pass]   # cached 1 h
    def current(self) -> PassState | None
    def next_pass(self) -> Pass | None
    async def track(self, pass_id: str, step_s: int = 10) -> list[tuple[datetime, float, float, float, float]]  # (t, az, el, range_km, doppler_hz)
    def doppler_hz(self, freq_mhz: float, t: datetime | None = None) -> float
    def is_visible(self) -> bool
    def state_at(self, t: datetime) -> tuple[float, float, float, float]   # az, el, range_km, range_rate_km_s
```
- `clock` is injectable so tests freeze time. All skyfield calls run through `asyncio.to_thread` in the async methods; `current()`/`state_at()`/`is_visible()` are sync (single-point evaluation, ~1 ms).

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_pass_predictor.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_pass_predictor.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement pass_predictor.py**

```python
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

    async def set_tle(self, line1: str, line2: str) -> None:
        prev = (self._sat, self.tle, self.reason)
        self._load_tle(line1, line2)
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
            passes = await asyncio.to_thread(self._search, start, days)
            self._cache, self._cache_at, self._cache_days = passes, t, days
            log.info("passes: %d passes in next %d day(s) above %.0f°", len(passes), days, self._min_el)
            return self._cache

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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_pass_predictor.py -q -W error`
Expected: 7 passed. If skyfield emits a `DeprecationWarning` on import under `-W error`, add a `filterwarnings = ignore::DeprecationWarning:skyfield` line to `pytest.ini` and note it in the report.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/pass_predictor.py cubesat_gs/tests/test_pass_predictor.py pytest.ini
git commit -m "Add skyfield-based pass predictor"
```

---

### Task 3: Pass scheduler, TLE refresh, station wiring

**Files:**
- Modify: `cubesat_gs/core/pass_predictor.py`, `cubesat_gs/core/station.py`, `cubesat_gs/core/config.py`
- Test: `cubesat_gs/tests/test_pass_predictor.py` (append), `cubesat_gs/tests/test_integration.py` (append)

**Interfaces:**
- Produces: `PassPredictor.start()/stop()` (scheduler task: `PassStarted` at AOS, `PassUpdate` every `update_interval` s during a pass, `PassEnded` at LOS with `packets_received` from a `counters: Callable[[], dict]` callback; hourly recompute; daily TLE refresh at 03:00 UTC when `tle_source` set); `async refresh_tle(client: httpx.AsyncClient | None = None) -> tuple[str, str]` (raises `TLEError` on fetch/parse failure); `PassPredictor.__init__(..., counters=None, update_interval=1.0, http_client_factory=None)`; `GroundStation.passes: PassPredictor`; `GroundStation.status()["passes"] = {"enabled", "reason", "next": Pass|None as dict, "current": PassState|None as dict}`; helper `pass_to_dict(Pass) -> dict`, `state_to_dict(PassState) -> dict` in `pass_predictor.py`.
- `SatelliteConfig.tle_source` may be a URL to a CelesTrak-style TLE text; the entry whose name line matches `satellite.name` (case-insensitive, stripped) is chosen, else the first entry.

- [ ] **Step 1: Write the failing tests** (append to `test_pass_predictor.py`)

```python
import asyncio
import httpx

from cubesat_gs.core.events import PassEnded, PassStarted, PassUpdate
from cubesat_gs.core.pass_predictor import pass_to_dict, state_to_dict


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
    await asyncio.sleep(0.1)
    assert any(isinstance(e, PassStarted) and e.pass_.id == p.id for e in got)
    assert sum(isinstance(e, PassUpdate) for e in got) >= 2
    clock["t"] = p.los + timedelta(seconds=1)
    await asyncio.sleep(0.1)
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
```

Append to `cubesat_gs/tests/test_integration.py`:
```python
async def test_station_exposes_pass_predictor(gs):
    station, sim, _ser = gs
    st = station.status()
    assert st["passes"]["enabled"] is False and "TLE" in st["passes"]["reason"]
    assert st["passes"]["next"] is None and st["passes"]["current"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_pass_predictor.py cubesat_gs/tests/test_integration.py -q`
Expected: FAIL (`ImportError: pass_to_dict`, `KeyError: 'passes'`)

- [ ] **Step 3: Implement**

`pass_predictor.py` additions:
```python
import httpx
from dataclasses import asdict
from cubesat_gs.core.events import PassEnded, PassStarted, PassUpdate

def pass_to_dict(p: Pass | None) -> dict | None:
    if p is None:
        return None
    d = asdict(p)
    for k in ("aos", "los", "tca"):
        d[k] = d[k].isoformat()
    return d


def state_to_dict(s: PassState | None) -> dict | None:
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
```
Constructor: add params `counters: Callable[[], dict] | None = None, update_interval: float = 1.0, http_client_factory: Callable[[], httpx.AsyncClient] | None = None`; store `self._counters = counters or (lambda: {"packets_received": 0})`, `self._update_interval`, `self._http_factory = http_client_factory or (lambda: httpx.AsyncClient(timeout=10.0))`, `self._tle_source = satellite_cfg.tle_source or ""`, `self._task: asyncio.Task | None = None`, `self._active: Pass | None = None`, `self._last_recompute: datetime | None = None`, `self._last_tle_refresh_day: date | None = None`.

```python
    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="pass-scheduler")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._task = None

    async def refresh_tle(self, client: httpx.AsyncClient | None = None) -> tuple[str, str]:
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
        while True:
            try:
                await self._tick()
            except Exception:  # noqa: BLE001 - the scheduler must survive anything
                log.exception("passes: scheduler tick failed")
            await asyncio.sleep(self._update_interval)

    async def _tick(self) -> None:
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
```

`core/station.py`: import `PassPredictor, pass_to_dict, state_to_dict`; in `__init__` after storage:
`self.passes = PassPredictor(self.bus, cfg.station, cfg.satellite, cfg.passes, tctm_mhz=cfg.frequencies.tctm, counters=lambda: self.storage.pass_counters)`;
`start()`: `await self.passes.start()` after storage; `stop()`: `await self.passes.stop()` first.
`status()` adds:
```python
            "passes": {"enabled": self.passes.enabled, "reason": self.passes.reason,
                       "next": pass_to_dict(self.passes.next_pass()),
                       "current": state_to_dict(self.passes.current())},
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest -q -W error`
Expected: all green (previous 108 + 2 + 7 + 4 + 1).

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/pass_predictor.py cubesat_gs/core/station.py cubesat_gs/tests/test_pass_predictor.py cubesat_gs/tests/test_integration.py
git commit -m "Add pass scheduler, TLE refresh and wire predictor into GroundStation"
```

---
### Task 4: Web scaffold — schemas, error mapping, app factory, status routes, test harness

**Files:**
- Create: `cubesat_gs/web/__init__.py`, `cubesat_gs/web/schemas.py`, `cubesat_gs/web/deps.py`, `cubesat_gs/web/app.py`, `cubesat_gs/web/routes/__init__.py`, `cubesat_gs/web/routes/status.py`, `cubesat_gs/tests/conftest.py`
- Test: `cubesat_gs/tests/test_web_status.py`

**Interfaces:**
- Produces: `create_app(station: GroundStation, *, static_dir: Path | None = None) -> FastAPI` (attributes `app.state.station`, `app.state.hub` set in Task 5 — until then `None`); `deps.get_station(request) -> GroundStation`; `deps.ApiError(status, error, detail=None)`; `deps.install_error_handlers(app)`; `schemas.ws_message(type_, data) -> dict`; Pydantic models listed in spec §3.5 (all created here, routes fill them in later tasks); fixture `web_stack` yielding `(station, sim, client)` where `client` is `httpx.AsyncClient(transport=ASGITransport(app), base_url="http://test")`, station started, SQLite in `tmp_path`, `dotenv=False`, simulator beacon interval 0.1 s and started.

- [ ] **Step 1: Write the failing test**

`cubesat_gs/tests/conftest.py`:
```python
"""Shared fixtures for web tests: a running GroundStation on the in-process simulator."""
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from cubesat_gs.core.config import load_config
from cubesat_gs.core.station import GroundStation
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial
from cubesat_gs.web.app import create_app


async def wait_until(pred, timeout=2.0):
    async def _w():
        while not pred():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_w(), timeout)


@pytest.fixture
async def web_stack(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    cfg = load_config(dotenv=False)
    cfg.serial.port = "sim://"
    cfg.serial.reconnect_interval = 0.05
    cfg.serial.timeouts.tx = 0.5
    cfg.serial.timeouts.freq = 0.5
    cfg.commands.default_timeout = 1.0
    cfg.commands.max_retries = 0
    cfg.database.local_fallback_path = str(tmp_path / "gs.db")
    cfg.database.mongo_uri = None
    cfg.logging.file = str(tmp_path / "gs.log")
    sim = ModemSimulator(beacon_interval=0.1)
    await sim.start()
    ser = SimulatedSerial(sim)
    station = GroundStation(cfg, open_connection=ser.open)
    app = create_app(station, static_dir=tmp_path / "static-none")
    await station.start()
    await wait_until(lambda: station.serial.connected)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield station, sim, client
    await station.stop()
    await sim.stop()
```

`cubesat_gs/tests/test_web_status.py`:
```python
async def test_status_shape(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["serial"]["connected"] is True
    assert body["frequency"] == {"mode": "tctm", "mhz": 435.5}
    assert body["storage"]["mongo"] == "disabled"
    assert body["passes"]["enabled"] is False
    assert body["pending_command"] is None
    assert "packets_received" in body["session"]


async def test_health_shape(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["mongo"] == "disabled" and body["pending_sync"] == 0
    assert body["web"] == {"clients": 0}


async def test_unknown_api_path_is_json_404(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"] == "not_found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_status.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cubesat_gs.web'`

- [ ] **Step 3: Implement**

`cubesat_gs/web/__init__.py` and `cubesat_gs/web/routes/__init__.py`: empty.

`cubesat_gs/web/schemas.py`:
```python
"""Pydantic models for every REST and WebSocket payload. The frontend's types.ts mirrors these."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from cubesat_gs.core.events import now

Kind = Literal["beacon", "telemetry", "command", "malformed", "unknown"]
Direction = Literal["rx", "tx"]
CommandStatus = Literal["acked", "responded", "timeout", "failed", "refused"]


class ErrorOut(BaseModel):
    error: str
    detail: str | None = None


class SerialStatus(BaseModel):
    connected: bool
    port: str | None


class FrequencyStatus(BaseModel):
    mode: str
    mhz: float


class StorageStatus(BaseModel):
    mongo: Literal["ok", "degraded", "disabled"]


class PassOut(BaseModel):
    id: str
    aos: datetime
    los: datetime
    tca: datetime
    max_el: float
    aos_az: float
    los_az: float
    duration_s: float


class PassStateOut(BaseModel):
    pass_id: str
    t: datetime
    az: float
    el: float
    range_km: float
    doppler_hz: float
    progress: float


class PassesStatus(BaseModel):
    enabled: bool
    reason: str | None
    next: PassOut | None
    current: PassStateOut | None


class SessionOut(BaseModel):
    start_time: datetime
    end_time: datetime | None
    pass_id: str | None
    packets_received: int
    packets_sent: int
    notes: str


class CommandRecordOut(BaseModel):
    ts: datetime
    name: str
    raw_hex: str
    status: CommandStatus
    response_hex: str | None
    latency_ms: float | None
    attempts: int
    error: str | None
    pending: bool = False


class StatusOut(BaseModel):
    station: str
    serial: SerialStatus
    frequency: FrequencyStatus
    pending_command: CommandRecordOut | None
    storage: StorageStatus
    session: SessionOut
    passes: PassesStatus


class HealthOut(BaseModel):
    mongo: str
    pending_sync: int
    sqlite_path: str
    web: dict[str, int]


class TelemetryField(BaseModel):
    name: str
    value: Any
    unit: str | None
    alarm: Literal["nominal", "low", "high"] | None


class FeedEntry(BaseModel):
    id: str
    ts: datetime
    direction: Direction
    apid: int | None
    apid_name: str | None
    seq: int | None
    raw_hex: str
    rssi: float | None
    snr: float | None
    freq_mhz: float
    kind: Kind
    summary: str
    fields: list[TelemetryField] | None


class TelemetryLatest(BaseModel):
    apid: int
    apid_name: str
    ts: datetime
    fields: list[TelemetryField]


class TelemetryDefField(BaseModel):
    name: str
    type: str
    unit: str | None
    alarm_low: float | None
    alarm_high: float | None


class TelemetryDefOut(BaseModel):
    apid: int
    name: str
    fields: list[TelemetryDefField]


class TelemetryPoint(BaseModel):
    t: datetime
    v: float


class TelemetryHistoryOut(BaseModel):
    apid: int
    field: str
    unit: str | None
    alarm_low: float | None
    alarm_high: float | None
    points: list[TelemetryPoint]
    total_rows: int


class CommandDefOut(BaseModel):
    name: str
    description: str
    apid: int
    payload_hex: str
    payload_text: str | None
    response_apid: int | None
    timeout: float
    critical: bool


class SendCommandIn(BaseModel):
    confirm: bool = False
    payload_hex: str | None = None


class SendRawIn(BaseModel):
    hex: str
    confirm: bool = False


class FrequencyOut(BaseModel):
    mode: str
    mhz: float
    presets: dict[str, float]
    history: list[dict[str, Any]]


class FrequencyIn(BaseModel):
    mode: Literal["tctm", "beacon_listen", "custom"]
    mhz: float | None = None


class PassesOut(BaseModel):
    enabled: bool
    reason: str | None
    passes: list[PassOut]


class TrackPoint(BaseModel):
    t: datetime
    az: float
    el: float
    range_km: float
    doppler_hz: float


class SerialPortOut(BaseModel):
    device: str
    description: str
    vid: int | None
    pid: int | None


class ConfigOut(BaseModel):
    config: dict[str, Any]
    writable: list[str]
    applies: dict[str, Literal["live", "restart"]]


class ConfigIn(BaseModel):
    sections: dict[str, dict[str, Any]]


class ConfigPutOut(BaseModel):
    config: dict[str, Any]
    applied_live: list[str]
    restart_required: bool


class ExportIn(BaseModel):
    collection: str
    fmt: Literal["csv", "json"] = "csv"
    start: datetime | None = None
    end: datetime | None = None
    apid: int | None = None


class AlarmOut(BaseModel):
    ts: datetime
    apid: int
    field_name: str
    value: float
    threshold: float
    alarm_type: Literal["low", "high"]


class GapOut(BaseModel):
    ts: datetime
    apid: int
    expected: int
    received: int
    missed: int


class SnapshotOut(BaseModel):
    status: StatusOut
    feed: list[FeedEntry]
    telemetry_latest: dict[int, TelemetryLatest]
    pending_command: CommandRecordOut | None
    next_pass: PassOut | None
    current_pass: PassStateOut | None
    alarms_active: list[dict[str, Any]]


WsType = Literal["snapshot", "status", "packet", "telemetry", "alarm", "gap", "command", "pass", "pong"]


class WsMessage(BaseModel):
    type: WsType
    ts: datetime = Field(default_factory=now)
    data: Any


def ws_message(type_: WsType, data: Any) -> dict:
    """Build the wire dict for a WS message (data already JSON-serialisable)."""
    return {"type": type_, "ts": now().isoformat(), "data": data}
```

`cubesat_gs/web/deps.py`:
```python
"""Request dependencies and the Phase 1 exception → HTTP status mapping."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cubesat_gs.core.pass_predictor import TLEError
from cubesat_gs.core.serial_handler import SerialCommandTimeout, SerialDisconnected
from cubesat_gs.core.station import GroundStation
from cubesat_gs.core.telecommand import CommandBusyError, UnknownCommandError, WrongModeError

log = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, error: str, detail: str | None = None) -> None:
        super().__init__(detail or error)
        self.status, self.error, self.detail = status, error, detail


def get_station(request: Request) -> GroundStation:
    return request.app.state.station


def _json(status: int, error: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse({"error": error, "detail": detail}, status_code=status)


_MAPPED: list[tuple[type[Exception], int, str]] = [
    (CommandBusyError, 409, "command_busy"),
    (WrongModeError, 400, "wrong_mode"),
    (UnknownCommandError, 404, "unknown_command"),
    (SerialCommandTimeout, 504, "modem_timeout"),
    (SerialDisconnected, 503, "serial_disconnected"),
    (TLEError, 422, "invalid_tle"),
    (ValueError, 422, "invalid_value"),
]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _json(exc.status, exc.error, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _json(422, "validation_error", str(exc.errors()[0].get("msg")) if exc.errors() else None)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return _json(exc.status_code, "not_found" if exc.status_code == 404 else "http_error", str(exc.detail))

    for exc_type, status, error in _MAPPED:
        def _make(status=status, error=error):
            async def handler(_: Request, exc: Exception):
                return _json(status, error, str(exc))
            return handler
        app.add_exception_handler(exc_type, _make())

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("web: unhandled error")
        return _json(500, "internal", None)
```

`cubesat_gs/web/routes/status.py`:
```python
from fastapi import APIRouter, Depends, Request

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import get_station
from cubesat_gs.web.schemas import HealthOut, StatusOut

router = APIRouter()


@router.get("/status", response_model=StatusOut)
async def get_status(station: GroundStation = Depends(get_station)):
    return station.status()


@router.get("/health", response_model=HealthOut)
async def get_health(request: Request, station: GroundStation = Depends(get_station)):
    hub = request.app.state.hub
    h = await station.storage.health()
    h["web"] = {"clients": hub.client_count if hub is not None else 0}
    return h
```

`cubesat_gs/web/app.py`:
```python
"""FastAPI application factory. Never constructs Phase 1 modules; wires the web layer onto a GroundStation."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import install_error_handlers
from cubesat_gs.web.routes import status as status_routes

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(station: GroundStation, *, static_dir: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield

    app = FastAPI(title="CubeSat GS", version="2.0", lifespan=lifespan, docs_url="/api/docs",
                  openapi_url="/api/openapi.json", redoc_url=None)
    app.state.station = station
    app.state.hub = None
    app.state.static_dir = static_dir or STATIC_DIR
    install_error_handlers(app)
    app.include_router(status_routes.router, prefix="/api")
    return app
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_status.py -q -W error`
Expected: 3 passed. Then `python -m pytest -q -W error` all green (the new `conftest.py` must not break the existing `test_integration.py`'s own `gs` fixture — names differ).

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web cubesat_gs/tests/conftest.py cubesat_gs/tests/test_web_status.py
git commit -m "Add FastAPI app factory, schemas, error mapping and status routes"
```

---

### Task 5: WebSocket hub and `/ws`

**Files:**
- Create: `cubesat_gs/web/hub.py`
- Modify: `cubesat_gs/web/app.py`
- Test: `cubesat_gs/tests/test_web_ws.py`

**Interfaces:**
- Produces: `WebSocketHub(station, *, ring_size=500, queue_size=500, status_poll=5.0, pending_ttl=2.0)` with `async start()`, `async stop()`, `client_count: int`, `feed: deque[dict]` (completed FeedEntry dicts, newest last), `snapshot() -> dict`, `async handle(websocket)` (the `/ws` endpoint body), `feed_entry_from_row(row: dict) -> dict` (used by Task 6 to shape DB rows like live entries). Route `/ws` registered in `app.py`; lifespan starts/stops the hub. Feed entry `id` = `f"{ts_ms}-{n}"` monotonic counter.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_web_ws.py`:
```python
import asyncio
import json

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until


class WsClient:
    """Drives hub.handle() through a fake Starlette WebSocket (no network)."""

    def __init__(self):
        self.sent: list[dict] = []
        self._incoming: asyncio.Queue = asyncio.Queue()
        self.closed: int | None = None
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        self.sent.append(json.loads(text))

    async def receive_text(self) -> str:
        item = await self._incoming.get()
        if item is None:
            from starlette.websockets import WebSocketDisconnect
            raise WebSocketDisconnect(1000)
        return item

    async def close(self, code: int = 1000):
        self.closed = code
        self._incoming.put_nowait(None)

    def disconnect(self):
        self._incoming.put_nowait(None)

    def of(self, t):
        return [m for m in self.sent if m["type"] == t]


async def _connect(web_stack):
    station, sim, client = web_stack
    hub = client._transport.app.state.hub
    ws = WsClient()
    task = asyncio.create_task(hub.handle(ws))
    await wait_until(lambda: any(m["type"] == "snapshot" for m in ws.sent))
    return hub, ws, task


async def test_snapshot_on_connect(web_stack):
    station, sim, client = web_stack
    hub, ws, task = await _connect(web_stack)
    snap = ws.of("snapshot")[0]["data"]
    assert snap["status"]["serial"]["connected"] is True
    assert isinstance(snap["feed"], list) and snap["telemetry_latest"] == {}
    assert snap["pending_command"] is None and snap["next_pass"] is None
    assert hub.client_count == 1
    ws.disconnect()
    await task
    assert hub.client_count == 0


async def test_beacon_produces_packet_and_telemetry_deltas(web_stack):
    station, sim, client = web_stack
    hub, ws, task = await _connect(web_stack)
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    await wait_until(lambda: len(ws.of("packet")) >= 1 and len(ws.of("telemetry")) >= 1)
    pkt = ws.of("packet")[0]["data"]
    assert pkt["direction"] == "rx" and pkt["apid"] == 10 and pkt["kind"] == "beacon"
    assert pkt["apid_name"] == "Beacon" and pkt["summary"] == "VLEO_BEACON_SYS_NOMINAL"
    assert pkt["fields"][0]["name"] == "message" and pkt["freq_mhz"] == 437.25
    assert pkt["raw_hex"] == pkt["raw_hex"].upper() and "-" in pkt["id"]
    tm = ws.of("telemetry")[0]["data"]
    assert tm["apid"] == 10 and tm["fields"][0]["value"] == "VLEO_BEACON_SYS_NOMINAL"
    assert any(m["data"]["frequency"]["mode"] == "beacon_listen" for m in ws.of("status"))
    assert len(hub.feed) >= 1 and hub.feed[-1]["kind"] == "beacon"
    ws.disconnect()
    await task


async def test_ping_pong_and_bad_message_ignored(web_stack):
    hub, ws, task = await _connect(web_stack)
    ws._incoming.put_nowait("not json")
    ws._incoming.put_nowait(json.dumps({"type": "ping"}))
    await wait_until(lambda: len(ws.of("pong")) == 1)
    ws.disconnect()
    await task


async def test_slow_client_is_dropped(web_stack):
    station, sim, client = web_stack
    hub = client._transport.app.state.hub
    hub._queue_size = 3

    class StuckWs(WsClient):
        async def send_text(self, text):
            if json.loads(text)["type"] != "snapshot":
                await asyncio.Event().wait()  # never returns → queue fills
            self.sent.append(json.loads(text))

    ws = StuckWs()
    task = asyncio.create_task(hub.handle(ws))
    await wait_until(lambda: ws.accepted)
    for _ in range(6):
        sim.inject_rx(bytes.fromhex("000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C"))
        await asyncio.sleep(0.01)
    await wait_until(lambda: ws.closed == 1013, timeout=3.0)
    await task
    assert hub.client_count == 0


async def test_feed_snapshot_includes_recent(web_stack):
    station, sim, client = web_stack
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    hub = client._transport.app.state.hub
    await wait_until(lambda: len(hub.feed) >= 2)
    hub2, ws, task = await _connect(web_stack)
    assert len(ws.of("snapshot")[0]["data"]["feed"]) >= 2
    ws.disconnect()
    await task
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_ws.py -q`
Expected: FAIL (`AttributeError: 'NoneType' object has no attribute 'handle'`)

- [ ] **Step 3: Implement hub.py**

```python
"""WebSocketHub: one more EventBus subscriber that fans events out to browsers as JSON deltas."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import OrderedDict, deque
from typing import Any

from starlette.websockets import WebSocketDisconnect

from cubesat_gs.core import ccsds
from cubesat_gs.core.events import (AlarmRaised, CommandCompleted, CommandStarted, ConnectionChanged,
                                    FrequencyChanged, PacketDecoded, PacketMalformed, PacketReceived,
                                    PacketSent, PassEnded, PassStarted, PassUpdate, SequenceGap, now)
from cubesat_gs.core.pass_predictor import pass_to_dict, state_to_dict
from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.schemas import ws_message

log = logging.getLogger(__name__)

_KIND_BY_APID = {ccsds.APID_BEACON: "beacon", ccsds.APID_TM_RESPONSE: "telemetry"}


def _fields(decoded) -> list[dict]:
    return [{"name": f.name, "value": f.value, "unit": f.unit, "alarm": f.alarm} for f in decoded.fields]


def summarize(kind: str, fields: list[dict] | None, reason: str | None = None, name: str | None = None) -> str:
    if kind == "malformed":
        return reason or "malformed"
    if kind == "command":
        return name or "TX"
    if fields:
        for f in fields:
            if isinstance(f["value"], str) and f["name"] != "raw_hex":
                return f["value"]
        return f"{len(fields)} fields"
    return "unknown APID"


class _Client:
    def __init__(self, ws, queue_size: int) -> None:
        self.ws = ws
        self.queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=queue_size)


class WebSocketHub:
    def __init__(self, station: GroundStation, *, ring_size: int = 500, queue_size: int = 500,
                 status_poll: float = 5.0, pending_ttl: float = 2.0) -> None:
        self._station = station
        self._bus = station.bus
        self._queue_size = queue_size
        self._status_poll = status_poll
        self._pending_ttl = pending_ttl
        self.feed: deque[dict] = deque(maxlen=ring_size)
        self._clients: set[_Client] = set()
        self._pending: OrderedDict[int, tuple[PacketReceived, dict]] = OrderedDict()
        self._seq = 0
        self._tasks: list[asyncio.Task] = []
        self._last_storage_state: str | None = None
        self._last_command_name: str | None = None

    # ---- lifecycle
    def _handlers(self):
        return ((ConnectionChanged, self._on_status_change), (FrequencyChanged, self._on_status_change),
                (PacketReceived, self._on_rx), (PacketDecoded, self._on_decoded),
                (PacketMalformed, self._on_malformed), (PacketSent, self._on_tx),
                (AlarmRaised, self._on_alarm), (SequenceGap, self._on_gap),
                (CommandStarted, self._on_command_started), (CommandCompleted, self._on_command),
                (PassStarted, self._on_pass_edge), (PassEnded, self._on_pass_edge), (PassUpdate, self._on_pass_update))

    async def start(self) -> None:
        for et, h in self._handlers():
            self._bus.subscribe(et, h)
        self._tasks = [asyncio.create_task(self._status_poll_loop(), name="hub-status"),
                       asyncio.create_task(self._pending_sweep(), name="hub-pending")]

    async def stop(self) -> None:
        for et, h in self._handlers():
            self._bus.unsubscribe(et, h)
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        self._tasks.clear()
        for c in list(self._clients):
            c.queue.put_nowait(None)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    # ---- broadcast
    def _broadcast(self, type_: str, data: Any) -> None:
        if not self._clients:
            return
        text = json.dumps(ws_message(type_, data), default=str)
        for c in list(self._clients):
            try:
                c.queue.put_nowait(text)
            except asyncio.QueueFull:
                log.warning("ws: dropping slow client")
                self._clients.discard(c)
                asyncio.ensure_future(self._close(c, 1013))  # handle()'s finally cancels the sender

    async def _close(self, c: _Client, code: int) -> None:
        try:
            await c.ws.close(code=code)
        except Exception:  # noqa: BLE001
            pass

    def snapshot(self) -> dict:
        st = self._station
        latest = {apid: {"apid": apid, "apid_name": d.apid_name, "ts": now().isoformat(), "fields": _fields(d)}
                  for apid, d in st.decoder.last_values.items()}
        alarms = [{"apid": apid, "field_name": f["name"], "value": f["value"], "alarm": f["alarm"]}
                  for apid, d in latest.items() for f in d["fields"] if f["alarm"] in ("low", "high")]
        status = st.status()
        return {"status": status, "feed": list(self.feed), "telemetry_latest": latest,
                "pending_command": status["pending_command"], "next_pass": status["passes"]["next"],
                "current_pass": status["passes"]["current"], "alarms_active": alarms}

    async def handle(self, ws) -> None:
        await ws.accept()
        c = _Client(ws, self._queue_size)
        self._clients.add(c)
        await ws.send_text(json.dumps(ws_message("snapshot", self.snapshot()), default=str))
        sender = asyncio.create_task(self._sender(c))
        try:
            while True:
                try:
                    raw = await ws.receive_text()
                except WebSocketDisconnect:
                    break
                try:
                    msg = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("type") == "ping":
                    c.queue.put_nowait(json.dumps(ws_message("pong", {})))
        finally:
            self._clients.discard(c)
            if not c.queue.full():
                c.queue.put_nowait(None)
            sender.cancel()
            try:
                await sender
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass

    async def _sender(self, c: _Client) -> None:
        while True:
            text = await c.queue.get()
            if text is None:
                return
            try:
                await c.ws.send_text(text)
            except Exception:  # noqa: BLE001 - client gone
                self._clients.discard(c)
                return

    # ---- feed assembly
    def _new_id(self) -> str:
        self._seq += 1
        return f"{int(now().timestamp() * 1000)}-{self._seq}"

    async def _on_rx(self, ev: PacketReceived) -> None:
        peek = ccsds.peek_apid_seq(ev.raw)
        entry = {"id": self._new_id(), "ts": ev.ts.isoformat(), "direction": "rx",
                 "apid": peek[0] if peek else None, "apid_name": None, "seq": peek[1] if peek else None,
                 "raw_hex": ev.raw.hex().upper(), "rssi": ev.rssi, "snr": ev.snr, "freq_mhz": ev.freq_mhz,
                 "kind": "unknown", "summary": "", "fields": None, "_at": now()}
        self._pending[id(ev)] = (ev, entry)
        while len(self._pending) > 1000:
            _, (_, stale) = self._pending.popitem(last=False)
            self._emit_entry(stale)

    def _emit_entry(self, entry: dict) -> None:
        entry.pop("_at", None)
        if not entry["summary"]:
            entry["summary"] = summarize(entry["kind"], entry["fields"])
        self.feed.append(entry)
        self._broadcast("packet", entry)

    async def _on_decoded(self, ev: PacketDecoded) -> None:
        item = self._pending.pop(id(ev.source), None)
        if item is None:
            return
        _, entry = item
        d = ev.decoded
        entry["apid"], entry["apid_name"], entry["seq"] = ev.packet.apid, d.apid_name, ev.packet.sequence_count
        entry["fields"] = _fields(d)
        entry["kind"] = "unknown" if d.unknown_apid else _KIND_BY_APID.get(ev.packet.apid, "telemetry")
        entry["summary"] = summarize(entry["kind"], entry["fields"])
        self._emit_entry(entry)
        self._broadcast("telemetry", {"apid": ev.packet.apid, "apid_name": d.apid_name,
                                      "ts": ev.source.ts.isoformat(), "fields": entry["fields"]})

    async def _on_malformed(self, ev: PacketMalformed) -> None:
        item = self._pending.pop(id(ev.source), None)
        if item is None:
            return
        _, entry = item
        entry["kind"], entry["summary"] = "malformed", summarize("malformed", None, reason=ev.reason)
        self._emit_entry(entry)

    async def _on_tx(self, ev: PacketSent) -> None:
        peek = ccsds.peek_apid_seq(ev.raw)
        name = self._last_command_name
        self._emit_entry({"id": self._new_id(), "ts": ev.ts.isoformat(), "direction": "tx",
                          "apid": peek[0] if peek else None, "apid_name": None, "seq": peek[1] if peek else None,
                          "raw_hex": ev.raw.hex().upper(), "rssi": None, "snr": None, "freq_mhz": ev.freq_mhz,
                          "kind": "command", "summary": summarize("command", None, name=name or f"TX {len(ev.raw)} B"),
                          "fields": None})

    async def _pending_sweep(self) -> None:
        while True:
            await asyncio.sleep(self._pending_ttl / 2)
            cutoff = now().timestamp() - self._pending_ttl
            for key, (_, entry) in list(self._pending.items()):
                if entry["_at"].timestamp() < cutoff:
                    del self._pending[key]
                    self._emit_entry(entry)

    # ---- other deltas
    async def _on_alarm(self, ev: AlarmRaised) -> None:
        self._broadcast("alarm", {"ts": ev.ts.isoformat(), "apid": ev.apid, "field_name": ev.field_name,
                                  "value": ev.value, "threshold": ev.threshold, "alarm_type": ev.alarm_type})

    async def _on_gap(self, ev: SequenceGap) -> None:
        self._broadcast("gap", {"ts": ev.ts.isoformat(), "apid": ev.apid, "expected": ev.expected,
                                "received": ev.received, "missed": ev.missed})

    async def _on_command_started(self, ev: CommandStarted) -> None:
        self._last_command_name = ev.name
        self._broadcast("command", {"ts": ev.ts.isoformat(), "name": ev.name, "raw_hex": ev.raw_hex,
                                    "status": "acked", "response_hex": None, "latency_ms": None,
                                    "attempts": 0, "error": None, "pending": True})

    async def _on_command(self, ev: CommandCompleted) -> None:
        self._last_command_name = None
        d = ev.record.as_dict()
        d["pending"] = False
        self._broadcast("command", d)
        self._broadcast("status", self._station.status())

    async def _on_status_change(self, ev) -> None:
        self._broadcast("status", self._station.status())

    async def _on_pass_edge(self, ev) -> None:
        kind = "aos" if isinstance(ev, PassStarted) else "los"
        self._broadcast("pass", {"event": kind, "pass": pass_to_dict(ev.pass_)})
        self._broadcast("status", self._station.status())

    async def _on_pass_update(self, ev: PassUpdate) -> None:
        self._broadcast("pass", state_to_dict(ev.state))

    async def _status_poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._status_poll)
            state = self._station.storage.state
            if state != self._last_storage_state:
                self._last_storage_state = state
                self._broadcast("status", self._station.status())


def feed_entry_from_row(row: dict, decoded_rows: list[dict] | None = None) -> dict:
    """Shape a raw_packets DB row (+ its decoded_telemetry rows) like a live FeedEntry."""
    apid = row.get("apid")
    fields = [{"name": d["field_name"], "value": d["field_value"], "unit": d.get("unit"),
               "alarm": d.get("alarm_status")} for d in (decoded_rows or [])] or None
    direction = row.get("direction", "rx")
    if direction == "tx":
        kind = "command"
    elif apid is None:
        kind = "malformed"
    elif fields:
        kind = _KIND_BY_APID.get(apid, "telemetry")
    else:
        kind = "unknown"
    apid_name = decoded_rows[0].get("apid_name") if decoded_rows else None
    return {"id": str(row["id"]), "ts": row["timestamp"], "direction": direction, "apid": apid,
            "apid_name": apid_name, "seq": row.get("sequence_count"), "raw_hex": row.get("raw_hex", ""),
            "rssi": row.get("rssi"), "snr": row.get("snr"), "freq_mhz": row.get("frequency_mhz", 0.0),
            "kind": kind, "summary": summarize(kind, fields, name=f"TX {len(row.get('raw_hex', '')) // 2} B"),
            "fields": fields}
```

`app.py` changes:
```python
from fastapi import WebSocket
from cubesat_gs.web.hub import WebSocketHub
...
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub = WebSocketHub(station)
        app.state.hub = hub
        await hub.start()
        try:
            yield
        finally:
            await hub.stop()
            app.state.hub = None
...
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        hub: WebSocketHub | None = app.state.hub
        if hub is None:
            await websocket.close(code=1013)
            return
        await hub.handle(websocket)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_ws.py -q -W error` then the full suite.
Expected: 5 passed; suite green.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web/hub.py cubesat_gs/web/app.py cubesat_gs/tests/test_web_ws.py
git commit -m "Add WebSocket hub with snapshot and typed deltas"
```

---
### Task 6: Feed and telemetry routes (paging, LTTB downsampling)

**Files:**
- Create: `cubesat_gs/web/lttb.py`, `cubesat_gs/web/routes/feed.py`, `cubesat_gs/web/routes/telemetry.py`
- Modify: `cubesat_gs/web/app.py` (include routers)
- Test: `cubesat_gs/tests/test_web_feed_telemetry.py`

**Interfaces:**
- Produces: `lttb(points: list[tuple[float, float]], threshold: int) -> list[tuple[float, float]]`; `GET /api/packets?apid&direction&kind&start&end&limit&before` → `{"items": [FeedEntry], "next_before": str|null}`; `GET /api/telemetry/latest` → `{"latest": {apid: TelemetryLatest}, "definitions": [TelemetryDefOut]}`; `GET /api/telemetry/history?apid&field&start&end&max_points` → `TelemetryHistoryOut`; `GET /api/telemetry/definitions` → `{"yaml": str, "definitions": [TelemetryDefOut]}`.
- `Storage.query` has no `before` cursor; feed paging filters `id < before` client-side on the SQLite/Mongo rows by fetching `limit` rows with `end = ts_of(before)`: implement `before` as an ISO timestamp cursor (`next_before` = the oldest returned row's `timestamp`), which both backends support via `end`. Rows with an identical timestamp to the cursor are excluded by comparing `id != before_id`; pass `before` as `<iso>|<id>`.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_web_feed_telemetry.py`:
```python
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until
from cubesat_gs.web.lttb import lttb


def test_lttb_keeps_endpoints_and_caps():
    pts = [(float(i), float((i * 7919) % 101)) for i in range(1000)]
    out = lttb(pts, 50)
    assert len(out) == 50 and out[0] == pts[0] and out[-1] == pts[-1]
    assert lttb(pts, 5000) == pts and lttb(pts[:2], 1) == pts[:2] and lttb([], 10) == []


async def _seed(station, n=5):
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    await wait_until(lambda: len(station.decoder.last_values) >= 1)
    sim_wait = 0.12 * n
    await asyncio.sleep(sim_wait)
    await station.freq.set_mode(Mode.TCTM)
    await station.bus.drain()


async def test_packets_paging_and_filters(web_stack):
    station, sim, client = web_stack
    await _seed(station, 6)
    await asyncio.sleep(0.1)
    r = await client.get("/api/packets", params={"limit": 3})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 3 and body["next_before"]
    first = body["items"][0]
    assert first["direction"] == "rx" and first["kind"] == "beacon" and first["fields"][0]["name"] == "message"
    assert first["summary"] == "VLEO_BEACON_SYS_NOMINAL" and first["apid_name"] == "Beacon"
    r2 = await client.get("/api/packets", params={"limit": 3, "before": body["next_before"]})
    ids1 = {i["id"] for i in body["items"]}
    assert all(i["id"] not in ids1 for i in r2.json()["items"])
    assert all(i["ts"] <= body["items"][-1]["ts"] for i in r2.json()["items"])
    r3 = await client.get("/api/packets", params={"apid": 999})
    assert r3.json()["items"] == [] and r3.json()["next_before"] is None
    r4 = await client.get("/api/packets", params={"direction": "tx"})
    assert r4.json()["items"] == []
    r5 = await client.get("/api/packets", params={"limit": 9999})
    assert r5.status_code == 422


async def test_telemetry_latest_and_definitions(web_stack):
    station, sim, client = web_stack
    await _seed(station, 2)
    r = await client.get("/api/telemetry/latest")
    body = r.json()
    assert body["latest"]["10"]["fields"][0]["value"] == "VLEO_BEACON_SYS_NOMINAL"
    defs = {d["apid"]: d for d in body["definitions"]}
    assert defs[10]["name"] == "Beacon" and defs[101]["fields"][0]["name"] == "response_data"
    r = await client.get("/api/telemetry/definitions")
    assert "apid_10" in r.json()["yaml"] and len(r.json()["definitions"]) == 2


async def test_telemetry_history_downsamples(web_stack, tmp_path):
    station, sim, client = web_stack
    base = datetime(2026, 9, 13, 0, 0, tzinfo=timezone.utc)
    for i in range(300):
        await station.storage.write("decoded_telemetry", {
            "packet_id": None, "timestamp": base + timedelta(seconds=i), "apid": 50, "apid_name": "EPS",
            "field_name": "v_bat", "field_value": 3.0 + (i % 10) / 10, "unit": "V", "alarm_status": "nominal"})
    r = await client.get("/api/telemetry/history", params={"apid": 50, "field": "v_bat", "max_points": 40,
                                                            "start": base.isoformat(),
                                                            "end": (base + timedelta(seconds=400)).isoformat()})
    assert r.status_code == 200
    body = r.json()
    assert body["apid"] == 50 and body["field"] == "v_bat" and body["unit"] == "V"
    assert body["total_rows"] == 300 and len(body["points"]) == 40
    assert body["points"][0]["t"] < body["points"][-1]["t"]
    r = await client.get("/api/telemetry/history", params={"apid": 50, "field": "nope"})
    assert r.json()["points"] == [] and r.json()["total_rows"] == 0
    r = await client.get("/api/telemetry/history", params={"apid": 10, "field": "message"})
    assert r.status_code == 422  # non-numeric field
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_feed_telemetry.py -q`
Expected: FAIL with `ModuleNotFoundError: cubesat_gs.web.lttb`

- [ ] **Step 3: Implement**

`cubesat_gs/web/lttb.py`:
```python
"""Largest-Triangle-Three-Buckets downsampling (Steinarsson 2013) for time series."""
from __future__ import annotations


def lttb(points: list[tuple[float, float]], threshold: int) -> list[tuple[float, float]]:
    n = len(points)
    if threshold >= n or threshold < 3 or n < 3:
        return list(points)
    sampled = [points[0]]
    bucket = (n - 2) / (threshold - 2)
    a = 0
    for i in range(threshold - 2):
        r0 = int((i + 1) * bucket) + 1
        r1 = min(int((i + 2) * bucket) + 1, n)
        avg_x = sum(p[0] for p in points[r0:r1]) / max(r1 - r0, 1)
        avg_y = sum(p[1] for p in points[r0:r1]) / max(r1 - r0, 1)
        s0 = int(i * bucket) + 1
        s1 = int((i + 1) * bucket) + 1
        ax, ay = points[a]
        best, best_area = s0, -1.0
        for j in range(s0, s1):
            area = abs((ax - avg_x) * (points[j][1] - ay) - (ax - points[j][0]) * (avg_y - ay)) * 0.5
            if area > best_area:
                best, best_area = j, area
        sampled.append(points[best])
        a = best
    sampled.append(points[-1])
    return sampled
```

`cubesat_gs/web/routes/feed.py`:
```python
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.hub import feed_entry_from_row
from cubesat_gs.web.schemas import Direction, Kind

router = APIRouter()


def _parse_cursor(before: str | None) -> tuple[datetime | None, str | None]:
    if not before:
        return None, None
    iso, _, row_id = before.partition("|")
    try:
        return datetime.fromisoformat(iso), (row_id or None)
    except ValueError as e:
        raise ApiError(422, "invalid_cursor", str(e)) from e


@router.get("/packets")
async def list_packets(station: GroundStation = Depends(get_station),
                       apid: int | None = None, direction: Direction | None = None, kind: Kind | None = None,
                       start: datetime | None = None, end: datetime | None = None,
                       limit: int = Query(100, ge=1, le=500), before: str | None = None):
    cursor_ts, cursor_id = _parse_cursor(before)
    q_end = min(end, cursor_ts) if (end and cursor_ts) else (cursor_ts or end)
    rows = await station.storage.query("raw_packets", start=start, end=q_end, apid=apid, limit=limit + 1)
    if cursor_id is not None:
        rows = [r for r in rows if str(r["id"]) != cursor_id]
    page = rows[:limit]
    by_packet: dict[str, list[dict]] = {}
    if page:
        # one range query for all decoded rows of this page, grouped by packet_id (no N+1)
        decoded = await station.storage.query("decoded_telemetry", start=page[-1]["timestamp"],
                                              end=page[0]["timestamp"], limit=len(page) * 32)
        for d in decoded:
            by_packet.setdefault(str(d.get("packet_id")), []).append(d)
    items = []
    for r in page:
        if direction and r.get("direction") != direction:
            continue
        entry = feed_entry_from_row(r, by_packet.get(str(r["id"]), []))
        if kind and entry["kind"] != kind:
            continue
        items.append(entry)
    next_before = None
    if len(rows) > limit and rows[:limit]:
        last = rows[limit - 1]
        next_before = f"{last['timestamp']}|{last['id']}"
    return {"items": items, "next_before": next_before}
```

`cubesat_gs/web/routes/telemetry.py`:
```python
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.events import now
from cubesat_gs.core.station import GroundStation
from cubesat_gs.core.telemetry import _NUMERIC  # struct formats keyed by type name
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.lttb import lttb

router = APIRouter()


def _defs(station: GroundStation) -> list[dict]:
    return [{"apid": apid, "name": d.name,
             "fields": [{"name": f.name, "type": f.type, "unit": f.unit,
                         "alarm_low": f.alarm_low, "alarm_high": f.alarm_high} for f in d.fields]}
            for apid, d in sorted(station.decoder.definitions.items())]


@router.get("/telemetry/latest")
async def telemetry_latest(station: GroundStation = Depends(get_station)):
    latest = {}
    for apid, d in station.decoder.last_values.items():
        latest[apid] = {"apid": apid, "apid_name": d.apid_name, "ts": now().isoformat(),
                        "fields": [{"name": f.name, "value": f.value, "unit": f.unit, "alarm": f.alarm} for f in d.fields]}
    return {"latest": latest, "definitions": _defs(station)}


@router.get("/telemetry/definitions")
async def telemetry_definitions(station: GroundStation = Depends(get_station)):
    path = station.cfg.resolve(station.cfg.telemetry.definitions)
    return {"yaml": path.read_text(encoding="utf-8"), "definitions": _defs(station)}


@router.get("/telemetry/history")
async def telemetry_history(station: GroundStation = Depends(get_station), apid: int = Query(...),
                            field: str = Query(...), start: datetime | None = None,
                            end: datetime | None = None, max_points: int = Query(600, ge=10, le=2000)):
    fdef = None
    d = station.decoder.definitions.get(apid)
    if d is not None:
        fdef = next((f for f in d.fields if f.name == field), None)
        if fdef is not None and fdef.type not in _NUMERIC:
            raise ApiError(422, "not_numeric", f"field {field!r} of APID {apid} is {fdef.type}")
    end = end or now()
    start = start or end - timedelta(hours=1)
    rows = [r async for r in station.storage.iterate("decoded_telemetry", start=start, end=end, apid=apid)]
    rows = [r for r in rows if r.get("field_name") == field and isinstance(r.get("field_value"), (int, float))]
    pts = [(datetime.fromisoformat(r["timestamp"]).timestamp() if isinstance(r["timestamp"], str)
            else r["timestamp"].timestamp(), float(r["field_value"])) for r in rows]
    thinned = lttb(pts, max_points)
    return {"apid": apid, "field": field, "unit": fdef.unit if fdef else None,
            "alarm_low": fdef.alarm_low if fdef else None, "alarm_high": fdef.alarm_high if fdef else None,
            "points": [{"t": datetime.fromtimestamp(t, tz=timezone.utc).isoformat(), "v": v} for t, v in thinned],
            "total_rows": len(rows)}
```
(add `from datetime import timezone` to the import line.) In `telemetry.py` (core) confirm `_NUMERIC` is module-level — it is (`_NUMERIC = {...}` dict); importing a private name is acceptable here, but rename it to `NUMERIC_TYPES` in `core/telemetry.py` with `_NUMERIC = NUMERIC_TYPES` kept as an alias, and import `NUMERIC_TYPES`.

`app.py`: `from cubesat_gs.web.routes import feed as feed_routes, telemetry as telemetry_routes` and `app.include_router(feed_routes.router, prefix="/api")`, `app.include_router(telemetry_routes.router, prefix="/api")`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_feed_telemetry.py -q -W error` then full suite.
Expected: 4 passed; suite green.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web cubesat_gs/core/telemetry.py cubesat_gs/tests/test_web_feed_telemetry.py
git commit -m "Add packet feed paging and telemetry history with LTTB downsampling"
```

---

### Task 7: Commands and frequency routes

**Files:**
- Create: `cubesat_gs/web/routes/commands.py`, `cubesat_gs/web/routes/frequency.py`
- Modify: `cubesat_gs/web/app.py`, `cubesat_gs/core/telecommand.py` (publish `CommandStarted`)
- Test: `cubesat_gs/tests/test_web_commands.py`, `cubesat_gs/tests/test_web_frequency.py`

**Interfaces:**
- Produces: `GET /api/commands` → `[CommandDefOut]`; `GET /api/commands/history?limit&before` → `{"items": [CommandRecordOut], "next_before": iso|null}` (in-memory `telecommand.history` newest-first merged with `storage.query("commands")` beyond it); `POST /api/commands/{name}` body `SendCommandIn` → `CommandRecordOut` (403 when refused, with the record in `detail` as JSON string); `POST /api/commands/raw` body `SendRawIn` → `CommandRecordOut` (403 unless `confirm`); `GET /api/frequency` → `FrequencyOut`; `PUT /api/frequency` body `FrequencyIn` → `FrequencyOut`.
- `TelecommandManager._execute` publishes `CommandStarted(name, raw_hex)` right before `send_tx` on the first attempt (so the hub can broadcast `pending: true`).

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_web_commands.py`:
```python
import asyncio

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until


async def test_registry_lists_ping(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/commands")
    assert r.status_code == 200
    ping = next(c for c in r.json() if c["name"] == "PING")
    assert ping["apid"] == 100 and ping["response_apid"] == 101 and ping["critical"] is False
    assert ping["payload_hex"] == "50494E47" and ping["payload_text"] == "PING"


async def test_send_ping_ok_and_history(web_stack):
    station, sim, client = web_stack
    r = await client.post("/api/commands/PING", json={"confirm": False})
    assert r.status_code == 200
    rec = r.json()
    assert rec["status"] == "responded" and rec["response_hex"].startswith("0065") and rec["pending"] is False
    await asyncio.sleep(0.05)
    h = await client.get("/api/commands/history")
    assert h.json()["items"][0]["name"] == "PING" and h.json()["items"][0]["status"] == "responded"
    r = await client.post("/api/commands/NOPE", json={})
    assert r.status_code == 404 and r.json()["error"] == "unknown_command"


async def test_critical_and_raw_require_confirm(web_stack, tmp_path):
    station, sim, client = web_stack
    from cubesat_gs.core.telecommand import CommandDef
    station.telecommand.commands["REBOOT"] = CommandDef("REBOOT", "reboot", 100, b"\x01\xff", None, 1.0, True)
    r = await client.post("/api/commands/REBOOT", json={"confirm": False})
    assert r.status_code == 403 and r.json()["error"] == "confirm_required"
    r = await client.post("/api/commands/REBOOT", json={"confirm": True})
    assert r.status_code == 200 and r.json()["status"] == "acked"
    r = await client.post("/api/commands/raw", json={"hex": "DEADBEEF"})
    assert r.status_code == 403
    r = await client.post("/api/commands/raw", json={"hex": "XYZ", "confirm": True})
    assert r.status_code == 422
    r = await client.post("/api/commands/raw", json={"hex": "DE AD BE EF", "confirm": True})
    assert r.status_code == 200 and r.json()["name"] == "RAW" and sim.received_tx[-1] == b"\xde\xad\xbe\xef"


async def test_busy_wrong_mode_disconnected(web_stack):
    station, sim, client = web_stack
    sim.silent = True
    t = asyncio.create_task(client.post("/api/commands/PING", json={}))
    await wait_until(lambda: station.telecommand.pending is not None)
    r = await client.post("/api/commands/PING", json={})
    assert r.status_code == 409 and r.json()["error"] == "command_busy"
    sim.silent = False
    first = await t
    assert first.status_code == 200 and first.json()["status"] in ("timeout", "failed")
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    r = await client.post("/api/commands/PING", json={})
    assert r.status_code == 400 and r.json()["error"] == "wrong_mode"
    await station.freq.set_mode(Mode.TCTM)
    await station.serial.stop()
    r = await client.post("/api/commands/PING", json={})
    assert r.status_code == 503
    await station.serial.start()
    await wait_until(lambda: station.serial.connected)


async def test_command_started_event_is_published(web_stack):
    from cubesat_gs.core.events import CommandStarted
    station, sim, client = web_stack
    got = []
    station.bus.subscribe(CommandStarted, lambda e: _push(got, e))
    await client.post("/api/commands/PING", json={})
    await wait_until(lambda: len(got) == 1)
    assert got[0].name == "PING" and got[0].raw_hex.endswith("50494E47")


async def _push(lst, e):
    lst.append(e)
```

`cubesat_gs/tests/test_web_frequency.py`:
```python
async def test_get_and_put_frequency(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/frequency")
    assert r.json()["mode"] == "tctm" and r.json()["presets"] == {"tctm": 435.5, "beacon": 437.25}
    r = await client.put("/api/frequency", json={"mode": "beacon_listen"})
    assert r.status_code == 200 and r.json()["mhz"] == 437.25 and sim.freq == 437.25
    assert r.json()["history"][-1]["mode"] == "beacon_listen"
    r = await client.put("/api/frequency", json={"mode": "custom"})
    assert r.status_code == 422
    r = await client.put("/api/frequency", json={"mode": "custom", "mhz": 436.0})
    assert r.status_code == 200 and sim.freq == 436.0
    sim.silent = True
    r = await client.put("/api/frequency", json={"mode": "tctm"})
    assert r.status_code == 504 and r.json()["error"] == "modem_timeout"
    sim.silent = False
    r = await client.put("/api/frequency", json={"mode": "tctm"})
    assert r.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_commands.py cubesat_gs/tests/test_web_frequency.py -q`
Expected: FAIL (404s — routes missing)

- [ ] **Step 3: Implement**

`core/telecommand.py`: import `CommandStarted`; in `_execute`, inside the attempt loop before `await self._serial.send_tx(raw)`, add `if attempt == 1: self._bus.publish(CommandStarted(name=name, raw_hex=raw.hex().upper()))`.

`cubesat_gs/web/routes/commands.py`:
```python
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import CommandRecordOut, SendCommandIn, SendRawIn

router = APIRouter()


def _def_out(c) -> dict:
    try:
        text = c.payload.decode("utf-8")
        text = text if text.isprintable() else None
    except UnicodeDecodeError:
        text = None
    return {"name": c.name, "description": c.description, "apid": c.apid, "payload_hex": c.payload.hex().upper(),
            "payload_text": text, "response_apid": c.response_apid, "timeout": c.timeout, "critical": c.critical}


def _rec_out(rec) -> dict:
    d = rec.as_dict()
    d["pending"] = False
    return d


@router.get("/commands")
async def list_commands(station: GroundStation = Depends(get_station)):
    return [_def_out(c) for c in station.telecommand.commands.values()]


@router.get("/commands/history")
async def command_history(station: GroundStation = Depends(get_station),
                          limit: int = Query(50, ge=1, le=500), before: datetime | None = None):
    mem = [_rec_out(r) for r in reversed(station.telecommand.history)]
    if before is not None:
        mem = [m for m in mem if datetime.fromisoformat(m["ts"]) < before]
    items = mem[:limit]
    if len(items) < limit:
        oldest_mem = datetime.fromisoformat(mem[-1]["ts"]) if mem else before
        rows = await station.storage.query("commands", end=oldest_mem, limit=limit - len(items))
        seen = {(m["ts"], m["name"]) for m in items}
        for r in rows:
            key = (r["timestamp"], r["command_name"])
            if key in seen:
                continue
            items.append({"ts": r["timestamp"], "name": r["command_name"], "raw_hex": r["raw_hex_sent"],
                          "status": r["status"], "response_hex": r.get("response_hex"),
                          "latency_ms": r.get("latency_ms"), "attempts": r.get("attempts", 0),
                          "error": None, "pending": False})
    next_before = items[-1]["ts"] if len(items) == limit else None
    return {"items": items, "next_before": next_before}


def _guard_serial(station: GroundStation) -> None:
    if not station.serial.connected:
        raise ApiError(503, "serial_disconnected", "modem is not connected")


@router.post("/commands/raw", response_model=CommandRecordOut)
async def send_raw(body: SendRawIn, station: GroundStation = Depends(get_station)):
    if not body.confirm:
        raise ApiError(403, "confirm_required", "raw commands require confirm=true")
    _guard_serial(station)
    return _rec_out(await station.telecommand.send_raw(body.hex))


@router.post("/commands/{name}", response_model=CommandRecordOut)
async def send_command(name: str, body: SendCommandIn, station: GroundStation = Depends(get_station)):
    cdef = station.telecommand.commands.get(name)
    if cdef is None:
        raise ApiError(404, "unknown_command", name)
    if cdef.critical and not body.confirm:
        raise ApiError(403, "confirm_required", f"{name} is critical; send confirm=true")
    _guard_serial(station)
    payload = bytes.fromhex(body.payload_hex.replace(" ", "")) if body.payload_hex else None
    rec = await station.telecommand.send_command(name, confirm=body.confirm, payload_override=payload)
    return _rec_out(rec)
```
Note the route order: `/commands/raw` must be declared before `/commands/{name}`.

`cubesat_gs/web/routes/frequency.py`:
```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import FrequencyIn, FrequencyOut

router = APIRouter()


def _out(station: GroundStation) -> dict:
    f = station.freq
    return {"mode": f.mode.value, "mhz": f.mhz,
            "presets": {"tctm": station.cfg.frequencies.tctm, "beacon": station.cfg.frequencies.beacon},
            "history": [{"ts": h.ts.isoformat(), "mode": h.mode.value, "mhz": h.mhz} for h in list(f.history)[-20:]]}


@router.get("/frequency", response_model=FrequencyOut)
async def get_frequency(station: GroundStation = Depends(get_station)):
    return _out(station)


@router.put("/frequency", response_model=FrequencyOut)
async def put_frequency(body: FrequencyIn, station: GroundStation = Depends(get_station)):
    if body.mode == "custom" and body.mhz is None:
        raise ApiError(422, "invalid_value", "custom mode requires mhz")
    await station.freq.set_mode(Mode(body.mode), mhz=body.mhz)
    return _out(station)
```

`app.py`: include both routers under `/api`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_commands.py cubesat_gs/tests/test_web_frequency.py -q -W error` then full suite.
Expected: 6 passed; suite green (Phase 1 `test_telecommand.py` still green — `CommandStarted` is just an extra publish).

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web cubesat_gs/core/telecommand.py cubesat_gs/tests/test_web_commands.py cubesat_gs/tests/test_web_frequency.py
git commit -m "Add command and frequency API routes"
```

---

### Task 8: Passes routes

**Files:**
- Create: `cubesat_gs/web/routes/passes.py`
- Modify: `cubesat_gs/web/app.py`
- Test: `cubesat_gs/tests/test_web_passes.py`

**Interfaces:**
- Produces: `GET /api/passes?days` → `PassesOut`; `GET /api/passes/current` → `PassStateOut | null`; `GET /api/passes/history?limit` → `{"items": [rows]}`; `GET /api/passes/{id}/track?step_s` → `[TrackPoint]` (404 if unknown id); `POST /api/passes/refresh-tle` → `{"line1", "line2"}` (400 `no_tle_source`, 502 `tle_fetch_failed`).

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_web_passes.py`:
```python
from datetime import datetime, timezone

import httpx

from cubesat_gs.tests.test_pass_predictor import L1, L2, NOW


async def test_disabled_state(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/passes")
    assert r.json() == {"enabled": False, "reason": "TLE not configured", "passes": []}
    assert (await client.get("/api/passes/current")).json() is None
    assert (await client.get("/api/passes/nope/track")).status_code == 404
    r = await client.post("/api/passes/refresh-tle")
    assert r.status_code == 400 and r.json()["error"] == "no_tle_source"


async def test_enabled_passes_and_track(web_stack):
    station, sim, client = web_stack
    station.passes._clock = lambda: NOW
    await station.passes.set_tle(L1, L2)
    r = await client.get("/api/passes", params={"days": 1})
    body = r.json()
    assert body["enabled"] and len(body["passes"]) == 4
    p = body["passes"][0]
    assert p["aos"].startswith("2024-01-08T00:08:54") and abs(p["max_el"] - 21.3) < 0.2
    r = await client.get(f"/api/passes/{p['id']}/track", params={"step_s": 30})
    pts = r.json()
    assert 9 <= len(pts) <= 13 and set(pts[0]) == {"t", "az", "el", "range_km", "doppler_hz"}
    station.passes._clock = lambda: datetime.fromisoformat(p["tca"])
    cur = (await client.get("/api/passes/current")).json()
    assert cur["pass_id"] == p["id"] and abs(cur["el"] - p["max_el"]) < 0.3
    st = (await client.get("/api/status")).json()
    assert st["passes"]["current"]["pass_id"] == p["id"]


async def test_refresh_tle_via_api(web_stack, monkeypatch):
    station, sim, client = web_stack
    station.passes._tle_source = "https://tle.example/x.txt"
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, text=f"ISS\n{L1}\n{L2}\n")

    station.passes._http_factory = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    r = await client.post("/api/passes/refresh-tle")
    assert r.status_code == 502 and r.json()["error"] == "tle_fetch_failed"
    r = await client.post("/api/passes/refresh-tle")
    assert r.status_code == 200 and r.json() == {"line1": L1, "line2": L2}
    assert station.passes.enabled


async def test_pass_history_empty(web_stack):
    station, sim, client = web_stack
    assert (await client.get("/api/passes/history")).json() == {"items": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_passes.py -q`
Expected: FAIL (404)

- [ ] **Step 3: Implement `routes/passes.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.pass_predictor import TLEError, pass_to_dict, state_to_dict
from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station

router = APIRouter()


@router.get("/passes")
async def list_passes(station: GroundStation = Depends(get_station), days: int | None = Query(None, ge=1, le=14)):
    pp = station.passes
    passes = await pp.upcoming(days) if pp.enabled else []
    return {"enabled": pp.enabled, "reason": pp.reason, "passes": [pass_to_dict(p) for p in passes]}


@router.get("/passes/current")
async def current_pass(station: GroundStation = Depends(get_station)):
    return state_to_dict(station.passes.current())


@router.get("/passes/history")
async def pass_history(station: GroundStation = Depends(get_station), limit: int = Query(50, ge=1, le=500)):
    return {"items": await station.storage.query("passes", limit=limit)}


@router.post("/passes/refresh-tle")
async def refresh_tle(station: GroundStation = Depends(get_station)):
    pp = station.passes
    if not pp._tle_source:
        raise ApiError(400, "no_tle_source", "satellite.tle_source is not configured")
    try:
        l1, l2 = await pp.refresh_tle()
    except TLEError as e:
        raise ApiError(502, "tle_fetch_failed", str(e)) from e
    return {"line1": l1, "line2": l2}


@router.get("/passes/{pass_id}/track")
async def pass_track(pass_id: str, station: GroundStation = Depends(get_station),
                     step_s: int = Query(10, ge=1, le=120)):
    pts = await station.passes.track(pass_id, step_s=step_s)
    if not pts:
        raise ApiError(404, "unknown_pass", pass_id)
    return [{"t": t.isoformat(), "az": az, "el": el, "range_km": rng, "doppler_hz": dop} for t, az, el, rng, dop in pts]
```
Add a public property to `PassPredictor`: `tle_source -> str` (returns `self._tle_source`) and use it in the route instead of the private attribute; likewise expose `set_tle_source(url: str)` for Task 9. Include the router in `app.py`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_passes.py -q -W error` then full suite. Expected: 4 passed; green.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web cubesat_gs/core/pass_predictor.py cubesat_gs/tests/test_web_passes.py
git commit -m "Add pass prediction API routes"
```

---
### Task 9: Config routes (ruamel round-trip, live apply), serial ports, DB stats, export

**Files:**
- Create: `cubesat_gs/web/config_writer.py`, `cubesat_gs/web/routes/config.py`, `cubesat_gs/web/routes/export.py`
- Modify: `cubesat_gs/web/app.py`, `cubesat_gs/core/frequency_manager.py` (presets setter), `cubesat_gs/core/pass_predictor.py` (`set_tle_source`)
- Test: `cubesat_gs/tests/test_web_config.py`, `cubesat_gs/tests/test_web_export.py`

**Interfaces:**
- Produces: `config_writer.WRITABLE = {"serial": {"port","baudrate","reconnect_interval"}, "frequencies": {"tctm","beacon"}, "station": {"name","latitude","longitude","altitude"}, "satellite": {"name","tle_line1","tle_line2","tle_source"}, "passes": {"min_elevation","prediction_days"}, "commands": {"default_timeout","max_retries","retry_backoff"}}`; `APPLIES: dict[str, "live"|"restart"]` keyed `section.key` (`serial.port` live (reconnect), `serial.baudrate`/`reconnect_interval` restart, `frequencies.*` live, `station.*` live, `satellite.*` live, `passes.*` live, `commands.*` restart); `public_config(cfg) -> dict` (dataclasses → dict, `database.mongo_uri` omitted, `base_dir` omitted); `validate_merge(path, sections) -> dict` (loads YAML via ruamel round-trip, merges, builds `GSConfig` via `config._build` + `_validate` to validate, returns the merged plain dict); `write_config(path, sections) -> None` (temp file + `os.replace`); `apply_live(station, sections) -> list[str]` (returns applied `section.key` list).
- Routes: `GET /api/config` → `ConfigOut`; `PUT /api/config` body `ConfigIn` → `ConfigPutOut`; `GET /api/config/serial-ports` → `[SerialPortOut]`; `GET /api/db/stats` → `{counts, health}`; `POST /api/export` → file download.
- `FrequencyManager.set_presets(tctm, beacon)`; `PassPredictor.set_tle_source(url)`.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_web_config.py`:
```python
import shutil
from pathlib import Path

import pytest

from cubesat_gs.tests.conftest import wait_until

PKG = Path(__file__).resolve().parents[1]


@pytest.fixture
async def cfg_stack(web_stack, tmp_path):
    station, sim, client = web_stack
    cfg_path = tmp_path / "gs_config.yaml"
    shutil.copy(PKG / "config" / "gs_config.yaml", cfg_path)
    station.cfg.base_dir = cfg_path.parent
    station.cfg.config_path = cfg_path
    return station, sim, client, cfg_path


async def test_get_config_hides_secrets_and_marks_writable(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    r = await client.get("/api/config")
    body = r.json()
    assert "mongo_uri" not in body["config"]["database"]
    assert body["config"]["frequencies"] == {"tctm": 435.5, "beacon": 437.25}
    assert set(body["writable"]) == {"serial", "frequencies", "station", "satellite", "passes", "commands"}
    assert body["applies"]["frequencies.tctm"] == "live" and body["applies"]["serial.baudrate"] == "restart"


async def test_put_config_round_trips_and_applies_live(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    original = cfg_path.read_text(encoding="utf-8")
    assert "# MONGO_URI is read from the environment" in original
    r = await client.put("/api/config", json={"sections": {
        "frequencies": {"beacon": 437.3}, "station": {"latitude": -33.0},
        "passes": {"min_elevation": 15}, "commands": {"max_retries": 5}}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["config"]["frequencies"]["beacon"] == 437.3
    assert set(body["applied_live"]) == {"frequencies.beacon", "station.latitude", "passes.min_elevation"}
    assert body["restart_required"] is True
    text = cfg_path.read_text(encoding="utf-8")
    assert "# MONGO_URI is read from the environment" in text and "beacon: 437.3" in text and "max_retries: 5" in text
    assert station.cfg.frequencies.beacon == 437.3 and station.passes._min_el == 15
    r = await client.put("/api/frequency", json={"mode": "beacon_listen"})
    assert r.json()["mhz"] == 437.3


async def test_put_config_rejects_bad_values_without_writing(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    before = cfg_path.read_text(encoding="utf-8")
    r = await client.put("/api/config", json={"sections": {"database": {"retention_days": 1}}})
    assert r.status_code == 422 and "database" in r.json()["detail"]
    r = await client.put("/api/config", json={"sections": {"serial": {"bogus": 1}}})
    assert r.status_code == 422
    r = await client.put("/api/config", json={"sections": {"passes": {"min_elevation": "high"}}})
    assert r.status_code == 422
    assert cfg_path.read_text(encoding="utf-8") == before


async def test_put_tle_enables_predictor(cfg_stack):
    from cubesat_gs.tests.test_pass_predictor import L1, L2
    station, sim, client, cfg_path = cfg_stack
    r = await client.put("/api/config", json={"sections": {"satellite": {"tle_line1": L1, "tle_line2": L2}}})
    assert r.status_code == 200 and station.passes.enabled
    r = await client.put("/api/config", json={"sections": {"satellite": {"tle_line1": "junk", "tle_line2": "junk"}}})
    assert r.status_code == 422 and r.json()["error"] == "invalid_tle" and station.passes.enabled
    assert L1 in cfg_path.read_text(encoding="utf-8")


async def test_serial_port_change_reconnects(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    r = await client.put("/api/config", json={"sections": {"serial": {"port": "sim://again"}}})
    assert r.status_code == 200 and "serial.port" in r.json()["applied_live"]
    await wait_until(lambda: station.serial.connected and station.serial.port == "sim://again")


async def test_serial_ports_and_db_stats(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    r = await client.get("/api/config/serial-ports")
    assert r.status_code == 200 and isinstance(r.json(), list)
    r = await client.get("/api/db/stats")
    assert set(r.json()["counts"]) >= {"raw_packets", "passes"} and r.json()["health"]["mongo"] == "disabled"
```

`cubesat_gs/tests/test_web_export.py`:
```python
import asyncio

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.tests.conftest import wait_until


async def test_export_csv_download(web_stack):
    station, sim, client = web_stack
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    await wait_until(lambda: station.storage.session["packets_received"] >= 2)
    await asyncio.sleep(0.05)
    r = await client.post("/api/export", json={"collection": "raw_packets", "fmt": "csv"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'attachment; filename="raw_packets-' in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("id,timestamp,direction") and len(lines) >= 3
    r = await client.post("/api/export", json={"collection": "nope"})
    assert r.status_code == 422
    r = await client.post("/api/export", json={"collection": "alarms", "fmt": "json"})
    assert r.status_code == 200 and r.json() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_config.py cubesat_gs/tests/test_web_export.py -q`
Expected: FAIL (404 / AttributeError `config_path`)

- [ ] **Step 3: Implement**

`core/config.py`: add `config_path: Path = field(default_factory=lambda: DEFAULT_CONFIG_PATH)` to `GSConfig` and set `cfg.config_path = path.resolve()` in `load_config`.

`core/frequency_manager.py`: add
```python
    def set_presets(self, tctm: float, beacon: float) -> None:
        self._cfg.tctm, self._cfg.beacon = float(tctm), float(beacon)
```
`core/pass_predictor.py`: add `def set_tle_source(self, url: str) -> None: self._tle_source = (url or "").strip()`.

`cubesat_gs/web/config_writer.py`:
```python
"""Read/validate/write gs_config.yaml (comment-preserving) and apply changes live where safe."""
from __future__ import annotations

import dataclasses
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from cubesat_gs.core import config as cfgmod
from cubesat_gs.core.config import GSConfig
from cubesat_gs.core.pass_predictor import TLEError

log = logging.getLogger(__name__)

WRITABLE: dict[str, set[str]] = {
    "serial": {"port", "baudrate", "reconnect_interval"},
    "frequencies": {"tctm", "beacon"},
    "station": {"name", "latitude", "longitude", "altitude"},
    "satellite": {"name", "tle_line1", "tle_line2", "tle_source"},
    "passes": {"min_elevation", "prediction_days"},
    "commands": {"default_timeout", "max_retries", "retry_backoff"},
}
APPLIES: dict[str, str] = {
    "serial.port": "live", "serial.baudrate": "restart", "serial.reconnect_interval": "restart",
    "frequencies.tctm": "live", "frequencies.beacon": "live",
    "station.name": "live", "station.latitude": "live", "station.longitude": "live", "station.altitude": "live",
    "satellite.name": "live", "satellite.tle_line1": "live", "satellite.tle_line2": "live", "satellite.tle_source": "live",
    "passes.min_elevation": "live", "passes.prediction_days": "live",
    "commands.default_timeout": "restart", "commands.max_retries": "restart", "commands.retry_backoff": "restart",
}
_HIDDEN = {("database", "mongo_uri")}


def public_config(cfg: GSConfig) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in dataclasses.fields(cfg):
        if f.name in ("base_dir", "config_path"):
            continue
        section = dataclasses.asdict(getattr(cfg, f.name))
        for (sec, key) in _HIDDEN:
            if sec == f.name:
                section.pop(key, None)
        out[f.name] = section
    return out


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 120
    return y


def check_sections(sections: dict[str, dict[str, Any]]) -> None:
    for sec, values in sections.items():
        if sec not in WRITABLE:
            raise ValueError(f"section {sec!r} is read-only (edit gs_config.yaml and restart)")
        if not isinstance(values, dict):
            raise ValueError(f"section {sec!r} must be a mapping")
        for key in values:
            if key not in WRITABLE[sec]:
                raise ValueError(f"{sec}.{key} is not a writable setting")


def validate_merge(path: Path, sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return the merged plain dict after building a GSConfig from it (raises ValueError if invalid)."""
    check_sections(sections)
    y = _yaml()
    with open(path, "r", encoding="utf-8") as fh:
        doc = y.load(fh) or {}
    merged = _to_plain(doc)
    for sec, values in sections.items():
        merged.setdefault(sec, {}).update(values)
    cfg: GSConfig = cfgmod._build(GSConfig, merged, "config")
    cfgmod._validate(cfg)
    for sec in ("station", "passes", "frequencies", "serial"):
        for key, val in sections.get(sec, {}).items():
            if key in ("latitude", "longitude", "altitude", "min_elevation", "tctm", "beacon", "reconnect_interval"):
                float(val)  # raises ValueError/TypeError for non-numeric input
            if key == "prediction_days" and int(val) < 1:
                raise ValueError("passes.prediction_days must be >= 1")
    return merged


def _to_plain(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _to_plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_to_plain(v) for v in node]
    return node


def write_config(path: Path, sections: dict[str, dict[str, Any]]) -> None:
    y = _yaml()
    with open(path, "r", encoding="utf-8") as fh:
        doc = y.load(fh) or {}
    for sec, values in sections.items():
        if sec not in doc:
            doc[sec] = {}
        for key, val in values.items():
            doc[sec][key] = val
    fd, tmp = tempfile.mkstemp(prefix=".gs_config.", suffix=".yaml", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            y.dump(doc, fh)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    log.info("config: wrote %s (%s)", path, ", ".join(f"{s}.{k}" for s, v in sections.items() for k in v))


async def apply_live(station, sections: dict[str, dict[str, Any]]) -> list[str]:
    """Apply writable settings to the running station. Returns the list of `section.key` applied live."""
    applied: list[str] = []
    cfg = station.cfg
    for sec, values in sections.items():
        for key, val in values.items():
            if APPLIES.get(f"{sec}.{key}") != "live":
                setattr(getattr(cfg, sec), key, val)
                continue
            setattr(getattr(cfg, sec), key, val)
            applied.append(f"{sec}.{key}")
    if "frequencies" in sections:
        station.freq.set_presets(cfg.frequencies.tctm, cfg.frequencies.beacon)
    if "station" in sections:
        await station.passes.set_location(cfg.station.latitude, cfg.station.longitude, cfg.station.altitude)
    if "passes" in sections:
        await station.passes.set_min_elevation(cfg.passes.min_elevation)
        station.passes._days = int(cfg.passes.prediction_days)
    if "satellite" in sections:
        station.passes.set_tle_source(cfg.satellite.tle_source)
        if "tle_line1" in sections["satellite"] or "tle_line2" in sections["satellite"]:
            await station.passes.set_tle(cfg.satellite.tle_line1, cfg.satellite.tle_line2)  # raises TLEError
    if "serial" in sections and "port" in sections["serial"]:
        await station.serial.stop()
        await station.serial.start()
    return applied
```
Route order: `validate_merge` (structure/types) → `apply_live` (may raise `TLEError` → 422; `PassPredictor.set_tle` restores the previous TLE on failure, per Task 2) → `write_config`. So an invalid TLE is never written and the running predictor keeps working. Note `apply_live` mutates `station.cfg` before the write; if `write_config` then fails (disk), the response is a 500 and the in-memory config differs from the file until restart — acceptable and logged.

`cubesat_gs/web/routes/config.py`:
```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web import config_writer as cw
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import ConfigIn, ConfigOut, ConfigPutOut

router = APIRouter()


@router.get("/config", response_model=ConfigOut)
async def get_config(station: GroundStation = Depends(get_station)):
    return {"config": cw.public_config(station.cfg), "writable": sorted(cw.WRITABLE), "applies": cw.APPLIES}


@router.put("/config", response_model=ConfigPutOut)
async def put_config(body: ConfigIn, station: GroundStation = Depends(get_station)):
    path = station.cfg.config_path
    try:
        cw.validate_merge(path, body.sections)          # ValueError → 422 via deps mapping
    except (TypeError, KeyError) as e:
        raise ApiError(422, "invalid_value", str(e)) from e
    applied = await cw.apply_live(station, body.sections)  # TLEError → 422, nothing written
    cw.write_config(path, body.sections)
    restart = any(cw.APPLIES.get(f"{s}.{k}") == "restart" for s, v in body.sections.items() for k in v)
    return {"config": cw.public_config(station.cfg), "applied_live": applied, "restart_required": restart}


@router.get("/config/serial-ports")
async def serial_ports():
    from serial.tools import list_ports
    return [{"device": p.device, "description": p.description or "", "vid": p.vid, "pid": p.pid}
            for p in list_ports.comports()]


@router.get("/db/stats")
async def db_stats(station: GroundStation = Depends(get_station)):
    return {"counts": await station.storage.stats(), "health": await station.storage.health()}
```

`cubesat_gs/web/routes/export.py`:
```python
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse

from cubesat_gs.core.station import GroundStation
from cubesat_gs.storage.exporter import export
from cubesat_gs.storage.sqlite_backend import COLLECTIONS
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import ExportIn

router = APIRouter()
_MEDIA = {"csv": "text/csv", "json": "application/json"}


@router.post("/export")
async def export_collection(body: ExportIn, background: BackgroundTasks,
                            station: GroundStation = Depends(get_station)):
    if body.collection not in COLLECTIONS:
        raise ApiError(422, "invalid_value", f"unknown collection {body.collection!r}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = station.cfg.base_dir.parent / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{body.collection}-{stamp}.{body.fmt}"
    await export(station.storage, body.collection, path, fmt=body.fmt, start=body.start, end=body.end, apid=body.apid)
    background.add_task(path.unlink, missing_ok=True)
    return FileResponse(path, media_type=_MEDIA[body.fmt], filename=path.name)
```

`app.py`: include `config` and `export` routers under `/api`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_config.py cubesat_gs/tests/test_web_export.py -q -W error`, then the full suite.
Expected: 7 passed; suite green. If `FileResponse` + `background.add_task(unlink)` raises `PermissionError` on Windows because the file is still open when the task runs, wrap the unlink in a small helper that retries 3× with `asyncio.sleep(0.1)`.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web cubesat_gs/core cubesat_gs/tests/test_web_config.py cubesat_gs/tests/test_web_export.py
git commit -m "Add config editing, serial port listing, DB stats and export routes"
```

---

### Task 10: `main.py` in-loop uvicorn, static SPA serving

**Files:**
- Modify: `cubesat_gs/main.py`, `cubesat_gs/web/app.py`
- Create: `cubesat_gs/web/static/index.html` (placeholder until Task 15 replaces it with the build), `cubesat_gs/web/static/.gitkeep`
- Test: `cubesat_gs/tests/test_web_static.py`, `cubesat_gs/tests/test_main.py` (append)

**Interfaces:**
- Produces: `main.run(args)` starts uvicorn unless `args.no_web`; `--host/--port` override `web.host/port`; `web.serve(app, host, port) -> uvicorn.Server` helper in `app.py` (`config.install_signal_handlers` disabled); static SPA: `/assets/*` from `static_dir/assets`, any other non-`/api`, non-`/ws` path → `static_dir/index.html` if it exists, else 503 JSON `{"error":"dashboard_not_built"}`.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_web_static.py`:
```python
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from cubesat_gs.web.app import create_app


async def test_spa_fallback_and_assets(web_stack, tmp_path):
    station, sim, client = web_stack
    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    (static / "index.html").write_text("<!doctype html><title>GS</title>", encoding="utf-8")
    (static / "assets" / "app-abc123.js").write_text("console.log(1)", encoding="utf-8")
    app = create_app(station, static_dir=static)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for path in ("/", "/telemetry", "/passes/abc"):
            r = await c.get(path)
            assert r.status_code == 200 and "<title>GS</title>" in r.text, path
        r = await c.get("/assets/app-abc123.js")
        assert r.status_code == 200 and "javascript" in r.headers["content-type"]
        assert (await c.get("/assets/missing.js")).status_code == 404
        assert (await c.get("/api/nope")).status_code == 404


async def test_missing_bundle_is_503(web_stack):
    station, sim, client = web_stack  # fixture uses a non-existent static dir
    r = await client.get("/")
    assert r.status_code == 503 and r.json()["error"] == "dashboard_not_built"
```

Append to `cubesat_gs/tests/test_main.py`:
```python
async def test_sim_mode_serves_web(tmp_path, monkeypatch):
    import httpx
    import socket
    monkeypatch.delenv("MONGO_URI", raising=False)
    log_file = tmp_path / "gs.log"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    cfg = {
        "serial": {"port": "auto", "reconnect_interval": 0.2},
        "commands": {"registry": str(PKG / "config" / "commands.yaml")},
        "telemetry": {"definitions": str(PKG / "config" / "telemetry_defs.yaml")},
        "database": {"local_fallback_path": str(tmp_path / "gs.db")},
        "logging": {"level": "INFO", "file": str(log_file)},
        "web": {"host": "127.0.0.1", "port": port},
    }
    cfg_path = tmp_path / "gs_config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    args = argparse.Namespace(config=str(cfg_path), sim=True, sim_beacon_interval=1.0, sim_rssi=False,
                              log_level="INFO", no_web=False, host=None, port=None)
    task = asyncio.create_task(run(args))
    try:
        await _wait_for_line(log_file, "web: listening on")
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://127.0.0.1:{port}/api/status", timeout=5.0)
            assert r.status_code == 200 and r.json()["serial"]["connected"] in (True, False)
        signal.raise_signal(signal.SIGINT)
        rc = await asyncio.wait_for(task, 10.0)
    finally:
        if not task.done():
            task.cancel()
    assert rc == 0
    text = log_file.read_text(encoding="utf-8", errors="ignore")
    assert "web: stopped" in text and "ground station stopping" in text
```
Also update the existing `test_main.py` `argparse.Namespace(...)` constructions to include `no_web=True, host=None, port=None`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_web_static.py cubesat_gs/tests/test_main.py -q`
Expected: FAIL (503/404 mismatch; `run()` ignores `no_web`)

- [ ] **Step 3: Implement**

`app.py` additions (after routers, as the LAST routes):
```python
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

    static_dir = app.state.static_dir
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str, request: Request):
        if path.startswith("api/") or path == "ws":
            return JSONResponse({"error": "not_found", "detail": None}, status_code=404)
        index = app.state.static_dir / "index.html"
        candidate = app.state.static_dir / path if path else None
        if candidate and candidate.is_file() and candidate.resolve().is_relative_to(app.state.static_dir.resolve()):
            return FileResponse(candidate)
        if not index.is_file():
            return JSONResponse({"error": "dashboard_not_built",
                                 "detail": "run `npm run build` in cubesat_gs/web/frontend"}, status_code=503)
        return FileResponse(index)


def serve(app: FastAPI, host: str, port: int) -> uvicorn.Server:
    """A uvicorn server that runs in the caller's loop and never installs its own signal handlers."""
    config = uvicorn.Config(app, host=host, port=port, loop="none", log_config=None, access_log=False)
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # main.py owns SIGINT/SIGTERM
    return server
```
(`loop="none"` tells uvicorn not to create/configure a loop; check the installed uvicorn's `Config` accepts `loop="none"` — 0.30+ does. `assets` mount happens at create time, so the test that builds `static/assets` before `create_app` works; the `web_stack` fixture's nonexistent dir simply gets no mount.)

`main.py`:
- argparse: `--no-web` (store_true), `--host`, `--port` (int).
- in `run()`, after `station.start()`:
```python
        server = None
        server_task = None
        if not args.no_web:
            from cubesat_gs.web.app import create_app, serve
            app = create_app(station)
            host, port = args.host or cfg.web.host, args.port or cfg.web.port
            server = serve(app, host, port)
            server_task = asyncio.create_task(server.serve(), name="uvicorn")
            await _wait_started(server)
            log.info("web: listening on http://%s:%d", host, port)
```
with helper:
```python
async def _wait_started(server, timeout: float = 10.0) -> None:
    async def _w():
        while not server.started:
            await asyncio.sleep(0.05)
    await asyncio.wait_for(_w(), timeout)
```
- in `finally`, BEFORE `station.stop()`:
```python
        if server is not None and server_task is not None:
            server.should_exit = True
            try:
                await asyncio.wait_for(server_task, 10.0)
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                server_task.cancel()
            log.info("web: stopped")
```
`server` and `server_task` initialised to `None` before the `try`.

`cubesat_gs/web/static/index.html` placeholder (replaced by the real build in Task 15):
```html
<!doctype html><html><head><meta charset="utf-8"><title>CubeSat GS</title></head>
<body style="font-family:monospace;background:#0b0d10;color:#c9d1d9;padding:2rem">
<h1>CubeSat GS</h1><p>Dashboard bundle not built yet. Run <code>npm run build</code> in <code>cubesat_gs/web/frontend</code>.</p>
<p>API: <a href="/api/docs" style="color:#58a6ff">/api/docs</a></p></body></html>
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cubesat_gs/tests/test_web_static.py cubesat_gs/tests/test_main.py -q -W error` (3×), then full suite.
Expected: green. Manual check: `python cubesat_gs/main.py --sim --log-level INFO` → open `http://127.0.0.1:8080/api/docs` (Swagger) and `/api/status`; Ctrl+C stops with `web: stopped` then `ground station stopping`.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/main.py cubesat_gs/web cubesat_gs/tests/test_web_static.py cubesat_gs/tests/test_main.py
git commit -m "Serve the dashboard and API from main.py with in-loop uvicorn"
```

---
### Task 11: Frontend scaffold, design tokens, API client, WS client, store

**Files:**
- Create (all under `cubesat_gs/web/frontend/`): `package.json`, `vite.config.ts`, `tsconfig.json`, `tsconfig.node.json`, `tailwind.config.ts`, `postcss.config.js`, `index.html`, `components.json`, `src/main.tsx`, `src/App.tsx`, `src/index.css`, `src/lib/utils.ts`, `src/lib/format.ts`, `src/lib/time.ts`, `src/lib/lttb.ts`, `src/lib/polar.ts`, `src/api/types.ts`, `src/api/client.ts`, `src/api/ws.ts`, `src/store/gs.ts`, `src/components/{Panel,Value,AlarmBadge,StatusStrip,DisconnectedBanner,ConfirmDialog,Countdown,HexView}.tsx`, `src/components/ui/*` (shadcn), `src/views/*.tsx` (stubs rendering their title — filled in Tasks 12–14), `src/test/{store,lttb,polar,format}.test.ts`
- Test: Vitest (`npm test`), `npm run typecheck`, `npm run build`

**Design plan (from the `frontend-design` pass — the brief pins dark-only, four semantic colours, mono numbers, condensed labels; these are the specific choices within that):**
- Subject: a university CubeSat ground station in Santiago; operators watch a 6-minute pass at 2 a.m. The page's job is *situational awareness during a pass*. The one bold element is the **pass instrument** (polar track + countdown/progress) — it is the largest tile on Overview and the hero of Pass Tracker; everything else is quiet tabular data.
- Palette (cool graphite, not tinted black): `--bg #0E1116`, `--bg-raised #151A21`, `--line #262D37`, `--text #D6DCE4`, `--text-dim #8A94A3`; semantic `--nominal #43C97A`, `--warn #E0A526`, `--alarm #E5484D`, `--info #4C9BE8`, each also as `-dim` (14 % alpha). No gradients, no shadows, no rounded cards: panels are 1 px `--line` rectangles with 2 px radius.
- Type: Barlow Condensed 500/600 for nav, panel titles and table headers (12–13 px, letter-spacing 0.04em, sentence case — not tracked all-caps); JetBrains Mono 400/500 with `font-variant-numeric: tabular-nums` for every value, hex, timestamp, and the body of tables. Line length in text blocks ≤ 72 ch.
- Layout: 56 px left rail; content is a 12-column 4 px-rhythm grid; left-aligned everywhere; tables 28 px rows. Motion: only the pass progress bar and countdown tick; `prefers-reduced-motion` disables the polar dot easing. Focus rings: 2 px `--info`.
- Copy: sentence case, verbs first ("Send PING", "Save frequencies", "Refresh TLE"); empty states say what to do ("No passes — add a TLE in Settings"); errors say what happened and the fix.

**Interfaces:**
- Produces: `api/types.ts` mirroring `schemas.py` (every model, same field names); `api/client.ts` `api.get<T>(path, params?)`, `api.post<T>(path, body?)`, `api.put<T>(path, body)`, `ApiError {status, error, detail}`; `api/ws.ts` `connectWs(onMessage, onStatus)` returning `{close()}` with reconnect backoff 1→10 s and 20 s ping; `store/gs.ts` Zustand store `useGs` with state `{connected, status, feed, pausedBuffer, paused, telemetryLatest, series, alarmsActive, pendingCommand, commandHistory, nextPass, currentPass, toasts}` and `applyMessage(msg: WsMessage)`, `setPaused(bool)`, `flushPaused()`; `lib/lttb.ts` `lttb(points: [number, number][], n)`; `lib/polar.ts` `azElToXY(az, el, radius) -> {x,y}`; `lib/format.ts` `fmtNum(v, digits)`, `fmtHz(hz)`, `fmtMhz(mhz)`, `fmtDuration(s)`, `fmtBytes(hex)`; `lib/time.ts` `utc(iso)`, `local(iso)`, `age(iso, now)`, `countdown(iso, now)`.
- Vite dev proxies `/api` and `/ws` to `http://localhost:8080`; build output `../static` (`emptyOutDir: true`).

- [ ] **Step 1: Scaffold**

From `cubesat_gs/web/`:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom@6 zustand@4 @tanstack/react-query@5 @tanstack/react-virtual@3 recharts@2 clsx tailwind-merge class-variance-authority lucide-react sonner @fontsource/jetbrains-mono @fontsource/barlow-condensed
npm install -D tailwindcss@3 postcss autoprefixer @types/node vitest @testing-library/react @testing-library/jest-dom jsdom
npx tailwindcss init -p --ts
npx shadcn@latest init -d --yes
npx shadcn@latest add button dialog table tabs select input badge tooltip scroll-area separator checkbox textarea label --yes
```
If `shadcn init` refuses non-interactive use, create `components.json` by hand:
```json
{ "$schema": "https://ui.shadcn.com/schema.json", "style": "default", "rsc": false, "tsx": true,
  "tailwind": { "config": "tailwind.config.ts", "css": "src/index.css", "baseColor": "zinc", "cssVariables": true },
  "aliases": { "components": "@/components", "utils": "@/lib/utils" } }
```
and re-run `add`. If `add` still fails, copy the component sources from `https://ui.shadcn.com/docs/components/<name>` (they are MIT; each is one file under `src/components/ui/`).

`package.json` scripts:
```json
"scripts": { "dev": "vite", "build": "tsc -b && vite build", "typecheck": "tsc -b --noEmit", "test": "vitest run", "preview": "vite preview" }
```

`vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: { port: 5173, proxy: { "/api": "http://localhost:8080", "/ws": { target: "ws://localhost:8080", ws: true } } },
  build: { outDir: "../static", emptyOutDir: true, sourcemap: false },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"] },
});
```
(`/// <reference types="vitest" />` at the top of the file.) `src/test/setup.ts`: `import "@testing-library/jest-dom";`

`tsconfig.json` `compilerOptions`: `"strict": true, "baseUrl": ".", "paths": {"@/*": ["src/*"]}, "types": ["vitest/globals"]`.

`tailwind.config.ts`:
```ts
import type { Config } from "tailwindcss";
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "hsl(var(--bg))", raised: "hsl(var(--bg-raised))", line: "hsl(var(--line))",
        fg: "hsl(var(--text))", dim: "hsl(var(--text-dim))",
        nominal: "hsl(var(--nominal))", warn: "hsl(var(--warn))", alarm: "hsl(var(--alarm))", info: "hsl(var(--info))",
        // shadcn tokens
        background: "hsl(var(--bg))", foreground: "hsl(var(--text))", border: "hsl(var(--line))", input: "hsl(var(--line))",
        ring: "hsl(var(--info))", primary: { DEFAULT: "hsl(var(--info))", foreground: "hsl(var(--bg))" },
        secondary: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
        destructive: { DEFAULT: "hsl(var(--alarm))", foreground: "hsl(var(--text))" },
        muted: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text-dim))" },
        accent: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
        popover: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
        card: { DEFAULT: "hsl(var(--bg-raised))", foreground: "hsl(var(--text))" },
      },
      fontFamily: { label: ["'Barlow Condensed'", "sans-serif"], mono: ["'JetBrains Mono'", "monospace"] },
      borderRadius: { DEFAULT: "2px", sm: "2px", md: "2px", lg: "3px" },
      spacing: { 1: "4px", 2: "8px", 3: "12px", 4: "16px", 5: "20px", 6: "24px", 8: "32px" },
    },
  },
  plugins: [],
} satisfies Config;
```

`src/index.css`:
```css
@import "@fontsource/jetbrains-mono/400.css";
@import "@fontsource/jetbrains-mono/500.css";
@import "@fontsource/barlow-condensed/500.css";
@import "@fontsource/barlow-condensed/600.css";
@tailwind base; @tailwind components; @tailwind utilities;

:root {
  --bg: 214 22% 7%;  --bg-raised: 214 22% 10%;  --line: 214 18% 18%;
  --text: 214 18% 87%; --text-dim: 214 12% 59%;
  --nominal: 145 55% 52%; --warn: 41 76% 51%; --alarm: 358 75% 59%; --info: 210 77% 60%;
  color-scheme: dark;
}
html, body, #root { height: 100%; }
body { @apply bg-bg text-fg font-mono text-[13px] antialiased; font-variant-numeric: tabular-nums; }
.label { @apply font-label text-[13px] font-medium tracking-[0.04em] text-dim; }
.panel { @apply border border-line bg-bg rounded; }
.panel-title { @apply label border-b border-line px-3 h-8 flex items-center justify-between; }
.row { @apply h-7 border-b border-line/60; }
:focus-visible { outline: 2px solid hsl(var(--info)); outline-offset: 1px; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
```

`index.html`: `<title>CubeSat GS</title>`, `<meta name="viewport" ...>`, `<div id="root">`, `<script type="module" src="/src/main.tsx">`; `<html class="dark" lang="en">`.

- [ ] **Step 2: Write the failing unit tests**

`src/test/store.test.ts`:
```ts
import { describe, expect, it, beforeEach } from "vitest";
import { useGs } from "@/store/gs";
import type { WsMessage } from "@/api/types";

const snapshot: WsMessage = { type: "snapshot", ts: "2026-09-13T12:00:00Z", data: {
  status: { station: "UAI", serial: { connected: true, port: "COM3" }, frequency: { mode: "tctm", mhz: 435.5 },
    pending_command: null, storage: { mongo: "disabled" }, passes: { enabled: false, reason: "TLE not configured", next: null, current: null },
    session: { start_time: "2026-09-13T11:00:00Z", end_time: null, pass_id: null, packets_received: 0, packets_sent: 0, notes: "" } },
  feed: [], telemetry_latest: {}, pending_command: null, next_pass: null, current_pass: null, alarms_active: [] } };

const pkt = (i: number): WsMessage => ({ type: "packet", ts: "2026-09-13T12:00:01Z", data: {
  id: `1-${i}`, ts: "2026-09-13T12:00:01Z", direction: "rx", apid: 10, apid_name: "Beacon", seq: i, raw_hex: "00",
  rssi: null, snr: null, freq_mhz: 437.25, kind: "beacon", summary: "ok", fields: null } });

describe("gs store", () => {
  beforeEach(() => useGs.getState().reset());

  it("hydrates from snapshot", () => {
    useGs.getState().applyMessage(snapshot);
    expect(useGs.getState().status?.frequency.mhz).toBe(435.5);
    expect(useGs.getState().feed).toEqual([]);
  });

  it("appends packets, caps at 2000, and buffers while paused", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    for (let i = 0; i < 2100; i++) s.applyMessage(pkt(i));
    expect(useGs.getState().feed.length).toBe(2000);
    expect(useGs.getState().feed[0].id).toBe("1-2099");
    s.setPaused(true);
    s.applyMessage(pkt(5000));
    expect(useGs.getState().feed[0].id).toBe("1-2099");
    expect(useGs.getState().pausedBuffer.length).toBe(1);
    s.flushPaused();
    expect(useGs.getState().feed[0].id).toBe("1-5000");
    expect(useGs.getState().paused).toBe(false);
  });

  it("tracks telemetry latest, series and alarms", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    s.applyMessage({ type: "telemetry", ts: "t", data: { apid: 50, apid_name: "EPS", ts: "2026-09-13T12:00:02Z",
      fields: [{ name: "v_bat", value: 3.1, unit: "V", alarm: "low" }, { name: "tag", value: "x", unit: null, alarm: null }] } });
    expect(useGs.getState().telemetryLatest[50].fields[0].value).toBe(3.1);
    expect(useGs.getState().series["50:v_bat"]).toEqual([[Date.parse("2026-09-13T12:00:02Z"), 3.1]]);
    expect(useGs.getState().series["50:tag"]).toBeUndefined();
    expect(useGs.getState().alarmsActive).toEqual([{ apid: 50, field_name: "v_bat", value: 3.1, alarm: "low" }]);
    s.applyMessage({ type: "telemetry", ts: "t", data: { apid: 50, apid_name: "EPS", ts: "2026-09-13T12:00:03Z",
      fields: [{ name: "v_bat", value: 3.8, unit: "V", alarm: "nominal" }] } });
    expect(useGs.getState().alarmsActive).toEqual([]);
  });

  it("caps series at 5000 points", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    for (let i = 0; i < 5010; i++)
      s.applyMessage({ type: "telemetry", ts: "t", data: { apid: 1, apid_name: "A", ts: new Date(i * 1000).toISOString(),
        fields: [{ name: "x", value: i, unit: null, alarm: null }] } });
    expect(useGs.getState().series["1:x"].length).toBe(5000);
  });

  it("pending command lifecycle and history", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    s.applyMessage({ type: "command", ts: "t", data: { ts: "t", name: "PING", raw_hex: "10", status: "acked",
      response_hex: null, latency_ms: null, attempts: 0, error: null, pending: true } });
    expect(useGs.getState().pendingCommand?.name).toBe("PING");
    s.applyMessage({ type: "command", ts: "t", data: { ts: "t", name: "PING", raw_hex: "10", status: "responded",
      response_hex: "0065", latency_ms: 12, attempts: 1, error: null, pending: false } });
    expect(useGs.getState().pendingCommand).toBeNull();
    expect(useGs.getState().commandHistory[0].status).toBe("responded");
  });

  it("status and pass messages", () => {
    const s = useGs.getState();
    s.applyMessage(snapshot);
    s.applyMessage({ type: "status", ts: "t", data: { ...snapshot.data.status, frequency: { mode: "beacon_listen", mhz: 437.25 } } });
    expect(useGs.getState().status?.frequency.mode).toBe("beacon_listen");
    s.applyMessage({ type: "pass", ts: "t", data: { pass_id: "p1", t: "t", az: 1, el: 2, range_km: 3, doppler_hz: 4, progress: 0.5 } });
    expect(useGs.getState().currentPass?.pass_id).toBe("p1");
    s.applyMessage({ type: "pass", ts: "t", data: { event: "los", pass: { id: "p1", aos: "a", los: "b", tca: "c", max_el: 1, aos_az: 0, los_az: 0, duration_s: 1 } } });
    expect(useGs.getState().currentPass).toBeNull();
  });
});
```

`src/test/lttb.test.ts`:
```ts
import { expect, it } from "vitest";
import { lttb } from "@/lib/lttb";
it("lttb keeps endpoints and caps", () => {
  const pts: [number, number][] = Array.from({ length: 1000 }, (_, i) => [i, (i * 7919) % 101]);
  const out = lttb(pts, 50);
  expect(out.length).toBe(50); expect(out[0]).toEqual(pts[0]); expect(out[49]).toEqual(pts[999]);
  expect(lttb(pts, 5000)).toEqual(pts); expect(lttb([], 10)).toEqual([]);
});
```

`src/test/polar.test.ts`:
```ts
import { expect, it } from "vitest";
import { azElToXY } from "@/lib/polar";
it("maps zenith to centre and horizon north to top", () => {
  expect(azElToXY(0, 90, 100)).toEqual({ x: 0, y: 0 });
  const n = azElToXY(0, 0, 100); expect(n.x).toBeCloseTo(0); expect(n.y).toBeCloseTo(-100);
  const e = azElToXY(90, 0, 100); expect(e.x).toBeCloseTo(100); expect(e.y).toBeCloseTo(0);
  const half = azElToXY(180, 45, 100); expect(half.y).toBeCloseTo(50);
});
```

`src/test/format.test.ts`:
```ts
import { expect, it } from "vitest";
import { fmtDuration, fmtHz, fmtMhz, fmtNum } from "@/lib/format";
import { age, countdown } from "@/lib/time";
it("formats", () => {
  expect(fmtNum(3.14159, 2)).toBe("3.14"); expect(fmtNum(null, 2)).toBe("—");
  expect(fmtHz(4008.4)).toBe("+4.01 kHz"); expect(fmtHz(-120)).toBe("-120 Hz");
  expect(fmtMhz(437.25)).toBe("437.250 MHz"); expect(fmtDuration(318)).toBe("5m 18s");
  const now = Date.parse("2026-09-13T12:00:10Z");
  expect(age("2026-09-13T12:00:00Z", now)).toBe("10s"); expect(countdown("2026-09-13T13:01:05Z", now)).toBe("1h 00m 55s");
});
```

Run: `npm test` → FAIL (modules missing).

- [ ] **Step 3: Implement the infrastructure**

`src/lib/utils.ts`: the shadcn `cn()` (clsx + twMerge).

`src/lib/lttb.ts`: port of the Python `lttb` (same algorithm, `[number, number][]`).

`src/lib/polar.ts`:
```ts
/** Polar sky plot: zenith at centre, horizon at `radius`, north up, east right. */
export function azElToXY(az: number, el: number, radius: number): { x: number; y: number } {
  const r = ((90 - Math.max(0, Math.min(90, el))) / 90) * radius;
  const a = (az * Math.PI) / 180;
  return { x: r * Math.sin(a), y: -r * Math.cos(a) };
}
```

`src/lib/format.ts`:
```ts
export const fmtNum = (v: number | null | undefined, digits = 2) => (v == null || Number.isNaN(v) ? "—" : v.toFixed(digits));
export const fmtHz = (hz: number) => (Math.abs(hz) >= 1000 ? `${hz > 0 ? "+" : "-"}${(Math.abs(hz) / 1000).toFixed(2)} kHz` : `${hz > 0 ? "+" : ""}${Math.round(hz)} Hz`);
export const fmtMhz = (mhz: number) => `${mhz.toFixed(3)} MHz`;
export const fmtDuration = (s: number) => { const m = Math.floor(s / 60); const r = Math.round(s % 60); return m ? `${m}m ${String(r).padStart(2, "0")}s` : `${r}s`; };
export const fmtBytes = (hex: string) => `${Math.floor(hex.length / 2)} B`;
export const fmtValue = (v: unknown, digits = 3) => (typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(digits)) : v == null ? "—" : String(v));
```

`src/lib/time.ts`:
```ts
const pad = (n: number) => String(n).padStart(2, "0");
export const utc = (iso: string) => { const d = new Date(iso); return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`; };
export const utcTime = (iso: string) => utc(iso).slice(11);
export const local = (iso: string) => new Date(iso).toLocaleString();
export const age = (iso: string, now = Date.now()) => { const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${pad(s % 60)}s` : `${Math.floor(s / 3600)}h ${pad(Math.floor((s % 3600) / 60))}m`; };
export const countdown = (iso: string, now = Date.now()) => { const s = Math.max(0, Math.round((Date.parse(iso) - now) / 1000)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60; return h ? `${h}h ${pad(m)}m ${pad(r)}s` : m ? `${m}m ${pad(r)}s` : `${r}s`; };
```

`src/api/types.ts` — one interface per Pydantic model, same field names (`StatusOut`, `HealthOut`, `FeedEntry`, `TelemetryField`, `TelemetryLatest`, `TelemetryDefOut`, `TelemetryDefField`, `TelemetryHistoryOut`, `TelemetryPoint`, `CommandDefOut`, `CommandRecordOut`, `SendCommandIn`, `SendRawIn`, `FrequencyOut`, `FrequencyIn`, `PassOut`, `PassStateOut`, `PassesOut`, `TrackPoint`, `SerialPortOut`, `ConfigOut`, `ConfigIn`, `ConfigPutOut`, `ExportIn`, `AlarmOut`, `GapOut`, `SnapshotOut`, `ErrorOut`) plus:
```ts
export type Kind = "beacon" | "telemetry" | "command" | "malformed" | "unknown";
export type WsType = "snapshot" | "status" | "packet" | "telemetry" | "alarm" | "gap" | "command" | "pass" | "pong";
export type PassEdge = { event: "aos" | "los"; pass: PassOut };
export type WsMessage =
  | { type: "snapshot"; ts: string; data: SnapshotOut } | { type: "status"; ts: string; data: StatusOut }
  | { type: "packet"; ts: string; data: FeedEntry } | { type: "telemetry"; ts: string; data: TelemetryLatest }
  | { type: "alarm"; ts: string; data: AlarmOut } | { type: "gap"; ts: string; data: GapOut }
  | { type: "command"; ts: string; data: CommandRecordOut } | { type: "pass"; ts: string; data: PassStateOut | PassEdge }
  | { type: "pong"; ts: string; data: Record<string, never> };
```
Datetimes are `string` (ISO). `telemetry_latest` is `Record<string, TelemetryLatest>` (JSON keys are strings).

`src/api/client.ts`:
```ts
export class ApiError extends Error { constructor(public status: number, public error: string, public detail: string | null) { super(detail ?? error); } }
async function request<T>(method: string, path: string, body?: unknown, params?: Record<string, unknown>): Promise<T> {
  const url = new URL(path, window.location.origin);
  if (params) for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
  const r = await fetch(url.toString(), { method, headers: body ? { "content-type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) { let e = { error: "http_error", detail: r.statusText }; try { e = await r.json(); } catch { /* not json */ } throw new ApiError(r.status, e.error, e.detail ?? null); }
  const ct = r.headers.get("content-type") ?? "";
  return (ct.includes("json") ? await r.json() : await r.text()) as T;
}
export const api = {
  get: <T,>(path: string, params?: Record<string, unknown>) => request<T>("GET", path, undefined, params),
  post: <T,>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T,>(path: string, body: unknown) => request<T>("PUT", path, body),
};
export async function downloadExport(body: unknown, filename: string) {
  const r = await fetch("/api/export", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) { const e = await r.json(); throw new ApiError(r.status, e.error, e.detail); }
  const blob = await r.blob(); const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = r.headers.get("content-disposition")?.match(/filename="(.+)"/)?.[1] ?? filename; a.click(); URL.revokeObjectURL(a.href);
}
```

`src/api/ws.ts`:
```ts
import type { WsMessage } from "./types";
export function connectWs(onMessage: (m: WsMessage) => void, onStatus: (connected: boolean) => void) {
  let ws: WebSocket | null = null, closed = false, delay = 1000, ping: number | undefined;
  const url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
  const open = () => {
    ws = new WebSocket(url);
    ws.onopen = () => { delay = 1000; onStatus(true); ping = window.setInterval(() => ws?.send(JSON.stringify({ type: "ping" })), 20000); };
    ws.onmessage = (ev) => { try { onMessage(JSON.parse(ev.data)); } catch (e) { console.warn("ws: bad message", e); } };
    ws.onclose = () => { window.clearInterval(ping); onStatus(false); if (!closed) { setTimeout(open, delay); delay = Math.min(delay * 2, 10000); } };
    ws.onerror = () => ws?.close();
  };
  open();
  return { close() { closed = true; window.clearInterval(ping); ws?.close(); } };
}
```

`src/store/gs.ts`:
```ts
import { create } from "zustand";
import type { CommandRecordOut, FeedEntry, PassOut, PassStateOut, StatusOut, TelemetryLatest, WsMessage } from "@/api/types";

export type Alarm = { apid: number; field_name: string; value: unknown; alarm: "low" | "high" };
export type Toast = { id: number; kind: "alarm" | "info"; text: string };
const FEED_CAP = 2000, SERIES_CAP = 5000;

type State = {
  connected: boolean; status: StatusOut | null; feed: FeedEntry[]; paused: boolean; pausedBuffer: FeedEntry[];
  telemetryLatest: Record<number, TelemetryLatest>; series: Record<string, [number, number][]>; alarmsActive: Alarm[];
  pendingCommand: CommandRecordOut | null; commandHistory: CommandRecordOut[]; nextPass: PassOut | null; currentPass: PassStateOut | null;
  toasts: Toast[]; gaps: number;
  setConnected: (c: boolean) => void; applyMessage: (m: WsMessage) => void; setPaused: (p: boolean) => void; flushPaused: () => void;
  dismissToast: (id: number) => void; reset: () => void;
};
let toastId = 0;
const initial = { connected: false, status: null, feed: [], paused: false, pausedBuffer: [], telemetryLatest: {}, series: {},
  alarmsActive: [], pendingCommand: null, commandHistory: [], nextPass: null, currentPass: null, toasts: [], gaps: 0 };

function alarmsFrom(latest: Record<number, TelemetryLatest>): Alarm[] {
  return Object.values(latest).flatMap((t) => t.fields.filter((f) => f.alarm === "low" || f.alarm === "high")
    .map((f) => ({ apid: t.apid, field_name: f.name, value: f.value, alarm: f.alarm as "low" | "high" })));
}

export const useGs = create<State>((set, get) => ({
  ...initial,
  setConnected: (connected) => set({ connected }),
  setPaused: (paused) => set({ paused }),
  flushPaused: () => set((s) => ({ feed: [...s.pausedBuffer, ...s.feed].slice(0, FEED_CAP), pausedBuffer: [], paused: false })),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  reset: () => set({ ...initial }),
  applyMessage: (m) => {
    const s = get();
    switch (m.type) {
      case "snapshot": {
        const latest: Record<number, TelemetryLatest> = {};
        for (const [k, v] of Object.entries(m.data.telemetry_latest)) latest[Number(k)] = v;
        set({ status: m.data.status, feed: [...m.data.feed].reverse().slice(0, FEED_CAP), telemetryLatest: latest,
          alarmsActive: alarmsFrom(latest), pendingCommand: m.data.pending_command, nextPass: m.data.next_pass, currentPass: m.data.current_pass });
        return;
      }
      case "status": set({ status: m.data, nextPass: m.data.passes.next, currentPass: m.data.passes.current }); return;
      case "packet":
        if (s.paused) set({ pausedBuffer: [m.data, ...s.pausedBuffer].slice(0, FEED_CAP) });
        else set({ feed: [m.data, ...s.feed].slice(0, FEED_CAP) });
        return;
      case "telemetry": {
        const latest = { ...s.telemetryLatest, [m.data.apid]: m.data };
        const series = { ...s.series }; const t = Date.parse(m.data.ts);
        for (const f of m.data.fields) if (typeof f.value === "number") {
          const key = `${m.data.apid}:${f.name}`; const arr = series[key] ? [...series[key], [t, f.value] as [number, number]] : [[t, f.value] as [number, number]];
          series[key] = arr.length > SERIES_CAP ? arr.slice(arr.length - SERIES_CAP) : arr;
        }
        set({ telemetryLatest: latest, series, alarmsActive: alarmsFrom(latest) });
        return;
      }
      case "alarm": set({ toasts: [...s.toasts, { id: ++toastId, kind: "alarm", text: `${m.data.field_name} ${m.data.alarm_type}: ${m.data.value} (limit ${m.data.threshold})` }].slice(-5) }); return;
      case "gap": set({ gaps: s.gaps + m.data.missed }); return;
      case "command":
        if (m.data.pending) set({ pendingCommand: m.data });
        else set({ pendingCommand: null, commandHistory: [m.data, ...s.commandHistory].slice(0, 500) });
        return;
      case "pass":
        if ("event" in m.data) set({ currentPass: null, toasts: [...s.toasts, { id: ++toastId, kind: "info", text: m.data.event === "aos" ? `Pass started — max elevation ${m.data.pass.max_el.toFixed(0)}°` : "Pass ended" }].slice(-5) });
        else set({ currentPass: m.data });
        return;
      case "pong": return;
    }
  },
}));
```

`src/components/Panel.tsx` (`<Panel title actions>` = `.panel` + `.panel-title`), `Value.tsx` (`<Value v unit digits tone>` mono number + dim unit), `AlarmBadge.tsx` (dot + text in `nominal/warn/alarm` tone), `StatusStrip.tsx` (three segments from `useGs().status`: serial (dot nominal/alarm + port), frequency (mode + MHz + two small buttons "TCTM"/"Beacon" calling `api.put("/api/frequency")`), storage (ok/degraded/disabled)), `DisconnectedBanner.tsx` (full-width alarm-dim bar "Connection to the ground station lost — reconnecting…" when `!connected`), `ConfirmDialog.tsx` (shadcn Dialog with title, body, optional "I understand this is a critical command" checkbox, confirm button label passed in), `Countdown.tsx` (ticks every 1 s via `useEffect`, renders `countdown(iso)`), `HexView.tsx` (16 bytes per row, offset column).

`src/App.tsx`: `QueryClientProvider`, WS bootstrap (`useEffect` → `connectWs(applyMessage, setConnected)`), `BrowserRouter` with routes `/`, `/feed`, `/telemetry`, `/commands`, `/passes`, `/settings`; layout = 56 px rail (`NavLink`s with lucide icons `Gauge, Radio, Activity, Send, Orbit, Settings2`, badges for `alarmsActive.length` and `pendingCommand`), `DisconnectedBanner`, `StatusStrip`, `<Outlet/>`, `sonner` `<Toaster theme="dark">` fed from `toasts`.

Views (`src/views/*.tsx`): for this task each renders `<Panel title="…">Coming in Task N</Panel>` so the app compiles and routes work.

- [ ] **Step 4: Run tests, typecheck, build**

Run (in `cubesat_gs/web/frontend`): `npm test` → 4 files pass; `npm run typecheck` → clean; `npm run build` → writes `../static/index.html` + `assets/`. Then from the git root `python -m pytest cubesat_gs/tests/test_web_static.py -q` still passes (the fixture uses its own static dir). Do **not** commit `static/` yet (Task 15 commits the final build) — `git checkout -- cubesat_gs/web/static` if the build changed it… except `static/` currently holds the placeholder: revert to the placeholder after the build check.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web/frontend
git commit -m "Scaffold dashboard: Vite/React/Tailwind, design tokens, API + WS clients, store"
```

---

### Task 12: Overview and Live Feed views

**Files:**
- Create/replace: `src/views/Overview.tsx`, `src/views/LiveFeed.tsx`, `src/components/PassInstrument.tsx`, `src/components/Sparkline.tsx`, `src/components/FeedRow.tsx`
- Test: `src/test/feed.test.tsx` (Testing Library)

**Interfaces:**
- Consumes: `useGs`, `api`, `lib/*`, `PassOut/PassStateOut`.
- Produces: `PassInstrument` (used again by Pass Tracker): props `{next: PassOut|null, current: PassStateOut|null, track?: TrackPoint[], size?: number}` renders the polar SVG (rings 0/30/60°, N/E/S/W, track polyline, current dot) with a right column: countdown to AOS or progress bar with az/el/range/doppler.

- [ ] **Step 1: Write the failing test**

`src/test/feed.test.tsx`:
```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGs } from "@/store/gs";
import LiveFeed from "@/views/LiveFeed";

const entry = (i: number, kind = "beacon") => ({ id: `1-${i}`, ts: "2026-09-13T12:00:01Z", direction: "rx" as const, apid: kind === "command" ? 100 : 10,
  apid_name: "Beacon", seq: i, raw_hex: "000AC000", rssi: -97.5, snr: 8.2, freq_mhz: 437.25, kind: kind as never, summary: `msg ${i}`, fields: null });

describe("LiveFeed", () => {
  beforeEach(() => { useGs.getState().reset(); });
  it("renders entries, pauses and shows the new-count chip", () => {
    const s = useGs.getState();
    s.applyMessage({ type: "packet", ts: "t", data: entry(1) });
    render(<QueryClientProvider client={new QueryClient()}><LiveFeed /></QueryClientProvider>);
    expect(screen.getByText("msg 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /pause/i }));
    s.applyMessage({ type: "packet", ts: "t", data: entry(2) });
    expect(screen.queryByText("msg 2")).not.toBeInTheDocument();
    expect(screen.getByText(/1 new/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /resume/i }));
    expect(screen.getByText("msg 2")).toBeInTheDocument();
  });
  it("filters by direction", () => {
    const s = useGs.getState();
    s.applyMessage({ type: "packet", ts: "t", data: entry(1) });
    s.applyMessage({ type: "packet", ts: "t", data: { ...entry(2, "command"), direction: "tx" } });
    render(<QueryClientProvider client={new QueryClient()}><LiveFeed /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: /^tx$/i }));
    expect(screen.queryByText("msg 1")).not.toBeInTheDocument();
    expect(screen.getByText("msg 2")).toBeInTheDocument();
  });
});
```
(The virtualiser needs a fixed-height scroll container; in jsdom `@tanstack/react-virtual` measures 0 — pass `initialRect={{ width: 800, height: 600 }}` to `useVirtualizer` so rows render in tests.)

- [ ] **Step 2: Run** `npm test` → FAIL (view is a stub).

- [ ] **Step 3: Implement**

`Overview.tsx` — grid `grid-cols-12 gap-2`:
- Row 1 (full width): `PassInstrument` (col-span-7, size 260) — the hero; beside it (col-span-5) "Last packet" panel: kind badge, APID/name, summary, UTC time + age (ticks), RSSI/SNR when present.
- Row 2: "Today" panel (rx packets, tx packets, command success rate = responded/(responded+timeout+failed) over `commandHistory`, uptime from `status.session.start_time`, sequence gaps from `gaps`); "Packets per minute" panel with `Sparkline` (15 one-minute buckets computed from `feed` timestamps, SVG polyline, no axes, last value printed).
- Empty states: no feed → "No packets yet — switch to Beacon to listen on 437.250 MHz" with a button that calls `api.put("/api/frequency", {mode:"beacon_listen"})`; passes disabled → the instrument shows "Add a TLE in Settings to predict passes".

`PassInstrument.tsx`: SVG `viewBox="-110 -110 220 220"`; circles r=100/66.7/33.3 stroke `--line`; cardinal letters in `font-label`; track `<polyline>` from `azElToXY`; current dot r=4 fill `--info` with a `--info-dim` halo; if `current`: right column shows `progress` bar (`h-1 bg-info` width %), az/el/range/doppler as `Value`s; else if `next`: `Countdown` to `next.aos` big (text-2xl mono), max el, AOS az, LOS az, duration; else the empty-state sentence.

`LiveFeed.tsx`: toolbar — direction segmented buttons (All/RX/TX, `aria-pressed`), kind select, APID multi-select (checkbox list from `telemetryLatest` keys ∪ seen apids), time-range select (all / last 10 min / 1 h), Pause/Resume button (label toggles; when paused and `pausedBuffer.length` show chip "N new"); body — `useVirtualizer` over filtered rows (row 28 px; expanded row grows to fit `fields` table + `HexView`), click toggles expand; colour by kind: beacon `info`, telemetry `nominal`, command `warn`, malformed `alarm`, unknown `dim`; columns: time (UTC, tooltip local), dir, APID, seq, summary (truncate), RSSI, SNR; footer "Load older" → `useInfiniteQuery(['packets', filters])` on `/api/packets` with `before` cursor, prepending to a local `older` list rendered after the live rows.

- [ ] **Step 4: Run** `npm test`, `npm run typecheck`, `npm run build` (revert `static/` after). Start `python cubesat_gs/main.py --sim --sim-beacon-interval 3` + `npm run dev`, open http://localhost:5173, click "Beacon" in the status strip and verify packets stream, pause works, expand shows hex. Take a screenshot with the browser if available and check the panels line up on the 4 px grid.

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web/frontend
git commit -m "Dashboard: Overview with pass instrument and Live Feed"
```

---
### Task 13: Telemetry and Telecommand views

**Files:**
- Create/replace: `src/views/Telemetry.tsx`, `src/views/Telecommand.tsx`, `src/components/TimeSeries.tsx`, `src/components/CommandDialog.tsx`
- Test: `src/test/telecommand.test.tsx`

**Interfaces:**
- Consumes: `api`, `useGs`, `lttb`, `TelemetryHistoryOut`, `CommandDefOut`, `CommandRecordOut`, `ConfirmDialog`.
- Produces: `TimeSeries` props `{apid, field, unit, window: "1h"|"6h"|"24h"|{start,end}, live: [number,number][], alarmLow?, alarmHigh?}` — fetches `/api/telemetry/history` for the window (TanStack Query, `staleTime` 30 s), merges live points newer than the last history point, thins to ≤600 with `lttb`, renders a Recharts `LineChart` (mono tick labels, `ReferenceLine`s for thresholds in `--alarm`, line in `--info`, no grid fill, no animation).

- [ ] **Step 1: Write the failing test**

`src/test/telecommand.test.tsx`:
```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGs } from "@/store/gs";
import Telecommand from "@/views/Telecommand";

const defs = [
  { name: "PING", description: "Liveness check", apid: 100, payload_hex: "50494E47", payload_text: "PING", response_apid: 101, timeout: 10, critical: false },
  { name: "REBOOT", description: "Reboot OBC", apid: 100, payload_hex: "01FF", payload_text: null, response_apid: null, timeout: 5, critical: true },
];

function mockFetch(routes: Record<string, unknown>) {
  const calls: { url: string; body?: unknown }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    const url = String(input); const path = new URL(url, "http://x").pathname;
    calls.push({ url: path, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const hit = routes[path];
    return new Response(JSON.stringify(hit ?? { error: "not_found", detail: null }), { status: hit ? 200 : 404, headers: { "content-type": "application/json" } });
  }));
  return calls;
}

describe("Telecommand", () => {
  beforeEach(() => { useGs.getState().reset(); useGs.setState({ connected: true }); });

  it("lists commands and sends PING after confirmation", async () => {
    const calls = mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null },
      "/api/commands/PING": { ts: "t", name: "PING", raw_hex: "10", status: "responded", response_hex: "0065", latency_ms: 12.5, attempts: 1, error: null, pending: false } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    await screen.findByText("Liveness check");
    fireEvent.click(screen.getAllByRole("button", { name: /send/i })[0]);
    fireEvent.click(await screen.findByRole("button", { name: /send ping/i }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/commands/PING")).toBe(true));
    expect(calls.find((c) => c.url === "/api/commands/PING")?.body).toEqual({ confirm: false, payload_hex: null });
  });

  it("critical command requires the checkbox", async () => {
    mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    await screen.findByText("Reboot OBC");
    fireEvent.click(screen.getAllByRole("button", { name: /send/i })[1]);
    const confirm = await screen.findByRole("button", { name: /send reboot/i });
    expect(confirm).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox"));
    expect(confirm).toBeEnabled();
  });

  it("raw hex input validates", async () => {
    mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    const input = await screen.findByLabelText(/raw hex/i);
    fireEvent.change(input, { target: { value: "DEAD BEE" } });
    expect(screen.getByText(/odd number of hex digits/i)).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "DEAD BEEF" } });
    expect(screen.getByText("4 B")).toBeInTheDocument();
  });

  it("shows the pending indicator", () => {
    mockFetch({ "/api/commands": defs, "/api/commands/history": { items: [], next_before: null } });
    useGs.getState().applyMessage({ type: "command", ts: "t", data: { ts: new Date().toISOString(), name: "PING", raw_hex: "10", status: "acked", response_hex: null, latency_ms: null, attempts: 0, error: null, pending: true } });
    render(<QueryClientProvider client={new QueryClient()}><Telecommand /></QueryClientProvider>);
    expect(screen.getByText(/waiting for response/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run** `npm test` → FAIL.

- [ ] **Step 3: Implement**

`Telemetry.tsx`: left column (col-span-4) — one `Panel` per APID from `telemetryLatest` (title `${apid_name} · APID ${apid}` with age), rows `name | value unit | AlarmBadge`; numeric rows are buttons that select `{apid, field}`; right column (col-span-8) — `TimeSeries` for the selection with a window segmented control (1h / 6h / 24h / Custom → two `datetime-local` inputs), title `${field} (${unit})`, current value large, min/max/last of the plotted points. Empty state: "No telemetry decoded yet" / "Select a numeric field to chart it".

`TimeSeries.tsx` as in Interfaces; tooltip shows UTC time + value; y-axis auto with 8 % padding; if `alarmLow/High` provided, `ReferenceLine` dashed `--alarm` with label "low"/"high".

`Telecommand.tsx`:
- "Commands" panel: table (name, description, APID, response APID, timeout, critical badge, Send button). Send → `CommandDialog` (shows payload text/hex preview, an optional "Override payload (hex)" input, for critical: alarm-dim callout "This command is marked critical. It will be sent exactly once." + checkbox "I understand this is a critical command"; confirm button text "Send {name}", disabled until the checkbox for critical). On confirm `api.post("/api/commands/{name}", {confirm, payload_hex})`; success → toast "Sent {name} — {status}"; `ApiError` → toast with `detail`.
- "Pending" strip under the table: when `pendingCommand` — pulsing `--warn` dot, "Waiting for response to {name}", elapsed `age(ts)` ticking, attempts.
- "Raw command" panel: label "Raw hex" input (`aria-label="Raw hex"`), live validation (strip spaces; even length; hex digits only) with messages "Odd number of hex digits" / "Only 0–9 A–F allowed" / byte count `fmtBytes`; "Send raw" → `ConfirmDialog` (always requires the checkbox) → `api.post("/api/commands/raw", {hex, confirm: true})`.
- "History" panel: rows from `commandHistory` (live) merged with `useInfiniteQuery(['commands'])` on `/api/commands/history`; columns ts (UTC), name, status badge (responded nominal / acked info / timeout warn / failed, refused alarm), response (first 16 hex chars…), latency ms, attempts; "Load older".
- All mutation buttons disabled when `!connected` (tooltip "Ground station connection lost").

- [ ] **Step 4: Run** `npm test`, `npm run typecheck`, `npm run build` (revert `static/`). Dev-run with `--sim`: send PING and see `responded` with latency; send raw `DEADBEEF`; watch the pending strip; chart a field: with the shipped string-only definitions there is no numeric field — temporarily add the commented `apid_50` EPS block to `telemetry_defs.yaml` and inject a packet with `sim.inject_rx(...)`? Not needed: assert the empty-state copy renders; the chart path is covered by `TimeSeries` rendering `/api/telemetry/history` data seeded via the Task 6 test (visual check optional).

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web/frontend
git commit -m "Dashboard: Telemetry charts and Telecommand console"
```

---

### Task 14: Pass Tracker and Settings views

**Files:**
- Create/replace: `src/views/PassTracker.tsx`, `src/views/Settings.tsx`, `src/components/ConfigSection.tsx`
- Test: `src/test/settings.test.tsx`

**Interfaces:**
- Consumes: `PassInstrument`, `api`, `ConfigOut/ConfigIn/ConfigPutOut`, `SerialPortOut`, `downloadExport`.

- [ ] **Step 1: Write the failing test**

`src/test/settings.test.tsx`:
```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Settings from "@/views/Settings";

const config = { config: { serial: { port: "auto", baudrate: 115200, reconnect_interval: 5, timeouts: { tx: 5, freq: 2 } },
  frequencies: { tctm: 435.5, beacon: 437.25 }, station: { name: "UAI", latitude: -33.35, longitude: -70.67, altitude: 500 },
  satellite: { name: "UAI-SAT", tle_line1: "", tle_line2: "", tle_source: "" }, passes: { min_elevation: 10, prediction_days: 7 },
  commands: { registry: "config/commands.yaml", default_timeout: 10, max_retries: 3, retry_backoff: 1.5, history_size: 500 },
  database: { db_name: "cubesat_gs", retention_days: 365, local_fallback_path: "data/gs_offline.db" },
  logging: { level: "INFO", file: "logs/gs.log" }, web: { host: "0.0.0.0", port: 8080 },
  ccsds: { length_includes_crc: true, sequence_scope: "global" }, telemetry: { definitions: "config/telemetry_defs.yaml" } },
  writable: ["serial", "frequencies", "station", "satellite", "passes", "commands"],
  applies: { "frequencies.beacon": "live", "frequencies.tctm": "live", "serial.port": "live", "serial.baudrate": "restart", "commands.max_retries": "restart" } };

function mockFetch() {
  const calls: { url: string; method: string; body?: unknown }[] = [];
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    const path = new URL(String(input), "http://x").pathname; const method = init?.method ?? "GET";
    calls.push({ url: path, method, body: init?.body ? JSON.parse(String(init.body)) : undefined });
    const table: Record<string, unknown> = { "/api/config": method === "PUT" ? { config: config.config, applied_live: ["frequencies.beacon"], restart_required: false } : config,
      "/api/config/serial-ports": [{ device: "COM3", description: "CP210x", vid: 4292, pid: 60000 }],
      "/api/telemetry/definitions": { yaml: "apid_10:\n  name: Beacon\n", definitions: [] },
      "/api/db/stats": { counts: { raw_packets: 12, passes: 0 }, health: { mongo: "disabled", pending_sync: 0, sqlite_path: "x" } } };
    return new Response(JSON.stringify(table[path] ?? {}), { status: 200, headers: { "content-type": "application/json" } });
  }));
  return calls;
}

describe("Settings", () => {
  it("saves a frequencies change with only the edited key", async () => {
    const calls = mockFetch();
    render(<QueryClientProvider client={new QueryClient()}><Settings /></QueryClientProvider>);
    const beacon = await screen.findByLabelText(/beacon/i);
    fireEvent.change(beacon, { target: { value: "437.3" } });
    fireEvent.click(screen.getByRole("button", { name: /save frequencies/i }));
    await waitFor(() => expect(calls.some((c) => c.method === "PUT")).toBe(true));
    expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ sections: { frequencies: { beacon: 437.3 } } });
    expect(await screen.findByText(/applied live/i)).toBeInTheDocument();
  });
  it("marks read-only sections and shows db stats", async () => {
    mockFetch();
    render(<QueryClientProvider client={new QueryClient()}><Settings /></QueryClientProvider>);
    expect(await screen.findByText(/edit gs_config.yaml and restart/i)).toBeInTheDocument();
    expect(await screen.findByText("12")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run** `npm test` → FAIL.

- [ ] **Step 3: Implement**

`ConfigSection.tsx`: props `{name, title, values, fields: {key, label, type: "text"|"number"|"select"|"textarea", options?, step?}[], applies, onSave(section, changed)}`; keeps a local draft; each field shows a small badge "live" or "restart" from `applies[section.key]`; Save button label "Save {title}" enabled when the draft differs; sends only changed keys (numbers coerced with `Number()`); after save shows "Applied live" or "Saved — restart the ground station to apply" for 4 s.

`Settings.tsx` — `useQuery(['config'])`; sections in order:
1. Serial — port select (options: `auto` + `/api/config/serial-ports` devices with descriptions + the current value) and baudrate/reconnect (restart).
2. Frequencies — tctm, beacon (number, step 0.001, MHz) — labels "TC/TM (MHz)", "Beacon (MHz)".
3. Station — name, latitude, longitude, altitude (m).
4. Satellite — name, TLE (one textarea for two lines, split on newline into `tle_line1/2`; validation: exactly 2 non-empty lines starting with "1 " and "2 "), TLE URL, and a "Refresh TLE now" button → `POST /api/passes/refresh-tle` (toast result; disabled without URL).
5. Passes — min elevation (°), prediction days.
6. Commands — default timeout (s), max retries, backoff multiplier (all "restart").
7. Read-only: `database`, `logging`, `web`, `ccsds`, `telemetry` rendered greyed as key/value with the sentence "Edit gs_config.yaml and restart to change these."
8. Telemetry definitions — `<pre>` of `/api/telemetry/definitions` yaml (mono, scroll).
9. Database — counts table from `/api/db/stats` (plain numbers, e.g. "12"), health line, export form (collection select, format, optional start/end `datetime-local`, APID) with "Download CSV/JSON" → `downloadExport`.

`PassTracker.tsx`: `useQuery(['passes'])` on `/api/passes` (refetch 60 s). If `!enabled`: full-panel empty state "No passes — {reason}. Add a TLE in Settings." with a `Link` to `/settings`. Else: top row `PassInstrument` (col-span-7, size 320, `track` from `useQuery(['track', selectedId])` on `/api/passes/{id}/track`) + "Selected pass" panel (AOS/LOS UTC and local, TCA, duration, max el, AOS/LOS az); "Upcoming" table (rows selectable; the current pass highlighted `--info-dim`; countdown column ticking); "Pass history" table from `/api/passes/history` (aos, duration, max el, packets rx/tx, commands).

- [ ] **Step 4: Run** `npm test`, `npm run typecheck`, `npm run build` (revert `static/`); dev-run: paste the pinned ISS TLE from this plan into Settings → Satellite, save, open Pass Tracker: 4+ passes listed (the dates are 2024, so all are in the past for "now" — set `prediction_days` to 1 and expect an empty upcoming list but no error; to see a live pass, fetch a current TLE from `https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=tle` into the TLE URL field and Refresh).

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/web/frontend
git commit -m "Dashboard: Pass Tracker and Settings"
```

---

### Task 15: Production build, schema-sync guard, README, end-to-end run

**Files:**
- Create: `cubesat_gs/tests/test_schema_sync.py`, `cubesat_gs/web/static/**` (build output)
- Modify: `README.md`, `cubesat_gs/web/app.py` (`GET /api/schema.json`)
- Delete: the placeholder `cubesat_gs/web/static/index.html` (overwritten by the build)

- [ ] **Step 1: Schema endpoint + sync test**

`app.py`: add
```python
    @app.get("/api/schema.json", include_in_schema=False)
    async def schema_json():
        from cubesat_gs.web import schemas
        import inspect
        from pydantic import BaseModel
        return {name: cls.model_json_schema() for name, cls in inspect.getmembers(schemas, inspect.isclass)
                if issubclass(cls, BaseModel) and cls is not BaseModel}
```

`cubesat_gs/tests/test_schema_sync.py`:
```python
"""Guard: every Pydantic model + field name in web/schemas.py must appear in frontend/src/api/types.ts."""
import inspect
import re
from pathlib import Path

from pydantic import BaseModel

from cubesat_gs.web import schemas

TYPES_TS = Path(__file__).resolve().parents[1] / "web" / "frontend" / "src" / "api" / "types.ts"


def test_types_ts_mirrors_schemas():
    text = TYPES_TS.read_text(encoding="utf-8")
    missing = []
    for name, cls in inspect.getmembers(schemas, inspect.isclass):
        if not issubclass(cls, BaseModel) or cls is BaseModel or name == "WsMessage":
            continue
        if not re.search(rf"\b(interface|type)\s+{name}\b", text):
            missing.append(name)
            continue
        for field in cls.model_fields:
            if not re.search(rf"\b{field}\??:", text):
                missing.append(f"{name}.{field}")
    assert not missing, f"types.ts is missing: {missing}"


async def test_schema_endpoint(web_stack):
    station, sim, client = web_stack
    r = await client.get("/api/schema.json")
    assert r.status_code == 200 and "StatusOut" in r.json() and "FeedEntry" in r.json()
```

Run `python -m pytest cubesat_gs/tests/test_schema_sync.py -q` — fix `types.ts` until it passes.

- [ ] **Step 2: Build and commit the bundle**

```bash
cd cubesat_gs/web/frontend && npm test && npm run typecheck && npm run build && cd ../../..
python -m pytest -q -W error
python -m pytest cubesat_gs/tests/test_web_static.py -q
```
Then run `python cubesat_gs/main.py --sim --sim-beacon-interval 3` and open `http://127.0.0.1:8080/` — the built dashboard loads from FastAPI (no Vite). Walk every view: Overview shows the instrument empty state; Live Feed streams after switching to Beacon; Telecommand PING responds; Pass Tracker shows the TLE empty state; Settings loads and saves a frequency; export downloads a CSV. Ctrl+C stops cleanly. Note the bundle size in the report (`static/assets/*.js` total, expect < 1 MB gzip-less on Recharts).

- [ ] **Step 3: README**

Replace the "Phase 1 (this state)" line and the Run section of `README.md` with:
```markdown
Phase 1 + 2 (this state): headless core, FastAPI/WebSocket backend, React dashboard, pass prediction.

## Run

```bash
python cubesat_gs/main.py                 # real modem + dashboard on http://0.0.0.0:8080
python cubesat_gs/main.py --sim           # no hardware: in-process ESP32/OBC simulator
python cubesat_gs/main.py --no-web        # headless
```

Open `http://<pi-address>:8080/` for the dashboard and `/api/docs` for the API.

## Dashboard development

```bash
cd cubesat_gs/web/frontend
npm install
npm run dev          # http://localhost:5173, proxies /api and /ws to :8080 (run main.py --sim alongside)
npm test && npm run typecheck
npm run build        # writes cubesat_gs/web/static/ — commit the result; the Pi needs no Node
```

## Pass prediction

Set `satellite.tle_line1/2` (or `satellite.tle_source` to a CelesTrak URL and press "Refresh TLE" in Settings).
Passes above `passes.min_elevation` are listed for `passes.prediction_days`; the current pass streams az/el/Doppler to the dashboard once per second.
```

- [ ] **Step 4: Final verification and commit**

```bash
python -m pytest -q -W error
git add README.md cubesat_gs/web/static cubesat_gs/web/app.py cubesat_gs/tests/test_schema_sync.py cubesat_gs/web/frontend
git commit -m "Build and commit dashboard bundle; schema sync guard; README for Phase 2"
```

---

## Self-review notes

- Spec §3.2 in-loop uvicorn without its signal handlers — Task 10 `serve()`.
- Spec §3.3 hub: pending-entry TTL 2 s, ring 500, slow-client 1013, status poll 5 s — Task 5.
- Spec §3.4 every endpoint has a task: status/health (4), packets + telemetry (6), commands + frequency (7), passes (8), config + serial-ports + db/stats + export (9), static (10), schema.json (15).
- Spec §3.6 predictor incl. daily 03:00 UTC TLE refresh — Task 3 `_tick`.
- Spec §5.3 all six views — Tasks 12–14; §5.4 store caps — Task 11 tests.
- Spec §6 test list — every file present; frontend Vitest in Tasks 11–14.
- Interface consistency checked: `feed_entry_from_row` (Task 5) used by Task 6; `CommandStarted` (Task 1) published in Task 7 and consumed by Task 5; `set_presets`/`set_tle_source`/`set_tle` restore semantics (Tasks 2, 9); `config_path` (Task 9) used by the config route; `PassInstrument` (Task 12) reused in Task 14.
