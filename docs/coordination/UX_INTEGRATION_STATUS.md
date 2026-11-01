# UX-Integrationsprotokoll — Phase 1

## Technischer Snapshot nach v1.5.37

**Erneuter GitHub-Abgleich: 01.11.2026, 21:20 Uhr Europe/Berlin.** Der Ausgangsnachweis von 20:35 Uhr wurde anhand aktueller Main-/Tagrefs, Git-Objekte, PR-Zustände, Dateidiffs, Reviewthread sowie tatsächlicher Run-/Jobergebnisse und Checkoutlogs erneut geprüft. Die Codebelege für Adapter, Helper, Host, Previewfix und kanonischen UX3-Vertrag wurden gelesen. Maßgeblich für fachliche Arbeits- und Abnahmestände bleibt ausschließlich [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md#pflegevertrag-und-statusbedeutung).

Während der regulären CI des ersten eigenen Dokumentationsheads `9acf98bcfdf411c1fbee14e0b5ca96de7b4e59cd` wurde #319 integriert. Dessen neun erfolgreiche Prüfjobs am alten Testmerge `8166475402ad05a8a8eaa9f855c5c7043626bc2c` bleiben vorheriger Nachweis; sie qualifizieren nicht automatisch den jetzt auf aktuellen Main fortgeschriebenen Head. Der bestehende eigene Draft #321 wird fortgesetzt.

Dieser Lauf schreibt nur die fünf Koordinationsdateien technisch fort. Keine lokalen Produkt-/PostgreSQL-/E2E-Tests oder PC-Prüfungen wurden dafür ausgeführt. Vorhandene GitHub-Ausführung und neue Dokumentprüfung sind getrennte Nachweise. Die frühere Prüfung von 15:28 Uhr bleibt unten ausdrücklich historisch erhalten; ihre damaligen offenen Integrationsaufträge gelten nicht weiter als heutiger Befund.

### Main, finaler Integrationsstand und Tag

| Nachweis | Tatsächlich verifizierter Stand |
|---|---|
| Aktueller Main / Dokumentmerge #319 | [`484143d33aa5f2d443da6b2edf097ae1cb5aee3a`](https://github.com/burckhju/trading-workspace/commit/484143d33aa5f2d443da6b2edf097ae1cb5aee3a), Tree `08aaa9d41e64abd5021a391a9e6a1ebb6fbc8778`; integriert am **01.11.2026, 21:06:41 Uhr Europe/Berlin**. Eltern `bb49ffe…` und `5e58fc4…`; ausschließlich zwei Dokumentdateien zusätzlich zum Tag. |
| Veröffentlichter Produktmerge / tatsächlicher #318-Merge | [`bb49ffe781933270746b9f86f4aee99b6f8144c2`](https://github.com/burckhju/trading-workspace/commit/bb49ffe781933270746b9f86f4aee99b6f8144c2); #318 integriert am 01.11.2026 um **19:26:06 Uhr Europe/Berlin** |
| Finaler #318-Head | `54eaba19fc626194237e8280af2e6cc315b1bac7` |
| Qualifizierter PR-Testmerge | [`341f9a031928268827710186446268217770e1ac`](https://github.com/burckhju/trading-workspace/commit/341f9a031928268827710186446268217770e1ac) |
| Eltern von Testmerge und tatsächlichem Mainmerge | Jeweils `d80bd45d84d845aa920a7eac5b19a7fe6cd63307` und `54eaba19fc626194237e8280af2e6cc315b1bac7`; die historische `base.sha` im PR ersetzt diese tatsächlich geprüfte Basis nicht |
| Gemeinsamer Tree | `a924db2985cba84f37952faef6b73c16be8984ed`, identisch in finalem #318-Head, Testmerge und veröffentlichtem #318-Produktmerge; nicht mehr der vollständige Tree des aktuellen Dokumentmains |
| VERSION / veröffentlichter Tag | [VERSION](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/VERSION) = `1.5.37`; separat gelesener [Tag `v1.5.37`](https://github.com/burckhju/trading-workspace/tree/v1.5.37) zeigt exakt auf den veröffentlichten Produktmerge `bb49ffe781933270746b9f86f4aee99b6f8144c2`; aktueller Main enthält zusätzlich #319-Dokumentation |
| PC / menschliche Fachabnahme | Aus den gelesenen Quellen weiterhin **nicht nachgewiesen**. Tag, CI und synthetische Deploymenttests belegen keine tatsächliche Zielinstallation oder beobachteten Nutzerbetrieb. |

Die erhaltene Abstammung ist zusätzlich durch Git-Vergleiche belegt: Der finale #311-Head `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` und finale #312-Head `b1df1c1000815786a6623d35bf3f8631661a9543` sind jeweils die Mergebase ihres Vergleichs mit Main. GitHub führt beide als integriert mit Mergecommit `bb49ffe…` (19:26:08 Uhr). Der alte #312-Prüfhead `8f67442d…` bleibt ausschließlich historischer Einzelnachweis.

### Tatsächliche PR-Zustände

| PR | Gelesener finaler bzw. aktueller Head | Zustand / Integration |
|---|---|---|
| [#313](https://github.com/burckhju/trading-workspace/pull/313) — Masterkoordination | `958bf9e9e554953bbb7a465c1dfdc863abd6ebed` | Geschlossen, integriert über `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35` |
| [#316](https://github.com/burckhju/trading-workspace/pull/316) — UX4-A-Vertrag | `82b11711a70aacf39fddf59a6545662fb7102b92` | Geschlossen, integriert über `5f2e12667759bfb54eb14f39c6d8426c9cd8080f` |
| [#314](https://github.com/burckhju/trading-workspace/pull/314) — kanonischer UX3-K-Vertrag | `cc547ef662d1bc28315d25df1930c32b94278d6b` | Geschlossen, integriert über `d80bd45d84d845aa920a7eac5b19a7fe6cd63307`; vier Typpräzisierungen und Quellenübernahmen enthalten |
| [#311](https://github.com/burckhju/trading-workspace/pull/311) — UX2-A | `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | Geschlossen, `merged=true`, über erhaltene Abstammung in #318/Main `bb49ffe…` enthalten; historisches Draftflag ist keine offene Produktintegration |
| [#312](https://github.com/burckhju/trading-workspace/pull/312) — UX1 | `b1df1c1000815786a6623d35bf3f8631661a9543` | Geschlossen, `merged=true`, über erhaltene Abstammung in demselben #318/Mainmerge enthalten |
| [#318](https://github.com/burckhju/trading-workspace/pull/318) — gemeinsame Integration | `54eaba19fc626194237e8280af2e6cc315b1bac7` | Geschlossen, integriert über `bb49ffe781933270746b9f86f4aee99b6f8144c2`, gemeinsam als `v1.5.37` veröffentlicht |
| [#315](https://github.com/burckhju/trading-workspace/pull/315) — UX3-Quelle | `d9d85f1af3159c4356c8773d076decbf1dc604e4` | Bewusst offen und Draft; kein zweiter normativer Hinweisvertrag, keine Schließung durch MASTER |
| [#319](https://github.com/burckhju/trading-workspace/pull/319) — UX1-Dokumentnachtrag | `5e58fc49781e0b944d94edcf2b298336051955c8` | Geschlossen, integriert über `484143d33aa5f2d443da6b2edf097ae1cb5aee3a`; zwei Dokumentdateien, kein Produktfix |
| [#320](https://github.com/burckhju/trading-workspace/pull/320) — bestehender UX3-B1/F1-Pilot | `71e971a67be7f1ca10192e04e3832f843b8099bd` | Offen und Draft auf `484143d…`; 18 Dateien, eigene Produktprüfung erforderlich. Vorbereitete `v1.5.38`-Dateien sind keine Veröffentlichung. |
| [#322](https://github.com/burckhju/trading-workspace/pull/322) — lokale UX4-B-Serienwahl | `e3365df7afc70ec52fe6fb19aabc4050250091e3` | Offen und Draft auf `484143d…`; zwei History-Komponenten-/Testdateien, eigene Produktqualifikation noch offen |

Bei Arbeitsbeginn existierte kein entsprechender offener Master-Dokumentations-PR; inzwischen wird der eigene [Draft #321](https://github.com/burckhju/trading-workspace/pull/321) fortgesetzt. Die erneut gelesenen offenen Fremd-PRs einschließlich #315, #320, #322 und der Alt-PRs #187/#197/#205/#207/#220 verändern keine der fünf Koordinationsdateien. #319 ist integriert; #320 verändert am aktuellen Head weder Backlog noch kanonische UX3-Dokumente. Die frühere #319/#320-Backlogüberschneidung galt für den Snapshot von 20:52 Uhr. Weitere Dateiarbeit jeweils am aktuellen Head prüfen. Ein Repositorylink ist ein Übergabeangebot und kein bestätigter Empfang in einem anderen Chat.

### Implementierung, Reviewfix und finale gemeinsame Qualifikation

BUY-only-`InitialPurchaseCurrencyPreview`, einmaliger Shared-`reportTimezoneError`, beide Host-/Performance-Testumfänge und die erfolgreiche Preview-Fixture sind im aktuellen Main vorhanden. Die alten Adapter-/Helper-/Host-/Fixtureaufträge sind damit technisch abgeschlossen. Codeanker und unveränderte Schutzgrenzen stehen in [UX_SHARED_CONTRACTS](UX_SHARED_CONTRACTS.md#exakter-integrationsvertrag-ux1ux2); die frühere Vier-Dateienmatrix bleibt in [UX_DEPENDENCIES](UX_DEPENDENCIES.md#konfliktmatrix-311312) historisch nachvollziehbar.

Der [Fix `86472f3571c127f6234b89ede08ac18fbd3adb48`](https://github.com/burckhju/trading-workspace/commit/86472f3571c127f6234b89ede08ac18fbd3adb48) verwirft abgeschlossene alte Previewergebnisse beim Wechsel des Eingabetupels. Die drei Regressionen sichern alten A-Erfolg, alten A-Fehler und den bewusst geöffneten leeren Override. Der finale Head `54eaba19…` enthält diesen Fix und die separat qualifizierte E2E-Synchronisation in `tests/e2e/support/trade_source_journey.ts`: begrenztes Warten auf Linkgeometrie bei Remount/Reflow und Prüfung der exakten Ziel-URL einschließlich Journalversion. Die finalen normalen Gates liefen anschließend erneut.

Der [Reviewthread mit Abschlusskommentar 4436821052](https://github.com/burckhju/trading-workspace/pull/318#discussion_r4436821052) ist direkt als `is_resolved=true`, `is_outdated=false` gelesen; Thread-ID `PRRT_kwDOToYiZM6yc1-x`. Abschlusskommentar: 01.11.2026, 19:25:38 Uhr Europe/Berlin. Ein aufgelöster Thread ersetzt weder die unten separat belegte CI noch menschliche Fachabnahme.

### Finale PR-CI von #318

Alle vier Runs: Event `pull_request`, Versuch 1, Head `54eaba19fc626194237e8280af2e6cc315b1bac7`, abgeschlossen erfolgreich. Die Checkoutlogs aller neun ausgeführten Prüfjobs bestätigen **Testmerge `341f9a031928268827710186446268217770e1ac`**. Der zusätzliche Tagjob ist regulär übersprungen und zählt nicht als Veröffentlichung.

| Prüfung / Run | Tatsächliche Jobs und Ergebnis |
|---|---|
| Backend [41335256321](https://github.com/burckhju/trading-workspace/actions/runs/41335256321) | Quality [124933693629](https://github.com/burckhju/trading-workspace/actions/runs/41335256321/job/124933693629), restrictive-umask [124933693890](https://github.com/burckhju/trading-workspace/actions/runs/41335256321/job/124933693890), renderer sandbox [124933694011](https://github.com/burckhju/trading-workspace/actions/runs/41335256321/job/124933694011): alle erfolgreich |
| Frontend [41335256433](https://github.com/burckhju/trading-workspace/actions/runs/41335256433) | Quality [124933606533](https://github.com/burckhju/trading-workspace/actions/runs/41335256433/job/124933606533) erfolgreich |
| E2E [41335256250](https://github.com/burckhju/trading-workspace/actions/runs/41335256250) | Realized gross [124933605940](https://github.com/burckhju/trading-workspace/actions/runs/41335256250/job/124933605940), candidate [124933606078](https://github.com/burckhju/trading-workspace/actions/runs/41335256250/job/124933606078), smoke [124933606172](https://github.com/burckhju/trading-workspace/actions/runs/41335256250/job/124933606172), journal/evidence [124933606742](https://github.com/burckhju/trading-workspace/actions/runs/41335256250/job/124933606742): alle erfolgreich |
| Publication Guards [41335256299](https://github.com/burckhju/trading-workspace/actions/runs/41335256299) | Guards [124933606056](https://github.com/burckhju/trading-workspace/actions/runs/41335256299/job/124933606056) erfolgreich; Tagjob [124933646279](https://github.com/burckhju/trading-workspace/actions/runs/41335256299/job/124933646279) übersprungen |

Ausführungslogs: **3.880 Backendtests**, **1.981 Frontendtests in 164 Dateien**, darunter 15 Previewtests, erfolgreich. Smoke **143 bestanden / 5 regulär übersprungen**; die ausgelagerten Ownerfälle bestehen separat: Realized Gross zweimal ein Fall, Journal/Evidence zwei Fälle, Candidate ein Fall. Keine Skips als Erfolge zählen. Letzter PR-Runabschluss: **19:23:32 Uhr Europe/Berlin**.

### Tatsächliche Main-Push-CI des veröffentlichten Produktstands

Alle drei Runs: Event **`push`**, Versuch 1, Head **`bb49ffe781933270746b9f86f4aee99b6f8144c2`**, abgeschlossen erfolgreich. Die Logs aller acht Produktjobs bestätigen den tatsächlichen Maincheckout; dies ist ein eigener Nachweis zusätzlich zur PR-CI.

| Prüfung / Run | Tatsächliche Jobs | Abschluss am 01.11.2026, Europe/Berlin |
|---|---|---|
| Backend [41336601722](https://github.com/burckhju/trading-workspace/actions/runs/41336601722) | [124937641378](https://github.com/burckhju/trading-workspace/actions/runs/41336601722/job/124937641378), [124937641587](https://github.com/burckhju/trading-workspace/actions/runs/41336601722/job/124937641587), [124937641620](https://github.com/burckhju/trading-workspace/actions/runs/41336601722/job/124937641620): drei erfolgreich | 19:48:02 Uhr |
| Frontend [41336601804](https://github.com/burckhju/trading-workspace/actions/runs/41336601804) | [124937641585](https://github.com/burckhju/trading-workspace/actions/runs/41336601804/job/124937641585) erfolgreich | 19:30:05 Uhr |
| E2E [41336601617](https://github.com/burckhju/trading-workspace/actions/runs/41336601617) | [124937641397](https://github.com/burckhju/trading-workspace/actions/runs/41336601617/job/124937641397), [124937641400](https://github.com/burckhju/trading-workspace/actions/runs/41336601617/job/124937641400), [124937641440](https://github.com/burckhju/trading-workspace/actions/runs/41336601617/job/124937641440), [124937641485](https://github.com/burckhju/trading-workspace/actions/runs/41336601617/job/124937641485): vier erfolgreich | 19:29:54 Uhr |

Mainlogs bestätigen erneut 3.880 Backendtests, 1.981 Frontendtests, Smoke 143 bestanden/fünf übersprungen und erfolgreiche ausgelagerte Ownerfälle. Typprüfung, Lint, Formatierung, Coverage und Build sind erfolgreich. Deployment-/Migrationsmeldungen der Sandboxjobs gehören zur synthetischen Runnerumgebung; sie sind kein PC- oder JMBbot-Betriebsbeleg.

Für den aktuellen Dokumentmain `484143d…` liefern Actions, Check-Runs und einzelne Commitstatus **keine neuen Läufe**. Dies entspricht den direkt gelesenen bestehenden Push-Pfadfiltern von [Backend](https://github.com/burckhju/trading-workspace/blob/484143d33aa5f2d443da6b2edf097ae1cb5aee3a/.github/workflows/backend.yml), [Frontend](https://github.com/burckhju/trading-workspace/blob/484143d33aa5f2d443da6b2edf097ae1cb5aee3a/.github/workflows/frontend.yml) und [E2E](https://github.com/burckhju/trading-workspace/blob/484143d33aa5f2d443da6b2edf097ae1cb5aee3a/.github/workflows/e2e.yml): Die beiden #319-Dokumentpfade lösen keine Produkt-Push-CI aus. Pull-Request-Prüfungen bleiben ungefiltert. Der Publisher hat keinen eigenen Push-Trigger. Die vollständige #319-PR-CI und die Produkt-Main-CI auf `bb49ffe…` bleiben getrennte Nachweise; ein aggregiertes `pending` bei null Commitstatus ist kein laufender Test.

### Publisher und unabhängiger Tagref

[Publisher 41338459285](https://github.com/burckhju/trading-workspace/actions/runs/41338459285): Event `workflow_run`, Versuch 1, Head `bb49ffe781933270746b9f86f4aee99b6f8144c2`, erfolgreich. [Publication Guards 124943177313](https://github.com/burckhju/trading-workspace/actions/runs/41338459285/job/124943177313) bestätigen diesen Checkout und 9/9 Tests. Der [Tagjob 124943214386](https://github.com/burckhju/trading-workspace/actions/runs/41338459285/job/124943214386) ist **tatsächlich ausgeführt und erfolgreich**; sein Log bestätigt um **19:48:20 Uhr Europe/Berlin** die Veröffentlichung von `v1.5.37` auf genau diesem vollständig getesteten Main. Runabschluss: **19:48:22 Uhr**. Der anschließend separat gelesene Tagref stimmt überein.

Ein zusätzlicher nativer GitHub-Releaseobjekt-Nachweis wird in diesem Snapshot nicht behauptet. Sicher belegt sind VERSION, erfolgreiche Tagpublikation und passender Tagref. PC-Installation und menschliche Fachabnahme folgen daraus nicht.

### Getrennter UX1-Dokumentationsnachtrag #319

Head `5e58fc49781e0b944d94edcf2b298336051955c8`, Basis `bb49ffe781933270746b9f86f4aee99b6f8144c2`, Testmerge `d90ce507e401db7957c05b0dc19e0a93a4ea8fd0`, identischer Head-/Testmerge-Tree `08aaa9d41e64abd5021a391a9e6a1ebb6fbc8778`. Der tatsächliche Diff betrifft ausschließlich `docs/implementation/UX1_INPUT_REUSE_QUALIFICATION.md` (+98) und PB-016 Eröffnung in `docs/planning/PRODUCT_BACKLOG.md` (+10/−2). Der Nachtrag ist seit 21:06:41 Uhr über `484143d…` im Main enthalten; dessen Tree entspricht dem qualifizierten #319-Head/Testmerge. Beide Dateien bleiben vollständig außerhalb dieses Master-Diffs.

| Aktuelle #319-CI am genannten Head, jeweils `pull_request` / Versuch 1 | Jobs |
|---|---|
| Backend [41342474542](https://github.com/burckhju/trading-workspace/actions/runs/41342474542) erfolgreich | [124955216998](https://github.com/burckhju/trading-workspace/actions/runs/41342474542/job/124955216998), [124955217207](https://github.com/burckhju/trading-workspace/actions/runs/41342474542/job/124955217207), [124955217233](https://github.com/burckhju/trading-workspace/actions/runs/41342474542/job/124955217233) |
| Frontend [41342474532](https://github.com/burckhju/trading-workspace/actions/runs/41342474532) erfolgreich | [124955216750](https://github.com/burckhju/trading-workspace/actions/runs/41342474532/job/124955216750) |
| E2E [41342474484](https://github.com/burckhju/trading-workspace/actions/runs/41342474484) erfolgreich | [124955216797](https://github.com/burckhju/trading-workspace/actions/runs/41342474484/job/124955216797), [124955217003](https://github.com/burckhju/trading-workspace/actions/runs/41342474484/job/124955217003), [124955217063](https://github.com/burckhju/trading-workspace/actions/runs/41342474484/job/124955217063), [124955217123](https://github.com/burckhju/trading-workspace/actions/runs/41342474484/job/124955217123) |
| Guards [41342474531](https://github.com/burckhju/trading-workspace/actions/runs/41342474531) erfolgreich | [124955217062](https://github.com/burckhju/trading-workspace/actions/runs/41342474531/job/124955217062); Tagjob [124955253895](https://github.com/burckhju/trading-workspace/actions/runs/41342474531/job/124955253895) übersprungen |

Frontend- und Guard-Checkoutlogs bestätigen `d90ce507…`. Letzter Runabschluss: **20:48:17 Uhr Europe/Berlin**. Der inzwischen integrierte Dokumentationsnachtrag ist kein Produktfix und begründet keinen neuen fachlichen Status. Die frühere offene Draft-Einordnung bleibt mit ihrem Zeitpunkt historisch.

### Tatsächlich vorhandene Folgearbeit

Der vorhandene UX3-B1/F1-Draft [#320](https://github.com/burckhju/trading-workspace/pull/320), aktueller Head `71e971a67be7f1ca10192e04e3832f843b8099bd` auf `484143d…`, ist die nächste begrenzte Präsentationsprüfung. Sein 18-Dateien-Diff enthält Produktcode, Tests, Qualifikation und vorbereitete Versions-/Releasebelege; Backlog und die sechs vormals geänderten kanonischen UX3-Dokumente sind aus dem Diff entfernt. Im Snapshot sind [Frontend 41345560327](https://github.com/burckhju/trading-workspace/actions/runs/41345560327), [E2E 41345560368](https://github.com/burckhju/trading-workspace/actions/runs/41345560368) und [Guards 41345560328](https://github.com/burckhju/trading-workspace/actions/runs/41345560328) erfolgreich; [Backend 41345560403](https://github.com/burckhju/trading-workspace/actions/runs/41345560403) läuft noch. Testmerge `0dfc3a6ea56694a6c49477f06fbea100298a01ba`, Tree `8ff96a7a9bf0e725d983d5cc0e9e329612cd9a4a`. Dies ist keine vollständige Master- oder Integrationsfreigabe.

Der frühere #320-Head `36522cdb8ca6a202950e459f07616483258927a8` mit 25 Dateien gehört zum Snapshot von 20:52 Uhr. Sein [Backendrun 41343090757](https://github.com/burckhju/trading-workspace/actions/runs/41343090757) wurde abgebrochen; alte grüne Einzelruns qualifizieren den neuen Head nicht.

Zusätzlich liegt [UX4-B-Draft #322](https://github.com/burckhju/trading-workspace/pull/322) am Head `e3365df7afc70ec52fe6fb19aabc4050250091e3` vor: ausschließlich `PositionPriceHistory.tsx` und dessen Test, ohne Überschneidung mit #320 oder den fünf Masterdateien. [Frontend 41345202499](https://github.com/burckhju/trading-workspace/actions/runs/41345202499) ist fehlgeschlagen; E2E/Guards sind erfolgreich, Backend läuft im Snapshot noch. Keine Fehlerursachen- oder Gesamtproduktabnahme dieses Piloten in diesem Dokumentlauf.

UX4-B/C/D bleiben eigenständige, konkret abhängige Darstellungsaufträge; insbesondere Änderungen an `RealizedGrossSources`/`ReportSourceEntry` mit #320 abstimmen. Kein zweiter B1/F1-Pilot und keine zusätzliche Lock-/Statusdatenbank. [Owner und Dateiabstimmung](UX_OWNERSHIP.md#dateiabstimmung), [begrenzte Folgeaufträge](UX_DEPENDENCIES.md#präzise-folgeaufträge).

### Getrennte Liefer- und Abnahmestufen nach v1.5.37

| Stufe | Technischer Befund dieses Snapshots |
|---|---|
| Implementiert | Gemeinsamer begrenzter UX1/UX2-A-Schnitt einschließlich Adapter, Helper, Host-/Fixtureintegration und Reviewfix; UX3-K/UX4-A als kanonische Dokumentverträge. Keine pauschale Freigabe von UX1-B/C/D, UX2-B/C/D oder späteren UX3-/UX4-Produktoberflächen. |
| PR-geprüft | Finaler #318-Head am tatsächlichen Testmerge mit allen neun regulären Prüfjobs qualifiziert; finale E2E-Synchronisation enthalten. |
| Main-integriert | #313, #316, #314 und die gemeinsame #318-Integration; #311/#312 über erhaltene Abstammung im Produktmerge enthalten; #319 anschließend als Dokumentation im aktuellen Main integriert. |
| Veröffentlicht | `v1.5.37` auf `bb49ffe…`, getrennte erfolgreiche Mainprüfungen, Publisher und Tagref belegt. |
| PC-installiert | Weiterhin nicht nachgewiesen; kein PC-Zugriff oder Update in diesem Lauf. |
| Menschlich fachlich abgenommen | Aus diesen Quellen weiterhin nicht nachgewiesen; fachliche Arbeits-/Abnahmestände ausschließlich im PRODUCT_BACKLOG. |

### Prüfung und Übergabe dieses Dokumentationslaufs

Die fünf Koordinationsdateien werden als eigener Dokumentationsschnitt ab frisch geprüftem Main fortgeschrieben. Normative Owner-/Schutzgrenzen bleiben erhalten; Produktcode, Produktregressionen, Workflows, Versionen, Tags, Migrationen, Finanzverträge und Backlog sind außerhalb des Diffs. Die lokale Dokumentprüfung ist erfolgreich: fünf UTF-8/LF-Dateien mit finalen Newlines, 76 lokale Linkziele einschließlich 36 Anker, 28 Tabellen sowie vollständiger Fünf-Dateien-Diff und `git diff --check` ohne Befund. Die ursprünglichen fünf Dokumentblobs stimmen exakt mit der Mainbasis überein; die normativen Ownership-Tabellen sind unverändert. Eigener Branch, finaler Head/Testmerge/Tree und die **eigene reguläre PR-CI** werden im zugehörigen Draft-PR gebunden; die oben gelesenen Produkt-/Dokumentationsruns ersetzen diese neue CI nicht.

Keine Merges, Releases, Tags, PC-Updates, produktiven Datenänderungen oder PR-Schließungen durch diesen Auftrag. Ein grüner Dokumentations-PR erteilt keine Freigabe für #320 oder andere Produktschnitte.

### Genau ein nächster Integrationsschritt

**Den bereits vorhandenen UX3-B1/F1-Draft #320 am dann aktuellen Head gegen den integrierten kanonischen Vertrag und den tatsächlichen Main prüfen, einschließlich seiner eigenen vollständigen CI und der begrenzten Quellen-/Aktions-/Ownerregressionen.** Keine erneute Verteilung der abgeschlossenen UX1/UX2-Aufträge, kein zweiter Pilot und keine aus diesem Dokumentationsauftrag abgeleitete Mergefreigabe.

## Historischer Snapshot vom 01.11.2026, 15:28 Uhr

Die folgende frühere Prüfung bleibt als Herkunftsnachweis erhalten. **Alle dortigen Angaben „aktuell“, „neu“, „offen“ und „nächster Schritt“ beziehen sich ausschließlich auf den damaligen Stand `1883f7f…` / `v1.5.35`.** Alte CI, lokale Prüfläufe, Headzahlen und Integrationshindernisse sind keine Nachweise des heutigen Heads und keine erneut zu verteilenden Aufträge. Die damalige Schlussanweisung zu #313 ist durch dessen erfolgte Integration erledigt.

<details>
<summary>Historische Belege vom 01.11.2026, 15:28 Uhr Europe/Berlin</summary>

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

## Historische Schlussanweisung zu #313 — erledigt

Der damalige Auftrag, den korrigierten Draft #313 mit eigener grüner CI zur ausdrücklichen Mergefreigabe vorzulegen, ist durch die Integration über `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35` erledigt. Er ist keine heutige Schlussanweisung. Der aktuelle nächste begrenzte Prüfpunkt steht im technischen Snapshot nach `v1.5.37`.

</details>
