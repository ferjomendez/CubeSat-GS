from fastapi import APIRouter, Depends, Request

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import get_station
from cubesat_gs.web.schemas import HealthOut, StatusOut

router = APIRouter()


@router.get("/status", response_model=StatusOut)
async def get_status(station: GroundStation = Depends(get_station)):
    return station.status()


@router.get("/health", response_model=HealthOut)
async def get_health(request: Request, station: GroundStation = Depends(get_station)):
    hub = request.app.state.hub
    h = await station.storage.health()
    h["web"] = {"clients": hub.client_count if hub is not None else 0}
    return h
