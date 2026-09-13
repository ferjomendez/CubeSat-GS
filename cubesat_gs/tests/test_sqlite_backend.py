from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from cubesat_gs.storage.sqlite_backend import COLLECTIONS, SQLiteBackend


def _t(minutes=0):
    return datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


@pytest.fixture
async def db(tmp_path):
    b = SQLiteBackend(tmp_path / "sub" / "gs.db")  # parent dir must be created
    await b.connect()
    yield b
    await b.close()


async def test_tables_created_and_ping(db):
    assert await db.ping() is True
    for c in COLLECTIONS:
        assert await db.count(c) == 0


async def test_insert_get_query_order_and_filters(db):
    i1 = await db.insert("raw_packets", {"timestamp": _t(0), "apid": 10, "raw_hex": "AA", "rssi": None})
    i2 = await db.insert("raw_packets", {"timestamp": _t(5), "apid": 101, "raw_hex": "BB"})
    i3 = await db.insert("raw_packets", {"timestamp": _t(10), "apid": 10, "raw_hex": "CC"})
    assert [i1, i2, i3] == ["1", "2", "3"]
    got = await db.get("raw_packets", "2")
    assert got["raw_hex"] == "BB" and got["id"] == "2" and got["timestamp"] == _t(5).isoformat()
    rows = await db.query("raw_packets")
    assert [r["raw_hex"] for r in rows] == ["CC", "BB", "AA"]
    rows = await db.query("raw_packets", apid=10)
    assert [r["raw_hex"] for r in rows] == ["CC", "AA"]
    rows = await db.query("raw_packets", start=_t(1), end=_t(6))
    assert [r["raw_hex"] for r in rows] == ["BB"]
    rows = await db.query("raw_packets", limit=1)
    assert [r["raw_hex"] for r in rows] == ["CC"]
    assert [r["raw_hex"] async for r in db.iterate("raw_packets", batch=2)] == ["AA", "BB", "CC"]


async def test_sessions_use_start_time_and_update(db):
    sid = await db.insert("sessions", {"start_time": _t(0), "end_time": None, "packets_received": 0})
    await db.update("sessions", sid, {"end_time": _t(30), "packets_received": 7})
    s = await db.get("sessions", sid)
    assert s["packets_received"] == 7 and s["end_time"] == _t(30).isoformat()
    assert (await db.query("sessions"))[0]["id"] == sid


async def test_bytes_and_nested_values_serialised(db):
    i = await db.insert("commands", {"timestamp": _t(), "raw_hex_sent": b"\x01", "meta": {"a": [1, 2]}})
    got = await db.get("commands", i)
    assert got["raw_hex_sent"] == "01" and got["meta"] == {"a": [1, 2]}


async def test_sync_bookkeeping(db):
    ids = await db.insert_many("alarms", [{"timestamp": _t(i), "apid": 5, "v": i} for i in range(3)])
    assert ids == ["1", "2", "3"]
    pending = await db.unsynced("alarms", limit=2)
    assert [i for i, _, _ in pending] == [1, 2] and pending[0][1]["v"] == 0
    assert all(isinstance(key, str) and key for _, _, key in pending)  # sync_key populated
    assert pending[0][2] != pending[1][2]  # distinct per row
    await db.mark_synced("alarms", [1, 2], ["aaa", "bbb"])
    assert [i for i, _, _ in await db.unsynced("alarms", limit=10)] == [3]
    assert await db.mongo_id_for("alarms", 2) == "bbb"
    assert await db.mongo_id_for("alarms", 3) is None
    assert await db.count_unsynced("alarms") == 1
    assert await db.count_unsynced("commands") == 0


async def test_purge_only_synced_old_rows(db):
    old = datetime.now(timezone.utc) - timedelta(days=400)
    a = await db.insert("raw_packets", {"timestamp": old, "apid": 1})
    b = await db.insert("raw_packets", {"timestamp": old, "apid": 1})
    c = await db.insert("raw_packets", {"timestamp": datetime.now(timezone.utc), "apid": 1})
    await db.mark_synced("raw_packets", [int(a), int(c)], ["x", "y"])
    assert await db.purge_synced_older_than(365) == 1
    assert {r["id"] for r in await db.query("raw_packets")} == {b, c}


async def test_purge_older_than_ignores_synced_flag(db):
    """F2: with Mongo disabled, retention must delete old rows regardless of sync state."""
    old = datetime.now(timezone.utc) - timedelta(days=400)
    a = await db.insert("raw_packets", {"timestamp": old, "apid": 1})  # old, never synced
    b = await db.insert("raw_packets", {"timestamp": datetime.now(timezone.utc), "apid": 1})  # recent
    assert await db.purge_older_than(365) == 1
    assert {r["id"] for r in await db.query("raw_packets")} == {b}


async def test_unknown_collection_rejected(db):
    with pytest.raises(ValueError):
        await db.insert("nope", {"timestamp": _t()})


async def test_insert_many_single_commit(db):
    """Verify insert_many uses single commit for all rows and returns consecutive IDs."""
    commit_count = 0
    original_commit = db._conn.commit

    async def counting_commit():
        nonlocal commit_count
        commit_count += 1
        await original_commit()

    # Patch commit to count calls
    db._conn.commit = counting_commit

    # Insert 3 documents
    ids = await db.insert_many("raw_packets", [
        {"timestamp": _t(i), "apid": 5, "v": i} for i in range(3)
    ])

    # Restore original commit
    db._conn.commit = original_commit

    # Verify consecutive IDs and single commit
    assert ids == ["1", "2", "3"]
    assert commit_count == 1
    assert await db.count("raw_packets") == 3


async def test_datetimes_normalised_to_utc(db):
    """Verify datetimes are normalized to UTC before storage and filtering."""
    # Insert with non-UTC timezone (17:00 UTC-5 = 22:00 UTC)
    non_utc_tz = timezone(timedelta(hours=-5))
    i1 = await db.insert("raw_packets", {
        "timestamp": datetime(2026, 9, 13, 17, 0, tzinfo=non_utc_tz),
        "apid": 1
    })

    # Insert with naive datetime (treated as UTC)
    i2 = await db.insert("raw_packets", {
        "timestamp": datetime(2026, 9, 13, 12, 0),
        "apid": 2
    })

    # Retrieve and verify ISO strings end with +00:00 and have correct UTC times
    doc1 = await db.get("raw_packets", i1)
    doc2 = await db.get("raw_packets", i2)

    assert doc1["timestamp"] == "2026-09-13T22:00:00+00:00"
    assert doc2["timestamp"] == "2026-09-13T12:00:00+00:00"

    # Verify filtering with UTC start time returns only doc1 (which is at 22:00 UTC)
    rows = await db.query("raw_packets", start=datetime(2026, 9, 13, 15, 0, tzinfo=timezone.utc))
    assert len(rows) == 1
    assert rows[0]["id"] == i1
