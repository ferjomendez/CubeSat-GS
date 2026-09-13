from pathlib import Path

import pytest

from cubesat_gs.core.config import load_config, GSConfig

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def test_load_default_config():
    cfg = load_config(CONFIG_DIR / "gs_config.yaml")
    assert isinstance(cfg, GSConfig)
    assert cfg.serial.port == "auto"
    assert cfg.serial.baudrate == 115200
    assert cfg.serial.timeouts.tx == 5.0
    assert cfg.frequencies.tctm == 435.5
    assert cfg.frequencies.beacon == 437.25
    assert cfg.ccsds.length_includes_crc is True
    assert cfg.ccsds.sequence_scope == "global"
    assert cfg.commands.max_retries == 3
    assert cfg.database.db_name == "cubesat_gs"


def test_resolve_relative_paths():
    cfg = load_config(CONFIG_DIR / "gs_config.yaml")
    assert cfg.resolve(cfg.commands.registry) == CONFIG_DIR / "commands.yaml"
    assert cfg.resolve(cfg.telemetry.definitions) == CONFIG_DIR / "telemetry_defs.yaml"


def test_missing_keys_get_defaults(tmp_path):
    p = tmp_path / "gs.yaml"
    p.write_text("serial:\n  port: COM7\n")
    cfg = load_config(p)
    assert cfg.serial.port == "COM7"
    assert cfg.serial.baudrate == 115200
    assert cfg.frequencies.tctm == 435.5
    assert cfg.ccsds.sequence_scope == "global"


def test_invalid_sequence_scope_rejected(tmp_path):
    p = tmp_path / "gs.yaml"
    p.write_text("ccsds:\n  sequence_scope: bogus\n")
    with pytest.raises(ValueError, match="sequence_scope"):
        load_config(p)


def test_mongo_uri_from_env(tmp_path, monkeypatch):
    p = tmp_path / "gs.yaml"
    p.write_text("database: {}\n")
    monkeypatch.setenv("MONGO_URI", "mongodb://x")
    assert load_config(p, dotenv=False).database.mongo_uri == "mongodb://x"
    monkeypatch.delenv("MONGO_URI")
    assert load_config(p, dotenv=False).database.mongo_uri is None  # dotenv=False: ignore a real .env
