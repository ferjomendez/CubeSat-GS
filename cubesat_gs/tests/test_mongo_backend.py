from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import PyMongoError

from cubesat_gs.storage.mongo_backend import MongoBackend
from cubesat_gs.tests.fakes import FakeMotorClient


def _t(m=0):
    return datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=m)


@pytest.fixture
async def mb():
    client = FakeMotorClient()
    b = MongoBackend("mongodb://fake", "cubesat_gs", retention_days=30, client_factory=lambda uri: client)
    await b.connect()
    yield client, b
    await b.close()


async def test_connect_creates_indexes(mb):
    client, b = mb
    db = client["cubesat_gs"]
    names = {c: [k for k, _ in db[c].indexes] for c in ("raw_packets", "decoded_telemetry", "commands", "sessions", "alarms")}
    for c in names:
        assert [("timestamp" if c != "sessions" else "start_time", -1)] in names[c]
    assert [("apid", 1)] in names["raw_packets"] and [("apid", 1), ("timestamp", 1)] in names["decoded_telemetry"]
    ttl = [kw for k, kw in db["raw_packets"].indexes if kw.get("expireAfterSeconds")]
    assert ttl and ttl[0]["expireAfterSeconds"] == 30 * 86400
    assert await b.ping() is True


async def test_insert_get_query_iterate_count(mb):
    client, b = mb
    i1 = await b.insert("raw_packets", {"timestamp": _t(0), "apid": 10, "raw_hex": b"\xaa"})
    i2 = await b.insert("raw_packets", {"timestamp": _t(5), "apid": 101, "raw_hex": "BB"})
    assert len(i1) == 24
    got = await b.get("raw_packets", i1)
    assert got["raw_hex"] == "AA" and got["id"] == i1 and "_id" not in got
    rows = await b.query("raw_packets")
    assert [r["raw_hex"] for r in rows] == ["BB", "AA"]
    assert [r["id"] for r in await b.query("raw_packets", apid=101)] == [i2]
    assert [r["id"] for r in await b.query("raw_packets", start=_t(1))] == [i2]
    assert [r["raw_hex"] async for r in b.iterate("raw_packets")] == ["AA", "BB"]
    assert await b.count("raw_packets") == 2
    ids = await b.insert_many("alarms", [{"timestamp": _t(), "apid": 1}, {"timestamp": _t(), "apid": 2}])
    assert len(ids) == 2 and await b.count("alarms") == 2


async def test_update_and_session_time_field(mb):
    client, b = mb
    sid = await b.insert("sessions", {"start_time": _t(0), "end_time": None})
    await b.update("sessions", sid, {"end_time": _t(9)})
    assert (await b.get("sessions", sid))["end_time"] == _t(9)
    assert (await b.query("sessions"))[0]["id"] == sid


async def test_errors_propagate(mb):
    client, b = mb
    client.fail = True
    assert await b.ping() is False
    with pytest.raises(PyMongoError):
        await b.insert("raw_packets", {"timestamp": _t()})
