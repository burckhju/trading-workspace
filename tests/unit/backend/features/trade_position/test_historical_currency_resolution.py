"""No historical execution is unlocked by today's listing or an ambiguous source."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from itertools import permutations
from uuid import UUID

import pytest
from tests.unit.backend.features.trade_position.currency_evidence_fixtures import (
    FRANKFURT,
    XETRA,
    document,
    historical,
    listing,
)
from tests.unit.backend.features.trade_position.test_currency_resolution import (
    TRADE,
    confirmed,
    execution,
)

from app.features.trade_position.domain.currency_resolution import (
    CurrencyResolutionLimitExceeded,
    resolve_execution_currencies,
)


def resolve(facts, evidence=(), confirmations=()):
    return resolve_execution_currencies(
        trade=TRADE,
        executions=facts,
        current={item.execution_id: item for item in confirmations},
        evidence=evidence,
    )


def test_explicit_confirmation_has_priority_without_relabelling_derived_information():
    fact = execution(10)
    receipt = document(TRADE, fact.id, code="USD")
    old_listings = historical(TRADE)
    explicit = confirmed(fact, "CHF")
    value = resolve([fact], (receipt, old_listings), (explicit,))[fact.id]
    assert value.currency_code == "CHF"
    assert value.source == "USER_CONFIRMED"
    assert value.confirmation_ids == (explicit.id,)
    assert fact.currency_confirmation is None


def test_exact_document_precedes_different_historical_listing_currency():
    fact = execution(10)
    receipt = document(TRADE, fact.id, code="USD")
    value = resolve([fact], (historical(TRADE), receipt))[fact.id]
    assert value.currency_code == "USD"
    assert value.source == "EXECUTION_DOCUMENT"
    assert value.evidence_ids == (receipt.id,)
    assert value.confirmation_ids == ()


def test_two_matching_execution_documents_are_not_an_ambiguity():
    fact = execution(10)
    sources = (document(TRADE, fact.id, 9001), document(TRADE, fact.id, 9002))
    value = resolve([fact], sources)[fact.id]
    assert value.currency_code == "EUR"
    assert value.source == "EXECUTION_DOCUMENT"
    assert set(value.evidence_ids) == {item.id for item in sources}


def test_contradictory_documents_block_fallback_to_prior_buy_and_eur_listings():
    buy, sale = execution(10), execution(11, "SELL")
    sources = (
        document(TRADE, sale.id, 9001),
        document(TRADE, sale.id, 9002, code="USD"),
        historical(TRADE),
    )
    value = resolve([buy, sale], sources, (confirmed(buy),))[sale.id]
    assert value.currency_code is None
    assert value.source == "CONFLICT"
    assert value.reason


def test_known_execution_venue_selects_its_valid_listing_even_with_other_currency_elsewhere():
    fact = execution(10)
    receipt = document(TRADE, fact.id, code=None, venue=XETRA)
    old_listings = historical(
        TRADE, codes=(listing(XETRA, "EUR"), listing(FRANKFURT, "USD")), complete=False
    )
    value = resolve([fact], (receipt, old_listings))[fact.id]
    assert value.currency_code == "EUR"
    assert value.source == "HISTORICAL_LISTING"
    assert set(value.evidence_ids) == {receipt.id, old_listings.id}


def test_two_venues_with_same_historical_currency_need_no_repeated_confirmation():
    buy, sale = execution(10), execution(11, "SELL")
    source = historical(TRADE)
    values = resolve([buy, sale], (source,))
    for fact in (buy, sale):
        assert values[fact.id].currency_code == "EUR"
        assert values[fact.id].source == "HISTORICAL_LISTINGS"
        assert values[fact.id].evidence_ids == (source.id,)
        assert values[fact.id].confirmation_ids == ()


@pytest.mark.parametrize(
    ("rows", "complete"),
    [
        ((listing(),), False),
        ((listing(), listing(FRANKFURT, "USD")), True),
        ((listing(), listing(FRANKFURT, None)), True),
    ],
)
def test_unknown_venue_cannot_use_partial_mixed_or_incompletely_known_listing_set(rows, complete):
    fact = execution(10)
    value = resolve([fact], (historical(TRADE, codes=rows, complete=complete),))[fact.id]
    assert value.currency_code is None
    assert value.reason


def test_missing_recorded_execution_venue_is_not_replaced_by_another_venues_currency():
    fact = execution(10)
    receipt = document(TRADE, fact.id, code=None, venue=UUID(int=7003))
    value = resolve([fact], (receipt, historical(TRADE)))[fact.id]
    assert value.currency_code is None


def test_conflicting_execution_venues_do_not_select_a_convenient_listing():
    fact = execution(10)
    sources = (
        document(TRADE, fact.id, 9001, code=None, venue=XETRA),
        document(TRADE, fact.id, 9002, code=None, venue=FRANKFURT),
        historical(TRADE, codes=(listing(), listing(FRANKFURT, "USD"))),
    )
    value = resolve([fact], sources)[fact.id]
    assert value.currency_code is None
    assert value.source == "CONFLICT"


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_historical_validity_is_half_open_and_does_not_backfill_before_start(offset):
    fact = execution(10)
    start = fact.executed_at + timedelta(seconds=offset)
    source = historical(TRADE, start=start, end=fact.executed_at + timedelta(days=1))
    value = resolve([fact], (source,))[fact.id]
    assert value.currency_code == (None if offset == 1 else "EUR")


@pytest.mark.parametrize("offset", [-1, 0, 1])
def test_historical_validity_excludes_end_instant(offset):
    fact = execution(10)
    source = historical(TRADE, end=fact.executed_at + timedelta(seconds=offset))
    value = resolve([fact], (source,))[fact.id]
    assert value.currency_code == ("EUR" if offset == 1 else None)


@pytest.mark.parametrize("boundary", ["start", "end", "full"])
def test_date_only_execution_requires_evidence_covering_the_entire_dst_day(boundary):
    fact = replace(
        execution(10),
        executed_at=datetime(2026, 10, 24, 22, tzinfo=UTC),
        recorded_at=datetime(2026, 11, 1, tzinfo=UTC),
        executed_on=date(2026, 10, 25),
        execution_timezone="Europe/Berlin",
    )
    start = datetime(2026, 10, 24, 22, tzinfo=UTC)
    end = datetime(2026, 10, 25, 23, tzinfo=UTC)
    source = historical(
        TRADE,
        start=start + (timedelta(hours=1) if boundary == "start" else timedelta()),
        end=end - (timedelta(hours=1) if boundary == "end" else timedelta()),
    )
    value = resolve([fact], (source,))[fact.id]
    assert value.currency_code == ("EUR" if boundary == "full" else None)


def segmented_day(known_venue, *, gap=timedelta(), second_currency="EUR"):
    start = datetime(2026, 10, 24, 22, tzinfo=UTC)
    split = datetime(2026, 10, 25, 10, tzinfo=UTC)
    end = datetime(2026, 10, 25, 23, tzinfo=UTC)
    fact = replace(
        execution(10),
        executed_at=start,
        recorded_at=datetime(2026, 11, 1, tzinfo=UTC),
        executed_on=date(2026, 10, 25),
        execution_timezone="Europe/Berlin",
    )
    sources = (
        historical(
            TRADE,
            8001,
            codes=(listing(XETRA),),
            complete=not known_venue,
            start=start,
            end=split,
        ),
        historical(
            TRADE,
            8002,
            codes=(listing(XETRA, second_currency),),
            complete=not known_venue,
            start=split + gap,
            end=end,
        ),
    )
    if known_venue:
        sources += (document(TRADE, fact.id, code=None, venue=XETRA),)
    return fact, sources, split, end


@pytest.mark.parametrize("known_venue", [False, True])
def test_adjacent_evidenced_intervals_jointly_cover_the_entire_date_only_day(known_venue):
    fact, sources, _, _ = segmented_day(known_venue)
    value = resolve([fact], sources)[fact.id]
    assert value.currency_code == "EUR"
    assert value.source == ("HISTORICAL_LISTING" if known_venue else "HISTORICAL_LISTINGS")
    assert set(value.evidence_ids) == {item.id for item in sources}


@pytest.mark.parametrize("known_venue", [False, True])
def test_even_a_one_microsecond_gap_between_evidenced_intervals_remains_unresolved(known_venue):
    fact, sources, _, _ = segmented_day(known_venue, gap=timedelta(microseconds=1))
    value = resolve([fact], sources)[fact.id]
    assert value.currency_code is None
    assert value.reason == "LISTING_HISTORY_INCOMPLETE"


@pytest.mark.parametrize("known_venue", [False, True])
def test_different_currency_in_second_day_segment_blocks_the_date_only_execution(known_venue):
    fact, sources, _, _ = segmented_day(known_venue, second_currency="USD")
    value = resolve([fact], sources)[fact.id]
    assert value.currency_code is None
    assert value.source == "CONFLICT"


@pytest.mark.parametrize("known_venue", [False, True])
def test_segment_union_contains_shared_boundary_but_never_the_exclusive_final_endpoint(known_venue):
    fact, sources, split, end = segmented_day(known_venue)
    at_split = replace(fact, executed_at=split, executed_on=None, execution_timezone=None)
    at_end = replace(fact, executed_at=end, executed_on=None, execution_timezone=None)
    assert resolve([at_split], sources)[fact.id].currency_code == "EUR"
    assert resolve([at_end], sources)[fact.id].currency_code is None


def test_newly_recorded_historical_source_can_prove_its_own_past_interval():
    fact = execution(10)
    source = historical(TRADE)
    assert source.recorded_at > fact.executed_at
    assert resolve([fact], (source,))[fact.id].currency_code == "EUR"


@pytest.mark.parametrize("scope", ["workspace", "product", "trade", "execution"])
def test_execution_documents_from_another_scope_do_not_prove_this_execution(scope):
    fact = execution(10)
    source = replace(document(TRADE, fact.id), **{f"{scope}_id": UUID(int=99001)})
    assert resolve([fact], (source,))[fact.id].currency_code is None


@pytest.mark.parametrize("scope", ["workspace", "product"])
def test_historical_listings_from_another_scope_cannot_seed_a_trade(scope):
    fact = execution(10)
    source = replace(historical(TRADE), **{f"{scope}_id": UUID(int=99001)})
    assert resolve([fact], (source,))[fact.id].currency_code is None


def test_historical_derivation_does_not_escape_its_validity_via_prior_buy_reuse():
    buy, sale = execution(10), execution(11, "SELL")
    source = historical(TRADE, end=sale.executed_at)
    values = resolve([buy, sale], (source,))
    assert values[buy.id].currency_code == "EUR"
    assert values[sale.id].currency_code is None


def test_exact_buy_document_does_not_fabricate_a_later_execution_document():
    buy, sale = execution(10), execution(11, "SELL")
    source = document(TRADE, buy.id)
    values = resolve([buy, sale], (source,))
    assert values[buy.id].source == "EXECUTION_DOCUMENT"
    assert values[sale.id].currency_code is None


def test_date_correction_reevaluates_listings_instead_of_inheriting_automatic_currency():
    original = execution(10)
    changed = replace(execution(20), supersedes_execution_id=original.id)
    source = historical(TRADE, end=changed.executed_at)
    values = resolve([original, changed], (source,))
    assert values[original.id].currency_code == "EUR"
    assert values[changed.id].currency_code is None


def test_correction_keeps_explicit_ancestor_priority_but_not_a_document_for_the_old_fact():
    original = execution(10)
    changed = replace(execution(20), supersedes_execution_id=original.id)
    source = document(TRADE, original.id)
    assert resolve([original, changed], (source,))[changed.id].currency_code is None
    explicit = resolve([original, changed], (source,), (confirmed(original),))[changed.id]
    assert explicit.currency_code == "EUR"
    assert explicit.source == "REPLACED_EXECUTION"


def test_replacement_own_document_precedes_derived_confirmation_from_old_execution():
    original = execution(10, "SELL")
    changed = replace(execution(20, "SELL"), supersedes_execution_id=original.id)
    own_source = document(TRADE, changed.id, code="USD")
    value = resolve([original, changed], (own_source,), (confirmed(original),))[changed.id]
    assert value.currency_code == "USD"
    assert value.source == "EXECUTION_DOCUMENT"
    assert value.evidence_ids == (own_source.id,)
    assert value.confirmation_ids == ()


def test_conflicting_replacement_documents_do_not_disappear_behind_ancestor_confirmation():
    original = execution(10, "SELL")
    changed = replace(execution(20, "SELL"), supersedes_execution_id=original.id)
    sources = (
        document(TRADE, changed.id, 9001),
        document(TRADE, changed.id, 9002, code="USD"),
    )
    value = resolve([original, changed], sources, (confirmed(original),))[changed.id]
    assert value.currency_code is None
    assert value.source == "CONFLICT"


def test_corrected_execution_uses_its_own_historical_interval_before_ancestor_currency():
    original = execution(10)
    changed = replace(execution(20), supersedes_execution_id=original.id)
    source = historical(TRADE, start=changed.executed_at, codes=(listing(XETRA, "USD"),))
    value = resolve([original, changed], (source,), (confirmed(original),))[changed.id]
    assert value.currency_code == "USD"
    assert value.source == "HISTORICAL_LISTINGS"
    assert value.evidence_ids == (source.id,)


@pytest.mark.parametrize("conflicting", [False, True])
def test_later_correction_cannot_resurrect_ancestor_currency_across_a_conflicting_source(
    conflicting,
):
    original = execution(10, "SELL")
    middle = replace(execution(11, "SELL"), supersedes_execution_id=original.id)
    latest = replace(execution(12, "SELL"), supersedes_execution_id=middle.id)
    sources = (document(TRADE, middle.id, 9001, code="USD"),)
    if conflicting:
        sources += (document(TRADE, middle.id, 9002),)
    values = resolve([original, middle, latest], sources, (confirmed(original),))
    assert values[original.id].currency_code == "EUR"
    assert values[middle.id].currency_code == (None if conflicting else "USD")
    assert values[latest.id].currency_code is None


def test_source_revision_replaces_old_evidence_and_revocation_does_not_revive_it():
    fact = execution(10)
    first = document(TRADE, fact.id)
    corrected = replace(document(TRADE, fact.id, 9002, code="USD"), supersedes_evidence_id=first.id)
    revoked = replace(
        document(TRADE, fact.id, 9003, code="USD"),
        supersedes_evidence_id=corrected.id,
        revoked=True,
    )
    assert resolve([fact], (first,))[fact.id].currency_code == "EUR"
    corrected_value = resolve([fact], (first, corrected))[fact.id]
    assert corrected_value.currency_code == "USD"
    assert corrected_value.evidence_ids == (corrected.id,)
    assert resolve([fact], (first, corrected, revoked))[fact.id].currency_code is None


def test_unknown_or_conflicting_new_evidence_never_falls_back_to_retired_good_revision():
    fact = execution(10)
    first = historical(TRADE)
    corrected = replace(
        historical(TRADE, 8002, codes=(listing(), listing(FRANKFURT, "USD"))),
        supersedes_evidence_id=first.id,
    )
    assert resolve([fact], (first, corrected))[fact.id].currency_code is None


@pytest.mark.parametrize("problem", ["missing", "fork", "cycle", "wrong_scope", "reversed_time"])
def test_invalid_evidence_revision_graph_never_unlocks_money(problem):
    fact = execution(10)
    first = document(TRADE, fact.id)
    successor = replace(document(TRADE, fact.id, 9002), supersedes_evidence_id=first.id)
    sources = (first, successor)
    if problem == "missing":
        sources = (successor,)
    elif problem == "fork":
        sources = (
            first,
            successor,
            replace(document(TRADE, fact.id, 9003), supersedes_evidence_id=first.id),
        )
    elif problem == "cycle":
        sources = (replace(first, supersedes_evidence_id=successor.id), successor)
    elif problem == "wrong_scope":
        sources = (replace(first, execution_id=UUID(int=99001)), successor)
    elif problem == "reversed_time":
        sources = (first, replace(successor, recorded_at=first.recorded_at - timedelta(days=1)))
    value = resolve([fact], sources)[fact.id]
    assert value.currency_code is None
    assert value.source == "CONFLICT"


def test_explicit_execution_confirmation_can_correct_two_conflicting_source_documents():
    fact = execution(10)
    sources = (
        document(TRADE, fact.id, 9001),
        document(TRADE, fact.id, 9002, code="USD"),
    )
    assert resolve([fact], sources)[fact.id].currency_code is None
    explicit = confirmed(fact)
    resolved = resolve([fact], sources, (explicit,))[fact.id]
    assert resolved.currency_code == "EUR"
    assert resolved.source == "USER_CONFIRMED"
    assert resolved.confirmation_ids == (explicit.id,)


def test_overlapping_historical_sources_with_different_currencies_are_a_conflict():
    fact = execution(10)
    eur = historical(TRADE)
    usd = historical(TRADE, 8002, codes=(listing(XETRA, "USD"),))
    value = resolve([fact], (eur, usd))[fact.id]
    assert value.currency_code is None
    assert value.source == "CONFLICT"


def test_derivation_is_pure_and_deterministic_for_source_and_execution_order():
    facts = (execution(10), execution(11, "SELL"))
    sources = (
        historical(TRADE),
        document(TRADE, facts[0].id, 9001),
        document(TRADE, facts[0].id, 9002),
    )
    before = tuple(asdict(source) for source in sources)
    expected = resolve(facts, sources)
    for source_order in permutations(sources):
        assert resolve(tuple(reversed(facts)), source_order) == expected
    assert tuple(asdict(source) for source in sources) == before
    assert all(fact.currency_confirmation is None for fact in facts)


def test_automatic_provenance_obeys_complete_read_budget_instead_of_truncating():
    fact = execution(10)
    sources = (document(TRADE, fact.id, 9001), document(TRADE, fact.id, 9002))
    with pytest.raises(CurrencyResolutionLimitExceeded):
        resolve_execution_currencies(
            trade=TRADE, executions=[fact], current={}, evidence=sources, max_provenance_links=1
        )
