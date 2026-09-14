# Handoff — CubeSat GS Phase 2 (para continuar en un chat nuevo)

**Fecha:** 2026-09-13 · **Repo:** https://github.com/ferjomendez/CubeSat-GS.git · **Git root:** `C:\Users\ferjo\Desktop\Fernando Mendez\Aerospace Team UAI` (rutas con espacios: siempre entre comillas).

## Estado en una línea

Fase 1 (núcleo headless) está en `main`. Fase 2 se está ejecutando en la rama **`phase2-web`** (HEAD `0d4b62c`, 16 commits sobre `main`, **150 tests verdes con `python -m pytest -q -W error`**, working tree limpio, nada pusheado aún). **Tareas 1–6 completas y revisadas. Tarea 7 implementada pero con 3 hallazgos de revisión abiertos (el fix round 1 no empezó: el subagente chocó con el límite de sesión de la API, que se resetea a las 21:00 America/Santiago). Faltan Tarea 7 (fix) → Tarea 15.**

## Cómo retomar (instrucción para el nuevo chat)

Pedirle a Claude:

> Lee `docs/superpowers/HANDOFF-phase2.md` y continúa la ejecución del plan `docs/superpowers/plans/2026-09-13-cubesat-gs-phase2.md` con `superpowers:subagent-driven-development`. El ledger está en `.superpowers/sdd/2026-09-13-cubesat-gs-phase2/progress.md`; las tareas marcadas `complete` no se repiten. Retoma en Task 7 fix round 1 con un implementer nuevo. Usa Haiku para implementers cuando el plan trae el código completo (Tasks 7–10, 15), Sonnet para las vistas del frontend (11–14) y para reviewers, Opus solo para la revisión final.

El skill lee el ledger y sabe dónde está. Los briefs de las Tasks 1–10 ya están generados en `.superpowers/sdd/2026-09-13-cubesat-gs-phase2/task-N-brief.md` (el script `task-brief` del skill los regenera si hace falta). Cada implementer recibe: el brief, el contexto de interfaces de abajo, y la ruta del report `task-N-report.md`.

## Reglas duras del proyecto (no negociables)

- **Nunca** agregar `Co-Authored-By` ni "Generated with Claude" a commits/PRs (instrucción del usuario; guardada en memoria).
- `MONGO_URI` (credenciales Atlas) vive solo en `cubesat_gs/.env` (gitignored). Nunca en archivos trackeados ni en respuestas de la API. El usuario rotará la contraseña cuando todo funcione.
- Tests: `python -m pytest -q -W error` desde el git root, debe quedar limpio (sin warnings). `pytest.ini` tiene `asyncio_mode = auto`.
- Un solo event loop asyncio, sin threads (salvo `asyncio.to_thread` para skyfield). **Prohibido** meter `await asyncio.sleep(0)` o `bus.drain()` en código de producción para que pase un test; los tests hacen poll con deadline (`wait_until` en `cubesat_gs/tests/conftest.py`).
- Tests 100 % offline: simulador (`cubesat_gs/tests/serial_simulator.py`), SQLite en `tmp_path`, `httpx.MockTransport` / `ASGITransport`, sin red.
- API bajo `/api`; errores `{"error": str, "detail": str|null}`; mapeo `CommandBusyError→409`, `WrongModeError→400`, `UnknownCommandError→404`, `SerialCommandTimeout→504`, `SerialDisconnected→503`, `ValueError→422`, crítico sin confirm→403. Toda ruta declara `response_model` (convención desde Task 6).
- WS: `{"type", "ts" (ISO UTC), "data"}`; bytes en hex mayúsculas.
- Frontend: solo dark; 4 colores semánticos (nominal verde / warn ámbar / alarm rojo / info azul); JetBrains Mono tabular para números; Barlow Condensed para labels; caps del store: feed 2000, series 5000/campo; el bundle compilado se **commitea** en `cubesat_gs/web/static/`.
- Toolchain: Python 3.11.4, Node 24.16, npm 11.13. Deps Python de Fase 2 ya instaladas (fastapi 0.141, uvicorn 0.52, httpx 0.28, skyfield 1.55, sgp4, ruamel.yaml 0.19, websockets 17).

## Documentos de referencia

- Spec Fase 2 (vinculante): `docs/superpowers/specs/2026-09-13-cubesat-gs-phase2-design.md`
- Plan Fase 2 (15 tareas, código completo para backend): `docs/superpowers/plans/2026-09-13-cubesat-gs-phase2.md`
- Spec/plan Fase 1: `docs/superpowers/specs/2026-09-13-cubesat-gs-phase1-design.md`, `docs/superpowers/plans/2026-09-13-cubesat-gs-phase1.md`
- Ledger SDD (fuente de verdad del progreso, rulings, minors diferidos): `.superpowers/sdd/2026-09-13-cubesat-gs-phase2/progress.md`
- Reports por tarea: `.superpowers/sdd/2026-09-13-cubesat-gs-phase2/task-N-report.md`

## Lo hecho en `phase2-web` (Tasks 1–7)

| Task | Qué | Commits | Estado |
|---|---|---|---|
| 1 | Eventos `PassStarted/PassEnded/PassUpdate/CommandStarted`; colección `passes`; `Storage.pass_counters`; deps en requirements | c3e7374, ad69e3b | ✅ |
| 2 | `core/pass_predictor.py` (skyfield): `Pass`, `PassState`, `PassPredictor` (`set_tle` restaura TLE previo, `upcoming` cache 1 h con contador de generación, `current`, `track`, `doppler_hz`, `state_at` normaliza naive→UTC) | f86918a, 81a7d18, 23f7298 | ✅ |
| 3 | Scheduler (`start/stop`, `_tick`: AOS/Update/LOS, recompute horario **y cuando `_cache_at is None`**), `refresh_tle` (httpx, `parse_tle_text`), `pass_to_dict/state_to_dict`, `GroundStation.passes` + `status()["passes"]` | 29246c3, 867a015, 77a1c2e | ✅ |
| 4 | `web/schemas.py` (todos los modelos), `web/deps.py` (ApiError + mapeo), `web/app.py` `create_app(station, *, static_dir)`, `routes/status.py`, fixture `web_stack` → `(station, sim, client)` | 41a0991 | ✅ |
| 5 | `web/hub.py` `WebSocketHub` (snapshot + deltas, ring 500, cola 500, 1013 slow-client, pending TTL 2 s, `feed_entry_from_row`), `/ws`, lifespan | 90525ae, 48112f7 | ✅ |
| 6 | `web/lttb.py`; `routes/feed.py` (`GET /api/packets` con cursor `<iso>\|<id>`, `_id_key` numérico/ObjectId, refetch loop acotado, campos ordenados por id); `routes/telemetry.py` (`latest`, `history` LTTB, `definitions`); `NUMERIC_TYPES` en `core/telemetry.py`; wrappers `PacketsPageOut/TelemetryLatestOut/TelemetryDefsOut` | 87cf8e6, 97104a9, d97b9bb, ddc5884 | ✅ |
| 7 | `routes/commands.py`, `routes/frequency.py`, `CommandStarted` publicado en `TelecommandManager._execute` (attempt 1, antes de `send_tx`) | 0d4b62c | ⚠️ fix pendiente |

### Task 7 — hallazgos abiertos (fix round 1, nada aplicado aún)

1. **`response_model` faltante** en `GET /api/commands` (usar `list[CommandDefOut]`) y `GET /api/commands/history` (crear `CommandHistoryOut(items: list[CommandRecordOut], next_before)` en `schemas.py`).
2. **Comando crítico sin `confirm` debe pasar por el flujo "refused" del manager** (ruling del controller; la spec manda): la ruta hoy corta con un 403 de string antes de llamar al manager. Debe llamar siempre a `station.telecommand.send_command(...)`; el manager devuelve `CommandRecord(status="refused")` (`core/telecommand.py:112-116`) que queda en history/storage; si `status == "refused"` → `ApiError(403, "confirm_required", json.dumps(record como CommandRecordOut))`. Igual criterio para `/api/commands/raw` sin confirm. Actualizar el test del 403 (`json.loads(detail)["status"] == "refused"` y el registro aparece en history). Quitar el `import json` muerto o usarlo.
3. **Merge de history sin test**: escribir 3 filas `commands` vía `station.storage.write("commands", {timestamp, command_name, raw_hex_sent, response_received, response_hex, latency_ms, status, attempts})` más antiguas que cualquier registro en memoria, mandar un PING por API, paginar `GET /api/commands/history?limit=2` siguiendo `next_before` hasta `null`; assert orden newest-first, sin duplicados `(ts, name)`, 4 registros.

Después: `python -m pytest cubesat_gs/tests/test_web_commands.py cubesat_gs/tests/test_web_frequency.py -q -W error`, suite completa, commit, re-review scoped (script `review-package PLAN 0d4b62c HEAD`).

## Lo que falta (Tasks 8–15)

| Task | Qué | Modelo sugerido |
|---|---|---|
| 8 | `routes/passes.py`: `GET /api/passes?days`, `/passes/current`, `/passes/history?limit`, `/passes/{id}/track?step_s` (404 si no existe), `POST /passes/refresh-tle` (400 `no_tle_source`, 502 `tle_fetch_failed`); propiedad `PassPredictor.tle_source` | Haiku (código completo en el plan) |
| 9 | `web/config_writer.py` (`WRITABLE`, `APPLIES` live/restart, `public_config` **omite `mongo_uri` y `base_dir`**, `validate_merge` con ruamel round-trip, `write_config` temp+`os.replace`, `apply_live`), `routes/config.py` (`GET/PUT /api/config`, `GET /api/serial/ports`, `GET /api/db/stats`), `routes/export.py`; `GSConfig.config_path`; `FrequencyManager.set_presets`; `PassPredictor.set_tle_source` | Haiku |
| 10 | `main.py` `--no-web/--host/--port`, `web.serve()` uvicorn in-loop (`loop="none"`, sin signal handlers), SPA fallback (`/assets/*`, resto → `index.html` o 503 `dashboard_not_built`), placeholder `web/static/index.html` | Haiku |
| 11 | Scaffold Vite + React 18 + TS + Tailwind + shadcn + Recharts + TanStack Query + Zustand + react-router + Vitest en `cubesat_gs/web/frontend/`; tokens de diseño; `api/types.ts` (espejo de `schemas.py`, incluidos los wrappers nuevos), `api/client.ts`, `api/ws.ts` (reconexión 1→10 s, ping 20 s), `store/gs.ts` (`applyMessage`, pausa/flush), `lib/{format,time,lttb,polar}.ts` + tests Vitest. `vite.config` con proxy a `/api` y `/ws`, `outDir: "../static"` | Sonnet |
| 12 | Vistas Overview (hero `PassInstrument`: polar SVG + countdown/progress) y Live Feed (virtualizado, pausa) | Sonnet |
| 13 | Telemetry (`TimeSeries` Recharts con LTTB ≤600 pts, umbrales) y Telecommand (`CommandDialog` confirm) | Sonnet |
| 14 | Pass Tracker y Settings (`ConfigSection`, export) | Sonnet |
| 15 | `GET /api/schema.json`, `tests/test_schema_sync.py` (types.ts ↔ schemas.py), `npm run build` y **commit de `web/static/`**, README, corrida e2e `python cubesat_gs/main.py --sim` | Haiku + verificación manual |

Nota: el skill `web-artifacts-builder` que pidió el usuario **no está instalado**; el scaffold de Vite se hace a mano (ya decidido). La dirección de diseño salió de `frontend-design`: paleta grafito fría (bg `#0E1116`, línea `#262D37`, texto `#D6DCE4`, dim `#8A94A3`; nominal `#43C97A`, warn `#E0A526`, alarm `#E5484D`, info `#4C9BE8`), Barlow Condensed + JetBrains Mono, el instrumento de pase como único elemento audaz.

## Interfaces clave ya existentes (para no releer todo)

- `GroundStation(cfg, *, open_connection=None, mongo_client_factory=None)`: `.bus .serial .freq .builder .decoder .telecommand .storage .passes`, `start()/stop()`, `status()`.
- `Storage.query(collection, *, start, end, apid, limit)` (filas con `id` **str** en ambos backends), `.iterate`, `.stats()`, `.health()`, `.state`, `.session`, `.write(collection, doc)` → `Ref=(backend, id)`, `.pass_counters`.
- `TelecommandManager.commands/.history/.pending`, `send_command(name, *, confirm, payload_override)`, `send_raw(hex)`; `CommandRecord(ts, name, raw_hex, status, response_hex, latency_ms, attempts, error, pending)`.
- `FrequencyManager.mode/.mhz/.history`, `set_mode(Mode, mhz=)`.
- `PassPredictor`: ver Tasks 2/3 arriba; `pass_to_dict`, `state_to_dict`, `parse_tle_text`, `TLEError`.
- `WebSocketHub.snapshot()`, `.feed`, `feed_entry_from_row(row, decoded_rows=None)`; `app.state.hub`.
- Fixture `web_stack` → `(station, sim, client)`; `wait_until(pred, timeout)`.
- Simulador: PING (APID 100) → PONG APID 101 `"PONG_DATA_6.28"`; beacon APID 10 cada 0.1 s en tests; `sim.silent = True` para forzar timeouts.
- Valores pinneados de pases (skyfield 1.55): TLE ISS `1 25544U 98067A   24007.51787037  .00017371  00000+0  31288-3 0  9994` / `2 25544  51.6412 203.6489 0004735  97.8797 262.2814 15.49897836434892`; observador −33.35, −70.67, 500 m; now `2024-01-07T12:00Z`; 4 pases/24 h ≥10°; primer AOS `2024-01-08T00:08:54Z`, LOS `00:14:12Z`, max el 21.3°; tercer pase 44.8°; Doppler 435.5 MHz +4008 Hz (TCA−60 s) / −4124 Hz (TCA+60 s).

## Rulings del controller hasta ahora (para que el usuario pueda revertir lo que no le guste)

1. Task 2: datetimes naive se tratan como UTC en `state_at`.
2. Task 2: contador de generación en `upcoming()` para no cachear búsquedas obsoletas tras un setter.
3. Task 2: `set_tle` corre `_load_tle` en `asyncio.to_thread`.
4. Task 3: se quitaron `bus.drain()`/`sleep(0)` de producción; tests con poll.
5. Task 3: `_tick` recomputa también cuando `_cache_at is None` (tras cualquier setter/TLE refresh) — afecta a `apply_live` de Task 9 (deseado).
6. Task 3: `next(..., None)` en `_tick` (no revienta si un recompute cambia ids).
7. Task 6: cursor excluye `ts == cursor_ts and id >= cursor_id` con `_id_key`; `next_before` según página cruda llena; refetch loop acotado (4 iteraciones / 4096).
8. Task 6: campos decodificados ordenados por id asc dentro de cada paquete.
9. Task 6: `response_model` en todas las rutas + wrappers nuevos en `schemas.py` (Task 11 debe espejarlos en `types.ts`).
10. Task 7: 403 de comando crítico sin confirm pasa por el flujo `refused` del manager (audit trail) — **pendiente de aplicar**.

Minors diferidos (para la revisión final): ver las líneas `minor (deferred)` en el ledger.

## Al terminar Task 15

Revisión final de toda la rama (Opus, `review-package PLAN a229cfa HEAD`), un solo fix wave, re-review, borrar `.superpowers/sdd/2026-09-13-cubesat-gs-phase2/`, y `superpowers:finishing-a-development-branch` (en Fase 1 el usuario eligió merge local a `main`; preguntar igual). Push a `origin` solo con OK del usuario.
