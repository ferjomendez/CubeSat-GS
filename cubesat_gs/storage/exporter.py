"""Stream a collection to CSV or JSON with optional date/APID filters."""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

from cubesat_gs.storage.sqlite_backend import COLLECTIONS, to_jsonable

log = logging.getLogger(__name__)

COLUMNS: dict[str, list[str]] = {
    "raw_packets": ["id", "timestamp", "direction", "frequency_mhz", "raw_hex", "rssi", "snr",
                    "crc_valid", "apid", "sequence_count"],
    "decoded_telemetry": ["id", "packet_id", "timestamp", "apid", "apid_name", "field_name",
                          "field_value", "unit", "alarm_status"],
    "commands": ["id", "timestamp", "command_name", "raw_hex_sent", "response_received",
                 "response_hex", "latency_ms", "status", "attempts"],
    "sessions": ["id", "start_time", "end_time", "pass_id", "packets_received", "packets_sent", "notes"],
    "alarms": ["id", "timestamp", "packet_id", "apid", "field_name", "value", "threshold", "alarm_type"],
}


async def export(storage, collection: str, path: str | Path, *, fmt: str = "csv",
                 start: datetime | None = None, end: datetime | None = None,
                 apid: int | None = None) -> int:
    if collection not in COLLECTIONS:
        raise ValueError(f"unknown collection {collection!r}")
    if fmt not in ("csv", "json"):
        raise ValueError(f"fmt must be 'csv' or 'json', got {fmt!r}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = COLUMNS[collection]
    n = 0
    with open(path, "w", encoding="utf-8", newline="") as fh:
        if fmt == "csv":
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            async for doc in storage.iterate(collection, start=start, end=end, apid=apid):
                row = to_jsonable(doc)
                w.writerow({c: ("" if row.get(c) is None else row.get(c)) for c in cols})
                n += 1
        else:
            fh.write("[")
            async for doc in storage.iterate(collection, start=start, end=end, apid=apid):
                if n:
                    fh.write(",\n")
                fh.write(json.dumps(to_jsonable(doc), ensure_ascii=False))
                n += 1
            fh.write("]")
    log.info("export: %d rows from %s -> %s", n, collection, path)
    return n


def _parse_dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


async def _main(argv: list[str] | None = None) -> int:
    from cubesat_gs.core.config import load_config
    from cubesat_gs.core.events import EventBus
    from cubesat_gs.storage.database import Storage

    ap = argparse.ArgumentParser(description="Export a ground-station collection to CSV/JSON")
    ap.add_argument("collection", choices=COLLECTIONS)
    ap.add_argument("output", help="output file; .csv or .json decides the format")
    ap.add_argument("--start"); ap.add_argument("--end"); ap.add_argument("--apid", type=int)
    ap.add_argument("--config")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    st = Storage(EventBus(), cfg.database, cfg.base_dir.parent, sync_interval=10_000)
    await st.start(create_session=False)
    try:
        n = await export(st, a.collection, a.output, fmt="json" if a.output.endswith(".json") else "csv",
                         start=_parse_dt(a.start), end=_parse_dt(a.end), apid=a.apid)
    finally:
        await st.stop()
    print(f"{n} rows written to {a.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
