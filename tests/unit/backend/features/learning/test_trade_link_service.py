from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.ports import ProductContext, TradeContext
from app.features.learning.application.trade_link_service import (
    ExternalObservationTradeLinkService,
    TradeLinkErrorCode,
    TradeLinkServiceError,
)
from app.features.learning.domain import (
    ExternalObservation,
    ExternalObservationRecordingMethod,
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
    ExternalObservationVersion,
    TradeLinkChangeReason,
    TradeLinkStatus,
)
from app.features.trade_position.domain.enums import TradeOrigin

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class QueueIds:
    def __init__(self, *values: UUID) -> None:
        self._values = list(values)

    def new_uuid(self) -> UUID:
        return self._values.pop(0)


class FakeTradeReader:
    def __init__(self, trade: TradeContext | None) -> None:
        self.trade = trade

    async def get(self, *, workspace_id: UUID, trade_id: UUID):
        del workspace_id, trade_id
        return self.trade


class FakeProductReader:
    def __init__(self, product: ProductContext | None) -> None:
        self.product = product

    async def get(self, *, workspace_id: UUID, product_id: UUID):
        del workspace_id, product_id
        return self.product


class FakeRepo:
    def __init__(self) -> None:
        self.added = []
        self.lock_result = True
        self.value = None
        self.current = None
        self.exists_pair = False
        self.next_number = 2
        self.advanced = None

    async def add(self, value):
        self.added.append(value)

    async def lock(self, *args):
        del args
        return self.lock_result

    async def get(self, *args):
        del args
        return self.value

    async def get_current(self, *args):
        del args
        return self.current

    async def exists_current_active_pair(self, **kwargs):
        del kwargs
        return self.exists_pair

    async def next_version_number(self, *args):
        del args
        return self.next_number

    async def advance_current(self, **kwargs):
        self.advanced = kwargs


class FakeUow:
    def __init__(self) -> None:
        self.external_observations = FakeRepo()
        self.external_observation_versions = FakeRepo()
        self.external_observation_trade_links = FakeRepo()
        self.external_observation_trade_link_versions = FakeRepo()
        self.commits = 0
        self.flushes = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        del exc_type, exc, traceback

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


def _source(
    observation_id: UUID,
    *,
    product_id: UUID | None,
    underlying_id: UUID,
    version_id: UUID | None = None,
) -> ExternalObservationVersion:
    return ExternalObservationVersion(
        id=version_id or uuid4(),
        external_observation_id=observation_id,
        version=1,
        underlying_id=underlying_id,
        product_id=product_id,
        source_type="MANUAL",
        source_name="unit",
        external_reference=None,
        observed_at=NOW,
        recorded_at=NOW,
        imported_at=None,
        recording_method=ExternalObservationRecordingMethod.MANUAL,
        import_row_id=None,
        source_metadata=None,
        supersedes_version_id=None,
        created_at=NOW,
        created_by=uuid4(),
    )


def _service(
    *,
    uow: FakeUow,
    trade: TradeContext | None,
    product: ProductContext | None,
    ids: tuple[UUID, ...],
) -> ExternalObservationTradeLinkService:
    return ExternalObservationTradeLinkService(
        uow=uow,
        trade_reader=FakeTradeReader(trade),
        product_reader=FakeProductReader(product),
        clock=FixedClock(),
        id_factory=QueueIds(*ids),
    )


@pytest.mark.asyncio
async def test_create_builds_initial_active_link_version() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    product_id = uuid4()
    underlying_id = uuid4()
    trade_id = uuid4()
    actor_id = uuid4()

    uow = FakeUow()
    uow.external_observations.value = ExternalObservation(
        id=observation_id,
        workspace_id=workspace_id,
        current_version_id=uuid4(),
        created_at=NOW,
        created_by=actor_id,
    )
    uow.external_observation_versions.current = _source(
        observation_id,
        product_id=product_id,
        underlying_id=underlying_id,
    )
    trade = TradeContext(
        workspace_id=workspace_id,
        trade_id=trade_id,
        origin=TradeOrigin.EXTERNAL,
        product_id=product_id,
    )

    result = await _service(
        uow=uow,
        trade=trade,
        product=None,
        ids=(uuid4(), uuid4()),
    ).create(
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        trade_id=trade_id,
        actor_id=actor_id,
    )

    assert result.status is TradeLinkStatus.ACTIVE
    assert result.change_reason is TradeLinkChangeReason.INITIAL_LINK
    assert result.version == 1
    assert result.trade_id == trade_id
    assert uow.commits == 1


@pytest.mark.asyncio
async def test_create_rejects_non_external_trade() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    product_id = uuid4()

    uow = FakeUow()
    uow.external_observations.value = ExternalObservation(
        id=observation_id,
        workspace_id=workspace_id,
        current_version_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )
    uow.external_observation_versions.current = _source(
        observation_id,
        product_id=product_id,
        underlying_id=uuid4(),
    )

    service = _service(
        uow=uow,
        trade=TradeContext(
            workspace_id=workspace_id,
            trade_id=uuid4(),
            origin=TradeOrigin.WORKSPACE_SELECTION,
            product_id=product_id,
        ),
        product=None,
        ids=(uuid4(), uuid4()),
    )
    with pytest.raises(TradeLinkServiceError) as exc:
        await service.create(
            workspace_id=workspace_id,
            external_observation_id=observation_id,
            trade_id=uuid4(),
            actor_id=uuid4(),
        )
    assert exc.value.code is TradeLinkErrorCode.TRADE_LINK_TARGET_NOT_EXTERNAL


@pytest.mark.asyncio
async def test_create_uses_underlying_fallback_when_source_has_no_product() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    trade_product_id = uuid4()
    underlying_id = uuid4()

    uow = FakeUow()
    uow.external_observations.value = ExternalObservation(
        id=observation_id,
        workspace_id=workspace_id,
        current_version_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )
    uow.external_observation_versions.current = _source(
        observation_id,
        product_id=None,
        underlying_id=underlying_id,
    )

    result = await _service(
        uow=uow,
        trade=TradeContext(
            workspace_id=workspace_id,
            trade_id=uuid4(),
            origin=TradeOrigin.EXTERNAL,
            product_id=trade_product_id,
        ),
        product=ProductContext(
            product_id=trade_product_id,
            underlying_id=underlying_id,
        ),
        ids=(uuid4(), uuid4()),
    ).create(
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        trade_id=uuid4(),
        actor_id=uuid4(),
    )
    assert result.change_reason is TradeLinkChangeReason.INITIAL_LINK


@pytest.mark.asyncio
async def test_duplicate_active_pair_is_rejected() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    product_id = uuid4()

    uow = FakeUow()
    uow.external_observations.value = ExternalObservation(
        id=observation_id,
        workspace_id=workspace_id,
        current_version_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )
    uow.external_observation_versions.current = _source(
        observation_id,
        product_id=product_id,
        underlying_id=uuid4(),
    )
    uow.external_observation_trade_links.exists_pair = True

    service = _service(
        uow=uow,
        trade=TradeContext(
            workspace_id=workspace_id,
            trade_id=uuid4(),
            origin=TradeOrigin.EXTERNAL,
            product_id=product_id,
        ),
        product=None,
        ids=(uuid4(), uuid4()),
    )
    with pytest.raises(TradeLinkServiceError) as exc:
        await service.create(
            workspace_id=workspace_id,
            external_observation_id=observation_id,
            trade_id=uuid4(),
            actor_id=uuid4(),
        )
    assert exc.value.code is TradeLinkErrorCode.TRADE_LINK_ACTIVE_PAIR_ALREADY_EXISTS


@pytest.mark.asyncio
async def test_retract_preserves_target_and_source() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    link_id = uuid4()
    source_id = uuid4()
    trade_id = uuid4()
    current_id = uuid4()

    link = ExternalObservationTradeLink(
        id=link_id,
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        current_version_id=current_id,
        created_at=NOW,
        created_by=uuid4(),
    )
    current = ExternalObservationTradeLinkVersion(
        id=current_id,
        external_observation_trade_link_id=link_id,
        version=1,
        external_observation_version_id=source_id,
        trade_id=trade_id,
        status=TradeLinkStatus.ACTIVE,
        change_reason=TradeLinkChangeReason.INITIAL_LINK,
        created_at=NOW,
        created_by=uuid4(),
    )

    uow = FakeUow()
    uow.external_observation_trade_links.value = link
    uow.external_observation_trade_link_versions.current = current

    result = await _service(
        uow=uow,
        trade=None,
        product=None,
        ids=(uuid4(),),
    ).retract(
        workspace_id=workspace_id,
        trade_link_id=link_id,
        actor_id=uuid4(),
    )

    assert result.status is TradeLinkStatus.RETRACTED
    assert result.change_reason is TradeLinkChangeReason.LINK_RETRACTED
    assert result.trade_id == trade_id
    assert result.external_observation_version_id == source_id


@pytest.mark.asyncio
async def test_revalidate_source_requires_superseded_source() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    link_id = uuid4()
    source_id = uuid4()
    product_id = uuid4()
    trade_id = uuid4()

    link = ExternalObservationTradeLink(
        id=link_id,
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        current_version_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )
    current = ExternalObservationTradeLinkVersion(
        id=link.current_version_id,
        external_observation_trade_link_id=link_id,
        version=1,
        external_observation_version_id=source_id,
        trade_id=trade_id,
        status=TradeLinkStatus.ACTIVE,
        change_reason=TradeLinkChangeReason.INITIAL_LINK,
        created_at=NOW,
        created_by=uuid4(),
    )

    uow = FakeUow()
    uow.external_observation_trade_links.value = link
    uow.external_observation_trade_link_versions.current = current
    uow.external_observations.value = ExternalObservation(
        id=observation_id,
        workspace_id=workspace_id,
        current_version_id=source_id,
        created_at=NOW,
        created_by=uuid4(),
    )
    uow.external_observation_versions.current = _source(
        observation_id,
        product_id=product_id,
        underlying_id=uuid4(),
        version_id=source_id,
    )

    service = _service(
        uow=uow,
        trade=TradeContext(
            workspace_id=workspace_id,
            trade_id=trade_id,
            origin=TradeOrigin.EXTERNAL,
            product_id=product_id,
        ),
        product=None,
        ids=(uuid4(),),
    )
    with pytest.raises(TradeLinkServiceError) as exc:
        await service.revalidate_source(
            workspace_id=workspace_id,
            trade_link_id=link_id,
            actor_id=uuid4(),
        )
    assert exc.value.code is TradeLinkErrorCode.TRADE_LINK_SOURCE_NOT_CURRENT
