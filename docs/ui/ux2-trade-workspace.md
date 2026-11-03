# UX-2: Einheitlicher Trade- und Positionsarbeitsbereich

## UX2-B — aktueller, begrenzter Implementierungsschnitt

### Live-Basis und Datei-/Leseverantwortung vor dem Produktdiff

Am 03.11.2026 vor dem Produktdiff geprüft: Ausgangs-Main `3397399e7bf8364501437f9509a4fb18dbe32c08`,
Tree `c9362029d9fc3a1d0ccf7bee4e1f5b942e474807`, Version **1.5.38**.
#321 ist über `e681c79e0c46a6efb9e4eeb7cd18d959ad99ea97`, #320 über
`91ebbc0f51ef000891aee7218ec6dff6a3ce2620` und #322 über den aktuellen Main
integriert. Der getrennte Versionsschnitt #323 und Tag `v1.5.38` zeigen auf
`849a6d54eaeb5f5831754c6b15a41358c571f6da`; UX4-B liegt danach auf Main.
Die früheren Main-/Draftangaben unten und in den Masterdokumenten sind datierte
Nachweise. Die integrierten Owner-/Schutzverträge gelten weiter. #321 verändert
genau die fünf Masterdateien; sie bleiben in diesem Auftrag unverändert.

Kein bestehender UX2-B-Branch oder -PR wurde gefunden. Eigener Branch:
`feat/ux2-b-trade-overview`. Die beim Start offenen PRs #315, #220, #207, #205, #197 und #187
haben keine Dateiüberschneidung mit dem folgenden Schnitt. #315 bleibt eine
historische Draft-Quellreferenz, kein zweiter normativer Hinweisvertrag.

| Datei / bestehender Owner | Erlaubter Änderungsschnitt | Props und Lade-/Aktualisierungspfad | Überschneidung / Integrationsfolge |
| --- | --- | --- | --- |
| `frontend/src/features/trade/pages/TradeManagementPage.tsx`: UX2-Host, validiert Trade/Position/Management/Produkt | Vorhandenen Überblick komponieren, validierte Position weiterreichen, technische Readbereitschaft und Revision führen | `tradeId`, `productId`, `position`, `cancelled`, `positionRead`; Reload und bestehende Write-Readbacks erneuern den Host; Timelineereignis invalidiert nur | UX1-Entwürfe/Preview erhalten; UX4-Slot mit `tradeId`, `positionId`, `historyReloadToken` erhalten. Direkt auf aktuellem Main |
| `frontend/src/features/trade/pages/index.ts`: Routenexport mit separat angehängter Bewertung | Bestehende Seite direkt exportieren; Bewertung nur im Hostüberblick | Kein eigener Positions-/Bewertungsread mehr außerhalb des Hosts; Quellenmodus bleibt ausgeschlossen | Gemeinsam mit Host/Panel integrieren; keine neue Route |
| `frontend/src/features/trade/components/ProductValuationPanel.tsx`: Bewertungsread und bestehende Qualifikationsdarstellung | Doppelten Positionsread entfernen; unabhängigen Bewertungszustand an validierten Host und Revision binden; ausführliche Herkunft aufklappbar ordnen | Nur `productValuation`; Abort/Generation, Trade-/Positions-/optionale Basisidentität prüfen; keine Hash-/Detailabhängigkeit | Vorbereiteter UX3-B2/Q12-Schnitt: Status-/Reason-/Warningmapper bleiben UX3; spätere Arbeit auf neuen Propvertrag abgleichen. Keine Zustimmung eines anderen Leads behauptet |
| Bewertungs-/Host-/Kontexttests unter `frontend/src/features/trade/` | Geänderte Readzahlen, Qualifikation, Racefälle, Readback und Entwurfserhalt absichern | OPEN/CLOSED/CANCELLED, fehlende/fremde Daten, Reload, A→B→A, bestätigter Write mit erfolgreichem/fehlgeschlagenem Readback | Bestehende UX1-/Chartregressionen behalten |
| `tests/e2e/trade-workspace-navigation.spec.ts` | Synthetische Bewertungsfixture und additive Überblicks-/Read-/Tastaturfälle bei 320/390/1280 px | Kopierter Direktlink, Reload, Hash-/Detailwechsel und historische Rückwege | #322 ist integriert: dessen Quellenwahl-, Originalbeleg-, Pagination- und Entwurfsassertionen vollständig erhalten |
| Dieses UX2-Dokument | Lesevertrag, Herkunft und konkrete Nutzerwege; tatsächliche Prüfbelege im PR | Keine neue Fachstatusquelle | PRODUCT_BACKLOG bleibt einzige fachliche Statusquelle; keine Änderung der fünf Masterdateien |

**Parallelstand und anschließende Main-Anbindung von #324:** Der während der
Umsetzung erschienene [UX3-B2-PR #324](https://github.com/burckhju/trading-workspace/pull/324)
wurde zunächst als Draft am Head `5c6eab563595872ab5fc19123578beb8e6870fa9` geprüft.
Seine sieben Dateien überschneiden sich in `ProductValuationPanel.tsx`, dessen
Haupttest und Währungstest mit UX2-B. UX3 verantwortet Warnursachen/-texte und
Originalcodedetails; UX2 Props, Readlebensdauer und Platzierung.

Am 03.11.2026 um 05:47:53 UTC wurde #324 auf Main integriert. Die neue tatsächliche
Integrationsbasis ist **`7399bccaf0c2923327b15ee43cfbc484e7cd3b30`**; Version 1.5.38
bleibt erhalten. UX2 übernimmt genau diesen integrierten Main. Die UX3-Mapper,
Originalhinweisdetails, Warntextassertions und der geänderte Monitoring-E2E-Fall
bleiben vollständig erhalten. Die neue `ProductValuationPanel.notices.test.tsx`
erhält den validierten Hostkontext und erwartet null eigene Positionsreads;
ihre acht Q12-/Qualifikations-/Originalcode-/XSS-/Bedienfälle bleiben erhalten.

Damit ist die zuvor dokumentierte technische Reihenfolge umgesetzt. Der textuell
saubere Merge allein ist keine kombinierte Qualifikation: Alle regulären Gates
werden am neuen gemeinsamen Head/Testmerge erneut ausgeführt und am eigenen
Draft-PR nachgewiesen. Keine fremde Zustimmung, menschliche Fachabnahme oder
Freigabe zum Merge dieses UX2-PRs wird daraus abgeleitet.

**Ergänzter Prüfschnitt nach der ersten Implementierung:** Die Einbettung und die
O1-konforme Anzeige betreffen zusätzlich bestehende Browserassertions. Ihre
fachlichen Werte, Write-/Receipt-/Historienprüfungen und Mindestbreiten bleiben
verbindlich; nur die tatsächlich geänderten Orte und Anzeigen werden angepasst.

| Bestehende E2E-Dateien | Begrenzte Anpassung |
| --- | --- |
| `frankfurt-reference-valuation.spec.ts`, `position-currency-qualification.spec.ts`, `position-risk.spec.ts` | Eindeutig benannte Bewertungsregion statt aller verschachtelten Abschnitte; vorhandene Frankfurt-IDs vervollständigen; Herkunft explizit aufklappen; Bewertung vor Risiko prüfen. Bestehende Finanz-, Read-only-, Breiten- und Overflowassertions bleiben erhalten |
| `ft010-trade-management.spec.ts`, `trade-management-context.spec.ts`, `depot-sell-capture.spec.ts`, `trade-timeline.spec.ts`, `position-price-history.spec.ts` | Offene Menge weiterhin exakt, jetzt mit Einheit Stück; Planreferenz in den Herkunftsdetails prüfen. Kein Chart-/Historienverhalten ändern |
| `trade-execution-corrections.spec.ts` | Alle exakten API-Betrags-/Average-Cost-/Korrekturprüfungen beibehalten; im Überblick Menge mit Einheit und den O1-Ausschluss unqualifizierter Rohbeträge prüfen |

Der Bewertungsblock nutzt die vorhandene Kartenbreite. Die bestehenden
Mindestbreiten im Risikotest werden nicht abgesenkt.

Beim weiteren Live-Abgleich wurden außerdem zwei neue offene Drafts geprüft:
#326 am Head `799d2d69d45e890a440ed4963ad5399335bb8b75` betrifft die Q12-Darstellung
in `PositionDetails`; die einzige gemeinsame Datei ist nun
`position-currency-qualification.spec.ts`. #326 ergänzt dort die Assertions vor
der Navigation, UX2 präzisiert den Bewertungsselektor danach; beide Teile bleiben
bei Integration erhalten. #327 am Head
`797e08abb10e9a1698cd8c873791baad9b8d4ae3` betrifft UX4-C und hat keine
Dateischnittmenge. Aus diesen beiden Vergleichen folgt keine zusätzliche
technische Reihenfolge. Die Anbindung an den integrierten #324-Stand ist oben
gesondert belegt.

### Positions- und Bewertungs-Lesevertrag

Der Host besitzt die validierte Position. Seine vorhandenen Trade-, Positions-,
Management- und Produktprüfungen bleiben Erfolgsvoraussetzung des fachlichen
Readbacks. Die Bewertung bleibt ein nachgelagerter, unabhängiger Reader und wird
**keine zusätzliche Erfolgsvoraussetzung** einer gespeicherten Buchung.

Jeder Hostversuch und jede bestätigte passende Buchungsänderung entwerten die
bisherige Bewertungsrevision. Das Timelineereignis belegt den bestätigten Write,
nicht den anschließenden erfolgreichen Host-Readback: Es invalidiert nur und
startet keinen eigenen Positionsread. Erst ein erfolgreich validierter, offener,
nicht stornierter Hoststand erlaubt einen Bewertungsread. `historyReloadToken`
bleibt bei seiner bisherigen Bedeutung für Chart und UX1-Vorschau; er allein
wäre für den Fall „Write bestätigt, Host-Readback fehlgeschlagen“ unzureichend.

| Ereignis | Position / Bewertung | Sichtbarer vorheriger Stand |
| --- | --- | --- |
| Erster OPEN-Aufruf | Ein Hostpositionsread, danach ein Bewertungsread | Kein erfundener Wert während Laden/Fehler |
| CLOSED oder CANCELLED | Ein Hostpositionsread, kein aktueller Bewertungsread | Historische Zugänge; kein neuer Pflichtschritt |
| Same-Trade-Reload | Alte Revision sofort ungültig; ein Hostread; Bewertung erst nach dessen Erfolg | Letzte Hostidentität/Position mit sichtbarem Aktualisierungsvorbehalt; Entwürfe/Chart bleiben gemountet; alte Bewertung ausgeblendet |
| Bestätigter Write | Timelineereignis invalidiert, bestehender Aufrufer führt Host-Readback aus | Receipt bleibt vom Readback getrennt |
| Host-Readback erfolgreich | Neue Revision; ein neuer Bewertungsread | Neuer validierter Hoststand; Bewertung hat eigenes Laden/Ergebnis/Fehler |
| Host-Readback fehlgeschlagen | Keine neue Bewertungsfreigabe | Alte Bewertung bleibt ungültig; letzter Hoststand ausdrücklich als nicht aktualisiert kenntlich |
| Tradewechsel / A→B→A | Bestehender keyed Kontext, Abort und Generation; Identitäten erneut prüfen | Kein fremder oder bereits abgeschlossener alter Erfolg/Fehler darf wiederkehren |
| Hashwechsel / Details | Null zusätzliche Positions-/Bewertungsreads | Formulare und Chartzustand erhalten |
| `view=sources` | Keine aktuellen Positionsbewertungsreads | Bestehende unabhängige historische Quellenreader |

Die Bewertungsantwort muss zum Trade und zur Position gehören; eine vorhandene
`position_basis.position` zusätzlich zu Trade, Position und Produkt. Die
Mengen-/Zeit-/Geldwerte verschiedener Reader werden nicht auf vermeintliche
Gleichzeitigkeit geprüft oder gemeinsam verrechnet. Zusammen dargestellte
Abschnitte garantieren **keinen atomaren Finanzsnapshot**. Die tatsächliche
Bewertungsbasis bleibt über `PositionValuationBasisDetails` erreichbar.

### Herkunftsmatrix des Überblicks

| Anzeigewert | Vorhandener Owner / DTO | Qualifikation und Basis | Ohne passenden Nachweis |
| --- | --- | --- | --- |
| Trade-/Produktidentität, ISIN/WKN | TradePosition `TradeResponse`; Produkt `WarrantResponse` | Host prüft Trade-/Produktzugehörigkeit | Keine erfundene Identität |
| OPEN/CLOSED/CANCELLED | `TradeResponse.cancelled_at`, `PositionResponse.is_closed` | Bestehende Lifecyclebedeutung; kein Status aus HTTP 404 | Lade-/Fehlerzustand, keine erfundene Schließung |
| Offene Menge | `PositionResponse.open_quantity` | Validierte Positionsprojektion, Einheit Stück | Fehlend bleibt fehlend; echte 0 bleibt 0 |
| Eröffnung, letzte Ausführung, Abschluss | `opened_on/at`, `last_execution_on/at`, `closed_on/at` | Datum ohne Uhrzeit bleibt date-only | Keine ergänzte Uhrzeit |
| Bid, Ask, Referenzkurs | `ProductPositionValuationResponse` | Bestehende `valuation_usable`-/`analysis_usable`-Anzeige, Kursart und Kurswährung | `null` bleibt „—“, kein Ersatzkurs/Nullbetrag |
| Marktwert / indikativer Wert | Derselbe DTO: `market_value` / `analysis_market_value` | Jeweilige Ownerverwendbarkeit und tatsächliche Bewertungsbasis | Kein Betrag ohne Verwendbarkeit; `null` bleibt fehlend |
| Unrealisierter Brutto-G/V | Derselbe DTO: aktuelle oder Analyse-G/V-Felder | `qualifiedUnrealizedPnl`, eigenständiges `unrealized_pnl_usable` bzw. `analysis_unrealized_pnl_usable` und Währung | Bestehender Nichtberechenbarkeitsgrund; echter Nullbetrag bleibt möglich |
| Volumen, Spread und Spread-% | Bestehende optionale Bewertungsfelder | Unveränderte Ownerwerte; Spreadbezug Bid | Fehlendes Feld entfällt; Volumen 0 bleibt Einschränkung der Handelbarkeit |
| Kursalter, Kurs-/Abruf-/Bewertungszeit | Bestehende Bewertungsfelder | Originalpräzision, unbekannte Zeitzone und Retention bleiben erhalten | Unbekannt bleibt unbekannt; Abrufzeit ist keine neue Kurszeit |
| Kostenbasis-/Währungsevidenz | `PositionValuationBasis` | Bestehende Definition, `basis_id`, wirksame Executions und Kaufwährungsnachweise | Kein zusätzlicher Geldqualifikationsschluss |

**O1-Teilblocker:** `PositionResponse.cost_basis`, `average_entry_price` und
`realized_gross_pnl` besitzen keinen ausreichenden Geldwertvertrag für den neuen
Überblick. Sie werden dort nicht als qualifizierte Geldwerte präsentiert. Weder
die heutige Kurswährung noch `currency_status=KNOWN` qualifizieren pauschal diese
drei Rohwerte. Der genaue fehlende Teil bleibt benannt; Layout, vorhandene
Bewertung und ihre eigene G/V-Qualifikation sind davon unabhängig. Keine eigene
Kostenbasis-, Average-Cost-, FX- oder Ergebnisrechnung.

Die Q12-Hinweisregeln aus dem inzwischen integrierten UX3-B2-Schnitt #324 bleiben
unverändert beim UX3-Owner; UX2 übernimmt sie ohne neue Ursachen- oder
Finanzqualifikation. Die gesonderte `PositionDetails`-Fortsetzung in #326 und
menschliche Q12-/F2-Abnahmen bleiben getrennt. Alerts, Positionsrisiko und
operativer Monitoringzustand behalten ihre getrennten Flächen und Owner.

### Vorherige und neue Nutzerwege

| Nutzerziel | Vorher auf dieser bereits vorhandenen Route | UX2-B |
| --- | --- | --- |
| Bestand und Produktbewertung gemeinsam prüfen | Positionskopf oben; Bewertung erst hinter Buchungen, Risiko, Verkaufs-/Managementformularen und Storno | Beides direkt im vorhandenen `#trade-overview`, Bewertung vor dem Chart; kein zusätzlicher Seitenwechsel behauptet |
| Verwendbarkeit/G/V-Grenze erkennen | Bewertung und ihre Einschränkungen erst nach langem Scrollweg | Bestehende Einschränkungen neben den Werten; technische Herkunft aufklappbar |
| Mögliche weitere Arbeit wählen | Allgemeiner „Nächster Schritt“, einschließlich pauschaler Nachbeobachtungsaufforderung | Konkrete bestehende Links entsprechend OPEN/CLOSED/CANCELLED; keine neue Pflicht aus einem Lifecyclezustand |
| Bewertung nach Buchungsänderung einordnen | Separater Positionsread und Timelineevent konnten der Hostvalidierung vorauslaufen | Hostposition einmal validiert; neue Bewertung erst nach erfolgreichem Readback; Fehlergrenze sichtbar |

Die ergänzten Regressionen prüfen diese Read-, Qualifikations- und Bediengrenzen
in den bestehenden Bewertungssuites, der neuen `TradeManagementOverview.test.tsx`
und den erhaltenen Host-/Navigationssuites. Der vollständige UX4-B-Charttest in der
gemeinsamen E2E-Datei bleibt unverändert. Die drei Überblicksfälle erzeugen
Screenshotanhänge bei 320, 390 und 1280 px für die konkrete Darstellungsprüfung.

Reproduktion mit `frontend/.nvmrc` (Node 22.16.0), npm 10.9.2 und unveränderter
Lockdatei: `bash scripts/check-frontend.sh`; Browserregression über
`npm --prefix frontend run e2e -- trade-workspace-navigation.spec.ts` im bestehenden
Teststack. Die reguläre PR-CI führt zusätzlich Backend-Coverage, alle vier
E2E-Ownerjobs, Issuer-Sandbox, restriktive Imageprüfung und Publication Guards
aus. Keine Pflichtprüfung wird durch einen Teiltest ersetzt.

Tatsächlich ausgeführte Läufe, finale Dateiliste, Head/Testmerge/Tree und reguläre
CI werden am eigenen Draft-PR gebunden. Die lokale Sandbox kann Chromium nicht
starten (SIGTRAP vor Seitenöffnung); lokale Vitest-Dateiergebnisse ohne beendeten
Prozess sind ebenfalls kein vollständiger Gateerfolg. Die CI muss deshalb den
gesamten tatsächlichen Änderungssatz qualifizieren. Technische Implementierung
ist keine menschliche Fachabnahme. UX2-C/D, Merge, Versionserhöhung, Release,
Deployment und PC-Update bleiben getrennt.

## Historische UX2-A-Übergabe

Die folgenden zeitgebundenen Angaben dokumentieren die damalige A-Arbeit; ihre
offenen Integrationsaussagen wurden inzwischen durch #318 und seine Nachfolger
überholt. Sie sind keine erneuten Umsetzungsaufträge.

## Prüfgrundlage und Umfang

Die Bestandsaufnahme vom 31.10.2026 beruht auf dem tatsächlich geklonten Main-Commit
`1883f7f330719453958f8be1dd51d48db816662e`. Der live geprüfte veröffentlichte Versions-Tag
`v1.5.35` zeigt genau auf diesen Commit. Der erfolgreiche
[Version-Tag-Lauf 41172652775](https://github.com/burckhju/trading-workspace/actions/runs/41172652775)
einschließlich Tag-Job `124453728314` bestätigt die Veröffentlichung. Der Publisher erzeugt
Git-Tags; das separate letzte GitHub-Release-Objekt ist weiterhin `v1.0.0-product-selection`.
Tag und GitHub-Release-Objekt werden deshalb nicht gleichgesetzt.

Main-CI auf genau diesem Commit: [Backend](https://github.com/burckhju/trading-workspace/actions/runs/41171213873),
[Frontend](https://github.com/burckhju/trading-workspace/actions/runs/41171213875) und
[End-to-End](https://github.com/burckhju/trading-workspace/actions/runs/41171214040) erfolgreich.
Main wurde unmittelbar vor PR-Vorbereitung erneut abgefragt und war unverändert.

UX2-A erweitert die vorhandene Tradeverwaltung. UX2-B bis UX2-D werden hier vorbereitet,
aber nicht zusammen mit UX2-A implementiert. Die folgende Matrix beschreibt ausdrücklich
den Ausgangsstand; der implementierte A-Umfang und seine Testbelege folgen getrennt weiter unten.

Feature-Branch: `feat/ux2-a-trade-workspace-navigation`.

### Offene relevante PRs und parallele Arbeit

Die erste vollständige Live-Abfrage ergab fünf offene PRs. Während der Prüfung wurden
zusätzlich UX-1, die gemeinsame Koordination und der UX-3-Hinweisvertrag veröffentlicht.
Der ergänzte Parallelstand ist:

| PR | Head | Relevanz für UX2 |
| --- | --- | --- |
| [#220](https://github.com/burckhju/trading-workspace/pull/220) | `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Quellenforschung, nur Dokumentation; kein produktiver Providerqualitätsnachweis |
| [#207](https://github.com/burckhju/trading-workspace/pull/207) | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | Draft; veröffentlichter Diff nur Entwicklungsworkflow, beschriebene Regelimplementierung nicht enthalten |
| [#205](https://github.com/burckhju/trading-workspace/pull/205) | `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Alter Kursverlaufsentwurf, Draft mit Konflikt; #302/#306 sind bereits integriert |
| [#197](https://github.com/burckhju/trading-workspace/pull/197) | `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | Forschungsworkflow; kein produktiver Historienfeed |
| [#187](https://github.com/burckhju/trading-workspace/pull/187) | `bad00a420f56994216ad1def6a580b00b0f5772f` | Draft mit Konflikt; Hebeltrader-Eingaben/Regeln, u. a. TradePlanWorkflowPage, nicht TradeManagementPage |
| [#312](https://github.com/burckhju/trading-workspace/pull/312) | `8f67442daac6879d7dfb28416f2171f67aead0e5` | UX-1: Währungsvorschau, belegte Eingaben und Auswahlruns; gemeinsame Produktionsdateien TradeManagementPage und performanceReportContext, außerdem zwei Performance-Tests |
| [#313](https://github.com/burckhju/trading-workspace/pull/313) | `2312abfe8834a1b652b100fc635c4d36172d5c32` | Fünf neue Koordinationsdokumente, keine Dateischnittmenge; weist auf die bestehende öffentliche Feature-Importgrenze hin |
| [#314](https://github.com/burckhju/trading-workspace/pull/314) | `52a24266dce1ec048b23360b4b75d5b3f54d746b` | Zehn neue UX-3-Dokumentations-/Vertragsdateien, keine produktive Hinweisimplementierung und keine Dateischnittmenge |
| [#315](https://github.com/burckhju/trading-workspace/pull/315) | `d9d85f1af3159c4356c8773d076decbf1dc604e4` | UX-3-A: Hinweisvertrag und Backlog; RealizedGrossSources ist als späterer Pilot benannt, aktuell nur Dokumentation |
| [#316](https://github.com/burckhju/trading-workspace/pull/316) | `ae8c792f3e3ad74994894fac581cb4cf81ba5de7` | UX-4-A: Visualisierungsvertrag und Vorbereitung, keine produktive Chartänderung |

Die grünen alten PR-Läufe vom September qualifizieren keinen heutigen Testmerge. Keiner der
fünf älteren Diffs berührt TradeManagementPage. Beim ersten Abgleich aller 292 veröffentlichten
Branches war UX-1 noch nicht identifizierbar; der später erschienene tatsächliche Diff von #312
wurde deshalb erneut geprüft. Die eigene Umsetzung liegt in [#311](https://github.com/burckhju/trading-workspace/pull/311);
maßgebliche finale Heads, Testmerge und CI stehen dort, ohne selbstreferenzierende Commitangaben
in dieser Datei zu erzeugen.

Die Fortsetzung baut auf dem bereits veröffentlichten UX2-A-Head
`9c9c949c32f53eba7980cd8109bfa9f29e4d0bb5` auf. Alle fünf gemeinsamen
Koordinationsdokumente aus #313 wurden gelesen:
[Masterplan](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_MASTER_PLAN.md),
[Ownership](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_OWNERSHIP.md),
[Shared Contracts](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_SHARED_CONTRACTS.md),
[Dependencies](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_DEPENDENCIES.md)
und [Integration Status](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_INTEGRATION_STATUS.md).
UX2 bleibt Integrator für Navigation und Trade-Host, UX1 für Eingabe-/Vorschausemantik.
Die Koordinationsdateien bleiben im Master-PR; dieser Branch erzeugt keine zweite Fassung.
Die technische Zusammenarbeit setzt keinen vorherigen Merge des Dokumentations-PRs voraus.

## Navigations- und Komponentenmatrix des Ausgangsstands

Die Wechsel beziehen sich auf die angegebenen Wege, nicht auf eine pauschale Zahl aller
möglichen Klicks. Aufklappen oder Scrollen ist kein Seitenwechsel. Die Routerdefinition
steht in [`frontend/src/app/router.tsx`](../../frontend/src/app/router.tsx).

| Nutzerziel | Aktuelle Ansicht und Kontext | Erforderliche Wechsel im Ausgangsstand | Bestehende Komponenten / Datenquellen | Konsolidierung |
| --- | --- | --- | --- | --- |
| Position auswählen und zugehörigen Trade öffnen | `/workspace`, offene Positionen; serverseitiges `position.target` enthält `/trade-management?trade_id=…` | Auswahl in der Liste, ein Seitenwechsel zur Tradeverwaltung | `OperationalWorkspacePage`, `OpenPositionsPanel`, `PositionDetails`; `operationalWorkspaceApiClient.getPositions` | UX2-A: vorhandenen Einstieg nutzen, zentralen Trade-Kontext beibehalten; keine zweite Positionsliste |
| Eine konkrete Analyseversion nachvollziehen | `/market-analyses/:analysisId?version=N`; zusätzliche Kontextparameter `candidate_id`, `evaluation_id`, `overview_context` | Von einer Planquelle sind Analyse-ID und Versionsnummer bisher in Provenance sichtbar, aber nicht direkt verlinkt | `MarketAnalysisDetailPage`, `analysisSetupContext`; `TradePlanProvenance`, `candidate_evaluation.sources` | UX2-D: nur belegte `source_id`/`source_version` verlinken; nicht die neueste Analyse einsetzen |
| Aus einer bestimmten Kandidatenbewertung planen | `/candidates`, danach `/trade-plans?candidate_id=…&candidate_evaluation_id=…` | Ein bewusster Seitenwechsel mit gebundener Evaluation | `CandidatePage`, `TradePlanWorkflowPage`, bestehendes `TradePlanPage`, `TradePlanContentForm` | Bereits konsolidiert; Eingabeableitungen und Formularsemantik gehören UX-1 |
| Bestehenden Plan und historische Version öffnen | `/trade-plans/overview`, danach `/trade-plans?trade_plan_id=…&trade_plan_version_id=…` | Ein Wechsel aus der Planliste; die Tradeverwaltung zeigt bisher nur die Planreferenz und technische IDs | `TradePlanOverviewPage`, `ExistingTradePlanPage`, `TradePlanVersionContent`, `TradePlanProvenance`; `tradePlanApiClient.get/versions/version` | UX2-A: direkter Link zur am Trade gespeicherten Planversion; UX2-D: gemeinsame historische Quellennavigation |
| Produktauswahl für bestätigte Planversion bearbeiten | `/product-selection?trade_plan_id=…&trade_plan_version_id=…` | Ein Wechsel von der geöffneten Planversion; neuer Run wird nur ausdrücklich ausgelöst | `ProductSelectionWorkflowPage`, `ProductSelectionPage`, `loadSelectionPlanContext` | Bestehende Auswahl und historische Runs wiederverwenden; kein paralleler Produktworkflow |
| Einen konkreten historischen Auswahlrun lesen | `/product-selection?run_id=…`; Run liefert seine Plan- und Versionsbindung | Direkter Runlink aus Arbeitsbereich/Produktauswahl; vom Trade liegt keine direkte `run_id` vor | `ProductSelectionPage`, `productSelectionApiClient.get/listForTradePlanVersion` | UX2-D: vorhandene Quellenbeziehung auflösen, bevor ein Runlink ergänzt wird |
| Bestätigtes Instrument und tatsächlichen Erstkauf verfolgen | Produktauswahl zeigt bestätigte Selection, Kaufstatus und Link `/trade-management?trade_id=…` | Ein Seitenwechsel nach vorhandener, expliziter Kaufbuchung | `ProductSelectionPage`; `TradeResponse.product_selection_id`, `product_evaluation_id`, Produkt-ID | UX2-A: denselben Trade als Arbeitskontext übernehmen; Kauf- und Freigabelogik erhalten |
| Position und aktuellen Bewertungsstand prüfen | `/trade-management?trade_id=…`; `ProductValuationPanel` hängt im Routenexport hinter der Basisseite | Kein weiterer Seitenwechsel; bisher langes Scrollen zwischen Positionskopf und Bewertung | `TradeManagementContext`, `ProductValuationPanel`, `PositionValuationBasisDetails`; Trade-, Position-, Management- und Bewertungs-GETs | UX2-A: Bereichsnavigation; UX2-B: begründete Kennzahlen und Qualität zusammenführen, ohne neue Berechnung |
| Historische Kurse, Herkunft und Ausführungsmarken lesen | Positionsdetails im `/workspace` und Positionsabschnitt in `/trade-management` | Bereits ohne Seitenwechsel verfügbar; Öffnen beider Ansichten liest Historie erneut | `PositionPriceHistory`, `PositionPricePlot`, `PositionPriceHistoryEvidence`; `readPositionPriceHistory` | Bereits integriert; UX2-A: direkt adressierbarer Bereich; UX2-C: dieselbe Komponente beibehalten |
| Käufe, Nachkäufe und Verkäufe in ihrer Historie prüfen | `/trade-management?trade_id=…#execution-dates`, Tabs „Aktuelle Buchungen“ und „Historie“ | Kein Seitenwechsel, ein lokaler Tabwechsel zur Historie | `ExecutionDatesPanel` besitzt den Timeline-Read; `TradeTimelinePanel` erhält `entries` | Bereits konsolidiert; kein zusätzlicher Timeline-Owner und keine zweite Buchungshistorie |
| Nachkauf, Teilverkauf oder Vollverkauf dokumentieren | Bestehende Nachkaufsektion und `/trade-management?trade_id=…#sale-capture` | Kein weiterer Seitenwechsel; Formularwechsel innerhalb des Trades | `AdditionalPurchasePanel`, bestehendes Verkaufsformular, `ExecutionDateInput`, `ExecutionCurrencyOverride` | UX2-A: direkte Bereichslinks; keine Felder, Defaults oder Buchungsregeln verändern |
| Buchungsfehler korrigieren oder Trade stornieren | Buchungseditor in `#execution-dates`, `TradeCancellationPanel` am Seitenende | Kein Seitenwechsel; lokale Editoren mit bewusstem Verwerfen | `ExecutionDatesPanel`, `ExecutionCurrencySources`, `TradeCancellationPanel`, `TradePendingChangesProvider` | Navigation darf Editor und Recoveryzustand nicht unbemerkt verlieren; Storno bleibt vom Verkauf getrennt |
| Historische Ausführungswährung und Belege prüfen | Buchungen/Währungseditor; zusätzlich `/trade-management?trade_id=…&view=sources` | Im Buchungsbereich kein Seitenwechsel; zur lesenden Quellenansicht bislang neuer Tab | `ExecutionCurrencySources`, Währungsbestätigungs- und Evidence-Komponenten, `TradeSourcesView`; bestehende Currency-GETs | UX2-A: Quellen direkt erreichbar; UX2-C: vorhandene Nachweise präsentieren, keine neue Währungsauflösung |
| Positionsrisiken, Warnungen und Monitoring prüfen | Risiko-/Alertabschnitte in `/trade-management`; lesender Risikoabschnitt auch in `/workspace`-Details | Kein weiterer Seitenwechsel; bisher Scrollen | `PositionRiskPanel`, `TradeAlertsPanel`, `MonitoringRuntimePanel`; Risiko-, Alert-, Health- und Runtime-Reader | UX2-A: direkter Bereich; UX2-B: fachliche Hinweise, Kursqualität und operative Fehler weiterhin unterscheiden |
| Geschlossenen Trade wirtschaftlich auswerten | `/performance/closed-trades`; Quellenansicht enthält `ClosedTradeResult` | Ein Wechsel vom Bericht zur konkreten Tradequellenansicht; gültiger Berichtsrückweg schon vorhanden | `PerformanceWorkspace`, `ClosedTradesReportView`, `ClosedTradeResult`, `ClosedTradeSources`; `performanceApiClient` | UX2-A: vorhandenen Berichtskontext durch weitere Bereichswechsel erhalten; keine neue Ergebnisberechnung |
| Verkäufe einschließlich Teilverkäufen im Zeitraum vergleichen | `/performance/realized-gross`; gemeinsamer Filterowner mit Abschlussbericht | Berichtstypwechsel übernimmt gültige Auswahl, liest aber den fachlich anderen Bericht | `PerformanceWorkspace`, `PerformanceFilters`, `RealizedGrossReportView` | Bereits konsolidiert; kein zweiter Performancebereich und keine Vermischung beider Berichtstypen |
| Ursprünglichen Plan, Ausführungen, Review und Journal lesen | `/trade-management?trade_id=…&view=sources`, optional `review_version_id`, `journal_version_id` | Tradeverwaltung öffnet bislang neuen Tab; Rückweg trägt nur `trade_id` | `TradeSourcesView`, `ReadSection`, bestehender Source-Reader; `ClosedTradeResult` als separater wirtschaftlicher Owner | UX2-A: gemeinsame Navigation, bestehende Pins und Berichtskontext bewahren; historische Quellen bleiben lesend |
| Nachbeobachtung, Review und Journal bearbeiten | `/post-trade?trade_id=…`, optional `journal_version_id=…` | Von geschlossenem Trade über „Nachbeobachtung starten“ bzw. Arbeitsbereich; keine gleichwertige durchgängige Bereichsnavigation | `PostTradeLearningPage`, `PostTradeReviewPage`, `TradeJournalPanel`, `useTradeJournal` | UX2-A: direkt erreichbarer vorhandener Owner mit Trade-Rückweg; kein implizites Starten, Finalisieren oder Materialisieren |
| Frühere Evidence und zugehörige Lessons prüfen | Post-Trade enthält `Ft011EvidenceHistory`; Quellenansicht zeigt Evidence- und Lessonversionen | Ein Wechsel zur Lesson; Original-Trade fehlt im bisherigen allgemeinen Rücklink | `Ft011EvidenceHistory`, `TradeSourcesView`, `lessonReadbackClient`, `LessonDraftFromEvidence` | UX2-A: Trade-Rückkontext mitführen; bestehende historische `lesson_version_id` erhalten |
| Lessonversion, Reviewentscheidung und Herkunft lesen | `/lessons/:lessonId?lesson_version_id=…#lesson-history` | Bisheriger Rücklink `/post-trade` erfordert neue Tradeauswahl; belegte Journalquelle hat bereits einen exakten Direktlink | `LessonDetailPage`, `LessonReviewPanel`, `JournalEvidenceOrigin`, `LessonHypothesisPanel` | UX2-A: qualifizierter Rückweg zum mitgegebenen Trade; Governance und Quellenauflösung unverändert |

## Bereits integrierte Konsolidierungen

Diese Funktionen sind im geprüften Main vorhanden und werden nicht neu implementiert:

| Integration | Nachweis im Main | Vorhandene Zuständigkeit |
| --- | --- | --- |
| TradePlan und Produktauswahl, PR #284 | Merge `059860ea` | Exakte Planversion, historische freigegebene Version trotz neuerem Entwurf, Quellen- und Kontextprüfung, vorhandene Formulare |
| Trade und Buchungen, PR #287 | Merge `36db3910` | Ein Buchungsowner für aktuelle Einträge, Korrekturen und Timeline; koordinierte Schreibsperren und Navigationsschutz |
| Journal, PR #289 | Merge `38cac1a0` | Post-Trade, Journal, Evidence und Lessonübergabe teilen fachlich getrennte, koordinierte Bearbeitungen |
| Performance, PR #290 | Merge `ca4258fd` | Gemeinsame Filter und URL-Zuständigkeit für zwei fachlich unterschiedliche Berichtstypen |
| Historische Währungsherkunft, PR #298 | Merge `271d2abb` | Ausführungsgebundene Nachweise, explizite Bestätigungen, nachvollziehbare Quellen und Konflikte |
| Positionskursverlauf, PR #302 | Merge `e8703a65` | Persistierte Beobachtungen, Quelle, Preisart, Währung, tatsächliche Kurszeit und qualifizierte Ausführungsmarker |
| Ergänzung Positionskursverlauf, PR #306 | Merge `2534d7c5` | Verfügbare Zeiträume, Abdeckungsgrenzen und weitere belegte Historien-/Darstellungsfälle |

## Bestehende Kontext- und Ladegrenzen

### Trade und Position

`TradeManagementPage` verwendet `trade_id` als Identität und keyed den gesamten
`TradePendingChangesProvider` danach. Trade, Position und Management werden parallel gelesen;
das Produkt wird anschließend nach der gelesenen Produkt-ID aufgelöst. Die Antworten werden
auf Trade-, Produkt- und Positionszugehörigkeit geprüft. Generation und AbortController
verhindern, dass ein überholter Read eine neuere Projektion ersetzt. Fachliche Schreibaktionen
verwenden den bestehenden synchronen Schreibschutz und Readback.

`ExecutionDatesPanel` besitzt einen einzelnen Timeline-Read für aktuelle Buchungen, Historie
und Bearbeitungsgrundlage. `TradeTimelinePanel` ist eine reine Darstellung dieser `entries`.
Ein Bereichswechsel darf keinen neuen Timelineowner und keinen zusätzlichen GET auslösen.

`ProductValuationPanel` wird im ursprünglichen `trade/pages/index.ts` separat angehängt. Es liest
die Position erneut, obwohl die Basisseite sie bereits besitzt, und liest danach die Bewertung.
Das ist eine konkrete verbleibende Doppelladung. Im Ausgangsstand ist es außerdem nicht nach
Trade-ID keyed und erscheint auch im Quellenmodus. Eine zukünftige Zusammenführung muss seine
Read-Lebensdauer, Timeline-Invalidierung und Unterscheidung aktueller Bewertung versus
historischem Ergebnis ausdrücklich erhalten. UX2-A darf einen bestehenden Bewertungstext
nicht als atomaren gemeinsamen Datenstand mit anderen Abschnitten ausgeben.

### Quellen, Plan und Analyse

`TradeSourcesView` liest zunächst den Tradequellenkern und danach Plan, Reviews, Journal und
Evidence in eigenen `ReadSection`-Lesefenstern. Ein Fehler in Journalquellen ist kein Fehler des
wirtschaftlichen Ergebnisses. `ClosedTradeResult` bleibt der Owner qualifizierter finanzieller
Ergebnisse. Die getrennten Lesefenster werden bereits sichtbar erklärt; ein globaler Cache
oder ein künstlich gemeinsamer Snapshot wäre eine zusätzliche fachliche Änderung.

Ein Quellenbesuch ist durch `location.key` und `location.search` isoliert. Historische Pinwechsel
lesen die Quellen neu. Das ist beim geprüften Ausgangsstand beabsichtigt und darf nicht durch
ungeprüfte Wiederverwendung einer anderen Version ersetzt werden. Hashnavigation innerhalb
unveränderter URL-Parameter benötigt dagegen keinen neuen fachlichen Read.

`ExistingTradePlanPage` lädt Plan, Versionsliste und gegebenenfalls exakt angeforderte Version.
Eine fehlende oder fremde explizite Version führt zu einer Fehlermeldung und nicht zu `latest`.
Aktuelle Basiswertnamen sind nur optionale Anzeige. Planinhalt und Kandidatenbewertung bleiben
an der historischen Version gebunden.

`TradeResponse.product_selection_id` bezeichnet eine bestätigte Selection, **nicht** ihren Run.
`/product-selection?run_id=…` benötigt die tatsächliche `selection.run_id`. Der bestehende
`SqlAlchemyWorkspaceSelectionResolver` prüft Selection, Evaluation, Produkt, Plan und Version;
`source_view.plan` nutzt ihn bereits. UX2 darf `product_selection_id` nicht als `run_id` ausgeben.
Ebenso liegen Analysequellen in `candidate_evaluation.sources`; eine beliebige aktuelle Analyse
des gleichen Basiswerts ist kein Ersatz für den dokumentierten Quellstand.

### Post-Trade und Lessons

`PostTradeLearningPage` liest Trade/Produkt erneut für seinen Kontextkopf. Review, Journal,
Materialisierungsstatus, frühere Evidence und Lessonreferenzen haben getrennte Reader und
explizite Invalidierungen. Diese Antworten haben unterschiedliche fachliche Bedeutungen.
Ein vorhandener Journalentwurf beweist weder Finalisierung noch Lessonfreigabe.

`LessonDetailPage` wahrt die konkrete Lessonversion, aber der ursprüngliche allgemeine
Rücklink `/post-trade` verliert den Trade. Lessonlinks aus Post-Trade und Tradequellen geben
bisher lediglich Lesson- und gegebenenfalls Lessonversions-ID weiter. `JournalEvidenceOrigin`
besitzt dagegen schon einen fachlich geprüften Direktlink zur exakt materialisierten
Journalversion mit passender Trade-ID.

### Berichtskontext

`closedReportContext.ts` definiert eine begrenzte Liste erlaubter Navigationsparameter:
`report_context`, `from_date`, `to_date`, `report_currency`, `report_timezone`, `report_view`,
`report_page`, `report_basis`. Sie sind Navigationskontext und kein übergebener Geldbetrag.
`sourceLink` bewahrt diese Werte auch in einem ungültigen Zustand, damit mehrdeutige Links
nicht stillschweigend repariert werden. Der ursprüngliche Rücklink zur Tradeverwaltung
reduziert dagegen auf `trade_id` und verliert diesen Kontext.

## UX2-A: implementierter, separat prüfbarer Umfang

1. Gemeinsame, responsive Bereichsnavigation in der bestehenden Tradeverwaltung und ihren
   vorhandenen Quellen-/Post-Tradeansichten; sichtbare Tradeidentität aus dem tatsächlichen Kontext.
2. Hashlinks zu den bereits vorhandenen Tradeabschnitten. Bestehende `#sale-capture` und
   `#execution-dates` bleiben gültig. Formularowner und Eingaben bleiben beim Bereichswechsel
   gemountet; Hashnavigation löst keinen neuen Trade- oder Timeline-Read aus.
3. Direkte Links zur gespeicherten Planversion und zu bestehenden Review-, Journal- und
   Quellenfunktionen. Ein Link liest oder navigiert; er startet keine Nachbeobachtung und
   finalisiert oder materialisiert nichts.
4. Trade-ID, historische Pins und begrenzten Berichtskontext beim Wechsel und Rückweg erhalten.
   Zielrouten und Parameternamen bleiben explizit; kein ungeprüftes freies `returnTo`.
5. Kontextbezogener Lesson-Rückweg, ohne Lessonversion, Evidenzbindung oder menschliche
   Reviewentscheidung umzudeuten.
6. Lade-, Fehler- und Leerzustände verständlich halten. Fehlende Position oder unbekannte
   Quelle ergibt weder einen Bestand von null noch einen vermeintlich abgeschlossenen Schritt.

Die Navigation verwendet native Links mit sichtbarem Tastaturfokus. Hashziele sind
nach dem Laden fokussierbar. Ein Nachladen darf den Tastaturfokus nicht wiederholt aus
einem aktiven Eingabefeld ziehen. Eine einfache Bereichsnavigation braucht keine zusätzlichen
Tabrollen; die vorhandenen echten Buchungstabs behalten ihre Pfeiltastensteuerung.

Die neue `TradeWorkspaceNavigation` und ihre Linkfunktionen liegen hinter der öffentlichen
Schnittstelle `frontend/src/shared/trade-workspace-navigation`. Das gemeinsame Modul enthält
ausschließlich Darstellung und reine URL-Verträge; es importiert keine internen Features.
Die vorhandenen URL-Schlüssel, Berichtsauswahlfilter und Navigationsfunktionen werden genau
einmal ausgegliedert. Die bisherigen Ownerimporte bleiben über kompatible Exporte gültig.
`sourceQueryError`, `verifyClosedReport`, `verifyClosedStatistics`, `verifyRealizedReport`, API-Reader und Finanzlogik
verbleiben bei ihren Fachownern. Die Ausgliederung ändert keine Filter- oder Quellenprüfung.
Damit wird die bereits in `FRONTEND_ARCHITECTURE.md` festgelegte Featuregrenze eingehalten;
der während der Prüfung erschienene Koordinations-Draft #313 hat diesen Integrationspunkt
konkret benannt. Dies ist ein eigener, kontrollierter Architekturcommit.

Erlaubte bestehende Suchparameter bleiben innerhalb eines
Owners bytegenau erhalten; unbekannte Parameter wie `returnTo` oder Geldwerte werden nicht in
erzeugte Links übernommen. Die Quellenansicht wird nur nach `location.search` gekeyt, sodass
ein Hashwechsel keine Quellen neu lädt. Historische Pinwechsel bleiben neue Lesekontexte.

Der vorhandene Routenexport keyed die aktuelle Produktbewertung nun nach Trade-ID und hängt
sie nicht mehr an die historische Quellenansicht an. Die doppelte Positionsabfrage innerhalb
der aktiven Tradeverwaltung bleibt eine ausdrücklich noch offene UX2-B-Aufgabe.
Der genaue Planlink öffnet die belegte Planversion im selben Tab. Die Plan-URL führt Trade,
Quellenpins und Berichtskontext mit; der neue Rücklink öffnet die ursprünglichen Tradequellen
auch nach Kopieren oder Reload. Der vorhandene Plan-Guard schützt Entwürfe und laufende Writes.
Es wird kein Produkt-Run und keine Analyseversion erraten.

Lessonlinks und kopierbare Lessonversionslinks führen den Rückkontext mit. Beim bewussten
Tradewechsel in Tradeverwaltung und Post-Trade werden beide alten Review-/Journal-Pins entfernt;
die ursprüngliche Berichtsauswahl bleibt erhalten. Ein erneutes Laden desselben Trades erhält
seine Pins und offenen Eingaben. Die optionale `lessonHref`-/`versionHref`-Anbindung ändert nur
Links, keine Felder, Quellenbindung, Reviewentscheidung oder Speicheraktion.

### Ergänzung des Implementierungsauftrags UX2-A

- `tradeLookupQuery` ist der einzige reine URL-Vertrag für eine bewusst neu eingegebene Trade-ID.
  Er erhält den Berichtskontext einschließlich ungültiger Duplikate und entfernt alte Tradepins.
  Same-Trade-Reload und bestehende Dirty-/Busy-/Generation-Guards bleiben unverändert.
- `tradePlanLink` und `planTradeReturnLink` ergänzen den gebundenen Plan-Rundweg. Eine explizit
  fehlende historische Planversion wird weiterhin nicht durch die neueste Version ersetzt.
- `realizedReportNavigation` enthält einmalig die bereits vorhandenen reinen SELL-URL-Verträge;
  `performanceReportContext` exportiert sie kompatibel. `reportReturnLink` unterscheidet die
  ursprüngliche Abschlussauswahl und Verkaufsauswahl. SELL-Seiten bis 1000 und das bestehende
  Abschlusslimit von 100 bleiben getrennt; beide Parser behalten ihre bisherige Validierung.
- Links aus `RealizedGrossReportView` übernehmen Filter und Basis der tatsächlich dargestellten
  Antwort sowie sichtbare Ansicht und Seite. Der Link führt zum bestehenden Buchungsbereich.
  Die Quellenansicht löst mit SELL-Herkunft keine Abschlussberichtsabfrage aus und deutet
  einzelne Verkäufe nicht als wirtschaftliches Gesamtergebnis des Trades um.
- Ein mitgeführter `review_version_id` ist beim aktuellen Post-Trade-Editor ausdrücklich als
  historischer Quellenverweis erkennbar. Der direkte Link fokussiert die exakte historische
  Reviewquelle. Der bestehende Editor bearbeitet weiterhin seinen aktuellen Reviewstand.

Diese Ergänzung ändert weder Formulare noch fachliche Speicher-, Freigabe- oder Rechenregeln.

### Konkreter Nutzen gegenüber dem Ausgangsstand

| Nutzerweg | Nachgewiesene Änderung |
| --- | --- |
| Überblick → Kurs → Buchungen → Risiko | Vier direkt fokussierbare Ziele im selben Trade; kein zusätzlicher API-Read, beide offenen Verkaufs-/Korrekturentwürfe bleiben erhalten |
| Trade → Quellen | Kein zwingender neuer Browser-Tab mehr; normaler Router-Link mit bestehendem Eingabenschutz |
| Quellen → Trade → Quellen | Trade, Review-/Journal-Pins und typgerechter Berichtskontext bleiben erhalten; vorher gingen Pins und Berichtsrückweg beim ersten Rücksprung verloren |
| Post-Trade/Quellen → historische Lesson → zurück | Eine erneute Tradeauswahl entfällt; Lessonversion sowie ursprünglicher Quellen-/Journalbereich bleiben adressierbar, auch nach Reload |
| Quellen → gebundene Planversion → Quellen | Exakte Plan-/Versions-ID im selben Tab; Rückweg aus der URL statt Planliste, Browserhistorie oder erneuter Tradeauswahl |
| Verkaufsauswahl → Buchungen → Quellen → Verkaufsauswahl | Ursprüngliche Filter, Ansicht und Seite bleiben erreichbar; keine erneute Filtereingabe und kein Wechsel zum fachlich anderen Abschlussbericht |
| Manueller Wechsel von Trade A zu B | Berichtsrückweg bleibt erhalten; die historischen Pins von A werden nicht auf B angewandt |
| Historische Quellen lesen | Die dort bisher zusätzlich angehängte aktuelle Produktbewertung und ihre Reads entfallen |

Bereits vorhandene Chart-, Buchungs-, Journal- und Performancekonsolidierungen werden nicht
als neue UX2-A-Leistung gezählt. Plan, Journal und Lessons behalten ihre bestehenden Owner;
UX2-A behauptet deshalb nicht, alle fachlichen Bearbeitungen auf eine einzige Route zu verlegen.

## Schutz ungespeicherter Änderungen

`PendingNavigationGuard` schützt Änderungen von Pfad oder Suchparametern und native
Seitenentladung. Reine Hashwechsel sind bereits ausgenommen. Das ist sicher, solange die
betroffenen Formulare beim Hashwechsel gemountet bleiben. `TradePendingChangesProvider`
koordiniert Buchungseditor, Verkaufs-, Management-, Nachkauf- und Stornozustände.

Post-Trade koordiniert seine Review-, Journal-, Lesson- und Materialisierungszustände mit dem
bestehenden Guard. `LessonDetailPage` koordiniert Lessonreview und Hypothesenentwurf. UX2-A
benutzt diese Mechanismen und führt weder eine weitere Draftablage noch eine automatische
Verwerfentscheidung ein. Ein bestätigtes Verwerfen ist eine bewusste Nutzerentscheidung;
ein Reload verspricht keine dauerhafte Wiederherstellung ungespeicherter Texte.

## UX2-B bis UX2-D: fachliche Vorbereitung, nicht implementiert

### UX2-B – Überblick

- Bestehende Trade-/Produktidentität, Positionsstatus und nächste mögliche Aktion zusammen
  mit belegter Kursqualität präsentieren. Werte kommen aus bestehenden Antworten.
- `ProductValuationPanel` und `PositionValuationBasisDetails` weiterverwenden. Die doppelte
  Positionsabfrage erst nach einer gezielten Zuständigkeits- und Invalidierungsprüfung reduzieren.
- Verfügbarkeit und Währung jedes Geldwerts mitführen. Unbekannt, nicht berechenbar und null
  bleiben verschieden; Buchungsprojektion, qualifizierter Bericht und aktuelle Bewertung nicht
  als gleichwertige Ergebnisse darstellen.
- `TradeAlertsPanel`, `PositionRiskPanel` und `MonitoringRuntimePanel` behalten ihre getrennten
  Bedeutungen: fachliche Meldung, Risikobeurteilung, operativer Daten-/Providerzustand.
- Gemeinsame Terminologie vorbereiten: „Ausführung“, „Planversion“, „Kostenbasis“,
  „Realisierter Bruttobeitrag“, „Nicht berechenbar“, „Quelle ungeklärt“, „Fachliche Prüfung“.
  Eine Umbenennung ersetzt keine fachliche Qualifikation.

### UX2-C – Kursverlauf und Buchungen

- Vorhandene `PositionPriceHistory` samt Plot und Evidence bleibt die einzige Kurskomponente.
  Im Plot sind Linien ausdrücklich deaktiviert; zwischen Beobachtungen ist keine Entwicklung
  belegt. Währungen, Provider und Preisarten bleiben getrennt.
- Nur vom bestehenden Report als `plottable` qualifizierte, zeitlich zuordenbare Kauf-/Verkaufs-
  events in passender Währung markieren. Ein Buchungsdatum ohne Uhrzeit ist kein erfundener
  Intradaykurs.
- `ExecutionDatesPanel` und sein Timelineowner bleiben erhalten. Währungserklärung,
  historischer Beleg und Mengen-/Preiskorrektur behalten getrennte Bedienvorgänge.
- Eine Vermögens-, Einstands- oder Gewinnkurve ist durch die vorhandenen einzelnen Markt-
  und Ausführungskurse nicht automatisch belegt. Ohne fachlich qualifizierte Zeitreihe wird
  keine zusätzliche Positionsentwicklungskurve erzeugt.

### UX2-D – Plan, Journal und Lessons

- Exakte Planversion, Kandidatenevaluation und deren konkrete Analysequellen verknüpfen.
  Fehlende oder widersprüchliche Referenzen verständlich kennzeichnen.
- Historischen Auswahlrun erst nach belegter Selection-zu-Run-Zuordnung verlinken.
- Vorhandene Quellenansicht, `TradeJournalPanel`, `Ft011EvidenceHistory`, `JournalEvidenceOrigin`
  und `LessonReviewPanel` nutzen. Historische Journal-/Reviewpins und Lessonversions-IDs bewahren.
- Eine kompakte Lebenszyklusanzeige kann tatsächliche Quellen referenzieren. Jeder Schritt
  erhält seinen eigenen belegten Status; ein späterer Datensatz beweist keine Freigabe oder
  Fertigstellung eines früheren Schritts. Ein externer Trade darf ohne Plan existieren.

## Abgrenzung und Integrationskonflikte mit UX-1

UX-1 wurde nach Veröffentlichung von #312 am tatsächlichen Head
`8f67442daac6879d7dfb28416f2171f67aead0e5` geprüft. Die gemeinsame Ausgangsbasis ist exakt
`1883f7f330719453958f8be1dd51d48db816662e`. Die Fortsetzung berührt vier gemeinsame Dateien:
`TradeManagementPage.tsx`, `performanceReportContext.ts`, `RealizedGrossPage.test.tsx` und
`PerformanceWorkspace.test.tsx`. Ein rein rechnerischer
Dreiwegevergleich verändert weder Branch-Referenzen noch Main und ersetzt keine gemeinsame CI.

UX-1 ersetzt dort die Währungseingabe durch `ExecutionCurrencyPreview` und bindet den bestehenden
`historyReloadToken` an Nachkauf- und Verkaufsvorschau. UX2 ergänzt Navigation und Bereichsanker.
Bei Integration sind beide Änderungen zu erhalten, statt die gesamte Datei eines Branches
zu übernehmen. Der UX-1-Readkey enthält keinen URL-Hash; Navigationswechsel dürfen daher keine
zusätzliche Währungsvorschau oder Formularänderung auslösen. Die gemeinsame lokale Qualifikation
und ihre genauen Heads werden im PR nachgehalten. Eine gemeinsame reale PostgreSQL-/GitHub-
Qualifikation bleibt vor späterer Integration auf dem dann aktuellen Main erforderlich.

Im Performance-Service extrahiert UX1 `reportTimezoneError` und nutzt diesen Helper sowohl
für Filterprüfung als auch Browserzeitzonenvorschlag. Beim späteren Kombinieren bleibt der reine
URL-/Filtervertrag genau einmal in `shared`; die Browserableitung in `initialPerformanceFilters`
bleibt im Feature. Der Helper darf keine zweite Parserkopie oder einen Shared-Import aus dem
Feature erzeugen. Die zwei gemeinsamen Testdateien müssen sowohl UX1-Zeitzonenfälle als auch
UX2-Rücklinkassertionen behalten.

`RealizedGrossSources.tsx` ist der geplante UX3-Pilot aus #314/#315. Der UX2-Diff ergänzt dort
nur den typisierten Berichtskontext und den bestehenden Buchungslink; Hinweisstruktur und
Statussemantik bleiben beim UX3-Vertrag. UX4s bestehende Kurskomponenten und Markerlogik
werden in dieser Fortsetzung nicht verändert.

UX2-A beschränkt gemeinsame Dateien auf Navigation, Bereichsanker und Darstellung. Besonders
`TradeManagementPage.tsx` ist als gemeinsame Integrationsstelle zu behandeln: Navigation und
Anker sollen in kleinen, getrennten Hunks bleiben. `AdditionalPurchasePanel`,
`ExecutionDatesPanel`, `ExecutionCurrencyOverride`, `TradePlanContentForm` und Kauf-/Verkaufs-
ableitungen werden von UX2 nicht semantisch umgebaut. Kein Feature-Branch wird ungeprüft in
den anderen übernommen. Die gemeinsame Regression erfolgt später auf dem dann aktuellen Main.

## Reproduzierbare Prüfwege und vorhandene Regressionen

| Prüfweg | Erwarteter Nachweis | Bereits vorhandene Regressionen / geplante Ergänzung |
| --- | --- | --- |
| Trade A aus Arbeitsbereich öffnen, zu Kursen und Buchungen wechseln | Gleiche `trade_id`, passende Identität, kein zweiter Trade-/Timeline-Read | `TradeManagementContext.test.tsx`, `trade-management-context.spec.ts`; ergänzt durch `TradeWorkspaceNavigation.test.tsx` und `trade-workspace-navigation.spec.ts` |
| Direkten Buchungs-/Verkaufslink kopieren und neu öffnen | Gültiger Kontext wird aus URL geladen, Ziel erhält Fokus | `TradeManagementPage.test.tsx`, `trade-execution-dates.spec.ts`; neue Anker und Reload in `trade-workspace-navigation.spec.ts` |
| Verkaufsmenge oder Korrekturentwurf eingeben und Hashbereich wechseln | Eingabe bleibt erhalten; kein Verwerfendialog für bloßes Scrollen | `TradeManagementContext.test.tsx`, `trade-execution-consolidation.spec.ts` |
| Mit ungespeicherten Daten zu Quellen, Plan, Post-Trade oder anderem Trade wechseln | Bestehender Guard; „Hier bleiben“ erhält Eingaben; während Schreiben kein Verwerfen | `TradeManagementContext.test.tsx`, `trade-capture-safety.spec.ts`; neue Links und nativer Reloadschutz in `trade-workspace-navigation.spec.ts` |
| A → B → A mit verspäteter A-Antwort | Alter Besuch überschreibt keine neue Identität oder Eingaben | `TradeManagementContext.test.tsx`, Plan-/Post-Trade-/Lesson-Kontexttests |
| Fehlende Position, nicht vorhandener Trade oder stornierter Trade öffnen | Verständlicher Lade-/Fehler-/Leerzustand, keine alten Daten und keine erfundenen Schreibaktionen | Bestehende Trade-Kontexttests; ergänzte Navigationsfälle für fehlende Position sowie geschlossen/storniert |
| Geschlossenen Trade öffnen | Keine neue Verkaufsfreigabe; vorhandenes Post-Trade/Quellenziel erreichbar | `TradeManagementPage.test.tsx`, `PostTradeLearningPage.integration.test.tsx` |
| Trade mit historischer Planversion öffnen, obwohl neuer Entwurf existiert | Exakt gespeicherte Version; kein Wechsel auf `latest` | `ExistingTradePlanPage.test.tsx`, `TradePlanPage.deep-link.test.tsx`, `ft007-plan-context-postgres.spec.ts` |
| Abschlussliste → Quellen → Bereich → Quellen → Bericht | Filter, Seite und historische Pins bleiben erhalten; veränderter Bericht wird erneut qualifiziert | `ClosedTradeSourceJourney.test.tsx`, `ClosedTradeResult.test.tsx`, `workspaceNavigation.test.ts`, realer Quellen-Rundweg in `trade_source_journey.ts` |
| Journal/Review → historische Lesson → Rückweg | Original-Trade und konkrete Quellpins bleiben erhalten | Erweiterte `LessonDetailPage.governance.test.tsx`, `lesson-detail-consolidation.spec.ts` sowie Quellen-/Journal-E2E |
| Navigation per Tastatur und schmalem Viewport | Sichtbarer Fokus, erreichbare Links, kein Layoutüberlauf; bestehende Buchungstabs weiterhin bedienbar | Fokussierter neuer Playwright-Nutzerweg sowie bestehende mobile UI-Tests |
| Buchungs-/Finanzregression | Bestehende Mengen-, Storno-, Average-Cost-, Währungs- und Berichtsregeln bleiben erfolgreich | Backend-Suiten für Trade/Position, historische Währung und Performance; bestehende E2E-Nutzerwege |

## Bereits vorliegende Verifikation bis zum Fortsetzungsstand

Die folgende vorhandene Dokumentation bezieht sich auf den Stand bis `9c9c949c`,
nicht automatisch auf die nachfolgenden Änderungen. Damals lokal erfolgreich am 31.10.2026:

- Node **22.16.0** entsprechend `frontend/.nvmrc`: TypeScript, ESLint (0 Warnungen), Prettier
  und Produktionsbuild erfolgreich. Vite meldet weiterhin den bestehenden großen Hauptchunk;
  die Grenze wurde nicht verändert.
- Vollständiges Frontend-Coverage-Gate: **1.861 Tests in 160 Dateien** erfolgreich.
  Statements/Lines **95,84 %**, Branches **90,25 %**, Functions **91,07 %**;
  unveränderte Mindestwerte **80/80/80/70** bestanden.
- Python **3.12**: **558 Backend-Tests** aus `trade_position` und `performance` erfolgreich.
  Eine vorhandene Starlette/AnyIO-DeprecationWarning; kein lokaler vollständiger PostgreSQL-
  oder 85-%-Backend-Coverage-Nachweis behauptet.
- Chromium: **8 neue UX2-Navigationsfälle** und **2 bestehende Buchungs-UI-Fälle** erfolgreich.
  390 px und 1280 px, Tab/Enter, sichtbarer Fokus, zwei gleichzeitige Entwürfe, konstante
  GET-Zahl, native Reloadwarnung, direkte/alte Anker, fehlende Position, geschlossen und storniert.
  Die API-Fixtures blockieren alle Writes; diese Fälle ersetzen keine PostgreSQL-Owner-Suite.
- Unabhängiges Review und `git diff --check` erfolgreich. Ein gefundener fremder Review-Pin
  nach Tradewechsel wurde behoben und mit einer eigenen Regression abgesichert.
- Nach Ausgliederung der öffentlichen Navigationsschnittstelle erneut erfolgreich:
  vollständiges Frontend-Coverage-Gate mit denselben 1.861 Tests und Coveragewerten,
  TypeScript/ESLint/Prettier/Build sowie **13 Chromium-Fälle** (acht Navigation, fünf Handoff).
  Ein unabhängiger strukturierter Vergleich bestätigt **35 unveränderte Deklarationen**,
  einschließlich Finanz-/Quellenvalidatoren, URL-Parsern und Navigationskomponente.

### Erneute Qualifikation der UX2-A-Fortsetzung

Auf dem vollständigen fortgesetzten Arbeitsstand am 31.10.2026 erneut ausgeführt:

- Node **22.16.0**: TypeScript, ESLint mit null Warnungen, Prettier und Produktionsbuild erfolgreich.
  Die bestehende Vite-Hauptchunkwarnung bleibt sichtbar; keine Änderung an der Chunkgrenze.
- **1.913 Tests in 161 Dateien**, unverändertes vollständiges Frontend-Coverage-Gate bestanden:
  Statements/Lines **95,85 %**, Branches **90,27 %**, Functions **91,11 %**.
- **10 Chromium-Navigationsfälle** gemeinsam erfolgreich, einschließlich der acht bisherigen
  Fälle und zwei neuer Rundwege bei 1280/390 px. Die historische Planversion bleibt trotz
  neuerem Entwurf nach kopiertem Direktlink und Reload exakt ausgewählt. Verkaufsbericht,
  konkrete Buchungsquelle und ursprüngliche Auswahl bleiben im selben Kontext.
- Ergänzte Komponentenregressionen belegen Same-Trade-Reload, bewussten Tradewechsel mit
  Berichtserhalt, Entfernen fremder Pins, Plan-Dirty-/Busy-Schutz und ausgeblendete verspätete
  Abschlussantworten nach Wechsel zum Verkaufskontext. Ungültige Duplikate bleiben ungültig.
- Unabhängiges Delta-Review: keine neue Produktabweichung gefunden. Der strukturierte Vergleich
  bestätigt 17 unveränderte bestehende Deklarationen: 14 reine URL-/Filterdeklarationen wurden
  verschoben, Finanzdefinition, Browserfilterinitialisierung und Finanzvalidator blieben im Feature.

Die Browserregressionen verwenden abgefangene synthetische Reads und blockieren Writes.
Die aktuelle unveränderte GitHub-CI einschließlich PostgreSQL-Owner-Jobs wird für den
tatsächlich veröffentlichten Fortsetzungs-Head im Draft-PR nachgehalten. Die älteren grünen
Läufe oben sind kein Ersatz für diese Prüfung. Backendtests wurden lokal in dieser Fortsetzung
nicht erneut ausgeführt; Backend- und fachliche Schreibimplementierungen sind unverändert.

Die vorinstallierte Node-24-Laufzeit verursachte `AbortSignal`-Fehler auch auf einem separat
geprüften, unveränderten Main. Die Tests wurden mit der festgeschriebenen Node-22-Laufzeit
vollständig wiederholt; keine Tests oder Qualitätsgrenzen wurden dafür geändert/deaktiviert.

Reproduzierbare Befehle mit der Projektlaufzeit:

```bash
cd frontend
npm ci
npm run typecheck
npm run lint
npm run format
npm run test:coverage -- --coverage.thresholds.lines=80 --coverage.thresholds.functions=80 --coverage.thresholds.statements=80 --coverage.thresholds.branches=70
npm run build
npm run e2e -- trade-workspace-navigation.spec.ts
cd ..
python -m pytest -c backend/pyproject.toml tests/unit/backend/features/trade_position tests/unit/backend/features/performance -q
```

Die lokale Browserprüfung benötigt den Frontend-Testserver und synthetische API-Fixtures.
Die unveränderte GitHub-CI ergänzt PostgreSQL-, Backend-Coverage-, Smoke- und Owner-Jobs.
PR-Head, Testmerge und konkrete CI-URLs werden im zugehörigen Draft-PR dokumentiert, damit
eine reine Aktualisierung von Laufnummern keine neue ungeprüfte Codeversion erzeugt.

| Stufe | Status dieser Dokumentfassung |
| --- | --- |
| UX2-A implementiert | Ja, Navigation und Rückkontext; B-D bleiben Vorbereitung |
| Lokal getestet | Ja, oben aufgeführte erfolgreiche Läufe |
| PR-geprüft | Maßgeblich sind tatsächlicher PR-Head/Testmerge und die im Draft-PR nachgehaltene CI |
| In Main integriert | Nicht beauftragt |
| Veröffentlicht | Nicht beauftragt |
| Auf dem PC installiert | Nicht beauftragt |
| Fachlich abgenommen | Nicht behauptet |

Der UX2-A-PR soll abschließend konkret belegen, welche vorher notwendigen erneuten
Tradeauswahlen oder Rückwege entfallen und welche reinen Hashwechsel ohne neue Datenabfrage
auskommen. Bereits vorhandene gemeinsame Ansichten und bereits entfallene Wechsel aus früheren
PRs zählen nicht als neuer UX2-A-Erfolg.
