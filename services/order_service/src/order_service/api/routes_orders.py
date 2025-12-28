from __future__ import annotations

from typing import Annotated, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.logging import get_logger
from ..db import get_db
from ..dependencies import get_current_user
from ..message_bus import get_rabbitmq_client
from ..models import Cart, CartItem, Order, OrderItem
from ..schemas import OrderList, OrderRead, OrderItemRead

router = APIRouter(prefix="/orders", tags=["orders"])

logger = get_logger(__name__)


async def _get_user_id_from_token(user: dict) -> int:
    user_id = user.get("user_id")
    if user_id:
        return int(user_id)
    sub = user.get("sub")
    if sub and str(sub).isdigit():
        return int(sub)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user in token")


async def _load_order(session: AsyncSession, order: Order) -> OrderRead:
    result = await session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = result.scalars().all()
    items = [OrderItemRead(book_id=i.book_id, quantity=i.quantity, price=float(i.price)) for i in order_items]
    return OrderRead(
        id=order.id,
        status=order.status,
        total_amount=float(order.total_amount),
        created_at=order.created_at,
        items=items,
    )


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый заказ из корзины",
)
async def create_order(
    db: AsyncSession = Depends(get_db),
    user: Annotated[dict, Depends(get_current_user)] = None,  # noqa: ARG001
) -> OrderRead:
    """
    Создать заказ из текущей корзины пользователя, сохранить его в БД
    и опубликовать событие OrderCreated в RabbitMQ.
    """

    settings = get_settings()
    user_id = await _get_user_id_from_token(user)

    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    cart_items = result.scalars().all()
    if not cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    # Получаем цены из catalog-service
    total_amount = 0.0
    order_items: List[OrderItem] = []
    async with httpx.AsyncClient() as client:
        for item in cart_items:
            resp = await client.get(
                f"http://catalog-service:8000/books/{item.book_id}",
                timeout=5,
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book not found in catalog")
            book_data = resp.json()
            price = float(book_data["price"])
            total_amount += price * item.quantity
            order_items.append(
                OrderItem(
                    book_id=item.book_id,
                    quantity=item.quantity,
                    price=price,
                )
            )

    order = Order(user_id=user_id, total_amount=total_amount, status="created")
    db.add(order)
    await db.flush()

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    # Очистить корзину
    for item in cart_items:
        await db.delete(item)

    await db.commit()

    # Публикация событий
    client = get_rabbitmq_client()
    payload = {
        "order_id": order.id,
        "user_id": user_id,
        "total_amount": float(order.total_amount),
        "items": [{"book_id": i.book_id, "quantity": i.quantity} for i in order_items],
    }
    client.publish_event("order.created", payload)

    # Также можно отправить запрос на резервирование stock
    client.publish_event("stock.reserve.request", payload)

    logger.info("order_created", order_id=order.id, user_id=user_id)
    return await _load_order(db, order)


@router.get(
    "",
    response_model=OrderList,
    summary="Список заказов текущего пользователя",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user: Annotated[dict, Depends(get_current_user)] = None,  # noqa: ARG001
) -> OrderList:
    """Вернуть список заказов текущего пользователя."""

    user_id = await _get_user_id_from_token(user)
    result = await db.execute(select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()))
    orders = result.scalars().all()
    items = [await _load_order(db, o) for o in orders]
    return OrderList(items=items)


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Получить заказ по идентификатору",
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    user: Annotated[dict, Depends(get_current_user)] = None,  # noqa: ARG001
) -> OrderRead:
    """Вернуть заказ по идентификатору, если он принадлежит текущему пользователю."""

    user_id = await _get_user_id_from_token(user)
    result = await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return await _load_order(db, order)


