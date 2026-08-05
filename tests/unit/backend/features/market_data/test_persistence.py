import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql

from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import DailyPrice, ProviderInstrumentMapping
from app.features.market_data.persistence.mapping import (
    apply_daily_price,
    daily_price_to_domain,
    daily_price_to_model,
    mapping_to_domain,
    mapping_to_model,
)
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)
from app.features.market_data.persistence.repositories import (
    SqlAlchemyDailyPriceRepository,
    SqlAlchemyProviderInstrumentMappingRepository,
)
from app.features.market_data.service.unit_of_work import SqlAlchemyMarketDataUnitOfWork

NOW = datetime(2026, 8, 5, 10, tzinfo=UTC)


def _sql(statement: object) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def _price(close: str = "101") -> DailyPrice:
    return DailyPrice(
        listing_id=uuid4(),
        trading_date=date(2026, 8, 4),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal(close),
        adjusted_close=None,
        volume=None,
        currency="EUR",
        provider=MarketDataProvider.EODHD,
        provider_symbol="SIE.XETRA",
        retrieved_at=NOW,
        source_updated_at=None,
        quality_status=QualityStatus.VALID,
        warnings=("checked",),
    )


def test_models_register_constraints_and_delete_rules() -> None:
    mapping = ProviderInstrumentMappingModel.__table__
    price = DailyPriceModel.__table__
    assert {c.name for c in mapping.constraints if isinstance(c, UniqueConstraint)} >= {
        "uq_provider_instrument_mappings_provider_listing",
        "uq_provider_instrument_mappings_provider_symbol",
    }
    assert {c.name for c in price.constraints if isinstance(c, UniqueConstraint)} >= {
        "uq_daily_prices_listing_date_type"
    }
    assert len([c for c in price.constraints if isinstance(c, CheckConstraint)]) >= 9
    assert next(iter(mapping.c.listing_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(price.c.currency.foreign_keys)).ondelete == "RESTRICT"
    assert ProviderInstrumentMappingModel.__mapper__.version_id_col is mapping.c.version


def test_mapping_round_trip_preserves_domain_value() -> None:
    value = ProviderInstrumentMapping(
        id=uuid4(),
        workspace_id=uuid4(),
        listing_id=uuid4(),
        provider=MarketDataProvider.EODHD,
        provider_symbol="sie.xetra",
        provider_exchange_code="xetra",
        status=MappingStatus.ACTIVE,
        validated_at=NOW,
        validation_message=None,
        created_at=NOW,
        updated_at=NOW,
        version=1,
    )
    assert mapping_to_domain(mapping_to_model(value)) == value


def test_daily_price_round_trip_and_change_detection() -> None:
    value = _price()
    model = daily_price_to_model(value, workspace_id=uuid4(), price_id=uuid4(), now=NOW)
    assert daily_price_to_domain(model) == value
    assert apply_daily_price(model, value, now=NOW) is False
    changed = _price("100.5")
    object.__setattr__(changed, "listing_id", value.listing_id)
    assert apply_daily_price(model, changed, now=NOW) is True
    assert model.close == Decimal("100.5")


def test_repository_queries_are_workspace_scoped_and_ordered() -> None:
    session = Mock()
    session.scalar = AsyncMock(return_value=None)
    repository = SqlAlchemyDailyPriceRepository(session)
    asyncio.run(repository.latest(uuid4(), uuid4(), date(2026, 8, 4)))
    sql = _sql(session.scalar.await_args.args[0])
    assert "daily_prices.workspace_id" in sql
    assert "daily_prices.listing_id" in sql
    assert "daily_prices.trading_date <=" in sql
    assert "ORDER BY daily_prices.trading_date DESC" in sql


def test_repositories_do_not_commit() -> None:
    session = Mock()
    session.add = Mock()
    session.flush = AsyncMock()
    repo = SqlAlchemyProviderInstrumentMappingRepository(session)
    asyncio.run(repo.add(Mock()))
    asyncio.run(repo.flush())
    assert not hasattr(repo, "commit")


def test_unit_of_work_owns_commit_and_rolls_back_on_error() -> None:
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    uow = SqlAlchemyMarketDataUnitOfWork(session)
    asyncio.run(uow.commit())
    asyncio.run(uow.__aexit__(ValueError, ValueError("x"), None))
    session.commit.assert_awaited_once()
    session.rollback.assert_awaited_once()
