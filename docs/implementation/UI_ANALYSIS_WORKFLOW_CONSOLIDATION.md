# UI7 – Analyse-Workflow: Eingaben und Versionskontext konsolidieren

Datum: 27.10.2026. Arbeitsbranch: `refactor/analysis-workflow-consolidation`.

## Auftrag, Ausgangsbasis und Nachweisgrenze

Dieser Schnitt führt die bisher verteilten Eingaben für Analyseanlage und neue Analyseversionen in einem kanonischen Editor zusammen. Vorhandene Analyse-, Basiswert-, Listing- und Quellversionsidentitäten werden übernommen. Die fachlichen Berechnungen sowie die Backend-, Snapshot-, Modell- und Lifecycle-Verträge bleiben bestehen.

Ausgangsbasis ist Main **`eff24912ebfc1499fcea2cbf32dc1dbf8b0975e4`**, VERSION **1.5.23**. UI3, UI4 und UI5 sind in dieser Basis bereits integriert. Ihre Implementierungen werden nicht erneut angelegt. Insbesondere bleiben die sieben Referenzdaten-/Mappingaktionen von UI5 bei `/chart-setup`; dieser Folgeschnitt konsolidiert den bisher separat behandelten `RUN_MARKET_ANALYSIS`-Einstieg.

Der freigegebene Folgeauftrag umfasst Implementierung und Prüfung sowie Merge bei grünen erforderlichen Prüfungen und die versionierte PC-Bereitstellung über den bestehenden Veröffentlichungsweg. Dieser Bericht behauptet keine bereits erfolgte Veröffentlichung oder Installation. Der tatsächlich qualifizierte Gesamtbaum, GitHub-Prüfungen, Merge, Tag und Bereitstellungsstatus werden im Abschlussnachweis eindeutig ergänzt. Eine tatsächliche Installation auf dem Nutzer-PC bleibt ein eigener Betriebsnachweis.

### Vorbereiteter Releasezusatz 1.5.24

Für die freigegebene PC-Bereitstellung ist **1.5.24** vorbereitet. Der abgeglichene Versionsdiff ändert genau fünf eigene Versionswerte in vier Dateien: `VERSION`, `backend/pyproject.toml`, `frontend/package.json` sowie die beiden Projektversionsfelder in `frontend/package-lock.json`. Dependencies und Lockauflösung bleiben unverändert. Die Änderung der Backend-Projektversion ist keine Backend-Domain-, API- oder Berechnungsänderung.

Diese Vorbereitung ist noch kein Veröffentlichungsnachweis. Der finale Release-Tree muss die unveränderten erforderlichen Prüfungen bestehen; Merge, Main-Push-Prüfungen, veröffentlichter Tag und PC-Bereitstellung werden anschließend getrennt zurückgelesen und gebunden. Die Release-Notiz gehört zu diesem gesondert erkennbaren Releasezusatz.

| Bindung | Stand dieses Berichts |
|---|---|
| Implementierungs-/Testcommit und vollständiger Tree | **wird durch Abschlussnachweis ergänzt** |
| Unverändertes vollständiges Frontend-Gate | **wird durch Abschlussnachweis ergänzt** |
| Backend-Regressionen und gegebenenfalls PostgreSQL-Nachweis | **wird durch Abschlussnachweis ergänzt** |
| Browsernachweis | **3/3 kontrollierte lokale Browserfälle bestanden**; der echte API-/PostgreSQL-Zweig steht noch aus. Finale Lauf-/Treebindung **wird durch Abschlussnachweis ergänzt** |
| PR-Head, tatsächlicher CI-Testmerge und reguläre Prüfungen | **wird durch Abschlussnachweis ergänzt** |
| Merge, erneute Main-Prüfungen, Veröffentlichung und PC-Bereitstellung | **wird durch Abschlussnachweis ergänzt** |

Frühere grüne UI5-/Releaseprüfungen gelten nicht als Ausführungsnachweis dieses neuen Dateistands. Die unten aufgeführten fokussierten lokalen Tests sind abgeschlossene Entwicklungsprüfungen; sie ersetzen kein vollständiges Gate und keinen Browser-/PostgreSQL-Nachweis.

## Bedienung vorher und nachher

| Einstieg | Bisheriger Ablauf | Neuer Ablauf |
|---|---|---|
| `/market-analyses` | Übersicht und eigenes Anlageformular mit Basiswert-/Listingauswahl | Lesende Übersicht mit bestehenden Filtern, Ansichten und Export; ausdrücklicher Link zum gemeinsamen Editor |
| `/market-analyses/:analysisId` | Ergebnis, Historie und eigenes Formular „Neue Analyseversion“; Auswahl der letzten Version beim Laden | Genau eine über `?version=` ausgewählte Ergebnisversion; Link zur Vorbereitung einer neuen Version aus genau dieser Quelle |
| `/top-down-admin?action=RUN_MARKET_ANALYSIS&…` | Eigene Datumsfelder und implizite Verkettung von Analyseanlage und Ausführung | Frische Prüfung des konkreten blockierten Schritts, anschließend Weiterleitung in den gemeinsamen Editor; kein zweites Analyseformular |
| Historische Candidate-Evaluation | Angegebene Analysequelle ohne durchgehenden exakten Versions-/Rückkehrkontext | Analysequelle öffnet die gespeicherte Version mit konkretem Candidate-/Evaluationsrückweg |

Der einzige Eingabeort für Anlage und neue Runs ist **`/market-analyses/setup`**. Die vorhandenen Übersichts-, Detail- und Top-down-Routen bleiben erreichbar. Der neue Editor wird über die vorhandene Anwendungsroute eingebunden; die globale Guard-API bleibt unverändert.

Ein normaler neuer Analyseauftrag hat zwei sichtbare Schritte:

1. Vorhandenen Basiswert und eine bestehende Notierung prüfen, nur fehlende Auswahl ergänzen und **genau eine Analyse anlegen**.
2. Die bestätigte neue Analyse-ID weiterverwenden, Zeitraum und alle Parameter prüfen und **genau einen neuen Lauf gesondert bestätigen**.

Eine bereits vorhandene Analyse beginnt unmittelbar beim zweiten Schritt. Ein Aufruf aus einer historischen Version bindet diese Version als Vorschlagsquelle. Der aktuelle Datenkontext erscheint kompakt einmal; nach erfolgreichem Run ersetzt der bestätigte Abschluss das Eingabeformular. Die Ergebnisdetails stehen unter einem eigenen, exakt versionierten Link.

Die Detailseite enthält weiterhin die eigenständigen Lifecycle-Aktionen Retry, Supersede und Verify. Ein geöffneter Retry- oder Supersede-Editor ersetzt den entsprechenden Aktionsbereich; es sind nicht mehrere Lifecycle-Formulare gleichzeitig aktiv.

## URLs und eindeutiger Kontext

`analysisWorkflowContext.ts` verantwortet das Parsen, Zusammenführen und Prüfen der Eingangsidentitäten sowie die internen Links. `canonicalAnalysisSetupUrl`, `analysisDetailUrl` und `analysisContextReturnTo` verwenden denselben Vertrag.

| Feld | Bedeutung und Prüfung |
|---|---|
| `analysis_id` | Bestehende oder bereits durch Create bestätigte Analyse; der vollständige GET-Datensatz muss genau diese ID besitzen |
| `underlying_id` | Tatsächlicher Owner eines Listings; keine pauschale Ableitung aus dem Candidate |
| `listing_id` | Explizite bestehende Notierung; muss genau einmal zu den gelesenen Listings dieses Owners gehören |
| `market_data_instrument_id` | Tatsächliches Dateninstrument; bei direkter Referenzanalyse bleiben Basiswert und Listing null |
| `source_version` | Positive ganze Quellversion im Setup; benötigt `analysis_id` und genau einen passenden gespeicherten Run |
| `version` | Positive ganze Ergebnisversion auf der Detailroute; ist dort die maßgebliche Auswahl |
| `candidate_id` | Konkreter Candidate und intern konstruierter Rückweg |
| `evaluation_id` | Optional konkrete historische Evaluation; nur zusammen mit `candidate_id` |
| `action` | Im Analysesetup ausschließlich `RUN_MARKET_ANALYSIS`; unbekannte Aktionen sperren |
| `resource_id` | Nur bei diesem Workflow ein Legacy-Fallback für die Listing-ID; muss zu expliziten IDs und Workflowparametern passen |
| `step_code` | Bindet den konkreten blockierten Schritt, auch wenn mehrere Rollen dieselbe Aktion anbieten |
| `action_params` | Strukturierte Workflowparameter; Konflikte, unlesbares JSON oder abweichende konkrete Parameter sperren |
| `overview_context` | Ausschließlich erlaubte Queryfelder der bestehenden Übersicht; keine frei übergebene Rücksprungadresse |

Die erlaubten Übersichtsparameter sind `offset`, `underlying_id`, `status`, `quality_status`, `analysis_time_from`, `analysis_time_to`, `sort_by` und `sort_direction`. Der Rückweg wird intern als `/market-analyses?...`, `/market-analyses/:id?version=…` oder `/candidates?candidate=…&evaluation=…` aufgebaut. Freie externe Return-URLs werden nicht verarbeitet.

Beispiele für die Form der Links; `A`, `U`, `L`, `I`, `C` und `E` stehen hier nur für vorhandene Identitäten:

```text
/market-analyses/setup?underlying_id=U&listing_id=L
/market-analyses/setup?analysis_id=A&source_version=2
/market-analyses/setup?analysis_id=A&market_data_instrument_id=I&source_version=2
/market-analyses/A?version=2&candidate_id=C&evaluation_id=E
```

Auf der Detailseite sperren eine explizit leere, negative, nichtganzzahlige, mehrfach angegebene oder nicht vorhandene `version` sowie widersprüchliche Quell-/Analyseidentitäten. Es erfolgt kein stiller Rückfall auf die neueste Version. Nur ein erster Besuch **ohne** Versionsparameter darf die numerisch höchste vorhandene Version wählen; diese Auswahl wird sofort mit `replace` in der URL festgehalten. Der Versionswähler ändert die URL. Querywechsel und Browser-Zurück/Vor lesen dadurch genau die gewählte Version.

Die Übersicht verlinkt die tatsächlich angezeigte `latest_version`. Candidate-Quellen vom Backendtyp `ANALYSIS` verlinken ihre tatsächlich gespeicherte Version. Ein neuerer Run ändert keine bestehende historische Candidate-Evaluation und keine bereits gepinnte Detailauswahl.

## Candidate-Reparatur und Listingzugehörigkeit

Der Legacy-Einstieg liest den aktuellen Candidate-Workflow vor der Weiterleitung. Der kanonische Editor prüft den Kontext selbst erneut und liest ihn unmittelbar vor einem Write frisch.

Der Abgleich prüft alle passenden **blockierten** Schritte, nicht nur `next_action`. Aktion, gegebenenfalls `step_code`, Ressourcen-ID und die übergebenen Parameter müssen zum konkreten Schritt passen. Mehrdeutige passende Schritte werden gesperrt; es wird nicht der erste Treffer verwendet. Ein inzwischen erledigter oder geänderter Schritt erfordert die Rückkehr zum Candidate und eine erneute Entscheidung.

Ein Markt-/Sektor-Listing darf einen anderen Basiswert besitzen als der analysierte Candidate. Der tatsächliche Owner wird aus Workflowparametern, Analyseidentität und Stammdaten geprüft. Explizite nichtprimäre Listings bleiben erhalten. Nur ohne explizite Listingwahl kann ein eindeutig vorhandenes aktives Primary Listing vorausgewählt werden. Ein unvollständiger oder widersprüchlicher Owner-/Listingkontext blockiert die Anlage.

Ein alleiniger Listing-Link ohne bekannten Owner und ohne bestehende Analyse wird nicht durch eine erratene Zugehörigkeit repariert: Der vorhandene API-Vertrag bietet dafür keinen allgemeinen direkten Listing-GET. In diesem Fall verlangt die Oberfläche einen vollständigen vorhandenen Kontext.

Nach bestätigter Ausführung wird aktuelle Readiness gelesen. Die Readback-Option darf einen inzwischen abgeschlossenen Schritt lesen; sie ist keine Freigabe, einen nicht mehr blockierten Reparaturschritt erneut zu schreiben. Evaluation, Modellaktivierung, Mappingpflege und Providerimport bleiben getrennte Verantwortlichkeiten und werden nicht automatisch ausgelöst.

## Anlage und Ausführung bleiben getrennte Befehle

| Vorgang | Bestehender API-Vertrag | Bindung |
|---|---|---|
| Analyse anlegen | `POST /api/v1/market-analyses` | Genau `underlying_id` und `listing_id` |
| Listingbasierte neue Version | `POST /api/v1/market-analyses/{analysis_id}/runs` | Bestätigte Analyse, Zeitraum und vollständige Parameter |
| Neue Version einer bestehenden direkten Referenzanalyse | `POST /api/v1/top-down-reference-data/market-reference-analyses/{analysis_id}/runs` | Bestehende listingfreie Analyse und ihr echtes Dateninstrument |
| Retry | `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/retry` | Gespeicherte Quellversion, optionaler Grund; keine Parameter-/Modellüberschreibung |
| Supersede | `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/supersede` | Quellversion, ausdrücklich gewählte neuere Ersatzversion und optionaler Grund |
| Verify | `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/verify` | Exakte gespeicherte Version; gesonderter ausdrücklicher Prüfauftrag |

Create wird anhand der tatsächlich zurückgegebenen Analyse-ID und der angeforderten Zugehörigkeiten geprüft. Die bestätigte ID wird in die kanonische Setup-URL übernommen, bevor ein Run vorbereitet wird. Es gibt nach Create keinen automatischen Run. Schlägt das Nachlesen fehl, bleibt die bestätigte Identität bestehen; „Nur Lesestand erneut laden“ sendet keinen weiteren Create. Ein späterer spezifischer Runfehler erzeugt ebenfalls keine zweite Analyse.

`RunSummaryResponse` enthält **keine** `analysis_id`. Die Oberfläche erfindet daher kein solches Receiptfeld. Sie prüft die tatsächlichen Runfelder und bindet die Antwort an den gesendeten Endpunkt. Anschließend liest sie genau die bestätigte Version per `getRun(analysis_id, version)` und gleicht Analysezugehörigkeit, Runfelder und gespeicherte Parameter ab. Ein zufällig passender „latest run“ ersetzt diesen Nachweis nicht.

Eine direkte Referenzanalyse bleibt listingfrei. Dieser Editor erweitert die Anlageverträge nicht und erzeugt keine künstlichen Index-Basiswerte oder Listings. Neue Runs vorhandener direkter Analysen verwenden den bestehenden D01-F-Owner.

## Historische Parameter, neuer Zeitraum und Modellgrenze

Im gemeinsamen Editor sind sämtliche elf Felder des vorhandenen Parametervertrags sichtbar:

- `price_field`;
- `short_window`, `medium_window`, `long_window`;
- `momentum_windows`;
- `volatility_window`, `range_window`;
- `minimum_required_observations`, `maximum_data_age_days`;
- `annualization_factor` und `rounding_scale`.

Raw-Eingaben bleiben für Korrekturen erhalten. Die Validierung orientiert sich am vorhandenen Vertrag: gültige Datumsgrenzen, aufsteigende Fenster, unterstütztes Kursfeld, Ganzzahlen und erlaubte Dezimalstellen. Die zulässige leere Momentumliste wird nicht künstlich verboten. Der Annualisierungsfaktor bleibt ein Dezimalstring; der Readbackvergleich normalisiert nur die Dezimaldarstellung, ohne den Wert durch JavaScript-Gleitkommarundung zu verändern.

Eine ausdrücklich gewählte historische Version liefert ihre vollständig gespeicherten Parameter. **„Parameter aus Version … vorbereiten“** übernimmt diese Werte erst auf Wunsch und schreibt nichts. Unvollständige oder unbekannt erweiterte Parameterverträge werden nicht still mit heutigen Standardwerten aufgefüllt. Ein offener Entwurf wird vor einer Vorschlagsübernahme geschützt; bereits gewählte neue Datumswerte bleiben Teil dieses Entwurfs.

Der ursprüngliche Anfragezeitraum ist im vorhandenen Run-Detail-DTO nicht enthalten. Deshalb bleiben `Von` und `Bis` bei einem historischen Einstieg zunächst leer. Weder das Analysezeitdatum noch das erste/letzte Snapshotdatum werden als ursprünglicher Anfragezeitraum ausgegeben. Der Benutzer wählt den Zeitraum des neuen Runs ausdrücklich.

Ohne historische Quelle bleiben die bisherigen unterschiedlichen Zeitraumsvorschläge sichtbar: **365 Tage** beim normalen Einstieg und **400 Tage** im Candidate-Reparaturkontext, jeweils bis zum UTC-Tagesdatum. Diese Werte sind Vorschläge und werden vor einem Run gesondert bestätigt.

Neue Runs behalten die bestehende explizite Frontendauswahl **`EOD_TREND_MOMENTUM / 1.0.1`**. Eine historische Parameterübernahme ändert diese Modellauswahl nicht. Sie bereitet einen neuen Run mit aktuellen gespeicherten Marktdaten im neu gewählten Zeitraum vor. Retry und Verify verwenden dagegen weiterhin exakt Snapshot, Parameter sowie Modell-ID/-Version ihrer gespeicherten Quellversion. Keine Modellregistrierung, Governance-Aktivierung, Finanzberechnung oder neue Auswahlregel wird eingeführt.

## Historische Detailansicht und Lifecycle-Schutz

Die Detailseite prüft die gelesene Analyse-ID, Listing-/Instrumentzugehörigkeit und die exakte Runversion gegen den zugehörigen Historyeintrag. Ergebnisse, Kriterien, Hinweise, gespeichertes Modell, Eingabe-Hash, Parameter und Datenquellen gehören zu einer einzigen gewählten Version. Die Versionshistorie bleibt kompakte Navigation; sie stellt keine zweite vollständige Ergebnisversion dar.

Snapshotseiten werden nur auf ausdrückliches Anzeigen gelesen. Offset, Limit und Antwortform werden geprüft. Ein verspäteter Snapshotabruf einer vorherigen Version wird nicht in den neuen Kontext übernommen.

Retry ist nur für `FAILED` beziehungsweise `NOT_EVALUABLE` ohne vorhandenes Supersede-Ereignis verfügbar. Supersede verlangt eine ausdrücklich ausgewählte neuere zulässige Ersatzversion. Die Quellversion bleibt unverändert; das append-only Lifecycle-Ereignis dokumentiert die Ersetzung. Ein bestätigter Retry bleibt über einen Link auf seine genaue neue Version erreichbar, während die ursprüngliche historische Auswahl sichtbar gepinnt bleibt.

Die optionalen Begründungs-/Ersatzentwürfe besitzen einen synchron geprüften Dirtyzustand. Wechsel der Version, Querynavigation, Browser-Zurück/Vor, Verlassen der Seite, lokale Aktionswechsel und Abbrechen verlangen bei offenen Eingaben eine bewusste Entscheidung. Während einer laufenden Aktion sind zweiter Submit, Kontextverwerfung und Wechsel in einen anderen Editor gesperrt. Verify läuft über denselben synchronen Aktionslock, jedoch als eigener ausdrücklicher Befehl ohne neues Runformular.

## Entwürfe, Nebenläufigkeit und Fehlerbehandlung

Je schreibender Seite wird der vorhandene `PendingNavigationGuard` mit unveränderter API verwendet. Eine lokale Verwerfungsentscheidung ergänzt den Routenschutz. Dialogfokus geht zunächst auf „Hier bleiben“; Escape erhält den Entwurf. Der aktive Editor beziehungsweise bestätigte Abschluss erhält gezielt den Fokus.

Reads sind an Kontext und Generation gebunden und werden abgebrochen beziehungsweise bei verspäteter Antwort ignoriert. Die A→B→A-Fälle werden ausdrücklich geprüft. Ein Readback desselben Kontexts remountet den Editor nicht und ersetzt keine offenen Eingaben. Änderungen an Ziel, Datenbasis oder Parametern setzen die Bestätigung zurück. Erkannte Änderungen des unmittelbar vor dem Write frisch gelesenen Stands verlangen eine erneute Prüfung.

| Ergebnis | Verhalten |
|---|---|
| Create bestätigt | Exakte Analyse-ID bleibt gebunden; der Run verlangt einen eigenen bestätigten Schritt |
| Run/Lifecycle-Write bestätigt, Readback erfolgreich | Bestätigten Abschluss und genau gelesene Version anzeigen; keine automatische Folgeaktion |
| Write bestätigt, GET danach fehlgeschlagen oder widersprüchlich | Write bleibt abgeschlossen; ausschließlich Lesestand erneut laden |
| Spezifischer API-Konflikt oder Validierungsfehler unterhalb HTTP 500 | Vorhandenen Fehlercode/-text erhalten und Eingaben zur Korrektur bewahren |
| Transportfehler, unbrauchbare Erfolgspayload oder unklarer serverseitiger Abschluss | Ergebnis als unbekannt behandeln, zunächst GETs ausführen und den betroffenen Schreibauftrag nicht automatisch oder blind wiederholen |
| Passender aktueller Stand nach unbekanntem Request | Als aktuellen Lesestand zeigen; er belegt nicht den Abschluss des eigenen Requests |

Nach unklarer Anlage können vorhandene Analysen mit genau demselben Basiswert und Listing lesend angeboten werden. Sie werden nicht automatisch zur vermeintlichen Antwort des eigenen Create erklärt oder anstelle der unbekannten Identität übernommen. Auf der Detailseite bleiben unbekannte Lifecycle-Ergebnisse auch bei einem Versionswechsel A→B→A innerhalb derselben Seiteninstanz erhalten.

Die Vorabreads sind **keine atomare Konkurrenzsperre**. Die bestehenden Analysebefehle besitzen weder einen allgemeinen `expected_version`-/Compare-and-swap-Vertrag noch eine Request-ID mit Replaygarantie. Eine konkurrierende Änderung nach dem Read bleibt möglich. Der Frontendlock schützt die eigene laufende Aktion, nicht andere Tabs oder Prozesse. Ein lokales Receipt ist keine dauerhafte serverseitige Wiederholungsgarantie; ein vollständiger Seitenneustart erweitert den API-Vertrag nicht.

Normales Öffnen, Auswahl, Weiterleitung, Vorschlagsvorbereitung und GETs lösen keine Analyse, Evaluation, Providerabfrage, Importkette oder Modellaktivierung aus. Die Einrichtungssuche verwendet vorhandene lokale Stammdaten. Der Backend-Owner liest für bestätigte neue Runs weiterhin die gespeicherten Marktdaten; Provider-, Refresh- und Schedulerpfade werden nicht umgebaut.

## Abgeschlossene fokussierte lokale Prüfungen

Laufzeit: **Node 22.16.0 / npm 10.9.2**, vorhandene Lockdatei und unveränderte Testkonfiguration. Die folgenden Suites wurden im Entwicklungsstand vollständig mit Exit 0 ausgeführt. Fokussierte Teilmengen werden nicht zusätzlich zu einem späteren Gesamtgate addiert.

| Suite | Tatsächlich abgeschlossenes Ergebnis | Grenze |
|---|---|---|
| `analysisWorkflowContext.test.ts`, `TopDownWorkflowActionPage.test.tsx`, `topDownAdminClient.test.ts` | **87 Tests / 3 Dateien**: 61 Kontext-, 21 Weiterleitungs-/Restaktions- und 5 Clientfälle | Danach nur gezielte Promise-Mock-/Lintanpassung; endgültiger integrierter Stand wird vom Gesamtgate gebunden |
| `AnalysisSetupPage.test.tsx`, `analysisSetupDraft.test.ts` | **37 Tests / 2 Dateien**: 20 UI-/Guardfälle und 17 Parameter-/Receipt-/Decimalfälle | Nach diesem fokussierten Lauf ergänzte Fokus-/Unmount-Generationssicherung wird durch das abschließende Gesamtgate geprüft |
| `MarketAnalysisDetailPage.test.tsx` | **41 Tests / 1 Datei** einschließlich echter Data-Router-Navigation, Lifecycle und Snapshot | Ein sichtbarer React-`act`-Hinweis im kombinierten History-Guardfall; keine Warnungsunterdrückung oder Timeoutänderung |
| Zugeordnete ESLint-/Prettier-Prüfungen | Erfolgreich, ESLint jeweils mit `--max-warnings=0` | Keine Absenkung bestehender Regeln |
| TypeScript nach Detailintegration | `npm run typecheck` mit Exit 0 | Kein Ersatz für die spätere Typprüfung des finalen Gesamtbaums |
| Detail-Diff | `git diff --check` für die zugeordneten Detaildateien mit Exit 0 | Gesamt-Diff-/Treeabgleich wird durch Abschlussnachweis ergänzt |

Fokussierte Testbefehle aus `frontend/`:

```bash
node node_modules/vitest/vitest.mjs run \
  src/features/analysis/services/analysisWorkflowContext.test.ts \
  src/features/administration/pages/TopDownWorkflowActionPage.test.tsx \
  src/features/administration/services/topDownAdminClient.test.ts

./node_modules/.bin/vitest run \
  src/features/analysis/pages/AnalysisSetupPage.test.tsx \
  src/features/analysis/services/analysisSetupDraft.test.ts

npm run test -- src/features/analysis/pages/MarketAnalysisDetailPage.test.tsx
npm run typecheck
```

Die fokussierten UI-Tests verwenden `createMemoryRouter` und `RouterProvider`. Sie prüfen tatsächliche Routensperren, Versionsquerys, Browser-POP, A→B→A, Fremdidentitäten, bekannte nichtprimäre Listings, konkrete nicht-`next_action`-Reparaturschritte, Änderungsschutz, Doppelklick, genaue Befehlsargumente, Create-/Run-Trennung und Unknown-/Readbackgrenzen. Dies sind kontrollierte Frontendtests mit synthetischen API-Antworten; sie werden nicht als PostgreSQL-Schreibnachweis ausgegeben.

Das unveränderte verbindliche Gesamtgate bleibt:

```bash
bash scripts/check-frontend.sh
```

Dieses unveränderte Gesamtgate wurde am 27.10.2026 auf dem integrierten Anwendungsstand einschließlich der fünf Versionswerte für 1.5.24 mit Node **22.16.0** / npm **10.9.2** vollständig ausgeführt und endete mit **Exit 0**: Typprüfung, ESLint ohne Warnungen, Formatprüfung, **1362 Tests in 139 Dateien**, Coverage und Produktionsbuild. Die Coverage betrug **95,57 % Statements/Zeilen, 89,33 % Branches und 89,98 % Funktionen**. Der bestehende Vite-Hinweis auf große Bundles sowie der sichtbare React-`act`-Hinweis wurden nicht unterdrückt. Danach wurden nur dieser Nachweis und die separaten Browsernachweise fertiggestellt; der geprüfte Frontendanwendungscode blieb unverändert.

Tatsächlich geprüfter finaler Commit/Tree, reguläre GitHub-Prüfungen sowie Merge-/Tagbezüge **werden im Abschlussnachweis des PRs ergänzt**. Eine erfolgreiche Mock-Suite oder vorhandene alte Backend-CI ersetzt keinen neuen Ausführungsnachweis. Die isolierten PostgreSQL-/Docker-Workflows können in dieser lokalen Umgebung ohne Docker nicht ausgeführt werden und bleiben bis zum neuen CI-Ergebnis ausdrücklich offen.

## Browserfälle: bereits ausgeführte UI-Prüfung und noch offene Persistenzausführung

`tests/e2e/analysis-workflow-consolidation.spec.ts` enthält **vier Fälle**. In einem gezielten lokalen Browserlauf sind die **drei kontrollierten Fälle mit 3/3 bestanden**. Sie verwenden ausdrücklich synthetische API-Antworten und belegen:

| Kontrollierter Browserfall | Tatsächlich geprüfte Bedienung |
|---|---|
| Bestätigter Run mit anschließendem GET-Fehler | Exakte nichtprimäre Notierung bleibt gebunden; Doppelklick erzeugt einen Run-POST; Erfolg bleibt trotz Readbackfehler sichtbar; erneutes Laden sendet nur GETs; Ergebnislink führt zu genau der bestätigten Version |
| Unbekannter Create-Abschluss | Ein abgebrochener Antworttransport sperrt Wiederholung; passende aktuell gelesene Analysen werden nur als lesbare Treffer angeboten, ohne automatische Übernahme einer vermeintlichen Create-Antwort |
| Historische Quelle und geschützter Entwurf | Version 1 bleibt trotz vorhandener Version 2 ausgewählt; der gemeinsame Editor erhält `source_version=1`, Candidate-/Evaluationsrückweg und zunächst leere historische Datumsfelder; Vorbereitung, Escape und Routenguard bewahren die eingegebenen neuen Daten ohne Write |

Die kontrollierten Fälle prüfen außerdem Fokus, Tastaturbedienung und eine **390 × 844 Pixel** breite Ansicht ohne horizontalen Dokumentüberlauf. Ihre gezielten Screenshot-Anhänge unterstützen die visuelle Prüfung. Diese drei erfolgreichen Browserfälle sind keine PostgreSQL-Schreibnachweise. Die konkrete finale Commit-/Tree-/Laufbindung **wird durch Abschlussnachweis ergänzt**.

Der vierte Fall ist als **echter Browser→API→PostgreSQL-Weg implementiert, aber zu diesem Dokumentationsstand noch nicht ausgeführt**. Seine tatsächliche Ausführung folgt in der regulären CI; bis zu deren Ergebnis bleibt sie offen. Er verwendet keine API-Interception und ausschließlich ein neu angelegtes synthetisches Listing ohne Kurshistorie. Der vorgesehene Nachweis ist eng:

1. Aus dem bestehenden Basiswert-/Listingkontext öffnet der Browser den gemeinsamen Editor und bestätigt die Analyseanlage. Ein Doppelklick darf genau einen Create-POST erzeugen.
2. Die bestätigte Analyse-ID wird sofort in der URL gebunden; die Anlage startet keinen Run.
3. Zwei separat bestätigte Runanfragen gehen an genau diese ID. Die echte API weist sie wegen absichtlich fehlender gespeicherter Historie jeweils mit **422** ab; vor dem zweiten Auftrag wird der Zeitraum ausdrücklich geändert und neu bestätigt.
4. Der anschließende maßgebliche Detail-/Übersichtsread muss genau eine gespeicherte Analyse mit dieser ID und `runs: []` zeigen. Die Fehler dürfen keine weitere Analyseanlage auslösen. Die Rückkehr führt zur gebundenen bestehenden Analyse.

Dieser native Fall prüft die dauerhaft bestätigte Create-Identität und die Grenze zwischen Anlage und expliziten fehlgeschlagenen Runanfragen. Er behauptet **keinen erfolgreich berechneten Run und keinen neu persistierten erfolgreichen Snapshot**. Es gibt keinen neuen Produktions-Leseendpunkt und keinen zusätzlichen direkten SQL-Reader. Aktiviert wird der Fall nur mit der bestehenden synthetischen Smoke-Schreibfreigabe `TRADE_E2E_WRITES_ALLOWED=1` oder der ausdrücklich lokalen Testfreigabe `ANALYSIS_WORKFLOW_E2E_WRITES_ALLOWED=1`; die bestehenden Runner- und CI-Schutzregeln werden nicht verändert.

## Dateizuständigkeit, Integration und offene Verträge

Der Anwendungsschnitt liegt in `frontend/src/features/analysis/**`. Dazu kommen ausschließlich die neue Route, die Weiterleitung der verbleibenden Top-down-Analyseaktion, die Entfernung ihres zweiten Clientpfads sowie die notwendigen exakten Analysequellenlinks in `CandidatePage`. Die vorhandenen Übersichtsfunktionen für Filter, gespeicherte Ansichten und Export bleiben erhalten.

`PRODUCT_BACKLOG.md`, `TRACEABILITY.md` und historische Qualifikationsberichte werden durch diesen Implementierungsbericht nicht umgeschrieben. UI3-/UI4-Learning-/Trade-/Alertdateien bleiben außerhalb des Schnitts. Die UI5-Referenzdateneditoren sowie ihr global unveränderter Guard behalten ihren bisherigen Owner. Gemeinsame Integrationsstellen sind Router, Candidate-Quellenlinks und Top-down-Weiterleitung; parallele Änderungen dort sind vor Integration abzugleichen.

### Abgleich paralleler Arbeiten am 27.10.2026

Der frisch geprüfte Diff von [PR #290 – Performance Workspace](https://github.com/burckhju/trading-workspace/pull/290) berührt ebenfalls **`frontend/src/app/router.tsx`**. In UI7 besteht der dortige Anwendungsdiff ausschließlich aus dem Import von `AnalysisSetupPage` und der Route `/market-analyses/setup`. Dies ist die einzige gemeinsame Anwendungsdatei im abgeglichenen UI7-/Performance-Schnitt; weitere Anwendungspfade überschneiden sich bei diesem Vergleich nicht. Bei Integration müssen die unabhängigen Routen-/Importergänzungen beider Arbeiten erhalten bleiben.

[PR #289 – Journal](https://github.com/burckhju/trading-workspace/pull/289) bleibt ein separater Umfang und wird nicht durch diesen Analyseauftrag übernommen. Seine Journalimplementierung und Abnahme werden nicht aus den UI7-Nachweisen abgeleitet. Der abschließende Abgleich vor Merge muss den dann aktuellen Main und die tatsächlichen PR-Heads erneut prüfen; der frühere Dateivergleich ersetzt keinen Test eines künftig kombinierten Release-Trees. Gemeinsame Versions-/Releasefortschreibungen sind zusätzlich zur genannten Anwendungsdatei am tatsächlichen Integrationsstand abzustimmen.

Separate Backendverträge bleiben erforderlich, falls künftig ein ursprüngliches Run-Anfrageintervall öffentlich gelesen, ein Befehl per Request-ID zuverlässig wiederholt oder eine Mutation atomar an eine erwartete Version gebunden werden soll. Dieser Schnitt simuliert keinen solchen Vertrag. Backend-Domain, DTOs, Persistenz, Migrationen, Scheduler-/Refreshpfade, Modellgovernance und Finanzberechnungen werden nicht geändert. Der vorbereitete Versionszusatz **1.5.24** ist oben getrennt ausgewiesen; Release-Notiz, finaler Release-Stand und dessen neue Prüfungen werden im Abschlussnachweis gebunden.

Maßgebliche bestehende Verträge:

- [ADR-S4-005: Market-Analysis-Lifecycle](../decisions/ADR-S4-005-MARKET-ANALYSIS-LIFECYCLE.md)
- [D01-F: Referenzanalyse und Readiness](D01F_REFERENCE_ANALYSIS_READINESS.md)
- [FT-006: Marktanalyse](../features/FT-006_MARKET_ANALYSIS.md)
- [FT-006: Modellprovenienz](../features/FT-006_GOVERNED_MODEL_PROVENANCE.md)
- [UI5: Referenzdaten- und Mapping-Eingaben](UI_REFERENCE_DATA_CONSOLIDATION.md)
