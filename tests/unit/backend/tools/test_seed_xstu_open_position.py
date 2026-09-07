import argparse
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.tools.seed_xstu_open_position import (
    LOCAL_ACTOR_ID,
    _candidate_statement,
    _positive_decimal,
    _positive_int,
    _timestamp,
    build_parser,
)


def test_parser_requires_explicit_purchase_price() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_defaults_to_one_unit_and_local_actor() -> None:
    args = build_parser().parse_args(["--price", "2.42"])

    assert args.quantity == 1
    assert args.price == Decimal("2.42")
    assert args.actor_id == LOCAL_ACTOR_ID
    assert args.selection_id is None
    assert args.force_new is False


def test_positive_value_parsers_reject_zero_and_negative_values() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_decimal("0")
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_decimal("-1")
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("0")
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("-1")


def test_timestamp_requires_timezone_and_normalizes_to_utc() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _timestamp("2026-09-07T18:00:00")

    value = _timestamp("2026-09-07T20:00:00+02:00")

    assert value == datetime(2026, 9, 7, 18, 0, tzinfo=UTC)


def test_candidate_statement_is_restricted_to_workspace_xstu_and_optional_selection() -> None:
    workspace_id = UUID("00000000-0000-4000-8000-000000000001")
    selection_id = UUID("11111111-1111-4111-8111-111111111111")

    sql = str(
        _candidate_statement(
            workspace_id=workspace_id,
            selection_id=selection_id,
        )
    )

    assert "product_selection_runs.workspace_id" in sql
    assert "trading_venues.mic" in sql
    assert "product_selections.id" in sql
    assert "warrants.isin IS NOT NULL" in sql
