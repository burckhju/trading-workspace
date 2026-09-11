"""Create one reproducible open XSTU warrant position through FT-009 services.

This tool is intentionally limited to existing FT-008 ProductSelections whose
selected ProductEvaluation references an XSTU WarrantListing. It never inserts
or mutates Trade/Execution/Position persistence models directly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config.settings import get_settings
from app.database import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.product.service.application import WarrantService
from app.features.product_selection.persistence.models import (
    ProductEvaluationModel,
    ProductSelectionModel,
    ProductSelectionRunModel,
)
from app.features.trade_position.persistence.models import PositionModel, TradeModel
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import (
    SqlAlchemyWorkspaceSelectionResolver,
    WarrantProductResolver,
)

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")

SelectionRow = tuple[UUID, UUID, UUID, UUID, str | None, str | None, str, datetime]


@dataclass(frozen=True, slots=True)
class XstuSelectionCandidate:
    selection_id: UUID
    evaluation_id: UUID
    warrant_listing_id: UUID
    warrant_id: UUID
    symbol: str | None
    isin: str
    currency: str
    selected_at: datetime


def _candidate_statement(
    *,
    workspace_id: UUID,
    selection_id: UUID | None,
) -> Select[SelectionRow]:
    statement = (
        select(
            ProductSelectionModel.id.label("selection_id"),
            ProductSelectionModel.product_evaluation_id.label("evaluation_id"),
            ProductEvaluationModel.warrant_listing_id.label("warrant_listing_id"),
            ProductEvaluationModel.warrant_id.label("warrant_id"),
            WarrantListingModel.symbol.label("symbol"),
            WarrantModel.isin.label("isin"),
            WarrantListingModel.quotation_currency_code.label("currency"),
            ProductSelectionModel.selected_at.label("selected_at"),
        )
        .join(
            ProductSelectionRunModel,
            ProductSelectionRunModel.id == ProductSelectionModel.run_id,
        )
        .join(
            ProductEvaluationModel,
            ProductEvaluationModel.id == ProductSelectionModel.product_evaluation_id,
        )
        .join(
            WarrantListingModel,
            WarrantListingModel.id == ProductEvaluationModel.warrant_listing_id,
        )
        .join(WarrantModel, WarrantModel.id == ProductEvaluationModel.warrant_id)
        .join(
            TradingVenueModel,
            TradingVenueModel.id == WarrantListingModel.trading_venue_id,
        )
        .where(
            ProductSelectionRunModel.workspace_id == workspace_id,
            WarrantListingModel.workspace_id == workspace_id,
            WarrantModel.workspace_id == workspace_id,
            TradingVenueModel.mic == "XSTU",
            WarrantModel.isin.is_not(None),
        )
        .order_by(ProductSelectionModel.selected_at.desc())
        .limit(1)
    )
    if selection_id is not None:
        statement = statement.where(ProductSelectionModel.id == selection_id)
    return statement


async def find_xstu_selection(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    selection_id: UUID | None = None,
) -> XstuSelectionCandidate | None:
    row = (
        (
            await session.execute(
                _candidate_statement(workspace_id=workspace_id, selection_id=selection_id)
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    isin = row["isin"]
    if not isinstance(isin, str) or not isin.strip():
        return None
    return XstuSelectionCandidate(
        selection_id=row["selection_id"],
        evaluation_id=row["evaluation_id"],
        warrant_listing_id=row["warrant_listing_id"],
        warrant_id=row["warrant_id"],
        symbol=row["symbol"],
        isin=isin,
        currency=row["currency"],
        selected_at=row["selected_at"],
    )


async def find_existing_open_trade(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    selection_id: UUID,
) -> tuple[UUID, int] | None:
    row = (
        await session.execute(
            select(TradeModel.id, PositionModel.open_quantity)
            .join(PositionModel, PositionModel.trade_id == TradeModel.id)
            .where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.product_selection_id == selection_id,
                PositionModel.open_quantity > 0,
            )
            .order_by(TradeModel.created_at.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def _positive_decimal(value: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("price must be a decimal number") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("price must be greater than zero")
    return parsed


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("quantity must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("quantity must be greater than zero")
    return parsed


def _timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("executed-at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("executed-at must include a timezone")
    return parsed.astimezone(UTC)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create an open XSTU warrant position from an existing FT-008 ProductSelection "
            "through TradePositionService.record_initial_purchase()."
        )
    )
    parser.add_argument(
        "--selection-id",
        type=UUID,
        help=(
            "Use this ProductSelection UUID; otherwise the latest eligible XSTU selection is used."
        ),
    )
    parser.add_argument("--quantity", type=_positive_int, default=1)
    parser.add_argument(
        "--price",
        type=_positive_decimal,
        required=True,
        help="Captured BUY execution price per warrant unit; no broker order is sent.",
    )
    parser.add_argument(
        "--executed-at",
        type=_timestamp,
        help="ISO-8601 execution time; defaults to now in UTC.",
    )
    parser.add_argument("--actor-id", type=UUID, default=LOCAL_ACTOR_ID)
    parser.add_argument(
        "--force-new",
        action="store_true",
        help=(
            "Create another trade even when the selected ProductSelection already has an open one."
        ),
    )
    return parser


async def seed(args: argparse.Namespace) -> dict[str, object]:
    settings = get_settings()
    database = DatabaseManager(settings)
    try:
        async with database.session_context() as session:
            candidate = await find_xstu_selection(
                session,
                workspace_id=WORKSPACE_ID,
                selection_id=args.selection_id,
            )
            if candidate is None:
                qualifier = f" with id {args.selection_id}" if args.selection_id is not None else ""
                raise RuntimeError(
                    "No existing FT-008 ProductSelection"
                    f"{qualifier} references a WarrantListing on MIC XSTU with an ISIN. "
                    "Create/select an XSTU warrant through the normal product-selection "
                    "workflow first."
                )

            if not args.force_new:
                existing = await find_existing_open_trade(
                    session,
                    workspace_id=WORKSPACE_ID,
                    selection_id=candidate.selection_id,
                )
                if existing is not None:
                    trade_id, open_quantity = existing
                    return {
                        "created": False,
                        "reason": "OPEN_POSITION_ALREADY_EXISTS_FOR_SELECTION",
                        "trade_id": str(trade_id),
                        "open_quantity": open_quantity,
                        "selection": asdict(candidate),
                    }

            service = TradePositionService(
                uow=SqlAlchemyTradePositionUnitOfWork(session),
                workspace_selections=SqlAlchemyWorkspaceSelectionResolver(session),
                products=WarrantProductResolver(WarrantService(session)),
            )
            trade, execution, position = await service.record_initial_purchase(
                workspace_id=WORKSPACE_ID,
                product_selection_id=candidate.selection_id,
                quantity=args.quantity,
                price_per_unit=args.price,
                executed_at=args.executed_at or datetime.now(UTC),
                actor=args.actor_id,
            )
            return {
                "created": True,
                "trade_id": str(trade.id),
                "execution_id": str(execution.id),
                "position_id": str(position.id),
                "open_quantity": position.open_quantity,
                "average_entry_price": str(position.average_entry_price),
                "selection": asdict(candidate),
            }
    finally:
        await database.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = asyncio.run(seed(args))
    except RuntimeError as exc:
        print(json.dumps({"created": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
