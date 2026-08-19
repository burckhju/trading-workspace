# ADR-S11-006 – ExitReview: Identität, Lifecycle und Benutzerbewertung

## Status

Accepted for Sprint 11.

## Kontext

FT-011 trennt bewusst:

PostTradeObservation
=
beobachtbare Evidenz nach dem tatsächlichen Exit

von:

ExitReview
=
Benutzerbewertung der tatsächlichen Exit-Entscheidung

Ein späterer Kursanstieg beweist nicht automatisch einen schlechten Exit.

Ein späterer Kursrückgang beweist nicht automatisch einen guten Exit.

Das System liefert Fakten und transparente Ableitungen. Das Urteil bleibt beim
Nutzer.

## Entscheidung

Für FT-011 V1 existiert pro PostTradeObservation höchstens ein aktueller
ExitReview-Kontext.

Der Lifecycle lautet:

DRAFT -> FINALIZED

Die Aktualität wird davon getrennt modelliert:

CURRENT | STALE

Ein ExitReview darf erst finalisiert werden, wenn:

PostTradeObservation == COMPLETED

Die Finalisierung ist ausschließlich eine explizite Benutzeraktion.

FT-011 V1 verwendet vier getrennte Bewertungsdimensionen:

- TIMING
- PROCESS_ADHERENCE
- RISK_DECISION
- OVERALL_EXIT_DECISION

Für jede Dimension gilt dieselbe qualitative Skala:

- GOOD
- ACCEPTABLE
- IMPROVABLE
- NOT_ASSESSABLE

OVERALL_EXIT_DECISION ist eine eigenständige Benutzerbewertung.

Sie wird nicht automatisch aus den drei anderen Dimensionen berechnet.

Bei Finalisierung ist eine nichtleere Begründung erforderlich.

NOT_ASSESSABLE ist ein echter fachlicher Wert und darf verwendet werden, wenn
die vorhandene Evidenz keine belastbare Bewertung zulässt.

Beispiele:

- External Trade ohne historischen Plan;
- relevante Datenlücken;
- fehlender Management-Kontext.

Ein finalisierter Review kann gemäß ADR-S11-005 später STALE werden.

Eine erneute Finalisierung darf die ursprüngliche Bewertung nicht spurlos
überschreiben. Die Review-Historie muss nachvollziehbar bleiben.

## Auswirkungen für den Nutzer

Die Anwendung zwingt den Nutzer nicht zu einem simplen:

guter Exit / schlechter Exit

Stattdessen kann eine Bewertung beispielsweise lauten:

Timing:
IMPROVABLE

Process Adherence:
GOOD

Risk Decision:
GOOD

Overall Exit Decision:
ACCEPTABLE

Damit kann der Nutzer erkennen:

Das Timing hätte besser sein können,
aber mein Prozess und meine Risikoentscheidung
waren trotzdem sinnvoll.

Ein finanziell ungünstig wirkender Ausgang wird dadurch nicht automatisch zu
einer schlechten Entscheidung.

Wenn Daten fehlen, kann der Nutzer NOT_ASSESSABLE wählen, statt ein
unbegründetes Urteil abzugeben.

Die verpflichtende Begründung macht die Bewertung auch Monate später noch
verständlich.

## Begründung

Timing, Prozesstreue und Risikoentscheidung sind fachlich unterschiedliche
Aspekte eines Exits.

Ein einzelner Score würde diese Unterschiede verdecken.

Eine numerische Skala wie 1–10 würde außerdem Genauigkeit suggerieren, obwohl
kein validiertes Bewertungsmodell existiert.

Die qualitative Vierer-Skala ist für V1 verständlich und transparent.

IMPROVABLE wird gegenüber einem pauschalen BAD bevorzugt, weil FT-011 dem
Lernen und konkretem Verbesserungspotenzial dient.

## Invarianten

### INV-S11-039
PostTradeObservation und ExitReview bleiben getrennte fachliche Objekte.

### INV-S11-040
Ein ExitReview wird nicht automatisch erzeugt oder finalisiert.

### INV-S11-041
Finalisierung ist erst nach COMPLETED Observation zulässig.

### INV-S11-042
Finalisierung ist eine explizite Benutzeraktion.

### INV-S11-043
TIMING, PROCESS_ADHERENCE, RISK_DECISION und OVERALL_EXIT_DECISION bleiben
getrennte Bewertungen.

### INV-S11-044
OVERALL_EXIT_DECISION wird nicht automatisch berechnet.

### INV-S11-045
GOOD, ACCEPTABLE, IMPROVABLE und NOT_ASSESSABLE sind die V1-Werte.

### INV-S11-046
Ein finalisierter Review benötigt eine Benutzerbegründung.

### INV-S11-047
System-Evidenz und Benutzerurteil bleiben unterscheidbar.

### INV-S11-048
Ein STALE Review wird nicht still gelöscht oder überschrieben.

### INV-S11-049
FT-011 V1 erzeugt keinen automatischen Exit-Quality-Score.
