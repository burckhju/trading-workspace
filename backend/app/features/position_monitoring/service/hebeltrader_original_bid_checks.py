"""Readable input coverage kept separate from implemented rules and operation."""

from dataclasses import replace

from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.position_monitoring.domain.hebeltrader_original_bid import (
    DocumentedSessionMatch,
    OriginalBidAssessment,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_contracts import (
    OriginalBidCheck,
    ProductSessionPrerequisites,
    UnderlyingSessionsAtBid,
)
from app.features.position_monitoring.service.hebeltrader_sessions import REASONS as SESSION_REASONS
from app.features.trade_position.service.valuation_basis import PositionValuationBasis

REASONS = {
    **SESSION_REASONS,
    "NO_CONFIRMED_SAVED_QUOTE_SOURCE": (
        "Für die Position ist noch keine gespeicherte Kursroute bestätigt."
    ),
    "NO_SAVED_QUOTE_FOR_CURRENT_ROUTE": (
        "Für die bestätigte Kursroute fehlt ein gespeicherter Kurs."
    ),
    "SAVED_QUOTE_PROVIDER_UNSUPPORTED": "Die gespeicherte Providerkennung ist nicht unterstützt.",
    "SAVED_QUOTE_ROUTE_IDENTITY_CHANGED": (
        "Die gespeicherte Route passt nicht mehr zu den aktuellen Instrument-/Listingbelegen."
    ),
    "SAVED_QUOTE_HELD_INSTRUMENT_MISMATCH": (
        "Die Kursroute gehört zu einem anderen Instrument als die gehaltene Position."
    ),
    "SAVED_QUOTE_SELECTION_AFTER_READ": "Die Quellenwahl liegt nach dem angezeigten Lesestand.",
    "SAVED_QUOTE_PAYLOAD_INVALID": "Der gespeicherte Kursbeleg verletzt den Datenvertrag.",
    "SAVED_QUOTE_QUALITY_INVALID": "Die gespeicherte technische Kursqualität ist ungeeignet.",
    "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID": (
        "Instrument, Listing, Währung oder Zeitfolge des gespeicherten Kurses sind widersprüchlich."
    ),
    "SAVED_QUOTE_BINDING_OR_PROVENANCE_MISSING": (
        "Die ausdrückliche Bindung oder Herkunft des gespeicherten Kurses fehlt."
    ),
    "ORIGINAL_BID_PRICE_MISSING": "Ein Geldkurs des gehaltenen Optionsscheins fehlt.",
    "ORIGINAL_BID_SIDE_TIME_MISSING": (
        "Eine ausdrückliche Originalzeit für die Geldkursseite fehlt. Gemeinsame Snapshotzeit, "
        "Briefkurszeit und Abrufzeit ersetzen sie nicht."
    ),
    "ORIGINAL_BID_SOURCE_CONTRACT_UNSUPPORTED": (
        "Für diesen Quellenvertrag ist die Bedeutung des separaten Geldkurszeitfelds noch "
        "nicht qualifiziert. Eine neue Quelle wird nicht automatisch freigegeben."
    ),
    "ORIGINAL_BID_AFTER_RETRIEVAL": (
        "Original-Geldkurs oder Quellgenerierung liegen nach dem gespeicherten Abrufzeitpunkt."
    ),
    "ORIGINAL_BID_AFTER_READ": "Die Original-Geldkurszeit liegt nach dem Lesestand.",
    "ORIGINAL_BID_TOO_OLD": (
        "Der Original-Geldkurs ist zum Lesestand älter als die zulässigen 900 Sekunden. "
        "Ein späterer Abruf oder eine nominelle Feedverzögerung macht ihn nicht jünger."
    ),
    "PRODUCT_CALENDAR_ROUTE_MISSING": (
        "Ohne passende bestätigte Kursroute ist kein Produktkalender eindeutig zuordenbar."
    ),
    "PRODUCT_CALENDAR_NOT_ASSESSABLE": "Die dokumentierten Produktsitzungen sind nicht belegbar.",
    "OUTSIDE_DOCUMENTED_PRODUCT_SESSION": (
        "Der betreffende Zeitpunkt liegt außerhalb der vollständig dokumentierten "
        "Produkt-Handelsintervalle."
    ),
}

UNSUITABLE_REASONS = {
    "SESSION_EVIDENCE_WITHDRAWN",
    "SESSION_LISTING_BINDING_MISMATCH",
    "SESSION_OWNER_BINDING_CHANGED",
    "SESSION_DAYS_CONFLICT",
    "ENTRY_TIME_INVALID",
    "ENTRY_TIMEZONE_INVALID",
    "ENTRY_DATE_INTERVAL_INVALID",
    "ENTRY_AFTER_EVALUATION",
    "ENTRY_CALENDAR_DAY_AMBIGUOUS",
    "ENTRY_OUTSIDE_BINDING_VALIDITY",
    "EVALUATION_OUTSIDE_BINDING_VALIDITY",
    "OUTSIDE_DOCUMENTED_PRODUCT_SESSION",
}


def details(reasons: tuple[str, ...]) -> str:
    return " ".join(
        REASONS.get(code, f"Ungeeigneter oder fehlender Beleg: {code}.") for code in reasons
    )


def _session_check(key: str, label: str, match: DocumentedSessionMatch) -> OriginalBidCheck:
    if match.status == "IN_DOCUMENTED_INTERVAL":
        return OriginalBidCheck(
            key,
            label,
            "SATISFIED",
            "Der Zeitpunkt liegt in einem vollständig dokumentierten Produkt-Handelsintervall. "
            "Das ist kein unabhängiger Nachweis eines aktuell offenen Instruments.",
            (),
        )
    return OriginalBidCheck(
        key,
        label,
        "UNSUITABLE" if UNSUITABLE_REASONS.intersection(match.reasons) else "MISSING",
        details(match.reasons),
        match.reasons,
    )


def input_checks(
    *,
    economic: PositionValuationBasis,
    saved: SavedQuoteEvidence,
    bid: OriginalBidAssessment,
    product: ProductSessionPrerequisites,
    underlying: UnderlyingSessionsAtBid,
    applicable: bool,
) -> tuple[OriginalBidCheck, ...]:
    held = OriginalBidCheck(
        "HELD_INSTRUMENT",
        "Gehaltenes Instrument und Kursroute",
        (
            "SATISFIED"
            if saved.quote is not None and saved.route is not None
            else ("MISSING" if saved.reason.startswith("NO_") else "UNSUITABLE")
        ),
        (
            "Gespeicherter Kurs und bestätigte Route gehören zum exakt gehaltenen Optionsschein."
            if saved.quote is not None and saved.route is not None
            else details((saved.reason,))
        ),
        () if saved.quote is not None and saved.route is not None else (saved.reason,),
    )
    time = OriginalBidCheck(
        "ORIGINAL_BID_TIME_AND_AGE",
        "Original-Geldkurszeit und Kursalter",
        (
            "SATISFIED"
            if bid.status == "AVAILABLE"
            else ("UNSUITABLE" if bid.status == "UNSUITABLE" else "MISSING")
        ),
        (
            f"Original-Geldkursalter zum angezeigten Lesestand: {bid.age_seconds} Sekunden; "
            "die Grenze von höchstens 900 Sekunden ist eingehalten."
            if bid.status == "AVAILABLE"
            else details(bid.reasons)
        ),
        bid.reasons,
    )
    if (
        saved.quote is None
        or saved.quote.bid is None
        or economic.currency_status == "UNKNOWN"
        or (economic.currency_status == "KNOWN" and economic.cost_basis_currency is None)
    ):
        currency = OriginalBidCheck(
            "EXECUTION_CURRENCY",
            "Historische Ausführungswährung",
            "MISSING",
            "Eine bekannte historische Einstandswährung und ein passender "
            "gespeicherter Geldkurs werden benötigt. Bereits belegte Kaufwährungen werden "
            "vom Ausführungsowner wiederverwendet.",
            ("EXECUTION_OR_BID_CURRENCY_MISSING",),
        )
    elif (
        economic.currency_status == "MIXED" or saved.quote.currency != economic.cost_basis_currency
    ):
        currency = OriginalBidCheck(
            "EXECUTION_CURRENCY",
            "Historische Ausführungswährung",
            "UNSUITABLE",
            "Kaufbasis und Geldkurs haben gemischte oder unterschiedliche "
            "Währungen. Es erfolgt keine automatische Umrechnung.",
            ("EXECUTION_BID_CURRENCY_MISMATCH",),
        )
    else:
        currency = OriginalBidCheck(
            "EXECUTION_CURRENCY",
            "Historische Ausführungswährung",
            "SATISFIED",
            "Ausführungsowner und Geldkurs belegen dieselbe Währung: "
            f"{economic.cost_basis_currency}. "
            "Der historische Produkt-Preismaßstab bleibt gesondert zu belegen.",
            (),
        )
    count = underlying.count
    if count is not None and count.status == "AVAILABLE":
        sessions = OriginalBidCheck(
            "TWENTY_UNDERLYING_SESSIONS_AT_BID",
            "20 Basiswertsitzungen zur Geldkurszeit",
            "SATISFIED" if count.threshold_reached else "NOT_REACHED",
            f"Zur Original-Geldkurszeit waren {count.completed_sessions} dokumentierte "
            "Basiswertsitzungen nach Tag 0 abgeschlossen. Spätere Sitzungsschlüsse zählen nicht.",
            () if count.threshold_reached else ("TWENTIETH_SESSION_NOT_COMPLETED_AT_BID",),
        )
    else:
        reasons = count.reasons if count is not None else bid.reasons
        sessions = OriginalBidCheck(
            "TWENTY_UNDERLYING_SESSIONS_AT_BID",
            "20 Basiswertsitzungen zur Geldkurszeit",
            "UNSUITABLE" if UNSUITABLE_REASONS.intersection(reasons) else "MISSING",
            details(reasons),
            reasons,
        )
    checks = (
        held,
        time,
        currency,
        _session_check(
            "PRODUCT_SESSION_AT_BID",
            "Dokumentierte Produktsitzung zur Geldkurszeit",
            product.at_bid,
        ),
        _session_check(
            "PRODUCT_SESSION_AT_READ", "Dokumentierte Produktsitzung zum Lesestand", product.at_read
        ),
        sessions,
        OriginalBidCheck(
            "PRICE_SCALE",
            "Historischer Produkt-Preismaßstab",
            "MISSING",
            "Ein Ownerbeleg für den unveränderten oder verifiziert angepassten Preismaßstab "
            "zwischen Optionsschein-Einstand und Geldkurs fehlt. Die vorhandene "
            "Basiswert-/Markenqualifikation bestätigt diesen Produktmaßstab nicht.",
            ("WARRANT_EXECUTION_BID_SCALE_EVIDENCE_MISSING",),
        ),
        OriginalBidCheck(
            "VERIFIED_LIVE_MARKET_STATUS",
            "Verifizierte offene Produktsitzung",
            "MISSING",
            "Ein zeitlich zugeordneter unabhängiger Nachweis der geöffneten Produktsitzung "
            "fehlt. Importierte Kalenderintervalle und der Quelltext zum Handelsstatus "
            "ersetzen diesen Nachweis nicht.",
            ("VERIFIED_LIVE_PRODUCT_SESSION_MISSING",),
        ),
    )
    if applicable:
        return checks
    return tuple(
        replace(
            check,
            status="NOT_APPLICABLE",
            detail=REASONS["POSITION_CLOSED_OR_CANCELLED"],
            reasons=("POSITION_CLOSED_OR_CANCELLED",),
        )
        for check in checks
    )
