"""FastAPI application factory. Never constructs Phase 1 modules; wires the web layer onto a GroundStation."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import install_error_handlers
from cubesat_gs.web.hub import WebSocketHub
from cubesat_gs.web.routes import commands as commands_routes, feed as feed_routes, frequency as frequency_routes, status as status_routes, telemetry as telemetry_routes

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(station: GroundStation, *, static_dir: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        hub = WebSocketHub(station)
        app.state.hub = hub
        await hub.start()
        try:
            yield
        finally:
            await hub.stop()
            app.state.hub = None

    app = FastAPI(title="CubeSat GS", version="2.0", lifespan=lifespan, docs_url="/api/docs",
                  openapi_url="/api/openapi.json", redoc_url=None)
    app.state.station = station
    app.state.hub = None
    app.state.static_dir = static_dir or STATIC_DIR
    install_error_handlers(app)
    app.include_router(status_routes.router, prefix="/api")
    app.include_router(feed_routes.router, prefix="/api")
    app.include_router(telemetry_routes.router, prefix="/api")
    app.include_router(commands_routes.router, prefix="/api")
    app.include_router(frequency_routes.router, prefix="/api")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        hub: WebSocketHub | None = app.state.hub
        if hub is None:
            await websocket.close(code=1013)
            return
        await hub.handle(websocket)

    return app
