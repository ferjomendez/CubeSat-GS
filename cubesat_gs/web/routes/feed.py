from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import ApiError, get_station
from cubesat_gs.web.hub import feed_entry_from_row
from cubesat_gs.web.schemas import Direction, Kind, PacketsPageOut

router = APIRouter()


def _parse_cursor(before: str | None) -> tuple[datetime | None, str | None]:
    if not before:
        return None, None
    iso, _, row_id = before.partition("|")
    try:
        return datetime.fromisoformat(iso), (row_id or None)
    except ValueError as e:
        raise ApiError(422, "invalid_cursor", str(e)) from e


@router.get("/packets", response_model=PacketsPageOut)
async def list_packets(station: GroundStation = Depends(get_station),
                       apid: int | None = None, direction: Direction | None = None, kind: Kind | None = None,
                       start: datetime | None = None, end: datetime | None = None,
                       limit: int = Query(100, ge=1, le=500), before: str | None = None):
    cursor_ts, cursor_id = _parse_cursor(before)
    q_end = min(end, cursor_ts) if (end and cursor_ts) else (cursor_ts or end)
    # Fetch more rows when cursor filtering is needed, since some will be dropped
    fetch_limit = limit + 1 if cursor_id is None else limit * 2 + 1
    rows = await station.storage.query("raw_packets", start=start, end=q_end, apid=apid, limit=fetch_limit)

    # Drop rows on identical timestamp >= cursor_id to avoid duplicates across pages
    if cursor_id is not None and rows:
        # Normalize timestamps for comparison (may be datetime or string)
        def ts_equal(row_ts, cursor_ts):
            if hasattr(row_ts, 'isoformat'):
                row_ts = row_ts.isoformat()
            if hasattr(cursor_ts, 'isoformat'):
                cursor_ts = cursor_ts.isoformat()
            return str(row_ts) == str(cursor_ts)
        rows = [r for r in rows if not (ts_equal(r["timestamp"], cursor_ts) and str(r["id"]) >= cursor_id)]

    raw_page = rows[:limit]
    # Check if there are more rows beyond this page (before direction/kind filtering)
    has_more = len(rows) > limit

    by_packet: dict[str, list[dict]] = {}
    if raw_page:
        # one range query for all decoded rows of this page, grouped by packet_id (no N+1)
        decoded = await station.storage.query("decoded_telemetry", start=raw_page[-1]["timestamp"],
                                              end=raw_page[0]["timestamp"], limit=len(raw_page) * 32)
        for d in decoded:
            by_packet.setdefault(str(d.get("packet_id")), []).append(d)
        # Sort each packet's decoded fields by id to preserve field definition order
        for packet_id in by_packet:
            by_packet[packet_id].sort(key=lambda d: d.get("id", 0))
    items = []
    for r in raw_page:
        if direction and r.get("direction") != direction:
            continue
        entry = feed_entry_from_row(r, by_packet.get(str(r["id"]), []))
        if kind and entry["kind"] != kind:
            continue
        items.append(entry)

    # Compute next_before from whether raw page was full, using the last row before filtering
    next_before = None
    if has_more and raw_page:
        last = raw_page[-1]
        ts = last['timestamp']
        if hasattr(ts, 'isoformat'):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)
        next_before = f"{ts_str}|{last['id']}"
    return {"items": items, "next_before": next_before}
