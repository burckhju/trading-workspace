# Positionsübersicht mit farbigen Statusmarkierungen

## Bedienung

Der Arbeitsbereich zeigt offene Positionen standardmäßig als Tabelle statt großer
Karten. Suche über Produktname, WKN, ISIN, Basiswertname und Symbol; Filter für
fachliche Hinweise, Datenprobleme, Gewinn und Verlust. Es wird **der gesamte geladene
Bestand** gefiltert und sortiert, erst danach in 25/50/100 Zeilen paginiert. Die
Trefferzahl nennt immer auch den Gesamtbestand. Ansicht zurücksetzen entfernt alle
Filter und schließt geöffnete Details. Suche, Sortierung und Seite bleiben im gleichen Browser-Tab beim Rücksprung
erhalten; sie sind keine serverseitige Benutzerpräferenz. Fehlerhafte oder gesperrte
Session-Speicherung blockiert die Nutzung nicht.

Sortierbare Spalten besitzen native Buttons und `aria-sort`. Tabellenkopf und
Produktspalte bleiben im Tabellen-Scrollbereich stehen. Auf schmalen Bildschirmen
werden Basiswert, Kaufdatum und Einstand in die Details verlagert; die Tabelle ist
innerhalb ihres begrenzten Bereichs horizontal scrollbar, nicht das ganze Dokument.
Es gibt keine unzugänglichen ausschließlich per Hover sichtbaren Aktionen.
Die Suchfelder stehen auf schmalen Bildschirmen untereinander. Geöffnete Details
erscheinen in einem eigenen Bereich direkt unter der Tabelle: Ihre Lesbarkeit bleibt
unabhängig vom horizontalen Scrollstand der Tabelle erhalten.

## Farben bedeuten nicht dasselbe

- Rot / `! Kritischer Hinweis`: vorhandener Stop-Hinweis oder verfügbares kritisches
  Positionssignal; kein abgeleitetes Signal aus einem negativen G/V.
- Gelb / `! Fachlicher Hinweis`: bestätigter sonstiger Hinweis oder Gewinnschutz.
- Gelb / `? Daten prüfen`: fehlende, veraltete, indikative oder fehlerhafte Daten.
  Das ist kein Verkaufssignal. Ein Trade kann gleichzeitig Hinweis- und Datenfilter treffen.
- Grün / `✓ Unauffällig`: keine fachlichen Hinweise und vorhandene unauffällige Daten.
  Ein fehlendes/stales Positionssignal wird nicht als NORMAL behandelt.
- Blau: indikativer Referenzkurs. Grau: fehlender oder nicht verfügbarer Produktkurs.
- G/V hat separat +/− und grüne/rote Zahlen. Farbe allein vermittelt niemals den Status.

Quelle, ursprünglicher Kurszeitpunkt, Monitoring, Positionssignal, Stop/Ziel und
Buchungswerte sind unter **Details** erreichbar. Der allgemeine Warntext steht einmal
über der Tabelle; die konkrete Kursqualität bleibt je Zeile sichtbar. Keine Orderfreigabe.

## Beträge und Zeitangaben

Bewertungssummen sind einklappbar und gelten für den gesamten offenen Bestand, nicht
nur Suchtreffer. Nur Werte mit bekannter Bewertungswährung werden je Währung addiert.
Die Abdeckung (z.B. 8/10 bewertet), indikative/veraltete Teilbeträge und ältester
berücksichtigter Kurs bzw. unbekannte Zeitpunkte sind sichtbar. Es gibt keine
Mischwährungssumme und keine implizite Wechselkursumrechnung. Geldsortierungen gruppieren
zuerst nach Währung. Fehlende Werte bleiben in beiden Sortierrichtungen zuletzt.
Summen und Geldsortierung nutzen exakte skalierte Ganzzahlen statt binärer Gleitkommazahlen;
Anzeige von Geldsummen mit zwei Dezimalstellen, gespeicherte Einzelwerte bleiben unverändert.

Das Kaufdatum ist `opened_on`, sonst der lokale Kalendertag von `opened_at`, nicht das
Erfassungsdatum. Es beschreibt den ersten effektiven Kauf. Nachkäufe/Teilverkäufe und
Datumskorrekturen bleiben im Trade-Bereich. Unbekannte Datumsangaben werden nicht erfunden.
Stop/Ziel werden nicht mit einem möglicherweise anderen Instrument oder einer anderen
Währung verrechnet. Prozent-G/V, Stop-Abstände und Sammelverkäufe sind nicht hinzugefügt.

**Verkauf erfassen** navigiert zum Formular des exakten Trades (`#sale-capture`) und
fokussiert es nach Laden. **Kauf-/Verkaufsdaten und Historie öffnen** führt zu
`#execution-dates`. Navigation und Filterung buchen oder stornieren nichts.

## Produktnamen und Architektur

Die Positionsabfrage liest WKN, ISIN und Basiswertnamen im vorhandenen SQL-Join mit;
keine zusätzlichen Requests pro Tabellenzelle. Optionale Positionssignale werden nach
Laden des Bestands mit höchstens sechs gleichzeitigen Requests ergänzt; Fehler bleiben
als nicht verfügbar sichtbar. Abbruch/Neuladen verwirft alte Antworten. Das bestehende
Backend berechnet Health/Bewertungen weiterhin über seine vorhandenen Fachservices;
diese Änderung ersetzt diese nicht durch einen neuen Bulk-Quote-Dienst.

Die TradePlan-Übersicht ergänzt in einer mengenbasierten Abfrage das zuletzt ausdrücklich
gewählte Produkt **der konkreten aktuellen Planversion**. Ein neuer Run ohne Auswahl
oder ein Versionswechsel darf kein Produkt aus einem anderen Kontext unterschieben.
Basiswert und Optionsschein bleiben separate Namen. Produktvergleich, Bestätigungsdialog
und ausgewähltes Produkt zeigen aktuelle Stammdaten plus WKN/ISIN; IDs bleiben erreichbar.
Fehlende Namen werden explizit gemeldet und können erneut geladen werden. Historische
Bewertungen und Buchungen werden nicht umbenannt oder geändert.

## Prüfung und Umfang

Regressionen umfassen 100 synthetische Positionen, globale Suche, Seitenwechsel,
Ansichtserhalt, gemischte Währungen, fehlende Kurse, exakte Dezimalsummen, Farb-/Textstatus,
Tastaturbedienung und mobile Layoutgrenzen. Browser-Layouttests nutzen kontrollierte
API-Fixtures; PostgreSQL-Integration prüft die tatsächliche Namenszuordnung und
Versionsisolation. Bestehende echte Browser-Kauf-/Verkaufs- und Datumsabläufe bleiben
Teil der normalen CI. Kein Test darf gegen eine persönliche Produktivdatenbank laufen.

Keine Schemaänderung: Backend-Migration `20260912_0036` bleibt Voraussetzung.
Deployment über `scripts/start-linux.sh` nach Backup und Fast-Forward-Update; das erhält
vorhandene Frankfurt-Zusatzkonfiguration. Keine lokalen Trades werden durch Installation
geändert. Konfigurierbare Spalten, serverseitig gespeicherte Ansichten, Gruppierung und
CSV-Export bleiben weitere Ausbaustufen.

Referenz für native sortierbare Tabellen: W3C WAI APG,
https://www.w3.org/WAI/ARIA/apg/patterns/table/examples/sortable-table/.
Dies behauptet keine vollständige WCAG-Zertifizierung oder Screenreader-Abnahme.
