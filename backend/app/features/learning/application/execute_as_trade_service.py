"""FT-012 execute-as-trade application service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.application.external_trade_creator import (
    ExternalTradeCreator,
)
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
)
from app.features.learning.domain import (
    IdempotencyRecord,
    IdempotencyStatus,
)
from app.features.learning.persistence.unit_of_work import (
    LearningTradeLinkUnitOfWork,
)

COMMAND_TYPE = "EXECUTE_AS_TRADE"
RESULT_TYPE = "TRADE"


class ExecuteAsTradeErrorCode(StrEnum):
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    IDEMPOTENCY_IN_PROGRESS = "IDEMPOTENCY_IN_PROGRESS"
    IDEMPOTENCY_FAILED_FINAL = "IDEMPOTENCY_FAILED_FINAL"
    EXTERNAL_OBSERVATION_NOT_FOUND = "EXTERNAL_OBSERVATION_NOT_FOUND"
    EXTERNAL_OBSERVATION_SOURCE_NOT_FOUND = "EXTERNAL_OBSERVATION_SOURCE_NOT_FOUND"
    EXTERNAL_OBSERVATION_PRODUCT_REQUIRED = "EXTERNAL_OBSERVATION_PRODUCT_REQUIRED"


class ExecuteAsTradeError(Exception):
    def __init__(self, code: ExecuteAsTradeErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_uuid(self) -> UUID: ...


@dataclass(frozen=True, slots=True)
class ExecuteAsTradeResult:
    trade_id: UUID
    trade_link_id: UUID
    replayed: bool


def request_fingerprint(
    *,
    observation_id: UUID,
    quantity: int,
    price_per_unit: Decimal,
    executed_at: datetime,
) -> str:
    payload = {
        "observation_id": str(observation_id),
        "quantity": quantity,
        "price_per_unit": format(price_per_unit, "f"),
        "executed_at": executed_at.isoformat(),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ExecuteExternalObservationAsTradeService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        uow: LearningTradeLinkUnitOfWork,
        external_trade_creator: ExternalTradeCreator,
        trade_link_service: ExternalObservationTradeLinkService,
        clock: Clock,
        id_factory: IdFactory,
    ) -> None:
        self._session = session
        self._uow = uow
        self._external_trade_creator = external_trade_creator
        self._trade_link_service = trade_link_service
        self._clock = clock
        self._id_factory = id_factory

    async def execute(
        self,
        *,
        workspace_id: UUID,
        observation_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor_id: UUID,
        idempotency_key: str,
    ) -> ExecuteAsTradeResult:
        fingerprint = request_fingerprint(
            observation_id=observation_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
        )

        existing = await self._uow.idempotency_records.get(
            workspace_id,
            COMMAND_TYPE,
            idempotency_key,
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise ExecuteAsTradeError(
                    ExecuteAsTradeErrorCode.IDEMPOTENCY_KEY_REUSED,
                    "idempotency key was already used for another request",
                )
            if existing.status is IdempotencyStatus.SUCCEEDED:
                if existing.result_id is None:
                    raise RuntimeError("succeeded idempotency record has no result")
                link = await self._find_link_for_trade(
                    workspace_id=workspace_id,
                    observation_id=observation_id,
                    trade_id=existing.result_id,
                )
                if link is None:
                    raise RuntimeError("idempotency result trade has no TradeLink")
                return ExecuteAsTradeResult(
                    trade_id=existing.result_id,
                    trade_link_id=link,
                    replayed=True,
                )
            if existing.status is IdempotencyStatus.IN_PROGRESS:
                raise ExecuteAsTradeError(
                    ExecuteAsTradeErrorCode.IDEMPOTENCY_IN_PROGRESS,
                    "idempotent command is already in progress",
                )
            raise ExecuteAsTradeError(
                ExecuteAsTradeErrorCode.IDEMPOTENCY_FAILED_FINAL,
                existing.error_code or "idempotent command failed finally",
            )

        record = IdempotencyRecord(
            id=self._id_factory.new_uuid(),
            workspace_id=workspace_id,
            command_type=COMMAND_TYPE,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            status=IdempotencyStatus.IN_PROGRESS,
            created_at=self._clock.now(),
        )
        await self._uow.idempotency_records.add(record)
        await self._session.flush()

        locked = await self._uow.external_observations.lock(
            workspace_id,
            observation_id,
        )
        if not locked:
            raise ExecuteAsTradeError(
                ExecuteAsTradeErrorCode.EXTERNAL_OBSERVATION_NOT_FOUND,
                "external observation not found",
            )

        source = await self._uow.external_observation_versions.get_current(observation_id)
        if source is None:
            raise ExecuteAsTradeError(
                ExecuteAsTradeErrorCode.EXTERNAL_OBSERVATION_SOURCE_NOT_FOUND,
                "current external observation source not found",
            )
        if source.product_id is None:
            raise ExecuteAsTradeError(
                ExecuteAsTradeErrorCode.EXTERNAL_OBSERVATION_PRODUCT_REQUIRED,
                "execute-as-trade requires a concrete product",
            )

        trade, _, _ = await self._external_trade_creator.create(
            workspace_id=workspace_id,
            product_id=source.product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
            actor_id=actor_id,
        )

        link_version = await self._trade_link_service.create(
            workspace_id=workspace_id,
            external_observation_id=observation_id,
            trade_id=trade.id,
            actor_id=actor_id,
        )

        await self._uow.idempotency_records.mark_succeeded(
            record_id=record.id,
            result_type=RESULT_TYPE,
            result_id=trade.id,
            completed_at=self._clock.now(),
        )
        await self._session.flush()

        return ExecuteAsTradeResult(
            trade_id=trade.id,
            trade_link_id=link_version.external_observation_trade_link_id,
            replayed=False,
        )

    async def _find_link_for_trade(
        self,
        *,
        workspace_id: UUID,
        observation_id: UUID,
        trade_id: UUID,
    ) -> UUID | None:
        links = await self._uow.external_observation_trade_links.list_for_observation(
            workspace_id,
            observation_id,
        )
        for link in links:
            version = await self._uow.external_observation_trade_link_versions.get_current(link.id)
            if version is not None and version.trade_id == trade_id:
                return link.id
        return None
