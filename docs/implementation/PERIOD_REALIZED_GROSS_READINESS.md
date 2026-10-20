# Realisierte Bruttoergebnisse nach Zeitraum — Quellenvertrag und Readiness

Stand: 17.10.2026. Prüfgrundlage: `e9aac2bfaadeb9133a6ed07e42d1dec39836b156`
(`main`, Softwareversion 1.5.8). Auftrag: Startprompt 08, Fassung 1.1.
Maßgeblicher Arbeitsstatus ausschließlich im
[Product Backlog: PB-019 Kennzahlen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics),
[Periodenauswertung](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations)
und [PB-017 Brutto-PnL](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl).
Diese Arbeitsbezeichnung ist keine neue FT-ID.

**Fortschreibung nach der Quellenprüfung:** Am 17.10.2026 hat der Nutzer nach
Vorlage dieses konkreten Vorschlags und Erklärung der Nutzerwirkung ausdrücklich
„Ok, umsetzen“ angewiesen. Der unten beschriebene additive Währungsvertrag und
der enge V1-Berichtsvertrag sind damit zur Umsetzung freigegeben; siehe
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md).
Das ist keine Endabnahme des fertigen Codes und kein Installationsnachweis.
Die auf diesem vorab festgelegten Vertrag beruhende Umsetzung und ihre neuen
Tests sind inzwischen im [vertikalen Qualifikationsnachweis](PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
belegt. Die folgenden Ausgangsbefunde bleiben auf den genannten Prüfcommit bezogen.

## Entscheidung vor Implementierung

Bei der ursprünglichen Quellenprüfung war die vertikale Geldbetragsauswertung
**nicht ready**: Für gespeicherte
BUY-/SELL-Preise ist bisher kein qualifizierter historischer Vertrag der
tatsächlichen Ausführungswährung belegt. Das gilt getrennt für
`WORKSPACE_SELECTION` und eigene `EXTERNAL`-Trades. Die Produktauswahl und heutige
Listing-/Kursquellenwährungen schließen diese Lücke nicht. Die vorgeschlagenen
Perioden-/Auswahlregeln des Auftrags waren zu diesem Prüfzeitpunkt noch keine
erteilte Fachfreigabe. Die spätere ausdrückliche Entscheidung oben erlaubt jetzt
die additive Owner-Erfassung und anschließend die zugehörige Berichtsstrecke.

Die unabhängige rein arithmetische Owner-Vorleistung ist ready: Die Formel
`quantity * (price_per_unit - applicable_average_cost)` ist bereits in
[ADR-S10-004](../decisions/ADR-S10-004-AVERAGE-COST-AND-GROSS-REALIZED-PNL.md)
fachlich entschieden. Der Auftrag erlaubt ihre rückwärtskompatible Offenlegung
und unabhängige synthetische Qualifikation. Dies autorisiert weder eine
Währungsbestätigung alter Buchungen noch eine nutzerbestandsfähige Berichtssumme.

## Erster Schritt: Owner-Vorleistung und deren vorab festgelegte Abnahmebedingungen

Owner bleibt `trade_position.domain.PositionProjector`. Additiv wird ein reiner
Projektions-Trace angeboten. Der bestehende `project()`-Rückgabevertrag,
Sortierschlüssel `(executed_at, recorded_at, id)`, Decimal-Operationen und
Validierungsregeln bleiben erhalten; genau eine Rechenschleife bildet beide
Zugriffe ab. Der Trace hält die vollständige geordnete wirksame Historie einmal
und referenziert pro SELL deren benötigten Präfix einschließlich früherer SELLs.
Er bindet genaue Execution-Identitäten und vorhandene Datumspräzision. Er setzt
wirksame, vollständige und vom Owner qualifizierte Eingaben voraus; er ersetzt
weder dessen Korrektur-/Storno-/Date-only-Prüfung noch die Berichtsauswahl.

Vor Änderung des Rechencodes sind folgende Bedingungen festgelegt:

1. Unabhängig vorgegebene Beiträge des synthetischen Auftragsfalls sind
   `10`, `30`, `-20`, `30`; die zwei September-SELLs ergeben `10`, die gesamte
   Folge `50`. Der im September offene Restbestand ist `60` mit Kosten `180`.
2. Bei wirksam ersetztem September-SELL zu `3.00` lauten die Beiträge
   `10`, `30`, `0`, `30`; September `30`, gesamte Folge `70`. Die alte ID darf
   in der vom bestehenden Repository ermittelten wirksamen Folge nicht zählen.
3. Trace und bisherige Projektion liefern exakt dieselbe Position; keine
   Float-Konversion, neue Quantisierung, Toleranz oder Änderung des Decimal-Kontexts.
4. Vor-/Nachbestand und Kostenbasis werden für jeden SELL offengelegt. Der
   vollständige Präfix enthält auch frühere Teilverkäufe und spätere Nachkäufe
   nur bis zu diesem SELL. Nachfolgende Executions sind keine dessen Quellen.
5. BUY-only bleibt ohne SELL-Beitrag. Überverkauf, fehlender BUY, falsche
   Trade-/Produktidentität und Wiedereröffnung bleiben Fehler. Bestehende
   Date-only- und Supersession-Regeln bleiben unangetastet.
6. Ein separat vorgerechneter Fall mit periodischen Dezimalbrüchen fixiert die
   tatsächliche bestehende Decimal-Rechenreihenfolge und die Nullsetzung einer
   vollständig geschlossenen Kostenbasis; die Abweichung von idealer rationaler
   Rechnung wird sichtbar, nicht durch großzügige Assertions verdeckt.
7. Keine Datenbank-, API-, Frontend-, Provider-, Lernprozess- oder
   Persistenzänderung folgt aus diesem Trace. Der Input wird nicht mutiert.

Die EUR-Bezeichnung des Referenzfalls ist ausschließlich eine ausdrücklich
synthetische Testannahme. Das Execution-Modell selbst belegt diese Währung nicht.
Eine Auswahl dieser Testdaten nach ihrem Datum ist kein implementierter
Perioden-/Zeitzonenvertrag und kein API-/Browsernachweis.

## Geprüfter Ausgangsstand und Grenzen

Die frische Arbeitskopie hatte keine fremden Änderungen und keine getrackte
`AGENTS.md`. Aufgabenbranch: `work/realized-gross-readiness-20261017`.
`VERSION`, Backend-/Frontend-Manifeste und Frontend-Lockwurzel nennen 1.5.8.
Die integrierten PRs #260, #261 und #263 werden wiederverwendet. #249 ist am
Prüftag weiter offen und Draft; seine Formularänderung ist nicht Teil dieses
Diffs. Sie bleibt vor weiterer betrieblicher Ausweitung prioritär, blockiert
aber diese Quellenprüfung und reine Owner-Qualifikation nicht.

Gelesen wurden die relevanten Foundation-, Domain-, Planungs-, Lifecycle- und
Entwicklungsverträge, die unveränderte M8-Baseline, FT-009/010-ADRs, Capture-
Verträge sowie aktuelle Capture-, Korrektur-, SQL-, API-, Router- und Testpfade.
Die Prüfung umfasst keine Nutzerabrechnungen, Nutzerbestände oder Zielinstallation.
Es wird deshalb weder deren tatsächliche Währung noch eine numerische
Bestandsabdeckung behauptet. Die belegte Lücke ist der Erfassungs-/Read-Vertrag.

Ältere Journal-/Lesson-Qualifikationsberichte nennen noch offene Materialisierung
und Evidence-Historie. Die spätere
[FT-011-Qualifikation](FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md)
schließt diese beiden Lücken für ihren genauen Umfang. Ihre Testzahlen und die
[Release-Notiz 1.5.8](../releases/V1.5.8-FT011-CONSISTENCY-HISTORY.md) sind
historische Nachweise und werden nicht als neue Testausführung oder PC-Beleg
verwendet. Eigene erneut ausgeführte Prüfungen stehen gesondert im
[Qualifikationsbericht](PERIOD_REALIZED_GROSS_QUALIFICATION.md).
Die frühere gemeinsame Journal-/Performance-Phase im Prozessmodell begründet
keinen Journalzwang für diesen finanziellen Leseschnitt; maßgeblich sind die
präzisierten Grenzen von Roadmap-Ziel C und dem neuen Quellenvertrag.

## Feldbezogene Quellenmatrix am Ausgangscommit

Die kurzen Pfade `domain/`, `persistence/`, `service/` und `api/` in dieser Matrix
liegen unter `backend/app/features/trade_position/`; kurze Testdateien ohne
anderen Pfad unter `tests/unit/backend/features/trade_position/`. Genannte Tests sind zunächst
gelesener Testcode; neue Ausführungen stehen gesondert im
[Qualifikationsbericht](PERIOD_REALIZED_GROSS_QUALIFICATION.md).

| Feld / Zweck | Owner und Speicherort | Historische Bindung / Änderbarkeit | Read-Contract und heutige Consumer | Vorhandene Tests | Fehlende Voraussetzung |
|---|---|---|---|---|---|
| Workspace, Trade, Produkt, eigener Ursprung | FT-009/010: `domain/models.py::Trade`, `persistence/models.py::TradeModel` | Stabile IDs; bei WORKSPACE_SELECTION konkrete Plan-, Planversions-, Selection- und Evaluation-IDs; EXTERNAL erfindet diese nicht. | `service/read.py::TradeReadService`; Trade-API, Managementseite. | `test_domain.py`, `test_trade_read.py` | Identität ist belegt, Ausführungsnotierung/Währung daraus nicht ableitbar. |
| SELL/BUY, Menge, tatsächlicher Stückpreis | FT-009/010: `ExecutionRecord`, `execution_records` | Immutable Fakt; ganzzahlige positive Menge; Preis `Decimal` / SQL `Numeric(24,10)`. | `SqlAlchemyExecutionRecordRepository`, `api/dtos.py::ExecutionResponse`, Timeline. | `test_domain.py`, `test_persistence.py`, `test_rest_api.py` | Preiszahl vorhanden; ihre tatsächliche Währung nicht bestätigt. |
| Kaufkosten / Verkaufserlös | `ExecutionRecord.gross_amount` | Aus Menge × Stückpreis abgeleitet, kein zweiter gespeicherter Betrag. | Projector und ExecutionResponse. | `test_domain.py::test_execution_gross_amount_is_derived` | Kein qualifizierter Geldbetrag ohne Preiswährungsbeleg. |
| Wirksamkeit und Ersatz | FT-010: `supersedes_execution_id` in `execution_records` | Original erhalten; Korrektur fügt Nachfolger hinzu. `recorded_at` des Nachfolgers ist neu. | `list_effective_for_trade`: Anti-EXISTS gegen Replacement; `list_for_trade`: volle Historie. Commands rekonstruieren Position. | `test_corrections_timeline.py`, `test_repository.py` | Zukünftige Währungsbestätigung muss die genaue Execution-ID binden. |
| Ausführungszeit / bestätigtes Datum / Erfassungszeit | FT-009/010: `executed_at`, `executed_on`, `execution_timezone`, `recorded_at` | Aware-Instant oder Datum plus IANA-Zone; interner Date-only-Anker ist keine reale Uhrzeit. Korrektur erhält Original. | CaptureTimeRequest, `_capture_time`, Timeline, Datumskorrekturformular. | `test_capture_safety.py`; `frontend/src/features/trade/services/executionDateCorrection.test.ts` | Perioden-/Zeitzonenregeln benötigen die unten beschriebene Freigabe. |
| Durchschnittskosten unmittelbar vor SELL | FT-010: `domain/projector.py` | Vollständige wirksame BUY-/SELL-Reihenfolge; frühere Teilverkäufe beeinflussen Restkosten vor Nachkäufen. Position wird neu abgeleitet. | `project()` für bestehende Commands; additive `project_with_trace()`-Ableitung dieses Schnitts. | `test_projector.py`, neuer `test_projector_trace.py` | Rein arithmetisch nutzbar; Preiswährungen separat qualifizieren. |
| Gespeicherte Positionssumme | FT-009/010: `PositionModel` | Aktuelle Projektion, keine historischen Periodensnapshots; Basis/PnL `Numeric(30,10)`, Durchschnitt `Numeric(24,10)`. | PositionResponse, TradeManagement, OperationalWorkspace, FT-011 ActualExit. | `test_rest_api.py`, `tests/unit/backend/features/operational_workspace/test_position_snapshot.py`, `tests/unit/backend/features/post_trade/test_read_adapters.py` | Weder aktueller Closed-Status noch kumulierte Summe liefern einen Periodenbeitrag; DB-Rundung ist nicht Roh-Owner-Arithmetik. |
| Historische Auswahl-/Listing-/Terms-Identität | FT-008: `ProductSelectionModel`, `ProductEvaluationModel`, `ProductSelectionRunModel` | Konkrete unveränderliche Auswahl-/Evaluation-IDs; Evaluation bindet `warrant_listing_id` und TermsVersion. | `service/resolvers.py::SqlAlchemyWorkspaceSelectionResolver`, Selection-UI und Workspace-Kauf. | `test_resolvers.py`, `tests/integration/backend/test_product_selection_trade_position_handoff.py` | Bewertete Notierung ist keine Bestätigung der tatsächlichen Ausführungswährung. |
| Historische Quote-Währung / Kursquellenwahl | FT-008 Evaluation-Metriken; TC-001 `PositionQuoteSourceSelectionModel.evidence` | Quote-Metriken können eine historische Einheit enthalten; Kursquellenentscheidung speichert expected_currency, Listing und Kandidaten; historisierte Nachfolger. | `PositionQuoteSourceSelector.select_once`, Bewertung/Monitoring/Refresh. Workspace-Capture reicht Währung nur hierhin. | Produktselektions-Tests; `tests/unit/backend/features/market_data/test_position_quote_source.py`, `tests/unit/backend/features/market_data/test_automatic_source_selection.py`, entsprechende PG-Tests | Belegt Marktquote bzw. Quellenwahl, keine userbestätigte Bindung jedes Execution-Preises. |
| Heutige Listing-/Regelwährung | FT-004 `WarrantListingModel.quotation_currency_code`; FT-010 `TradeManagementEvent.price_binding` | Listing ist heutiger Datensatz; Managementpreisbindung ist historisch konkret, aber betrifft Stop/Ziel. Warrant besitzt mehrere Listings. | Selection-Resolver liest heutige Listingwährung; Preisbindung steuert Regelmonitoring. | Resolver-/Listing- und Monitoring-Preisbindungstests | Keine dieser Quellen darf Ausführungswährung ersetzen. Die alte EUR-Regelbestätigung gilt nur für Stop-/Zielwerte. |
| Storno | FT-009/010 `Trade.cancelled_at` usw.; `service/cancellation.py` | Explizites Metadatum/Audit; ursprüngliche BUYs und Positionswerte bleiben historisch erhalten. | Cancellation-Preview, aktive Positionen, Timeline; keine künstliche SELL. | `test_capture_safety.py::test_cancellation_is_not_a_full_exit`, `tests/integration/backend/test_trade_capture_safety.py` | Bericht muss ausschließen und erklären; ein numerisch erhaltener Positionswert ist kein wirksamer Bestand. |
| Anzeigenachkommastellen | Market-Owner `CurrencyModel.minor_unit`, `reference_version` | Versionierte Katalogreferenz mit Konfliktbehandlung, keine Execution-Evidenz. | Currency-Administration, `CurrencyResponse`. | Currency-Administration-/Katalogtests | Verwendete Referenz im Bericht ausweisen; Währungsbestätigung und Anzeigenregel nicht vermischen. |
| Journal / Review / Evidence / Lesson | FT-011/FT-012, bestehende versionierte Tabellen | Konkrete Versionen, CURRENT/STALE, Quellenprüfung und Relationslinks bleiben getrennt. | Journal-, Lesson-Review- und Evidence-History-Reader. | Journal-/Lesson-/FT011-Qualifikationsberichte und deren Testquellen | Keine Voraussetzung für finanzielle Auswertbarkeit; kein heutiger Lessonlink als wirtschaftlicher Fakt. |

### Capture-Einstiege am Ausgangscommit

`TradePositionService.record_initial_purchase`, `record_external_purchase`,
`record_additional_purchase`, `record_sale` und `correct_execution` speichern
am Ausgangscommit keine Ausführungswährung. Weder deren DTOs noch die damaligen Formulare
bestätigen sie. WORKSPACE_SELECTION übergibt die aufgelöste Listingwährung nur
an die Positionskursquellenwahl; EXTERNAL hat nicht einmal diese Vorgabe.

Zusätzlich erzeugt
`learning/application/external_trade_creator.py::SqlAlchemyExternalTradeCreator`
beim expliziten `execute-as-trade` dieselben kanonischen Trade-/Execution-/Position-
Objekte über deren Repositories. Auch dieser Handoff enthält keinen Währungsbeleg.
Eine reine ExternalObservation bleibt dagegen eine Drittbeobachtung ohne eigene
Execution. Der spätere Erfassungsvertrag muss den vorhandenen Handoff einschließen.

### Repositoryweite Consumersuche und ungeeignete Nachbarpfade

Backendregistrierung `backend/app/main.py`, Frontendrouter
`frontend/src/app/router.tsx` und repositoryweite Suchen nach Performance,
PnL-/Realisationswerten und Periodenfiltern wurden geprüft. Am Ausgangscommit
war kein registrierter Reader mit dem verlangten periodenbezogenen SELL-/Kosten-
Herkunftsvertrag vorhanden. Die gelesenen Ergebnisconsumer liefern kumulierte
Positionswerte, heutige Bewertungen oder FT-011-Exit-/Reflexionskontext.

Bestehende Grenzen sind ausdrücklich zu beachten:

- `TradeRepository.get()` nutzt für Commands `FOR UPDATE`. Einen neuen strikt
  lesenden Snapshotreader nicht ungeprüft über diesen schreiborientierten Einstieg
  zusammensetzen. Die effektive Execution-Abfrage selbst benötigt keine Sperre.
- FT-011 `GET /observation` und `GET /observation/evidence` rufen `refresh()` auf;
  `PostTradeObservationService.refresh()` kann COMPLETED speichern und committen.
  Diese GETs sind nicht der reine Finanzreader dieses Auftrags.
- OperationalWorkspace liest nur heute offene Positionen und verwendet
  Bewertungs-/Quote-Resolver. Dessen valuation_currency und Providerpfade sind
  keine Ausführungswährungs-/No-live-call-Garantie.
- Timeline enthält absichtlich auch supersedierte Executions und Managementevents.
  Sie ist historische Herkunft, keine unmittelbar summierbare SELL-Menge.
- FT-011/FT-012-Handoffprüfung und Evidenceinventar sind vorhandene reine Reads,
  versprechen aber keinen gemeinsamen globalen Berichtssnapshot.
  `materialized_at` ist Evidence-Erstellung, `checked_at` heutige Quellenprüfung.

## Freigegebener minimaler Währungserfassungsvertrag

**Am 17.10.2026 ausdrücklich zur Umsetzung freigegeben.** Die folgenden Regeln
legen den Vertrag fest; Implementierungs- und Testnachweise bleiben getrennt.

1. Der Execution-Owner erhält eine additive unveränderliche, versionierbare
   Währungsbestätigung an einer konkreten Execution-ID. Mindestfelder:
   Bestätigungs-ID, Execution-ID, Währungscode von `price_per_unit`,
   Bestätigungszeit, Audit-Akteur, ausdrückliche Bestätigungs-/Quellenangabe und
   optional `supersedes_confirmation_id`. Die tatsächliche Abrechnung bzw.
   Benutzerbestätigung ist die Quelle. Ein Listing ist nur optional bei belegter
   Ausführungsnotierung erforderlich; eine bekannte Währung benötigt keine
   erfundene Börsenkennung. Audit-Akteur ist weiterhin kein Authentifizierungsbeleg.
2. Alle oben genannten Capture-Einstiege speichern diese Erklärung atomar mit
   der neuen tatsächlichen Ausführung. Vorgeschlagene Währungen dürfen sichtbar
   aus Stammdaten stammen, gelten erst nach ausdrücklicher Bestätigung als Fakt.
   Ein kompatibler API-Aufruf ohne Bestätigung bleibt möglich, aber monetär
   `UNKNOWN`. Es gibt keinen Default EUR und keinen FX-Fallback.
3. Bestehende Ausführungen erhalten keine automatische Bestätigung. Eine separate
   bewusste Owner-Aktion ergänzt nur ihre Währungsherkunft. Sie verändert weder
   Menge/Preis noch `recorded_at`, `executed_at` oder Owner-Sortierung. Ein GET
   schreibt oder repariert nichts. Keine rückwirkende Gleichsetzung der
   Bestätigungszeit mit dem wirtschaftlichen Ausführungszeitpunkt.
4. Die Relation gehört demselben Execution-Owner, keinem Performance-Schreiber.
   Ein eindeutiger wirksamer Bestätigungsstand, Workspace-/Execution-FKs,
   Supersession, Idempotenz und konkurrierende Bestätigungen müssen im separaten
   additiven Migrations-/Command-Schnitt mit echtem PostgreSQL qualifiziert werden.
   Eine falsche Bestätigung erhält einen dokumentierten Nachfolger; das Original
   bleibt erhalten. Eine wirtschaftliche Execution-Korrektur benötigt eine eigene
   Bestätigung der Ersatz-ID oder eine ausdrücklich erklärte, belegte Übernahme.
5. **Begründung für eine additive Relation:** Die bestehende wirtschaftliche
   `correct_execution` erzeugt ein neues `recorded_at`. Bei gleichen Zeitankern
   kann das die Reihenfolge verändern. Eine bloße Währungsbestätigung darf diesen
   unveränderten Rechenvertrag nicht unbeabsichtigt verändern.

Damit existiert weiterhin genau eine wirtschaftliche Execution-Wahrheit. Die
vorgeschlagene Ergänzung belegt deren Einheit; sie ist keine zweite Buchführung,
keine Portfolio-/Kontowährung und keine Migration bestehender Zahlen zu EUR.

## Freigegebener V1-Berichtsvertrag

Die folgenden Regeln wurden zusammen mit dem Währungsvorschlag am 17.10.2026
ausdrücklich zur Umsetzung freigegeben. Sie ergänzen die bereits beschlossenen
wirtschaftlichen Owner-Fakten, Korrekturen und Average-Cost-Formel.

### Grundgesamtheit, Filter und Validierung

- Eindeutige wirksame SELL-IDs eigener, nicht stornierter Trades im aktuellen
  Workspace. WORKSPACE_SELECTION und bewusst erfasste eigene EXTERNAL-Trades
  sind zulässig. Heute oder am Periodenende offene Trades bleiben zulässig.
  Keine Filterung nach Trade-/Journal-/Reviewabschluss. BUY ist nur Kostenquelle.
- V1 verwendet genau eine ausdrücklich gewählte `report_currency` sowie
  `from_date`, `to_date` (inklusive ISO-Kalendertage) und `report_timezone`
  (explizite IANA-Zone). Die UI kann Europe/Berlin sichtbar vorschlagen; weder
  Browserstandort noch Berichtswährung bestätigen eine Buchungswährung.
  Ein paralleler Modus für alle Währungsgruppen ist für V1 nicht erforderlich.
- Ungültige Datumswerte, `from_date > to_date`, nicht darstellbarer Folgetag,
  ungültige Berichtszone oder unbekannter Währungscode sind HTTP-422-Eingabefehler.
  Deaktivierte historische Währungen dürfen vorhandene bestätigte Fakten nicht
  unsichtbar machen. Ungültige gespeicherte Quellen sind dagegen Datenlücken.
- Lade vollständige wirksame Historien der benötigten Trades, auch vor Beginn
  und nach Ende der Periode. Rekonstruiere mit dem Owner; ordne erst die
  SELL-Beiträge zu. Keine SQL-Vorfilterung, die überlappende Date-only-Tage allein
  anhand ihres Kalendertags oder internen Ankers verwirft.
- Stabiler SELL-Sortierschlüssel bleibt `(executed_at, recorded_at, execution_id)`.
  Der Anker ordnet Date-only intern, seine Anzeige bleibt ein Datum ohne Uhrzeit.

### Preisbestandteile und Währung

Ein monetärer SELL-Beitrag benötigt eine gemeinsame belegte Währung für seinen
Verkaufspreis und **alle BUY-Preisbestandteile seiner geltenden Kostenbasis**.
Gemischte oder unbekannte dieser Preiswährungen liefern keine Geldzahl. Die
vollständige vorherige Execution-Historie einschließlich früherer SELLs bleibt
als Herkunft erhalten.

Die Währung des Erlöspreises eines **früheren** SELL beeinflusst die Restkostenbasis
nicht: Dessen Menge und geltende Kostenbasis reduzieren den Bestand. Beispiel:
BUY 100 × 2 EUR, SELL 20 × 3 USD, später SELL 10 × 2,50 EUR. Der erste SELL ist
ohne FX monetär unqualifiziert; der spätere SELL kann mit belegten Mengen und
BUY-Währung einen Beitrag von 5 EUR liefern. Eine pauschale Ein-Währungs-Pflicht
für sämtliche früheren SELL-Erlöse wäre ein zusätzlicher, hier nicht vorgeschlagener
Ausschluss. Unklare Mengen, Identitäten, Wirksamkeit oder ungültige Owner-Reihenfolge
bleiben dagegen auch für spätere Basisberechnungen relevant.

### Periodenzuordnung ohne erfundene Uhrzeiten

Das Berichtsintervall ist `[Tagesbeginn(from_date, report_timezone),
Tagesbeginn(to_date + 1 Kalendertag, report_timezone))`. Beide Grenzen werden
getrennt aus dem lokalen Datum ermittelt und als UTC-Instants verglichen.
Kein pauschales Vielfaches von 24 Stunden. Aware-Ausführungen zählen genau bei
`start <= executed_at < end`.

Date-only wird als Menge möglicher Instants des gespeicherten Tages in seiner
gespeicherten Zone betrachtet: `[Tagesbeginn(executed_on, execution_timezone),
Tagesbeginn(executed_on + 1 Kalendertag, execution_timezone))`.

| Beziehung zum Bericht | Ergebnis |
|---|---|
| Der gesamte mögliche Ausführungstag liegt darin. | `IN_PERIOD` |
| Die Intervalle sind disjunkt; bloße Grenzberührung genügt nicht. | `OUTSIDE_PERIOD` |
| Echte Überschneidung, aber keine vollständige Enthaltenheit. | `PERIOD_AMBIGUOUS` |
| Gespeicherte Zone/Datum oder Tagesgrenzen nicht zuverlässig interpretierbar. | `PERIOD_UNKNOWN` |

Ein übersprungener historischer Kalendertag oder eine unklare Tagesgrenze darf
nicht als leere, scheinbar enthaltene Menge gelten. In der Anfrage wird eine
solche nicht unterstützte Grenze abgelehnt; bei Quellen bleibt sie unklar.
Es wird weder der interne Anker noch eine geratene Uhrzeit als Ausführung gezeigt.

Vor Implementierung festgelegte Beispiele zur technischen Abnahme:

| Zeitraum / Quelle | Erwartete Grenze / Zuordnung |
|---|---|
| 29.03.2026, Europe/Berlin | `[28.03.23:00Z, 29.03.22:00Z)`, 23 Stunden. |
| 25.10.2026, Europe/Berlin | `[24.10.22:00Z, 25.10.23:00Z)`, 25 Stunden. Beide ausdrücklich offsetgebundenen 02:30-Instants zählen. |
| 31.12.2026, Europe/Berlin | Ende `31.12.23:00Z`; dieser Instant gehört bereits zum Berliner 01.01.2027. |
| September/Berlin; Date-only 02.09./Asia/Tokyo | Vollständig enthalten. |
| September/Berlin; Date-only 01.09./Asia/Tokyo | Berliner 31.08.17:00 bis 01.09.17:00: mehrdeutig. |
| September/Berlin; Date-only 01.10./Asia/Tokyo | Berliner 30.09.17:00 bis 01.10.17:00: mehrdeutig trotz gespeichertem Oktoberdatum. |
| September/Berlin; Date-only 31.08./America/New_York | Berliner 31.08.06:00 bis 01.09.06:00: mehrdeutig trotz gespeichertem Augustdatum. |
| September/Berlin; Date-only 30.09./America/New_York | Berliner 30.09.06:00 bis 01.10.06:00: mehrdeutig. |
| September/Berlin; Date-only 31.08. oder 01.10./Europe/Berlin | Außerhalb; bloße Grenzberührung zählt nicht. |

### Ergebnis, Datenlücke und Ausschluss

Zeilen halten Periodenzustand, Quellen-/Betragsqualifikation und Währungsfilter
getrennt. `reasons[]` darf mehrere Gründe enthalten; jede SELL-ID zählt trotzdem
genau einmal. Implementierte Zeilengründe: `CURRENCY_UNKNOWN`, `CURRENCY_MIXED`,
`HISTORY_INVALID`, `PERIOD_AMBIGUOUS`, `PERIOD_UNKNOWN`, `OTHER_CURRENCY` und
`OUTSIDE_PERIOD`. Eine nicht projektierbare oder unvollständige Owner-Historie
liefert `HISTORY_INVALID`. `TRADE_CANCELLED` steht ausschließlich in
`excluded_trades[].reason`; stornierte Trades erzeugen keine SELL-Zeilen in
`items[]`. `counts.cancelled` zählt Trades, die übrigen Ergebniszähler zählen SELLs.
Fachliche Ausschlüsse sind keine erfolgreichen oder verlorenen Trades.

Für die wirksamen SELLs eigener nicht stornierter Trades gilt zunächst:
`examined = in_period + outside_period + period_ambiguous + period_unknown`.
Für den ausgewählten Währungsumfang werden sicher fremde Verkaufswährungen
ausgefiltert; unbekannte Verkaufswährung verschwindet nicht aus dem EUR-Bericht.
Der entsprechende Kandidatenzähler zerfällt eindeutig in verwendbare Beiträge
und noch relevante ungeklärte/nicht auswertbare Fälle. BUYs, mehrfache Kaufquellen
und Lessonlinks vergrößern keinen SELL-Zähler. Supersedierte IDs bleiben
historischer Drill-down, nicht Teil der wirksamen Grundgesamtheit.

| Zustand dieser Währungsauswahl | `total` | `subtotal` | Bedeutung |
|---|---|---|---|
| `EMPTY`: kein passender SELL, keine relevante Unklarheit | `"0"` | `null` | Vollständig geprüfte leere Auswahl; UI sagt „Keine wirksamen Verkäufe in dieser Auswahl“. |
| `COMPLETE`: mindestens ein verwendbarer SELL, keine relevante Lücke | Decimalstring, auch `"0"` | `null` | Vollständiges Bruttoergebnis dieses engen Umfangs. |
| `PARTIAL`: verwendbare Beiträge und relevante Lücken | `null` | Decimalstring, auch `"0"` | Bekannte Teilsumme; Gesamtsumme nicht berechenbar. |
| `NOT_COMPUTABLE`: relevante Fälle, kein verwendbarer Beitrag | `null` | `null` | Keine belastbare Geldsumme; weder null Euro noch leere Auswahl. |

Sicher außerhalb liegende Verkäufe oder sicher andere Verkaufswährungen machen
die angefragte Auswahl nicht unvollständig. Unklare Periodenzugehörigkeit blockiert
eine Gesamtsumme, soweit der Fall zur gewählten Währung gehören könnte. Normale
Filterausschlüsse und ihre Mengen bleiben sichtbar. Ein mathematischer
Nullbeitrag ist eine verwendbare SELL-Zeile; ein gerundetes 0,00 kann einen
von null verschiedenen Rohwert besitzen.

### Decimal, Anzeige, Definition und Herkunft

Berechnung bleibt beim Backend-Owner mit unveränderter Decimal-Operationsfolge.
Die API überträgt ausschließlich endliche Decimalstrings oder `null`, keine
JSON-Floats/NaN. Execution-Numeric-Präzision und unquantisierte Domainwerte bleiben
unterscheidbar. Direkte SELL-Deltas werden in stabilem Owner-Schlüssel summiert,
niemals als Differenz aktueller Positionssnapshots rekonstruiert.

Anzeige: vorhandene `CurrencyModel.minor_unit` mit verwendeter
`reference_version` aus demselben Lesezustand; `ROUND_HALF_EVEN` ausschließlich
für Anzeige. Backend liefert Roh- und Anzeigewerte, Stellenzahl und Regel;
Frontend führt keine Geldrechnung oder stille `Number`-/Float-Konversion aus.
Summen werden aus ungekürzten Beiträgen gebildet, danach angezeigt. Beispiel:
0,004 + 0,004 ergibt roh 0,008; angezeigte Einzelzeilen 0,00 + 0,00, Summe 0,01.
Die 0,01 Darstellungsdifferenz wird erklärt, keinem SELL als Fakt zugeschlagen.
Unklare Anzeigenreferenzen werden offengelegt; es gibt keine pauschalen zwei Stellen.

Der vorhandene Owner arbeitet ohne eigenen Kontextwechsel; die qualifizierte
Standardkonfiguration ist Decimal-Präzision 28. Periodische Dezimalbrüche können
Restwerte ergeben. Beispiel des unabhängigen Tests: Domain-PnL
`2.000000000000000000000000001` und Kostenrest `1E-27` vor der bisherigen
Vollverkaufs-Nullsetzung. Trace und Bericht dürfen diese Werte nicht still
an eine idealisierte rationale Rechnung oder DB-Zehnstellenwerte angleichen.

Freigegebene Definitionskennung: `realized-gross-sell-v1`; keine FT-ID.
Antworten enthalten normalisierte Filter, Berichtszone, UTC-Grenzen,
Definitionsversion, eindeutig bezeichnete Lese-/Berechnungszeiten und eine
Quellenbasiskennung. Je Beitrag: Trade-/Produkt-/Execution-ID, genaue
Zeitpräzision, Menge/Preis, verwendeter Durchschnitt, Vor-/Nachbestand, vollständiger
Kostenbasispräfix, konkrete Währungsbestätigungs-IDs und Ausschluss-/Lückengründe.
Heutige Produktnamen dürfen zusätzlich angezeigt werden, werden als heutige
Anzeige gekennzeichnet und ersetzen keine historische Identität.

### Wissensstand, konsistenter Read und UI

V1 liest heute wirksame korrigierte Fakten über einen vergangenen Zeitraum.
Es rekonstruiert keinen damaligen Kenntnisstand. Eine Preis-/Datums-/Mengen- oder
Währungsbestätigungskorrektur kann frühere Berichte verändern. Die ursprüngliche
Execution und alte Journal-/Review-/Evidence-Inhalte bleiben historisch unverändert.

Technische Lesegrenze: eigener kurzer `REPEATABLE READ READ ONLY`-Vorgang am
Execution-Reader, vor dem ersten fachlichen SELECT eingerichtet, mit frischer
Session und `autoflush=False`. Die bestehende globale Engine-/Sessionisolation
bleibt unverändert. Alle benötigten Trade-/Storno-/Execution-/Supersession-,
Währungsevidenz- und Anzeigenreferenzdaten werden innerhalb dieser Grenze als
immutable Eingaben materialisiert. Danach endet die Transaktion; Berechnung,
Summary, Zähler, Zeilen und Details verwenden ausschließlich diesen Bestand.
Keine Lazy-Reads wirtschaftlicher Quellen nach der Grenze, keine FT-011-
Materialisierungssperren, kein `FOR UPDATE`, keine Kurse oder Lernzustände.

Begründung: Unter READ COMMITTED kann jeder folgende SELECT einen neuen
Quellenstand sehen; eine gemeinsame Session ändert dies nicht. PostgreSQLs
REPEATABLE READ hält den Snapshot der ersten nicht transaktionssteuernden
Anweisung für nachfolgende Reads fest. Das ist eine begrenzte Lesegarantie,
keine globale Serialisierbarkeitszusage. Quelle:
[PostgreSQL 17, Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html).

Der Reader wird auf den aktuellen Workspace und das Quelleninventar des Berichts
begrenzt; technische Query-/Request-Limits brechen sichtbar ab, statt eine
gekappte Historie als vollständig auszugeben. Keine Transaktion bleibt über
menschliche Interaktion offen. Ein dokumentierter Hash über die normalisierten
Filter, Definition und tatsächlich verwendeten Fakten-/Evidenz-/Referenzversionen
kennzeichnet die Berechnungsbasis. Zeitstempel allein genügt nicht; auch ein Hash
verspricht keine später wiederherstellbare historische Berichtssitzung.

Die kleinste UI liefert eine vollständige Antwort mit allen Beiträgen und
Herkunft; Tabellenseiten und Aufklappen arbeiten lokal mit diesem Bestand.
Summary ist nie eine Seitensumme. Spätere Requests lesen neu; bei geänderter
Basis wird die komplette Antwort ersetzt und der Wechsel angezeigt.
Verspätete Antworten dürfen nur ihren passenden Request-/Filterstand aktualisieren.
Keine persistente Berichtshistorie oder automatische Evidence folgt aus Lesen.

Vor Implementierungsabnahme müssen zwei echte PostgreSQL-Sessions eine parallel
committene Execution-Korrektur zwischen zwei Report-Reads koordinieren: die
offene Antwort bleibt vollständig alt, die neue Antwort vollständig neu.
Zusätzlich eine Datumsverschiebung über die Periodengrenze und eine Änderung der
Währungsevidenz prüfen. Zeilen, Quellen-IDs, Zähler und Summary müssen gemeinsam
geprüft werden; der Writer darf nicht von schreibenden Report-Sperren abhängen.
Der reine Owner-Trace allein implementiert oder qualifiziert diese
Berichtsgrenze nicht; dafür ist die eigene vertikale Qualifikation erforderlich.

## Definition of Ready vor der freigegebenen vertikalen Fortsetzung

| Voraussetzung | Entscheidung dieses Auftrags |
|---|---|
| Wirtschaftliche Fakten, wirksame Historie, Brutto-Average-Cost-Owner | Vorhanden; additive arithmetische Trace-Vorleistung im aktuellen Diff. |
| Historische Ausführungswährung | Additiver Erfassungs-/Bestätigungsvertrag ausdrücklich freigegeben; vor Verwendung separat technisch qualifizieren. Eine einzelne Bestandsbuchung bleibt ohne Erklärung unbekannt. Keine Nutzerdatenabdeckung behauptet. |
| Perioden-, Auswahl-, Lücken- und Anzeigenvertrag | Konkreter V1-Vertrag oben am 17.10.2026 ausdrücklich zur Umsetzung freigegeben. |
| Konsistenter reiner Bericht, API und Oberfläche | Technische Grenze und Abnahmefälle vorgegeben; nach qualifizierter Owner-Erfassung die vertikale Strecke umsetzen und nachweisen. |
| Freigabe dieser neuen Semantik / menschliche Abnahme | Die Nutzeranweisung „Ok, umsetzen“ akzeptiert den vorgelegten Vertrag und erlaubt Implementierung. Endabnahme des fertigen Schnitts, Release und Zielbetrieb bleiben gesondert. |

Der vorangegangene Diff lieferte die unabhängige Owner-Vorleistung und deren
[Qualifikationsnachweis](PERIOD_REALIZED_GROSS_QUALIFICATION.md).
M8-Statistiken, Gewinner-/Verliererkohorten, Trefferquote, Median, Profit-Faktor,
Prozessqualität, Diagramme und Export bleiben im bestehenden Backlog erhalten.
Netto, FX-Performance, Depot-Equity, Drawdown, TWR/IRR, Sharpe/Sortino,
Annualisierung, R-Multiples und Modellüberlegenheit erhalten dadurch keine
stillschweigende Semantik oder Abnahme.

**Freigegebene Fortsetzung:** die additive Execution-Währungsbestätigung beim
bestehenden Owner qualifizieren und darauf die vollständige vertikale
Berichtsstrecke umsetzen. Die Entscheidung muss nicht erneut eingeholt werden.
Die tatsächliche Durchführung dieses Auftrags und ihre verbleibenden Prüfgrenzen
stehen im [Berichtsqualifikationsnachweis](PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md).
