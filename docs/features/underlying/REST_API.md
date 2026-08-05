# FT-001 REST API – Sprint 2 Schritt 7

## Status

Approved for DTO implementation.

## Architekturprüfung

Die API ist ein reiner FastAPI-Adapter über dem freigegebenen Service Layer. Endpunkte erzeugen keine Repositories und steuern keine Transaktionen. Der unsichtbare Version-1-Workspace wird serverseitig mit der in ADR-S2-001 festgelegten UUID gesetzt. Fach- und Servicefehler werden in den zentralen Fehlervertrag übersetzt.

## Versionierung und Ressourcen

Basispräfix: `/api/v1`.

| Methode | Pfad | Semantik | Erfolg |
|---|---|---|---|
| GET | `/underlyings` | Suche, Lifecycle-Filter und Pagination | 200 |
| POST | `/underlyings` | Underlying mit primärer Notierung atomar anlegen | 201 |
| GET | `/underlyings/{underlying_id}` | Detail einschließlich Listings lesen | 200 |
| PATCH | `/underlyings/{underlying_id}` | explizite Stammdatenänderung mit Version | 200 |
| POST | `/underlyings/{underlying_id}/verify` | verifizieren | 200 |
| POST | `/underlyings/{underlying_id}/deactivate` | deaktivieren | 200 |
| POST | `/underlyings/{underlying_id}/reactivate` | reaktivieren | 200 |
| DELETE | `/underlyings/{underlying_id}?version=…` | nur unreferenziert physisch löschen | 204 |
| POST | `/underlyings/{underlying_id}/listings` | Listing ergänzen | 201 |
| PATCH | `/underlyings/{underlying_id}/listings/{listing_id}` | Listing ändern | 200 |
| PUT | `/underlyings/{underlying_id}/primary-listing/{listing_id}` | Primärnotierung setzen | 200 |
| GET | `/market-reference-data/trading-venues` | aktive kontrollierte Handelsplätze | 200 |
| GET | `/market-reference-data/currencies` | aktive kontrollierte Währungen | 200 |

## Nebenläufigkeit

Alle ändernden Operationen übertragen eine gelesene Version. Underlying-Änderungen verwenden `version`; Listing-Änderungen und Primärwechsel verwenden die Listing-Version. Abweichungen werden als HTTP 409 mit `UNDERLYING_CONCURRENT_MODIFICATION` beantwortet.

## Fehlerabbildung

- nicht vorhandene Ressourcen: 404,
- Dubletten, Referenzkonflikte, Löschreferenzen und Versionskonflikte: 409,
- fachliche Regel- und Formatverletzungen: 422,
- erfolgreiche Löschung: 204 ohne Response Body.

Die Antwort verwendet unverändert den zentralen Vertrag mit `code`, `message`, `details` und `timestamp`. Löschkonflikte liefern Referenzart und stabile Objekt-ID in den Details.

## Actor und Workspace

Der Workspace wird nicht vom Client übertragen. Für die bis zur Authentifizierungsimplementierung erforderliche Audit-Zuordnung akzeptiert die API optional `X-Actor-ID` und `X-Actor-Name`. Fehlen sie, wird der technische Anzeigename `Trading Workspace User` verwendet. Diese Header sind keine Authentifizierung und gewähren keine Berechtigung.

## Abgrenzung

Schritt 7 fixiert Pfade, Verben, Statuscodes, Dependency Injection, Serialisierung und Fehlersemantik. Dedizierte Pydantic Request-/Response-DTOs folgen in Schritt 8. Vertiefte Transportvalidierungen folgen in Schritt 9. Die lokale JSON-Extraktion ist deshalb eine bewusst vorläufige Transportgrenze und enthält keine neue Fachlogik.

## Abschlussreview

- ausschließlich FT-001 und dessen kontrollierte Referenzdaten-Lesezugriffe umgesetzt,
- keine Datenbankzugriffe aus Endpunkten,
- keine Transaktionssteuerung in der API,
- keine doppelte Referenzdatenhaltung,
- versionierter API-Pfad,
- Service-, Domain- und Fehlerverträge bleiben unverändert,
- OpenAPI enthält alle freigegebenen Routen,
- freigegeben für Schritt 8 „DTOs“.

## Ergänzung für die freigegebenen Frontend Views (2026-08-04)

- `GET /api/v1/underlyings` akzeptiert zusätzlich `trading_venue_id` und `currency_code`.
- `GET /api/v1/underlyings/{underlying_id}/audit-events` liefert die paginierte Historie des Basiswerts einschließlich seiner Listings.
- `GET /api/v1/underlyings/{underlying_id}/usages` liefert die nach Verwendungstyp gruppierte Verwendungsübersicht.
- Summary-Antworten enthalten `primary_listing`; Listing-Antworten enthalten Handelsplatz-MIC und -Name.
