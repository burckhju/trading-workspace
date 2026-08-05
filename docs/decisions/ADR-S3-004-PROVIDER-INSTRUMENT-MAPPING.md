# ADR-S3-004 – Separates Provider-Instrument-Mapping

## Status

Accepted – 2026-08-05

## Kontext

Ticker und Handelsplatz aus FT-001 sind fachliche Stammdaten. EODHD-Symbol und EODHD-Exchange-Code sind providerbezogene Identifikatoren und können sich unabhängig ändern.

## Entscheidung

Die Zuordnung wird als eigenes `ProviderInstrumentMapping` im Feature `market_data` geführt. In Sprint 3 wird sie manuell angelegt und anschließend providerseitig validiert. Providerdaten ändern keine FT-001-Felder.

## Konsequenzen

- kein Provider-Lock-in im Listingmodell,
- explizite Pflegehandlung für neue Listings,
- Mappingfehler sind sichtbar und auditierbar,
- spätere automatische Vorschläge benötigen weiterhin Freigabe.
