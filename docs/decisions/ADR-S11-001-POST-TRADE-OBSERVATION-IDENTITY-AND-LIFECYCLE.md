# ADR-S11-001 – PostTradeObservation: Identität und Lifecycle

## Status

Accepted for Sprint 11.

## Kontext

FT-010 stellt nach vollständigem wirtschaftlichem Exit die FT-011-Eligibility bereit.

Ein Teilverkauf darf keine PostTradeObservation starten.

FT-010 erzeugt selbst keine Post-Trade-Objekte.

Nachbeobachtung ist eine analytische Lernphase ohne reale Position, reales Risiko,
reale Order oder neue reale Execution.

## Entscheidung

Für FT-011 V1 gilt:

Trade 1 -> 0..1 PostTradeObservation

Eine PostTradeObservation wird ausschließlich durch eine explizite
Benutzeraktion gestartet.

Vor dem Start muss gelten:

effective Position.open_quantity == 0

Der fachliche Lifecycle lautet:

ACTIVE -> COMPLETED

ACTIVE bedeutet:
- Observation wurde gestartet;
- der Horizon ist noch nicht vollständig erreicht.

COMPLETED bedeutet:
- der definierte Observation-Horizon wurde vollständig erreicht.

Der Standard-Horizon beträgt:

20 abgeschlossene, tatsächlich verfügbare
Underlying-EOD-Beobachtungen

Nicht-Handelstage zählen nicht.

Fehlende Marktdaten werden nicht als vorhandene Beobachtungen gezählt.

Datenvollständigkeit bleibt von ACTIVE / COMPLETED fachlich getrennt.

Eine Upstream-Korrektur erzeugt keine zweite PostTradeObservation.

ExitReview bleibt ein separates nachgelagertes FT-011-Objekt.

## Auswirkungen für den Nutzer

Nach vollständigem Verkauf kann die Oberfläche anbieten:

Trade geschlossen
[ Nachbeobachtung starten ]

Bei einem Teilverkauf bleibt diese Aktion gesperrt.

Während der Observation kann der Nutzer beispielsweise sehen:

13 / 20 Beobachtungen

Fehlende Daten bleiben sichtbar.

Ein Trade erhält keine konkurrierenden Nachbeobachtungen.

## Begründung

Der explizite Start erhält die Benutzerkontrolle und respektiert den
bestehenden FT-010-Handoff.

Die One-per-Trade-Regel verhindert konkurrierende Learning-Artefakte.

20 tatsächliche EOD-Beobachtungen entsprechen der vorhandenen
Market-Data-Granularität und ungefähr einem Handelsmonat.

Ein kleiner Business-Lifecycle verhindert, dass technische Datenprobleme mit
fachlichen Zuständen vermischt werden.

## Invarianten

### INV-S11-001
Kein Start bei effektiver open_quantity > 0.

### INV-S11-002
Eligibility erzeugt keine Observation automatisch.

### INV-S11-003
Pro Trade existiert höchstens eine PostTradeObservation.

### INV-S11-004
FT-011 reaktiviert niemals reale Position, Risiko, Order oder Execution.

### INV-S11-005
Der V1-Horizon beträgt 20 abgeschlossene Underlying-EOD-Beobachtungen.

### INV-S11-006
Fehlende Daten zählen nicht als vorhandene Observation.

### INV-S11-007
Datenvollständigkeit und Business-Lifecycle bleiben unterscheidbar.

### INV-S11-008
Eine Upstream-Korrektur erzeugt keine zweite Observation.

### INV-S11-009
PostTradeObservation und ExitReview bleiben getrennte Objekte.
