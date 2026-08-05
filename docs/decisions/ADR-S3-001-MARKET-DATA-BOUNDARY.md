# ADR-S3-001 – Eigenständige Marktdaten-Fähigkeit

## Status

Accepted – 2026-08-05

## Kontext

FT-001 besitzt Basiswerte und Listings. Marktdaten haben einen eigenen Lebenszyklus, eigene Qualitätsregeln und externe Abhängigkeiten. Eine Erweiterung des bestehenden Features würde Stammdaten und zeitabhängige Daten vermischen.

## Entscheidung

Sprint 3 führt die technische Featuregrenze `app/features/market_data/` ein. FT-001 bleibt unverändert Owner der Basiswert- und Listing-Stammdaten. `market_data` referenziert Listings ausschließlich über stabile IDs und öffentliche Verträge.

Die bestehende Feature-Nummerierung FT-001 bis FT-013 wird nicht verändert. `market_data` ist eine Querschnittsfähigkeit; ein späteres benutzerverwaltetes Providerfeature bleibt separat.

## Konsequenzen

- keine Breaking Changes an FT-001,
- klare Verantwortungs- und Abhängigkeitsrichtung,
- zusätzlicher Integrationsvertrag zwischen Listing und Marktdaten,
- spätere Marktdatenarten können unabhängig ergänzt werden.
