# FT-001 – Physisches Datenmodell

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Feature-ID | FT-001 |
| Implementierungsschritt | 1 – Datenmodell |
| Version | 1.0 |
| Status | Approved for SQLAlchemy Mapping |
| Datum | 2026-08-03 |

## Architekturgrundlage

Dieses Modell konkretisiert ADR-S1-001 bis ADR-S1-013 sowie ADR-S2-001 bis ADR-S2-003. Es verändert keine fachliche Regel der Sprint-1-Baseline.

## Tabellenübersicht

### `workspaces`

| Spalte | Typ | Null | Regel |
|---|---|---:|---|
| `id` | UUID | nein | Primärschlüssel; feste Version-1-UUID |
| `name` | varchar(100) | nein | technischer Name, nicht in der UI sichtbar |
| `created_at` | timestamptz | nein | UTC, unveränderlich |

Der Version-1-Datensatz wird migrationsseitig angelegt und darf durch FT-001 nicht verändert oder gelöscht werden.

### `trading_venues`

| Spalte | Typ | Null | Regel |
|---|---|---:|---|
| `id` | UUID | nein | Primärschlüssel |
| `mic` | varchar(4) | nein | kanonisch großgeschrieben, eindeutig |
| `name` | varchar(200) | nein | getrimmt, nicht leer |
| `country_code` | char(2) | nein | ISO-3166-1 alpha-2 |
| `timezone` | varchar(64) | nein | gültige IANA-Zeitzone |
| `is_active` | boolean | nein | steuert Neuauswahl |
| `reference_version` | varchar(50) | nein | Version der kontrollierten Liste |
| `created_at` | timestamptz | nein | UTC |
| `updated_at` | timestamptz | nein | UTC |

Eindeutigkeit: `mic`.

### `currencies`

| Spalte | Typ | Null | Regel |
|---|---|---:|---|
| `code` | char(3) | nein | Primärschlüssel; ISO-4217, großgeschrieben |
| `name` | varchar(100) | nein | getrimmt, nicht leer |
| `minor_unit` | smallint | nein | Wertebereich 0 bis 6 |
| `is_active` | boolean | nein | steuert Neuauswahl |
| `reference_version` | varchar(50) | nein | Version der kontrollierten Liste |
| `created_at` | timestamptz | nein | UTC |
| `updated_at` | timestamptz | nein | UTC |

### `underlyings`

| Spalte | Typ | Null | Regel |
|---|---|---:|---|
| `id` | UUID | nein | Primärschlüssel |
| `workspace_id` | UUID | nein | FK auf `workspaces.id`, Delete Restrict |
| `type` | varchar(20) | nein | Check: ausschließlich `STOCK` |
| `name` | varchar(200) | nein | getrimmt, nicht leer |
| `isin` | varchar(12) | ja | kanonisch; formal gültig |
| `wkn` | varchar(6) | ja | kanonisch; formal gültig |
| `lifecycle_status` | varchar(20) | nein | `ACTIVE`, `INACTIVE` |
| `quality_status` | varchar(20) | nein | `DRAFT`, `COMPLETE`, `VERIFIED` |
| `version` | integer | nein | mindestens 1, monoton steigend |
| `created_at` | timestamptz | nein | UTC, unveränderlich |
| `updated_at` | timestamptz | nein | UTC |
| `data_origin` | varchar(20) | nein | in FT-001 `MANUAL` |

Constraints und Indizes:

- partieller Unique Index auf `(workspace_id, isin)` für `isin IS NOT NULL`,
- partieller Unique Index auf `(workspace_id, wkn)` für `wkn IS NOT NULL`,
- Index auf `(workspace_id, lifecycle_status, name)`,
- Check `version >= 1`,
- Check `length(trim(name)) > 0`.

### `listings`

| Spalte | Typ | Null | Regel |
|---|---|---:|---|
| `id` | UUID | nein | Primärschlüssel |
| `workspace_id` | UUID | nein | FK auf `workspaces.id`, Delete Restrict |
| `underlying_id` | UUID | nein | FK auf `underlyings.id`, Delete Cascade nur innerhalb des FT-001-Aggregats |
| `trading_venue_id` | UUID | nein | FK auf `trading_venues.id`, Delete Restrict |
| `ticker` | varchar(32) | nein | kanonisch, nicht leer |
| `currency_code` | char(3) | nein | FK auf `currencies.code`, Delete Restrict |
| `lifecycle_status` | varchar(20) | nein | `ACTIVE`, `INACTIVE` |
| `is_primary` | boolean | nein | Primärkennzeichen |
| `version` | integer | nein | mindestens 1, monoton steigend |
| `created_at` | timestamptz | nein | UTC, unveränderlich |
| `updated_at` | timestamptz | nein | UTC |
| `data_origin` | varchar(20) | nein | in FT-001 `MANUAL` |

Constraints und Indizes:

- Unique Constraint auf `(workspace_id, trading_venue_id, ticker)`,
- partieller Unique Index auf `(underlying_id)` für `is_primary = true AND lifecycle_status = 'ACTIVE'`,
- Index auf `(underlying_id, lifecycle_status)`,
- Index auf `(workspace_id, ticker)`,
- Check `version >= 1`,
- Check `length(trim(ticker)) > 0`.

`workspace_id` wird bewusst auch im Listing gespeichert. Dadurch sind Workspace-Isolation und die workspaceweite Markt/Ticker-Eindeutigkeit ohne Join datenbankseitig erzwingbar. Service und Repository müssen sicherstellen, dass Listing und Underlying demselben Workspace angehören.

### `audit_events`

| Spalte | Typ | Null | Regel |
|---|---|---:|---|
| `id` | UUID | nein | Primärschlüssel |
| `workspace_id` | UUID | nein | FK auf `workspaces.id`, Delete Restrict |
| `aggregate_type` | varchar(30) | nein | zunächst `UNDERLYING`, `LISTING` |
| `aggregate_id` | UUID | nein | logische Referenz, bewusst ohne Aggregate-FK |
| `occurred_at` | timestamptz | nein | UTC, unveränderlich |
| `actor_type` | varchar(20) | nein | in Version 1 `SYSTEM_USER` |
| `actor_id` | varchar(100) | ja | technische Actor-Kennung |
| `actor_display_name` | varchar(200) | nein | lesbare Anzeige |
| `data_origin` | varchar(20) | nein | zunächst `MANUAL` |
| `change_type` | varchar(30) | nein | definierte Änderungsart |
| `version_before` | integer | ja | bei Anlage null |
| `version_after` | integer | ja | bei Löschung gegebenenfalls null |
| `field_changes` | jsonb | nein | validierte Map aus Feldname sowie `old`/`new` |

Indizes:

- `(workspace_id, aggregate_type, aggregate_id, occurred_at DESC)`,
- `(workspace_id, occurred_at DESC)`.

Für `audit_events` werden keine fachlichen Update- oder Delete-Pfade implementiert.

## Beziehungen und Kardinalitäten

```text
Workspace 1 ─── n Underlying
Workspace 1 ─── n Listing
Workspace 1 ─── n AuditEvent
Underlying 1 ─── n Listing
TradingVenue 1 ─── n Listing
Currency 1 ─── n Listing
```

Ein operativ nutzbares Underlying besitzt genau eine aktive primäre Notierung. Die Datenbank verhindert mehr als eine aktive primäre Notierung; die Pflicht zu mindestens einer aktiven primären Notierung wird transaktional in der Domänen- und Service-Logik abgesichert, da sie bei mehrstufigen Anlage- und Statuswechselvorgängen nicht als einfache Zeilen-Constraint formulierbar ist.

## Löschregeln

- `workspaces`, `trading_venues` und `currencies`: `RESTRICT`.
- `underlyings`: physische Löschung ausschließlich nach fachlicher Referenzprüfung.
- Zugehörige `listings` dürfen beim zulässigen Löschen des Aggregats kaskadierend entfernt werden.
- `audit_events` werden niemals kaskadierend gelöscht.
- Fachfremde Referenzen auf Underlyings müssen physische Löschung verhindern; andernfalls erfolgt Deaktivierung.

## Transaktionsgrenzen

Folgende Änderungen sind jeweils atomar:

- Underlying und primäres Listing anlegen,
- Primärnotierung wechseln,
- Statusänderung mit Folgeregeln,
- fachliche Änderung mit zugehörigen Audit-Events,
- zulässige physische Löschung mit vorher erzeugtem Lösch-Audit.

## Architekturreview Schritt 1

- Underlying und Listing bleiben getrennte Objekte: erfüllt.
- Keine doppelte Speicherung von Handelsplatz- oder Währungsstammdaten: erfüllt.
- Workspace-Zuordnung vollständig und referenziell abgesichert: erfüllt.
- Eindeutigkeitsregeln aus ADR-S1-008 datenbankseitig abbildbar: erfüllt.
- Optimistic Locking durch explizite Versionen vorbereitet: erfüllt.
- Audit bleibt nach physischer Löschung erhalten: erfüllt.
- Keine Implementierung anderer Features: erfüllt.

**Ergebnis:** Schritt 1 „Datenmodell“ ist abgeschlossen und für Schritt 2 „SQLAlchemy-Domänenmodell“ freigegeben.
