"""Derived TradeLink read projections for FT-012 Learning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.features.learning.application.ports import ProductReader, TradeReader
from app.features.learning.domain import (
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
)
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


class TradeLinkSourceState(StrEnum):
    CURRENT_SOURCE = "CURRENT_SOURCE"
    SOURCE_SUPERSEDED = "SOURCE_SUPERSEDED"


class TradeLinkCurrentSourceCompatibility(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass(frozen=True, slots=True)
class TradeLinkProjection:
    link: ExternalObservationTradeLink
    version: ExternalObservationTradeLinkVersion
    source_state: TradeLinkSourceState
    current_source_compatibility: TradeLinkCurrentSourceCompatibility


class TradeLinkProjectionService:
    def __init__(
        self,
        *,
        uow: LearningTradeLinkUnitOfWork,
        trade_reader: TradeReader,
        product_reader: ProductReader,
    ) -> None:
        self._uow = uow
        self._trade_reader = trade_reader
        self._product_reader = product_reader

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
    ) -> TradeLinkProjection | None:
        link = await self._uow.external_observation_trade_links.get(
            workspace_id,
            trade_link_id,
        )
        if link is None:
            return None

        version = await self._uow.external_observation_trade_link_versions.get_current(
            trade_link_id
        )
        if version is None:
            return None

        current_source = await self._uow.external_observation_versions.get_current(
            link.external_observation_id
        )
        if current_source is None:
            return None

        source_state = (
            TradeLinkSourceState.CURRENT_SOURCE
            if version.external_observation_version_id == current_source.id
            else TradeLinkSourceState.SOURCE_SUPERSEDED
        )

        trade = await self._trade_reader.get(
            workspace_id=workspace_id,
            trade_id=version.trade_id,
        )
        if trade is None:
            compatibility = TradeLinkCurrentSourceCompatibility.INCOMPATIBLE
        elif current_source.product_id is not None:
            compatibility = (
                TradeLinkCurrentSourceCompatibility.COMPATIBLE
                if trade.product_id == current_source.product_id
                else TradeLinkCurrentSourceCompatibility.INCOMPATIBLE
            )
        else:
            product = await self._product_reader.get(
                workspace_id=workspace_id,
                product_id=trade.product_id,
            )
            compatibility = (
                TradeLinkCurrentSourceCompatibility.COMPATIBLE
                if (product is not None and product.underlying_id == current_source.underlying_id)
                else TradeLinkCurrentSourceCompatibility.INCOMPATIBLE
            )

        return TradeLinkProjection(
            link=link,
            version=version,
            source_state=source_state,
            current_source_compatibility=compatibility,
        )
