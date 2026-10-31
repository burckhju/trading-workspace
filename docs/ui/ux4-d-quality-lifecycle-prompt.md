# UX4-D — Startprompt: Datenqualität und Trade-Lebenszyklus

| Feld | Stand |
| --- | --- |
| Dokumenttyp / Version | Eigenständiger Implementierungsauftrag, 0.1 |
| Status | Draft; keine Implementierungs- oder Integrationsabnahme |
| Datum | 31.10.2026, Europe/Vienna |
| Historische Referenz / geprüfter Main | `1883f7f330719453958f8be1dd51d48db816662e`, `v1.5.35` |
| Voraussetzung | Aktuellen Main, Fachverträge und UX-1/2/3-Koordination beim Start erneut prüfen |
| Ergebnis | Eigenständiger Draft-PR mit Darstellung, tatsächlichen Prüfnachweisen und offenen Voraussetzungen |
| Freigabegrenze | Kein Merge, Release oder PC-Update ohne gesonderte Freigabe |

## Auftrag

Du verantwortest UX4-D im Repository `burckhju/trading-workspace`.
Verbessere die Darstellung vorhandener Datenqualitätsinformationen und
historischer Tradebelege. Verwende **absolute, bereits gelieferte Qualitätszähler**
und eine **referenzierte Belegliste** für Analyse → Plan → Ausführung → Position
→ Review/Journal → Lesson. Diese Reihenfolge dient der Orientierung und ist
kein vorgeschriebener, vollständig abzuarbeitender Prozess.

UX4-D entwickelt keine Finanz-, Frische-, Qualitäts- oder Lebenszyklusberechnung.
Die Fach-Owner liefern Werte, Einheiten, Identitäten, Status und Gründe. UX-4
gestaltet ihre lesbare, mobile und mit Tastatur bedienbare Darstellung.

Der Auftrag ist unabhängig von einer Umsetzung von UX4-B und UX4-C bearbeitbar.
Er setzt die [Inventur](ux4-visualization-inventory.md), den
[Visualisierungsvertrag](ux4-visualization-contract.md), insbesondere V01–V04
und V10–V14, sowie die [Prüfplanung](../implementation/UX4_A_QUALIFICATION.md)
voraus. Er erlaubt keine gemeinsame Workspace-Integration vor der konkreten
Abstimmung mit UX-2.

### Gelesener UX-3-Koordinationsstand

[UX-3-Draft #314](https://github.com/burckhju/trading-workspace/pull/314) wurde am
31.10.2026 am exakten Head `52a24266dce1ec048b23360b4b75d5b3f54d746b` gelesen:
[Hinweisvertrag](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/notice-contract.md),
[Komponenten und Aktionen](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/components-and-actions.md),
[Integration und Folgearbeiten](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/integration-and-rollout.md)
und [Übersicht](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/README.md).
Diese Dokumentation schlägt Hinweissprache und View-Props vor. `NoticeCard`,
`NoticeSummary`, `NoticeDetails`, `ContextActionLink` und `NoticeStatus` sind
**keine vorhandenen produktiven Komponenten** und kein bereits abgestimmter
Importvertrag. UX4-D baut weder eine zweite Notice-Schicht noch einen globalen
Hinweisspeicher; es bleibt Consumer der abgestimmten Qualitätsdarstellung.

Die Planungskürzel UX3-F3/F4/F7/F8 berühren Refreshdiagnostik, Kursqualität,
historische Quellen und lokale Zusammenfassungen. Sie reservieren keine Dateien
und geben keine Integrationsreihenfolge frei. Bei derselben Fläche stimmen
UX-3, Fachowner und UX-2 den konkreten Schnitt ab. Fachlich lokale Arbeit an
Zählern und Belegen wartet nicht pauschal auf alle UX-3-Folgearbeiten.

## 1. Vor Beginn prüfen

1. Ermittle den tatsächlichen Remote-Main, Commit, Tag und Versionsdateien.
   Vergleiche die betroffenen Pfade mit der historischen Referenz oben. Nenne
   relevante Änderungen; behandle den Referenzcommit nicht automatisch als
   weiterhin aktuellen Main. Arbeite auf einem eigenen Branch oder isolierten
   Worktree und übernimm keine parallelen Feature-Branches durch Merge.
2. Lies vorhandene `AGENTS.md`, README, [Product Backlog](../planning/PRODUCT_BACKLOG.md),
   [Frontendarchitektur](../architecture/FRONTEND_ARCHITECTURE.md),
   [Backendarchitektur](../architecture/BACKEND_ARCHITECTURE.md),
   [Development Guide](../technical/DEVELOPMENT_GUIDE.md) und
   [Teststrategie](../reference/TEST_STRATEGY.md). Lies die tatsächlichen
   Master-Lead-Koordinationsdokumente und aktuellen UX-1/2/3-Verträge; die
   Inventur nennt die gelesenen parallelen Dokumentationsheads. Deren
   Verfügbarkeit belegt noch keine fachliche Abnahme oder Integrationsfreigabe.
3. Prüfe die folgenden Komponenten, DTOs, Reader und Tests erneut. Stelle fest,
   welche Anzeige bereits existiert und welche Fähigkeit nur als API vorhanden
   ist. Ein Dokumentations- oder Forschungs-PR beweist keine Runtimefähigkeit.
4. Halte mit UX-2 Einbindungsstelle, Props, Readowner, Read-Lebensdauer,
   Invalidierung, Navigation, Anker und gemeinsam betroffene Dateien fest.
   Bereite bis dahin fachlich lokale Verbesserungen und konkrete Ansichten vor;
   ändere keine gemeinsamen Workspace-Komponenten oder deren Navigation.

## 2. Vorhandene Anzeigen und Quellenowner

Die Endpunkte in der Tabelle haben den Präfix `/api/v1`. Verifiziere beim Start
den tatsächlichen Stand; ergänze weder neue Provideradapter noch neue Fach-APIs.

| Bereich / vorhandene Anzeige | Datenquelle und Owner | Zulässige Arbeit |
| --- | --- | --- |
| Gehaltene Optionsscheine: [QuoteCoveragePanel](../../frontend/src/features/operational_workspace/pages/QuoteCoveragePanel.tsx) | `/market-data/warrants/quote-coverage`; [QuoteCoverageService](../../backend/app/features/market_data/service/quote_coverage.py) und persistierte Quellenbelege | Absolute Zähler, Produktpopulation, Route, Identität, Preisart, Währung und Qualitätsgründe klarer gliedern; vorhandene Filter und Details erhalten. |
| Offene Positionen: im geprüften Main API ohne eigenen Frontendverbraucher | `/market-data/positions/quote-coverage`; [PositionQuoteCoverageService](../../backend/app/features/market_data/service/position_quote_coverage.py), [Repository](../../backend/app/features/market_data/persistence/position_quote_coverage.py) | Nach UX-2-Abstimmung vorhandene Positionszähler und genaue Quellenbindung anzeigen; keine neue Sammelbewertung. |
| Providerbetrieb: [MarketDataRefreshPanel](../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.tsx), darin `RefreshDiagnostics` | `/market-data/refresh/status`; [RefreshDiagnostics](../../backend/app/features/market_data/service/refresh_diagnostics.py), [RefreshQuality](../../backend/app/features/market_data/service/refresh_quality.py), bestehender Runtime-Owner | Aktuellen Versuch, letzten abgeschlossenen Versuch, Quellenfehler und Retention mit ihren eigenen Zeiten lesbar halten. |
| Monitoring: [MonitoringRuntimePanel](../../frontend/src/features/alert/components/MonitoringRuntimePanel.tsx) und [TradeAlertsPanel](../../frontend/src/features/alert/components/TradeAlertsPanel.tsx) | `/position-monitoring/runtime/status`; bestehende Health-, Alert- und Notification-Owner | Globale Laufzähler von Tradechecks sowie fachliche Warnung von Daten- und Zustellproblem unterscheiden. Vorhandene Daten nutzen; keine zusätzlichen Healthreads für die Visualisierung. |
| Historische Erfassung: [WarrantQuoteHistory](../../frontend/src/features/product/components/WarrantQuoteHistory.tsx) | `/market-data/warrants/{id}/quote-history`; [QuoteHistoryReader](../../backend/app/features/market_data/service/quote_history.py) | Vorhandene Segmentzähler, Zeitfenster und begrenzte Detailbelege mobil lesbar darstellen; keine neue Kurskurve. |
| Historische Quellen: [TradeSourcesView](../../frontend/src/features/trade/components/TradeSourcesView.tsx), `ReadSection` und [sourceView](../../frontend/src/features/trade/services/sourceView.ts) | `/trade-position/trades/{id}/sources` sowie `/sources/plan`, `/sources/reviews`, `/sources/journal`, `/sources/evidence`; [TradeSourceReader](../../backend/app/features/trade_position/service/source_view.py) | Vorhandene unabhängige Abschnitte als vertikale Belegliste verständlicher ordnen; Quellenowner und exakte Versionslinks erhalten. |

Nutze bestehende Qualitäts- und Herkunftsdetails in `ProductValuationPanel`,
`PositionValuationBasisDetails`, `PositionRiskSummary`, `PositionRiskPanel`,
`IvRiskPanel`, `WarrantValuationEvidence`, `TradeJournalPanel`,
`Ft011EvidenceHistory`, `JournalEvidenceOrigin` und `EvidenceSourceStatus`.
Erzeuge keine zweite Bewertung oder abweichende Warnsemantik. Ein bestehendes
`CURRENT` bei einem Produktbeleg beweist beispielsweise keine verfügbare Live-IV.

Die Positionskursdarstellung gehört [UX4-B](ux4-b-position-price-history-prompt.md),
die Performancevisualisierung [UX4-C](ux4-c-performance-visualization-prompt.md).
API-only Scores, PositionPhase, DynamicStop, hypothetisches IV-Modelllabor und
neue Risiko- oder Performancecharts sind nicht Bestandteil dieses Auftrags.

## 3. Verbindliche Regeln für Datenqualität

- **Population nennen.** Gehaltene Produkte, offene Positionen, Erfassungsslots,
  unterschiedliche Kursbelege, beobachtete UTC-Tage, Monitoringpositionen,
  Regelprüfungen, Alerts und Zustellversuche sind verschiedene Einheiten.
  Zwei Positionen desselben Optionsscheins sind nicht zwei gehaltene Produkte.
- **Dimensionen getrennt halten.** Verfügbarkeit, Kursfrische, Identitätsbeleg,
  Preisart, Historienumfang, Providerbetrieb und fachliche Berechenbarkeit
  erhalten eigene Beschriftungen. Kein universeller Qualitätswert und keine
  neue Rot-Gelb-Grün-Gesamteinstufung.
- **Überlappung erhalten.** `bound_positions`, `source_verified` und
  Frischegruppen sind keine gemeinsame Zerlegung. `missing_source` enthält
  bereits Teilgruppen wie `legacy_unbound` und `ambiguous_source`. Keine
  Summe aller Diagnosefelder, Prozentnormalisierung, Torte oder 100-%-Staplung.
  Verwende zunächst Zählerkarten oder Tabellen mit genauem Scope.
- **Gebundene Route erhalten.** Bei Positionsqualität entscheiden die
  persistierten Provider-, Listing-, Mapping-/Versions- und Identitätsbelege
  der gewählten Route. Eine andere frische Produktquelle beseitigt keinen
  Konflikt oder Ausfall dieser Route. Keine UI-Identitätsauflösung.
- **Stored Observations präzise benennen.** Die Coverageantwort mit
  `STORED_OBSERVATIONS_NOT_LIVE_VALUATION` und `execution_usable=false` ist keine
  ausführbare Quote oder Bewertung. Vorhandene Reasoncodes und Ownerdefinitionen
  bleiben maßgeblich; keine eigenen Schwellen oder Frischeregeln.
- **Prozesslokale Diagnose erhalten.** `PROCESS_LOCAL` bedeutet keinen
  dauerhaften Uptimeverlauf. Aktueller Versuch und letzter abgeschlossener Lauf
  bleiben getrennt. `true`, `false` und `null` bei Reachability, Responsevalidität
  und Quoteverwendbarkeit bleiben unterscheidbar. Neustart oder fehlender Lauf
  beweisen weder Erfolg noch Fehlerfreiheit.
- **Retentionsbeleg erhalten.** Ein gespeicherter brauchbarer Kurs nach einem
  Fehler ist kein neuer Providererfolg. Cache, Wiederverwendung, Deferral oder
  eine andere erfolgreiche Route beweisen keine Erholung der betroffenen
  Identität. Verwende ausschließlich die gelieferten Erfolg-/Fehlerzeiten.
  `qualified_success` belegt die Ownerqualifikation des Checks, nicht allein
  einen neuen HTTP-Kontakt. „Provider wieder erreichbar“ braucht zusätzlich
  `provider_reachable=true`. Eine alte `recovered_at`-Angabe darf die neue
  Fehlerfolge eines aktuelleren Snapshots nicht überdecken.
- **Zeitbedeutung sichtbar machen.** Originalkurszeit, Abrufzeit, Erfassungszeit,
  Bewertungszeit, Reviewprüfung und Ausführungszeit sind eigenständig. Zeitzone,
  Preisart und Währung bleiben am jeweiligen Beleg. Fehlende Originalzeit
  bleibt unbekannt; eine Abrufzeit wird nicht als Börsenzeit bezeichnet.
- **Erfassungsprotokoll begrenzen.** `FIRST_CAPTURE_PER_ROUTE_5_MIN_UTC_V1`
  bewahrt die erste abgeschlossene Erfassung je Route/Identität/UTC-Slot,
  einschließlich Fehlern. Wiederholte Erfassung eines alten Kurses ist kein
  neuer Originalkurs. `sampled_slots`, `distinct_quote_evidence` und
  `observed_utc_days` bleiben getrennt. Segmentzähler beziehen sich auf das
  angefragte Erfassungsfenster, Detailitems auf höchstens die letzten 50
  Beobachtungen des gesamten Reports über alle Segmente.
  `time_coverage_percent=null` wird nicht lokal berechnet. Unbeobachtete
  Zeit ist unbekannt; kein erfundener Ausfallkalender oder Handelskalender.
- **Keine impliziten Aktionen.** Die Coverage- und Quellenreader lesen
  gespeicherte Belege. Das gilt nicht pauschal für jeden GET: Monitoring-Health
  kann EODHD abfragen; Analytics-/Phase-/Score-/Stopreads können dies mittelbar
  tun. Öffnen, Fokussieren, Filtern und Navigieren lösen keine zusätzlichen
  Provideraufrufe, Refreshjobs, POST/PUT/PATCH/DELETE-Commands oder Speicherung aus.
- **Hinweis und Fachstatus unterscheiden.** Gleichnamige Codes verschiedener
  Owner werden nicht global gemappt. Grobe Fehlercodes oder Freitext belegen
  keine spezifische Quellenlücke; unbekannte Status erhalten weder eine erfundene
  Blockade noch Entwarnung. DRAFT, belegtes EMPTY und reguläres LAST_AVAILABLE
  sind keine pauschalen Fehler. UX-3-Präsentationsarten ersetzen weder
  AlertSeverity noch ACTION/REVIEW/BLOCKED oder deren globale Ownerreihenfolge.

## 4. Verbindliche Regeln für die Belegliste

| Abschnitt | Darstellbarer Beleg | Grenze |
| --- | --- | --- |
| Analyse / Kandidat | Exakte historische Quelle mit tatsächlichem `source_type`, ID, Version und gegebenenfalls Modellversion | Eine numerische Quellversion ist nicht automatisch eine Analysis-UUID. Kein erratener Analyselink und kein Ersatz durch die neueste Analyse. |
| Plan | Gebundene Planversion, Herkunft und eigenes Approval | Ein manueller Plan kann ohne Analyseherkunft gültig sein; ein externer Trade kann ohne Plan existieren. Keine künstliche Lücke im Pflichtprozess und keine angenommene Freigabe. |
| Ausführung | Wirksame Ausführung mit Originalzeitpräzision, Währung, Vorgänger-/Korrekturbezug | Ersetzte Buchungen nicht doppelt zählen. DATE_ONLY bleibt Datum mit vorhandener Ausführungszeitzone, ohne erfundene Mitternacht; `recorded_at` ist kein Ersatz. |
| Position | Zugehörige Projektion mit OPEN/CLOSED/CANCELLED/UNKNOWN | Storno ist kein SELL oder wirtschaftlicher Vollabschluss. Fehlende offene Menge nicht als 0 Stück darstellen. |
| Review / Journal | Exakte Version, DRAFT/FINALIZED, eigene Quellenbindung und Aktualität | Entwurf ist nicht finalisiert; aktueller Quellenbezug ist kein Qualitätsurteil. Ein finalisiertes leeres Journal kann gültig sein, beweist aber keine vollständige Reflexion. |
| Evidence / Lesson | Evidence-ID, Entstehungszeit, Review-/Journalversion, `source_bound` und historische Lessonrelation | Lessonlink liefert Version, Relation und `is_current_version`, keinen Lessonreviewstatus. SUPPORTS/CONTRADICTS/CONTEXTUAL ist eine Beziehung, kein Freigabeurteil. |

Zeige belegtes Fehlen, nicht geprüfte Herkunft, Ladevorgang und Readfehler
unterschiedlich. Ein später vorhandener Beleg setzt frühere Schritte nicht auf
„erledigt“. Keine „6/6 abgeschlossen“-Anzeige, Prozentfortschritte oder neue
Lifecycle-Statusmaschine. Die Monitoring-PositionPhase ist eine andere Aussage.

`DRAFT/FINALIZED`, gespeicherte Quellenaktualität, aktuell geprüfte
`CURRENT/STALE/UNKNOWN` mit `checked_at`, `source_bound`, historische
Evidenceexistenz und aktuelle Materialisierungsbereitschaft sind getrennte
Achsen. Ein aktuelles `materialized=false` für einen noch nicht bereiten
Reviewstand widerlegt ältere Evidence nicht. Eine Nachbeobachtung mit 20
tatsächlichen Basiswert-EOD-Beobachtungen bedeutet weder vollständige
Reflexion noch freigegebene Lesson oder nachgewiesene Kalendervollständigkeit.

Erhalte `trade_id`, `review_version_id` und `journal_version_id` über Auswahl,
Quellenlinks, Navigation und Rückkehr. Ungültige, doppelte, fremde oder nicht
vorhandene Pins führen zu einem eindeutigen Fehler, niemals zum stillen
Latest-Fallback. Eine Journal-Draftversion hat zusätzlich `edit_revision`;
ihre Versions-ID allein verspricht keinen unveränderlichen Text.

Verlinke nur tatsächlich unterstützte Objekt-/Versions-/Bereichsziele. Ein
Buchungsbereich ist kein bereits vorhandener Fokus auf eine einzelne Ausführung;
genaue Providercheck-/Listing-/Identitätsziele bleiben ohne Zielvertrag offen.
Keine Wunschparameter, ungeprüften `returnTo`-Ziele oder aus Freitext erzeugten
Quellen-URLs. Ein Navigationslink und das Öffnen eines Entscheidungsworkflows
führen selbst keinen Write aus. Ein reiner Hash-/Abschnittswechsel desselben
Trades darf keine Nutzerdrafts verwerfen oder zusätzliche Trade-/Positions-/
Timeline-Reads erzeugen; diese Lebensdauer bleibt beim UX-2-Host.

Die fünf Quellenreads besitzen eigene `read_started_at`/`read_completed_at`
und getrennte `REPEATABLE READ READ ONLY`-Fenster. Es entsteht kein atomarer
Gesamtsnapshot. Erhalte ihre individuellen Lade-/Fehlerzustände, Abbruchlogik,
Versionsguards und bestehenden Budgets. Limitüberschreitung oder Lesefehler
werden nicht in „kein Beleg“ oder stillen Teilerfolg umgewandelt. Eine neue
frontendseitige Form darf keinen zusätzlichen Backend-Lifecycleowner behaupten.

## 5. Abhängigkeiten und fehlende Daten

| Owner | Erforderliche Abstimmung / Grenze |
| --- | --- |
| UX-1 und Fach-Owner | Sichere Ableitungen, historische IDs, Währungs-/Zeitbelege, gültige Versionslinks und Definitionen. Fehlende Daten nicht im Browser rekonstruieren. Unterschiede zwischen bestehenden Frischepfaden beim Owner klären, statt sie in der Anzeige zu vereinheitlichen. |
| UX-2 | Gemeinsamer Einbau, Props, Zuständigkeit für Reads, Invalidierung, Lebensdauer, Navigation und Konfliktdateien vor der Integration festhalten. Bestehende Quellenansicht erweitern; keinen parallelen Trade-Workspace bauen. |
| UX-3 | Den oben gepinnten Draft als Darstellungsgrundlage lesen und den tatsächlichen Folgehead prüfen. Ursache, Wirkung, Nutzerbedarf, Hinweisidentität und Priorität innerhalb einer Hinweisgruppe abstimmen; Fachstatus und globale Ownerpriorität bleiben erhalten. Keine produktiven Notice-Komponenten oder freigegebene Integration aus #314 ableiten. |
| UX4-B / UX4-C | Gemeinsame Herkunfts-/Lückenbegriffe abstimmen; vorhandene Kurs- und Performanceowner bleiben eigenständig. Keine technische Abhängigkeit von einem ungemergten Folge-Branch erzeugen. |

**Öffentliche Typgrenze:** UX-3 benennt in O3 die derzeit privaten
`RefreshCheck`-/`RefreshStatus`- und Coverage-Typen. Vor featureübergreifender
Wiederverwendung vereinbaren Market Data und UX-2 einen zugänglichen Read-Typ
oder ein geprüftes Adapterinterface für die echte Payload einschließlich
älterer/fehlender Felder. Keine zweite kopierte Statusunion oder Recoverylogik.
Gemeinsame Präsentation erhält qualifizierte Ownerdaten und Links über eine
schmale öffentliche Grenze bzw. typisierte Props; dokumentarische Typimporte
erlauben keine produktiven Querimporte interner Features. Ein Reexport-Barrel
allein löst diese Grenze nicht.

Fehlen Quellenidentität, Originalzeit, Währung, eine konkrete historische
Verknüpfung oder ein expliziter Status, zeige genau diese fehlende Voraussetzung.
Erfinde keine Werte, Quoteintervalle, Status oder Beziehungen. Behaupte keine
vollständige Historie aus gespeicherten Stichproben oder operativer Providerqualität.

Wenn ein gewünschter Ausbau einen neuen Quellenresolver, eine Aggregation,
zusätzliche Providerreads oder Fachzustände benötigt, dokumentiere dafür den
konkreten fehlenden Ownervertrag und eine überprüfbare Darstellung der Lücke.
Führe die weiterhin möglichen lokalen Arbeiten fort. Gemeinsame Einbindung
wartet auf UX-2; fehlende UX-3-Semantik wird als Voraussetzung ausgewiesen.

## 6. Umsetzung und echte Abnahme

Nutze die bestehenden Komponenten, Tabellen, `details`, Buttons, Links und
Selects. Die Belegliste kann vertikal gegliedert sein; zusätzliche Diagramme
oder eine neue Chartbibliothek sind für diesen Auftrag nicht erforderlich.
Quellen, Zeitbedeutung, Einheiten und Gründe müssen ohne Hover erreichbar sein.
Farbe erhält immer Text oder ein zweites unterscheidbares Merkmal.
Wesentliche Einschränkungen stehen neben der betroffenen Zahl; Details ergänzen
sie. Gleiche Ursache am selben Objekt erscheint pro Oberfläche einmal mit
Verweis auf ihren Beleg. Unabhängige Ursachen und Quellenidentitäten bleiben
getrennt. Keine zusätzliche Deduplizierung persistierter Alerts.

Initiale und unveränderte Hinweise bleiben statisch. Ein vom Host belegter
neuer oder verschlechterter Zustand wird höchstens einmal angekündigt;
Zusammenfassung und Detail erzeugen keine Doppelansage. `role=alert` folgt
nicht automatisch aus „Warnung“ oder „Blocker“. Polling verschiebt keinen
Fokus; aufgeklappte Details und sichere Navigation behalten ihre Kontextprüfung.

| Prüfung | Verbindlicher Abnahmefall |
| --- | --- |
| Population und Überlappung | Zwei Positionen desselben Produkts ergeben getrennte Produkt-/Positionsaussagen. Überlappende Zähler erscheinen ohne falsche Summe oder Prozentquote. Ein Tradefilter ändert globale Monitoringzähler nicht in Tradezähler. |
| Werte / Einheiten / Zeit | Belegtes 0, `null`, nicht berechenbar, leere Auswahl, Laden und Readfehler sind unterscheidbar. Währung, Sekunden/Tage und Original-/Abruf-/Erfassungszeit bleiben korrekt; DATE_ONLY erzeugt keinen Instant. |
| Quellenkonflikt | Frische Quelle B heilt die gebundene fehlerhafte Quelle A nicht. Mapping-/Identitätsversionswechsel bleibt getrennt. Retention, Cache und Deferral erhalten alte Kurszeiten und erzeugen keinen Erfolg. |
| Erfassung | Erste Fehlerprobe bleibt Fehlerprobe, wiederholter alter Kurs bleibt derselbe Kursbeleg. Fensterzähler und 50-Item-Detailgrenze bleiben erkennbar; unbekannte Coverage bleibt unbekannt. |
| Lebenszyklus / Pins | Manueller Plan und externer Trade bleiben gültig. Exakte Plan-/Review-/Journal-/Lessonversion bleibt erhalten. Falsche oder doppelte Pins haben keinen Latest-Fallback. Korrektur und Storno erzeugen keinen falschen Abschluss. |
| Unabhängige Achsen | DRAFT mit CURRENT, FINALIZED mit STALE, leeres finales Journal sowie ältere Evidence bei neuem nicht bereitem Review sind getrennt lesbar; kein erfundener Lessonreviewstatus. |
| Readgrenzen / Nebenwirkungen | Langsame Antwort nach Trade-/Pinwechsel einschließlich A→B→A wird durch Kontext und Requestgeneration verworfen; auch alte Hinweise, Aktionen, Fehler und Erfolge werden ungültig. Fehler/Timeout/Limit bleibt eigener Zustand. Öffnen, Fokus, Filter und Links erzeugen keine zusätzlichen Provideraufrufe oder fachlichen Commands; reiner Abschnittswechsel keine neuen Hostreads. Getrennte Readfenster bleiben sichtbar. |
| Mobile / Zoom | Tatsächliche Browserprüfung bei 320, 390 und 1280 CSS-Pixeln sowie 200 % Zoom; kompakte Hinweisflächen zusätzlich bei 400 % gemäß UX-3-Draft. Keine horizontale Dokumentrolle, verdeckten Controls oder abgeschnittenen Einheiten. Breite Tabellen nur in einem beschrifteten eigenen Scrollbereich. |
| Tastatur / Zugänglichkeit | Tab/Shift-Tab, Enter/Leertaste, vorhandene Ausklapp-/Filterbedienung, sinnvoller sichtbarer Fokus, zugängliche Namen und semantische Tabellen tatsächlich prüfen. Keine Doppelankündigung oder erneute Live-Ansage unveränderter Hinweise. Alle Belege ohne Hover; Kontraste prüfen. Keine Screenreader- oder WCAG-Vollabnahme ohne echten Nachweis. |
| Fachliche Unverändertheit | Keine Änderung an Finanzformeln, Währungsresolvern, Frischepolicy, Statusableitungen oder Persistenz. Bestehende relevante Backend-/Frontendregressionen bleiben grün; keine abgeschwächten Assertions oder Coveragegates. |

Erweitere gezielt die vorhandenen Tests für das geänderte Verhalten:

- Frontend: [QuoteCoveragePanel](../../frontend/src/features/operational_workspace/pages/QuoteCoveragePanel.test.tsx),
  [Refreshdiagnostik](../../frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.diagnostics.test.tsx),
  [WarrantQuoteHistory](../../frontend/src/features/product/components/WarrantQuoteHistory.test.tsx),
  [TradeSourcesView](../../frontend/src/features/trade/components/TradeSourcesView.test.tsx)
  und [MonitoringRuntimePanel](../../frontend/src/features/alert/components/MonitoringRuntimePanel.test.tsx).
- Backend-Unit: [Positionscoverage](../../tests/unit/backend/features/market_data/test_position_quote_coverage.py),
  [Quotehistory](../../tests/unit/backend/features/market_data/test_quote_history.py),
  [Identitätsdiagnostik](../../tests/unit/backend/features/market_data/test_refresh_identity_evidence.py)
  und [Quellenreader](../../tests/unit/backend/features/trade_position/test_source_view.py).
- Integration: [Coverage-API](../../tests/integration/backend/test_held_quote_coverage_api.py),
  [Refreshdiagnostik-API](../../tests/integration/backend/test_refresh_diagnostics_api.py)
  und [Quellenreader mit PostgreSQL](../../tests/integration/backend/test_trade_source_view_postgres.py).
- Browser: [Quotecoverage](../../tests/e2e/quote-coverage.spec.ts),
  [exakter Handoff-Pin](../../tests/e2e/post-trade-handoff-pin.spec.ts)
  und [historische Evidence](../../tests/e2e/post-trade-evidence-history-postgres.spec.ts).

Führe die für die Änderung relevanten Unit-, Integrations- und Browsertests
tatsächlich aus. Vorhandene Tests allein sind kein Ausführungsnachweis;
DOM-Tests ersetzen keine reale Mobile-/Tastaturprüfung. Dokumentiere genaue
Kommandos, Umgebung, Commit und Resultate. Fehlende Umgebung oder nicht
ausgeführte Fälle bleiben als offen markiert. Verwende kontrollierte Fixtures
und vorhandene Testprovider; teste keine neuen Produktionsproviderabfragen.

## 7. Lieferumfang und Abschluss

Erstelle einen eigenständigen **Draft-PR** mit knapp begründetem Scope,
betroffenen Komponenten, dem tatsächlich geprüften Main und eigenen Head,
Beispielen für belegte und fehlende Informationen sowie den echten
Testnachweisen. Halte dokumentiert, implementiert, lokal geprüft, CI-geprüft,
fachlich abgestimmt und integriert ausdrücklich auseinander.

Nenne offene Daten-/Ownerverträge und den konkret vereinbarten UX-2-Einbau.
Bestätige anhand des Diffs, dass finanzielle Berechnungen, Provideranbindung,
Fachcommands und bestehende Versionspins unverändert geblieben sind.
Kein Merge, Release oder PC-Update ohne gesonderte Freigabe.

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | Eigenständiger UX4-D-Startauftrag aus UX4-A; absolute Qualitätszähler und historische Belegliste, mit Integrationsgrenzen und geplanter echter Abnahme; UX-3-Draft #314 am exakten Head abgeglichen |
