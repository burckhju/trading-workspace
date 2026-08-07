# Sprint 4 – Architekturvorschlag Marktanalyse

## Dokumentstatus

| Feld | Wert |
|---|---|
| Status | Proposed – Freigabe erforderlich |
| Datum | 2026-08-05 |
| Scope | Repository-Analyse, Auswirkungsanalyse, offene Fragen, Architekturvorschlag |
| Implementierung | Nicht begonnen |

## 1. Executive Summary

Sprint 4 soll die Marktanalyse als erstes fachliches Modul auf der vorhandenen providerunabhängigen Marktdaten-Infrastruktur aufbauen. Die bestehende Architektur unterstützt dieses Ziel grundsätzlich: Stammdaten (`market`), interne Marktdaten (`market_data`) und konkrete Provideradapter (`providers/eodhd`) sind getrennt. Das neue Modul darf ausschließlich stabile interne Verträge konsumieren.

Empfohlen wird ein eigenständiges Featurepaket `app/features/analysis/` mit Domain, Application Service, Persistence und API. Die Analyse-Domain erhält keinen Zugriff auf EODHD, HTTP, SQLAlchemy oder Provider-DTOs. Marktdaten werden über einen neuen internen lesenden Port aus `market_data` bezogen. Jede ausgeführte Analyse wird als unveränderlicher, versionierter Snapshot mit vollständiger Provenance und reproduzierbaren Eingaben persistiert.

Vor Implementierung ist eine fachliche Freigabe insbesondere zu Feature-ID, Analysemodell V1, Lebenszyklus, Qualitätsregeln und Versionierungsstrategie erforderlich.

## 2. Repository-Analyse

### 2.1 Architektur und Schichten

Das Backend folgt einer vertikalen Feature-Struktur:

- `features/market`: Owner von Basiswerten und Listings.
- `features/market_data`: providerunabhängige Marktdatenmodelle, Application Services und Persistenz.
- `providers/eodhd`: externer Adapter einschließlich Transport, Mapping und Resilience.
- `core/di`: Composition Root und technische Verdrahtung.
- `database`: SQLAlchemy-Basis und Session-Lifecycle.
- `shared`: technische beziehungsweise domänenübergreifende Hilfen.

Innerhalb implementierter Features sind Domain, Service, Persistence und API getrennt. FastAPI-Router verwenden Dependency Injection. SQLAlchemy ist nicht Bestandteil der Domain. Provider-DTOs verlassen den Adapter nicht.

### 2.2 Bestehende interne Marktdatenbasis

Vorhanden sind insbesondere:

- providerunabhängiges `DailyPrice`-Modell mit `Decimal`, UTC-Zeit, Währung, Providerherkunft, Qualitätsstatus und Warnungen,
- persistierte EOD-Preise mit eindeutiger Identität je Workspace, Listing, Handelstag und Preistyp,
- capability-basierte Provider-Protocols,
- explizite Import-Services und Unit-of-Work-Grenzen,
- Mapping zwischen internem Listing und Providersymbol,
- Cache-, Retry-, Rate-Limit- und Budget-Metadaten,
- REST-Endpunkte für Import und Provideradministration.

Für Marktanalyse fehlt derzeit ein stabiler interner **Read Port**, der bereits persistierte Marktdaten providerneutral nach Zeitraum und Listing bereitstellt. Der bestehende Import-Service ist ein Command und darf nicht als Analyseabhängigkeit missbraucht werden.

### 2.3 Frontend

Das Frontend ist featureorientiert. Aktuell existiert nur die Underlying-Oberfläche. API-Clients, Typen, Seiten und Tests liegen unter `src/features/<feature>`. Routing erfolgt zentral in `src/app/router.tsx`. Für Marktanalyse ist ein eigenes Frontend-Feature vorzusehen; keine Analysefachlogik gehört in React-Komponenten.

### 2.4 Tests und Qualität

Vorhanden sind Unit-, Integrations-, Contract- und E2E-Teststrukturen. Backend-Gates umfassen Ruff, Black, mypy, pytest und Coverage; Frontend-Gates umfassen TypeScript, ESLint, Prettier, Vitest-Coverage und Build.

Die mitgelieferten `.venv`- und `node_modules`-Verzeichnisse sind nach dem Entpacken nicht portabel. Deshalb konnten die Quality-Wrapper in dieser Analyseumgebung nicht erfolgreich ausgeführt werden. Die Fehler betreffen fehlende Runtime-Dateien der eingecheckten Umgebungen, nicht einen nachgewiesenen Fehler im Anwendungscode.

### 2.5 Dokumentation und Traceability

Die Dokumentation ist umfangreich und ADR-basiert. Für neue Features bestehen etablierte Ablagen unter:

- `docs/features/<feature>/`,
- `docs/decisions/`,
- `docs/implementation/`,
- `docs/planning/reviews/`,
- `docs/reference/`.

## 3. Kritische Inkonsistenz der Feature-ID

Die Sprintvorgabe nennt „FT-004 Marktanalyse“. Im verbindlichen Repository-Katalog gilt dagegen:

- FT-004 = Optionsscheinverwaltung,
- FT-006 = Marktanalyse.

Empfehlung: Marktanalyse in Code und Dokumentation als **FT-006** weiterführen und Sprint 4 lediglich als zeitlichen Sprint bezeichnen. Eine Umnummerierung bestehender Features wäre ein Breaking Change der fachlichen Traceability. Falls die neue Sprintvorgabe bewusst den Katalog ersetzt, ist zuerst ein gesondertes ADR mit vollständiger Migration aller Referenzen erforderlich.

## 4. Auswirkungen auf bestehende Module

### 4.1 `market`

- Nur lesende Referenz auf Underlying und Listing.
- Keine Änderung an Ownership oder Stammdatenregeln.
- Benötigt einen stabilen Query-Vertrag zur Prüfung, ob Underlying und gewähltes Listing existieren und operativ verwendbar sind.
- Keine Fremdschlüsselabhängigkeit auf veränderliche natürliche Kennungen; ausschließlich UUIDs.

### 4.2 `market_data`

- Ergänzung eines providerneutralen Query Ports für persistierte Marktdaten.
- Keine direkte Nutzung von EODHD-Adapter oder Import-Service durch Analyse.
- Bestehende Marktdatenmodelle bleiben unverändert.
- Optionaler neuer Read Service kann Datenvollständigkeit, Sortierung und Zeitraumbeschränkung zentral garantieren.

### 4.3 `providers/eodhd`

- Keine fachliche Änderung.
- Keine Importabhängigkeit aus `analysis`.
- Provider bleibt ausschließlich über `market_data` erreichbar.

### 4.4 `core/di`

- Composition Root ergänzt Factory/Context Manager für Analyse-Services.
- Verdrahtung erfolgt gegen Protocols, konkrete SQLAlchemy-Reader werden nur im Composition Root eingesetzt.
- Keine Providerwahl in der Analyse-Domain.

### 4.5 Datenbank und Migrationen

- Neue additive Tabellen und Indizes.
- Keine Änderung oder Löschung bestehender Spalten.
- Migration `0003` baut auf der Market-Data-Migration auf.
- Historische Analyse-Snapshots bleiben unverändert; Korrekturen erzeugen neue Versionen beziehungsweise neue Ausführungen.

### 4.6 REST API

- Neue additive Route, empfohlen `/api/v1/market-analyses`.
- Bestehende Routen bleiben unverändert.
- Idempotenz und Concurrency werden explizit spezifiziert.

### 4.7 Frontend

- Neues Feature `src/features/analysis/`.
- Wiederverwendung gemeinsamer HTTP- und Feedback-Komponenten, soweit fachlich passend.
- Keine Berechnung technischer Indikatoren im Browser.

## 5. Fachliche Definition Marktanalyse V1

Eine Marktanalyse ist ein nachvollziehbarer, vom Benutzer ausgelöster Berechnungsvorgang für genau einen Basiswert und genau ein Listing auf Basis eines abgeschlossenen Marktdaten-Snapshots. Sie liefert beschreibende und regelbasierte Ergebnisse, aber keine Kauf-, Verkaufs-, Halte-, Produkt- oder Positionsgrößenentscheidung.

### 5.1 Analyseobjekte

1. **MarketAnalysis** – fachlicher Kopf und Lebenszyklus.
2. **MarketAnalysisVersion** – unveränderliche ausgeführte Version.
3. **MarketDataSnapshot** – exakt verwendete Marktdatenzeilen plus Provenance.
4. **AnalysisModelReference** – Modellkennung und semantische Version.
5. **AnalysisParameters** – validierte, kanonisch serialisierte Eingaben.
6. **AnalysisResult** – Kennzahlen, Bewertungen, Hinweise und Qualitätsstatus.
7. **AnalysisEvent** – Auditspur der Statusübergänge.

### 5.2 Mindestinhalt jeder ausgeführten Version

- Analyse-ID,
- Versionsnummer,
- Analysezeitpunkt in UTC,
- Workspace-ID,
- Underlying-ID,
- Listing-ID,
- Datenquelle beziehungsweise Providerherkunft,
- konkrete verwendete Marktdaten einschließlich Handelstag und Werte,
- Analysemodell-ID und Modellversion,
- Eingabeparameter in kanonischer Form,
- Einzelergebnisse und aggregierte Bewertung,
- Hinweise und Warnungen,
- Qualitätsstatus,
- deterministischer Input-Hash,
- Erstellungsakteur beziehungsweise Auslöser,
- technische Correlation-ID.

### 5.3 Analysemodell V1 – vorgeschlagener Scope

Für die erste Version wird ein transparentes EOD-Trend- und Momentum-Modell vorgeschlagen:

- Schlusskurs beziehungsweise Adjusted Close nach expliziter Parameterwahl,
- einfache gleitende Durchschnitte für kurz, mittel und lang,
- prozentuale Rendite über definierte Fenster,
- realisierte Volatilität aus täglichen logarithmischen Renditen,
- Abstand zum Periodenhoch und Periodentief,
- Datenvollständigkeit und Aktualität,
- regelbasierte Teilbewertungen je Kriterium.

Nicht im V1-Scope:

- Intraday-Daten,
- Forecasting oder Machine Learning,
- Sentiment- oder Fundamentaldaten,
- automatische Handelsentscheidung,
- Optionsscheinbewertung,
- automatische Nachladung externer Daten während der Berechnung.

### 5.4 Parameter V1

Empfohlene explizite Parameter:

- `price_field`: `CLOSE` oder `ADJUSTED_CLOSE`,
- `short_window`: positive ganze Zahl,
- `medium_window`: positive ganze Zahl,
- `long_window`: positive ganze Zahl,
- `momentum_windows`: geordnete Liste positiver ganzer Zahlen,
- `volatility_window`: positive ganze Zahl,
- `range_window`: positive ganze Zahl,
- `minimum_required_observations`: positive ganze Zahl,
- `maximum_data_age_days`: nichtnegative ganze Zahl,
- `annualization_factor`: positiver Decimal-Wert,
- Schwellenwerte je Bewertungskriterium als `Decimal`,
- Rundungsskala und Rundungsmodus.

Alle Parameter werden in der ausgeführten Analyse persistiert. Defaults gehören zur Modellversion und werden beim Start in konkrete Werte aufgelöst; historische Ergebnisse dürfen niemals von später geänderten Defaults abhängen.

### 5.5 Bewertungskriterien V1

Bewertungen sollen keine Handlungsempfehlung ausdrücken. Empfohlene neutrale Klassifikation:

- `POSITIVE`,
- `NEUTRAL`,
- `NEGATIVE`,
- `NOT_EVALUABLE`.

Kriterien:

- kurzfristiger Trend,
- mittelfristiger Trend,
- langfristiger Trend,
- Momentum je Fenster,
- Volatilitätsband,
- Position innerhalb der Handelsspanne,
- Datenaktualität,
- Datenvollständigkeit.

Jedes Kriterium enthält:

- Kriteriums-ID und Regelversion,
- Eingabewerte,
- Formel beziehungsweise Regelkennung,
- Schwellenwerte,
- Ergebniswert,
- Klassifikation,
- textuelle Begründung,
- Qualitätsstatus.

Eine optionale Gesamtklassifikation darf nur als transparente, versionierte Aggregationsregel erfolgen. Sie darf nicht als Handelsentscheidung benannt oder dargestellt werden.

### 5.6 Qualitätsstatus

Empfohlene Statuswerte:

- `VALID` – vollständig und ohne relevante Warnung,
- `VALID_WITH_WARNINGS` – berechenbar, aber mit dokumentierten Einschränkungen,
- `INSUFFICIENT_DATA` – nicht genügend Beobachtungen,
- `STALE_DATA` – letzte Marktdaten älter als erlaubt,
- `INVALID_INPUT` – Parameter oder Daten verletzen Invarianten,
- `FAILED` – technischer oder unerwarteter Berechnungsfehler.

Der fachliche Qualitätsstatus ist getrennt vom Lebenszyklusstatus.

## 6. Lebenszyklus und Statusübergänge

### 6.1 Status

- `DRAFT`: Analyseauftrag angelegt, noch nicht ausgeführt.
- `RUNNING`: Ausführung wurde atomar beansprucht.
- `COMPLETED`: Ergebnis erfolgreich und unveränderlich persistiert.
- `COMPLETED_WITH_WARNINGS`: Ergebnis persistiert, relevante Qualitätswarnungen vorhanden.
- `NOT_EVALUABLE`: deterministisch nicht berechenbar, zum Beispiel zu wenig Daten.
- `FAILED`: technische Ausführung fehlgeschlagen.
- `SUPERSEDED`: ältere Version wurde durch eine neue Version ersetzt; historisch weiterhin lesbar.

### 6.2 Erlaubte Übergänge

```text
DRAFT -> RUNNING
RUNNING -> COMPLETED
RUNNING -> COMPLETED_WITH_WARNINGS
RUNNING -> NOT_EVALUABLE
RUNNING -> FAILED
COMPLETED -> SUPERSEDED
COMPLETED_WITH_WARNINGS -> SUPERSEDED
NOT_EVALUABLE -> SUPERSEDED
FAILED -> RUNNING          (expliziter Retry derselben Draft-Version, falls keine Ergebnisse persistiert wurden)
```

Keine Rückkehr abgeschlossener Versionen in `DRAFT`. Eine fachlich geänderte Analyse erzeugt eine neue Version. Statusänderungen werden als Audit Events persistiert.

## 7. Vorgeschlagenes Domain Model

```text
MarketAnalysis
- id: UUID
- workspace_id: UUID
- underlying_id: UUID
- listing_id: UUID
- status: AnalysisLifecycleStatus
- current_version: int
- created_at: datetime UTC
- updated_at: datetime UTC
- optimistic_lock_version: int

MarketAnalysisRun
- id: UUID
- analysis_id: UUID
- version: int
- model_id: str
- model_version: str
- parameters: canonical object
- input_hash: str
- analysis_time: datetime UTC
- started_at: datetime UTC
- completed_at: datetime UTC | None
- quality_status: AnalysisQualityStatus
- lifecycle_status: AnalysisLifecycleStatus
- warnings: tuple[str, ...]
- notes: tuple[str, ...]
- result: AnalysisResult | None

MarketDataSnapshot
- run_id: UUID
- listing_id: UUID
- start_date: date
- end_date: date
- price_type: PriceType
- rows: tuple[DailyPriceSnapshotRow, ...]
- providers: tuple[MarketDataProvider, ...]
- retrieved_at_min/max: datetime UTC
- snapshot_hash: str

CriterionResult
- criterion_id: str
- rule_version: str
- inputs: canonical object
- thresholds: canonical object
- numeric_value: Decimal | None
- classification: CriterionClassification
- explanation: str
- quality_status: AnalysisQualityStatus
```

Domainobjekte werden als immutable Dataclasses modelliert. Berechnungen sind reine Funktionen beziehungsweise versionierte Model-Implementierungen. JSON-Payloads werden an der Domain-Grenze in typisierte Value Objects überführt.

## 8. Reproduzierbarkeit

Eine Berechnung gilt nur dann als reproduzierbar, wenn gespeichert werden:

1. genaue Modell- und Regelversion,
2. vollständig aufgelöste Parameter,
3. exakte Reihenfolge und Werte aller Eingabedaten,
4. Dezimal- und Rundungsregeln,
5. Zeitzonen- und Handelstagssemantik,
6. verwendetes Preisfeld,
7. kanonische Serialisierung,
8. kryptografischer Hash von Snapshot und Gesamteingabe,
9. Ergebnis und Teilbegründungen.

Wiederholung bedeutet: dieselbe Modellimplementierung plus derselbe kanonische Input erzeugt denselben kanonischen Output. Der erneute Abruf „gleicher Tage“ vom Provider reicht nicht aus, da Provider historische Werte korrigieren können.

## 9. Persistence Model

Empfohlene additive Tabellen:

- `market_analyses`
- `market_analysis_runs`
- `market_analysis_snapshot_rows`
- `market_analysis_criterion_results`
- `market_analysis_events`

Wichtige Constraints:

- Unique `(analysis_id, version)`,
- Unique `(workspace_id, analysis_id)`,
- Unique `(run_id, sequence_number)`,
- positive Versionsnummern,
- UTC-Zeitstempel,
- Status- und Quality-Enums als validierte Strings,
- Snapshotwerte als `NUMERIC`, niemals Float,
- unveränderliche Run- und Snapshotzeilen nach Abschluss,
- FK auf Underlying und Listing mit restriktivem Löschen,
- Indizes auf Workspace, Underlying, Listing, Status und Analysezeitpunkt.

JSON kann für kanonische Parameter und strukturierte Result-Metadaten verwendet werden, aber zentrale filter- und constraintrelevante Felder bleiben relational. Snapshot-Preiszeilen werden relational persistiert, um Reproduzierbarkeit und Prüfbarkeit nicht in einer undurchsichtigen Blob-Struktur zu verstecken.

## 10. Interne Ports und Application Services

### 10.1 Neue interne Ports

```python
class HistoricalDailyPriceReader(Protocol):
    async def list_daily_prices(
        self,
        workspace_id: UUID,
        listing_id: UUID,
        start_date: date,
        end_date: date,
        price_type: PriceType,
    ) -> tuple[DailyPrice, ...]: ...

class UnderlyingListingReader(Protocol):
    async def get_analysis_subject(
        self, workspace_id: UUID, underlying_id: UUID, listing_id: UUID
    ) -> AnalysisSubject | None: ...

class MarketAnalysisRepository(Protocol): ...
class MarketAnalysisUnitOfWork(Protocol): ...
class AnalysisModel(Protocol): ...
class AnalysisModelRegistry(Protocol): ...
```

Der `HistoricalDailyPriceReader` gehört fachlich zur öffentlichen Servicegrenze von `market_data`, nicht zum Providerpaket. Seine SQLAlchemy-Implementierung liest ausschließlich persistierte validierte Preise.

### 10.2 Application Services

- `CreateMarketAnalysisService`
- `RunMarketAnalysisService`
- `GetMarketAnalysisService`
- `ListMarketAnalysesService`
- `CreateAnalysisVersionService`
- optional `RetryFailedAnalysisService`

`RunMarketAnalysisService` orchestriert:

1. Analyse und Subject laden,
2. Status atomar auf `RUNNING` setzen,
3. Modell und konkrete Version auflösen,
4. Parameter validieren und Defaults materialisieren,
5. persistierte Marktdaten lesen,
6. Snapshot kanonisieren und hashen,
7. reine Modellberechnung ausführen,
8. Ergebnisse, Kriterien, Snapshot und Events in einer Transaktion persistieren,
9. finalen Status setzen.

Keine Providerabfrage innerhalb der Berechnung. Ein fehlender Datenbestand wird als fachlicher Zustand behandelt; ein separater Marktdatenimport bleibt eine explizite vorgelagerte Aktion.

## 11. REST API Vorschlag

Basisroute: `/api/v1/market-analyses`

- `POST /market-analyses` – Draft anlegen.
- `GET /market-analyses` – filterbare Liste.
- `GET /market-analyses/{analysis_id}` – Kopf und aktuelle Version.
- `POST /market-analyses/{analysis_id}/runs` – neue Version anlegen und synchron ausführen.
- `GET /market-analyses/{analysis_id}/runs/{version}` – vollständiges Ergebnis.
- `GET /market-analyses/{analysis_id}/runs/{version}/snapshot` – verwendete Daten.
- `POST /market-analyses/{analysis_id}/runs/{version}/retry` – nur für zulässigen Fehlerstatus.

Für V1 wird synchrone Ausführung empfohlen, solange der definierte EOD-Datenumfang klein und begrenzt ist. Asynchrone Jobs würden zusätzliche Infrastruktur und Statuskomplexität erzeugen. Request-Limits verhindern ungebundene Berechnungen.

HTTP-Konflikte:

- `404` unbekanntes Objekt,
- `409` ungültiger Statusübergang oder Optimistic-Concurrency-Konflikt,
- `422` ungültige Parameter,
- fachlich `NOT_EVALUABLE` bleibt ein erfolgreich persistiertes Ergebnis und kein HTTP-Fehler.

## 12. Frontend Vorschlag

Struktur:

```text
src/features/analysis/
  components/
  pages/
  services/
  types/
  index.ts
```

V1-Seiten:

- Analyseliste mit Status, Basiswert, Modellversion, Zeitpunkt und Qualität,
- Analyse anlegen beziehungsweise Parameter prüfen,
- Analyseergebnis mit Kennzahlen, Kriterien und Begründungen,
- Marktdaten-Snapshot als prüfbare Tabelle,
- Versionshistorie und Auditspur.

UI-Regeln:

- klare Trennung von Lebenszyklus- und Qualitätsstatus,
- Warnungen sichtbar, nicht nur als Tooltip,
- Modellversion und Parameter immer einsehbar,
- keine Formulierungen wie „kaufen“, „verkaufen“ oder „Signal“,
- keine Berechnung im Frontend,
- Dezimalwerte werden nur formatiert, nicht fachlich gerundet.

## 13. Teststrategie

### Domain Unit Tests

- Parameterinvarianten,
- Statusmaschine vollständig positiv und negativ,
- deterministische Berechnungen,
- Decimal- und Rundungsregeln,
- Datenlücken und unzureichende Daten,
- Klassifikationsgrenzen exakt an Schwellenwerten,
- Hash-Stabilität und kanonische Serialisierung.

### Application Service Tests

- ausschließlich interne Ports,
- korrekte Orchestrierung und Transaktionsgrenzen,
- kein Provideraufruf,
- Wiederholbarkeit mit identischem Snapshot,
- Fehler- und Retrypfade,
- Optimistic Concurrency,
- Audit Events.

### Persistence Tests

- Migrations-Upgrade,
- Constraints und Indizes,
- Decimal-Roundtrip,
- Snapshot-Unveränderlichkeit,
- Repositoryfilter und Versionierung.

### API Tests

- DTO-Validierung,
- Statuscodes und Fehlerübersetzung,
- vollständige Provenance im Response,
- keine Breaking Changes bestehender OpenAPI-Pfade.

### Frontend Tests

- Seitenzustände Loading/Empty/Error/Success,
- sichtbare Warnungen und Qualitätsstatus,
- Parameter- und Ergebnisdarstellung,
- Snapshot und Versionsnavigation,
- API-Client-Verträge.

### E2E

- Basiswert mit vorhandenen EOD-Daten analysieren,
- Ergebnis und Snapshot öffnen,
- neue Version mit geänderten Parametern erzeugen,
- alte Version unverändert wiederfinden,
- unzureichende Daten transparent darstellen.

## 14. Vorgeschlagene ADRs

- ADR-S4-001: Feature-ID und Scope der Marktanalyse.
- ADR-S4-002: Eigenständige Analyse-Featuregrenze.
- ADR-S4-003: Persistierter Marktdaten-Snapshot für Reproduzierbarkeit.
- ADR-S4-004: Versionierte, deterministische Analysemodelle.
- ADR-S4-005: Analyse-Lebenszyklus und Statusmaschine.
- ADR-S4-006: Trennung von Lebenszyklusstatus und Qualitätsstatus.
- ADR-S4-007: Interner Market-Data Read Port ohne Providerabhängigkeit.
- ADR-S4-008: Synchrone Ausführung in Version 1.
- ADR-S4-009: Relationale Snapshot-Persistenz und kanonische Hashes.
- ADR-S4-010: Neutrale Bewertung ohne Handelsentscheidung.

## 15. Offene Fragen vor Freigabe

### Blockierend

1. Wird die Repository-Nomenklatur beibehalten: Marktanalyse = FT-006?
2. Ist der vorgeschlagene EOD-Trend-/Momentum-Scope das verbindliche Analysemodell V1?
3. Soll eine Gesamtklassifikation existieren oder ausschließlich Einzelkriterien?
4. Welche konkreten Defaultfenster und Schwellenwerte gelten fachlich?
5. Ist `ADJUSTED_CLOSE` bei Verfügbarkeit Standard, oder immer `CLOSE`?
6. Darf eine Analyse mehrere Providerherkünfte im Snapshot enthalten, oder muss ein Run homogen sein?
7. Was ist der fachliche Analysezeitpunkt: Ausführungszeitpunkt, letzter Handelstag oder beides?
8. Soll `FAILED -> RUNNING` als Retry derselben Version erlaubt sein, oder erzeugt jeder Retry zwingend eine neue Version?
9. Wer beziehungsweise was ist in V1 der Actor für Audit Events?
10. Muss das Ergebnis vom Benutzer explizit bestätigt/freigegeben werden?

### Nicht blockierend, aber vor API-Freeze zu klären

- maximale Historienlänge pro Run,
- Pagination und Filter der Analyseliste,
- Exportformat,
- Aufbewahrung und Löschregeln,
- Lokalisierung der Erklärtexte,
- Darstellung von Nicht-Handelstagen und Datenlücken,
- spätere Integration mit Candidate und TradePlan.

## 16. Risiken und Gegenmaßnahmen

| Risiko | Auswirkung | Gegenmaßnahme |
|---|---|---|
| Feature-ID-Konflikt | gebrochene Traceability | ADR vor Implementierung |
| Analyse liest Provider direkt | Architekturverletzung | interner Read Port und Importregeltests |
| Historische Providerkorrekturen | Ergebnis nicht reproduzierbar | persistierter Snapshot plus Hash |
| JSON-Blackbox | schlechte Prüfbarkeit | relationale Snapshot- und Kriterienzeilen |
| Defaults ändern sich | historische Abweichungen | materialisierte Parameter je Run |
| Float-Berechnung | instabile Resultate | ausschließlich Decimal und definierte Rundung |
| Bewertung wird als Signal verstanden | Verletzung der Systemgrenze | neutrale Begriffe und UI-Texte |
| Überladener V1-Scope | langer Sprint, hohe Fehlerrate | begrenztes EOD-Modell ohne Forecasting |
| Race Conditions bei Runs | doppelte Versionen | Unique Constraints und Optimistic Locking |
| Analyse startet Datenimport implizit | versteckte Seiteneffekte | getrennte explizite Commands |

## 17. Empfohlene Implementierungsreihenfolge nach Freigabe

1. ADRs und fachliche Spezifikation finalisieren.
2. Analyse-Domain, Parameter, Regeln und Statusmaschine implementieren.
3. Domain-Unit-Tests vollständig grünstellen.
4. internen `market_data` Read Port ergänzen.
5. Persistence Model und Migration implementieren.
6. Repositories und Unit of Work implementieren.
7. Application Services implementieren.
8. REST DTOs, Fehlerabbildung und Router ergänzen.
9. DI im Composition Root ergänzen.
10. Frontend-Feature implementieren.
11. Integration-, API-, Frontend- und E2E-Tests ergänzen.
12. Dokumentation, Traceability und Architecture Review abschließen.

## 18. Abschluss dieser Arbeitseinheit

### Erledigte Arbeiten

- Repository-Struktur und Git-Stand analysiert.
- Backend-, Frontend-, Datenbank-, DI-, Provider- und Testarchitektur geprüft.
- bestehende interne Market-Data-Verträge und Provenance-Regeln bewertet.
- Auswirkungen auf alle bestehenden Module beschrieben.
- fachliche Marktanalyse V1 vorgeschlagen.
- Analyseobjekte, Parameter, Kriterien, Ergebnis und Qualität definiert.
- Lebenszyklus und Statusübergänge vorgeschlagen.
- Domain-, Persistence-, API-, Service-, Frontend- und Testarchitektur entworfen.
- ADR-Bedarf und Risiken dokumentiert.

### Offene Punkte

Siehe Abschnitt 15. Die Feature-ID und das konkrete Modell V1 sind vor Implementierung zwingend freizugeben.

### Testergebnisse

- Keine Produktänderungen implementiert; daher keine neuen Tests.
- Backend-Quality-Skript konnte wegen einer nicht portablen, beschädigten mitgelieferten `.venv` nicht starten (`encodings` fehlte).
- Frontend-Quality-Skript konnte wegen unvollständiger mitgelieferter `node_modules` nicht starten (`typescript/lib/tsc.js` fehlte).
- Diese Befunde sind Umgebungs-/Packagingprobleme der ZIP und kein Nachweis fehlerhafter Anwendungstests.

### Dokumentationsstatus

- Architekturvorschlag vollständig.
- ADRs noch `Proposed` und noch nicht als Einzeldateien angelegt.
- Fachspezifikation und Traceability werden nach Freigabe finalisiert.

### Empfohlener nächster Schritt

Freigabe beziehungsweise Korrektur der blockierenden Entscheidungen in Abschnitt 15; anschließend Implementierung ab Domain und ADRs in kleinen, testbaren Arbeitseinheiten.
