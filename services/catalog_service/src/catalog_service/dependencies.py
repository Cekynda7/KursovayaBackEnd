from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .security import decode_jwt_token


bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> dict:
    """Получить текущего пользователя по JWT из заголовка Authorization."""

    token = credentials.credentials
    payload = decode_jwt_token(token)
    return payload


async def get_current_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Убедиться, что пользователь имеет роль admin."""

    role = user.get("role")
    if role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


