"""Date reminders disclose their precision without borrowing a price claim."""

from dataclasses import replace
from decimal import Decimal

import pytest
from tests.unit.backend.features.notification.test_position_review_alerts import review_alert
from tests.unit.backend.features.notification.test_warrant_name import ISIN, NAME, WKN

from app.features.alert.domain.models import AlertType
from app.features.notification.service.formatter import format_position_alert


@pytest.mark.parametrize(
    "kind", [AlertType.PRODUCT_DEADLINE_REVIEW, AlertType.POSITION_DATA_UNAVAILABLE]
)
@pytest.mark.parametrize("precision", ["DAY_ONLY", "ORIGINAL_SESSION_TIMES"])
def test_product_deadline_alert_is_price_independent_and_preserves_actual_detection(
    kind, precision
):
    item = replace(
        review_alert(kind),
        price_context={
            "scope": "DOCUMENTED_PRODUCT_DEADLINE_REVIEW_V1",
            "rule_version": "product-deadline-review-v1",
            "calendar_precision": precision,
            "scheduled_on": "2026-11-17",
            "scheduled_at": "2026-11-17T07:00:00+00:00" if precision != "DAY_ONLY" else None,
            "last_trading_on": "2026-12-17",
            "maturity_on": "2026-12-18",
            "exit_venue_mic": "XSTU",
        },
    )
    body = format_position_alert(
        item, symbol=ISIN, warrant_name=NAME, warrant_isin=ISIN, warrant_wkn=WKN
    )
    for expected in (
        NAME,
        ISIN,
        WKN,
        "product-deadline-review-v1",
        "B05-Teilumfang",
        "produktspezifischer Handelsschluss nicht qualifiziert",
        "XSTU",
        "2026-12-17",
        "2026-12-18",
        "Tatsächlich festgestellt: " + item.detected_at.isoformat(),
    ):
        assert expected in body
    for invented_claim in (
        "BID",
        "Einstand",
        "Basiswertsitzungen",
        "Original-Geldkurszeit",
        "None",
    ):
        assert invented_claim not in body
    if precision == "DAY_ONLY":
        assert "Erinnerungstag: 2026-11-17" in body
        assert "individuelle Öffnungs- und Schlusszeiten unbekannt" in body
        assert "Kalendertermin:" not in body
    else:
        assert "Kalendertermin: 2026-11-17T07:00:00+00:00" in body
        assert "kein verifizierter Produkthandelsschluss" in body


def test_product_deadline_formatter_rejects_a_fabricated_price_threshold():
    item = replace(review_alert(AlertType.PRODUCT_DEADLINE_REVIEW), threshold_value=Decimal("1"))
    with pytest.raises(ValueError, match="must not carry numeric price values"):
        format_position_alert(item, symbol=ISIN)
