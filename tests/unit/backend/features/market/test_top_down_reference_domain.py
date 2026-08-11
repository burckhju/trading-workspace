from datetime import date
from uuid import uuid4

import pytest

from app.features.market.domain.top_down import (
    BenchmarkRole,
    MarketReference,
    MarketReferenceType,
    Sector,
    UnderlyingSectorAssignment,
)


def test_market_reference_is_provider_neutral_and_versioned() -> None:
    reference = MarketReference(
        id=uuid4(),
        workspace_id=uuid4(),
        code="SP500",
        name="S&P 500",
        reference_type=MarketReferenceType.INDEX,
        region="US",
        role=BenchmarkRole.BROAD_MARKET,
        reference_version="1.0",
    )
    assert reference.role is BenchmarkRole.BROAD_MARKET
    assert reference.reference_version == "1.0"


def test_sector_requires_classification_version() -> None:
    with pytest.raises(ValueError):
        Sector(uuid4(), uuid4(), "TECH", "Technology", "INTERNAL", "")


def test_sector_assignment_rejects_invalid_validity_range() -> None:
    with pytest.raises(ValueError):
        UnderlyingSectorAssignment(
            uuid4(),
            uuid4(),
            date(2026, 8, 8),
            date(2026, 8, 7),
            "manual",
            None,
            "GOOD",
        )


def test_benchmark_assignment_rejects_invalid_validity_range() -> None:
    from app.features.market.domain.top_down import UnderlyingBenchmarkAssignment

    with pytest.raises(ValueError):
        UnderlyingBenchmarkAssignment(
            uuid4(),
            uuid4(),
            BenchmarkRole.BROAD_MARKET,
            date(2026, 8, 8),
            date(2026, 8, 7),
            "manual",
            None,
            "GOOD",
        )


def test_market_reference_listing_assignment_is_historized() -> None:
    from app.features.market.domain.top_down import MarketReferenceListingAssignment

    assignment = MarketReferenceListingAssignment(
        uuid4(),
        uuid4(),
        date(2026, 8, 8),
        None,
        "manual",
        "SPX",
        "GOOD",
    )
    assert assignment.valid_to is None
