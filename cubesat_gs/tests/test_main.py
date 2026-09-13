"""Smoke test: main.run() in --sim mode starts, then stops cleanly on SIGINT."""
import argparse
import asyncio
import signal
from pathlib import Path

import yaml

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
                              sim_rssi=False, log_level="INFO")
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
