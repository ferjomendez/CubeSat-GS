import csv
import json
from datetime import datetime, timedelta, timezone

import pytest

from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import EventBus
from cubesat_gs.storage.database import Storage
from cubesat_gs.storage.exporter import COLUMNS, export


def _t(m=0):
    return datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=m)


@pytest.fixture
async def st(tmp_path):
    cfg = DatabaseConfig(local_fallback_path=str(tmp_path / "gs.db"))
    s = Storage(EventBus(), cfg, tmp_path, sync_interval=1000)
    await s.start()
    for i in range(3):
        await s.write("raw_packets", {"timestamp": _t(i), "direction": "rx", "frequency_mhz": 437.25,
                                      "raw_hex": f"0{i}", "rssi": None, "snr": None, "crc_valid": True,
                                      "apid": 10 if i < 2 else 101, "sequence_count": i})
    yield s
    await s.stop()


async def test_export_csv(st, tmp_path):
    out = tmp_path / "raw.csv"
    n = await export(st, "raw_packets", out, fmt="csv")
    assert n == 3
    with out.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert list(rows[0].keys()) == COLUMNS["raw_packets"]
    assert [r["raw_hex"] for r in rows] == ["00", "01", "02"]
    assert rows[0]["rssi"] == ""


async def test_export_json_with_filters(st, tmp_path):
    out = tmp_path / "raw.json"
    n = await export(st, "raw_packets", out, fmt="json", apid=10, start=_t(1))
    assert n == 1
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list) and data[0]["raw_hex"] == "01"
    n = await export(st, "raw_packets", out, fmt="json", apid=999)
    assert n == 0 and json.loads(out.read_text(encoding="utf-8")) == []


async def test_bad_args(st, tmp_path):
    with pytest.raises(ValueError):
        await export(st, "raw_packets", tmp_path / "x.txt", fmt="xml")
    with pytest.raises(ValueError):
        await export(st, "nope", tmp_path / "x.csv")
