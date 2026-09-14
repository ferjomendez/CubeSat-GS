from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.pass_predictor import TLEError, pass_to_dict, state_to_dict
from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import PassHistoryOut, PassesOut, PassStateOut, TLEOut, TrackPoint

router = APIRouter()


@router.get("/passes", response_model=PassesOut)
async def list_passes(station: GroundStation = Depends(get_station), days: int | None = Query(None, ge=1, le=14)):
    pp = station.passes
    passes = await pp.upcoming(days) if pp.enabled else []
    return {"enabled": pp.enabled, "reason": pp.reason, "passes": [pass_to_dict(p) for p in passes]}


@router.get("/passes/current", response_model=PassStateOut | None)
async def current_pass(station: GroundStation = Depends(get_station)):
    return state_to_dict(station.passes.current())


@router.get("/passes/history", response_model=PassHistoryOut)
async def pass_history(station: GroundStation = Depends(get_station), limit: int = Query(50, ge=1, le=500)):
    return {"items": await station.storage.query("passes", limit=limit)}


@router.post("/passes/refresh-tle", response_model=TLEOut)
async def refresh_tle(station: GroundStation = Depends(get_station)):
    pp = station.passes
    if not pp.tle_source:
        raise ApiError(400, "no_tle_source", "satellite.tle_source is not configured")
    try:
        l1, l2 = await pp.refresh_tle()
    except TLEError as e:
        raise ApiError(502, "tle_fetch_failed", str(e)) from e
    return {"line1": l1, "line2": l2}


@router.get("/passes/{pass_id}/track", response_model=list[TrackPoint])
async def pass_track(pass_id: str, station: GroundStation = Depends(get_station),
                     step_s: int = Query(10, ge=1, le=120)):
    pts = await station.passes.track(pass_id, step_s=step_s)
    if not pts:
        raise ApiError(404, "unknown_pass", pass_id)
    return [{"t": t.isoformat(), "az": az, "el": el, "range_km": rng, "doppler_hz": dop} for t, az, el, rng, dop in pts]
