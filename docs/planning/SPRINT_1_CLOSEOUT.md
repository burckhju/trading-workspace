# Sprint 1 Closeout – Fachliche Architektur

## Status

**Approved – 2026-08-03**

## Abgenommene Ergebnisse

- Domain Map freigegeben.
- Trading-Prozessmodell freigegeben.
- Modul- und Feature-Zuordnung für `underlying` freigegeben.
- ADR-S1-001 bis ADR-S1-013 akzeptiert.
- FT-001 Feature Book vollständig und `Approved for Build`.
- Traceability-Baseline von Anforderungen über Entscheidungen zu Tests hergestellt.

## Architekturreview

Keine blockierenden fachlichen Inkonsistenzen verbleiben. Zwei Begriffe wurden konsistent normalisiert: Versionsprüfung als optimistisches Locking sowie die Trennung von Lebenszyklus und Datenqualität.

## Nicht Bestandteil des Closeouts

- keine Datenbankmigration,
- kein Domain-Code,
- keine API-Implementierung,
- keine Frontend-Implementierung,
- keine produktive Markt- oder Währungsverwaltung.

## Übergabe an Sprint 2

Sprint 2 darf FT-001 vertikal implementieren. Vor dem ersten Code-Commit sind technische API- und Persistenzverträge aus dem freigegebenen Feature Book abzuleiten und gemeinsam zu reviewen. Fachregeln dürfen dabei nicht neu interpretiert werden.
