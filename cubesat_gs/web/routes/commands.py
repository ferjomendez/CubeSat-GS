from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import CommandDefOut, CommandHistoryOut, CommandRecordOut, SendCommandIn, SendRawIn

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


@router.get("/commands", response_model=list[CommandDefOut])
async def list_commands(station: GroundStation = Depends(get_station)):
    return [_def_out(c) for c in station.telecommand.commands.values()]


@router.get("/commands/history", response_model=CommandHistoryOut)
async def command_history(station: GroundStation = Depends(get_station),
                          limit: int = Query(50, ge=1, le=500), before: datetime | None = None):
    mem = [_rec_out(r) for r in reversed(station.telecommand.history)]
    if before is not None:
        mem = [m for m in mem if datetime.fromisoformat(m["ts"]) < before]
    items = mem[:limit]
    if len(items) < limit:
        # If mem is not empty, query storage before the oldest mem record.
        # If mem is empty, query storage before the given "before" parameter.
        # This ensures we don't get duplicates of records already in memory.
        oldest_mem = datetime.fromisoformat(mem[-1]["ts"]) if mem else before
        rows = await station.storage.query("commands", end=oldest_mem, limit=limit - len(items) + 100)
        seen = {(m["ts"], m["name"]) for m in items}
        for r in rows:
            key = (r["timestamp"], r["command_name"])
            if key in seen:
                continue
            items.append({"ts": r["timestamp"], "name": r["command_name"], "raw_hex": r["raw_hex_sent"],
                          "status": r["status"], "response_hex": r.get("response_hex"),
                          "latency_ms": r.get("latency_ms"), "attempts": r.get("attempts", 0),
                          "error": None, "pending": False})
            if len(items) >= limit:
                break
    next_before = items[-1]["ts"] if len(items) == limit else None
    return {"items": items, "next_before": next_before}


def _guard_serial(station: GroundStation) -> None:
    if not station.serial.connected:
        raise ApiError(503, "serial_disconnected", "modem is not connected")


@router.post("/commands/raw", response_model=CommandRecordOut)
async def send_raw(body: SendRawIn, station: GroundStation = Depends(get_station)):
    _guard_serial(station)
    rec = await station.telecommand.send_raw(body.hex, confirm=body.confirm)
    if rec.status == "refused":
        detail = json.dumps(CommandRecordOut.model_validate(rec.as_dict()).model_dump(mode="json"))
        raise ApiError(403, "confirm_required", detail)
    return _rec_out(rec)


@router.post("/commands/{name}", response_model=CommandRecordOut)
async def send_command(name: str, body: SendCommandIn, station: GroundStation = Depends(get_station)):
    cdef = station.telecommand.commands.get(name)
    if cdef is None:
        raise ApiError(404, "unknown_command", name)
    _guard_serial(station)
    payload = bytes.fromhex(body.payload_hex.replace(" ", "")) if body.payload_hex else None
    rec = await station.telecommand.send_command(name, confirm=body.confirm, payload_override=payload)
    if rec.status == "refused":
        detail = json.dumps(CommandRecordOut.model_validate(rec.as_dict()).model_dump(mode="json"))
        raise ApiError(403, "confirm_required", detail)
    return _rec_out(rec)
