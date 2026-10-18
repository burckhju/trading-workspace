"""Append-only currency declarations; no default or backfill for execution prices."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ExecutionCurrencyConfirmationModel(Base):
    __tablename__ = "execution_currency_confirmations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "trade_id"],
            ["trades.workspace_id", "trades.id"],
            name="fk_execution_currency_trade_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["trade_id", "execution_id"],
            ["execution_records.trade_id", "execution_records.id"],
            name="fk_execution_currency_execution_scope",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["currency_code"],
            ["currencies.code"],
            name="fk_execution_currency_code",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "id", "workspace_id", "trade_id", "execution_id", name="uq_execution_currency_identity"
        ),
        ForeignKeyConstraint(
            ["supersedes_confirmation_id", "workspace_id", "trade_id", "execution_id"],
            [
                "execution_currency_confirmations.id",
                "execution_currency_confirmations.workspace_id",
                "execution_currency_confirmations.trade_id",
                "execution_currency_confirmations.execution_id",
            ],
            name="fk_execution_currency_predecessor",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("supersedes_confirmation_id", name="uq_execution_currency_successor"),
        UniqueConstraint("workspace_id", "request_id", name="uq_execution_currency_request"),
        Index(
            "uq_execution_currency_root",
            "execution_id",
            unique=True,
            postgresql_where=text("supersedes_confirmation_id IS NULL"),
        ),
        CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="execution_currency_code_valid"),
        CheckConstraint("source = 'USER_CONFIRMED'", name="execution_currency_source_valid"),
        CheckConstraint(
            "note IS NULL OR (length(trim(note)) BETWEEN 1 AND 1000)",
            name="execution_currency_note_valid",
        ),
        CheckConstraint("id <> supersedes_confirmation_id", name="execution_currency_not_self"),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="execution_currency_fingerprint_valid"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    execution_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    supersedes_confirmation_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    request_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
