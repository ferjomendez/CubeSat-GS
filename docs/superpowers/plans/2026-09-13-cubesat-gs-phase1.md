# CubeSat GS Phase 1 (Headless Core) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A headless CubeSat ground station in Python that talks to the ESP32 LoRa modem (or a simulator), parses CCSDS packets, decodes telemetry, sends telecommands with retry, manages frequency, and stores everything in MongoDB Atlas with SQLite fallback — runnable end-to-end with `python main.py --sim`.

**Architecture:** One asyncio process. A central `EventBus` decouples modules: `SerialHandler` publishes `PacketReceived`; `TelemetryDecoder`, `TelecommandManager`, `Storage` and `FrequencyManager` subscribe. `GroundStation` (core/station.py) owns everything and exposes `start()`/`stop()`.

**Tech Stack:** Python 3.11, asyncio, pyserial + pyserial-asyncio, motor/pymongo, aiosqlite, PyYAML, python-dotenv, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-13-cubesat-gs-phase1-design.md`

## Global Constraints

- Python 3.11 (RPi 3B+ target; no threads, single event loop, keep memory small).
- Git root is the workspace root (`Aerospace Team UAI/`); all Python code lives under `cubesat_gs/`. Run every command from the git root.
- Commit messages are plain text. **Never add `Co-Authored-By` or "Generated with" trailers.**
- Never write credentials into any tracked file. `MONGO_URI` comes only from the environment / gitignored `.env`.
- CRC-16-CCITT: init `0xFFFF`, poly `0x1021`, no reflection, no final XOR. Vector `b"123456789"` → `0x29B1`.
- Default CCSDS conventions match the OBC: `length_includes_crc=True`, `sequence_scope="global"`.
- Frequencies: TCTM `435.500`, beacon `437.250`. Uplink APID `100`, beacon APID `10`, TM response APID `101`.
- Tests are fully offline: no hardware, no network, no real Mongo. Run with `python -m pytest cubesat_gs/tests -q` from the git root.
- pytest-asyncio in `asyncio_mode = auto` (set in `pytest.ini`), so `async def test_*` needs no decorator.
- Every module imports only `cubesat_gs.core.events`, `cubesat_gs.core.config`, `cubesat_gs.core.ccsds` and stdlib/3rd-party — never another feature module (station.py is the only place that wires them).

## File Map

| File | Responsibility |
|---|---|
| `cubesat_gs/__init__.py` | package marker |
| `cubesat_gs/requirements.txt` | pinned floors from spec §6 |
| `cubesat_gs/.env.example` | placeholder `MONGO_URI` |
| `cubesat_gs/config/gs_config.yaml` | master config (spec §3.3) |
| `cubesat_gs/config/telemetry_defs.yaml` | APID field definitions (spec §3.7) |
| `cubesat_gs/config/commands.yaml` | telecommand registry (spec §3.8) |
| `cubesat_gs/core/config.py` | YAML + .env → typed dataclasses |
| `cubesat_gs/core/events.py` | `EventBus` + event dataclasses |
| `cubesat_gs/core/ccsds.py` | CRC, parse/build, `PacketBuilder`, `SequenceTracker` |
| `cubesat_gs/core/serial_handler.py` | async modem I/O, command queue, reconnect |
| `cubesat_gs/core/frequency_manager.py` | `Mode`, `FrequencyManager` |
| `cubesat_gs/core/telemetry.py` | `TelemetryDecoder`, `DecodedPacket` |
| `cubesat_gs/core/telecommand.py` | `TelecommandManager`, `CommandRecord` |
| `cubesat_gs/core/station.py` | `GroundStation` wiring |
| `cubesat_gs/storage/sqlite_backend.py` | `SQLiteBackend` |
| `cubesat_gs/storage/mongo_backend.py` | `MongoBackend` |
| `cubesat_gs/storage/database.py` | `Storage` facade: routing, fallback, sync, sessions |
| `cubesat_gs/storage/exporter.py` | CSV/JSON export + CLI |
| `cubesat_gs/tests/serial_simulator.py` | `ModemSimulator`, `SimulatedSerial`, TCP server CLI |
| `cubesat_gs/tests/fakes.py` | `FakeMotorClient` for storage tests |
| `cubesat_gs/tests/test_*.py` | one test module per source module + integration |
| `cubesat_gs/main.py` | CLI entry point |
| `pytest.ini` (git root) | asyncio mode, test path |

The spec lists `storage/database.py` as one file; it is split into three (sqlite_backend, mongo_backend, database) so each backend can be read and tested alone. Public import path stays `cubesat_gs.storage.database.Storage`.

---

### Task 1: Project scaffold and config loader

**Files:**
- Create: `pytest.ini`, `cubesat_gs/__init__.py`, `cubesat_gs/core/__init__.py`, `cubesat_gs/storage/__init__.py`, `cubesat_gs/tests/__init__.py`, `cubesat_gs/requirements.txt`, `cubesat_gs/.env.example`, `cubesat_gs/config/gs_config.yaml`, `cubesat_gs/core/config.py`
- Test: `cubesat_gs/tests/test_config.py`

**Interfaces:**
- Produces: `load_config(path: str | Path | None = None, *, dotenv: bool = True) -> GSConfig` (tests pass `dotenv=False` so a developer's real `.env` cannot leak in) and the dataclasses `GSConfig, SerialConfig, SerialTimeouts, FrequencyConfig, CCSDSConfig, CommandConfig, TelemetryConfig, DatabaseConfig, LoggingConfig, StationConfig, SatelliteConfig, PassConfig, WebConfig`. `GSConfig.base_dir: Path` is the directory containing the YAML; relative paths in the config (`commands.registry`, `telemetry.definitions`, `database.local_fallback_path`, `logging.file`) are resolved against `base_dir.parent` (i.e. `cubesat_gs/`) by `GSConfig.resolve(path_str) -> Path`.

- [ ] **Step 1: Create scaffold files**

`pytest.ini` (git root):
```ini
[pytest]
asyncio_mode = auto
testpaths = cubesat_gs/tests
```

`cubesat_gs/requirements.txt`:
```
pyserial>=3.5
pyserial-asyncio>=0.6
motor>=3.4
pymongo[srv]>=4.6
aiosqlite>=0.20
pyyaml>=6
python-dotenv>=1
pytest>=8
pytest-asyncio>=0.23
```

`cubesat_gs/.env.example`:
```
# Copy to .env (gitignored). Never commit the real value.
MONGO_URI=mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net/?appName=cubesat-gs
```

Empty `__init__.py` in `cubesat_gs/`, `cubesat_gs/core/`, `cubesat_gs/storage/`, `cubesat_gs/tests/`.

`cubesat_gs/config/gs_config.yaml`:
```yaml
serial:
  port: "auto"              # "auto", "/dev/ttyUSB0", "COM3", or "socket://localhost:5000"
  baudrate: 115200
  reconnect_interval: 5     # seconds
  timeouts:
    tx: 5.0                 # seconds to wait for OK:TX_DONE
    freq: 2.0               # seconds to wait for OK:FREQ_SET

frequencies:
  tctm: 435.500
  beacon: 437.250

ccsds:
  length_includes_crc: true   # OBC_sim.py convention; false when OBC becomes standard-compliant
  sequence_scope: global      # global | per_apid

station:
  name: "UAI Ground Station"
  latitude: -33.35
  longitude: -70.67
  altitude: 500

satellite:
  name: "UAI-SAT"
  tle_line1: ""
  tle_line2: ""
  tle_source: ""

passes:
  min_elevation: 10
  prediction_days: 7

commands:
  registry: "config/commands.yaml"
  default_timeout: 10
  max_retries: 3
  retry_backoff: 1.5
  history_size: 500

telemetry:
  definitions: "config/telemetry_defs.yaml"

web:
  host: "0.0.0.0"
  port: 8080

database:
  # MONGO_URI is read from the environment variable, NOT from this file
  db_name: "cubesat_gs"
  retention_days: 365
  local_fallback_path: "data/gs_offline.db"

logging:
  level: "INFO"
  file: "logs/gs.log"
```

- [ ] **Step 2: Install dependencies**

Run: `python -m pip install -r cubesat_gs/requirements.txt`
Expected: all packages install without error.

- [ ] **Step 3: Write the failing tests**

`cubesat_gs/tests/test_config.py`:
```python
from pathlib import Path

import pytest

from cubesat_gs.core.config import load_config, GSConfig

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_load_default_config():
    cfg = load_config(CONFIG_DIR / "gs_config.yaml")
    assert isinstance(cfg, GSConfig)
    assert cfg.serial.port == "auto"
    assert cfg.serial.baudrate == 115200
    assert cfg.serial.timeouts.tx == 5.0
    assert cfg.frequencies.tctm == 435.5
    assert cfg.frequencies.beacon == 437.25
    assert cfg.ccsds.length_includes_crc is True
    assert cfg.ccsds.sequence_scope == "global"
    assert cfg.commands.max_retries == 3
    assert cfg.database.db_name == "cubesat_gs"


def test_resolve_relative_paths():
    cfg = load_config(CONFIG_DIR / "gs_config.yaml")
    assert cfg.resolve(cfg.commands.registry) == CONFIG_DIR / "commands.yaml"
    assert cfg.resolve(cfg.telemetry.definitions) == CONFIG_DIR / "telemetry_defs.yaml"


def test_missing_keys_get_defaults(tmp_path):
    p = tmp_path / "gs.yaml"
    p.write_text("serial:\n  port: COM7\n")
    cfg = load_config(p)
    assert cfg.serial.port == "COM7"
    assert cfg.serial.baudrate == 115200
    assert cfg.frequencies.tctm == 435.5
    assert cfg.ccsds.sequence_scope == "global"


def test_invalid_sequence_scope_rejected(tmp_path):
    p = tmp_path / "gs.yaml"
    p.write_text("ccsds:\n  sequence_scope: bogus\n")
    with pytest.raises(ValueError, match="sequence_scope"):
        load_config(p)


def test_mongo_uri_from_env(tmp_path, monkeypatch):
    p = tmp_path / "gs.yaml"
    p.write_text("database: {}\n")
    monkeypatch.setenv("MONGO_URI", "mongodb://x")
    assert load_config(p, dotenv=False).database.mongo_uri == "mongodb://x"
    monkeypatch.delenv("MONGO_URI")
    assert load_config(p, dotenv=False).database.mongo_uri is None  # dotenv=False: ignore a real .env
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cubesat_gs.core.config'`

- [ ] **Step 5: Implement config.py**

`cubesat_gs/core/config.py`:
```python
"""Configuration loader: gs_config.yaml + .env -> typed dataclasses."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "gs_config.yaml"


@dataclass
class SerialTimeouts:
    tx: float = 5.0
    freq: float = 2.0


@dataclass
class SerialConfig:
    port: str = "auto"
    baudrate: int = 115200
    reconnect_interval: float = 5.0
    timeouts: SerialTimeouts = field(default_factory=SerialTimeouts)


@dataclass
class FrequencyConfig:
    tctm: float = 435.500
    beacon: float = 437.250


@dataclass
class CCSDSConfig:
    length_includes_crc: bool = True
    sequence_scope: str = "global"  # global | per_apid


@dataclass
class StationConfig:
    name: str = "Ground Station"
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0


@dataclass
class SatelliteConfig:
    name: str = ""
    tle_line1: str = ""
    tle_line2: str = ""
    tle_source: str = ""


@dataclass
class PassConfig:
    min_elevation: float = 10.0
    prediction_days: int = 7


@dataclass
class CommandConfig:
    registry: str = "config/commands.yaml"
    default_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff: float = 1.5
    history_size: int = 500


@dataclass
class TelemetryConfig:
    definitions: str = "config/telemetry_defs.yaml"


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class DatabaseConfig:
    db_name: str = "cubesat_gs"
    retention_days: int = 365
    local_fallback_path: str = "data/gs_offline.db"
    mongo_uri: str | None = None  # env only


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/gs.log"


@dataclass
class GSConfig:
    serial: SerialConfig = field(default_factory=SerialConfig)
    frequencies: FrequencyConfig = field(default_factory=FrequencyConfig)
    ccsds: CCSDSConfig = field(default_factory=CCSDSConfig)
    station: StationConfig = field(default_factory=StationConfig)
    satellite: SatelliteConfig = field(default_factory=SatelliteConfig)
    passes: PassConfig = field(default_factory=PassConfig)
    commands: CommandConfig = field(default_factory=CommandConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    web: WebConfig = field(default_factory=WebConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    base_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_PATH.parent)

    def resolve(self, path_str: str) -> Path:
        """Resolve a config-relative path against the package dir (parent of config/)."""
        p = Path(path_str)
        return p if p.is_absolute() else (self.base_dir.parent / p).resolve()


# Nested sections by key name (field annotations are strings under `from __future__ import annotations`).
_NESTED: dict[str, type] = {
    "serial": SerialConfig, "timeouts": SerialTimeouts, "frequencies": FrequencyConfig,
    "ccsds": CCSDSConfig, "station": StationConfig, "satellite": SatelliteConfig,
    "passes": PassConfig, "commands": CommandConfig, "telemetry": TelemetryConfig,
    "web": WebConfig, "database": DatabaseConfig, "logging": LoggingConfig,
}


def _build(cls: type, data: Any, where: str) -> Any:
    """Recursively build a dataclass from a dict, applying defaults, warning on unknown keys."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{where}: expected a mapping, got {type(data).__name__}")
    known = {f.name for f in fields(cls)}
    for key in data:
        if key not in known:
            log.warning("config: unknown key %s.%s ignored", where, key)
    kwargs = {}
    for name in known:
        if name not in data:
            continue
        value = data[name]
        if name in _NESTED:
            kwargs[name] = _build(_NESTED[name], value, f"{where}.{name}")
        else:
            kwargs[name] = value
    return cls(**kwargs)


def _validate(cfg: GSConfig) -> None:
    if cfg.ccsds.sequence_scope not in ("global", "per_apid"):
        raise ValueError(
            f"ccsds.sequence_scope must be 'global' or 'per_apid', got {cfg.ccsds.sequence_scope!r}"
        )
    if cfg.commands.max_retries < 0:
        raise ValueError("commands.max_retries must be >= 0")
    if cfg.serial.reconnect_interval <= 0:
        raise ValueError("serial.reconnect_interval must be > 0")


def load_config(path: str | Path | None = None, *, dotenv: bool = True) -> GSConfig:
    """Load the YAML config; with dotenv=True also load a .env file found upward from this package."""
    if dotenv:
        load_dotenv()
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    cfg: GSConfig = _build(GSConfig, data, "config")
    cfg.base_dir = path.resolve().parent
    cfg.database.mongo_uri = os.environ.get("MONGO_URI") or None
    cfg.serial.reconnect_interval = float(cfg.serial.reconnect_interval)
    _validate(cfg)
    return cfg
```

Also remove the unused `is_dataclass` name from the `dataclasses` import line.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_config.py -q`
Expected: 5 passed

- [ ] **Step 7: Commit**

```bash
git add pytest.ini cubesat_gs
git commit -m "Add project scaffold and typed config loader"
```

---

### Task 2: Event bus

**Files:**
- Create: `cubesat_gs/core/events.py`
- Test: `cubesat_gs/tests/test_events.py`

**Interfaces:**
- Produces: `EventBus` with `subscribe(event_type, handler)`, `unsubscribe(event_type, handler)`, `publish(event) -> None`, `async wait_for(event_type, predicate=None, timeout=None)`; `now() -> datetime` (UTC); event dataclasses `ConnectionChanged, SerialError, PacketReceived, PacketSent, ModemAck, SequenceGap, PacketDecoded, PacketMalformed, AlarmRaised, CommandCompleted, FrequencyChanged`. `PacketDecoded.decoded`, `CommandCompleted.record`, `FrequencyChanged.mode` are typed `Any` here to avoid importing feature modules; the concrete types are defined in Tasks 7–9.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_events.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_events.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement events.py**

`cubesat_gs/core/events.py`:
```python
"""Central asyncio event bus and the event dataclasses shared by all modules."""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, TypeVar

log = logging.getLogger(__name__)

E = TypeVar("E")
Handler = Callable[[Any], Awaitable[None]]


def now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- events

@dataclass(frozen=True)
class ConnectionChanged:
    connected: bool
    port: str
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class SerialError:
    message: str
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketReceived:
    raw: bytes
    rssi: float | None
    snr: float | None
    freq_mhz: float
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketSent:
    raw: bytes
    freq_mhz: float
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class ModemAck:
    kind: str  # "TX_DONE" | "FREQ_SET"
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class SequenceGap:
    apid: int
    expected: int
    received: int
    missed: int
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketDecoded:
    source: PacketReceived
    packet: Any      # ccsds.CCSDSPacket
    decoded: Any     # telemetry.DecodedPacket
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class PacketMalformed:
    source: PacketReceived
    reason: str
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class AlarmRaised:
    source: PacketReceived
    apid: int
    field_name: str
    value: float
    threshold: float
    alarm_type: str  # "low" | "high"
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class CommandCompleted:
    record: Any  # telecommand.CommandRecord
    ts: datetime = field(default_factory=now)


@dataclass(frozen=True)
class FrequencyChanged:
    mode: Any    # frequency_manager.Mode
    mhz: float
    ts: datetime = field(default_factory=now)


# ---------------------------------------------------------------- bus

class EventBus:
    """Fan-out of events to async handlers. Handlers run as tasks; exceptions are logged, never raised."""

    def __init__(self) -> None:
        self._subs: dict[type, list[Handler]] = defaultdict(list)
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._subs[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        try:
            self._subs[event_type].remove(handler)
        except ValueError:
            pass

    def subscriber_count(self, event_type: type) -> int:
        return len(self._subs.get(event_type, []))

    def publish(self, event: Any) -> None:
        for handler in list(self._subs.get(type(event), [])):
            task = asyncio.ensure_future(self._run(handler, event))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _run(self, handler: Handler, event: Any) -> None:
        try:
            await handler(event)
        except Exception:  # noqa: BLE001 - isolation is the point
            log.exception("event handler %r failed for %r", handler, event)

    async def wait_for(self, event_type: type, predicate: Callable[[Any], bool] | None = None,
                       timeout: float | None = None) -> Any:
        """Await the next event of `event_type` matching `predicate`. Raises asyncio.TimeoutError."""
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()

        async def _once(ev: Any) -> None:
            if not fut.done() and (predicate is None or predicate(ev)):
                fut.set_result(ev)

        self.subscribe(event_type, _once)
        try:
            return await asyncio.wait_for(fut, timeout)
        finally:
            self.unsubscribe(event_type, _once)

    async def drain(self) -> None:
        """Wait for all in-flight handler tasks (used by tests and shutdown)."""
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_events.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/events.py cubesat_gs/tests/test_events.py
git commit -m "Add asyncio event bus and event dataclasses"
```

---
### Task 3: CCSDS — CRC, parse, build

**Files:**
- Create: `cubesat_gs/core/ccsds.py`
- Test: `cubesat_gs/tests/test_ccsds.py`

**Interfaces:**
- Produces: `crc16_ccitt(data: bytes) -> int`, `crc16_append(data) -> bytes`, `crc16_verify(data_with_crc) -> bool`, `CCSDSError(ValueError)`, `CCSDSPacket` (frozen dataclass: `version, packet_type, sec_header_flag, apid, sequence_flags, sequence_count, data_length, payload`, method `to_bytes()`), `parse(raw, *, length_includes_crc=True) -> CCSDSPacket`, `build(apid, payload, *, sequence_count, packet_type=1, seq_flags=0b11, sec_header_flag=False, length_includes_crc=True) -> bytes`, `peek_apid_seq(raw) -> tuple[int, int] | None` (header-only best-effort read used by Storage), constants `HEADER_LEN = 6`, `APID_BEACON = 10`, `APID_TM_RESPONSE = 101`, `APID_TELECOMMAND = 100`.

Reference vectors (from `cubesat_comms-main/OBC_sim.py` conventions):
- Beacon, seq 0: `000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C` (payload `VLEO_BEACON_SYS_NOMINAL`, 23 bytes, data_length field 0x18 = 24 = 23+2-1).
- TM response, seq 1: `0065C001000F504F4E475F444154415F362E3238` (payload `PONG_DATA_6.28`).
- GS PING, type=1, seq 0: `1064C000000550494E47`.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_ccsds.py`:
```python
import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.ccsds import CCSDSError, CCSDSPacket, build, parse

BEACON_HEX = "000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C"
PONG_HEX = "0065C001000F504F4E475F444154415F362E3238"
PING_HEX = "1064C000000550494E47"


# ---- CRC

def test_crc_standard_vector():
    assert ccsds.crc16_ccitt(b"123456789") == 0x29B1


def test_crc_append_and_verify():
    framed = ccsds.crc16_append(b"abc")
    assert len(framed) == 5
    assert ccsds.crc16_verify(framed)
    assert not ccsds.crc16_verify(framed[:-1] + b"\x00")
    assert not ccsds.crc16_verify(b"\x01")  # too short


# ---- parse

def test_parse_obc_beacon():
    p = parse(bytes.fromhex(BEACON_HEX))
    assert p.version == 0
    assert p.packet_type == 0
    assert p.sec_header_flag is False
    assert p.apid == 10
    assert p.sequence_flags == 0b11
    assert p.sequence_count == 0
    assert p.data_length == 24
    assert p.payload == b"VLEO_BEACON_SYS_NOMINAL"


def test_parse_pong():
    p = parse(bytes.fromhex(PONG_HEX))
    assert p.apid == 101 and p.sequence_count == 1
    assert p.payload == b"PONG_DATA_6.28"


def test_parse_strict_standard_convention():
    # data_length = len(payload) - 1 = 2 for b"abc"
    raw = bytes([0x00, 0x05, 0xC0, 0x00, 0x00, 0x02]) + b"abc"
    p = parse(raw, length_includes_crc=False)
    assert p.payload == b"abc"
    with pytest.raises(CCSDSError, match="length"):
        parse(raw, length_includes_crc=True)


def test_parse_rejects_short():
    with pytest.raises(CCSDSError, match="short"):
        parse(b"\x00\x0A\xC0")


def test_parse_rejects_bad_version():
    raw = bytearray(bytes.fromhex(BEACON_HEX))
    raw[0] |= 0x20  # version bits = 001
    with pytest.raises(CCSDSError, match="version"):
        parse(bytes(raw))


def test_parse_rejects_length_mismatch():
    raw = bytes.fromhex(BEACON_HEX)[:-1]  # truncated payload
    with pytest.raises(CCSDSError, match="length"):
        parse(raw)


def test_parse_type_and_secheader_bits():
    raw = bytes([0x18, 0x05, 0xC0, 0x00, 0x00, 0x01]) + b""  # type=1, sec hdr=1, apid=5
    p = parse(raw)
    assert p.packet_type == 1 and p.sec_header_flag is True and p.apid == 5
    assert p.payload == b""


# ---- build

def test_build_ping_matches_vector():
    raw = build(100, b"PING", sequence_count=0)
    assert raw.hex().upper() == PING_HEX


def test_build_roundtrip_both_conventions():
    for conv in (True, False):
        raw = build(2047, b"\x01\x02\x03", sequence_count=0x3FFF, packet_type=0,
                    length_includes_crc=conv)
        p = parse(raw, length_includes_crc=conv)
        assert p.apid == 2047 and p.sequence_count == 0x3FFF and p.payload == b"\x01\x02\x03"
        assert p.to_bytes() == raw


def test_build_rejects_out_of_range():
    with pytest.raises(CCSDSError):
        build(2048, b"", sequence_count=0)
    with pytest.raises(CCSDSError):
        build(1, b"", sequence_count=0x4000)
    with pytest.raises(CCSDSError):
        build(1, b"x" * 65536, sequence_count=0)


def test_peek_apid_seq():
    assert ccsds.peek_apid_seq(bytes.fromhex(PONG_HEX)) == (101, 1)
    assert ccsds.peek_apid_seq(b"\x00") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_ccsds.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement ccsds.py (CRC, dataclass, parse, build, peek)**

`cubesat_gs/core/ccsds.py`:
```python
"""CCSDS Space Packet (133.0-B-2) primary header + CRC-16-CCITT matching the ESP32 firmware."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HEADER_LEN = 6
APID_BEACON = 10
APID_TELECOMMAND = 100
APID_TM_RESPONSE = 101

_MAX_APID = 0x7FF
_MAX_SEQ = 0x3FFF


class CCSDSError(ValueError):
    """Malformed packet or invalid build parameters."""


# ---------------------------------------------------------------- CRC-16-CCITT (init 0xFFFF, poly 0x1021)

def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def crc16_append(data: bytes) -> bytes:
    return data + crc16_ccitt(data).to_bytes(2, "big")


def crc16_verify(data_with_crc: bytes) -> bool:
    if len(data_with_crc) < 2:
        return False
    body, tail = data_with_crc[:-2], data_with_crc[-2:]
    return crc16_ccitt(body) == int.from_bytes(tail, "big")


# ---------------------------------------------------------------- packet

@dataclass(frozen=True)
class CCSDSPacket:
    version: int
    packet_type: int
    sec_header_flag: bool
    apid: int
    sequence_flags: int
    sequence_count: int
    data_length: int  # raw field value as transmitted
    payload: bytes

    def to_bytes(self) -> bytes:
        return _header(
            self.apid, self.sequence_count, self.data_length,
            packet_type=self.packet_type, seq_flags=self.sequence_flags,
            sec_header_flag=self.sec_header_flag, version=self.version,
        ) + self.payload


def _header(apid: int, seq: int, data_length: int, *, packet_type: int, seq_flags: int,
            sec_header_flag: bool, version: int = 0) -> bytes:
    w0 = (version << 13) | (packet_type << 12) | (int(sec_header_flag) << 11) | apid
    w1 = (seq_flags << 14) | seq
    return w0.to_bytes(2, "big") + w1.to_bytes(2, "big") + data_length.to_bytes(2, "big")


def _expected_payload_len(data_length: int, length_includes_crc: bool) -> int:
    return data_length + 1 - (2 if length_includes_crc else 0)


def parse(raw: bytes, *, length_includes_crc: bool = True) -> CCSDSPacket:
    if len(raw) < HEADER_LEN:
        raise CCSDSError(f"packet too short: {len(raw)} bytes")
    w0 = int.from_bytes(raw[0:2], "big")
    w1 = int.from_bytes(raw[2:4], "big")
    data_length = int.from_bytes(raw[4:6], "big")
    version = w0 >> 13
    if version != 0:
        raise CCSDSError(f"unsupported version {version}")
    payload = raw[HEADER_LEN:]
    expected = _expected_payload_len(data_length, length_includes_crc)
    if len(payload) != expected:
        raise CCSDSError(
            f"data length mismatch: header declares {expected} payload bytes "
            f"(field={data_length}, includes_crc={length_includes_crc}), got {len(payload)}"
        )
    return CCSDSPacket(
        version=version,
        packet_type=(w0 >> 12) & 0x1,
        sec_header_flag=bool((w0 >> 11) & 0x1),
        apid=w0 & _MAX_APID,
        sequence_flags=w1 >> 14,
        sequence_count=w1 & _MAX_SEQ,
        data_length=data_length,
        payload=bytes(payload),
    )


def build(apid: int, payload: bytes, *, sequence_count: int, packet_type: int = 1,
          seq_flags: int = 0b11, sec_header_flag: bool = False,
          length_includes_crc: bool = True) -> bytes:
    if not 0 <= apid <= _MAX_APID:
        raise CCSDSError(f"apid out of range: {apid}")
    if not 0 <= sequence_count <= _MAX_SEQ:
        raise CCSDSError(f"sequence_count out of range: {sequence_count}")
    if packet_type not in (0, 1) or not 0 <= seq_flags <= 3:
        raise CCSDSError("invalid packet_type or seq_flags")
    data_length = len(payload) - 1 + (2 if length_includes_crc else 0)
    if not 0 <= data_length <= 0xFFFF:
        raise CCSDSError(f"payload length not encodable: {len(payload)}")
    return _header(apid, sequence_count, data_length, packet_type=packet_type,
                   seq_flags=seq_flags, sec_header_flag=sec_header_flag) + bytes(payload)


def peek_apid_seq(raw: bytes) -> tuple[int, int] | None:
    """Best-effort (apid, seq) from the header without length validation. None if too short."""
    if len(raw) < HEADER_LEN:
        return None
    w0 = int.from_bytes(raw[0:2], "big")
    w1 = int.from_bytes(raw[2:4], "big")
    return w0 & _MAX_APID, w1 & _MAX_SEQ
```

Note: `data_length = len(payload) - 1 + 2` with an empty payload and the standard convention gives `-1`, which `build` rejects — CCSDS requires at least one payload byte. With the OBC convention an empty payload encodes as `1`, matching what the OBC would produce. This is intentional.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_ccsds.py -q`
Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/ccsds.py cubesat_gs/tests/test_ccsds.py
git commit -m "Add CCSDS packet parse/build and CRC-16-CCITT"
```

---

### Task 4: CCSDS — PacketBuilder and SequenceTracker

**Files:**
- Modify: `cubesat_gs/core/ccsds.py` (append)
- Test: `cubesat_gs/tests/test_ccsds.py` (append)

**Interfaces:**
- Consumes: `build`, `CCSDSPacket` from Task 3.
- Produces: `PacketBuilder(length_includes_crc: bool)` with `build(apid, payload, packet_type=1) -> bytes` and `next_count(apid) -> int` (peek); `SequenceTracker(scope: Literal["global","per_apid"])` with `observe(packet: CCSDSPacket) -> int | None` (missed count; `None` on first packet or no gap) and `reset()`.

- [ ] **Step 1: Write the failing tests** (append to `test_ccsds.py`)

```python
from cubesat_gs.core.ccsds import PacketBuilder, SequenceTracker


def _pkt(apid, seq):
    return parse(build(apid, b"x", sequence_count=seq, packet_type=0))


def test_packet_builder_counts_per_apid_and_wraps():
    b = PacketBuilder(length_includes_crc=True)
    assert parse(b.build(100, b"a")).sequence_count == 0
    assert parse(b.build(100, b"a")).sequence_count == 1
    assert parse(b.build(7, b"a")).sequence_count == 0  # independent counter
    b._counters[100] = 0x3FFF
    assert parse(b.build(100, b"a")).sequence_count == 0x3FFF
    assert parse(b.build(100, b"a")).sequence_count == 0
    assert b.next_count(7) == 1


def test_tracker_global_scope_obc_interleaving():
    t = SequenceTracker("global")
    assert t.observe(_pkt(10, 0)) is None
    assert t.observe(_pkt(101, 1)) is None   # different APID, same global counter: no gap
    assert t.observe(_pkt(10, 2)) is None
    assert t.observe(_pkt(10, 5)) == 2       # 3 and 4 missed


def test_tracker_per_apid_scope():
    t = SequenceTracker("per_apid")
    assert t.observe(_pkt(10, 0)) is None
    assert t.observe(_pkt(101, 0)) is None
    assert t.observe(_pkt(10, 1)) is None
    assert t.observe(_pkt(101, 3)) == 2


def test_tracker_wraparound():
    t = SequenceTracker("global")
    t.observe(_pkt(10, 0x3FFE))
    assert t.observe(_pkt(10, 0x3FFF)) is None
    assert t.observe(_pkt(10, 0)) is None
    assert t.observe(_pkt(10, 2)) == 1


def test_tracker_duplicate_or_backwards_is_not_a_gap():
    t = SequenceTracker("global")
    t.observe(_pkt(10, 5))
    assert t.observe(_pkt(10, 5)) is None
    assert t.observe(_pkt(10, 3)) is None
    t.reset()
    assert t.observe(_pkt(10, 9)) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_ccsds.py -q`
Expected: FAIL with `ImportError: cannot import name 'PacketBuilder'`

- [ ] **Step 3: Implement** (append to `ccsds.py`)

```python
# ---------------------------------------------------------------- TX counters / RX gap detection

class PacketBuilder:
    """Builds packets with a per-APID 14-bit sequence counter (CCSDS standard for the GS side)."""

    def __init__(self, length_includes_crc: bool = True) -> None:
        self._length_includes_crc = length_includes_crc
        self._counters: dict[int, int] = {}

    def next_count(self, apid: int) -> int:
        return self._counters.get(apid, 0)

    def build(self, apid: int, payload: bytes, packet_type: int = 1) -> bytes:
        seq = self._counters.get(apid, 0)
        raw = build(apid, payload, sequence_count=seq, packet_type=packet_type,
                    length_includes_crc=self._length_includes_crc)
        self._counters[apid] = (seq + 1) & _MAX_SEQ
        return raw


class SequenceTracker:
    """Detects missed downlink packets. scope='global' = one counter for all APIDs (current OBC)."""

    def __init__(self, scope: Literal["global", "per_apid"] = "global") -> None:
        if scope not in ("global", "per_apid"):
            raise ValueError(f"invalid sequence scope {scope!r}")
        self._scope = scope
        self._last: dict[int | None, int] = {}

    def reset(self) -> None:
        self._last.clear()

    def observe(self, packet: CCSDSPacket) -> int | None:
        key = packet.apid if self._scope == "per_apid" else None
        last = self._last.get(key)
        self._last[key] = packet.sequence_count
        if last is None:
            return None
        delta = (packet.sequence_count - last) & _MAX_SEQ
        # delta 1 = in order; 0 = duplicate; large delta (> half range) = out of order / reset
        if delta <= 1 or delta > _MAX_SEQ // 2:
            return None
        return delta - 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_ccsds.py -q`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/ccsds.py cubesat_gs/tests/test_ccsds.py
git commit -m "Add per-APID packet builder and sequence gap tracker"
```

---

### Task 5: Modem simulator (in-process core)

**Files:**
- Create: `cubesat_gs/tests/serial_simulator.py`
- Test: `cubesat_gs/tests/test_serial_simulator.py`

**Interfaces:**
- Consumes: `ccsds.build`, `ccsds.parse`, `ccsds.APID_*`.
- Produces: `ModemSimulator(*, beacon_interval=10.0, length_includes_crc=True, sequence_scope="global", fake_rssi=False, ping_apid=100, tctm_mhz=435.5, beacon_mhz=437.25)` with `async start()`, `async stop()`, `async handle_line(line: str)`, `async read_line() -> str` (next output line, no trailing newline), `inject_rx(raw: bytes, rssi=None, snr=None)`, `emit_beacon()`, attributes `freq: float`, `received_tx: list[bytes]`, `beacons_sent: int`; `SimulatedSerial(sim)` with `async open(url, baudrate) -> (StreamReader, SimulatedWriter)` usable as the `open_connection` factory of `SerialHandler`, plus `close_from_modem_side()` to simulate an unplug. The TCP server/CLI is added in Task 14.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_serial_simulator.py`:
```python
import asyncio

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
    with __import__("pytest").raises(asyncio.TimeoutError):
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_serial_simulator.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement the simulator core**

`cubesat_gs/tests/serial_simulator.py`:
```python
"""Simulates the ESP32 LoRa modem + OBC_sim.py from the serial side.

Usable in-process (SimulatedSerial) or as a TCP server (see main() — added in Task 14)
so the GS can connect with serial.port = "socket://localhost:<port>".
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from cubesat_gs.core import ccsds

log = logging.getLogger(__name__)

BEACON_PAYLOAD = b"VLEO_BEACON_SYS_NOMINAL"
PONG_PAYLOAD = b"PONG_DATA_6.28"


class ModemSimulator:
    def __init__(self, *, beacon_interval: float = 10.0, length_includes_crc: bool = True,
                 sequence_scope: Literal["global", "per_apid"] = "global", fake_rssi: bool = False,
                 ping_apid: int = ccsds.APID_TELECOMMAND, tctm_mhz: float = 435.5,
                 beacon_mhz: float = 437.25) -> None:
        self.beacon_interval = beacon_interval
        self.length_includes_crc = length_includes_crc
        self.sequence_scope = sequence_scope
        self.fake_rssi = fake_rssi
        self.ping_apid = ping_apid
        self.tctm_mhz = tctm_mhz
        self.beacon_mhz = beacon_mhz

        self.freq: float = tctm_mhz
        self.received_tx: list[bytes] = []
        self.beacons_sent = 0
        self.silent = False  # when True, never send OK:* (simulates a dead/failing modem)
        self._counters: dict[int | None, int] = {}
        self._out: asyncio.Queue[str] = asyncio.Queue()
        self._beacon_task: asyncio.Task | None = None
        self._pending: set[asyncio.Task] = set()

    # ---- lifecycle
    async def start(self) -> None:
        if self._beacon_task is None:
            self._beacon_task = asyncio.create_task(self._beacon_loop())

    async def stop(self) -> None:
        for t in [self._beacon_task, *self._pending]:
            if t is not None:
                t.cancel()
        self._beacon_task = None
        self._pending.clear()

    # ---- serial side
    async def handle_line(self, line: str) -> None:
        line = line.strip()
        if line.startswith("TX:"):
            try:
                raw = bytes.fromhex(line[3:])
            except ValueError:
                log.warning("sim: bad hex in %r", line)
                return
            self.received_tx.append(raw)
            if self.silent:
                return
            self._out.put_nowait("OK:TX_DONE")
            if self.freq == self.tctm_mhz and b"PING" in raw[ccsds.HEADER_LEN:]:
                self._spawn(self._reply_pong())
        elif line.startswith("FREQ:"):
            try:
                self.freq = float(line[5:])
            except ValueError:
                return  # real firmware stays silent on failure
            if not self.silent:
                self._out.put_nowait("OK:FREQ_SET")
        else:
            log.debug("sim: ignoring %r", line)

    async def read_line(self) -> str:
        return await self._out.get()

    # ---- RF side
    def inject_rx(self, raw: bytes, rssi: float | None = None, snr: float | None = None) -> None:
        line = "RX:" + raw.hex().upper()
        if self.fake_rssi:
            rssi = -97.5 if rssi is None else rssi
            snr = 8.25 if snr is None else snr
        if rssi is not None and snr is not None:
            line += f"|RSSI:{rssi}|SNR:{snr}"
        self._out.put_nowait(line)

    def emit_beacon(self) -> None:
        self.inject_rx(self._build(ccsds.APID_BEACON, BEACON_PAYLOAD))
        self.beacons_sent += 1

    def _build(self, apid: int, payload: bytes) -> bytes:
        key = apid if self.sequence_scope == "per_apid" else None
        seq = self._counters.get(key, 0)
        self._counters[key] = (seq + 1) & 0x3FFF
        return ccsds.build(apid, payload, sequence_count=seq, packet_type=0,
                           length_includes_crc=self.length_includes_crc)

    async def _reply_pong(self) -> None:
        await asyncio.sleep(0.05)
        self.inject_rx(self._build(ccsds.APID_TM_RESPONSE, PONG_PAYLOAD))

    async def _beacon_loop(self) -> None:
        while True:
            await asyncio.sleep(self.beacon_interval)
            if self.freq == self.beacon_mhz:
                self.emit_beacon()

    def _spawn(self, coro) -> None:
        t = asyncio.create_task(coro)
        self._pending.add(t)
        t.add_done_callback(self._pending.discard)


class SimulatedWriter:
    """Minimal asyncio.StreamWriter stand-in that feeds lines into the simulator."""

    def __init__(self, sim: ModemSimulator) -> None:
        self._sim = sim
        self._buf = b""
        self._closed = False

    def write(self, data: bytes) -> None:
        self._buf += data
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            asyncio.get_running_loop().create_task(self._sim.handle_line(line.decode(errors="ignore")))

    async def drain(self) -> None:
        await asyncio.sleep(0)

    def close(self) -> None:
        self._closed = True

    def is_closing(self) -> bool:
        return self._closed

    async def wait_closed(self) -> None:
        return None


class SimulatedSerial:
    """Factory compatible with SerialHandler's `open_connection(url, baudrate)` argument."""

    def __init__(self, sim: ModemSimulator) -> None:
        self.sim = sim
        self._reader: asyncio.StreamReader | None = None
        self._pump: asyncio.Task | None = None
        self.open_count = 0
        self.fail_next_open = False

    async def open(self, url: str, baudrate: int) -> tuple[asyncio.StreamReader, SimulatedWriter]:
        if self.fail_next_open:
            self.fail_next_open = False
            raise OSError("simulated open failure")
        self.open_count += 1
        self._reader = asyncio.StreamReader()
        self._pump = asyncio.create_task(self._pump_output(self._reader))
        return self._reader, SimulatedWriter(self.sim)

    async def _pump_output(self, reader: asyncio.StreamReader) -> None:
        try:
            while True:
                line = await self.sim.read_line()
                reader.feed_data(line.encode() + b"\n")
        except asyncio.CancelledError:
            pass

    def close_from_modem_side(self) -> None:
        if self._pump:
            self._pump.cancel()
        if self._reader:
            self._reader.feed_eof()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_serial_simulator.py -q`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/tests/serial_simulator.py cubesat_gs/tests/test_serial_simulator.py
git commit -m "Add in-process ESP32 modem simulator"
```

---
### Task 6: Serial handler

**Files:**
- Create: `cubesat_gs/core/serial_handler.py`
- Test: `cubesat_gs/tests/test_serial_handler.py`

**Interfaces:**
- Consumes: `EventBus`, events (`ConnectionChanged, SerialError, PacketReceived, PacketSent, ModemAck`), `SerialConfig`, `SimulatedSerial.open` (tests).
- Produces: `SerialHandler(bus, cfg: SerialConfig, get_freq: Callable[[], float], open_connection=None)` with `async start()`, `async stop()`, `async send_tx(raw: bytes) -> None`, `async set_frequency(mhz: float) -> None`, properties `connected: bool`, `port: str | None`; exceptions `SerialCommandTimeout(Exception)`, `SerialDisconnected(Exception)`; helper `parse_rx_line(line: str) -> tuple[bytes, float | None, float | None]` (raises `ValueError` on bad hex); `detect_port() -> str | None`; `default_open_connection(url, baudrate)`.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_serial_handler.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_serial_handler.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement serial_handler.py**

`cubesat_gs/core/serial_handler.py`:
```python
"""Async serial interface to the ESP32 LoRa modem (or the simulator)."""
from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import Awaitable, Callable

from cubesat_gs.core.config import SerialConfig
from cubesat_gs.core.events import (ConnectionChanged, EventBus, ModemAck, PacketReceived,
                                    PacketSent, SerialError)

log = logging.getLogger(__name__)

OpenConnection = Callable[[str, int], Awaitable[tuple[asyncio.StreamReader, object]]]

# USB-UART bridge vendor IDs commonly found on ESP32 dev boards
_KNOWN_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}


class SerialCommandTimeout(Exception):
    """The modem did not acknowledge a command in time."""


class SerialDisconnected(Exception):
    """The connection dropped while a command was in flight."""


def parse_rx_line(line: str) -> tuple[bytes, float | None, float | None]:
    """'RX:<hex>[|RSSI:<f>|SNR:<f>]' -> (raw, rssi, snr). Raises ValueError on bad hex."""
    body = line[3:].strip()
    parts = body.split("|")
    try:
        raw = bytes.fromhex(parts[0])
    except ValueError as e:
        raise ValueError(f"invalid hex in RX line: {parts[0]!r}") from e
    rssi = snr = None
    for tok in parts[1:]:
        key, _, val = tok.partition(":")
        try:
            if key.upper() == "RSSI":
                rssi = float(val)
            elif key.upper() == "SNR":
                snr = float(val)
        except ValueError:
            log.debug("serial: unparsable %s value %r", key, val)
    return raw, rssi, snr


def detect_port() -> str | None:
    """First plausible USB serial device: prefers known USB-UART VIDs, else any ttyUSB/ttyACM/COM."""
    from serial.tools import list_ports
    candidates = []
    for p in list_ports.comports():
        dev = p.device
        if sys.platform.startswith("win"):
            ok = dev.upper().startswith("COM")
        else:
            ok = dev.startswith("/dev/ttyUSB") or dev.startswith("/dev/ttyACM")
        if ok:
            candidates.append(p)
    if not candidates:
        return None
    for p in candidates:
        if p.vid in _KNOWN_VIDS:
            return p.device
    return candidates[0].device


async def default_open_connection(url: str, baudrate: int):
    if url.startswith("socket://"):
        host, _, port = url[len("socket://"):].partition(":")
        return await asyncio.open_connection(host or "localhost", int(port or 5000))
    import serial_asyncio
    return await serial_asyncio.open_serial_connection(url=url, baudrate=baudrate)


@dataclass
class _Cmd:
    line: str
    ack_kind: str
    timeout: float
    done: asyncio.Future
    ack: asyncio.Future


class SerialHandler:
    def __init__(self, bus: EventBus, cfg: SerialConfig, get_freq: Callable[[], float],
                 open_connection: OpenConnection | None = None) -> None:
        self._bus = bus
        self._cfg = cfg
        self._get_freq = get_freq
        self._open = open_connection or default_open_connection
        self._queue: asyncio.Queue[_Cmd] = asyncio.Queue()
        self._inflight: _Cmd | None = None
        self._connected = False
        self._port: str | None = None
        self._run_task: asyncio.Task | None = None
        self._writer = None
        self._stopping = False
        self._announced: bool | None = None  # last published connection state

    # ---- public
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def port(self) -> str | None:
        return self._port

    async def start(self) -> None:
        self._stopping = False
        self._run_task = asyncio.create_task(self._run(), name="serial-run")

    async def stop(self) -> None:
        self._stopping = True
        if self._run_task:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass
        self._close_writer()
        self._set_connected(False)

    async def send_tx(self, raw: bytes) -> None:
        await self._submit("TX:" + raw.hex().upper(), "TX_DONE", self._cfg.timeouts.tx)
        self._bus.publish(PacketSent(raw=bytes(raw), freq_mhz=self._get_freq()))

    async def set_frequency(self, mhz: float) -> None:
        await self._submit(f"FREQ:{mhz:.3f}", "FREQ_SET", self._cfg.timeouts.freq)

    # ---- command queue
    async def _submit(self, line: str, ack_kind: str, timeout: float) -> None:
        loop = asyncio.get_running_loop()
        cmd = _Cmd(line, ack_kind, timeout, loop.create_future(), loop.create_future())
        await self._queue.put(cmd)
        await cmd.done

    async def _writer_loop(self, writer) -> None:
        while True:
            cmd = await self._queue.get()
            if cmd.done.done():
                continue
            self._inflight = cmd
            try:
                writer.write((cmd.line + "\n").encode())
                await writer.drain()
                await asyncio.wait_for(cmd.ack, cmd.timeout)
            except asyncio.TimeoutError:
                log.warning("serial: no %s within %.1fs for %r", cmd.ack_kind, cmd.timeout, cmd.line)
                cmd.done.set_exception(SerialCommandTimeout(cmd.line))
            except asyncio.CancelledError:
                if not cmd.done.done():
                    cmd.done.set_exception(SerialDisconnected(cmd.line))
                raise
            except Exception as e:  # noqa: BLE001 - write failure = link is gone
                if not cmd.done.done():
                    cmd.done.set_exception(SerialDisconnected(str(e)))
                raise
            else:
                cmd.done.set_result(None)
            finally:
                self._inflight = None

    # ---- reader
    async def _reader_loop(self, reader: asyncio.StreamReader) -> None:
        while True:
            data = await reader.readline()
            if not data:
                raise ConnectionError("EOF from modem")
            line = data.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        if line.startswith("RX:"):
            try:
                raw, rssi, snr = parse_rx_line(line)
            except ValueError as e:
                self._bus.publish(SerialError(message=str(e)))
                return
            self._bus.publish(PacketReceived(raw=raw, rssi=rssi, snr=snr, freq_mhz=self._get_freq()))
        elif line.startswith("OK:"):
            kind = line[3:].strip()
            cmd = self._inflight
            if cmd is not None and cmd.ack_kind == kind and not cmd.ack.done():
                cmd.ack.set_result(None)
            else:
                log.debug("serial: unexpected ack %r", line)
            self._bus.publish(ModemAck(kind=kind))
        else:
            log.debug("serial: modem says %r", line)

    # ---- connection lifecycle
    async def _run(self) -> None:
        while not self._stopping:
            port = self._cfg.port
            if port == "auto":
                port = detect_port()
            if port is None:
                self._set_connected(False, "auto")
                await asyncio.sleep(self._cfg.reconnect_interval)
                continue
            try:
                reader, writer = await self._open(port, self._cfg.baudrate)
            except Exception as e:  # noqa: BLE001 - OSError, SerialException, ConnectionRefusedError...
                log.warning("serial: cannot open %s: %s", port, e)
                self._set_connected(False, port)
                await asyncio.sleep(self._cfg.reconnect_interval)
                continue

            self._writer = writer
            self._port = port
            self._set_connected(True, port)
            writer_task = asyncio.create_task(self._writer_loop(writer), name="serial-writer")
            try:
                await self._reader_loop(reader)
            except (ConnectionError, OSError) as e:
                log.warning("serial: link lost on %s: %s", port, e)
            finally:
                writer_task.cancel()
                try:
                    await writer_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
                self._close_writer()
                self._set_connected(False, port)
            await asyncio.sleep(self._cfg.reconnect_interval)

    def _close_writer(self) -> None:
        w, self._writer = self._writer, None
        if w is not None:
            try:
                w.close()
            except Exception:  # noqa: BLE001
                pass

    def _set_connected(self, value: bool, port: str | None = None) -> None:
        """Publish ConnectionChanged only on an actual transition (first call always publishes)."""
        self._connected = value
        if value == self._announced:
            return
        self._announced = value
        self._bus.publish(ConnectionChanged(connected=value, port=port or self._port or ""))
```



- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_serial_handler.py -q`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/serial_handler.py cubesat_gs/tests/test_serial_handler.py
git commit -m "Add async serial handler with command queue and reconnect"
```

---

### Task 7: Frequency manager

**Files:**
- Create: `cubesat_gs/core/frequency_manager.py`
- Test: `cubesat_gs/tests/test_frequency_manager.py`

**Interfaces:**
- Consumes: `SerialHandler.set_frequency`, `SerialCommandTimeout`, `ConnectionChanged`, `FrequencyChanged`, `FrequencyConfig`.
- Produces: `Mode(str, Enum)` with `BEACON_LISTEN="beacon_listen"`, `TCTM="tctm"`, `CUSTOM="custom"`; `FrequencyManager(bus, serial, cfg: FrequencyConfig)` with `start()`, `stop()`, `async set_mode(mode: Mode, mhz: float | None = None)`, properties `mode: Mode`, `mhz: float`, `history: list[FrequencyChanged]` (last 100).

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_frequency_manager.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_frequency_manager.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement frequency_manager.py**

`cubesat_gs/core/frequency_manager.py`:
```python
"""Operating-frequency modes and switching via the modem's FREQ command."""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from enum import Enum

from cubesat_gs.core.config import FrequencyConfig
from cubesat_gs.core.events import ConnectionChanged, EventBus, FrequencyChanged

log = logging.getLogger(__name__)


class Mode(str, Enum):
    BEACON_LISTEN = "beacon_listen"
    TCTM = "tctm"
    CUSTOM = "custom"


class FrequencyManager:
    def __init__(self, bus: EventBus, serial, cfg: FrequencyConfig) -> None:
        self._bus = bus
        self._serial = serial
        self._cfg = cfg
        self._mode = Mode.TCTM
        self._mhz = cfg.tctm  # matches the ESP32 firmware boot default
        self._lock = asyncio.Lock()
        self.history: deque[FrequencyChanged] = deque(maxlen=100)

    @property
    def mode(self) -> Mode:
        return self._mode

    @property
    def mhz(self) -> float:
        return self._mhz

    def start(self) -> None:
        self._bus.subscribe(ConnectionChanged, self._on_connection)

    def stop(self) -> None:
        self._bus.unsubscribe(ConnectionChanged, self._on_connection)

    def _target_mhz(self, mode: Mode, mhz: float | None) -> float:
        if mode is Mode.TCTM:
            return self._cfg.tctm
        if mode is Mode.BEACON_LISTEN:
            return self._cfg.beacon
        if mhz is None:
            raise ValueError("CUSTOM mode requires an explicit mhz")
        return float(mhz)

    async def set_mode(self, mode: Mode, mhz: float | None = None) -> None:
        target = self._target_mhz(mode, mhz)
        async with self._lock:
            await self._serial.set_frequency(target)  # raises on timeout; state unchanged
            self._mode, self._mhz = mode, target
            ev = FrequencyChanged(mode=mode, mhz=target)
            self.history.append(ev)
            log.info("frequency: %s -> %.3f MHz", mode.value, target)
            self._bus.publish(ev)

    async def _on_connection(self, ev: ConnectionChanged) -> None:
        if not ev.connected:
            return
        try:
            async with self._lock:
                await self._serial.set_frequency(self._mhz)
            log.info("frequency: re-applied %.3f MHz after connect", self._mhz)
        except Exception as e:  # noqa: BLE001 - modem may not answer yet; next set_mode will retry
            log.warning("frequency: could not re-apply %.3f MHz: %s", self._mhz, e)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_frequency_manager.py -q`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/core/frequency_manager.py cubesat_gs/tests/test_frequency_manager.py
git commit -m "Add frequency manager with mode switching and re-apply on reconnect"
```

---
### Task 8: Telemetry decoder

**Files:**
- Create: `cubesat_gs/core/telemetry.py`, `cubesat_gs/config/telemetry_defs.yaml`
- Test: `cubesat_gs/tests/test_telemetry.py`

**Interfaces:**
- Consumes: `ccsds.parse`, `ccsds.CCSDSPacket`, `ccsds.SequenceTracker`, `CCSDSConfig`, events `PacketReceived, PacketDecoded, PacketMalformed, AlarmRaised, SequenceGap`.
- Produces: `DecodedField(name, value, unit, alarm, raw)`, `DecodedPacket(apid, apid_name, fields, unknown_apid, partial, error)` with `as_dict() -> dict[str, Any]`; `TelemetryDefError(ValueError)`; `load_definitions(path) -> dict[int, ApidDef]`; `TelemetryDecoder(bus, defs_path, ccsds_cfg)` with `decode(packet) -> DecodedPacket`, `start()`, `stop()`, `definitions: dict[int, ApidDef]`, `last_values: dict[int, DecodedPacket]` (latest per APID).

- [ ] **Step 1: Create the definitions file**

`cubesat_gs/config/telemetry_defs.yaml`:
```yaml
# Telemetry field definitions per APID. Big-endian. Key format: apid_<decimal>.
# Types: uint8 int8 uint16 int16 uint32 int32 float32 string bytes
# string/bytes: optional `length` (omit = rest of payload). string: optional `encoding` (default utf-8).
# numeric: optional `scale` (default 1), `offset` (default 0), `unit`, `alarm_low`, `alarm_high`.

apid_10:
  name: "Beacon"
  fields:
    - name: "message"
      type: "string"
      encoding: "utf-8"

apid_101:
  name: "TM Response"
  fields:
    - name: "response_data"
      type: "string"
      encoding: "utf-8"

# Future structured example (uncomment and adapt when the EPS subsystem defines its packet):
# apid_50:
#   name: "EPS Telemetry"
#   fields:
#     - name: "battery_voltage"
#       type: "float32"
#       unit: "V"
#       alarm_low: 3.3
#       alarm_high: 4.2
#     - name: "battery_temp"
#       type: "int16"
#       scale: 0.1
#       unit: "°C"
#       alarm_low: -10
#       alarm_high: 50
```

- [ ] **Step 2: Write the failing tests**

`cubesat_gs/tests/test_telemetry.py`:
```python
import asyncio
import struct
from pathlib import Path

import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CCSDSConfig
from cubesat_gs.core.events import (AlarmRaised, EventBus, PacketDecoded, PacketMalformed,
                                    PacketReceived, SequenceGap)
from cubesat_gs.core.telemetry import TelemetryDecoder, TelemetryDefError, load_definitions

DEFS = Path(__file__).resolve().parents[1] / "config" / "telemetry_defs.yaml"

EPS_YAML = """
apid_50:
  name: "EPS"
  fields:
    - {name: v_bat, type: float32, unit: V, alarm_low: 3.3, alarm_high: 4.2}
    - {name: t_bat, type: int16, scale: 0.1, unit: "°C", alarm_low: -10, alarm_high: 50}
    - {name: mode, type: uint8}
    - {name: uptime, type: uint32, unit: s}
    - {name: tag, type: string, length: 3}
    - {name: rest, type: bytes}
"""


def _pkt(apid, payload, seq=0):
    return ccsds.parse(ccsds.build(apid, payload, sequence_count=seq, packet_type=0))


def _decoder(tmp_path, text=None, scope="global"):
    path = DEFS
    if text is not None:
        path = tmp_path / "defs.yaml"
        path.write_text(text, encoding="utf-8")
    return TelemetryDecoder(EventBus(), path, CCSDSConfig(sequence_scope=scope))


def test_load_shipped_definitions():
    defs = load_definitions(DEFS)
    assert defs[10].name == "Beacon" and defs[101].name == "TM Response"
    assert defs[10].fields[0].type == "string"


def test_decode_beacon_string(tmp_path):
    d = _decoder(tmp_path)
    out = d.decode(_pkt(10, b"VLEO_BEACON_SYS_NOMINAL"))
    assert out.apid_name == "Beacon" and not out.unknown_apid and not out.partial
    assert out.fields[0].name == "message" and out.fields[0].value == "VLEO_BEACON_SYS_NOMINAL"
    assert out.fields[0].alarm is None
    assert out.as_dict() == {"message": "VLEO_BEACON_SYS_NOMINAL"}


def test_decode_structured_types_scale_alarms(tmp_path):
    d = _decoder(tmp_path, EPS_YAML)
    payload = struct.pack(">fhBI", 3.0, 555, 2, 123456) + b"abcXYZ"
    out = d.decode(_pkt(50, payload))
    f = {x.name: x for x in out.fields}
    assert f["v_bat"].value == pytest.approx(3.0) and f["v_bat"].alarm == "low" and f["v_bat"].unit == "V"
    assert f["t_bat"].value == pytest.approx(55.5) and f["t_bat"].alarm == "high"
    assert f["mode"].value == 2 and f["mode"].alarm is None
    assert f["uptime"].value == 123456
    assert f["tag"].value == "abc"
    assert f["rest"].value == b"XYZ"
    out2 = d.decode(_pkt(50, struct.pack(">fhBI", 3.8, 250, 0, 0) + b"abc"))
    f2 = {x.name: x for x in out2.fields}
    assert f2["v_bat"].alarm == "nominal" and f2["t_bat"].alarm == "nominal"
    assert f2["rest"].value == b""


def test_unknown_apid(tmp_path):
    d = _decoder(tmp_path)
    out = d.decode(_pkt(999, b"\x01\x02"))
    assert out.unknown_apid and out.apid_name == "UNKNOWN"
    assert out.fields[0].name == "raw_hex" and out.fields[0].value == "0102"


def test_truncated_payload_is_partial(tmp_path):
    d = _decoder(tmp_path, EPS_YAML)
    out = d.decode(_pkt(50, struct.pack(">f", 3.9) + b"\x00"))  # t_bat needs 2 bytes, only 1 left
    assert out.partial and "t_bat" in out.error
    assert [x.name for x in out.fields] == ["v_bat"]


def test_invalid_definitions_rejected(tmp_path):
    with pytest.raises(TelemetryDefError, match="type"):
        _decoder(tmp_path, "apid_1:\n  name: x\n  fields:\n    - {name: a, type: float64}\n")
    with pytest.raises(TelemetryDefError, match="length"):
        _decoder(tmp_path, "apid_1:\n  name: x\n  fields:\n    - {name: a, type: uint8, length: 2}\n")
    with pytest.raises(TelemetryDefError, match="scale"):
        _decoder(tmp_path, "apid_1:\n  name: x\n  fields:\n    - {name: a, type: string, scale: 2}\n")
    with pytest.raises(TelemetryDefError, match="apid"):
        _decoder(tmp_path, "beacon:\n  name: x\n  fields: []\n")


async def test_bus_flow_decoded_alarm_gap_malformed(tmp_path):
    bus = EventBus()
    path = tmp_path / "defs.yaml"
    path.write_text(EPS_YAML, encoding="utf-8")
    d = TelemetryDecoder(bus, path, CCSDSConfig())
    d.start()
    got = []

    async def on(ev):
        got.append(ev)

    for t in (PacketDecoded, AlarmRaised, SequenceGap, PacketMalformed):
        bus.subscribe(t, on)

    def rx(raw):
        bus.publish(PacketReceived(raw=raw, rssi=None, snr=None, freq_mhz=435.5))

    good = ccsds.build(50, struct.pack(">fhBI", 2.0, 0, 0, 0) + b"abc", sequence_count=0, packet_type=0)
    rx(good)
    rx(ccsds.build(50, struct.pack(">fhBI", 3.8, 0, 0, 0) + b"abc", sequence_count=3, packet_type=0))
    rx(b"\x00\x32\xc0")  # malformed
    await asyncio.sleep(0.02)

    decoded = [e for e in got if isinstance(e, PacketDecoded)]
    assert len(decoded) == 2 and decoded[0].source.raw == good
    alarms = [e for e in got if isinstance(e, AlarmRaised)]
    assert len(alarms) == 1 and alarms[0].field_name == "v_bat" and alarms[0].alarm_type == "low"
    assert alarms[0].threshold == 3.3
    gaps = [e for e in got if isinstance(e, SequenceGap)]
    assert len(gaps) == 1 and gaps[0].missed == 2 and gaps[0].apid == 50
    bad = [e for e in got if isinstance(e, PacketMalformed)]
    assert len(bad) == 1 and "short" in bad[0].reason
    assert d.last_values[50].as_dict()["v_bat"] == pytest.approx(3.8)
    d.stop()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_telemetry.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement telemetry.py**

`cubesat_gs/core/telemetry.py`:
```python
"""YAML-driven telemetry decoder with alarm evaluation."""
from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CCSDSConfig
from cubesat_gs.core.events import (AlarmRaised, EventBus, PacketDecoded, PacketMalformed,
                                    PacketReceived, SequenceGap)

log = logging.getLogger(__name__)

_NUMERIC = {
    "uint8": ">B", "int8": ">b", "uint16": ">H", "int16": ">h",
    "uint32": ">I", "int32": ">i", "float32": ">f",
}
_TYPES = set(_NUMERIC) | {"string", "bytes"}


class TelemetryDefError(ValueError):
    """Invalid telemetry_defs.yaml."""


@dataclass(frozen=True)
class FieldDef:
    name: str
    type: str
    unit: str | None = None
    scale: float = 1.0
    offset: float = 0.0
    alarm_low: float | None = None
    alarm_high: float | None = None
    length: int | None = None
    encoding: str = "utf-8"


@dataclass(frozen=True)
class ApidDef:
    apid: int
    name: str
    fields: tuple[FieldDef, ...]


@dataclass
class DecodedField:
    name: str
    value: Any
    unit: str | None
    alarm: str | None  # "nominal" | "low" | "high" | None (no thresholds)
    raw: bytes


@dataclass
class DecodedPacket:
    apid: int
    apid_name: str
    fields: list[DecodedField] = field(default_factory=list)
    unknown_apid: bool = False
    partial: bool = False
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {f.name: f.value for f in self.fields}


def _parse_field(apid_key: str, raw: dict) -> FieldDef:
    where = f"{apid_key}.fields[{raw.get('name', '?')}]"
    if not isinstance(raw, dict) or "name" not in raw or "type" not in raw:
        raise TelemetryDefError(f"{where}: each field needs 'name' and 'type'")
    t = str(raw["type"])
    if t not in _TYPES:
        raise TelemetryDefError(f"{where}: unknown type {t!r}")
    if t in _NUMERIC and "length" in raw:
        raise TelemetryDefError(f"{where}: 'length' is only valid for string/bytes")
    if t not in _NUMERIC and ("scale" in raw or "offset" in raw):
        raise TelemetryDefError(f"{where}: 'scale'/'offset' only valid for numeric types")
    return FieldDef(
        name=str(raw["name"]), type=t, unit=raw.get("unit"),
        scale=float(raw.get("scale", 1.0)), offset=float(raw.get("offset", 0.0)),
        alarm_low=raw.get("alarm_low"), alarm_high=raw.get("alarm_high"),
        length=raw.get("length"), encoding=str(raw.get("encoding", "utf-8")),
    )


def load_definitions(path: str | Path) -> dict[int, ApidDef]:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    defs: dict[int, ApidDef] = {}
    for key, body in data.items():
        if not str(key).startswith("apid_"):
            raise TelemetryDefError(f"top-level key {key!r} must look like apid_<n>")
        try:
            apid = int(str(key)[5:])
        except ValueError as e:
            raise TelemetryDefError(f"bad apid in key {key!r}") from e
        body = body or {}
        fields = tuple(_parse_field(str(key), f) for f in (body.get("fields") or []))
        defs[apid] = ApidDef(apid=apid, name=str(body.get("name", f"APID {apid}")), fields=fields)
    return defs


def _alarm(value: float, fd: FieldDef) -> str | None:
    if fd.alarm_low is None and fd.alarm_high is None:
        return None
    if fd.alarm_low is not None and value < fd.alarm_low:
        return "low"
    if fd.alarm_high is not None and value > fd.alarm_high:
        return "high"
    return "nominal"


def decode_payload(apid_def: ApidDef, payload: bytes) -> DecodedPacket:
    out = DecodedPacket(apid=apid_def.apid, apid_name=apid_def.name)
    pos = 0
    for fd in apid_def.fields:
        if fd.type in _NUMERIC:
            fmt = _NUMERIC[fd.type]
            size = struct.calcsize(fmt)
            chunk = payload[pos:pos + size]
            if len(chunk) < size:
                out.partial, out.error = True, f"payload exhausted at field {fd.name!r}"
                break
            value = struct.unpack(fmt, chunk)[0] * fd.scale + fd.offset
            if fd.type != "float32" and fd.scale == 1.0 and fd.offset == 0.0:
                value = int(value)
            out.fields.append(DecodedField(fd.name, value, fd.unit, _alarm(value, fd), chunk))
        else:
            chunk = payload[pos:] if fd.length is None else payload[pos:pos + fd.length]
            if fd.length is not None and len(chunk) < fd.length:
                out.partial, out.error = True, f"payload exhausted at field {fd.name!r}"
                break
            size = len(chunk)
            value: Any = chunk.decode(fd.encoding, errors="replace") if fd.type == "string" else bytes(chunk)
            out.fields.append(DecodedField(fd.name, value, fd.unit, None, chunk))
        pos += size
    return out


class TelemetryDecoder:
    def __init__(self, bus: EventBus, defs_path: str | Path, ccsds_cfg: CCSDSConfig) -> None:
        self._bus = bus
        self._cfg = ccsds_cfg
        self.definitions = load_definitions(defs_path)
        self._tracker = ccsds.SequenceTracker(ccsds_cfg.sequence_scope)  # type: ignore[arg-type]
        self.last_values: dict[int, DecodedPacket] = {}
        log.info("telemetry: loaded %d APID definitions", len(self.definitions))

    def start(self) -> None:
        self._bus.subscribe(PacketReceived, self._on_packet)

    def stop(self) -> None:
        self._bus.unsubscribe(PacketReceived, self._on_packet)

    def decode(self, packet: ccsds.CCSDSPacket) -> DecodedPacket:
        apid_def = self.definitions.get(packet.apid)
        if apid_def is None:
            return DecodedPacket(
                apid=packet.apid, apid_name="UNKNOWN", unknown_apid=True,
                fields=[DecodedField("raw_hex", packet.payload.hex(), None, None, packet.payload)],
            )
        return decode_payload(apid_def, packet.payload)

    async def _on_packet(self, ev: PacketReceived) -> None:
        try:
            packet = ccsds.parse(ev.raw, length_includes_crc=self._cfg.length_includes_crc)
        except ccsds.CCSDSError as e:
            log.warning("telemetry: malformed packet %s: %s", ev.raw.hex(), e)
            self._bus.publish(PacketMalformed(source=ev, reason=str(e)))
            return
        missed = self._tracker.observe(packet)
        if missed:
            expected = (packet.sequence_count - missed) & 0x3FFF
            log.warning("telemetry: APID %d gap: expected seq %d, got %d (%d missed)",
                        packet.apid, expected, packet.sequence_count, missed)
            self._bus.publish(SequenceGap(apid=packet.apid, expected=expected,
                                          received=packet.sequence_count, missed=missed))
        decoded = self.decode(packet)
        self.last_values[packet.apid] = decoded
        self._bus.publish(PacketDecoded(source=ev, packet=packet, decoded=decoded))
        for f in decoded.fields:
            if f.alarm in ("low", "high"):
                fd = next(x for x in self.definitions[packet.apid].fields if x.name == f.name)
                threshold = fd.alarm_low if f.alarm == "low" else fd.alarm_high
                self._bus.publish(AlarmRaised(source=ev, apid=packet.apid, field_name=f.name,
                                              value=f.value, threshold=float(threshold),
                                              alarm_type=f.alarm))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_telemetry.py -q`
Expected: 7 passed

- [ ] **Step 6: Commit**

```bash
git add cubesat_gs/core/telemetry.py cubesat_gs/config/telemetry_defs.yaml cubesat_gs/tests/test_telemetry.py
git commit -m "Add YAML-driven telemetry decoder with alarms and gap detection"
```

---

### Task 9: Telecommand manager

**Files:**
- Create: `cubesat_gs/core/telecommand.py`, `cubesat_gs/config/commands.yaml`
- Test: `cubesat_gs/tests/test_telecommand.py`

**Interfaces:**
- Consumes: `SerialHandler.send_tx` (+ `SerialCommandTimeout`, `SerialDisconnected`), `FrequencyManager.mode` / `Mode`, `ccsds.PacketBuilder`, `ccsds.peek_apid_seq`, `CommandConfig`, events `PacketReceived, CommandCompleted`, `EventBus.wait_for`.
- Produces: `CommandDef(name, description, apid, payload: bytes, response_apid: int | None, timeout: float, critical: bool)`; `CommandRecord(ts, name, raw_hex, status, response_hex, latency_ms, attempts, error)` with `as_dict()`; exceptions `CommandBusyError`, `WrongModeError`, `UnknownCommandError`; `load_commands(path, default_timeout) -> dict[str, CommandDef]`; `TelecommandManager(bus, serial, freq_mgr, builder, cfg: CommandConfig, registry_path)` with `commands`, `history: deque[CommandRecord]`, `pending: CommandRecord | None`, `async send_command(name, *, confirm=False, payload_override=None) -> CommandRecord`, `async send_raw(hex_str) -> CommandRecord`.

- [ ] **Step 1: Create the registry file**

`cubesat_gs/config/commands.yaml`:
```yaml
# Telecommand registry. payload: UTF-8 string, or hex prefixed with 0x (e.g. "0x01FF").
# response_apid: APID expected in reply (null = fire-and-forget, completes on modem TX ack).
# critical: true requires confirm=True from the caller (dashboard shows a confirmation dialog).
commands:
  - name: PING
    description: "Liveness check; satellite answers PONG_DATA_<value> on APID 101"
    apid: 100
    payload: "PING"
    response_apid: 101
    timeout: 10
    critical: false
```

- [ ] **Step 2: Write the failing tests**

`cubesat_gs/tests/test_telecommand.py`:
```python
import asyncio
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
    conf = CommandConfig(max_retries=cfg.pop("max_retries", 1), retry_backoff=0.01, **cfg)
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
    rec = await m.send_raw("DEADBEEF")
    assert rec.name == "RAW" and rec.status == "acked" and ser.sent[-1] == b"\xde\xad\xbe\xef"
    with pytest.raises(ValueError):
        await m.send_raw("XYZ")
    rec = await m.send_command("PING", payload_override=b"PING2")
    assert ser.sent[-1][6:] == b"PING2" and rec.status == "responded"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_telecommand.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Implement telecommand.py**

`cubesat_gs/core/telecommand.py`:
```python
"""Telecommand registry, sending with retry, and response correlation."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import CommandConfig
from cubesat_gs.core.events import CommandCompleted, EventBus, PacketReceived, now
from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.serial_handler import SerialCommandTimeout, SerialDisconnected

log = logging.getLogger(__name__)


class CommandBusyError(Exception):
    """Another command is still waiting for its response."""


class WrongModeError(Exception):
    """Frequency manager is not in TCTM mode."""


class UnknownCommandError(KeyError):
    """Command name not in the registry."""


@dataclass(frozen=True)
class CommandDef:
    name: str
    description: str
    apid: int
    payload: bytes
    response_apid: int | None
    timeout: float
    critical: bool


@dataclass
class CommandRecord:
    ts: datetime
    name: str
    raw_hex: str
    status: str  # acked | responded | timeout | failed | refused
    response_hex: str | None = None
    latency_ms: float | None = None
    attempts: int = 0
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ts"] = self.ts.isoformat()
        return d


def _payload_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    s = "" if value is None else str(value)
    if s.lower().startswith("0x"):
        return bytes.fromhex(s[2:])
    return s.encode("utf-8")


def load_commands(path: str | Path, default_timeout: float) -> dict[str, CommandDef]:
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out: dict[str, CommandDef] = {}
    for i, c in enumerate(data.get("commands") or []):
        if not isinstance(c, dict) or "name" not in c or "apid" not in c:
            raise ValueError(f"{path}: commands[{i}] needs 'name' and 'apid'")
        name = str(c["name"])
        if name in out:
            raise ValueError(f"{path}: duplicate command {name!r}")
        out[name] = CommandDef(
            name=name, description=str(c.get("description", "")), apid=int(c["apid"]),
            payload=_payload_bytes(c.get("payload", "")),
            response_apid=None if c.get("response_apid") is None else int(c["response_apid"]),
            timeout=float(c.get("timeout", default_timeout)), critical=bool(c.get("critical", False)),
        )
    return out


class TelecommandManager:
    def __init__(self, bus: EventBus, serial, freq_mgr, builder: ccsds.PacketBuilder,
                 cfg: CommandConfig, registry_path: str | Path) -> None:
        self._bus = bus
        self._serial = serial
        self._freq = freq_mgr
        self._builder = builder
        self._cfg = cfg
        self.commands = load_commands(registry_path, cfg.default_timeout)
        self.history: deque[CommandRecord] = deque(maxlen=cfg.history_size)
        self.pending: CommandRecord | None = None
        log.info("telecommand: %d commands loaded", len(self.commands))

    # ---- public
    async def send_command(self, name: str, *, confirm: bool = False,
                           payload_override: bytes | None = None) -> CommandRecord:
        cdef = self.commands.get(name)
        if cdef is None:
            raise UnknownCommandError(name)
        payload = cdef.payload if payload_override is None else payload_override
        if cdef.critical and not confirm:
            rec = CommandRecord(now(), name, payload.hex().upper(), "refused",
                                error="critical command requires confirm=True")
            self._finish(rec)
            return rec
        return await self._execute(cdef.name, self._builder.build(cdef.apid, payload),
                                   cdef.response_apid, cdef.timeout)

    async def send_raw(self, hex_str: str) -> CommandRecord:
        try:
            raw = bytes.fromhex(hex_str.replace(" ", ""))
        except ValueError as e:
            raise ValueError(f"invalid hex: {hex_str!r}") from e
        return await self._execute("RAW", raw, None, self._cfg.default_timeout)

    # ---- core
    async def _execute(self, name: str, raw: bytes, response_apid: int | None,
                       timeout: float) -> CommandRecord:
        if self._freq.mode is not Mode.TCTM:
            raise WrongModeError(f"frequency mode is {self._freq.mode.value}, need tctm")
        if self.pending is not None:
            raise CommandBusyError(f"{self.pending.name} still pending")
        rec = CommandRecord(now(), name, raw.hex().upper(), "failed")
        self.pending = rec
        try:
            for attempt in range(1, self._cfg.max_retries + 2):
                rec.attempts = attempt
                try:
                    await self._serial.send_tx(raw)
                except (SerialCommandTimeout, SerialDisconnected) as e:
                    rec.status, rec.error = "failed", f"{type(e).__name__}: {e}"
                    break
                t0 = time.monotonic()
                if response_apid is None:
                    rec.status = "acked"
                    break
                try:
                    ev = await self._bus.wait_for(
                        PacketReceived, lambda e: _apid_of(e.raw) == response_apid, timeout)
                except asyncio.TimeoutError:
                    rec.status, rec.error = "timeout", f"no APID {response_apid} within {timeout}s"
                    if attempt <= self._cfg.max_retries:
                        delay = self._cfg.retry_backoff ** (attempt - 1)
                        log.warning("telecommand: %s attempt %d timed out, retrying in %.2fs", name, attempt, delay)
                        await asyncio.sleep(delay)
                    continue
                rec.status = "responded"
                rec.error = None
                rec.response_hex = ev.raw.hex().upper()
                rec.latency_ms = (time.monotonic() - t0) * 1000.0
                break
        finally:
            self.pending = None
        self._finish(rec)
        return rec

    def _finish(self, rec: CommandRecord) -> None:
        self.history.append(rec)
        log.info("telecommand: %s -> %s (attempts=%d, latency=%s)", rec.name, rec.status,
                 rec.attempts, rec.latency_ms)
        self._bus.publish(CommandCompleted(record=rec))


def _apid_of(raw: bytes) -> int | None:
    peek = ccsds.peek_apid_seq(raw)
    return None if peek is None else peek[0]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_telecommand.py -q`
Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add cubesat_gs/core/telecommand.py cubesat_gs/config/commands.yaml cubesat_gs/tests/test_telecommand.py
git commit -m "Add telecommand manager with registry, retry and response correlation"
```

---
### Task 10: SQLite backend

**Files:**
- Create: `cubesat_gs/storage/sqlite_backend.py`
- Test: `cubesat_gs/tests/test_sqlite_backend.py`

**Interfaces:**
- Produces: `COLLECTIONS = ("raw_packets", "decoded_telemetry", "commands", "sessions", "alarms")`, `TIME_FIELD = {"sessions": "start_time"}` (all others use `"timestamp"`); `SQLiteBackend(path: str | Path)` with `async connect()`, `async close()`, `async ping() -> bool`, `async insert(collection, doc) -> str`, `async insert_many(collection, docs) -> list[str]`, `async update(collection, id, fields) -> None`, `async get(collection, id) -> dict | None`, `async query(collection, *, start=None, end=None, apid=None, limit=100) -> list[dict]` (newest first, each dict includes `"id"`), `async iterate(collection, *, start=None, end=None, apid=None, batch=500) -> AsyncIterator[dict]` (oldest first), `async count(collection) -> int`, `async unsynced(collection, limit) -> list[tuple[int, dict]]`, `async mark_synced(collection, ids: list[int], mongo_ids: list[str])`, `async mongo_id_for(collection, id: int) -> str | None`, `async purge_synced_older_than(days: int) -> int`.
- Storage model: one table per collection, all with the same shape: `id INTEGER PRIMARY KEY, ts TEXT NOT NULL, apid INTEGER, doc TEXT NOT NULL (JSON), synced INTEGER DEFAULT 0, mongo_id TEXT`. `ts` is the ISO-8601 UTC string of the doc's time field. `datetime` values inside docs are serialised to ISO strings; `bytes` to hex.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_sqlite_backend.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest

from cubesat_gs.storage.sqlite_backend import COLLECTIONS, SQLiteBackend


def _t(minutes=0):
    return datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


@pytest.fixture
async def db(tmp_path):
    b = SQLiteBackend(tmp_path / "sub" / "gs.db")  # parent dir must be created
    await b.connect()
    yield b
    await b.close()


async def test_tables_created_and_ping(db):
    assert await db.ping() is True
    for c in COLLECTIONS:
        assert await db.count(c) == 0


async def test_insert_get_query_order_and_filters(db):
    i1 = await db.insert("raw_packets", {"timestamp": _t(0), "apid": 10, "raw_hex": "AA", "rssi": None})
    i2 = await db.insert("raw_packets", {"timestamp": _t(5), "apid": 101, "raw_hex": "BB"})
    i3 = await db.insert("raw_packets", {"timestamp": _t(10), "apid": 10, "raw_hex": "CC"})
    assert [i1, i2, i3] == ["1", "2", "3"]
    got = await db.get("raw_packets", "2")
    assert got["raw_hex"] == "BB" and got["id"] == "2" and got["timestamp"] == _t(5).isoformat()
    rows = await db.query("raw_packets")
    assert [r["raw_hex"] for r in rows] == ["CC", "BB", "AA"]
    rows = await db.query("raw_packets", apid=10)
    assert [r["raw_hex"] for r in rows] == ["CC", "AA"]
    rows = await db.query("raw_packets", start=_t(1), end=_t(6))
    assert [r["raw_hex"] for r in rows] == ["BB"]
    rows = await db.query("raw_packets", limit=1)
    assert [r["raw_hex"] for r in rows] == ["CC"]
    assert [r["raw_hex"] async for r in db.iterate("raw_packets", batch=2)] == ["AA", "BB", "CC"]


async def test_sessions_use_start_time_and_update(db):
    sid = await db.insert("sessions", {"start_time": _t(0), "end_time": None, "packets_received": 0})
    await db.update("sessions", sid, {"end_time": _t(30), "packets_received": 7})
    s = await db.get("sessions", sid)
    assert s["packets_received"] == 7 and s["end_time"] == _t(30).isoformat()
    assert (await db.query("sessions"))[0]["id"] == sid


async def test_bytes_and_nested_values_serialised(db):
    i = await db.insert("commands", {"timestamp": _t(), "raw_hex_sent": b"\x01", "meta": {"a": [1, 2]}})
    got = await db.get("commands", i)
    assert got["raw_hex_sent"] == "01" and got["meta"] == {"a": [1, 2]}


async def test_sync_bookkeeping(db):
    ids = await db.insert_many("alarms", [{"timestamp": _t(i), "apid": 5, "v": i} for i in range(3)])
    assert ids == ["1", "2", "3"]
    pending = await db.unsynced("alarms", limit=2)
    assert [i for i, _ in pending] == [1, 2] and pending[0][1]["v"] == 0
    await db.mark_synced("alarms", [1, 2], ["aaa", "bbb"])
    assert [i for i, _ in await db.unsynced("alarms", limit=10)] == [3]
    assert await db.mongo_id_for("alarms", 2) == "bbb"
    assert await db.mongo_id_for("alarms", 3) is None


async def test_purge_only_synced_old_rows(db):
    old = datetime.now(timezone.utc) - timedelta(days=400)
    a = await db.insert("raw_packets", {"timestamp": old, "apid": 1})
    b = await db.insert("raw_packets", {"timestamp": old, "apid": 1})
    c = await db.insert("raw_packets", {"timestamp": datetime.now(timezone.utc), "apid": 1})
    await db.mark_synced("raw_packets", [int(a), int(c)], ["x", "y"])
    assert await db.purge_synced_older_than(365) == 1
    assert {r["id"] for r in await db.query("raw_packets")} == {b, c}


async def test_unknown_collection_rejected(db):
    with pytest.raises(ValueError):
        await db.insert("nope", {"timestamp": _t()})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_sqlite_backend.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement sqlite_backend.py**

`cubesat_gs/storage/sqlite_backend.py`:
```python
"""Local SQLite store: offline fallback and sync buffer for MongoDB Atlas."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

log = logging.getLogger(__name__)

COLLECTIONS = ("raw_packets", "decoded_telemetry", "commands", "sessions", "alarms")
TIME_FIELD = {"sessions": "start_time"}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS {t} (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    apid INTEGER,
    doc TEXT NOT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    mongo_id TEXT
);
CREATE INDEX IF NOT EXISTS {t}_ts ON {t}(ts);
CREATE INDEX IF NOT EXISTS {t}_apid_ts ON {t}(apid, ts);
CREATE INDEX IF NOT EXISTS {t}_synced ON {t}(synced);
"""


def _check(collection: str) -> str:
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}")
    return collection


def time_field(collection: str) -> str:
    return TIME_FIELD.get(collection, "timestamp")


def to_jsonable(value: Any) -> Any:
    """datetime -> ISO string, bytes -> hex, recursively."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex().upper()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return str(value)


class SQLiteBackend:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._db: aiosqlite.Connection | None = None

    # ---- lifecycle
    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        for t in COLLECTIONS:
            await self._db.executescript(_SCHEMA.format(t=t))
        await self._db.commit()
        log.info("sqlite: using %s", self.path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def ping(self) -> bool:
        try:
            await self._conn.execute("SELECT 1")
            return True
        except Exception:  # noqa: BLE001
            return False

    @property
    def _conn(self) -> aiosqlite.Connection:
        assert self._db is not None, "SQLiteBackend not connected"
        return self._db

    # ---- writes
    def _row(self, collection: str, doc: dict) -> tuple[str, int | None, str]:
        doc = to_jsonable(doc)
        ts = _iso(doc.get(time_field(collection)))
        apid = doc.get("apid")
        return ts, (int(apid) if apid is not None else None), json.dumps(doc)

    async def insert(self, collection: str, doc: dict) -> str:
        t = _check(collection)
        cur = await self._conn.execute(
            f"INSERT INTO {t}(ts, apid, doc) VALUES (?, ?, ?)", self._row(t, doc))
        await self._conn.commit()
        return str(cur.lastrowid)

    async def insert_many(self, collection: str, docs: list[dict]) -> list[str]:
        ids = []
        for d in docs:
            ids.append(await self.insert(collection, d))
        return ids

    async def update(self, collection: str, id: str, fields: dict) -> None:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT doc FROM {t} WHERE id = ?", (int(id),))
        row = await cur.fetchone()
        if row is None:
            return
        doc = json.loads(row["doc"])
        doc.update(to_jsonable(fields))
        ts, apid, text = self._row(t, doc)
        await self._conn.execute(f"UPDATE {t} SET ts = ?, apid = ?, doc = ? WHERE id = ?",
                                 (ts, apid, text, int(id)))
        await self._conn.commit()

    # ---- reads
    @staticmethod
    def _load(row: aiosqlite.Row) -> dict:
        doc = json.loads(row["doc"])
        doc["id"] = str(row["id"])
        return doc

    async def get(self, collection: str, id: str) -> dict | None:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT id, doc FROM {t} WHERE id = ?", (int(id),))
        row = await cur.fetchone()
        return self._load(row) if row else None

    @staticmethod
    def _where(start, end, apid) -> tuple[str, list]:
        clauses, params = [], []
        if start is not None:
            clauses.append("ts >= ?"); params.append(_iso(start))
        if end is not None:
            clauses.append("ts <= ?"); params.append(_iso(end))
        if apid is not None:
            clauses.append("apid = ?"); params.append(int(apid))
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    async def query(self, collection: str, *, start=None, end=None, apid=None, limit: int = 100) -> list[dict]:
        t = _check(collection)
        where, params = self._where(start, end, apid)
        cur = await self._conn.execute(
            f"SELECT id, doc FROM {t}{where} ORDER BY ts DESC, id DESC LIMIT ?", [*params, int(limit)])
        return [self._load(r) for r in await cur.fetchall()]

    async def iterate(self, collection: str, *, start=None, end=None, apid=None,
                      batch: int = 500) -> AsyncIterator[dict]:
        t = _check(collection)
        where, params = self._where(start, end, apid)
        last_id = 0
        while True:
            sep = " AND " if where else " WHERE "
            cur = await self._conn.execute(
                f"SELECT id, doc FROM {t}{where}{sep}id > ? ORDER BY id LIMIT ?", [*params, last_id, batch])
            rows = await cur.fetchall()
            if not rows:
                return
            for r in rows:
                last_id = r["id"]
                yield self._load(r)

    async def count(self, collection: str) -> int:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT COUNT(*) AS n FROM {t}")
        return (await cur.fetchone())["n"]

    # ---- sync bookkeeping
    async def unsynced(self, collection: str, limit: int) -> list[tuple[int, dict]]:
        t = _check(collection)
        cur = await self._conn.execute(
            f"SELECT id, doc FROM {t} WHERE synced = 0 ORDER BY id LIMIT ?", (int(limit),))
        return [(r["id"], json.loads(r["doc"])) for r in await cur.fetchall()]

    async def mark_synced(self, collection: str, ids: list[int], mongo_ids: list[str]) -> None:
        t = _check(collection)
        await self._conn.executemany(
            f"UPDATE {t} SET synced = 1, mongo_id = ? WHERE id = ?",
            [(m, int(i)) for i, m in zip(ids, mongo_ids)])
        await self._conn.commit()

    async def mongo_id_for(self, collection: str, id: int) -> str | None:
        t = _check(collection)
        cur = await self._conn.execute(f"SELECT mongo_id FROM {t} WHERE id = ?", (int(id),))
        row = await cur.fetchone()
        return row["mongo_id"] if row else None

    async def purge_synced_older_than(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        total = 0
        for t in COLLECTIONS:
            cur = await self._conn.execute(f"DELETE FROM {t} WHERE synced = 1 AND ts < ?", (cutoff,))
            total += cur.rowcount
        await self._conn.commit()
        return total
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_sqlite_backend.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/storage/sqlite_backend.py cubesat_gs/tests/test_sqlite_backend.py
git commit -m "Add SQLite backend with sync bookkeeping"
```

---

### Task 11: Mongo backend and fake client

**Files:**
- Create: `cubesat_gs/storage/mongo_backend.py`, `cubesat_gs/tests/fakes.py`
- Test: `cubesat_gs/tests/test_mongo_backend.py`

**Interfaces:**
- Consumes: `COLLECTIONS`, `time_field`, `to_jsonable` from Task 10 (Mongo stores `datetime` natively — only `bytes` are hex-encoded, via `to_bsonable`).
- Produces: `MongoBackend(uri, db_name, retention_days, client_factory=None)` with the same method names as `SQLiteBackend` for `connect, close, ping, insert, insert_many, update, get, query, iterate, count`, plus `ensure_indexes()`. Ids are `str(ObjectId)`. All methods let `pymongo.errors.PyMongoError` propagate (the facade decides what to do). `FakeMotorClient(fail=False)` in `tests/fakes.py` emulating the subset of motor used here; setting `client.fail = True` makes every operation raise `pymongo.errors.AutoReconnect`.

- [ ] **Step 1: Write the fake motor client**

`cubesat_gs/tests/fakes.py`:
```python
"""In-memory stand-in for motor's AsyncIOMotorClient covering what mongo_backend.py uses."""
from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo.errors import AutoReconnect


class _Cursor:
    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, key: str, direction: int):
        self._docs = sorted(self._docs, key=lambda d: d.get(key), reverse=direction < 0)
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration

    async def to_list(self, length=None):
        return list(self._docs)


class _Result:
    def __init__(self, inserted_id=None, inserted_ids=None):
        self.inserted_id = inserted_id
        self.inserted_ids = inserted_ids or []


def _match(doc: dict, flt: dict) -> bool:
    for k, v in flt.items():
        if isinstance(v, dict):
            x = doc.get(k)
            if "$gte" in v and (x is None or x < v["$gte"]):
                return False
            if "$lte" in v and (x is None or x > v["$lte"]):
                return False
        elif doc.get(k) != v:
            return False
    return True


class FakeCollection:
    def __init__(self, client: "FakeMotorClient"):
        self._client = client
        self.docs: list[dict] = []
        self.indexes: list[tuple] = []

    def _guard(self):
        if self._client.fail:
            raise AutoReconnect("fake: connection lost")

    async def insert_one(self, doc: dict) -> _Result:
        self._guard()
        d = dict(doc); d.setdefault("_id", ObjectId())
        self.docs.append(d)
        return _Result(inserted_id=d["_id"])

    async def insert_many(self, docs: list[dict], ordered=True) -> _Result:
        self._guard()
        ids = [(await self.insert_one(d)).inserted_id for d in docs]
        return _Result(inserted_ids=ids)

    async def update_one(self, flt: dict, update: dict):
        self._guard()
        for d in self.docs:
            if _match(d, flt):
                d.update(update.get("$set", {}))
                return

    async def find_one(self, flt: dict):
        self._guard()
        return next((dict(d) for d in self.docs if _match(d, flt)), None)

    def find(self, flt: dict | None = None) -> _Cursor:
        self._guard()
        return _Cursor([dict(d) for d in self.docs if _match(d, flt or {})])

    async def count_documents(self, flt: dict) -> int:
        self._guard()
        return sum(1 for d in self.docs if _match(d, flt))

    async def create_index(self, keys, **kwargs):
        self._guard()
        self.indexes.append((keys, kwargs))
        return "idx"


class FakeDatabase:
    def __init__(self, client):
        self._client = client
        self._colls: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self._colls.setdefault(name, FakeCollection(self._client))


class _Admin:
    def __init__(self, client):
        self._client = client

    async def command(self, name: str) -> dict:
        if self._client.fail:
            raise AutoReconnect("fake: ping failed")
        return {"ok": 1}


class FakeMotorClient:
    def __init__(self, *args: Any, fail: bool = False, **kwargs: Any):
        self.fail = fail
        self.admin = _Admin(self)
        self._dbs: dict[str, FakeDatabase] = {}
        self.closed = False

    def __getitem__(self, name: str) -> FakeDatabase:
        return self._dbs.setdefault(name, FakeDatabase(self))

    def close(self):
        self.closed = True
```

- [ ] **Step 2: Write the failing tests**

`cubesat_gs/tests/test_mongo_backend.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import PyMongoError

from cubesat_gs.storage.mongo_backend import MongoBackend
from cubesat_gs.tests.fakes import FakeMotorClient


def _t(m=0):
    return datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=m)


@pytest.fixture
async def mb():
    client = FakeMotorClient()
    b = MongoBackend("mongodb://fake", "cubesat_gs", retention_days=30, client_factory=lambda uri: client)
    await b.connect()
    yield client, b
    await b.close()


async def test_connect_creates_indexes(mb):
    client, b = mb
    db = client["cubesat_gs"]
    names = {c: [k for k, _ in db[c].indexes] for c in ("raw_packets", "decoded_telemetry", "commands", "sessions", "alarms")}
    for c in names:
        assert [("timestamp" if c != "sessions" else "start_time", -1)] in names[c]
    assert [("apid", 1)] in names["raw_packets"] and [("apid", 1), ("timestamp", 1)] in names["decoded_telemetry"]
    ttl = [kw for k, kw in db["raw_packets"].indexes if kw.get("expireAfterSeconds")]
    assert ttl and ttl[0]["expireAfterSeconds"] == 30 * 86400
    assert await b.ping() is True


async def test_insert_get_query_iterate_count(mb):
    client, b = mb
    i1 = await b.insert("raw_packets", {"timestamp": _t(0), "apid": 10, "raw_hex": b"\xaa"})
    i2 = await b.insert("raw_packets", {"timestamp": _t(5), "apid": 101, "raw_hex": "BB"})
    assert len(i1) == 24
    got = await b.get("raw_packets", i1)
    assert got["raw_hex"] == "AA" and got["id"] == i1 and "_id" not in got
    rows = await b.query("raw_packets")
    assert [r["raw_hex"] for r in rows] == ["BB", "AA"]
    assert [r["id"] for r in await b.query("raw_packets", apid=101)] == [i2]
    assert [r["id"] for r in await b.query("raw_packets", start=_t(1))] == [i2]
    assert [r["raw_hex"] async for r in b.iterate("raw_packets")] == ["AA", "BB"]
    assert await b.count("raw_packets") == 2
    ids = await b.insert_many("alarms", [{"timestamp": _t(), "apid": 1}, {"timestamp": _t(), "apid": 2}])
    assert len(ids) == 2 and await b.count("alarms") == 2


async def test_update_and_session_time_field(mb):
    client, b = mb
    sid = await b.insert("sessions", {"start_time": _t(0), "end_time": None})
    await b.update("sessions", sid, {"end_time": _t(9)})
    assert (await b.get("sessions", sid))["end_time"] == _t(9)
    assert (await b.query("sessions"))[0]["id"] == sid


async def test_errors_propagate(mb):
    client, b = mb
    client.fail = True
    assert await b.ping() is False
    with pytest.raises(PyMongoError):
        await b.insert("raw_packets", {"timestamp": _t()})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_mongo_backend.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cubesat_gs.storage.mongo_backend'`

- [ ] **Step 4: Implement mongo_backend.py**

`cubesat_gs/storage/mongo_backend.py`:
```python
"""MongoDB Atlas backend (motor). Errors propagate as pymongo.errors.PyMongoError."""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from cubesat_gs.storage.sqlite_backend import COLLECTIONS, time_field

log = logging.getLogger(__name__)

_TTL_COLLECTIONS = ("raw_packets", "decoded_telemetry")
_APID_COLLECTIONS = ("raw_packets", "decoded_telemetry")


def to_bsonable(value: Any) -> Any:
    """bytes -> hex string, recursively; datetimes are kept (BSON native)."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex().upper()
    if isinstance(value, dict):
        return {k: to_bsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_bsonable(v) for v in value]
    return value


def _check(collection: str) -> str:
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}")
    return collection


def _public(doc: dict) -> dict:
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d


class MongoBackend:
    def __init__(self, uri: str, db_name: str, retention_days: int,
                 client_factory: Callable[[str], Any] | None = None) -> None:
        self._uri = uri
        self._db_name = db_name
        self._retention_days = retention_days
        self._factory = client_factory or self._default_factory
        self._client: Any = None
        self._db: Any = None

    @staticmethod
    def _default_factory(uri: str) -> Any:
        from motor.motor_asyncio import AsyncIOMotorClient
        return AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)

    # ---- lifecycle
    async def connect(self) -> None:
        self._client = self._factory(self._uri)
        self._db = self._client[self._db_name]
        await self._client.admin.command("ping")
        await self.ensure_indexes()
        log.info("mongo: connected to database %s", self._db_name)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    async def ping(self) -> bool:
        try:
            await self._client.admin.command("ping")
            return True
        except (PyMongoError, AttributeError):
            return False

    async def ensure_indexes(self) -> None:
        for c in COLLECTIONS:
            await self._db[c].create_index([(time_field(c), DESCENDING)])
        for c in _APID_COLLECTIONS:
            await self._db[c].create_index([("apid", ASCENDING)])
            await self._db[c].create_index([("apid", ASCENDING), ("timestamp", ASCENDING)])
        for c in _TTL_COLLECTIONS:
            await self._db[c].create_index(
                [("timestamp", ASCENDING)], name="ttl_timestamp",
                expireAfterSeconds=int(self._retention_days) * 86400)

    # ---- writes
    async def insert(self, collection: str, doc: dict) -> str:
        res = await self._db[_check(collection)].insert_one(to_bsonable(doc))
        return str(res.inserted_id)

    async def insert_many(self, collection: str, docs: list[dict]) -> list[str]:
        if not docs:
            return []
        res = await self._db[_check(collection)].insert_many([to_bsonable(d) for d in docs], ordered=True)
        return [str(i) for i in res.inserted_ids]

    async def update(self, collection: str, id: str, fields: dict) -> None:
        await self._db[_check(collection)].update_one({"_id": ObjectId(id)}, {"$set": to_bsonable(fields)})

    # ---- reads
    @staticmethod
    def _filter(collection: str, start, end, apid) -> dict:
        flt: dict = {}
        tf = time_field(collection)
        if start is not None or end is not None:
            rng = {}
            if start is not None:
                rng["$gte"] = start
            if end is not None:
                rng["$lte"] = end
            flt[tf] = rng
        if apid is not None:
            flt["apid"] = int(apid)
        return flt

    async def get(self, collection: str, id: str) -> dict | None:
        doc = await self._db[_check(collection)].find_one({"_id": ObjectId(id)})
        return _public(doc) if doc else None

    async def query(self, collection: str, *, start=None, end=None, apid=None, limit: int = 100) -> list[dict]:
        c = _check(collection)
        cur = self._db[c].find(self._filter(c, start, end, apid)).sort(time_field(c), DESCENDING).limit(int(limit))
        return [_public(d) async for d in cur]

    async def iterate(self, collection: str, *, start=None, end=None, apid=None,
                      batch: int = 500) -> AsyncIterator[dict]:
        c = _check(collection)
        cur = self._db[c].find(self._filter(c, start, end, apid)).sort(time_field(c), ASCENDING)
        async for d in cur:
            yield _public(d)

    async def count(self, collection: str) -> int:
        return await self._db[_check(collection)].count_documents({})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_mongo_backend.py -q`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add cubesat_gs/storage/mongo_backend.py cubesat_gs/tests/fakes.py cubesat_gs/tests/test_mongo_backend.py
git commit -m "Add MongoDB backend with index setup and in-memory fake client"
```

---
### Task 12: Storage facade — routing, fallback, sync, sessions

**Files:**
- Create: `cubesat_gs/storage/database.py`
- Test: `cubesat_gs/tests/test_storage.py`

**Interfaces:**
- Consumes: `SQLiteBackend`, `MongoBackend`, `FakeMotorClient`, `DatabaseConfig`, `ccsds.peek_apid_seq`, events `PacketReceived, PacketSent, PacketDecoded, AlarmRaised, CommandCompleted`.
- Produces: `Storage(bus, cfg: DatabaseConfig, base_dir: Path, *, mongo_client_factory=None, sync_interval=30.0, session_flush_interval=60.0)` with `async start()`, `async stop()`, `async health() -> dict`, `async query(collection, *, start=None, end=None, apid=None, limit=100) -> list[dict]`, `iterate(collection, *, start=None, end=None, apid=None, batch=500)` (async iterator, oldest first), `async stats() -> dict[str, int]`, `async sync_now() -> int` (rows uploaded), `session: dict` (in-memory current session doc), `async write(collection, doc, *, force_sqlite=False) -> tuple[str, str]` (returns `(backend, id)`, `backend` is `"mongo"` or `"sqlite"`), `packet_ref(source: PacketReceived) -> asyncio.Future[tuple[str, str]]`.
- Read routing: `query`/`iterate`/`stats` use Mongo when it is enabled and not degraded, else SQLite. (Live dashboards read the last N rows; the offline buffer is small and syncs quickly.)

Routing rules:
1. `mongo_uri` unset → everything to SQLite; `health()["mongo"] == "disabled"`.
2. Mongo enabled, healthy → write to Mongo. On `PyMongoError` → write the same doc to SQLite (`synced=0`), set `degraded=True`, log a warning once per outage.
3. `degraded=True` → write to SQLite directly.
4. `force_sqlite=True` → SQLite regardless (used for decoded/alarm rows whose raw packet went to SQLite, so `packet_id` references stay consistent and are remapped on sync).
5. Sync task (every `sync_interval` s while Mongo is enabled): if `degraded` or SQLite has unsynced rows → `ping()`; if ok, upload per collection in order `raw_packets, sessions, commands, decoded_telemetry, alarms`, batches of 200, remapping `packet_id` for `decoded_telemetry`/`alarms` via `mongo_id_for("raw_packets", int(packet_id))` (a row whose raw packet is not yet synced is skipped this round). After a full clean pass, `degraded=False`.
6. `packet_id` correlation: `_on_packet_received` creates a Future in `_refs[id(event)]` (bounded `OrderedDict`, 1000 entries), resolves it with `(backend, id)` after the raw insert. `_on_decoded`/`_on_alarm` await `packet_ref(source)` (with 5 s timeout, then `packet_id=None`).

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_storage.py`:
```python
import asyncio
from pathlib import Path

import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import (AlarmRaised, CommandCompleted, EventBus, PacketDecoded,
                                    PacketReceived, PacketSent)
from cubesat_gs.core.telecommand import CommandRecord
from cubesat_gs.core.telemetry import DecodedField, DecodedPacket
from cubesat_gs.core.events import now
from cubesat_gs.storage.database import Storage
from cubesat_gs.storage.sqlite_backend import SQLiteBackend
from cubesat_gs.tests.fakes import FakeMotorClient

BEACON = bytes.fromhex("000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C")


def _cfg(tmp_path, uri=None):
    return DatabaseConfig(db_name="cubesat_gs", retention_days=30,
                          local_fallback_path=str(tmp_path / "data" / "gs.db"), mongo_uri=uri)


async def _settle():
    await asyncio.sleep(0.05)


def _decoded(source):
    pkt = ccsds.parse(source.raw)
    dec = DecodedPacket(apid=10, apid_name="Beacon",
                        fields=[DecodedField("message", "VLEO_BEACON_SYS_NOMINAL", None, None, pkt.payload)])
    return PacketDecoded(source=source, packet=pkt, decoded=dec)


# ---- SQLite only

async def test_sqlite_only_flow(tmp_path):
    bus = EventBus()
    st = Storage(bus, _cfg(tmp_path), tmp_path, sync_interval=1000)
    await st.start()
    src = PacketReceived(raw=BEACON, rssi=-90.0, snr=7.0, freq_mhz=437.25)
    bus.publish(src)
    bus.publish(_decoded(src))
    bus.publish(AlarmRaised(source=src, apid=10, field_name="x", value=1.0, threshold=2.0, alarm_type="low"))
    bus.publish(PacketSent(raw=b"\x10\x64\xc0\x00\x00\x05PING", freq_mhz=435.5))
    bus.publish(CommandCompleted(record=CommandRecord(now(), "PING", "1064", "responded", "0065", 12.5, 1)))
    await _settle()

    h = await st.health()
    assert h["mongo"] == "disabled" and h["pending_sync"] == 0
    raw = await st.query("raw_packets")
    assert len(raw) == 2
    rx = [r for r in raw if r["direction"] == "rx"][0]
    assert rx["apid"] == 10 and rx["sequence_count"] == 0 and rx["rssi"] == -90.0 and rx["crc_valid"] is True
    assert rx["frequency_mhz"] == 437.25 and rx["raw_hex"] == BEACON.hex().upper()
    dec = await st.query("decoded_telemetry")
    assert dec[0]["field_name"] == "message" and dec[0]["packet_id"] == rx["id"] and dec[0]["apid_name"] == "Beacon"
    al = await st.query("alarms")
    assert al[0]["packet_id"] == rx["id"] and al[0]["alarm_type"] == "low"
    cmd = await st.query("commands")
    assert cmd[0]["command_name"] == "PING" and cmd[0]["response_received"] is True and cmd[0]["latency_ms"] == 12.5
    assert st.session["packets_received"] == 1 and st.session["packets_sent"] == 1
    stats = await st.stats()
    assert stats["raw_packets"] == 2 and stats["sessions"] == 1
    await st.stop()
    reopened = SQLiteBackend(tmp_path / "data" / "gs.db")  # storage is closed; read the file directly
    await reopened.connect()
    sess = await reopened.query("sessions")
    assert sess[0]["end_time"] is not None and sess[0]["packets_received"] == 1
    await reopened.close()


async def test_malformed_raw_still_stored(tmp_path):
    bus = EventBus()
    st = Storage(bus, _cfg(tmp_path), tmp_path, sync_interval=1000)
    await st.start()
    bus.publish(PacketReceived(raw=b"\x00\x0a", rssi=None, snr=None, freq_mhz=435.5))
    await _settle()
    r = (await st.query("raw_packets"))[0]
    assert r["apid"] is None and r["sequence_count"] is None and r["raw_hex"] == "000A"
    await st.stop()


# ---- Mongo with fallback and sync

async def test_mongo_primary_then_fallback_then_sync(tmp_path):
    bus = EventBus()
    client = FakeMotorClient()
    st = Storage(bus, _cfg(tmp_path, uri="mongodb://fake"), tmp_path,
                 mongo_client_factory=lambda uri: client, sync_interval=1000)
    await st.start()
    assert (await st.health())["mongo"] == "ok"

    src1 = PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25)
    bus.publish(src1); bus.publish(_decoded(src1))
    await _settle()
    assert len(client["cubesat_gs"]["raw_packets"].docs) == 1
    assert len(client["cubesat_gs"]["decoded_telemetry"].docs) == 1

    client.fail = True  # Atlas goes away
    src2 = PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25)
    bus.publish(src2); bus.publish(_decoded(src2))
    await _settle()
    h = await st.health()
    assert h["mongo"] == "degraded" and h["pending_sync"] == 2
    assert len(client["cubesat_gs"]["raw_packets"].docs) == 1
    local_raw = await st._sqlite.query("raw_packets")
    local_dec = await st._sqlite.query("decoded_telemetry")
    assert local_dec[0]["packet_id"] == local_raw[0]["id"]  # sqlite-local reference

    client.fail = False  # Atlas is back
    uploaded = await st.sync_now()
    assert uploaded == 2
    h = await st.health()
    assert h["mongo"] == "ok" and h["pending_sync"] == 0
    mongo_raw = client["cubesat_gs"]["raw_packets"].docs
    mongo_dec = client["cubesat_gs"]["decoded_telemetry"].docs
    assert len(mongo_raw) == 2 and len(mongo_dec) == 2
    synced_dec = [d for d in mongo_dec if d["packet_id"] == str(mongo_raw[1]["_id"])]
    assert len(synced_dec) == 1  # packet_id remapped to the new ObjectId

    src3 = PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25)
    bus.publish(src3)
    await _settle()
    assert len(mongo_raw) == 3  # back to writing Mongo directly
    await st.stop()
    assert client["cubesat_gs"]["sessions"].docs[0]["end_time"] is not None


async def test_mongo_unreachable_at_start_is_degraded_not_fatal(tmp_path):
    bus = EventBus()
    client = FakeMotorClient(fail=True)
    st = Storage(bus, _cfg(tmp_path, uri="mongodb://fake"), tmp_path,
                 mongo_client_factory=lambda uri: client, sync_interval=0.05)
    await st.start()
    assert (await st.health())["mongo"] == "degraded"
    bus.publish(PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25))
    await _settle()
    assert (await st.health())["pending_sync"] >= 1
    client.fail = False
    await asyncio.sleep(0.2)  # background sync task picks it up
    h = await st.health()
    assert h["mongo"] == "ok" and h["pending_sync"] == 0
    await st.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_storage.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cubesat_gs.storage.database'`

- [ ] **Step 3: Implement database.py**

`cubesat_gs/storage/database.py`:
```python
"""Storage facade: MongoDB Atlas primary with SQLite offline fallback and background sync."""
from __future__ import annotations

import asyncio
import logging
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from pymongo.errors import PyMongoError

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import (AlarmRaised, CommandCompleted, EventBus, PacketDecoded,
                                    PacketReceived, PacketSent, now)
from cubesat_gs.storage.mongo_backend import MongoBackend
from cubesat_gs.storage.sqlite_backend import COLLECTIONS, SQLiteBackend

log = logging.getLogger(__name__)

Ref = tuple[str, str]  # ("mongo" | "sqlite", id)
_SYNC_ORDER = ("raw_packets", "sessions", "commands", "decoded_telemetry", "alarms")
_PACKET_REF_COLLECTIONS = ("decoded_telemetry", "alarms")
_SYNC_BATCH = 200
_TIME_KEYS = ("timestamp", "start_time", "end_time")


def _restore_datetimes(doc: dict) -> None:
    """SQLite stores datetimes as ISO strings; Mongo wants real datetimes (TTL index, range queries)."""
    for k in _TIME_KEYS:
        v = doc.get(k)
        if isinstance(v, str):
            try:
                doc[k] = datetime.fromisoformat(v)
            except ValueError:
                pass


class Storage:
    def __init__(self, bus: EventBus, cfg: DatabaseConfig, base_dir: Path, *,
                 mongo_client_factory: Callable[[str], Any] | None = None,
                 sync_interval: float = 30.0, session_flush_interval: float = 60.0) -> None:
        self._bus = bus
        self._cfg = cfg
        p = Path(cfg.local_fallback_path)
        self._sqlite = SQLiteBackend(p if p.is_absolute() else Path(base_dir) / p)
        self._mongo: MongoBackend | None = (
            MongoBackend(cfg.mongo_uri, cfg.db_name, cfg.retention_days, mongo_client_factory)
            if cfg.mongo_uri else None)
        self._degraded = False
        self._sync_interval = sync_interval
        self._flush_interval = session_flush_interval
        self._refs: OrderedDict[int, asyncio.Future] = OrderedDict()
        self._tasks: list[asyncio.Task] = []
        self._sync_lock = asyncio.Lock()
        self.session: dict[str, Any] = {}
        self._session_ref: Ref | None = None

    # ---- lifecycle
    async def start(self) -> None:
        await self._sqlite.connect()
        purged = await self._sqlite.purge_synced_older_than(self._cfg.retention_days)
        if purged:
            log.info("sqlite: purged %d synced rows older than %d days", purged, self._cfg.retention_days)
        if self._mongo is not None:
            try:
                await self._mongo.connect()
            except PyMongoError as e:
                log.warning("mongo: unreachable at startup (%s); buffering to SQLite", e)
                self._degraded = True
            self._tasks.append(asyncio.create_task(self._sync_loop(), name="storage-sync"))
        else:
            log.info("mongo: MONGO_URI not set; SQLite only")
        self.session = {"start_time": now(), "end_time": None, "pass_id": None,
                        "packets_received": 0, "packets_sent": 0, "notes": ""}
        self._session_ref = await self.write("sessions", dict(self.session))
        self._tasks.append(asyncio.create_task(self._session_flush_loop(), name="storage-session"))
        for et, h in self._handlers():
            self._bus.subscribe(et, h)

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
        await self._bus.drain()
        self.session["end_time"] = now()
        await self._flush_session()
        if self._mongo is not None:
            await self._mongo.close()
        await self._sqlite.close()

    def _handlers(self):
        return ((PacketReceived, self._on_packet_received), (PacketSent, self._on_packet_sent),
                (PacketDecoded, self._on_decoded), (AlarmRaised, self._on_alarm),
                (CommandCompleted, self._on_command))

    # ---- routing
    @property
    def _reads(self):
        return self._mongo if (self._mongo is not None and not self._degraded) else self._sqlite

    async def write(self, collection: str, doc: dict, *, force_sqlite: bool = False) -> Ref:
        if self._mongo is not None and not self._degraded and not force_sqlite:
            try:
                return "mongo", await self._mongo.insert(collection, doc)
            except PyMongoError as e:
                log.warning("mongo: write failed (%s); switching to SQLite buffer", e)
                self._degraded = True
        return "sqlite", await self._sqlite.insert(collection, doc)

    async def _update(self, ref: Ref, collection: str, fields: dict) -> None:
        backend, id = ref
        if backend == "mongo":
            try:
                await self._mongo.update(collection, id, fields)
            except PyMongoError as e:
                log.warning("mongo: update of %s/%s failed: %s", collection, id, e)
            return
        await self._sqlite.update(collection, id, fields)
        mongo_id = await self._sqlite.mongo_id_for(collection, int(id))
        if mongo_id and self._mongo is not None and not self._degraded:
            try:
                await self._mongo.update(collection, mongo_id, fields)
            except PyMongoError:
                pass  # the SQLite copy is authoritative until next sync anyway

    # ---- reads
    async def query(self, collection: str, *, start=None, end=None, apid=None, limit: int = 100) -> list[dict]:
        return await self._reads.query(collection, start=start, end=end, apid=apid, limit=limit)

    async def iterate(self, collection: str, *, start=None, end=None, apid=None,
                      batch: int = 500) -> AsyncIterator[dict]:
        async for d in self._reads.iterate(collection, start=start, end=end, apid=apid, batch=batch):
            yield d

    async def stats(self) -> dict[str, int]:
        return {c: await self._reads.count(c) for c in COLLECTIONS}

    async def health(self) -> dict[str, Any]:
        pending = 0
        for c in COLLECTIONS:
            pending += len(await self._sqlite.unsynced(c, limit=10_000))
        if self._mongo is None:
            mongo = "disabled"
        else:
            mongo = "degraded" if self._degraded else "ok"
        return {"mongo": mongo, "pending_sync": pending, "sqlite_path": str(self._sqlite.path)}

    # ---- packet id correlation
    def packet_ref(self, source: PacketReceived) -> asyncio.Future:
        key = id(source)
        fut = self._refs.get(key)
        if fut is None:
            fut = asyncio.get_running_loop().create_future()
            self._refs[key] = fut
            while len(self._refs) > 1000:
                self._refs.popitem(last=False)
        return fut

    async def _ref_for(self, source: PacketReceived) -> Ref | None:
        try:
            return await asyncio.wait_for(asyncio.shield(self.packet_ref(source)), 5.0)
        except asyncio.TimeoutError:
            return None

    # ---- event handlers
    async def _on_packet_received(self, ev: PacketReceived) -> None:
        fut = self.packet_ref(ev)
        peek = ccsds.peek_apid_seq(ev.raw)
        doc = {"timestamp": ev.ts, "direction": "rx", "frequency_mhz": ev.freq_mhz,
               "raw_hex": ev.raw.hex().upper(), "rssi": ev.rssi, "snr": ev.snr, "crc_valid": True,
               "apid": peek[0] if peek else None, "sequence_count": peek[1] if peek else None}
        ref = await self.write("raw_packets", doc)
        self.session["packets_received"] += 1
        if not fut.done():
            fut.set_result(ref)

    async def _on_packet_sent(self, ev: PacketSent) -> None:
        peek = ccsds.peek_apid_seq(ev.raw)
        await self.write("raw_packets", {
            "timestamp": ev.ts, "direction": "tx", "frequency_mhz": ev.freq_mhz,
            "raw_hex": ev.raw.hex().upper(), "rssi": None, "snr": None, "crc_valid": True,
            "apid": peek[0] if peek else None, "sequence_count": peek[1] if peek else None})
        self.session["packets_sent"] += 1

    async def _on_decoded(self, ev: PacketDecoded) -> None:
        ref = await self._ref_for(ev.source)
        for f in ev.decoded.fields:
            await self.write("decoded_telemetry", {
                "packet_id": ref[1] if ref else None, "timestamp": ev.source.ts, "apid": ev.packet.apid,
                "apid_name": ev.decoded.apid_name, "field_name": f.name, "field_value": f.value,
                "unit": f.unit, "alarm_status": f.alarm,
            }, force_sqlite=bool(ref and ref[0] == "sqlite"))

    async def _on_alarm(self, ev: AlarmRaised) -> None:
        ref = await self._ref_for(ev.source)
        await self.write("alarms", {
            "timestamp": ev.ts, "packet_id": ref[1] if ref else None, "apid": ev.apid,
            "field_name": ev.field_name, "value": ev.value, "threshold": ev.threshold,
            "alarm_type": ev.alarm_type,
        }, force_sqlite=bool(ref and ref[0] == "sqlite"))

    async def _on_command(self, ev: CommandCompleted) -> None:
        r = ev.record
        await self.write("commands", {
            "timestamp": r.ts, "command_name": r.name, "raw_hex_sent": r.raw_hex,
            "response_received": r.status == "responded", "response_hex": r.response_hex,
            "latency_ms": r.latency_ms, "status": r.status, "attempts": r.attempts})

    # ---- sessions
    async def _flush_session(self) -> None:
        if self._session_ref is None:
            return
        try:
            await self._update(self._session_ref, "sessions", {
                k: self.session[k] for k in ("end_time", "packets_received", "packets_sent", "notes")})
        except Exception as e:  # noqa: BLE001
            log.warning("storage: session flush failed: %s", e)

    async def _session_flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_session()

    # ---- sync
    async def _sync_loop(self) -> None:
        while True:
            await asyncio.sleep(self._sync_interval)
            try:
                await self.sync_now()
            except Exception as e:  # noqa: BLE001
                log.warning("storage: sync failed: %s", e)

    async def sync_now(self) -> int:
        """Upload unsynced SQLite rows to Mongo. Returns rows uploaded; 0 if Mongo is down/disabled."""
        if self._mongo is None:
            return 0
        async with self._sync_lock:
            if not await self._mongo.ping():
                self._degraded = True
                return 0
            uploaded = 0
            try:
                if self._degraded:
                    await self._mongo.ensure_indexes()  # connect() may have failed before creating them
                for c in _SYNC_ORDER:
                    while True:
                        rows = await self._sqlite.unsynced(c, _SYNC_BATCH)
                        if not rows:
                            break
                        ids, docs = [], []
                        for rid, doc in rows:
                            _restore_datetimes(doc)
                            if c in _PACKET_REF_COLLECTIONS:
                                pid = doc.get("packet_id")
                                if pid is not None and str(pid).isdigit():
                                    mapped = await self._sqlite.mongo_id_for("raw_packets", int(pid))
                                    if mapped is None:
                                        continue  # raw packet not uploaded yet; retry next round
                                    doc["packet_id"] = mapped
                            ids.append(rid)
                            docs.append(doc)
                        if not docs:
                            break
                        mongo_ids = await self._mongo.insert_many(c, docs)
                        await self._sqlite.mark_synced(c, ids, mongo_ids)
                        uploaded += len(ids)
                        if len(rows) < _SYNC_BATCH:
                            break
            except PyMongoError as e:
                log.warning("mongo: sync interrupted (%s); %d rows uploaded", e, uploaded)
                self._degraded = True
                return uploaded
            if self._degraded:
                log.info("mongo: connection restored; %d buffered rows uploaded", uploaded)
            self._degraded = False
            return uploaded
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_storage.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/storage/database.py cubesat_gs/tests/test_storage.py
git commit -m "Add storage facade with Mongo primary, SQLite fallback and sync"
```

---

### Task 13: Exporter

**Files:**
- Create: `cubesat_gs/storage/exporter.py`
- Test: `cubesat_gs/tests/test_exporter.py`

**Interfaces:**
- Consumes: `Storage.iterate`, `COLLECTIONS`, `load_config`.
- Produces: `COLUMNS: dict[str, list[str]]` (fixed column order per collection, `id` first), `async export(storage, collection, path, *, fmt="csv", start=None, end=None, apid=None) -> int`; CLI `python -m cubesat_gs.storage.exporter <collection> <out.csv|out.json> [--start ISO] [--end ISO] [--apid N] [--config PATH]`.

- [ ] **Step 1: Write the failing tests**

`cubesat_gs/tests/test_exporter.py`:
```python
import csv
import json
from datetime import datetime, timedelta, timezone

import pytest

from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import EventBus
from cubesat_gs.storage.database import Storage
from cubesat_gs.storage.exporter import COLUMNS, export


def _t(m=0):
    return datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=m)


@pytest.fixture
async def st(tmp_path):
    cfg = DatabaseConfig(local_fallback_path=str(tmp_path / "gs.db"))
    s = Storage(EventBus(), cfg, tmp_path, sync_interval=1000)
    await s.start()
    for i in range(3):
        await s.write("raw_packets", {"timestamp": _t(i), "direction": "rx", "frequency_mhz": 437.25,
                                      "raw_hex": f"0{i}", "rssi": None, "snr": None, "crc_valid": True,
                                      "apid": 10 if i < 2 else 101, "sequence_count": i})
    yield s
    await s.stop()


async def test_export_csv(st, tmp_path):
    out = tmp_path / "raw.csv"
    n = await export(st, "raw_packets", out, fmt="csv")
    assert n == 3
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert list(rows[0].keys()) == COLUMNS["raw_packets"]
    assert [r["raw_hex"] for r in rows] == ["00", "01", "02"]
    assert rows[0]["rssi"] == ""


async def test_export_json_with_filters(st, tmp_path):
    out = tmp_path / "raw.json"
    n = await export(st, "raw_packets", out, fmt="json", apid=10, start=_t(1))
    assert n == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data[0]["raw_hex"] == "01"
    n = await export(st, "raw_packets", out, fmt="json", apid=999)
    assert n == 0 and json.loads(out.read_text(encoding="utf-8")) == []


async def test_bad_args(st, tmp_path):
    with pytest.raises(ValueError):
        await export(st, "raw_packets", tmp_path / "x.txt", fmt="xml")
    with pytest.raises(ValueError):
        await export(st, "nope", tmp_path / "x.csv")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest cubesat_gs/tests/test_exporter.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement exporter.py**

`cubesat_gs/storage/exporter.py`:
```python
"""Stream a collection to CSV or JSON with optional date/APID filters."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from cubesat_gs.storage.sqlite_backend import COLLECTIONS, to_jsonable

log = logging.getLogger(__name__)

COLUMNS: dict[str, list[str]] = {
    "raw_packets": ["id", "timestamp", "direction", "frequency_mhz", "raw_hex", "rssi", "snr",
                    "crc_valid", "apid", "sequence_count"],
    "decoded_telemetry": ["id", "packet_id", "timestamp", "apid", "apid_name", "field_name",
                          "field_value", "unit", "alarm_status"],
    "commands": ["id", "timestamp", "command_name", "raw_hex_sent", "response_received",
                 "response_hex", "latency_ms", "status", "attempts"],
    "sessions": ["id", "start_time", "end_time", "pass_id", "packets_received", "packets_sent", "notes"],
    "alarms": ["id", "timestamp", "packet_id", "apid", "field_name", "value", "threshold", "alarm_type"],
}


async def export(storage, collection: str, path: str | Path, *, fmt: str = "csv",
                 start: datetime | None = None, end: datetime | None = None,
                 apid: int | None = None) -> int:
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}")
    if fmt not in ("csv", "json"):
        raise ValueError(f"fmt must be 'csv' or 'json', got {fmt!r}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = COLUMNS[collection]
    n = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        if fmt == "csv":
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            async for doc in storage.iterate(collection, start=start, end=end, apid=apid):
                row = to_jsonable(doc)
                w.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in cols})
                n += 1
        else:
            fh.write("[")
            async for doc in storage.iterate(collection, start=start, end=end, apid=apid):
                if n:
                    fh.write(",\n")
                fh.write(json.dumps(to_jsonable(doc), ensure_ascii=False))
                n += 1
            fh.write("]")
    log.info("export: %d rows from %s -> %s", n, collection, path)
    return n


def _parse_dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


async def _main(argv: list[str] | None = None) -> int:
    from cubesat_gs.core.config import load_config
    from cubesat_gs.core.events import EventBus
    from cubesat_gs.storage.database import Storage

    ap = argparse.ArgumentParser(description="Export a ground-station collection to CSV/JSON")
    ap.add_argument("collection", choices=COLLECTIONS)
    ap.add_argument("output", help="output file; .csv or .json decides the format")
    ap.add_argument("--start"); ap.add_argument("--end"); ap.add_argument("--apid", type=int)
    ap.add_argument("--config")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    st = Storage(EventBus(), cfg.database, cfg.base_dir.parent, sync_interval=10_000)
    await st.start()
    try:
        n = await export(st, a.collection, a.output, fmt="json" if a.output.endswith(".json") else "csv",
                         start=_parse_dt(a.start), end=_parse_dt(a.end), apid=a.apid)
    finally:
        await st.stop()
    print(f"{n} rows written to {a.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_exporter.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add cubesat_gs/storage/exporter.py cubesat_gs/tests/test_exporter.py
git commit -m "Add CSV/JSON exporter with CLI"
```

---
### Task 14: GroundStation wiring, main.py and integration test

**Files:**
- Create: `cubesat_gs/core/station.py`, `cubesat_gs/main.py`
- Test: `cubesat_gs/tests/test_integration.py`

**Interfaces:**
- Consumes: every module above.
- Produces: `GroundStation(cfg: GSConfig, *, open_connection=None, mongo_client_factory=None)` with attributes `bus, serial, freq, builder, decoder, telecommand, storage` and `async start()`, `async stop()`, `status() -> dict`; `setup_logging(cfg: LoggingConfig, base_dir: Path, level_override=None)`; `main.py` CLI `python cubesat_gs/main.py [--config PATH] [--sim] [--log-level LEVEL]`.

- [ ] **Step 1: Write the failing integration test**

`cubesat_gs/tests/test_integration.py`:
```python
"""Full stack: GroundStation + in-process ModemSimulator + SQLite. No hardware, no network."""
import asyncio

import pytest

from cubesat_gs.core.config import load_config
from cubesat_gs.core.events import PacketDecoded, SequenceGap
from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.station import GroundStation
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial


async def _wait_until(pred, timeout=2.0):
    async def _w():
        while not pred():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_w(), timeout)


@pytest.fixture
async def gs(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    cfg = load_config(dotenv=False)
    cfg.serial.port = "sim://"
    cfg.serial.reconnect_interval = 0.05
    cfg.serial.timeouts.tx = 0.5
    cfg.serial.timeouts.freq = 0.5
    cfg.database.local_fallback_path = str(tmp_path / "gs.db")
    cfg.database.mongo_uri = None
    sim = ModemSimulator(beacon_interval=0.1)
    await sim.start()
    ser = SimulatedSerial(sim)
    station = GroundStation(cfg, open_connection=ser.open)
    await station.start()
    await _wait_until(lambda: station.serial.connected)
    yield station, sim, ser
    await station.stop()
    await sim.stop()


async def test_beacon_then_ping_end_to_end(gs):
    station, sim, _ser = gs
    decoded, gaps = [], []
    station.bus.subscribe(PacketDecoded, lambda e: _push(decoded, e))
    station.bus.subscribe(SequenceGap, lambda e: _push(gaps, e))

    # 1. initial mode was applied to the modem on connect
    assert sim.freq == 435.5 and station.freq.mode is Mode.TCTM

    # 2. listen for beacons
    await station.freq.set_mode(Mode.BEACON_LISTEN)
    assert sim.freq == 437.25
    await _wait_until(lambda: len(decoded) >= 2)
    assert decoded[0].decoded.apid_name == "Beacon"
    assert decoded[0].decoded.as_dict()["message"] == "VLEO_BEACON_SYS_NOMINAL"
    assert station.decoder.last_values[10].as_dict()["message"] == "VLEO_BEACON_SYS_NOMINAL"

    # 3. back to TCTM and ping
    await station.freq.set_mode(Mode.TCTM)
    rec = await station.telecommand.send_command("PING")
    assert rec.status == "responded" and rec.latency_ms is not None
    await _wait_until(lambda: any(e.decoded.apid == 101 for e in decoded))
    pong = next(e for e in decoded if e.decoded.apid == 101)
    assert pong.decoded.as_dict()["response_data"] == "PONG_DATA_6.28"
    assert gaps == []  # global counter, no gaps

    # 4. everything persisted
    await asyncio.sleep(0.1)
    raw = await station.storage.query("raw_packets", limit=100)
    rx = [r for r in raw if r["direction"] == "rx"]
    tx = [r for r in raw if r["direction"] == "tx"]
    assert len(rx) >= 3 and len(tx) == 1 and tx[0]["apid"] == 100
    assert any(r["apid"] == 101 for r in rx)
    dec = await station.storage.query("decoded_telemetry", apid=101)
    assert dec[0]["field_value"] == "PONG_DATA_6.28" and dec[0]["packet_id"] is not None
    cmds = await station.storage.query("commands")
    assert cmds[0]["command_name"] == "PING" and cmds[0]["status"] == "responded"
    assert station.storage.session["packets_sent"] == 1
    assert station.storage.session["packets_received"] == len(rx)

    st = station.status()
    assert st["serial"]["connected"] is True and st["frequency"]["mode"] == "tctm"
    assert st["storage"]["mongo"] == "disabled"


async def _push(lst, e):
    lst.append(e)


async def test_survives_modem_unplug(gs):
    station, sim, ser = gs
    ser.close_from_modem_side()
    await _wait_until(lambda: not station.serial.connected)
    await _wait_until(lambda: station.serial.connected)
    await station.freq.set_mode(Mode.BEACON_LISTEN)  # modem answers on the new link
    assert sim.freq == 437.25
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cubesat_gs/tests/test_integration.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'cubesat_gs.core.station'`

- [ ] **Step 3: Implement station.py**

`cubesat_gs/core/station.py`:
```python
"""GroundStation: owns the config, the event bus and every module; single start()/stop()."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Any, Callable

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import GSConfig, LoggingConfig
from cubesat_gs.core.events import EventBus
from cubesat_gs.core.frequency_manager import FrequencyManager
from cubesat_gs.core.serial_handler import SerialHandler
from cubesat_gs.core.telecommand import TelecommandManager
from cubesat_gs.core.telemetry import TelemetryDecoder
from cubesat_gs.storage.database import Storage

log = logging.getLogger(__name__)


def setup_logging(cfg: LoggingConfig, base_dir: Path, level_override: str | None = None) -> None:
    level = getattr(logging, (level_override or cfg.level).upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    if cfg.file:
        path = Path(cfg.file)
        path = path if path.is_absolute() else base_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3,
                                                  encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)


class GroundStation:
    def __init__(self, cfg: GSConfig, *, open_connection: Callable | None = None,
                 mongo_client_factory: Callable[[str], Any] | None = None) -> None:
        self.cfg = cfg
        pkg_dir = cfg.base_dir.parent
        self.bus = EventBus()
        self.serial = SerialHandler(self.bus, cfg.serial, get_freq=lambda: self.freq.mhz,
                                    open_connection=open_connection)
        self.freq = FrequencyManager(self.bus, self.serial, cfg.frequencies)
        self.builder = ccsds.PacketBuilder(cfg.ccsds.length_includes_crc)
        self.decoder = TelemetryDecoder(self.bus, cfg.resolve(cfg.telemetry.definitions), cfg.ccsds)
        self.telecommand = TelecommandManager(self.bus, self.serial, self.freq, self.builder,
                                              cfg.commands, cfg.resolve(cfg.commands.registry))
        self.storage = Storage(self.bus, cfg.database, pkg_dir, mongo_client_factory=mongo_client_factory)

    async def start(self) -> None:
        log.info("ground station %r starting", self.cfg.station.name)
        await self.storage.start()
        self.decoder.start()
        self.freq.start()
        await self.serial.start()  # last: its ConnectionChanged(True) triggers the initial FREQ

    async def stop(self) -> None:
        log.info("ground station stopping")
        await self.serial.stop()
        self.freq.stop()
        self.decoder.stop()
        await self.storage.stop()

    def status(self) -> dict[str, Any]:
        return {
            "station": self.cfg.station.name,
            "serial": {"connected": self.serial.connected, "port": self.serial.port},
            "frequency": {"mode": self.freq.mode.value, "mhz": self.freq.mhz},
            "pending_command": self.telecommand.pending.as_dict() if self.telecommand.pending else None,
            "storage": {"mongo": "disabled" if self.storage._mongo is None
                        else ("degraded" if self.storage._degraded else "ok")},
            "session": dict(self.storage.session),
        }
```

- [ ] **Step 4: Implement main.py**

`cubesat_gs/main.py`:
```python
"""Entry point: python cubesat_gs/main.py [--config PATH] [--sim] [--log-level LEVEL]"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# allow `python cubesat_gs/main.py` from the git root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cubesat_gs.core.config import load_config  # noqa: E402
from cubesat_gs.core.station import GroundStation, setup_logging  # noqa: E402

log = logging.getLogger("main")


async def run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    setup_logging(cfg.logging, cfg.base_dir.parent, args.log_level)

    sim_server = None
    if args.sim:
        from cubesat_gs.tests.serial_simulator import ModemSimulator, serve_tcp
        sim = ModemSimulator(beacon_interval=args.sim_beacon_interval, fake_rssi=args.sim_rssi)
        sim_server, port = await serve_tcp(sim, "127.0.0.1", 0)
        cfg.serial.port = f"socket://127.0.0.1:{port}"
        log.info("simulator: modem simulator listening on %s", cfg.serial.port)

    station = GroundStation(cfg)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows: no loop signal handlers
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))

    await station.start()
    log.info("ground station running; Ctrl+C to stop")
    try:
        await stop.wait()
    finally:
        await station.stop()
        if sim_server is not None:
            sim_server.close()
            await sim_server.wait_closed()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CubeSat ground station (headless core)")
    ap.add_argument("--config", help="path to gs_config.yaml (default: cubesat_gs/config/gs_config.yaml)")
    ap.add_argument("--sim", action="store_true", help="run against an in-process ESP32 simulator")
    ap.add_argument("--sim-beacon-interval", type=float, default=10.0)
    ap.add_argument("--sim-rssi", action="store_true", help="simulator appends fake RSSI/SNR")
    ap.add_argument("--log-level", help="override logging.level from config")
    args = ap.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`serve_tcp` does not exist yet — it is added in Task 15. The integration test does not need it, so proceed.

- [ ] **Step 5: Run the integration test**

Run: `python -m pytest cubesat_gs/tests/test_integration.py -q`
Expected: 2 passed

- [ ] **Step 6: Run the whole suite**

Run: `python -m pytest -q`
Expected: all passed, no warnings about un-awaited coroutines or pending tasks.

- [ ] **Step 7: Commit**

```bash
git add cubesat_gs/core/station.py cubesat_gs/main.py cubesat_gs/tests/test_integration.py
git commit -m "Wire GroundStation, add main entry point and end-to-end test"
```

---

### Task 15: Simulator TCP server, README, manual end-to-end run

**Files:**
- Modify: `cubesat_gs/tests/serial_simulator.py` (append `serve_tcp` + `main`)
- Create: `README.md` (git root)
- Test: `cubesat_gs/tests/test_serial_simulator.py` (append)

**Interfaces:**
- Produces: `async serve_tcp(sim: ModemSimulator, host: str, port: int) -> tuple[asyncio.AbstractServer, int]` (returns the bound port; `0` picks a free one); CLI `python -m cubesat_gs.tests.serial_simulator [--host 127.0.0.1] [--port 5000] [--beacon-interval 10] [--rssi] [--per-apid-seq] [--standard-length]`.

- [ ] **Step 1: Write the failing test** (append to `test_serial_simulator.py`)

```python
from cubesat_gs.tests.serial_simulator import serve_tcp


async def test_tcp_server_speaks_modem_protocol():
    sim = ModemSimulator(beacon_interval=1000)
    server, port = await serve_tcp(sim, "127.0.0.1", 0)
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"FREQ:437.25\n")
        await writer.drain()
        assert (await asyncio.wait_for(reader.readline(), 1.0)) == b"OK:FREQ_SET\n"
        sim.inject_rx(b"\x00\x0a\xc0\x00\x00\x03ab")
        assert (await asyncio.wait_for(reader.readline(), 1.0)) == b"RX:000AC00000036162\n"
        writer.close()
        await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cubesat_gs/tests/test_serial_simulator.py -q`
Expected: FAIL with `ImportError: cannot import name 'serve_tcp'`

- [ ] **Step 3: Implement** (append to `serial_simulator.py`)

```python
# ---------------------------------------------------------------- TCP transport (serial.port = "socket://host:port")

async def serve_tcp(sim: ModemSimulator, host: str, port: int) -> tuple[asyncio.AbstractServer, int]:
    """Serve the modem protocol over TCP. One client at a time gets the output stream."""

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        log.info("sim: client connected %s", peer)

        async def pump() -> None:
            while True:
                line = await sim.read_line()
                writer.write(line.encode() + b"\n")
                await writer.drain()

        pump_task = asyncio.create_task(pump())
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                await sim.handle_line(data.decode(errors="ignore"))
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            pump_task.cancel()
            writer.close()
            log.info("sim: client disconnected %s", peer)

    server = await asyncio.start_server(handle, host, port)
    bound = server.sockets[0].getsockname()[1]
    await sim.start()
    return server, bound


async def _main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="ESP32 LoRa modem + OBC simulator over TCP")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--beacon-interval", type=float, default=10.0)
    ap.add_argument("--rssi", action="store_true", help="append |RSSI|SNR to RX lines")
    ap.add_argument("--per-apid-seq", action="store_true", help="standard per-APID sequence counters")
    ap.add_argument("--standard-length", action="store_true", help="data_length excludes CRC (strict CCSDS)")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sim = ModemSimulator(beacon_interval=a.beacon_interval, fake_rssi=a.rssi,
                         sequence_scope="per_apid" if a.per_apid_seq else "global",
                         length_includes_crc=not a.standard_length)
    server, port = await serve_tcp(sim, a.host, a.port)
    log.info("sim: listening on %s:%d — set serial.port: \"socket://%s:%d\"", a.host, port, a.host, port)
    try:
        await server.serve_forever()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await sim.stop()
        server.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest cubesat_gs/tests/test_serial_simulator.py -q`
Expected: 7 passed

- [ ] **Step 5: Manual end-to-end run (two terminals, from the git root)**

Terminal 1: `python -m cubesat_gs.tests.serial_simulator --port 5000 --beacon-interval 3`
Terminal 2: set `serial.port: "socket://127.0.0.1:5000"` in `cubesat_gs/config/gs_config.yaml` temporarily (or use the one-terminal form below), then `python cubesat_gs/main.py --log-level DEBUG`.
Expected in Terminal 2: `serial: ... ConnectionChanged`, `frequency: re-applied 435.500 MHz after connect`, then nothing (beacons only arrive on 437.250 — Phase 1 has no UI to switch mode; that is expected). Ctrl+C stops cleanly with `ground station stopping`.

One-terminal form: `python cubesat_gs/main.py --sim --sim-beacon-interval 3 --log-level DEBUG` — expected: simulator port logged, connection, initial FREQ, clean Ctrl+C. Revert any temporary config change.

- [ ] **Step 6: Write README.md** (git root)

```markdown
# CubeSat-GS — UAI CubeSat Ground Station

Ground station software for the UAI CubeSat: ESP32 + SX1278 LoRa modem on USB serial,
Raspberry Pi host, CCSDS Space Packets, MongoDB Atlas storage with SQLite offline fallback.

Phase 1 (this state): headless core. Phase 2: FastAPI + React dashboard. Phase 3: pass prediction.

## Layout

- `cubesat_gs/` — Python package (core, storage, tests, `main.py`)
- `cubesat_comms-main/` — reference satellite-side code (ESP32 firmware, OBC simulator)
- `docs/superpowers/specs/` — design specs; `docs/superpowers/plans/` — implementation plans

## Setup

```bash
python -m pip install -r cubesat_gs/requirements.txt
cp cubesat_gs/.env.example .env      # then put the real MONGO_URI in .env (gitignored)
```

Without `MONGO_URI` the station stores everything in `cubesat_gs/data/gs_offline.db` (SQLite).

## Run

```bash
python cubesat_gs/main.py                 # real modem, port from config (auto-detect by default)
python cubesat_gs/main.py --sim           # no hardware: in-process ESP32/OBC simulator
python -m cubesat_gs.tests.serial_simulator --port 5000   # standalone simulator (serial.port: "socket://127.0.0.1:5000")
python -m cubesat_gs.storage.exporter raw_packets out.csv --start 2026-09-01T00:00:00+00:00
```

## Test

```bash
python -m pytest -q
```

## Protocol notes

The parser defaults follow the current OBC code (`cubesat_comms-main/OBC_sim.py`), which differs from
strict CCSDS in two ways; both are switches in `cubesat_gs/config/gs_config.yaml`:

- `ccsds.length_includes_crc: true` — the OBC counts the 2 CRC bytes in the data-length field.
- `ccsds.sequence_scope: global` — the OBC uses one sequence counter for all APIDs.

Telecommands are defined in `cubesat_gs/config/commands.yaml`; telemetry layouts in
`cubesat_gs/config/telemetry_defs.yaml`.
```

- [ ] **Step 7: Full verification and commit**

Run: `python -m pytest -q`
Expected: all tests pass.

```bash
git add README.md cubesat_gs/tests/serial_simulator.py cubesat_gs/tests/test_serial_simulator.py
git commit -m "Add simulator TCP server and README"
git push origin main
```

---

## Self-review notes

- Spec §3.5 asks `"auto"` port detection to prefer known USB-UART VIDs — Task 6 `detect_port`.
- Spec §3.10 `packet_id` remap and `decoded_telemetry`/`alarms` following the raw packet's backend — Task 12 `force_sqlite` + `sync_now`.
- Spec §3.12 start order (storage, decoder, telecommand, freq, serial) — Task 14; `TelecommandManager` has no start (it only reacts inside `send_command`).
- Spec §5 `test_frequency_manager.py` — Task 7. `test_storage.py` covers SQLite CRUD via Task 10's dedicated file plus facade tests in Task 12.
- Phase 2 will read `GroundStation.status()`, `storage.query`, `telecommand.commands/history`, `decoder.last_values`, `freq.set_mode` and subscribe to the bus — no Phase 1 interface changes anticipated.
