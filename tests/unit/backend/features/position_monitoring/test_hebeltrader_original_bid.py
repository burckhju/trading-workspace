"""Pure original-BID prerequisites with synthetic clocks, sources and sessions."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import TypeAdapter, ValidationError

from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_quote_evidence import (
    OriginalQuoteEvidence,
    OriginalQuoteSideEvidence,
)
from app.features.market_data.domain.risk_evidence import (
    SavedQuoteEvidence,
    SavedQuoteProvenance,
    SavedQuoteRouteBinding,
)
from app.features.market_data.domain.session_evidence import SessionDay, SessionWindow
from app.features.position_monitoring.domain.hebeltrader_original_bid import (
    assess_original_bid,
    documented_session_at,
)

NOW = datetime(2026, 11, 15, 18, tzinfo=UTC)
ISIN = "DE000VH2LU21"


def saved_example(
    *, now: datetime = NOW, bid_age: timedelta = timedelta(seconds=60)
) -> SavedQuoteEvidence:
    """Public factory for service tests; scopes can be replaced explicitly by the caller."""
    bid_at = now - bid_age
    ask_at = bid_at - timedelta(seconds=30)
    route = SavedQuoteRouteBinding(
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        position_id=UUID(int=2),
        warrant_id=UUID(int=3),
        warrant_listing_id=UUID(int=4),
        trading_venue_id=UUID(int=5),
        venue_mic="XFRA",
        currency="EUR",
        identity_key="1" * 64,
        selection_id=UUID(int=6),
        selected_at=now - timedelta(days=30),
    )
    proof = OriginalQuoteEvidence(
        version="original-quote-evidence-v1",
        source_contract="frankfurt-quotes-v1",
        source_reference="synthetic-test-source",
        generated_at=bid_at,
        isin=ISIN,
        currency="EUR",
        venue_mic="XFRA",
        bid=OriginalQuoteSideEvidence(Decimal("1.00"), bid_at, bid_at.isoformat(), "bid_at"),
        ask=OriginalQuoteSideEvidence(Decimal("1.10"), ask_at, ask_at.isoformat(), "ask_at"),
    )
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=route.warrant_listing_id,
        bid=proof.bid.price,
        ask=proof.ask.price,
        currency=route.currency,
        provider_symbol=ISIN,
        provider_exchange_code="XFRA",
        observed_at=ask_at,
        isin=ISIN,
        source_mode="FRANKFURT_REALTIME_MONITORING",
        trading_status="OPEN",
        assessed_at=now,
        feed_delay_seconds=0,
        venue_mic=route.venue_mic,
        original_evidence=proof,
    )
    return SavedQuoteEvidence(
        reason="LAST_SUCCESS_IS_NOT_A_PRICE_SERIES",
        quote=quote,
        provider="FRANKFURT_QUOTES",
        retrieved_at=now,
        identity_key=route.identity_key,
        history_observations=1,
        route=route,
        provenance=SavedQuoteProvenance(
            read_at=now,
            raw_payload_fingerprint="2" * 64,
            retrieved_at=now,
            quality_status="VALID",
            warnings=("NOT_EXECUTABLE",),
            reason_code="FRANKFURT_BID_ASK_AVAILABLE",
        ),
    )


@pytest.mark.parametrize(
    "age,status,reason",
    [
        (timedelta(0), "AVAILABLE", None),
        (timedelta(seconds=899, microseconds=999999), "AVAILABLE", None),
        (timedelta(seconds=900), "AVAILABLE", None),
        (timedelta(seconds=900, microseconds=1), "UNSUITABLE", "ORIGINAL_BID_TOO_OLD"),
        (timedelta(seconds=3600), "UNSUITABLE", "ORIGINAL_BID_TOO_OLD"),
    ],
)
def test_exact_bid_age_boundary_does_not_round_or_use_older_ask(age, status, reason):
    saved = saved_example(bid_age=age)
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == status
    assert result.original_bid_at == NOW - age
    assert result.age_seconds == (
        Decimal(age.days * 86400 + age.seconds) + Decimal(age.microseconds) / 1000000
    )
    assert result.maximum_age_seconds == 900
    assert result.price_axis == "WARRANT_BID"
    assert result.price == Decimal("1.00")
    assert result.currency == "EUR"
    assert result.reasons == (() if reason is None else (reason,))
    assert saved.quote.observed_at == NOW - age - timedelta(seconds=30)


@pytest.mark.parametrize("delay", [0, 900, 3600])
def test_fresh_receipt_assessment_or_nominal_delay_never_refreshes_a_stale_bid(delay):
    saved = saved_example(bid_age=timedelta(seconds=901))
    saved = replace(
        saved,
        quote=replace(
            saved.quote,
            observed_at=NOW,
            feed_delay_seconds=delay,
            max_quote_age_seconds=86400,
            assessed_at=NOW,
        ),
    )
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_TOO_OLD",)
    assert result.age_seconds == Decimal(901)


@pytest.mark.parametrize("retained", [False, True])
def test_retention_flag_neither_invalidates_nor_refreshes_original_bid(retained):
    saved = saved_example()
    saved = replace(saved, quote=replace(saved.quote, retained=retained))
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "AVAILABLE"
    assert result.age_seconds == Decimal(60)


@pytest.mark.parametrize("reference_kind", ["LAST_TRADE", "PREVIOUS_CLOSE", "ASK_ONLY"])
def test_reference_or_ask_price_cannot_be_used_as_bid(reference_kind):
    saved = saved_example()
    if reference_kind == "ASK_ONLY":
        quote = replace(
            saved.quote,
            bid=None,
            original_evidence=replace(saved.quote.original_evidence, bid=None),
        )
    else:
        quote = replace(
            saved.quote,
            bid=None,
            ask=None,
            reference_price=Decimal("1.05"),
            reference_price_type=reference_kind,
            original_evidence=None,
        )
    result = assess_original_bid(replace(saved, quote=quote), evaluated_at=NOW, applicable=True)
    assert result.status == "MISSING"
    assert result.price is result.original_bid_at is result.age_seconds is None
    assert result.reasons == ("ORIGINAL_BID_PRICE_MISSING",)


@pytest.mark.parametrize("partial", [False, True])
def test_missing_bid_side_evidence_does_not_use_common_ask_or_receipt_time(partial):
    saved = saved_example()
    quote = replace(
        saved.quote,
        original_evidence=(replace(saved.quote.original_evidence, bid=None) if partial else None),
    )
    result = assess_original_bid(replace(saved, quote=quote), evaluated_at=NOW, applicable=True)
    assert result.status == "MISSING"
    assert result.original_bid_at is result.age_seconds is None
    assert result.price == Decimal("1.00")
    assert result.reasons == ("ORIGINAL_BID_SIDE_TIME_MISSING",)


@pytest.mark.parametrize(
    "mode,basis,text",
    [
        ("OFFICIAL_ISSUER_INDICATION_TIME_ONLY", "DATE_AND_TIMEZONE_UNKNOWN", "18:00:00"),
        (
            "OFFICIAL_ISSUER_INDICATION_LOCAL_DATETIME",
            "LOCAL_DATETIME_TIMEZONE_UNKNOWN",
            "15/11/2026 18:00:00",
        ),
        ("OFFICIAL_ISSUER_INDICATION_LOCAL_DATETIME", "TIMESTAMP_MISSING", None),
    ],
)
def test_unknown_historical_time_stays_unknown_even_with_fresh_receipt(mode, basis, text):
    saved = saved_example()
    quote = replace(
        saved.quote,
        provider_exchange_code="ISSUER",
        original_evidence=None,
        observed_at=None,
        source_mode=mode,
        quote_time_basis=basis,
        quote_time_text=text,
        feed_delay_seconds=0,
    )
    result = assess_original_bid(replace(saved, quote=quote), evaluated_at=NOW, applicable=True)
    assert result.status == "MISSING"
    assert result.original_bid_at is result.age_seconds is None


@pytest.mark.parametrize(
    "provider",
    [
        "EODHD",
        "VONTOBEL_MARKETS",
        "JPMORGAN",
        "MORGAN_STANLEY",
        "BOERSE_STUTTGART_DELAYED",
        "GETTEX_DELAYED",
        None,
    ],
)
def test_structurally_valid_proof_does_not_qualify_another_provider(provider):
    saved = replace(saved_example(), provider=provider)
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED",)


@pytest.mark.parametrize("source_contract", ["frankfurt-quotes-v2", "unreviewed-feed-v1"])
def test_structurally_valid_new_source_contract_remains_unqualified(source_contract):
    saved = saved_example()
    proof = replace(saved.quote.original_evidence, source_contract=source_contract)
    saved = replace(saved, quote=replace(saved.quote, original_evidence=proof))
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED",)


@pytest.mark.parametrize(
    "source_field", ["ask_at", "generated_at", "latestTimestamp", "TransactionTime"]
)
def test_renaming_a_common_or_other_side_field_does_not_create_original_bid(source_field):
    saved = saved_example()
    proof = saved.quote.original_evidence
    proof = replace(proof, bid=replace(proof.bid, source_field=source_field))
    saved = replace(saved, quote=replace(saved.quote, original_evidence=proof))
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED",)


@pytest.mark.parametrize("time_basis", ["SHARED_QUOTE_TIMESTAMP", "SNAPSHOT_TIMESTAMP", "UNKNOWN"])
def test_unknown_or_shared_side_time_basis_cannot_enter_the_typed_consumer(time_basis):
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    payload = adapter.dump_python(saved_example().quote, mode="json")
    payload["original_evidence"]["bid"]["time_basis"] = time_basis
    with pytest.raises(ValidationError):
        adapter.validate_python(payload)


@pytest.mark.parametrize(
    "mode",
    [
        None,
        "NORMALIZED_SNAPSHOT",
        "OFFICIAL_WEBSITE_LAST_TRADE",
        "OFFICIAL_DELAYED_PRETRADE",
        "OFFICIAL_ISSUER_INDICATION",
    ],
)
def test_original_bid_source_mode_must_be_the_demonstrated_producer_path(mode):
    saved = saved_example()
    saved = replace(saved, quote=replace(saved.quote, source_mode=mode))
    assert assess_original_bid(saved, evaluated_at=NOW, applicable=True).reasons == (
        "ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED",
    )


def test_delayed_normalized_contract_uses_actual_age_not_its_delay_label():
    saved = saved_example()
    saved = replace(
        saved,
        quote=replace(
            saved.quote, source_mode="FRANKFURT_DELAYED_MONITORING", feed_delay_seconds=900
        ),
    )
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "AVAILABLE"
    assert result.age_seconds == Decimal(60)


@pytest.mark.parametrize("changed", ["route_mic", "quote_and_proof_mic", "exchange"])
def test_supported_provider_name_does_not_qualify_another_venue_or_public_route(changed):
    saved = saved_example()
    if changed == "route_mic":
        saved = replace(saved, route=replace(saved.route, venue_mic="XSTU"))
    elif changed == "quote_and_proof_mic":
        saved = replace(
            saved,
            quote=replace(
                saved.quote,
                venue_mic="XSTU",
                original_evidence=replace(saved.quote.original_evidence, venue_mic="XSTU"),
            ),
        )
    else:
        saved = replace(saved, quote=replace(saved.quote, provider_exchange_code="XSC"))
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED",)


@pytest.mark.parametrize("missing", ["route", "provenance"])
def test_unbound_original_quote_cannot_be_available(missing):
    saved = replace(saved_example(), **{missing: None})
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("SAVED_QUOTE_BINDING_OR_PROVENANCE_MISSING",)


@pytest.mark.parametrize(
    "reason,status",
    [
        ("NO_CONFIRMED_SAVED_QUOTE_SOURCE", "MISSING"),
        ("NO_SAVED_QUOTE_FOR_CURRENT_ROUTE", "MISSING"),
        ("SAVED_QUOTE_PAYLOAD_INVALID", "UNSUITABLE"),
        ("SAVED_QUOTE_HELD_INSTRUMENT_MISMATCH", "UNSUITABLE"),
    ],
)
def test_absent_or_rejected_owner_read_retains_exact_reason(reason, status):
    result = assess_original_bid(SavedQuoteEvidence(reason), evaluated_at=NOW, applicable=True)
    assert result.status == status
    assert result.reasons == (reason,)
    assert result.price is result.original_bid_at is result.age_seconds is None


@pytest.mark.parametrize(
    "changed", ["missing_receipt", "side_after_receipt", "generated_after_receipt"]
)
def test_side_and_generation_clocks_cannot_follow_actual_retrieval(changed):
    saved = saved_example()
    if changed == "missing_receipt":
        saved = replace(saved, retrieved_at=None)
    elif changed == "side_after_receipt":
        saved = replace(
            saved,
            retrieved_at=saved.quote.original_evidence.bid.observed_at - timedelta(microseconds=1),
        )
    else:
        saved = replace(
            saved,
            quote=replace(
                saved.quote,
                original_evidence=replace(
                    saved.quote.original_evidence, generated_at=NOW + timedelta(microseconds=1)
                ),
            ),
        )
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_AFTER_RETRIEVAL",)


def test_bid_after_read_is_never_a_current_prerequisite():
    saved = saved_example(now=NOW + timedelta(seconds=61))
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=True)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("ORIGINAL_BID_AFTER_READ",)
    assert result.age_seconds == Decimal(-1)


@pytest.mark.parametrize("age", [timedelta(seconds=60), timedelta(seconds=901)])
def test_closed_or_cancelled_position_is_not_applicable_without_mutation(age):
    saved = saved_example(bid_age=age)
    original = deepcopy(saved)
    result = assess_original_bid(saved, evaluated_at=NOW, applicable=False)
    assert result.status == "NOT_APPLICABLE"
    assert result.reasons == ("POSITION_CLOSED_OR_CANCELLED",)
    assert saved == original


def test_domain_is_repeatable_immutable_and_uses_instants_across_timezones():
    saved = saved_example()
    original = deepcopy(saved)
    local_now = NOW.astimezone(ZoneInfo("Europe/Berlin"))
    first = assess_original_bid(saved, evaluated_at=local_now, applicable=True)
    assert first == assess_original_bid(saved, evaluated_at=local_now, applicable=True)
    assert first.status == "AVAILABLE"
    assert first.age_seconds == Decimal(60)
    assert saved == original
    with pytest.raises(FrozenInstanceError):
        first.status = "MISSING"
    with pytest.raises(ValueError, match="timezone-aware"):
        assess_original_bid(saved, evaluated_at=NOW.replace(tzinfo=None), applicable=True)


def day_with_intervals(*intervals, day=None):
    return SessionDay(day or NOW.date(), "SESSION", tuple(intervals), "synthetic original calendar")


@pytest.mark.parametrize(
    "offset,status",
    [
        (timedelta(microseconds=-1), "OUTSIDE_DOCUMENTED_INTERVAL"),
        (timedelta(0), "IN_DOCUMENTED_INTERVAL"),
        (timedelta(minutes=59, seconds=59, microseconds=999999), "IN_DOCUMENTED_INTERVAL"),
        (timedelta(hours=1), "OUTSIDE_DOCUMENTED_INTERVAL"),
    ],
)
def test_documented_session_includes_open_and_excludes_close(offset, status):
    window = SessionWindow(NOW, NOW + timedelta(hours=1))
    result = documented_session_at(days=(day_with_intervals(window),), event_at=NOW + offset)
    assert result.status == status
    assert result.interval == (window if status == "IN_DOCUMENTED_INTERVAL" else None)


def test_documented_intraday_break_does_not_become_open_market():
    first = SessionWindow(NOW - timedelta(hours=2), NOW)
    second = SessionWindow(NOW + timedelta(minutes=30), NOW + timedelta(hours=2))
    days = (day_with_intervals(first, second),)
    for event in (NOW, NOW + timedelta(minutes=29, seconds=59, microseconds=999999)):
        assert (
            documented_session_at(days=days, event_at=event).status == "OUTSIDE_DOCUMENTED_INTERVAL"
        )
    assert documented_session_at(days=days, event_at=second.opens_at).interval == second


def test_overnight_interval_keeps_original_session_date():
    window = SessionWindow(
        datetime(2026, 11, 14, 22, tzinfo=UTC), datetime(2026, 11, 15, 3, tzinfo=UTC)
    )
    days = (day_with_intervals(window, day=date(2026, 11, 14)),)
    result = documented_session_at(days=days, event_at=datetime(2026, 11, 15, 1, tzinfo=UTC))
    assert result.status == "IN_DOCUMENTED_INTERVAL"
    assert result.session_date == date(2026, 11, 14)
    assert result.interval == window
    assert (
        documented_session_at(days=days, event_at=window.closes_at).status
        == "OUTSIDE_DOCUMENTED_INTERVAL"
    )


def test_dst_repeated_hour_is_compared_by_instant_not_local_wall_clock():
    zone = ZoneInfo("Europe/Berlin")
    first_hour = SessionWindow(
        datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=0),
        datetime(2026, 10, 25, 2, 45, tzinfo=zone, fold=0),
    )
    days = (day_with_intervals(first_hour, day=date(2026, 10, 25)),)
    first = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
    later = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1)
    assert documented_session_at(days=days, event_at=first).status == "IN_DOCUMENTED_INTERVAL"
    assert documented_session_at(days=days, event_at=later).status == "OUTSIDE_DOCUMENTED_INTERVAL"


def test_dst_session_crossing_fall_back_keeps_actual_duration():
    zone = ZoneInfo("Europe/Berlin")
    window = SessionWindow(
        datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0),
        datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=1),
    )
    days = (day_with_intervals(window, day=date(2026, 10, 25)),)
    event = datetime(2026, 10, 25, 2, 15, tzinfo=zone, fold=1)
    assert documented_session_at(days=days, event_at=event).status == "IN_DOCUMENTED_INTERVAL"
    assert (
        documented_session_at(days=days, event_at=window.closes_at).status
        == "OUTSIDE_DOCUMENTED_INTERVAL"
    )


def test_unknown_day_never_becomes_documented_closed_or_open_day():
    unknown = SessionDay(NOW.date(), "UNKNOWN", (), "synthetic missing calendar evidence")
    result = documented_session_at(days=(unknown,), event_at=NOW)
    assert result.status == "NOT_ASSESSABLE"
    assert result.reasons == ("SESSION_DAYS_UNKNOWN",)
    assert result.interval is result.session_date is None


def test_conflicting_supplied_intervals_never_pick_an_arbitrary_session():
    window = SessionWindow(NOW, NOW + timedelta(hours=1))
    days = (day_with_intervals(window), day_with_intervals(window))
    result = documented_session_at(days=days, event_at=NOW)
    assert result.status == "NOT_ASSESSABLE"
    assert result.reasons == ("SESSION_DAYS_CONFLICT",)


def test_pure_interval_match_preserves_originals_and_rejects_unknown_event_clock():
    window = SessionWindow(NOW, NOW + timedelta(hours=1))
    days = (day_with_intervals(window),)
    original = deepcopy(days)
    result = documented_session_at(days=days, event_at=NOW)
    assert days == original
    assert result == documented_session_at(days=days, event_at=NOW)
    with pytest.raises(FrozenInstanceError):
        result.status = "OUTSIDE_DOCUMENTED_INTERVAL"
    with pytest.raises(ValueError, match="aware"):
        documented_session_at(days=days, event_at=NOW.replace(tzinfo=None))
