# FT-007 – TradePlan V1

## Status

Approved for Build – Sprint 6, 2026-08-11.

## Nutzerproblem und Ziel

Der Benutzer benötigt zwischen Candidate Qualification beziehungsweise manueller Underlying-Auswahl und späterer Product Selection einen reproduzierbaren, produktneutralen Planungsstand. FT-007 ermöglicht, einen TradePlan zu erstellen, fachlich zu prüfen, versioniert zu ändern und eine konkrete Version explizit freizugeben.

Trading Workspace trifft keine Handelsentscheidung. Entry, Stop, Invalidation, Targets, Risikoannahmen und Approval bleiben Benutzerentscheidungen; das System validiert ausschließlich Konsistenz und dokumentiert Provenance.

## Scope V1

- langlebige TradePlan-Identität;
- immutable TradePlanVersion-Snapshots;
- Ursprung aus konkreter CandidateEvaluation oder manuell gewähltem Underlying;
- LONG-only;
- Thesis;
- produktneutraler Entry;
- Stop und fachliche Invalidation;
- geordnete Targets;
- Plan-Risiko und transparente, nicht entscheidende Ableitungen;
- Lifecycle und explizites Approval;
- Amendment nach Approval als neue Version;
- Provenance, Audit, Persistence, REST API, Frontend und Tests.

## Non-Scope V1

Nicht Bestandteil sind Warrant-/Issuer-/Produktattribute, Produktauswahl, Warrant Scoring, automatische Position Size, Portfolio Risk, Order Quantity, Execution, Broker API, Position Management, SHORT Candidate Qualification und automatische Trade-Freigabe.

## Aggregate Ownership

FT-007 besitzt `TradePlan` und `TradePlanVersion`.

FT-007 referenziert, aber besitzt nicht:

- Workspace;
- Underlying;
- Candidate;
- CandidateEvaluation;
- Analysis Runs / Market Context / Relative Strength;
- spätere Product Selection oder Execution Records.

## TradePlan Identity

`TradePlan` ist die langlebige fachliche Identität einer Planung innerhalb eines Workspace und für genau ein Underlying.

Identity-Felder:

- `id`;
- `workspace_id`;
- `underlying_id`;
- `origin_type` (`CANDIDATE_EVALUATION`, `MANUAL`);
- bei Candidate-Ursprung `candidate_id` und konkrete `candidate_evaluation_id`;
- `created_at`, `created_by`.

Der Ursprung wird nach Anlage nicht umgebogen. Ein manuell angelegter TradePlan wird nicht nachträglich Candidate-originated; ebenso wird eine konkrete CandidateEvaluation nie durch eine neuere ersetzt.

## TradePlanVersion

Jede fachliche Änderung erzeugt einen neuen immutable Snapshot mit monoton steigender Versionsnummer je TradePlan.

Versionierte Inhalte:

- `version`;
- `direction` (V1 ausschließlich `LONG`);
- `thesis`;
- `entry`;
- `invalidation`;
- `targets`;
- `risk_assumptions`;
- `status`;
- `change_reason` bei Amendment;
- `previous_version_id`;
- `created_at`, `created_by`.

Ein historischer Versions-Snapshot wird nicht fachlich überschrieben. Statusänderungen, die Historie erzeugen müssen, werden als neue Version beziehungsweise explizites Audit-/Approval-Ereignis dokumentiert.

## Origin und CandidateEvaluation-Handoff

### Candidate-originated

```text
Candidate
  → konkrete immutable CandidateEvaluation
  → TradePlan
  → TradePlanVersion
```

Voraussetzungen:

- Candidate und CandidateEvaluation gehören zum selben Workspace;
- Evaluation gehört zum Candidate;
- Candidate und Evaluation beziehen sich auf dasselbe Underlying wie der TradePlan;
- V1 akzeptiert nur LONG-kompatible CandidateEvaluationen;
- `READY_FOR_PLANNING` ist keine Approval-Voraussetzung auf Datenbankebene und kein automatisches Approval; die UI darf es als Prozesshinweis nutzen.

Spätere Re-Evaluationen verändern keine bestehende TradePlan-Referenz.

### Manual-originated

```text
Underlying
  → TradePlan
```

Candidate- und CandidateEvaluation-Referenzen sind leer. Der Benutzer wählt ein aktives, referenzierbares Underlying explizit aus.

## Direction V1

FT-007 V1 ist vollständig LONG-only, auch für manuell angelegte TradePlans. `direction` wird dennoch explizit als versioniertes Domainfeld gespeichert. SHORT wird erst mit eigener fachlicher Spezifikation und Validierungssemantik eingeführt und nicht durch Spiegelung von LONG-Regeln abgeleitet.

## Lifecycle

V1 verwendet folgende Zustände je fachlichem Versionsstand:

- `DRAFT` – bearbeitbarer Planungsstand;
- `READY_FOR_REVIEW` – alle Approval-Pflichtfelder sind vorhanden und der Benutzer hat Review angefordert;
- `APPROVED` – konkrete immutable Version explizit freigegeben;
- `ABANDONED` – Planung wird bewusst nicht weiterverfolgt;
- `SUPERSEDED` – historischer Approved-Stand, für den ein neuerer Approved-Stand desselben TradePlans existiert.

`REJECTED` ist V1 kein eigener TradePlan-Status. Ohne getrennte Reviewer-Rolle beschreibt `ABANDONED` die fachlich relevante negative Benutzerentscheidung eindeutiger.

### Zulässige Benutzeraktionen

```text
DRAFT → READY_FOR_REVIEW
DRAFT → ABANDONED
READY_FOR_REVIEW → DRAFT
READY_FOR_REVIEW → APPROVED
READY_FOR_REVIEW → ABANDONED
APPROVED → amendment → neue DRAFT-Version
neue DRAFT/READY_FOR_REVIEW → ABANDONED
```

Wenn eine Amendment-Version Approved wird, bleibt die vorherige Approval historisch erhalten und wird als `SUPERSEDED` sichtbar.

## Approval

Approval ist eine separate explizite Benutzeraktion für genau eine immutable TradePlanVersion.

Pflichtnachweis:

- `trade_plan_id`;
- `trade_plan_version_id` und Versionsnummer;
- Actor/Benutzer;
- Approval-Zeitpunkt;
- Request-/Correlation-Identität gemäß bestehendem Pattern;
- Audit Event.

Approval darf nicht aus Candidate-Status, Qualification, Analyseergebnis oder einer Berechnung automatisch entstehen.

Approval-Voraussetzungen V1:

- Version ist `READY_FOR_REVIEW`;
- Direction ist `LONG`;
- nichtleere Thesis;
- gültiger Entry;
- Stop oder fachliche Invalidation ist definiert;
- mindestens ein Target;
- Targets sind geordnet und fachlich oberhalb des relevanten Entry-Preisniveaus, soweit preisbasiert;
- Stop liegt bei preisbasierter LONG-Planung unter dem relevanten Entry-Niveau;
- alle Pflicht-Risikoannahmen sind vorhanden;
- Origin-Referenzen sind konsistent.

## Amendment nach Approval

Ein Approved-Snapshot wird nie editiert. Änderungen an Thesis, Entry, Stop/Invalidation, Targets oder Risikoannahmen erzeugen eine neue `DRAFT`-Version mit:

- `previous_version_id` auf den vorherigen Stand;
- verpflichtendem `change_reason` bei Ursprung aus einer Approved-Version;
- neuem Actor-/Zeitnachweis.

Die neue Version benötigt ein eigenes Approval. Ein späteres Product-Selection-Objekt referenziert die konkrete Approved-Version und verändert sie nicht.

## Entry-Modell V1

`EntryPlan` ist produktneutral und unterstützt:

- `PRICE` – einzelnes Underlying-Preisniveau;
- `PRICE_RANGE` – Unter- und Obergrenze;
- `TRIGGER` – textuell/strukturiert beschriebene fachliche Bedingung mit optionalem Referenzpreis.

Felder:

- `type`;
- `price` oder `price_from`/`price_to`;
- optional `trigger`;
- `currency` aus dem relevanten Underlying-/Listing-Kontext, nicht als Produktwährung;
- optional `valid_until`;
- optional `rationale`.

Keine Orderart, Stückzahl, Warrant-Preis oder Brokersemantik.

## Stop und Invalidation V1

`InvalidationPlan` trennt Preis-Stop und fachliche Invalidierung:

- optional `stop_price`;
- optional `invalidation_rule`;
- verpflichtende `rationale`, wenn nur eine fachliche Regel ohne Preis-Stop vorliegt.

Mindestens eine der beiden Varianten muss für Approval definiert sein. Keine automatische Ausführung.

## Targets V1

Ein TradePlan besitzt mindestens ein geordnetes Target.

`Target` enthält:

- `sequence` ab 1 ohne Lücken;
- `price`;
- optional `rationale`.

Teilverkaufsquoten und Ordermengen sind Non-Scope. Mehrere Targets dokumentieren lediglich fachliche Zielstufen.

## Risk Boundary

FT-007 speichert vom Benutzer gesetzte Planannahmen und darf transparente Ableitungen anzeigen, zum Beispiel Distanz zwischen Entry und Stop oder prozentuale Plan-Distanz.

```text
Plan Risk
≠ Position Sizing
≠ Portfolio Allocation
≠ Order Quantity
≠ Execution
```

V1 erzeugt keine Empfehlung, wie viel Kapital oder wie viele Stücke eingesetzt werden sollen.

## Provenance / Snapshot Policy

Für jede Version sind mindestens reproduzierbar:

- TradePlan-ID und Version;
- Origin;
- Underlying;
- Candidate und konkrete CandidateEvaluation, falls vorhanden;
- Versionseingaben;
- Actor;
- Zeitpunkte;
- Lifecycle-/Approval-Nachweis;
- `previous_version_id` und Änderungsgrund;
- Request-/Correlation-Information gemäß bestehender Audit-Infrastruktur.

FT-007 dupliziert keine Market-/Candidate-Berechnungen. Candidate-originated Provenance wird über die konkrete CandidateEvaluation transitiv nachvollziehbar; deren bereits gespeicherte Analyse-IDs und Modellversionen bleiben Source of Truth.

Stammdaten werden nur dort gesnapshottet, wo bestehende Repository-Konventionen dies zur historischen Darstellung verlangen. Fachliche IDs und immutable Bewertungs-/Versionsreferenzen haben Vorrang vor Kopien veränderlicher Objekte.

## Audit

Mindestens folgende Ereignisse sind fachlich relevant:

- `TRADE_PLAN_CREATED`;
- `TRADE_PLAN_VERSION_CREATED`;
- `TRADE_PLAN_READY_FOR_REVIEW`;
- `TRADE_PLAN_RETURNED_TO_DRAFT`;
- `TRADE_PLAN_APPROVED`;
- `TRADE_PLAN_ABANDONED`;
- `TRADE_PLAN_AMENDED`;
- `TRADE_PLAN_SUPERSEDED`.

Audit nutzt die vorhandene append-only Infrastruktur und zentrale Request Identity; keine parallele Audit-Lösung in FT-007.

## REST Contract – Zielbild

Der konkrete DTO-/Router-Schnitt wird in der Implementierungsunit gegen bestehende FastAPI-Patterns finalisiert. Zielbild:

- `POST /api/v1/trade-plans`;
- `GET /api/v1/trade-plans`;
- `GET /api/v1/trade-plans/{trade_plan_id}`;
- `GET /api/v1/trade-plans/{trade_plan_id}/versions`;
- `POST /api/v1/trade-plans/{trade_plan_id}/versions`;
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version}/ready-for-review`;
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version}/return-to-draft`;
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version}/approve`;
- `POST /api/v1/trade-plans/{trade_plan_id}/versions/{version}/abandon`.

Commands müssen erwartete Version/Concurrency berücksichtigen und bestehende REST-Error-Konventionen verwenden.

## Frontend-Zielbild

FT-007 erhält eine eigene Feature-Grenze `frontend/src/features/trade_plan/` und verwendet vorhandene API-/Routing-/State-Patterns.

V1 benötigt mindestens:

- TradePlan-Liste;
- Create Flow: CandidateEvaluation oder Manual Underlying;
- Editor für DRAFT-Version;
- Versionshistorie;
- Review-/Approval-Ansicht;
- sichtbare Provenance bei Candidate-Ursprung;
- Amendment-Aktion von Approved;
- klare Kennzeichnung, dass keine Handelsentscheidung oder Order erfolgt.

## Akzeptanzkriterien

1. Ein Benutzer kann einen LONG-TradePlan aus einem Underlying manuell anlegen.
2. Ein Benutzer kann einen LONG-TradePlan aus Candidate + konkreter CandidateEvaluation anlegen; die Referenz bleibt bei späterer Re-Evaluation unverändert.
3. Fachliche Änderungen erzeugen neue immutable Versionen; historische Versionen bleiben lesbar.
4. Eine Version kann nur bei erfüllten Pflichtvalidierungen `READY_FOR_REVIEW` werden.
5. Approval ist eine explizite Benutzeraktion und gilt nur für die konkrete Version.
6. Ein Approved-Snapshot kann nicht in-place geändert werden.
7. Amendment erzeugt eine neue DRAFT-Version mit Referenz auf den Vorgänger und Änderungsgrund.
8. Approval einer Amendment-Version lässt den früheren Approved-Stand historisch nachvollziehbar und als superseded erkennen.
9. FT-007 enthält keine Warrant-, Issuer-, Leverage-, Spread-, Ratio-, Expiry- oder Product-Score-Felder.
10. FT-007 berechnet Candidate Qualification, Market Context oder Relative Strength nicht neu.
11. FT-007 erzeugt keine Position Size, Order Quantity oder Execution.
12. Audit und Provenance weisen Actor, Zeitpunkt, Version und Ursprung nachvollziehbar nach.
13. Concurrent/Stale Writes werden gemäß bestehender Optimistic-Concurrency-/REST-Konvention kontrolliert abgewiesen.
14. Backend-, API-, Persistence-, Frontend- und E2E-Tests decken Lifecycle, Versionierung, Approval, Amendment und Origin ab.

## Verbindliche ADRs

- ADR-S6-001 TradePlan Identity & Versioning;
- ADR-S6-002 TradePlan Origin & CandidateEvaluation Handoff;
- ADR-S6-003 TradePlan Lifecycle & Approval;
- ADR-S6-004 Amendment after Approval;
- ADR-S6-005 Risk / Position-Sizing Boundary;
- ADR-S6-006 Product Neutrality;
- ADR-S6-007 Provenance / Snapshot Policy;
- ADR-S6-008 LONG-only Scope.
