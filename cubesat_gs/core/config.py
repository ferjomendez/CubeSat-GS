"""Configuration loader: gs_config.yaml + .env -> typed dataclasses."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "gs_config.yaml"


@dataclass
class SerialTimeouts:
    tx: float = 5.0
    freq: float = 2.0


@dataclass
class SerialConfig:
    port: str = "auto"
    baudrate: int = 115200
    reconnect_interval: float = 5.0
    timeouts: SerialTimeouts = field(default_factory=SerialTimeouts)


@dataclass
class FrequencyConfig:
    tctm: float = 435.500
    beacon: float = 437.250


@dataclass
class CCSDSConfig:
    length_includes_crc: bool = True
    sequence_scope: str = "global"  # global | per_apid


@dataclass
class StationConfig:
    name: str = "Ground Station"
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0


@dataclass
class SatelliteConfig:
    name: str = ""
    tle_line1: str = ""
    tle_line2: str = ""
    tle_source: str = ""


@dataclass
class PassConfig:
    min_elevation: float = 10.0
    prediction_days: int = 7


@dataclass
class CommandConfig:
    registry: str = "config/commands.yaml"
    default_timeout: float = 10.0
    max_retries: int = 3
    retry_backoff: float = 1.5
    history_size: int = 500


@dataclass
class TelemetryConfig:
    definitions: str = "config/telemetry_defs.yaml"


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class DatabaseConfig:
    db_name: str = "cubesat_gs"
    retention_days: int = 365
    local_fallback_path: str = "data/gs_offline.db"
    mongo_uri: str | None = None  # env only


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/gs.log"


@dataclass
class GSConfig:
    serial: SerialConfig = field(default_factory=SerialConfig)
    frequencies: FrequencyConfig = field(default_factory=FrequencyConfig)
    ccsds: CCSDSConfig = field(default_factory=CCSDSConfig)
    station: StationConfig = field(default_factory=StationConfig)
    satellite: SatelliteConfig = field(default_factory=SatelliteConfig)
    passes: PassConfig = field(default_factory=PassConfig)
    commands: CommandConfig = field(default_factory=CommandConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    web: WebConfig = field(default_factory=WebConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    base_dir: Path = field(default_factory=lambda: DEFAULT_CONFIG_PATH.parent)

    def resolve(self, path_str: str) -> Path:
        """Resolve a config-relative path against the package dir (parent of config/)."""
        p = Path(path_str)
        return p if p.is_absolute() else (self.base_dir.parent / p).resolve()


# Nested sections by key name (field annotations are strings under `from __future__ import annotations`).
_NESTED: dict[str, type] = {
    "serial": SerialConfig, "timeouts": SerialTimeouts, "frequencies": FrequencyConfig,
    "ccsds": CCSDSConfig, "station": StationConfig, "satellite": SatelliteConfig,
    "passes": PassConfig, "commands": CommandConfig, "telemetry": TelemetryConfig,
    "web": WebConfig, "database": DatabaseConfig, "logging": LoggingConfig,
}


def _build(cls: type, data: Any, where: str) -> Any:
    """Recursively build a dataclass from a dict, applying defaults, warning on unknown keys."""
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{where}: expected a mapping, got {type(data).__name__}")
    known = {f.name for f in fields(cls)}
    for key in data:
        if key not in known:
            log.warning("config: unknown key %s.%s ignored", where, key)
    kwargs = {}
    for name in known:
        if name not in data:
            continue
        value = data[name]
        if name in _NESTED:
            kwargs[name] = _build(_NESTED[name], value, f"{where}.{name}")
        else:
            kwargs[name] = value
    return cls(**kwargs)


def _validate(cfg: GSConfig) -> None:
    if cfg.ccsds.sequence_scope not in ("global", "per_apid"):
        raise ValueError(
            f"ccsds.sequence_scope must be 'global' or 'per_apid', got {cfg.ccsds.sequence_scope!r}"
        )
    if cfg.commands.max_retries < 0:
        raise ValueError("commands.max_retries must be >= 0")
    if cfg.serial.reconnect_interval <= 0:
        raise ValueError("serial.reconnect_interval must be > 0")


def load_config(path: str | Path | None = None, *, dotenv: bool = True) -> GSConfig:
    """Load the YAML config; with dotenv=True also load a .env file found upward from this package."""
    if dotenv:
        load_dotenv()
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    cfg: GSConfig = _build(GSConfig, data, "config")
    cfg.base_dir = path.resolve().parent
    cfg.database.mongo_uri = os.environ.get("MONGO_URI") or None
    cfg.serial.reconnect_interval = float(cfg.serial.reconnect_interval)
    _validate(cfg)
    return cfg
