# ADR-S1-001 – Anlageuniversum Version 1

**Status:** Accepted
**Datum:** 2026-08-03

## Entscheidung

Version 1 unterstützt Aktien als Basiswerte und Optionsscheine als handelbare Produkte. Aktienindizes, ETFs, Rohstoffe, Währungen und andere Produktarten sind nicht enthalten.

`UnderlyingType` besitzt in Version 1 nur `STOCK`. `ProductType` besitzt zunächst `WARRANT`.

## Konsequenzen

- FT-001 verwaltet keine Optionsscheine.
- Basiswert- und Produktauswahl sind getrennte UI-Kontexte.
- Ein Warrant referenziert genau ein Underlying.
