from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import get_logger
from ..db import get_db
from ..models import User, UserRole
from ..schemas import TokenResponse, UserCreate, UserLogin, UserRead
from ..security import create_access_token, hash_password, verify_password
from ..dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

logger = get_logger(__name__)


async def _authenticate_user(email: str, password: str, db: AsyncSession) -> User:
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> UserRead:
    """Зарегистрировать нового пользователя."""

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")
    await db.refresh(user)
    logger.info("user_registered", user_id=user.id, email=user.email)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login_user(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Выполнить вход пользователя и выдать access-токен."""

    user = await _authenticate_user(payload.email, payload.password, db)
    token = create_access_token(subject=str(user.id), role=user.role)
    logger.info("user_logged_in", user_id=user.id, email=user.email)
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
async def token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """OAuth2 token endpoint compatible with Swagger Authorize."""

    user = await _authenticate_user(form_data.username, form_data.password, db)
    token = create_access_token(subject=str(user.id), role=user.role)
    logger.info("user_logged_in", user_id=user.id, email=user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
async def read_me(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    """Вернуть профиль текущего пользователя."""

    return current_user


