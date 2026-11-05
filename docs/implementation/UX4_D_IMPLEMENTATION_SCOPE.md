# UX4-D — Vorbereiteter Implementierungsumfang

## Auftrag, Basis und Nachweisgrenze

Stand: **05.11.2026, Europe/Berlin**. Dieser Vorbereitungs-Draft aktualisiert den
[UX4-D-Startprompt](../ui/ux4-d-quality-lifecycle-prompt.md) und bindet die spätere
Darstellung an vorhandene Daten, Dateien und Owner. Er enthält **keine Runtime- oder
Teständerung** und erklärt UX4-D nicht für implementiert, fachlich abgenommen oder
integriert. Fachliche Aufgabenstände bleiben im
[Product Backlog](../planning/PRODUCT_BACKLOG.md).

| Bezug | Geprüfter Stand |
| --- | --- |
| Tatsächlicher Main | `e4921d6e25b70baddb80d4eaaf61028bb055ad04` |
| Main-Tree | `ff0dc79a4ee679eb9803e89d96d560b0e12d5470` |
| Versionsdateien / veröffentlichter Git-Tag | `1.5.40` / `v1.5.40`, Tag zeigt auf den genannten Main; daraus folgt kein Installationsbeleg |
| Eigener Implementierungsbranch | `feat/ux4-d-quality-lifecycle-20261105`, direkt aus Main |
| UX4-C | [PR #327](https://github.com/burckhju/trading-workspace/pull/327), aktueller Head `79760e9cf40cef6c6e58d8b15b6849a3056cc5c8`; genaue finale CI dort gebunden |
| Erfüllte Vorbedingung der D-Veröffentlichung | Vollständiger erneuter C-CI-Abschluss auf diesem Head und Main, vier Workflows / neun ausgeführte Prüfjobs erfolgreich; Draft bleibt getrennt von C und übernimmt keine offenen Featurecommits |
| D-Runtime / menschliche Abnahme | Noch nicht ausgeführt; die nachstehenden Fälle sind verbindliche spätere Prüfungen |

Die erste aktualisierte C-Produktbasis `a68b3a92…` wurde mit allen neun Prüfjobs
erfolgreich qualifiziert. Danach ergänzte #329 ausschließlich Versionsmetadaten
und UX3-Dokumentation. Der erneute vollständige C-Nachweis ist abgeschlossen und
gehört ausdrücklich zum neuen Head: [Backend](https://github.com/burckhju/trading-workspace/actions/runs/42110490344),
[Frontend](https://github.com/burckhju/trading-workspace/actions/runs/42110490324),
[E2E](https://github.com/burckhju/trading-workspace/actions/runs/42110490287) und
[Releaseguards](https://github.com/burckhju/trading-workspace/actions/runs/42110490758)
waren im jeweils ersten Versuch erfolgreich. Der PR-Tagjob war bestimmungsgemäß
übersprungen. Testmerge `0b54de55654d06e3bced587876c24e8d00470a2d` und Head haben
denselben Tree `1b8f42b79cc28778f3808dd99b39ede8549626e9`. Frühere grüne Läufe
ersetzen diesen Nachweis nicht. C bleibt Draft und wird durch diesen D-Auftrag
weder gemergt noch freigegeben.

Die aktuelle Branchsuche und PR-Suche ergaben vor dieser Vorbereitung keinen
eigenständigen begonnenen UX4-D-Schnitt. Die vollständigen Dateilisten der offenen
#327/#325/#315/#220/#207/#205/#197/#187 wurden verglichen: keine Überschneidung mit
den beiden Dokumentdateien dieses Drafts oder den vier unten vorgeschlagenen
lokalen Renderern. Das ist ein technischer Abgleich, keine persönliche
UX1-/UX2-/UX3-/Domainfreigabe.

## 1. Konkreter lokaler Produktumfang für die spätere Umsetzung

### Erfassungsprotokoll und historische Quellen

Erster begrenzter Schnitt:
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
und je Item `quote_fingerprint`. Der aktuelle schmale
[`QuoteHistoryReport`-Frontendtyp](../../frontend/src/features/product/types/dataEvidence.ts)
bildet sie noch nicht alle ab. Nur bei tatsächlicher Nutzung additiv gegen die
reale Payload und ältere/fehlende Felder typisieren. `time_coverage_percent=null`
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

Bereits serverseitig vorhanden, aber im schmalen Frontendtyp noch nicht vollständig:
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

Der offene UX2-B #325 an `555538fa0519cd31e6d5391dd938a8150c90ac3d` ändert 22 Dateien,
insbesondere `TradeManagementPage`, `pages/index.ts`, `ProductValuationPanel` und
zugehörige Tests. Die vier lokalen D-Renderer überschneiden sich damit nicht.
Eine fehlende Schreibüberschneidung ersetzt dennoch keine UX2-Zustimmung.

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

Die jetzige Vorbereitung ändert nur diesen Umfang und den Startprompt. Die
folgenden Produkt- und Testdateien sind **geplante spätere Änderungen**, keine
aktuelle Dateireservierung oder bereits ausgeführte Tests:

| Schnitt | Produktfläche | Bestehende gezielte Testanker |
| --- | --- | --- |
| Erfassungsprotokoll | `product/components/WarrantQuoteHistory.tsx`; nur bei benötigten vorhandenen Payloadfeldern `product/types/dataEvidence.ts` | `WarrantQuoteHistory.test.tsx`, Backend `test_quote_history.py` |
| Produktquellen | `operational_workspace/pages/QuoteCoveragePanel.tsx` | `QuoteCoveragePanel.test.tsx`, `test_held_quote_coverage_api.py`, Browser `quote-coverage.spec.ts` |
| Refreshdiagnostik | lokale `RefreshDiagnostics` in `MarketDataRefreshPanel.tsx` | `MarketDataRefreshPanel.diagnostics.test.tsx`, `test_refresh_identity_evidence.py`, `test_refresh_diagnostics_api.py` |
| Historische Belegliste | `trade/components/TradeSourcesView.tsx`, gegebenenfalls fachlokale reine Renderer | `TradeSourcesView.test.tsx`, `test_source_view.py`, `test_trade_source_view_postgres.py`, Browser `post-trade-handoff-pin.spec.ts` und `post-trade-evidence-history-postgres.spec.ts` |

Frontendpfade beginnen mit `frontend/src/features/`. Keine neue gemeinsame
Hostkomponente, Backendroute, Persistenz, Migration, Dependency, Finanzformel oder
Statusmaschine gehört zu dieser Folge.

Für den tatsächlichen späteren Runtime-Head nachweisen:

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

Menschliche UX-/Domain-/Screenreader-/Touchabnahme und repräsentative Nutzerdaten
bleiben gesondert offen. C-Screenshots oder ein erfolgreicher Dokumentationslauf
sind keine Belege für eine zukünftige D-Oberfläche.

## 4. Veröffentlichung dieses Vorbereitungsstands

Vor Erstellung des eigenständigen Drafts Main, C-Head, Reviews, CI, Branchrückstand
und konkurrierende D-/UX-Arbeiten erneut prüfen. Die zweite vollständige C-CI muss
abgeschlossen sein. Dann diesen vorbereiteten Stand auf dem oben genannten
Implementierungsbranch veröffentlichen; genaue D-Head-/Basis-/Diff- und Prüfbelege
in der PR-Beschreibung führen. Dokumentiert, implementiert, getestet, menschlich
abgenommen und integriert bleiben getrennte Aussagen.

Dieser Auftrag erteilt keine Merge-, Release-, Tag-, Deployment- oder PC-Freigabe.
