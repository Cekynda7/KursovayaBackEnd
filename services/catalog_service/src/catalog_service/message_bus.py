from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import pika
from sqlalchemy import select

from .config import get_settings
from .core.logging import get_logger
from .db import AsyncSessionLocal
from .models import Stock


logger = get_logger(__name__)


class RabbitMQClient:
    """Простой клиент RabbitMQ для публикации событий."""

    def __init__(self) -> None:
        settings = get_settings()
        params = pika.URLParameters(settings.rabbitmq_url)
        self.exchange = settings.rabbitmq_exchange
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)

    def publish_event(self, routing_key: str, payload: Dict[str, Any]) -> None:
        """Опубликовать событие в exchange bookstore.events."""

        envelope = {
            "idempotency_key": payload.get("idempotency_key") or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        body = json.dumps(envelope).encode("utf-8")
        self._channel.basic_publish(
            exchange=self.exchange,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
        logger.info("event_published", routing_key=routing_key)

    def close(self) -> None:
        try:
            self._connection.close()
        except Exception:
            logger.warning("rabbitmq_close_failed")


_client: RabbitMQClient | None = None
_client_lock = threading.Lock()


def get_rabbitmq_client() -> RabbitMQClient:
    """Получить singleton-клиент для RabbitMQ."""

    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = RabbitMQClient()
    return _client


class StockReserveConsumer(threading.Thread):
    """Consumer для обработки stock.reserve.request и генерации succeeded/failed."""

    daemon = True

    def __init__(self) -> None:
        super().__init__()
        settings = get_settings()
        self._connection_params = pika.URLParameters(settings.rabbitmq_url)
        self.exchange = settings.rabbitmq_exchange

    def run(self) -> None:
        connection = pika.BlockingConnection(self._connection_params)
        channel = connection.channel()
        channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)

        result = channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue

        channel.queue_bind(exchange=self.exchange, queue=queue_name, routing_key="stock.reserve.request")

        def callback(ch, method, properties, body) -> None:  # type: ignore[no-untyped-def]
            import asyncio

            try:
                envelope = json.loads(body.decode("utf-8"))
                idempotency_key = envelope.get("idempotency_key")
                payload: Dict[str, Any] = envelope.get("payload", {})
            except Exception:
                logger.warning("invalid_stock_reserve_payload")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            async def handle_reserve() -> None:
                async with AsyncSessionLocal() as session:
                    items = payload.get("items", [])
                    # Проверяем наличие stock по всем книгам
                    ok = True
                    stocks: Dict[int, Stock] = {}
                    for item in items:
                        book_id = item.get("book_id")
                        qty = int(item.get("quantity", 0))
                        if not book_id or qty <= 0:
                            ok = False
                            break
                        res = await session.execute(select(Stock).where(Stock.book_id == book_id))
                        stock: Stock | None = res.scalar_one_or_none()
                        if not stock or stock.quantity < qty:
                            ok = False
                            break
                        stocks[book_id] = stock

                    client = get_rabbitmq_client()
                    if not ok:
                        client.publish_event(
                            "stock.reserve.failed",
                            {
                                "idempotency_key": idempotency_key,
                                "reason": "not_enough_stock",
                                "original": payload,
                            },
                        )
                        return

                    # Резервируем: уменьшаем количество
                    for item in items:
                        book_id = item["book_id"]
                        qty = int(item["quantity"])
                        stocks[book_id].quantity -= qty

                    await session.commit()

                    client.publish_event(
                        "stock.reserve.succeeded",
                        {
                            "idempotency_key": idempotency_key,
                            "original": payload,
                        },
                    )

            asyncio.run(handle_reserve())
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        logger.info("stock_reserve_consumer_started")
        channel.start_consuming()


_consumer_started = False
_consumer_lock = threading.Lock()


def ensure_stock_consumer_started() -> None:
    """Гарантировать запуск consumer-а резервирования склада."""

    global _consumer_started
    if not _consumer_started:
        with _consumer_lock:
            if not _consumer_started:
                consumer = StockReserveConsumer()
                consumer.start()
                _consumer_started = True


