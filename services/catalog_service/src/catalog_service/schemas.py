from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Единый формат ошибок для catalog-service."""

    error_code: str
    message: str
    details: Dict[str, Any] | None = None


class AuthorRead(BaseModel):
    """DTO автора."""

    id: int
    name: str

    class Config:
        from_attributes = True


class CategoryRead(BaseModel):
    """DTO категории."""

    id: int
    name: str

    class Config:
        from_attributes = True


class BookBase(BaseModel):
    """Базовая информация о книге."""

    title: str = Field(..., description="Название книги")
    description: Optional[str] = Field(None, description="Описание книги")
    isbn: Optional[str] = Field(None, description="ISBN книги")
    price: float = Field(..., ge=0, description="Цена книги")


class BookCreate(BookBase):
    """Payload для создания книги (admin)."""

    author_name: Optional[str] = Field(None, description="Имя автора")
    category_names: List[str] = Field(default_factory=list, description="Список категорий")
    stock_quantity: int = Field(ge=0, default=0, description="Начальное количество на складе")


class BookUpdate(BaseModel):
    """Payload для частичного обновления книги (admin)."""

    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    stock_quantity: Optional[int] = Field(None, ge=0)


class BookRead(BaseModel):
    """DTO книги для ответов API."""

    id: int
    title: str
    description: Optional[str]
    isbn: Optional[str]
    price: float
    author: Optional[AuthorRead] = None
    categories: List[CategoryRead] = Field(default_factory=list)
    stock_quantity: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedBooks(BaseModel):
    """Результат пагинированного списка книг."""

    items: List[BookRead]
    total: int
    page: int
    page_size: int


