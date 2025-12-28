from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Event(Base):
    """Сохранённое доменное событие из шины RabbitMQ."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    routing_key: Mapped[str] = mapped_column(String(128), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)


