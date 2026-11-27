# Alt-PR-Konsolidierung — belegter Main-Abgleich vom 27.11.2026

## Auftrag, Nachweisgrenze und Ergebnis

Geprüfte Repositorybasis ist
[`eb7f89a30a1772f2c140c5a11cdfb0284d80fc3c`](https://github.com/burckhju/trading-workspace/commit/eb7f89a30a1772f2c140c5a11cdfb0284d80fc3c),
Tree `e96fd709a6525a9e7092a542570f94ff1614c7a3`. Der Live-Abgleich begann am
27.11.2026 um 23:25 Uhr Europe/Berlin. Ein vollständiger Git-Clone, alle neun
offenen PRs einschließlich Drafts, ihre vollständigen eigenen Diffs, aktuelle
Main-Dateien, Fachverträge, konkrete Testassertionen und GitHub-Run-/Jobdaten
wurden geprüft. Ein alter PR-Text zählt nicht als Implementierungsnachweis.

**Ergebnis:** Ein Alt-PR ist dokumentarisch vollständig ersetzt, vier sind
teilweise ersetzt, einer ist technisch eigenständig relevant, zwei sind in ihrer
ursprünglichen technischen Form überholt und einer ist extern blockiert.
Die genaue, ausschließliche Zuordnung steht in der Matrix unten. Es gibt keinen Grund, einen alten Gesamt-Diff
ungeprüft zu integrieren. Vier voneinander unabhängige Produkt-/Werkzeugschnitte
sind als neue Drafts vorbereitet; sie ändern keine produktiven Daten.

Diese Datei ist ein datierter technischer Prüfbericht. **Einziger Aufgaben- und
Abnahmestatusowner bleibt der [Product Backlog](../planning/PRODUCT_BACKLOG.md#pr-abgleich).**
Der [kanonische UX3-Vertrag](../ui/ux-3/README.md) und der
[Hebeltrader-Integrationsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md)
werden nicht durch einen zweiten Regel- oder Aufgabenplan ersetzt.

Keine alten PRs wurden geschlossen, keine PRs gemergt, keine Kommentare
veröffentlicht, keine Workflows manuell gestartet oder wiederholt, keine Tags,
Releases, Deployments oder PC-Updates erzeugt. Die neuen Drafts erhalten ihre
normalen automatischen PR-Prüfungen. Keine Providerzustimmung, Quelle, Order,
P01-Bindung oder echte Buchung wurde verändert.

## 1. Neu verifizierter Ausgangsstand

| Gegenstand | Direkt erhobener Nachweis | Bedeutung |
|---|---|---|
| Main | `eb7f89a30a1772f2c140c5a11cdfb0284d80fc3c`, Merge #370 vom 25.11.2026 | Tatsächliche Codebasis, weiterhin `VERSION=1.5.55` |
| Neuester numerischer Versionstag | `refs/tags/v1.5.55` ist ein direkter Commitref auf denselben Main | Durch Git-Remote und GitHub-Git-Ref separat aufgelöst; kein angenommener `target_commitish` |
| Neuester GitHub-Release-Eintrag | [`v1.0.0-product-selection`](https://github.com/burckhju/trading-workspace/releases/tag/v1.0.0-product-selection), veröffentlicht 16.08.2026 | Releaseobjekt ist älter als der aktuelle Softwaretag. Annotiertes Tagobjekt `4b532974cfc3d2880b28eb249fc379876d9f58a7` zeigt direkt auf Commit `773201bcc0605f89e0817a297ada45b41020ec3e` |
| Offene PRs vor eigener Arbeit | Genau #187, #197, #205, #207, #220, #315, #335, #341, #342 | Vollständige Liste unter 100 Einträgen; acht Drafts, nur #220 kein Draft |
| Main-CI | Backend [45569606837](https://github.com/burckhju/trading-workspace/actions/runs/45569606837), Frontend [45569606801](https://github.com/burckhju/trading-workspace/actions/runs/45569606801), E2E [45569606742](https://github.com/burckhju/trading-workspace/actions/runs/45569606742): `completed/success` | Alle drei Pushläufe gehören genau zu `eb7f89a…`; Backend umfasst PostgreSQL, umask-Image und Renderer, E2E die vier regulären Jobs |
| Versionspublisher | [45573534512](https://github.com/burckhju/trading-workspace/actions/runs/45573534512) erfolgreich; direkter Tagread wie oben | Veröffentlichung des Tags belegt keine PC-Installation |
| PC | Betreiberreferenz vom 27.11. nennt installiertes v1.5.55 und dokumentierte P01-Produkt-/Listingbindung | In dieser Sitzung kein eigener PC-Readback. Letzter im Main öffentlich gebundener enger PC-Beleg ist vom 24.11. auf v1.5.54. Die spätere Betreiberreferenz wird weder als widerlegt noch als unabhängig erneut geprüft ausgegeben |
| P01 | Separat laufender Auftrag; Mapping, anschließende V2-Bewertung und Verbraucherabnahme bleiben getrennt | Keine Import-/Mappingschritte aus diesem Audit |

Der bestehende Tagpublisher erstellt nach erfolgreichen Main-Push-Gates einen
Versionstag. Er erzeugt nicht automatisch ein gleichnamiges GitHub-Releaseobjekt.
Deshalb sind beide oben genannten Versionsangaben miteinander vereinbar.

## 2. Konsolidierte Bereinigungsmatrix

A = vollständig durch Main ersetzt; B = teilweise ersetzt; C = eigenständig
relevant; D = ursprüngliche technische Form überholt; E = vollständiger Auftrag
fachlich oder extern blockiert. Jede Zeile hat genau eine Hauptkategorie.

| PR | Bereits in Main | Fehlende oder erhaltene Restarbeit | Kategorie | Empfohlene Aktion | Nachweis |
|---|---|---|---|---|---|
| [#205](https://github.com/burckhju/trading-workspace/pull/205) | Historienreader/API, offene und geschlossene Positionen, Originalzeit/-währung/-handelsplatz, Lücken, Quellenwahl, Originalbelege und Diagramm-/Browserfälle über #302/#306/#322 | Allgemeine rückwirkende Produktversorgung, echte Bestandsabdeckung und historische Maßstabsqualifikation fehlen; alter Seit-Kauf-/Basiswertumschalter ist nicht wortgleich umgesetzt | **B** | Keine zweite Historienfunktion. Zwei Entwicklungsworkflows verwerfen; relevante Datenversorgungs-/Maßstabsreste beim bestehenden Owner erhalten. Dann Original technisch schließbar | [Abschnitt 4](#4-positionskursverlauf-205), Main-Reader/Tests |
| [#315](https://github.com/burckhju/trading-workspace/pull/315) | Tatsächlicher Dokumentationsumfang vollständig in #314 kanonisiert, spätere B1/Q12-Produktschnitte vorhanden | Gesamtes UX3-Produkt und menschliche Abnahme bleiben offen, waren aber kein Runtime-Diff dieses PRs | **A** | Ohne Verlust seines Inhalts schließbar; keinen zweiten Hinweisvertrag integrieren. Historische Referenz erhalten | [Abschnitt 5](#5-ux3-und-koordination-315342), 10 Dokumentprüfungen und Typcheck |
| [#342](https://github.com/burckhju/trading-workspace/pull/342) | Masterkoordination, spätere UX-Integrationen und Fachstruktur A/#372 | Exakte historische Analyse-/Kandidatenrückwege, Selection→Run-Vertrag, M02, Coveragefläche, Abnahmen; M06/TP06 in neuen Drafts | **D** | Fünf alten Koordinationsdateien nicht unverändert mergen. Restanforderungen im bestehenden Backlog sichern, danach alten Snapshot schließen lassen | [Abschnitt 5](#5-ux3-und-koordination-315342), heutige Hosts und Quellen-DTOs |
| [#335](https://github.com/burckhju/trading-workspace/pull/335) | Historischer Währungsresolver, append-only Confirmation-Owner und regulärer Performancebericht; der Wartungshelfer fehlt | Atomarer Helfer technisch weiter sinnvoll; PC-Wrapper, Runtime-/Backupprüfung und Betreiberfreigabe separat erforderlich | **C** | Auf heutiger Basis als [#377](https://github.com/burckhju/trading-workspace/pull/377) neu qualifiziert. Reale Anwendung bleibt blockiert. Alten PR erst nach Ersatzintegration schließen lassen | [Abschnitt 7](#7-eur-bestandskorrektur-335), 28 Unit-/25 PostgreSQLfälle |
| [#341](https://github.com/burckhju/trading-workspace/pull/341) | E2E-Runneränderung bytegleich über #343 integriert | Offline-Quellenprüfung/Export fehlte; Collector, historische Kursqualifikation und Forschung weiterhin getrennt offen | **B** | Nur lokalen Vorbereitungsschnitt plus Privatschutz als [#375](https://github.com/burckhju/trading-workspace/pull/375) integrieren lassen; Runner-/alten Backlogdiff verwerfen | [Abschnitt 8](#8-provider-und-forschung-220341197), reine Offline-Module und 80 Fälle |
| [#187](https://github.com/burckhju/trading-workspace/pull/187) | Strenger Learning-Quellenowner, aktuelle Plan-/Preisachsen, versionierte Sitzungen, BSM-Grundmodell und F207-Evidenz | Eigenständige quellengebundene Einstiegsvorschau, Quellen-CRV/Banddiagnose/B07 und begrenztes Szenario fehlen weiterhin | **D** | Anforderungen erhalten, alte Quellen-/Kalender-/BSM-Parallelmodelle nicht übernehmen. Größere Folgen zuerst ownerkonform abgrenzen | [Abschnitt 6](#6-hebeltrader-187197207), konkreter alter Diff und heutige Owner |
| [#197](https://github.com/burckhju/trading-workspace/pull/197) | Keine seiner sieben Collector-/Repairdateien; bestehende Quellen-/Importversionierung und Governance | Private Originalquellen, heutige Rohdaten-/Rechtequalifikation, zertifizierte Historien und versionierter Forschungs-/Ausführungsvertrag | **E** | Als Forschung erhalten. Historisch ausgeführten Abruf anerkennen; öffentlichen Auto-Akquisitionsworkflow nicht übernehmen oder neu starten | [Abschnitt 6](#6-hebeltrader-187197207), damaliger Originaljob und heute leere Artefaktliste |
| [#207](https://github.com/burckhju/trading-workspace/pull/207) | Breite F207-Teilschnitte: Belege, Targets, Sessions, Skala, Original-BID/-Status, B04/B57, begrenzte Fristen/V2/Aktivierung/Delivery | B58-Quelle, B06/Schutz, vollständiges B05/B20, F207-5 und Gesamtbetriebs-/Fachabnahme | **B** | Tatsächlichen 40-Zeilen-Exporthelper verwerfen; fachliche Restanforderungen im bestehenden Vertrag/Backlog erhalten. Original danach schließbar, Baseline bleibt unvollständig | [Abschnitt 6](#6-hebeltrader-187197207), integrierte PRs #344–#365 |
| [#220](https://github.com/burckhju/trading-workspace/pull/220) | MS-/JPM-/gettex-Adapter, Resolver, Retention, spätere datierte Quellenqualifikation | Historische Recherche, aktuelle konkrete Instrumentabdeckung und notwendige Zugangs-/Nutzungs-/Originalstatusnachweise | **B** | Keine neuen gleichartigen Adapter. Veraltete Schemaanleitung korrigieren; Forschung und Rechteblocker erhalten. Original nach gesicherter Übernahme schließbar | [Abschnitt 8](#8-provider-und-forschung-220341197), vorhandene Provider und Tests |

Die Matrix umfasst genau neun PRs: **A: 1, B: 4, C: 1, D: 2, E: 1**.
Kategorien sind Entscheidungen, keine Fertigstellungsprozente.

## 3. Exakte Heads, Diffs und Mergefähigkeit

`Base` bezeichnet die lokal gegen heutigen Main berechnete Merge-base. Alle
vollständigen eigenen Dateidiffs wurden auf diesem Bereich gelesen, nicht
als rückwärts gerichteter Vergleich alter Dateibäume mit neuem Main.

| PR | Draft | Veröffentlichter Head | Merge-base gegen heutigen Main | Eigener Diff | Mergefähigkeit gegen Main |
|---|---|---|---|---|---|
| #187 | ja | `bad00a420f56994216ad1def6a580b00b0f5772f` | `eca87f428a86ac03a008183c15b1aecdb748800b` | 16 Dateien, +3237/−0 | `false` / `dirty` |
| #197 | ja | `08d2a5c9abe91ef518eb2c940eff9bbeceb073f8` | `aba5bff449bab980e487282bee155097018a3e25` | 7 Dateien, +682/−0 | `true` / `behind` |
| #205 | ja | `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | `87d464f2d2b79d8ad08ca1f1951949cc62a49d38` | 3 Dateien, +352/−0 | `false` / `dirty` |
| #207 | ja | `85921b9a6db30028a25b9c69a3e9a97a50482c10` | `afdeaad0dcc57fa64e0b7933e144f2655e5f02bc` | 1 Datei, +40/−0 | `true` / `behind` |
| #220 | nein | `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | `e001d7c68dad7e50fa3e42e4e2a50500edc69b9d` | 3 Dateien, +296/−4 | `true` / `behind` |
| #315 | ja | `d9d85f1af3159c4356c8773d076decbf1dc604e4` | `1883f7f330719453958f8be1dd51d48db816662e` | 5 Dateien, +1401/−1 | `false` / `dirty` |
| #335 | ja | `be746bfeb1b89846a127eaa3274662c8bab0ff05` | `fcca5539562a24c1c5e89ee510f3c4d8b509713f` | 4 Dateien, +1612/−0 | `true` / `behind` |
| #341 | ja | `52640616ed7ef0e8c91f945905ad3857ff263fed` | `d01c259f4b79fdfbdcec8743ececda035b69f9d1` | 10 Dateien, +1760/−5 | `true` / `behind` |
| #342 | ja | `5d3f017d8f65a51b26ad8aeab3ca1364eff1796c` | `b84544edabccbe5a9102ee883eb26ebf01f40f9a` | 5 Dateien, +390/−5 | `false` / `dirty` |

Bei #197/#207/#220/#335/#341 existieren aktuelle Testmergeobjekte mit Eltern
`eb7f89a…` und jeweiligem Alt-Head. Für diese fünf Testmerges lieferte der
direkte Check-Runs-Read **jeweils null Checks**. Historische Head-Runs sind
deshalb kein heutiger Main-Integrationsnachweis.

| PR | Aktueller Testmerge gegen `eb7f89a…` |
|---|---|
| #197 | `64bf4458a591871de25a55796a66252c122598a9` |
| #207 | `12c0fa6e520d7378ef80749e9ae68748ca81e6fe` |
| #220 | `322d10f522a9235c089ed47d67a7ddb8b61e8312` |
| #335 | `b6cc5caef4f3e19f4c9bfea11e6a2292143ca52f` |
| #341 | `f17eb44100f33ae277e9e34c2606ac3d804e7b4b` |

Die vier konfliktbehafteten PRs haben noch historische `refs/pull/*/merge`:
#187 `ca6f596f…` hat Basis `fbd77fb9…`, #205 `7871b2b0…` hat Basis
`eb443bdf…`, #315 `5bb4ace0…` hat Basis `1883f7f3…`, #342 `180abea8…`
hat Basis `6c0f9160…`. Ihre direkte Elternprüfung zeigt: Ein vorhandener
Merge-Ref ist allein kein gültiger Testmerge gegen heutigen Main.

### Alte CI, heute erneut gelesen

| PR | Historischer Headlauf vom | Backend | Frontend | E2E | Weitere historische Läufe |
|---|---|---|---|---|---|
| #187 | 2026-09-12 | [34690488439](https://github.com/burckhju/trading-workspace/actions/runs/34690488439) | [34690488560](https://github.com/burckhju/trading-workspace/actions/runs/34690488560) | [34690488455](https://github.com/burckhju/trading-workspace/actions/runs/34690488455) | — |
| #197 | 2026-09-13 | [34752894574](https://github.com/burckhju/trading-workspace/actions/runs/34752894574) | [34752894580](https://github.com/burckhju/trading-workspace/actions/runs/34752894580) | [34752894613](https://github.com/burckhju/trading-workspace/actions/runs/34752894613) | Research public history: [34752894596](https://github.com/burckhju/trading-workspace/actions/runs/34752894596) |
| #205 | 2026-09-13 | [34781508726](https://github.com/burckhju/trading-workspace/actions/runs/34781508726) | [34781508739](https://github.com/burckhju/trading-workspace/actions/runs/34781508739) | [34781508725](https://github.com/burckhju/trading-workspace/actions/runs/34781508725) | Position history development export: [34781506722](https://github.com/burckhju/trading-workspace/actions/runs/34781506722) |
| #207 | 2026-09-15 | [35032404812](https://github.com/burckhju/trading-workspace/actions/runs/35032404812) | [35032404811](https://github.com/burckhju/trading-workspace/actions/runs/35032404811) | [35032404809](https://github.com/burckhju/trading-workspace/actions/runs/35032404809) | Hebeltrader integration source snapshot: [35032404841](https://github.com/burckhju/trading-workspace/actions/runs/35032404841) |
| #220 | 2026-09-14 | [34885796940](https://github.com/burckhju/trading-workspace/actions/runs/34885796940) | [34885796699](https://github.com/burckhju/trading-workspace/actions/runs/34885796699) | [34885796621](https://github.com/burckhju/trading-workspace/actions/runs/34885796621) | — |
| #315 | 2026-10-31 | [41206859666](https://github.com/burckhju/trading-workspace/actions/runs/41206859666) | [41206859799](https://github.com/burckhju/trading-workspace/actions/runs/41206859799) | [41206859719](https://github.com/burckhju/trading-workspace/actions/runs/41206859719) | Version tag: [41206859749](https://github.com/burckhju/trading-workspace/actions/runs/41206859749) |
| #335 | 2026-11-08 | [42474024699](https://github.com/burckhju/trading-workspace/actions/runs/42474024699) | [42474024700](https://github.com/burckhju/trading-workspace/actions/runs/42474024700) | [42474024691](https://github.com/burckhju/trading-workspace/actions/runs/42474024691) | Version tag: [42474024694](https://github.com/burckhju/trading-workspace/actions/runs/42474024694) |
| #341 | 2026-11-11 | [42995060477](https://github.com/burckhju/trading-workspace/actions/runs/42995060477) | [42995060396](https://github.com/burckhju/trading-workspace/actions/runs/42995060396) | [42995060434](https://github.com/burckhju/trading-workspace/actions/runs/42995060434) | Version tag: [42995060466](https://github.com/burckhju/trading-workspace/actions/runs/42995060466) |
| #342 | 2026-11-13 | [43385779882](https://github.com/burckhju/trading-workspace/actions/runs/43385779882) | [43385779885](https://github.com/burckhju/trading-workspace/actions/runs/43385779885) | [43385779904](https://github.com/burckhju/trading-workspace/actions/runs/43385779904) | Version tag: [43385779996](https://github.com/burckhju/trading-workspace/actions/runs/43385779996) |

Alle genannten historischen Läufe sind erfolgreich, aber ausschließlich an
ihren konkreten Head und damaligen Checkout gebunden. Keine davon wurde als
Abschlussbeleg für einen neuen Diff oder heutigen Testmerge übernommen.

## 4. Positionskursverlauf #205

Main enthält #302 (`e8703a65…`), #306 (`2534d7c5…`) und #322 (`3397399e…`).
Das wurde durch PR-Metadaten, Git-Abstammung und tatsächliche Dateien geprüft.

- [Market-Data-Historienreader](../../backend/app/features/market_data/service/warrant_price_history.py)
  liest persistierte Samples und Quote-Beobachtungen. Originalzeit, Empfang,
  historische Identität, Provider, Listing/MIC, Währung und BID/ASK/LAST bleiben
  getrennt. Retention liefert höchstens die tatsächlich erhaltene Beobachtung.
  Keine interpolierte Historie aus einem letzten Cachewert; 10.000er-Samplebudget,
  verworfene Belege, vorhandene/untersuchte Samples und Kürzung sind sichtbar.
- [Positionsservice](../../backend/app/features/trade_position/service/price_history.py)
  verwendet effektive Ausführungen und den bestehenden Währungsresolver.
  Date-only erzeugt keinen erfundenen Mitternachtskurs. Ersetzte Ausführungen
  sind keine aktuellen Marker; fehlende Kaufwährung wird nicht aus Quotes geraten.
- [Registrierter GET](../../backend/app/features/trade_position/api/price_history.py)
  verwendet `REPEATABLE READ READ ONLY`, begrenzte Laufzeit und bestehende
  Kontextowner. Fehlender/fremder/stornierter Kontext, Konflikt, Speicherfehler
  und leere echte Historie haben unterschiedliche Antworten. Kein Providerabruf.
- [PositionPriceHistory](../../frontend/src/features/operational_workspace/components/PositionPriceHistory.tsx),
  `PositionPricePlot`, `PositionPriceHistoryEvidence` und `positionPriceHistory`
  zeigen Scatter ohne interpolierende Linie, Quellenwahl, Originaldezimalwerte,
  Zeit-/Qualitätsangaben und erhaltene Tabellen bei Chartfehlern.
  `TradeManagementPage` bindet die Fläche für offene **und** geschlossene Trades ein.

Konkrete Tests sind
[Market-Data-History](../../tests/unit/backend/features/market_data/test_warrant_price_history.py),
[Positionshistory](../../tests/unit/backend/features/trade_position/test_position_price_history.py),
[native PostgreSQL-History](../../tests/integration/backend/database/test_position_price_history_postgres.py)
und [Browserhistory](../../tests/e2e/position-price-history.spec.ts).
Sie prüfen unter anderem Originalzeiten/MIC, falsche Identitäten, Währungen,
Korrekturen, Teil-/Vollverkauf, Read-only-Verhalten, geschlossene alte Positionen,
Quellenüberlagerungen, Datumspräzision, Chartfehler, Tastatur und Zoom.

**Erhaltene Grenze:** Kein allgemeiner rückwirkender Feed für abgelaufene
Optionsscheine und kein aktueller privater Bestandsnachweis. Der alte Entwurf
`SINCE_ENTRY`/Basiswertumschalter ist nicht wörtlich implementiert; heutiger
Vertrag bietet alle gespeicherten Punkte oder Zeitfenster und einen getrennten
Basiswertchart. Die ursprünglichen Vorschläge bleiben erhalten; ihre weitere
Umsetzung oder Ablösung benötigt eine ausdrückliche Produktentscheidung.
Produktmaßstabswechsel sind keine eigene historische
Seriendimension; weitere Skalenqualifikation gehört zum bestehenden Product-/
Market-Data-Owner und darf P01 nicht parallel verändern.

Die beiden alten Entwicklungsworkflows exportieren Quelltext beziehungsweise
Testwerkzeuge. Sie beschaffen keine Produktgeschichte und werden nicht übernommen.

## 5. UX3 und Koordination #315/#342

### Genau ein verbindlicher Hinweisvertrag

#314, Merge `d80bd45d84d845aa920a7eac5b19a7fe6cd63307`, erhält den gesamten
Dokumentumfang aus #315 unter [docs/ui/ux-3](../ui/ux-3/README.md): 79 Befunde,
vier Typpräzisierungen, 24 Abnahmezuordnungen und den gemeinsamen Folgeplan.
Inhaltsfamilien, Darstellungsart, Ownergrund, Ursache/Wirkung/Aktion,
Herkunft, unbekannter Schreibausgang und bestätigter Write ohne Readback bleiben
getrennt. Ein technischer Reason allein beweist keine Berechnungssperre.

Neu ausgeführt: `node docs/ui/ux-3/verify-docs.mjs`, **10/10 erfolgreich**,
855 lokale Dateilinks, 29 Markdownanker, 58 Tabellen und vollständige
24-Fälle-Zuordnung. Der strikte Dokumenttypcheck ist ebenfalls erfolgreich.
Keine parallelen Runtimeimporte oder konkurrierenden B/C/D-Pläne gefunden.

Main-Produktteile: #320 (`91ebbc0f…`) mit
[NoticeCard](../../frontend/src/shared/notices/NoticeCard.tsx) und dem
lesenden Währungspiloten; #324 (`7399bcca…`) mit Q12-Hinweisen in
`ProductValuationPanel`; #326 (`a68b3a92…`) mit Statusdarstellung in
`PositionDetails`. Das ersetzt nicht alle noch geplanten UX3-Produktfälle.

### Veralteter Koordinationssnapshot, echte Reste

#342 ist ein v1.5.46-Snapshot in fünf bestehenden Koordinationsdateien.
#313/#321 und insbesondere #372 (`febeb922…`, Fachstruktur A) sind inzwischen
integriert. Heutige Hosts `TradeManagementPage`, `OperationalWorkspacePage`,
`TodayPage`, `TradeWorkspaceNavigation`, `WorkspaceEntryPages` und
`Application` verwenden die konsolidierte Struktur; unter anderem
`ui-fachstruktur-navigation.spec.ts` prüft sie. Ein alter Dokumentmerge darf
diese neue Struktur nicht rückwärts überschreiben.

Die folgenden konkreten Anforderungen bleiben beim bestehenden Owner erhalten:

1. `TradeSourcesView::Analysis` zeigt historische Analyse-/Kandidaten-IDs,
   aber keinen qualifizierten exakten Hin-/Rückweg. Keine Latest-Aliasse erfinden.
2. `trade_position/service/resolvers.py::ResolvedWorkspaceSelection` übergibt
   keine `run_id`, obwohl der Resolver die Auswahl intern daran prüft. Ein
   historischer Auswahlrun-Link braucht einen additiven qualifizierten Source-Read.
3. M02: Health-Teilreadfehler werden derzeit zu `health=null`. Eine geschlossene
   Position darf nur aus gültigem Ownerkontext folgen, nicht aus 404/leeren Alerts.
4. Die Positionscoveragefläche benötigt den vorhandenen Quote-Coverage-Owner,
   einen abgegrenzten Readtyp/Hostslot und korrekte Populationen/Invalidierung.
5. Menschliche Bedien-, Screenreader-, Touch- und Fachabnahmen sowie weitere
   Entscheidungsqualitätskriterien sind keine Folge grüner technischer Tests.

Zwei eindeutig geregelte Reste wurden unabhängig vorbereitet:

- **M06 / #374:** `TradeAlertsPanel` erklärt nur bei `INVALIDATED` den tatsächlichen
  gespeicherten Ownergrund. Legacy-Kursbezug und abgelöste Risiko-/Identitätsbindung
  sind getrennt; fehlende/unbekannte Gründe bleiben neutral. Originalcode und
  Belege bleiben aufklappbar, OPEN/RESOLVED und Delivery unabhängig. 70 lokale
  Tests, Lint/Format/Typecheck erfolgreich.
- **TP06 / #376:** `PlanPurchaseStatus` erklärt fehlende Daten als ungeklärten
  Kaufstatus und verweist auf den vorhandenen Aktualisieren-Button. Keine
  unbelegte Backendupdatepflicht, kein neuer Read/Write. 21 lokale Tests und
  die gleichen statischen Frontendprüfungen erfolgreich.

Beide verwenden Repository-Node 22.16.0. Ein früherer Hosttest unter Node 24
scheiterte an einem AbortSignal-Realm-Konflikt; unter der vorgesehenen Nodeversion
bestand die gesamte betreffende Suite. Kein Testschutz wurde dafür geändert.

## 6. Hebeltrader #187/#197/#207

### #187: Anforderungen nicht mit Monitoring gleichsetzen

Der alte Diff ergänzt eigene Plan-/Preis-/Kalendermodelle, API-Leser,
Frontend-Panel und Tests. Der direkte Learning-ORM-Zugriff im alten Trade-Plan-
API würde heute den strengeren
[Learning-Quellenowner](../../backend/app/features/learning/application/hebeltrader_source_reader.py)
umgehen: genaue Version, Workspace/Instrument, ACCEPTED/VALID-Import,
Datei-/Batch-/Hashbindung, Rohherkunft und historische Supersession.
Main besitzt außerdem `analysis/domain/vanilla_iv.py` mit eigenem
`BSM_CONTINUOUS_YIELD_ACT365_V1` sowie versionierte Sitzungsowner.

Erhalten werden: Auswahl vorhandener bestätigter Quellen ohne neue Modellfelder,
unveränderte Marken und getrennte Preisachsen, historisches Quellen-CRV,
`2*T1-T2` gegen GD200 ausdrücklich als Diagnose, gesonderte 50/50-Ask-CRV-/
2%-Einstiegsvorschau, unbekannte Zielhistorie, ausdrückliche Planerzeugung und
getrennte theoretische Szenarien. Das aktuelle gleichwährungsgebundene BSM-Modell
belegt keine FX-/Quanto-Unterstützung. B07 bleibt separat; B08 bleibt aus der
bestätigten Positionsbaseline ausgeschlossen. Ein bestätigter Z1-Treffer darf
nicht auf einen schon ausgeführten SELL reduziert werden.

### #197: historische Akquisition ist belegt, Datenqualifikation nicht

Alle sieben Collector-/Repair-/Workflowdateien fehlen in Main. Der damalige
[Originaljob 103712335946](https://github.com/burckhju/trading-workspace/actions/runs/34752894596/job/103712335946)
wurde neu gelesen: Testmerge `0632c08689b63f6b17a7445bfd6ca9c277455bd3`,
23 Offline-Tests erfolgreich, Zeitraum 01.10.2024–11.09.2026, **113/113
Listinganfragen plus ECB abgerufen**. Daneben stehen **41 Null-Sitzungen,
0 echte Daily-Reparaturen und 41 rekonstruierte Stundenraster**; der Job weist
`certified_daily_close_claim=false` ausdrücklich aus.

Das damalige Artefakt `10315962663` hatte 400 Dateien, 2.688.684 Byte und den
Joblog-Hash `2d1935ca21dc0fea8cdda2bb0923ba29810a6e2ab95536f8596915f271603e37`.
Die heutige Artefaktliste zu diesem Run ist leer. Es wurde kein ZIP erneut
gehasht. Daher weder „nie beschafft“ noch „vollständige qualifizierte Historie“.
Der Repair erkennt vorhandene Nullzeilen, nicht automatisch fehlende Kalendertage.

Private 135 PDFs, Regeloriginal und v0.6-Paket standen hier nicht zur Verfügung.
Aktuelle Zugangs-/Speicherrechte, Instrument/Listing, Währung/Einheit,
Kapitalmaßnahmen und Sitzungsabdeckung bleiben zu qualifizieren. Die eigene
Forschungsvariante mit 25%-Z1, Peak-/ATR-/SMA-/Swing-Annahmen ist nicht die
bestätigte B01–B58-Baseline. Ein lokaler privater Collector und reproduzierbarer
Studienvertrag wären eigenständige Folgeschnitte; der alte öffentliche Autojob
wird nicht unverändert in Main genommen oder erneut gestartet.

### #207: der alte Diff enthält nur einen Helper

Der veröffentlichte eigene Diff besteht ausschließlich aus 40 Zeilen
`.github/workflows/hebeltrader-baseline.yml`. Die im alten Body beschriebenen
62 lokalen Implementierungsdateien sind darin nicht nachgewiesen. Spätere
Main-Implementierung wird deshalb über ihre tatsächlichen Integrationen belegt:

| Bereich | Main-Integration | Code / konkrete Testfamilie |
|---|---|---|
| Historische Positions-/Ausführungsbelege, ursprüngliche Gruppe und Basiswertbeiträge | #344 `e6738c29…` | `trade_position/{domain,service,persistence}/hebeltrader_evidence.py`, `hebeltrader_coverage.py`; Coverage-/Monitoring-Basis-/Source-Reader-Tests |
| Dauerhafte Z1/Z2-Treffer und getrennte Schutzgrundlage | #345 `6efa74d3…`, Migration 0051 | `position_monitoring/domain/hebeltrader_targets.py`, Services/Persistenz; Targets-/API-/PostgreSQLfälle; kein Schutzvorschlag aus bloßer Schutzgrundlage |
| Historische Eingangsqualifikation | #346 `1d63d001…` | `market_data/service/hebeltrader_history.py`, Target-Inputreview; Tageshoch nicht als Intradaybeweis |
| Verifizierte Basiswertsitzungen, Zeitzone, Tag 0 und Lücken | #347 `19a10ad4…`, Migration 0052 | Session-Evidence-Owner, `hebeltrader_sessions.py`; Sitzung 20 erst nach tatsächlichem Schluss |
| Original-BID, Seitenzeit, exakte Altersgrenze | #348 `62d9dc83…` | `hebeltrader_original_bid.py`; Zukunft/900s/Retention/Identitäts-/DST-Fälle |
| Historischer Produktmaßstab | #349 `003f9a4d…`, Migration 0053 | Product-Scale-Evidence, `hebeltrader_product_price_scale.py`; kein Produktmaßstab aus Basiswertsplit allein |
| Originalmarktstatus und unabhängiges Statusjournal | #350 `c914fb2d…`, #351 `fdba5b51…`, Migration 0054 | `hebeltrader_live_market_status.py`; `OBSERVED_AT_INSTANT` ohne erfundene Gültigkeitsdauer |
| Strenger B04/B57-Verlustkern und Episoden | #352 `37294a59…`, Migration 0055 | `hebeltrader_loss.py` und Services; Lücke keine Erholung, neue Episode erst nach echter qualifizierter Entwarnung |
| B05/B17–19-Rechnung | #353 `02eb6e1c…` | `hebeltrader_deadlines.py`; 19/20/21 Sitzungen, Deckung, DST; B20 nicht damit abgenommen |
| V1/V2-Indikation und begrenzte Produktfristreviews | #357 `412f6843…`, #358 `dc68a7b3…`, #365 `e335a42f…` | `indicative_entry.py`, `indicative_policy.py`, `indicative_recovery.py`, Deadline-Reader/Delivery; eigene Qualitätsgrenzen |
| Begrenzte Aktivierung und Zustellung | #359 `7c360b65…`, spätere V2-Anpassung | vorhandener Aktivierungshelfer, Runtime/Runner und Notification-Lifecycle; synthetische Tests senden keine echten Nachrichten |
| Produktende versus Zahlungstag, erneute Auswertung gespeicherter Originale | #368 `c7db441d…` | Product-Dokumentparser/-reparse; Originalbytes/Hash/Abrufzeiten bleiben erhalten |

### Sechs unterschiedliche Nachweisstufen

| Umfang | Implementiert / technisch getestet | Fachlicher Quellenstand | Aktivierung / realer Bestand | Noch nicht vorhanden oder belegt |
|---|---|---|---|---|
| Belege und Z1/Z2 | Ownerpfade und dauerhafte Treffer vorhanden; gezielte Kernfälle lokal erfolgreich, PG/UI-Fälle vorhanden | Synthetische Vertragsnachweise, keine vollständige private historische Belegkette | Keine neue Aktivierung; dokumentierter 22.11-Readback ohne Target-Assessments | Vollständige persönliche Quellen, Schutzboden/Bekanntgabe/Folgeüberwachung |
| B04/B57/B58 | Strenger Kern und Originalreader vorhanden, Grenz-/Episodenfälle lokal grün | **Keine reale positiv qualifizierte B58-Produktionsquelle** | Strenger Umfang im dokumentierten Readback deaktiviert; keine eigene PC-Prüfung | Quellenzeit, Statusgeltung, persönliche Historien und Gesamtfreigabe |
| V2-Indikation | Eigene begrenzte Regel, Episode, Qualitätsboden und Delivery getestet | Bekannte Annahmen bleiben sichtbar, keine strenge B58-Ersatzqualifikation | Repository dokumentiert V2-Betrieb und P02-Befund vom 24.11.; hier nicht neu gemessen | P01 separat, Gesamtdepot-/Fach-/Zustellabnahme |
| Produktfristen | Rechner und begrenzte V2-Erinnerung vorhanden/testbar | `B05_PARTIAL_B20_UNVERIFIED`, keine erfundene Uhrzeit | Teil des dokumentierten V2-Betriebs, keine vollständige B05-Freigabe | Exitlisting, Kalenderdeckung und individueller Schluss |
| F207-5 | Teilpfade für Episode/Outbox/Deduplizierung/Versionsfamilie vorhanden | Kein vollständig abgenommener gemeinsamer Meldungs-/Reaktionsvertrag | Kein Komplettregelwerk aktiviert oder real abgenommen | gesehen/abgelehnt/ausgeführt, Gesamtpriorisierung und Betriebsabnahme |

Der echte Produktionskatalog in
[`hebeltrader_b58_sources.py`](../../backend/app/features/position_monitoring/service/hebeltrader_b58_sources.py)
bleibt **`QUALIFIED_B58_PATHS = ()`**. Synthetische Registryeinträge oder Payloads
ändern das nicht. 900 Sekunden BID-Alter sind keine Status-TTL. V2 hat einen
eigenen begrenzten Zeit-/Empfangsvertrag und öffnet B58 nicht.

**B06 ist nicht vollständig implementiert:** benötigt dauerhaften Z1-Bezug,
20 abgeschlossene Basiswertsitzungen ab Z1/Tag 0 und den höheren gültigen
Schutzboden aus bestehendem Schutz, persönlichem Basiswerteinstieg und
0,8 × ursprünglichem Z1, einschließlich Bekanntgabe, Folgeüberwachung und
Korrektur. `DYNAMIC_STOP_V1` ist eine andere ATR-Policy. Das ist kein sicherer
kleiner Formelpatch; ein abgegrenzter Anschlussvertrag bleibt nötig.

## 7. EUR-Bestandskorrektur #335

Der Zweck ist eine **heutige ausdrückliche Währungsdeklaration** für einen
exakt bekannten historischen UNKNOWN-Kaufbestand, keine rückdatierte
Bestätigung. Der ursprüngliche 606-Zeilen-Helper und die Owner-/Testpfade wurden
vollständig gelesen. Currency-Owner/Resolver, Evidence-Repositories und
RealizedGrossSnapshotReader sind seit #335-Basis `fcca5539…` unverändert;
Main enthält den Helper bislang nicht. v1.5.55 qualifiziert aktuelle
Listingeinheiten und ersetzt keine historische Ausführungswährung.

Der Folge-Draft [#377](https://github.com/burckhju/trading-workspace/pull/377)
behält diese Architektur bei:

- Nur effektive BUYs nicht stornierter Trades, exakte Workspace-/Produkt-/
  Trade-/Executionbindung; Menge muss allen UNKNOWN-BUYs des gebundenen Bestands
  entsprechen. Vorhandene Bestätigung, Geschichte oder widersprechende Quelle
  verhindert die neue Behauptung.
- Vollständiger regulärer Berichtsbasisfingerprint; NOWAIT-Tabellen- und
  deterministische Ownerlocks; einzelne Ownercommits lösen Savepoints innerhalb
  genau einer äußeren Transaktion. Fehler vor deren Commit rollen alles zurück.
- Nur neue append-only `USER_CONFIRMED`-Datensätze; Originalpreise, Mengen,
  Ausführungen, historische Belege und SELLs bleiben erhalten. Keine zweite
  Kostenbasis- oder Performanceformel; Auswirkungen kommen aus dem vorhandenen
  qualifizierten Währungsresolver.
- Deterministische Requests, vollständige Replayprüfung, Rekonstruktion der
  Ausgangsbasis durch Entfernen nur der eigenen neuen Belege und exakte
  Report-Postconditions. Teilwiederholung, spätere Ersetzung und fremde Belege
  werden nicht überschrieben.
- Frische Read-only-Prüfung nach Commit; verlorene Commitbestätigung und
  fehlgeschlagene Nachprüfung werden ausdrücklich als unsicherer Ausgang
  beziehungsweise verifizierungsbedürftiger Commit ausgegeben, nie als
  behauptetes „nichts geschrieben“.

**Zusätzlich gegenüber #335:** acht Unitfälle prüfen den echten `run()`-
Kontrollfluss an diesen Commitgrenzen; die alten Fälle mockten dort `run()`.
Die technische Dokumentation korrigiert die unbelegte Installationsannahme und
benennt den fehlenden PC-Wrapper. Ein Planhash erklärt nicht, dass Originalinventar,
Backup, Runtime, `update.lock`, `pending` oder Betreiberberechtigung geprüft wurden.

Lokal sind **28 Helfer-Unitfälle**, mit bestehenden historischen Currency- und
Performancefällen **104 Fälle insgesamt**, sowie **25/25 native PostgreSQL-
Integrationsfälle** erfolgreich. Die PostgreSQL 16.2-Instanz wurde eigens lokal
erzeugt, echte Migrationen und Owner-APIs liefen auf synthetischen zufälligen
Testdatenbanken, HTTP-Transporte waren gesperrt. Laufzeit 118,67 Sekunden;
Instanz danach beendet. Die reguläre PR-CI prüft PostgreSQL 17 zusätzlich.
Ein anfänglicher Lauf ohne Test-URL übersprang 25 Fälle und zählt nicht als Erfolg.

**Realer Betrieb bleibt blockiert:** qualifizierter privater Wrapper,
validierte Sicherung, wiederherstellbarer Zustand, genaue Runtime-/Planbindung,
separate Betreiberfreigabe und koordiniertes Wartungsfenster. Die breiten
Tabellenlocks würden einen späteren echten P01-Import berühren; hier wurden
sie ausschließlich an synthetischen Daten ausgeführt.

## 8. Provider und Forschung #220/#341/#197

### Vorhandene Adapter, keine doppelte Implementierung

Main enthält [Morgan Stanley](../../backend/app/providers/morganstanley/),
[JPMorgan](../../backend/app/providers/jpmorgan/) und
[gettex delayed](../../backend/app/providers/gettex_delayed/) sowie den
vorhandenen `quote_runtime`-Resolver und `retained_quotes`-Owner.
Relevante Integrationen: #224 `f95f60d6…`, #228 `9a7944ee…`, #237 `022f4953…`,
#242 `16e2feec…`, #247 `baee6f81…`, #305 `7ab6eea2…`.

| Quelle | Tatsächlicher Code-/Datenvertrag | Offene Grenze |
|---|---|---|
| MS | Gebundene Streams, getrennte BID/ASK, Nullseite bleibt fehlend; Originalzeittext erhalten | Volle lokale Zeit ohne qualifizierte Zeitzone; `observed_at=None`, Marktstatus UNKNOWN; keine B58-Quelle |
| JPM | Gebundene/dynamisch geprüfte Produktstreams, eigene geschützte persönliche Zustimmung, getrennte Seiten | Uhrzeittext ohne qualifiziertes Datum/Zeitzone; Rendererempfang ist keine Originalzeit; keine neue Zustimmung durch diesen Audit |
| gettex | Headerlose 7-Feld-CSV, MUND/MUNC, Original-UTC-Fenster, vollständige GZip-Prüfung, ISIN-Isolation, gemeinsamer Cache, Rate-Limits/Retention | Default aus/Privatbestätigung nötig; Marktstatus UNKNOWN; tatsächliche heutige Instrumentquote und B58-Frische nicht aus Dateiliste ableitbar |
| Weitere im Alt-PR genannte Anbieter | Historische Onvista-/ARIVA-/UniCredit-/FactSet-/SIX-/Infront-Recherche | Keine neue lizenzierte Kursversorgung oder aktuelle Instrumentpayload-Qualifikation in dieser Sitzung |

Direkt gelesene Tests: `test_morganstanley_runtime.py`,
`test_jpmorgan_runtime.py`, `providers/gettex_delayed/test_parser.py`,
`test_gettex_delayed_adapter.py`, `test_gettex_retention_regression.py`.
Sie prüfen unter anderem fehlende Zeiten/Seiten, feste Identität, deaktivierte
Quelle ohne Netzwerk, Mitternacht, CRC, falsches Fenster, Cachedeckung,
429-Backoff, unveränderte gebundene Quelle und Erholung nach Sperre.

Dateicache und Abrufsperren sind prozesslokal. Der ursprüngliche Vorschlag
eines dauerhaften zentralen Dateicheckpoints ist damit nicht umgesetzt;
dieser Rest bleibt beim vorhandenen Providerowner und benötigt vor einer
Umsetzung einen konkreten Bedarfs-, Speicher- und Rechtevertrag.

Die inzwischen überholte [GETTEX_SCHEMA_PROBE](../GETTEX_SCHEMA_PROBE.md)
wird in diesem Dokumentationsschnitt als historische Discovery eingeordnet und
auf die vorhandenen Adapter/Tests verwiesen. Die alten Prüfanforderungen bleiben
lesbar, aber der falsche erneute Implementierungsauftrag entfällt.

### Begrenzte aktuelle öffentliche Quellenprüfung

Am 27.11. wurden nur offizielle Informationsseiten gelesen:
[gettex-Bedingungen](https://www.gettex.de/en/trading/delayed-data/),
[gettex-Dateiliste](https://www.gettex.de/en/trading/delayed-data/pretrade-data/),
[Onvista-Bedingungen](https://www.onvista.de/nutzungsbedingungen) und
[MS-Bedingungen](https://zertifikate.morganstanley.com/nutzungsbedingungen/).
Die gettex-Liste zeigt aktuelle MUND-/MUNC-Dateinamen bis 27.11., 22:00 UTC.
Keine Kursdatei wurde heruntergeladen und keine Erklärung abgegeben.
Gettex beschränkt die angegebene Nutzung auf private natürliche Personen ohne
Weitergabe; Onvista verlangt in Abschnitt 6 Einwilligung für automatisierte
Abfragen; MS bezeichnet Preise als indikativ. Das sind Quellenhinweise,
keine neue rechtliche Freigabe oder Provideraktivierung.
Die untersuchte JPM-Produktseite war über den Webreader nicht zugänglich;
dies belegt keinen allgemeinen Ausfall oder fehlenden PC-Zugang.

### #341: Runnerfix vorhanden, Offlinevorbereitung fehlte

Die E2E-Workflowdatei ist zwischen #341-Head und aktuellem Main bytegleich.
#343 (`b84544ed…`, Einzelcommit `f4cbd59c…`) hat die Runnerkorrektur bereits
integriert. Die vier anderen Vorbereitungsmodule und zwei Tests fehlten dagegen
vollständig. Der alte Gesamt-Diff wird nicht übernommen.

Der isolierte [Draft #375](https://github.com/burckhju/trading-workspace/pull/375)
ergänzt einen lokalen Quellenvertrag im bestehenden Learning-Owner:
striktes explizites JSON, getrennte Preisachsen, unveränderte Decimallexeme,
DATE_ONLY, Sollanzahl/Dubletten und deterministische Manifest-/CSV-/Datenbedarfe.
`NOT_COMPUTED`, `UNVERIFIED_LISTING`, `NOT_SELECTED` und
`DECLARED_NOT_REHASHED` verhindern erfundene Markt-/Ergebnisqualifikation.
Kein Netzwerk, keine DB, Settings, Provider, operativen Imports oder Commands.

Private Ausgaben werden außerhalb jedes erkennbaren Git-Checkouts einschließlich
Worktree-/Submodule-/bare-/Symlinkpfad verlangt. Neuer POSIX-Ordner 0700,
Dateien 0600, exklusive Erstellung, Manifest zuletzt, keine Quellwerte/Pfade auf
stdout/stderr, CSV-Formelneutralisierung bei unverändertem JSON-Original.
Die neue Exportversion v2 erklärt diesen Unterschied zum alten Entwurf.

**Lokal:** vollständiges Ruff/Black und strict mypy für 683 Quelldateien erfolgreich.
Von 80 gezielten Fällen bestanden 67; 13 positive Dateiausgaben wurden durch den
vorgesehenen Git-Schutz in der umschließenden Executor-Arbeitskopie abgewiesen.
Das ist kein erfolgreicher Gesamtlauf. Keine Abschwächung oder Testentfernung;
positive Ausgaben müssen in regulärer CI außerhalb Git bestehen. Getestete
Umasks sind 000 und 077; extreme andere Werte begründen keine Erfolgsgarantie.

Der Adapter ist kein XLSX/PDF-Collector, historischer Quote-Backfill, Backtest,
Handels-/Ausführungsmodell oder Rendite-/Trefferquotenbericht. Quellenrechte,
Settlement-/KO-/Finanzierungsevidenz und Datenabdeckung bleiben eigenständig.

## 9. Neue unabhängige Drafts und tatsächliche Prüfungen

| Draft | Veröffentlichter Head | Lokal geprüfter identischer Tree | Begrenzter Stand |
|---|---|---|---|
| [#374 M06](https://github.com/burckhju/trading-workspace/pull/374) | `8f46e87d1fc791b8d48263d8f6f9d5e164935ed0` | `c977f1c3a5022d7dfd101bc04cab98618b51f69c` | 2 Dateien, 70 Tests, Frontendstatik erfolgreich |
| [#375 Offlinequellen](https://github.com/burckhju/trading-workspace/pull/375) | `84d5b030108bba7814332eb68d99d2ff54295183` | `7ba5072efbb49ac0560bf1ee552407448f9d91d8` | 8 Dateien, 67 lokale Tests erfolgreich / 13 echte Umgebungsblockierungen; vollständige Pythonstatik erfolgreich |
| [#376 TP06](https://github.com/burckhju/trading-workspace/pull/376) | `efbcb8052b6a30bddf2e75e950981df25178a6c0` | `6cac9a70efaf9c5a4a3315edb69ffba3ad57e70b` | 2 Dateien, 21 Tests, Frontendstatik erfolgreich |
| [#377 EUR-Recovery](https://github.com/burckhju/trading-workspace/pull/377) | `20266a7c99c259bf3c7f9d4c1c23a6295da3f0f5` | `e204ba34266c415c896fee8c1fd9e6a4c4d949ba` | 4 Dateien, 104 Unit-/Fachfälle sowie 25 PostgreSQLfälle erfolgreich; Pythonstatik erfolgreich |

Alle vier haben ausschließlich `eb7f89a…` als Basis. Keine Abhängigkeit auf
einen anderen neuen Featurebranch. Direkter Gitpush war mangels CLI-Credential
nicht verfügbar; die autorisierte GitHub-Verbindung publizierte jeweils genau
den lokal geprüften Tree. Unterschiedliche lokale/Remote-Commitkennungen werden
deshalb nicht gleichgesetzt. Für Integration zählt der veröffentlichte Head.

Zusätzlich auf unverändertem Main: **648 verschiedene F207-Tests bestanden**,
32 bestehende Managed-PC-Aktivierungsfälle übersprungen wegen des unveränderten
Outside-Git-Fixtureschutzes. Die 453er Kern- und 195er Ergänzungsauswahl werden
nicht mit Wiederholungsläufen doppelt gezählt. **23 #197-Offline-Tests** bestanden
ohne Netzabruf. **9 Version-/Publicationguards** bestanden.

Lokale `verify-release-readiness.sh` scheitert an fehlendem Docker. Es wird weder
eine lokale vollständige Container-/Browserqualifikation noch Releasebereitschaft
behauptet. Die vorgesehenen PR-Gates liefern PostgreSQL 17, Backend-Coverage,
Frontend-Coverage/Build, vier E2E-Jobs und Versionsschutz auf dem eigenen Head.

### Aktuelle PR-CI wird separat an tatsächliche Checkouts gebunden

Snapshot vom 27.11.2026, 23:47 Uhr Europe/Berlin: Frontend, E2E und Versionsgate
sind für alle vier veröffentlichten Heads erfolgreich. Backend läuft jeweils
noch; insbesondere sein abschließendes Test-/Coverageergebnis wird hier nicht
vorweggenommen.

| Draft | Backend | Frontend | E2E | Versionsgate |
|---|---|---|---|---|
| #374 | [46077247671](https://github.com/burckhju/trading-workspace/actions/runs/46077247671), läuft | [46077247676](https://github.com/burckhju/trading-workspace/actions/runs/46077247676), erfolgreich | [46077247680](https://github.com/burckhju/trading-workspace/actions/runs/46077247680), erfolgreich | [46077247681](https://github.com/burckhju/trading-workspace/actions/runs/46077247681), erfolgreich |
| #375 | [46077410945](https://github.com/burckhju/trading-workspace/actions/runs/46077410945), läuft | [46077410916](https://github.com/burckhju/trading-workspace/actions/runs/46077410916), erfolgreich | [46077410973](https://github.com/burckhju/trading-workspace/actions/runs/46077410973), erfolgreich | [46077410977](https://github.com/burckhju/trading-workspace/actions/runs/46077410977), erfolgreich |
| #376 | [46077677205](https://github.com/burckhju/trading-workspace/actions/runs/46077677205), läuft | [46077677161](https://github.com/burckhju/trading-workspace/actions/runs/46077677161), erfolgreich | [46077677188](https://github.com/burckhju/trading-workspace/actions/runs/46077677188), erfolgreich | [46077677132](https://github.com/burckhju/trading-workspace/actions/runs/46077677132), erfolgreich |
| #377 | [46077872951](https://github.com/burckhju/trading-workspace/actions/runs/46077872951), läuft | [46077872891](https://github.com/burckhju/trading-workspace/actions/runs/46077872891), erfolgreich | [46077873001](https://github.com/burckhju/trading-workspace/actions/runs/46077873001), erfolgreich | [46077873007](https://github.com/burckhju/trading-workspace/actions/runs/46077873007), erfolgreich |

Die Frontend-Logs belegen jeweils 212 Testdateien: 2.851 bestandene Tests für
#374, 2.838 für #375, 2.839 für #376 und 2.838 für #377. Je PR enthält der
E2E-Smoke 208 bestandene und fünf übersprungene Fälle; die zusätzlichen
PostgreSQL-Ownerjobs für Realized-Gross, Journal/Evidence und Candidate-Governance
sind erfolgreich. Die Checkoutzeilen dieser Jobs zeigen die untenstehenden
Testmerges; deren direkt gelesene Eltern sind jeweils Main und der PR-Head,
der Tree ist identisch zum jeweiligen Head. Das Versionsgate im PR veröffentlicht
keinen Tag.

Die vollständigen Run-/Job-/Checkoutnachweise werden in den jeweiligen
Draftbeschreibungen fortgeschrieben, ohne Quellcommit oder Tests zu verändern.
Dieser Bericht überträgt keine alten grünen Läufe auf einen neuen Head.
Ein laufender oder ausgelassener Job ist kein erfolgreicher Nachweis.
Die bei Erstellung zurückgelesenen Testmerges sind:

| Draft | Tatsächlicher Testmerge | Erwartete Eltern |
|---|---|---|
| #374 | `27edd9673f9ec7ac414e3d491fa35b106d81b1c7` | `eb7f89a…` und `8f46e87d…` |
| #375 | `7084c4da0b8b61c67936149eb01052154223f058` | `eb7f89a…` und `84d5b030…` |
| #376 | `f69012ee31086382a17b0abc6ee9c17ee4b800f8` | `eb7f89a…` und `efbcb805…` |
| #377 | `fb1103e2159ec38c43f5bda7722ce5d629c34394` | `eb7f89a…` und `20266a7c…` |

## 10. Schließungsentscheidungen, P01 und ein nächster Integrationsschritt

**Ohne Verlust seines tatsächlichen Inhalts schließbar:** #315. Der kanonische
Vertrag erhält alle Dokumentanforderungen; offene Produktarbeit wird dadurch
nicht geschlossen. Die ältere Koordination hält #315 als Quellreferenz, nicht
als zweiten Vertrag. Die Betreiberentscheidung zur Schließung bleibt ausstehend.

**Nach dauerhafter Sicherung der Anforderungen in dieser Konsolidierung
schließbar:** #205, #207, #220 und #342. Originale bleiben über PR-/Commitlinks
historisch erreichbar. #187 sollte als überholte Implementierungsform erst nach
Bestätigung der erhaltenen Einstiegsvorschau-/Szenarioanforderungen abgelöst
werden. #335/#341 erst nach Integration und Qualifikation ihrer begrenzten
Nachfolger; kein grüner Draft allein ersetzt den Mainnachweis. #197 bleibt
offene Forschung mit externen Daten-/Rechtehindernissen.

**P01-Auswirkung:** Kein Mapping, Listing, Import, Originalbeleg, Preismaßstabs-
oder Währungsresolver und kein V2-/Diagnosepfad geändert. Technische
Überschneidungen sind die historische Skalenfrage aus #205 und die breiten
Wartungslocks eines späteren echten #335-Vorgangs. Beide werden separat
koordiniert. P01-gettex schließt B58/B06 nicht. Der bestehende P01-Auftrag
und sein nächster Betreiber-/Verbrauchernachweis bleiben unverändert.

Die Nachweisfolge bleibt ausdrücklich:

**konzipiert → implementiert → lokal getestet → PR-geprüft → Main-integriert
→ veröffentlicht → PC-installiert → fachlich abgenommen.**

Die neuen Drafts befinden sich vor Mainintegration. Keine tatsächliche
Handelsentscheidung, Order, Bestandskorrektur, neue Providerfreigabe oder
Fachabnahme wird aus synthetischen Tests abgeleitet.

**Genau ein nächster Integrationsschritt:** Den kleinsten unabhängigen
M06-Fix [#374](https://github.com/burckhju/trading-workspace/pull/374) nach
vollständig erfolgreicher eigener Head-/Testmerge-CI zur ausdrücklichen
Mergeentscheidung vorlegen. Dieser Auftrag führt den Merge nicht aus.
