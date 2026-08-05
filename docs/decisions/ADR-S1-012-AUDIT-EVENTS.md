# ADR-S1-012 – Auditmodell für Stammdatenänderungen

## Status

Accepted – 2026-08-03

## Entscheidung

Jede erfolgreiche fachliche Änderung an Underlying oder Listing erzeugt einen unveränderlichen Audit-Event. Er enthält mindestens:

- Aggregate-ID und Aggregate-Typ,
- Workspace-ID,
- Zeitpunkt,
- Actor beziehungsweise in Version 1 den Systembenutzer,
- Datenquelle,
- Versionsnummer vor und nach der Änderung,
- Änderungsart,
- geänderte Felder mit altem und neuem Wert.

Für die Änderungshistorie werden Feldänderungen gespeichert; vollständige Snapshots sind nicht die alleinige Auditstrategie.

## Konsequenzen

- Anlage, Änderung, Aktivierung, Deaktivierung, Reaktivierung, Primärwechsel und Löschung werden auditierbar.
- Audit-Events dürfen durch normale Featureoperationen nicht verändert oder gelöscht werden.
- Die Detailseite zeigt eine lesbare Historie; technische Metadaten können bei Bedarf aufgeklappt werden.
