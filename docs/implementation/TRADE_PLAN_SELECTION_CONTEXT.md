# FT-007 / FT-008: gebundener Kontext, Planansicht und Approved-Amendment

Auftrag und begrenzte UI-Freigabe: **25.10.2026**.
Ursprüngliche Ausgangsbasis: Main `6c98f7357066c6db5a364370d6dbde637902c4df`,
VERSION `1.5.19`. Während der Arbeit wurde PR #282 regulär in Main integriert.
Die abschließende Basis dieses UI-Diffs ist deshalb Main
`17d5891e0ff6e89ced73d587addb28589f5a292f`, VERSION **1.5.20**. Der Branch wurde
konfliktfrei darauf aktualisiert; dieser Auftrag ändert die Version nicht.
Der Auftrag umfasst Implementierung, Tests, Dokumentation, Commit und Draft-PR.
Version, Merge, Release und Deployment gehören nicht dazu.

## Bestehende fachliche Grundlage

Maßgeblich bleiben [FT-007](../features/FT-007_TRADEPLAN.md),
[Identität und Versionierung](../decisions/ADR-S6-001-TRADEPLAN-IDENTITY-AND-VERSIONING.md),
[Candidate-Ursprung](../decisions/ADR-S6-002-TRADEPLAN-ORIGIN-AND-CANDIDATE-EVALUATION-HANDOFF.md),
[Lifecycle](../decisions/ADR-S6-003-TRADEPLAN-LIFECYCLE-AND-APPROVAL.md),
[Approved-Amendment](../decisions/ADR-S6-004-AMENDMENT-AFTER-APPROVAL.md),
[historische Produktreferenzen](../decisions/ADR-S8-002-HISTORICAL-PRODUCT-REFERENCE.md)
und [FT-008-Handoff](../decisions/ADR-S8-004-TRADEPLAN-HANDOFF.md).
Diese UI-Arbeit führt weder Handelsregeln noch neue Schreibverträge ein.

## Benutzerablauf und unveränderliche Bindungen

Der manuelle Einstieg sucht den Basiswert einmal über seine fachlichen Kennungen.
Ein Candidate-Einstieg lädt die konkrete übergebene CandidateEvaluation innerhalb
des bezeichneten Kandidaten. Ein neuerer Bewertungsstand ersetzt diese Auswahl
nicht. Unvollständige oder widersprüchliche Parameter blockieren die Anlage mit
sichtbarer Erklärung. Ein Ursprungswechsel ist eine bewusste Auswahlaktion und
berücksichtigt ungespeicherte Eingaben.

Das gebundene Formular zeigt Basiswert, Ursprung und den erforderlichen
Versionsbezug lesbar. Technische Identitäten bleiben intern beziehungsweise in
aufklappbaren Herkunftsdetails. Nach bestätigter Anlage führt es in die zentrale
Planansicht, die auch bestehende Planlinks verwenden.

`/trade-plans?trade_plan_id=…&trade_plan_version_id=…` bindet die genaue Version.
Der Planlink ohne Version bleibt unterstützt. Eine ausdrücklich angeforderte
fehlende Version wird nicht still durch `latest` ersetzt. Inhalt, Herkunft und
Aktionen gelten für denselben ausgewählten Stand. Zusätzliche historische
Versionen sind auswählbar, ohne vollständige Inhaltsblöcke zu wiederholen.

FT-008 lädt Plan und genaue Version gemeinsam; dauerhaft editierbare UUID-Felder
entfallen. Ohne Kontext werden ausdrücklich wählbare APPROVED-Versionen aus der
Versionenliste angeboten. Der Status von `latest_version` allein entscheidet
nicht, ob noch eine zulässige Freigabe existiert. „Anderen Plan auswählen“ führt
bewusst zum Auswahlschritt. Ein gespeicherter `run_id` bleibt an seine ursprüngliche
Planversion gebunden. Lesen oder Navigieren bewertet keine Produkte neu und
erfasst keinen Kauf.

## Vollständiger Approved-Amendment-Vertrag

Der Editor kopiert die ausdrücklich ausgewählte APPROVED-Version und hält Plan-ID
und Basisversions-ID bis zum Abschluss fest. Sein Payload enthält ausschließlich
die vorhandenen Inhaltsfelder und den verpflichtenden Änderungsgrund. Änderungen
werden über den vorhandenen Amendment-Endpunkt gespeichert. Der neue Stand ist
DRAFT und verweist mit `previous_version_id` auf diese genaue Basis.

Das gemeinsame typisierte Formular für Anlage und Amendment erhält:

- PRICE, PRICE_RANGE und TRIGGER mit allen vertraglichen Preisfeldern;
- `currency`, `valid_until`, `entry.rationale` und `reference_price`;
- Preisstop, Invalidierungsregel und ihre Begründung;
- alle Targets mit unveränderter Reihenfolge, Preis und Begründung;
- `thesis_risk`, `max_loss_assumption` und `notes`.

Preise bleiben Strings; die vorhandene Dezimalkomma-Normalisierung bleibt im
Client. Nicht angefasste Inhalte werden weder durch versteckte Defaults noch
durch pauschales Nullsetzen gelöscht. Seltene Felder sind aufklappbar, bleiben
aber Teil des gespeicherten Inhalts. Die Planwährung wird ausdrücklich erfasst;
Produkt-/Ausführungswährung, Kaufdatum, Menge und Kaufpreis werden daraus nicht
abgeleitet.

Ein Amendment allein supersediert die Basis nicht. Neuer DRAFT und bisheriges
APPROVED bleiben unterscheidbar. Die neue Version braucht eine eigene Freigabe;
erst diese löst nach Backendvertrag die frühere Freigabe ab. Historische Runs,
Bewertungen, Entscheidungen, Trades und frühere Planinhalte werden nicht auf die
neue Version umgebogen.

## Eingabe- und Mutationsschutz

Kontextwechsel entwerten verspätete Antworten. Hintergrundreads ersetzen keine
bewussten Formulareingaben und keine ausgewählte Amendment-Basis. Laufende
Schreibaktionen sperren Eingaben und weitere Auslösung synchron. Fehlgeschlagene
Speicherung erhält den Entwurf. Ein bestätigter Save mit gescheitertem anschließendem
Read wird getrennt dargestellt; Schreibrequests werden nicht automatisch wiederholt.
Backendkonflikte bleiben sichtbar und führen nicht zu einem stillen Basiswechsel.

Die vorhandenen Auswahlbestätigungen, NOT_EVALUABLE-Begründungen, Erstkaufstrecke,
OPEN_TRADE_EXISTS-Antworten, Kaufstatus und Löschbestätigungen bleiben erhalten.

## Verbleibende DRAFT-Revisionslücke

Es besteht weiterhin **kein allgemeiner Inhaltsrevisionsvertrag für bereits
gespeicherte DRAFT-Versionen**. Approved-Amendment akzeptiert ausschließlich eine
APPROVED-Basis. Der Folgepunkt benötigt einen eigenen fachlichen/API-Vertrag mit
Versionierung, Concurrency, Audit und Tests. Gespeicherte Stände werden nicht
überschrieben, zur Umgehung freigegeben/gelöscht oder als unabhängige Pläne kopiert.
READY_FOR_REVIEW → DRAFT bleibt eine reine zulässige Statusaktion.

## Integrationspunkte

Die Produktverwaltung unter `frontend/src/features/product/` bleibt eigener
Auftrag. Ihre stabile Reparaturschnittstelle ist
`/warrants-admin?selection_run_id=…&warrant_id=…`; `warrant_id` bleibt nach
bestehendem Vertrag optional. Die Rückkehr lautet `/product-selection?run_id=…`.
Zugehörigkeitsprüfungen und der ursprüngliche Run bleiben erhalten. Reparatur
startet weder Bewertung noch Kauf automatisch.

Beim Live-Abgleich war kein neuer Produktverwaltungs-UI-PR veröffentlicht.
Gemeinsame Repair-Tests und die gezielten PB-014-/PB-015-/Traceability-Nachträge
müssen beim ersten integrierten UI-Branch gegen den tatsächlichen zweiten Diff
abgeglichen werden. Danach ist der andere Branch auf Main zu aktualisieren und
der Reparatur-/Rückkehrweg erneut zu prüfen. Parallele native Tests benötigen
getrennte Datenbanken, Ports und Arbeitsverzeichnisse.

[PR #187](https://github.com/burckhju/trading-workspace/pull/187) war beim Abgleich
offen und Draft, Head `bad00a420f56994216ad1def6a580b00b0f5772f`. Sein konkreter
Wrapper-Diff importiert `HebeltraderPanel`, mountet es für
`!candidateOrigin && selectedUnderlyingId` und setzt nach Anlage `trade_plan_id`.
Diese Einbettung muss bei späterer Integration an den konsolidierten
Erstellungszustand angeschlossen werden. Unintegrierte Handelsregeln werden nicht
übernommen.

[PR #282](https://github.com/burckhju/trading-workspace/pull/282) war im ersten
Abgleich offen und Draft, Head `b72698940501b507c414387bc5860c3a50308910`.
Der abschließende GitHub-Readback bestätigte den Merge mit Commit
`17d5891e0ff6e89ced73d587addb28589f5a292f`. Seine fachlichen Performance-Dateien
überlappen nicht. Sein PB-019-Statistikblock und der additive Statistikabschnitt in
TRACEABILITY sind in der aktualisierten Basis erhalten. Version **1.5.20** stammt
aus diesem Main-Merge. Der folgende Browsernachweis wurde auf dieser Basis erneut
ausgeführt; ältere Läufe auf 1.5.19 bleiben ausdrücklich Vorläufe.

## Qualifikationsumfang und Ergebniszuordnung

Die folgenden **abschließenden** Browserläufe prüfen den eingefrorenen UI-Diff auf
Main `17d5891e0ff6e89ced73d587addb28589f5a292f` / **1.5.20** am 25.10.2026.
Die beiden letzten Reviewkorrekturen – erneutes Lesen desselben aktuellen Runs
und sichtbare Fehler im Bestätigungsdialog – sind in diesem Build enthalten.

| Abschließender Nachweis | Ergebnis | Ausführung |
|---|---|---|
| Chromium mit synthetischen API-Fixtures | **17/17 bestanden**, 11,7 s | 2 Worker, 0 Retries, 0 Skips |
| Chromium mit realen APIs und PostgreSQL | **5/5 bestanden**, 17,6 s | 1 Worker, 0 Retries, 0 Skips, keine API-Mocks |
| Gezielte Backend-/Handoff-Regression | **130 bestanden**, 14,33 s | Exit 0; eine bekannte Starlette/AnyIO-DeprecationWarning |
| Vollständiges `scripts/check-frontend.sh` | **904 Tests in 126 Dateien bestanden**, Tests 85,49 s | Exit 0; Typecheck, ESLint, Prettier-Check, Coverage und Build bestanden |

Das vollständige Frontendgate meldet **94,24 % Lines/Statements, 87,25 % Branches
und 87,27 % Functions**. Der reguläre Build umfasst 783 Module und dauerte 3,47 s.
Verbliebene Hinweise sind React-`act`-Warnungen in Learning-/Navigationstests,
die Vite-Chunkgrößenwarnung und npm-`http-proxy`-Konfiguration; es gab keine
unbehandelten Fehler.

Die Ergebnisse werden im Draft-PR am abschließenden Commit gebunden. Frühere
Projekt-CI oder erfolgreiche Test-Collection gelten nicht als Nachweis dieses Diffs.
Gemockte React-Tests, Browser-Fixtures, native Browser-/API-/Datenbankfälle und das
vollständige lokale Frontendgate bleiben getrennte Nachweisarten. Die reguläre CI
wird anhand ihres tatsächlichen Heads zugeordnet; fachliche Benutzerabnahme und
PC-Betrieb werden aus diesen lokalen Ergebnissen nicht abgeleitet.

### Statischer Build und reproduzierbare Testumgebung

Beide finalen Browserbuilds wurden mit Node **22.16.0**, Vite **6.3.5**, Playwright
**1.55.0** und Chromium **140.0.7339.16** erstellt beziehungsweise ausgeführt.
Sie liegen in getrennten transienten Verzeichnissen außerhalb des Repositories;
`frontend/dist` des regulären Gates wird dafür nicht verwendet. Es gibt kein
Hot-Reload während der Prüfung.

| Build | API-Basis im Build | Hauptasset | SHA-256 |
|---|---|---|---|
| Fixtures, UI auf `127.0.0.1:5188` | `http://127.0.0.1:5188/api` | `index-DnZ2CSW0.js` | `4024d346e5ad335340977867f658357af586a9e499a9deac3d17382c1523ad1f` |
| Native, UI auf `127.0.0.1:5189` | `http://127.0.0.1:5189/api` | `index-Dqn72ugO.js` | `c1815cf2b5a67671682e56ae839c3001b4ae259ffe34f4db455b7676ac23432e` |

Die Builds verwenden `VITE_API_BASE_URL` mit der jeweils genannten API-Basis und
`vite build --outDir <getrenntes Testverzeichnis> --emptyOutDir`.
[Das Evidence-Manifest](evidence/trade-plan-selection-context/manifest.json)
enthält zusätzlich SHA-256 aller Buildassets, der ausgeführten Specs und der
kompakten Originalnachweise. Große Bundles und Traces sind nicht Teil des Commits.

Für beide Läufe:

```text
PATH=/workspace/scratch/59da26c5711e/test-tools/node_modules/node/bin:$PATH
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/workspace/scratch/59da26c5711e/browser-shell/chromium_headless_shell-1187/chrome-linux/headless_shell
```

#### Fixture-Browserlauf

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:5188 \
npm run e2e -- --workers=2 --retries=0 --trace=on \
  --output=test-results/plan-context-main1520-final-fixtures \
  ft007-trade-plan.spec.ts ft007-trade-plan-hard-delete.spec.ts \
  ft008-product-selection.spec.ts trade-plan-warrant-identity.spec.ts \
  trade-plan-purchase-status.spec.ts purchase-workspace-handoff.spec.ts
```

Alle fachlichen API-Antworten dieses Laufs stammen aus `page.route`-Fixtures.
Erfolgreich geprüft wurden drei Löschbestätigungsfälle, manuelle Anlage und
Kandidatenpin, PRICE-/PRICE_RANGE-/TRIGGER-Amendment (TRIGGER auf 1280 und 390 px),
vier Produktauswahlfälle, bestehender Kauf-Handoff, Kaufstatus sowie historische
Produktidentität auf beiden Bildschirmbreiten. Die gespeicherte CandidateEvaluation
v7 bleibt trotz einer verfügbaren v8 gebunden. Die Amendment-Assertions vergleichen
den gesamten Payload mit dem Ausgangsinhalt einschließlich hochpräziser Strings.
Die bewusste Neubewertung führt in die kanonische URL des neu bestätigten Runs.
Tastaturbedienung, der mobile Overflow-Check und ausbleibende automatische Writes
sind Bestandteil dieser tatsächlich ausgeführten Browserfälle.

#### Nativer Browser-/API-/PostgreSQL-Lauf

```bash
TRADE_E2E_UI_URL=http://127.0.0.1:5189 \
TRADE_E2E_API_URL=http://127.0.0.1:8187/api/v1 \
TRADE_E2E_WRITES_ALLOWED=1 \
npm run e2e -- --workers=1 --retries=0 --trace=on \
  --output=test-results/plan-context-main1520-final-native \
  ft007-plan-context-postgres.spec.ts \
  product-selection-confirmation-capture.spec.ts \
  warrant-listing-without-symbol.spec.ts
```

Die native Prüfung verwendet ausschließlich die eigens angelegte, wegwerfbare
Datenbank `trade_plan_context_ui`. Ein SQL-Readback bestätigte PostgreSQL **16.2**
und den vollständig migrierten Repositorystand **20261017_0047**. Vor dem ersten
nativen Vorlauf war die Planliste leer; die späteren Läufe ergänzten ausschließlich
weitere eindeutig benannte synthetische Datensätze in dieser eigenen Testdatenbank.
PostgreSQL stammt aus `pgserver 0.1.4` in einem isolierten Workspace-Verzeichnis;
keine Hostinstallation oder bestehende Nutzerdatenbank wurde verwendet. Die
reguläre Projektumgebung verwendet PostgreSQL 17; dieser lokale Nachweis ersetzt
deren CI-Gate nicht.

Das unveränderte Backend lief unter Python **3.12.14** auf Loopback `8187` und
wurde nach der Main-Aktualisierung neu gestartet. Refresh, Monitoring und Telegram
waren mit den bestehenden Konfigurationsvariablen deaktiviert:

```text
TRADING_WORKSPACE_ENVIRONMENT=test
TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://trade_plan_test@127.0.0.1:55487/trade_plan_context_ui
TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED=false
TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=false
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false
```

Der eigene statische UI-Server auf `5189` leitet `/api/...` nach Entfernen des
ersten `/api` an Backend `8187` weiter. Proxy und Serverkonfiguration liegen nur
in der transienten Testumgebung. Kein Produkt-/Backend-/Schema- oder
Repository-Deploymentvertrag wurde dafür geändert. Es liefen keine parallelen
Datenbanktests.

| Nativer Fall | Abschließendes Ergebnis |
|---|---|
| Vollständiger TRIGGER-Amendment-/Approval-/Historienfall | Bestanden, 4,7 s |
| Bestehende NOT_EVALUABLE-Bestätigung → genau ein persistierter BUY | Bestanden, 3,4 s |
| Gezielte Listingreparatur → unveränderter alter Run → explizite Neubewertung → bestehender BUY | Bestanden, 2,0 s |
| Produkt mit expliziter Notierung anlegen und nach Reload wiederverwenden, 1440 px | Bestanden, 2,3 s |
| Derselbe bestehende Reparatur-/Anlagefall, 390 px | Bestanden, 2,2 s |

Der TRIGGER-Fall verwendet eine USD-Planwährung bei separat bestätigter
EUR-Ausführung. Ausschließlich die These und der Änderungsgrund werden neu
formuliert. Der einzige Amendment-Request referenziert die ausgewählte V1 und
enthält unverändert Referenzpreis, `valid_until`, Entry-/Invalidierungsbegründung,
drei begründete Targets und sämtliche Risikoangaben. V2 ist zunächst DRAFT und
V1 bleibt APPROVED sowie im Picker wählbar. Die spätere separate Einreichung und
Freigabe erzeugen genau zwei weitere Browser-Schreibbefehle. Danach ist V1
SUPERSEDED; ihr ursprünglicher Inhalt und Approval-Nachweis sind unverändert.
Die vollständigen Run-, Trade- und Timeline-Readbacks vor/nach dieser Freigabe sind
jeweils gleich. Das anschließende Öffnen des historischen Runs erzeugt keinen
Schreibbefehl und erlaubt keine neue Bewertung dieser alten Version.

Das bestehende Backend speichert Planpreise als **`Numeric(24, 10)`**. Der native
Fall vergleicht deshalb den tatsächlich gespeicherten Quellstand mit dem Amendment;
er behauptet keine zusätzliche Datenbankpräzision. Die getrennten UI-Fixtures
belegen die verlustfreie Weitergabe längerer Decimalstrings durch das Frontend.

Die drei nativen Specs behalten den ausdrücklichen `TRADE_E2E_WRITES_ALLOWED`-Guard.
`TRADE_E2E_UI_URL` und `TRADE_E2E_API_URL` sind optionale isolierte Testendpoints;
ihre bisherigen Defaults `http://localhost:8080` beziehungsweise
`http://127.0.0.1:8000/api/v1` bleiben erhalten. Das eigene UI-Env erhält den
bisherigen nativen CI-Origin: `.github/workflows/e2e.yml` setzt
`VITE_API_BASE_URL=http://localhost:8080/api`, während das allgemeine
`PLAYWRIGHT_BASE_URL` auf `http://127.0.0.1:8080` zeigt. Die nativen Specs öffnen
standardmäßig weiterhin `localhost` und vermeiden damit eine neue CORS-Grenze.
Der unveränderte Workflow setzt bereits `TRADE_E2E_WRITES_ALLOWED=1`; der neue
Fall wird dort mit ausgeführt. Nur Aufrufe ohne den ausdrücklichen Guard
überspringen die nativen Fälle. Eine Collection oder ein Skip ist kein nativer
CI-Nachweis.

### Kompakte Reviewnachweise im Repository

Diese Dateien stammen unverändert aus den Attachments des **finalen** nativen
5/5-Laufs. Beide Screenshots wurden tatsächlich gesichtet; der 390-px-Editor zeigt
alle optionalen Angaben und drei Targets ohne horizontalen Overflow. Der
1280-px-Stand zeigt den historischen Run an seiner ursprünglichen SUPERSEDED-V1.
Die JSON-Readbacks wurden nach dem Extrahieren zusätzlich auf vollständige
Gleichheit der historischen Antworten und den exakten Amendment-Inhalt geprüft.
Alle enthaltenen Personen-/Depotbezüge, UUIDs und Stammdaten sind synthetisch.

- [Vollständiger TRIGGER-Editor, 390 px](evidence/trade-plan-selection-context/native-trigger-390.png)
- [Historischer Run nach separater Freigabe, 1280 px](evidence/trade-plan-selection-context/native-historical-run-1280.png)
- [Exakte Versionen, Amendment-Payload und historische Readbacks](evidence/trade-plan-selection-context/native-context-readbacks.json)
- [Manifest mit Quelle, Umgebung, Präzisionsgrenze und Prüfsummen](evidence/trade-plan-selection-context/manifest.json)

Der SHA-256 des finalen JSON-Readbacks ist
`e7cd79f37f1f40ba29b4cd56eb54f7f13a377af0b2f9724060da28420a77ef0e`.
Die lokalen vollständigen Traces bleiben unter den oben genannten Testoutputs.

### Historische Vorläufe und behobene Testprobleme

Diese älteren Läufe auf Main 1.5.19 sind **keine finale Qualifikation**:

- Der erste Fixture-Lauf bestand 13/17 Fälle. Vier Amendment-Fälle warteten auf
  einen zu engen Label-Locator des Versionsselects; der eindeutige Combobox-Locator
  behob das Problem ohne Änderung fachlicher Assertions. Ein weiterer Lauf bestand
  15/17 und wurde in zwei offenen Editoren durch paralleles Vite-Hot-Reload mit
  vollständigem Reload unterbrochen. Die Traces belegen HMR und `beforeunload`.
  Der daraufhin eingefrorene Build bestand 17/17 in 7,9 s (damals Node 24.22.1).
- Ein späterer statischer Fixture-Vorlauf mit den kanonischen Run-URL-Assertions
  bestand 17/17 in 10,6 s unter Node 22. Durch den zwischenzeitlichen Main-Merge
  blieb auch er Vorlauf (`plan-context-final-fixtures`).
- Der erste native Aufruf bestand vier bestehende Fälle, scheiterte aber im neuen
  TRIGGER-Fall vor der Mutation an einem zu engen Label-Locator des vorbefüllten
  Textfelds. Der gesamte 4/5-Lauf blieb fehlgeschlagen (15,5 s). Nach Wechsel auf
  die eindeutige Textbox-Rolle und explizitem Sollinhalt aus dem gespeicherten
  versionsgenauen GET bestand der neue Fall einzeln 1/1 in 3,3 s. Die damaligen
  Outputs heißen `plan-context-native` und `plan-context-native-amendment-corrected`.
  Diese frühen Aufrufe adressierten ihre isolierte UI noch über
  `PLAYWRIGHT_BASE_URL`; der finale Lauf verwendet `TRADE_E2E_UI_URL` wie oben.

Keine fachliche Assertion wurde für diese Korrekturen entfernt, kein Timeout
angehoben, kein Retry oder Skip ergänzt. Der finale gemeinsame 17/17- und 5/5-Lauf
ersetzt die Vorläufe für die Qualifikation dieses Diffs.
