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
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

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
            "open_quantity > 0",
            name="open_quantity_positive",
        ),
        CheckConstraint(
            "cost_basis > 0",
            name="cost_basis_positive",
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
