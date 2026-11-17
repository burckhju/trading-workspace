"""A reported status point cannot become a live opening or recovery assertion."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from tests.unit.backend.features.position_monitoring.test_hebeltrader_original_bid import (
    NOW,
    saved_example,
)

from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.position_monitoring.domain.hebeltrader_live_market_status import (
    assess_live_market_status,
)


def with_status(saved, *, observed_at=None, status="OPEN", source_contract=None):
    """Synthetically supplied source observation; never a verified vendor example."""
    quote = saved.quote
    source = quote.original_evidence
    point = observed_at if observed_at is not None else source.bid.observed_at
    generated = max(source.generated_at, point)
    if source_contract is not None:
        source = replace(source, source_contract=source_contract)
    evidence = OriginalMarketStatusEvidence(
        version="original-market-status-evidence-v1",
        source_contract=source.source_contract,
        source_reference=source.source_reference,
        generated_at=generated,
        isin=source.isin,
        venue_mic=source.venue_mic,
        status=status,
        original_status_text=status,
        source_status_field="trading_status",
        observed_at=point,
        original_time_text=point.astimezone(ZoneInfo("Europe/Berlin")).isoformat(),
        source_time_field="status_observed_at",
    )
    return replace(
        saved,
        quote=replace(
            quote,
            original_evidence=replace(source, generated_at=generated),
            trading_status=status,
            original_market_status=evidence,
        ),
    )


def assess(saved, *, bid_at=NOW - timedelta(seconds=60), now=NOW, applicable=True):
    return assess_live_market_status(
        saved, original_bid_at=bid_at, evaluated_at=now, applicable=applicable
    )


def test_legacy_open_does_not_borrow_a_price_generation_or_receipt_clock():
    saved = saved_example()
    result = assess(saved)
    assert result.status == "MISSING"
    assert result.reported_status == "OPEN"
    assert result.original_evidence is None
    assert result.at_bid.relation == result.at_read.relation == "NO_ORIGINAL_STATUS_TIME"
    assert result.at_bid.event_at == saved.quote.original_evidence.bid.observed_at
    assert result.at_read.event_at == NOW
    assert "MARKET_STATUS_ORIGINAL_TIME_MISSING" in result.reasons
    assert "MARKET_STATUS_NEWER_OBSERVATIONS_NOT_COVERED" in result.reasons
    assert result.source_qualification == "NOT_INDEPENDENTLY_VERIFIED"
    assert result.evidence_scope == "SAVED_QUOTE_LAST_SUCCESS_ONLY"
    assert result.newer_status_observations == "NOT_OBSERVED_BY_SAVED_QUOTE_READER"
    assert result.status_validity_interval == "NOT_ESTABLISHED"


@pytest.mark.parametrize(
    "offset,bid_relation,read_relation",
    [
        (-120, "AFTER_SOURCE_POINT", "AFTER_SOURCE_POINT"),
        (-60, "AT_SOURCE_POINT", "AFTER_SOURCE_POINT"),
        (0, "BEFORE_SOURCE_POINT", "AT_SOURCE_POINT"),
    ],
)
def test_original_point_is_not_extended_to_earlier_bid_or_later_read(
    offset, bid_relation, read_relation
):
    saved = with_status(saved_example(), observed_at=NOW + timedelta(seconds=offset))
    original = deepcopy(saved)
    result = assess(saved)
    assert result.at_bid.relation == bid_relation
    assert result.at_read.relation == read_relation
    assert result.at_bid.status == result.at_read.status == "NOT_ASSESSABLE"
    assert result.status == "MISSING"
    assert result.original_evidence is saved.quote.original_market_status
    assert "MARKET_STATUS_POINT_IS_NOT_VALIDITY_INTERVAL" in result.reasons
    assert "MARKET_STATUS_SOURCE_SEMANTICS_NOT_VERIFIED" in result.reasons
    assert saved == original


def test_even_exact_same_bid_status_and_read_instant_is_not_a_verified_open_market():
    saved = with_status(saved_example(bid_age=timedelta(0)), observed_at=NOW)
    result = assess(saved, bid_at=NOW)
    assert result.at_bid.relation == result.at_read.relation == "AT_SOURCE_POINT"
    assert result.status == "MISSING"
    assert result.at_bid.status == result.at_read.status == "NOT_ASSESSABLE"
    assert result.status_validity_interval == "NOT_ESTABLISHED"


@pytest.mark.parametrize("age", [899, 900, 900.000001, 901, 86400])
def test_bid_age_limit_is_never_invented_as_status_validity(age):
    saved = with_status(saved_example(), observed_at=NOW - timedelta(seconds=age))
    result = assess(saved)
    assert result.status == "MISSING"
    assert result.at_read.relation == "AFTER_SOURCE_POINT"
    assert result.at_read.status == "NOT_ASSESSABLE"
    assert result.status_validity_interval == "NOT_ESTABLISHED"
    assert "MARKET_STATUS_SOURCE_TIME_INCONSISTENT" not in result.reasons


@pytest.mark.parametrize("status", ["CLOSED", "SUSPENDED", "UNKNOWN"])
def test_reported_negative_or_unknown_status_remains_a_source_fact(status):
    saved = with_status(saved_example(), status=status)
    result = assess(saved)
    assert result.status == ("MISSING" if status == "UNKNOWN" else "UNSUITABLE")
    assert result.reported_status == result.original_evidence.status == status
    assert result.at_bid.status == result.at_read.status == "NOT_ASSESSABLE"
    assert result.status_validity_interval == "NOT_ESTABLISHED"


@pytest.mark.parametrize("status", ["CLOSED", "SUSPENDED", "HALTED", "AUCTION"])
def test_legacy_non_open_value_is_not_an_opening_proof_or_current_closed_claim(status):
    saved = saved_example()
    saved = replace(saved, quote=replace(saved.quote, trading_status=status))
    result = assess(saved)
    assert result.status == "UNSUITABLE"
    assert result.original_evidence is None
    assert result.reported_status == status
    assert result.at_read.status == "NOT_ASSESSABLE"


@pytest.mark.parametrize("status", [None, "UNKNOWN"])
def test_missing_or_unknown_reported_status_does_not_invent_an_opening(status):
    saved = saved_example()
    result = assess(replace(saved, quote=replace(saved.quote, trading_status=status)))
    assert result.status == "MISSING"
    assert "MARKET_STATUS_VALUE_MISSING_OR_UNKNOWN" in result.reasons


def test_no_quote_or_no_bid_time_is_not_replaced_by_receipt_time():
    empty = assess(SavedQuoteEvidence("NO_SAVED_QUOTE_FOR_CURRENT_ROUTE"), bid_at=None)
    assert empty.reported_status is None
    assert empty.at_bid.event_at is None
    assert empty.at_bid.relation == "NO_EVENT_TIME"
    assert "MARKET_STATUS_SAVED_QUOTE_MISSING" in empty.reasons
    result = assess(with_status(saved_example()), bid_at=None)
    assert result.at_bid.event_at is None
    assert result.at_bid.relation == "NO_EVENT_TIME"
    assert result.at_read.status == "NOT_ASSESSABLE"


@pytest.mark.parametrize("change", ["mic", "listing", "identity", "route", "provenance"])
def test_foreign_or_unbound_source_point_is_unsuitable(change):
    saved = with_status(saved_example())
    if change == "mic":
        saved = replace(saved, route=replace(saved.route, venue_mic="XSTU"))
    elif change == "listing":
        saved = replace(saved, route=replace(saved.route, warrant_listing_id=UUID(int=9001)))
    elif change == "identity":
        saved = replace(saved, identity_key="f" * 64)
    else:
        saved = replace(saved, **{change: None})
    result = assess(saved)
    assert result.status == "UNSUITABLE"
    assert "MARKET_STATUS_BINDING_OR_PROVENANCE_INVALID" in result.reasons


@pytest.mark.parametrize(
    "change", ["future", "receipt_missing", "generation", "read", "provenance"]
)
def test_original_status_receipt_and_common_snapshot_cannot_conflict(change):
    saved = with_status(saved_example())
    if change == "future":
        saved = with_status(saved_example(), observed_at=NOW + timedelta(microseconds=1))
    elif change == "receipt_missing":
        saved = replace(saved, retrieved_at=None)
    elif change == "generation":
        saved = replace(saved, retrieved_at=NOW - timedelta(seconds=61))
    elif change == "read":
        saved = replace(saved, retrieved_at=NOW + timedelta(microseconds=1))
    else:
        saved = replace(
            saved,
            provenance=replace(saved.provenance, read_at=NOW + timedelta(seconds=1)),
        )
    result = assess(saved)
    assert result.status == "UNSUITABLE"
    assert "MARKET_STATUS_SOURCE_TIME_INCONSISTENT" in result.reasons


def test_read_time_and_bid_clock_must_not_be_naive():
    for kwargs in [
        {"now": NOW.replace(tzinfo=None)},
        {"bid_at": NOW.replace(tzinfo=None)},
    ]:
        with pytest.raises(ValueError, match="aware"):
            assess(with_status(saved_example()), **kwargs)


def test_dst_offset_and_utc_point_remain_exact_without_a_status_age_policy():
    instant = datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
    saved = with_status(saved_example(now=instant, bid_age=timedelta(0)), observed_at=instant)
    result = assess(saved, now=instant, bid_at=instant.astimezone(ZoneInfo("Europe/Berlin")))
    assert result.original_evidence.original_time_text == "2026-10-25T02:30:00+01:00"
    assert result.at_bid.relation == result.at_read.relation == "AT_SOURCE_POINT"
    assert result.status == "MISSING"


def test_new_source_contract_and_fresh_refresh_flags_never_qualify_status_semantics():
    saved = with_status(saved_example(), source_contract="unqualified-new-exporter-v2")
    saved = replace(
        saved,
        quote=replace(saved.quote, assessed_at=NOW, retained=True, refresh_error="NO_NEW_BID"),
    )
    result = assess(saved)
    assert result.original_evidence.observed_at == NOW - timedelta(seconds=60)
    assert result.status == "MISSING"
    assert result.source_qualification == "NOT_INDEPENDENTLY_VERIFIED"
    assert result.newer_status_observations == "NOT_OBSERVED_BY_SAVED_QUOTE_READER"


def test_closed_position_keeps_source_fact_without_current_qualification():
    result = assess(with_status(saved_example(), status="CLOSED"), applicable=False)
    assert result.status == "NOT_APPLICABLE"
    assert result.reasons == ("POSITION_CLOSED_OR_CANCELLED",)
    assert result.reported_status == "CLOSED"
    assert result.at_bid.status == result.at_read.status == "NOT_APPLICABLE"
    assert result.at_bid.relation == result.at_read.relation == "NOT_APPLICABLE"
    assert asdict(result)["definition_version"] == "hebeltrader-live-market-status-v1"
