# Markt-, Sektor- und Aktiendiagramme

Datum: 2026-10-04. Status: Implementierung; keine fachliche Liveabnahme.
Auftrag: integrierte, rein lesende Diagramme und nachvollziehbare Vergleiche.
Ausgangsbasis: `16e2feec398658c82fa8773fa29feaa1c8fbbba8` (`main`, `v1.4.5`).

## Bestand und Abgrenzung

FT-006 besitzt EOD-Trend/Momentum, SMA, Volatilität und immutable Runs. D01-A–G
erweitern Referenzen auf eigene MarketDataInstrument-Identitäten. Das ältere
ADR-S5-007/008-Listing-Erfordernis gilt für direkte Indexreferenzen nicht mehr.
FT-001 unterstützt tatsächlich nur STOCK; ETF wird für echte Wertpapiere additiv
ergänzt. Indizes erhalten weiterhin weder Underlying noch Listing.

Der EODHD-Katalog enthält einen Hinweis auf GSPC.INDX; ein Hinweis beweist weder
ein aktives Mapping noch vorhandene Historie. Sektoren und Zuordnungen sind
administrierte, zeitlich gültige Daten; es gibt keine vollständige Taxonomie im
Repository und keinen Zugriff auf die produktive Datenbank in diesem Auftrag.
Aktuelle UI: Analyseübersicht/-details, Basiswertdetails, Kandidaten und
Top-down-Aktionsformulare; keine Diagrammbibliothek oder Chart-API.

Offene PRs bei Beginn: #235/#225 Scheduler, #220 Quellenrecherche, #207/#187
Regeln, #205 Optionsschein-Historienkonzept, #204 Basiswertnavigation, #197
historische Forschung, #90 Lernnavigation. Keine dieser Arbeiten wird ersetzt.
Neue Diagramme historisieren keine Optionsscheine und verändern keine Risikoregel.

## Datenpfad und Contract

Market Data besitzt einen begrenzten, providerneutralen Reader für persistierte
EOD-Zeilen. Market besitzt den lesenden Identitäts-/Sektorkontext; Analysis besitzt
Ausrichtung und Decimal-Normalisierung `TIME_SERIES_COMPARISON/1.0.0`.
Die API liefert Eigentümer, MDI, Listing/ISIN/MIC soweit vorhanden, Preisfeld,
Währung, Renditebasis, Herkunft je Beobachtung, Handelstag als Datum,
source_updated_at und retrieved_at mit unveränderter Bedeutung sowie Qualität.
Ein Handelstag wird nicht zu einem UTC-Kurszeitpunkt umgedeutet.

Ein GET importiert nichts, erzeugt keine Identität/Analyse und ändert keine
Zuordnung. Explizite Einrichtung, Mappingvalidierung und begrenzter Import nutzen
die vorhandene Administration. Index-Renditebasis muss belegt sein; unbekannte
Basis blockiert den Vergleich. ETF-Proxies tragen ihre echte Wertpapieridentität.
Ein Abruffehler schaltet keine Quelle um.

Vergleich: maximal 4 Serien, maximal 10.000 EOD-Beobachtungen je Serie, keine
stille Reduktion. ALL bezeichnet vorhandene Historie innerhalb der offengelegten
Antwortgrenze. Gemeinsamer Start ist der erste gemeinsame, gültige, positive
Beobachtungstag im gewählten Intervall. Fehlende Serien verhindern einen
scheinbar vollständigen Vergleich. Kein Forward-Fill, keine Interpolation,
keine FX-Umrechnung. CLOSE bleibt unbereinigt; ADJUSTED_CLOSE fällt niemals auf
CLOSE zurück. Unpassende Renditegrundlagen werden erklärt statt vermischt.

## UI und Einrichtung

Einstieg über Marktanalyse → Diagramme, außerdem URLs aus Basiswert-/Kandidaten-
und Positionskontext. Markt, gesamte administrierte Sektormatrix und ausgewählte
Aktie verwenden dieselbe Komponente. Sektormatrix enthält auch inaktive, fehlende
und mehrdeutige Zuordnungen mit konkretem Einrichtungspfad. Quellenbelegte
ETF-Vorschläge sind Administrationshilfe, keine zweite Stammdatenliste und keine
Kaufempfehlung; Änderungen benötigen eine sichtbare Bestätigung.

Zeiträume: 1/3/6 Monate, 1/3 Jahre und vorhandene Gesamthistorie. Absolute
Einzelserie, Basis 100 und Prozentveränderung; Legende, Datum/Quelle im Hover,
Tastaturbedienung, responsive Anzeige und zugängliche Datentabelle.
Keine Candlesticks oder geglättete Linien über unbelegte Intervalle.

## Akzeptanz und Prüfung

- Index ohne Listing, mehrere ETF-Sektoren und Aktien durch echte HTTP-Contracts.
- Vollständige dynamische Sektorabdeckung; fehlende Daten bleiben sichtbar.
- Gemeinsamer Start, Null/negative Werte, Splits, fehlendes Adjusted Close,
  unterschiedliche Basis/Währung, Lücken, Grenztage und Zukunftsausschluss getestet.
- GETs ohne Provideraufrufe oder fachliche Writes; begrenzte Datenmenge.
- Wechsel der Darstellung ohne neue fachliche Berechnung/Importmutation;
  Fehler, Tastatur, mobile Darstellung und Tabellenalternative geprüft.
- `scripts/check-backend.sh`, `scripts/check-frontend.sh`, `scripts/run-e2e.sh`,
  erforderliche CI am finalen Commit, Diff-Review und Dokumentationsabgleich.

## Übergabestand

Pflichtdokumente und D01-Korrekturen geprüft; sauberer eigener Branch angelegt.
GitHub-Basis verifiziert. Providerzugangsrechte und tatsächliche Historie auf
JMBbot sind noch nicht belegt. Kein Deployment erfolgt. Umsetzung und Prüfungen
werden hier mit konkreten Nachweisen fortgeschrieben.
