"""Read/query service for FT-012 Learning TradeLinks."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.features.learning.application.trade_link_projection_service import (
    TradeLinkCurrentSourceCompatibility,
    TradeLinkProjection,
    TradeLinkProjectionService,
    TradeLinkSourceState,
)
from app.features.learning.domain import ExternalObservationTradeLinkVersion
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork


@dataclass(frozen=True, slots=True)
class TradeLinkHistoryEntry:
    version: ExternalObservationTradeLinkVersion
    source_state: TradeLinkSourceState
    current_source_compatibility: TradeLinkCurrentSourceCompatibility


class TradeLinkQueryService:
    def __init__(
        self,
        *,
        uow: LearningTradeLinkUnitOfWork,
        projection_service: TradeLinkProjectionService,
    ) -> None:
        self._uow = uow
        self._projection_service = projection_service

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
    ) -> TradeLinkProjection | None:
        return await self._projection_service.get(
            workspace_id=workspace_id,
            trade_link_id=trade_link_id,
        )

    async def list_for_observation(
        self,
        *,
        workspace_id: UUID,
        observation_id: UUID,
    ) -> tuple[TradeLinkProjection, ...]:
        links = await self._uow.external_observation_trade_links.list_for_observation(
            workspace_id,
            observation_id,
        )
        result: list[TradeLinkProjection] = []
        for link in links:
            projection = await self._projection_service.get(
                workspace_id=workspace_id,
                trade_link_id=link.id,
            )
            if projection is not None:
                result.append(projection)
        return tuple(result)

    async def history(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
    ) -> tuple[TradeLinkHistoryEntry, ...] | None:
        link = await self._uow.external_observation_trade_links.get(
            workspace_id,
            trade_link_id,
        )
        if link is None:
            return None

        current_source = await self._uow.external_observation_versions.get_current(
            link.external_observation_id
        )
        if current_source is None:
            return None

        current_projection = await self._projection_service.get(
            workspace_id=workspace_id,
            trade_link_id=trade_link_id,
        )
        if current_projection is None:
            return None

        versions = await self._uow.external_observation_trade_link_versions.list_for_link(
            trade_link_id
        )
        return tuple(
            TradeLinkHistoryEntry(
                version=version,
                source_state=(
                    TradeLinkSourceState.CURRENT_SOURCE
                    if version.external_observation_version_id == current_source.id
                    else TradeLinkSourceState.SOURCE_SUPERSEDED
                ),
                current_source_compatibility=(current_projection.current_source_compatibility),
            )
            for version in versions
        )
