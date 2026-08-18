# ADR-S11-008 – Persistenz, Review-Versionierung und Input-Fingerprint

## Status

Accepted for Sprint 11 technical Definition of Ready.

## Kontext

Die fachlichen ADR-S11-001 bis ADR-S11-007 definieren:

- höchstens eine PostTradeObservation pro Trade;
- expliziten Observation-Start;
- gepinnte Underlying-Listing-ID;
- 20 EOD-Beobachtungen;
- DailyPrice als Market-Data Source of Truth;
- getrennte PostTradeObservation und ExitReview;
- CURRENT-/STALE-Semantik;
- historische Nachvollziehbarkeit finalisierter Reviews.

Die technische Persistenz muss diese Regeln erzwingen, ohne bestehende
Trade-, Market-Data-, TradePlan- oder Product-Selection-Wahrheiten zu
duplizieren.

## Entscheidung

FT-011 V1 verwendet drei persistente Kernstrukturen:

post_trade_observations
exit_reviews
exit_review_versions

Die vollständige DailyPrice-Zeitreihe wird nicht in FT-011 kopiert.

## 1. post_trade_observations

post_trade_observations ist die stabile Identität einer Nachbeobachtung.

Fachlich erforderliche Felder:

- id
- workspace_id
- trade_id
- underlying_listing_id
- status
- target_observation_count
- started_at
- started_by
- completed_at
- created_at
- updated_at

Für V1 gilt:

UNIQUE(trade_id)

target_observation_count = 20

status erlaubt:

ACTIVE
COMPLETED

Für COMPLETED muss completed_at gesetzt sein.

Für ACTIVE ist completed_at NULL.

Die Observation referenziert stabil:

trade_id -> trades.id
underlying_listing_id -> listings.id

Workspace-Isolation folgt dem bestehenden Repository-Pattern.

Historische Referenzen sollen nicht kaskadierend gelöscht werden.

## 2. Keine kopierten Observation Points

FT-011 führt in V1 keine eigene Tabelle ein, die vorhandene DailyPrice-Zeilen
dupliziert.

Observation Points bleiben ein Read Model aus:

PostTradeObservation
+ underlying_listing_id
+ Observation Boundary
+ DailyPrice

DailyPrice bleibt die persistierte EOD-Marktdatenwahrheit.

## 3. exit_reviews

exit_reviews ist die stabile Identität des Review-Kontexts.

Fachlich erforderliche Felder:

- id
- workspace_id
- post_trade_observation_id
- created_at
- created_by

Für V1 gilt:

UNIQUE(post_trade_observation_id)

Die konkreten Bewertungsinhalte liegen in exit_review_versions.

## 4. exit_review_versions

exit_review_versions enthält die konkrete Review-Fassung.

Fachlich erforderliche Felder:

- id
- exit_review_id
- version
- status
- currentness
- timing
- process_adherence
- risk_decision
- overall_exit_decision
- rationale
- input_fingerprint
- created_at
- created_by
- finalized_at
- finalized_by
- supersedes_version_id
- stale_at
- stale_reason

Für jeden ExitReview gilt:

UNIQUE(exit_review_id, version)

version >= 1

## 5. Draft-Semantik

Eine DRAFT-Version darf bearbeitet werden.

Während DRAFT dürfen Bewertungsfelder und rationale geändert werden.

Es darf pro ExitReview höchstens einen offenen DRAFT geben.

Die Datenbank beziehungsweise Repository-Schicht muss diese Invariante
zusätzlich absichern.

## 6. Finalized-Semantik

Bei Finalisierung gilt:

status = FINALIZED
currentness = CURRENT

Zusätzlich müssen gesetzt sein:

- timing
- process_adherence
- risk_decision
- overall_exit_decision
- rationale
- input_fingerprint
- finalized_at
- finalized_by

Eine FINALIZED Review-Version ist hinsichtlich ihrer Bewertungsinhalte
immutable.

## 7. Staleness

Eine finalisierte Version kann später wechseln:

CURRENT -> STALE

Dabei bleiben unverändert:

- Bewertungen
- rationale
- Finalisierungszeitpunkt
- ursprünglicher input_fingerprint

Zusätzlich werden gesetzt:

- stale_at
- stale_reason

STALE beschreibt die Gültigkeit gegenüber der aktuellen Faktenbasis und
überschreibt nicht die historische Benutzerbewertung.

## 8. Neue Version nach Staleness

Eine erneute Prüfung erzeugt eine neue Review-Version.

Beispiel:

Version 1
FINALIZED / später STALE

Version 2
DRAFT
-> FINALIZED / CURRENT

Version 2 referenziert Version 1 über supersedes_version_id.

Die alte Version bleibt unverändert erhalten.

## 9. Bewertungswerte

Folgende Felder verwenden denselben kontrollierten Wertebereich:

- timing
- process_adherence
- risk_decision
- overall_exit_decision

Zulässig:

- GOOD
- ACCEPTABLE
- IMPROVABLE
- NOT_ASSESSABLE

Ein numerischer Score wird nicht persistiert.

## 10. Input-Fingerprint

Jede finalisierte ExitReview-Version speichert einen reproduzierbaren:

input_fingerprint

Favorisierte technische Form:

SHA-256 über eine kanonisch serialisierte semantische Input-Struktur.

Der Fingerprint ist kein Business-Score.

Er identifiziert die fachliche Faktenbasis, auf der der Review finalisiert
wurde.

## 11. Semantische Fingerprint-Inputs

Der Fingerprint umfasst nur review-relevante Inputs.

Mindestens, soweit vorhanden:

### Trade / Exit

- trade_id
- effektive ExecutionRecord-IDs
- relevante Execution-Felder
- finaler Full-Exit-Zeitpunkt
- tatsächliche Exit-Mengen
- tatsächliche Exit-Preise

### Management

- effektive TradeManagementEvent-IDs
- relevante Management-Felder

### Plan-Provenance

- trade_plan_version_id
- ursprüngliche Stop-Level
- ursprüngliche Target-Level

### Produkt-Provenance

- product_evaluation_id
- warrant_terms_version_id
- maturity_date

### Observation

- post_trade_observation_id
- pinned underlying_listing_id
- target_observation_count
- tatsächlich verwendete Observation-Dates

### Market Data

Für tatsächlich verwendete DailyPrice-Zeilen mindestens:

- listing_id
- trading_date
- open
- high
- low
- close
- adjusted_close, sofern fachlich verwendet
- quality_status

Nicht fachlich relevante technische Attribute gehören nicht in den
Fingerprint.

## 12. Kanonische Serialisierung

Der Fingerprint muss deterministisch sein.

Deshalb:

- stabile Sortierreihenfolge;
- UUIDs als kanonische Strings;
- Datums-/Zeitwerte einheitlich serialisiert;
- Decimal-Werte ohne Float-Rundung;
- NULL eindeutig repräsentiert;
- stabile Schlüsselreihenfolge.

Der Hash darf nicht von ORM-Repräsentationen oder zufälliger
Dictionary-Reihenfolge abhängen.

## 13. Staleness-Erkennung

Für V1 wird keine neue Cross-Feature-Event-Infrastruktur eingeführt.

Favorisierte Lösung:

Der aktuelle Fingerprint wird neu berechnet:

1. bei expliziter Revalidation;
2. vor FT-012-Handoff;
3. vor Erstellung einer neuen Review-Version;
4. bei relevanten FT-011-Review-Aktionen.

Wenn:

stored input_fingerprint
!=
current semantic input_fingerprint

dann:

CURRENT -> STALE

## 14. Keine Staleness durch irrelevante Änderungen

Nicht jede Repository-Änderung macht einen Review stale.

Beispiele ohne Staleness:

- reine UI-Änderung;
- Formatierungsänderung;
- Cache-Refresh;
- erneute Speicherung identischer Fakten;
- heutiges Primary Listing geändert, solange pinned underlying_listing_id und
  verwendete EOD-Serie unverändert bleiben.

## Auswirkungen für den Nutzer

Der Nutzer kann später beispielsweise sehen:

Review Version 1
finalisiert am ...
später aufgrund korrigierter Ausgangsdaten veraltet

Review Version 2
auf korrigierter Faktenbasis
aktuell

Die ursprüngliche Bewertung verschwindet nicht.

Vor FT-012-Handoff wird außerdem geprüft, ob der Review noch auf der aktuellen
effektiven Faktenlage beruht.

## Begründung

Die stabile ExitReview-Identität trennt den Review-Kontext von seinen
historischen Versionen.

Append-orientierte Review-Versionen verhindern, dass finalisierte
Benutzerentscheidungen in-place überschrieben werden.

SHA-256 eignet sich für die deterministische Gleichheitsprüfung der
semantischen Input-Basis, ohne selbst fachliche Bedeutung zu erzeugen.

DailyPrice wird nicht kopiert, weil sonst eine zweite Market-Data-Wahrheit
entstehen würde.

## Konsequenzen für die Migration

Die erste FT-011-Migration setzt auf Alembic-Head:

20260817_0018

Sie soll mindestens anlegen:

- post_trade_observations
- exit_reviews
- exit_review_versions

mit:

- Fremdschlüsseln;
- Unique Constraints;
- Check Constraints;
- sinnvollen Lookup-Indizes.

Eine Observation-Point-Kurstabelle gehört ausdrücklich nicht zur V1-Migration.

## Invarianten

### INV-S11-061
post_trade_observations.trade_id ist für V1 eindeutig.

### INV-S11-062
exit_reviews.post_trade_observation_id ist für V1 eindeutig.

### INV-S11-063
Finalisierte Review-Inhalte werden nicht in-place überschrieben.

### INV-S11-064
Neue Bewertung nach Staleness erzeugt eine neue Review-Version.

### INV-S11-065
Pro ExitReview existiert höchstens ein offener DRAFT.

### INV-S11-066
FINALIZED benötigt vollständige Bewertungen, rationale und Input-Fingerprint.

### INV-S11-067
Ein Fingerprint repräsentiert semantische Review-Inputs und keinen Score.

### INV-S11-068
Nur fachlich relevante Änderungen dürfen den semantischen Fingerprint ändern.

### INV-S11-069
Vor FT-012-Handoff wird die Aktualität des finalisierten Reviews revalidiert.

### INV-S11-070
FT-011 persistiert keine zweite vollständige DailyPrice-Zeitreihe.
