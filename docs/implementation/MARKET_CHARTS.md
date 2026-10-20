# Markt-, Sektor- und Aktiendiagramme

Datum: 2026-10-04. Status: implementiert und mit PR #243 gemergt (`f580bfe`).
Versionierte Auslieferung: [1.5.0](../releases/V1.5.0-MARKET-CHARTS-AND-POSITION-RISK.md).
Keine fachliche Liveabnahme oder Bereitstellung.
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
Antwortgrenze. Gemeinsamer Start ist der erste gemeinsam beobachtete Tag im
gewählten Intervall; ein unbrauchbarer Startwert sperrt den Vergleich, ohne auf
einen späteren Tag auszuweichen. Fehlende Serien verhindern einen
scheinbar vollständigen Vergleich. Kein Forward-Fill, keine Interpolation,
keine FX-Umrechnung. CLOSE bleibt unbereinigt; ADJUSTED_CLOSE fällt niemals auf
CLOSE zurück. Unpassende Renditegrundlagen werden erklärt statt vermischt.

## UI und Einrichtung

Bedienkorrektur 1.5.1: Mehrere Serien starten mit gemeinsamem Start 100.
Explizites Vergleichen verlässt die absolute Einzelansicht und blendet die
gewählten Reihen ein. Prozentdarstellung, Legende und per Identität gewählte
Einzelserie bleiben bei Zeitraum-, Enddatum- und Preisfeldwechsel erhalten.
Die Einstellung gilt innerhalb der geöffneten Seite; ein vollständiges Neuladen
startet mit der automatischen Darstellung. Tabellenpagination startet nach einem
Datenwechsel neu. „Originalkurs“ und „Split-/dividendenbereinigter Kurs“ sind
verständliche Beschriftungen der unveränderten CLOSE/ADJUSTED_CLOSE-Werte.

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

Implementiert auf `feat/market-sector-stock-charts`,
[PR #243](https://github.com/burckhju/trading-workspace/pull/243).
Marktserie, dynamische gesamte Sektormatrix, Aktien-/Positions-Drill-down,
Vergleich und bestätigte Einrichtung sind vorhanden. Die PostgreSQL-Abnahme nutzt
elf synthetische Sektoren, zwei ETF-Zuordnungen, eine Aktie und einen direkten
Index; neun absichtliche Einrichtungslücken bleiben sichtbar. Diese Fixtures
werden nie als Produktionsdaten ausgeliefert. Providerzugangsrechte, vorhandene
Zuordnungen und tatsächliche Historie auf JMBbot sind nicht belegt.

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

Provenienzgrenze der vorhandenen DailyPrice-Persistenz: je Zeile sind MDI,
Provider, Symbol, Währung und Empfangs-/Quellenzeit gespeichert, jedoch keine
historische Provider-Exchange- oder Mappingrevision. `identity.mapping_*` und
`provider_identity` beschreiben den aktuellen Verwaltungsstand, keinen
nachträglich erfundenen Importnachweis. Symbol-/Providerkonflikte sperren die
betroffenen Werte. Nach einer fachlichen Mappingkorrektur müssen betroffene
Historien über den kontrollierten Import geprüft/erneuert werden.

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
ETF-Vorbelegungen binden MIC und Währung explizit; fehlt der passende aktive
Handelsplatz oder die Währung, blockiert das Formular statt den ersten Eintrag
zu übernehmen. Der vorhandene Handelsplatzabgleich wird nach technischer
Mappingvalidierung angezeigt; mehrdeutige Provider-Exchange-Codes sind kein
Beweis für eine genaue Notierung.

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
Kein pauschales Abhängigkeitsupgrade im Chart-PR. Produktionsbuild: Haupteinstieg
633,42 kB / 170,19 kB gzip (Basis: 629,46 / 168,73 kB); separat geladene
Diagrammroute 382,24 / 113,26 kB, Einrichtung 14,04 / 4,82 kB. Die schon zuvor
vorhandene Vite-Warnung zum Haupteinstieg über 500 kB bleibt bestehen.

Lokale Python-3.12-Unit-Suite: 2.188 bestanden; anschließend elf weitere gezielte
Zuordnungs-/Quellen-Tests bestanden. Der vollständige Backend-Einstieg wurde
ausgeführt, kann ohne PostgreSQL hier das Projektgate nicht erfüllen. Lokale
Chromium-Ausführung endet vor Testbeginn mit SIGTRAP; Browser-/Container- und
PostgreSQL-Nachweise werden auf dem tatsächlichen PR-Code in der CI benötigt.
Diese Einschränkungen sind keine bestandenen Gates. Keine Schwelle wurde gesenkt.

CI auf `4187d33c5d0975324debb22107c18882350f206d`: 2.335 Backend-Tests,
85,48 % Coverage; Ruff, Black, mypy, PostgreSQL-Migration, restriktive Image-Rechte
und Renderer-/Legacy-Migrations-/Compose-Sandbox-Prüfung bestanden. Erste
Frontend-Runde: 403/405 bestanden (zwei ältere Erwartungen an Navigation und
STOCK-Payload); E2E: 43/44 bestanden (neue Tabellenüberschriften benötigten
explizites `scope="col"` für Chromium). Folgeänderungen beheben diese Befunde,
prüfen die exakte ETF-Vorbelegung und hängen Desktop-/Mobilbilder zur visuellen
Kontrolle an. Finale unveränderte Gates und Commit sind im PR nachgewiesen.

Integrationsnachweis vom 04.10.2026: PR #244 ist anschließend als `35a9cb7`
gemergt. Seine Risiko-Migration `20261004_0044` folgt der Chart-Migration 0043;
es gibt genau einen Alembic-Head. Die Positionsdetails enthalten Diagrammlink
und Risikoanzeige. Der kombinierte Stand besteht die vollständige CI: 2.393
Backend-Tests mit 85,71 % Coverage, 417 Frontend- und 45 E2E-Tests. Die
Chart-Fachverträge wurden dabei nicht verändert. Der gemeinsame Release ist
1.5.0; der historische Tag 1.4.5 bleibt unverändert auf `16e2fee`.

## Betreiberübergabe ohne Serverzugriff

Für die versionierte Auslieferung gelten die aktuellen
[1.5.0-Betreiberbefehle](../technical/LINUX_DEPLOYMENT.md#market-charts-and-position-risk-150).
Die folgenden Commit-Befehle dokumentieren die vorherige Chart-Einzelübergabe.

Keine Server-, Provider-, Consent- oder Telegram-Aktivierung wurde ausgeführt.
Auf einem bereits migrierten Vier-Service-Stack gilt der aktuelle Abschnitt
[Update an already migrated four-service deployment](../technical/LINUX_DEPLOYMENT.md#update-an-already-migrated-four-service-deployment-145).
Vor einer Bereitstellung muss der Betreiber den tatsächlich qualifizierten
Merge-Commit aus PR #243 und seine aktuelle Topologie prüfen. `v1.4.5` enthält
diese Diagramme nicht. Mit diesem geprüften Commit kann ein neuer, bislang
nicht existierender Arbeitsbaum vorbereitet werden (lokale Eingabe statt
erfundener SHA oder privater Zustandsdatei):

```bash
read -r -p 'Qualifizierter Merge-Commit aus PR #243: ' chart_commit
git -C "$HOME/Boerse/trading-workspace" fetch origin main </dev/null
git -C "$HOME/Boerse/trading-workspace" show --no-patch --format=fuller "$chart_commit"
chart_release="$HOME/Boerse/trading-workspace-charts-${chart_commit:0:12}"
chart_state="$HOME/Boerse/trading-workspace-deploy-charts-${chart_commit:0:12}"
git -C "$HOME/Boerse/trading-workspace" worktree add --detach "$chart_release" "$chart_commit" </dev/null
bash "$chart_release/scripts/migrate-legacy-issuer.sh" prepare \
  "$HOME/Boerse/trading-workspace" "$chart_state" </dev/null
```

Nur nach erfolgreicher Prüfung dieser Vorbereitung im Wartungsfenster:

```bash
bash "$chart_release/scripts/migrate-legacy-issuer.sh" apply "$chart_state" </dev/null
bash "$chart_release/scripts/migrate-legacy-issuer.sh" compose "$chart_state" ps
bash "$chart_release/scripts/migrate-legacy-issuer.sh" compose "$chart_state" \
  exec -T backend python -m app.tools.monitoring_resume preflight
```

Die Befehle setzen die im Runbook dokumentierte Quellinstallation voraus; bei
abweichender Topologie zuerst den vorhandenen Erhaltungsnachweis klären.
Alte Release-/Zustandsverzeichnisse bleiben erhalten. Kein ungeprüfter Basisstart,
kein Volume-Löschen, kein DB-Stamp und kein automatisches Downgrade. Anschließend
im UI Zuordnungen/Quellen prüfen, einzelne begrenzte Importe bestätigen und die
Abdeckungsmatrix sowie reale EOD-Daten abnehmen. CI belegt diesen Livezustand nicht.
