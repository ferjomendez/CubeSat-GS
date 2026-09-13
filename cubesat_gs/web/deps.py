"""Request dependencies and the Phase 1 exception → HTTP status mapping."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from cubesat_gs.core.pass_predictor import TLEError
from cubesat_gs.core.serial_handler import SerialCommandTimeout, SerialDisconnected
from cubesat_gs.core.station import GroundStation
from cubesat_gs.core.telecommand import CommandBusyError, UnknownCommandError, WrongModeError

log = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, error: str, detail: str | None = None) -> None:
        super().__init__(detail or error)
        self.status, self.error, self.detail = status, error, detail


def get_station(request: Request) -> GroundStation:
    return request.app.state.station


def _json(status: int, error: str, detail: str | None = None) -> JSONResponse:
    return JSONResponse({"error": error, "detail": detail}, status_code=status)


_MAPPED: list[tuple[type[Exception], int, str]] = [
    (CommandBusyError, 409, "command_busy"),
    (WrongModeError, 400, "wrong_mode"),
    (UnknownCommandError, 404, "unknown_command"),
    (SerialCommandTimeout, 504, "modem_timeout"),
    (SerialDisconnected, 503, "serial_disconnected"),
    (TLEError, 422, "invalid_tle"),
    (ValueError, 422, "invalid_value"),
]


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _json(exc.status, exc.error, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _json(422, "validation_error", str(exc.errors()[0].get("msg")) if exc.errors() else None)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        return _json(exc.status_code, "not_found" if exc.status_code == 404 else "http_error", str(exc.detail))

    for exc_type, status, error in _MAPPED:
        def _make(status=status, error=error):
            async def handler(_: Request, exc: Exception):
                return _json(status, error, str(exc))
            return handler
        app.add_exception_handler(exc_type, _make())

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("web: unhandled error")
        return _json(500, "internal", None)
