# Sprint 3 – Arbeitseinheit 8: REST-API und Fehlervertrag

Status: Implementiert

## Umfang

- providerunabhängiger Import-Endpunkt für historische EOD-Tageskurse
- Pydantic-DTOs ohne EODHD-Transportstrukturen
- session-scoped Importservice über den Application Container
- Request-ID als Correlation-ID
- Zeitraumvalidierung mit maximal zehn Jahren
- stabile Übersetzung aller Market-Data-Fehler in das zentrale API-Fehlerformat
- API-, OpenAPI- und Regressionstests

## Endpunkt

`POST /api/v1/market-data/daily-prices/import`

Der Endpunkt importiert abgeschlossene Tageskurse idempotent für ein bestehendes Listing und ein freigegebenes Provider-Mapping. Die feste Workspace-ID entspricht weiterhin dem bestehenden Single-Workspace-Vertrag von FT-001.

## Architekturgrenzen

- Der öffentliche Vertrag enthält keine EODHD-Feldnamen, URLs oder Tarifbezeichnungen.
- Der Router kennt ausschließlich `DailyPriceImportService` und providerunabhängige Requests/Resultate.
- Die Datenbanksession wird durch die Container-Factory geöffnet und nach dem Request geschlossen.
- Die Request-ID aus dem Middleware-Kontext wird als UUID-Correlation-ID an den Service übergeben.

## Fehlervertrag

Market-Data-Fehler werden unter ihren stabilen internen Codes ausgegeben. Authentifizierungs- und Konfigurationsprobleme ergeben 503, fehlende Mappings 404, Entitlement-Probleme 403, Limits 429 und ungültige Providerdaten 502. `Retry-After` wird ausschließlich als kontrollierter Sekundenwert im Detailkontext veröffentlicht.

## Quality Gate

- 159 Unit-, Contract- und Integrationstests erfolgreich
- Python-Kompilierung erfolgreich
- kein Live-EODHD-Zugriff
