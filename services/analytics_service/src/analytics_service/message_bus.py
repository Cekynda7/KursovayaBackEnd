from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime
from typing import Any, Dict

import pika
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .core.logging import get_logger
from .db import AsyncSessionLocal
from .models import Event


logger = get_logger(__name__)


class AnalyticsConsumer(threading.Thread):
    """Фоновый consumer RabbitMQ, пишущий события в БД analytics_service."""

    daemon = True

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        settings = get_settings()
        self._connection_params = pika.URLParameters(settings.rabbitmq_url)
        self.exchange = settings.rabbitmq_exchange
        self._loop = loop

    def run(self) -> None:
        connection = pika.BlockingConnection(self._connection_params)
        channel = connection.channel()
        channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)

        result = channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue

        # Подписываемся на ключи событий
        for routing_key in ["order.created", "stock.reserve.succeeded", "stock.reserve.failed"]:
            channel.queue_bind(exchange=self.exchange, queue=queue_name, routing_key=routing_key)

        def callback(ch, method, properties, body) -> None:  # type: ignore[no-untyped-def]
            try:
                envelope = json.loads(body.decode("utf-8"))
                idempotency_key = envelope.get("idempotency_key")
                occurred_at = envelope.get("timestamp")
                payload: Dict[str, Any] = envelope.get("payload", {})
            except Exception:
                logger.warning("invalid_event_payload")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if isinstance(occurred_at, str):
                try:
                    occurred_at = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning("invalid_event_timestamp", routing_key=method.routing_key)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    logger.warning("invalid_event_payload_json", routing_key=method.routing_key)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

            async def persist_event() -> None:
                async with AsyncSessionLocal() as session:  # type: AsyncSession
                    event = Event(
                        routing_key=method.routing_key,
                        idempotency_key=idempotency_key,
                        occurred_at=occurred_at,
                        payload=payload,
                    )
                    session.add(event)
                    await session.commit()

            future = asyncio.run_coroutine_threadsafe(persist_event(), self._loop)
            try:
                future.result(timeout=10)
            except Exception:
                logger.exception("event_persist_failed", routing_key=method.routing_key)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                return

            logger.info("event_stored", routing_key=method.routing_key)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        logger.info("analytics_consumer_started")
        channel.start_consuming()


_consumer_started = False
_lock = threading.Lock()


def ensure_consumer_started(loop: asyncio.AbstractEventLoop) -> None:
    """Гарантировать запуск consumer-а, если он ещё не запущен."""

    global _consumer_started
    if not _consumer_started:
        with _lock:
            if not _consumer_started:
                consumer = AnalyticsConsumer(loop)
                consumer.start()
                _consumer_started = True


