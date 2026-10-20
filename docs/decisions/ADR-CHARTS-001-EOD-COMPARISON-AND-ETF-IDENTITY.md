# ADR-CHARTS-001 – EOD-Vergleich und echte ETF-Identität

Status: Implementiert und über PR #243 gemergt; Teil von Version 1.5.0.
Datum: 2026-10-04. Auftrag: Markt-/Sektor-/Aktiendiagramme.

## Entscheidung

Market Data stellt persistierte, begrenzte EOD-Beobachtungen über einen neutralen
Read-Port bereit. Market löst bestehende Identitäten und zeitlich gültige
Zuordnungen auf. Analysis besitzt die versionierte Decimal-Ausrichtung und
Normalisierung. GETs erzeugen keine Providerabrufe, Analyse-Runs oder Stammdaten.
FT-006-SMA/Momentum/Volatilität und immutable Runs bleiben unverändert.

ETF wird additiv als echte FT-001-Wertpapierart mit Listing unterstützt. Dies
ersetzt ausschließlich den ETF-Ausschluss in ADR-S1-001; D01-Indizes behalten
ihre listingfreie Referenzidentität. Die Produktauswahl bleibt WARRANT;
ETF-Stammdaten sind keine Erweiterung von Handelsregeln oder Orderfreigaben.

Quellenbelegte Administrationsvorschläge ersetzen keine vorhandene Taxonomie.
Charts lesen nur gespeicherte Zuordnungen. Ein ETF-Proxy wird explizit ausgewählt
und als solcher benannt. Fehlende Indexdaten lösen keinen stillen Proxywechsel aus.
Index-Renditegrundlagen werden append-only für die geprüfte Mappingrevision
bestätigt. Unbekannte oder unvereinbare Grundlagen sperren den Vergleich.

## Folgen

1–4 Serien, höchstens 10.000 Punkte je Serie, volle EOD-Auflösung. Gemeinsamer
Start ist der erste beobachtete gemeinsame Tag; ungültiger Start wird nicht
übersprungen. Keine Interpolation, FX-Bereinigung oder erfundene Kursuhrzeit.
Historische Chartansichten sind kein Point-in-time-Backtest. Rückmigration mit
ETF-Daten oder bestätigter Indexevidenz erfordert einen eigenen Erhaltungsplan.

API, Einrichtung, Quellen und Prüfstand: [MARKET_CHARTS](../implementation/MARKET_CHARTS.md).
