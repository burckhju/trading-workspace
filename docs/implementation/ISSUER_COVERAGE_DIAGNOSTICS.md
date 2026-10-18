# Abrufdiagnose für Emittentenkurse

Stand: 13.10.2026. Kleine Korrektur auf Basis von v1.5.4, ohne Änderung
an Abrufen, Freigaben, Kursalter, IV-Modellen oder Stop-/Zielregeln.

## Befund und Korrektur

Der Scheduler führt JPMorgan und Morgan Stanley über `ISSUER_QUOTES`, andere
Quellen über `WARRANT_QUOTES`. Gemischte Produkte besitzen beide Aufträge.
Die Depotdiagnose las bisher ausschließlich `WARRANT_QUOTES`: Dadurch erschien
bei reinen Emittentenprodukten irreführend `NOT_SCHEDULED`; auch die zugehörigen
Abruffehler fehlten.

Die lesende Diagnose berücksichtigt jetzt beide Aufträge ausschließlich für den
angefragten Laufzeit-Workspace. `refresh_jobs` enthält je Auftragsart Status,
bereinigten Grund sowie tatsächliche letzte/nächste Prüfzeit. Laufende Aufträge
erscheinen als `RUNNING`, ausgeschaltete als `DISABLED`. Unterschiedliche Stände
werden als `MIXED` zusammengefasst und einzeln angezeigt; der Prüfbedarfsfilter
behält solche Produkte sowie verzögerte Wiederholungen bei. Bei zwei Aufträgen
bleiben die alten zusammenfassenden Zeit-/Grundfelder leer: Es gibt dafür keinen
einzelnen gemeinsamen Abruf. Bei einem Auftrag bleiben sie wie bisher verwendbar.
Quellenversuche werden über Provider und Notierungs-ID dem Kursweg zugeordnet.
Ein erfolgreicher Abruf ist weiterhin kein Nachweis eines aktuellen Kurszeitpunkts.

## Quellenprüfung und Grenzen

Am 13.10.2026 über die Web-Recherche geprüfte Primärquellen:

- [Produkt DE000MN50FN0](https://zertifikate.morganstanley.com/produktdetails/de000mn50fn0):
  Die abrufbare, etwa drei Wochen alte Fassung enthält Kursangaben vom 21.09.2026,
  keine Live-Messung. Sie bezeichnet die Ausübung als amerikanisch, die
  Produktwährung als EUR und den Basispreis/Basiswertkurs in USD. Somit ist das
  bestehende europäische Gleichwährungsmodell für diesen Schein nicht passend.
- [Startseite](https://zertifikate.morganstanley.com/home/): Preis- und
  Kennzahlenangaben können verzögert sein und sind indikativ.
- [Nutzungsbedingungen](https://zertifikate.morganstanley.com/nutzungsbedingungen/):
  kein technischer Zeitzonenvertrag für `lastquotetimestamp` im geprüften Text.

In diesen geprüften Texten konnte die Zeitzone des Streamfelds nicht eindeutig
belegt werden. Das ist kein Nachweis, dass nirgendwo eine Spezifikation existiert.
Ein plausibler Unterschied von zwei Stunden zur Empfangszeit reicht nicht.
`observed_at` bleibt deshalb unbekannt; keine nachträgliche Umdeutung vorhandener
Journalwerte, keine Ersetzung durch Abrufzeit und keine Freischaltung realer IV.

Für die nächste Datenfreigabe benötigt werden: verbindliche Felddefinition mit
Zeitzone und Sommerzeitregel, Behandlung mehrdeutiger Herbst-Zeitpunkte,
Bedeutung des Zeitpunkts (Quote/Publikation), Verzögerung sowie getrennte
Zeitbasis für Basiswert und Optionsschein. Danach folgen bestätigte
Produktbedingungen, passendes Modell einschließlich Ausübung/Dividenden/FX und
zeitlich passende Basiswert-/FX-Kurse. Anbieter-IV/Greeks benötigen zusätzlich
Kursseite, Zeitpunkt, Modell und Einheiten. Diese Korrektur ändert keine
Zustimmung und erschließt keine neue Datenroute.

## Nachweise

Gezielte Backendtests decken beide Emittenten, laufende und abgeschaltete
Aufträge, Workspace-Isolation, gemischte Ergebnisse, Fehlerzuordnung und
unverändert unbekannte Kurszeiten ab. Frontendtests prüfen getrennte Anzeige
und Prüfbedarfsfilter. Ein zusätzlicher Browserfall mit synthetischer
GET-Antwort prüft die Darstellung bei 390 Pixeln und seitlichen Seitenüberlauf.
Ausführungsergebnisse und Umgebungsgrenzen stehen im zugehörigen PR.
