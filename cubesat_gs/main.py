"""Entry point: python cubesat_gs/main.py [--config PATH] [--sim] [--log-level LEVEL]"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# allow `python cubesat_gs/main.py` from the git root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cubesat_gs.core.config import load_config  # noqa: E402
from cubesat_gs.core.station import GroundStation, setup_logging  # noqa: E402

log = logging.getLogger("main")


async def _wait_started(server, timeout: float = 10.0) -> None:
    async def _w():
        while not server.started:
            await asyncio.sleep(0.05)
    await asyncio.wait_for(_w(), timeout)


def _restore_signal_handlers(handlers: dict[int, tuple[str, object]], loop: asyncio.AbstractEventLoop) -> None:
    """Restore signal handlers to their original state."""
    for sig, (method, old_handler) in handlers.items():
        if method == "add_signal_handler":
            loop.remove_signal_handler(sig)
        else:  # method == "signal.signal"
            signal.signal(sig, old_handler)


async def run(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    setup_logging(cfg.logging, cfg.base_dir.parent, args.log_level)

    sim = None
    sim_server = None
    if args.sim:
        from cubesat_gs.tests.serial_simulator import ModemSimulator, serve_tcp
        sim = ModemSimulator(beacon_interval=args.sim_beacon_interval, fake_rssi=args.sim_rssi)
        sim_server, port = await serve_tcp(sim, "127.0.0.1", 0)
        cfg.serial.port = f"socket://127.0.0.1:{port}"
        log.info("simulator: modem simulator listening on %s", cfg.serial.port)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    handlers: dict[int, tuple[str, object]] = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
            handlers[sig] = ("add_signal_handler", None)
        except NotImplementedError:  # Windows: no loop signal handlers
            old_handler = signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))
            handlers[sig] = ("signal.signal", old_handler)

    station = None
    server = None
    server_task = None
    try:
        station = GroundStation(cfg)
        await station.start()
        if not args.no_web:
            from cubesat_gs.web.app import create_app, serve
            app = create_app(station)
            host, port = args.host or cfg.web.host, args.port or cfg.web.port
            server = serve(app, host, port)
            server_task = asyncio.create_task(server.serve(), name="uvicorn")
            await _wait_started(server)
            log.info("web: listening on http://%s:%d", host, port)
        log.info("ground station running; Ctrl+C to stop")
        await stop.wait()
    finally:
        if server is not None and server_task is not None:
            server.should_exit = True
            try:
                await asyncio.wait_for(server_task, 10.0)
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                server_task.cancel()
            log.info("web: stopped")
        log.info("ground station stopping")
        if station is not None:
            await station.stop()
        if sim is not None:
            await sim.stop()
        if sim_server is not None:
            sim_server.close()
            await sim_server.wait_closed()
        _restore_signal_handlers(handlers, loop)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CubeSat ground station (headless core)")
    ap.add_argument("--config", help="path to gs_config.yaml (default: cubesat_gs/config/gs_config.yaml)")
    ap.add_argument("--sim", action="store_true", help="run against an in-process ESP32 simulator")
    ap.add_argument("--sim-beacon-interval", type=float, default=10.0)
    ap.add_argument("--sim-rssi", action="store_true", help="simulator appends fake RSSI/SNR")
    ap.add_argument("--log-level", help="override logging.level from config")
    ap.add_argument("--no-web", action="store_true", help="skip running the web server")
    ap.add_argument("--host", type=str, help="override web.host from config")
    ap.add_argument("--port", type=int, help="override web.port from config")
    args = ap.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
