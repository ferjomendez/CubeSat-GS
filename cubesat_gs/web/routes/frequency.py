from __future__ import annotations

from fastapi import APIRouter, Depends

from cubesat_gs.core.frequency_manager import Mode
from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.schemas import FrequencyIn, FrequencyOut

router = APIRouter()


def _out(station: GroundStation) -> dict:
    f = station.freq
    return {"mode": f.mode.value, "mhz": f.mhz,
            "presets": {"tctm": station.cfg.frequencies.tctm, "beacon": station.cfg.frequencies.beacon},
            "history": [{"ts": h.ts.isoformat(), "mode": h.mode.value, "mhz": h.mhz} for h in list(f.history)[-20:]]}


@router.get("/frequency", response_model=FrequencyOut)
async def get_frequency(station: GroundStation = Depends(get_station)):
    return _out(station)


@router.put("/frequency", response_model=FrequencyOut)
async def put_frequency(body: FrequencyIn, station: GroundStation = Depends(get_station)):
    if body.mode == "custom" and body.mhz is None:
        raise ApiError(422, "invalid_value", "custom mode requires mhz")
    await station.freq.set_mode(Mode(body.mode), mhz=body.mhz)
    return _out(station)
