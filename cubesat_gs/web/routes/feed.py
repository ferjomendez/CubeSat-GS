from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.hub import feed_entry_from_row
from cubesat_gs.web.schemas import Direction, Kind

router = APIRouter()


def _parse_cursor(before: str | None) -> tuple[datetime | None, str | None]:
    if not before:
        return None, None
    iso, _, row_id = before.partition("|")
    try:
        return datetime.fromisoformat(iso), (row_id or None)
    except ValueError as e:
        raise ApiError(422, "invalid_cursor", str(e)) from e


@router.get("/packets")
async def list_packets(station: GroundStation = Depends(get_station),
                       apid: int | None = None, direction: Direction | None = None, kind: Kind | None = None,
                       start: datetime | None = None, end: datetime | None = None,
                       limit: int = Query(100, ge=1, le=500), before: str | None = None):
    cursor_ts, cursor_id = _parse_cursor(before)
    q_end = min(end, cursor_ts) if (end and cursor_ts) else (cursor_ts or end)
    rows = await station.storage.query("raw_packets", start=start, end=q_end, apid=apid, limit=limit + 1)
    if cursor_id is not None:
        rows = [r for r in rows if str(r["id"]) != cursor_id]
    page = rows[:limit]
    by_packet: dict[str, list[dict]] = {}
    if page:
        # one range query for all decoded rows of this page, grouped by packet_id (no N+1)
        decoded = await station.storage.query("decoded_telemetry", start=page[-1]["timestamp"],
                                              end=page[0]["timestamp"], limit=len(page) * 32)
        for d in decoded:
            by_packet.setdefault(str(d.get("packet_id")), []).append(d)
    items = []
    for r in page:
        if direction and r.get("direction") != direction:
            continue
        entry = feed_entry_from_row(r, by_packet.get(str(r["id"]), []))
        if kind and entry["kind"] != kind:
            continue
        items.append(entry)
    next_before = None
    if len(rows) > limit and rows[:limit]:
        last = rows[limit - 1]
        next_before = f"{last['timestamp']}|{last['id']}"
    return {"items": items, "next_before": next_before}
