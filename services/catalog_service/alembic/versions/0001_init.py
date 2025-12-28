from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "authors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "books",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("isbn", sa.String(length=32)),
        sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("authors.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("isbn", name="uq_books_isbn"),
    )
    op.create_index("ix_books_title", "books", ["title"])
    op.create_index("ix_books_isbn", "books", ["isbn"])

    op.create_table(
        "book_categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id"), nullable=False),
        sa.UniqueConstraint("book_id", "category_id", name="uq_book_category"),
    )

    op.create_table(
        "stock",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False, unique=True),
        sa.Column("quantity", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("stock")
    op.drop_table("book_categories")
    op.drop_index("ix_books_isbn", table_name="books")
    op.drop_index("ix_books_title", table_name="books")
    op.drop_table("books")
    op.drop_table("categories")
    op.drop_table("authors")


