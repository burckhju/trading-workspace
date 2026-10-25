# Begrenzte Restprüfung der PRs #204, #225, #235 und #90

## Datierte Fortschreibung — 25.10.2026, A: Navigation

Der folgende Bericht beschreibt weiterhin ausschließlich den Prüfstand vom
20.10.2026. Inzwischen enthält Main `fbd77fb94947a1fdbfc0aeb90811353fae655a59`
(v1.5.14) den Quellenmodus-/Pacing-Schnitt **#271** sowie die gemeinsame
Finanz-/Journalqualifikation **#273 einschließlich #269/#270/#272** und den
Proposal-Kontextschutz **#274/#275**. Der unten als offen beschriebene
Quellenmodus-/Pacing-Anteil von #225 ist damit zeitlich überholt; seine alte
CI-Aufteilung wird durch diese Feststellung weder übernommen noch freigegeben.
Die [Pacing-Nachprüfung vom 21.10.2026](MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md)
und die aktuellen Releasebelege bleiben die passenden Quellen.

#204 bleibt der bestehende Navigationsbranch. Die aktuelle konfliktfreie
Main-Integration, erhaltenen Formularinvarianten und neuen Nachweise stehen in
der [Fortschreibung der Navigationsqualifikation](../implementation/UNDERLYING_NAVIGATION_QUALIFICATION.md).
Die historischen Konflikt- und Testaussagen weiter unten sind keine Aussagen
über den neuen Integrationslauf. #225, #235 und #90 wurden durch A weder
geschlossen noch gemergt. Der neue Candidate-Governance-Strang B bleibt getrennt.

## Historischer Bericht vom 20.10.2026

Prüfdatum: 20.10.2026. Vergleichsbasis ist `main` bei
`5e9ede2dc29f52eaff601d30614df6bc9c25c426` (Tree
`303e56c078efd578e6e147edcf2ebac6accf6ba5`, veröffentlichter Stand v1.5.11).
Diese Prüfung erklärt Codeunterschiede und verbleibenden Umfang. Der maßgebliche
Aufgabenstatus bleibt im [Product Backlog](../planning/PRODUCT_BACKLOG.md).
Sie erteilt keine Freigabe zum Schließen, Mergen oder Ersetzen eines PRs.

## Ergebnis

| PR und geprüfter Head | Einordnung | Konkreter Rest |
|---|---|---|
| [#204](https://github.com/burckhju/trading-workspace/pull/204), `3a2dd4823aa2ff8b0b44d23655bab3a0e443efaa` | **eigenständiger offener Umfang** | Listenrücksprung ist auf der Vergleichsbasis nicht enthalten. Vorhandene Lösung mit aktuellen Formularschutzregressionen integrieren, Rücksprungziele und Browserfixture qualifizieren. Lokale Umsetzung und ihre Grenzen stehen in der [Navigationsqualifikation](../implementation/UNDERLYING_NAVIGATION_QUALIFICATION.md). |
| [#235](https://github.com/burckhju/trading-workspace/pull/235), `86314c869147e6eba81c79fd7c2c88a28d6fa155` | **vollständig anderweitig umgesetzt** | Discovery-Lane und gezielter Same-Cycle-Retry sind enthalten; der aktuelle Retry berücksichtigt zusätzlich den Beginn des Quote-Auftrags. Kein verbleibender Funktionsdiff dieses PRs gefunden. |
| [#225](https://github.com/burckhju/trading-workspace/pull/225), `79f607810196f172870a7127567f25109916e06a` | **teilweise relevant mit genau benanntem Rest** | Lane-/Retry-Anteil enthalten. Die frühere Beschränkung des Frankfurt-Pacings auf `PUBLIC_WEBSITE` ist im heutigen providerbezogenen Aufruf nicht äquivalent enthalten. Dieser kleine Quellenmodus-Unterschied braucht gesonderte fachliche/technische Bewertung; die alte allgemeine Backend-CI-Aufteilung bleibt ebenfalls außerhalb des Navigationsauftrags. |
| [#90](https://github.com/burckhju/trading-workspace/pull/90), `7383e8edb965a7d2590cef2c8262e1407482336f` | **teilweise relevant mit genau benanntem Rest** | Erstellen, Readback und Aufruf der Lesson sind in beiden heutigen Consumern vorhanden. In der Kindkomponente verbleibt die kompaktere Erfolgsmeldung mit Kurzreferenz, eigenem Link und aufklappbarer UUID. Kein vollständiger Neuaufbau der Lesson-Navigation erforderlich. |

Die Einordnung beruht auf PR-Metadaten, tatsächlichen Diffs und aktuellem Code;
Testdateien wurden als zugehörige Verträge gelesen. Die Backend-Lane- und
PostgreSQL-Journaltests wurden im Rahmen dieser Triage nicht neu ausgeführt.
Ihr Vorhandensein ist kein neu erhobener Laufnachweis.

## #204: bestehende Navigation behutsam fortführen

Der GitHub-PR ist weiterhin offen und Draft. Die abgerufenen Reviews und
Review-Threads waren leer; daraus folgt keine Reviewfreigabe. Sein vorhandener
Diff umfasst elf Dateien: Listen-/Detail-/Formularnavigation, URL-Helfer,
zugehörige Tests und das FT-001 Feature Book. Gegenüber aktuellem Main ist der
Listenrücksprung weiterhin eigenständig; #249/#267 haben den Formularschutz
geliefert, aber diesen Rücksprung nicht ersetzt.

Die historischen Check-Runs des ursprünglichen PR-Heads sind getrennt vom
lokalen integrierten Stand zu behandeln:

| Historischer Check auf `3a2dd482…` | Ergebnis und Quelle |
|---|---|
| Frontend quality | Erfolg, [Run 34768146142 / Job 103752763270](https://github.com/burckhju/trading-workspace/actions/runs/34768146142/job/103752763270) |
| Backend quality | Erfolg, [Run 34768146134 / Job 103752760236](https://github.com/burckhju/trading-workspace/actions/runs/34768146134/job/103752760236) |
| Backend restrictive umask | Erfolg, [Run 34768146134 / Job 103752760410](https://github.com/burckhju/trading-workspace/actions/runs/34768146134/job/103752760410) |
| E2E smoke | Fehler, [Run 34768146144 / Job 103752766598](https://github.com/burckhju/trading-workspace/actions/runs/34768146144/job/103752766598) |

Der [PR-Kommentar zum alten Browserlauf](https://github.com/burckhju/trading-workspace/pull/204#issuecomment-5654574060)
ordnet drei Fehler der Fixture zu: Der Build verwendet `/api/api/v1`, die alte
Fixture erwartete teilweise `/api/v1`. Die dort genannten 40 Tests mit 37 Erfolgen
und drei Fehlern sowie Artefakt `10321490353` und Report-SHA256
`23321539a840477380670023b06fca9f0298a7d2fbd5f28773b12aba9f6058e3` sind historische,
im Kommentar dokumentierte Angaben. Das Artefakt wurde für diese Triage nicht
erneut heruntergeladen. Ein leerer kombinierter Commit-Status ersetzt diese
einzelnen Check-Runs nicht.

### Integrationsentscheidung

Der vorhandene Branch `fix/underlying-list-return` bleibt erhalten. Main wird als
zweiter Elternstand integriert; kein Reset, Rebase oder Kopieren der vollständigen
alten Formularseite. Konflikte betreffen `UnderlyingFormPage.tsx` und `FEATURE.md`.
Im Formular bleiben die aktuelle instanzgebundene Identität, der stabile
Vorschlagssnapshot, frühe Deaktivierung, geladene Version, Ladefehler-Sperre und
synchrone Submit-Sperre erhalten. `returnTo` wird separat als Navigation geführt.
Die Featurebeschreibung erhält sowohl die bestehenden Schutzregeln als auch den
Rücksprungvertrag.

Die aktuelle Browserfixture leitet Origin und API-Präfix aus derselben expliziten
Build-Basis ab. Nur statische Frontenddateien dürfen das eigene Testfrontend
erreichen; API, Mutation, Fetch/XHR und fremde URLs werden synthetisch abgefangen.
Unbekannte Requests erzeugen einen Fehler und werden im Testreport ausgewiesen.
Das tatsächliche Präfix wird geprüft und dokumentiert; Produktionsrouting und
Proxykonfiguration bleiben unverändert.

Quellen: [ursprünglicher PR-Head](https://github.com/burckhju/trading-workspace/tree/3a2dd4823aa2ff8b0b44d23655bab3a0e443efaa),
[aktuelle Formisolation](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/frontend/src/features/market/pages/UnderlyingFormIsolation.test.tsx),
[Browser-Formisolation](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/tests/e2e/underlying-form-isolation.spec.ts),
[Release-Nachweis v1.5.11](../releases/V1.5.11-UNDERLYING-FORM-ISOLATION.md).

## #235: Discovery und Quote-Retry bereits enthalten

Der PR ändert `refresh.py` und `test_refresh_lanes.py`. Die konkrete Lösung
ergänzt `WARRANT_DISCOVERY`, ordnet Frankfurt-/Vontobel-Mappingjobs dieser Lane zu
und führt nach erfolgreicher Discovery einen begrenzten Retry für zuvor fehlende
Quotes aus. Diese Elemente sind in Main bereits vorhanden: `RefreshLane`,
`_job_lane`, `_run_lane` und `_retry_quotes_after_discovery`.

Der heutige Retry ist darüber hinaus zeitlich präziser. Er vergleicht
`quote_started_at = quote_job.get("started_at", quote_job.get("checked_at"))`
mit dem erfolgreichen Discovery-Abschluss. Dadurch wird auch der Fall erfasst,
in dem ein leerer Quote-Read vor dem Mapping beginnt und erst danach endet. Der
alte PR verglich allein den Abschlusszeitpunkt des Quote-Jobs.

Die aktuelle Testdatei prüft die Lane-Zuordnung, Fortschritt während blockierter
Discovery sowie
`test_same_cycle_discovery_retries_quote_that_missed_before_mapping` mit
`finish_after_discovery=False` und `True`. Weitere Fälle sichern unabhängige
Underlying-Arbeit, begrenzte Lane-Worker und den Leader-/Shutdown-Lebenszyklus.
Der Nachfolger `0c2097517885c9c8b9aba41db28ae42f24a2a426` ergänzt ausdrücklich
den begonnenen Quote-Read und den nativen parallelen Discovery-Nachweis.

Quellen: [PR-Quelle refresh.py](https://github.com/burckhju/trading-workspace/blob/86314c869147e6eba81c79fd7c2c88a28d6fa155/backend/app/features/market_data/service/refresh.py),
[heutiger Scheduler](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/backend/app/features/market_data/service/refresh.py),
[heutige Lane-Tests](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/tests/unit/backend/features/market_data/test_refresh_lanes.py),
[Integrationsnachfolger](https://github.com/burckhju/trading-workspace/commit/0c2097517885c9c8b9aba41db28ae42f24a2a426).

## #225: vorhandene Lane-Trennung vom Pacing-Rest unterscheiden

Der PR enthält neben Lane-/Retry-Code einen zusätzlichen Pacing-Filter und eine
allgemeine Backend-Workflowänderung. Die Lane-/Retry-Teile sind aus den bei #235
genannten Gründen bereits vorhanden.

Der alte `_should_pace_frankfurt_quote(venue_mic)` verlangt gleichzeitig
`venue_mic == "XFRA"` und `FrankfurtSourceMode.PUBLIC_WEBSITE`. Heute wählt
`_warrant` aktive, validierte Provider-Mappings und ruft `resolve_selected`
providerbezogen auf. Unzugeordnete oder deaktivierte Routen verursachen keinen
Quote-Aufruf und kein pauschales Frankfurt-Warten. Frankfurt, Vontobel, gettex und
Issuer sind dadurch genauer getrennt als in der alten generischen
`_resolver.resolve`-Schleife.

Der **genaue verbleibende Unterschied** ist der Quellenmodus einer aktiven
`FRANKFURT_QUOTES`-Route: Der aktuelle Aufruf von `_pace()` prüft den vorhandenen
Frankfurt-Container, aber nicht `PUBLIC_WEBSITE`. `HTTPS_JSON` und `LOCAL_FILE`
sind ebenfalls definierte Modi. Damit ist die vollständige alte Bedingung nicht
äquivalent übernommen. Das beweist noch keinen reproduzierten Betriebsfehler:
Vor einer Änderung sind die beabsichtigten Intervalle und Snapshot-Limits je
Quellenmodus zu klären und getrennt zu testen. Den alten MIC-Filter unverändert
über den heutigen Providerselektor zu kopieren wäre keine sichere Integration.

`test_unmapped_routes_are_skipped_and_issuer_routes_are_isolated` prüft heute,
dass Issuer nicht auf Frankfurt-Pacing warten, inaktive/unvalidierte Mappings
übersprungen werden und nur die aktive Frankfurt-Route `_pace()` aufruft.
Der Test variiert nicht die drei Frankfurt-Quellenmodi. Die alte Testdatei
`test_refresh_lane_isolation.py` prüft nur eine öffentliche XFRA- gegen eine
XSTU-Notierung und ersetzt diesen fehlenden Modusvergleich ebenfalls nicht.

Die Backend-CI-Aufteilung aus dem PR ist ein eigener Infrastrukturvorschlag.
Sie ist weder Voraussetzung für die heutige Lane-Trennung noch Bestandteil der
Navigation. Aktuelle Workflows werden für diese Triage nicht ersetzt.

Quellen: [PR-Quelle refresh.py](https://github.com/burckhju/trading-workspace/blob/79f607810196f172870a7127567f25109916e06a/backend/app/features/market_data/service/refresh.py),
[alter Isolationstest](https://github.com/burckhju/trading-workspace/blob/79f607810196f172870a7127567f25109916e06a/tests/unit/backend/features/market_data/test_refresh_lane_isolation.py),
[heutiger Provider-/Lane-Test](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/tests/unit/backend/features/market_data/test_issuer_refresh_lane.py),
[Frankfurt-Quellenmodi](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/backend/app/core/config/frankfurt.py).

## #90: vorhandene Lesson-Kette und enger Darstellungsrest

Der PR verändert die Erfolgsmeldung von `LessonDraftFromEvidence` und ihren Test:
eine `LS-…`-Kurzreferenz, ein direkter Lesson-Link und eine aufklappbare vollständige
UUID. Die heutige Kindkomponente zeigt weiterhin die UUID. Daraus folgt jedoch
kein unterbrochener Gesamtweg:

1. `LessonDraftFromEvidence` verwendet `lessonDraftClient.createFromEvidence`,
   speichert die zurückgegebene Lesson-ID und ruft `onCreated(lesson_id)` auf.
2. `PostTradeLearningPage` übergibt `refreshLessonReferences`. Dessen
   Aktualisierung löst `lessonReadbackClient.listForEvidence` aus. Der Readback
   zeigt vorhandene Lessons mit Titel, Zustand und `/lessons/{id}`-Link; Lade-,
   Fehler- und bewusster Wiederholungszustand sind vorhanden. Solange der Readback
   läuft, wird kein neues paralleles Erstellungsformular angeboten.
3. `TradeJournalPanel` verwendet `onCreated={setLessonId}` und zeigt danach
   „Angelegte Lesson öffnen“ auf `/lessons/{id}`.
4. Der Router ordnet `lessons/:lessonId` der `LessonDetailPage` zu. Die gesonderte
   FT-011-Historie verlinkt außerdem die konkrete historische Version mit
   `lesson_version_id` und `#lesson-history`.

Der aktuelle `PostTradeLearningPage.test.tsx` prüft den vorhandenen Lesson-Link
und das Ausblenden einer erneuten Erstellung für bereits interpretierte Evidence.
Der vorhandene native Journal-Browserfall erstellt eine Lesson, liest sie über
die API zurück und nutzt den angezeigten Link. Seine historische Versionsprüfung
gehört zum bestehenden Journal-/Evidence-Vertrag, nicht zu einem neu eingeführten
PR-#90-Navigationspfad.

Der verbleibende mögliche UX-Schnitt ist deshalb ausschließlich die lokale
Erfolgsmeldung der Kindkomponente: Kurzreferenz, direkt dort sichtbarer Link und
UUID-Details. Bei späterer Umsetzung die funktionierenden Consumer-Readbacks und
historischen Zieladressen erhalten; kein neues Lesson-Backend erforderlich.

Quellen: [alter Komponentendiff](https://github.com/burckhju/trading-workspace/pull/90/files),
[aktuelle Kindkomponente](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/frontend/src/features/learning/components/LessonDraftFromEvidence.tsx),
[Post-Trade-Consumer](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx),
[Journal-Consumer](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/frontend/src/features/learning/components/TradeJournalPanel.tsx),
[Consumer-Tests](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/frontend/src/features/post_trade/pages/PostTradeLearningPage.test.tsx),
[Journal-Browserfall](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/tests/e2e/post-trade-journal-postgres.spec.ts).
