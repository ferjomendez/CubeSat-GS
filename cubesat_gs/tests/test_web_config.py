import shutil
from pathlib import Path

import pytest

from cubesat_gs.tests.conftest import wait_until

PKG = Path(__file__).resolve().parents[1]


@pytest.fixture
async def cfg_stack(web_stack, tmp_path):
    station, sim, client = web_stack
    cfg_path = tmp_path / "gs_config.yaml"
    shutil.copy(PKG / "config" / "gs_config.yaml", cfg_path)
    station.cfg.base_dir = cfg_path.parent
    station.cfg.config_path = cfg_path
    return station, sim, client, cfg_path


async def test_get_config_hides_secrets_and_marks_writable(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    r = await client.get("/api/config")
    body = r.json()
    assert "mongo_uri" not in body["config"]["database"]
    assert body["config"]["frequencies"] == {"tctm": 435.5, "beacon": 437.25}
    assert set(body["writable"]) == {"serial", "frequencies", "station", "satellite", "passes", "commands"}
    assert body["applies"]["frequencies.tctm"] == "live" and body["applies"]["serial.baudrate"] == "restart"


async def test_put_config_round_trips_and_applies_live(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    original = cfg_path.read_text(encoding="utf-8")
    assert "# MONGO_URI is read from the environment" in original
    r = await client.put("/api/config", json={"sections": {
        "frequencies": {"beacon": 437.3}, "station": {"latitude": -33.0},
        "passes": {"min_elevation": 15}, "commands": {"max_retries": 5}}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["config"]["frequencies"]["beacon"] == 437.3
    assert set(body["applied_live"]) == {"frequencies.beacon", "station.latitude", "passes.min_elevation"}
    assert body["restart_required"] is True
    text = cfg_path.read_text(encoding="utf-8")
    assert "# MONGO_URI is read from the environment" in text and "beacon: 437.3" in text and "max_retries: 5" in text
    assert station.cfg.frequencies.beacon == 437.3 and station.passes._min_el == 15
    r = await client.put("/api/frequency", json={"mode": "beacon_listen"})
    assert r.json()["mhz"] == 437.3


async def test_put_config_rejects_bad_values_without_writing(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    before = cfg_path.read_text(encoding="utf-8")
    r = await client.put("/api/config", json={"sections": {"database": {"retention_days": 1}}})
    assert r.status_code == 422 and "database" in r.json()["detail"]
    r = await client.put("/api/config", json={"sections": {"serial": {"bogus": 1}}})
    assert r.status_code == 422
    r = await client.put("/api/config", json={"sections": {"passes": {"min_elevation": "high"}}})
    assert r.status_code == 422
    assert cfg_path.read_text(encoding="utf-8") == before


async def test_put_tle_enables_predictor(cfg_stack):
    from cubesat_gs.tests.test_pass_predictor import L1, L2
    station, sim, client, cfg_path = cfg_stack
    r = await client.put("/api/config", json={"sections": {"satellite": {"tle_line1": L1, "tle_line2": L2}}})
    assert r.status_code == 200 and station.passes.enabled
    r = await client.put("/api/config", json={"sections": {"satellite": {"tle_line1": "junk", "tle_line2": "junk"}}})
    assert r.status_code == 422 and r.json()["error"] == "invalid_tle" and station.passes.enabled
    assert L1 in cfg_path.read_text(encoding="utf-8")


async def test_serial_port_change_reconnects(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    r = await client.put("/api/config", json={"sections": {"serial": {"port": "sim://again"}}})
    assert r.status_code == 200 and "serial.port" in r.json()["applied_live"]
    await wait_until(lambda: station.serial.connected and station.serial.port == "sim://again")


async def test_serial_ports_and_db_stats(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    r = await client.get("/api/config/serial-ports")
    assert r.status_code == 200 and isinstance(r.json(), list)
    r = await client.get("/api/db/stats")
    assert set(r.json()["counts"]) >= {"raw_packets", "passes"} and r.json()["health"]["mongo"] == "disabled"


async def test_put_tle_rejects_junk_without_corrupting_config(cfg_stack):
    from cubesat_gs.tests.test_pass_predictor import L1, L2
    station, sim, client, cfg_path = cfg_stack
    # Set valid TLE first
    r = await client.put("/api/config", json={"sections": {"satellite": {"tle_line1": L1, "tle_line2": L2}}})
    assert r.status_code == 200
    assert station.cfg.satellite.tle_line1 == L1 and station.cfg.satellite.tle_line2 == L2
    # Try to set junk TLE - should reject and restore valid TLE in config
    r = await client.put("/api/config", json={"sections": {"satellite": {"tle_line1": "junk", "tle_line2": "junk"}}})
    assert r.status_code == 422 and r.json()["error"] == "invalid_tle"
    # Config must still have valid TLE (not junk)
    assert station.cfg.satellite.tle_line1 == L1 and station.cfg.satellite.tle_line2 == L2
    # GET config must also return the valid TLE
    r = await client.get("/api/config")
    assert r.json()["config"]["satellite"]["tle_line1"] == L1 and r.json()["config"]["satellite"]["tle_line2"] == L2


async def test_put_config_rejects_invalid_types(cfg_stack):
    station, sim, client, cfg_path = cfg_stack
    before = cfg_path.read_text(encoding="utf-8")
    # Invalid type for int field
    r = await client.put("/api/config", json={"sections": {"serial": {"baudrate": "fast"}}})
    assert r.status_code == 422 and "invalid" in r.json()["error"]
    # Invalid type for float field
    r = await client.put("/api/config", json={"sections": {"commands": {"default_timeout": "abc"}}})
    assert r.status_code == 422
    # Invalid type for float field
    r = await client.put("/api/config", json={"sections": {"commands": {"retry_backoff": "slow"}}})
    assert r.status_code == 422
    # File should not be written on validation failure
    assert cfg_path.read_text(encoding="utf-8") == before
    # int value for float field should succeed (backward compat)
    r = await client.put("/api/config", json={"sections": {"passes": {"min_elevation": 15}}})
    assert r.status_code == 200
