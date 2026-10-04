from dataclasses import replace
from types import SimpleNamespace as Obj
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from tests.unit.backend.features.analysis.test_time_series import DAY, END, NOW, identity

from app.features.market.persistence.chart_context import SqlAlchemyChartContextReader
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider, QualityStatus
from app.features.market_data.persistence.time_series import SqlAlchemyTimeSeriesReader


class Rows(list):
    def all(self):
        return self

    def one_or_none(self):
        return self[0] if self else None


def session():
    return Obj(
        execute=AsyncMock(return_value=Rows()),
        scalars=AsyncMock(return_value=Rows()),
        scalar=AsyncMock(),
        add=Mock(),
        commit=AsyncMock(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case,expected",
    [
        ("valid", "CONFIGURED"),
        ("inactive", "INACTIVE_SECTOR"),
        ("missing", "MISSING_REFERENCE"),
        ("ambiguous", "AMBIGUOUS_REFERENCE"),
        ("quality", "INSUFFICIENT_ASSIGNMENT_QUALITY"),
        ("inactive_ref", "INACTIVE_REFERENCE"),
        ("proxy_ambiguous", "AMBIGUOUS_PROXY"),
        ("proxy_quality", "INSUFFICIENT_PROXY_QUALITY"),
        ("stock_proxy", "PROXY_IS_NOT_ETF"),
    ],
)
async def test_matrix_explains_ambiguous_or_unusable_assignments(case, expected):
    db = session()
    reference = identity("INDEX", reference_id=uuid4())
    if case == "inactive_ref":
        reference = replace(reference, active=False)
    sector = Obj(
        id=uuid4(),
        name="Energy",
        code="10",
        classification_system="GICS",
        classification_version="test",
        active=case != "inactive",
    )
    assignment = Obj(
        sector_id=sector.id,
        market_reference_id=reference.reference_id,
        quality_status="INSUFFICIENT" if case == "quality" else "GOOD",
    )
    proxy = Obj(
        market_reference_id=reference.reference_id,
        listing_id=uuid4(),
        quality_status="INSUFFICIENT" if case == "proxy_quality" else "GOOD",
    )
    db.scalars.side_effect = [
        Rows([sector]),
        Rows([] if case == "missing" else [assignment] * (2 if case == "ambiguous" else 1)),
        Rows([proxy] * (2 if case == "proxy_ambiguous" else 1)),
    ]
    reader = SqlAlchemyChartContextReader(db)
    reader.references = AsyncMock(return_value=(reference,))
    reader.resolve = AsyncMock(return_value=identity("STOCK" if case == "stock_proxy" else "ETF"))
    result = await reader.sectors(uuid4(), DAY)
    assert len(result) == 1 and result[0].status == expected
    assert result[0].setup_url.endswith(str(sector.id))
    statement = str(db.scalars.await_args_list[1].args[0])
    assert (
        "workspace_id" in statement and "valid_from <=" in statement and "valid_to >=" in statement
    )


@pytest.mark.asyncio
async def test_reader_bounds_query_and_preserves_provenance_without_writes():
    db = session()
    owner, workspace = uuid4(), uuid4()
    db.scalars.return_value = Rows(
        [
            Obj(
                trading_date=DAY,
                close=100,
                adjusted_close=None,
                currency="USD",
                provider=MarketDataProvider.EODHD,
                provider_symbol="TEST",
                retrieved_at=NOW,
                source_updated_at=None,
                quality_status=QualityStatus.VALID,
                warnings="first\nsecond",
            )
        ]
    )
    reader = SqlAlchemyTimeSeriesReader(db)
    values = await reader.observations(workspace, owner, DAY, END)
    assert values[0].warnings == ("first", "second")
    statement = db.scalars.await_args.args[0]
    assert statement._limit_clause.value == 10001
    assert "BETWEEN" in str(statement) and "workspace_id" in str(statement)
    db.execute.return_value = Rows([(owner, 2, DAY, END)])
    assert (await reader.coverage(workspace, (owner,), END))[owner].count == 2
    assert await reader.coverage(workspace, (), END) == {}
    db.commit.assert_not_awaited()
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_series_basis_requires_current_active_index_mapping_and_evidence():
    db = session()
    service = TopDownReferenceAdministrationService(db)
    service._require_reference = AsyncMock()
    kwargs = dict(
        workspace_id=uuid4(),
        market_reference_id=uuid4(),
        mapping_id=uuid4(),
        mapping_version=1,
        return_basis="PRICE_INDEX",
        source_url="https://example.test/index",
        actor="Test",
    )
    db.scalar.return_value = Obj(
        version=1, status=MappingStatus.ACTIVE, provider_exchange_code="INDX"
    )
    result = await service.confirm_series_basis(**kwargs)
    assert result.mapping_version == 1 and result.confirmed_by == "Test"
    db.commit.assert_awaited_once()
    for patch in (
        {"return_basis": "UNKNOWN"},
        {"source_url": "http://example.test"},
        {"source_url": "https://user:secret@example.test"},
        {"mapping_version": 2},
    ):
        with pytest.raises(ValueError):
            await service.confirm_series_basis(**(kwargs | patch))
    db.scalar.return_value.provider_exchange_code = "US"
    with pytest.raises(ValueError, match="ETFs need"):
        await service.confirm_series_basis(**kwargs)
    db.scalar.return_value = None
    with pytest.raises(ValueError, match="reload"):
        await service.confirm_series_basis(**kwargs)
