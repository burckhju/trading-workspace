# FT-001 Test Specification

## Domain Tests

- UnderlyingType akzeptiert nur `STOCK`.
- Name darf nicht leer sein.
- ISIN-/WKN-Normalisierung ist deterministisch.
- Genau eine aktive primäre Notierung.
- Ticker+Markt-Dublette wird verhindert.
- Referenziertes Underlying kann nicht gelöscht werden.
- Deaktivierung und Reaktivierung behalten Identität.

## Service-/Repository-Tests

- atomare Anlage von Underlying und Primärlisting,
- Suche über Name, Ticker, ISIN und WKN,
- Filter für Status,
- Konflikte bei konkurrierender Änderung,
- Verwendungsprüfung vor Löschung,
- Workspace-Grenze wird in jeder Abfrage eingehalten.

## API Contract Tests

- erfolgreiche und fehlerhafte Anlage,
- stabile Fehlercodes,
- Pagination und Filter,
- Deaktivierung, Reaktivierung und Löschablehnung.

## Frontend Tests

- geführte Anlage,
- dynamische Validierung und Erhalt der Eingaben,
- verständliche Dublettenanzeige,
- deaktivierte Datensätze standardmäßig verborgen,
- Anzeige der Verwendungen bei Löschkonflikt.

## E2E-Kernfälle

1. Aktie mit primärer Notierung anlegen und wiederfinden.
2. Dublette über normalisierte ISIN verhindern.
3. Zweites Listing ergänzen und primäres Listing wechseln.
4. Basiswert deaktivieren, in Standardauswahl ausblenden und reaktivieren.
5. Referenzierten Basiswert nicht löschen können.
6. Unbenutzten Fehleintrag endgültig löschen.

## Zusätzliche ADR-Abdeckung

- ISIN-Normalisierung und ISO-6166-Prüfziffer werden positiv und negativ getestet.
- WKN-Normalisierung und sechsstellige Formatregel werden getestet.
- Eindeutigkeit wird workspacebezogen geprüft.
- Markt- und Währungswerte akzeptieren nur kontrollierte Referenzen.
- Veraltete Versionsnummer führt ohne Überschreibung zum Konflikt.
- Jede Änderungsart erzeugt einen unveränderlichen Audit-Event mit Feld-Diff.
- Datenqualitätsstatus wird regelbasiert ermittelt.
- Verifikation ist nur bei `COMPLETE` möglich und wird nach relevanter Änderung zurückgesetzt.
- `INACTIVE` bleibt unabhängig vom Datenqualitätsstatus.
