"""Tests for SQLAlchemy-backed EODHD read ports."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.providers.eodhd.persistence import (
    SqlAlchemyListingCurrencyReader,
    SqlAlchemyMappingReader,
)


class FakeDatabase:
    def __init__(self, scalar_result: object) -> None:
        self.session = AsyncMock()
        self.session.scalar.return_value = scalar_result

    @asynccontextmanager
    async def session_context(self):
        yield self.session


def test_mapping_reader_returns_domain_value() -> None:
    workspace_id = uuid4()
    mapping_id = uuid4()
    now = datetime.now(UTC)
    model = ProviderInstrumentMappingModel(
        id=mapping_id,
        workspace_id=workspace_id,
        listing_id=uuid4(),
        provider=MarketDataProvider.EODHD,
        provider_symbol="AAPL",
        provider_exchange_code="US",
        status=MappingStatus.ACTIVE,
        validated_at=now,
        validation_message=None,
        created_at=now,
        updated_at=now,
        version=1,
    )
    database = FakeDatabase(model)

    result = asyncio.run(
        SqlAlchemyMappingReader(database).get_mapping(workspace_id, mapping_id)  # type: ignore[arg-type]
    )

    assert result is not None
    assert result.id == mapping_id
    assert result.provider_symbol == "AAPL"


def test_currency_reader_returns_ft001_currency_code() -> None:
    database = FakeDatabase("EUR")

    result = asyncio.run(
        SqlAlchemyListingCurrencyReader(database).get_currency(uuid4(), uuid4())  # type: ignore[arg-type]
    )

    assert result == "EUR"
