from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..dependencies import get_current_user
from ..models import Cart, CartItem
from ..schemas import CartItemCreate, CartItemRead, CartRead

router = APIRouter(prefix="/cart", tags=["cart"])


async def _get_or_create_cart(db: AsyncSession, user_id: int) -> Cart:
    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = result.scalar_one_or_none()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        await db.flush()
    return cart


async def _get_cart_items(db: AsyncSession, cart_id: int) -> list[CartItemRead]:
    result = await db.execute(select(CartItem).where(CartItem.cart_id == cart_id))
    items = result.scalars().all()
    return [CartItemRead(book_id=i.book_id, quantity=i.quantity) for i in items]


@router.post(
    "/items",
    response_model=CartRead,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить позицию в корзину",
)
async def add_cart_item(
    payload: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    user: Annotated[dict, Depends(get_current_user)] = None,  # noqa: ARG001
) -> CartRead:
    """Добавить или увеличить количество книги в корзине текущего пользователя."""

    user_id = int(user["sub"]) if str(user.get("sub", "")).isdigit() else user.get("user_id", 0)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user in token")

    cart = await _get_or_create_cart(db, user_id=user_id)

    result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.book_id == payload.book_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        item = CartItem(cart_id=cart.id, book_id=payload.book_id, quantity=payload.qty)
        db.add(item)
    else:
        item.quantity += payload.qty

    await db.commit()
    items = await _get_cart_items(db, cart.id)
    return CartRead(items=items)


@router.get(
    "",
    response_model=CartRead,
    summary="Получить текущую корзину",
)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    user: Annotated[dict, Depends(get_current_user)] = None,  # noqa: ARG001
) -> CartRead:
    """Вернуть содержимое корзины текущего пользователя."""

    user_id = int(user["sub"]) if str(user.get("sub", "")).isdigit() else user.get("user_id", 0)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user in token")

    result = await db.execute(select(Cart).where(Cart.user_id == user_id))
    cart = result.scalar_one_or_none()
    if not cart:
        return CartRead(items=[])
    items = await _get_cart_items(db, cart.id)
    return CartRead(items=items)


