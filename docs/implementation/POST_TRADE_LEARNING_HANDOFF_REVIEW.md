# Startprompt 07 — begrenzter Handoff-Patch und offene Lernabschlussstrecke

## Technische Fortschreibung — 14.10.2026

Der begrenzte Review-Pin-/Readback-Schnitt ist im vollständigen Repository
auf `dev/post-trade-handoff-qualification-20261014` integriert:
[Draft-PR #259](https://github.com/burckhju/trading-workspace/pull/259).
Der Journal-/Lern-Gesamtabschluss bleibt offen. Nur das zentrale Backlog
führt Arbeitsstatus; technische Prüfung ist keine Fach-/Betriebsabnahme.

### Identifizierte Prüfstände

Basis: `2ac107d04f9b2f6b2636009da6ad16af59550df5` (v1.5.6).
Implementierung: `b40c5cc120512a3f8b5c5af36bcaf06691f920ed`, vollständiger
Tree `25f7269dc471e9f512887a22221fc89418f7995a`.
Der Zusatzworkflow auf `8f2a423107c91b286d1c261d38a7e4b3f209b578` testet
den gepinnten b40-Anwendungscode. Reguläre PR-Läufe auf 8f testen
`173c952f71c3d51936a988ecd86332102e8cb170`, GitHubs synthetischen Testmerge
mit main, keinen tatsächlich vollzogenen Merge. Spätere Heads separat prüfen.

### Technische Belege

| Prüfung | Stand / Lauf | Ergebnis |
|---|---|---|
| Unverändertes `bash scripts/check-backend.sh` | b40; [38613983711](https://github.com/burckhju/trading-workspace/actions/runs/38613983711) | Ruff, Black (912 Dateien), mypy (523 Quelldateien), 2600 Tests bestanden; Coverage 86,15 % bei unveränderter 85-%-Schwelle |
| Unabhängige PostgreSQL-Transaktionen | b40; gleicher Lauf, `test_ft011_materialization_command_postgres.py` | Drei Fälle bestanden: gleiche/verschiedene Keys, Rollback ohne orphan Evidence, Retry, falsche/veraltete/ersetzte Quelle |
| Migrationen | b40; `alembic heads`, `upgrade head`, `current` | Ein Head `20261012_0045`; lokaler Graphabgleich: 45 Revisionen, keine fehlenden Eltern; keine neue Migration |
| Reguläre Frontend-CI | 8f-Testmerge; [38613992924](https://github.com/burckhju/trading-workspace/actions/runs/38613992924) | TypeScript, ESLint, Prettier, 456 Tests in 99 Dateien, Coverage-Gates und Build bestanden; Lines/Statements 92,21 %, Branches 83,39 %, Functions 84,42 % |
| Reguläre End-to-End-CI | 8f-Testmerge; [38613992910](https://github.com/burckhju/trading-workspace/actions/runs/38613992910) | Docker-Build, Migration und 51 Browserfälle bestanden; 0 fehlgeschlagen/flaky/skipped |
| Neue Handoff-Browserfälle | Drei der 51; zusätzlich separat gegen b40 im Zusatzlauf | Explizite Reviewfinalisierung, gepinnte Materialisierung, ausdrückliche Interpretation; Versionswechsel ohne automatischen Retry; historischer Replay ohne CURRENT-Fiktion |

Die drei PostgreSQL-Fälle sind Teil der 2600, nicht zusätzliche 2603
unterschiedliche Tests. Die drei neuen Browserfälle sind Teil der 51.
Die neuen Browserfälle fangen synthetische HTTP-Antworten ab: kein
Browser-zu-Datenbank-Beweis der vollständigen Nutzerreise. Die PostgreSQL-
Fixture beginnt mit einem qualifizierten Reviewgraphen, nicht mit einem
durch reale Capture-Commands erzeugten synthetischen BUY/SELL-Voll-Exit.

Die zehn vorab festgelegten DoR-Kriterien besitzen jetzt abgegrenzte
Application-/API-/React- sowie PostgreSQL-/Browserbelege. Pin und semantische
Eindeutigkeit sind geprüft; FT-011 bleibt der einzige Readiness-Owner.
Keine Aussage über atomare Serialisierung gegen eine Upstream-Korrektur
nach dem Handoff-Read oder über unveränderte historische Lesson-Versionen
über die gesamte Execution-/Journal-Korrekturkette.

### Umgebungs-, Fehler- und Betriebsgrenzen

Frische GitHub-Runner, synthetische UUIDs und PostgreSQL 17 auf
`localhost:5432/trading_workspace_test`; Ziel und Alembic-Head werden geprüft.
Keine private .env/Nutzer-Volumes. Provider, Scheduler und Telegram im
Zusatzlauf ausgeschaltet. Reguläre E2E-CI nutzt ihren eigenen Wegwerf-
Compose-Stack mit bestehenden synthetischen Schreibfreigaben, nicht JMBbot.
Python 3.12.15 und Frontend Node/npm 22.16.0/10.9.2. Eine AnyIO-
BlockingPortal-DeprecationWarning und die bestehende Vite-Warnung zu Chunks
über 500 kB bleiben sichtbar; kein warnungsfreier Lauf behauptet.

Vollständiger credential-freier Quell-/Dependency-Export aus Zusatzlauf
38613983711: Archivprüfsummen und b40-HEAD/Tree lokal abgeglichen, eigener
Aufgabenbranch. Das ist jetzt ein vollständiger Quellbaum, aber nur shallow
Git-Historie. Keine AGENTS.md im vollständigen verfolgten Baum gefunden.

Der erste isolierte Browserlauf blieb durch `VITE_API_BASE_URL=/api` vor
jedem API-Aufruf leer: Die bestehende Anwendung verlangt eine absolute
HTTP(S)-URL. Ausschließlich Prüfaufbau korrigiert; Anwendung und Assertions
unverändert. Danach alle drei Browserfälle grün. Die jobweite Browser-URL
im Zusatzlauf beeinflusste außerdem 18 Unit-Assertions auf die Standard-URL
(438 bestanden/18 fehlgeschlagen); dieser Frontend-Teil ist NICHT grün.
Die oben genannte reguläre Frontend-CI lief mit Standardumgebung erfolgreich.
Ein lokaler vollständiger Skriptversuch endete nach Typecheck während
ESLint am Werkzeug-Zeitlimit und zählt nicht als bestandener Gesamtgate.

Der frühere npm-ci-/sharp-Fehler war im separaten unveränderten main-
Versuch ([38609444879](https://github.com/burckhju/trading-workspace/actions/runs/38609444879),
`baseline-docker`) nicht reproduzierbar. Auch der neue reguläre E2E-Build
ist grün. Keine Lockdatei, kein Image und keine Schwelle zur Erzwingung von
Grün geändert; kein fortbestehender Lockfiledefekt behauptet.

Ergänzend ist `bash scripts/check-frontend.sh` in Standardumgebung auf b40 im erfolgreichen vorgeschalteten Job von [Run 38616143106](https://github.com/burckhju/trading-workspace/actions/runs/38616143106) vollständig ausgeführt. Die Dokumentationsfortschreibung ändert keinen Anwendungscode.

### Offener fachlicher Schnitt

Der vollständige Checkout bestätigt im FT-012-Owner Journalmodelle,
Mapping und Evidence-Lesetypen, aber keinen Journal-Schreibservice,
entsprechende UOW-Repositories, registrierte Schreibroute oder Editor.
Der untenstehende Journal-Vertragsvorschlag ist keine fachliche Freigabe.
Nächster Schnitt bleibt [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#naechster-schnitt):
Modell zu Commands, Persistenz, API und Entwurfsdialog verbinden;
Abschlussinhalt, exakte Quellenbindung, Konkurrenz und Folgeversion vor
der jeweiligen Änderung festlegen. Keine Performance-Zwangsvoraussetzung.

Ebenfalls offen: historische Evidence-Anzeige bei NOT_READY, atomare
Upstream-Korrekturabsicherung und vollständige Capture→Journal→Lesson-
Korrekturstrecke. Keine neue Migration, Backfill, reale Ausführung,
Nachricht, Modellaktivierung, Merge/Tag/Deployment oder Zielinstallations-
beobachtung. Temporäre Prüfhilfe vor Übergabe aus dem PR entfernen.

---

## Historischer Erstnachweis — vor vollständiger Qualifikation

Die folgenden Nicht-ausgeführt-Aussagen dokumentieren den ursprünglichen
Teilrekonstruktionsstand. Nur die oben belegten Teilprüfungen sind inzwischen
fortgeschrieben; frühere Prüfungen werden nicht rückwirkend als ausgeführt
und der Gesamtprozess nicht als abgeschlossen ausgegeben.

## Einordnung

**Der beauftragte vollständige Abschluss ist nicht geliefert.** Vorbereitet ist ein
lokaler, überprüfbarer Patch für die Bestätigung einer konkreten Review-Version und
den anschließenden UI-Readback. Der Journal-Schreib-/Finalisierungsweg wurde nicht
implementiert. PostgreSQL, Browser-E2E und Zielinstallation wurden nicht ausgeführt.

Dieses Dokument ist eine datierte Nachweisansicht, keine zweite Statusquelle.
Maßgeblich bleiben [PB-018 Review](../planning/PRODUCT_BACKLOG.md#pb-018-review),
[PB-018 Currentness](../planning/PRODUCT_BACKLOG.md#pb-018-currentness),
[PB-019 Materialisierung](../planning/PRODUCT_BACKLOG.md#pb-019-materialization),
[PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal) und
[PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons).
M0–M11, bestehende FT-IDs und Paketownership bleiben unverändert.

## Ausgangspunkt und tatsächlicher Arbeitsstand

Remote-Basis: `burckhju/trading-workspace`, `main`,
`f918194150636f03faab466a6e41a4b67b2841dc`, Version `1.5.5` in beiden Manifesten.
Die Ausgangsreferenz `a78288ad38610656480d0363abe657b567c7ba94` ist der Vorgänger,
nicht der zurückgesetzte Arbeitsstand. Der neue Main-Commit konsolidiert Planung.

Lokal gab es keinen vollständigen Checkout. GitHub war über den lesenden Connector
zugänglich; direkter Git-Zugriff scheiterte an DNS. Docker und PostgreSQL fehlen.
Deshalb wurden ausgewählte Originaldateien rekonstruiert und vor Bearbeitung mit
ihren Git-Blob-Hashes abgeglichen. Der lokale Aufgabenbranch heißt
`task/post-trade-learning-handoff-20261014`. Seine Commits sind ausdrücklich keine
vollständigen Nachkommen des Remote-Commits. Das mitgelieferte `source-blobs.json`
und die Patch-Metadaten dokumentieren die ausgewählte Vergleichsbasis.

Der Arbeitsbaum einer Nutzerinstallation war nicht sichtbar. Es wurden keine
fremden Änderungen überschrieben, keine Remotes beschrieben, kein PR veröffentlicht,
kein Merge/Tag/Deployment und keine Datenbank-/Provider-/Notification-Aktion ausgeführt.
Root-, Backend-, Frontend- und Docs-Bauminventare enthielten keine AGENTS.md;
der vollständige Tests-Unterbaum und alle offenen PRs wurden nicht abschließend
abgeglichen. Das ist vor Integration nachzuholen, kein behaupteter sauberer Checkout.

## Quellen und Konfliktauflösung

Gelesen wurden die relevanten Teile von README, PROJECT, ROADMAP, ARCHITECTURE,
MODEL_BOOK, TRACEABILITY, MODULE_AND_FEATURE_CATALOG, PRODUCT_BACKLOG,
TRADING_PROCESS_MODEL, DEVELOPMENT_GUIDE, FEATURE_LIFECYCLE sowie:

- `SPRINT_11_FT011_SPECIFICATION_BASELINE.md` und ADR-S11-007;
- `POST_D01_GOLDEN_PATH_CLOSEOUT.md` und `POST_D01_GOLDEN_PATH_EXTENSION_09.md`;
- ADR-POST-FT012-004, `EXTERNAL_HISTORICAL_OBSERVATIONS.md`,
  `POST_FT012_EXTERNAL_OBSERVATION_DOR.md` und `trade-capture-safety.md`;
- aktuelle FT-012-Domain-/Persistenzmodelle, UOW/Repository-Ausschnitte,
  Materialisierung, Status, DI, FT-011-Handoff und die konkreten UI-Consumer;
- vorhandene Materialisierungs-, API-, Route-Coverage- und UI-Testquellen.

Nicht abschließend gelesen/ausgeführt: alle FT-011/FT-012-Reviews und
Akzeptanzmatrizen, gesamte Git-Umbenennungshistorie, vollständige Routerkomposition,
Observation-/ExitReview-Korrekturpfade, Lesson-Review-/Currentness-Persistenz,
alle spätere Golden-Path-Nachträge, sämtliche Development-Guide-/Lifecycle-Abschnitte
und das vollständige Migrationen-/offene-PR-Geflecht. Eine vollständige
Bestandsfreigabe wird daher nicht behauptet.

Die alte fehlende FT-011→FT-012-Materialisierung ist durch Extension 09 und
vorhandene API/UI überholt. Das alte Closeout bleibt historisch richtig; es ist
kein Neubauauftrag. ADR-POST-FT012-004 definiert bewusst einen Low-input-Befehl,
der die Version beim Owner auflöst. Der neue Pin ist eine additive
Bestätigungsvorbedingung, nicht die Behauptung, der alte ADR habe bereits einen
Pflicht-Pin verlangt. Sein Accepted-Text bleibt erhalten, die Erweiterung ist
als vorgeschlagener Nachtrag gekennzeichnet.

Dataclasses allein beweisen keinen Journalprozess. Das aktuelle Journalmodell
hat drei optionale Textfelder und erlaubt eine inhaltsleere Finalisierung.
Die gelesene Persistenz besitzt ein Journal pro Trade und höchstens einen DRAFT,
aber keinen Journal-Schreibservice im inventarisierten Application-Paket und
keine Journal-Schreibrepositories in der gelesenen UOW. Der aktuelle Consumer
enthält keinen Journaleditor. Das belegt die Lücke in diesen untersuchten
Schichten, nicht die Abwesenheit beliebiger ununtersuchter Altpfade.

## Getrennte Nachweismatrix

| Teilfähigkeit / maßgeblicher Eintrag | Vorhandener Code und Consumer | Testlage an dieser Basis | Rest und Entscheidung | Betriebsnachweis |
|---|---|---|---|---|
| Nachbeobachtung / PB-018 observation | `post_trade`; FT-011-Spezifikation, Observation-/Evidence-UI in `PostTradeReviewPage.tsx` | Vorhandene UI-Testquelle trennt Actual/Counterfactual und 13/20; nicht ausgeführt | Reale synthetische BUY/SELL-Kette, offene/stornierte Trades, Tages-/Sessiondaten und Vollständigkeit beim Owner nachweisen; kein neues Beobachtungssystem | Nicht ausgeführt |
| Exit Review / PB-018 review/currentness | `Ft012HandoffService`: COMPLETED + FINALIZED + CURRENT; Version-/History-/Revalidate-UI | Handoff- und Review-Testquellen; neue Application-Tests prüfen erhaltene NOT_READY-Sperren, nicht den Upstream-Owner | Execution-Korrektur→Review-STALE→explizite neue Bewertung und Race-Vertrag vollständig qualifizieren | Nicht ausgeführt |
| Journal CRUD / PB-019 journal | `TradeJournal`, `TradeJournalVersion`, Persistenztabellen/Constraints; kein Editor im gelesenen Consumer | Keine ausgeführte Journal-Schreibstrecke; Dataclasses sind kein CRUD-Nachweis | Application Commands, Repositories, API und Editor fehlen im untersuchten Weg; globale Schreibwegsuche vor Ausbau abschließen | Nicht ausgeführt |
| Journal Finalisierung/Versionierung / PB-019 journal | DRAFT/FINALIZED, Audit, Supersession und unveränderliche Snapshots im Domainmodell | Keine PostgreSQL-/UI-Qualifikation | Leerfall, Finalisierungsbedeutung, konkrete Quellenbindung, CAS, Retry und Folgeversion vor Implementierung festlegen; keine Scores erfinden | Nicht ausgeführt |
| Evidence-Übergabe / PB-019 materialization | Bestehender Service/API/Status; zwei bisher konkurrierende UI-Aktionen | 23 neue isolierte Application-Tests bestanden; 4 isolierte Client-Wire-Prüfungen bestanden; API-/React-Tests nur Quelltext | Patch bindet First-party-Bestätigung an konkrete Version und synchronisiert Readback; PostgreSQL-Konflikte und atomare Upstream-Korrektur bleiben offen | Nicht ausgeführt |
| Lesson-Erstellung / PB-019 lessons | `LessonDraftFromEvidence`, Titel/Kategorie/Inhalt explizit; versionierte Domainmodelle und EvidenceLink-Relation | Bestehende Quellen gelesen; keine vollständige Writer-/DB-Strecke ausgeführt | Kein neuer Lesson-Generator; exakte Provenance bis Detail und Voll-Exit-Szenario qualifizieren | Nicht ausgeführt |
| Lesson-Review / PB-019 lessons/currentness | LessonReviewSignal, NEW_VERSION_CREATED/UNCHANGED_CONFIRMED/LESSON_RETIRED; registrierungsbezogene Testquellen | Domain/Route-Testquellen vorhanden, Review Services/DB nicht vollständig verifiziert | Explizite Revalidierung, Relation SUPPORTS/CONTRADICTS/CONTEXTUAL und alte Version nach Quellenkorrektur nachweisen; nicht automatisch auf CURRENT setzen | Nicht ausgeführt |
| Rückverfolgbarkeit / PB-018 currentness, PB-019 lessons | FT011Evidence referenziert Trade/Observation/Review/konkrete ReviewVersion; LessonEvidenceLink gehört zu LessonVersion | Neue Unit-Fälle erhalten alte Evidence beim Replay und neuer Quellversion, nicht alte Lesson-DB-Versionen | Status ist kein historisches Evidence-Inventar; STALE-Quellen dürfen nicht unsichtbar/ausgetauscht werden. Historische Lesson-Details und Journalquellen bleiben offen | Nicht ausgeführt |
| Externe Beobachtungen / bestehendes FT-012 | Bulk-Import-Dokument und ExternalObservation-/Evidence-Typen; getrenntes execute-as-trade | Import-Retry und wirtschaftliche Dubletten nicht neu ausgeführt | Import, Zuordnung, ausdrücklich bestätigte Tradeerfassung und Materialisierung getrennt halten; kein neuer Importprovider | Nicht ausgeführt |

## Gewählter Patch und Vertrag

Der vor Änderung festgehaltene DoR steht in
[POST_TRADE_LEARNING_HANDOFF_DOR.md](POST_TRADE_LEARNING_HANDOFF_DOR.md).
Der Schnitt ersetzt ausdrücklich nicht den priorisierten Journalabschluss.

### Backend

`backend/app/features/learning/application/ft011_materialization_service.py` erhält
`expected_exit_review_version_id`. Ein nicht passender Owner-Handoff führt vor neuen
Schreiboperationen zu `SOURCE_VERSION_MISMATCH`. FT-011 bleibt alleiniger
Eignungsowner. Gültige NOT_READY-/STALE-Sperren und semantische Eindeutigkeit bleiben.
Typ-only-Imports wurden unter TYPE_CHECKING gestellt; Domainimplementierung,
Persistenz, SQL-Transaktionsreihenfolge und bestehende DI-Fabrik bleiben dieselben.

Der optionale API-Body im vorhandenen `materialization_router.py` enthält bei
Verwendung genau eine gültige UUID. `{}`, falscher Name, null-UUID, ungültige UUID
und zusätzliche Felder sind ungültig. Ein ausgelassener Body beziehungsweise der
bisherige bodylose Vertrag bleibt kompatibel. Legacy-Clients bestätigen dadurch
weiterhin keine zuvor angezeigte Version. Für strikte Pflicht-Pins aller externen
Clients wäre eine eigene Kompatibilitätsentscheidung nötig.

Der Fingerprint enthält den Pin nur, wenn er angegeben wurde. Bestehende persistierte
Fingerprints ändern sich nicht. Derselbe erfolgreiche Request liefert seine alte
Evidence auch nach späterer Quellenänderung zurück. Das ist keine erneute CURRENT-
Bestätigung. Unterschiedliche Keys zur selben geeigneten Quellversion erzeugen
weiterhin keine semantisch neue Evidence. Ein DB-Konflikt bleibt 409 mit Rollback;
die Unit-Prüfung ist ausdrücklich kein echter Nebenläufigkeitsnachweis.

### UI

`materializationClient.ts` verwendet den vorhandenen JSON-HTTP-Helper und übergibt
das Objekt genau einmal serialisierbar. Beide First-party-Aufrufe senden die
angezeigte Version mit dem stabilen separaten Key-Namensraum
`ft011-to-ft012:v2:<trade>:<review-version>`; kein Date.now und kein current-Fallback.

`PostTradeLearningPage.tsx` zeigt eine Übergabeaktion, liest nach Review-Aktionen
und Materialisierung den Backendstatus neu und erfindet keinen Ready-/Materialized-
Status aus einem Command-Receipt. `PostTradeReviewPage.tsx` behält seine einzelne
Aktion im Standalone-Kontext, aber nicht zusätzlich im kombinierten Einstieg.
Die URL bestimmt den Trade-Kontext; verspätete Reads eines alten Trades werden
nicht in den neuen übernommen. Laden desselben Trades ist eine explizite Leseaktion.

Lesson-Readback hat getrennte Zustände für lädt, erfolgreich leer, erfolgreich
vorhanden und Fehler mit Retry. Ein Fehler öffnet nicht ersatzweise den
Lesson-Erstellungsdialog. Es wird keine Lesson, Hypothese, Freigabe, Modellversion
oder Aktivierung automatisch erzeugt.

Nicht gelöst: Source-Correction-Race nach dem Handoff-Read; historischer Evidence-
Readback bei STALE; allgemeine atomare Review-Update/Finalize-CAS; vorhandener
Review-GET-catch, der unterschiedliche Ladefehler als fehlendes Review behandelt.
Diese Grenzen gehören zur Gesamtstrecke, nicht zu einem behaupteten Abschluss.

## Ergebnisse je Nutzer-Abnahmekriterium

| Kriterium des Startprompts | Ergebnis dieser Arbeit |
|---|---|
| Geeigneter Voll-Exit erreicht Beobachtung/Review, offen/storniert abweisen | Soll und Consumer geprüft; keine echte synthetische Capture-/DB-Strecke ausgeführt |
| Unvollständiger Horizont bleibt unvollständig, damalige Kenntnis nicht erfinden | FT-011-Soll erhalten; 13/20-UI-Testquelle vorhanden, kein aktueller Lauf |
| Journal speichern, finden, bearbeiten, finalisieren, Folgeversion, Leer-/Pflicht-/Konkurrenzfälle | **Nicht implementiert/nicht erfüllt**; konkreter Entscheidungsvorschlag unten |
| Explizite Evidence der konkreten Review-Version, Retry/falsche Version/STALE/parallel | Application-Pin-/Replay-/Negativfälle bestanden; wire-boundary bestanden; echte parallele DB-Übergaben und API-App-Integration offen |
| Lesson braucht ausdrückliche Interpretation und konkrete Evidence, keine Modellversion | Aktueller Formular-/Domainvertrag gelesen und nicht verändert; durchgängiger Nachweis offen |
| Korrektur erhält alte Lesson und zeigt Currentness mit kontrollierter Aktualisierung | Alte Evidence bleibt in Unit-Fixtures stabil; alte Lesson-DB-Version und vollständige Currentness-Kette nicht nachgewiesen |
| Externe Beobachtung getrennt, Import-Retry ohne wirtschaftliche Dublette | Dokument-/Typgrenze erhalten, Importpfade unverändert; Testlauf offen |
| Browser und PostgreSQL: Voll-Exit→Beobachtung→Review→Journal/Evidence→Lesson plus Korrektur | **Nicht ausgeführt/nicht erfüllt** |

## Journal: konkreter Entscheidungsvorschlag, keine stillschweigende Freigabe

Inputs bleiben eigene Trade-ID, feste Workspace-/Actorgrenze, vorhandene
Reflexionsfelder `what_went_well`, `would_do_differently`, `additional_notes` sowie
der beim Abschluss tatsächlich herangezogene Quellenstand. Actor-Audit ist kein
Authentifizierungsnachweis. Outputs bleiben FT-012-Journal und konkrete Version.
Keine psychologischen Scores, Schulnoten oder neue PnL-Felder.

| Vertragsfrage | Vorschlag und Auswirkung | Vor Implementierung zu entscheiden/nachzuweisen |
|---|---|---|
| Entwurf | Alle drei vorhandenen Textfelder optional; leerer Entwurf speicherbar. Ein Journal je Trade, höchstens ein offener Entwurf. Kein Performance-Gate. | Exakter existierender Trade-/Handoff-Gate für Draft versus Finalisierung; nicht pauschal auf alle Downstreamschritte verschärfen |
| Abschlussinhalt | Mindestens eines der drei Felder enthält eine ausdrücklich gespeicherte nicht-leere Reflexion; keine Pflicht, jedes Feld zu bewerten. | Das wäre eine neue Verschärfung gegenüber der aktuellen Domain, die leere Finals erlaubt; deshalb ausdrücklich entscheiden. Alternative: leere Finals zulassen und als inhaltsleer ausweisen. Kein Backfill historischer Texte |
| Finalisierungsbedeutung | Gespeicherten Draft mit konkreter Identität, Versionsnummer, Audit und exakt herangezogener Quellversion sichern; unsaved UI-Inhalte nicht als persistiert behandeln. | Bestehende JournalVersion hat kein Review-Pin-Feld. Additive Quellenbindung beim FT-012-Owner spezifizieren; Altstände ohne Pin bleiben UNKNOWN, nicht latest |
| Konkurrenz/Retry | Auf gesperrtem Journal-Aggregat zusätzlich optimistische Draft-Revision/Precondition prüfen. Identischer erfolgreicher Finalize-Retry liefert denselben Stand. | Bestehende Constraints verwenden, CAS-Feld/-Token nicht nur UI-Hilfszustand; echte parallele PostgreSQL-Tests für Erstentwurf, Speichern, Finalisieren, Folgeversion |
| Folgeversion | Neuer Draft mit neuer ID/Versionsnummer und `supersedes_version_id`; letzte finale Texte können als erkennbare Vorlage kopiert werden. Alte finale Inhalte/Audit unverändert. | Eindeutiger Vorgänger, nur ein offener Draft, altes Finale unveränderlich, stale Quellen erneut ausdrücklich bewerten |
| Löschen | Keine finale Version löschen. Entwurf nur verwerfen, sofern der geltende Vertrag dies ausdrücklich zulässt. | Audit-/Versionsnummern-/Linkfolgen vor einer DELETE-API entscheiden, nicht pauschales CRUD erfinden |
| Evidence | Nur konkrete finale JournalVersion referenzieren, `TRADE_JOURNAL_VERSION` als Typ behalten, semantisch deduplizieren. | Materialisierung und Lesson-Erstellung getrennt; eine nachträgliche Journal-/Quellenkorrektur retargetiert keine alte LessonVersion |
| UI | Bestehender Learning-Consumer: Entwurf laden/speichern, klarer Finalisierungsdialog, History/readonly Finals, ausdrückliche Folgeversion; Fehler/Conflict mit Readback. | Reload, Leerfälle, Quellenwechsel, zwei Tabs, Response-Verlust und historical provenance im Browser prüfen |

Ein neuer Journal-Owner, neue Importquelle oder automatische Optimierung lösen
keinen dieser Punkte. Neue additive Migrationen erst nach vollständigem
Schema-/Parallel-PR-Abgleich; keine freigegebene Migration ändern und kein stamp.

## Lesende Verträge für Performance und Governance

**Wirtschaftliche Fakten:** Nur bestätigte effektive ExecutionRecords/Positionen
aus FT-009/010 tragen tatsächliche realisierte Bruttoergebnisse. Storno erzeugt
keinen SELL. Ein aktueller korrigierter Positionsread ist nicht automatisch der
bei einer historischen Journal-/Lessonentscheidung bekannte Stand. Referenzierte
Execution-IDs/Supersession, zeitliche Präzision und Recording-Zeit getrennt lesen.
Date-only-UTC-Anker beweist keine Mitternachtsausführung. Keine Gebühren/FX/Netto-
Werte aus fehlenden Eingaben erzeugen.

**Beobachtung:** FT-011 besitzt 20 zulässige abgeschlossene Underlying-EOD-Punkte
nach dem Exit-Tag. Anzahl verfügbarer Beobachtungen ist nicht Kalenderdauer.
Hypothetische Underlying-Entwicklung ist kein erzielbarer Warrant-Verkaufspreis
und keine realisierte Performance. Beobachtungsdatum, Abruf-/Kenntniszeit,
Listing/Quelle und Qualitätszustand nicht gleichsetzen. In dieser Arbeit wurden
keine historischen Preise hinzugefügt, interpoliert oder als damals bekannt markiert.

**Review und Evidence:** `FT011Evidence` referenziert konkrete Trade-, Observation-,
Review- und ReviewVersion-IDs. Materialisierungszeit ist weder Exit-Zeit noch
Kenntnisstichtag. Der bestehende Materialisierungsstatus ist nur ein aktueller
Handoff-Read: Bei NOT_READY/STALE liefert er `materialized=false` ohne historische
Evidence-ID. Er darf daher nicht als Beweis benutzt werden, es existiere keine
alte Evidence, und nicht als Currentness-Prüfung beliebiger gespeicherter IDs.

**Journal und Lesson:** Ein Draft ist nicht die referenzierbare finale
JournalVersion. Lesson-Version, Evidence-ID, Source-Typ, konkrete Source-Version
und Relation SUPPORTS/CONTRADICTS/CONTEXTUAL getrennt lesen. Lesson.current_state
allein beweist nicht die Freshness jeder Quelle; die gelesene Lesson-Referenzliste
ist eine Navigation zu aktuellen Lesson-IDs, kein unveränderlicher historischer
Detailnachweis. Alte Inhalte/Links bleiben erhalten; Revalidierung beziehungsweise
neue LessonVersion benötigt eine ausdrückliche, auditierte Aktion. Dieser
vollständige Readback ist noch zu qualifizieren.

**Externe Beobachtungen:** ExternalObservation-Evidence bleibt separat von eigenen
ExecutionRecords und eigener Performance. Quelle, konkrete Version, observed_at,
recorded_at/imported_at und Datei-/Row-Herkunft getrennt lesen. Import, Zuordnung,
ausdrückliches execute-as-trade und Materialisierung sind verschiedene Aktionen.

**Governance:** Evidence-/Journal-/Lessonabschluss erzeugt keine Hypothese,
ModelVersion, Approval oder RuntimeActivation. Downstream-Governance muss konkrete
versionierte Inputs und ihren Bewertungs-/Kenntniszeitpunkt festhalten und
Quellenqualität/Currentness prüfen. Performance ist ein Leser, kein Journal-Gate.

## Verifikation und Betriebsfolgen

Ausgeführt wurden ausschließlich synthetische lokale Tests ohne Netzwerk-/DB-
Schreiben. Die genaue lokale Patch-Commit-ID, Befehle, Versionen und Logs liegen
im mitgelieferten Verifikationsprotokoll. 23 Application-Fälle liefen mit echten
FT-012-Dataclasses und dem tatsächlichen geänderten Service, aber Fake-UOW/Repository/
Handoff. Vier Node-Wire-Prüfungen führten den geänderten TS-Client zusammen mit dem
hashgeprüften originalen HTTP-Helper aus; fetch, Umgebung und Auditidentität waren
synthetisch. Das ist weder Vitest, Browser-E2E noch ein Backend-HTTP-Server.

Zusätzliche registrierte API- und React-/Vitest-Regressionen sind als Quelltext
vorbereitet, nicht ausgeführt. TypeScript-Transpilation prüft Syntax, nicht die
vollständigen Projekttypen. Python-compileall prüft Syntax, nicht Integration.

Nicht ausgeführt: `bash scripts/check-backend.sh` (vollständiger Checkout und
ruff/black/mypy/asyncpg fehlen), `bash scripts/check-frontend.sh` (Projekt-React/
Vitest/Lockfile-Installation fehlt), `bash scripts/run-e2e.sh` (Docker/Teststack
fehlt), `python -m alembic heads/current/upgrade head` (Migrationengraph/DB nicht
lokal vorhanden). Projekt-Coverage-Gates wurden nicht geändert oder ersetzt.
Python im Container ist 3.13.5, nicht der Projekt-Baseline-Interpreter 3.12.

Der gelesene E2E-Einstieg nutzt `trading-workspace-e2e`, Ports 25432/28000/28080 und
löscht eigene Volumes im Cleanup. Er wurde nicht gestartet. Vor jeder künftigen
Schreibprüfung DB-Ziel, Compose-Konfiguration, Volumes/Bind-Mounts, Scheduler,
Provider und Notifications identifizieren; Schreibfreigaben ausschließlich für
den Wegwerfstack. Keine Produktiv- oder Nutzerdaten als Testfixture.

Der Patch enthält keine Migration und keinen Daten-Backfill, keine Änderungen an
.env/Compose/Consent/Provider/Activation und keinen Deployment-Schritt. Die
Versionsmanifeste bleiben 1.5.5. Das Remote-Migrationenverzeichnis wurde gelesen;
ein vollständiger `alembic heads`-Nachweis und ein paralleler Migrationenabgleich
fehlen. Keine Behauptung über das installierte Schema oder Verlustfreiheit eines
Downgrades. Benutzerinstallation und menschliche Abnahme bleiben separat offen.
