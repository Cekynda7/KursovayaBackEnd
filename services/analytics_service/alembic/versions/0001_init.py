from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("routing_key", sa.String(length=128), nullable=False, index=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False, index=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("events")


