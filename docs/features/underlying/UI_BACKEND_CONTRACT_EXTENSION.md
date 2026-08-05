# FT-001 UI-Backend-Vertragserweiterung

Status: Accepted and implemented, Sprint 2 correction before Frontend Views.

## Anlass

Die freigegebene UI benötigt Primärnotierungsdaten in der Liste, serverseitige Handelsplatz- und Währungsfilter, eine Änderungshistorie sowie eine Verwendungsübersicht. Diese Lesepfade waren in den bis Schritt 11 stabilisierten Verträgen nicht vollständig vorhanden. Frontend-Workarounds, N+1-Abfragen oder lokale Filterung paginierter Teilmengen sind unzulässig.

## Umgesetzte Entscheidungen

1. `UnderlyingSummaryResponse` enthält `primary_listing` mit Ticker, Handelsplatz-ID, MIC, Name und Währung.
2. Die Suche akzeptiert `trading_venue_id` und `currency_code`; beide Filter berücksichtigen aktive Listings und werden serverseitig auf den vollständigen Datenbestand angewendet.
3. `GET /api/v1/underlyings/{underlying_id}/audit-events` liefert eine absteigend chronologische, paginierte Historie für Underlying und zugehörige Listings.
4. `GET /api/v1/underlyings/{underlying_id}/usages` verwendet denselben Usage-Repository-Vertrag wie der Löschschutz und gruppiert Verwendungen nach Typ.
5. `ListingResponse` enthält zusätzlich Handelsplatz-MIC und Handelsplatzname. In Detail- und Suchlesepfaden werden diese Werte serverseitig angereichert.

## Architekturwirkung

- Keine doppelte Referenzdatenhaltung im Frontend.
- Keine N+1-Detailabfragen für die Listenansicht.
- Anzeige und Löschschutz greifen auf dieselbe Verwendungsquelle zu.
- Auditdaten bleiben append-only; hinzugefügt wurde ausschließlich ein Lesepfad.
- Bestehende Schreibregeln, Transaktionen und Domaininvarianten bleiben unverändert.

## Nutzerwirkung

Der Nutzer sieht die Primärnotierung direkt in der Liste, erhält korrekte markt- und währungsbezogene Trefferzahlen, kann Änderungen nachvollziehen und Verwendungen vor einer Löschentscheidung prüfen.
