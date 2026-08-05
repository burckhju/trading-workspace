# ADR-S2-003 – Physische Persistenz unveränderlicher Audit-Events

## Status

Accepted – 2026-08-03

## Kontext

ADR-S1-012 fordert für jede erfolgreiche fachliche Änderung unveränderliche, feldbasierte Audit-Events. Für das physische Datenmodell waren Tabellenzuschnitt, Speicherung der Feldänderungen und die Referenzierung physisch löschbarer Aggregate festzulegen.

## Entscheidung

Audit-Events werden in einer gemeinsamen append-only Tabelle `audit_events` gespeichert.

- Die Tabelle enthält eine eigene UUID, `workspace_id`, Aggregate-Typ, Aggregate-ID, Zeitpunkt, Actor-Daten, Datenquelle, Änderungsart, Version vorher/nachher und Feldänderungen.
- Feldänderungen werden als strukturiertes JSONB mit altem und neuem Wert gespeichert.
- Es gibt keinen Foreign Key von `audit_events.aggregate_id` auf `underlyings` oder `listings`.
- `audit_events.workspace_id` referenziert `workspaces.id`.
- Die Kombination aus Aggregate-Typ und Aggregate-ID bildet die historische logische Referenz.
- Audit-Events werden ausschließlich angehängt; normale Featureoperationen bieten keine Update- oder Delete-Operation.
- Fachänderung und zugehörige Audit-Events werden atomar in derselben Datenbanktransaktion gespeichert.
- Kann das Audit-Event nicht persistiert werden, wird die Fachänderung zurückgerollt.

## Konsequenzen

- Underlying- und Listing-Ereignisse verwenden ein einheitliches Auditmodell.
- Physische Löschungen bleiben dauerhaft nachvollziehbar, ohne durch Foreign Keys blockiert zu werden.
- Die Integrität der logischen Aggregatreferenz wird durch Service-Transaktion, Repositorygrenzen und Tests abgesichert.
- Die JSONB-Struktur benötigt ein verbindliches Anwendungsschema.
- Die zentrale Tabelle benötigt Indizes für Workspace, Aggregat und Zeitpunkt.

## Nutzerwirkung

Der Nutzer erhält eine einheitliche chronologische Änderungshistorie. Auch nach der zulässigen physischen Löschung eines unbenutzten Fehleintrags bleibt die Löschung nachvollziehbar, während der gelöschte Datensatz nicht mehr in normalen Listen erscheint.
