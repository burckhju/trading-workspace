# Statusmeldungen im Arbeitsbereich

Stand der Auswertung: `main` bei `3b344855d56e8add972d2459d5a15c32c8e9c230`
(14.09.2026). Dies ist der Katalog möglicher Anzeigen, kein Befund über ein
persönliches Depot oder einen tatsächlich aktualisierten Nutzerrechner.

Integration geprüft gegen `e001d7c68dad7e50fa3e42e4e2a50500edc69b9d`
(inklusive #218). Die dauerhafte Aufbewahrung letzter Kurse und die auditierte
ISIN/WKN-Korrektur bleiben erhalten. Der Namensfix benötigt keine eigene
Migration; die aktuelle Basis enthält bereits `20260914_0038`.

## Vier verschiedene Aussagen

Aufgabenpriorität, fachlicher Positionshinweis, Kursqualität und technischer
Abrufzustand sind getrennt. Ein erfolgreicher Abruf garantiert keinen aktuellen
oder ausführbaren Kurs. Ein Datenproblem ist kein Verkaufssignal. „Handlungsbereit“
bedeutet, dass der angegebene nächste Arbeitsschritt offen ist, nicht dass eine
Brokerorder freigegeben wurde. „Öffnen“ navigiert nur zum zuständigen Bereich.

## Aufgabenbereiche und Kartenstatus

| Anzeige | Bedeutung |
| --- | --- |
| Jetzt handeln | `ACTION`: ein nächster Arbeitsschritt ist möglich oder erforderlich; Positionsalerts werden vor Datenproblemen und weiteren Aufgaben einsortiert. Keine automatische Handelsanweisung. |
| Prüfen | `REVIEW`: Planfreigabe oder Nachbereitung eines geschlossenen Trades steht aus. Die bisherige Abschnittsbeschreibung erwähnt nur geschlossene Trades, die Projektion enthält aber auch Planfreigaben. |
| Blockiert | `BLOCKED`: eine Voraussetzung des Kandidaten-Workflows fehlt; die Karte nennt den bekannten nächsten Schritt. |
| Handlungsbereit | `ACTIONABLE`: der zugehörige Arbeitsschritt kann aufgerufen werden. Dies kann auch „Daten prüfen“ oder „Exit Review öffnen“ sein. |

Die Karten sind nicht eigenständig quittierbar. Sie verschwinden, wenn der
zugrunde liegende Fachzustand keine solche Aufgabe mehr begründet. „Aktuell keine
offenen Aufgaben“ ist ein leeres Projektionsergebnis, kein allgemeiner Depot- oder
Systemgesundheitsnachweis.

## Status einer offenen Position

| Anzeige | Auslöser in der aktuellen Oberfläche |
| --- | --- |
| ! Kritischer Hinweis | Offener `STOP_REACHED`-Alert oder verfügbares Positionssignal mit `CRITICAL`. |
| ! Fachlicher Hinweis | Anderer offener Alert, insbesondere Ziel erreicht, oder verfügbares `ATTENTION`-Signal (Gewinnschutz). |
| ? Daten prüfen | Kein vorrangiger fachlicher Hinweis, aber fehlende, veraltete, indikative oder fehlerhafte Daten; auch unvollständige Bewertung, Währung oder Positionssignal. |
| ✓ Unauffällig | Weder fachlicher Hinweis noch eines der geprüften Datenprobleme. Keine Halte-/Kaufempfehlung. |

Rot/Gelb/Grün ersetzen den Text nicht. Die Farbe des G/V ist davon unabhängig.
Eine Position kann zugleich einen fachlichen Hinweis und ein Datenproblem haben;
der zusammengefasste Positionsstatus zeigt den vorrangigen Hinweis.

## Produktkurs und Monitoring

| Produktkurs-Anzeige | Interner Status | Bedeutung |
| --- | --- | --- |
| Aktuell | `AVAILABLE` | Bewertung nach dem vorhandenen Produktkursvertrag verfügbar. Keine Orderfreigabe allein durch diese Anzeige. |
| Letzter verfügbarer Kurs | `LAST_AVAILABLE` | Älterer zulässiger Kurs bleibt als Referenz sichtbar; Originalzeit und Warnungen beachten. |
| Indikativer Referenzkurs | `INDICATIVE` | Verfügbarer Referenzpreis, beispielsweise Last/Close; kein als Bid/Ask umetikettierter Ausführungskurs. |
| Veraltet | `STALE` | Die Aktualitätsanforderung ist nicht erfüllt. Eine ausdrücklich zulässige indikative Analyse kann trotzdem verfügbar sein. |
| Fehlt | `MISSING` | Kein verwendbarer Produktkurs für diesen Bewertungspfad. Fehlende Beträge sind nicht null. |
| Nicht verfügbar | `UNAVAILABLE` | Bewertung im vorhandenen Produkt-/Listing-/Quellenkontext nicht verfügbar. |
| Prüfen | `ERROR` bzw. unbekannter Status | Technischer oder ungeklärter Zustand; Details prüfen. |

Unter **Details** zeigt **Monitoring** aktuell `OK` als „Aktuell“, `MISSING` als
„Fehlt“, `STALE` als „Veraltet“ und `ERROR` als „Prüfen“. Dieser Health-Lesepfad
beurteilt die abgeschlossenen Basiswert-Tagesdaten und deren Zuordnung. Er ist
kein Nachweis, dass der automatische Dienst aktiviert ist oder jede bestätigte
Optionsscheinregel prüfbar ist. Die tatsächliche Stop-/Zielprüfung verwendet die
bestätigte Instrument-/Währungsbindung der jeweiligen Regel.

Bekannte Bestandsgrenze: Manche Datenhealth-Kartentexte sprechen pauschal von
Stop-/Target-Überwachung, obwohl der Health-Pfad Basiswertdaten liest. Ein Problem
in diesem Pfad beweist nicht, dass auch eine korrekt gebundene Produktkursregel
keinen Alert erzeugen kann. Der Namensfix verändert diese Health- oder Regel-
Semantik nicht. Siehe auch `docs/monitoring-price-basis.md`.

## Positionssignal in den Details

Mögliche vollständige Anzeigen sind:

- `Positionssignal: dynamischer Stop erreicht`: verfügbares kritisches Signal aus der bestehenden dynamischen Stop-Projektion; nicht automatisch ein bestätigter Brokerstop.
- `Positionssignal: Gewinnschutz aktiv`: verfügbare Projektion mit `ATTENTION`.
- `Positionssignal: keine besondere Aufmerksamkeit nötig`: verfügbare, nicht kritische und nicht aufmerksamkeitspflichtige Projektion; separate offene Alerts bleiben möglich.
- `Positionssignal: Daten veraltet` (`STALE`).
- `Positionssignal: Daten fehlen` (`MISSING`).
- `Positionssignal: noch nicht ausreichend Daten` (`INSUFFICIENT`).
- `Positionssignal: Prüfung erforderlich` (`ERROR` bzw. unbekannte Qualität).
- `Positionssignal: nicht verfügbar`: noch keine geladene oder nutzbare Signalantwort.

## Mögliche Titel der Einzelmeldungen

Die aktuelle Projektion kann die folgenden **24 festen Kartentitel** erzeugen.
Details und Diagnosegründe kommen zusätzlich aus den jeweiligen Fachzuständen.

| Titel | Bedeutung / nächster Schritt |
| --- | --- |
| Stop erreicht / Target erreicht | Bestehender offener Stop-/Zielalert; exakten Trade und Kursbezug prüfen. |
| Benachrichtigung fehlgeschlagen | Terminaler Zustellfehler, nicht bloß ein noch ausstehender Versand; fachlicher Alert und Versandstatus sind getrennt. |
| Offene Position verwalten | Reguläre Managementaufgabe für einen offenen Bestand; kein neu festgestelltes Verkaufssignal. |
| Monitoring-Daten veraltet / Monitoring-Daten fehlen / Monitoring-Daten prüfen | Basiswert-Health veraltet, ohne Tagesdaten oder ungeklärt/fehlerhaft. |
| Produktkurs veraltet / Produktkurs fehlt | Produktbewertung meldet ein Aktualitäts- oder Datenproblem, ohne vorrangige speziellere Anzeige. |
| Produktbewertung nicht verfügbar / Produktbewertung prüfen | Produktbewertung im vorhandenen Kontext nicht verfügbar bzw. ungeklärt/fehlerhaft. |
| Produkt nicht im Stuttgart-Feed enthalten | Der Quellversuch meldete das konkrete Listing im Feed als fehlend; kein Beweis, dass es nirgendwo Kurse gibt. |
| Indikative Produktbewertung | Analyse ist mit einem Referenzpreis zulässig; Quelle/Alter/Warnung beachten. |
| Positionsdaten prüfen | Basiswert-Health und Produktbewertung melden gleichzeitig Probleme; Details nennen beide getrennt. |
| Kandidat bewerten / Kandidat vorbereiten | Kandidat ist bewertbar bzw. eine vom Kandidaten-Service bestimmte Voraussetzung fehlt. |
| TradePlan freigeben | Neueste Planversion steht zur expliziten Prüfung/Freigabe; Freigabe ist kein Kauf. |
| Produktauswahl starten | Freigegebene aktuelle Planversion ohne Auswahl-Run. |
| Produkt auswählen | Auswahl-Run besitzt geeignete oder ausdrücklich nicht vollständig bewertbare Produkte, aber noch keine dokumentierte Auswahl. |
| Kauf erfassen | Maßgebliche dokumentierte Produktauswahl ohne zugehörigen nicht stornierten Trade; nur tatsächlichen Kauf erfassen. |
| Nachbeobachtung starten | Geschlossener Trade hat noch keine Nachbeobachtung. |
| Exit Review erstellen / Exit Review abschließen / Exit Review aktualisieren | Abgeschlossene Nachbeobachtung ohne Review, mit offenem aktuellem Entwurf oder ohne aktuelles finalisiertes Review. |

Eine laufende Nachbeobachtung und ein aktuelles finalisiertes Review erzeugen
keine solche Nachbereitungsaufgabe. Die feste Anzahl beschreibt nur die Titel,
nicht alle variablen Fehler-/Reason-Texte.

## Automatischer Kursabruf

Global: „Automatischer Kursabruf ist ausgeschaltet“, „Kursabruf läuft“,
„Automatischer Kursabruf ist aktiv“ oder „Kursabruf wartet auf den Hintergrunddienst“.
Pro Verarbeitungsspur zusätzlich „Abruf läuft“ / „Wartet auf nächste Prüfung“.

| Anzeige pro Aufgabe | Bedeutung |
| --- | --- |
| Erster Abruf steht aus | `PENDING`: erste Prüfung noch offen; nicht gleichbedeutend mit fehlendem Kurs. |
| Abruflimit erreicht · Wiederholung eingeplant | `DEFERRED`: Abruf wurde aufgeschoben; vorhandene Wiederholungsplanung bleibt zuständig. |
| Erfolgreich | `AVAILABLE`: dieser Job hat erfolgreich geantwortet; nicht automatisch frischer oder ausführbarer Produktkurs. |
| Keine Kursdaten | `MISSING`: diese Prüfung lieferte keine verwendbaren Daten. |
| Zuordnung oder Zugang fehlt | `BLOCKED`: benötigte Zuordnung oder Zugangsvoraussetzung fehlt. |
| Abruf prüfen | Sonstiger/fehlerhafter Jobstatus; „Diagnose“ nennt den technischen Grund. |
| Abruf läuft | Die Aufgabe wird gerade verarbeitet; überlagert die Anzeige des letzten Ergebnisses. |

„Ohne Erstprüfung“, „fällig“, „überfällig“ und „längster Rückstand“ sind
Warteschlangenangaben, keine Handelswarnungen. „Nächste Prüfung frühestens“ ist
keine Garantie, dass bis dahin ein neuer Kurs verfügbar ist. Fehleranzeigen:
„Abrufstatus konnte nicht geladen werden“ und „Letzte Prüfung fehlgeschlagen: …“.
Jobzeilen zeigen bereits Namen und ISIN des jeweils abgefragten Instruments;
eine Basiswertaufgabe wird nicht als einzelner Optionsschein ausgegeben.

## Namenszuordnung der Einzelkarten – WORKSPACE-NAME-001

Die Ergänzung transportiert `product_id`, `product_name`, `product_isin` und
`product_wkn` additiv in der bestehenden Action-API. Alert/Zustellfehler/Management/
Nachbereitung verwenden den exakten `Trade.product_id`; „Kauf erfassen“ verwendet
die Evaluation der ausdrücklich dokumentierten Auswahl **im selben Run**. Keine
Zuordnung über Namen, Basiswert, Ziel-URL oder nur aktuell sichtbare Positionen.

`WarrantService.read_identities` ist ein öffentlicher mengenbasierter Lesevertrag;
der SQL-Adapter bleibt im Produktfeature. Nicht-leere Produktmengen erzeugen
**eine** zusätzliche SQL-Abfrage pro Action-Antwort, nicht eine pro Karte. Ohne
Produktbezug entfällt sie. Kein zusätzlicher Provider- oder Browserrequest.
Die produktübergreifende Workspace-Grenze wird im Namensreader geprüft. Fehlende
oder fremde Stammdaten lassen die Aufgabe sichtbar, mit „Name nicht verfügbar“
und `—` für fehlende Kennungen. Noch nicht ausgewählten Kandidaten/Plänen/Runs
wird kein Optionsschein untergeschoben. Historische/geschlossene Produkte bleiben
lesbar; aktuelle Stammdatennamen verändern keine historischen Benachrichtigungstexte.

Regressionen: exakte Referenzen aller produktbezogenen Actions, 100 Actions in
einem Namensbatch, fehlende Kennungen, Sonderzeichen, Name nach Health-Umsortierung,
PostgreSQL-Isolation/geschlossene und stornierte Trades, Auswahlherkunft sowie
schmale Browserdarstellung und unveränderte Navigation. Browser-Layoutfixtures
sind synthetisch; die SQL-Zuordnung wird separat gegen Wegwerf-PostgreSQL geprüft.

Keine neue Migration, Konfiguration, Provideraktivierung, Meldungsquittierung oder
Handelsregel. Lokal nach freigegebenem Deployment ausschließlich lesend im
Arbeitsbereich die Karte mit den Produktstammdaten vergleichen; „Öffnen“ muss zum
passenden Trade/Run führen. Keine Testorders, echten Testmeldungen oder schreibenden
Monitoring-One-shots nötig. Vorherige Telegram-Erweiterung (#217) bleibt erhalten.
