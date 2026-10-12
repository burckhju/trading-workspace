"""Real persisted-contract limitations must never turn into zero IV or green risk."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D
from uuid import uuid4

import pytest
from pydantic import TypeAdapter

from app.features.market.service.risk_reference import RiskListingReference
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.position_monitoring.service.iv_readiness import assess_iv_readiness
from app.features.product.service.risk_reference import RiskProductReference

NOW = datetime(2026, 10, 12, 12, tzinfo=UTC)
PRODUCT = RiskProductReference(
    uuid4(),
    uuid4(),
    "Synthetic",
    "DE000SYN0001",
    None,
    uuid4(),
    "CALL",
    D(".1"),
    D(100),
    "EUR",
    date(2027, 1, 1),
)
LISTING = RiskListingReference(uuid4(), "EUR", "SYN")
QUOTE = WarrantQuoteSnapshot(
    uuid4(),
    D(2),
    D("2.2"),
    "EUR",
    PRODUCT.isin,
    "ISSUER",
    NOW,
    isin=PRODUCT.isin,
    max_quote_age_seconds=60,
)


def assess(quote=QUOTE, **changes):
    return assess_iv_readiness(
        PRODUCT,
        LISTING,
        SavedQuoteEvidence("SAVED", quote, "SYNTHETIC", NOW, "route-a"),
        as_of=changes.get("as_of", NOW),
    )


def test_no_fake_iv_history_or_risk_even_with_a_fresh_valid_quote():
    result = assess()
    payload = TypeAdapter(type(result)).dump_python(result, mode="json")
    assert result.status == "NOT_EVALUABLE" and not result.execution_usable
    for field in (
        "current_iv_decimal",
        "change_pp",
        "percentile",
        "rank",
        "vega_per_warrant_per_pp",
        "position_iv_effect",
        "risk_level",
        "next_event",
        "selected_scenario_loss",
        "model_version",
        "iv_origin",
    ):
        assert payload[field] is None
    assert result.history_status == "NO_QUALIFIED_IV_HISTORY"
    assert result.event_status == "NO_VERIFIED_EVENT_SOURCE"
    assert result.quote_side == "MID_INDICATION" and result.quote_age_seconds == 0
    assert "EXERCISE_STYLE_UNKNOWN" in result.reasons
    assert "SYNCHRONIZED_UNDERLYING_QUOTE_MISSING" in result.reasons


def test_unknown_timestamp_is_not_retrieval_time_stale_quotes_not_extended_at_weekend():
    unknown = assess(
        replace(
            QUOTE,
            observed_at=None,
            source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
            quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
        )
    )
    assert unknown.quote_age_seconds is None
    assert "SOURCE_TIME_OR_TIMEZONE_UNKNOWN" in unknown.reasons
    stale = assess(as_of=NOW + timedelta(days=6))
    assert "QUOTE_STALE" in stale.reasons
    assert "SESSION_CALENDAR_UNVERIFIED_NO_AGE_EXTENSION" in stale.reasons
    assert "QUOTE_STALE" not in assess(as_of=NOW + timedelta(seconds=60)).reasons
    assert "QUOTE_STALE" in assess(as_of=NOW + timedelta(seconds=61)).reasons


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"observed_at": NOW + timedelta(seconds=1)}, "QUOTE_TIME_IN_FUTURE"),
        ({"retained": True}, "QUOTE_RETAINED_OR_REFRESH_FAILED"),
        ({"ask": None}, "MID_REQUIRES_TWO_SIDED_QUOTE"),
        ({"bid": None}, "MID_REQUIRES_TWO_SIDED_QUOTE"),
        ({"currency": "USD"}, "FX_OR_QUANTO_UNSUPPORTED"),
        ({"max_quote_age_seconds": None}, "QUOTE_AGE_POLICY_UNKNOWN"),
        ({"isin": "DIFFERENT"}, "POSITION_QUOTE_IDENTITY_MISMATCH"),
    ],
)
def test_concrete_quote_blockers(changes, reason):
    assert reason in assess(replace(QUOTE, **changes)).reasons


@pytest.mark.parametrize(
    "changes", [{"bid": D(0)}, {"ask": D(0)}, {"bid": D(3)}, {"ask": D("NaN")}]
)
def test_ingestion_rejects_nonpositive_crossed_or_nonfinite_pair(changes):
    with pytest.raises(ValueError):
        replace(QUOTE, **changes)


def test_reference_missing_terms_receipt_and_unsupported_product():
    reference = replace(
        QUOTE, bid=None, ask=None, reference_price=D(2), reference_price_type="PREVIOUS_CLOSE"
    )
    assert "REFERENCE_PRICE_NOT_CURRENT_IV_BASIS" in assess(reference).reasons
    assert "WARRANT_QUOTE_MISSING" in assess(None).reasons
    none = assess_iv_readiness(
        None, None, SavedQuoteEvidence("SAVED_QUOTE_ROUTE_IDENTITY_CHANGED"), as_of=NOW
    )
    assert "PRODUCT_TERMS_OR_PRIMARY_LISTING_MISSING" in none.reasons
    assert "SAVED_QUOTE_ROUTE_IDENTITY_CHANGED" in none.reasons
    product = replace(PRODUCT, exercise_style="AMERICAN", quanto=True, maturity=NOW.date())
    unsupported = assess_iv_readiness(
        product, LISTING, SavedQuoteEvidence("SAVED", QUOTE), as_of=NOW
    )
    assert "UNSUPPORTED_PRODUCT_OR_EXERCISE" in unsupported.reasons
    assert "MATURITY_REACHED_OR_TODAY" in unsupported.reasons
    assert "QUOTE_RECEIPT_UNKNOWN" in unsupported.reasons
