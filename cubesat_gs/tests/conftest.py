"""Shared fixtures for web tests: a running GroundStation on the in-process simulator."""
import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from cubesat_gs.core.config import load_config
from cubesat_gs.core.station import GroundStation
from cubesat_gs.tests.serial_simulator import ModemSimulator, SimulatedSerial
from cubesat_gs.web.app import create_app


async def wait_until(pred, timeout=2.0):
    async def _w():
        while not pred():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(_w(), timeout)


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
