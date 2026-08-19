# Sprint 11 – FT-011 Acceptance Tests und minimaler Frontend-Flow

## Status

Accepted technical Definition-of-Ready specification for FT-011.

## Ziel

Diese Spezifikation definiert die minimal erforderlichen Tests und den
minimalen Benutzerflow für FT-011.

FT-011 gilt erst als implementierungsbereit, wenn die fachlichen
Kerninvarianten auf Backend-, Integrations- und Frontend-Ebene testbar sind.

## Backend-Teststruktur

Neue Tests folgen dem bestehenden Repository-Layout:

tests/unit/backend/features/post_trade/
    test_domain.py
    test_repository.py
    test_unit_of_work.py
    test_application.py
    test_fingerprint.py
    test_metrics.py
    test_rest_api.py
    test_migration.py

tests/integration/backend/
    test_ft011_post_trade_e2e.py

## Acceptance Tests

### AT-S11-001 – Observation nur nach Full Exit
Offene Position -> Start wird mit POST_TRADE_NOT_ELIGIBLE abgelehnt.
Keine Observation wird persistiert.

### AT-S11-002 – Full Exit erlaubt Observation-Start
Geschlossene Position + auflösbares Listing -> genau eine ACTIVE Observation,
target_observation_count = 20.

### AT-S11-003 – Zweiter Start erzeugt kein Duplikat
Bereits vorhandene Observation -> 409
POST_TRADE_OBSERVATION_ALREADY_EXISTS.

### AT-S11-004 – Same-Day-EOD zählt nicht
Intraday Full Exit an D + DailyPrice D/D+1 -> erster Observation Point
frühestens D+1.

### AT-S11-005 – Gepinnte Listing-ID bleibt stabil
Spätere Primary-Listing-Änderung verändert die laufende Observation nicht.

### AT-S11-006 – Mehrdeutiges Listing schlägt kontrolliert fehl
Keine zufällige Auswahl; stabiler 422-Fehlercode.

### AT-S11-007 – Nur reale DailyPrice-Beobachtungen zählen
18 verfügbare EOD-Daten -> available_observation_count = 18, status ACTIVE.

### AT-S11-008 – Completion bei 20 Beobachtungen
20 verwendbare EOD-Beobachtungen -> ACTIVE -> COMPLETED, completed_at gesetzt.

### AT-S11-009 – Highest High
highest_observed_high == max(DailyPrice.high), trading_date stimmt.

### AT-S11-010 – Lowest Low
lowest_observed_low == min(DailyPrice.low), trading_date stimmt.

### AT-S11-011 – Final Close
final_observed_close entspricht dem letzten verwendeten Observation Point.

### AT-S11-012 – Target Crossing
LONG: DailyPrice.high >= historisches Target -> crossed.
Kein hypothetischer Verkaufspreis.

### AT-S11-013 – Stop Crossing
LONG: DailyPrice.low <= historischer Stop -> crossed.
Kein automatisches Qualitätsurteil.

### AT-S11-014 – Plan- und Management-Level bleiben getrennt
Ursprünglicher Stop und späterer STOP_CHANGED werden getrennt ausgewiesen.

### AT-S11-015 – Historische Maturity
FT-011 verwendet die historisch referenzierte WarrantTermsVersion.

### AT-S11-016 – Maturity stoppt Underlying-Observation nicht
Warrant läuft z. B. nach Punkt 7 aus -> Underlying darf bis 20/20 weiterlaufen.

### AT-S11-017 – Keine Post-Maturity-Warrant-P&L
Kein hypothetischer Marktwert, keine Settlement-/Exercise-Simulation.

### AT-S11-018 – Review vor Completion nicht finalisierbar
18/20 -> 422 OBSERVATION_HORIZON_NOT_COMPLETE.

### AT-S11-019 – Draft editierbar
Bewertungen/rationale können im DRAFT geändert werden, ohne neue Version.

### AT-S11-020 – Vier Bewertungen erforderlich
Fehlende Dimension -> EXIT_REVIEW_INCOMPLETE.

### AT-S11-021 – rationale erforderlich
Leere rationale -> EXIT_REVIEW_RATIONALE_REQUIRED.

### AT-S11-022 – Gültige Bewertungswerte
Nur GOOD, ACCEPTABLE, IMPROVABLE, NOT_ASSESSABLE.

### AT-S11-023 – Finalisierung speichert Fingerprint
COMPLETED + vollständiger Draft -> FINALIZED/CURRENT + input_fingerprint.

### AT-S11-024 – Finalized nicht editierbar
Draft-Update gegen finalisierte Version -> 409 EXIT_REVIEW_NOT_EDITABLE.

### AT-S11-025 – Identische Inputs bleiben CURRENT
Revalidation ohne semantische Änderung -> Fingerprint identisch.

### AT-S11-026 – Korrigierter SELL macht Review STALE
Upstream-Korrektur -> Revalidation -> CURRENT -> STALE,
Bewertungen/rationale bleiben unverändert.

### AT-S11-027 – Technischer Refresh macht nicht STALE
Keine fachliche Änderung -> Fingerprint stabil.

### AT-S11-028 – Neue Review-Version nach Staleness
Version 1 FINALIZED/STALE -> Version 2 DRAFT mit supersedes_version_id.

### AT-S11-029 – Nur ein offener Draft
Wiederholte/parallele Draft-Erzeugung -> höchstens ein DRAFT, kontrollierter 409.

### AT-S11-030 – External Trade ohne Plan bleibt beobachtbar
Full Exit + Underlying/EOD auflösbar -> Observation erlaubt.

### AT-S11-031 – Fehlende Provenance wird nicht erfunden
Keine synthetischen Targets/Stops.

### AT-S11-032 – NOT_ASSESSABLE bleibt zulässig
Zum Beispiel PROCESS_ADHERENCE bei fehlendem Plan-Kontext.

### AT-S11-033 – DRAFT ist nicht handoff-ready
ready = false.

### AT-S11-034 – STALE ist nicht handoff-ready
ready = false.

### AT-S11-035 – CURRENT FINALIZED + COMPLETED ist handoff-ready
Nach erfolgreicher Revalidation -> ready = true.

## REST Acceptance

Mindestens testen:

POST /api/v1/post-trade/trades/{trade_id}/observation
GET  /api/v1/post-trade/trades/{trade_id}/observation
GET  /api/v1/post-trade/trades/{trade_id}/observation/evidence

POST /api/v1/post-trade/trades/{trade_id}/exit-review
GET  /api/v1/post-trade/trades/{trade_id}/exit-review
PUT  /api/v1/post-trade/trades/{trade_id}/exit-review/draft
POST /api/v1/post-trade/trades/{trade_id}/exit-review/finalize
POST /api/v1/post-trade/trades/{trade_id}/exit-review/revalidate
GET  /api/v1/post-trade/trades/{trade_id}/exit-review/history

GET  /api/v1/post-trade/trades/{trade_id}/handoff

Zusätzlich prüfen:

- 201 bei Creation;
- 200 bei Reads/erfolgreichen Commands;
- 404 bei fehlenden Ressourcen;
- 409 bei Lifecycle-/Concurrency-Konflikten;
- 422 bei fachlichen Preconditions;
- stabile Fehlercodes;
- keine erwartbaren Domain-Konflikte als 500.

## Migration Acceptance

Alembic-Basis:

20260817_0018

Mindestens prüfen:

- upgrade erfolgreich;
- post_trade_observations vorhanden;
- UNIQUE(trade_id);
- exit_reviews vorhanden;
- UNIQUE(post_trade_observation_id);
- exit_review_versions vorhanden;
- UNIQUE(exit_review_id, version);
- Fremdschlüssel vorhanden;
- Status-/Assessment-Checks vorhanden;
- keine Observation-Point-Kurstabelle.

## Integration E2E

Datei:

tests/integration/backend/test_ft011_post_trade_e2e.py

Happy Path:

Trade kaufen
-> vollständiger SELL
-> FT-011 eligible
-> Observation starten
-> 20 EOD-Preise
-> COMPLETED
-> ExitReview DRAFT
-> Bewertungen speichern
-> finalisieren
-> CURRENT
-> FT-012 handoff ready

Kritischer Correction Path:

Happy Path
-> Review finalisiert
-> SELL upstream korrigieren
-> revalidate
-> Review STALE
-> Handoff false
-> Review Version 2
-> finalisieren
-> CURRENT
-> Handoff true

## Minimaler Frontend-Scope

Favorisierte Struktur:

frontend/src/features/post_trade/
    pages/
        PostTradeReviewPage.tsx
        PostTradeReviewPage.test.tsx
    services/
        client.ts
        client.test.ts
    types/
        api.ts
    components/
        ObservationProgress.tsx
        ExitEvidence.tsx
        ExitReviewForm.tsx
        ReviewHistory.tsx

V1 benötigt eine zentrale PostTradeReviewPage.

## Einstieg aus Trade Management

Nicht eligible:

Nachbeobachtung noch nicht verfügbar
Trade besitzt weiterhin offene Position.

Eligible, nicht gestartet:

Trade geschlossen
[ Nachbeobachtung starten ]

Observation vorhanden:

[ Nachbeobachtung öffnen ]

## PostTradeReviewPage

Kopfbereich mindestens:

- Trade geschlossen am ...
- Warrant ...
- Underlying ...
- Observation-Serie ...
- Warrant-Maturity ...

Fortschritt:

13 / 20 EOD-Beobachtungen
Nachbeobachtung läuft

oder:

20 / 20
Nachbeobachtung abgeschlossen

Datenlücken bleiben sichtbar.

## Evidence

Visuell getrennt:

### Tatsächlicher Exit
- tatsächliche SELLs;
- Preise;
- Mengen;
- Zeitpunkte;
- reales Brutto-P&L.

### Danach beobachtet
- Underlying-EOD-Serie;
- Highest High;
- Lowest Low;
- Final Close;
- Plan Target Crossings;
- Plan Stop Crossing;
- spätere Management-Level;
- Maturity-Kontext.

Keine Formulierung wie:

entgangener sicherer Gewinn

## Review-Formular

Felder:

- Timing
- Process Adherence
- Risk Decision
- Overall Exit Decision
- Begründung

UI-Texte:

- Gut
- Vertretbar
- Verbesserungswürdig
- Nicht belastbar beurteilbar

API-Werte:

- GOOD
- ACCEPTABLE
- IMPROVABLE
- NOT_ASSESSABLE

Während DRAFT:

[ Entwurf speichern ]
[ Exit Review finalisieren ]

Nach Finalisierung:

Exit Review finalisiert

read-only.

## STALE UX

Anzeige:

Ausgangsdaten wurden geändert

Dieser Review wurde auf Basis einer älteren Faktenlage finalisiert.

[ Review erneut prüfen ]

Alte Version bleibt in Review-Historie sichtbar.

## Frontend Acceptance Tests

### FE-S11-001
Start-Button nur bei eligible closed trade.

### FE-S11-002
Start erzeugt Observation und öffnet Review-Seite.

### FE-S11-003
13/20 wird korrekt dargestellt.

### FE-S11-004
20/20 zeigt COMPLETED.

### FE-S11-005
Actual und Counterfactual sind getrennt beschriftet.

### FE-S11-006
Maturity-Hinweis sichtbar.

### FE-S11-007
Draft kann gespeichert und erneut geladen werden.

### FE-S11-008
Finalize bei unvollständigem Formular nicht erfolgreich.

### FE-S11-009
Finalized Review ist read-only.

### FE-S11-010
STALE-Hinweis und "Review erneut prüfen" erscheinen.

### FE-S11-011
Historische Review-Version bleibt sichtbar.

### FE-S11-012
Backend-Fehlercodes werden in verständliche Hinweise übersetzt.

## V1-Frontend Non-Scope

Nicht erforderlich:

- Post-Trade-Dashboard über alle Trades;
- Intraday-Charts;
- hypothetischer Warrant-P&L-Chart;
- automatischer Exit-Score;
- KI-generierte Review-Begründung;
- Journal-Editor;
- Lessons-Learned-Editor;
- Performance-Dashboard.

## Definition of Ready

FT-011 ist technisch implementierungsbereit, wenn:

- Baseline vorhanden;
- ADR-S11-001 bis ADR-S11-010 vorhanden;
- physisches Datenmodell entschieden;
- Review-Versionierung entschieden;
- Input-Fingerprint entschieden;
- UoW-/Repository-Grenzen entschieden;
- REST-/Fehlercontract entschieden;
- Acceptance Tests enumeriert;
- minimaler Frontend-Flow entschieden;
- Alembic-Basis 20260817_0018 bestätigt.

## Favorisierte Implementierungsreihenfolge

1. Domain Enums / Models
2. Migration
3. Persistence Models / Mapping / Repositories / UoW
4. Read Ports / Resolver
5. Fingerprint / Metrics
6. Application Service
7. REST DTOs / Router / Errors / Bootstrap
8. Backend Unit Tests
9. Backend Integration E2E
10. Frontend API Types / Client
11. PostTradeReviewPage
12. TradeManagement Entry Point
13. Frontend Tests
14. Full Quality Gate
