"""Cross-feature ports consumed by FT-012 Learning application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.features.trade_position.domain.enums import TradeOrigin


@dataclass(frozen=True, slots=True)
class TradeContext:
    workspace_id: UUID
    trade_id: UUID
    origin: TradeOrigin
    product_id: UUID


@dataclass(frozen=True, slots=True)
class ProductContext:
    product_id: UUID
    underlying_id: UUID


class TradeReader(Protocol):
    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> TradeContext | None: ...


class ProductReader(Protocol):
    async def get(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContext | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_uuid(self) -> UUID: ...
