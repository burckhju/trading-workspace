"""Tests for secret-safe EODHD redaction helpers."""

from app.providers.eodhd.redaction import REDACTED, redact_query_params, redact_url


def test_redact_query_params_does_not_mutate_input() -> None:
    original = {"api_token": "secret", "fmt": "json"}
    redacted = redact_query_params(original)
    assert redacted == {"api_token": REDACTED, "fmt": "json"}
    assert original["api_token"] == "secret"


def test_redact_url_hides_known_secret_parameters() -> None:
    value = redact_url("https://eodhd.com/api/eod/SAP?api_token=secret&fmt=json")
    assert "secret" not in value
    assert "api_token=%2A%2A%2AREDACTED%2A%2A%2A" in value
    assert "fmt=json" in value
