# Berichtswährung fest Euro — UI-Nachtrag vom 25.10.2026

## Auftrag und Ausgangsstand

Nach dem bestätigten PC-Update auf v1.5.16 fragte der Nutzer nach einem
`NOT_COMPUTABLE`-Verkaufsbericht und wünschte: „die Eingabe Berichtswährung fix
auf Euro“. Ausgangsbasis ist Main
`7b70f0dfd5cbb81518c73d68d09bbad0c6a9ac2b`, Tree
`53ef549f7710508cbb14365b36a03a26d2843562`, Schema `20261017_0047`.
Eigener Branch: `fix/performance-report-eur`.

Der private Screenshot und reale Buchungsdaten werden nicht ins Repository
übernommen. Es gab keinen Datenbank-, Provider- oder schreibenden Zugriff auf
den Nutzer-PC. Die parallel offene FT-006-Arbeit in #278 bleibt getrennt.

## Diagnose und vorhandener Bedienweg

`performance.domain.report._summary()` liefert `NOT_COMPUTABLE`, wenn relevante
oder ungeklärte Verkäufe vorhanden sind, aber kein verwendbarer Beitrag vorliegt.
`total` und `subtotal` sind dann `null`, kein berechneter Nullbetrag.
Die sichtbare Meldung `CURRENCY_UNKNOWN` bedeutet: Für den konkreten Verkauf
oder mindestens einen vorherigen wirksamen Kauf seiner Kostenbasis fehlt eine
auflösbare Ausführungswährung. Die Meldung einer Zeile belegt nicht die Gründe
aller anderen Zeilen.

Der bestehende Weg bleibt maßgeblich:

1. Im Verkaufsbericht **Quellen und Berechnung** öffnen.
2. **Buchungen und Währungsbestätigungen im Trade prüfen** führt zum bestehenden
   Abschnitt **Kauf- und Verkaufsdaten**.
3. Die tatsächlich fehlende Kaufquelle über **Währung prüfen / bestätigen**
   anhand der Abrechnung prüfen und bewusst bestätigen.
4. Den Bericht erneut lesen. Vollständig bekannte gleichartige Kaufquellen
   können nachfolgende Buchungen über den vorhandenen Ownerresolver qualifizieren.

Eine spätere bekannte Kaufwährung heilt keinen früheren unbekannten Kauf.
Eine Berichtswährung bestätigt keine Buchung; es gibt keine Umrechnung oder
automatische Nachbelegung alter Ausführungen. Siehe
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md).

## Enger Umsetzungsschnitt

| Consumer | Änderung | Erhaltene Grenze |
|---|---|---|
| `/performance/realized-gross` | Sichtbar festes, schreibgeschütztes EUR; jeder ausdrücklich ausgelöste Read sendet `report_currency=EUR`. | Zeitraum/Zone, unbekannt/Null, Quellen und Schutz vor verspäteten Antworten bleiben erhalten. |
| `/performance/closed-trades` | Dieselbe feste EUR-Vorgabe. | Ein bestehender Nicht-EUR-URL-Kontext wird sichtbar ohne automatischen Ersatzread abgewiesen. Erst ein bewusster neuer Submit erzeugt EUR mit neuer Seite, Zeilenauswahl und ohne alten Basisfingerprint. |
| Allgemeiner Quellen-/Rückkehrkontext und Backend | Unverändert. | Andere belegte Währungen bleiben im allgemeinen API-Vertrag und vorhandenen genauen Quellenkontext zulässig; keine stille Umdeutung zu EUR. |

Keine neue Definition, Kennzahl, Datenmigration, Ownerbestätigung oder globale
Formular-/Routingabstraktion. Die Frontendanzeige rechnet weiterhin keine Beträge.
Die beiden Definitionen `realized-gross-sell-v2` und `closed-trade-gross-v1`
bleiben unverändert.

## Qualifikation und Nachweisgrenzen

Die bestehenden Componentfälle werden an die feste Eingabe angepasst. Der Fall
für späte Fehler verwendet weiterhin einen editierbaren Filter (die Zeitzone).
Eine gezielte neue Regression prüft einen fremden Währungskontext: zunächst kein
Read und unveränderte URL; danach genau ein bewusster EUR-Read mit frischem
Kontext. Bestehende Antwort-/Definitionsprüfungen und Quellenrückkehr bleiben
Teil der Suite.

Die beiden bestehenden nativen Finanzfälle behalten Titel, Fallidentität,
synthetische Owneraktionen, Guards und vollständige Report-/Cleanup-Prüfungen.
Ihre bisherige Währungseingabe wird durch Assertions auf EUR und
Nichteditierbarkeit ersetzt. Der normale Smoke, beide Lernfälle und der
Governancefall bleiben ebenfalls unverändert vorgesehen. Keine Workflow-,
Retry-, Timeout-, Coverage- oder Berechtigungserweiterung.

Ausgeführte Prüfungen, exakter finaler Head/Tree, tatsächlicher CI-Checkout,
Versuch, Rohreports, Artefakthashes, Desktop-/Mobilprüfung und Cleanup werden im
zugehörigen PR-Handoff gebunden. Die Beschreibung eines Tests ist kein
Ausführungsnachweis. Bestehende historische Qualifikationszahlen werden nicht
rückwirkend geändert. Die unten erfassten lokalen Ergebnisse, CI- und spätere
Auslieferungsnachweise bleiben getrennt.

Die EUR-Vorgabe allein repariert keine reale Quellenlücke. Eine vollständige
Währungsabdeckung des Nutzerbestands, wirtschaftliche Wirksamkeit, neue
Fachabnahme, Veröffentlichung oder PC-Installation dieser Folgeänderung wird
hier nicht behauptet.

### Tatsächlich ausgeführte lokale Prüfungen — 25.10.2026

| Prüfung | Ergebnis |
|---|---|
| Beide Reportseiten, Quellenrückkehr und Kontextparser | 4 Dateien, 62 Tests bestanden; Exit 0. |
| Unverändertes `bash scripts/check-frontend.sh` | TypeScript, ESLint, Prettier, 124 Dateien / 806 Tests und Produktionsbuild bestanden; Exit 0. |
| Coverage im vollständigen Frontendgate | Statements/Lines 93,86 %, Branches 86,26 %, Functions 86,59 %; bestehende Schwellen unverändert. |
| Dokumentpfade / Diff | 179 relative Verweisziele in den geänderten Dokumenten vorhanden; `git diff --check` sauber. |

Werkzeuge: Node 22.16.0, npm 10.9.2, unveränderte Lockdatei und eigene kopierte
Abhängigkeiten im neuen Worktree. Der vorhandene Buildhinweis zu großen Chunks
bleibt sichtbar.

Zwei vorherige lokale Sandboxläufe meldeten einzelne bestandene Dateien, konnten
aber ohne normale Prozesssicht nicht abschließen (`/proc` nicht verfügbar,
`os.cpus()` leer). Beide eigenen Prozesse wurden mit Exit 130 beendet; sie gelten
nicht als Erfolg. Die unveränderten Befehle bestanden danach in der freigegebenen
normalen Prozessumgebung. Keine Test-, Timeout-, Retry- oder Worker-Einstellung
wurde dafür verändert.

Docker ist lokal nicht verfügbar; die vollständigen Backend-/PostgreSQL- und
nativen Browsergates werden über die bestehenden regulären PR-Jobs qualifiziert.
Deren genaue aktuelle Run-/Checkout-/Artefaktbindung steht im PR, nicht in den
historischen lokalen Ergebnissen dieser Tabelle.
