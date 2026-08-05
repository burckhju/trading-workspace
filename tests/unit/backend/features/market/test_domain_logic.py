from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.market.domain.entities import (
    Listing,
    Underlying,
    determine_quality_status,
    ensure_expected_version,
    ensure_operational_listing_invariant,
)
from app.features.market.domain.errors import (
    ConcurrentModification,
    InvalidIsin,
    InvalidWkn,
    MultiplePrimaryListings,
    NotOperationallyComplete,
    PrimaryListingRequired,
)
from app.features.market.domain.normalization import (
    normalize_code,
    normalize_isin,
    normalize_ticker,
    normalize_wkn,
)
from app.features.market.domain.enums import (
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)

NOW = datetime(2026, 8, 3, tzinfo=UTC)
LATER = datetime(2026, 8, 4, tzinfo=UTC)


def listing(*, primary: bool = True, active: bool = True) -> Listing:
    workspace_id = uuid4()
    return Listing(
        id=uuid4(), workspace_id=workspace_id, underlying_id=uuid4(),
        trading_venue_id=uuid4(), ticker=" sie ", currency_code=" eur ",
        lifecycle_status=LifecycleStatus.ACTIVE if active else LifecycleStatus.INACTIVE,
        is_primary=primary, version=1, created_at=NOW, updated_at=NOW,
    )


def underlying(*, quality: QualityStatus = QualityStatus.COMPLETE,
               lifecycle: LifecycleStatus = LifecycleStatus.ACTIVE) -> Underlying:
    return Underlying(
        id=uuid4(), workspace_id=uuid4(), type=UnderlyingType.STOCK,
        name=" Siemens AG ", isin="DE0007236101", wkn="723610",
        lifecycle_status=lifecycle, quality_status=quality, version=1,
        created_at=NOW, updated_at=NOW,
    )


def test_identifier_normalization_is_deterministic() -> None:
    assert normalize_isin(" de-0007236101 ") == "DE0007236101"
    assert normalize_wkn(" 723 610 ") == "723610"
    assert normalize_ticker(" sie ") == "SIE"
    assert normalize_code(" eur ") == "EUR"


@pytest.mark.parametrize("value", ["DE0007236102", "ABC", ""])
def test_invalid_isin_is_rejected_except_blank(value: str) -> None:
    if value == "":
        assert normalize_isin(value) is None
    else:
        with pytest.raises(InvalidIsin):
            normalize_isin(value)


def test_invalid_wkn_is_rejected() -> None:
    with pytest.raises(InvalidWkn):
        normalize_wkn("12345")


def test_listing_normalizes_values() -> None:
    item = listing()
    assert item.ticker == "SIE"
    assert item.currency_code == "EUR"


def test_exactly_one_active_primary_listing_is_required() -> None:
    ensure_operational_listing_invariant((listing(),))
    with pytest.raises(PrimaryListingRequired):
        ensure_operational_listing_invariant((listing(primary=False),))
    with pytest.raises(MultiplePrimaryListings):
        ensure_operational_listing_invariant((listing(), listing()))


def test_quality_is_derived_from_operational_completeness() -> None:
    assert determine_quality_status(name="Siemens", listings=(listing(),)) is QualityStatus.COMPLETE
    assert determine_quality_status(name="Siemens", listings=()) is QualityStatus.DRAFT


def test_verified_master_data_change_resets_quality_and_increments_version() -> None:
    changed = underlying(quality=QualityStatus.VERIFIED).with_master_data(now=LATER, name="Siemens")
    assert changed.name == "Siemens"
    assert changed.quality_status is QualityStatus.COMPLETE
    assert changed.version == 2
    assert changed.updated_at == LATER


def test_noop_change_does_not_increment_version() -> None:
    original = underlying()
    assert original.with_master_data(now=LATER, name="Siemens AG") is original


def test_lifecycle_transitions_are_idempotent() -> None:
    inactive = underlying().deactivate(now=LATER)
    assert inactive.lifecycle_status is LifecycleStatus.INACTIVE
    assert inactive.version == 2
    assert inactive.deactivate(now=LATER) is inactive
    active = inactive.reactivate(now=LATER, listings=(listing(),))
    assert active.lifecycle_status is LifecycleStatus.ACTIVE
    assert active.version == 3


def test_draft_cannot_be_verified_or_reactivated() -> None:
    draft = underlying(quality=QualityStatus.DRAFT, lifecycle=LifecycleStatus.INACTIVE)
    with pytest.raises(NotOperationallyComplete):
        draft.verify(now=LATER, listings=(listing(),))
    with pytest.raises(NotOperationallyComplete):
        draft.reactivate(now=LATER, listings=(listing(),))


def test_complete_underlying_can_be_verified() -> None:
    verified = underlying().verify(now=LATER, listings=(listing(),))
    assert verified.quality_status is QualityStatus.VERIFIED
    assert verified.version == 2


def test_expected_version_prevents_silent_overwrite() -> None:
    ensure_expected_version(2, 2)
    with pytest.raises(ConcurrentModification):
        ensure_expected_version(1, 2)
