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


## Ergänzung 2026-10-04: integrierte EOD-Diagramme

Der Chart-Arbeitszweig ergänzt echte ETF-Stammdaten und einen rein lesenden
Markt-/Sektor-/Aktienvergleich. Indexreferenzen bleiben ohne synthetische Listings.
Frühere STOCK-only-Aussagen gelten damit nicht mehr für die Stammdatenverwaltung.
Analyse-Runs, Candidate-Regeln und fachliche Freigaben bleiben unverändert.
Contracts, Preis-/Zeitsemantik, Einrichtung und Prüfstand:
[MARKET_CHARTS](../implementation/MARKET_CHARTS.md).
