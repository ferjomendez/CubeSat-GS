# CubeSat Ground Station — Phase 1 Design (Headless Core)

Date: 2026-09-13
Status: approved in brainstorming, pending spec review
Repo: https://github.com/ferjomendez/CubeSat-GS.git

## 1. Scope

Phase 1 delivers a fully working **headless** ground station: it talks to the
ESP32 LoRa modem (or a simulator), parses CCSDS packets, decodes telemetry,
sends telecommands with retry/verification, manages the operating frequency,
and persists everything to MongoDB Atlas with a SQLite offline fallback.
It is runnable end-to-end on a laptop with no hardware (`python main.py --sim`).

Out of scope (later phases, each with its own spec):

- Phase 2: FastAPI backend + WebSocket + React/Tailwind/shadcn dashboard.
- Phase 3: pass predictor (sgp4/skyfield), Doppler, frequency auto-mode.

## 2. Ground truth from the existing satellite code

Source: `cubesat_comms-main/` (ESP32_LoRa_Handler.ino, OBC_sim.py).

Modem serial protocol (115200 8N1, `\n` terminated):

| Direction | Line | Notes |
|---|---|---|
| RPi → ESP32 | `TX:<hex>` | ESP32 appends CRC-16-CCITT, transmits, replies `OK:TX_DONE` (always). |
| RPi → ESP32 | `FREQ:<mhz>` | Replies `OK:FREQ_SET` **only on success**; silent on failure. |
| ESP32 → RPi | `RX:<HEX>` | Uppercase hex, CRC already verified and stripped. Only packets ≥ 8 bytes on air are forwarded. |
| ESP32 → RPi (future) | `RX:<hex>\|RSSI:<f>\|SNR:<f>` | Must be parsed if present, ignored if absent. |

CRC-16-CCITT: init `0xFFFF`, poly `0x1021`, no reflection, no final XOR.
Test vector: `b"123456789"` → `0x29B1`.

LoRa: SX1278, 125 kHz, SF9, CR 4/7, sync 0x12, 17 dBm, preamble 8.
Frequencies: 435.500 MHz TC/TM, 437.250 MHz beacon.

CCSDS primary header (6 bytes, big-endian) as in CCSDS 133.0-B-2. The OBC
sets version=0, type=0, sec_hdr=0, seq_flags=0b11.

**Deviation 1 — data length includes CRC.** `OBC_sim.py:24` sets
`data_length = len(payload) + 2 - 1`. Because the ESP32 strips the CRC, the
GS receives packets whose declared length is 2 bytes larger than the actual
payload. Decision: parser convention is configurable
(`ccsds.length_includes_crc`, default `true`). GS-built packets use the same
convention so the OBC sees symmetric frames.

**Deviation 2 — one global sequence counter.** `OBC_sim.py:34` shares one
counter across APIDs. Decision: gap detection scope is configurable
(`ccsds.sequence_scope: global | per_apid`, default `global`). GS TX counters
are always per-APID (standard).

Telecommand protocol (defined by `OBC_sim.py:54`): the satellite checks
`b"PING" in payload` and replies on APID 101 with UTF-8 `PONG_DATA_6.28`.
The GS uplinks on **APID 100** (chosen here; the OBC ignores the APID).

Known APIDs: 10 beacon (UTF-8 string, 437.250 only), 101 TM response
(UTF-8 string, 435.500), 100 telecommand (uplink).

## 3. Architecture

Single process, single asyncio loop, central event bus. Modules never import
each other; they import `core.events` and the shared dataclasses.

```
ESP32/simulator ──► SerialHandler ──publish──► EventBus ◄──subscribe── TelemetryDecoder
 (socket:// or        (cmd queue, 1 outstanding,   │      ◄──subscribe── TelecommandManager
  /dev/ttyUSB0)        per-kind timeout,           │      ◄──subscribe── Storage
                       auto-reconnect)             │      ◄──subscribe── FrequencyManager
                          ▲                        │      ◄──subscribe── [Phase 2 WebSocket hub]
                          └── send_tx()/set_frequency() from TelecommandManager, FrequencyManager
```

### 3.1 Package layout

```
cubesat_gs/
  config/
    gs_config.yaml
    telemetry_defs.yaml
    commands.yaml
  core/
    __init__.py
    config.py            # YAML + .env → typed dataclasses with defaults
    events.py            # EventBus + event dataclasses
    ccsds.py
    serial_handler.py
    telemetry.py
    telecommand.py
    frequency_manager.py
    station.py           # GroundStation: owns config, bus, modules; start()/stop()
  storage/
    __init__.py
    database.py          # Storage facade, MongoBackend, SQLiteBackend, sync task
    exporter.py
  tests/
    __init__.py
    serial_simulator.py
    test_ccsds.py
    test_telemetry.py
    test_serial_handler.py
    test_telecommand.py
    test_frequency_manager.py
    test_storage.py
    test_integration.py
  main.py
  requirements.txt
  .env.example
docs/superpowers/specs/...
cubesat_comms-main/      # reference satellite code, unchanged
.gitignore               # .env, data/, logs/, __pycache__, .pytest_cache
```

### 3.2 `core/events.py`

```python
class EventBus:
    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None
    def unsubscribe(self, event_type, handler) -> None
    def publish(self, event) -> None      # schedules one task per handler; never raises
    async def wait_for(self, event_type, predicate=None, timeout=None) -> E   # one-shot await
```

Handler exceptions are logged with the event repr and swallowed. `wait_for`
is what TelecommandManager uses to await a response.

Events (frozen dataclasses, all carry `ts: datetime` UTC):

| Event | Fields | Publisher |
|---|---|---|
| `ConnectionChanged` | `connected: bool, port: str` | SerialHandler |
| `SerialError` | `message: str` | SerialHandler |
| `PacketReceived` | `raw: bytes, rssi: float\|None, snr: float\|None, freq_mhz: float` | SerialHandler |
| `PacketSent` | `raw: bytes, freq_mhz: float` | SerialHandler |
| `ModemAck` | `kind: "TX_DONE" \| "FREQ_SET"` | SerialHandler |
| `SequenceGap` | `apid: int, expected: int, received: int, missed: int` | TelemetryDecoder |
| `PacketDecoded` | `source: PacketReceived, packet: CCSDSPacket, decoded: DecodedPacket` | TelemetryDecoder |
| `PacketMalformed` | `source: PacketReceived, reason: str` | TelemetryDecoder |
| `AlarmRaised` | `source: PacketReceived, apid, field_name, value, threshold, alarm_type: "low"\|"high"` | TelemetryDecoder |
| `CommandCompleted` | `record: CommandRecord` | TelecommandManager |
| `FrequencyChanged` | `mode: Mode, mhz: float` | FrequencyManager |

`freq_mhz` on packet events is read from FrequencyManager's current value at
the moment of the event (SerialHandler holds a callable to fetch it).

### 3.3 `core/config.py`

`load_config(path="config/gs_config.yaml") -> GSConfig`. Loads `.env` via
python-dotenv first. Typed dataclasses: `SerialConfig`, `FrequencyConfig`,
`CCSDSConfig`, `CommandConfig`, `TelemetryConfig`, `DatabaseConfig`,
`LoggingConfig`, `StationConfig`, `SatelliteConfig`, `PassConfig`,
`WebConfig` (the last four are loaded and validated now, used in later
phases). Missing keys get defaults; unknown keys are logged as warnings.
`MONGO_URI` is read from the environment only and exposed as
`DatabaseConfig.mongo_uri: str | None`.

Additions to the spec's `gs_config.yaml`:

```yaml
serial:
  port: "auto"           # "auto", "/dev/ttyUSB0", "COM3", or "socket://localhost:5000"
  baudrate: 115200
  reconnect_interval: 5
  timeouts:
    tx: 5.0
    freq: 2.0

ccsds:
  length_includes_crc: true   # OBC_sim.py convention; set false when OBC is standard-compliant
  sequence_scope: global      # global | per_apid

commands:
  registry: "config/commands.yaml"
  default_timeout: 10
  max_retries: 3
  retry_backoff: 1.5          # multiplier per attempt
  history_size: 500

telemetry:
  definitions: "config/telemetry_defs.yaml"
```

### 3.4 `core/ccsds.py`

```python
@dataclass(frozen=True)
class CCSDSPacket:
    version: int; packet_type: int; sec_header_flag: bool; apid: int
    sequence_flags: int; sequence_count: int; data_length: int   # raw field value
    payload: bytes
    def to_bytes(self) -> bytes

class CCSDSError(ValueError): ...

def parse(raw: bytes, *, length_includes_crc: bool = True) -> CCSDSPacket
def build(apid, payload, *, sequence_count, packet_type=1, seq_flags=0b11,
          sec_header_flag=False, length_includes_crc=True) -> bytes

class PacketBuilder:            # owns per-APID TX counters
    def __init__(self, length_includes_crc: bool)
    def build(self, apid, payload, packet_type=1) -> bytes

class SequenceTracker:
    def __init__(self, scope: Literal["global", "per_apid"])
    def observe(self, packet) -> int | None   # number of missed packets, None if none/first

def crc16_ccitt(data: bytes) -> int
def crc16_append(data: bytes) -> bytes
def crc16_verify(data_with_crc: bytes) -> bool
```

`parse` raises `CCSDSError` when: `len(raw) < 6`; `version != 0`; declared
length ≠ actual payload under the configured convention. Expected payload
length is `data_length + 1 - (2 if length_includes_crc else 0)`.
`packet_type=1` for telecommands (CCSDS: 0 = telemetry, 1 = telecommand); the
OBC ignores the bit. `SequenceTracker.observe` handles 14-bit wraparound
(`(received - expected) & 0x3FFF`).

### 3.5 `core/serial_handler.py`

```python
class SerialHandler:
    def __init__(self, bus, cfg: SerialConfig, get_freq: Callable[[], float],
                 open_connection=serial_asyncio.open_serial_connection)
    async def start() / async def stop()
    async def send_tx(self, raw: bytes) -> None           # raises SerialCommandTimeout / SerialDisconnected
    async def set_frequency(self, mhz: float) -> None     # same
    @property connected: bool ; port: str | None
```

- Connection via `open_connection(url=port, baudrate=...)`. `"auto"` → first
  match among `serial.tools.list_ports.comports()` whose device matches
  `/dev/ttyUSB*`, `/dev/ttyACM*`, or `COM*` on Windows, preferring ports whose
  VID matches known USB-UART bridges (CP210x 0x10C4, CH340 0x1A86, FTDI
  0x0403); else the first candidate; none → treated as connection failure.
- Reader task: `readline()` loop. Parse:
  - `RX:` → split on `|`; first token hex (case-insensitive); remaining
    `KEY:VAL` tokens with `RSSI`/`SNR` parsed as float, unknown keys ignored,
    parse errors → the field is `None`. Invalid hex → `SerialError`, line dropped.
  - `OK:<kind>` → resolve pending future if kind matches, publish `ModemAck`;
    unexpected ack → debug log.
  - other → debug log.
- Writer: `asyncio.Queue[(line, ack_kind, timeout, future)]`; one worker.
  Writes line, awaits future with timeout. Timeout → future exception
  `SerialCommandTimeout`, worker moves on. `send_tx` publishes `PacketSent`
  only after `TX_DONE`.
- Reconnect: on open failure or reader EOF/`SerialException`, publish
  `ConnectionChanged(False)`, sleep `reconnect_interval`, retry forever.
  Queued commands remain queued; the in-flight command (if any) fails with
  `SerialDisconnected`.
- `stop()` cancels tasks and closes the transport.

### 3.6 `tests/serial_simulator.py`

Behaves like ESP32 + OBC_sim together, from the modem's serial side.

```python
class ModemSimulator:
    def __init__(self, *, beacon_interval=10.0, length_includes_crc=True,
                 sequence_scope="global", fake_rssi=False, ping_apid=100)
    async def handle_line(self, line: str) -> None      # feeds TX:/FREQ:
    async def output(self) -> AsyncIterator[str]        # lines the GS would read
    # helpers for tests:
    def inject_rx(self, raw: bytes, rssi=None, snr=None)
    freq: float ; received_tx: list[bytes]
```

State: current freq (starts 435.500). `FREQ:x` → `OK:FREQ_SET`. `TX:hex` →
record, `OK:TX_DONE`; if freq == 435.500 and payload contains `PING` →
after 50 ms emit `RX:` of an APID 101 `PONG_DATA_6.28` packet. Beacon task:
every `beacon_interval` s, if freq == 437.250, emit `RX:` of an APID 10
`VLEO_BEACON_SYS_NOMINAL` packet (uppercase hex, as the ESP32 prints).
`fake_rssi` appends `|RSSI:-97.5|SNR:8.25`.

Transports:
- `python -m cubesat_gs.tests.serial_simulator --port 5000 [--beacon-interval 10] [--rssi]`
  → TCP server; the GS uses `serial.port: "socket://localhost:5000"`.
- In-process for pytest: `SimulatedSerial` provides a `StreamReader`/
  `StreamWriter`-compatible pair, injected into `SerialHandler` through the
  `open_connection` factory argument.

### 3.7 `core/telemetry.py`

```python
@dataclass class DecodedField: name, value, unit: str|None, alarm: Literal["nominal","low","high"]|None, raw: bytes
@dataclass class DecodedPacket: apid, apid_name, fields: list[DecodedField], unknown_apid: bool, partial: bool, error: str|None

class TelemetryDecoder:
    def __init__(self, bus, defs_path, ccsds_cfg)
    def decode(self, packet: CCSDSPacket) -> DecodedPacket      # pure, testable
    # subscribes to PacketReceived: parse → SequenceTracker → decode → publish PacketDecoded (+AlarmRaised each)
```

Definition file schema (`telemetry_defs.yaml`), key `apid_<n>`:

```yaml
apid_10:
  name: "Beacon"
  fields:
    - name: message
      type: string          # uint8 int8 uint16 int16 uint32 int32 float32 string bytes
      encoding: utf-8       # string only, default utf-8, errors="replace"
      length: 12            # string/bytes only; omitted = rest of payload
      scale: 0.1            # numeric only, applied as value*scale + offset
      offset: 0
      unit: "°C"
      alarm_low: -10
      alarm_high: 50
```

Validation at load: unknown type, `length` on numeric, or `scale` on string →
fail fast with file/field name. Decoding: numeric via `struct` `>` formats;
payload exhausted before a field → `partial=True`, `error` set, remaining
fields skipped. Unknown APID → `unknown_apid=True`, one field
`raw_hex`. Alarm: `low` if `value < alarm_low`, `high` if `value > alarm_high`,
`nominal` if thresholds exist and value is within them, `None` if no
thresholds are defined.

Parse failure of the raw bytes → publish `PacketMalformed` (Storage still
records the raw packet with `crc_valid=True, apid=None`).

### 3.8 `core/telecommand.py`

`config/commands.yaml`:

```yaml
commands:
  - name: PING
    description: "Liveness check; satellite answers PONG_DATA_<value>"
    apid: 100
    payload: "PING"          # utf-8 string, or hex: "0x01FF"
    response_apid: 101       # null = no response expected
    timeout: 10
    critical: false
```

```python
@dataclass class CommandRecord:
    ts, name, raw_hex, status: Literal["acked","responded","timeout","failed","refused"],
    response_hex: str|None, latency_ms: float|None, attempts: int, error: str|None

class TelecommandManager:
    def __init__(self, bus, serial, freq_mgr, builder: PacketBuilder, cfg: CommandConfig)
    @property commands: dict[str, CommandDef] ; history: deque[CommandRecord] ; pending: CommandRecord|None
    async def send_command(self, name, *, confirm=False, payload_override: bytes|None=None) -> CommandRecord
    async def send_raw(self, hex_str: str) -> CommandRecord
```

`send_command` flow: refuse if `critical and not confirm` (`status=refused`);
refuse if another command is pending (`CommandBusyError`); refuse if
`freq_mgr.mode != TCTM` (`WrongModeError`). Then for attempt in
1..max_retries+1: build packet, `serial.send_tx`, start timer, `bus.wait_for(
PacketReceived, lambda e: parsed apid == response_apid, timeout)`. Success →
`responded`, latency = response ts − TX ack ts. Timeout → sleep
`retry_backoff ** attempt` s, retry (so the first retry delay already scales with the configured multiplier). Exhausted → `timeout`. Serial errors
→ `failed`. Commands with `response_apid: null` complete as `acked` after
`TX_DONE`. Every record appended to history and published as
`CommandCompleted`. `send_raw` sends the hex bytes verbatim (no CCSDS
header added) as a command named `RAW` with no response expected.

### 3.9 `core/frequency_manager.py`

```python
class Mode(str, Enum): BEACON_LISTEN="beacon_listen"; TCTM="tctm"; CUSTOM="custom"
class FrequencyManager:
    def __init__(self, bus, serial, cfg: FrequencyConfig)
    async def set_mode(self, mode: Mode, mhz: float|None=None) -> None   # mhz required for CUSTOM
    @property mode: Mode ; mhz: float
```

Initial state TCTM/435.500 (matches the ESP32 boot default), re-applied via
`FREQ:` on every `ConnectionChanged(True)` so state is never stale after a
modem reset. Publishes `FrequencyChanged` after `OK:FREQ_SET`; on timeout
keeps the previous state and raises.

### 3.10 `storage/database.py`

```python
class Storage:
    def __init__(self, bus, cfg: DatabaseConfig)
    async def start() / async def stop()
    async def health() -> dict     # {"mongo": "ok"|"degraded"|"disabled", "pending_sync": int, "sqlite_path": str}
    async def query(collection, *, start=None, end=None, apid=None, limit=100) -> list[dict]
    async def stats() -> dict      # counts per collection
```

Collections/tables (identical field names in both backends):

- `raw_packets`: `timestamp, direction ("rx"|"tx"), frequency_mhz, raw_hex, rssi, snr, crc_valid, apid, sequence_count`
- `decoded_telemetry`: `packet_id, timestamp, apid, apid_name, field_name, field_value, unit, alarm_status`
- `commands`: `timestamp, command_name, raw_hex_sent, response_received (bool), response_hex, latency_ms, status, attempts`
- `sessions`: `start_time, end_time, pass_id, packets_received, packets_sent, notes`
- `alarms`: `timestamp, packet_id, apid, field_name, value, threshold, alarm_type`

Backends:

- `MongoBackend` (motor). `connect()`: `admin.command("ping")` with
  `serverSelectionTimeoutMS=5000`; then `ensure_indexes()`: `timestamp` desc
  on all five; `apid` and `(apid, timestamp)` on raw_packets and
  decoded_telemetry; TTL `expireAfterSeconds=retention_days*86400` on
  `timestamp` of raw_packets and decoded_telemetry. `insert(collection, doc)
  -> id`, `insert_many`.
- `SQLiteBackend` (aiosqlite, WAL mode). Same five tables with `id INTEGER
  PRIMARY KEY`, `synced INTEGER DEFAULT 0`, `mongo_id TEXT`, `sync_key TEXT`
  (a `uuid4` assigned on every insert; see below). Non-scalar values
  JSON-encoded. Retention: with Mongo enabled, on start delete rows older
  than `retention_days` that are already synced (never delete unsynced
  rows); with `MONGO_URI` unset nothing is ever marked synced, so on start
  instead delete rows older than `retention_days` regardless of sync state
  (there is no Atlas copy to lose).

`Storage` routing:

- `mongo_uri` unset → SQLite only; `health.mongo == "disabled"`.
- `mongo_uri` set → write to Mongo; on `PyMongoError` write to SQLite
  (`synced=0`), set `degraded=True`, log once per outage. Sync task every
  30 s: ping; if ok, upload unsynced rows oldest-first in batches of 200 via
  `insert_many(ordered=False)`, store returned ids in `mongo_id`, mark synced.
  `decoded_telemetry.packet_id`/`alarms.packet_id` referencing a SQLite raw
  packet id are remapped to that row's `mongo_id` during sync (raw packets are
  synced first, so the mapping always exists). Idempotency: each row's
  `sync_key` is uploaded with it and enforced as a sparse unique index in
  Mongo, so a batch re-uploaded after a partial failure (e.g. a crash between
  `insert_many` succeeding and `mark_synced` running) is a no-op — on
  `BulkWriteError` each row is resolved individually by `sync_key` (existing
  doc's id if already present, otherwise a fresh `insert`) before marking
  synced.
- Session doc created at `start()` (SQLite first, mirrored to Mongo), counters
  updated in memory and written at `stop()` plus every 60 s.

Subscriptions: `PacketReceived`, `PacketSent` → raw_packets (apid/seq from a
best-effort header parse, `None` if malformed); `PacketDecoded` → one
decoded_telemetry row per field; `AlarmRaised` → alarms; `CommandCompleted`
→ commands. `packet_id` correlation: `PacketDecoded`/`AlarmRaised` carry the
originating `PacketReceived` event as `source`; Storage keeps a bounded map
(1000 entries) from the source event (held strongly) to a Future resolved
with the raw packet's `(backend, id)`. Because the bus schedules handlers as
tasks, the decoded/alarm insert awaits that Future rather than `id(source)`
directly — keying on the raw `id()` would be unsafe, since CPython can reuse
the address of a freed `PacketReceived` and collide with an unrelated
packet's entry.

### 3.11 `storage/exporter.py`

`async def export(storage, collection, path, *, fmt="csv"|"json", start=None,
end=None, apid=None) -> int` (rows written). Streams from the active backend
in batches of 500 rows; JSON output is a JSON array written incrementally;
CSV columns are the fixed per-collection schema above. CLI:
`python -m cubesat_gs.storage.exporter raw_packets out.csv --start 2026-09-01`.

### 3.12 `core/station.py` and `main.py`

`GroundStation(cfg)` constructs: bus → serial → freq_mgr → builder/tracker →
decoder → telecommand → storage. `start()` order: storage, decoder,
telecommand, freq_mgr, serial last (its `ConnectionChanged(True)` triggers
the initial `FREQ:`). `stop()` reverse. Exposes the modules as attributes for
Phase 2's API.

`main.py`: `--config`, `--sim` (starts `ModemSimulator` TCP server on a free
localhost port and overrides `serial.port`), `--log-level`. Installs SIGINT/
SIGTERM handlers → `stop()`. Logging: console + `RotatingFileHandler`
(`logging.file`, 5 MB × 3).

## 4. Error handling summary

| Failure | Behaviour |
|---|---|
| Modem not present at startup | `ConnectionChanged(False)`, retry every `reconnect_interval`, process keeps running |
| USB disconnect mid-run | same; in-flight command fails; queued commands wait |
| `FREQ:` not acknowledged | `SerialCommandTimeout`; freq state unchanged |
| Malformed RX line / bad hex | `SerialError`, line dropped |
| CCSDS parse error | `PacketMalformed`; raw still stored |
| Unknown APID | stored raw + decoded as `raw_hex`, no exception |
| Truncated payload for defs | partial decode, `error` set |
| Mongo unreachable | SQLite buffer, sync on recovery |
| Both DBs failing (disk full) | log error, events dropped, process keeps running |
| Invalid YAML (config/defs/commands) | fail fast at startup with file and key |
| Subscriber raises | logged with event, other subscribers unaffected |

## 5. Testing

pytest + pytest-asyncio, fully offline. No hardware, no network, no Mongo.

- `test_ccsds.py`: CRC vectors; parse of the exact OBC beacon frame;
  both length conventions; short/version/length errors; build→parse
  round-trip; TX per-APID counters and 14-bit wrap; gap detection global vs
  per_apid with interleaved APIDs (the OBC case).
- `test_telemetry.py`: each type; scale/offset; string/bytes with/without
  length; alarms low/high/nominal/none; unknown APID; truncated payload;
  invalid definition file rejected.
- `test_serial_handler.py` (in-process `SimulatedSerial`): RX with and
  without RSSI/SNR, lowercase hex, malformed hex; ack resolution; one
  outstanding at a time (order preserved); timeout; reconnect after EOF.
- `test_telecommand.py`: PING happy path with latency; timeout + retries +
  backoff; critical refused without confirm; busy; wrong mode; send_raw.
- `test_frequency_manager.py`: mode switch, CUSTOM requires mhz, re-apply on
  reconnect, timeout keeps state.
- `test_storage.py`: SQLite backend CRUD + query + retention; Mongo backend
  against a fake client that fails then recovers → fallback rows synced,
  `packet_id` remapped; exporter CSV/JSON.
- `test_integration.py`: `GroundStation` + `ModemSimulator` + SQLite: beacon
  received on 437.250, switch to TCTM, PING → PONG stored raw + decoded, gap
  detection clean, session counters correct.

## 6. Dependencies (Phase 1)

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

Phase 2/3 add fastapi, uvicorn, websockets, sgp4, skyfield.

## 7. Repository conventions

- Git root = workspace root; remote `origin` = CubeSat-GS.git, branch `main`.
- Commit messages: plain, no attribution trailers.
- `.env` (real `MONGO_URI`) is gitignored; `.env.example` has a placeholder.
  The Atlas password that was shared in chat should be rotated.
- `cubesat_comms-main/` is kept as-is for reference.
