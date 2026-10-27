# UI6 — Journalansicht und exakte Quellenaufrufe konsolidieren

Umsetzungsstand vom 27.10.2026. Technische Entwicklungsqualifikation; keine
fachliche Abnahme, Veröffentlichung oder nachgewiesene Installation am Nutzer-PC.
Arbeitsstatus bleibt ausschließlich in [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal).

## Basis, Dateigrenzen und Prüfbindung

- Vor Beginn erneut gelesener Main:
  `eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4`, Tree
  `a864274c4c050698e1fc61134a98dfb03dcf1441`.
- `VERSION` 1.5.23 und Tag `v1.5.23` zeigen auf diesen Stand. UI1–UI5
  (#285/#284/#286/#287/#288) sind integriert und werden nicht erneut implementiert.
- Eigener Branch: `refactor/journal-ui-consolidation`.
- Qualifizierter Implementierungs-/Testcommit:
  `3ed591ccee1f576c635655f3c90a83cce3f0c56d`; vollständiger Tree:
  `e4bc00d82b003df1547f43209f2b93656f10f701`. Die abschließenden lokalen
  Frontend-/Browserprüfungen unten wurden auf genau diesen Anwendungsdateien und
  lokalen Testfällen ausgeführt. Der folgende Dokumentationscommit ändert sie nicht.
  Die native Journey wird im regulären CI-Lauf des endgültigen PR-Heads qualifiziert.
- [Draft-PR UI6](https://github.com/burckhju/trading-workspace/pull/289) bindet den endgültigen PR-Head, dessen Tree und die
  regulären PR-Workflows separat. Ein grüner Basislauf ist kein Nachweis für UI6.

README und Development Guide/Coding Standards wurden gelesen; im Checkout wurden
keine zusätzlichen `AGENTS.md` gefunden. Vor Beginn waren neun PRs offen:
#268, #235, #225, #220, #207, #205, #197, #187 und #90. Kein alter Branch wurde
übernommen. Der tatsächliche Diff von #90 ist unten eingeordnet.

Geändert werden der Journal-Consumer samt direkten Hilfsdateien/Tests,
`journalClient`, die Post-Trade-Einbettung, eng begrenzte Lesson-/Reviewadapter,
die bestehende native Journaljourney und eine eigene isolierte Browserregression.
`JournalEvidenceOrigin` aus UI3 bleibt unverändert. Backend, Datenmodell,
Migrationen, APIs, Finanzregeln, Scheduler, globale Guard-API, Versionen, Runner,
Prüfschwellen und CI-Workflows bleiben unverändert.

## Bedienweg vorher und nachher

| Vorher | UI6 |
|---|---|
| Einmalige Auswertung von `window.location.search`; unbekannte ID konnte auf die neueste Version fallen. | Laufender React-Router-Kontext; explizite ID muss im exakten Trade/Journal vorkommen. Ein Fehler liefert keinen Ersatzstand. |
| Lokale Versionswahl ohne passende URL und unzuverlässige gleichbleibende Trade-Queries. | Kompakte Versionsauswahl schreibt `journal_version_id`; Querywechsel, Reload und Zurück/Vor wählen denselben gespeicherten Stand. |
| Draftfelder und zusätzliche Volltextvorschau in der Abschlussbestätigung. | Ein Journaltextbereich: Lesen, vollständig vorbefülltes Bearbeiten oder Bestätigung ersetzen einander. |
| Schutz nur bei lokaler Versionswahl; direktes Laden konnte Eingaben ersetzen. | Ein zentraler Seitenguard plus bewusste lokale Verwerfen-/Ladeentscheidungen schützen alle betroffenen Formulare. |

Ein gespeicherter DRAFT öffnet im Lesemodus. **Journal bearbeiten** übernimmt alle
drei gespeicherten Felder vollständig. Ein neu bestätigter CREATE_DRAFT öffnet
nach exaktem Readback und URL-Auswahl direkt seine Bearbeitung. Ein SAVE kehrt
erst nach dem passenden aktuellen Readback in den Lesemodus zurück.

Die Abschlussbestätigung ersetzt den Textbereich und zeigt genau einmal alle
drei gespeicherten Texte, konkrete Journalversion, Bearbeitungsrevision und
gespeicherte Reviewquelle. Ungespeicherter Text wird weder mitgespeichert noch
finalisiert. Abbrechen kehrt zum vorherigen Modus zurück; bewusstes Verwerfen
kehrt zum gespeicherten Lesemodus zurück und sendet keinen Command.

`what_went_well`, `would_do_differently` und `additional_notes` bleiben optional.
Ein leerer DRAFT wird neutral als leer bezeichnet; eine leere Abschlussvorschau
und ein leerer FINALIZED-Stand als **inhaltsleerer Abschluss**. Keine neuen
Pflichttexte, Scores, Zeichenlimits oder erzeugten Interpretationen.

Finale Versionen bleiben unveränderlich. Bei einer betrachteten älteren Version
benennt die CREATE-Bestätigung ausdrücklich die **letzte finale Version** als
serverseitigen Kopierursprung. Ein vorhandener DRAFT wird bewusst geöffnet;
die Oberfläche fordert keinen zweiten Entwurf an. Vorgänger, Evidence und Lessons
werden nicht verändert.

## Exakte URL- und Quellenbindung

Der vorhandene Einstieg bleibt
`/post-trade?trade_id=…&journal_version_id=…`. Es gibt keine zusätzliche API.
Der bestehende History-Read liefert die Prüfung der Trade-ID, Journalzugehörigkeit
aller Einträge, eindeutiger Versions-IDs und der ausdrücklich angefragten Version.
Ohne explizite ID darf nur beim Einstieg der eindeutig als `is_latest` ausgewiesene
Stand gewählt werden; auch diese Auswahl bleibt bei späteren Quellenrefreshes
gebunden. `version()` und die exakten UI3-Herkunftsprüfungen bleiben erhalten.

Leere/Whitespace-IDs, fehlender oder widersprüchlicher Trade, doppelte
Versionsparameter (auch identische Duplikate), unbekannte Versionen und fremde
Trade-/Journalzugehörigkeit erzeugen einen verständlichen Fehler. Ein ungeklärter
Kontext schaltet keine Journalwrites frei. Die Versionswahl erhält weitere
Kontextparameter. Der vorhandene Trade-Lookup entfernt beim bewussten Tradewechsel
die vorherige Journalversions-ID. Eine fremde, von außen mitgebrachte ID wird
stattdessen als ungültig abgewiesen.

Es gibt keinen normalisierenden Navigationseffekt beim Einstieg oder Refresh.
Die Auswahl schreibt die URL aufgrund einer ausdrücklichen Aktion; CREATE wählt
erst nach bestätigtem Receipt und exaktem Readback sein Ergebnis. Andere offene
Formulare bleiben dabei dem zentralen Guard unterstellt. Ein Quellenrefresh von
V1 wird nicht durch ein inzwischen vorhandenes V2 zu einem Versionswechsel.

Gespeicherter Journalstatus, `is_latest`, konkrete
`source_exit_review_version_id` und heutige `source_currentness` mit
`source_checked_at` bleiben getrennte Aussagen. Die technische Herkunft und das
Audit sind aufklappbar. Die Lessons behalten kompakte Quellenverweise; dort werden
keine Journalvolltexte erneut eingebettet.

## Erhaltene Schreibverträge

Die vollständigen Verträge in `journal_router.py`, `journal_service.py`,
`journalClient.ts` und
[ADR-POST-FT012-005](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md)
sind die fachliche Basis.

| Command | Unveränderte Bindung und Wirkung |
|---|---|
| CREATE_DRAFT | `expected_latest_version_id`, genaue `expected_exit_review_version_id`, `confirmed`; erster Entwurf oder Kopie des letzten Finalstands, bestehender FT-011-Handoff. |
| SAVE_DRAFT | Konkrete `version_id`, bisherige `expected_edit_revision`, alle drei Texte. Bleibt bei STALE/UNKNOWN/nicht bereiter Reviewquelle zulässig, sofern genau diese Draftbasis gültig gelesen und unverändert ist. |
| REBIND_SOURCE | Konkreter DRAFT, erwartete Revision, genaue neue Reviewversion, `confirmed`; eigenständige Aktion mit geeignetem Handoff. |
| FINALIZE | Konkreter DRAFT, erwartete Revision, genaue gebundene Reviewversion, `confirmed`; friert nur den bereits gespeicherten Inhalt ein. Bei Dirty-Text gesperrt. |
| MATERIALIZE | Konkrete finale `version_id`, `confirmed`; historische/STALE-Versionen sind ausdrücklich zulässig. Das Receipt enthält eine Evidence-ID, keine Journalversions-ID. |

MATERIALIZE hält die ausdrücklich materialisierte Journalversion gewählt und
prüft im Readback deren Evidence-ID gegen das Receipt. Eine historische Quelle
wird nicht revalidiert, umgebunden oder in eine automatische Lesson verwandelt.
`TRADE_JOURNAL_VERSION`-Evidence und direkte `FT011`-Evidence bleiben verschiedene
Quellen mit verschiedenen Ableitungsformularen.

Konkrete API-Fehler wie `JOURNAL_CONFLICT`, `SOURCE_VERSION_MISMATCH`,
`JOURNAL_SOURCE_NOT_READY`, `JOURNAL_NOT_FOUND` und `IDEMPOTENCY_KEY_REUSED`
erhalten unterscheidbare Meldungen. Eine offene Bestätigung hält ihren alten
Snapshot und ihre IDs fest. Änderung von Version, Revision, gespeichertem Inhalt,
relevanter Quelle oder Handoff sperrt sie; neue Werte werden nicht still in den
alten Dialog eingesetzt. Ein bloß neuer Prüfzeitpunkt erzwingt keinen Versionswechsel.

## Lokale Eingaben, Receipt und Readback

Der Journalzustand trennt drei Verantwortungen:

1. Die frische History besitzt den gespeicherten Stand und die aktuelle
   Quelleninspektion.
2. Der lokale Editor besitzt seine unveränderte Ausgangsversion samt Revision
   und die noch nicht gespeicherten Texte.
3. Ein Schreibversuch hält Trade, eingefrorenen Command, Idempotency-Key und
   eingefrorene Actorbindung fest; ein Receipt benennt nur Ergebnis und Replay.

Ein Refresh überschreibt keine offene Bearbeitungsbasis. Bei externer Revision,
gespeicherter Quellumbindung oder anderem Inhalt bleiben die Eingaben erhalten,
während betroffene Aktionen gesperrt werden. Erst bewusstes Verwerfen oder Laden
übernimmt den gespeicherten Stand. Ein fehlgeschlagener Read ersetzt weder Journal
noch eingebetteten Lessonentwurf durch einen Ladeplatzhalter.

Bei unbekanntem Schreibausgang erfolgt kein automatischer Retry. Der ausdrücklich
gewählte identische Retry sendet denselben alten Command, Key und Actor, auch wenn
inzwischen lokal weitergetippt wurde. Ein neuer geänderter Auftrag bekommt einen
neuen Key. Der normale Read und das bewusste Laden können den unbekannten Ausgang
nicht zu einem bestätigten Command erklären; Folgeaktionen bleiben gesperrt.

Ein erfolgreicher Write mit gescheitertem Readback bleibt ein bestätigter Write.
**Nur Lesestand erneut laden** sendet keinen Command. Die erwartete Journalversion
muss exakt vorhanden sein; es gibt keinen Ersatz durch `versions[0]`. Bei SAVE
und REBIND wird nur der passende aktuelle Stand mit erwarteter Folgerevision,
Texten und Quelle automatisch als erledigt behandelt. Ein früheres SAVE-Replay
bei inzwischen fortgeschrittener Revision erhält die lokalen Texte und verlangt
einen bewussten Abgleich. FINALIZE bestätigt zusätzlich finalen Status, genaue
Revision, Quelle und unveränderte gespeicherte Texte.

Synchrone Ref-Sperren greifen vor dem nächsten React-Render. Reads werden
abgebrochen und zusätzlich durch Read-, Lifetime- und Kontextgenerationen
abgesichert. A→B→A oder ein Unmount macht alte Antworten ungültig; StrictMode
erzeugt keinen Command. Der Editor ist während eines laufenden Writes nicht
verwerfbar. Die lokale Bearbeitung wird nicht automatisch außerhalb der Seite
gespeichert; bewusst bestätigtes Verlassen bleibt eine Verwerfung.

## Zentraler Entwurfsschutz und begrenzte Adapter

`PostTradeLearningPage` besitzt genau einen `PendingNavigationGuard` mit
unveränderter globaler API. Eine kleine Teilnehmermap koordiniert Journal,
Review, direkte FT011-Lesson und direkte Materialisierung; das Journal aggregiert
seine eingebettete Lesson. Die optionalen Rückmeldungen melden Eingaben und
Submitbeginn synchron. Ein erfolgreicher Einzelauftrag beendet ausschließlich
seinen Teilnehmerzustand.

Route-, Trade-, Query-, Zurück/Vor- und native Verlassen-Versuche werden geschützt.
**Hier bleiben** erhält alle betroffenen Eingaben. Bewusstes Navigationsverwerfen
wird über einen Zähler an die betroffenen Formulare gemeldet; während Pending
gibt es keine Verwerfen-Freigabe. Lokales Laden und Bearbeitungsverwerfen besitzen
eine eigene konkrete Bestätigung. Ein optionaler synchroner Pending-Getter sperrt
diese lokalen Entscheidungen auch während eines Writes eines anderen
Seitenformulars, ohne den geerbten Zustand als eigenen Pendingstatus zurückzumelden.
Versionswahl verwendet die echte Router-Navigation, nicht einen erzwungenen
Key-Rerender als Ersatz für den Schutz.

`LessonDraftFromEvidence` hält seine tatsächlich gebundene Evidence bei einem
Quellenwechsel fest und sperrt den Submit bis zum bewussten Abgleich. Die neue
Evidence wird nicht still an einen vorhandenen Text gehängt. Unveränderter Kontext
bleibt bei Refresh oder Lesefehler gemountet. Die optionalen Adapter verändern
keinen Lessonpayload und erzeugen keinen Journal-Idempotency-Key: der bestehende
Lessonclient sendet einen normalen POST. Bei unklarer Antwort wird nicht
automatisch erneut angelegt; dieser POST besitzt keine Journal-Replaygarantie.

Der Reviewadapter meldet Dirty/Pending und hält offene Texte bei Refresh und
externem Versionswechsel fest. Ein fehlgeschlagener Read kann durch einen alten
Cache nicht Schreibaktionen erneut freigeben. Die bereits vorhandene
Parent-Refresh-Sperre sowie FT-011-Commands und ihre Reihenfolge bleiben erhalten.
Die direkte FT011-Materialisierung behält ihre genaue Reviewbindung und wird
zusätzlich als laufender Seitenteilnehmer gemeldet. Es gibt keinen Umbau des
Reviewablaufs und keine neue allgemeine Guard-API.

## Tatsächlich ausgeführte lokale Prüfungen

Laufzeit: Node **22.16.0**, npm **10.9.2**, Python **3.12.14**. Node24 verursachte
im lokalen Testkontext einen undici/jsdom-AbortSignal-Fehler; die für das Repository
vorgesehene Nodeversion löste ihn ohne Testshim. Die eingeschränkte Prozesssandbox
ließ einzelne Testprozesse nach Ausgabe hängen; die identischen Befehle wurden
im freigegebenen lokalen Prozesskontext ordnungsgemäß beendet. Es wurden keine
Prüfschwellen, Runner oder Workflows verändert.

| Prüfung | Ergebnis und Aussage |
|---|---|
| Unverändertes `bash scripts/check-frontend.sh` | 138 Dateien / 1.312 Tests bestanden, Exitcode 0. Coverage: Statements/Lines 95,29 %, Branches 89,08 %, Functions 90,00 %. Typecheck, ESLint ohne Warnungen, Prettier, komplette Coverage-Suite und Produktionsbuild erfolgreich. |
| `TradeJournalPanel.test.tsx` | 33 Komponenten-/Routerregressionen. `createMemoryRouter`/`RouterProvider`, kein MemoryRouter als Guardnachweis. |
| `journalClient.test.ts` und `journalViewState.test.ts` | 14 + 22 Tests zu Identität, Actor/Key/Command, Receipts, Query und fest gebundener Bestätigung. |
| Lesson-, bestehende Parent-, Review- und neue Parentintegration | 56 Tests (6 + 11 + 22 + 17). Die 17 Integrationen verwenden echte Parent-, Journal-, Lesson- und Reviewkomponenten; nur I/O ist gemockt. |
| `JournalEvidenceOrigin.test.tsx` und bestehende Learning-Tests | Im vollständigen Frontend-Gate enthalten; UI3-Consumer unverändert. |
| `test_journal_commands.py`, `test_journal_api.py`, `test_journal_source_inspection.py` | 40 bestanden; bestehende Backendverträge, kein PostgreSQL-Nachweis. |
| `test_journal_e2e_contracts.py` und `test-journal-api-guard.mjs` | 91 Python- und 1 Node-Schutztest bestanden. |
| Isolierte Chromium-UI- und Handoff-Specs | 6/6 bestanden: drei neue UI6- und drei bestehende Handoff-Fälle, Node 22.16.0, Chromium, ein Worker, keine Skips/Retry; 16,4 s. Echte Oberfläche/Router mit synthetischem HTTP, keine echte API oder PostgreSQL-Persistenz. |
| Owner-Discovery und unveränderter Reportchecker | Genau zwei vorhandene, unverändert benannte Journeys erkannt; Discovery ist kein Ausführungsnachweis. |
| Diff-/Scopeprüfung | Keine Backend-/API-/Migrations-/Versions-/Workflow-/Runneränderung; gezielte Dokumenteinfügungen erhalten alle vorhandenen historischen Zeilen. |

Der erste gemeinsame Vollgate-Lauf fand eine noch gesperrte bewusste
Evidence-Abgleichsaktion nach der Adapterhärtung. Die Parentfreigabe wurde korrigiert:
die Child-Kontextprüfung sperrt weiterhin den POST, während der ausdrückliche
Abgleich bei bestätigter neuer Quelle möglich bleibt. Der vollständige Abschlusslauf
oben qualifiziert die Korrektur. Die Browserprüfung fand außerdem den fehlenden
Fokusrücksprung nach Escape; Rückfokus und Tab-/ShiftTab-Trap sind jetzt explizit geprüft.

Der erste vollständige CI-Smoke-Lauf auf dem Zwischenstand `ac50ce48` zeigte zudem
eine sporadisch fehlende SOURCE_VERSION_MISMATCH-Meldung im vorhandenen
FT011-Handoff-Fall. Ein erfolgreicher Statusread löschte den konkreten
Commandfehler zu früh. Eine neue echte Parentintegration reproduzierte dies
deterministisch nach abgeschlossenem V2-Read. Die unbedingte Fehlerlöschung wurde
entfernt; nur bewusstes erneutes Laden oder ein neuer Command löscht die Meldung.
Die Regression, das Vollgate und die unveränderten sechs Browserfälle prüfen die
Korrektur. Es wurde kein Timeout erhöht und kein zusätzlicher Retry eingeführt.

### Zuordnung der 18 Abnahmefälle

`J` bezeichnet die direkten Journaltests; `S` die Client-/Zustandstests; `P` die
17 echten Parentintegrationen und Adaptertests; `B` die tatsächlich ausgeführte
synthetische Chromium-Spec. `N` bezeichnet Schritte der erweiterten nativen
PostgreSQL-Journey, deren Ausführungsbeleg separat im PR geführt wird.

| Fall | Konkreter Nachweis |
|---|---|
| 1 Historischer Link bleibt exakt | J: historischer V1-Refresh, implizite Einstiegsauswahl bleibt gebunden; B: V1-Link/Refresh/Reload; N: bestehender UI3-Quellenlink mit V1 trotz V2. |
| 2 Unbekannt/fremd/leer/widersprüchlich | J: sechs URLfehlformen, fremder Trade und falsches Journal; S: doppelte IDs/fehlende Version; B/N: ungültige URL ohne Latest-Inhalt/Command. |
| 3 URL, Reload, Query, Zurück/Vor | J: Data-Router-Navigation samt erhaltenem Kontextparameter; B/N: echte Browserhistorie und Reload. |
| 4 Einmaltext und Vorbelegung | J/B/N: drei Felder vorbefüllt, Lesen/Bearbeiten/FINALIZE ersetzen einander, jede gespeicherte Reflexion genau einmal. |
| 5 Unveränderliche Finals/Folgeentwurf | J: richtiger letzter Finalstand als Kopierursprung, vorhandener Draft wird geöffnet; N erhält Vorgänger/Evidence/Lesson-Prüfungen. |
| 6 Alle Texte optional/leer | J/S: drei optionale Felder, expliziter leerer Abschluss und immutable FINALIZED-Anzeige. |
| 7 SAVE bei STALE, strengere Quellenaktionen | J: SAVE bei unbereitem STALE-Handoff; separate Rebind-/Finalizepins; bestehende Backendtests. |
| 8 Kein Dirty-Autosave/-Finalize | J/B: blockierte FINALIZE-/Rebindaktionen, Abbrechen/Verwerfen ohne Command. |
| 9 Externe Revision/Quelle | J/S: alte Editorbasis bleibt, aktueller Read getrennt, offene Bestätigung invalidiert statt umgebunden; P: konkreter Reviewadapter. |
| 10 Identischer Retry/alter SAVE-Replay | J/S: gleicher Key/Trade/Actor/Payload, fortgeschrittene Serverrevision erhält lokale Eingaben und sperrt Folgeaktionen. |
| 11 Bestätigter Write/Readbackfehler | J: rein lesender Retry, fehlendes Resultat ohne neuesten Ersatzstand. |
| 12 Doppelklick/Unmount/StrictMode/A→B→A | J: synchrone Submitsperre, späte Receipt-/Readantworten nach Kontextwechsel; P/Adapter: StrictMode, Unmount und normale Lesson-POSTs. |
| 13 Route/Query/lokaler Dirty-/Pending-Schutz | J/P/B: echte Routerblockade, Zurück, Trade-/Querywechsel, beforeunload und Hier-bleiben-Fokus. |
| 14 Journal/Lesson überleben Refresh | J/P/B: echte Formulare behalten Eingaben bei erfolgreichem/gescheitertem Refresh und tatsächlichem Evidencewechsel. |
| 15 Review-/Materialisierungsadapter | P: Parent-Refresh-Sperre, fehlgeschlagene Reads, laufende Review-/FT011-Materialisierungswrites, getrennte Teilnehmerzustände; bestehende Handoff-Browserregression. |
| 16 Historisch/STALE materialisieren | J/S: konkrete finale Version bleibt gewählt, Receipt-Evidence-ID muss dort vorhanden sein; N behält native historische Quellenprüfungen. |
| 17 Keine automatische Fachmutation | J/P/B prüfen Commands/POSTs bei Lesen, Auswahl, URLwechsel, Abbrechen und Verwerfen; N zählt echte Journalcommand-Requests. |
| 18 Tastatur/schmale Ansicht/UI3/Journeys | J/B/N: Fokus, Escape, Tab/ShiftTab, 390 px ohne horizontalen Überlauf; UI3 und vorhandene Learning-Tests im Vollgate. Keine pauschale Barrierefreiheitsabnahme. |

## PostgreSQL, CI und Betriebsgrenzen

Lokal fehlen Docker und PostgreSQL. `test_journal_write_postgres.py` wurde daher
nicht lokal ausgeführt. Der unveränderte
`scripts/run-journal-evidence-e2e.sh` wurde aufgerufen und verweigerte den Start
mit `This runner requires its disposable GitHub Actions checkout.` Es wurden
keine CI-Identität und keine Write-Freigaben vorgetäuscht.

Der vorhandene PR-Workflow führt Backendintegration mit eigenem PostgreSQL und
den separaten Job **End-to-End / journal and evidence owner** aus. Dessen zwei
Testtitel und Identitäten bleiben unverändert; nur die passende bestehende
Journaljourney erhält neue Schritte. `check-journal-e2e-report.py` bleibt
unverändert und verlangt weiterhin genau diese zwei tatsächlichen Erfolge ohne
Skip/Retry. Nach FINALIZE wartet die Journaljourney ausdrücklich auf den im
Readback angezeigten FINALIZED-Stand von V1 beziehungsweise V2. Das bloße Fehlen
der Eingabefelder genügt dafür nicht, weil schon die Bestätigung den Editor ersetzt.
Der endgültige PR-Bericht führt Run, Checkout/Tree und Ergebnis als
eigenständigen CI-Nachweis. Die lokale Mock-HTTP-Prüfung ersetzt diesen nicht.

Die technische Qualifikation behauptet keine neue fachliche FT-011-Freigabe,
keine globale Serialisierbarkeit gegen sämtliche externen Änderungen und keine
PC-Abnahme. Quellenprüfungen gelten zum ausgewiesenen Lesezeitpunkt. Vorhandene
Backendkonflikte bleiben maßgeblich. Ein vollständiger menschlicher Mobil-/
Barrierefreiheitsreview und die fachliche Bewertung bleiben eigenständige Schritte.

## Integrationshinweis zu PR #90

Vor Beginn geprüft: [PR #90](https://github.com/burckhju/trading-workspace/pull/90)
ist offen, Head `7383e8edb965a7d2590cef2c8262e1407482336f`. Sein tatsächlicher Diff
betrifft nur `LessonDraftFromEvidence.tsx` und dessen Test: Erfolgsmeldung mit
`LS-…`, technisches UUID-Detail und **Lesson öffnen**-Link. UI6 basiert nicht auf
diesem alten Branch und übernimmt ihn nicht automatisch.

UI6 ändert dieselben Dateien ausschließlich für den notwendigen Dirty-/Pending-/
Kontextschutz. Die bisherige Erfolgsmeldung bleibt erhalten; es wird kein neuer
konkurrierender Erfolgslink in das Formular eingebaut. Der bereits vorhandene
Journal-Erfolgslink bleibt an seine tatsächlich erzeugende Evidence gebunden.
Bei späterer Integration von #90 sind dessen Anzeigeänderungen mit diesen
Adapterprops und den erweiterten Tests gezielt zusammenzuführen.

Die Lieferung endet beim geprüften Draft-PR. Merge, Versionsanhebung, Tag,
Veröffentlichung und Installation werden daraus nicht abgeleitet.
