# UX4-B — Quellenwahl und eindeutige Originalbelege

## Abschlussnachtrag vom 03.11.2026 — integriert und technisch qualifiziert

**UX4-B ist in Main enthalten; ein zusätzlicher UX4-B-Produktfix ist nach diesem
Abgleich nicht erforderlich.** [PR #322](https://github.com/burckhju/trading-workspace/pull/322)
ist geschlossen und gemergt, seit **01.11.2026, 22:52:54 Uhr Europe/Berlin**.
Die erneute Prüfung liest tatsächliche GitHub-Metadaten, Gitobjekte, Joblogs,
das konkrete Playwright-Artefakt und den Maincode. Sie führt keine neue lokale
UX4-B-Testsuite aus und erteilt keine menschliche Fach- oder Bedienabnahme.

### Exakter Integrationsstand

| Bezug | Verifizierter Stand |
| --- | --- |
| Main bei dieser UX4-B-Abschlussprüfung / tatsächlicher Merge #322 | [`3397399e7bf8364501437f9509a4fb18dbe32c08`](https://github.com/burckhju/trading-workspace/commit/3397399e7bf8364501437f9509a4fb18dbe32c08) |
| Main vor Integration / erster Merge-Elterncommit | `849a6d54eaeb5f5831754c6b15a41358c571f6da` |
| Finaler PR-Head / zweiter Merge-Elterncommit | `d3c12f105fbd643f5579e23e00b4cca978229184` |
| Tatsächlicher Checkout aller neun regulären PR-Prüfjobs | [`1fc6f408894f6c26b942439dfe93ba526ffff5d1`](https://github.com/burckhju/trading-workspace/commit/1fc6f408894f6c26b942439dfe93ba526ffff5d1) |
| Identischer vollständiger Tree von PR-Head, CI-Testmerge und Mainmerge | `c9362029d9fc3a1d0ccf7bee4e1f5b942e474807` |

Nach dieser Prüfung wurde UX3-B2 #324 am 03.11.2026 um 05:47:53 UTC unabhängig
von diesem Auftrag in Main integriert: `7399bccaf0c2923327b15ee43cfbc484e7cd3b30`.
Die sieben geänderten Dateien betreffen Produktbewertung, ihre Tests und UX3-Dokumente;
UX4-B-Code und seine Nachweise bleiben unverändert. Die nachstehende historische
Main-CI gehört weiterhin ausdrücklich zum UX4-B-Merge `3397399e…`. Die kombinierte
UX4-C-Qualifikation auf der neueren Mainbasis ist im eigenständigen Draft dokumentiert.

Der [integrierte Diff](https://github.com/burckhju/trading-workspace/compare/849a6d54eaeb5f5831754c6b15a41358c571f6da...3397399e7bf8364501437f9509a4fb18dbe32c08)
enthält 24 Dateien: lokale Historienkomponenten und Präsentationshelfer,
zugehörige Tests, Dokumentation und synthetische Nachweise. Enthalten sind
Quellenwahl nach historischer Serienidentität, einzeln erreichbare überlagerte
Originalbelege, paginierter Tastaturzugang, getrennte Währungen und Zeitbezüge,
sichtbare Begrenzungs-/Ausschlussgründe sowie lokaler Import-/Renderausfallschutz.
Die vollständige Originaltabelle und Ereignisliste bleiben auch ohne Chart
bedienbar. Diese Funktionen werden für UX4-C nicht erneut implementiert.

Dieser UX4-B-Diff ändert weder Backend noch Finanzberechnung, historische
Kursdaten, API/Reader, Persistenz, Hostintegration, Navigation, Dependencies,
Versionen oder Workflows. Main enthält bereits die vorherigen UX2-/UX3-
Integrationen; deren Änderungen werden UX4-B nicht zugerechnet.

### Tatsächliche finale PR-CI und nachgelagerte Main-CI

Alle vier finalen PR-Workflows sind im ersten Versuch erfolgreich: **neun
reguläre Prüfjobs**, dazu der auf PRs bestimmungsgemäß übersprungene Tagjob.
Die Checkoutlogs aller neun Jobs bestätigen `1fc6f408…`; die Ergebnisse gehören
zum PR-Head `d3c12f105…` über diesen Testmerge. Die vollständige Treegleichheit
mit Main ist unabhängig von den Statuslabels geprüft.

| Finaler PR-Workflow | Direkt aus Jobs/Logs geprüfter Nachweis |
| --- | --- |
| [Frontend 41352906300](https://github.com/burckhju/trading-workspace/actions/runs/41352906300) | TypeScript, ESLint, Prettier und Build erfolgreich; **2.082 Tests in 169 Dateien**. Coverage Statements/Lines **96,04 %**, Branches **90,46 %**, Functions **91,60 %**. |
| [Backend 41352906162](https://github.com/burckhju/trading-workspace/actions/runs/41352906162) | Alle drei Jobs erfolgreich; Quality: **3.880 bestanden, 0 Skips**, eine Warnung, Coverage **88,04 %** bei unverändertem 85-%-Gate. Renderer-Sandbox und Umask-Image erfolgreich. |
| [End-to-End 41352906157](https://github.com/burckhju/trading-workspace/actions/runs/41352906157) | Alle vier Jobs erfolgreich; Smoke **154 bestanden / 5 vorgesehene Skips**. Alle fünf ausgelagerten Datenbankjourneys bestehen in den drei Ownerjobs: Candidate **1**, Journal/Evidence **2**, SELL/Vollabschluss **1 + 1**. |
| [Versionsschutz 41352906155](https://github.com/burckhju/trading-workspace/actions/runs/41352906155) | **9 Publication-Guardtests bestanden**, keine Fehler/Skips; veröffentlichender Tagjob auf dem PR übersprungen. |

Der [Backend-Qualityjob](https://github.com/burckhju/trading-workspace/actions/runs/41352906162/job/124986802622)
enthält `database/test_position_price_history_postgres.py ..`: beide lokal
übersprungenen Historienfälle liefen hier tatsächlich erfolgreich. Das bleibt
ein CI-Nachweis und wird nicht als lokaler PostgreSQL-Pass ausgegeben.

Das [Playwright-Artefakt 13102077057](https://github.com/burckhju/trading-workspace/actions/runs/41352906157/artifacts/13102077057)
wurde erneut heruntergeladen und ausgewertet: **159 Tests / 159 Ergebnisse**,
154 bestanden, fünf vorgesehene Skips, keine unerwarteten Ergebnisse oder Flakes,
jedes Ergebnis `retry=0`. Alle acht UX4-B-Fälle bestehen; die vollständigen
History-/Navigationssuiten umfassen **20 + 14 Pässe**. Drei native Zoom-PNGs und
beide Mess-JSONs sind byteidentisch mit Main. Gemessen sind **200 %** mit
640 CSS-Pixeln, DPR 2 und Dokumentbreite 632 sowie **400 %** mit 320 CSS-Pixeln,
DPR 4 und Dokumentbreite 320; der native 400-%-Rohwert ist
`3.9999999999999996`.

Auf dem tatsächlichen Main-Checkout `3397399…` bestehen zusätzlich der
[Frontend-Pushlauf 41354255997](https://github.com/burckhju/trading-workspace/actions/runs/41354255997)
mit 2.082 Tests / 169 Dateien und der
[E2E-Pushlauf 41354256013](https://github.com/burckhju/trading-workspace/actions/runs/41354256013)
mit 154 Smoke-Pässen, fünf vorgesehenen Smoke-Skips und allen fünf erfolgreichen
Ownerjourneys. **Ein gesonderter Backend-Pushlauf auf diesem Main-SHA existiert
nicht:** Der unveränderte
[Backend-Pfadfilter](https://github.com/burckhju/trading-workspace/blob/3397399e7bf8364501437f9509a4fb18dbe32c08/.github/workflows/backend.yml)
wird durch den UX4-B-Dateischnitt nicht ausgelöst. Die vollständige
Backendqualifikation stammt vom oben genannten identischen PR-Testmerge-Tree.

Die nachgelagerten Version-tag-Läufe
[41354516028](https://github.com/burckhju/trading-workspace/actions/runs/41354516028)
und [41354589642](https://github.com/burckhju/trading-workspace/actions/runs/41354589642)
sind erfolgreich beendet, ihre Tagjoblogs melden jedoch jeweils
`Waiting for successful backend.yml at 3397399e7bf8364501437f9509a4fb18dbe32c08`.
Das ist kein Publikationsnachweis für UX4-B. Der erneut aufgelöste
[Tag v1.5.38](https://github.com/burckhju/trading-workspace/tree/v1.5.38) zeigt
unverändert auf `849a6d54…`, also auf Main vor UX4-B. Ein Installationsstand auf
dem Nutzer-PC ist dadurch nicht belegt.

### Historische lokale Prüfungen und Sourcegleichheit

Die folgenden Läufe sind im erhaltenen Bericht dokumentiert, nicht am
03.11.2026 erneut ausgeführt. Testpopulationen verschiedener Stände werden
nicht addiert und lokale Ergebnisse nicht auf spätere vollständige Trees
umetikettiert.

| Exakter Bezug | Dokumentierte lokale Prüfung |
| --- | --- |
| `9e4f8460e3d3d69262e907eed21fbae536ebe9b8` | Frontend **1.995 / 165 Dateien**, Backend **71**, PostgreSQL **2 übersprungen**, Browser **33** ohne Retries. |
| `8ea8db66991eb27938e699b645dde2876e2a24b0` | Frontendzwischenlauf **1.998 / 166 Dateien**. |
| Folgepatch auf `7ef57c788cced3d4edf49411d421794f3bf02d99`, committed als [`e6f2b2f23eda1255b53fbc05248f2f10e1d3c19e`](https://github.com/burckhju/trading-workspace/commit/e6f2b2f23eda1255b53fbc05248f2f10e1d3c19e) | Finale lokale Prüfung: Frontend **2.082 / 169 Dateien**, Backend **71**, PostgreSQL **2 übersprungen**, Browser **34 in 48,2 s**, native 200-/400-%-Nachweise. |
| `1e1b29a69215040e823979c452a377bfe9fa671e` | Ausschließlich zwei Dokumentnachträge, kein neuer lokaler Produktlauf. |
| `d3c12f105fbd643f5579e23e00b4cca978229184` | Kombinierter Head mit Main-Versionsmetadaten 1.5.38; vollständige eigenständige CI wie oben. |

Der [Diff vom letzten lokalen Produktstand zum finalen Head](https://github.com/burckhju/trading-workspace/compare/e6f2b2f23eda1255b53fbc05248f2f10e1d3c19e...d3c12f105fbd643f5579e23e00b4cca978229184)
ist leer für `frontend/src`, `tests`, `backend/app`, `backend/migrations` und
`.github/workflows`. Die zehn geänderten Dateien betreffen Dokumentation und
Versionsmetadaten; `package.json`, Lockdatei und `pyproject.toml` ändern nur
1.5.37 auf 1.5.38, keine Dependency. Der Produkt-/Testinhalt ist gleich; der
vollständige Tree von `e6f2b2f…` ist dagegen
`00e9c2710265af3b5808200bf0a9c337f685c2bc` und wird vom finalen Tree getrennt.

### UX-2-/UX-3-Abgleich und verbleibende Abnahme

Der vorhandene [UX2-Host](https://github.com/burckhju/trading-workspace/blob/3397399e7bf8364501437f9509a4fb18dbe32c08/frontend/src/features/trade/pages/TradeManagementPage.tsx)
verwendet weiterhin den öffentlichen `PositionPriceHistory`-Export, Anker
`#position-price-history`, `tradeId`, `positionId` und
`reloadToken={historyReloadToken}`. Ein erfolgreich qualifizierter Readback
erhöht den Token; Identitäts-, Generations- und Abortprüfungen bleiben beim
Host. `PositionDetails` bleibt zusätzlicher bestehender Host. Gleicher
Trade/anderer Hash erhält Auswahl, Belegseite und Entwürfe ohne neue Reads.

Der [kanonische UX3-Vertrag](https://github.com/burckhju/trading-workspace/blob/3397399e7bf8364501437f9509a4fb18dbe32c08/docs/ui/ux-3/README.md)
aus #314 und der begrenzte B1/F1-Pilot #320 sind Mainbestand. UX4-B unterscheidet
bestätigte Leere, technischen Fehler, Begrenzung, historische Qualität und
Darstellungswahl. Die passive B1-API ist für den Kursverlauf keine zusätzliche
Abhängigkeit. Neue Qualitätsampeln, Recovery- oder Handelbarkeitsaussagen
entstehen nicht. Dieser technische Abgleich behauptet keine neue persönliche
UX2-/UX3- oder Fachownerfreigabe.

| Abnahmebereich | Vorhandener Nachweis | Weiterhin offen |
| --- | --- | --- |
| Fachlichkeit | Unveränderte Ownerwerte, Herkunft, Zeitpräzision, Währungs-/Quellentrennung und Ausschlussgründe | Menschliche Domainprüfung repräsentativer realer Fälle; tatsächliche Historienabdeckung auf dem Nutzer-PC. |
| Tastatur | Native Quellenwahl, Belegsprung und Pagination, Tab/Shift-Tab/Enter/Space, sichtbarer Fokus, Chartpfeile und chartloser Fallback automatisiert | Durchgängiger menschlicher Bedienlauf; keine vollständige Scatter-/Assistenztechniknavigation behauptet. |
| Screenreader | Semantische Tabelle, native Controls und eigenständiger Belegzugang | Tatsächlicher Screenreaderlauf einschließlich Ansagen, Fokusfolge und Live-Regionen; keine vollständige WCAG-Abnahme. |
| Mobile und Zoom | 320/390/1280 CSS-Pixel, native 200/400 %, lokale Tabellenrolle ohne horizontalen Dokumentüberlauf | Menschliche Lesbarkeits-/Touchabnahme auf realem Mobilgerät und repräsentativen Daten. |
| Integration und Bereitstellung | UX4-B in Main, identischer qualifizierter Tree | Persönliche UX2-/UX3-Abnahme sowie jede gesonderte Release-/PC-Freigabe bleiben getrennt. |

## Historischer Fortsetzungsauftrag vom 01.11.2026: Draft und vollständiger Chartausfallschutz

**Die folgenden Abschnitte bewahren den damaligen Arbeits- und Nachweisstand
vom 01.11.2026.** Aussagen wie „aktuell“, „Draft offen“ und „CI ausstehend“
beziehen sich dort auf den jeweiligen Fortsetzungslauf, nicht auf den oben
verifizierten Abschlussstand vom 03.11.2026. Die ebenfalls historisch
fortgeschriebene [Positionshistorienbeschreibung](../ui/position-price-history.md)
beschreibt den vorhandenen Darstellungsschnitt; für tatsächlichen Merge und
finale CI gilt dieser Abschlussnachtrag. Er setzt den historischen Vorschlag
#205 weder erneut um noch ändert er dessen PR-Status.

Die erneute Implementierungsfortsetzung vom 01.11.2026 verlangt ausdrücklich:
**PR #322 bleibt bis zur gesonderten Mergefreigabe Draft. Kein Merge, Release,
Deployment oder PC-Update durch diesen Auftrag.** Der nachstehende frühere
Integrationsauftrag ist ein historischer Arbeitsstand, keine Freigabe dieses
Fortsetzungslaufs.

**Aktuelle Main-Basis nach paralleler Releasefortschreibung:** Während der
abschließenden CI wurde #323 unabhängig von diesem Auftrag als
`849a6d54eaeb5f5831754c6b15a41358c571f6da` in Main integriert. Gegenüber dem
nachstehend geprüften `91ebbc0f…` ändern sich ausschließlich vier Versionsdateien
auf `1.5.38` und vier Dokumentdateien; Produktcode, Tests, Dependencies und
Workflows sind bytegleich. Dieser abschließende UX4-B-Nachtrag ändert nur die
beiden eigenen Dokumente. Er übernimmt keinen Mainmerge und ändert keine
Versionsdatei. Die reguläre CI des neuen PR-Heads muss den tatsächlichen
GitHub-Testmerge mit `849a6d54…` qualifizieren. Der zuvor geprüfte Testmerge
`44a2e7a2f1b6b8d93ef2b50eab662bc5c756e4db` bleibt seinem damaligen Main
`91ebbc0f…` zugeordnet; seine grünen Ergebnisse werden nicht auf die neuere
Main-Basis umetikettiert. Finale Commit-, Tree- und Run-Bindung steht im PR.

Zu Beginn wurden Main `e681c79e0c46a6efb9e4eeb7cd18d959ad99ea97`, der offene
Draft #322 am tatsächlichen Head `9e4f8460e3d3d69262e907eed21fbae536ebe9b8`,
seine vollständigen Änderungen und alle vier erfolgreichen CI-Workflows erneut
gelesen. Während des Abgleichs wurde #322 parallel auf
`8ea8db66991eb27938e699b645dde2876e2a24b0` und anschließend
`7ef57c788cced3d4edf49411d421794f3bf02d99` fortgeschrieben. Beide Commits
bleiben vollständig erhalten. Der zuletzt übernommene Stand enthält zusätzlich
die bereits erfolgte Main-Integration des UX3-Piloten; der neue Folgepatch setzt
ohne eigenen Mergecommit auf `7ef57c78…` auf. Die zwei eigenen Dokumentnachträge
wurden zusammengeführt und nach dem aktuellen Draftauftrag eingeordnet.

Der erneut geprüfte Main `91ebbc0f51ef000891aee7218ec6dff6a3ce2620` integriert
inzwischen #320 am Head `9e725563a5f09a6601bbe1aceee85ef32f7b7d18`. Dessen
begrenzter B1/F1-Pilot betrifft Performance und `shared/notices`; seine 16 Dateien
überschneiden sich mit keiner UX4-B-Datei. Der kanonische Hinweisvertrag ist
unverändert. Die neue schmale `NoticeCard`-API ist keine erforderliche Abhängigkeit
des vorhandenen Positionskursverlaufs. #315 bleibt ergänzende Draft-Quelle.

Der unabhängige Code-/Vertragsabgleich bestätigt die vorhandene Quellenwahl,
historischen Identitäten, überlagerten Originalbelege, Ereignisqualifikation,
UTC-Achsen, Paginierung und Requestisolation. Diese Funktionen werden nicht
erneut entwickelt. Zwei konkrete Lücken werden geschlossen:

1. **Chartausfall:** Eine lokale ErrorBoundary um den optionalen Plot fängt nun
   auch Fehler beim Rendern eines erfolgreich geladenen Chartmoduls ab. Tabelle,
   Ereignisse, Ausschlussgründe und ihre Originalwerte bleiben außerhalb dieser
   Grenze. Auch ein Importfehler erzeugt bei mehreren Währungen genau eine
   Meldung. Lade- und Renderfehler bleiben unterscheidbar. Die vorhandene
   Trade-/Position-/Reloadgrenze setzt den lokalen Fehlerzustand zurück;
   Darstellungsaktionen erzeugen keinen neuen Datenread.
2. **Hinweise bei 400 %:** V12 und Q24 verlangen ergänzend zum unveränderten
   nativen 200-%-Browserzoom einen 400-%-Nachweis für Hinweisflächen. Der bestehende
   Browserfall prüft nun auch Kürzung, unbekannte Kurszeit und date-only-Ereignisse
   bei tatsächlich gemessenem Browserzoom, sichtbarem Tastaturfokus und ohne
   horizontale Dokumentrolle oder zusätzliche API-Anfragen.

Die einzige zusätzliche Produktänderung im Folgepatch gegenüber `7ef57c78…` liegt in
`PositionPriceHistory.tsx`. Hinzu kommen der erhaltene und um Mehrwährung
erweiterte Lazytest, `PositionPriceHistoryChartError.test.tsx`, zwei gezielte
Ergänzungen der bestehenden Browserdatei sowie diese beiden UX4-B-Dokumente
und synthetische Zoomnachweise. Host, öffentliche Imports/Props, Readback,
Backend, Reader, Finanzberechnungen, Provider, Persistenz, Dependencies,
Versionsdateien und Workflows bleiben unverändert.

Die erneuten tatsächlichen Prüfungen werden unten separat vom geerbten
Nachweisstand aufgeführt. Finale SHA, aktueller Main, CI-Testmerge und reguläre
Run-/Jobergebnisse werden in der PR-Beschreibung aneinander gebunden.

## Historische Integrationsfortschreibungen 8ea8db66 und 7ef57c78

Am 01.11.2026 wurde anschließend ausdrücklich beauftragt: „Falls vorhanden
Widersprüche aufzeigen, ansonsten wenn grün mergen“. Diese bedingte Freigabe
ersetzte in jenem Arbeitsstand die ursprüngliche Beschränkung auf einen Draft. Release,
Deployment, PC-Installation und menschliche Fach-/Screenreaderabnahme bleiben
getrennte, hier nicht behauptete Nachweise.

Die erste Aktualisierung übernahm Main
`e681c79e0c46a6efb9e4eeb7cd18d959ad99ea97`, Tree
`cbae4ba7e9c030e0c7e2db3a5374e88fc8d3ac8f`: ausschließlich die fünf
#321-Koordinationsdokumente am bereits gelesenen Head
`f90ba2c1baebbe530af536348bc71d73ca0e0108`. Der daraus entstandene
UX4-B-Zwischenhead `8ea8db66991eb27938e699b645dde2876e2a24b0` wurde während
seiner CI erneut vom aktuellen Main überholt.

Die tatsächliche Integrationsbasis ist jetzt
`91ebbc0f51ef000891aee7218ec6dff6a3ce2620`, Tree
`615154d4c56284a1ade1263f85dd3fc64a284b22`. Dieser Main integriert zusätzlich
#320 am erneut gelesenen Head `9e725563a5f09a6601bbe1aceee85ef32f7b7d18`.
Der begrenzte UX3-B1-Währungsherkunftspilot, sein passiver Notice-Presenter und
seine Tests sind damit Mainbestand. B2 ist nur als getrennter Folgeauftrag
dokumentiert. Version 1.5.37 bleibt erhalten; eine Releasevorbereitung ist nicht
Teil dieses integrierten Stands.

Die 16 #320-Dateien überschneiden sich nicht mit dem UX4-B-Diff. Der Abgleich
bestätigt den lokalen Chartkorridor, den vorhandenen UX2-Hostvertrag und die
kanonische UX3-Sprache. UX4-B übernimmt keinen neuen Notice-Import und ändert
keine Performance-/Shared- oder Hostdatei. Der kanonische Hinweisvertrag wird
durch die begrenzte passive Pilot-API nicht ersetzt.

Beide Main-Aktualisierungen sind konfliktfrei. Der eigene UX4-B-Produkt-/Testcode
ist gegenüber dem qualifizierten Head `9e4f8460e3d3d69262e907eed21fbae536ebe9b8`
unverändert; hinzugekommener UX3-Produkt-/Testcode stammt ausschließlich aus dem
bereits integrierten Main. Die beiden eigenen Dokumente kennzeichnen den neuen
Auftrag und die aktualisierte Basis. Backend, Reader, Workflows, Abhängigkeiten
und Versionswerte ändern sich nicht. Es werden nur integrierte Mainstände,
keine offenen fremden Featurebranches übernommen.
Die bisherigen grünen Runs bleiben Nachweise ihres exakten früheren Stands;
der neue kombinierte Head benötigt gemäß aktivem Main-Ruleset aktuelle normale
CI. Finaler Head, Tree, tatsächlicher Testmerge, Runs und gegebenenfalls der
ausgeführte Merge werden im PR dokumentiert. Schutzregeln werden nicht umgangen.

## Ursprünglicher Auftrag und Ausgangsstand

Datum: 01.11.2026. Ursprünglicher Implementierungsauftrag für den vorhandenen
Positionskursverlauf: Draft-PR, kein Merge, Release, Deployment oder PC-Update.
Die anschließende bedingte Mergefreigabe steht oben. Repository- und Testdaten
sind kein Nachweis tatsächlich gespeicherter Kurshistorie auf dem Nutzer-PC.

Der tatsächliche Main zu Beginn ist
`484143d33aa5f2d443da6b2edf097ae1cb5aee3a`, Tree
`08aaa9d41e64abd5021a391a9e6a1ebb6fbc8778`. `VERSION`,
`frontend/package.json`, Frontendlockdatei und `backend/pyproject.toml` enthalten
`1.5.37` und bleiben unverändert. Der historische Promptstand
`1883f7f330719453958f8be1dd51d48db816662e` wurde nicht wiederhergestellt.

Zu Beginn existiert bereits [Draft #322](https://github.com/burckhju/trading-workspace/pull/322),
Branch `feat/ux4-b-position-price-visibility-20261101`, Head
`e3365df7afc70ec52fe6fb19aabc4050250091e3`, mit einem ersten Quellenfilter und
zwei Tests. Dieser eigene Arbeitsstrang wird vervollständigt. Seine drei
veröffentlichten Commits bleiben erhalten; ausschließlich der aktuelle Main
wird in einem eigenen lokalen Checkout einbezogen. Kein fremder Featurebranch
wird zur Vorbereitung gemergt und keine fremde lokale Änderung überschrieben.
Der finale Head, Tree, tatsächliche CI-Testmerge und Run-Links stehen im PR;
ein Dokument kann seine eigene spätere Commit-SHA nicht vorwegnehmen.

Keine `AGENTS.md` im Repository. Gelesen wurden README, Entwicklungsanleitung,
Coding Standards, Product Backlog, Frontendarchitektur, Teststrategie,
Positionshistorienvertrag sowie UX4-Inventur, V01–V07/V12–V14 und Prüfmatrix.
Reader, Composer und lokale Chartbausteine auf Main entsprechen weiterhin dem
historischen UX4-A-Ausgangsstand. Bestehende automatische Reads, geschlossene
Positionen, UTC-Achsen, getrennte Währungen, Markerqualifikation, Retention und
50-zeilige Originaltabelle werden wiederverwendet.

## Koordination und Integration auf dem ursprünglichen Ausgangs-Main

Die folgende Tabelle dokumentiert den zuerst geprüften Stand auf `484143d…`;
die anschließenden Integrationen von #321 und #320 sind im aktuellen
Integrationsauftrag oben gesondert ausgewiesen.

| Bezug | Exakt geprüfter Head | Integrationsstand auf dem Ausgangs-Main |
| --- | --- | --- |
| Master #313 | `958bf9e9e554953bbb7a465c1dfdc863abd6ebed` | Gemergt als `35f3ab2133fa40beb4ab2e502a08fa3bf5b44e35` |
| UX2-A #311 | `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` | Über #318 integriert |
| UX1 #312 | `b1df1c1000815786a6623d35bf3f8631661a9543` | Über #318 integriert |
| Kanonischer UX3-Vertrag #314 | `cc547ef662d1bc28315d25df1930c32b94278d6b` | Gemergt als `d80bd45d84d845aa920a7eac5b19a7fe6cd63307` |
| Ergänzungsquelle #315 | `d9d85f1af3159c4356c8773d076decbf1dc604e4` | Offen/Draft; kein zweiter normativer Hinweisvertrag |
| UX4-A #316 | `82b11711a70aacf39fddf59a6545662fb7102b92` | Gemergt als `5f2e12667759bfb54eb14f39c6d8426c9cd8080f` |
| Gemeinsame UX1-/UX2-Integration #318 | `54eaba19fc626194237e8280af2e6cc315b1bac7` | Gemergt als `bb49ffe781933270746b9f86f4aee99b6f8144c2` |
| UX1-Dokumentnachtrag #319 | `5e58fc49781e0b944d94edcf2b298336051955c8` | Gemergt als aktueller Main `484143d33aa5f2d443da6b2edf097ae1cb5aee3a` |
| UX3-B1/F1 #320 | `71e971a67be7f1ca10192e04e3832f843b8099bd` | Offen/Draft; dessen Notice-Presenter ist kein Mainbestand |
| Masterfortschreibung #321 | `f90ba2c1baebbe530af536348bc71d73ca0e0108` | Offen/Draft; nur Koordinationsdokumente |

Die historischen Masterreferenzen `2312abfe…` und UX3-Referenzen `52a24266…`
sind durch integrierte, konkretere Verträge ergänzt. Die Shared-Navigation,
UX2-Chartstelle und UX1-Währungsübergaben sind inzwischen vorhanden. UX3 präzisiert
unter anderem unbekannt/leer/Fehler, Gültigkeit eines Snapshots, beleggebundene
Aktionen und Recovery im genauen Geltungsbereich. Die Dokumentintegration macht
die vorgeschlagenen `Notice*`-Bausteine nicht automatisch zu verfügbaren Imports.
Die spätere Masterfortschreibung bestätigt den bestehenden lokalen Chartkorridor.

Relevante offene Arbeiten wurden erneut geprüft: #320/#321/#315, eigener #322
sowie #205/#220/#197/#187/#207. #205 ist weiterhin ein historischer Vorschlag;
die vorhandene Chartimplementierung stammt aus bereits integrierten Folge-PRs.
Quellenforschung und Monitoringarbeit liefern keine zusätzliche produktive
Historienabdeckung für diese Darstellung.

## Konkreter Nutzerweg und Dateischnitt

1. Eine vorhandene Position oder die bestehende Tradeverwaltung öffnen. Die
   vorhandene Historienantwort liefert alle Marktquellen und effektiven Ereignisse.
2. Provider, Preisarten, Währung, historischen Handelsplatz, Quellenmodus und
   belegte Zeiten lesen. Bei mehr als sechs Quellen die zunächst kompakte Legende
   aufklappen; ausschließlich nach exakter Serien-ID lokal ein-/ausblenden.
3. Einen Punkt anklicken oder **Punkte und Buchungen auswählen** mit der Tastatur
   öffnen. Auch 16 oder mehr überlagerte Originalbelege bleiben einzeln anwählbar.
4. **Originalbeleg anzeigen** öffnet die richtige Evidenzseite und fokussiert die
   kompakte Originalkarte beziehungsweise die konkrete Kauf-/Verkaufsbuchung.

Produktdateien: `PositionPriceHistory`, `PositionPricePlot`,
`PositionPriceHistoryEvidence`, der unmittelbare lokale Präsentationsbaustein
`PositionPricePointAccess` und `priceHistoryPresentation`. Hinzu kommen deren
lokale Tests, zwei vorhandene Browser-Testdateien, der aktualisierte
Positionshistorienvertrag und dieser Nachweis mit synthetischen Screenshots.

Die ursprüngliche Quellenwahl in #322 bleibt erhalten; ergänzt werden stabile
Quellenkennzeichnung, jederzeit erreichbare Wiederherstellung auch bei nur noch
einer ausgeblendeten Serie, unveränderte Marker bei ausgeblendeten Marktquellen,
überlagerte Belege, paginierter Tastaturzugang und kompakte mobile Evidenz.
Bekannte tatsächliche Producer-/Moduscodes erhalten lesbare Labels und behalten
den Rohcode. Unbekannte Codes bleiben unverändert.

Es gibt keine neue Datenpopulation, Kursableitung, FX, lokale finanzielle Rechnung,
Historyrekonstruktion, Interpolation, Deduplizierung oder zusätzliche Stichprobe.
Originalstrings und Zeitzuständigkeiten bleiben erhalten. Die Auswahl zählt
Marktpunkte separat von Stichproben und Ausführungen; `report.events` und die
serverseitige Markerzulässigkeit werden durch Sichtbarkeitswahl nicht verändert.
Die 20-zeilige Belegauswahl paginiert Bedienelemente, die 50-zeilige Tabelle
weiterhin sämtliche Originalwerte. Alle Diagrammpunkte werden unverändert
berücksichtigt, soweit endliche JavaScript-Koordinaten darstellbar sind.

## Bestehende UX2-Einbindung und öffentliche Grenze

| Feld | Bestehender, unveränderter Vertrag |
| --- | --- |
| Hoststelle | `TradeManagementPage`, vorhandener Anker `#position-price-history` innerhalb von „Trade und Position“ |
| Weitere Verwendung | Bestehende `PositionDetails` im Operational Workspace; kein zweiter Positionsbereich |
| Öffentliche Grenze | Bereits vorhandener öffentlicher `PositionPriceHistory`-Export aus `features/operational_workspace`; keine neuen Querimporte oder Barrelumwege |
| Props | `tradeId`, `positionId`, in der Tradeverwaltung `reloadToken={historyReloadToken}` |
| Read-Lebensdauer | Vorhandene lokale Historyinstanz, gebunden an Trade/Position/Reload; `days` und Retry lösen den bestehenden GET aus |
| Readback | UX2-Host erhöht `historyReloadToken` erst nach vollständig qualifiziertem erfolgreichen Refresh; fehlgeschlagener Readback ist kein neuer Historienstand |
| Timeline | `ExecutionDatesPanel` behält seinen eigenen Read und seinen bestehenden `onChanged`-Ablauf |
| Abschnittswechsel | Bestehende Shared-Navigation; gleicher Trade/anderer Hash ändert keinen Historienrequestschlüssel |
| Neue Fokusziele | Rein lokal: Originalkarte beziehungsweise Ereignis-ID in vorhandener Evidenz; kein neuer Hash oder angeblicher Fokus auf eine fremde Buchungsoberfläche |
| Konfliktdateien | `TradeManagementPage`, `PositionDetails`, `OpenPositionsPanel`, Navigation, Routing, Lade-/Invalidierungsowner bleiben unverändert |
| Owner/Integrationsfolge | UX2-A #311 und gemeinsame #318-Integration bereits auf Main; darauf lokaler UX4-B-Draft. UX2 bleibt einziger Hostintegrator. |

Damit ist der konkrete vorhandene Schnitt technisch geprüft. Eine neue
Ownerfreigabe für gemeinsame Dateien ist nicht erforderlich, weil keine solche
Datei geändert wird. Das ist keine behauptete persönliche UX2-Abnahme oder ein
gemeinsamer Laufzeitnachweis mit offenen UX3-/UX4-C-/UX4-D-Arbeiten.

## UX1-/UX3-Abhängigkeiten und Qualitätstexte

UX1 behält Währungs-/Quellenauflösung, Capture, Kostenbasis und Performance.
UX4-B verwendet ausschließlich die gelieferten historischen Belege. UX3 behält
den kanonischen Hinweisvertrag; fachliche Codes und ihre Qualifikation bleiben
beim Domain-Owner. Kein neues Notice-Framework oder globale Qualitätsampel.

| Zustand | Konkrete Darstellung und Vertragsabgleich |
| --- | --- |
| Alle Quellen ausgeblendet | „Das ist Ihre Darstellungswahl“ und lokale Wiederherstellung; keine Datenfehlerbehauptung |
| Bestätigte leere Antwort | Bestehender Text „Keine zeitlich und fachlich zuordenbaren Kursdaten vorhanden.“ |
| Technischer Readfehler | Bestehendes Alert und „Kursverlauf erneut laden“ beim bisherigen Readowner |
| Gekürzte Samples | Unveränderte Zahlen und Warnung „Begrenzter Ausschnitt … Ältere Belege können fehlen“ nahe der Grafik |
| Unvollständige Zeitabdeckung | „Zwischen den Punkten ist kein Kursverlauf belegt“ und „Eine vollständige Handelszeitabdeckung ist nicht belegt“ |
| Historische Qualität | Bestehende Reasonlabels wie „Bei Erfassung veraltet“; keine heutige Frische-/Recovery-/Handelbarkeitsfreigabe |
| Nicht plottbare Buchung | Unveränderter gelieferter Reason, Date-only-Datum, Zeitzone und Präzision in der Ereignisliste |
| Lazy-Chartfehler | Technischer Chartfehler und weiter nutzbare Kursevidenz/Ereignisliste; kein Ersatz durch leere Daten |

Neue statische Hinweise verwenden keine zusätzliche Live-Ankündigung. Einziger
Auswahlstatus ist der lokale Alle-ausgeblendet-Status; bestehende Lade-/Readfehler
bleiben getrennt. Der technische Wortlautabgleich wurde gegen die gelesenen
UX3-Verträge durchgeführt. Eine neue persönliche Fach-/UX3-Abnahme wurde nicht
erteilt und wird nicht als abgeschlossen ausgewiesen.

## Erneute lokale Prüfung des Folgepatches auf 7ef57c78

Ausgeführt mit Node `22.16.0`, npm `10.9.2`, Python `3.12.14` und dem zum
vorhandenen Playwright `1.55.0` gehörenden Chromium `140.0.7339.16` (Build 1187).
Dependencies, Lockdateien, bestehende Assertions und Coveragegates bleiben
unverändert. Der abschließende lokale Lauf enthält den Folgepatch auf
`7ef57c788cced3d4edf49411d421794f3bf02d99` einschließlich des zuvor separat
geprüften integrierten UX3-Piloten. Ein erster vollständiger Frontendlauf auf
`8ea8db66…` bestand bereits mit 1.998 Tests in 166 Dateien; nach der neuen
Main-Integration wurde das vollständige Gate erneut ausgeführt. Diese Läufe
werden nicht zu einer größeren Testpopulation addiert.
Der spätere reine Main-Release-/Dokumentationsnachtrag verändert keinen lokal
geprüften Produkt- oder Testinhalt. Der vollständige Dateibaum des neuen
CI-Testmerges unterscheidet sich durch die nachfolgenden Versions-/Dokumentdateien;
diese Integrationsqualifikation wird deshalb gesondert im PR nachgewiesen.

| Prüfung | Tatsächlich erneut ausgeführtes Ergebnis |
| --- | --- |
| Unverändertes `bash scripts/check-frontend.sh` | **Bestanden:** TypeScript, ESLint, Prettier, **2.082 Tests in 169 Dateien**, Coverage und Produktionsbuild |
| Frontend-Coverage | Statements/Lines **96,04 %**, Branches **90,46 %**, Functions **91,60 %**; Gates unverändert |
| Fokussierte Backend-Ownerregressionen | **71 bestanden**, eine bestehende Starlette/AnyIO-Deprecationwarnung |
| PostgreSQL-Historienintegration lokal | **2 übersprungen**: keine disposable PostgreSQL-Testdatenbank; ausdrücklich kein lokaler Pass |
| Beide vollständigen History-/Navigations-Browsersuiten am Produktionsbuild | **34 bestanden**, 0 fehlgeschlagen, 0 übersprungen, keine Retries; **48,2 Sekunden** auf dem kombinierten Stand |
| Chartausfall | Erfolgreicher Modulimport mit anschließendem Renderthrow; vollständige 51-zeilige Originalevidenz auf 2 Seiten, native Tastatur-/Scrollbedienung, BUY/SELL, date-only und unbekannte Währung erhalten, keine zusätzlichen API-Reads/Writes |
| Native Zoommessung | 200 %: 1280 → 640 CSS-Pixel, DPR 1 → 2, Dokumentbreite 632. 400 %: 1280 → 320 CSS-Pixel, DPR 1 → 4, Dokumentbreite 320 |
| Unabhängiger Review | Zwei getrennte Code-/Vertragsprüfungen; keine Änderung der UX2-Hostgrenze und keine neue Abhängigkeit vom integrierten UX3-Piloten |

Browserbefehl gegen den Produktionsbuild und lokalen `vite preview`:

```bash
npm run e2e -- \
  ../tests/e2e/position-price-history.spec.ts \
  ../tests/e2e/trade-workspace-navigation.spec.ts --workers=1
```

Der neue native 400-%-Test speichert den unveränderten Chromium-Rohwert
`3.9999999999999996`. Ein erster Lauf hatte diesen IEEE-754-Wert noch mit
strikter numerischer Gleichheit gegen `4` verglichen (33 Pässe, 1 Testfehler).
Die korrigierte neue Zoomassertion verwendet eine enge numerische Toleranz;
die exakte Breite von 320 CSS-Pixeln, der unveränderte 200-%-Pfad, Reflow,
Fokus und sämtliche Read-/Writeassertions bleiben erforderlich. Der obige
vollständige Lauf wurde danach frisch ohne Retries ausgeführt.

Der erste Backendversuch wurde wegen blockierten lokalen Prozess-/Socketzugriffs
beendet; dieselben isolierten Tests bestanden mit erlaubtem Prozesszugriff.
Der komplette Frontendlauf enthält weiterhin bestehende React-`act`-Hinweise;
Vite meldet große Chunks. Diese Hinweise werden nicht als Warnungsfreiheit ausgegeben.

Die aktuellen Bilder wurden visuell geprüft. Die zusätzlichen 400-%-Belege
zeigen vollständigen horizontalen Reflow von Kürzung und Datumshinweis sowie
den sichtbaren Fokus am Buchungsbeleg. Sie sind synthetische Browserfixtures,
keine Produktionsdaten und keine menschliche Screenreader-Vollabnahme.

| Zusätzlicher aktueller Nachweis | Datei |
| --- | --- |
| Hinweis zur begrenzten Historie bei nativem 400-%-Zoom | [Kürzung](evidence/ux4-b/ux4-b-native-400-percent-limits-synthetic.png) |
| Date-only-Hinweis und fokussierte Buchungsherkunft bei nativem 400-%-Zoom | [Datumsbeleg](evidence/ux4-b/ux4-b-native-400-percent-date-only-synthetic.png) |
| Unveränderte native Messwerte | [400-%-Messung](evidence/ux4-b/ux4-b-native-400-zoom-measurements.json) |

Die früheren Prüfzahlen folgen als eindeutig getrennter historischer Nachweis.
Die reguläre vollständige CI des neuen veröffentlichten Heads steht bei Erstellung
dieses Folgecommits noch aus; ihre tatsächlichen Jobs, der Main-SHA und der
ausgecheckte Testmerge werden nach Abschluss in der PR-Beschreibung festgehalten.

## Geerbte lokale Prüfung des ersten vollständigen Heads 9e4f8460

Node `22.16.0`, npm `10.9.2` gemäß Repository; unveränderte Lockdatei. Python
`3.12.14` in isolierter Virtualenv aus unveränderten Requirements.

| Prüfung | Ergebnis |
| --- | --- |
| `bash scripts/check-frontend.sh` | Bestanden: TypeScript, ESLint ohne Warnungen, Prettier, **1.995 Tests in 165 Dateien**, Coverage und Produktionsbuild |
| Frontend-Coverage | Statements **96,00 %**, Lines **96,00 %**, Branches **90,34 %**, Functions **91,46 %**; bestehende Gates 80/80/70/80 unverändert |
| Fokussierte Backend-Ownerregressionen | **71 bestanden**, eine Starlette/AnyIO-Deprecationwarnung |
| PostgreSQL-Historienintegration lokal | **2 übersprungen**, Grund `Disposable PostgreSQL test URL required`; keine Testdatenbank, PostgreSQL-/Docker-Binaries lokal nicht verfügbar |
| Browser, Produktionsbuild | **33 bestanden** in 45,2 Sekunden: komplette `position-price-history.spec.ts` und `trade-workspace-navigation.spec.ts`, einschließlich sieben neuer UX4-B-Fälle; keine Retries im lokalen Lauf |
| Finanz-/Reader-/Hostgrenze | `git diff origin/main -- backend frontend/src/shared frontend/src/features/trade frontend/src/features/performance VERSION frontend/package.json frontend/package-lock.json .github/workflows` leer |

Backendbefehl (mit deaktivierten externen Provider-/Nachrichtenpfaden):

```bash
PYTHONPATH=backend:. \
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false \
TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY= \
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=false \
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false \
backend/.venv/bin/python -m pytest -c backend/pyproject.toml \
  tests/unit/backend/features/market_data/test_warrant_price_history.py \
  tests/unit/backend/features/trade_position/test_position_price_history.py -q
```

Der erste Backendversuch unter eingeschränktem Prozess-/Socketzugriff hing und
wurde beendet; dieselben unveränderten Tests bestanden anschließend mit erlaubtem
lokalem Prozesszugriff. Ein Entwicklungsserverlauf der Browserfälle wurde wegen
der React-StrictMode-Doppelmounts nicht als Produktionsnachweis gewertet. Die
abschließende Browserprüfung läuft gegen `npm run build` / `npm run preview`;
die exakten GET-Zahlassertionen wurden nicht abgeschwächt.

Die Frontendsuite gibt React-`act`-Hinweise aus; der Produktionsbuild meldet
weiterhin große Chunks. Erfolgreicher Exit ist nicht gleich Warnungsfreiheit.
Keine Schwelle, bestehende Assertion, Retrykonfiguration oder Workflow wurde
abgesenkt oder übersprungen, um einen unerwarteten Befund zu verdecken.

## Mobil, Tastatur und Screenshots

Die neuen Fälle prüfen 320, 390 und 1280 CSS-Pixel, mehr als zwölf Marktserien,
verschiedene Preisarten/Modi/MICs, sichtbaren Fokus, native Tab-/Shift-Tab-/Enter-/
Leertastenbedienung, Wiederherstellung, unveränderte Reads/Writes, 16 überlagerte
Originalbelege und den exakten Originalbeleg auf Tabellenseite 2.

Der 200-%-Fall setzt echten Browserzoom über eine ausschließlich für den
Browser-Test erzeugte MV3-Extension und `chrome.tabs.setZoom`. `getZoom() === 2`,
CSS-Breite 1280 → 640 und `devicePixelRatio` 1 → 2 werden gemessen. Das ist keine
CSS-`zoom`-/Viewportsimulation. Die temporäre Extension wird nicht in Produktcode
oder eine Nutzerinstallation übernommen. Der Screenshot wird über die native
CDP-Oberfläche aufgenommen, da elementbezogenes Screenshot-Clipping bei diesem
Zoom einen schwarzen Ausschnitt lieferte; der endgültige Beleg wird visuell geprüft.

Recharts-Pfeiltests verifizieren konkret einen Tooltipwechsel und erhaltenen
Chartfokus, keine vollständige Scatter- oder Screenreader-Navigation. Der native
Belegwähler ist die vollständige Tastaturalternative. Dieselbe-Trade-Hashnavigation
erhält lokale Quellenwahl, Evidenzseite und manuelle Formularentwürfe ohne neue
Historien-, Positions- oder Timeline-Reads. Echte Identitätswechsel, A→B→A sowie
alte Erfolge/Fehler und Korrekturantworten bleiben isoliert.

Screenshots und Zoommessung sind ausdrücklich synthetische Testdaten:

| Nachweis | Datei |
| --- | --- |
| Kompakte Grafik, 320 CSS-Pixel | [320 px](evidence/ux4-b/ux4-b-compact-chart-320-synthetic.png) |
| Kompakte Grafik, 390 CSS-Pixel | [390 px](evidence/ux4-b/ux4-b-compact-chart-390-synthetic.png) |
| Kompakte Grafik, 1280 CSS-Pixel | [1280 px](evidence/ux4-b/ux4-b-compact-chart-1280-synthetic.png) |
| Quellenwahl und Tastaturfokus, 390 CSS-Pixel | [Quellenwahl](evidence/ux4-b/ux4-b-many-sources-390-synthetic.png) |
| Überlagerte Originalbelege (Auswahlliste) | [Originalbelege](evidence/ux4-b/ux4-b-overlap-originals-390-synthetic.png) |
| Nativer Browserzoom 200 % | [Zoom-Screenshot](evidence/ux4-b/ux4-b-native-200-percent-synthetic.png) und [gemessene Werte](evidence/ux4-b/ux4-b-native-zoom-measurements.json) |
| Begrenzte konkrete Kontrastprüfung | [Farben und Kontrastverhältnisse](evidence/ux4-b/contrast-check.json) |

Die Screenshots wurden visuell geprüft. Die Marktsymbolpalette erreicht auf dem
gemessenen Diagrammhintergrund `#070c20` mindestens **7,21:1**, die Achsenfarbe
**13,07:1**. Die separat erfasste Sekundärtextfarbe bleibt ebenfalls über 4,5:1.
Native Fokusumrisse sind im Quellen- und Zoombeleg sichtbar. Formen, Quellnummern,
Preisart-/Währungstext und Kauf-/Verkaufsbezeichnungen ergänzen die Farben.
Diese begrenzte konkrete Prüfung ist keine vollständige WCAG- oder Screenreaderabnahme.

Die separat gehaltene vollständige Tabelle darf in ihrer eigenen beschrifteten
Region horizontal scrollen; horizontale Dokumentrolle ist in den genannten
Breiten ausgeschlossen. Manuelle Screenreader- und menschliche Fachabnahme
bleiben offen.

## Nachweisstufen und genau ein nächster Schritt

| Stufe | Einordnung |
| --- | --- |
| Implementiert | Vollständiger lokaler UX4-B-Darstellungsschnitt im bestehenden Draft |
| Lokal geprüft | Folgepatch auf `7ef57c78…` einschließlich integriertem Main: vollständiges Frontendgate mit 2.082 Tests, 71 Backend-Ownerregressionen und 34 Browserfällen bestanden; PostgreSQL lokal übersprungen. Geerbte Zahlen sind separat ausgewiesen. |
| CI-geprüft | Frühere grüne Runs bleiben ihren damaligen Heads zugeordnet. Der neue Folgecommit benötigt die vollständige reguläre CI am tatsächlichen Testmerge mit aktuellem Main. Maßgebliche finale SHA-/Run-/Jobergebnisse stehen in der PR-Beschreibung. |
| Fachlich abgestimmt | Technischer Abgleich mit exakten kanonischen Verträgen erfolgt; neue persönliche Domain-/UX-/Screenreaderabnahme offen |
| Integriert/ausgeliefert | Der aktuelle Fortsetzungsauftrag hält #322 als Draft offen. Kein Merge, Release, Deployment oder PC-Update durch diesen Auftrag. |

**Nächster Schritt:** Den technisch qualifizierten Draft #322 zur menschlichen
UX2-/UX3-/Domain- und Bedienabnahme prüfen.
