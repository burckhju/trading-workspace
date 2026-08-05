# ADR-S1-002 – Trennung von Basiswert und Notierung

**Status:** Accepted
**Datum:** 2026-08-03

## Entscheidung

Underlying und Listing sind getrennte fachliche Objekte. Das Underlying beschreibt die Aktie unabhängig vom Markt; das Listing beschreibt Ticker, Markt, Währung und Primärstatus.

## Konsequenzen

- `Underlying 1:n Listing`.
- Ticker ist nur mit Markt eindeutig.
- Normale Auswahlfelder zeigen primär das Underlying und seine primäre Notierung.
