# ruff: noqa: I001

from app.features.learning.application.hebeltrader_parser import parse_hebeltrader_text

BASE = """
10.07.2026 · # 122/2026
Kinder Morgan:
KI-Boom trifft Pipeline-Gigant!
Kinder Morgan
Optionsschein Call
WKN JE85E1
Akt. Kurs** 0,046 €
Ziel 1 0,24 €
Ziel 2 0,79 €
Stopp 1 0,015 €
Stopp 2 0,046 €
Basispreis 38,00 $
Omega/Hebel 11,2
Laufzeit 18.12.26
**Kursindikation, Stand: 10.07.2026 um 08:15 Uhr
Potenzial Risiko
Aktie +20% -8%
Hebelprodukt +424% -67%
CHARTTECHNISCHES BILD AKTIE
Basiswert Kinder Morgan
WKN A1H6GK
Akt. Kurs 32,40 $
Kursziel 1 39,00 $
Kursziel 2 47,00 $
Stopp 1 30,00 $
Stopp 2 32,40 $
GD50 32,15 $
GD200 30,60 $
"""


def test_extracts_core_recommendation_fields() -> None:
    result = parse_hebeltrader_text(BASE)

    assert result.issue_number == 122
    assert result.underlying_name == "Kinder Morgan"
    assert result.underlying_wkn == "A1H6GK"
    assert result.derivative_wkn == "JE85E1"
    assert result.derivative_type == "OPTIONSSCHEIN_CALL"
    assert str(result.derivative_indicated_price) == "0.046"
    assert str(result.strike) == "38.00"
    assert result.strike_currency == "USD"
    assert str(result.omega_or_leverage) == "11.2"
    assert str(result.underlying_price) == "32.40"
    assert str(result.stock_upside_pct) == "20"
    assert str(result.derivative_risk_pct) == "-67"
    assert result.validation_issues == ()


def test_preserves_mismatching_source_timestamp_as_issue() -> None:
    result = parse_hebeltrader_text(BASE.replace("10.07.2026 um", "10.07.2025 um"))

    assert result.price_indication_at is not None
    assert result.price_indication_at.year == 2025
    assert [issue.code for issue in result.validation_issues] == ["PRICE_INDICATION_DATE_MISMATCH"]


def test_marks_source_placeholder_without_correcting_it() -> None:
    result = parse_hebeltrader_text(BASE + "\nStand: Xx.xx.26\n")

    assert "SOURCE_PLACEHOLDER_DATE" in {issue.code for issue in result.validation_issues}
