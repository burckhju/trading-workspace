import json
import logging

from app.core.logging.configuration import JsonFormatter


def test_json_formatter_emits_structured_log_record() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "123"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"
    assert payload["message"] == "completed"
    assert payload["request_id"] == "123"
    assert payload["timestamp"].endswith("+00:00")
