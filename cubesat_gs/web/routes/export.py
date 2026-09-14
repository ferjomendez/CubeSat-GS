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
