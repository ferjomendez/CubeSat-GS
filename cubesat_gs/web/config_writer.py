"""Read/validate/write gs_config.yaml (comment-preserving) and apply changes live where safe."""
from __future__ import annotations

import dataclasses
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from cubesat_gs.core import config as cfgmod
from cubesat_gs.core.config import GSConfig
from cubesat_gs.core.pass_predictor import TLEError

log = logging.getLogger(__name__)

WRITABLE: dict[str, set[str]] = {
    "serial": {"port", "baudrate", "reconnect_interval"},
    "frequencies": {"tctm", "beacon"},
    "station": {"name", "latitude", "longitude", "altitude"},
    "satellite": {"name", "tle_line1", "tle_line2", "tle_source"},
    "passes": {"min_elevation", "prediction_days"},
    "commands": {"default_timeout", "max_retries", "retry_backoff"},
}
APPLIES: dict[str, str] = {
    "serial.port": "live", "serial.baudrate": "restart", "serial.reconnect_interval": "restart",
    "frequencies.tctm": "live", "frequencies.beacon": "live",
    "station.name": "live", "station.latitude": "live", "station.longitude": "live", "station.altitude": "live",
    "satellite.name": "live", "satellite.tle_line1": "live", "satellite.tle_line2": "live", "satellite.tle_source": "live",
    "passes.min_elevation": "live", "passes.prediction_days": "live",
    "commands.default_timeout": "restart", "commands.max_retries": "restart", "commands.retry_backoff": "restart",
}
_HIDDEN = {("database", "mongo_uri")}


def public_config(cfg: GSConfig) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in dataclasses.fields(cfg):
        if f.name in ("base_dir", "config_path"):
            continue
        section = dataclasses.asdict(getattr(cfg, f.name))
        for (sec, key) in _HIDDEN:
            if sec == f.name:
                section.pop(key, None)
        out[f.name] = section
    return out


def _yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.width = 120
    return y


def check_sections(sections: dict[str, dict[str, Any]]) -> None:
    for sec, values in sections.items():
        if sec not in WRITABLE:
            raise ValueError(f"section {sec!r} is read-only (edit gs_config.yaml and restart)")
        if not isinstance(values, dict):
            raise ValueError(f"section {sec!r} must be a mapping")
        for key in values:
            if key not in WRITABLE[sec]:
                raise ValueError(f"{sec}.{key} is not a writable setting")


def validate_merge(path: Path, sections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return the merged plain dict after building a GSConfig from it (raises ValueError if invalid)."""
    check_sections(sections)
    y = _yaml()
    with open(path, "r", encoding="utf-8") as fh:
        doc = y.load(fh) or {}
    merged = _to_plain(doc)
    for sec, values in sections.items():
        merged.setdefault(sec, {}).update(values)
    cfg: GSConfig = cfgmod._build(GSConfig, merged, "config")
    cfgmod._validate(cfg)
    for sec in ("station", "passes", "frequencies", "serial"):
        for key, val in sections.get(sec, {}).items():
            if key in ("latitude", "longitude", "altitude", "min_elevation", "tctm", "beacon", "reconnect_interval"):
                float(val)  # raises ValueError/TypeError for non-numeric input
            if key == "prediction_days" and int(val) < 1:
                raise ValueError("passes.prediction_days must be >= 1")
    return merged


def _to_plain(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _to_plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_to_plain(v) for v in node]
    return node


def write_config(path: Path, sections: dict[str, dict[str, Any]]) -> None:
    y = _yaml()
    with open(path, "r", encoding="utf-8") as fh:
        doc = y.load(fh) or {}
    for sec, values in sections.items():
        if sec not in doc:
            doc[sec] = {}
        for key, val in values.items():
            doc[sec][key] = val
    fd, tmp = tempfile.mkstemp(prefix=".gs_config.", suffix=".yaml", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            y.dump(doc, fh)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    log.info("config: wrote %s (%s)", path, ", ".join(f"{s}.{k}" for s, v in sections.items() for k in v))


async def apply_live(station, sections: dict[str, dict[str, Any]]) -> list[str]:
    """Apply writable settings to the running station. Returns the list of `section.key` applied live."""
    applied: list[str] = []
    cfg = station.cfg
    for sec, values in sections.items():
        for key, val in values.items():
            if APPLIES.get(f"{sec}.{key}") != "live":
                setattr(getattr(cfg, sec), key, val)
                continue
            setattr(getattr(cfg, sec), key, val)
            applied.append(f"{sec}.{key}")
    if "frequencies" in sections:
        station.freq.set_presets(cfg.frequencies.tctm, cfg.frequencies.beacon)
    if "station" in sections:
        await station.passes.set_location(cfg.station.latitude, cfg.station.longitude, cfg.station.altitude)
    if "passes" in sections:
        await station.passes.set_min_elevation(cfg.passes.min_elevation)
        station.passes._days = int(cfg.passes.prediction_days)
    if "satellite" in sections:
        station.passes.set_tle_source(cfg.satellite.tle_source)
        if "tle_line1" in sections["satellite"] or "tle_line2" in sections["satellite"]:
            await station.passes.set_tle(cfg.satellite.tle_line1, cfg.satellite.tle_line2)  # raises TLEError
    if "serial" in sections and "port" in sections["serial"]:
        await station.serial.stop()
        await station.serial.start()
    return applied
