from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field

from .models import UserRole


class ErrorResponse(BaseModel):
    """Единый формат ошибок."""

    error_code: str
    message: str
    details: Dict[str, Any] | None = None


class UserCreate(BaseModel):
    """Payload для регистрации пользователя."""

    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=6, description="Пароль пользователя")


class UserLogin(BaseModel):
    """Payload для логина пользователя."""

    email: EmailStr
    password: str


class UserRead(BaseModel):
    """Информация о пользователе для ответа API."""

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Ответ с access-токеном."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Декодированный payload JWT."""

    sub: int
    role: UserRole
    exp: int


