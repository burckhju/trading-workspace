from __future__ import annotations

from app.features.alert.domain.models import Alert, AlertType


def format_position_alert(alert: Alert, *, symbol: str) -> str:
    title = "Stop erreicht" if alert.alert_type is AlertType.STOP_REACHED else "Target erreicht"
    return (
        "Position Alert\n"
        f"{symbol}\n"
        f"{title}\n"
        f"Kurs: {alert.observed_value}\n"
        f"Schwelle: {alert.threshold_value}\n"
        "Trade Management im Trading Workspace prüfen."
    )
