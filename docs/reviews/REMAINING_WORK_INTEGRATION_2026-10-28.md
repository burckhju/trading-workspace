# Restarbeiten: Integrationsprüfung vom 28.10.2026

## Prüfstand und Nachweisgrenze

Dieser Nachweis ordnet die tatsächlich vorhandene Implementierung und den engen
Restumfang des nächsten Integrations-PRs ein. Er ersetzt weder den
[Product Backlog](../planning/PRODUCT_BACKLOG.md) noch historische Abnahmen.
Die nachstehenden lokalen Nachweise gehören zur Vorbereitung des Branches
`integration/remaining-work-20261028`. Der abschließende Commitbezug und die
Ergebnisse der vollständigen Backend-/PostgreSQL-/PR-CI werden in der
PR-Beschreibung am tatsächlich geprüften Head geführt. Die erfolgreiche
Ausgangs-CI wird nicht auf neue Änderungen übertragen.

| Gegenstand | Festgestellter Stand |
|---|---|
| Main bei Beginn | `f3c067ecdfe99e46f3c8b63c37bb4d283cd5a568`, Merge von [#291](https://github.com/burckhju/trading-workspace/pull/291). |
| Veröffentlichter Versionstag | `v1.5.28` löst direkt auf denselben Commit auf. Ein Versionstag ist kein Nachweis einer PC-Installation. |
| Historische Referenz | `v1.5.25` vom 27.10.2026 löst auf `38cac1a0cda52e4e1e6c4e69bd38f1842e388acb` auf. Dieser Stand ist nicht mehr die Implementierungsbasis. |
| Seitdem relevante Integrationen | [#290](https://github.com/burckhju/trading-workspace/pull/290) und #291 sind bereits Main; außerdem werden die enthaltenen Konsolidierungen aus [#289](https://github.com/burckhju/trading-workspace/pull/289)/[#292](https://github.com/burckhju/trading-workspace/pull/292), die Buchungskorrekturen aus [#293](https://github.com/burckhju/trading-workspace/pull/293) und die Veröffentlichung aus [#294](https://github.com/burckhju/trading-workspace/pull/294) erhalten. |
| Offene PRs bei der Prüfung | #90, #187, #197, #205, #207, #220, #225, #235 und #268. Keiner wird durch diesen Auftrag geschlossen oder gemergt. |

Die frühere [Restprüfung vom 20.10.2026](LEGACY_PR_REMAINDERS_2026-10-20.md)
enthält bereits datierte Fortschreibungen. Ihre damaligen offenen Punkte und
Testzahlen werden nicht ungeprüft als heutiger Status übernommen. Frühere
Gesprächsinhalte waren in dieser Sitzung nicht abrufbar; maßgeblich sind der
vollständige Checkout, Git-Historie, PR-Diffs und abgerufene GitHub-Ergebnisse.

## Entscheidung je Arbeitsbereich

| Bezug | Tatsächlicher Befund und Integrationsentscheidung |
|---|---|
| **#291: Providerkennung** | Bereits in Main. Die Providerprüfung im [MappingEditor](../../frontend/src/features/administration/components/MappingEditor.tsx) und die [Mapping-Verträge](../../frontend/src/features/administration/services/referenceMapping.ts) werden erhalten und regressionsgeprüft; keine zweite Providerdiagnose. |
| **#90: Lesson öffnen** | Erstellen, Readback, bestehende Detailroute und historische Versionsnavigation sind vorhanden. Auf der Ausgangsbasis fehlte die gemeinsame unmittelbare Erfolgsaktion in [LessonDraftFromEvidence](../../frontend/src/features/learning/components/LessonDraftFromEvidence.tsx). Der aktuelle Schnitt ergänzt dort „Lesson öffnen“, eine `LS-…`-Kurzreferenz und aufklappbare vollständige UUID; der zusätzliche Parent-Link im [TradeJournalPanel](../../frontend/src/features/learning/components/TradeJournalPanel.tsx) entfällt. Die [direkte FT-011-Übergabe](../../frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx) erhält das bestätigte Erstellergebnis auch bei verzögertem, leerem oder fehlgeschlagenem Readback. |
| **#290: Performance** | Bereits in Main. [PerformanceWorkspace](../../frontend/src/features/performance/pages/PerformanceWorkspace.tsx), gemeinsamer [Berichtskontext](../../frontend/src/features/performance/services/performanceReportContext.ts) und bestehende Berichts-/Quellenkomponenten bilden die konsolidierte Oberfläche. Kein neuer Bericht, keine Berechnungsänderung, keine parallele Navigation. |
| **#225/#235: Scheduler** | Discovery-/Quote-Lanes und begrenzter Retry sind über [#237](https://github.com/burckhju/trading-workspace/pull/237) vorhanden; der Quellenmodus-/Pacing-Rest wurde durch [#271](https://github.com/burckhju/trading-workspace/pull/271) integriert. Siehe [Pacing-Qualifikation](MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md). Die alten Implementierungen und die zusätzliche CI-Aufteilung aus #225 werden nicht übernommen. Bei der erneuten Prüfung wurde im heutigen Same-Cycle-Retry ein eigener Reentranzfehler gefunden; der aktuelle Schnitt ergänzt einen Guard im vorhandenen Scheduler samt reproduzierender Regression. |
| **#187: Hebeltrader** | Eigenständiger, nicht integrierter Strategieumfang. Sinnvolle Bausteine und konkrete Blocker unten; keine neuen Strategie-Endpunkte, keine neue Anlageoberfläche und keine Aktivierung. |

Der Scheduler-Guard verhindert, dass ein Rescan während eines bereits laufenden
Discovery-Retry erneut Arbeit in derselben Quote-Lane startet. Zurückgestellte
Arbeit muss fällig bleiben. Der Nachweis gehört zu
[test_refresh_lanes.py](../../tests/unit/backend/features/market_data/test_refresh_lanes.py);
es entsteht weder ein zweiter Scheduler noch ein neuer Jobtyp.

Die Lesson-Regressionen prüfen erfolgreiche Erstellung, Fehlerfälle, verzögerten
bzw. fehlgeschlagenen Readback, Kontextwechsel und die konkrete Zielroute.
Vorhandene historische Journal-/Evidence-/Lesson-Versionen dürfen nicht durch
den aktuellen Erfolgshinweis ersetzt werden. Der native
[Journal-Browserweg](../../tests/e2e/post-trade-journal-postgres.spec.ts) bleibt
Teil der Qualifikation.

## Hebeltrader: vorhandene Grundlage und abgegrenzter Rest

[#187](https://github.com/burckhju/trading-workspace/pull/187) ist am geprüften
Head `bad00a420f56994216ad1def6a580b00b0f5772f` weiterhin Draft. Sein Diff umfasst
16 Dateien und 3.237 zusätzliche Zeilen; die spezifischen Strategie-Module sind
nicht Main. Die neue Oberfläche erzeugt nach Bestätigung einen manuellen
TradePlan-Draft über den bestehenden Create-Endpunkt. Der sichtbare
`execution_enabled=False`-Hinweis ersetzt deshalb nicht die Prüfung dieses
neuen fachlichen Anlagewegs.

Bereits vorhanden und wiederzuverwenden sind:

- [PDF-Parser](../../backend/app/features/learning/application/hebeltrader_parser.py),
  [bestätigter Mehrdateiimport](../../backend/app/features/learning/application/bulk_import_service.py)
  und unveränderliche `ExternalObservationVersion` mit Dateinachweis; kein
  zweiter Import und keine automatische Umwandlung in Trades.
- [TradePlan-Versionen und Approval](../../backend/app/features/trade_plan/domain/models.py)
  sowie [ProductSelection](../../backend/app/features/product_selection/domain/models.py)
  mit konkreten Warrant-/TermsVersion-/Listing-Bezügen.
- Das vorhandene
  [Vanilla-Bewertungsmodell](../../backend/app/features/analysis/domain/vanilla_iv.py)
  und [produktgebundene Bewertungsbelege](../../backend/app/features/product/service/valuation_evidence.py).
  Der zusätzliche Call-Rechner aus #187 würde ein zweites Modell mit anderem
  FX-/Numerik-Scope einführen und wird nicht übernommen.
- [PriceBinding](../../backend/app/features/trade_position/domain/price_binding.py)
  und der [bestehende Preisresolver](../../backend/app/features/position_monitoring/service/rule_prices.py).
  Unbestätigte oder fremde Preisachsen bleiben blockiert.

Als spätere technische Bausteine sind die serverseitige Auflösung einer
bestätigten Importversion, die strikte Decimal-/Quellenvalidierung und die
getrennte Anzeige von Aktien- und Optionsscheinmarken sinnvoll. Sie werden hier
nicht als ungenutzte zweite Bibliothek oder aktive Strategieoberfläche eingebaut.

| Restblocker | Konkrete Voraussetzung für eine spätere Integration |
|---|---|
| Daten- und Identitätsbindung | Freie Levels, Währungen und Kalenderlisten aus #187 müssen an die vorhandenen Preis-, Produkt-, Terms- und Listing-Verträge angebunden werden. Die heutige [IV-Readiness](../../backend/app/features/position_monitoring/service/iv_readiness.py) benennt fehlende synchronisierte Basiswertquotes, Provider-IV/Greeks, Zins-/Dividendenannahmen und ungeprüfte Sitzungskalender ausdrücklich; diese Lücken werden nicht geschätzt. |
| Abgrenzung der Rekonstruktion | #187 beschreibt die B-Formel als unbekannt und den nie sinkenden Folgestopp als eigene Konsistenzentscheidung. Die zulässige Verwendung dieser rekonstruierten/eigenen Annahmen ist vor einer aktiven Draft-/Managementintegration konkret festzuhalten. Historische Quellenanzeige, Szenariorechnung und aktuelle Einstiegs-/Managementfreigabe bleiben getrennt. |
| Tatsächlicher Code von #207 fehlt | [#207](https://github.com/burckhju/trading-workspace/pull/207), Head `85921b9a6db30028a25b9c69a3e9a97a50482c10`, enthält im Remote-Diff ausschließlich einen 40-zeiligen Entwicklungshilfsworkflow. Der im PR beschriebene lokale 62-Dateien-Implementierungsbaum ist hier nicht verfügbar. Zuerst ist dieser prüfbare Code erforderlich. Die dort behauptete frühere fachliche Bestätigung wird weder widerrufen noch als neuer Nachweis dieses Audits ausgegeben. |
| Aktuelle Integrationsqualifikation | Konflikte mit heutiger TradePlan-Oberfläche auflösen, vorhandene Bewertung und Preisbindung wiederverwenden, dann den tatsächlichen Integrationsstand mit den unveränderten Projektgates prüfen. Alte grüne PR-Läufe reichen dafür nicht. |

[#197](https://github.com/burckhju/trading-workspace/pull/197), Head
`08d2a5c9abe91ef518eb2c940eff9bbeceb073f8`, enthält Research-Workflow,
Kursdatenkollektoren, öffentliche Symbolkennungen und Tests. Das ist keine
produktive Historienanbindung und kein aus vollständigen Quellen qualifizierter
Backtest. Private Quellen werden nicht gesucht, rekonstruiert oder hochgeladen.

## Weitere offene Dokumentations-PRs

| PR / geprüfter Head | Relevanz für diesen Integrationsschritt |
|---|---|
| [#268](https://github.com/burckhju/trading-workspace/pull/268), `eec41d6e00957625f9c836be4857ad08dbee5002` | Drei Dokumente zur Auslieferung und begrenzten Abnahme von v1.5.11. Keine Laufzeitfunktion. Historische PC-/Bediennachweise werden hier weder nachgetragen noch auf v1.5.28 oder den neuen PR übertragen; die alten Dokumentfassungen werden nicht über heutige Backlog-/Traceability-Änderungen kopiert. |
| [#220](https://github.com/burckhju/trading-workspace/pull/220), `40da0f23dea50cf6c70f1232f61ffd83f825dd19` | Drei Recherche-/Probe-Dokumente zu Quellenständen vom September. Main enthält inzwischen [gettex](../../backend/app/providers/gettex_delayed/adapter.py), [JPMorgan](../../backend/app/providers/jpmorgan/adapter.py), [Morgan Stanley](../../backend/app/providers/morganstanley/adapter.py) und Retention. Die alte Recherche ist keine heutige Live-Coverage-/Zustimmungsfreigabe und begründet keine erneute Adapterimplementierung. |
| [#205](https://github.com/burckhju/trading-workspace/pull/205), `ba7f442a027c55fd3bb15ed6f77271690c8a9055` | Tatsächlicher Diff: Positionschart-Konzept und zwei Entwicklungs-Hilfsworkflows; keine Runtime-Implementierung. Main hat inzwischen dauerhafte Quote-Retention, [begrenzte Quote-Samples/Reader](../../backend/app/features/market_data/service/quote_history.py), [Lese-API](../../backend/app/features/market_data/api/quote_history.py) und [Erfassungsprotokoll-UI](../../frontend/src/features/product/components/WarrantQuoteHistory.tsx) in Produkt-/IV-Ansichten. Der historische Befund rein prozesslokaler Quotes ist überholt. Ein Positionschart wäre ein gesonderter Consumer vorhandener Quellen; kein vollständiger Kursverlauf seit Kauf ist dadurch belegt und keine zweite Historienpersistenz wird eingeführt. |

## Test- und Integrationsnachweise

### Bereits bestätigte Ausgangsbasis

Für Main `f3c067ecdfe99e46f3c8b63c37bb4d283cd5a568` wurden folgende abgeschlossene
Workflows mit Ergebnis `success` abgerufen:

- [Backend 40645641949](https://github.com/burckhju/trading-workspace/actions/runs/40645641949)
- [Frontend 40645641935](https://github.com/burckhju/trading-workspace/actions/runs/40645641935)
- [End-to-End 40645641957](https://github.com/burckhju/trading-workspace/actions/runs/40645641957)
- [Version tag 40647604340](https://github.com/burckhju/trading-workspace/actions/runs/40647604340)

Auch der alte #187-Head `bad00a420f56994216ad1def6a580b00b0f5772f` besitzt
erfolgreiche [Backend](https://github.com/burckhju/trading-workspace/actions/runs/34690488439)-,
[Frontend](https://github.com/burckhju/trading-workspace/actions/runs/34690488560)-
und [E2E](https://github.com/burckhju/trading-workspace/actions/runs/34690488455)-Läufe.
Das korrigiert die alte offene CI-Aussage in seiner Beschreibung, qualifiziert
aber weder den heutigen Main-Testmerge noch die Strategie fachlich.

### Erster lokal belegter Stand (Head `77506c35`, vor der ersten PR-CI)

- Backend: die fünf Scheduler-Suiten einschließlich neuer Regression bestehen mit
  **56 Tests**. Die neue Regression scheitert auf der ursprünglichen Implementierung
  mit vier statt zwei Quote-Aufrufen und besteht mit dem Guard. Ruff, Black und
  mypy über den gesamten Backend-Prüfumfang sind erfolgreich.
- Der reguläre lokale Backend-Gesamtlauf endet mit **3.194 bestanden, 148
  übersprungen und 64 Setup-Fehlern** (449,30 s). Die 64 Fehler stammen aus den
  vorhandenen Learning-/PostTrade-PostgreSQL-Fixtures: ohne isolierte Test-URL
  verweigern sie bewusst den Start. Mit den fehlenden Datenbankfällen erreicht
  dieser Lauf nur **84,02 % Coverage** und verfehlt die unveränderte
  **85-%-Grenze**. Dies ist **kein grüner Backend-Gesamtlauf**.
  Ein ausschließlich in Scratch vorbereiteter PostgreSQL-Aufbau wurde wegen
  fehlender Berechtigung zum Anlegen der benötigten Gerätedateien nicht gestartet;
  bestehende Verzeichnisrechte, Fixtures und Systeminstallation bleiben unverändert.
  Der vollständige Datenbanknachweis muss am neuen PR-Head mit PostgreSQL 17 erfolgen.
- Frontend: **1.696 Tests in 145 Dateien** bestehen. Coverage: **95,71 %** Zeilen
  und Statements, **90,70 %** Funktionen, **89,85 %** Branches. Die vorhandenen
  Mindestgrenzen 80/80/80/70 bleiben unverändert. TypeScript, ESLint, Prettier und
  Produktionsbuild sind erfolgreich.
- Browserregressionen am lokalen Produktionsbuild: **20 bestanden, ein bestehender
  nativer PostgreSQL-Fall planmäßig nicht lokal ausgeführt**. Geprüft wurden
  `post-trade-handoff-pin`, `lesson-detail-consolidation`, `post-trade-journal-ui`,
  `performance-workspace-ui` und `reference-data-consolidation`. Die beiden
  erweiterten nativen Journal-/FT011-Journeys gehören zusätzlich in die reguläre
  isolierte Owner-CI; synthetische Browserantworten ersetzen diesen Nachweis nicht.
- Versionsprüfung: `node --test .github/tests/version-tag.test.cjs` erfolgreich
  (ein TAP-Test mit den vorhandenen Veröffentlichungsszenarien). Alle fünf
  Versionsfelder sind unverändert konsistent `1.5.28`; `git diff --check` besteht.

Reproduzierbare Umgebungsgrenzen: Die vorinstallierte Node-24-Laufzeit verursachte
AbortSignal-/Navigationfehler und keinen regulären Testabschluss. Mit dem
vorgegebenen **Node 22.16.0 / npm 10.9.2** bestehen die unveränderten betreffenden
Tests. Die normale Sandbox blockierte außerdem den vorhandenen Backend-TestClient;
derselbe Test und die Scheduler-Suite bestehen außerhalb dieser Sandbox.
Ein erster Browserlauf verwendete eine unpassende API-Basis; ein weiterer am
Entwicklungsserver zählte zusätzliche React-StrictMode-Lesezyklen. Der erfolgreiche
Nachweis oben verwendet die tatsächliche lokale API-Basis und den Produktionsbuild.
Keine Tests oder Assertions wurden dafür abgeschaltet. Docker ist lokal nicht
vorhanden; der lokale Release-Voraussetzungscheck meldet dies ausdrücklich.

### Review-Nachbesserung am 28.10.2026

Die unabhängige Nachprüfung von PR #295 auf Head `77506c35` fand einen konkreten
Lesson-Lifecycle-Fehler: Nach bestätigter Erstellung konnte der gemeinsame
Discard beim Wechsel einer Journalversion innerhalb desselben Trades den Erfolg
zurücksetzen. Der Elternmarker hielt die Komponente gleichzeitig offen; dadurch
verschwand die Öffnen-Aktion und ein weiteres Erstellungsformular wurde freigegeben.
Ein gezielter Reproduktionstest wies einen zweiten nicht idempotenten POST nach.

Der Discard-Effekt erhält jetzt bestätigte Erstellungen, solange die gebundene
Evidence unverändert ist. Ungespeicherte Eingaben, unbekannte Mutationsergebnisse,
Pending-Sperren und echte Quellenwechsel behalten ihre bisherigen Regeln. Die
Korrektur liegt ausschließlich in der gemeinsamen Lesson-Komponente; es gibt
keinen zusätzlichen Elternzustand und keine neue Oberfläche.

Der Fehler wurde vor der Korrektur sowohl im Komponententest als auch in drei
DataRouter-Fällen (vorhandene, leere und fehlgeschlagene Referenzantwort) und im
Browser gegen den alten Produktionsbuild nachgewiesen. Die Browserregression
verwendet echte Journalbearbeitung, Versionsauswahl, Abbruch des Navigationsdialogs
und anschließendes bewusstes Verwerfen. Sie verlangt den erhaltenen Erfolgslink,
die unveränderte vollständige Lesson-ID und keinen weiteren POST.

Mit der Korrektur bestehen die **65 gezielten Tests** der gemeinsamen Komponente,
des Journals und beider Post-Trade-Seitensuiten. Wiederholtes Verwerfen bei gleicher
Evidence sowie neue Evidence mit und ohne gleichzeitiges Verwerfen sind ausdrücklich
abgesichert. Der neue Produktionsbuild besteht; **12 Browserfälle** aus Handoff,
Journal und Lesson-Detail bestehen ohne Skips oder Wiederholungen.

Der erste vollständige Frontend-Nachlauf hatte **1.700 bestandene Tests und einen
Fehler** im vorhandenen Produktauswahl-Test. Die Ursache wurde getrennt geklärt:
Nach einem bestätigten Selection Run konnte dessen Vergleich kurz vor dem Wechsel
zur kanonischen Run-URL sichtbar sein. Der Test wartete nur auf diese Überschrift
und griff im folgenden Kontextwechsel auf vorübergehend ausgeblendete Aktionen zu.
Die Testkorrektur wartet gemeinsam auf die exakte Run-URL und beide bedienbaren
Produktaktionen. Fachliche Assertions zu Warnstatus, Begründung, ausdrücklicher
Auswahl und BUY-Erfassung bleiben erhalten; Produktlogik und Berechnungen werden
dafür nicht geändert.

Der anschließende vollständige Frontendlauf besteht mit **1.701 Tests in 145 Dateien**
(55,14 s). Coverage bleibt bei **95,71 %** Zeilen/Statements, **90,70 %** Funktionen
und **89,85 %** Branches; die unveränderten CI-Mindestgrenzen 80/80/80/70 wurden
ausdrücklich mitgeprüft. Typecheck, ESLint und Prettier bestehen. Der neue CI-Nachweis
wird mit dem neuen Commit und seinen Run-IDs in der PR-Beschreibung dokumentiert. Die grünen
CI-Ergebnisse des vorherigen Commits werden nicht als Prüfung dieser Nachbesserung
ausgegeben. Der Scheduler-Review ergab keinen zusätzlichen Korrekturbedarf.

### Statusgrenzen des Integrationsschnitts

| Statusstufe | Nachweis für die neuen Änderungen |
|---|---|
| Implementiert | Gemeinsame Lesson-Erfolgsaktion mit Quellen-/Readbackbindung sowie Guard gegen Scheduler-Reentranz, jeweils mit neuen Regressionen; Branch `integration/remaining-work-20261028`. |
| Lokal getestet | Die oben konkret angegebenen lokalen Prüfungen sind belegt; vollständige PostgreSQL-/Backend-Abschlusszahlen werden zusätzlich in der PR-Beschreibung geführt. |
| PR-geprüft | Die neue PR-CI muss den tatsächlichen Branch-Head prüfen. Ihre Run-IDs, Ergebnisse und eventuelle Einschränkungen stehen in der PR-Beschreibung; dieser vorbereitende Audittext behauptet keinen vorweggenommenen CI-Erfolg. |
| In Main integriert | Nein; dieser Auftrag enthält keine Mergefreigabe. |
| Veröffentlicht | Nein; keine neue Version, kein Tag oder Release für diesen Schnitt. |
| Auf dem PC installiert | Nicht durchgeführt und nicht nachgewiesen. |
| Fachlich abgenommen | Keine neue menschliche Fach-/Bedienabnahme in diesem Auftrag. Automatisierte Prüfungen werden davon getrennt ausgewiesen. |

Die neuen und vorhandenen relevanten Prüfungen müssen mit isolierten Testdaten
laufen. Fehler werden ursächlich bearbeitet; keine Abschaltung von Tests,
Coverage-Gates oder Versionsprüfungen. Handelsdaten, Buchungen, Berechnungen,
Providerzustimmungen, produktive Strategien, PC-Installation und bestehende
Nutzerbestände sind außerhalb dieses Änderungsschnitts.
