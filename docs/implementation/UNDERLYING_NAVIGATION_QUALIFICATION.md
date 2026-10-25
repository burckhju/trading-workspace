# Basiswert-Listennavigation: gemeinsame Qualifikation mit Formularschutz

## A: Navigation — Fortschreibung 25.10.2026 auf aktuellem Main

Dieser Abschnitt qualifiziert den vorhandenen #204-Fix erneut auf v1.5.14.
Die folgenden Abschnitte ab „Historischer Prüfstand 20.10.2026“ bleiben datierte
Vorgeschichte; ihre grünen Zahlen werden nicht als neuer Integrationslauf gezählt.
Der veröffentlichte finale PR-Head, sein vollständiger Tree, der tatsächliche
CI-Checkout, Run-/Jobkennungen, Workflowversuch und Ergebnis werden im
[bestehenden PR #204](https://github.com/burckhju/trading-workspace/pull/204)
zugeordnet. Ein PR-Testmerge ist weder Main-Merge noch Veröffentlichung.

### Grundlage, Integration und enger Restdiff

| Bezug | Erneut gelesener beziehungsweise geprüfter Wert |
|---|---|
| Bestehender Aufgabenbranch / vorheriger Head | `fix/underlying-list-return` / `d279db33716ff0070c12ccd44f02036f137fa566` |
| Mergebase mit aktuellem Main | `5e9ede2dc29f52eaff601d30614df6bc9c25c426` |
| Integriertes Main / Tree | `fbd77fb94947a1fdbfc0aeb90811353fae655a59` / `027e1d0546f4c09d761ac10d1f59e87d613aff41` |
| Unveränderte Projektversion / Schema-Dateihead | `1.5.14` / `20261017_0047` (keine lokale DB-Migration behauptet) |
| Geprüfter Frontend-Quelltree | `c8589dc5b212cc7afd7c186935a8977f8cb826f5` |
| Geprüfter Browser-Quelltree `tests/e2e/` | `7ad8b33abd417afb8dc0d4ba0b6ae7c3ad2d9598` |
| Runtime | Node `22.16.0`, npm `10.9.2`; Playwright `1.55.0`, Chromium `140.0.7339.16` / Build `1187` |

Der eigene frische Clone enthielt keine fremden Änderungen. #204 war erneut
`open`, `draft=true`, `merged=false`, `mergeable=true`, `mergeable_state=behind`.
Reviews und Review-Threads waren leer. Die tatsächliche Dateiliste enthielt die
14 erwarteten Dateien. Der einzige alte Kommentar beschreibt die frühere,
bereits korrigierte API-Präfix-Fixture. Ein konkurrierender Navigations-PR war
nicht sichtbar; daraus folgt keine Aussage über unveröffentlichte fremde Arbeit.

`git merge --no-ff --no-commit origin/main` hat Main **ohne Konflikte** integriert.
Es gab diesmal keine manuelle Konfliktauflösung. Die früheren Konflikte im
historischen Abschnitt gehören zum 20.10.2026. Beide Eltern bleiben erhalten;
kein Rebase, Force-Push, Reset oder Datei-Overlay wird verwendet.

Die vier produktiven Navigationsdateien entsprechen unverändert dem bisherigen
#204-Head. Auch der deterministische `flushSync`-Fix und sein Regressionstest
bleiben erhalten. Der neue Entwicklungsanteil besteht ausschließlich aus
Testverschärfungen und diesem datierten Nachweis. Gegenüber Main bleibt der
Produktivdiff auf diese vier Dateien begrenzt. Backend, Migrationen, API-Client,
Modell-/Performance-/Trade-/Learningcode, Router/Layout, Versionen, Abhängigkeiten,
Lockfile, sämtliche Workflows, Owner-Runner und der bestehende Browser-
Formisolationstest sind bytegleich mit Main. Damit bleiben #269/#271/#273 und
der v1.5.14-Proposal-Kontextschutz #274/#275 erhalten. Der neue Parallelstrang B
wird weder implementiert noch verändert. Backlog und Traceability erhalten nur
den eigenen Abschnitt „A: Navigation“.

### Neue Qualifikation und Abnahmematrix

| Kriterium | Konkreter gemeinsamer Nachweis |
|---|---|
| A01 | Konfliktfreie normale Main-Integration; vollständiger Diff und unveränderte ausgeschlossene Pfade geprüft. |
| A02 | Beide Browserfälle Seite 2/3: alle fünf URL-Werte vor Reload, Detail → Edit → Save, genaue ID/Version/gesamte PATCH-Payload, aktuelle Anzeige und vollständiger neuer Listenrequest. |
| A03 | Abbrechen, Formular-Zurück und Detail-Zurück; zwei Tabs mit vollständigen unterschiedlichen Such-/Filter-/Seitenkontexten und null Mutationen. |
| A04 | Listen-/Formular-Reload, echtes Back/Forward sowie unabhängig erneut geladene Tabs; kein sessionweiter Store. |
| A05 | Bestehende deterministische Sofortaktionsregression und `flushSync: true` unverändert; keine Wartezeit zwischen den schnellen Browseraktionen ergänzt. |
| A06 | 39 Helperfälle einschließlich Duplikaten, verschachtelten/externalen Zielen, Kodierungsfehlern und gültigen äquivalenten Kodierungen. Die fünf Browser-Negativfälle prüfen jetzt zusätzlich die vollständige PATCH-Folge mit Versionen 1–5. |
| A07 | Direkter Edit-/Create-Rückweg, vorhandene validierte Vorschlags-/STOCK-/ETF-/MIC-/Währungsfälle; FT-001-CREATE prüft jetzt alle Payloadfelder und genau einen Auftrag. |
| A08 | Synthetisches DELETE des einzigen Eintrags auf Seite 3, Version 1, identische Filter, genau Offsets `50, 50, 25`, Seite 2 von 2 und gesperrtes Weiter. |
| A09 | Bestehende kontrollierte CREATE-/UPDATE-Formtests und zwei neue Desktop-/Mobilbrowserfälle: PATCH bleibt offen, nur `returnTo` ändert sich, Eingaben und Sperre bleiben erhalten, keine erneuten GETs, trotz zusätzlicher Submit-Ereignisse genau ein Auftrag; freigegebener Erfolg liest das aktuelle gültige Listenziel neu. |
| A10 | Vorhandene 43 Formularisolationsfälle; erweiterte Detailtests für verspäteten Erfolg/Fehler nach A→B und A→B→A sowie explizite Ablehnung falscher Detail-ID ohne Edit-/Mutationsangebot. |
| A11 | Synchrone Submit-Sperre, aktueller Fehler mit erhaltener Payload/Version, bewusste Wiederholung, kein automatischer Retry oder blindes Konfliktüberschreiben. |
| A12 | Ergänzte DELETE-Erfolgs-/Fehlerfälle nach A→B und A→B→A prüfen ursprüngliche ID/Version, genau einen Auftrag und unveränderte aktuelle Route/Anzeige; bestehende späte Save-Fälle bleiben enthalten. |
| A13 | 24 gemeinsam ausgeführte Browserfälle, 25 API-Vertragsanhänge mit exaktem `/api/api/v1` und `unexpected=[]`; vollständige Payloads/Mutationsfolgen. Tatsächliche Desktop- und Mobilbilder geprüft. |
| A14 | Alle aktuellen Main-Workflows und die beiden Finanz-/beiden Lernfälle bleiben unverändert. Ihre aktuelle vollständige Ausführung einschließlich Checkout/Tree und Rohreportprüfung wird separat im PR gebunden; lokale UI-Erfolge ersetzen sie nicht. |

Die FT-001-Fixture lässt jetzt ausschließlich eigene statische GET-Ressourcen
durch. Alle API-, Fetch/XHR-, Mutations- und Fremdrequests werden kontrolliert
abgefangen; falscher Origin, falsches Präfix und unbekannte Pfade scheitern auch
in der automatischen Fixture-Abschlussprüfung. Sie prüft CREATE, Verifizieren,
Deaktivieren und DELETE mit vollständigen Methoden, Pfaden, Querywerten,
Payloads und Mutationszahlen. Der Produktionsproxy bleibt unverändert.

| Neuer lokaler Lauf | Tatsächliches Ergebnis |
|---|---|
| Bestehende gemeinsame Suite nach Main-Integration | **115/115**, sieben Dateien |
| Erweiterte gemeinsame Suite | **122/122**, sieben Dateien, davon 21 Navigation und 43 Formularisolation |
| Unverändertes `bash scripts/check-frontend.sh` | **780/780**, 119 Dateien; TypeScript, ESLint, Prettier, Coverage und Produktionsbuild bestanden |
| Coverage Statements/Lines / Functions / Branches | **93,49 / 86,38 / 85,95 %**, alle Schwellen unverändert |
| Gemeinsamer Browserlauf | **24/24**, 8 Navigation + 12 Formularisolation + 4 FT-001; ein Worker, je genau ein erfolgreicher Versuch, `retry=0`, kein Skip/Flaky/Reporterfehler |
| Browserartefakte | 24 Traces, 20 Screenshotanhänge und 25 geprüfte API-Verträge |
| Diff / ausgeschlossene Pfade | `git diff --check` und Indexprüfung erfolgreich; keine zusätzlichen Produktivänderungen |

Der erste lokale Sandbox-Testprozess lieferte keinen Report und wurde gezielt
beendet. Er zählt nicht als Testlauf mit Erfolg. Die dokumentierten Ergebnisse
stammen aus der funktionsfähigen isolierten Werkzeugumgebung. Der vollständige
Frontend-Gatelauf und der Browserlauf bestanden jeweils beim ersten beendeten
Versuch. Der normale Playwright-Download-Fallback nach defektem CDN-Archiv fand
vor Testbeginn statt und ist kein Testretry. Es gab keinen neuen Produktivfehler
und daher keinen künstlich erzeugten Rotnachweis oder neuen Produktivfix.

Der eigene Browserbuild verwendete explizit
`VITE_API_BASE_URL=http://127.0.0.1:31804/api`; derselbe Wert war
`E2E_VITE_API_BASE_URL`, das eigene Frontend lief auf `127.0.0.1:31804`.
Es war kein Backend oder Datenbankziel angeschlossen. Der Previewprozess ist
beendet; die Loopback-Verbindung wurde danach mit `ECONNREFUSED` geprüft.
Die Bilder zeigen gefilterte Seite 2/3, den erhaltenen Speicherzustand auf
Desktop/Mobil, die mobile Rückkehrliste und den gesperrten Ladefehlerzustand.
Der eigene Mobilfall prüft zusätzlich fehlenden horizontalen Seitenüberlauf.

Docker ist lokal nicht vorhanden. `scripts/check-backend.sh` und
`scripts/run-e2e.sh` wurden deshalb hier nicht als vollständige lokale Gates
ausgeführt. Die unveränderten regulären CI-Jobs müssen den veröffentlichten
gemeinsamen Tree prüfen: Backend einschließlich PostgreSQL, Produktionsimage,
Renderer, Frontend, Smoke, beide Finanz- und beide Lern-Ownerfälle sowie
Veröffentlichungsschutz. Der tag-Job bleibt beim PR vorgesehen übersprungen.
Die Owner-Runner behalten ihre expliziten frischen UUID-Ziele, Zielprüfungen,
Netzgrenzen und Cleanup-Nachweise. Der bestehende Smokejob verwendet seinen
eigenen frischen Hosted Runner; ihm werden keine zusätzlichen Owner-Guards
zugeschrieben. A verändert keine dieser Infrastrukturen.

### Neue lokale Artefaktbindung

| Artefakt | SHA256 |
|---|---|
| `navigation-integrated-before.json` | `16b586e00f043c82fcde2cb0bc1cdd1153d5690ecc0475515cfa26c29b702f16` |
| `navigation-integrated-expanded.json` | `3e700bd84237b0041d5153ebdef22eaa07bd4411eb65cd4d95ca38df10c80f95` |
| `frontend-gate.log` | `ed5c34dd88816db38fdabfcf318a7e6b16f188ee351de5eee8a8001ee5acd5fa` |
| `browser-integrated.json` | `00af3a64cfebc514d3a4a6471835d7f7161a0d0335aaa83af988d0f726adff85` |
| `browser-api-contracts.json` | `4ab6b8d12f434f777b40b818d13c2f652d9a3bf814a97e6df1f25a23145c0019` |

Diese Rohartefakte sind Sitzungsnachweise; die neuen unveränderlichen CI-Artefakte
werden nach ihrem tatsächlichen Lauf im PR referenziert. Große Rohberichte oder
private Daten werden nicht in das Repository übernommen.

### Grenzen und späterer lesender PC-Abnahmeweg

Mock-HTTP belegt Clientverhalten, keine PostgreSQL-Persistenz oder Veränderung
von Nutzerstammdaten. Ein abgesendeter Serverauftrag wird durch das Ignorieren
seiner alten Antwort nicht rückgängig gemacht. Der historisch dokumentierte
gleiche-ID-StrictMode-Doppelladerandfall bleibt ausdrücklich von der hier
geprüften Isolation verschiedener Datensatzinstanzen getrennt; seine Behebung
wird nicht behauptet. Der unabhängige Lesereview der Ergänzungen fand keinen
weiteren Produktivdefekt oder Testblocker.

Nach späterer gesondert freigegebener Auslieferung kann der Nutzer rein lesend:

1. Installierte Version/Commit getrennt feststellen; eine vorhandene gefilterte
   Auswahl mit mindestens zwei Seiten öffnen und deren vollständige URL notieren.
2. Auf Seite 2 beziehungsweise 3 einen Basiswert öffnen, „Bearbeiten“ wählen und
   ausschließlich „Abbrechen“ beziehungsweise „Zurück“ verwenden. URL, alle Filter
   und Seite müssen übereinstimmen; keine Speicher-/Löschaktion ausführen.
3. Liste und Formular erneut laden, Browser-Zurück/-Vorwärts sowie einen zweiten
   Tab mit anderer Auswahl prüfen. Jeder Tab muss seinen eigenen Kontext behalten.

Speichern, DELETE, Fehler-/Antwortreihenfolgen und aktuelle Daten nach Mutation
bleiben zunächst den synthetischen Tests zugeordnet. Keine PC-Prüfung wurde hier
ausgeführt. Main-Merge, Release, Tag, Installation und menschliche Fachabnahme
benötigen ihre eigenen Nachweise beziehungsweise Freigaben.

## Historischer Prüfstand 20.10.2026

Prüfdatum: 20.10.2026. Gegenstand ist die begrenzte Weiterführung von
[PR #204](https://github.com/burckhju/trading-workspace/pull/204) auf v1.5.11.
Die ursprünglichen Ergebnisse bis einschließlich „Sitzungsartefakte und weitere
Freigabe“ sind lokale synthetische Entwicklungsnachweise vor der anschließenden
PR-Aktualisierung. Der Nachtrag trennt davon den ersten tatsächlichen PR-Lauf
und seinen gezielten Folgefix. Dieser Bericht erhebt keinen Main-Lauf, Main-Merge,
Release, PC-Update oder menschliche Fachabnahme als Nachweis. Der Aufgabenstatus bleibt im
[Product Backlog](../planning/PRODUCT_BACKLOG.md).

## Geprüfte Grundlage und Integration

| Bezug | Wert |
|---|---|
| Bestehender Branch | `fix/underlying-list-return` |
| Ursprünglicher PR-Head | `3a2dd4823aa2ff8b0b44d23655bab3a0e443efaa` |
| Integrierter Main-Elternstand | `5e9ede2dc29f52eaff601d30614df6bc9c25c426` |
| Main-Tree | `303e56c078efd578e6e147edcf2ebac6accf6ba5` |
| Geprüfter Frontend-Quelltree | `c8d98bc689b0cd57e5a32eb473a82a1adc6c27f8` |
| Geprüfter `tests/e2e`-Quelltree | `192ded7fb7e8b10a10cf6ec1710fc5ead4ba8db4` |
| Runtime | Node `22.16.0`, npm `10.9.2`, unverändertes Lockfile |
| Browser | Playwright `1.55.0`, Chromium `140.0.7339.16` / Build `1187` |

Die Quelltrees wurden aus dem gestageten Integrationsstand mit
`git write-tree --prefix=frontend/` beziehungsweise `--prefix=tests/e2e/`
ermittelt. Sie binden die ausführbaren Nachweise unabhängig von späteren reinen
Dokumentationsänderungen. Der lokale Merge war bei Durchführung der Prüfungen
noch nicht committet; ein späterer Commit muss diese Trees erhalten oder seine
Abweichung erneut qualifizieren.

Main wurde nichtdestruktiv in den vorhandenen Branch übernommen. Die beiden
Konflikte in `UnderlyingFormPage.tsx` und `FEATURE.md` wurden inhaltlich aufgelöst:
aktuelle Formularschutzmechanismen aus #249/#267 erhalten, gezielten
Listenrücksprung hinzufügen. Backend, Stammdatenvalidierung, API-/Versions- und
Auditverträge, Provider, Migrationen, Releases, Währungs-/Performancecode,
Workflows und Dependency-Pins sind gegenüber dem Main-Elternstand unverändert.

## Verhalten und Schutzgrenzen

| Anforderung | Umsetzung und konkreter Nachweis |
|---|---|
| Bestätigte Suche, Status, Markt, Währung, 25er-Seite | Gemeinsamer URL-Helfer; Liste liest und schreibt ausschließlich den URL-Kontext. Unit- und Browserfälle erhalten alle fünf Werte auf Seite 2 und 3. Neue Suche/Filter setzt den Offset auf 0. |
| Sichere Rücksprungziele | Nur `/underlyings` und bekannte eindeutige Listenparameter. Keine externen, protokollrelativen, fremden, verschachtelten, doppelten oder missverständlich kodierten Ziele. Korrekt kodierte Suchzeichen werden kanonisiert, nicht als zweite URL interpretiert. 39 Helfertests einschließlich Negativfällen; fünf ungültige Ziele zusätzlich im Browser. |
| Detail → Edit → Save/Abbrechen/Zurück | Bestehende Linkkette gibt validiertes `returnTo` weiter. Edit-Save lädt die ursprüngliche Liste neu; Fehler behält Eingaben und führt nicht zur Erfolgsnavigation. Direkte Bearbeitung bleibt bei ihrem Detailziel; Neuanlage öffnet den angelegten Basiswert. |
| Reload, Verlauf, Tabs | Browser reloadet Liste und Formular; echter Browser-Zurück-/Vorwärtsweg und zwei unabhängige Tabs sind geprüft. Keine globale oder sessionweite zweite Zustandsablage. |
| Leere letzte Seite | Der bestehende Löschweg kehrt mit allen Filtern zurück. Nach Entfernen des einzigen Eintrags auf Seite 3 wird Seite 2 geladen. Die beobachteten Offsets sind genau `50, 50, 25`, ohne Schleife. |
| Vorschlag und Navigation getrennt | `returnTo` ist vom stabilen fachlichen Parametersnapshot/Formularschlüssel ausgeschlossen. Eine reine Zieländerung erhält Eingaben, Identität/Version und laufende Sperre. Ein noch aktiver Erfolg verwendet das aktuelle validierte Ziel. |
| Aktuelle Formularintegrität | Alle bisherigen Isolationsfälle bleiben erhalten: A→B, Ladefehler, StrictMode, Unmount, Version/Payload, kein Edit→Create-Fallback, synchrone Doppelübermittlung. Zusätzliche Fälle prüfen diese Regeln mit Listenkontext und reine Rücksprungänderungen während Create/Edit. |
| Detailwechsel und alte Löschantwort | Detailzustand ist an die Datensatzidentität gebunden. Verspätete A-Daten ersetzen B nicht; eine alte DELETE-Antwort navigiert B nicht weg. Eine synchrone Aktionssperre verhindert zwei gleichzeitige Löschaufträge. |

Ein bereits abgesendeter Schreibauftrag kann serverseitig weiterlaufen.
Navigation ist kein Abbruch oder Rollback. Die Tests prüfen ausschließlich,
dass verlassene Ansichten keine fremden Daten oder nachträgliche Navigation
übernehmen. Kein allgemeiner Umbau aller Detail-Aktualisierungsrennen wird
behauptet.

Der unabhängige Read-only-Review hat eine bereits auf Main bestehende engere
Grenze im Detail reproduziert: Unter React StrictMode können zwei Ladeeffekte
derselben Datensatzinstanz laufen; eine späte erste Antwort kann dann die
neuere zweite Version überschreiben. Das betrifft weder den hier ergänzten
A→B-Instanzschutz noch den bestehenden eigenen Lade-Abbruchschutz des Formulars.
Der Befund ist keine neue Navigationsregression und bleibt außerhalb dieses
begrenzten Integrationsschnitts sichtbar.

Produktionsdateien: `UnderlyingListPage.tsx`, `UnderlyingDetailPage.tsx`,
`UnderlyingFormPage.tsx` und `underlyingListNavigation.ts` unter
`frontend/src/features/market/`. Die ergänzte Featurebeschreibung steht im
[FT-001 Feature Book](../features/underlying/FEATURE.md).

## Reproduktion und Frontend-Gate

Vor der Korrektur wurden die neuen Fälle gegen den zunächst zusammengeführten
Code ausgeführt. Die 79 Formular-/URL-Fälle ergaben 67 Erfolge und zwölf
reproduzierte Fehler: zwei ungewollte Formular-Neuinitialisierungen bei reiner
Rücksprungänderung und zehn zu permissive Rücksprungziele. Die zwei ergänzten
Detailfälle ergaben vor ihrer Korrektur elf erfolgreiche bestehende Fälle und
zwei Fehler: verspätetes A ersetzt B sowie doppelte DELETE-Übermittlung.

Der fokussierte gemeinsame Lauf umfasst 114 Tests in sieben Dateien:
`UnderlyingNavigation.test.tsx` (13), `UnderlyingFormIsolation.test.tsx` (43),
`underlyingListNavigation.test.ts` (39), `UnderlyingFormPage.test.tsx` (7),
`UnderlyingListPage.test.tsx` (7), `UnderlyingDetailPage.test.tsx` (3) und
`src/app/Application.test.tsx` (2). Alle bestanden. Diese Teilmenge wird nicht
auf die Gesamtzahl des folgenden Gates aufaddiert.

Der erste vollständige Gateversuch stoppte an zwei `require-await`-Lintfehlern
in den neuen Detailtests. Die Tests warten nun explizit auf ihre kontrollierten
Promises. Anschließend bestand das unveränderte Repository-Gate:

```bash
bash scripts/check-frontend.sh
```

| Prüfung | Ergebnis |
|---|---|
| TypeScript | bestanden |
| ESLint, maximal 0 Warnungen | bestanden |
| Prettier | bestanden |
| Vollständige Vitest-Coverage-Suite | **632 bestanden in 113 Dateien**, keine Skips/Fehler |
| Lines / Statements | **92,86 % / 92,86 %**, Grenzen unverändert jeweils 80 % |
| Functions | **85,42 %**, Grenze unverändert 80 % |
| Branches | **85,08 %**, Grenze unverändert 70 % |
| Produktionsbuild | bestanden; bestehende Vite-Hinweismeldung zu großen Chunks bleibt sichtbar |
| Diff-/Konfliktprüfung | `git diff --check` und `git diff --cached --check` bestanden; keine unaufgelösten Indexkonflikte |

Die Runtime musste lokal bereitgestellt werden. Dependencyinstallation erfolgte
zunächst mit vorhandener Node-24-Runtime und gepinntem npm `10.9.2`, ohne
Lockfileänderung. Ein früh versuchter Node-24-Testlauf ohne Ergebnis wurde
abgebrochen und gilt nicht als Erfolg. Sämtliche hier als bestanden genannten
Gates und Browserläufe verwenden das verifizierte vollständige Node-22.16.0-Binary
und npm 10.9.2. Es wurden keine CI-Variablen gefälscht oder Schutzregeln geändert.

## Gemeinsamer synthetischer Browserlauf

Vor dem Lauf wurden genau **22 Tests in drei Dateien** per Playwright `--list`
erfasst. Anschließend wurden dieselben drei Dateien zusammen mit einem Worker,
`--retries=0`, `--trace=on` und JSON-Report ausgeführt:

```bash
npm run e2e -- \
  underlying-list-return.spec.ts \
  underlying-form-isolation.spec.ts \
  ft001-underlyings.spec.ts \
  --workers=1 --retries=0 --trace=on --reporter=list,json
```

| Browserdatei | Tatsächlich ausgeführter Umfang |
|---|---|
| `underlying-list-return.spec.ts` | 6: Save/Rückkehr Seite 2 und 3 mit Reload und allen Filtern; zwei Tabs/Abbrechen; leere letzte Seite nach Löschung; echtes Back/Forward; ungültige Rücksprungziele. |
| `underlying-form-isolation.spec.ts` | 12: sechs bestehende Fälle jeweils bei 1440×1000 und 390×844 — beide Lade-Reihenfolgen A/B, Ladefehler ohne Create-Fallback, alte Save-Auflösung/-Ablehnung während B speichert, synchrone doppelte Neuanlage. |
| `ft001-underlyings.spec.ts` | 4 bestehende Abläufe: Suche/Filter; Neuanlage mit Primärlisting; Detailhistorie/Verifizieren mit geladener Version; Deaktivieren/Löschen/Neuanlage. |

**Ergebnis: 22 bestanden in 18,3 Sekunden, 0 Skips, 0 Flaky, 0 Fehler und
0 Testretries.** Der JSON-Report wurde zusätzlich strukturell geprüft: exakt 22
eindeutige Testidentitäten, je genau ein Ergebnis `passed`, `retry=0`, keine
unerwarteten Ergebnisse und keine Reporterfehler. Der Browserreport enthält
22 Traces und 16 angehängte Screenshots. Seite 2/3 und mobile aktuelle bzw.
gesperrte Formulare wurden zusätzlich visuell geprüft; die bestehenden
Formularbrowserfälle prüfen horizontalen Überlauf programmatisch.

### Echte Pfade, synthetische Schreibantworten

Der separate Browserbuild verwendet ausdrücklich
`VITE_API_BASE_URL=http://localhost:8080/api`. Derselbe Wert wurde als
`E2E_VITE_API_BASE_URL` übergeben; `PLAYWRIGHT_BASE_URL` ist
`http://localhost:8080`. Daraus folgt für diesen Build tatsächlich
`/api/api/v1`. Diese testbezogenen Variablen wurden erst nach dem allgemeinen
Frontend-Gate gesetzt.

Die Navigation-/Formfixtures fangen alle API-, Fetch/XHR-, Mutations- und fremden
Requests ab. Nur statische Frontenddateien erreichen den eigenen lokalen
Previewprozess. Unbekannte Requests werden mit Fehler beantwortet und lassen
die Vertragsprüfung scheitern. Alle **19 angehängten API-Verträge** enthalten das
erwartete Präfix und `unexpected=[]`. Die Navigation prüft vollständige
Update-Payload, ID, Version, tatsächlichen API-Pfad und Filterparameter; die
bestehende Formisolation prüft ihre vollständigen Create-/Update-Payloads ebenfalls.
Der eigene Previewprozess wurde nach dem Lauf beendet.

Die Browserinstallation verwendete den normalen Playwright-Download-Fallback
nach einem fehlerhaften CDN-Archiv. Das war vor Testbeginn und ist kein
fachlicher Testretry. Es war kein Backend/Test-DB-Stack angeschlossen; diese
Mock-Browsernachweise ersetzen keine native PostgreSQL-Prüfung und belegen
keine realen Nutzerbestandsänderungen.

## Sitzungsartefakte und weitere Freigabe

Die unveränderten Rohberichte liegen in den Sitzungsartefakten und sind für eine
spätere autorisierte PR-Übergabe aufzubewahren. Sie wurden nicht als neue externe
CI-Artefakte veröffentlicht.

| Datei | SHA256 |
|---|---|
| `frontend-gate.log` | `663f841ee8388dd92b43976c2e89f5def5d3976f5937cf86c8abb16b2ef64ad2` |
| `browser-report.json` | `2b979bc7522804ae011a9711fc194f25e83bdc2109b3017c3b6efd17c549ff7c` |
| `browser-api-contracts.json` | `f61e974914f0e3a347c2491b80a1996095073c65e808fb9db482c482ed77dd09` |

Die unabhängige Alt-PR-Prüfung mit konkreten Quellen steht unter
[Restprüfung #204/#225/#235/#90](../reviews/LEGACY_PR_REMAINDERS_2026-10-20.md).
Alte PRs wurden im Rahmen dieser lokalen Prüfung weder geschlossen noch gemergt.
Die Entwicklungsbranch-/PR-Übergabe ist durch den Startauftrag autorisiert. Die
nachfolgenden tatsächlich erforderlichen Checks am exakten neuen PR- beziehungsweise
Testmerge-Head sind gesondert im bestehenden PR #204 zu ergänzen; die lokalen
Nachweise ersetzen sie nicht. Ein späterer Main-Push-/Release-/Installationsnachweis
bleibt ein eigener Schritt.

## Nachtrag: erster PR-Lauf und reproduziertes URL-Rennen

Der geprüfte Integrationsstand wurde anschließend als echter Zwei-Eltern-Commit
[`d908747b5b8d9b4a9f714926d74ebe77a23b6e29`](https://github.com/burckhju/trading-workspace/commit/d908747b5b8d9b4a9f714926d74ebe77a23b6e29)
auf dem vorhandenen PR-Branch veröffentlicht. Sein vollständiger Tree ist
`47bb0d614d904c271ed42a2f49ea313fa434db55`. Die GitHub-Checks verwendeten den
synthetischen Testmerge `17f584f428e4a291292598704b1eb0f5cef187ef` mit demselben
Tree; dessen Eltern sind Main `5e9ede2…` und PR-Head `d908747…`. Das ist kein
Merge nach Main.

Der [Frontend-Lauf 39425063492](https://github.com/burckhju/trading-workspace/actions/runs/39425063492)
bestand mit 632 Tests in 113 Dateien und unveränderten Gates. Der
[E2E-Lauf 39425063545](https://github.com/burckhju/trading-workspace/actions/runs/39425063545)
hat zwar einen erfolgreichen Jobstatus, aber der Smoke-Report enthält
**68 erwartete Erfolge, einen Flaky-Fall und drei deklarierte Skips bei
72 Testidentitäten**. Der separat verantwortete PostgreSQL-Reportfall bestand
im selben Workflow einmal ohne Retry; er wird nicht dem Smoke-Ergebnis
zugerechnet.

Der Flaky-Fall ist der Navigationsfall für Seite 2: Versuch 0 scheiterte am
fehlenden Suchwert `Test`, Retry 1 bestand. Die übrigen fünf Navigationsfälle
und alle zwölf Formularisolationsfälle bestanden jeweils ohne Retry.
Dieser erste Head ist damit ausdrücklich **kein Nachweis für 0 Flaky/Retry**.

Der fehlgeschlagene Erstversuch liefert Video, Screenshot und Fehlerkontext,
aber keinen Trace. Das Video zeigt den Suchtext noch nach Status-, Markt- und
Währungsauswahl sowie dem Wechsel auf Seite 2; nach dem ersten Listen-Reload
fehlt er bereits. Die dortigen Rücksprung-Links enthalten keinen `query`-Wert.
Der vorhandene Trace `8759ee4ceb1858b0236da45b52419802b8322ec4.zip` gehört nur
zu Retry 1. Die genaue fehlerhafte Request-/URL-Reihenfolge von Versuch 0 lässt
sich daraus nicht rückwirkend ableiten.

Der daraufhin ergänzte deterministische Komponententest sendet Suche und drei
unterschiedliche Filteraktionen, bevor der zuvor gestartete Transition-Render
abgeschlossen ist. Ohne Fix ergibt der Test `query=Original&currency=EUR`:
Der neue bestätigte Suchwert sowie Status und Markt gehen verloren. Der
Rotnachweis enthält 13 bestandene und genau diesen einen fehlgeschlagenen Test.
Damit ist der Fehler unabhängig vom flüchtigen CI-Zeitverhalten reproduziert.

Die gepinnte React-Router-7.6.0-Implementierung verwendet in `useSearchParams`
auch beim funktionalen Setter den Suchparameterstand des jeweiligen Renders;
der Setter besitzt keine React-State-Update-Warteschlange. Der vorhandene
DOM-`RouterProvider` unterstützt hingegen `flushSync`. Deshalb setzt allein
`UnderlyingListPage.updateView` seine bewusst ausgelöste URL-Navigation mit
`{ flushSync: true }`: Die folgende Aktion liest dann den bereits bestätigten
URL-Stand. Die URL bleibt Eigentümer des bestätigten Listenfilters. Es entsteht
keine zweite globale oder sessionweite Ablage.

Der Browserfall prüft zusätzlich unmittelbar nach der schnellen Aktionsfolge
und vor dem ersten Reload alle fünf URL-Werte. Es gibt keine zusätzliche
Wartepause zwischen den Aktionen. Formular-/Detaildateien, Hilfsparser,
Workflow-, Runtime- und Dependency-Pins werden durch diesen Folgefix nicht
geändert.

| Erstes CI-Artefakt | Kennung und SHA256 |
|---|---|
| Smoke-ZIP | Artefakt `12265840827`, `bc45bcbcb9370c86317e7792f5fc90a26b47f77eac32caa15c531cf6d4beb19b` |
| Extrahierter Smoke-Report | `ci-smoke-report.json`, `275e22643a2afe45b170620e61e6ebb7217ed4de3920717300cc22491c5702fa` |
| Separates PostgreSQL-Owner-ZIP | Artefakt `12265526428`, `8eae848a06c265a046b27aa3a65c71249ec953619aae9da0572c9f376de19793` |

## Nachtrag: lokale Qualifikation des Folgefixes

Der Folgefix basiert auf `d908747b5b8d9b4a9f714926d74ebe77a23b6e29` und erhält
dessen Integrationshistorie. Er ändert genau die Listenaktion, einen
Komponententest, die frühe URL-Prüfung im bestehenden Browserfall und diesen
Bericht. Die ausführbaren Quellen sind durch folgende gestagete Trees gebunden:

| Quelle | Geprüfter Tree |
|---|---|
| `frontend/` | `ea50a583e0a0ba5760dde0b1ca9561e62d96481f` |
| `tests/e2e/` | `599387b99c663df74393b21610038add8089b14c` |

Der fokussierte gemeinsame Lauf bestand mit **115/115 Tests in sieben Dateien**,
einschließlich nun 14 Navigations- und unverändert 43 Formularisolationsfällen.
Zwei frühe Gateversuche fanden ausschließlich Fehler im neuen Test: zunächst
vier nicht unterstützte RTL-`exact`-Optionen, danach die Formatierung der
verkürzten Aufrufe. Beide Logs bleiben erhalten. Nach deren Korrektur bestand
das unveränderte `scripts/check-frontend.sh` vollständig mit **633/633 Tests in
113 Dateien**, ohne Skips/Fehler. TypeScript, ESLint, Prettier und Build bestanden;
Coverage: **92,86 % Lines/Statements, 85,10 % Branches, 85,42 % Functions**.
Runtime und Schwellen sind unverändert.

Danach lief dieselbe gemeinsame synthetische Browsermenge einmal mit
`--workers=1 --retries=0 --trace=on`: **22/22 bestanden in 17,3 Sekunden,
0 Skips, 0 Flaky, 0 Fehler, 0 Retries**. Die Reportprüfung bestätigt 22 eindeutige
Testidentitäten mit jeweils genau einem erfolgreichen Versuch: sechs Navigation,
zwölf Formularisolation, vier FT-001. Alle 19 API-Verträge haben weiterhin
`apiPrefix=/api/api/v1` und `unexpected=[]`; sie sind inhaltlich identisch zum
ersten lokalen Lauf. Der neue Screenshot der Rückkehr auf Seite 2 wurde
zusätzlich angesehen. Alle 22 Traces und 16 Screenshots bleiben im Sitzungsreport.
Der eigene Previewprozess ist beendet; beide lokalen Loopback-Adressen auf
Port 8080 antworten danach mit „connection refused“.

| Folgefix-Artefakt | SHA256 |
|---|---|
| `list-transition-before.json` | `2e583df5ec1d9d975afe96845fdad95006bcc1600238cf34ea36f670d3186fed` |
| `list-transition-fixed.json` | `98f019866712f3310014558f9ec611be001fff6eb88ac93619186910a1277ac1` |
| `frontend-gate-transition-fix.log` | `27c1fac4aed10a61cd5c0fc68f0a3e319cf1a0028c987cbd247cd0c996bd8e8f` |
| `browser-report-transition-fix.json` | `13ed5127a2099c27616d3da67fda1b32cd61505a740da98afb536b7b9a471c70` |
| `browser-api-contracts-transition-fix.json` | `f61e974914f0e3a347c2491b80a1996095073c65e808fb9db482c482ed77dd09` |

Diese neuen grünen Ergebnisse sind lokale Nachweise des Folgefixes. Sie ersetzen
weder den dokumentierten Flaky-Befund des ersten PR-Heads noch die anschließend
erforderliche Prüfung des neuen veröffentlichten Heads und seines Testmerge-Trees.
Die nachfolgende CI-Evidenz wird im bestehenden PR separat ergänzt.
