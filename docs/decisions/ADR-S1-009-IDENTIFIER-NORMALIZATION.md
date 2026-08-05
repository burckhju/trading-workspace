# ADR-S1-009 – Normalisierung der Identifikatoren

## Status

Accepted – 2026-08-03

## Entscheidung

Identifikatoren werden vor Validierung, Vergleich und Speicherung deterministisch normalisiert:

- ISIN: trimmen, interne Leerzeichen und Bindestriche entfernen, Großschreibung,
- WKN: trimmen, interne Leerzeichen entfernen, Großschreibung,
- Ticker: führende und nachfolgende Leerzeichen entfernen, Großschreibung; fachlich bedeutende Sonderzeichen bleiben erhalten,
- MIC- und Währungscodes: trimmen und Großschreibung.

Die normalisierte Form ist die persistierte kanonische Form. Die Anwendung führt keine weitergehende stillschweigende fachliche Korrektur durch.

## Konsequenzen

- Dubletten unterscheiden sich nicht durch Schreibweise oder Rand-Leerzeichen.
- Fehlermeldungen zeigen den kanonischen Wert.
- Die Normalisierungsfunktionen sind versioniert und separat zu testen.
