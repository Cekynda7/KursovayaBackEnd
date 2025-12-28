from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import User, UserRole
from .schemas import UserRead
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


CurrentUser = Annotated[UserRead, Depends(lambda: None)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserRead:
    """Получить текущего пользователя по JWT-токену."""

    payload = decode_token(token)
    stmt = select(User).where(User.id == payload.sub)
    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return UserRead.model_validate(user)


async def get_current_admin(user: Annotated[UserRead, Depends(get_current_user)]) -> UserRead:
    """Убедиться, что пользователь имеет роль admin."""

    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


