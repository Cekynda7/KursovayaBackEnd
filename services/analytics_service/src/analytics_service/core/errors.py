from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..schemas import ErrorResponse
from .logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрация глобальных обработчиков исключений для единого формата ошибок."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        logger.warning(
            "http_error",
            path=str(request.url.path),
            status_code=exc.status_code,
            detail=exc.detail,
        )
        payload = ErrorResponse(
            error_code="HTTP_ERROR",
            message=str(exc.detail),
            details={"status_code": exc.status_code},
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info(
            "validation_error",
            path=str(request.url.path),
            errors=exc.errors(),
        )
        payload = ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Invalid request data",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=str(request.url.path),
            error=str(exc),
        )
        payload = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="Service temporarily unavailable",
            details=None,
        )
        return JSONResponse(status_code=503, content=payload.model_dump())


