"""FastAPI application factory. Never constructs Phase 1 modules; wires the web layer onto a GroundStation."""
from __future__ import annotations

import contextlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from cubesat_gs.core.station import GroundStation
from cubesat_gs.web.deps import install_error_handlers
from cubesat_gs.web.hub import WebSocketHub
from cubesat_gs.web.routes import commands as commands_routes, config as config_routes, export as export_routes, feed as feed_routes, frequency as frequency_routes, passes as passes_routes, status as status_routes, telemetry as telemetry_routes

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
    app.include_router(passes_routes.router, prefix="/api")
    app.include_router(config_routes.router, prefix="/api")
    app.include_router(export_routes.router, prefix="/api")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        hub: WebSocketHub | None = app.state.hub
        if hub is None:
            await websocket.close(code=1013)
            return
        await hub.handle(websocket)

    @app.get("/api/schema.json", include_in_schema=False)
    async def schema_json():
        from cubesat_gs.web import schemas
        import inspect
        from pydantic import BaseModel
        return {name: cls.model_json_schema() for name, cls in inspect.getmembers(schemas, inspect.isclass)
                if issubclass(cls, BaseModel) and cls is not BaseModel}

    static_dir = app.state.static_dir
    if (static_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str, request: Request):
        if path == "api" or path.startswith("api/") or path == "ws":
            return JSONResponse({"error": "not_found", "detail": None}, status_code=404)
        index = app.state.static_dir / "index.html"
        candidate = app.state.static_dir / path if path else None
        if candidate and candidate.is_file() and candidate.resolve().is_relative_to(app.state.static_dir.resolve()):
            return FileResponse(candidate)
        if not index.is_file():
            return JSONResponse({"error": "dashboard_not_built",
                                 "detail": "run `npm run build` in cubesat_gs/web/frontend"}, status_code=503)
        return FileResponse(index)

    return app


def serve(app: FastAPI, host: str, port: int) -> uvicorn.Server:
    """A uvicorn server that runs in the caller's loop and never installs its own signal handlers."""
    config = uvicorn.Config(app, host=host, port=port, loop="none", log_config=None, access_log=False)
    server = uvicorn.Server(config)
    # uvicorn 0.52.4's Server has no `install_signal_handlers` attribute (that was an older
    # API); Server.serve() unconditionally does `with self.capture_signals(): ...`, which
    # installs its own signal.signal handlers for SIGINT/SIGTERM/SIGBREAK for the life of
    # the call, replacing main.py's. Shadow it with a no-op context manager so main.py keeps
    # owning process signals and stops uvicorn only via `server.should_exit = True`.
    server.capture_signals = contextlib.nullcontext
    return server
