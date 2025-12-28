from __future__ import annotations

from fastapi import FastAPI

from .api.routes_auth import router as auth_router
from .core.errors import register_exception_handlers
from .core.logging import setup_logging, get_logger
from .core.middleware import CorrelationIdMiddleware


setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Auth Service",
    description="Сервис авторизации и аутентификации для онлайн-магазина книг.",
    version="1.0.0",
)

app.add_middleware(CorrelationIdMiddleware)

register_exception_handlers(app)

app.include_router(auth_router)


@app.get("/health", summary="Healthcheck сервиса", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Простой healthcheck-эндпоинт без авторизации."""

    return {"status": "ok"}


@app.on_event("startup")
async def on_startup() -> None:
    """Логирование старта приложения."""

    logger.info("auth_service_started")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Логирование остановки приложения."""

    logger.info("auth_service_stopped")


