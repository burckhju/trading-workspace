# UX4-D — Implementierungsumfang und Nachweisgrenzen

## Auftrag, Basis und Nachweisgrenze

Stand: **06.11.2026, UTC**. Der vorhandene [Draft #330](https://github.com/burckhju/trading-workspace/pull/330)
wird auf `feat/ux4-d-quality-lifecycle-20261105` fortgeführt. D1–D4 sind in den
bestehenden fachlokalen Renderern implementiert und durch gezielte Tests ergänzt.
Das ist keine menschliche Fachabnahme oder Integration. Die exakten veröffentlichten
Head-/Testmerge-SHAs, CI-Läufe, Browserartefakte und Ergebnisse werden in #330 an den
jeweiligen Head gebunden; ein älterer grüner Vorbereitungslauf gilt dafür nicht.
Fachliche Aufgabenstände bleiben im
[Product Backlog](../planning/PRODUCT_BACKLOG.md).

| Bezug | Geprüfter Stand |
| --- | --- |
| Tatsächlicher Main | `7bfe1bfa13ec158ec380aa6f5d3c7f480838f5e8` |
| Versionsdateien / veröffentlichter Git-Tag | Unverändert `1.5.41` / `v1.5.41`; daraus folgt kein Installationsbeleg |
| Übernommener D-Draft | `67af2c8c43d92c0cd6d14412f58b3c4129f1eec6`, zunächst 17 Commits hinter Main und einen voraus; ausschließlich zwei Dokumentdateien |
| Main-Integration | Konfliktfreier regulärer Merge `5d1916b548dcf483f341d6b0098aa80d198521f2`; kein Reset und keine Übernahme offener Featurebranches |
| UX4-C | [PR #327](https://github.com/burckhju/trading-workspace/pull/327), Draft-Head `79760e9cf40cef6c6e58d8b15b6849a3056cc5c8`, beim Start 17 Commits hinter Main; seine historische technische Qualifikation ist kein Nachweis gegen den neuen Main |
| Reviews beim Start | Keine Reviews, offenen Threads oder angeforderten Reviewer an #330; keine persönliche Ownerabnahme daraus ableiten |
| Grenzen | Draft bleibt Draft; kein Merge, Release, Tag, Deployment oder PC-Update |

Die Vorbereitung vom 05.11.2026 beruhte auf Main `e4921d6e25b70baddb80d4eaaf61028bb055ad04`
und Version `1.5.40`. Die damaligen zwei Dokumentänderungen sind Teil derselben
PR-Historie. Beim erneuten Abgleich am 06.11.2026 überschneiden sich die vollständigen
Dateilisten der offenen #327/#315/#220/#207/#205/#197/#187 nicht mit den vier
lokalen D-Renderern und deren Typ-/Testdateien. UX2-B #325 ist inzwischen integriert.
Das ist ein technischer Abgleich, keine persönliche UX1-/UX2-/UX3-/Domainfreigabe.

## 1. Implementierter lokaler Produktumfang

### Erfassungsprotokoll und historische Quellen

Begrenzter D1-Schnitt:
[`WarrantQuoteHistory.tsx`](../../frontend/src/features/product/components/WarrantQuoteHistory.tsx)
und dessen vorhandene Tests. Die Daten kommen über
[`dataEvidenceApi.history`](../../frontend/src/features/product/services/dataEvidence.ts)
aus dem bestehenden
[`QuoteHistoryReader`](../../backend/app/features/market_data/service/quote_history.py).

- Die drei bereits gelieferten Zähler `sampled_slots`, `distinct_quote_evidence`
  und `observed_utc_days` mit ihren unterschiedlichen Einheiten nebeneinander
  zeigen. `statuses` enthält vorhandene absolute Statuszahlen. Nichts addieren,
  normalisieren oder als gemeinsame Qualitätsquote ausgeben.
- Jedes Segment bleibt an `provider`, `identity_key` und `isin` gebunden.
  `first_capture_at`/`last_capture_at` sind Erfassungszeiten, keine Kurshistoriengrenzen.
- Das angefragte `window_start`/`window_end` begrenzt Zähler und Details. Die
  Detailauswahl enthält höchstens `item_limit=50` Beobachtungen dieses Fensters
  über alle Segmente. `collection_started_at` ist die erste bekannte Produkterfassung
  bis zum Prüfzeitpunkt und darf vor dem Fenster liegen.
- Originalbelege behalten `captured_at`, `slot_at`, `retrieved_at`,
  `quote.observed_at`, `status`, `reason`, `cache_status`, Preisart und Währung.
  Eine wiederholte Erfassung eines alten Kurses ist kein neuer Originalkurs.
- Eine semantische Tabelle oder gleichwertige Liste ergänzt die vorhandenen
  Details. Öffnen/Filtern/Fokussieren startet keinen zusätzlichen Read;
  „Gespeichertes Protokoll laden“ bleibt der ausdrückliche vorhandene Lesevorgang.

Die Backendantwort enthält außerdem `sampling_policy`, `time_coverage_percent`,
`iv_history_available`, `underlying_synchronization_available`, `execution_usable`
und je Item `quote_fingerprint`. Der additive
[`QuoteHistoryReport`-Frontendtyp](../../frontend/src/features/product/types/dataEvidence.ts)
bildet die verwendeten Felder optional gegen die reale Payload ab und akzeptiert
ältere Antworten mit fehlenden Feldern. `time_coverage_percent=null`
bleibt unbekannt; keine neue Frische-, Kalender-, IV- oder Zeitabdeckungsrechnung.

### Aktuelle Kursqualität und fehlende Kurs-/Quelleninformationen

Fachlokaler Schnitt:
[`QuoteCoveragePanel.tsx`](../../frontend/src/features/operational_workspace/pages/QuoteCoveragePanel.tsx)
mit unverändertem
[`QuoteCoverageService`](../../backend/app/features/market_data/service/quote_coverage.py).

Die Antwort enthält Produkte und Routen, **keine serverseitige Qualitätssummary**.
Die bestehende Zahl `report.items.length` beschreibt die gelieferte Produktliste;
sie ist keine Backendqualitätsquote. Es entsteht keine neue Statussumme aus Routen.
Zwei Positionen desselben Produkts werden nicht zu zwei Produkten umgedeutet.

Darstellung je Route: `provider`, `listing_id`, `mapping_status`, `provider_identity`,
`provider_exchange_code`, `validated_at`, `configured`, `route_reason`,
`observation_status`, Bid/Ask/Referenz, `observed_at`, `retrieved_at`, `age_seconds`,
`feed_delay_seconds`, `trading_status` und `refresh_error`. Produkt-`coverage` und
die separaten `refresh_jobs` behalten ihre eigene Bedeutung. Gelieferte Alterswerte
anzeigen, nicht aus `Date.now()` neu berechnen. Eine aktuelle Quelle B heilt weder
die gebundene Identität noch den Fehler einer Quelle A.

Additiv im lokalen Frontendtyp aus vorhandenen Serverfeldern abgebildet:
`assessment_scope=STORED_OBSERVATIONS_NOT_LIVE_VALUATION`, `execution_usable=false`,
`mapping_id`, `max_quote_age_seconds`, `quote_time_text` und `quote_time_basis`.
Eine unbekannte Zone im Originalzeittext darf nicht zu einem erfundenen Instant
werden. Bestehende Produkt-/Emittentenfilter bleiben lokale Darstellungsaktionen.

### Providerdiagnostik und Zeitbezug

Fachlokale `RefreshDiagnostics` in
[`MarketDataRefreshPanel.tsx`](../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx)
gliedert bereits gelieferte Informationen aus
[`refresh_diagnostics.py`](../../backend/app/features/market_data/service/refresh_diagnostics.py)
und [`refresh_quality.py`](../../backend/app/features/market_data/service/refresh_quality.py).

Aktuellen Versuch (`job.execution.running/started_at/elapsed_seconds`), letzten
abgeschlossenen Check, Fehlerfolge, gespeicherten Kurs und Providerantwort getrennt
zeigen. `provider_reachable`, `response_valid` und `quote_usable` unterscheiden
`true`, `false` und fehlend/null. `qualified_success` allein beweist keinen neuen
Netzkontakt. `retained_quote`, Cache und Deferral sind keine Providererholung.

Die vorhandenen `consecutive_failures`, `first_failure_at`, `last_failure_at`,
`last_success_at`, `recovered_at`, `last_checked_at` und `observed_in_latest_run`
werden nicht neu qualifiziert. `PROCESS_LOCAL` bleibt prozesslokale Diagnose,
kein Uptimeverlauf. Keine neue Recovery- oder Hinweispolicy und kein zusätzlicher
Refresh-/Health-/Provideraufruf durch Details oder lokale Gliederung.

### Analyse → Plan → Ausführung → Position → Journal → Lesson

Die bestehende
[`TradeSourcesView.tsx`](../../frontend/src/features/trade/components/TradeSourcesView.tsx)
ist die einzige erste Darstellungsfläche. Ihre lokalen Renderer erhalten bereits
qualifizierte Daten über `ReadSection<T>` und
[`SourceSnapshot<T>`](../../frontend/src/features/trade/services/sourceView.ts).
Die Orientierungsreihenfolge ist kein Pflichtprozess und kein neuer Fachzustand.

| Abschnitt | Vorhandener Beleg | Unveränderte Aussagegrenze |
| --- | --- | --- |
| Analyse / Kandidat | `PlanSource.candidate_evaluation`: Kandidat-/Evaluation-ID und Version, Modell, `qualification`, `quality_status`, `evaluated_at`, `sources[]` mit Typ, ID, numerischer Version und Rolle | Manueller Plan ohne Analyse ist zulässig. Generische Quellenreferenz ist kein beliebiger Analyselink und kein Beleg „Analyse abgeschlossen“. |
| Plan | `plan`, exakt gebundene `version`, eigenes `approval`, `events` | EXTERNAL kann ohne ursprünglichen Plan existieren. Planfreigabe und tatsächlicher Kauf bleiben getrennt. |
| Ausführung | `TradeSourceCore.timeline`, Wirksamkeit/Korrekturbezug, Originalzeitpräzision, Währung und Preisbindung | Ersetzte Quellen bleiben historisch; Storno ist kein SELL. DATE_ONLY erzeugt keine Uhrzeit; `recorded_at` ist keine Ausführungszeit. Keine Summen-/Abschlussneuberechnung. |
| Position | Geliefertes `state` und `open_quantity` im Core-Lesefenster | `UNKNOWN` und `null` bleiben unbekannt. Core enthält keine vollständige Position und keine Positions-ID; keinen exakten Positionsobjektlink erfinden. |
| Review / Journal | Eigene `history`/`selected`, DRAFT/FINALIZED, gespeicherte Currentness, heutige `source_currentness` mit `checked_at`; Journal mit `edit_revision` | DRAFT kann CURRENT, FINALIZED kann STALE sein. Ein finales leeres Journal ist kein Urteil über vollständige Reflexion. |
| Evidence / Lesson | Evidence-ID/-Zeit/-Typ, Review-/Journalversionsbezug, `source_bound`, genaue Lessonversionslinks und Relation | Historische Existenz, aktuelle Bindung und aktuelle Materialisierungsbereitschaft sind verschieden. Kein Lessonreviewstatus geliefert; Relation ist keine Freigabe. |

Es bleiben genau die bestehenden fünf Source-Reads mit eigenen Lade-/Fehler-/Retry-
und Abbruchgrenzen: Core, Plan, Review, Journal, Evidence. Nachgeordnete Abschnitte
werden erst nach erfolgreichem Core gelesen. Ein noch nicht gelesener Abschnitt,
ein fehlgeschlagener Read, eine bestätigte leere Antwort und ein existierender
Beleg mit unbekannter Currentness sind verschiedene Fälle. Eigene
`read_started_at`/`read_completed_at` bleiben sichtbar; kein gemeinsamer atomarer
Snapshot wird behauptet. Die bereits bedingt vorhandene Performancequellenansicht
behält ihren bisherigen Readvertrag.

Native Details, Listen/Tabellen und die vorhandenen Plan-/Review-/Journal-/Lessonlinks
verbessern. `trade_id`, `review_version_id`, `journal_version_id` und Rückkontext
erhalten. Falsche/doppelte/fremde Pins bleiben Fehler ohne Latest-Fallback. Die
[`TradeSourceReader`-Budgets](../../backend/app/features/trade_position/service/source_view.py)
und separaten read-only Transaktionen bleiben unverändert; kein abgeschnittener Erfolg.

`Ft011EvidenceHistory`, `JournalEvidenceOrigin` und `EvidenceSourceStatus` besitzen
eigene Reads. Sie werden hier nicht zusätzlich gemountet. Für eine rein optische
Gliederung vorhandene Daten/Renderprops verwenden; keine zweite Lese- oder Statusengine.

## 2. Ownergrenzen und konkret zurückgestellte Integration

| Zuständigkeit | Erhaltene Grenze / konkrete Voraussetzung |
| --- | --- |
| UX-1 | Eingaben, Entwurf, Vorbelegung, Währungs-/Quellenbestätigung und ihre Fachvalidatoren bleiben unverändert. Ein angezeigter Beleg erzeugt keine Bestätigung. |
| UX-2 | `TradeManagementPage`, gemeinsame Navigation, Readback, Invalidierung und Fokusziele bleiben beim Hostowner. Sein Abschnitt UX2-D besitzt bereits den geplanten gemeinsamen Lifecycle-Überblick. |
| UX-3 | Aktueller kanonischer Hinweisvertrag und enger B1-Renderer; keine globale Statusunion oder eigene Recovery-/Schweregradpolicy. B2-Produktbewertung/PositionDetails und vorbereiteter B3/M06-Alerttext sind keine ersten D-Schreibflächen. |
| Fachowner | Finanz-, Kurs-, Provider-, Währungs-, Frische-, Quellen- und Lebenszyklusqualifikation bleiben vollständig beim bestehenden Backend-/Readerowner. |

UX2-B #325 ist im geprüften Main integriert. `TradeManagementPage`, `pages/index.ts`,
`ProductValuationPanel` und gemeinsame Navigationsdateien werden von UX4-D nicht
geändert. Bestehende Hostanker, Versionspins und Readergrenzen werden erhalten.
Eine fehlende Schreibüberschneidung ersetzt dennoch keine UX2-Zustimmung zu einem
zukünftigen neuen Einbauvertrag.

Für folgende Ausbauten liegt **kein neuer Einbauvertrag** vor; sie werden hier nicht
als freigegebene Produktänderung aufgenommen:

- **Positionscoverage als neue Oberfläche.** Der vorhandene
  [`PositionQuoteCoverageService`](../../backend/app/features/market_data/service/position_quote_coverage.py)
  liefert echte Summaryzähler, aber es gibt noch keinen Frontendverbraucher.
  Vor einem Einbau braucht UX-2 Slot, Props, Readowner, Invalidierung und Fokusziele.
  `bound_positions`, `source_verified` und Healthgruppen sind überlappende Sichten;
  `missing_source` enthält bereits Teilgruppen. Keine neue Gesamtquote oder 100-%-Grafik.
- **Gemeinsamer Lifecycle-Überblick und neue Rückwege.** Vorhandene Analyseversionsroute
  `/market-analyses/:analysisId?version=N` nur mit belegtem Quellentyp/ID/Version
  verwenden. Ein neuer Trade → Analyse → Trade-Rückkontext ist noch kein vereinbarter
  Navigationsvertrag. Die erste lokale Liste zeigt die Provenance und behält den
  bestehenden gebundenen Planlink. Ein Buchungsanker ist kein Execution-Fokusziel.
- **Featureübergreifender Refresh-/Coverage-Vertrag.** `RefreshCheck`, `RefreshStatus`
  und Coverage-Typen sind lokal/private. Der öffentliche B1-Renderer löst diese
  O3-Grenze nicht. Keine kopierten Statusunionen, internen Querimporte oder bloßen
  Reexport-Barrels als Ersatz für den Market-Data-/UX2-Vertrag.

## 3. Dateien und tatsächliche spätere Abnahme

Der tatsächliche Produktdiff besteht aus den vier lokalen Renderern, dem additiv
erweiterten Historytyp und den vier dazugehörigen Unit-/Integrationstestdateien.
Zusätzlich kommen die beiden Browser-Specs `tests/e2e/ux4-d-quality.spec.ts` und
`tests/e2e/ux4-d-lifecycle.spec.ts` sowie ihr gemeinsamer Helper
`tests/e2e/support/ux4-native-zoom.ts` hinzu. Die Backendtests und vorhandenen
Ownerbrowsertests in der folgenden Tabelle bleiben unverändert:

| Schnitt | Produktfläche | Bestehende gezielte Testanker |
| --- | --- | --- |
| Erfassungsprotokoll | `product/components/WarrantQuoteHistory.tsx`; `product/types/dataEvidence.ts` | `WarrantQuoteHistory.test.tsx`, Backend `test_quote_history.py` |
| Produktquellen | `operational_workspace/pages/QuoteCoveragePanel.tsx` | `QuoteCoveragePanel.test.tsx`, `test_held_quote_coverage_api.py`, Browser `quote-coverage.spec.ts` |
| Refreshdiagnostik | lokale `RefreshDiagnostics` in `MarketDataRefreshPanel.tsx` | `MarketDataRefreshPanel.diagnostics.test.tsx`, `test_refresh_identity_evidence.py`, `test_refresh_diagnostics_api.py` |
| Historische Belegliste | `trade/components/TradeSourcesView.tsx` | `TradeSourcesView.test.tsx`, `test_source_view.py`, `test_trade_source_view_postgres.py`, Browser `post-trade-handoff-pin.spec.ts` und `post-trade-evidence-history-postgres.spec.ts` |

Frontendpfade beginnen mit `frontend/src/features/`. Keine neue gemeinsame
Hostkomponente, Backendroute, Persistenz, Migration, Dependency, Finanzformel oder
Statusmaschine gehört zu dieser Folge.

Für den veröffentlichten Runtime-Head nachweisen:

1. Getrennte Populationen/Einheiten; echte Null versus fehlend; unbekannte Codes
   ohne Entwarnung oder erfundene Ursache; keine lokal erzeugten Qualitätszahlen.
2. Originalzeit, Abrufzeit, Erfassungszeit und Prüfzeit; unbekannte Zone/DATE_ONLY
   ohne Instant; Kurs-/Quellenlücke, Cache, Retention und Providererfolg getrennt.
3. Historyfenster und globale 50-Item-Grenze über Segmente; keine erfundene
   Handelszeitabdeckung, keine Vermischung heutiger Qualität mit historischem Beleg.
4. Manueller Plan, EXTERNAL ohne Plan, Storno/Korrektur, UNKNOWN/null-Position,
   DRAFT/CURRENT, FINALIZED/STALE, finales leeres Journal und historische Evidence.
5. Exakte Pins/Links, eigene Lesefenster, A→B→A, alte Erfolge und Fehler,
   abschnittsbezogener Retry, keine Mehrreads durch Aufklappen/Filter/Hashnavigation.
6. Tatsächliche Browsernachweise bei 320/390/1280 CSS-Pixeln und nativem 200/400-%-Zoom,
   Tastatur, sichtbarem Fokus, semantischen Alternativen und begrenztem Tabellenscroll.
7. Unveränderte reguläre CI und relevante Ownerregressionen am genauen Head;
   nicht ausgeführte oder übersprungene Fälle ausdrücklich benennen.

### Ausführbare Browser- und Accessibility-Nachweise

Die zwei neuen Specs benutzen die echten bestehenden Hosts `/warrants-admin`,
`/workspace` und `/trade-management` mit synthetischen, strikt abgefangenen
API-Antworten. Sie lösen keine Providerabfragen oder Schreibvorgänge aus. Die
18 Browserfälle umfassen D1–D4 jeweils bei 320, 390 und 1280 CSS-Pixeln, vier
native Zoomfälle mit jeweils 200 und 400 Prozent sowie zwei zusätzliche
Lifecyclefälle für getrennte Lade-/Fehler-/Retry- und Leerzustände.

Die Zoomfälle verwenden Chromiums `chrome.tabs.setZoom/getZoom` über eine reine
Testextension. Angeforderter und tatsächlich gelesener Faktor, `innerWidth`,
`devicePixelRatio`, CSS-Zoom und Dokumentbreite werden protokolliert; CSS-Zoom
oder ein bloß verkleinertes Viewport ersetzt diesen Nachweis nicht. JSON,
Screenshots und Accessibility-Snapshots werden am jeweiligen Test angehängt.
Die Matrix prüft Enter/Space für native Details, Tab/Shift+Tab, fokussierbare
Tabellenbereiche, erhaltene Pins und Readbudgets. Konkrete Text-/Fokusfarbproben
prüfen mindestens 4,5:1 beziehungsweise 3:1; das ist keine vollständige
WCAG- oder Screenreader-Zertifizierung.

Die lokale Ausführungsumgebung kann Chromium wegen ihrer Prozess-/Dateisystemgrenzen
nicht starten. Auch Vitest meldet hier erfolgreiche einzelne Dateien, beendet
seinen Prozess aber nicht zuverlässig. Diese Ausgaben werden ausdrücklich nicht
als vollständiger grüner Gateabschluss gezählt. Die unveränderte reguläre CI auf
dem veröffentlichten PR-Head ist für die Laufqualifikation maßgeblich.

Menschliche UX-/Domain-/Screenreader-/Touchabnahme und repräsentative Nutzerdaten
bleiben gesondert offen. Synthetische Browserbelege belegen Darstellung und
Leseverträge, nicht die fachliche Repräsentativität echter Nutzerdaten.

## 4. Veröffentlichung und Übergabe

#330 bleibt der einzige UX4-D-Draft. Vor dem Push Remote-Main, Remote-Head,
Branchrückstand und Reviews erneut prüfen; keine fremden Änderungen überschreiben.
Nach dem Push müssen alle regulären Prüfjobs auf demselben Head beziehungsweise
seinem belegten Testmerge vollständig laufen. Genaue D-Head-/Basis-/Diff-, Testzahl-,
CI- und Browsernachweise sowie offene fachliche Abnahmen stehen in der
PR-Beschreibung. Dokumentiert, implementiert, getestet, menschlich abgenommen und
integriert bleiben getrennte Aussagen.

Dieser Auftrag erteilt keine Merge-, Release-, Tag-, Deployment- oder PC-Freigabe.
