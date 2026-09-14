"""Shared fixtures for web tests: a running GroundStation on the in-process simulator."""
import asyncio

import bson
import pytest
from bson import ObjectId
from bson.codec_options import CodecOptions
from httpx import ASGITransport, AsyncClient

from cubesat_gs.core.config import load_config
from cubesat_gs.core.station import GroundStation
from cubesat_gs.tests.fakes import FakeCollection, FakeDatabase, FakeMotorClient, _Result
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial
from cubesat_gs.web.app import create_app


async def wait_until(pred, timeout=2.0):
    async def _w():
        while not pred():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_w(), timeout)


class _BsonCollection(FakeCollection):
    """Round-trips inserted documents through real BSON encode/decode so datetime handling
    (aware vs. naive, microsecond-to-millisecond truncation) matches an actual MongoDB server."""

    async def insert_one(self, doc: dict):
        self._guard()
        d = dict(doc)
        d.setdefault("_id", ObjectId())
        self._check_dup(d)
        stored = bson.decode(bson.encode(d), codec_options=CodecOptions(tz_aware=self._client.tz_aware))
        self.docs.append(stored)
        return _Result(inserted_id=stored["_id"])


class _BsonDatabase(FakeDatabase):
    def __getitem__(self, name: str) -> _BsonCollection:
        return self._colls.setdefault(name, _BsonCollection(self._client))


class BsonMotorClient(FakeMotorClient):
    """A FakeMotorClient whose reads reflect a real BSON round-trip, so tests can verify
    behavior that depends on `tz_aware` (naive vs. aware datetimes) like a real deployment."""

    def __init__(self, *args, tz_aware: bool = True, fail: bool = False, **kwargs):
        super().__init__(*args, fail=fail, **kwargs)
        self.tz_aware = tz_aware

    def __getitem__(self, name: str) -> _BsonDatabase:
        return self._dbs.setdefault(name, _BsonDatabase(self))


@pytest.fixture
async def mongo_web_stack(tmp_path, monkeypatch):
    """Like `web_stack`, but storage reads and writes go through a Mongo backend whose fake
    client round-trips documents through real BSON (see `BsonMotorClient`)."""
    monkeypatch.delenv("MONGO_URI", raising=False)
    cfg = load_config(dotenv=False)
    cfg.serial.port = "sim://"
    cfg.serial.reconnect_interval = 0.05
    cfg.serial.timeouts.tx = 0.5
    cfg.serial.timeouts.freq = 0.5
    cfg.commands.default_timeout = 1.0
    cfg.commands.max_retries = 0
    cfg.database.local_fallback_path = str(tmp_path / "gs.db")
    cfg.database.mongo_uri = "mongodb://fake"
    cfg.logging.file = str(tmp_path / "gs.log")
    mongo_client = BsonMotorClient()
    sim = ModemSimulator(beacon_interval=0.1)
    await sim.start()
    ser = SimulatedSerial(sim)
    station = GroundStation(cfg, open_connection=ser.open, mongo_client_factory=lambda uri: mongo_client)
    app = create_app(station, static_dir=tmp_path / "static-none")
    await station.start()
    await wait_until(lambda: station.serial.connected)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield station, sim, client, mongo_client
    await station.stop()
    await sim.stop()


@pytest.fixture
async def web_stack(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    cfg = load_config(dotenv=False)
    cfg.serial.port = "sim://"
    cfg.serial.reconnect_interval = 0.05
    cfg.serial.timeouts.tx = 0.5
    cfg.serial.timeouts.freq = 0.5
    cfg.commands.default_timeout = 1.0
    cfg.commands.max_retries = 0
    cfg.database.local_fallback_path = str(tmp_path / "gs.db")
    cfg.database.mongo_uri = None
    cfg.logging.file = str(tmp_path / "gs.log")
    sim = ModemSimulator(beacon_interval=0.1)
    await sim.start()
    ser = SimulatedSerial(sim)
    station = GroundStation(cfg, open_connection=ser.open)
    app = create_app(station, static_dir=tmp_path / "static-none")
    await station.start()
    await wait_until(lambda: station.serial.connected)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield station, sim, client
    await station.stop()
    await sim.stop()
