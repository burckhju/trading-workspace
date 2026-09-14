from __future__ import annotations

from app.features.alert.domain.models import Alert, AlertType


def format_position_alert(alert: Alert, *, symbol: str) -> str:
    title = "Stop erreicht" if alert.alert_type is AlertType.STOP_REACHED else "Target erreicht"
    context = alert.price_context or {}
    details = ""
    if context:
        details = (
            "\n".join(
                f"{label}: {context.get(key) or '—'}"
                for label, key in (
                    ("Kursbezug", "basis"),
                    ("Währung", "currency"),
                    ("Kursart", "price_type"),
                    ("Quelle", "provider"),
                    ("Provider-ID", "provider_identity"),
                    ("Kurszeitpunkt", "observed_at"),
                    ("Handelstag", "trading_date"),
                    ("Hinweis", "warning"),
                )
            )
            + "\nKeine Orderfreigabe.\n"
        )
    return (
        "Position Alert\n"
        f"{symbol}\n"
        f"{title}\n"
        f"Kurs: {alert.observed_value}\n"
        f"Schwelle: {alert.threshold_value}\n"
        f"{details}"
        "Trade Management im Trading Workspace prüfen."
    )
