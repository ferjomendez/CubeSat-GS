# CubeSat-GS — UAI CubeSat Ground Station

Ground station software for the UAI CubeSat: ESP32 + SX1278 LoRa modem on USB serial,
Raspberry Pi host, CCSDS Space Packets, MongoDB Atlas storage with SQLite offline fallback.

Phase 1 + 2 (this state): headless core, FastAPI/WebSocket backend, React dashboard, pass prediction.

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
