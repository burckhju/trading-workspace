from uuid import uuid4

from app.features.operational_workspace.service.prioritization import (
    _product_detail,
    _product_title,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
)
from app.features.position_monitoring.service.quote_sources import (
    QuoteSourceAttempt,
    QuoteSourceAttemptStatus,
)


def test_missing_stuttgart_quote_is_explained_as_feed_coverage_gap() -> None:
    valuation = ProductPositionValuation(
        trade_id=uuid4(),
        position_id=uuid4(),
        status=ProductValuationStatus.MISSING,
        reason="NO_USABLE_WARRANT_QUOTE",
        source_attempts=(
            QuoteSourceAttempt(
                source="BOERSE_STUTTGART_DELAYED",
                status=QuoteSourceAttemptStatus.MISSING,
                reason="NO_QUOTE_RETURNED",
                delayed=True,
            ),
        ),
    )

    assert _product_title(valuation) == "Produkt nicht im Stuttgart-Feed enthalten"
    detail = _product_detail(valuation)
    assert "Börse-Stuttgart-Delayed-Feed" in detail
    assert "Marktwert und unrealized P&L werden nicht geschätzt" in detail
