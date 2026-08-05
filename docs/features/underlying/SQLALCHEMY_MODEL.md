# FT-001 – SQLAlchemy-Persistenzmodell

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Implementierungsschritt | 2 – SQLAlchemy-Domänenmodell |
| Version | 1.0 |
| Status | Approved for Alembic Migration |
| Datum | 2026-08-03 |

## Architekturprüfung

Das Mapping setzt ausschließlich das in `PHYSICAL_DATA_MODEL.md` freigegebene Modell um. Es führt keine Repositoryoperationen, Migrationen, Services oder fachliche Mutationslogik ein.

Die Klassen liegen unter `app/features/market/persistence`. Diese Trennung ist verbindlich: SQLAlchemy-Klassen bilden Persistenzzustand ab; die spätere Domain bleibt unabhängig von SQLAlchemy, HTTP und PostgreSQL.

## Implementierte Mappings

- `WorkspaceModel` → `workspaces`
- `TradingVenueModel` → `trading_venues`
- `CurrencyModel` → `currencies`
- `UnderlyingModel` → `underlyings`
- `ListingModel` → `listings`
- `AuditEventModel` → `audit_events`

Alle Modelle verwenden die zentrale `Base` und deren Naming Convention.

## Mappingregeln

### Enumerationen

Fachlich festgelegte Werte werden als Python-`StrEnum` und als nicht-native SQLAlchemy-Enums gemappt. Dadurch bleiben die Datenbankwerte lesbare `varchar`-Werte und die spätere Alembic-Migration erzeugt keine parallelen PostgreSQL-Enumtypen.

### Optimistic Locking

`UnderlyingModel.version` und `ListingModel.version` sind als `version_id_col` konfiguriert. Der Versionswert wird nicht automatisch durch SQLAlchemy erzeugt (`version_id_generator=False`), weil die Erhöhung Bestandteil der späteren kontrollierten Domänen- und Serviceoperation ist.

### Beziehungen

- Workspace zu Underlyings, Listings und AuditEvents: bidirektional.
- Underlying zu Listings: bidirektional mit `delete-orphan` und passivem Datenbank-Cascade.
- Listing zu TradingVenue und Currency: bidirektionale Referenzbeziehungen.
- AuditEvent zu Underlying oder Listing: bewusst keine ORM-Beziehung und kein Foreign Key; `aggregate_type` plus `aggregate_id` bleibt die historische Referenz.

### Constraints und Indizes

Alle in Schritt 1 festgelegten Checks, Unique Constraints, partiellen Unique Indizes und Suchindizes sind im SQLAlchemy-Metadatenmodell enthalten. PostgreSQL-spezifische Regeln verwenden `postgresql_where`; `field_changes` verwendet `JSONB`.

### Append-only Audit

Das Mapping stellt keine Update- oder Delete-API bereit. Der endgültige Schutz erfolgt zusätzlich in Repository, Berechtigungskonzept und Migration. Diese Verantwortlichkeiten gehören zu späteren Schritten.

## Tests

Architekturtests prüfen:

- Registrierung aller sechs Tabellen,
- Spaltentypen und Primärschlüssel,
- Foreign-Key-Löschregeln,
- Checks und Eindeutigkeitsregeln,
- partielle PostgreSQL-Indizes,
- JSONB-Kompilierung,
- Mapper-Konfiguration für Optimistic Locking,
- fehlenden Aggregate-Foreign-Key beim AuditEvent.

## Abgrenzung

Nicht enthalten:

- Alembic-Migration oder Seed-Daten,
- konkrete Repositoryimplementierung,
- Domain Entities und fachliche Invarianten,
- DTOs oder REST API,
- Datenbankintegrationstests gegen ein migriertes PostgreSQL-Schema.

## Architekturreview Schritt 2

- Physisches Modell vollständig abgebildet: erfüllt.
- Domain bleibt SQLAlchemy-unabhängig: erfüllt.
- Keine zweite Datenmodellvariante: erfüllt.
- Workspace und Referenzobjekte nur einmal modelliert: erfüllt.
- Optimistic Locking vorbereitet, aber nicht fachlich vorweggenommen: erfüllt.
- Audit-Lebenszyklus von Aggregaten entkoppelt: erfüllt.
- Keine Migration oder Repositorylogik vorgezogen: erfüllt.
- Ausschließlich FT-001 umgesetzt: erfüllt.

**Ergebnis:** Schritt 2 ist abgeschlossen und für Schritt 3 „Alembic-Migration“ freigegeben.
