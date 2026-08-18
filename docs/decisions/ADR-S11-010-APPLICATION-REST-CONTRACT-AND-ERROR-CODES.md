# ADR-S11-010 – Application-/REST-Contract und fachliche Fehlercodes

## Status

Accepted for Sprint 11 technical Definition of Ready.

## Kontext

FT-011 besitzt mehrere fachlich unterschiedliche Benutzeraktionen:

- Eligibility lesen;
- PostTradeObservation starten;
- Observation und Fortschritt lesen;
- Observation-Evidenz lesen;
- ExitReview-Draft anlegen;
- Draft bearbeiten;
- Review finalisieren;
- Review-Historie lesen;
- Staleness revalidieren;
- FT-012-Handoff prüfen.

Diese Aktionen besitzen unterschiedliche Preconditions und dürfen nicht in
einem generischen CRUD- oder Status-PATCH verborgen werden.

FT-010 bleibt Owner des bestehenden Eligibility-Handoffs.

## Entscheidung

### Eigene FT-011 API-Grenze

Favorisierter Prefix:

/api/v1/post-trade

FT-011 bleibt damit als eigenes Feature sichtbar.

## Observation starten

POST /api/v1/post-trade/trades/{trade_id}/observation

Request Body:

{}

Actor-/Request-Kontext folgt dem bestehenden Header-Pattern, insbesondere:

- X-Actor-ID
- X-Correlation-ID

Erfolg:

201 Created

Der Service:

1. lädt den Trade;
2. prüft FT-011 Eligibility;
3. prüft bestehende Observation;
4. löst Underlying-Kontext auf;
5. löst die konkrete Underlying-Listing-ID auf;
6. legt die Observation an;
7. committet atomar.

Ein zweiter Start erzeugt keine zweite Observation.

Fehler:

409 POST_TRADE_OBSERVATION_ALREADY_EXISTS

## Observation lesen

GET /api/v1/post-trade/trades/{trade_id}/observation

Erfolg:

200 OK

Mindestens enthalten:

- id
- trade_id
- status
- underlying_listing_id
- target_observation_count
- available_observation_count
- started_at
- completed_at
- created_at

Zusätzlich deterministisch ableitbar:

- is_complete
- missing_observation_count

Nicht vorhanden:

404 POST_TRADE_OBSERVATION_NOT_FOUND

## Observation Evidence

GET /api/v1/post-trade/trades/{trade_id}/observation/evidence

Der Endpoint liefert ein Read Model aus:

Observation
+ DailyPrice
+ historischer Provenance
+ effektiver FT-010-Historie

Actual Exit enthält mindestens:

- effektive SELL-Historie;
- finalen Full-Exit-Zeitpunkt;
- tatsächliche Mengen und Preise;
- realisiertes FT-010-Brutto-P&L.

Counterfactual Evidence enthält mindestens:

- Observation Points;
- Datenvollständigkeit;
- Highest High;
- Lowest Low;
- Final Close;
- Target-Crossings;
- Stop-Crossings;
- Management-Level-Crossings;
- Maturity-Kontext.

Actual und Counterfactual bleiben im DTO explizit getrennt.

## Observation Completion

Der Nutzer setzt den Status nicht manuell.

Es gibt keinen frei editierbaren:

status = COMPLETED

Command.

Die Application-Service-Schicht prüft deterministisch, ob 20 verwendbare
EOD-Beobachtungen erreicht wurden.

Dann darf:

ACTIVE -> COMPLETED

atomar persistiert werden.

## ExitReview-Draft anlegen

POST /api/v1/post-trade/trades/{trade_id}/exit-review

Semantik:

- noch kein Review-Kontext:
  ExitReview + Version 1 DRAFT erzeugen;

- offener DRAFT vorhanden:
  keinen zweiten DRAFT erzeugen;

- FINALIZED/CURRENT vorhanden:
  keinen neuen Draft erzeugen;

- FINALIZED/STALE vorhanden:
  neue DRAFT-Version ist zulässig.

Erfolg:

201 Created

Konflikte:

409 EXIT_REVIEW_DRAFT_ALREADY_EXISTS
409 EXIT_REVIEW_ALREADY_CURRENT

## ExitReview lesen

GET /api/v1/post-trade/trades/{trade_id}/exit-review

Mindestens enthalten:

- exit_review_id
- current_version_id
- version
- status
- currentness
- timing
- process_adherence
- risk_decision
- overall_exit_decision
- rationale
- created_at
- created_by
- finalized_at
- finalized_by
- stale_at
- stale_reason

## Draft bearbeiten

PUT /api/v1/post-trade/trades/{trade_id}/exit-review/draft

Request:

{
  "timing": "GOOD",
  "process_adherence": "ACCEPTABLE",
  "risk_decision": "GOOD",
  "overall_exit_decision": "ACCEPTABLE",
  "rationale": "..."
}

PUT wird gegenüber einem freien JSON-PATCH bevorzugt.

Der kleine Review-Draft wird als fachlich vollständige editierbare Ressource
behandelt.

Während DRAFT dürfen Felder mehrfach geändert werden.

Eine FINALIZED-Version ist über diesen Endpoint nicht editierbar.

Fehler:

409 EXIT_REVIEW_NOT_EDITABLE

## Review finalisieren

POST /api/v1/post-trade/trades/{trade_id}/exit-review/finalize

Request Body:

{}

Preconditions:

- Observation == COMPLETED;
- DRAFT vorhanden;
- alle vier Bewertungsdimensionen gesetzt;
- rationale nicht leer;
- aktueller semantischer Fingerprint berechenbar.

Erfolg:

200 OK

Finalisierung setzt atomar:

- status = FINALIZED
- currentness = CURRENT
- input_fingerprint
- finalized_at
- finalized_by

Das Speichern des Drafts finalisiert den Review nicht automatisch.

## Staleness revalidieren

POST /api/v1/post-trade/trades/{trade_id}/exit-review/revalidate

Semantik:

1. finalisierte aktuelle Version laden;
2. aktuellen semantischen Fingerprint berechnen;
3. mit gespeichertem Fingerprint vergleichen;
4. bei Differenz CURRENT -> STALE persistieren.

Erfolg:

200 OK

Ein normaler GET soll nach Möglichkeit ein Read bleiben.

Die explizite Revalidation macht die mögliche Mutation sichtbar.

Vor FT-012-Handoff ist serverseitige Revalidation trotzdem verpflichtend.

## Review-Historie

GET /api/v1/post-trade/trades/{trade_id}/exit-review/history

Liefert alle Review-Versionen in stabiler Reihenfolge.

Mindestens:

- version
- status
- currentness
- Bewertungen
- rationale
- created_at
- finalized_at
- supersedes_version_id
- stale_at
- stale_reason

## FT-012-Handoff

GET /api/v1/post-trade/trades/{trade_id}/handoff

Response enthält mindestens:

- ready
- reason
- post_trade_observation_id
- exit_review_id
- exit_review_version_id

ready == true nur wenn:

Observation == COMPLETED
AND
Review == FINALIZED
AND
Review == CURRENT
AND
Fingerprint-Revalidation erfolgreich

## Fachliche Fehlercodes

FT-011 liefert stabile strukturierte Fehlercodes.

Favorisiertes Format:

{
  "code": "POST_TRADE_NOT_ELIGIBLE",
  "message": "Trade is not eligible for post-trade observation.",
  "details": {}
}

message ist menschenlesbar.

code ist der stabile Client-Contract.

details enthält strukturierte fachliche Zusatzinformationen.

### 404 – Ressource fehlt

Mindestens:

- TRADE_NOT_FOUND
- POST_TRADE_OBSERVATION_NOT_FOUND
- EXIT_REVIEW_NOT_FOUND
- EXIT_REVIEW_VERSION_NOT_FOUND

### 409 – aktueller Zustand verhindert Command

Mindestens:

- POST_TRADE_OBSERVATION_ALREADY_EXISTS
- EXIT_REVIEW_DRAFT_ALREADY_EXISTS
- EXIT_REVIEW_ALREADY_CURRENT
- EXIT_REVIEW_NOT_EDITABLE
- EXIT_REVIEW_NOT_CURRENT
- CONCURRENT_POST_TRADE_CHANGE

409 wird bevorzugt, wenn der Request grundsätzlich gültig ist, aber der
aktuelle Ressourcenstatus die Aktion verhindert.

### 422 – fachliche Voraussetzungen / Eingabe

Mindestens:

- POST_TRADE_NOT_ELIGIBLE
- UNDERLYING_LISTING_NOT_RESOLVABLE
- UNDERLYING_LISTING_AMBIGUOUS
- OBSERVATION_HORIZON_NOT_COMPLETE
- EXIT_REVIEW_INCOMPLETE
- EXIT_REVIEW_RATIONALE_REQUIRED
- INVALID_EXIT_REVIEW_ASSESSMENT

## Unvollständige Market-Data-Evidenz

Fehlende Observationen sind nicht automatisch ein technischer Fehler.

Beispiel:

200 OK

mit:

available_observation_count = 18
target_observation_count = 20
status = ACTIVE

Erst ein Command, der vollständige Evidenz voraussetzt, erhält zum Beispiel:

422 OBSERVATION_HORIZON_NOT_COMPLETE

## Keine erwartbaren Domain-Konflikte als 500

Concurrency- oder Unique-Constraint-Konflikte werden an Service-/API-Grenze
auf stabile fachliche Fehler übersetzt.

Ein Doppelklick auf "Nachbeobachtung starten" darf keinen ungefangenen
IntegrityError beim Nutzer erzeugen.

## Auswirkungen für den Nutzer

Die UI kann direkte fachliche Aktionen anbieten:

- Nachbeobachtung starten
- Entwurf speichern
- Exit Review finalisieren
- Review erneut prüfen

Der Nutzer editiert keine technischen Lifecycle-Statuswerte.

Fehler können verständlich dargestellt werden, zum Beispiel:

Nachbeobachtung noch nicht möglich:
Der Trade ist noch nicht vollständig geschlossen.

oder:

Review kann noch nicht finalisiert werden:
18 von 20 Beobachtungen sind verfügbar.

Das bloße Ausfüllen des Review-Formulars finalisiert nichts.

Die letzte Benutzerentscheidung bleibt ausdrücklich:

[ Exit Review finalisieren ]

## Begründung

Explizite Command-Endpunkte machen die Domain-Semantik sichtbar.

start, finalize und revalidate besitzen eigene Preconditions und
Transaktionsgrenzen und sind keine beliebigen Feldänderungen.

Stabile Fehlercodes verhindern, dass das Frontend von englischen
Fehlermeldungsstrings abhängt.

PUT für den kleinen Review-Draft wird gegenüber generischem JSON-PATCH
bevorzugt, weil der Draft als zusammenhängende editierbare Ressource behandelt
wird.

Explizites Revalidate verhindert versteckte Mutation in gewöhnlichen GETs.

## Invarianten

### INV-S11-081
FT-010 bleibt Owner des Eligibility-Handoffs.

### INV-S11-082
Observation-Start ist ein expliziter FT-011-Command.

### INV-S11-083
Ein zweiter Start erzeugt keine zweite Observation.

### INV-S11-084
Observation Evidence trennt Actual und Counterfactual.

### INV-S11-085
Observation Completion ist keine frei setzbare Benutzeraktion.

### INV-S11-086
Review-Finalisierung ist ein expliziter Command.

### INV-S11-087
Eine FINALIZED-Version ist über den Draft-Endpunkt nicht editierbar.

### INV-S11-088
Stabile fachliche Fehlercodes sind Teil des REST-Contracts.

### INV-S11-089
Erwartbare Domain- und Concurrency-Konflikte werden nicht als ungefangene
500-Fehler exponiert.

### INV-S11-090
FT-012-Handoff meldet ready nur nach COMPLETED + FINALIZED + CURRENT +
erfolgreicher Revalidation.
