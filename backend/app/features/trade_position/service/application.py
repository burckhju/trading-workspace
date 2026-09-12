"""Application service for FT-009 Trade & Position purchase execution capture."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from app.features.trade_position.domain.enums import (
    ExecutionSide,
    TradeManagementEventType,
    TradeOrigin,
)
from app.features.trade_position.domain.management import (
    TradeManagementState,
    TradeManagementStateProjector,
)
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    Trade,
    TradeManagementEvent,
)
from app.features.trade_position.domain.projector import PositionProjector
from app.features.trade_position.domain.timeline import (
    Ft011Eligibility,
    TradeTimelineEntry,
    TradeTimelineEntryKind,
    compose_trade_timeline,
    ft011_eligibility,
)
from app.features.trade_position.persistence.unit_of_work import TradePositionUnitOfWork
from app.features.trade_position.service.errors import capture_conflict
from app.features.trade_position.service.resolvers import (
    ResolvedProduct,
    ResolvedWorkspaceSelection,
)


class WorkspaceSelectionResolver(Protocol):
    async def resolve(
        self,
        workspace_id: UUID,
        product_selection_id: UUID,
    ) -> ResolvedWorkspaceSelection | None: ...


class ProductResolver(Protocol):
    async def resolve(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ResolvedProduct | None: ...


class TradePositionService:
    @staticmethod
    def _request_identity(
        workspace_id: UUID,
        request_id: UUID | None,
        scope: str,
        quantity: int,
        price: Decimal,
        executed_at: datetime,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
    ) -> tuple[str | None, str | None]:
        if request_id is None:
            return None, None
        key = hashlib.sha256(f"{workspace_id}:{request_id}".encode()).hexdigest()
        payload = [
            scope,
            quantity,
            str(price.normalize()),
            executed_at.astimezone(UTC).isoformat(),
            str(executed_on),
            execution_timezone,
        ]
        return key, hashlib.sha256(json.dumps(payload).encode()).hexdigest()

    async def _replay(
        self, workspace_id: UUID, key: str | None, fingerprint: str | None
    ) -> tuple[Trade, ExecutionRecord, Position] | None:
        if key is None:
            return None
        original = await self._uow.executions.find_request(workspace_id, key)
        if original is None:
            return None
        if original.request_fingerprint != fingerprint:
            raise capture_conflict(
                "CAPTURE_KEY_CONFLICT",
                "Diese Vorgangskennung wurde bereits für andere Kauf-/Verkaufsdaten verwendet.",
            )
        trade = await self._uow.trades.get(workspace_id, original.trade_id)
        if trade is None:
            raise ValueError("trade not found")
        self._require_active(trade)
        position = await self._uow.positions.get_for_trade(workspace_id, trade.id)
        if position is None:
            raise ValueError("position not found")
        return trade, original, position

    @staticmethod
    def _require_active(trade: Trade) -> None:
        if trade.cancelled_at is not None:
            raise capture_conflict(
                "TRADE_CANCELLED",
                "Dieser Trade wurde als Fehleingabe storniert. Seine Historie ist "
                "schreibgeschützt.",
            )

    def __init__(
        self,
        *,
        uow: TradePositionUnitOfWork,
        workspace_selections: WorkspaceSelectionResolver,
        products: ProductResolver | None = None,
    ) -> None:
        self._uow = uow
        self._workspace_selections = workspace_selections
        self._products = products

    async def record_initial_purchase(
        self,
        *,
        workspace_id: UUID,
        product_selection_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
        request_id: UUID | None = None,
    ) -> tuple[Trade, ExecutionRecord, Position]:
        request_key, request_fingerprint = self._request_identity(
            workspace_id,
            request_id,
            f"selection:{product_selection_id}",
            quantity,
            price_per_unit,
            executed_at,
            executed_on,
            execution_timezone,
        )
        replay = await self._replay(workspace_id, request_key, request_fingerprint)
        if replay is not None:
            return replay
        selection = await self._workspace_selections.resolve(
            workspace_id,
            product_selection_id,
        )
        if selection is None:
            raise ValueError("product selection not found")

        now = datetime.now(UTC)

        trade = Trade(
            id=uuid4(),
            workspace_id=workspace_id,
            product_id=selection.product_id,
            origin=TradeOrigin.WORKSPACE_SELECTION,
            created_at=now,
            created_by=actor,
            trade_plan_id=selection.trade_plan_id,
            trade_plan_version_id=selection.trade_plan_version_id,
            product_selection_id=selection.product_selection_id,
            product_evaluation_id=selection.product_evaluation_id,
        )

        execution = ExecutionRecord(
            id=uuid4(),
            trade_id=trade.id,
            product_id=trade.product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
            recorded_at=now,
            recorded_by=actor,
            executed_on=executed_on,
            execution_timezone=execution_timezone,
            request_key=request_key,
            request_fingerprint=request_fingerprint,
        )

        position = Position.from_execution(
            id=uuid4(),
            trade=trade,
            execution=execution,
        )

        async with self._uow as uow:
            await uow.trades.add(trade)
            await uow.executions.add(execution)
            await uow.positions.add(position)
            await uow.commit()

        return trade, execution, position

    async def record_external_purchase(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
        request_id: UUID | None = None,
    ) -> tuple[Trade, ExecutionRecord, Position]:
        request_key, request_fingerprint = self._request_identity(
            workspace_id,
            request_id,
            f"external:{product_id}",
            quantity,
            price_per_unit,
            executed_at,
            executed_on,
            execution_timezone,
        )
        replay = await self._replay(workspace_id, request_key, request_fingerprint)
        if replay is not None:
            return replay
        if self._products is None:
            raise ValueError("product resolver is required")

        product = await self._products.resolve(
            workspace_id,
            product_id,
        )
        if product is None:
            raise ValueError("product not found")

        now = datetime.now(UTC)

        trade = Trade(
            id=uuid4(),
            workspace_id=workspace_id,
            product_id=product.product_id,
            origin=TradeOrigin.EXTERNAL,
            created_at=now,
            created_by=actor,
        )

        execution = ExecutionRecord(
            id=uuid4(),
            trade_id=trade.id,
            product_id=trade.product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
            recorded_at=now,
            recorded_by=actor,
            executed_on=executed_on,
            execution_timezone=execution_timezone,
            request_key=request_key,
            request_fingerprint=request_fingerprint,
        )

        position = Position.from_execution(
            id=uuid4(),
            trade=trade,
            execution=execution,
        )

        async with self._uow as uow:
            await uow.trades.add(trade)
            await uow.executions.add(execution)
            await uow.positions.add(position)
            await uow.commit()

        return trade, execution, position

    async def record_additional_purchase(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
        request_id: UUID | None = None,
    ) -> tuple[ExecutionRecord, Position]:
        request_key, request_fingerprint = self._request_identity(
            workspace_id,
            request_id,
            f"purchase:{trade_id}",
            quantity,
            price_per_unit,
            executed_at,
            executed_on,
            execution_timezone,
        )
        replay = await self._replay(workspace_id, request_key, request_fingerprint)
        if replay is not None:
            return replay[1], replay[2]
        async with self._uow as uow:
            trade = await uow.trades.get(
                workspace_id,
                trade_id,
            )
            if trade is None:
                raise ValueError("trade not found")
            self._require_active(trade)

            position = await uow.positions.get_for_trade(
                workspace_id,
                trade_id,
            )
            if position is None:
                raise ValueError("position not found")

            now = datetime.now(UTC)

            execution = ExecutionRecord(
                id=uuid4(),
                trade_id=trade.id,
                product_id=trade.product_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
                executed_at=executed_at,
                recorded_at=now,
                recorded_by=actor,
                executed_on=executed_on,
                execution_timezone=execution_timezone,
                request_key=request_key,
                request_fingerprint=request_fingerprint,
            )

            effective_history = await uow.executions.list_effective_for_trade(trade.id)
            if not effective_history:
                raise ValueError("effective execution history not found")
            updated = PositionProjector.project(
                id=position.id,
                trade=trade,
                executions=[*effective_history, execution],
            )

            await uow.executions.add(execution)
            await uow.positions.replace(updated)
            await uow.commit()

        return execution, updated

    async def record_sale(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
        request_id: UUID | None = None,
    ) -> tuple[ExecutionRecord, Position]:
        request_key, request_fingerprint = self._request_identity(
            workspace_id,
            request_id,
            f"sale:{trade_id}",
            quantity,
            price_per_unit,
            executed_at,
            executed_on,
            execution_timezone,
        )
        replay = await self._replay(workspace_id, request_key, request_fingerprint)
        if replay is not None:
            return replay[1], replay[2]
        async with self._uow as uow:
            trade = await uow.trades.get(
                workspace_id,
                trade_id,
            )
            if trade is None:
                raise ValueError("trade not found")
            self._require_active(trade)

            position = await uow.positions.get_for_trade(
                workspace_id,
                trade_id,
            )
            if position is None:
                raise ValueError("position not found")
            if position.is_closed:
                raise ValueError("trade is already closed")

            now = datetime.now(UTC)
            execution = ExecutionRecord(
                id=uuid4(),
                trade_id=trade.id,
                product_id=trade.product_id,
                side=ExecutionSide.SELL,
                quantity=quantity,
                price_per_unit=price_per_unit,
                executed_at=executed_at,
                recorded_at=now,
                recorded_by=actor,
                executed_on=executed_on,
                execution_timezone=execution_timezone,
                request_key=request_key,
                request_fingerprint=request_fingerprint,
            )

            effective_history = await uow.executions.list_effective_for_trade(trade.id)
            if not effective_history:
                raise ValueError("effective execution history not found")
            updated = PositionProjector.project(
                id=position.id,
                trade=trade,
                executions=[*effective_history, execution],
            )

            await uow.executions.add(execution)
            await uow.positions.replace(updated)
            await uow.commit()

        return execution, updated

    async def record_management_event(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        event_type: TradeManagementEventType,
        effective_at: datetime,
        actor: UUID,
        numeric_value: Decimal | None = None,
        text_value: str | None = None,
        supersedes_event_id: UUID | None = None,
    ) -> TradeManagementEvent:
        async with self._uow as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ValueError("trade not found")
            self._require_active(trade)

            now = datetime.now(UTC)
            event = TradeManagementEvent(
                id=uuid4(),
                trade_id=trade.id,
                event_type=event_type,
                effective_at=effective_at,
                recorded_at=max(now, effective_at),
                recorded_by=actor,
                numeric_value=numeric_value,
                text_value=text_value,
                supersedes_event_id=supersedes_event_id,
            )
            await uow.management_events.add(event)
            await uow.commit()

        return event

    async def change_stop(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        stop_price: Decimal,
        effective_at: datetime,
        actor: UUID,
    ) -> TradeManagementEvent:
        return await self.record_management_event(
            workspace_id=workspace_id,
            trade_id=trade_id,
            event_type=TradeManagementEventType.STOP_CHANGED,
            effective_at=effective_at,
            actor=actor,
            numeric_value=stop_price,
        )

    async def change_target(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        target_price: Decimal,
        effective_at: datetime,
        actor: UUID,
    ) -> TradeManagementEvent:
        return await self.record_management_event(
            workspace_id=workspace_id,
            trade_id=trade_id,
            event_type=TradeManagementEventType.TARGET_CHANGED,
            effective_at=effective_at,
            actor=actor,
            numeric_value=target_price,
        )

    async def update_thesis(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        thesis: str,
        effective_at: datetime,
        actor: UUID,
    ) -> TradeManagementEvent:
        return await self.record_management_event(
            workspace_id=workspace_id,
            trade_id=trade_id,
            event_type=TradeManagementEventType.THESIS_UPDATED,
            effective_at=effective_at,
            actor=actor,
            text_value=thesis,
        )

    async def add_management_note(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        note: str,
        effective_at: datetime,
        actor: UUID,
    ) -> TradeManagementEvent:
        return await self.record_management_event(
            workspace_id=workspace_id,
            trade_id=trade_id,
            event_type=TradeManagementEventType.MANAGEMENT_NOTE,
            effective_at=effective_at,
            actor=actor,
            text_value=note,
        )

    async def get_management_state(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> TradeManagementState:
        async with self._uow as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ValueError("trade not found")
            events = await uow.management_events.list_effective_for_trade(trade.id)

        return TradeManagementStateProjector.project(
            trade_id=trade.id,
            events=events,
        )

    async def get_position(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Position:
        async with self._uow as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ValueError("trade not found")
            position = await uow.positions.get_for_trade(workspace_id, trade.id)
            if position is None:
                raise ValueError("position not found")

        return replace(position, is_cancelled=trade.cancelled_at is not None)

    async def correct_execution(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        execution_id: UUID,
        side: ExecutionSide,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
        executed_on: date | None = None,
        execution_timezone: str | None = None,
    ) -> tuple[ExecutionRecord, Position]:
        async with self._uow as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ValueError("trade not found")
            self._require_active(trade)

            position = await uow.positions.get_for_trade(workspace_id, trade_id)
            if position is None:
                raise ValueError("position not found")

            history = await uow.executions.list_for_trade(trade.id)
            target = next((item for item in history if item.id == execution_id), None)
            if target is None:
                raise ValueError("execution not found")
            if any(item.supersedes_execution_id == execution_id for item in history):
                raise ValueError("execution is already superseded")

            now = datetime.now(UTC)
            replacement = ExecutionRecord(
                id=uuid4(),
                trade_id=trade.id,
                product_id=trade.product_id,
                side=side,
                quantity=quantity,
                price_per_unit=price_per_unit,
                executed_at=executed_at,
                recorded_at=now,
                recorded_by=actor,
                executed_on=executed_on,
                execution_timezone=execution_timezone,
                supersedes_execution_id=target.id,
            )

            effective_history = [
                item
                for item in history
                if item.id != target.id
                and not any(candidate.supersedes_execution_id == item.id for candidate in history)
            ]
            updated = PositionProjector.project(
                id=position.id,
                trade=trade,
                executions=[*effective_history, replacement],
            )

            await uow.executions.add(replacement)
            await uow.positions.replace(updated)
            await uow.commit()

        return replacement, updated

    async def correct_management_event(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        event_id: UUID,
        effective_at: datetime,
        actor: UUID,
        numeric_value: Decimal | None = None,
        text_value: str | None = None,
    ) -> TradeManagementEvent:
        async with self._uow as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ValueError("trade not found")
            self._require_active(trade)

            history = await uow.management_events.list_for_trade(trade.id)
            target = next((item for item in history if item.id == event_id), None)
            if target is None:
                raise ValueError("management event not found")
            if any(item.supersedes_event_id == event_id for item in history):
                raise ValueError("management event is already superseded")

            now = datetime.now(UTC)
            replacement = TradeManagementEvent(
                id=uuid4(),
                trade_id=trade.id,
                event_type=target.event_type,
                effective_at=effective_at,
                recorded_at=max(now, effective_at),
                recorded_by=actor,
                numeric_value=numeric_value,
                text_value=text_value,
                supersedes_event_id=target.id,
            )
            await uow.management_events.add(replacement)
            await uow.commit()

        return replacement

    async def get_trade_timeline(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> list[TradeTimelineEntry]:
        async with self._uow as uow:
            trade = await uow.trades.get(workspace_id, trade_id)
            if trade is None:
                raise ValueError("trade not found")
            executions = await uow.executions.list_for_trade(trade.id)
            management_events = await uow.management_events.list_for_trade(trade.id)

        timeline = compose_trade_timeline(
            trade_id=trade.id,
            executions=executions,
            management_events=management_events,
        )
        if trade.cancelled_at is not None:
            timeline.append(
                TradeTimelineEntry(
                    id=trade.id,
                    trade_id=trade.id,
                    occurred_at=trade.cancelled_at,
                    recorded_at=trade.cancelled_at,
                    kind=TradeTimelineEntryKind.CANCELLATION,
                    text_value=trade.cancellation_reason,
                )
            )
        return sorted(timeline, key=lambda item: (item.occurred_at, item.recorded_at, item.id))

    async def get_ft011_eligibility(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Ft011Eligibility:
        position = await self.get_position(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        return ft011_eligibility(position)
