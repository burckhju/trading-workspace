# Operational Workspace

## Status und Einordnung

Der Operational Workspace ist eine **nicht nummerierte, technische Querschnittsfähigkeit**. Er erhält keine eigene FT-Nummer und übernimmt keine fachliche Schreib-Ownership von bestehenden Features.

Seine Aufgabe ist ausschließlich, bereits autoritative Zustände anderer Features in eine priorisierte, ephemere Liste konkreter nächster Benutzeraktionen zu projizieren.

## Grundprinzip

Der Workspace ist **read-only**:

- keine eigenen fachlichen Lifecycle-Zustände,
- kein Done-/Acknowledge-/Assignment-State,
- keine automatische Handelsentscheidung,
- keine automatische Produktauswahl,
- keine Order- oder Positionsgrößenentscheidung,
- keine Mutation der projizierten Owner-Features.

Eine Action verschwindet ausschließlich dadurch, dass sich der autoritative Zustand im jeweiligen Owner-Feature ändert. Der Workspace selbst persistiert keine Action-Entitäten.

## API und Projektion

Der Backend-Einstieg ist:

`GET /api/v1/operational-workspace/actions`

Die Antwort enthält einen Erzeugungszeitpunkt und deterministisch projizierte Actions. Die Projektion ist workspace-scoped und wird bei jedem Read aus den aktuellen Owner-Zuständen abgeleitet.

## Priorisierung

Die Projektion verwendet drei Prioritätsklassen:

1. `ACTION` – konkrete Benutzerhandlung ist möglich oder erforderlich,
2. `REVIEW` – explizite fachliche Prüfung bzw. Review ist offen,
3. `BLOCKED` – ein bestehender Workflow kann wegen einer autoritativen Voraussetzung nicht fortgesetzt werden.

Innerhalb einer Priorität erfolgt die Sortierung deterministisch über fachlichen Zeitpunkt und Action-ID.

## Projizierte Owner-Zustände

### Candidate / FT-005 und FT-020

Der Workspace konsumiert die bestehende Candidate-Live-Readiness. Er projiziert entweder die nächste Candidate-Evaluation als `ACTION` oder die bereits vom Owner bestimmte blockierende Voraussetzung als `BLOCKED`.

Ziel: `/candidates`

### TradePlan / FT-007

Ist die **aktuelle** TradePlan-Version `READY_FOR_REVIEW`, wird eine Review-Action zur expliziten Prüfung und Freigabe projiziert.

Ziel: `/trade-plans?trade_plan_id=<id>`

### Product Selection starten / FT-007 → FT-008

Ist die aktuelle TradePlan-Version `APPROVED` und existiert für genau diese Version noch kein ProductSelectionRun, wird „Produktauswahl starten“ projiziert.

Ziel: `/product-selection?trade_plan_id=<id>&trade_plan_version_id=<id>`

### Explizite Produktauswahl / FT-008

Existiert ein ProductSelectionRun mit mindestens einer `ELIGIBLE` ProductEvaluation, aber noch keine ProductSelection, wird „Produkt auswählen“ projiziert.

FT-008 definiert keinen Supersede-/Currentness-State für Selection Runs. Der Workspace erfindet deshalb keine zusätzliche Latest-Run-Regel.

Ziel: `/product-selection?run_id=<id>`

### Initialen BUY erfassen / FT-008 → FT-009

Existiert eine ProductSelection, aber noch kein FT-009 Trade, der exakt diese `product_selection_id` referenziert, wird „Kauf erfassen“ projiziert.

Der Workspace leitet weder Kaufmenge noch Preis ab und erzeugt keinen Trade automatisch.

Ziel: `/product-selection?run_id=<id>`

### Offene Position / FT-009 und FT-010

Eine bestehende offene Position wird als Management-Action projiziert. Die eigentliche Trade-/Position-/Management-Logik bleibt vollständig bei FT-009/FT-010.

Ziel: `/trade-management?trade_id=<id>`

### Position Monitoring und Alerts

Bestehende offene Position-Alerts werden als konkrete Trade-Management-Actions projiziert. Der Workspace erzeugt oder quittiert keine Alerts.

Ziel: `/trade-management?trade_id=<id>`

### Notification Delivery

Terminal fehlgeschlagene Notifications werden als Action projiziert. Retry-, Delivery- und Notification-State bleiben bei der Notification Capability.

Ziel: `/trade-management?trade_id=<id>`

### Post Trade / FT-011

Für geschlossene Trades projiziert der Workspace ausschließlich bereits durch FT-011 definierte Übergänge: Nachbeobachtung starten, Exit Review erstellen, einen aktuellen Entwurf abschließen oder ein fehlendes aktuelles Review aktualisieren. Ein finalisiertes aktuelles Review erzeugt keine Action.

Ziel: `/post-trade?trade_id=<id>`

## Ownership-Grenze

Der Operational Workspace ist ein Leser der Owner-Features. Schreibende Owner bleiben insbesondere:

- FT-005/FT-020 für Candidate-Zustände,
- FT-007 für TradePlan und TradePlanVersion,
- FT-008 für ProductSelectionRun, ProductEvaluation und ProductSelection,
- FT-009 für Trade, ExecutionRecord und Position,
- FT-010 für Trade-Management-Zustände,
- FT-011 für Post-Trade-Beobachtung und Exit Review,
- Position Monitoring für Alerts,
- Notification Delivery für Notifications und Delivery Attempts.

Der Workspace besitzt über keines dieser Objekte Schreib-Ownership.

## Fachliche Leitplanken

- Actions sind Projektionen, keine neue Wahrheitsschicht.
- Deep Links navigieren zum jeweiligen Owner-Feature; Mutationen erfolgen dort.
- Historische Zustände werden nicht ohne vorhandene Owner-Semantik als „superseded“ interpretiert.
- Bestehende Feature-Grenzen und explizite Benutzerentscheidungen bleiben erhalten.
- Neue Workflow-Regeln benötigen weiterhin eine eigene fachliche Entscheidung und dürfen nicht im Workspace implizit eingeführt werden.
