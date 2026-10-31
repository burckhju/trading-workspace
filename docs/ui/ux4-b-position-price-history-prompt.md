# UX4-B — Startprompt: vorhandenen Positionskursverlauf verbessern

| Feld | Stand |
| --- | --- |
| Dokumenttyp / Version | Eigenständiger Implementierungsauftrag, Draft 0.1 |
| Datum | 31.10.2026, Europe/Vienna |
| Historische Prüfbasis | Main `1883f7f330719453958f8be1dd51d48db816662e`, `v1.5.35` |
| Gelesene Koordination | Draft #313, Head `2312abfe8834a1b652b100fc635c4d36172d5c32`; UX-3-Draft #314, Head `52a24266dce1ec048b23360b4b75d5b3f54d746b` |
| Status | Vorbereitung durch UX4-A; keine Implementierung oder Einbindungsfreigabe durch dieses Dokument |
| Ergebnis bei späterer Ausführung | Eigenständiger, getesteter Draft-PR mit begrenzten Darstellungsänderungen |
| Integrationsgrenze | Kein Merge, Release, Deployment oder PC-Update |

## Rolle und Auftrag

Du übernimmst **UX4-B** im Repository
[burckhju/trading-workspace](https://github.com/burckhju/trading-workspace).
Verbessere den **bereits vorhandenen** historischen Positionskursverlauf so,
dass Nutzer Quellen und Preisarten unterscheiden, Kauf-/Verkaufsbelege finden
und fehlende Daten auf Mobilgeräten und mit Tastatur verstehen können.

Arbeite auf dem tatsächlichen Main zum Beginn der Implementierung. Die SHA
oben ist eine historische Prüfreferenz, kein Auftrag zum Zurücksetzen.
Erhalte die vorhandenen Daten-, Zeit-, Währungs- und Berechnungsverträge.
Dieser Auftrag benötigt keine Implementierung von UX4-C oder UX4-D; gemeinsame
Einbindung und Warnsprache haben die unten genannten Abhängigkeiten.

## 1. Vor Beginn lesen und prüfen

1. Ermittle aktuellen Main-SHA, zugehörige Versionsdateien und die tatsächlich
   relevanten offenen PRs. Prüfe vorhandene Repositoryanweisungen und sichere
   fremde lokale Änderungen durch einen eigenen Arbeitszweig/-checkout.
   Keine gegenseitigen Feature-Branch-Merges zur Vorbereitung.
2. Lies [UX4-Inventur](ux4-visualization-inventory.md),
   [Visualisierungsvertrag](ux4-visualization-contract.md), insbesondere
   V01–V07 und V12–V14, die
   [Prüfmatrix](../implementation/UX4_A_QUALIFICATION.md) und den bestehenden
   [Positionshistorienvertrag](position-price-history.md).
3. Lies die unten verlinkte Master-Lead-Koordination und UX-3-Übergabe sowie
   [Product Backlog](../planning/PRODUCT_BACKLOG.md),
   [Frontendarchitektur](../architecture/FRONTEND_ARCHITECTURE.md) und
   [Teststrategie](../reference/TEST_STRATEGY.md). Löse vor Umsetzung den
   aktuellen Head und tatsächlichen Integrationsstand dieser Arbeiten erneut
   auf; benenne Änderungen gegenüber den hier gelesenen Vertragsständen.
4. Prüfe den aktuellen UX-2-Einbindungsstand. Bei der UX4-A-Inventur war
   [Draft #311](https://github.com/burckhju/trading-workspace/pull/311) mit
   `docs/ui/ux2-trade-workspace.md` außerhalb Main vorhanden; die Koordination
   prüfte Head `79e9b97e31d3bf80936fb5c026798bf8ebb10b33`. Das ist kein
   dauerhafter Status und keine automatische Einbindungsfreigabe.
   Prüfe entsprechend den tatsächlichen UX-1-Stand; damals war
   [Draft #312](https://github.com/burckhju/trading-workspace/pull/312), in der
   Koordination zuletzt Head `8f67442daac6879d7dfb28416f2171f67aead0e5`, offen.
5. Lies den unten benannten Code und die Tests auf deinem tatsächlichen
   Ausgangsstand. Halte bereits integrierte Verbesserungen fest und verkleinere
   den Änderungsumfang entsprechend, statt dieselbe Funktion erneut zu bauen.

### Veröffentlichte Koordinations- und Hinweisentwürfe

Die folgenden Quellen sind an den gelesenen Commit gebunden. Sie liegen auf
der historischen Main-Prüfbasis noch nicht vor; ihre Veröffentlichung als
Draft belegt eine Übergabe, keine Integration oder bereitgestellte gemeinsame
Runtimekomponente.

| Quelle | Gelesener Stand und Zweck |
| --- | --- |
| [UX_MASTER_PLAN](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_MASTER_PLAN.md) | Master-Auftrag und Übergaben, Draft #313 |
| [UX_OWNERSHIP](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_OWNERSHIP.md) | Ein Owner je Schnittstelle und konkrete Dateiabstimmung |
| [UX_SHARED_CONTRACTS](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_SHARED_CONTRACTS.md) | Kontext, Navigation, öffentliche Importgrenze, Readback und Qualitätsdarstellung |
| [UX_DEPENDENCIES](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_DEPENDENCIES.md) | Integrationsfolge und gemeinsame Regressionen |
| [UX_INTEGRATION_STATUS](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_INTEGRATION_STATUS.md) | Zeitgebundener Prüfstand; CI und Integrationshindernisse am aktuellen Head neu prüfen |
| [UX-3 Hinweisvertrag](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/notice-contract.md) | Belegte Ursachen, Auswirkungen, Identität, Zeit und Rückmeldungen, Draft #314 |
| [UX-3 Komponenten und Aktionen](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/components-and-actions.md) | Vorgeschlagene Präsentationsbausteine, sichere Navigationsziele, Mobil- und Fokusvertrag |

Die vorgeschlagenen UX-3-`Notice*`-Bausteine und die gemeinsame
Navigationsgrenze sind dadurch noch keine verfügbaren Imports. UX4-B nutzt
die abgestimmten Darstellungskonventionen im bestehenden lokalen Baustein;
eine konkrete gemeinsame Komponenten- oder Hostintegration folgt erst dem
bestätigten Dateischnitt. Dieser Startprompt setzt weder den Merge von #313
oder #314 voraus noch erlaubt er einen solchen Merge.

## 2. Verifizierter Iststand und Zuständigkeiten

Auf der historischen Prüfbasis existieren:

| Aufgabe | Bestehender Owner / Baustein |
| --- | --- |
| UI und Requestzustand | `frontend/src/features/operational_workspace/components/PositionPriceHistory.tsx` |
| Scatterplot pro Währung | `frontend/src/features/operational_workspace/components/PositionPricePlot.tsx` |
| Quellen-/Originalwerttabelle und Ereignisliste | `frontend/src/features/operational_workspace/components/PositionPriceHistoryEvidence.tsx` |
| Beschriftung, UTC-Zeitachsen und verfügbare Fenster | `frontend/src/features/operational_workspace/services/priceHistoryPresentation.ts` |
| Client und Antwortbindung | `frontend/src/features/operational_workspace/services/positionPriceHistory.ts` |
| Frontendvertrag | `frontend/src/features/operational_workspace/positionPriceHistory.ts` |
| Rein lesender Endpunkt | `backend/app/features/trade_position/api/price_history.py` |
| Wirksame Ausführungen und vorhandene Währungsauflösung | `TradePositionService.get_price_history_context` in `trade_position/service/application.py` |
| Positions-/Ereigniszusammenführung | `backend/app/features/trade_position/service/price_history.py` |
| Gespeicherte historische Kursbelege | `QuoteHistoryReader.prices` und `backend/app/features/market_data/service/warrant_price_history.py` |

`PositionPriceHistory` ist bereits in den aufgeklappten Workspace-Positionsdetails
und in der bestehenden Tradeverwaltung eingebunden. Geschlossene Positionen
haben dort ebenfalls eine Historie; stornierte Trades laden sie nicht. Die
ältere Planung in PR #205 wurde bereits durch #302 und Folgearbeit umgesetzt.
Prüfe den heutigen Code, nicht den Titel des alten offenen PRs.

Die Grafik verwendet Recharts als Scatterplot ohne Verbindungslinien.
Währungen erhalten getrennte Plots. Kaufdreieck und Verkaufskreuz sind
Ausführungen vorbehalten. Eine paginierte Tabelle und Ereignisliste liefern
die Belege. Default ist „Alle gespeicherten Kurse“; 7/31/90 Tage sind nur bei
nachgewiesenen Originalkurspunkten im jeweiligen Fenster wählbar.

Die Quellenlegende ist auf der Prüfbasis statisch. Bei vielen Serien
wiederholen sich Farben und Formen; die Quellen-/Ereignisevidenz ist auf
kleinen Bildschirmen umfangreich. Das sind die begrenzten Ansatzpunkte.
Das separate Basiswert-EOD-Diagramm `TimeSeriesChart` bleibt eine andere
Darstellung mit anderem Zeit- und Datenvertrag.

## 3. Konkretes Darstellungsdelta

Implementiere innerhalb der vorhandenen Komponenten folgende Verbesserungen,
soweit sie auf aktuellem Main noch fehlen:

1. **Quellen- und Preisartlegende:** Benenne Provider, Preisart, historischen
   Handelsplatz bzw. unbekannten Handelsplatz, Quellenmodus und Währung lesbar.
   Ermögliche eine rein lokale Serienauswahl nach exakter `series.id`, wenn
   mehrere Serien die Lesbarkeit beeinträchtigen. Startzustand sind alle
   gelieferten Serien. Ausblendung und Wiederherstellung sind sichtbar und
   per Tastatur bedienbar; keine automatische „beste Quelle“ auswählen.
2. **Eindeutiger Belegzugriff:** Verknüpfe angezeigte Markt-/Ausführungspunkte
   mit ihrer erreichbaren Originalwertevidenz. Die jeweilige Serien-/Punkt-
   oder Ereignis-ID muss den Beleg eindeutig halten, auch bei identischen
   Zeitpunkten/Preisen. Mehrere überlagerte Belege bleiben einzeln zugänglich;
   kein Durchschnittspunkt und keine erfundene Zeitverschiebung.
3. **Kauf und Verkauf:** Erhalte unterschiedliche Formen plus Textbezeichnung.
   Menge in Stück, Originaldatum/-zeit mit Präzision, Ausführungspreis,
   Währung und Herkunft müssen ohne Hover auffindbar sein. Ein nicht
   plottbares Ereignis erklärt weiterhin seinen vorhandenen Ausschlussgrund.
4. **Mobile Informationshierarchie:** Halte Preisart, Währung, belegten
   Zeitraum, unvollständige Abdeckung und zentrale Quellenhinweise nahe an
   der Grafik. Technische Belegdetails bleiben aufklappbar. Die vorhandene
   vollständige Tabelle darf im eigenen beschrifteten Bereich scrollen.
5. **Leere Auswahl von fehlenden Daten unterscheiden:** Sind alle Serien
   ausgeblendet, benenne diese Darstellungswahl und biete Wiederherstellung an.
   Das ist kein „keine Kursdaten“-Zustand. Originalevidenz und Ereignisliste
   bleiben vorhanden. Falls sichtbare und gelieferte Punktzahlen gezeigt
   werden, kennzeichne ihre unterschiedliche Zählbasis.

Serienwahl verändert weder `report.events` noch die serverseitige
Markerzulässigkeit, Originalwerte, Reportmetadaten oder fachliche Population.
UI-Auswahl darf beim Wechsel zu einem anderen Trade/einer anderen Position
keine fremden Quellen oder ausgeblendeten Zustände übernehmen. Keine neuen
Reads durch Tooltip, Fokus, Legende oder Quellen-/Ereignisdetails.

## 4. Unveränderlicher Kurs-, Quellen- und Ereignisvertrag

### Marktbeobachtungen und Währungen

- Verwende ausschließlich die bestehende Antwort von
  `GET /api/v1/trade-position/trades/{trade_id}/price-history` mit ihrem
  vorhandenen optionalen `days`-Parameter. Kein zusätzlicher Quote-,
  Health-, Bewertungs- oder Providerabruf zur Chartdarstellung.
- Jede Serie behält Provider, historische `identity_key`, Listing, ISIN,
  Währung, Preisart, Quellenmodus, `provider_exchange_code` und `venue_mic`.
  Gleicher Name, Provider oder gleiche Währung genügt nicht zum Zusammenlegen.
  Heutige Mappings/Listingdaten ersetzen keine historische Identität.
- BID, ASK, LAST_TRADE und PREVIOUS_CLOSE bleiben eigene Reihen.
  Unbekannte MIC bleibt unbekannt; `ISSUER` bezeichnet eine Emittentenquelle,
  keinen nachträglich angenommenen Börsenplatz.
- Getrennte Währungsplots, keine FX und keine gemischte Geldachse. Keine
  Preisableitung aus Basiswert, Einstand, Stop, Ziel, aktuellem Marktwert,
  theoretischem Modell oder Kauf-/Verkaufspreisen.
- `line={false}` und deaktivierte Animation erhalten. Keine Glättung,
  Interpolation, Fortschreibung, synthetischen Historienkurse oder zusätzliche
  stille UI-Stichprobe. Eine neue Chartengine/-bibliothek ist nicht nötig.
- Gleicher Preis bei späterer echter Originalzeit bleibt ein eigener Punkt.
  Widersprüchliche Belege bleiben getrennt; keine neue lokale Deduplizierung,
  Mittelung oder Rangordnung von Quellen.
- Decimalstrings bleiben in Tabelle und Punktdetails originalgetreu.
  Konvertierung in endliche JavaScript-Plotkoordinaten ist Darstellung,
  keine Änderung der fachlichen Werte oder Rundungsregeln.

### Zeit und Datenlücken

- Chartzeit ist `observed_at` in UTC. `retrieved_at` ist Empfangszeit,
  `captured_at` Stichproben-/Speicherzeit. Fehlendes `captured_at` eines
  Retentionsbelegs bleibt fehlend. Keine Zeit durch Abruf, Browseruhr,
  Sampling-Slot oder einen anderen Kurspunkt ersetzen.
- `collection_started_at` ist erster gespeicherter Samplezeitpunkt, kein
  Beginn vollständiger Kursversorgung. Erfasste Qualität/Status ist keine
  automatisch aktuelle Frische-/Handelbarkeitsfreigabe.
- Angefordertes Fenster, tatsächlich belegte Zeiten und Ausschlüsse bleiben
  unterscheidbar. 7/31/90 Tage verwenden den Serverzeitpunkt `window_end` und
  vorhandene Originalkurspunkte; keine Aktivierung wegen aktueller Abrufzeit
  oder eines Kauf-/Verkaufsmarkers.
- Zwischen Scatterpunkten ist kein Kurs bekannt. Zeige diese Grenze und
  vorhandene Ausschlussgründe, aber keine selbst errechnete Anzahl fehlender
  Handelskurse, Ausfallquote oder Vollständigkeitsprozent. Ein verifizierter
  Handelskalender und erwartete Frequenz sind im Vertrag nicht vorhanden.
- Der Reader prüft zuerst höchstens die neuesten **10.000 gespeicherten
  Samples nach Erfassungsreihenfolge**, danach das Originalzeitfenster;
  vorhandene Retention kommt gesondert hinzu. `samples_available`,
  `samples_considered`, `sample_limit`, `truncated` und Ausschlüsse bleiben
  sichtbar. „Alle“ behauptet keine unbegrenzte vollständige Historie.
  Sampleanzahl, Kurspunktanzahl und Zahl der Ausführungen nicht gleichsetzen.

### Kauf-/Verkaufsereignisse

- Marker nur bei bestehendem `plottable=true`, genauer Ereigniszeit und
  passendem Währungs-/Identitätskontext. `compose_price_history` und der
  vorhandene Währungsresolver entscheiden; kein lokaler Ersatzresolver.
- `executed_on` ist ein Date-only-Beleg. Datum, bekannte Zeitzone und
  Präzision bleiben in der Ereignisliste; kein Mitternachts-/Mittagsmarker,
  keine Verschiebung zum nächsten Quote. Ungeklärte Währung wird nicht aus
  dem heutigen Listing oder der Chartwährung übernommen.
- Verwende nur gelieferte wirksame Ausführungen. Korrekturen, Teilverkäufe,
  Vollverkäufe und Storno folgen dem vorhandenen Ownervertrag; keine
  Rekonstruktion effektiver History im Browser.
- Marktserien verwenden niemals die reservierten BUY-/SELL-Symbole.
  Ausführungspreise sind ausdrücklich Buchungsbelege, keine Marktbeobachtungen.
  Marker erhöhen weder Marktkurspunktzahl noch historische Kursabdeckung.

## 5. Dateiumfang und Koordination

**Fachlich lokaler Änderungskorridor:** die drei genannten
`PositionPriceHistory`-/Plot-/Evidence-Komponenten, ihr Präsentationshelper,
bei Bedarf kleine unmittelbar zugehörige Präsentationsbausteine und deren
Tests. Client-/Typänderungen sind nur zur Erhaltung der bestehenden
Antwortbindung bzw. lokalen Props zulässig, nicht zum Erfinden neuer
fachlicher Felder. Verwende vorhandene Fixtures; ergänzte Fixtures sind
ausdrücklich Testdaten und kein Nachweis realer Nutzerhistorie.

**Vor gemeinsamen Änderungen mit UX-2 abstimmen:**
`TradeManagementPage`, `PositionDetails`, `OpenPositionsPanel`, gemeinsame
Navigation, Routing, Bereichsanker, Ladeowner und Invalidierung. Dokumentiere
die genaue Einbindungsstelle, Props, Read-Lebensdauer, Reloadsignal,
Fokusziele, öffentliche Importgrenze und Konfliktdateien samt PR, Head,
Owner, erlaubtem Teilschnitt und Integrationsreihenfolge. UX-2 ist der eine
Integrator der gemeinsamen Hostdatei und besitzt hostweiten Readback,
Invalidierung und Navigation. `ExecutionDatesPanel` behält seinen eigenen
Timeline-Read. Ohne diesen Nachweis bearbeite die lokalen bestehenden
Chartkomponenten; implementiere keine neue gemeinsame Workspace-Komponente,
keinen zweiten Positionsbereich und keine zweite Timeline.

Neue direkte Imports interner Komponenten oder Services eines anderen
Features sind keine zulässige öffentliche Schnittstelle. Ein Reexport über
einen Barrelindex legitimiert solche Querimporte nicht. Verwende die von
UX-2 am konkreten Diff abgestimmte öffentliche Präsentations-/Navigationsgrenze
oder typisierte Props mit bereits qualifizierten Ownerlinks. Das in der
Koordination vorgeschlagene schmale Navigationsmodul in `frontend/src/shared/`
ist noch keine vorhandene Implementierung und wird nicht nebenbei von UX4-B
gebaut. Keine Rückimports in interne Trade-/Performance-Services und keine
Verlagerung ihrer Quellen-/Berichtsvalidatoren oder Finanzlogik in Shared.
Eine abweichende Abhängigkeitsrichtung braucht die konkrete Architektur-/
Featurevertragsentscheidung gemäß Master-Koordination.

UX-1 bleibt für sichere Währungs-/Quellenableitung zuständig. Verwende die
bereits gelieferten Belege; ändere keine Capture-, Currency-, Average-Cost-
oder Performanceberechnung. UX-3 verantwortet Qualitätssprache,
Präsentationspriorität und Hinweis-/Aktionsdarstellung; die fachliche
Qualifikation, Schwere und Blockierung bleiben beim jeweiligen Domain-Owner.
Verwende bestehende Reasoncodes/-labels nach dem gelesenen Hinweisvertrag;
stimme den konkreten Adapter und die Texte ab. Leere, fehlende, veraltete,
gekürzte und technisch fehlgeschlagene Reads bleiben verschieden. Keine
globale Qualitätsampel, eigene Freshness-Schwelle oder neues `Notice*`-
Framework in UX4-B. Historische Kursbelege erlauben keine neue Behauptung
über heutige Provider-Recovery. Folgeaktionen verwenden vorhandene geprüfte
Ziele; ein Trade-/Bereichslink behauptet keinen noch unbelegten Fokus auf
eine einzelne Ausführung. Ein Lese-Retry bleibt beim bestehenden Readowner.

Backend-Reader, Finanz-/Risiko-/Monitoringlogik, Persistenz, Provider,
Scheduler, Migrationen, Dependencies und Versionsmetadaten bleiben außerhalb
dieses Darstellungsauftrags. Reicht ein vorhandener fachlicher Vertrag für
eine gewünschte Anzeige nicht aus, benenne diese Voraussetzung und liefere
den unabhängig möglichen Darstellungsumfang; fehlende Daten nicht ergänzen.

## 6. Ladeverhalten, Mobil und Tastatur

Erhalte die vorhandene Trade-/Position-/Reload-Key-Grenze, Requestabbruch und
Abwehr verspäteter Antworten. A→B→A und Korrektur-/Reloadrennen dürfen keine
fremden/alten Marker, Serien, Fehler oder Folgeaktionen anzeigen. Echter
Identitätswechsel verwendet die vorhandenen Dirty-/Busy-Guards sowie
Generation-/Abortgrenzen; Abbruch allein reicht nicht als Nachweis.
Ein Abschnitts- oder Hashwechsel innerhalb desselben Trades ist dagegen
kein fachlicher Identitätswechsel: kein neuer Requestschlüssel aus dem
gesamten URL-/Hashwert, kein allein dadurch ausgelöster Reload oder Remount
und keine zusätzlichen Trade-/Positions-/Timeline-/Historien-Reads.
Formularentwürfe und gültige Chartzustände bleiben erhalten; die Navigation
und ihr Fokusziel gehören UX-2.

Erfolgreicher Buchungs-/Quellenreadback erneuert die betroffenen Sichten
über den mit UX-2 vereinbarten Ownerablauf, ohne manuelle Entwürfe zu löschen.
Ein gescheiterter Readback ist keine bestätigte neue Ausführung und kein
neuer qualifizierter Historienstand. Zeitraumwechsel entfernt die vorherige
Antwort; Ladefehler bleibt getrennt von leerer oder begrenzter Evidenz.
Lazy-Chartfehler lässt die zugängliche Datenevidenz weiterhin erreichbar.

Prüfe 320, 390 und 1280 CSS-Pixel sowie 200 % Zoom: keine horizontale
Dokumentrolle, abgeschnittene Einheiten oder unbedienbare Legenden. Erhalte
beschriftete eigene Tabellen-Scrollregionen, semantische Header und Pagination.
Bediene Zeitraum, Serienwahl, Belegzugriff und Retry mit Tab/Shift-Tab,
Enter/Leertaste; prüfe vorhandene Diagramm-Pfeiltasten. Jeder wesentliche
Punkt-/Ereignisinhalt bleibt ohne Hover erreichbar. `accessibilityLayer`
allein beweist keine vollständige Scatter-Punktnavigation oder Screenreader-
Abnahme. Prüfe sichtbaren Fokus, Text-/Grafikkontrast und Unterscheidbarkeit
durch Form/Text zusätzlich zu Farbe konkret.

## 7. Tests und Nachweise

Nutze die existierenden Tests als Regressionen; ändere keine Gates oder
Assertions, um einen unerwarteten Befund zu verbergen.

| Prüfbereich | Vorhandene Anker / zusätzliche Erwartungen |
| --- | --- |
| Originaldaten, Identity, Währung, Zeit und Limits | `tests/unit/backend/features/market_data/test_warrant_price_history.py`; bestehende Dedup-, Retention-, Quellen-/MIC-/Currency-/Originalzeit-/Budgetfälle unverändert erhalten |
| Effektive Ausführungen und Quellenbindung | `tests/unit/backend/features/trade_position/test_position_price_history.py`; Date-only/Sommerzeit, Korrektur, Storno, fremde/ungeklärte Währung, Teil-/Vollverkauf |
| Persistenz und rein lesende API | `tests/integration/backend/database/test_position_price_history_postgres.py`; nur mit tatsächlich verfügbarer Test-PostgreSQL als ausgeführt/bestanden ausweisen |
| Chart und Evidence | `frontend/src/features/operational_workspace/components/PositionPriceHistory.test.tsx`; neue Serienwahl, alle ausgeblendet, mehrere überlagerte Belege, volle Decimalwerte und erhaltene Ereignisliste |
| Zeit-/Quellenlabels und Responseguards | Bestehende Tests zu `services/priceHistoryPresentation.ts` und `services/positionPriceHistory.ts`; Sekunden, Tages-/Jahreswechsel, unbekannter/Issuer-Handelsplatz, exakte Trade-/Positionbindung |
| Host-Regression | `frontend/src/features/trade/pages/TradeManagementPriceHistory.test.tsx`; vorhandene Readback-/Reload-/Stornoisolation erhalten, gemeinsame Hoständerung nur mit UX-2-Abstimmung; Abschnitts-/Hashwechsel desselben Trades erhält Entwürfe und Chartzustand ohne neue Reads, echter Wechsel und A→B→A bleiben isoliert |
| Öffentliche Grenze und Hinweise | Konkreten Diff gegen Frontendarchitektur und UX-2-Schnittstelle prüfen; kein neuer interner Featurequerimport durch Barrelumweg; UX-3-Konventionen mit unveränderten Domaincodes, belegten Zielen und ohne doppelte Live-Ankündigung |
| Browser | `tests/e2e/position-price-history.spec.ts`; ergänze reale Mobil-/Tastatur-/Fokusfälle für das neue Delta und Screenshotbelege mit gekennzeichneten Testdaten |
| Viele Serien | Mehr als sechs bzw. zwölf Serien, mehrere Quellenmodi/Preisarten/MICs, reservierte BUY-/SELL-Formen, sichtbare Ausblendung und Originalevidenz ohne zusätzliche Serverreads |
| Fehlzustände und Seiteneffekte | Einzelpunkt, keine Punkte, nur nicht plottbare Ereignisse, truncated, Fehler/Retry, Lazy-Fehler, A→B→A und alter Korrekturresponse; keine neuen Writes oder Providerrequests |

Führe die relevanten vorhandenen Owner-/UI-Regressionen und das unveränderte
Frontendgate mit der im Repository festgelegten Toolchain aus. Wenn
PostgreSQL-/Browser-/CI-Prüfung nicht verfügbar ist, benenne das konkret;
übersprungen ist nicht bestanden. Die Standard-CI muss den tatsächlichen
PR-Head bzw. zugehörigen Testmerge prüfen. Frühere grüne Läufe zählen nicht.

Zeige per Diff, dass finanzielle Berechnungen und Kursreader unverändert
sind. Neue Tests prüfen Nutzerverhalten, Einheiten, Datenidentität und
Seiteneffekte; keine Tests nur für die gewählte JSX-Struktur schreiben.

## 8. Abschluss und Lieferung

Erstelle einen eigenen Draft-PR mit:

- tatsächlichem Main-SHA, eigenem finalen Head sowie exakt geprüften
  Master-/UX-1-/UX-2-/UX-3-Heads und deren Integrationsstand;
- konkretem verbessertem Nutzerweg und begrenztem Dateiumfang;
- Beschreibung der wiederverwendeten Komponenten und unveränderten
  Quellen-/Zeit-/Währungs-/Markerentscheidungen;
- dokumentierter UX-2-Einbindung bzw. noch offener Einbindung, öffentlicher
  Importgrenze und gemeinsamem Readback-/Navigationsnachweis sowie
  UX-1-/UX-3-Abhängigkeiten und konkret abgestimmten Qualitätstexten;
- tatsächlich ausgeführten Tests, verbleibenden Prüfgrenzen sowie Mobil-/
  Tastaturbelegen des konkreten Änderungsstands;
- aktualisiertem [Positionshistorienvertrag](position-price-history.md),
  soweit sich die Bedienung ändert, und genau einem nächsten Schritt.

Kennzeichne implementiert, lokal geprüft, CI-geprüft, fachlich abgestimmt
und integriert getrennt. Ein veröffentlichter Koordinations-/Hinweisentwurf
ist keine Runtimeintegration; ein grüner einzelner PR ist kein gemeinsamer
Laufzeitnachweis. Keine behauptete Produktionsdatenabdeckung,
kein Merge, Release oder PC-Update im Rahmen dieses Auftrags.

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | Eigenständiger UX4-B-Startprompt aus Main-Inventur und Visualisierungsvertrag; Koordination #313 und UX-3-Hinweisentwurf #314 an exakten Heads eingearbeitet; keine Runtimeänderung |
