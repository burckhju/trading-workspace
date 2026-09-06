"""Tests for request access-log performance metrics."""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.logging.context import record_database_query
from app.core.middleware import RequestContextMiddleware


def test_access_log_includes_request_scoped_database_metrics(caplog) -> None:
    application = FastAPI()
    application.add_middleware(RequestContextMiddleware)

    @application.get("/measured")
    async def measured() -> dict[str, str]:
        record_database_query(1.25)
        record_database_query(2.75)
        return {"status": "ok"}

    with caplog.at_level(logging.INFO, logger="app.core.middleware.request_context"):
        response = TestClient(application).get("/measured")

    assert response.status_code == 200
    record = next(entry for entry in caplog.records if entry.msg == "http_request_completed")
    assert record.db_query_count == 2
    assert record.db_query_duration_ms == 4.0
    assert record.duration_ms >= 0
