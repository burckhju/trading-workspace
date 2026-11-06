# UX1-B: Quellenvertrag und editierbarer Planwährungsvorschlag

## Auftrag und geprüfte Basis

Dieser abgegrenzte Auftrag vom 06.11.2026 reduziert ausschließlich die erneute
Eingabe von `entry.currency` bei der ersten Anlage eines Candidate-basierten
TradePlans. Die [neue FT-007-Regel](../features/FT-007_TRADEPLAN.md#neuer-vorschlag-ux1-b-editierbare-planwährung-bei-candidate-erstanlage)
ist ein Vorschlag dieses Drafts, keine bereits vorhandene Repositoryregel.
`PRODUCT_BACKLOG` bleibt die einzige fachliche Aufgabenstatusquelle. Der Bericht
führt technische Nachweise und Anforderungen, keinen zweiten Aufgabenstatus.

Am 06.11.2026 erneut gelesen: README, Development Guide, Frontendarchitektur,
die fünf Dokumente unter `docs/coordination/`, FT-007, ADR-S6-002/-007,
ADR-S4-002, die bestehenden UX1- und Plan-Kontextnachweise sowie die unten
genannten Producer/Reader/Consumer. Im Repository existiert keine `AGENTS.md`.
Historische Genehmigungen anderer PRs werden nicht übernommen.

| Gegenstand | Tatsächlich gelesener Ausgangsstand |
|---|---|
| Main | `e4921d6e25b70baddb80d4eaaf61028bb055ad04`, Tree `ff0dc79a4ee679eb9803e89d96d560b0e12d5470` |
| Veröffentlichter Tag | `v1.5.40` zeigt tatsächlich auf denselben Commit; #329 wurde am 05.11.2026 um 22:08:29 Uhr Europe/Berlin integriert. Kein neuer Releaseauftrag. |
| Vorheriger Tag | `v1.5.39` → `14913454ddecd1a9559639ec19d7373cf5269e90` |
| Integrierte Arbeit | #324/#322 sowie #326, Merge `a68b3a928129b42b19dc2a6de07be1bf7c91a811`, liegen in der Basis; werden nicht erneut implementiert. |
| Parallele Drafts | #325 `555538fa0519cd31e6d5391dd938a8150c90ac3d`, #327 `79760e9cf40cef6c6e58d8b15b6849a3056cc5c8`, zusätzlich #330 `67af2c8c43d92c0cd6d14412f58b3c4129f1eec6`; vollständige Dateilisten gelesen, keine Überschneidung mit diesem Schnitt. |
| Weitere offene PRs | #315/#220/#207/#205/#197/#187 ebenfalls auf Dateiebene geprüft. #187 betrifft einen getrennten Hebeltrader-Wrapper, nicht diese Erstanlage. Keine Übernahme fremder Branches. |
| Eigene Arbeit | Kein bestehender Branch/PR für diesen Planwährungsschnitt gefunden. Eigener Branch `feat/ux1-b-plan-currency-suggestion`, genau ein Draft-PR. |

Der historische Abschnitt „UX1-B“ in
[UX1_INPUT_REUSE_QUALIFICATION](UX1_INPUT_REUSE_QUALIFICATION.md) bezeichnete das
Wiederöffnen eines gespeicherten Produktauswahlruns. Seine ausgelieferte Leistung,
die damalige Planwährungszeile und der Auslieferungsnachweis bleiben unverändert.
Dieser neue Auftrag ist ausschließlich der hier bezeichnete Planwährungsschnitt.

## Genau eine Feldzeile

| Feld / Ablauf | Heute auf Ausgangs-Main | Quelle | Neue zulässige Übernahme | Nutzerentscheidung | Owner | Umsetzung |
|---|---|---|---|---|---|---|
| `entry.currency`, neuer Candidate-Plan | Manuelle Währungseingabe | Exakt gebundener vollständiger Underlying-Analysis-Snapshot | Einmaliger sichtbarer, editierbarer Vorschlag ausschließlich bei belegter Identität, vollständiger einheitlicher Quelle und unberührtem Formular | Abweichende Planwährung, alle Preise/Annahmen, Speichern und spätere Freigabe | UX1 + FT-007; FT-005/FT-006 liefern unveränderte Referenz/Quelle | Begrenzter Erstellungsflow und bestehende Reader; danach normale technische Qualifikation |

Erwartete Einsparung bei Umsetzung: **ein erneut einzugebender Währungscode pro
qualifiziertem neuen Candidate-Plan**. Keine Nutzungsquote oder Einsparung bei
unqualifizierter Quelle wird behauptet.

## Phase 1: bestehende Quelle, Bindung und öffentliche Lesegrenze

Die folgenden Befunde stammen aus dem Ausgangs-Main, vor dem Produktdiff.

| Vertrag / Beleg | Nachgewiesene Grenze |
|---|---|
| [ADR-S6-002](../decisions/ADR-S6-002-TRADEPLAN-ORIGIN-AND-CANDIDATE-EVALUATION-HANDOFF.md), [ADR-S6-007](../decisions/ADR-S6-007-PROVENANCE-AND-SNAPSHOT-POLICY.md) | Konkrete immutable CandidateEvaluation; Analyse-IDs und Modellversionen bleiben transitive Source of Truth. Keine spätere Evaluation als Ersatz. |
| [Candidate-Orchestrierung](../../backend/app/features/candidate/service/orchestration.py), `_load`, `_source`; [Candidate-Anwendung](../../backend/app/features/candidate/service/application.py), Evaluation-/Source-Persistierung | UNDERLYING-Analyse wird zum Underlying gebunden; Quelle speichert `ANALYSIS`, Analyse-ID, Run-Version, Modell-ID und Modellversion. |
| [Ursprungsreader](../../frontend/src/features/trade_plan/services/originContext.ts), `loadTradePlanOrigin`; [Candidate-Typen](../../frontend/src/features/candidate/types/api.ts) | Gewählter Candidate, konkrete Evaluation, LONG-Version und tatsächlich gelieferter Basiswert werden geprüft. Optionales `sources` darf fehlen; das allein macht den Planursprung nicht ungültig. |
| [Analyseclient](../../frontend/src/features/analysis/services/client.ts), `getRun` | Standardread bleibt `include_snapshot=false`. Sein leeres `snapshot` beweist keine leere gespeicherte Quelle. Gelieferte `analysis.id`, `underlying_id`, historische `listing_id`, `run.version`, `model_id` und `model_version` erlauben den Identitätsabgleich. |
| [Analyserouter](../../backend/app/features/analysis/api/router.py), `get_run` / `get_snapshot`; [Analysis-Service](../../backend/app/features/analysis/service/application.py), `details`, `snapshot`, `_require_analysis`, `_require_run` | Beide GETs prüfen den Workspace und lösen exakt Analyse-ID + Run-Version auf. Snapshotzeilen **und** Anzahl werden ausschließlich mit dieser gespeicherten `run.id` gelesen. Keine Providerabfrage oder Analyseausführung. |
| [Snapshotrepository](../../backend/app/features/analysis/persistence/repositories.py), `list_snapshot`, `count_snapshot`; [Modelle](../../backend/app/features/analysis/persistence/models.py) | Sortierung nach `trading_date`, eindeutiges `(run_id, trading_date)` sowie `(analysis_id, version)`; Zeilen und Count sind rungebunden. |
| [Immutable Snapshot ADR](../decisions/ADR-S4-002-IMMUTABLE-ANALYSIS-SNAPSHOT.md); [Snapshotpersistierung](../../backend/app/features/analysis/service/application.py), `_execute_snapshot` | `observation_count=len(rows)` wird mit dem exakten Inputsnapshot gespeichert; spätere Reads führen keine Neuberechnung durch. |
| [EntryPlan](../../backend/app/features/trade_plan/domain/models.py), `__post_init__` | Bestehender Währungsvertrag fordert einen nichtleeren String (`currency.strip()`). Kein zusätzlicher ISO-Regex, aktueller Katalog oder selbst erfundene Normalisierung. Der belegte String wird unverändert übernommen. |

### Tatsächliche Antwortbindung

Zuerst werden **alle** Quellen mit Rolle UNDERLYING gezählt; exakt eine muss
ANALYSIS sein. Fehlende ID, ungültige Run-Version oder fehlende Modellreferenzen
ergeben keinen Vorschlag. Der gelieferte Run muss exakt dieselbe Analyse-ID,
Run-Version, den geprüften Candidate-Basiswert und dieselben vorhandenen
Modellreferenzen tragen; eine gespeicherte Listingidentität muss vorhanden sein.
Sie wird nicht durch das heutige Primary-Listing ersetzt oder dagegen ausgewählt.
Historischer Status, Datenalter oder heutige Modellverfügbarkeit begründen keine
zusätzliche Freigabeschwelle für diese unveränderte Einheit.

`SnapshotPage` enthält ausschließlich `items`, `total`, `offset`, `limit` und
**keinen** erneuten Analyse-/Run-ID-Echo. Der Bindungsnachweis ist daher die
geprüfte tatsächliche Run-Antwort **zusammen mit** dem oben belegten bestehenden
öffentlichen serverseitigen Readervertrag. Es wird kein unabhängiger
Identitätsnachweis innerhalb jeder Zeile behauptet. Ein passender URL-String
allein genügt nicht. DTO, API und persistierte Referenzen müssen dafür nicht
geändert werden.

### Vollständigkeit über vorhandene Pagination

Der Read konsumiert ausschließlich `getSnapshot(id, version, offset, limit,
signal)` desselben festen Ursprungs. Die vorhandene Route erlaubt Seiten von
höchstens 200 Zeilen; dies ist eine **Seitengröße, keine Gesamtobergrenze**.

1. `run.observation_count` muss eine positive sichere Ganzzahl sein.
2. Beginn bei Offset 0, danach lückenlos fortschreitende Offsets. Jede Antwort
   muss den angeforderten Offset und das Limit bestätigen; `total` muss mit der
   gespeicherten Beobachtungszahl übereinstimmen und über alle Seiten gleich bleiben.
3. Die erwartete Seitenlänge ist `min(limit, total - offset)`. Leere oder verkürzte
   Zwischenseiten, zu viele Zeilen, widersprüchliche Metadaten und wiederholte
   beziehungsweise nicht fortschreitende Datumszeilen liefern keinen Vorschlag.
4. Jede Zeile muss denselben unveränderten, nichtleeren Währungsstring tragen.
   Konflikte auf späteren Seiten verwerfen den gesamten Vorschlag.
5. Erst nach exakt allen erwarteten Zeilen und ohne Abbruch darf ein Ergebnis
   zurückgegeben werden. Fehler/Abort erzeugen keinen Teilvorschlag und keinen
   automatischen Retry. Kein `verify`-POST, `run`, `latest`, Providerread oder
   Finanzresolver ist beteiligt.

### Ownerabgleich und Umsetzungsentscheidung

Die bestehende Quelle genügt für den ausdrücklich neu vorgeschlagenen engen
Erstellungsfall. Es verbleibt kein konkreter Widerspruch, der einen neuen
Backendresolver oder eine neue allgemeine Inventur erfordert. Die nachfolgenden
öffentlichen Grenzen sind Teil dieser Draftentscheidung:

- Analysis erhält einen schmalen öffentlichen Leseadapter mit genauer
  Quellenreferenz, Underlying und AbortSignal; er konsumiert die bestehenden
  `getRun`-/`getSnapshot`-Reader und liefert nur die geprüfte Währung mit
  Analyse-/Run-/Listingbezug oder keinen Vorschlag. Kein Reexport des gesamten
  internen Clients und kein neues REST-DTO.
- TradePlan prüft genau eine UNDERLYING-Quelle der bereits gebundenen Evaluation
  und konsumiert diesen öffentlichen Adapter. Das Formular kopiert keine
  Analyse-/Währungsresolverlogik.
- UX1 besitzt Initialisierung und Entwurfsschutz. FT-007 behält den manuellen
  Planwert, DRAFT-Command und explizites Approval. UX3-Hinweissemantik und
  UX2-Navigations-/Dirty-/Busy-Grenzen bleiben erhalten. Eine korrekte
  Textreferenz benennt Analyse und Run-Version, ohne die Navigation zu erweitern.

## Phase 2: begrenztes Verhalten und erforderliche Regressionen

Die neue Formularinstanz startet weiter mit `createEmptyTradePlanContent()`.
Erst nach erfolgreichem erforderlichem Ursprungsread beginnt separat der optionale
Read. Sein Ergebnis darf nur vor dem ersten echten Formularedit einmalig direkt
initialisieren; es läuft nicht durch den menschlichen `onChange`-Pfad und setzt
keinen Dirty-Zustand. Alle Inhaltsfelder einschließlich Targetaktionen und
Entry-Art setzen die dauerhafte Editsperre. Bereits eingegebene Preise werden
keiner verspätet eintreffenden Währung zugeordnet.

Formularinstanz und Anfragegeneration bleiben getrennt vom Ursprungsschlüssel.
Cleanup invalidiert die Generation und bricht Reads ab. A→B→A kann dadurch keine
alten Werte oder Fehler wiederbeleben. Herkunft wird nur lokal zur initialisierten
Währung gehalten; die erste manuelle Währungsänderung entfernt sie dauerhaft.
Andere Edits können den weiterhin unveränderten Währungsvorschlag erklärt lassen.
Bewusstes Speichern verwendet allein den sichtbaren Endwert im bestehenden
Create-DRAFT-Payload; die spätere Ansicht erfindet keine Übernahmeprovenienz.

| Fall | Erforderlicher Nachweis, vor Ausführung noch kein bestandener Test |
|---|---|
| 1 | Einheitliche historische Währung initialisiert nur das unberührte Candidate-Formular. |
| 2 | Neuere Evaluation und abweichende aktuelle Listingwährung ändern den historischen Pin nicht. |
| 3 | Mehrere UNDERLYING-Quellen, falsche Analyse/Version/Underlying/Modellantwort liefern keinen Vorschlag. |
| 4 | Leer, gemischt oder Readfehler: kein Vorschlag, gültiger manueller Weg bleibt benutzbar; ungültiger Ursprung bleibt blockiert. |
| 5 | Währungskonflikt erst nach der ersten Snapshotseite verhindert jede Übernahme. |
| 6 | Abbruch, fehlende/verkürzte Seite, falscher Count/Offset oder fehlender Fortschritt ergeben keinen Teilvorschlag. |
| 7 | Vorheriger Preis-/Referenz-/Stop-/Target-/Währungs-/Thesisedit schützt vor später Antwort. |
| 8 | Bearbeiten→Leeren hebt die Sperre nicht auf; Rückkehr zum gleichen Währungscode stellt Herkunft nicht wieder her. |
| 9 | Kontextwechsel und A→B→A verwerfen alte Erfolge und Fehler; jede neue Instanz hat eigene Zustände. |
| 10 | Manueller Ursprung, Amendments und gespeicherte Versionen behalten Inhalt und vorhandene Readergrenzen. |
| 11 | Vorschlag/Quellenread erzeugt keinen Write, keine Analyseausführung, Freigabe oder Navigation; Initialisierung allein keinen Dirty-Dialog. |
| 12 | Bewusstes Speichern erzeugt genau den bestehenden DRAFT mit dem sichtbaren Endwert; Busy, Concurrency, Unknown und Replaygrenzen bleiben erhalten. |

### Nachweisführung und Abnahmegrenze

Die Phase-1-Dokumentation ist vor jedem Runtimeedit als eigener Commit
`7454a7c0a22b9be7504075824cf8dc66fd73a4f3` erhalten.
Gezielte Quellen-/Formular-/Browserregressionen sowie Typecheck, Lint und
Formatprüfung ergänzen anschließend die unveränderten regulären PR-Gates:
Backend quality, restrictive-umask image, issuer renderer sandbox; Frontend
quality; E2E smoke, realized gross owner, candidate governance owner und journal
and evidence owner; Version publication guards. Der regulär übersprungene Tagjob
eines PR ist keine Veröffentlichung.

Konkrete Testresultate, finaler Head, tatsächlicher Testmerge/Tree und Joblinks
werden erst nach Ausführung in diesem Nachweis beziehungsweise im selben Draft-PR
ergänzt. Die obige Matrix ist bis dahin eine Anforderung. Alte grüne Läufe anderer
PRs zählen nicht. Keine Änderung an Gates, Retries, Schutzregeln, fünf
Masterdateien, gemeinsamer Trade-Workspace-E2E-Datei, Versionen oder Finanzlogik.
Menschlicher FT-007-/UX1-Review und fachliche Bedienabnahme bleiben offen;
technische Prüfungen erteilen weder Merge- noch Release-/PC-Freigabe.

## Implementierter Draft und technische Prüfung

Nach dem positiven Quellen-/Ownerabgleich wurde Phase 2 auf derselben Basis
umgesetzt. Der Draft enthält den Vorschlag als neues Verhalten; Ausgangs-Main
und veröffentlichter Tag enthalten diese Automatik weiterhin nicht.

### Konkrete Produktgrenze

- [Öffentlicher Analysis-Adapter](../../frontend/src/features/analysis/public/historicalSnapshotCurrency.ts)
  und [enger Export](../../frontend/src/features/analysis/index.ts): tatsächliche
  Runidentität prüfen, vollständige Pagination lesen, exakten einheitlichen
  Währungsstring liefern. Bestehende Reader, Standardaufrufe, DTOs und Backend
  bleiben unverändert.
- [Candidate-Quellenauswahl](../../frontend/src/features/trade_plan/services/planCurrencySuggestion.ts):
  genau eine UNDERLYING-Rolle vor Prüfung des ANALYSIS-Typs; nur die bereits
  geprüfte Evaluation, keine aktuellen Listing- oder latest-Lookups.
- [Erstellungsflow](../../frontend/src/features/trade_plan/pages/TradePlanPage.tsx):
  separater optionaler Read, einmalige direkte Initialisierung, dauerhafter
  `humanEdited`-Schutz, Anfragegeneration und Abort. Der bestehende
  Formular-Remount bei akzeptiertem Kontextwechsel bleibt erhalten.
- [Inhaltsformular](../../frontend/src/features/trade_plan/forms/TradePlanContentForm.tsx):
  nur additive optionale Hinweisprop; Währungsfeld bleibt sichtbar/editierbar
  und über `aria-describedby` mit der Analyse-/Versionstextreferenz verbunden.
  Kein Reader, Resolver oder Default im Formular.

`content.ts`, `originContext.ts`, `ExistingTradePlanPage.tsx`, Backend,
Candidate-/Analysis-Standardreader, Ausführungswährungsresolver, Navigation,
Workflow-/Versionsdateien und die fünf Masterdokumente wurden nicht geändert.
Der komplette neue fachliche Effekt ist **ein erneut einzugebender Währungscode
weniger pro qualifiziertem neuen Candidate-Plan**. Das gilt nicht für fehlende
Quellen oder bereits bearbeitete Formulare und enthält keine Nutzungsquote.

### Zuordnung der Regressionen

Die Dateien enthalten ausführbare Anforderungen für die obigen Fälle. Erst ein
vollständig beendeter Lauf am zugeordneten Head qualifiziert sie als bestanden.

| Testfläche | Konkrete Assertions |
|---|---|
| [Analysis-Adapter, 45 Fälle](../../frontend/src/features/analysis/public/historicalSnapshotCurrency.test.ts) | Tatsächliche HTTP-Readeraufrufe mit `include_snapshot=false`, 401 Zeilen auf drei Seiten, GET-only ohne Body, alte Modellreferenz, exakter Code, falsche Antwortidentität, leere/ungültige Quelle, später Währungskonflikt, widersprüchliche/verkürzte/wiederholte Seiten, HTTP-Fehler und Abbruch. |
| [Candidate-Selector, 22 Fälle](../../frontend/src/features/trade_plan/services/planCurrencySuggestion.test.ts) | Historischer Pin trotz heutiger EUR-Notierung, manuell ohne Read, mehrere UNDERLYING-Rollen auch mit unterschiedlichem Typ, fehlende Referenzen, optionale Fehler ohne Ursprungsmutation. |
| [Erstellungsflow, 25 Fälle](../../frontend/src/features/trade_plan/pages/TradePlanPage.currency-suggestion.test.tsx) | Initialisierung, neuere Evaluation ignorieren, finaler sichtbarer Savewert, manueller Fallback, ungültiger Pflichtursprung, gespeicherter Plan/Amendment unverändert, vorherige Feldedits, Edit→Leer, dauerhafte Herkunftsgrenze, Dirty/Busy/Unknown, A→B→A mit ausstehenden **und bereits abgeschlossenen** alten Erfolgen/Fehlern. |
| [Gemeinsames Formular](../../frontend/src/features/trade_plan/forms/TradePlanContentForm.test.tsx) | Zusätzlicher Hinweis-/Editierbarkeitstest; generischer Leerstart ohne versteckte Währung unverändert. |
| [Eigene Browserstrecke, fünf Fälle](../../tests/e2e/ux1-b-plan-currency-suggestion.spec.ts) | 201 Zeilen über zwei Seiten; vor letzter Seite kein Vorschlag; historische USD-Quelle trotz aktueller EUR-Notierung und neuerer Evaluation; 1280/390 px, editierbare Herkunft, genau ein bewusster DRAFT-POST mit CHF, Konflikt erst auf letzter Seite, verspätete Quelle nach Preis- beziehungsweise Thesis→Leer-Edit. Alle API-/XHR-/Fetchzugriffe sind synthetisch abgefangen; unbekannte Requests bleiben Fehler. |
| Bestehende Regressionen | Page-, Deep-Link-, ExistingPlan- und Form-Suites, Analysis-Client sowie Backend Analysis/Candidate/TradePlan einschließlich Candidate→TradePlan- und Plan→ProductSelection-Handoff. |

### Lokale Ergebnisse und offen gehaltene Ausführungsgrenzen

Toolchain: Node **22.16.0**, npm **10.9.2**, Python **3.12.14** mit den
Repositorymanifesten; keine Lockdateiänderung. Lokale Tests verwenden synthetische
Antworten und keine produktive Datenbank. Die folgenden Befunde sind von der
regulären PR-CI zu unterscheiden:

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Bestehende Backend-Units Analysis, Candidate, TradePlan und beide Handoff-Integrationen | **335 bestanden**, Exit 0, 44,78 s. Eine bestehende Starlette/AnyIO-DeprecationWarning; keine lokale PostgreSQL-Qualifikation behauptet. |
| Vollständiger Frontend-Typecheck | Exit 0 nach Korrektur dreier unzulässiger `exact`-Optionen in neuen Testing-Library-Testaufrufen; keine fachliche Assertion entfernt. |
| Gezielt ESLint und Prettier | Neue/angepasste Frontenddateien sowie Browser-Spec geprüft; keine Regelabsenkung. |
| Statischer Browserbuild | Vite-Build erfolgreich; bestehende Chunkgrößenwarnung. |
| Gezielte Vitest-Läufe | Quellenlauf meldete 69, Formularlauf zuletzt 86 grüne Fälle auf Dateiebene. Der lokale Runner beendete den Workerabschluss nicht regulär; begrenzter Quellengegenlauf Exit 124, ursprüngliche Prozesse beendet. **Kein vollständig bestandener lokaler Vitest-Gesamtlauf behauptet.** |
| Lokaler Chromiumlauf | Fünf Fälle entdeckt; Chromium 140.0.7339.16 bricht bereits beim Start mit SIGTRAP ab, auch beim isolierten `about:blank`-Start. Keine Produktassertion erreicht, kein bestandener Browsernachweis und keine Screenshots behauptet. Keine Browserflags oder Schutzregeln zur Umgehung geändert. |
| Dokumentation / Diff | UTF-8, vollständige Codeblöcke, lokale Linkziele und `git diff --check` geprüft. |

Die **maßgebliche finale Qualifikation** wird in der Beschreibung des einzigen
Draft-PRs dieses Branches mit finalem Head, tatsächlichem Testmerge/Tree,
aktueller Mainbasis und allen neun regulären Prüfjobs gebunden. Ein fehlender,
fehlgeschlagener oder abgebrochener Lauf bleibt dort ausdrücklich offen, bis die
reguläre CI ihn tatsächlich qualifiziert. Die lokalen Ausführungsgrenzen oben
werden nicht nachträglich als erfolgreiche Läufe umgedeutet.

Die neue Regel bleibt zur menschlichen Prüfung durch UX1/FT-007 im Draft.
Fachliche Bedienabnahme und reale Quellenabdeckung sind nicht aus synthetischen
Tests ableitbar. Kein Merge, Release, Tag, PC-Update oder produktiver Write wurde
durchgeführt oder für diesen Auftrag freigegeben.
