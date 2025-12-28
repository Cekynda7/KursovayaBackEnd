from __future__ import annotations

import asyncio

from fastapi import FastAPI

from .api import router as analytics_router
from .core.errors import register_exception_handlers
from .core.logging import get_logger, setup_logging
from .core.middleware import CorrelationIdMiddleware
from .message_bus import ensure_consumer_started


setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Analytics Service",
    description="Сервис аналитики заказов для онлайн-магазина книг.",
    version="1.0.0",
)

app.add_middleware(CorrelationIdMiddleware)

register_exception_handlers(app)

app.include_router(analytics_router)


@app.get("/health", summary="Healthcheck сервиса", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Простой healthcheck-эндпоинт без авторизации."""

    return {"status": "ok"}


@app.on_event("startup")
async def on_startup() -> None:
    """Логирование старта приложения и запуск consumer-а RabbitMQ."""

    logger.info("analytics_service_started")
    loop = asyncio.get_running_loop()
    ensure_consumer_started(loop)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Логирование остановки приложения."""

    logger.info("analytics_service_stopped")


