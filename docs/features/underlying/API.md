# FT-001 API Contract – fachliche Spezifikation

## Grundsätze

- Ressourcenname: `underlyings`.
- Listings sind untergeordnete Ressourcen oder Bestandteil eines transaktionalen Anlagecommands.
- Fehlerantworten enthalten stabilen Fehlercode, verständliche Meldung und betroffene Felder.
- Die technische Ausprägung wurde in Sprint 2 Schritt 7 finalisiert; siehe `REST_API.md`.

## Vorgesehene Fähigkeiten

| Fähigkeit | Semantik |
|---|---|
| Basiswertliste lesen | Suche, Filter, Sortierung, Pagination |
| Basiswertdetail lesen | Grunddaten, Listings, Status und Verwendungssummary |
| Basiswert anlegen | Underlying plus primäre Notierung atomar anlegen |
| Basiswert ändern | explizite Felder ändern; keine stille Überschreibung |
| Listing ergänzen/ändern | Eindeutigkeit und Primärregel prüfen |
| deaktivieren | Statuswechsel; bestehende Referenzen erhalten |
| reaktivieren | dasselbe Objekt reaktivieren |
| löschen | nur ohne Referenzen |

## Fachliche Fehlercodes

- `UNDERLYING_DUPLICATE_ISIN`
- `UNDERLYING_DUPLICATE_WKN`
- `LISTING_DUPLICATE_MARKET_TICKER`
- `UNDERLYING_PRIMARY_LISTING_REQUIRED`
- `UNDERLYING_MULTIPLE_PRIMARY_LISTINGS`
- `UNDERLYING_DELETE_REFERENCED`
- `UNDERLYING_TYPE_NOT_SUPPORTED`
- `UNDERLYING_CONCURRENT_MODIFICATION`
- `UNDERLYING_INVALID_ISIN`
- `UNDERLYING_INVALID_WKN`
- `UNDERLYING_NOT_OPERATIONALLY_COMPLETE`

## Verbindliche Vertragsregeln für Sprint 2

- Schreiboperationen übertragen die gelesene Versionsnummer; Abweichungen führen zu `UNDERLYING_CONCURRENT_MODIFICATION`.
- Marktwerte werden als `trading_venue_id`, Währungen als kontrollierte ISO-4217-Codes übertragen.
- Die Verwendungsübersicht enthält Referenzart, Anzahl und bei berechtigter Detailabfrage stabile Objekt-IDs.
- Validierungsfehler unterscheiden Formatfehler, Dubletten und Statusverletzungen.
- Exakte REST-Pfade, HTTP-Verben und Statuscodes sind in `REST_API.md` festgelegt.
