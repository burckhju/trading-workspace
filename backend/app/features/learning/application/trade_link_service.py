"""ExternalObservationTradeLink application service."""

from __future__ import annotations

from enum import StrEnum
from typing import NoReturn
from uuid import UUID

from app.features.learning.application.ports import (
    Clock,
    IdFactory,
    ProductReader,
    TradeReader,
)
from app.features.learning.domain import (
    ExternalObservation,
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
    ExternalObservationVersion,
    TradeLinkChangeReason,
    TradeLinkStatus,
)
from app.features.learning.persistence.unit_of_work import LearningTradeLinkUnitOfWork
from app.features.trade_position.domain.enums import TradeOrigin


class TradeLinkErrorCode(StrEnum):
    TRADE_LINK_NOT_FOUND = "TRADE_LINK_NOT_FOUND"
    TRADE_LINK_TARGET_NOT_FOUND = "TRADE_LINK_TARGET_NOT_FOUND"
    TRADE_LINK_TARGET_NOT_EXTERNAL = "TRADE_LINK_TARGET_NOT_EXTERNAL"
    TRADE_LINK_WORKSPACE_MISMATCH = "TRADE_LINK_WORKSPACE_MISMATCH"
    TRADE_LINK_PRODUCT_MISMATCH = "TRADE_LINK_PRODUCT_MISMATCH"
    TRADE_LINK_UNDERLYING_MISMATCH = "TRADE_LINK_UNDERLYING_MISMATCH"
    TRADE_LINK_ACTIVE_PAIR_ALREADY_EXISTS = "TRADE_LINK_ACTIVE_PAIR_ALREADY_EXISTS"
    TRADE_LINK_INVALID_TRANSITION = "TRADE_LINK_INVALID_TRANSITION"
    TRADE_LINK_SOURCE_NOT_CURRENT = "TRADE_LINK_SOURCE_NOT_CURRENT"
    TRADE_LINK_SOURCE_INCOMPATIBLE = "TRADE_LINK_SOURCE_INCOMPATIBLE"


class TradeLinkServiceError(RuntimeError):
    def __init__(self, code: TradeLinkErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class ExternalObservationTradeLinkService:
    def __init__(
        self,
        *,
        uow: LearningTradeLinkUnitOfWork,
        trade_reader: TradeReader,
        product_reader: ProductReader,
        clock: Clock,
        id_factory: IdFactory,
    ) -> None:
        self._uow = uow
        self._trade_reader = trade_reader
        self._product_reader = product_reader
        self._clock = clock
        self._id_factory = id_factory

    async def create(
        self,
        *,
        workspace_id: UUID,
        external_observation_id: UUID,
        trade_id: UUID,
        actor_id: UUID,
    ) -> ExternalObservationTradeLinkVersion:
        async with self._uow:
            observation = await self._lock_observation(
                workspace_id=workspace_id,
                external_observation_id=external_observation_id,
            )
            current_source = await self._current_source(external_observation_id)
            await self._validate_active_target(
                workspace_id=workspace_id,
                external_observation_id=external_observation_id,
                current_source=current_source,
                trade_id=trade_id,
                exclude_link_id=None,
            )

            now = self._clock.now()
            link_id = self._id_factory.new_uuid()
            version_id = self._id_factory.new_uuid()

            link = ExternalObservationTradeLink(
                id=link_id,
                workspace_id=observation.workspace_id,
                external_observation_id=observation.id,
                current_version_id=version_id,
                created_at=now,
                created_by=actor_id,
            )
            version = ExternalObservationTradeLinkVersion(
                id=version_id,
                external_observation_trade_link_id=link_id,
                version=1,
                external_observation_version_id=current_source.id,
                trade_id=trade_id,
                status=TradeLinkStatus.ACTIVE,
                change_reason=TradeLinkChangeReason.INITIAL_LINK,
                created_at=now,
                created_by=actor_id,
            )

            await self._uow.external_observation_trade_links.add(link)
            await self._uow.external_observation_trade_link_versions.add(version)
            await self._uow.commit()
            return version

    async def correct_target(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
        trade_id: UUID,
        actor_id: UUID,
        change_note: str | None = None,
    ) -> ExternalObservationTradeLinkVersion:
        async with self._uow:
            link, current = await self._lock_link(workspace_id, trade_link_id)
            if current.status is not TradeLinkStatus.ACTIVE:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION,
                    "correct_target requires current ACTIVE link version",
                )

            await self._lock_observation(
                workspace_id=workspace_id,
                external_observation_id=link.external_observation_id,
            )
            current_source = await self._current_source(link.external_observation_id)
            await self._validate_active_target(
                workspace_id=workspace_id,
                external_observation_id=link.external_observation_id,
                current_source=current_source,
                trade_id=trade_id,
                exclude_link_id=link.id,
            )
            if trade_id == current.trade_id:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION,
                    "correct_target requires a different trade",
                )

            return await self._append_and_advance(
                workspace_id=workspace_id,
                link=link,
                current=current,
                trade_id=trade_id,
                source_version_id=current_source.id,
                status=TradeLinkStatus.ACTIVE,
                reason=TradeLinkChangeReason.TARGET_CORRECTED,
                actor_id=actor_id,
                change_note=change_note,
            )

    async def retract(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
        actor_id: UUID,
        change_note: str | None = None,
    ) -> ExternalObservationTradeLinkVersion:
        async with self._uow:
            link, current = await self._lock_link(workspace_id, trade_link_id)
            if current.status is not TradeLinkStatus.ACTIVE:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION,
                    "retract requires current ACTIVE link version",
                )

            return await self._append_and_advance(
                workspace_id=workspace_id,
                link=link,
                current=current,
                trade_id=current.trade_id,
                source_version_id=current.external_observation_version_id,
                status=TradeLinkStatus.RETRACTED,
                reason=TradeLinkChangeReason.LINK_RETRACTED,
                actor_id=actor_id,
                change_note=change_note,
            )

    async def reactivate(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
        actor_id: UUID,
        trade_id: UUID | None = None,
        change_note: str | None = None,
    ) -> ExternalObservationTradeLinkVersion:
        async with self._uow:
            link, current = await self._lock_link(workspace_id, trade_link_id)
            if current.status is not TradeLinkStatus.RETRACTED:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION,
                    "reactivate requires current RETRACTED link version",
                )

            await self._lock_observation(
                workspace_id=workspace_id,
                external_observation_id=link.external_observation_id,
            )
            current_source = await self._current_source(link.external_observation_id)
            target_trade_id = trade_id or current.trade_id
            await self._validate_active_target(
                workspace_id=workspace_id,
                external_observation_id=link.external_observation_id,
                current_source=current_source,
                trade_id=target_trade_id,
                exclude_link_id=link.id,
            )

            reason = (
                TradeLinkChangeReason.LINK_REACTIVATED_WITH_TARGET_CORRECTION
                if target_trade_id != current.trade_id
                else TradeLinkChangeReason.LINK_REACTIVATED
            )
            return await self._append_and_advance(
                workspace_id=workspace_id,
                link=link,
                current=current,
                trade_id=target_trade_id,
                source_version_id=current_source.id,
                status=TradeLinkStatus.ACTIVE,
                reason=reason,
                actor_id=actor_id,
                change_note=change_note,
            )

    async def revalidate_source(
        self,
        *,
        workspace_id: UUID,
        trade_link_id: UUID,
        actor_id: UUID,
        change_note: str | None = None,
    ) -> ExternalObservationTradeLinkVersion:
        async with self._uow:
            link, current = await self._lock_link(workspace_id, trade_link_id)
            if current.status is not TradeLinkStatus.ACTIVE:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION,
                    "revalidate_source requires current ACTIVE link version",
                )

            await self._lock_observation(
                workspace_id=workspace_id,
                external_observation_id=link.external_observation_id,
            )
            current_source = await self._current_source(link.external_observation_id)
            if current.external_observation_version_id == current_source.id:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_SOURCE_NOT_CURRENT,
                    "trade link already references the current source",
                )

            try:
                await self._validate_active_target(
                    workspace_id=workspace_id,
                    external_observation_id=link.external_observation_id,
                    current_source=current_source,
                    trade_id=current.trade_id,
                    exclude_link_id=link.id,
                )
            except TradeLinkServiceError as error:
                if error.code in {
                    TradeLinkErrorCode.TRADE_LINK_PRODUCT_MISMATCH,
                    TradeLinkErrorCode.TRADE_LINK_UNDERLYING_MISMATCH,
                }:
                    self._fail(
                        TradeLinkErrorCode.TRADE_LINK_SOURCE_INCOMPATIBLE,
                        "current source is incompatible with existing trade",
                    )
                raise

            return await self._append_and_advance(
                workspace_id=workspace_id,
                link=link,
                current=current,
                trade_id=current.trade_id,
                source_version_id=current_source.id,
                status=TradeLinkStatus.ACTIVE,
                reason=TradeLinkChangeReason.SOURCE_REVALIDATED,
                actor_id=actor_id,
                change_note=change_note,
            )

    async def _lock_observation(
        self,
        *,
        workspace_id: UUID,
        external_observation_id: UUID,
    ) -> ExternalObservation:
        locked = await self._uow.external_observations.lock(
            workspace_id,
            external_observation_id,
        )
        if not locked:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
                "external observation not found",
            )

        observation = await self._uow.external_observations.get(
            workspace_id,
            external_observation_id,
        )
        if observation is None:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
                "external observation not found",
            )
        return observation

    async def _current_source(
        self,
        external_observation_id: UUID,
    ) -> ExternalObservationVersion:
        source = await self._uow.external_observation_versions.get_current(external_observation_id)
        if source is None:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_SOURCE_NOT_CURRENT,
                "current external observation version not found",
            )
        return source

    async def _lock_link(
        self,
        workspace_id: UUID,
        trade_link_id: UUID,
    ) -> tuple[ExternalObservationTradeLink, ExternalObservationTradeLinkVersion]:
        if not await self._uow.external_observation_trade_links.lock(
            workspace_id,
            trade_link_id,
        ):
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
                "trade link not found",
            )

        link = await self._uow.external_observation_trade_links.get(
            workspace_id,
            trade_link_id,
        )
        current = await self._uow.external_observation_trade_link_versions.get_current(
            trade_link_id
        )
        if link is None or current is None:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_NOT_FOUND,
                "trade link not found",
            )
        return link, current

    async def _validate_active_target(
        self,
        *,
        workspace_id: UUID,
        external_observation_id: UUID,
        current_source: ExternalObservationVersion,
        trade_id: UUID,
        exclude_link_id: UUID | None,
    ) -> None:
        trade = await self._trade_reader.get(
            workspace_id=workspace_id,
            trade_id=trade_id,
        )
        if trade is None:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_TARGET_NOT_FOUND,
                "target trade not found",
            )
        if trade.origin is not TradeOrigin.EXTERNAL:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_TARGET_NOT_EXTERNAL,
                "target trade must have EXTERNAL origin",
            )
        if trade.workspace_id != workspace_id:
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_WORKSPACE_MISMATCH,
                "target trade belongs to a different workspace",
            )

        if current_source.product_id is not None:
            if trade.product_id != current_source.product_id:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_PRODUCT_MISMATCH,
                    "target trade product does not match current source",
                )
        else:
            product = await self._product_reader.get(
                workspace_id=workspace_id,
                product_id=trade.product_id,
            )
            if product is None or product.underlying_id != current_source.underlying_id:
                self._fail(
                    TradeLinkErrorCode.TRADE_LINK_UNDERLYING_MISMATCH,
                    "target trade product underlying does not match current source",
                )

        if await self._uow.external_observation_trade_links.exists_current_active_pair(
            external_observation_id=external_observation_id,
            trade_id=trade_id,
            exclude_link_id=exclude_link_id,
        ):
            self._fail(
                TradeLinkErrorCode.TRADE_LINK_ACTIVE_PAIR_ALREADY_EXISTS,
                "current ACTIVE Observation/Trade pair already exists",
            )

    async def _append_and_advance(
        self,
        *,
        workspace_id: UUID,
        link: ExternalObservationTradeLink,
        current: ExternalObservationTradeLinkVersion,
        trade_id: UUID,
        source_version_id: UUID,
        status: TradeLinkStatus,
        reason: TradeLinkChangeReason,
        actor_id: UUID,
        change_note: str | None,
    ) -> ExternalObservationTradeLinkVersion:
        next_version = await self._uow.external_observation_trade_link_versions.next_version_number(
            workspace_id,
            link.id,
        )
        version = ExternalObservationTradeLinkVersion(
            id=self._id_factory.new_uuid(),
            external_observation_trade_link_id=link.id,
            version=next_version,
            external_observation_version_id=source_version_id,
            trade_id=trade_id,
            status=status,
            change_reason=reason,
            created_at=self._clock.now(),
            created_by=actor_id,
            supersedes_version_id=current.id,
            change_note=change_note,
        )
        await self._uow.external_observation_trade_link_versions.add(version)
        await self._uow.flush()
        await self._uow.external_observation_trade_links.advance_current(
            link_id=link.id,
            expected_current_version_id=current.id,
            new_current_version_id=version.id,
        )
        await self._uow.commit()
        return version

    @staticmethod
    def _fail(code: TradeLinkErrorCode, message: str) -> NoReturn:
        raise TradeLinkServiceError(code, message)
