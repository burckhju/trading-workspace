# Vorschlag: Arbeitsbereich für etwa 100 offene Positionen

Status: **Entwurf zur Entscheidung, keine umgesetzte Tabellenansicht.**
Grundlage: Nutzerfeedback vom 13.09.2026 zur großen zweispaltigen Kartenansicht.
Die konkrete Ergänzung der Produktnamen in der Produktauswahl ist davon getrennt.

## Ziel und Standardansicht

Die Übersicht soll Positionen vergleichen und Handlungsbedarf finden lassen; Details
gehören zur einzelnen Position. Empfehlung: **kompakte Tabelle als Desktop-Standard**,
Kartenansicht optional, Mobilansicht mit wenigen Kernwerten und aufklappbaren Details.
Eine Position entspricht einer Zeile. Produktname und Aktionen bleiben beim Scrollen
sichtbar; Tabellenkopf bleibt fixiert. Schrift nicht einfach verkleinern.

Oben: Anzahl offener Positionen, Trefferzahl des Filters, Anzahl mit fachlichen Hinweisen,
Anzahl mit Datenproblemen. Summen von Marktwert und nicht realisiertem Brutto-G/V nur
je Bewertungswährung; keine unbemerkte EUR/USD/CHF-Summe. Fehlende Bewertungen zählen
nicht als Null. Indikative oder veraltete Bewertungen mit Abdeckung und Zeitstand ausweisen.
Für diese Gesamtsicht sind die angezeigten 15 Positionen kein vollständiger Datensatz.

## Suche, Filter, Sortierung

Suchfeld für Produktname, WKN, ISIN und Basiswert. Schnellfilter für alle offenen
Positionen, fachliche Hinweise, Datenprobleme sowie positive/negative G/V-Werte.
Fachliche Hinweise und Datenqualität getrennt zählen; eine Position kann beides haben.
Keine Rangfolge aus fehlenden Kursen oder einem roten G/V-Wert als Verkaufssignal ableiten.

Sortierbare Spalten: Produktname, Kaufdatum, Bestand, Marktwert, G/V absolut und relativ,
Kurszeitpunkt. Standard: bestätigte fachliche Warnungen zuerst, danach Datenprobleme,
anschließend alphabetisch; genaue Rangordnung vor Umsetzung mit Nutzern festlegen.
Fehlende Werte als fehlend behandeln, nicht als Null; Gleichstände stabil nach Positions-ID.
Filterzustand und Sortierung beim Rücksprung aus Trade Management erhalten.

## Sichtbare Spalten

Standard: Status, Produkt (Name und WKN), Basiswert, Kaufdatum, Stück, Einstand,
Referenzkurs mit Währung/Qualität, Marktwert, nicht realisierter Brutto-G/V und Aktionen.
Die tatsächlich sichtbare Spaltenanzahl muss zur verfügbaren Breite passen. Auf schmaleren
Bildschirmen z.B. Einstand und Referenzkurs in die Details verschieben.
Optional: ISIN, Emittent, realisierter Brutto-G/V, Stop, Ziel, Fälligkeit, Haltedauer,
G/V in Prozent. Nur tatsächlich vorhandene bzw. fachlich definierte Werte anbieten.

Das bestehende Positions-API enthält u.a. Produktname, Menge, Einstand, Kaufdatum,
Bewertung, G/V, Stop/Ziel, Basiswertsymbol, Kursquelle/-zeit und Status. WKN, ISIN,
Emittent und Fälligkeit fehlen dort derzeit und benötigen eine gebündelte Anreicherung;
keine Einzelabfrage pro Tabellenzelle. Prozent-G/V ist erst nach Festlegung der
Bezugsgröße (Restbestand und Kostenbasis bei Teilverkäufen/Nachkäufen) korrekt ausweisbar.
Stop-Abstände nur bei identischem Instrument und passender Währung berechnen;
Basiswert-Stop nicht mit dem Optionsscheinpreis vergleichen.

## Warnungen und Aktionen

Eine kompakte, verständliche Statusanzeige je Zeile (Text und Symbol, nicht nur Farbe).
Gemeinsame Erklärungen zu indikativen Kursen einmal oberhalb der Tabelle zeigen;
positionsbezogene Warnung, Zeitstempel und Quelle bleiben unmittelbar erreichbar.
Ein allgemeiner Hinweis darf eine konkret kritische Position nicht verstecken.

"Details" öffnet eine aufklappbare Zeile oder seitliche Detailansicht mit Historie,
Kauf-/Verkaufsdaten, Nachkäufen, Teilverkäufen, Stop/Ziel, Kursherkunft und Warntexten.
"Trade verwalten" und "Verkauf erfassen" bleiben konkrete Einzelaktionen. Letzteres
soll das Verkaufsformular der richtigen Position ansteuern, aber nie einen Verkauf
bereits durch den Klick buchen. Keine Sammelverkäufe im Umfang dieses Vorschlags.
Bei offenen Positionen ist ein Teilverkaufsdatum nicht das Schließungsdatum.

## Umfang und Abnahme

Erste Ausbaustufe: Tabelle, Suche, fachliche-/Datenfilter, Sortierung, 25/50/100 Zeilen
pro Seite, sichtbare Gesamt-/Trefferzahl und klarer Detailzugang. 25 Zeilen ist ein
Startwert zur Erprobung, keine Behauptung zur Zahl auf einem konkreten Bildschirm.
Für etwa 100 Einträge genügt voraussichtlich die vorhandene Gesamtabfrage mit
clientseitiger Filterung/Sortierung; messen. Paginierung erst nach dem globalen Filtern
und Sortieren. Virtuelles Scrollen erst bei gemessenen Problemen, da es Tastaturbedienung
und Fokusverwaltung komplexer macht.

Zweite Ausbaustufe: konfigurierbare Spalten, gespeicherte Ansichten und Gruppierung nach
Basiswert/Emittent. CSV-Export nur nach gesonderter Freigabe des Umfangs.

Abnahme mit mindestens 100 synthetischen Positionen: Suche auch nach WKN/ISIN; mehrere
Produkte auf demselben Basiswert bleiben unterscheidbar; Rücksprung erhält den Kontext;
fehlende, veraltete und indikative Kurse bleiben erkennbar; keine Mischwährungssummen;
keine zusätzlichen Buchungen durch reine Navigation; Tastatur/Screenreader und schmale
Ansicht bedienbar. Ladezeit, Bedienbarkeit und Anzahl zusätzlicher Requests prüfen.
