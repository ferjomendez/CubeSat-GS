"""GroundStation: owns the config, the event bus and every module; single start()/stop()."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Any, Callable

from cubesat_gs.core import ccsds
from cubesat_gs.core.config import GSConfig, LoggingConfig
from cubesat_gs.core.events import EventBus
from cubesat_gs.core.frequency_manager import FrequencyManager
from cubesat_gs.core.serial_handler import SerialHandler
from cubesat_gs.core.telecommand import TelecommandManager
from cubesat_gs.core.telemetry import TelemetryDecoder
from cubesat_gs.storage.database import Storage

log = logging.getLogger(__name__)


def setup_logging(cfg: LoggingConfig, base_dir: Path, level_override: str | None = None) -> None:
    level = getattr(logging, (level_override or cfg.level).upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    if cfg.file:
        path = Path(cfg.file)
        path = path if path.is_absolute() else base_dir / path
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(path, maxBytes=5 * 1024 * 1024, backupCount=3,
                                                  encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)


class GroundStation:
    def __init__(self, cfg: GSConfig, *, open_connection: Callable | None = None,
                 mongo_client_factory: Callable[[str], Any] | None = None) -> None:
        self.cfg = cfg
        pkg_dir = cfg.base_dir.parent
        self.bus = EventBus()
        self.serial = SerialHandler(self.bus, cfg.serial, get_freq=lambda: self.freq.mhz,
                                    open_connection=open_connection)
        self.freq = FrequencyManager(self.bus, self.serial, cfg.frequencies)
        self.builder = ccsds.PacketBuilder(cfg.ccsds.length_includes_crc)
        self.decoder = TelemetryDecoder(self.bus, cfg.resolve(cfg.telemetry.definitions), cfg.ccsds)
        self.telecommand = TelecommandManager(self.bus, self.serial, self.freq, self.builder,
                                              cfg.commands, cfg.resolve(cfg.commands.registry))
        self.storage = Storage(self.bus, cfg.database, pkg_dir, mongo_client_factory=mongo_client_factory)

    async def start(self) -> None:
        log.info("ground station %r starting", self.cfg.station.name)
        await self.storage.start()
        self.decoder.start()
        self.freq.start()
        await self.serial.start()  # last: its ConnectionChanged(True) triggers the initial FREQ

    async def stop(self) -> None:
        log.info("ground station stopping")
        await self.serial.stop()
        self.freq.stop()
        self.decoder.stop()
        await self.storage.stop()

    def status(self) -> dict[str, Any]:
        return {
            "station": self.cfg.station.name,
            "serial": {"connected": self.serial.connected, "port": self.serial.port},
            "frequency": {"mode": self.freq.mode.value, "mhz": self.freq.mhz},
            "pending_command": self.telecommand.pending.as_dict() if self.telecommand.pending else None,
            "storage": {"mongo": self.storage.state},
            "session": dict(self.storage.session),
        }
