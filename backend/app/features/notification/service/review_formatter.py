"""Plain-text review notices with explicit price and non-price semantics."""

from app.features.alert.domain.models import Alert, AlertType


def format_review_alert(
    alert: Alert,
    *,
    symbol: str,
    warrant_name: str | None,
    warrant_isin: str | None,
    warrant_wkn: str | None,
) -> str:
    def label(value: str | None) -> str:
        return " ".join((value or "").split()) or "—"

    context = alert.price_context or {}
    titles = {
        AlertType.INDICATIVE_ENTRY_LOSS: "Preisindikation unter persönlichem Bruttoeinstand",
        AlertType.POSITION_REVIEW_DUE: "Positionsprüfung nach 20 Basiswertsitzungen fällig",
        AlertType.POSITION_DATA_UNAVAILABLE: "Daten für die Positionsprüfung fehlen",
    }
    lines = [
        "Positionsprüfung",
        f"Optionsschein: {label(warrant_name)}",
        f"WKN: {label(warrant_wkn)} | ISIN: {label(warrant_isin)}",
        label(symbol),
        titles[alert.alert_type],
        "Gesonderter Prüfhinweis; keine qualifizierte B04/B57-Bewertung.",
    ]
    if alert.alert_type is AlertType.INDICATIVE_ENTRY_LOSS:
        if alert.observed_value is None or alert.threshold_value is None:
            raise ValueError("Indicative entry notice requires a BID and gross entry")
        lines += [
            f"BID-Indikation: {alert.observed_value} {label(context.get('currency'))}",
            f"Persönlicher Bruttoeinstand je Stück: {alert.threshold_value} "
            f"{label(context.get('currency'))}",
            f"Original-Geldkurszeit: {label(context.get('observed_at'))}",
            f"Abgerufen: {label(context.get('retrieved_at'))}",
            f"Zeitangabe der Quelle: {label(context.get('quote_time_text'))}",
        ]
        if context.get("evaluation_mode") == "INDICATIVE_ISSUER":
            lines.append(
                "Originalkurszeit und Kursfrische unbekannt. Die Sitzungszahl belegt nur "
                "die fällige Positionsprüfung; Empfangszeit ist keine Originalkurszeit."
            )
        elif context.get("evaluation_mode") == "SOURCE_BID":
            lines.append("Sitzungszahl zur Original-BID-Zeit; Marktöffnung nicht B58-qualifiziert.")
        else:
            lines.append("Zeitbezug der Preisindikation nicht belegt.")
    else:
        if alert.observed_value is not None or alert.threshold_value is not None:
            raise ValueError("Non-price review notice must not carry numeric price values")
        lines.append("Dieser Hinweis stellt keinen Kursverlust und keine Erholung fest.")
    review_due = alert.alert_type is AlertType.POSITION_REVIEW_DUE
    sessions = context.get("review_completed_sessions" if review_due else "completed_sessions")
    session_at = context.get("review_session_count_at" if review_due else "session_count_at")
    lines += [
        f"Abgeschlossene Basiswertsitzungen: {label(sessions)}",
        f"Bezug der Sitzungszählung: {label(session_at)}",
        f"Quelle: {label(context.get('provider'))}",
        f"Regelversion: {label(context.get('rule_version'))}",
        f"Festgestellt: {alert.detected_at.isoformat()}",
        f"Grund: {label(alert.reason)}",
        "Im Trading Workspace prüfen. Keine Order und keine automatische Stop- oder Zieländerung.",
    ]
    return "\n".join(lines)
