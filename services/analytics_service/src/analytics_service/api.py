from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import Event
from .schemas import EventList, EventRead


router = APIRouter(tags=["analytics"])


@router.get(
    "/events",
    response_model=EventList,
    summary="Получить последние события из аналитики",
)
async def list_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> EventList:
    """Вернуть последние N событий, обработанных analytics-service."""

    result = await db.execute(select(Event).order_by(Event.id.desc()).limit(limit))
    events = result.scalars().all()
    items = [EventRead.model_validate(e) for e in events]
    return EventList(items=items)


