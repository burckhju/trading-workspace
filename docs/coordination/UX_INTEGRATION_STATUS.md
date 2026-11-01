# UX-Integrationsprotokoll — Phase 1

## Geltung und Nachweisgrenze

**Erneuter GitHub- und Git-Abgleich: 01.11.2026, 15:28 Uhr Europe/Berlin.** Vollständige aktuelle Diffs von #311 bis #316, Main, Tag, Reviews/Threads/Kommentare, Mergefähigkeit, Workflowversuche, einzelne Checkjobs und tatsächliche CI-Checkouts geprüft. Lokaler Klon und isolierte Prüfworktrees sind verfügbar. Maßgeblich für fachliche Aufgaben- und Abnahmestände bleibt ausschließlich [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md).

Dieses Protokoll ersetzt die überholten aktuellen Aussagen des ursprünglichen #313-Snapshots vom 31.10.2026; dessen Historie bleibt im [ursprünglichen Commit](https://github.com/burckhju/trading-workspace/tree/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination) erhalten. Nicht erneut geprüfte Alt-PRs sind keine heutige Integrationsgrundlage. Der korrigierte eigene Dokumentationshead und seine neue CI werden nach Veröffentlichung in [Draft #313](https://github.com/burckhju/trading-workspace/pull/313) gebunden; die unten genannte ursprüngliche #313-CI gilt nicht automatisch für diesen neuen Head.

## Main und Veröffentlichung

| Nachweis | Tatsächlich verifizierter Stand |
|---|---|
| Main | [`1883f7f330719453958f8be1dd51d48db816662e`](https://github.com/burckhju/trading-workspace/commit/1883f7f330719453958f8be1dd51d48db816662e), gegenüber letzter bekannter Referenz unverändert |
| Main-Tree | `e90aa341805c71362df1cda1a9dc378b0af9c4fe` |
| Version | `VERSION`, `backend/pyproject.toml`, `frontend/package.json` und Projektwerte der Lockdatei: `1.5.35` |
| Veröffentlichter Tag | [`v1.5.35`](https://github.com/burckhju/trading-workspace/tree/v1.5.35) zeigt exakt auf Main `1883f7f…`; kein neuer UX-Release |
| Main-CI | [Backend 41171213873](https://github.com/burckhju/trading-workspace/actions/runs/41171213873), [Frontend 41171213875](https://github.com/burckhju/trading-workspace/actions/runs/41171213875), [E2E 41171214040](https://github.com/burckhju/trading-workspace/actions/runs/41171214040), Event `push`, jeweils erfolgreich am genannten SHA; drei/ein/vier Jobs erfolgreich |
| Veröffentlichung | [Version tag 41172652775](https://github.com/burckhju/trading-workspace/actions/runs/41172652775), [Tagjob 124453728314](https://github.com/burckhju/trading-workspace/actions/runs/41172652775/job/124453728314), erfolgreich. Log bestätigt Veröffentlichung von v1.5.35 auf exakt diesem Main. |
| Separates GitHub-Release-Objekt | `releases/latest` und Release-Liste liefern weiterhin [`v1.0.0-product-selection`](https://github.com/burckhju/trading-workspace/releases/tag/v1.0.0-product-selection). Der bestehende [Veröffentlichungsvertrag](../releases/V1.5.35-HEBELTRADER-CONTRACT.md) verlangt keinen zusätzlichen Release-Eintrag; der Versionstag ist maßgeblich. |
| PC / Fachabnahme | Nicht geprüft und nicht aus Main/Tag/CI ableitbar. Keine Installation oder Handels-/Regelabnahme vorgenommen. |

## Aktuelle eingehende PR-Heads und Mainbezug

Alle sechs PRs: **offen, Draft, nicht gemergt, `mergeable=true`, `mergeable_state=clean`, kein Auto-Merge**. GitHub meldet bei jedem **null Reviews, null Reviewthreads und null Kommentare**. Das ist fehlende formale Zustimmung, kein positives Fachreview. Gemeinsamer Merge-Base ist exakt Main; alle haben **0 Commits Rückstand**.

| PR / Umfang | Vollständiger gelesener Head | Vorsprung / Dateien / Diff gegen Main |
|---|---|---|
| [#311](https://github.com/burckhju/trading-workspace/pull/311) — UX2-A Produktcode | `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | 5 Commits / 47 Dateien / +3461 −322 |
| [#312](https://github.com/burckhju/trading-workspace/pull/312) — UX1 Produktcode | `8f67442daac6879d7dfb28416f2171f67aead0e5` | 4 Commits / 33 Dateien / +2491 −82 |
| [#313](https://github.com/burckhju/trading-workspace/pull/313) — ursprüngliche Koordination | `2312abfe8834a1b652b100fc635c4d36172d5c32` | 1 Commits / 5 Dateien / +357 −0 |
| [#314](https://github.com/burckhju/trading-workspace/pull/314) — UX3 Vertrag/Typbeispiele, kein Runtimeimport | `52a24266dce1ec048b23360b4b75d5b3f54d746b` | 1 Commits / 10 Dateien / +2161 −0 |
| [#315](https://github.com/burckhju/trading-workspace/pull/315) — UX3-A Inventur/Vertrag | `d9d85f1af3159c4356c8773d076decbf1dc604e4` | 2 Commits / 5 Dateien / +1401 −1 |
| [#316](https://github.com/burckhju/trading-workspace/pull/316) — UX4-A Dokumentation | `ae8c792f3e3ad74994894fac581cb4cf81ba5de7` | 1 Commits / 6 Dateien / +2073 −0 |

**#313-Zeile ist der geprüfte Eingangszustand vor dieser eigenen Dokumentkorrektur.** Der fortgeschriebene Head ist im PR mit seinem neuen Testmerge/Tree und neuen Jobs auszuweisen. Alle anderen Heads werden vor Abschluss erneut gegen GitHub geprüft.

### Tatsächliche CI-Checkouts

Die Frontend-Joblogs bestätigen für jeden PR den vollständigen Checkout-SHA. Die lokal abgerufenen GitHub-Testmerges haben jeweils genau Main und den oben genannten PR-Head als Eltern. Jeder Testmerge-Tree entspricht dem jeweiligen Head-Tree; ein GitHub-Testmerge ist kein Merge nach Main.

| PR | Tatsächlich ausgecheckter Testmerge | Tree |
|---|---|---|
| #311 | `21262f3d5c18497ae3e7e88232655662c8b41d28` | `7def8301834697f7a0868551f29cb98039fb77ec` |
| #312 | `817a6762de66444127e7640650904b3af7122875` | `0ea8e9a53771578e7af9444e6d8dbc478d2725a6` |
| #313 | `ac46cb409548727eae691a925594294b2fd0cbfc` | `509f1d5943da5e05179c19387882bac933a67e7d` |
| #314 | `4b4e889904317ec1a826825311934f5caf5410b6` | `83aa7029f2ed3575b47b7f2946203a4d73c31562` |
| #315 | `5bb4ace0303b1fc5d7c72e52691ce24120747f9c` | `aa3ec2a6599f1be0a265ce61ba253e7922ad3fc7` |
| #316 | `f0f4f6746435a673b15d0c3eef4155c57c541e97` | `f0176a02ef5e31fe00744e286d1a69f938421a9f` |

### Aktuelle Einzel-PR-CI

Alle folgenden Runs erneut über GitHub abgefragt: **Event `pull_request`, Versuch 1, completed/success**, jeweilige `head_sha` exakt wie oben. Je PR **neun Prüfjobs erfolgreich**: Backend quality/issuer renderer/restrictive image, Frontend quality, E2E smoke/Performanceowner/Governanceowner/Journal-Evidenceowner, Publication Guards. Der zehnte Job `tag` ist **skipped** und zählt nicht als Test oder Veröffentlichung.

| PR | Backend | Frontend | End-to-End | Publication Guards / Tagworkflow | Frontendtestzahl aus Joblog |
|---|---|---|---|---|---|
| #311 | [41233048495](https://github.com/burckhju/trading-workspace/actions/runs/41233048495) | [41233048485](https://github.com/burckhju/trading-workspace/actions/runs/41233048485) | [41233048484](https://github.com/burckhju/trading-workspace/actions/runs/41233048484) | [41233048531](https://github.com/burckhju/trading-workspace/actions/runs/41233048531) | 1.913 / 161 Dateien bestanden |
| #312 | [41204565968](https://github.com/burckhju/trading-workspace/actions/runs/41204565968) | [41204566048](https://github.com/burckhju/trading-workspace/actions/runs/41204566048) | [41204565951](https://github.com/burckhju/trading-workspace/actions/runs/41204565951) | [41204565967](https://github.com/burckhju/trading-workspace/actions/runs/41204565967) | 1.862 / 159 Dateien bestanden |
| #313 | [41205151118](https://github.com/burckhju/trading-workspace/actions/runs/41205151118) | [41205151135](https://github.com/burckhju/trading-workspace/actions/runs/41205151135) | [41205151113](https://github.com/burckhju/trading-workspace/actions/runs/41205151113) | [41205151147](https://github.com/burckhju/trading-workspace/actions/runs/41205151147) | 1.824 / 158 Dateien bestanden |
| #314 | [41205178390](https://github.com/burckhju/trading-workspace/actions/runs/41205178390) | [41205178413](https://github.com/burckhju/trading-workspace/actions/runs/41205178413) | [41205178391](https://github.com/burckhju/trading-workspace/actions/runs/41205178391) | [41205178422](https://github.com/burckhju/trading-workspace/actions/runs/41205178422) | 1.824 / 158 Dateien bestanden |
| #315 | [41206859666](https://github.com/burckhju/trading-workspace/actions/runs/41206859666) | [41206859799](https://github.com/burckhju/trading-workspace/actions/runs/41206859799) | [41206859719](https://github.com/burckhju/trading-workspace/actions/runs/41206859719) | [41206859749](https://github.com/burckhju/trading-workspace/actions/runs/41206859749) | 1.824 / 158 Dateien bestanden |
| #316 | [41206274576](https://github.com/burckhju/trading-workspace/actions/runs/41206274576) | [41206274624](https://github.com/burckhju/trading-workspace/actions/runs/41206274624) | [41206274642](https://github.com/burckhju/trading-workspace/actions/runs/41206274642) | [41206274613](https://github.com/burckhju/trading-workspace/actions/runs/41206274613) | 1.824 / 158 Dateien bestanden |

Frontend-Logs bestätigen TypeScript, ESLint, Prettier, Coveragegate und Build. Mindestwerte bleiben 80 % Lines/Statements/Functions und 70 % Branches. #311 Smoke: 139 bestanden, fünf reguläre native Skips; #312: 130 bestanden, fünf reguläre native Skips. Diese Skips zählen nicht als Erfolge; die gesonderten nativen Ownerjobs sind ebenfalls erfolgreich. Keine Tests deaktiviert, keine Schutzregel gelockert und kein Workflow manuell neu gestartet.

Das aktive [Main-Ruleset](https://github.com/burckhju/trading-workspace/rules/20249841) verlangt unter anderem strikte aktuelle Statuschecks `Backend / quality`, `Frontend / quality`, `End-to-End / smoke`, aufgelöste Threads und PR-Integration; Löschung/Non-fast-forward sind geschützt. Die zusätzlichen vorhandenen Owner-/Sandbox-/Publication-Gates bleiben ebenfalls erhalten. Null geforderte Approvals im Ruleset sind keine vom Nutzer erteilte Mergefreigabe.

## Bewertung und belegte Korrekturen von #313

Der gesamte ursprüngliche Diff besteht aus fünf Koordinationsdokumenten. **Die Grundarchitektur ist richtig:** bestehende Domainowner bleiben erhalten, UX2 besitzt Host/Navigation, UX1 Eingaben, UX3 Hinweisdarstellung, UX4 Diagramme. Es gibt keine neue Finanzrechnung, Währungswahrheit oder fachliche Statusverwaltung; PRODUCT_BACKLOG bleibt maßgeblich.

Belegte Aktualisierungslücken und ihre Korrektur:

1. #311 ist jetzt `55072f8e…` mit 47 Dateien. Die gemeinsame Shared-Navigation und Lesson-Consumer sind bereits umgesetzt; alte erneute Implementierungsaufträge wurden entfernt.
2. #311/#312 teilen vier Dateien statt nur `TradeManagementPage.tsx`. Ein echter Textkonflikt im Performance-Service und die semantischen Host-/Testgrenzen sind mit einem eindeutigen Integrator dokumentiert.
3. UX3-/UX4-Übergaben sind mittlerweile als #314/#315/#316 vorhanden. Ihre vollständigen Diffs sind berücksichtigt; die alte Aussage fehlender Übergaben ist überholt.
4. Genau ein UX3-Vertrag wird festgelegt: #314 führt, #315 liefert Pflichtübernahmen. Vier echte Typpräzisierungen und die Inventur-/Test-/Recoveryübernahme sind als UX3-Auftrag festgehalten.
5. Dokumentintegration und spätere Produktintegration werden getrennt. #313/#316 sind unabhängig prüfbar; der gemeinsame Runtimepatch #311/#312 erhält ein eigenes zwingendes Kombinationsgate.
6. Tatsächlich beendete aktuelle CI ersetzt alte laufende Fehlersnapshots. Die eigenen neuen Dokumentänderungen benötigen trotzdem ihren eigenen Head-/Tree-/CI-Beleg.

Korrekturumfang dieses MASTER-Branches: ausschließlich dieselben fünf `docs/coordination/UX_*.md`; keine Änderung von Produktcode, Tests, Workflow, VERSION, Finanzvertrag oder PRODUCT_BACKLOG. Der vollständige Korrekturdiff ist im eigenen Draft #313 reviewbar. Unabhängige Gegenreviews für UX1/UX2, UX3 und UX4 sind in die Koordination eingeflossen; sie sind keine formalen GitHub-Approvals.

Lokale Dokumentprüfung dieser eigenen Korrektur: fünf UTF-8-Markdown-Dateien mit vollständigen Codeblöcken und finalem Zeilenumbruch; 60 lokale Linkziele einschließlich 28 Anker und 22 Tabellen ohne Befund. `git diff --check` erfolgreich; Runtime-/Test-/Workflow-/Versions-/Backlogdiff leer. Die nachfolgende neue GitHub-CI wird am finalen eigenen Head im PR gebunden.

## Entscheidungen für die übrigen PRs

| Gegenstand | Entscheidung und verbleibendes Gate |
|---|---|
| #311 / #312 | [Exakte Vier-Dateienmatrix](UX_DEPENDENCIES.md#konfliktmatrix-311312) und [gemeinsamer Vertrag](UX_SHARED_CONTRACTS.md#exakter-integrationsvertrag-ux1ux2). UX2 liefert einen additiven Shared-Zeitzonenhelper; UX1 die schmale öffentliche BUY-Previewgrenze; beide Host-/Testumfänge bleiben erhalten. Noch kein gemeinsam implementierter oder getesteter Codezustand. |
| #314 / #315 | [Ein kanonischer Hinweisvertrag](UX_SHARED_CONTRACTS.md#kanonischer-ux3-hinweisvertrag--masterentscheidung-phase-1): #314 führt; #315 bleibt Quelle. Die neuesten fünf/sieben-Arten- und Link/Read-Fragen sind bereits harmonisiert; keine veralteten Konflikte behaupten. Echte Lücken: Vor-Create-Identität, Writeoutcome, Governance-Readzustände, ausdrückliche Populationstypbindung. UX3 konsolidiert technisch. |
| #316 | [Kompatibel](UX_SHARED_CONTRACTS.md#kompatibilität-von-ux4-a--316): getrennte SELL-/Vollabschluss-Populationen, vorhandene Finanz-/Kursowner, echte Originalpunkte, Währung/Preisart, sichtbare Lücken, vorhandene Diagramme. Keine notwendige Änderung am fremden Branch belegt. Doku unabhängig integrierbar, B/C/D-Produktoberflächen bleiben abhängig von UX2-/UX3-Verträgen. |

Zusätzlicher konkreter Kombinationsbefund: #311s Browserfixture liefert für noch unbekannte Preview-GETs den generischen 503-Fallback. Der gemeinsame Navigationstest muss daher erfolgreiche Währungsvorschau, deren konstante GET-Zahl bei Hashwechsel, manuelle Code-/Notizerhaltung und alte Antworten ausdrücklich prüfen. Ein grün gebliebener Fehlerfallback qualifiziert keine Währungsherkunft.

## Tatsächlich neu ausgeführte lokale Prüfungen

| Exakter Stand | Neu ausgeführte Prüfung | Ergebnis / Grenze |
|---|---|---|
| #311 `55072f8e…`, Tree `7def8301834697f7a0868551f29cb98039fb77ec` | Node 22.16.0/npm 10.9.2, `TZ=UTC`: Shared-Navigation, TradeManagement-Kontext/Page/PriceHistory, Quellen, gesamter Performancebereich | **382 Tests in 15 Dateien bestanden**. Isolierter Head, keine Kombinationsaussage. |
| #312 `8f67442d…`, Tree `0ea8e9a53771578e7af9444e6d8dbc478d2725a6` | Gleiche Toolchain/Zone: TradeManagement, CurrencyPreview, Nachkauf, Client, ProductSelection samt Kontext, gesamter Performancebereich | **358 Tests in 16 Dateien bestanden**. Die Zahlen überlappen sich und werden nicht addiert. |
| #314 `52a24266…`, Tree `83aa7029f2ed3575b47b7f2946203a4d73c31562` | Vorhandenes `node docs/ui/ux-3/verify-docs.mjs`; Node 22.16.0, Projekt-TypeScript 5.8.3: `tsc -p docs/ui/ux-3/tsconfig.json` | **5/5 Dokumentprüfungen**, 353 lokale Dateiverweise, 80 eindeutige Inventurzeilen; strict/noEmit einschließlich 19 erwarteter negativer Typfälle erfolgreich. Kein UX3-Produkttest. |
| #316 `ae8c792f…`, Tree `f0176a02ef5e31fe00744e286d1a69f938421a9f` | Alle sechs Dateien: UTF-8/Newline/Codeblöcke/Konfliktmarker, Dateiverweise/Anker und Inventur-/Vertrags-/Abnahme-IDs | **207 lokale Dateiverweise und ein Anker**, I01–I35, V01–V14, Q01–Q26 vollständig. Kein lokaler Anwendungstest für den Dokumentationsschnitt. |
| #311–#316 | `git diff --check` gegen Main; tatsächliche Dateigrenzen und Gitbäume gelesen | Erfolgreich. #313/#314/#315/#316 verändern keine Runtime-/Test-/Workflow-Unterbäume. |
| #311 + #312 | `git merge-tree --write-tree` mit exakten Heads | Exit 1, einziger Inhaltskonflikt in `performanceReportContext.ts`; kein qualifizierter Integrationsbaum, kein Branchmerge. |
| Ursprünglicher #313 + #316 | Reiner Dreiwegevergleich ohne Branchänderung | Konfliktfrei; Tree `542cef50e90083ab2af77ed3fc511f82fbc7510c`. Der korrigierte #313 wird separat erneut gegen #316 geprüft. |
| #311 + #316 | Reiner Dreiwegevergleich ohne Branchänderung | Konfliktfrei; Tree `6359f73e999d1e9fbe871c921c3e9d02fd2fe4b2`. Kein kombinierter UX1/UX2-Nachweis. |

Der erste lokale #311-Prozesslauf lieferte keinen vollständigen Abschluss; nach gezieltem Beenden des eigenen Prozesses wurde derselbe unveränderte Umfang erfolgreich wiederholt. Nur der abgeschlossene Lauf zählt. SHA-256 der abgeschlossenen lokalen Logs: #311 `c9cf085e132e8f55c8bbb91bcdcba7c1a29cbfdb5f4fe585b36e496d42382156`, #312 `b9fcc5e35dc50bcf47a9a8069da64613c27053a57de39fb6911e92847246327e`.

### Reproduktion der gezielten lokalen Produktprüfungen

Jeweils im `frontend` des exakten PR-Heads, Node 22.16.0/npm 10.9.2, `TZ=UTC`, unveränderte Lockdatei:

```bash
# #311
npm test -- src/shared/trade-workspace-navigation src/features/trade/services/workspaceNavigation.test.ts src/features/trade/pages/TradeManagementContext.test.tsx src/features/trade/pages/TradeManagementPage.test.tsx src/features/trade/pages/TradeManagementPriceHistory.test.tsx src/features/trade/components/TradeSourcesView.test.tsx src/features/performance
# #312
npm test -- src/features/trade/pages/TradeManagementContext.test.tsx src/features/trade/pages/TradeManagementPage.test.tsx src/features/trade/pages/TradeManagementPriceHistory.test.tsx src/features/trade/components/ExecutionCurrencyPreview.test.tsx src/features/trade/components/AdditionalPurchasePanel.test.tsx src/features/trade/services/client.test.ts src/features/product_selection/pages/ProductSelectionPage.context.test.tsx src/features/product_selection/pages/ProductSelectionPage.test.tsx src/features/performance
```

Keine lokale PostgreSQL-/E2E-Ausführung oder vollständige lokale Coverage für diese erneuten gezielten Produktchecks behauptet. Die oben belegte GitHub-CI enthält die vollständigen regulären Einzel-PR-Gates. Geplante UX3-/UX4-Abnahmefälle und die noch nötige gemeinsame UX1/UX2-Regressionsmatrix sind keine bestandenen Tests.

## Getrennte Liefer- und Abnahmestufen

| Stufe | Befund dieser Phase |
|---|---|
| Implementiert | UX2-A und UX1 im jeweiligen Featurebranch; Koordination, UX3-Entwürfe und UX4-A als Dokumentation. Gemeinsamer Helper-/Adapter-/UX3-Konsolidierungspatch noch Aufgabe der zuständigen Leads. |
| PR-geprüft | Vollständige Diffs und aktuelle isolierte CI oben geprüft; lokale gezielte Checks durchgeführt. Korrigierter #313 benötigt seinen gesonderten finalen PR-Beleg. Kein formales Approval und keine gemeinsame Produktabnahme behauptet. |
| Main-integriert | Keiner der PRs #311–#316; Main bleibt `1883f7f…`. |
| Veröffentlicht | Vorhandene Version `v1.5.35`; keine der neuen UX-Änderungen dadurch veröffentlicht. |
| PC-installiert | Nicht nachgewiesen; kein PC-Zugriff/Update. |
| Fachlich abgenommen | Nicht nachgewiesen; CI und Dokumentvertrag ersetzen keine menschliche Fachabnahme. |

## Genau ein nächster Integrationsschritt

**Den korrigierten eigenen Draft #313 mit seinem finalen Head, unveränderter aktueller Mainbasis und vollständig erfolgreicher eigener CI zur ausdrücklichen Mergefreigabe vorlegen.** Das ist der erste kontrollierte Integrationsschnitt: ausschließlich Koordinationsdokumentation. Ohne diese Freigabe bleibt er Draft und ungemergt. Die weiteren Schritte und präzisen Rollenaufträge stehen in [UX_DEPENDENCIES](UX_DEPENDENCIES.md#integrationsreihenfolge-phase-1); sie sind keine parallelen Sofortaufträge zum Merge.
