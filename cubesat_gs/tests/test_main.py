"""Smoke test: main.run() in --sim mode starts, then stops cleanly on SIGINT."""
import argparse
import asyncio
import signal
from pathlib import Path

import pytest
import yaml

import cubesat_gs.main as main_mod
from cubesat_gs.main import run

PKG = Path(__file__).resolve().parents[1]


async def _wait_for_line(path: Path, needle: str, timeout: float = 8.0) -> None:
    async def _w():
        while not (path.exists() and needle in path.read_text(encoding="utf-8", errors="ignore")):
            await asyncio.sleep(0.05)
    await asyncio.wait_for(_w(), timeout)


async def test_sim_mode_starts_and_stops_on_sigint(tmp_path, monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    log_file = tmp_path / "gs.log"
    cfg = {
        "serial": {"port": "auto", "reconnect_interval": 0.2},
        "commands": {"registry": str(PKG / "config" / "commands.yaml")},
        "telemetry": {"definitions": str(PKG / "config" / "telemetry_defs.yaml")},
        "database": {"local_fallback_path": str(tmp_path / "gs.db")},
        "logging": {"level": "INFO", "file": str(log_file)},
    }
    cfg_path = tmp_path / "gs_config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    args = argparse.Namespace(config=str(cfg_path), sim=True, sim_beacon_interval=1.0,
                              sim_rssi=False, log_level="INFO", no_web=True, host=None, port=None)
    task = asyncio.create_task(run(args))
    try:
        await _wait_for_line(log_file, "ground station running")
        await _wait_for_line(log_file, "re-applied 435.500 MHz")   # modem handshake happened
        signal.raise_signal(signal.SIGINT)
        rc = await asyncio.wait_for(task, 10.0)
    finally:
        if not task.done():
            task.cancel()
    assert rc == 0
    text = log_file.read_text(encoding="utf-8", errors="ignore")
    assert "ground station stopping" in text


async def test_run_cleans_up_when_station_start_fails(tmp_path, monkeypatch):
    """F8: station.stop() and the --sim cleanup must run even if station.start() raises."""
    monkeypatch.delenv("MONGO_URI", raising=False)
    calls = []

    class FakeStation:
        def __init__(self, cfg, **kwargs):
            pass

        async def start(self):
            raise RuntimeError("boom")

        async def stop(self):
            calls.append("station_stop")

    class FakeSim:
        def __init__(self, **kwargs):
            pass

        async def stop(self):
            calls.append("sim_stop")

    class FakeServer:
        def close(self):
            calls.append("server_close")

        async def wait_closed(self):
            calls.append("server_wait_closed")

    async def fake_serve_tcp(sim, host, port):
        return FakeServer(), 0

    monkeypatch.setattr(main_mod, "GroundStation", FakeStation)
    monkeypatch.setattr("cubesat_gs.tests.serial_simulator.ModemSimulator", FakeSim)
    monkeypatch.setattr("cubesat_gs.tests.serial_simulator.serve_tcp", fake_serve_tcp)

    cfg = {
        "serial": {"port": "auto", "reconnect_interval": 0.2},
        "commands": {"registry": str(PKG / "config" / "commands.yaml")},
        "telemetry": {"definitions": str(PKG / "config" / "telemetry_defs.yaml")},
        "database": {"local_fallback_path": str(tmp_path / "gs.db")},
        "logging": {"level": "INFO", "file": str(tmp_path / "gs.log")},
    }
    cfg_path = tmp_path / "gs_config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    args = argparse.Namespace(config=str(cfg_path), sim=True, sim_beacon_interval=1.0,
                              sim_rssi=False, log_level="INFO", no_web=True, host=None, port=None)

    with pytest.raises(RuntimeError, match="boom"):
        await asyncio.wait_for(run(args), 5.0)

    assert calls == ["station_stop", "sim_stop", "server_close", "server_wait_closed"]


async def test_run_cleans_up_when_station_construction_fails(tmp_path, monkeypatch):
    """R4: GroundStation(cfg) must be constructed inside the try/finally, so a config
    problem (e.g. a bad telemetry_defs.yaml) surfacing from __init__ still tears down the
    --sim TCP server and simulator instead of leaking them."""
    monkeypatch.delenv("MONGO_URI", raising=False)
    calls = []

    class FakeStation:
        def __init__(self, cfg, **kwargs):
            raise RuntimeError("boom-construct")

        async def start(self):
            pass

        async def stop(self):
            calls.append("station_stop")

    class FakeSim:
        def __init__(self, **kwargs):
            pass

        async def stop(self):
            calls.append("sim_stop")

    class FakeServer:
        def close(self):
            calls.append("server_close")

        async def wait_closed(self):
            calls.append("server_wait_closed")

    async def fake_serve_tcp(sim, host, port):
        return FakeServer(), 0

    monkeypatch.setattr(main_mod, "GroundStation", FakeStation)
    monkeypatch.setattr("cubesat_gs.tests.serial_simulator.ModemSimulator", FakeSim)
    monkeypatch.setattr("cubesat_gs.tests.serial_simulator.serve_tcp", fake_serve_tcp)

    cfg = {
        "serial": {"port": "auto", "reconnect_interval": 0.2},
        "commands": {"registry": str(PKG / "config" / "commands.yaml")},
        "telemetry": {"definitions": str(PKG / "config" / "telemetry_defs.yaml")},
        "database": {"local_fallback_path": str(tmp_path / "gs.db")},
        "logging": {"level": "INFO", "file": str(tmp_path / "gs.log")},
    }
    cfg_path = tmp_path / "gs_config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    args = argparse.Namespace(config=str(cfg_path), sim=True, sim_beacon_interval=1.0,
                              sim_rssi=False, log_level="INFO", no_web=True, host=None, port=None)

    with pytest.raises(RuntimeError, match="boom-construct"):
        await asyncio.wait_for(run(args), 5.0)

    # station was never constructed, so no station_stop -- but the sim/server must still
    # be torn down.
    assert calls == ["sim_stop", "server_close", "server_wait_closed"]


async def test_sim_mode_serves_web(tmp_path, monkeypatch):
    import httpx
    import socket
    monkeypatch.delenv("MONGO_URI", raising=False)
    log_file = tmp_path / "gs.log"
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    cfg = {
        "serial": {"port": "auto", "reconnect_interval": 0.2},
        "commands": {"registry": str(PKG / "config" / "commands.yaml")},
        "telemetry": {"definitions": str(PKG / "config" / "telemetry_defs.yaml")},
        "database": {"local_fallback_path": str(tmp_path / "gs.db")},
        "logging": {"level": "INFO", "file": str(log_file)},
        "web": {"host": "127.0.0.1", "port": port},
    }
    cfg_path = tmp_path / "gs_config.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    args = argparse.Namespace(config=str(cfg_path), sim=True, sim_beacon_interval=1.0, sim_rssi=False,
                              log_level="INFO", no_web=False, host=None, port=None)
    task = asyncio.create_task(run(args))
    try:
        await _wait_for_line(log_file, "web: listening on")
        async with httpx.AsyncClient() as c:
            r = await c.get(f"http://127.0.0.1:{port}/api/status", timeout=5.0)
            assert r.status_code == 200 and r.json()["serial"]["connected"] in (True, False)
        signal.raise_signal(signal.SIGINT)
        rc = await asyncio.wait_for(task, 10.0)
    finally:
        if not task.done():
            task.cancel()
    assert rc == 0
    text = log_file.read_text(encoding="utf-8", errors="ignore")
    assert "web: stopped" in text and "ground station stopping" in text
