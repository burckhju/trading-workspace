# ADR-S1-011 – Schutz vor verlorenen Änderungen

## Status

Accepted – 2026-08-03

## Kontext

Auch in Version 1 können Browser-Tabs, API-Aufrufe oder spätere Importprozesse denselben Datensatz parallel ändern.

## Entscheidung

FT-001 verwendet optimistische Nebenläufigkeitskontrolle. Änderbare Aggregate besitzen eine technische Versionsnummer. Ein Schreibvorgang ist nur erfolgreich, wenn die vom Client gelesene Version noch aktuell ist. Bei Abweichung wird nicht automatisch überschrieben.

## Konsequenzen

- Konflikte liefern den stabilen Fehlercode `UNDERLYING_CONCURRENT_MODIFICATION` beziehungsweise ein entsprechendes Listing-Pendant.
- Die UI erhält die aktuellen Serverdaten und lässt den Benutzer neu laden, Änderungen verwerfen oder nach Sichtprüfung erneut anwenden.
- Es werden keine langfristigen Datenbanksperren oder Bearbeitungssperren eingesetzt.
