# UI3 — Lesson-Ansicht, Quellen und vorbefüllte Prüfung

26.10.2026, Europe/Berlin. Dieser Bericht beschreibt den abgegrenzten
UI-Implementierungs- und Nachweisstand. Den Arbeitsstatus führt ausschließlich
[PB-019 Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons).

## Basis und Integrationsgrenze

Ausgangsbasis ist der erneut gelesene `main`
[`f8f61a11f65e9b36735704a2fabc3e4e953d4a77`](https://github.com/burckhju/trading-workspace/commit/f8f61a11f65e9b36735704a2fabc3e4e953d4a77),
`VERSION` **1.5.21**. [#284](https://github.com/burckhju/trading-workspace/pull/284)
und [#285](https://github.com/burckhju/trading-workspace/pull/285) sind darin
integriert. Der Tag `v1.5.21` zeigt dagegen auf
`059860eaedeac158abb9c1a67476047c10ed8014`: Er enthält #284, aber nicht den späteren
Produkt-Merge #285. Main-Integration, veröffentlichtes Softwaretag und tatsächliche
PC-Installation sind getrennte Nachweise.

Die Bestandsprüfung fand keine parallele passende Lesson-Konsolidierung. Die
Arbeit erfolgt im eigenen Worktree auf `refactor/lesson-detail-consolidation`.
Die offenen Arbeiten [#90](https://github.com/burckhju/trading-workspace/pull/90)
und [#187](https://github.com/burckhju/trading-workspace/pull/187) bleiben separat.
Produkt-/Planfunktionen, Versionsdateien, Veröffentlichungsgates und Tags werden
durch diesen Auftrag nicht geändert. Der Auftrag endet beim geprüften Draft-PR;
Merge, Release und PC-Deployment gehören nicht dazu.

## Eine ausgewählte Inhaltsversion

[LessonDetailPage](../../frontend/src/features/learning/pages/LessonDetailPage.tsx)
isoliert den Seitenkontext nach Lesson-ID. Das
[LessonReviewPanel](../../frontend/src/features/learning/components/LessonReviewPanel.tsx)
verantwortet den vorhandenen `review-context` gemeinsam für Kopf, Versionswahl,
Inhalt, Quellen, Prüfaktionen und Audit. Der zusätzliche `getLesson`-Abruf und
sein zweiter vollständiger Inhalts-/Evidenceblock entfallen auf dieser Seite;
der Clientvertrag bleibt für andere Verbraucher erhalten. Es entsteht weder ein
zweiter persistierter Datenspeicher noch ein globaler Cache.

Der Kopf trennt Lesson-Titel, gewählte Inhaltsversion mit „aktueller Stand“ oder
„historisch“ und heutigen Lifecycle-Status. Der Titel gehört zur Lesson-Identität.
Ohne Versionsparameter wird zunächst der aktuelle Snapshot ausgewählt; ein
explizites `lesson_version_id` bindet ausschließlich diese Version. Lesson-,
Versions- und Evidence-Link-Zugehörigkeit werden geprüft. Ein fehlender oder
fremder Snapshot wird nicht durch aktuelle Inhalte ersetzt und eröffnet keine
Governance-Aktion. Bestehende `/lessons/{lessonId}`-URLs, genaue kopierbare Links,
`lesson_version_id` und `#lesson-history` bleiben unterstützt.

## Vorbefüllte Entscheidung im bestehenden Vertrag

Der Ablauf folgt unverändert dem
[Lesson-Review-ADR](../decisions/ADR-POST-FT012-006-EXPLICIT-LESSON-REVIEW.md)
und der [Definition of Ready](FT012_LESSON_REVIEW_DOR.md):

| Heutiger Status | Ausdrücklich erreichbare Lesson-Aktionen |
|---|---|
| `CURRENT` | Quellenprüfung beginnen; Widerspruchsprüfung mit konkreten geeigneten `CONTRADICTS`-Links. |
| `REVIEW_RECOMMENDED` | Interpretation unverändert bestätigen, vollständige neue Version erstellen oder außer Gebrauch nehmen. |
| `RETIRED` | Keine implizite Reaktivierung. |

`NEW_VERSION` übernimmt Kategorie, vollständigen Inhalt und sämtliche Evidence-IDs
einschließlich `SUPPORTS`, `CONTRADICTS` und `CONTEXTUAL` aus der bestätigten
aktuellen Basis. Der Editor ersetzt den bearbeiteten Inhalts-/Quellenbereich.
Zusätzliche Evidence wird aus dem vorhandenen Katalog ausgewählt; neue Quellen
werden nicht automatisch eingesetzt. Eindeutige Evidence-IDs, mindestens ein
`SUPPORTS`-Bezug und eine neue nichtleere Begründung mit höchstens 200 Zeichen
bleiben erforderlich. Abbrechen schreibt nichts. Historische Lesson-Inhalte sind
schreibgeschützt; zur Lesson-Änderung wird ausdrücklich zum aktuellen Stand gewechselt.

Ein Refresh derselben Grundlage erhält den lokalen Entwurf. Bei verändertem
Versions-/Status-/Signalstand bleiben seine Eingaben sichtbar und eine weitere
Bestätigung ist gesperrt. Der aktuelle Bedienweg ist bewusstes Abbrechen und
erneutes Vorbereiten aus der neu bestätigten Grundlage; es gibt keine stille
Neubindung und keinen neuen persistierten DRAFT-Lifecycle.

Der bestehende Schreibvertrag behält `Idempotency-Key`, `confirmed: true`,
`expected_current_version_id`, `expected_current_state`,
`expected_open_signal_id` einschließlich explizitem `null` und die vollständigen
operationsabhängigen Daten. Ein unveränderter manueller Retry verwendet denselben
Schlüssel; geänderte Eingaben bilden einen neuen ausdrücklich bestätigten Befehl.
Ein bestätigter Receipt wird vor Ergebnisnavigation gesichert und getrennt vom
anschließenden Readback behandelt. Ein Lesefehler erzeugt keinen weiteren Nachfolger.
Alte Versionen und Links werden nicht geändert.

## Genaue Quellen ohne wiederholte Journaltexte

[JournalEvidenceOrigin](../../frontend/src/features/learning/components/JournalEvidenceOrigin.tsx)
bündelt die Herkunft und die separate
[EvidenceSourceStatus](../../frontend/src/features/learning/components/EvidenceSourceStatus.tsx)-Abfrage
pro gewählter Evidence. Relation, Quellentyp, genaue Quellversion,
Materialisierungszeit und Prüfzeit bleiben zugeordnet. Die drei vollständigen
persönlichen Journaltexte entfallen auf der Lesson-Seite; die kanonische
Journalansicht behält sie.

Vor dem Link
`/post-trade?trade_id={tradeId}&journal_version_id={exactJournalVersionId}`
werden Evidence-Identität, Quellentyp, exakte finalisierte Journalversion,
Journalzugehörigkeit und Evidence-Verknüpfung geprüft. Externe Evidence wird nicht
als persönliches Trade-Journal dargestellt und erhält keinen erfundenen exakten
Journal-Link. Technische Herkunft und Audit bleiben aufklappbar.

`source_currentness` und `review_currentness` behalten ihre unterschiedlichen
Bedeutungen: Journal-`SUPERSEDED` und Review-`STALE` können gleichzeitig gelten.
`UNKNOWN`, fehlende Herkunft und Ladefehler bleiben sichtbar. Ein gültiger genauer
Journal-Link kann bei fehlgeschlagener separater Aktualitätsprüfung weiter genutzt
werden. Die Abfragen werden nur in der Darstellung zusammengeführt; ihre
fachlichen Verträge bleiben getrennt. `CURRENT` der Lesson bestätigt die
Interpretation und bescheinigt keine aktuelle Quelle. Maßgeblich bleibt auch das
[Journal-/Provenienz-ADR](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md).

## Navigation und Governance-Quelle

Ein zentraler bestehender
[PendingNavigationGuard](../../frontend/src/components/PendingNavigationGuard.tsx)
schützt den Lesson-Review-Entwurf und das unmittelbar eingebettete
[Hypothesenformular](../../frontend/src/features/model/components/LessonHypothesisPanel.tsx).
Versions-/Lesson-Wechsel und Browser-Zurück/Vor berücksichtigen ungespeicherte
Eingaben. „Hier bleiben“ erhält sie; Verwerfen öffnet das gewählte Ziel. Während
eines Schreibbefehls ist Verwerfen nicht verfügbar. Die Prüfung sieht dirty/pending
synchron, bevor der nächste Render abgeschlossen ist.

Die Seite wird nicht bei jeder Query-Änderung neu eingehängt. Abgleich mit der
bereits sichtbaren Version erzeugt keinen unnötigen History-Schritt und erhält
Entwurf, Receipt und Hypotheseneingaben. Ein ungeklärter Refresh derselben Quelle
behält das Hypothesenformular bei gesperrten Aktionen. Nur ein echter, zuvor
geschützter Quellversionswechsel setzt dessen versionsgebundenen Entwurf zurück.

Eine ausdrücklich angelegte Hypothese kann weiterhin die tatsächlich sichtbare
historische LessonVersion verwenden. Lesen, Editoröffnung und Versionswahl erzeugen
keinen Befehl. Hypothesentext wird nicht aus Lesson-Inhalten erzeugt. Bestehende
Proposal-/Validierungsregeln werden beibehalten; Modell-, Freigabe- und
Aktivierungslogik erhalten keine neuen fachlichen Funktionen.

## Verifikation und genaue Nachweisbindung

Implementierungs- und Testcommit:
[`986f20a2f7be7c2b38822cc3dbe3049f7c266029`](https://github.com/burckhju/trading-workspace/commit/986f20a2f7be7c2b38822cc3dbe3049f7c266029),
vollständiger Tree **`014efb3830e3865cc140ffcf51d0386f2801024b`**.
Der vollständige lokale Frontendlauf prüfte diesen unverändert gestageten Tree;
GitHub und der anschließend gelesene Commit besitzen exakt denselben Tree.
Der nachfolgende Dokumentationscommit ändert keine Anwendung, Tests oder Konfiguration.
Die reguläre PR-CI wird zusätzlich mit ihrem tatsächlichen Head/Testmerge und ihren
Run-Links im Draft-PR dokumentiert; ältere Main- oder Release-Läufe zählen nicht
als Nachweis dieser Änderung.

Der abschließende Main-/PR-Abgleich vor Erstellung bestätigte erneut `f8f61a11`.
Es gab keinen anderen offenen UI3-PR oder passenden Konsolidierungsbranch.
#90 und #187 bleiben getrennt; die vorhandenen Produkt-/Planimplementierungen,
`PendingNavigationGuard`, `JournalVersionSource`, `LessonDraftFromEvidence`,
Backendverträge, Versionsdateien und CI-Gates sind gegenüber dieser Basis unverändert.

| Ausgeführte Prüfung | Ergebnis und Grenze |
|---|---|
| `bash scripts/check-frontend.sh`, Node 22.16.0 / npm 10.9.2 | **1.009 Tests in 129 Dateien bestanden**, TypeScript, ESLint ohne Warnungen, Prettier und Produktionsbuild erfolgreich. Coverage: Statements/Lines **94,40 %**, Branches **87,78 %**, Functions **87,43 %**. Unveränderte Grenzen 80/80/80/70. |
| Darin: `LessonDetailPage.governance.test.tsx` | **22 Route-/Query-/POP-Tests** mit `createMemoryRouter` und `RouterProvider`, einschließlich synchronem Dirty-/Pending-Schutz und erhaltenem Formular bei fehlendem historischem Snapshot im Refresh. |
| Echter Chromium, synthetische HTTP-Fixtures | **4/4 bestanden in 6,9 Sekunden auf Commit `986f20a2`**. Vier Fälle bei 1440 × 1000 und 390 × 844, ohne Retry; kein PostgreSQL-Nachweis. |
| Betroffene Backend-Unit-/Vertragstests, Python 3.12.14 | **175/175 bestanden in 21,44 Sekunden auf Commit `986f20a2`**, eine bestehende Starlette/AnyIO-DeprecationWarning. 175 Fälle zu expliziten Befehlen/API, Lesson-Historie/Evidence, Quellenprüfung, Journal-API, Hypothesenübergabe und Owner-Testschutz. |
| Echte PostgreSQL-Integration und Journal-/Evidence-/Candidate-Ownerbrowser | Lokal nicht ausgeführt: Docker/PostgreSQL fehlen; die vorhandenen Owner-Runner verlangen einen tatsächlichen isolierten GitHub-Actions-Stack. Diese Prüfungen laufen über die unveränderte reguläre PR-CI, deren genaue Ergebnisse im PR ausgewiesen werden. |
| Diff-/Nachweisprüfung | `git diff --check`, lokale/entfernte Blob- und Tree-Identität sowie eng begrenzter Dokumentationsdiff geprüft. Historische Qualifikationsberichte unverändert. |

Die lokale Umgebung stellte zunächst Node 24 bereit. Dessen Request/AbortSignal-
Konflikt war auch in unveränderten Produkt-Guard-Tests reproduzierbar; der
maßgebliche Abschluss verwendet deshalb die festgelegte Node-Version 22.16.0.
Ein früher Vollgateversuch stoppte an zwei anschließend korrigierten
Testformatierungen. Ein weiterer Lauf hatte 1.007 erfolgreiche Fälle und einen
Timingfehler im unveränderten Produktauswahltest beim kanonischen Run-URL-Wechsel.
Dieser Test bestand anschließend einzeln und im vollständigen Abschlusslauf,
ohne Produktcode, Produkttests oder Assertions zu verändern. Diese Fehlversuche
werden nicht als erfolgreiche Gesamtprüfungen ausgegeben. Der Build meldet
weiterhin den bestehenden Hinweis auf große JavaScript-Chunks.

### Akzeptanzbezüge

| Fälle des Auftrags | Konkreter Nachweis |
|---|---|
| 1–4: eine Ansicht, Historie, ungültige Auswahl, URL/Reload/Zurück | Page- und Paneltests; Chromium für aktuelle/historische Version, Reload und POP. Kein zusätzlicher `getLesson`-Abruf. |
| 5–7: Vorbelegung, Ersetzen/Abbrechen, vollständiger Nachfolger | Panel-/Clienttests und Chromium mit SUPPORTS/CONTRADICTS/CONTEXTUAL; unveränderte alte Snapshots/Links; Pflichtbegründung, Eindeutigkeit und SUPPORTS-Regel. |
| 8–9: exakte Journalquelle und getrennte Aktualität | Herkunfts-/Statusregressionen, unveränderte Journal-Consumer-Tests, Chromium-Rücksprung auf ursprüngliches Journal trotz Nachfolger. |
| 10 und 13: Governance-Quelle und gleicher Versionskontext | Historische Hypothese bleibt zulässig; Refresh-/Fehler-/fehlender-Snapshot-Fälle behalten Titel/Text/Receipt bei gesperrten Befehlen. |
| 11–12: ungespeicherte und laufende Arbeit | Ein zentraler Guard, Bleiben/Verwerfen/exaktes Ziel, Browser-POP, native Unload-Prüfung und keine Verwerfen-Option während Writes. |
| 14–15: Retry, Konflikt, Receipt und Isolation | Panel-/Page-/Hypothesentests für Doppelsubmit, identischen versus geänderten Retry, bestätigten Write mit Readbackfehler, StrictMode, Unmount und A→B→A. |
| 16: zulässige Zustandsaktionen | CURRENT/REVIEW_RECOMMENDED/RETIRED, konkrete CONTRADICTS-Links, keine automatische Prüfung aus Quellenwarnungen. |
| 17: Bedienbarkeit | Tastaturöffnung der Quellen, Dialogfokus und unveränderte Eingaben; visuelle Kontrolle von Desktop und 390-Pixel-Ansicht. Keine vollständige menschliche Barrierefreiheitsabnahme behauptet. |

### Reproduzierbare Befehle

Vollständiger Frontendlauf im Repository-Stamm, mit der isoliert installierten
festgelegten Toolchain:

```bash
env PATH=/workspace/scratch/caccf9576ce2/ui3-tools/node_modules/.bin:$PATH \
  bash scripts/check-frontend.sh
```

Ausgeführter Build und Browserlauf aus `frontend/`, mit eigenem Ausgabeordner und
lokaler Vorschau. Sämtliche API-Antworten waren synthetisch abgefangen; unerwartete
API-/externe Requests und Browserfehler führen zum Testfehler:

```bash
PATH=/workspace/scratch/caccf9576ce2/ui3-tools/node_modules/.bin:$PATH \
VITE_API_BASE_URL=http://127.0.0.1:4183/api \
./node_modules/.bin/vite build \
  --outDir /workspace/scratch/caccf9576ce2/ui3-browser-dist

PATH=/workspace/scratch/caccf9576ce2/ui3-tools/node_modules/.bin:$PATH \
TMPDIR=/workspace/scratch/caccf9576ce2/browser-tmp \
PLAYWRIGHT_BROWSERS_PATH=/workspace/scratch/caccf9576ce2/playwright-browsers \
PLAYWRIGHT_BASE_URL=http://127.0.0.1:4183 \
E2E_VITE_API_BASE_URL=http://127.0.0.1:4183/api \
PLAYWRIGHT_JSON_OUTPUT_FILE=/workspace/scratch/caccf9576ce2/ui3-browser-final-results.json \
NODE_PATH=./node_modules \
./node_modules/.bin/playwright test lesson-detail-consolidation.spec.ts \
  --project=chromium --workers=1 --retries=0 --reporter=list,json \
  --trace=on --output=/workspace/scratch/caccf9576ce2/ui3-browser-final-results
```

Ausgeführter Backendlauf aus dem Repository-Stamm, Python 3.12.14 und unveränderte
Abhängigkeiten aus `backend/requirements-dev.txt`:

```bash
TMPDIR=/workspace/scratch/caccf9576ce2/browser-tmp \
PYTHONPATH=backend \
/workspace/scratch/caccf9576ce2/ui3-venv/bin/python -m pytest \
  -c backend/pyproject.toml \
  tests/unit/backend/features/learning/test_explicit_review_commands.py \
  tests/unit/backend/features/learning/test_explicit_review_api.py \
  tests/unit/backend/features/learning/test_lesson_evidence_read_service.py \
  tests/unit/backend/features/learning/test_lesson_history_api.py \
  tests/unit/backend/features/learning/test_lesson_review_resolutions.py \
  tests/unit/backend/features/learning/test_lesson_review_signal_service.py \
  tests/unit/backend/features/learning/test_evidence_source_inspection.py \
  tests/unit/backend/features/learning/test_learning_evidence_api.py \
  tests/unit/backend/features/learning/test_journal_api.py \
  tests/unit/backend/features/model/test_lesson_hypothesis_handoff.py \
  tests/unit/backend/test_journal_e2e_contracts.py
```

Die eingeschränkte Prozess-Sandbox verhinderte zunächst Chromium-Start und
FastAPI-TestClient-Abschluss. Diese unvollständigen Versuche zählen nicht als
Erfolg. Die genannten erfolgreichen Läufe nutzten dieselben isolierten
Testmechanismen außerhalb dieser Prozessbeschränkung. Desktop-/Schmalansicht-
Screenshots und Chromium-Traces wurden erzeugt; die Screenshots wurden visuell
geprüft. Der lokale Vorschauprozess wurde anschließend beendet.

Die historischen [Journal-](FT012_JOURNAL_WRITE_QUALIFICATION.md) und
[Lesson-Qualifikationen](FT012_LESSON_REVIEW_QUALIFICATION.md) bleiben als Belege
ihrer eigenen Commits erhalten.

## Verbleibende Grenzen

Allgemeine Titel-/Tagfunktionen, RETIRED-Reaktivierung, die eigene #90-Übergabe,
#187, allgemeine Plan-DRAFT-Revision, finanzielle Berechnungen und neue
Backend-Lebenszyklen sind nicht Bestandteil dieser Konsolidierung. Der Browsercheck
mit schmalem Viewport ersetzt keine vollständige menschliche Mobil-/Barrierefreiheits-
oder Fachabnahme. Es werden keine echte Handels-/Modellaktion, Providerzustimmung,
Nachricht, neue Migration, Versionserhöhung oder PC-Installation als Ergebnis
dieses Auftrags ausgewiesen.
