from datetime import UTC, datetime
from uuid import uuid4

from app.features.product.api.router import ListingRequest, ListingResponse
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel


def test_listing_request_allows_venue_identity_without_symbol() -> None:
    request = ListingRequest(
        trading_venue_id=uuid4(),
        quotation_currency_code="EUR",
    )

    assert request.symbol is None


def test_listing_response_preserves_missing_symbol() -> None:
    response = ListingResponse(
        id=uuid4(),
        workspace_id=uuid4(),
        warrant_id=uuid4(),
        trading_venue_id=uuid4(),
        symbol=None,
        quotation_currency_code="EUR",
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    assert response.symbol is None


def test_warrant_listing_metadata_supports_symbol_less_identity() -> None:
    table = WarrantListingModel.__table__

    assert table.c.symbol.nullable is True
    assert "uq_warrant_listings_symbol_less_warrant_venue" in {
        index.name for index in table.indexes
    }
