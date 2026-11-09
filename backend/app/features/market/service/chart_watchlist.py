"""Workspace-wide activation and resumable setup of a reviewed chart universe."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market.persistence.chart_watchlist import (
    ChartWatchlistMemberModel,
    ChartWatchlistModel,
)
from app.features.market.persistence.models import WorkspaceModel
from app.features.market.service.chart_watchlist_catalog import (
    ChartWatchlistCatalog,
    ChartWatchlistDefinition,
    bundled_chart_watchlist_catalog,
)
from app.features.market.service.chart_watchlist_contracts import (
    ChartWatchlistError,
    ChartWatchlistItemResponse,
    ChartWatchlistResponse,
)
from app.features.market.service.chart_watchlist_setup import (
    ChartEtfDiscovery,
    ChartWatchlistSetup,
    EtfResolverFactory,
    ReferenceServiceFactory,
)
from app.features.market.service.chart_watchlist_state import (
    ChartWatchlistStateReader,
    preview_item,
)
from app.features.market.service.types import Actor
from app.features.market_data.service.errors import MarketDataError
from app.features.market_data.service.reference_market_data import (
    ReferenceMarketDataService,
)


class ChartWatchlistService:
    def __init__(
        self,
        session: AsyncSession,
        workspace_id: UUID,
        *,
        catalog: ChartWatchlistCatalog | None = None,
        etf_discovery: ChartEtfDiscovery | None = None,
        etf_resolver_factory: EtfResolverFactory | None = None,
        reference_service: ReferenceMarketDataService | None = None,
        reference_service_factory: ReferenceServiceFactory | None = None,
    ) -> None:
        self._session = session
        self._workspace_id = workspace_id
        self._catalog = catalog or bundled_chart_watchlist_catalog()
        self._reader = ChartWatchlistStateReader(session, workspace_id)
        self._setup = ChartWatchlistSetup(
            session,
            workspace_id,
            etf_discovery=etf_discovery,
            etf_resolver_factory=etf_resolver_factory,
            reference_service=reference_service,
            reference_service_factory=reference_service_factory,
        )

    async def read(self) -> ChartWatchlistResponse:
        activation = await self._session.get(ChartWatchlistModel, self._workspace_id)
        if activation is None:
            return ChartWatchlistResponse(
                catalog_version=self._catalog.catalog_version,
                name=self._catalog.name,
                enabled=False,
                items=tuple(preview_item(item) for item in self._catalog.items),
            )
        return ChartWatchlistResponse(
            catalog_version=activation.catalog_version,
            name=activation.name,
            enabled=True,
            items=await self._reader.read(await self._members()),
        )

    async def activate(
        self, *, catalog_version: str, confirmed: bool, actor: Actor
    ) -> ChartWatchlistResponse:
        if confirmed is not True:
            raise ChartWatchlistError("CHART_WATCHLIST_CONFIRMATION_REQUIRED", status_code=422)
        if catalog_version != self._catalog.catalog_version:
            raise ChartWatchlistError("CHART_WATCHLIST_CATALOG_VERSION_MISMATCH")
        workspace = await self._session.scalar(
            select(WorkspaceModel.id)
            .where(WorkspaceModel.id == self._workspace_id)
            .with_for_update()
        )
        if workspace is None:
            raise ChartWatchlistError("WORKSPACE_NOT_FOUND", status_code=404)
        current = await self._session.get(
            ChartWatchlistModel, self._workspace_id, populate_existing=True
        )
        if current is not None:
            if (
                current.catalog_version != self._catalog.catalog_version
                or current.catalog_checksum != self._catalog.checksum
            ):
                raise ChartWatchlistError("CHART_WATCHLIST_CATALOG_CONFLICT")
            await self._session.commit()
            return await self.read()
        self._session.add(
            ChartWatchlistModel(
                workspace_id=self._workspace_id,
                catalog_version=self._catalog.catalog_version,
                catalog_checksum=self._catalog.checksum,
                name=self._catalog.name,
                activated_at=datetime.now(UTC),
                activated_by=actor.id,
                activated_by_name=actor.display_name,
            )
        )
        await self._session.flush()
        self._session.add_all(
            [
                ChartWatchlistMemberModel(
                    workspace_id=self._workspace_id,
                    code=definition.code,
                    kind=definition.kind,
                    ordinal=index,
                    definition=definition.model_dump(mode="json"),
                )
                for index, definition in enumerate(self._catalog.items)
            ]
        )
        await self._session.commit()
        return await self.read()

    async def list_pending_setup(self) -> tuple[ChartWatchlistItemResponse, ...]:
        members = tuple(row for row in await self._members() if row.setup_completed_at is None)
        return await self._reader.read(members)

    async def configure_item(self, code: str, actor: Actor) -> ChartWatchlistItemResponse:
        member = await self._member(code)
        # Even a stale queued job re-reads current owner identity and lifecycle facts.
        current = (await self._reader.read((member,)))[0]
        if member.setup_completed_at is not None:
            # A later local deactivation is not a new request to set the member up.
            return current
        definition = ChartWatchlistDefinition.model_validate(member.definition)
        member.last_attempt_at = datetime.now(UTC)
        member.last_attempt_reason = None
        await self._session.commit()
        try:
            binding = await self._setup.configure(member, definition, actor)
        except ChartWatchlistError as error:
            await self._record_failure(code, error.code)
        except MarketDataError as error:
            await self._record_failure(code, error.code)
            # Keep the released scheduler's retry/budget handling and backoff semantics.
            raise
        except ApplicationError as error:
            await self._record_failure(code, error.code)
        except ValueError as error:
            reason = str(error)
            await self._record_failure(
                code,
                (
                    reason
                    if re.fullmatch(r"[A-Z][A-Z0-9_]{2,119}", reason)
                    else "PROVIDER_IDENTITY_VERIFICATION_FAILED"
                ),
            )
        except SQLAlchemyError:
            await self._record_failure(code, "SETUP_CONCURRENT_MODIFICATION")
            raise
        else:
            member = await self._member(code)
            member.verified_mapping_id = binding.id
            member.verified_mapping_version = binding.version
            member.verified_provider_symbol = binding.provider_symbol
            member.verified_provider_exchange_code = binding.provider_exchange_code
            member.setup_completed_at = datetime.now(UTC)
            state = (await self._reader.read((member,)))[0]
            if state.setup_status == "CONFIGURED":
                member.last_attempt_reason = None
                await self._session.commit()
            else:
                await self._record_failure(code, state.setup_reason or "SETUP_OWNER_NOT_READY")
        return (await self._reader.read((await self._member(code),)))[0]

    async def _members(self) -> tuple[ChartWatchlistMemberModel, ...]:
        return tuple(
            await self._session.scalars(
                select(ChartWatchlistMemberModel)
                .where(ChartWatchlistMemberModel.workspace_id == self._workspace_id)
                .order_by(ChartWatchlistMemberModel.ordinal)
            )
        )

    async def _member(self, code: str) -> ChartWatchlistMemberModel:
        member = await self._session.get(
            ChartWatchlistMemberModel,
            (self._workspace_id, code),
            populate_existing=True,
        )
        if member is None:
            raise ChartWatchlistError("CHART_WATCHLIST_MEMBER_NOT_ACTIVATED", status_code=404)
        return member

    async def _record_failure(self, code: str, reason: str) -> None:
        await self._session.rollback()
        member = await self._member(code)
        member.last_attempt_reason = reason
        await self._session.commit()
