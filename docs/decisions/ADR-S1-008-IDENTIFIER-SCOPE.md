# ADR-S1-008 – Gültigkeitsbereich der Identifikatoren

## Status

Accepted – 2026-08-03

## Entscheidung

Für Version 1 gelten folgende Eindeutigkeitsbereiche:

- UUID: global technisch eindeutig,
- ISIN: innerhalb eines Workspace eindeutig, sofern vorhanden,
- WKN: innerhalb eines Workspace eindeutig, sofern vorhanden,
- Markt plus Ticker: innerhalb eines Workspace eindeutig für Listings.

Verglichen werden ausschließlich normalisierte Werte.

## Konsequenzen

- Alle fachlichen Eindeutigkeitsprüfungen enthalten `workspace_id`.
- Eine spätere Mehr-Workspace-Fähigkeit ist ohne Änderung der fachlichen Regel möglich.
- Version 1 zeigt den Workspace nicht in der Bedienoberfläche.
