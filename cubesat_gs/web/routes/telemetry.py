from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.events import now
from cubesat_gs.core.station import GroundStation
from cubesat_gs.core.telemetry import NUMERIC_TYPES  # struct formats keyed by type name
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.lttb import lttb
from cubesat_gs.web.schemas import TelemetryDefsOut, TelemetryHistoryOut, TelemetryLatestOut

router = APIRouter()


def _defs(station: GroundStation) -> list[dict]:
    return [{"apid": apid, "name": d.name,
             "fields": [{"name": f.name, "type": f.type, "unit": f.unit,
                         "alarm_low": f.alarm_low, "alarm_high": f.alarm_high} for f in d.fields]}
            for apid, d in sorted(station.decoder.definitions.items())]


@router.get("/telemetry/latest", response_model=TelemetryLatestOut)
async def telemetry_latest(station: GroundStation = Depends(get_station)):
    latest = {}
    for apid, d in station.decoder.last_values.items():
        latest[apid] = {"apid": apid, "apid_name": d.apid_name, "ts": now().isoformat(),
                        "fields": [{"name": f.name, "value": f.value, "unit": f.unit, "alarm": f.alarm} for f in d.fields]}
    return {"latest": latest, "definitions": _defs(station)}


@router.get("/telemetry/definitions", response_model=TelemetryDefsOut)
async def telemetry_definitions(station: GroundStation = Depends(get_station)):
    path = station.cfg.resolve(station.cfg.telemetry.definitions)
    return {"yaml": path.read_text(encoding="utf-8"), "definitions": _defs(station)}


@router.get("/telemetry/history", response_model=TelemetryHistoryOut)
async def telemetry_history(station: GroundStation = Depends(get_station), apid: int = Query(...),
                            field: str = Query(...), start: datetime | None = None,
                            end: datetime | None = None, max_points: int = Query(600, ge=10, le=2000)):
    fdef = None
    d = station.decoder.definitions.get(apid)
    if d is not None:
        fdef = next((f for f in d.fields if f.name == field), None)
        if fdef is not None and fdef.type not in NUMERIC_TYPES:
            raise ApiError(422, "not_numeric", f"field {field!r} of APID {apid} is {fdef.type}")
    end = end or now()
    start = start or end - timedelta(hours=1)
    rows = [r async for r in station.storage.iterate("decoded_telemetry", start=start, end=end, apid=apid)]
    rows = [r for r in rows if r.get("field_name") == field and isinstance(r.get("field_value"), (int, float))]
    pts = [(datetime.fromisoformat(r["timestamp"]).timestamp() if isinstance(r["timestamp"], str)
            else r["timestamp"].timestamp(), float(r["field_value"])) for r in rows]
    thinned = lttb(pts, max_points)
    unit = fdef.unit if fdef else (rows[0].get("unit") if rows else None)
    return {"apid": apid, "field": field, "unit": unit,
            "alarm_low": fdef.alarm_low if fdef else None, "alarm_high": fdef.alarm_high if fdef else None,
            "points": [{"t": datetime.fromtimestamp(t, tz=timezone.utc).isoformat(), "v": v} for t, v in thinned],
            "total_rows": len(rows)}
