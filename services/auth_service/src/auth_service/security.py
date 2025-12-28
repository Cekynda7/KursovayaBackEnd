from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings
from .models import UserRole
from .schemas import TokenPayload


pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")



def hash_password(password: str) -> str:
    # bcrypt реально ограничен 72 байтами — ловим это до passlib
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Password too long (bcrypt limit: 72 bytes).",
                "details": {"max_bytes": 72},
            },
        )

    try:
        return pwd_context.hash(password)
    except ValueError as exc:
        # на всякий случай, если backend всё равно кинет ValueError
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid password for hashing.",
                "details": str(exc),
            },
        ) from exc


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить соответствие пароля и хеша."""

    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: UserRole) -> str:
    """Создать JWT access-токен."""

    settings = get_settings()
    expire_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(tz=timezone.utc) + expire_delta
    payload = {"sub": subject, "role": role.value, "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """Декодировать и валидировать JWT-токен."""

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload.model_validate(payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc


