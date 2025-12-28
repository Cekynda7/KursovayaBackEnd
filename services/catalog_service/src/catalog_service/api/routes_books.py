from __future__ import annotations

from typing import Annotated, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..core.logging import get_logger
from ..db import get_db
from ..dependencies import get_current_admin, get_current_user
from ..models import Author, Book, BookCategory, Category, Stock
from ..schemas import BookCreate, BookRead, BookUpdate, PaginatedBooks

router = APIRouter(prefix="/books", tags=["books"])

logger = get_logger(__name__)


def _serialize_book(book: Book) -> BookRead:
    categories = [bc.category for bc in book.categories]
    stock_quantity = book.stock.quantity if book.stock else 0
    return BookRead(
        id=book.id,
        title=book.title,
        description=book.description,
        isbn=book.isbn,
        price=float(book.price),
        author=None if not book.author else book.author,
        categories=categories,
        stock_quantity=stock_quantity,
        created_at=book.created_at,
    )


def _books_with_relations() -> Select[tuple[Book]]:
    return select(Book).options(
        selectinload(Book.author),
        selectinload(Book.stock),
        selectinload(Book.categories).selectinload(BookCategory.category),
    )


@router.get(
    "",
    response_model=PaginatedBooks,
    summary="Поиск и просмотр книг",
)
async def list_books(
    query: Optional[str] = Query(None, description="Поиск по названию/описанию"),
    author: Optional[str] = Query(None, description="Фильтр по автору"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedBooks:
    """Вернуть список книг с фильтрами и пагинацией (публичный эндпоинт)."""

    base_stmt: Select[tuple[Book]] = select(Book).join(Author, isouter=True)

    if query:
        base_stmt = base_stmt.where(or_(Book.title.ilike(f"%{query}%"), Book.description.ilike(f"%{query}%")))

    if author:
        base_stmt = base_stmt.where(Author.name.ilike(f"%{author}%"))

    if category:
        base_stmt = base_stmt.join(BookCategory).join(Category).where(Category.name.ilike(f"%{category}%"))

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    data_stmt = (
        base_stmt.options(
            selectinload(Book.author),
            selectinload(Book.stock),
            selectinload(Book.categories).selectinload(BookCategory.category),
        )
        .order_by(Book.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(data_stmt)
    books = result.scalars().unique().all()

    items = [_serialize_book(b) for b in books]
    return PaginatedBooks(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{book_id}",
    response_model=BookRead,
    summary="Получить книгу по идентификатору",
)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)) -> BookRead:
    """Вернуть одну книгу по ее идентификатору (публичный эндпоинт)."""

    stmt = _books_with_relations().where(Book.id == book_id)
    result = await db.execute(stmt)
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return _serialize_book(book)


@router.post(
    "",
    response_model=BookRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую книгу (admin)",
)
async def create_book(
    payload: BookCreate,
    db: AsyncSession = Depends(get_db),
    admin: Annotated[dict, Depends(get_current_admin)] = None,  # noqa: ARG001
) -> BookRead:
    """Создать книгу, автора, категории и stock (доступно только admin)."""

    author: Author | None = None
    if payload.author_name:
        result = await db.execute(select(Author).where(Author.name == payload.author_name))
        author = result.scalar_one_or_none()
        if not author:
            author = Author(name=payload.author_name)
            db.add(author)
            await db.flush()

    book = Book(
        title=payload.title,
        description=payload.description,
        isbn=payload.isbn,
        price=payload.price,
        author=author,
    )
    db.add(book)
    await db.flush()

    categories: list[Category] = []
    for cat_name in payload.category_names:
        result = await db.execute(select(Category).where(Category.name == cat_name))
        category = result.scalar_one_or_none()
        if not category:
            category = Category(name=cat_name)
            db.add(category)
            await db.flush()
        categories.append(category)

    for category in categories:
        db.add(BookCategory(book=book, category=category))

    stock = Stock(book=book, quantity=payload.stock_quantity)
    db.add(stock)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book with this ISBN already exists")

    result = await db.execute(_books_with_relations().where(Book.id == book.id))
    book = result.scalar_one()
    logger.info("book_created", book_id=book.id, title=book.title)
    return _serialize_book(book)


@router.patch(
    "/{book_id}",
    response_model=BookRead,
    summary="Частично обновить книгу (admin)",
)
async def update_book(
    book_id: int,
    payload: BookUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Annotated[dict, Depends(get_current_admin)] = None,  # noqa: ARG001
) -> BookRead:
    """Обновить некоторые поля книги и при необходимости количество на складе (admin)."""

    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if payload.title is not None:
        book.title = payload.title
    if payload.description is not None:
        book.description = payload.description
    if payload.price is not None:
        book.price = payload.price

    if payload.stock_quantity is not None:
        if not book.stock:
            book.stock = Stock(quantity=payload.stock_quantity, book=book)
        else:
            book.stock.quantity = payload.stock_quantity

    await db.commit()
    result = await db.execute(_books_with_relations().where(Book.id == book.id))
    book = result.scalar_one()
    logger.info("book_updated", book_id=book.id)
    return _serialize_book(book)


@router.post(
    "/import/by-isbn",
    response_model=BookRead,
    summary="Импортировать книгу по ISBN из внешнего API (admin)",
)
async def import_book_by_isbn(
    isbn: str,
    db: AsyncSession = Depends(get_db),
    admin: Annotated[dict, Depends(get_current_admin)] = None,  # noqa: ARG001
) -> BookRead:
    """
    Импортировать книгу по ISBN, используя внешний Open Library API,
    и создать соответствующую запись в каталоге.
    """

    settings = get_settings()
    url = f"{settings.external_books_api_base}/isbn/{isbn}.json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
    if resp.status_code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found in external API")
    if resp.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="External books API error")

    data = resp.json()
    title = data.get("title", f"ISBN {isbn}")
    description = data.get("description")
    if isinstance(description, dict):
        description = description.get("value")

    book_payload = BookCreate(
        title=title,
        description=description,
        isbn=isbn,
        price=0.0,
        author_name=None,
        category_names=[],
        stock_quantity=0,
    )
    return await create_book(book_payload, db=db)  # type: ignore[arg-type]


