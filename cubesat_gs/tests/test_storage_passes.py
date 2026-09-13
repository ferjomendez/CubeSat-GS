import asyncio
from datetime import datetime, timedelta, timezone

from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import (CommandCompleted, EventBus, PacketReceived, PassEnded,
                                    PassStarted, now)
from cubesat_gs.core.telecommand import CommandRecord
from cubesat_gs.storage.database import Storage
from cubesat_gs.storage.exporter import COLUMNS
from cubesat_gs.storage.sqlite_backend import COLLECTIONS
from cubesat_gs.tests.fakes import FakeMotorClient

BEACON = bytes.fromhex("000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C")


class FakePass:
    id = "abc12345"
    aos = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    los = aos + timedelta(minutes=6)
    max_el = 42.5


async def test_passes_collection_registered():
    assert "passes" in COLLECTIONS
    assert COLUMNS["passes"] == ["id", "pass_id", "aos", "los", "max_el", "packets_received",
                                 "packets_sent", "commands_sent"]


async def test_pass_rows_and_session_pass_id(tmp_path):
    bus = EventBus()
    st = Storage(bus, DatabaseConfig(local_fallback_path=str(tmp_path / "gs.db")), tmp_path,
                 sync_interval=1000)
    await st.start()
    assert st.session["pass_id"] is None
    bus.publish(PassStarted(pass_=FakePass()))
    await asyncio.sleep(0.05)
    assert st.session["pass_id"] == "abc12345"
    bus.publish(PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25))
    bus.publish(PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25))
    bus.publish(CommandCompleted(record=CommandRecord(now(), "PING", "10", "responded", None, 1.0, 1)))
    await asyncio.sleep(0.05)
    assert st.pass_counters == {"packets_received": 2, "packets_sent": 0, "commands_sent": 1}
    bus.publish(PassEnded(pass_=FakePass(), packets_received=2))
    await asyncio.sleep(0.05)
    assert st.session["pass_id"] is None
    rows = await st.query("passes")
    assert len(rows) == 1
    r = rows[0]
    assert r["pass_id"] == "abc12345" and r["max_el"] == 42.5
    assert r["packets_received"] == 2 and r["commands_sent"] == 1 and r["packets_sent"] == 0
    assert r["aos"].startswith("2026-09-13T12:00:00") and r["los"].startswith("2026-09-13T12:06:00")
    assert (await st.stats())["passes"] == 1
    await st.stop()


async def test_pass_sync_datetime_restoration(tmp_path):
    """Verify aos/los are restored to datetime on sync (not left as ISO strings)."""
    bus = EventBus()
    client = FakeMotorClient(fail=True)  # Mongo initially unavailable
    cfg = DatabaseConfig(mongo_uri="mongodb://fake", local_fallback_path=str(tmp_path / "gs.db"))
    st = Storage(bus, cfg, tmp_path, mongo_client_factory=lambda uri: client, sync_interval=1000)
    await st.start()
    assert (await st.health())["mongo"] == "degraded"

    # Publish pass while Mongo is down (buffered to SQLite)
    bus.publish(PassStarted(pass_=FakePass()))
    await asyncio.sleep(0.05)
    bus.publish(PassEnded(pass_=FakePass(), packets_received=0))
    await asyncio.sleep(0.05)

    # Verify pass row was written to SQLite with datetimes as ISO strings
    sqlite_rows = await st._sqlite.query("passes")
    assert len(sqlite_rows) == 1
    assert isinstance(sqlite_rows[0]["aos"], str)
    assert isinstance(sqlite_rows[0]["los"], str)

    # Bring Mongo back up and sync
    client.fail = False
    uploaded = await st.sync_now()
    assert uploaded == 2  # session row + passes row

    # Verify the synced Mongo doc has aos/los as datetime instances
    mongo_passes = client["cubesat_gs"]["passes"].docs
    assert len(mongo_passes) == 1
    mongo_pass = mongo_passes[0]
    assert isinstance(mongo_pass["aos"], datetime), f"aos should be datetime, got {type(mongo_pass['aos'])}"
    assert isinstance(mongo_pass["los"], datetime), f"los should be datetime, got {type(mongo_pass['los'])}"
    assert mongo_pass["aos"].year == 2026 and mongo_pass["aos"].month == 9
    assert mongo_pass["los"].year == 2026 and mongo_pass["los"].month == 9

    await st.stop()
