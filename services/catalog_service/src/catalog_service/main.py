from __future__ import annotations

from fastapi import FastAPI

from .api.routes_books import router as books_router
from .core.errors import register_exception_handlers
from .core.logging import get_logger, setup_logging
from .core.middleware import CorrelationIdMiddleware
from .message_bus import ensure_stock_consumer_started


setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Catalog Service",
    description="Сервис каталога книг для онлайн-магазина.",
    version="1.0.0",
)

app.add_middleware(CorrelationIdMiddleware)

register_exception_handlers(app)

app.include_router(books_router)


@app.get("/health", summary="Healthcheck сервиса", tags=["health"])
async def healthcheck() -> dict[str, str]:
    """Простой healthcheck-эндпоинт без авторизации."""

    return {"status": "ok"}


@app.on_event("startup")
async def on_startup() -> None:
    """Логирование старта приложения и запуск consumer-а stock.reserve.request."""

    logger.info("catalog_service_started")
    ensure_stock_consumer_started()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Логирование остановки приложения."""

    logger.info("catalog_service_stopped")


