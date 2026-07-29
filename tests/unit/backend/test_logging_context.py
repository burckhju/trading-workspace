"""Tests for structured logging context propagation."""

import json
import logging

from app.core.logging.configuration import JsonFormatter
from app.core.logging.context import bind_request_id, get_request_id, reset_request_id


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
