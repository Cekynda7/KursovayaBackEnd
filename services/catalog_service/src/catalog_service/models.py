from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Author(Base):
    """Author entity."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Category(Base):
    """Book category."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    book_links: Mapped[list["BookCategory"]] = relationship(back_populates="category")


class Book(Base):
    """Book entity."""

    __tablename__ = "books"
    __table_args__ = (UniqueConstraint("isbn", name="uq_books_isbn"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    isbn: Mapped[str | None] = mapped_column(String(32), index=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    author: Mapped[Author | None] = relationship(back_populates="books")
    categories: Mapped[list["BookCategory"]] = relationship(back_populates="book")
    stock: Mapped["Stock"] = relationship(back_populates="book", uselist=False)


class BookCategory(Base):
    """Many-to-many between books and categories."""

    __tablename__ = "book_categories"
    __table_args__ = (UniqueConstraint("book_id", "category_id", name="uq_book_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))

    book: Mapped[Book] = relationship(back_populates="categories")
    category: Mapped[Category] = relationship(back_populates="book_links")


class Stock(Base):
    """Stock/inventory information for a book."""

    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), unique=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    book: Mapped[Book] = relationship(back_populates="stock")


