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

## Implementierter Arbeitsstand und wiederverwendbare API

`GET /api/v1/market-charts/series?target=reference:<uuid>&target=listing:<uuid>&start_date=2026-07-01&end_date=2026-10-01&price_field=CLOSE`
liest 1–4 verschiedene Eigentümer, höchstens 10.000 Punkte je Serie. `start_date`
ist optional (ab 1900); Zukunft und umgekehrte Intervalle sind Fehler. Die Abfrage
liest höchstens 10.001 Zeilen je Serie zur Grenzerkennung. Sie liefert keine
reduzierte Teilserie bei Überschreitung. Decimal-Werte sind JSON-Zeichenketten.

`GET /api/v1/market-charts/catalog?as_of=<date>` liefert alle administrierten
Sektoren, gültige Referenz-/ETF-Zuordnungen, direkte Marktserien, separat wählbare
ETF-Proxies und gruppierte Historienabdeckung ohne Vollserienabruf.
`GET /api/v1/market-charts/underlyings/<uuid>?as_of=<date>` löst Primärlisting,
Marktbenchmark und Sektor im Backend auf. Eine visuelle Auswahl schreibt nichts.
`market_data.service.time_series.TimeSeriesReader` ist der neutrale Read-Port;
`analysis.domain.time_series` besitzt Vergleich und Ausrichtung. `TimeSeriesChart`
zeigt ausschließlich Backendwerte und wandelt sie nur für SVG-Koordinaten in
JavaScript-Zahlen um. Sie erzeugt keine FT-006-Runs.

Der Start ist der **erste gemeinsam beobachtete Tag**. Ist dessen gewählter
Preiswert fehlend, nicht positiv oder unbrauchbar, bleibt der Vergleich gesperrt;
er sucht keinen späteren Ersatzstart. Das Ende ist der letzte gemeinsam
beobachtete Tag. Fehlende Tage bleiben Lücken. Ohne verifizierten Börsenkalender
unterbricht die Anzeige auch an unbeobachteten Wochentagen, die Feiertage sein
könnten; Wochenenden allein unterbrechen nicht. Die x-Achse benutzt gleichmäßig
skalierte Kalendertage, keinen erfundenen Quote-Zeitpunkt. Zeitfelder bleiben
`trading_date`, `received_at` (= gespeichertes `retrieved_at`), optionales
`source_updated_at`; `observed_at` ist unbekannt. Historische Sichten sind heutige
persistierte/gegebenenfalls nachbereinigte Werte, keine damaligen Wissensstände.

CLOSE von Aktie/ETF ist rohe Kursveränderung (Splits/Dividenden **nicht**
bereinigt). EODHD ADJUSTED_CLOSE enthält Split-/Dividendenbereinigung. Direkter
Preisindex, Total-Return-Index und unbekannte Indexgrundlage bleiben getrennt.
Bei fremder Providerherkunft wird keine Bereinigungssemantik angenommen.
Verschiedene lokale Währungen werden ausdrücklich ohne FX verglichen; wechselnde
Währung innerhalb einer Serie ist ein Datenfehler. Vorhandene Preise können auch
bei deaktiviertem Mapping angezeigt werden, mit sichtbarem Hinweis.

## Einrichtung und vollständige Sektorbelege

Navigation `Diagramme` → `Sektoren und Referenzen einrichten`. Die Seite zeigt
alle elf GICS-Sektorvorschläge, deren offizielle Select-Sector-Benchmarks, ISIN,
NYSE Arca (`ARCX`), USD und Emittentenbeleg. Der einzige Vorschlagsbestand liegt
in `market/service/sector_proposals.py`; er wird nur über die Administration
angeboten und niemals zur fachlichen Chartauflösung benutzt. Die vorhandene
Systematik wird nicht ersetzt; Namen allein lösen keine automatische Zuordnung aus.

Die Kennungen und Benchmarknamen wurden am 04.10.2026 anhand der jeweiligen
State-Street-Fondsseiten geprüft; MIC anhand des ISO-Verzeichnisses. Dies beweist
**keine** EODHD-Zugangsrechte oder tatsächlich gespeicherte Historie.

| GICS | Sektor | ETF | ISIN | Offizielle Benchmark |
| --- | --- | --- | --- | --- |
| 10 | Energy | XLE | US81369Y5069 | Energy Select Sector Index |
| 15 | Materials | XLB | US81369Y1001 | Materials Select Sector Index |
| 20 | Industrials | XLI | US81369Y7040 | Industrial Select Sector Index |
| 25 | Consumer Discretionary | XLY | US81369Y4070 | Consumer Discretionary Select Sector Index |
| 30 | Consumer Staples | XLP | US81369Y3080 | Consumer Staples Select Sector Index |
| 35 | Health Care | XLV | US81369Y2090 | Health Care Select Sector Index |
| 40 | Financials | XLF | US81369Y6059 | Financial Select Sector Index |
| 45 | Information Technology | XLK | US81369Y8030 | Technology Select Sector Index |
| 50 | Communication Services | XLC | US81369Y8527 | Communication Services Select Sector Index |
| 55 | Utilities | XLU | US81369Y8865 | Utilities Select Sector Index |
| 60 | Real Estate | XLRE | US81369Y8600 | Real Estate Select Sector Index |

Quellen: [GICS](https://www.spglobal.com/spdji/en/landing/topic/gics/),
[MIC](https://www.iso20022.org/market-identifier-codes), jeweils verlinkte
State-Street-Fondsseiten im Vorschlagsvertrag, [EODHD EOD-Semantik](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes).
Keine Kaufempfehlung, Lizenzbestellung oder Übernahme lizenzierter Unternehmensklassifikationen.

Pro Sektor: bestehenden Sektor auswählen oder begründet anlegen; Benchmark
anlegen/auswählen; ETF über reale Stammdaten/Notierung anlegen oder vorhandenes
Listing auswählen; Sektor→Benchmark und Benchmark→ETF mit gültigem Datum und
Beleg bestätigen. Mapping separat speichern, prüfen/aktivieren und Historie
kontrolliert importieren. Schritte sind einzelne bestehende Transaktionen;
Fehler rollen bereits erfolgreich bestätigte andere Schritte nicht zurück.
Überlappende Zuordnungen werden nicht ersetzt. Datenimporte sind maximal zehn
Jahre pro Anfrage; der Status zeigt laufenden Schritt, Fehler oder Importzahlen.
Indexreferenzen benötigen kein ETF-Listing. Ihre Provideridentität wird direkt
administriert und die belegte Preis-/Total-Return-Grundlage separat bestätigt.

Migration `20261004_0043` folgt `20260928_0042`: append-only
`reference_series_definitions` mit Quelle, Akteur und exakter Mappingrevision;
PostgreSQL prüft Workspace/Eigentümer/Revision und verhindert Update/Delete.
Mappingänderungen machen frühere Semantik für die neue Revision ungültig.
Downgrade verweigert vorhandene Evidenz oder ETF-Stammdaten; kein stiller
Datenverlust und kein Start alter Software auf neuen ETF-Daten. ETF ergänzt das
bestehende VARCHAR-Enum, Index bleibt ein eigener MarketDataInstrument-Eigentümer.
Keine neue Trading-Produktart, keine automatische ETF-Discovery, keine Handelsfreigabe.

## Bibliothek und Prüfumgebung

Recharts 3.10.1, MIT, unterstützt vorhandenes React 19.1; `react-is` ist passend
auf 19.1.0 gepinnt. Diagramm- und Einrichtungsrouten laden separat. Recharts-
Accessibility-Layer, Keyboard-Tooltip, unterscheidbare Strichmuster und eine
paginiert zugängliche Datentabelle ergänzen sich. Quellen:
[Repository/Lizenz](https://github.com/recharts/recharts),
[Installation](https://recharts.github.io/en-US/guide/installation/).
`npm audit --omit=dev` vom 04.10.2026 meldet keine neue Chart-Abhängigkeit;
die zwei vorhandenen High-Pakete sind react-router/react-router-dom 7.6.0.
Kein pauschales Abhängigkeitsupgrade im Chart-PR. Bundle-Nachweis folgt nach Build.

Lokale Python-3.12-Unit-Suite: 2.188 bestanden; anschließend elf weitere gezielte
Zuordnungs-/Quellen-Tests bestanden. Der vollständige Backend-Einstieg wurde
ausgeführt, kann ohne PostgreSQL hier das Projektgate nicht erfüllen. Lokale
Chromium-Ausführung endet vor Testbeginn mit SIGTRAP; Browser-/Container- und
PostgreSQL-Nachweise werden auf dem tatsächlichen PR-Code in der CI benötigt.
Diese Einschränkungen sind keine bestandenen Gates. Keine Schwelle wurde gesenkt.

Erneuter GitHub-Abgleich: main weiterhin `16e2fee`; neuer Draft #244 besitzt
Risiko-/Trendsignale und verweist ausdrücklich auf #243 als Chart-Eigentümer.
Dieses Feature ändert keine Risk-Contracts. Version/Tags bleiben bis zu einem
koordinierten Release unverändert. CI, Diff-Review und Übergabe werden ergänzt.
