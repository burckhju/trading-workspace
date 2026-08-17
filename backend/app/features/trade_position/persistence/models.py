"""SQLAlchemy persistence models for FT-009 Trade & Position."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class TradeModel(Base):
    __tablename__ = "trades"
    __table_args__ = (
        CheckConstraint(
            """
            (
                origin = 'WORKSPACE_SELECTION'
                AND trade_plan_id IS NOT NULL
                AND trade_plan_version_id IS NOT NULL
                AND product_selection_id IS NOT NULL
                AND product_evaluation_id IS NOT NULL
            )
            OR
            (
                origin = 'EXTERNAL'
                AND trade_plan_id IS NULL
                AND trade_plan_version_id IS NULL
                AND product_selection_id IS NULL
                AND product_evaluation_id IS NULL
            )
            """,
            name="origin_provenance",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_trades_workspace",
        ),
        ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_trades_product",
        ),
        ForeignKeyConstraint(
            ["trade_plan_id"],
            ["trade_plans.id"],
            ondelete="RESTRICT",
            name="fk_trades_trade_plan",
        ),
        ForeignKeyConstraint(
            ["trade_plan_version_id"],
            ["trade_plan_versions.id"],
            ondelete="RESTRICT",
            name="fk_trades_trade_plan_version",
        ),
        ForeignKeyConstraint(
            ["product_selection_id"],
            ["product_selections.id"],
            ondelete="RESTRICT",
            name="fk_trades_product_selection",
        ),
        ForeignKeyConstraint(
            ["product_evaluation_id"],
            ["product_evaluations.id"],
            ondelete="RESTRICT",
            name="fk_trades_product_evaluation",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

    trade_plan_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    trade_plan_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    product_selection_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    product_evaluation_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class ExecutionRecordModel(Base):
    __tablename__ = "execution_records"
    __table_args__ = (
        CheckConstraint(
            "side IN ('BUY', 'SELL')",
            name="side_valid",
        ),
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        CheckConstraint(
            "price_per_unit > 0",
            name="price_positive",
        ),
        CheckConstraint(
            "recorded_at >= executed_at",
            name="recorded_not_before_executed",
        ),
        ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_execution_records_trade",
        ),
        ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_execution_records_product",
        ),
        ForeignKeyConstraint(
            ["supersedes_execution_id"],
            ["execution_records.id"],
            ondelete="RESTRICT",
            name="fk_execution_records_supersedes",
        ),
        UniqueConstraint(
            "supersedes_execution_id",
            name="uq_execution_records_supersedes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

    side: Mapped[str] = mapped_column(String(16), nullable=False)
    supersedes_execution_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer(), nullable=False)
    price_per_unit: Mapped[Decimal] = mapped_column(
        Numeric(24, 10),
        nullable=False,
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    recorded_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class PositionModel(Base):
    __tablename__ = "positions"
    __table_args__ = (
        CheckConstraint(
            "open_quantity >= 0",
            name="open_quantity_non_negative",
        ),
        CheckConstraint(
            "cost_basis >= 0",
            name="cost_basis_non_negative",
        ),
        CheckConstraint(
            "(open_quantity = 0 AND cost_basis = 0) OR " "(open_quantity > 0 AND cost_basis > 0)",
            name="position_state_consistent",
        ),
        CheckConstraint(
            "average_entry_price > 0",
            name="average_entry_price_positive",
        ),
        CheckConstraint(
            "last_execution_at >= opened_at",
            name="last_execution_not_before_opened",
        ),
        ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_positions_trade",
        ),
        ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_positions_product",
        ),
        UniqueConstraint(
            "trade_id",
            name="uq_positions_trade",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

    open_quantity: Mapped[int] = mapped_column(Integer(), nullable=False)
    cost_basis: Mapped[Decimal] = mapped_column(
        Numeric(30, 10),
        nullable=False,
    )
    average_entry_price: Mapped[Decimal] = mapped_column(
        Numeric(24, 10),
        nullable=False,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_execution_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    realized_gross_pnl: Mapped[Decimal] = mapped_column(
        Numeric(30, 10),
        nullable=False,
        default=Decimal("0"),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class TradeManagementEventModel(Base):
    __tablename__ = "trade_management_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('STOP_CHANGED', 'TARGET_CHANGED', "
            "'THESIS_UPDATED', 'MANAGEMENT_NOTE')",
            name="event_type_valid",
        ),
        CheckConstraint(
            "recorded_at >= effective_at",
            name="recorded_not_before_effective",
        ),
        CheckConstraint(
            """
            (
                event_type IN ('STOP_CHANGED', 'TARGET_CHANGED')
                AND numeric_value IS NOT NULL
                AND numeric_value > 0
                AND text_value IS NULL
            )
            OR
            (
                event_type IN ('THESIS_UPDATED', 'MANAGEMENT_NOTE')
                AND text_value IS NOT NULL
                AND numeric_value IS NULL
            )
            """,
            name="payload_valid",
        ),
        ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_trade_management_events_trade",
        ),
        ForeignKeyConstraint(
            ["supersedes_event_id"],
            ["trade_management_events.id"],
            ondelete="RESTRICT",
            name="fk_trade_management_events_supersedes",
        ),
        UniqueConstraint(
            "supersedes_event_id",
            name="uq_trade_management_events_supersedes",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    text_value: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    supersedes_event_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
