# ADR-S3-005 – Fachliche EOD-Persistenz und getrennter technischer Cache

## Status

Accepted – 2026-08-05

## Kontext

Historische Marktdaten werden für reproduzierbare Analysen benötigt. Ein technischer Cache besitzt dagegen eine begrenzte Lebensdauer und darf nicht als implizite fachliche Datenbank dienen.

## Entscheidung

Validierte EOD-Tageskurse werden fachlich persistiert. Provider-Rohantworten werden nicht dauerhaft gespeichert. Ein injizierbarer technischer Cache wird separat geführt und in Sprint 3 in-memory implementiert.

Identische Reimporte sind idempotent. Providerkorrekturen aktualisieren kontrolliert und erzeugen ein Audit-Event.

## Konsequenzen

- Analysen können auf einen reproduzierbaren Datenbestand zugreifen,
- Speicher- und Migrationsaufwand entsteht,
- Cache-Löschung verändert keine fachliche Historie,
- Rohantworten können nicht nachträglich vollständig rekonstruiert werden; normalisierte Werte und Herkunft bleiben erhalten.
