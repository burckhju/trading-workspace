from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.errors import InvalidProviderInstrumentMapping
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.persistence.mapping import mapping_to_domain, mapping_to_model
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel


def _mapping(*, listing_id=None, market_data_instrument_id=None) -> ProviderInstrumentMapping:
    now = datetime.now(UTC)
    return ProviderInstrumentMapping(
        id=uuid4(),
        workspace_id=uuid4(),
        listing_id=listing_id,
        provider=MarketDataProvider.EODHD,
        provider_symbol="dax.indx",
        provider_exchange_code="indx",
        status=MappingStatus.DISABLED,
        validated_at=None,
        validation_message=None,
        created_at=now,
        updated_at=now,
        version=1,
        market_data_instrument_id=market_data_instrument_id,
    )


def test_provider_mapping_requires_internal_owner() -> None:
    with pytest.raises(InvalidProviderInstrumentMapping):
        _mapping()


def test_provider_mapping_allows_instrument_only_owner() -> None:
    instrument_id = uuid4()
    value = _mapping(market_data_instrument_id=instrument_id)
    assert value.listing_id is None
    assert value.market_data_instrument_id == instrument_id


def test_provider_mapping_orm_is_expand_phase_compatible() -> None:
    table = ProviderInstrumentMappingModel.__table__
    constraint_names = {constraint.name for constraint in table.constraints}
    index_names = {index.name for index in table.indexes}

    assert table.c.listing_id.nullable is True
    assert table.c.market_data_instrument_id.nullable is True
    assert "ck_provider_instrument_mappings_internal_owner" in constraint_names
    assert "uq_provider_instrument_mappings_provider_listing" in constraint_names
    assert "uq_provider_instrument_mappings_provider_instrument" in constraint_names
    assert "ix_provider_instrument_mappings_workspace_instrument" in index_names


def test_provider_mapping_conversion_preserves_neutral_identity() -> None:
    listing_id = uuid4()
    instrument_id = uuid4()
    value = _mapping(listing_id=listing_id, market_data_instrument_id=instrument_id)

    model = mapping_to_model(value)
    restored = mapping_to_domain(model)

    assert restored.listing_id == listing_id
    assert restored.market_data_instrument_id == instrument_id
