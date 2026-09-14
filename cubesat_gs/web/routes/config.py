from __future__ import annotations

from fastapi import APIRouter, Depends

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web import config_writer as cw
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import ConfigIn, ConfigOut, ConfigPutOut, DbStatsOut, SerialPortOut

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


@router.get("/config/serial-ports", response_model=list[SerialPortOut])
async def serial_ports():
    from serial.tools import list_ports
    return [{"device": p.device, "description": p.description or "", "vid": p.vid, "pid": p.pid}
            for p in list_ports.comports()]


@router.get("/db/stats", response_model=DbStatsOut)
async def db_stats(station: GroundStation = Depends(get_station)):
    return {"counts": await station.storage.stats(), "health": await station.storage.health()}
