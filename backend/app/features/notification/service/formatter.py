from __future__ import annotations

from app.features.alert.domain.models import Alert, AlertType


def _display_text(value: str | None, *, missing: str = "—") -> str:
    """Keep master-data labels on one plain-text line; never infer missing identity."""
    return " ".join((value or "").split()) or missing


def format_position_alert(
    alert: Alert,
    *,
    symbol: str,
    warrant_name: str | None = None,
    warrant_isin: str | None = None,
    warrant_wkn: str | None = None,
) -> str:
    title = {
        AlertType.STOP_REACHED: "Stop erreicht",
        AlertType.TARGET_REACHED: "Target erreicht",
        AlertType.RISK_TREND_CHANGED: "Trendverschlechterung (indikativ)",
        AlertType.RISK_VOLATILITY_HIGH: "Erhöhte realisierte Volatilität",
    }[alert.alert_type]
    if alert.alert_type in {AlertType.RISK_TREND_CHANGED, AlertType.RISK_VOLATILITY_HIGH}:
        context = alert.price_context or {}
        return (
            f"Position Alert\nOptionsschein: {_display_text(warrant_name)}\n"
            f"WKN: {_display_text(warrant_wkn)} | ISIN: {_display_text(warrant_isin)}\n"
            f"{symbol}\n{title}\nMesswert: {alert.observed_value * 100}%\n"
            f"Regelparameter: {alert.threshold_value * 100}%\n"
            f"Regel: {context.get('policy_version')} / "
            f"Revision {context.get('configuration_revision')}\n"
            f"Handelstag: {context.get('trading_date')}\nQuelle: {context.get('provider')}\n"
            f"Grund: {alert.reason}\nBeschreibender Risikohinweis. Keine Orderfreigabe."
        )
    context = alert.price_context or {}
    if context.get("evaluation_mode") == "INDICATIVE_ISSUER":
        title += " (indikative Prüfung)"
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
                    ("Zeitangabe der Quelle", "quote_time_text"),
                    ("Zeitbasis", "quote_time_basis"),
                    ("Abgerufen", "retrieved_at"),
                    ("Handelstag", "trading_date"),
                    ("Hinweis", "warning"),
                )
            )
            + "\nKeine Orderfreigabe.\n"
        )
    return (
        "Position Alert\n"
        f"Optionsschein: {_display_text(warrant_name, missing='Name nicht verfügbar')}\n"
        f"WKN: {_display_text(warrant_wkn)} | ISIN: {_display_text(warrant_isin)}\n"
        f"{symbol}\n"
        f"{title}\n"
        f"Kurs: {alert.observed_value}\n"
        f"Schwelle: {alert.threshold_value}\n"
        f"{details}"
        "Trade Management im Trading Workspace prüfen."
    )
