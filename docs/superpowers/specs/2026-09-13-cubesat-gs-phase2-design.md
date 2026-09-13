# CubeSat Ground Station — Phase 2 Design (Web Backend, Dashboard, Pass Predictor)

Date: 2026-09-13
Status: approved in brainstorming, pending spec review
Builds on: `docs/superpowers/specs/2026-09-13-cubesat-gs-phase1-design.md` (Phase 1, merged at 155ff9d)

## 1. Scope

Phase 2 adds everything an operator sees and touches:

- `cubesat_gs/web/` — FastAPI backend: REST for history/commands/config/export, one WebSocket
  (`/ws`) streaming a snapshot then typed deltas, static serving of the built dashboard.
- `cubesat_gs/web/frontend/` — React 18 + TypeScript + Tailwind + shadcn/ui dashboard, built
  with Vite into `cubesat_gs/web/static/` (committed; the Pi needs no Node).
- `cubesat_gs/core/pass_predictor.py` — satellite pass prediction (skyfield), folded in from
  Phase 3 so the Pass Tracker view ships complete.

Out of scope: frequency auto-mode (still "future"), authentication (LAN only), light theme.

Decisions from brainstorming:
- Real-time model: **snapshot + delta over one WebSocket**; REST only for history, mutations,
  config, export.
- Access: LAN, no auth. Critical commands still need the confirmation dialog.
- Config edits: written back to `gs_config.yaml` (comments preserved), applied live where safe.
- Frontend delivery: built bundle committed under `web/static/`.

## 2. Phase 1 interfaces consumed

| Need | Phase 1 interface |
|---|---|
| Status | `GroundStation.status()` (sync) |
| Live events | `EventBus.subscribe(EventType, handler)` for every event type in `core/events.py` |
| History | `Storage.query(collection, *, start, end, apid, limit)`, `Storage.iterate(...)`, `Storage.stats()`, `Storage.health()` |
| Export | `storage.exporter.export(storage, collection, path, fmt, start, end, apid)` |
| Commands | `TelecommandManager.commands`, `.history`, `.pending`, `send_command(name, confirm=, payload_override=)`, `send_raw(hex)`; exceptions `CommandBusyError`, `WrongModeError`, `UnknownCommandError` |
| Frequency | `FrequencyManager.mode`, `.mhz`, `.history`, `set_mode(Mode, mhz=)` |
| Telemetry | `TelemetryDecoder.last_values`, `.definitions` |
| Config | `GSConfig` dataclasses, `load_config()` for validation |
| Serial | `SerialHandler.connected`, `.port`; `serial_handler.detect_port()` and `serial.tools.list_ports` for the port picker |

Phase 1 changes required (small): `Storage` gains a `passes` collection and stamps
`session.pass_id`; `core/events.py` gains `PassStarted`/`PassEnded`/`PassUpdate`;
`main.py` gains `--no-web` and starts uvicorn in-loop; `GroundStation` gains
`.passes: PassPredictor | None` and `.hub` is *not* on the station (the web layer owns it).

## 3. Backend

### 3.1 Layout

```
cubesat_gs/web/
  __init__.py
  app.py           # create_app(station) -> FastAPI
  hub.py           # WebSocketHub
  schemas.py       # Pydantic models for every REST/WS payload
  deps.py          # get_station() dependency, error → HTTP mapping
  routes/
    __init__.py
    status.py  feed.py  telemetry.py  commands.py  frequency.py  passes.py  config.py  export.py
  static/          # built bundle (committed): index.html, assets/*.{js,css} (hashed)
  frontend/        # Vite source (see §5)
```

### 3.2 Process model

`main.py` builds `GroundStation`, calls `create_app(station)`, and runs
`uvicorn.Server(uvicorn.Config(app, host, port, loop="asyncio", log_config=None)).serve()`
as a task in the same event loop as serial/storage — no threads. `--no-web` skips it.
Shutdown order on SIGINT/SIGTERM: `server.should_exit = True` → await server task →
`station.stop()`. uvicorn's own signal handlers are disabled (`install_signal_handlers`
overridden) so `main.py` remains the single owner of signals.

`create_app(station)` installs a lifespan that starts/stops the `WebSocketHub` and the
`PassPredictor` scheduler. The app never constructs Phase 1 modules.

### 3.3 `hub.py` — WebSocketHub

- Subscribes to: `ConnectionChanged, SerialError, PacketReceived, PacketSent, ModemAck,
  SequenceGap, PacketDecoded, PacketMalformed, AlarmRaised, CommandCompleted,
  FrequencyChanged, PassStarted, PassEnded, PassUpdate` plus a synthetic
  `CommandStarted` published by the commands route before calling `send_command`.
- Feed entries: `PacketReceived` creates a pending entry keyed by `id(event)` (held
  strongly, like Storage); `PacketDecoded`/`PacketMalformed` completes it (decoded fields,
  `kind`) and the completed entry is broadcast as one `packet` message. `PacketSent`
  broadcasts immediately with `kind: "command"`. Entries not completed within 2 s are
  broadcast as-is (`kind: "unknown"`). Ring buffer: last 500 completed entries.
- Broadcast: each client has an `asyncio.Queue(maxsize=500)`; the hub `put_nowait`s; a
  per-client sender task drains it. `QueueFull` → close that client with code 1013. The bus
  handler never awaits network I/O.
- Snapshot on connect (built synchronously from in-memory state, no DB):
  `{status, feed, telemetry_latest, pending_command, next_pass, current_pass, alarms_active}`
  where `alarms_active` = fields whose latest decode is `low`/`high`.
- `status` messages are the full `station.status()` dict, emitted on
  `ConnectionChanged`, `FrequencyChanged`, storage state change (polled every 5 s and
  emitted only on change), `PassStarted/Ended`.
- Client → server: `{"type":"ping"}` → `{"type":"pong"}`; anything else ignored.
- Messages are JSON, `{"type": str, "ts": iso, "data": {...}}`; bytes as uppercase hex,
  datetimes ISO-8601 UTC.

### 3.4 REST endpoints

All under `/api`, JSON; errors are `{"error": str, "detail": str|None}`.

| Method & path | Purpose | Notes |
|---|---|---|
| GET `/status` | `station.status()` + `passes: {enabled, next, current}` | |
| GET `/health` | `storage.health()` + `web: {clients: n}` | |
| GET `/packets` | paged raw feed | `apid`, `direction`, `kind`, `start`, `end`, `limit≤500` (default 100), `before` (id cursor); newest first; each row joined with its decoded fields via `decoded_telemetry.packet_id` when present |
| GET `/telemetry/latest` | `decoder.last_values` + definitions (units, thresholds) | |
| GET `/telemetry/history` | `apid`, `field`, `start`, `end`, `max_points` (≤2000, default 600) | server-side downsampling: largest-triangle-three-buckets over the time-ordered rows; numeric fields only |
| GET `/telemetry/definitions` | raw YAML text + parsed | |
| GET `/commands` | registry (`CommandDef` minus payload bytes → hex/utf-8 preview) | |
| GET `/commands/history` | `telecommand.history` (in-memory) merged with `storage.query("commands")` for older rows; `limit`, `before` | |
| POST `/commands/{name}` | body `{confirm: bool, payload_hex?: str}` → `CommandRecord` | 404 unknown; 403 critical w/o confirm (`status=refused` record still returned in body); 409 busy; 400 wrong mode; 503 serial disconnected |
| POST `/commands/raw` | `{hex: str, confirm: true}` | 422 bad hex; same conflicts |
| GET `/frequency` | `{mode, mhz, history[-20:], presets: {tctm, beacon}}` | |
| PUT `/frequency` | `{mode, mhz?}` | 422 CUSTOM without mhz; 504 if modem times out (`SerialCommandTimeout`) |
| GET `/passes` | `{enabled, reason?, passes: [Pass]}` for `prediction_days` | |
| GET `/passes/current` | `PassState | null` | |
| GET `/passes/{id}/track` | `[{t, az, el, range_km, doppler_hz}]` at 10 s step | |
| GET `/passes/history` | `storage.query("passes")` | |
| POST `/passes/refresh-tle` | fetch `tle_source`, update config, recompute | 400 if no URL; 502 on fetch failure |
| GET `/config` | effective config, with `writable: [sections]` and `applies: {section.key: "live"|"restart"}` | secrets never included (`mongo_uri` omitted) |
| PUT `/config` | body `{section: {key: value}}` for writable sections only | validates by building `GSConfig` from the merged dict; writes via ruamel round-trip to a temp file then `os.replace`; applies live: `frequencies` (updates `FrequencyManager` presets), `station`/`satellite`/`passes` (recompute passes), `serial.port` (reconnect: `serial.stop()`; `cfg.serial.port = ...`; `serial.start()`); others → `restart_required: true` in the response |
| GET `/config/serial-ports` | `[{device, description, vid, pid}]` | |
| GET `/db/stats` | `storage.stats()` | |
| POST `/export` | `{collection, fmt, start?, end?, apid?}` → `FileResponse` | writes to `data/exports/<collection>-<ts>.<fmt>` via `exporter.export`, streams it, `Content-Disposition: attachment` |
| GET `/{path}` | static SPA | `index.html` for any non-`/api`, non-`/ws` path without a file extension match |

Writable config sections: `serial`, `frequencies`, `station`, `satellite`, `passes`,
`commands.default_timeout/max_retries/retry_backoff`. Read-only: `database`, `logging`,
`web`, `ccsds`, `telemetry` (edit YAML + restart; the UI says so).

### 3.5 `schemas.py`

Pydantic v2 models: `StatusOut`, `HealthOut`, `FeedEntry`, `TelemetryField`,
`TelemetryLatest`, `TelemetryPoint`, `CommandDefOut`, `CommandRecordOut`, `SendCommandIn`,
`SendRawIn`, `FrequencyOut`, `FrequencyIn`, `PassOut`, `PassStateOut`, `TrackPoint`,
`ConfigOut`, `ConfigIn`, `SerialPortOut`, `ExportIn`, `WsMessage` (discriminated union on
`type`). `GET /api/schema.json` returns the combined JSON schema; the frontend build has a
script that diffs it against `src/api/types.ts` field names (guard against drift; run in
the frontend test step).

### 3.6 `core/pass_predictor.py`

```python
@dataclass(frozen=True) class Pass: id: str; aos: datetime; los: datetime; max_el: float; aos_az: float; los_az: float; duration_s: float; tca: datetime
@dataclass(frozen=True) class PassState: pass_id: str; az: float; el: float; range_km: float; doppler_hz: float; progress: float; t: datetime
class PassPredictor:
    def __init__(self, bus, station_cfg, satellite_cfg, passes_cfg, *, tctm_mhz: float)
    enabled: bool; reason: str | None
    async def start() / async def stop()
    async def set_tle(line1, line2) -> None            # validates, recomputes
    async def set_location(lat, lon, alt) -> None
    async def refresh_tle() -> tuple[str, str]        # httpx GET tle_source (10 s), picks the entry matching satellite.name or the first
    async def upcoming(days: int | None = None) -> list[Pass]     # cached; recomputed hourly or on change
    def current() -> PassState | None                 # cheap: uses cached satellite object
    async def track(pass_id, step_s=10) -> list[tuple[datetime, float, float, float, float]]
    def doppler_hz(freq_mhz, t=None) -> float         # -range_rate/c * f
    def is_visible() -> bool
```

- skyfield `EarthSatellite` + `wgs84.latlon`; `find_events` with `altitude_degrees=min_elevation`.
- CPU work (`upcoming`, `track`) runs via `asyncio.to_thread`; the `sgp4` object is
  reused. On a Pi 3B+ a 7-day search is ~1–2 s; cached in memory.
- Scheduler task: every 1 s while a pass is in progress publish `PassUpdate(state)`;
  publish `PassStarted(pass)` at AOS and `PassEnded(pass, packets_received)` at LOS;
  recompute `upcoming` hourly; `refresh_tle` daily at 03:00 UTC if `tle_source` set.
- `enabled=False` with `reason` when TLE lines are empty or fail to parse; every public
  method then returns empty/None, never raises. TLE fetch failures log a warning and keep
  the old TLE.
- Storage: new collection `passes` `{pass_id, aos, los, max_el, packets_received,
  packets_sent, commands_sent}`; row inserted at `PassStarted`, updated at `PassEnded`;
  `session.pass_id` set during a pass. Added to `COLLECTIONS`, `COLUMNS`, indexes, and
  `to_bsonable` paths. Counters come from the existing session counters delta.

Events added to `core/events.py`: `PassStarted(pass_: Any)`, `PassEnded(pass_: Any,
packets_received: int)`, `PassUpdate(state: Any)`.

### 3.7 Error handling

- Hub: handler exceptions are logged by the bus; a client send failure closes that client.
- Routes: Phase 1 exceptions mapped in `deps.py` (`CommandBusyError→409`, `WrongModeError→400`,
  `UnknownCommandError→404`, `SerialCommandTimeout→504`, `SerialDisconnected→503`,
  `ValueError→422`). Unhandled → 500 with `{"error":"internal"}` and a logged traceback.
- Config PUT: validation failure → 422 with the dataclass error message; the YAML file is
  written only after validation passes, via temp file + `os.replace`.
- Pass predictor never raises out of its public API.
- uvicorn access logs go through the app's logger at DEBUG (quiet by default).

## 4. WebSocket message reference

```
snapshot   {status, feed:[FeedEntry], telemetry_latest:{apid:TelemetryLatest}, pending_command, next_pass, current_pass, alarms_active:[{apid,field_name,value,alarm}]}
status     StatusOut
packet     FeedEntry {id, ts, direction:"rx"|"tx", apid, apid_name, seq, raw_hex, rssi, snr, freq_mhz, kind:"beacon"|"telemetry"|"command"|"malformed"|"unknown", summary, fields:[TelemetryField]|null}
telemetry  {apid, apid_name, ts, fields:[TelemetryField]}
alarm      {ts, apid, field_name, value, threshold, alarm_type}
gap        {ts, apid, expected, received, missed}
command    CommandRecordOut (+ {pending:true} variant emitted at send start)
pass       PassStateOut | {event:"aos"|"los", pass:PassOut}
pong       {}
```

`summary` for a feed entry: beacon/telemetry → first string field value or `"<n> fields"`;
command → command name if it matches a TX record, else `"TX <n> B"`; malformed → reason.

## 5. Frontend

### 5.1 Stack & layout

Vite 5, React 18, TypeScript strict, Tailwind 3, shadcn/ui (button, dialog, table, tabs,
select, input, badge, tooltip, toast, scroll-area, separator), Radix primitives, Recharts,
TanStack Query 5, Zustand, react-router 6, @tanstack/react-virtual, Vitest + Testing
Library. `npm run build` → `../static/` (hashed assets, `index.html`). `npm run dev`
proxies `/api` and `/ws` to `http://localhost:8080`.

```
web/frontend/src/
  api/          client.ts (fetch wrapper, error shape), types.ts (mirrors schemas.py), ws.ts (reconnecting client)
  store/        gs.ts (Zustand: snapshot/delta reducer, feed pause buffer, alarms), selectors.ts
  components/   StatusStrip, Panel, Value (unit + tabular nums), AlarmBadge, Countdown, PolarPlot (SVG), TimeSeries (Recharts), HexView, ConfirmDialog, DisconnectedBanner
  views/        Overview, LiveFeed, Telemetry, Telecommand, PassTracker, Settings
  lib/          time.ts (UTC/local), format.ts, lttb.ts (client-side thinning for live windows), polar.ts
  App.tsx (router, layout: left nav rail + content), main.tsx, index.css (tokens)
```

### 5.2 Design direction

Mission-control instrument, dark only, no cards-with-shadows. Panels are hairline-bordered
regions with uppercase 10 px tracking-wide labels. Two typefaces: a condensed grotesk for
labels/nav (Barlow Condensed or IBM Plex Sans Condensed, self-hosted) and JetBrains Mono
(tabular figures) for every number, hex, timestamp. Four semantic colours only —
`nominal` (green), `warn` (amber), `alarm` (red), `info` (blue) — each as a dim/solid pair;
everything else neutral greys on near-black. 4 px spacing rhythm, dense tables with 28 px
rows. Every value shows its unit; timestamps UTC with local-time tooltip. Motion: none
except the pass progress bar and countdown. Layout: 56 px left rail (icons + labels), full-
width content; usable at 1280×720 and up (lab screens), degrades to single column ≥768.

### 5.3 Views (behaviour)

- **Overview**: status strip (serial connected/port, mode/MHz with quick TCTM/BEACON
  buttons, storage ok/degraded/disabled + pending sync); last-packet tile; next pass
  (countdown, max el, AOS az) and current-pass progress bar with az/el/doppler; today's
  counters (rx packets, tx, command success rate = responded/(responded+timeout+failed),
  uptime); 15-min packets/min sparkline from the feed buffer.
- **Live Feed**: virtualised rows; pause buffers deltas and shows "N new" chip; filters
  (APID multi-select from definitions + seen, direction, kind, time range); expand row →
  decoded fields table + hex dump (16/row); "Load older" fetches `/api/packets?before=`.
- **Telemetry**: one panel per APID with latest fields, unit, alarm badge, age; numeric
  field click → chart panel (Recharts line, threshold reference lines, window 1h/6h/24h/
  custom via `/api/telemetry/history`; live points appended from deltas, thinned by LTTB
  to ≤600 on screen).
- **Telecommand**: registry table (name, description, APID, response APID, timeout,
  critical badge) with Send → dialog (payload preview, critical warning in red, confirm
  checkbox required for critical); pending bar with elapsed timer and attempt count;
  history table (ts, name, status badge, response summary, latency, attempts); raw hex
  input (validates hex, byte count, confirm dialog).
- **Pass Tracker**: upcoming table (AOS/LOS local+UTC, duration, max el, az); polar plot
  of selected pass (`/track`) with current position; current-pass panel; history table with
  packet counts; disabled state explains "TLE not configured" with a link to Settings.
- **Settings**: sections as forms (serial port select from `/config/serial-ports` + auto,
  frequencies, station lat/lon/alt, satellite name/TLE textarea/URL + Refresh, passes
  min-el/days, command timeouts) each with "applies live"/"restart required" badge and
  Save; telemetry definitions viewer (read-only, monospace); database stats + export form
  (collection, fmt, range, apid → download); read-only sections shown greyed with "edit
  gs_config.yaml".
- **Global**: `DisconnectedBanner` when WS is down (mutations disabled); alarm toasts;
  nav badges for active alarms and pending command.

### 5.4 Store semantics

`snapshot` replaces state; `packet` appends to `feed` (cap 2000, drop oldest) unless
paused (then to `pausedBuffer`, capped 2000); `telemetry` updates `latest[apid]` and
appends to `series[apid][field]` (cap 5000 points); `alarm` updates `alarmsActive` and
pushes a toast; `command` sets/clears `pendingCommand` and prepends to `commandHistory`;
`status` replaces `status`; `pass` updates `currentPass`/`nextPass`. WS reconnect
re-hydrates from a new snapshot (feed merged by `id`).

## 6. Testing

Backend (pytest, offline; `httpx.AsyncClient(transport=ASGITransport(app))`; station =
`GroundStation` + `ModemSimulator` + SQLite, `create_session` normal):
- `test_web_status.py`, `test_web_ws.py` (snapshot; beacon → `packet`+`telemetry` deltas;
  slow client closed 1013; `ping/pong`), `test_web_commands.py` (200/403/409/400/422/503),
  `test_web_feed_telemetry.py` (paging, filters, downsampling cap), `test_web_frequency.py`,
  `test_web_config.py` (round-trip preserves comments; read-only → 422; `frequencies` applies
  live; temp-file write), `test_web_passes.py` (disabled; enabled with a pinned ISS TLE and a
  frozen `now` → ≥1 pass; track shape; refresh-tle with a mocked httpx transport),
  `test_web_export.py` (CSV attachment), `test_web_static.py` (index.html + hashed asset from
  the committed bundle; SPA fallback), `test_pass_predictor.py` (deterministic pass count for
  a fixed epoch/location; Doppler sign change through TCA; disabled without TLE; bad TLE →
  reason), `test_storage_passes.py` (passes rows, session.pass_id).
- `test_schema_sync.py`: dumps `/api/schema.json` and asserts every field name in the
  Pydantic models appears in `frontend/src/api/types.ts` (string search).

Frontend (Vitest): store reducer (snapshot, deltas, pause buffer, caps), `lttb.ts`,
`polar.ts`, `format.ts`. Run as part of the frontend task; not part of `pytest`.

## 7. Dependencies

Python: `fastapi>=0.115`, `uvicorn[standard]>=0.30`, `websockets>=12`, `httpx>=0.27`,
`ruamel.yaml>=0.18`, `skyfield>=1.49`, `sgp4>=2.23`, `python-multipart` (FastAPI forms, not
required but harmless — omit). Node (dev only): as §5.1.

## 8. Repository conventions

Unchanged from Phase 1: branch off `main` (`phase2-web`), plain commit messages, no
attribution trailers, secrets only in `.env`. `web/static/` is committed; `web/frontend/
node_modules/` and `dist/` are ignored. `data/exports/` is ignored.
