from __future__ import annotations

import inspect

from app.features.learning.application.external_trade_creator import (
    SqlAlchemyExternalTradeCreator,
)


def test_external_trade_creator_exposes_async_create() -> None:
    assert inspect.iscoroutinefunction(SqlAlchemyExternalTradeCreator.create)
