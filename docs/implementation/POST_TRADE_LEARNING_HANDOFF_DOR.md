# DoR vor der Änderung — PB-019 Materialisierung / PB-018 Handoff

Status: begrenzter technischer Reparaturschnitt, keine fachliche Abnahme.
Geltende Grundlage: ADR-S11-007 und ADR-POST-FT012-004, bestehender
Materialisierungsservice und PostTradeLearningPage am Remote-Basiscommit.

## Zu implementierender Schnitt

Die UI bestätigt eine konkret angezeigte ExitReviewVersion. FT-012 prüft die
Bindung gegen den von FT-011 gelieferten geeigneten Handoff, bevor es neue
Evidence schreibt. Wiederholung bleibt an denselben Request gebunden. Die
Oberfläche liest nach Review- und Materialisierungsaktionen den Ownerstatus
neu; sie erzeugt keine eigene READY-/CURRENT-Wahrheit.

## Vorab festgelegte Akzeptanz

1. Mit explizit passender Reviewversion entsteht Evidence für genau diese Version.
2. Eine abweichende Version wird vor Schreiboperationen mit 409 abgewiesen.
3. Derselbe Key und dieselbe Version liefern das ursprüngliche Ergebnis zurück,
   auch nach späterer Quellenänderung: historischer Replay, keine neue Freigabe.
4. Derselbe Key mit anderer Version ist ein anderer Request und wird abgewiesen.
5. Neue Keys erzeugen für dieselbe Quellversion keine zweite Evidence.
6. FT-011 bleibt alleiniger Owner der Eignung; NOT_READY/STALE werden nicht umgangen.
7. Legacy-Requests ohne neuen Pin behalten ihren Fingerprint; kein stiller Bruch
   bereits persistierter Idempotenz. Dieser Kompatibilitätsweg ist ausdrücklich
   nicht der neue versionsgebundene UI-Vertrag.
8. Im kombinierten UI gibt es genau eine Übergabeaktion. Nach Review-Finalisierung
   ist die Übergabe ohne Neuladen nutzbar; nach Übergabe wird Lesson-Readback geladen.
9. Navigation, abgebrochene/verspätete Reads und Readback-Fehler dürfen weder
   Quellen anderer Trades anzeigen noch fehlende Daten als leere Lessonliste deuten.
10. Keine Migration, kein Journal-/Lesson-/Modell-Schreiben als Nebenwirkung.

Nicht durch diesen Schnitt geschlossen: vollständiger Journal-Schreibpfad,
atomare Serialisierung gegen gleichzeitige Upstream-Korrektur, vollständige
PostgreSQL-/Browserqualifikation. Unit-Fakes ersetzen diese Nachweise nicht.
