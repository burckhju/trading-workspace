# FT-012 Journal — technische Qualifikation und Übergabe

Nachweisstand 15.10.2026 zu [PB-019 Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal).
Aufgabenstatus ausschließlich dort; keine menschliche Fachabnahme, kein Release oder Zielbetrieb.
Vertrag: [DoR](FT012_JOURNAL_WRITE_DOR.md), [ADR-POST-FT012-005](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md).

## Identität und tatsächlich ausgeführte Prüfungen

Draft #260 bleibt auf Draft #259 (`818d1d800f02bfe7478cefa89073643d655b7413`) gestapelt.
Ausgangsstand dieser Fehlerqualifikation: `85be220fdef6b21d27e1d3909e99d11a13b274cc`.
Gemeinsamer tatsächlich ausgecheckter Prüfcommit: **`666e8ab07d4fd509e316eadfa9b31d57ce3d48c3`**,
Tree **`542e50b5259c5d830e9c4b42946ef68165fbb439`**.
[Qualifikationslauf 38683089292](https://github.com/burckhju/trading-workspace/actions/runs/38683089292).
Trigger `9defb00d…` ist nicht der danach erzeugte Testhead; die Testjobs verwenden den obigen
unveränderten Checkout. Artefakt `qualification/identity.txt` und Playwright `gitCommit.hash`
belegen diese Identität. Die nachfolgende Fortschreibung ändert nur Dokumentation.

| Prüfung auf genau diesem Code-/Teststand | Ergebnis |
|---|---|
| Gezielte Journal-/Owner-/Löschschutztests, einschließlich drei echter PostgreSQL-Tests | **55 bestanden** |
| `bash scripts/check-backend.sh` | **2.645 bestanden**, 1 Warnung; **86,75 % Coverage**, Grenze unverändert 85 %. Ruff, Black über 922 Dateien und mypy über 528 Quelldateien bestanden. |
| Fünf gezielte Frontendtestdateien | **39 bestanden**; zusätzlich lokal 39 bestanden auf identischem Frontend-Code. |
| `bash scripts/check-frontend.sh` | **472 Tests / 102 Dateien bestanden**; TypeScript, ESLint, Prettier und Build bestanden. Zeilen/Statements **92,40 %**, Branches **83,53 %**, Funktionen **84,47 %**; Grenzen unverändert 80/80/80/70 %. |
| Gezielter echter Journal-Browserpfad mit Erfolgstrace | **1 bestanden**, nicht übersprungen |
| `bash scripts/run-e2e.sh` | **52 bestanden**, 0 fehlgeschlagen/flaky/übersprungen |
| Alembic auf realem PostgreSQL | Upgrade erfolgreich, vor/nach Gesamtgate genau Head **20261014_0046** |
| Git | `git diff --check` bestanden, vollständiger lokaler Prüfbaum entspricht dem CI-Tree |

Zieltests sind Teilmengen der Gesamtprüfungen, nicht zusätzliche Fälle. Der neue Journalbrowser
verwendet echte HTTP-Schreibbefehle und PostgreSQL; nur synthetische Underlying-Preisbeobachtungen
sind Testfixtures. Kein behaupteter Live-Datenanbieter-/Zielinstallationsnachweis.

## Fehler und begrenzte Reparatur

Der frühere Lauf `38634613102` war rot: ein ungültiger Löschschutz-Testdatenbestand und zwölf
Browserfehler. Ein EXTERNAL-Trade wurde dort nachträglich per SQL mit einem TradePlan verknüpft;
die bestehende Herkunftsconstraint wies das korrekt ab. Die neue Fixture erstellt über die
tatsächlichen Owner einen MANUAL-Plan, bestätigt seine genaue Version, dokumentiert eine
konkrete Produktwahl und erfasst BUY über `/purchases/from-selection`, anschließend Voll-SELL.
Fehlende Quotes bleiben NOT_EVALUABLE; die ausdrückliche Begründung ändert die Evaluation nicht.
Ursprung und vier Herkunftsreferenzen werden überprüft. Nach verweigertem Plan-Hard-Delete
bleiben Plan, Trade, Journal, Lesson und Execution-Historie unverändert. Keine SQL-Umschreibung
von EXTERNAL-Herkunft, keine abgeschwächte Constraint.

Alle zwölf erhaltenen Browser-Fehlertraces enthalten CORS-Fehler: `localhost:8080` griff auf
den für die Prüfung gebauten API-Ursprung `127.0.0.1:8080` zu. Der neue Journaltest verwendet
jetzt wie die bisherigen schreibenden Fälle ausdrücklich `localhost:8080`; die Prüf-API wird
wieder für `http://localhost:8080/api` gebaut. Keine Erweiterung von Produktions-CORS, keine
Änderung bestehender Browserfälle, Assertions, Zeitlimits oder Gates. Alle zwölf Fälle sind
im finalen Gesamtbericht erneut ausgeführt und erfolgreich.

Ein erster Reparaturlauf `38682752634` auf `6e5a9a3…` bestand schon die 55 gezielten Tests,
stoppte im vollständigen Backend-Gate aber an Ruff E501 in einer neuen Testzeile. Nur deren
Zeilenumbruch wurde korrigiert. Frühere Fehlversuche bleiben Fehlversuche. Gegenüber dem
Ausgangsstand ändern sich dafür nur `test_journal_write_postgres.py`, der neue
`post-trade-journal-postgres.spec.ts` und der vorab ergänzte DoR-Nachtrag.

## Getrennte Abnahmematrix / Restscope

| Teilfähigkeit | Technisch belegter V1-Weg | Eigenständig offen |
|---|---|---|
| Nachbeobachtung — FT-011 / PB-018 | Tatsächliche synthetische REST-BUY/SELL-Erfassung; offener Trade abgewiesen, echte Stornierung getrennt. 19 Beobachtungen bleiben unvollständig; erst 20 vorhandene abgeschlossene Datensätze ergeben COMPLETED. | Live-Datenqualität/-rechte, Zielinstallation; keine Kalendertagsauffüllung oder erfundene Warrant-/IV-Historie. |
| Exit Review — FT-011 | Browser: Entwurf, Finalisierung, ausdrückliche Quellenprüfung nach Execution-Korrektur, neue Review-Version und erneute Finalisierung; alte Version bleibt erhalten. | Globale Serialisierbarkeit gegenüber allen parallelen Preis-/Review-Änderungen. |
| Journal Schreiben / Abschluss / Versionieren — FT-012 / PB-019 | Vorhandenes Modell → JournalRepository/UOW → JournalService → registrierte API → TradeJournalPanel im PostTradeLearningPage. Speichern, Reload, geschützter Abschluss, ausdrückliche Folgeversion mit unverändertem altem Stand. | Kein externer Beobachtungsjournal-Editor, kein neuer Journal-DELETE-Endpunkt, keine gesonderte vollständige Journal-Mobil-/Barrierefreiheitsabnahme. |
| Leer-/Pflicht-/Konkurrenzfälle | Drei Texte optional; leeres Final sichtbar leer. Operationsabhängige Bestätigung, Key, Version/Revision Pflicht. Alte Revision erzeugt Konflikt. Reale parallele Commands: ein Gewinner oder derselbe Replay-Beleg. | Nicht jeder API-/Unit-Spezialfall zusätzlich als Browserfall dupliziert. |
| Evidence-Übergabe — FT-012 | Konkrete FINALIZED-JournalVersion ausdrücklich als TRADE_JOURNAL_VERSION materialisiert. Gleiche/andere Keys behalten dieselbe Evidence. Historische Journal-Evidence bleibt bei STALE lesbar. | FT011-Reviewmaterialisierung aus #259 ist eigener Weg; Race nach deren Handoff-Read und historisches FT011-Evidence-Inventar bei NOT_READY bleiben offen. |
| Lesson-Erstellung — FT-012 | Eigene Interpretation, genaue Evidence/Relation; GET/SQL in neuer Session belegen Commit. Ungültige Tags rollen Lesson, Version, Links und Tags zurück. Detail zeigt konkrete Journalversion und heutigen Source-Check. | Kein automatisches Lesson-, Hypothesen-, Approval- oder Aktivierungsprogramm. |
| Lesson-Review — FT-012 | Alte Lesson-Version und Evidence-Link bleiben bei Execution-/Review-/Journal-Korrektur unverändert; heutiges STALE sichtbar, neue Journalversion ersetzt keinen alten Lesson-Link. | Allgemeiner bedienbarer Lesson-Review-/Revalidierungs-/Folgeversionsdialog und alle SUPPORTS/CONTRADICTS-Kombinationen separat schließen. |
| Rückverfolgbarkeit / Historienerhalt | Konkrete IDs, DB-Schutz finaler Journalversionen und Evidence-Quellen. Tatsächlich planbasierter Hard-Delete mit 409 vor abhängigen Löschungen. Legacy NULL/UNKNOWN unverändert. | Audit-Actor ist kein Authentifizierungsnachweis; keine neue Multiusergrenze. |
| Externe Beobachtungen | Bestehende Import-/Execute-as-trade-Regressionen in vollständiger Suite; in dieser Reparatur kein Import-/Providerpfad verändert. | Kein neuer Import→Journal-Live-E2E-Beleg. Import, bestätigte eigene Ausführung und Evidenz bleiben getrennte Aktionen. |

Wesentliche ausführbare Quellen: `tests/integration/backend/learning/test_journal_write_postgres.py`
(echter Plan-/Capture-/Korrekturpfad, Parallelität, Legacy-Migration),
`tests/e2e/post-trade-journal-postgres.spec.ts` (echter Browser/HTTP/PostgreSQL),
`test_journal_commands.py`, `test_journal_api.py`, `test_journal_source_inspection.py`,
`TradeJournalPanel.test.tsx` und `JournalEvidenceOrigin.test.tsx`.
Die zuvor fehlende Journalstrecke ist damit V1-technisch qualifiziert, nicht der ganze Lernbereich.

## Bedienweg

Im vorhandenen Post-Trade-Einstieg den tatsächlichen Voll-Exit öffnen. Ausreichende
Nachbeobachtung und geeigneter finalisierter Review bleiben die FT-011-Voraussetzungen;
Performance ist kein zusätzliches Gate. Im **Trade-Journal** den Entwurf ausdrücklich anlegen.
Die optionalen Texte „Was lief gut?“, „Was würde ich anders machen?“ und „Weitere Notizen“
bearbeiten und speichern. Unsaved-Text ist nicht der Abschlussstand: Finalisieren bleibt
bis zum Speichern gesperrt. Der Bestätigungsdialog sichert nur den gespeicherten Stand.
Ein leerer Abschluss bleibt erkennbar leer, keine erfundene Bewertung.

**Journalversion als Evidence übergeben** separat bestätigen. Erst die weitere ausdrückliche
Eingabe von Titel, Kategorie und Inhalt erstellt eine Lesson. Die vorhandene FT011-Evidence-
Lesson-Strecke benötigt nicht zusätzlich ein Journal.

Nach einer Execution-Korrektur **Quellenstand neu laden**: originale Texte bleiben sichtbar,
die heutige Prüfung kann STALE ergeben. Review gegebenenfalls über **Review-Quellenstand
prüfen** und **Neue Review-Version vorbereiten** bewusst korrigieren und finalisieren.
Danach **Folgeversion vorbereiten**, bearbeiten, speichern und finalisieren. Vorhandene
Lesson-Version und ihr alter Evidence-Link werden nicht automatisch ersetzt.

Bei Konkurrenz oder unklarer Netzwerkantwort bleiben lokale Texte erhalten; dieselbe bewusste
Wiederholung verwendet denselben Schlüssel. Der gesonderte Ladebefehl zum gespeicherten
Journalstand ist als Verwerfen lokaler Texte beschriftet. Ein Befehlsbeleg ist kein historischer
Snapshot eines veränderlichen Entwurfs und ersetzt den aktuellen Readback nicht.

## Lesende Quellen für Performance und Governance

| Quelle | Versions-/Zeitbezug | Grenze |
|---|---|---|
| Execution/Position beim Trade-Owner | Konkrete Execution-IDs/Supersession und tatsächliches Ausführungsdatum/-zeit | Nur wirtschaftliche Fakten begründen realisierten Tradegewinn; Brutto nicht automatisch Netto. |
| FT-011 Observation / ExitReviewVersion | Exakte Review-Version, Fingerprint, Audit und eigene CURRENT/STALE-/Supersession-Verträge | Underlying-EOD-Verlauf ist hypothetischer Vergleich, kein erzielbarer Warrant-Verkaufspreis. |
| GET `/api/v1/learning/trades/{trade_id}/journal` | Journal-ID und einzelne version.id, edit_revision, Texte, Audit, supersedes_version_id | DRAFT veränderlich, FINALIZED gesicherter Inhalt; Abschluss bestätigt nicht die Wahrheit einer Interpretation. |
| GET `/api/v1/learning/journal-versions/{version_id}` | Exakte Version und ggf. nullable source_exit_review_version_id | is_latest ist nicht Source-Currentness. source_checked_at ist heutige Prüfung, nicht damalige Kenntnis. CURRENT gilt as-of-read. |
| LearningEvidence / LessonVersion | Typ TRADE_JOURNAL_VERSION, exakte Quelle, Materialisierungszeit und Relation am Lesson-Link | Persönlicher gespeicherter Stand, kein Marktbeweis. Späteres STALE mutiert weder alte Quelle noch Lesson-Link. Lesson-CURRENT allein bestätigt nicht alle Quellen. |

Lesson-Details verweisen auf genau die Journalversion. Der heutige nichtschreibende
Source-Check kann bis zur ausdrücklichen FT-011-Revalidierung von gespeicherter Currentness
abweichen. Das ist keine stille Umschreibung. Governance berücksichtigt diese Grenzen in
ihrem eigenen ausdrücklichen Review; keine automatische Modelländerung durch Journalabschluss.

## Migration, Betrieb und Nachweisgrenzen

Die bestehende Journal-PR-Migration `20261014_0046` erweitert `0045` additiv mit
edit_revision=1 und nullable Review-Quelle für Altstände. In dieser Reparatur unverändert.
Ein echter Legacy-Migrationstest belegt originale finale Texte und UNKNOWN statt erfundener
Herkunft. Finale Journalhistorie blockiert bisherige endgültige TradePlan-Löschungen mit
JOURNAL_HISTORY_PROTECTED. Das ist eine sichtbare Betriebsänderung, kein stiller Cascade.

Downgrade verweigert neue source-gebundene oder revisionierte Daten; andernfalls entfernt er
Schutzmechanismen. Kein verlustfreier Betriebsrollback. Vor einer gesondert freizugebenden
Installation Sicherung und Wiederherstellbarkeit prüfen. Keine Nutzerdatenbank migriert.

CI: frische Runner, Python 3.12.15, Node 22.16.0/npm 10.9.2, PostgreSQL 17, synthetische Daten.
Browserstack ausschließlich trading-workspace-e2e mit geprüften Ports 25432/8000/8080,
neuen eigenen Volumes und leerem eigenem Bind-Mount; keine private .env/Consent-Daten.
Provider, Scheduler und Telegram deaktiviert, Schreibfreigaben nur für diesen Teststack.
Cleanup nur für den zuvor als neu identifizierten Stack. Temporäre Prüf-/Transportdateien
sind aus dem Endstand entfernt. Standard-Gates, Locks und Versionsdateien bleiben unverändert.

Lokal nur 39 gezielte Frontendtests und Git-Prüfungen; kein Docker/PostgreSQL und kein
vollständiger manifestierter Python-3.12-Teststack. Lokale Befehle `bash scripts/check-backend.sh`
und `bash scripts/run-e2e.sh` deshalb nicht als durchgeführt behauptet; deren Gesamtbelege
stammen aus CI. Keine JMBbot-/Produktionsprüfung, echten Nachrichten, realen Bestandsänderungen,
Providerzustimmungen oder Modellaktivierungen. Keine menschliche Fach-/Betriebsabnahme.

## Artefakte und Integrität

Original-ZIPs aus demselben Qualifikationslauf wurden heruntergeladen und anhand der
GitHub-Digests verifiziert; Rohprotokolle und zwei Journal-/Lesson-Screenshots wurden gelesen.

| Artefakt-ID | Inhalt | SHA-256 |
|---|---|---|
| 11949731638 | Backend, Zieltests, Migration, Checkout, Coverage | b8485b937d8f5a16a54eb37ab310fe49ed4910f56795b66be4d1c393b71881fa |
| 11949495300 | Frontend-Gate/Zieltests/Coverage | cd547fe8408a3e684266623cf8b8b757e4d058b2f15f3f8adb0f0bb15c4b0d84 |
| 11949320596 | Vollständige Browser-Suite | 97ffe167f14eb091672bc2a51f5ab4fc6a68dbfac327da175f0453d3d6ed1435 |
| 11949690173 | Echter Journalpfad mit Erfolgstrace | 75a5acfdc49ce53b5157208c4caf3db7916295b00a23aa4787fe571dd2406956 |

## Genau nächster Umsetzungsschnitt

Den allgemeinen expliziten Lesson-Review-/Folgeversionsdialog für bereits verknüpfte veraltete
Evidence im FT-012-Owner schließen: bestehende Contracts, echte Commit-Grenzen, genaue
LessonVersion und SUPPORTS/CONTRADICTS-Relationen zuerst abgleichen. Keine automatische
Aktualisierung alter Lesson-Versionen. Die atomare FT011-Handoff-Lücke bleibt separat offen.
