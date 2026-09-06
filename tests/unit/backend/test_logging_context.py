"""Tests for structured logging context propagation."""

import json
import logging

from app.core.logging.configuration import JsonFormatter
from app.core.logging.context import (
    bind_database_query_stats,
    bind_request_id,
    get_database_query_stats,
    get_request_id,
    record_database_query,
    reset_database_query_stats,
    reset_request_id,
)


def test_request_id_is_scoped_and_added_to_json_logs() -> None:
    token = bind_request_id("b493b3ea-38e8-44d8-80c8-47c5acfaa9c4")
    try:
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
        payload = json.loads(JsonFormatter().format(record))

        assert get_request_id() == "b493b3ea-38e8-44d8-80c8-47c5acfaa9c4"
        assert payload["request_id"] == "b493b3ea-38e8-44d8-80c8-47c5acfaa9c4"
    finally:
        reset_request_id(token)

    assert get_request_id() is None


def test_database_query_stats_are_request_scoped() -> None:
    assert get_database_query_stats().count == 0

    token = bind_database_query_stats()
    try:
        record_database_query(1.25)
        record_database_query(2.75)
        stats = get_database_query_stats()

        assert stats.count == 2
        assert stats.duration_ms == 4.0
    finally:
        reset_database_query_stats(token)

    assert get_database_query_stats().count == 0
    assert get_database_query_stats().duration_ms == 0.0
