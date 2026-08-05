# ADR-S1-006 – Identifikatoren des Basiswerts

**Status:** Accepted
**Datum:** 2026-08-03

## Entscheidung

- interne UUID: verpflichtend, unveränderlich und eindeutig,
- Name und Status: verpflichtend,
- Typ: verpflichtend, in Version 1 `STOCK`,
- mindestens eine primäre Notierung für operative Nutzung,
- Ticker, Markt und Handelswährung: verpflichtend je operativer Notierung,
- ISIN und WKN: optional, aber nach Normalisierung eindeutig, sobald vorhanden,
- Provider-Symbole: providerbezogen und keine fachliche Identität des Underlyings.
