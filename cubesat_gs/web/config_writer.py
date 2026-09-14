"""Read/validate/write gs_config.yaml (comment-preserving) and apply changes live where safe."""
from __future__ import annotations

import dataclasses
import logging
import os
import tempfile
import typing
from pathlib import Path
from typing import Any, get_args, get_origin

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


def _validate_tle_format(tle_line: str, line_num: int) -> None:
    """Validate that a TLE line has the correct format (starts with line number)."""
    stripped = (tle_line or "").strip()
    if not stripped:
        return  # Empty lines are validated elsewhere
    if not stripped.startswith(f"{line_num} "):
        raise TLEError(f"TLE line {line_num} must start with '{line_num} '")


def _validate_types(sections: dict[str, dict[str, Any]]) -> None:
    """Validate that values match the expected types of their config fields."""
    nested_types = {
        "serial": cfgmod.SerialConfig,
        "frequencies": cfgmod.FrequencyConfig,
        "station": cfgmod.StationConfig,
        "satellite": cfgmod.SatelliteConfig,
        "passes": cfgmod.PassConfig,
        "commands": cfgmod.CommandConfig,
    }
    for sec, values in sections.items():
        if sec not in nested_types:
            continue
        cls = nested_types[sec]
        hints = typing.get_type_hints(cls)
        for key, val in values.items():
            if key not in hints:
                continue
            hint = hints[key]
            # Extract the actual type from Optional/Union types
            origin = get_origin(hint)
            args = get_args(hint)
            # Handle Optional[X] which is Union[X, None]
            if origin is typing.Union and type(None) in args:
                # Optional type: accept None and the non-None type
                inner_types = tuple(t for t in args if t is not type(None))
                if val is None:
                    continue
                hint = inner_types[0] if len(inner_types) == 1 else typing.Union[inner_types]
                origin = get_origin(hint)
                args = get_args(hint)
            # Type checking logic
            if hint is int or origin is int:
                if not isinstance(val, int) or isinstance(val, bool):
                    raise ValueError(f"{sec}.{key} must be int, got {type(val).__name__}")
            elif hint is float or origin is float:
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    raise ValueError(f"{sec}.{key} must be float or int, got {type(val).__name__}")
            elif hint is str or origin is str:
                if not isinstance(val, str):
                    raise ValueError(f"{sec}.{key} must be str, got {type(val).__name__}")
            elif hint is bool or origin is bool:
                if not isinstance(val, bool):
                    raise ValueError(f"{sec}.{key} must be bool, got {type(val).__name__}")


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
    _validate_types(sections)
    # Validate TLE line format
    if "satellite" in sections:
        if "tle_line1" in sections["satellite"]:
            _validate_tle_format(sections["satellite"]["tle_line1"], 1)
        if "tle_line2" in sections["satellite"]:
            _validate_tle_format(sections["satellite"]["tle_line2"], 2)
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
            # Skip TLE lines until they are validated
            if sec == "satellite" and key in ("tle_line1", "tle_line2"):
                continue
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
            # Build TLE pair from request with fallback to current config
            l1 = sections["satellite"].get("tle_line1", cfg.satellite.tle_line1)
            l2 = sections["satellite"].get("tle_line2", cfg.satellite.tle_line2)
            # Validate TLE first, then set in config only if validation succeeds
            await station.passes.set_tle(l1, l2)
            cfg.satellite.tle_line1 = l1
            cfg.satellite.tle_line2 = l2
            if "tle_line1" in sections["satellite"]:
                applied.append("satellite.tle_line1")
            if "tle_line2" in sections["satellite"]:
                applied.append("satellite.tle_line2")
    if "serial" in sections and "port" in sections["serial"]:
        await station.serial.stop()
        await station.serial.start()
    return applied
