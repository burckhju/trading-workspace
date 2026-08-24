from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.learning.application.ports import ProductContext, TradeContext
from app.features.learning.application.trade_link_projection_service import (
    TradeLinkCurrentSourceCompatibility,
    TradeLinkProjectionService,
    TradeLinkSourceState,
)
from app.features.learning.domain import (
    ExternalObservationRecordingMethod,
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
    ExternalObservationVersion,
    TradeLinkChangeReason,
    TradeLinkStatus,
)
from app.features.trade_position.domain.enums import TradeOrigin

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Repo:
    def __init__(self, *, value=None, current=None) -> None:
        self.value = value
        self.current = current

    async def get(self, *args):
        del args
        return self.value

    async def get_current(self, *args):
        del args
        return self.current


class FakeUow:
    def __init__(self, *, link, version, source) -> None:
        self.external_observation_trade_links = Repo(value=link)
        self.external_observation_trade_link_versions = Repo(current=version)
        self.external_observation_versions = Repo(current=source)


class TradeReader:
    def __init__(self, trade) -> None:
        self.trade = trade

    async def get(self, **kwargs):
        del kwargs
        return self.trade


class ProductReader:
    def __init__(self, product) -> None:
        self.product = product

    async def get(self, **kwargs):
        del kwargs
        return self.product


def _source(observation_id, product_id, underlying_id, version_id):
    return ExternalObservationVersion(
        id=version_id,
        external_observation_id=observation_id,
        version=2,
        underlying_id=underlying_id,
        product_id=product_id,
        source_type="MANUAL",
        source_name="projection",
        external_reference=None,
        observed_at=NOW,
        recorded_at=NOW,
        imported_at=None,
        recording_method=ExternalObservationRecordingMethod.MANUAL,
        import_row_id=None,
        source_metadata=None,
        supersedes_version_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_projection_marks_current_source_and_product_compatible() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    link_id = uuid4()
    current_source_id = uuid4()
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
    version = ExternalObservationTradeLinkVersion(
        id=link.current_version_id,
        external_observation_trade_link_id=link_id,
        version=2,
        external_observation_version_id=current_source_id,
        trade_id=trade_id,
        status=TradeLinkStatus.ACTIVE,
        change_reason=TradeLinkChangeReason.SOURCE_REVALIDATED,
        created_at=NOW,
        created_by=uuid4(),
        supersedes_version_id=uuid4(),
    )
    source = _source(
        observation_id,
        product_id,
        uuid4(),
        current_source_id,
    )

    projection = await TradeLinkProjectionService(
        uow=FakeUow(link=link, version=version, source=source),
        trade_reader=TradeReader(
            TradeContext(
                workspace_id=workspace_id,
                trade_id=trade_id,
                origin=TradeOrigin.EXTERNAL,
                product_id=product_id,
            )
        ),
        product_reader=ProductReader(None),
    ).get(
        workspace_id=workspace_id,
        trade_link_id=link_id,
    )

    assert projection is not None
    assert projection.source_state is TradeLinkSourceState.CURRENT_SOURCE
    assert projection.current_source_compatibility is TradeLinkCurrentSourceCompatibility.COMPATIBLE


@pytest.mark.asyncio
async def test_projection_marks_superseded_source_and_underlying_incompatible() -> None:
    workspace_id = uuid4()
    observation_id = uuid4()
    link_id = uuid4()
    trade_id = uuid4()
    trade_product_id = uuid4()

    link = ExternalObservationTradeLink(
        id=link_id,
        workspace_id=workspace_id,
        external_observation_id=observation_id,
        current_version_id=uuid4(),
        created_at=NOW,
        created_by=uuid4(),
    )
    version = ExternalObservationTradeLinkVersion(
        id=link.current_version_id,
        external_observation_trade_link_id=link_id,
        version=1,
        external_observation_version_id=uuid4(),
        trade_id=trade_id,
        status=TradeLinkStatus.ACTIVE,
        change_reason=TradeLinkChangeReason.INITIAL_LINK,
        created_at=NOW,
        created_by=uuid4(),
    )
    source = _source(
        observation_id,
        None,
        uuid4(),
        uuid4(),
    )

    projection = await TradeLinkProjectionService(
        uow=FakeUow(link=link, version=version, source=source),
        trade_reader=TradeReader(
            TradeContext(
                workspace_id=workspace_id,
                trade_id=trade_id,
                origin=TradeOrigin.EXTERNAL,
                product_id=trade_product_id,
            )
        ),
        product_reader=ProductReader(
            ProductContext(
                product_id=trade_product_id,
                underlying_id=uuid4(),
            )
        ),
    ).get(
        workspace_id=workspace_id,
        trade_link_id=link_id,
    )

    assert projection is not None
    assert projection.source_state is TradeLinkSourceState.SOURCE_SUPERSEDED
    assert (
        projection.current_source_compatibility is TradeLinkCurrentSourceCompatibility.INCOMPATIBLE
    )
