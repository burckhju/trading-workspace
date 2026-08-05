# FT-001 DTOs – Sprint 2 Schritt 8

## Status

Approved for Validation Implementation.

## Architekturprüfung

Die DTO-Schicht liegt ausschließlich unter `backend/app/features/market/api/` und bildet den Transportvertrag der in Schritt 7 freigegebenen REST API ab. Sie enthält keine Repository-Zugriffe, keine Transaktionssteuerung und keine fachlichen Zustandsentscheidungen. Service Commands und Domain Entities bleiben Pydantic- und FastAPI-unabhängig.

## Request-DTOs

- `CreateUnderlyingRequest` einschließlich `CreateListingRequest`
- `UpdateUnderlyingRequest`
- `VersionRequest` für Verifikation, Deaktivierung, Reaktivierung und Primärwechsel
- `AddListingRequest`
- `UpdateListingRequest`

Unbekannte JSON-Felder werden abgelehnt. UUIDs und Enums werden strukturell durch Pydantic geparst. Vertiefte Feldregeln wie Längen, Muster, Wertebereiche und Cross-Field-Validierung folgen ausschließlich in Schritt 9.

Bei PATCH-Requests bleibt die fachlich notwendige Unterscheidung erhalten:

- nicht enthaltenes Feld: keine Änderung,
- explizites `null` bei optionalen Identifikatoren: vorhandenen Wert entfernen.

## Response-DTOs

- `UnderlyingSummaryResponse`
- `UnderlyingDetailResponse`
- `UnderlyingSearchResponse`
- `ListingResponse`
- `TradingVenueResponse` und `TradingVenueListResponse`
- `CurrencyResponse` und `CurrencyListResponse`

Response-DTOs lesen SQLAlchemy-Ergebnisse über Pydantics `from_attributes`. Router enthalten keine manuelle UUID-, Enum- oder Datetime-Serialisierung mehr. Listen- und Detailantworten besitzen getrennte Verträge, damit die Suche keine Listings implizit lädt oder serialisiert.

## OpenAPI

Alle fachlichen Endpunkte deklarieren explizite `response_model`-Typen. Dadurch enthält OpenAPI benannte und wiederverwendbare Schemas für Requests und Responses. Diese Schemas bilden die Grundlage für den React API Client in Schritt 11.

## Tests

Die DTO- und REST-Tests prüfen:

- benannte OpenAPI-Schemas,
- strukturell typisierte UUIDs und Enums,
- Ablehnung unbekannter Felder,
- Verhinderung eines Serviceaufrufs bei fehlerhaftem Transport,
- ORM-basierte Response-Serialisierung,
- Unterscheidung von ausgelassenen und explizit geleerten Identifikatoren,
- unveränderte Pfade, Statuscodes und Service-Delegation.

## Abschlussreview

- Die in Schritt 7 festgelegten Pfade und Semantiken bleiben unverändert.
- Es existiert genau eine DTO-Lösung im API-Paket.
- Keine fachliche Validierung wurde aus der Domain dupliziert.
- Keine Validierungsentscheidung aus Schritt 9 wurde vorgezogen.
- DTOs, Router, OpenAPI, Tests und Dokumentation sind synchron.

## Vertragserweiterung vor Frontend Views

Hinzugefügt wurden `PrimaryListingSummaryResponse`, `AuditEventResponse`, `AuditEventListResponse`, `UnderlyingUsageResponse` und `UnderlyingUsageListResponse`. `UnderlyingSummaryResponse.primary_listing` ist für aktive, konsistente Datensätze gesetzt. `ListingResponse` trägt neben der stabilen Handelsplatz-ID auch MIC und Anzeigenamen.
