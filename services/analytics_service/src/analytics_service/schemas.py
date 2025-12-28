from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Единый формат ошибок для analytics-service."""

    error_code: str
    message: str
    details: Dict[str, Any] | None = None


class EventRead(BaseModel):
    """DTO события, сохранённого в БД аналитики."""

    id: int
    routing_key: str
    idempotency_key: str
    occurred_at: datetime
    payload: Dict[str, Any]

    class Config:
        from_attributes = True


class EventList(BaseModel):
    """Список последних событий."""

    items: List[EventRead]


