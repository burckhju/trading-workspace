# ADR-S3-002 – Capability-basierte Providercontracts

## Status

Accepted – 2026-08-05

## Kontext

Provider unterstützen unterschiedliche Datenarten. Ein großer universeller Contract würde nicht unterstützte Methoden, Dummy-Implementierungen oder EODHD-Begriffe in der Fachlogik erzwingen.

## Entscheidung

Providercontracts werden als kleine asynchrone Python-`Protocol`s je Fähigkeit definiert. Sprint 3 verwendet mindestens `HistoricalDailyPriceProvider`, `LatestCompletedDailyPriceProvider` und `ProviderInstrumentResolver`.

Contracts und interne Modelle liegen in `features/market_data`; konkrete Adapter liegen in `providers/<provider>`.

## Konsequenzen

- neue Provider können Fähigkeiten selektiv implementieren,
- Application Services hängen nicht von EODHD ab,
- Contract-Tests können je Fähigkeit wiederverwendet werden,
- die Zahl kleiner Schnittstellen steigt bewusst an.
