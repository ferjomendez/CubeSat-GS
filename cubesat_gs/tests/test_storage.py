import asyncio
from pathlib import Path

import pytest

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import DatabaseConfig
from cubesat_gs.core.events import (AlarmRaised, CommandCompleted, EventBus, PacketDecoded,
                                    PacketReceived, PacketSent)
from cubesat_gs.core.telecommand import CommandRecord
from cubesat_gs.core.telemetry import DecodedField, DecodedPacket
from cubesat_gs.core.events import now
from cubesat_gs.storage.database import Storage
from cubesat_gs.storage.sqlite_backend import SQLiteBackend
from cubesat_gs.tests.fakes import FakeMotorClient

BEACON = bytes.fromhex("000AC0000018564C454F5F424541434F4E5F5359535F4E4F4D494E414C")


def _cfg(tmp_path, uri=None):
    return DatabaseConfig(db_name="cubesat_gs", retention_days=30,
                          local_fallback_path=str(tmp_path / "data" / "gs.db"), mongo_uri=uri)


async def _settle():
    await asyncio.sleep(0.05)


def _decoded(source):
    pkt = ccsds.parse(source.raw)
    dec = DecodedPacket(apid=10, apid_name="Beacon",
                        fields=[DecodedField("message", "VLEO_BEACON_SYS_NOMINAL", None, None, pkt.payload)])
    return PacketDecoded(source=source, packet=pkt, decoded=dec)


# ---- SQLite only

async def test_sqlite_only_flow(tmp_path):
    bus = EventBus()
    st = Storage(bus, _cfg(tmp_path), tmp_path, sync_interval=1000)
    await st.start()
    src = PacketReceived(raw=BEACON, rssi=-90.0, snr=7.0, freq_mhz=437.25)
    bus.publish(src)
    bus.publish(_decoded(src))
    bus.publish(AlarmRaised(source=src, apid=10, field_name="x", value=1.0, threshold=2.0, alarm_type="low"))
    bus.publish(PacketSent(raw=b"\x10\x64\xc0\x00\x00\x05PING", freq_mhz=435.5))
    bus.publish(CommandCompleted(record=CommandRecord(now(), "PING", "1064", "responded", "0065", 12.5, 1)))
    await _settle()

    h = await st.health()
    assert h["mongo"] == "disabled" and h["pending_sync"] == 0
    raw = await st.query("raw_packets")
    assert len(raw) == 2
    rx = [r for r in raw if r["direction"] == "rx"][0]
    assert rx["apid"] == 10 and rx["sequence_count"] == 0 and rx["rssi"] == -90.0 and rx["crc_valid"] is True
    assert rx["frequency_mhz"] == 437.25 and rx["raw_hex"] == BEACON.hex().upper()
    dec = await st.query("decoded_telemetry")
    assert dec[0]["field_name"] == "message" and dec[0]["packet_id"] == rx["id"] and dec[0]["apid_name"] == "Beacon"
    al = await st.query("alarms")
    assert al[0]["packet_id"] == rx["id"] and al[0]["alarm_type"] == "low"
    cmd = await st.query("commands")
    assert cmd[0]["command_name"] == "PING" and cmd[0]["response_received"] is True and cmd[0]["latency_ms"] == 12.5
    assert st.session["packets_received"] == 1 and st.session["packets_sent"] == 1
    stats = await st.stats()
    assert stats["raw_packets"] == 2 and stats["sessions"] == 1
    await st.stop()
    reopened = SQLiteBackend(tmp_path / "data" / "gs.db")  # storage is closed; read the file directly
    await reopened.connect()
    sess = await reopened.query("sessions")
    assert sess[0]["end_time"] is not None and sess[0]["packets_received"] == 1
    await reopened.close()


async def test_malformed_raw_still_stored(tmp_path):
    bus = EventBus()
    st = Storage(bus, _cfg(tmp_path), tmp_path, sync_interval=1000)
    await st.start()
    bus.publish(PacketReceived(raw=b"\x00\x0a", rssi=None, snr=None, freq_mhz=435.5))
    await _settle()
    r = (await st.query("raw_packets"))[0]
    assert r["apid"] is None and r["sequence_count"] is None and r["raw_hex"] == "000A"
    await st.stop()


# ---- Mongo with fallback and sync

async def test_mongo_primary_then_fallback_then_sync(tmp_path):
    bus = EventBus()
    client = FakeMotorClient()
    st = Storage(bus, _cfg(tmp_path, uri="mongodb://fake"), tmp_path,
                 mongo_client_factory=lambda uri: client, sync_interval=1000)
    await st.start()
    assert (await st.health())["mongo"] == "ok"

    src1 = PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25)
    bus.publish(src1); bus.publish(_decoded(src1))
    await _settle()
    assert len(client["cubesat_gs"]["raw_packets"].docs) == 1
    assert len(client["cubesat_gs"]["decoded_telemetry"].docs) == 1

    client.fail = True  # Atlas goes away
    src2 = PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25)
    bus.publish(src2); bus.publish(_decoded(src2))
    await _settle()
    h = await st.health()
    assert h["mongo"] == "degraded" and h["pending_sync"] == 2
    assert len(client["cubesat_gs"]["raw_packets"].docs) == 1
    local_raw = await st._sqlite.query("raw_packets")
    local_dec = await st._sqlite.query("decoded_telemetry")
    assert local_dec[0]["packet_id"] == local_raw[0]["id"]  # sqlite-local reference

    client.fail = False  # Atlas is back
    uploaded = await st.sync_now()
    assert uploaded == 2
    h = await st.health()
    assert h["mongo"] == "ok" and h["pending_sync"] == 0
    mongo_raw = client["cubesat_gs"]["raw_packets"].docs
    mongo_dec = client["cubesat_gs"]["decoded_telemetry"].docs
    assert len(mongo_raw) == 2 and len(mongo_dec) == 2
    synced_dec = [d for d in mongo_dec if d["packet_id"] == str(mongo_raw[1]["_id"])]
    assert len(synced_dec) == 1  # packet_id remapped to the new ObjectId

    src3 = PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25)
    bus.publish(src3)
    await _settle()
    assert len(mongo_raw) == 3  # back to writing Mongo directly
    await st.stop()
    assert client["cubesat_gs"]["sessions"].docs[0]["end_time"] is not None


async def test_mongo_unreachable_at_start_is_degraded_not_fatal(tmp_path):
    bus = EventBus()
    client = FakeMotorClient(fail=True)
    st = Storage(bus, _cfg(tmp_path, uri="mongodb://fake"), tmp_path,
                 mongo_client_factory=lambda uri: client, sync_interval=0.05)
    await st.start()
    assert (await st.health())["mongo"] == "degraded"
    bus.publish(PacketReceived(raw=BEACON, rssi=None, snr=None, freq_mhz=437.25))
    await _settle()
    assert (await st.health())["pending_sync"] >= 1
    client.fail = False
    await asyncio.sleep(0.2)  # background sync task picks it up
    h = await st.health()
    assert h["mongo"] == "ok" and h["pending_sync"] == 0
    await st.stop()
