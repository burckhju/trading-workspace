# Sprint 3 – Arbeitseinheit 6: Application Service und Persistenzorchestrierung

## Status

Abgeschlossen.

## Umfang

- providerunabhängiger `DailyPriceImportService`
- explizite Unit-of-Work-Transaktion
- idempotentes Insert/Update/No-op-Verhalten
- Importergebnis mit Provider-, Cache-, Qualitäts- und Kostenmetadaten
- Schutz gegen Cross-Listing-Providerdaten
- tarifneutrale EODHD-Betriebskonfiguration

## Transaktionsregel

Der Providerabruf und die Persistenzorchestrierung werden durch den Application Service koordiniert. Repositories führen keinen Commit aus. Ein Commit erfolgt nur, wenn mindestens ein Datensatz neu angelegt oder fachlich geändert wurde. Bei Fehlern wird die Unit of Work zurückgerollt.

## Idempotenz

Die fachliche Eindeutigkeit bleibt `(listing_id, trading_date, price_type)`. Für jeden Providerwert gilt:

- nicht vorhanden: Insert,
- vorhanden und geändert: Update,
- vorhanden und identisch: No-op.

Das Ergebnis weist `inserted`, `updated` und `unchanged` getrennt aus.

## Paid-Account-Kompatibilität EODHD

Die Implementierung ist nicht auf den kostenlosen Tarif zugeschnitten. Folgende Werte sind konfigurierbar:

- `daily_call_limit`
- `daily_call_safety_reserve`
- `requests_per_minute`
- `historical_eod_call_cost`

Damit können Free-, Paid- und zusätzlich erworbene Kontingente ohne Änderung an Domain oder Application Service abgebildet werden. Die konkrete produktive Konfiguration bleibt Deploymentverantwortung.

## Nicht enthalten

- Dependency-Injection-Verkabelung
- REST-API
- öffentliche API-Fehlerübersetzung
- Metriken
- User-API-Abgleich des tatsächlichen EODHD-Verbrauchs
- PostgreSQL-Live-Integrationstest
