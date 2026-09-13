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
