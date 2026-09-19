# Positionsdetails: Kursverlauf und belastbare Datenverfügbarkeit

**Status:** Umsetzungsvorschlag / Review, keine implementierte oder freigegebene Runtime-Änderung.
**Prüfdatum:** 13.09.2026.
**Prüfbasis:** `97eb3ddcf148e82338a9fd851bbb47a98a5740a0`, anschließend gegen
`87d464f2d2b79d8ad08ca1f1951949cc62a49d38` einschließlich Merge von PR #202 abgeglichen.
**Arbeitspaket:** `POSITION-PRICE-HISTORY-001` — UX, PROVIDER_COVERAGE, INTEGRATION.

## 1. Befund und Entscheidungsvorschlag

Das aufgeklappte Positionsdetail soll einen tatsächlichen Kursverlauf zeigen, nicht eine
hochgerechnete Bewertung. Die Frontend-Erweiterung allein genügt dafür nicht.

| Datenpfad | Im geprüften Code vorhanden | Grenze für den Chart |
| --- | --- | --- |
| Basiswert | EODHD-Import abgeschlossener Tageskurse nach `daily_prices`; `MarketDataReader.list_daily_prices` | Tatsächliche lokale Bestände, Identität und Abdeckung seit Kauf sind nicht aus dem Repository beweisbar. |
| Optionsschein | Exakte Warrant-/Listing-/Providerzuordnung und `WarrantQuoteSnapshot`; bestehende Providerauflösung | Scheduler/Provider halten aktuelle Beobachtungen prozesslokal, keine belastbare fortlaufende Kurshistorie. |
| Automatischer Abruf | Bestehender Scheduler, Priorisierung gehaltener Instrumente, Budgets, Fehlerisolation und Diagnostik | Erfolgreicher Abruf beweist weder dauerhafte Speicherung noch vollständige Historie oder Ausführbarkeit. |
| Positionsdetails | Positionsdaten und Herkunftshinweise; keine Kurszeitreihe im Positions-DTO | Zusätzlicher, rein lesender Historienvertrag erforderlich. |

`MarketDataRefreshRuntime.status()` nennt ausdrücklich
`quote_storage=PROCESS_CACHE_WITH_ORIGINAL_TIMESTAMPS`.
`_warrant()` gibt Quote-Beobachtungen in der Jobdiagnostik zurück; `_underlying()` verwendet
den bestehenden persistenten `DailyPriceImportService`. Initial werden bis zu 400 Kalendertage
angefordert, später sieben Tage überlappend. Das garantiert keine Historie seit einem älteren Kauf.
Die tatsächliche Rückgabe kann kürzer sein. [S1–S4]

PR #202 verbessert die verifizierte EODHD-Katalogzuordnung fehlender Basiswert-Mappings.
Er ist berücksichtigt, aber kein Beleg eines aktualisierten Nutzer-Deployments und keine
Optionsschein-Historisierung. Die betroffenen Speicher-/Leserverträge bleiben unverändert. [S5]

**Vorschlag:** Bestehende Market-Data-Pfade erweitern: Basiswert-EOD wiederverwenden,
Optionsscheinbeobachtungen dauerhaft speichern und beide getrennt über einen lesenden
Positionskontext ausliefern. Kein zusätzlicher Quote-Resolver, Provider-Scheduler oder
Handels-/Positionsrechner. Eine rückwirkende Optionsscheinhistorie bleibt eine separat zu
belegende Fähigkeit der bereits vorgesehenen Quellen, kein Versprechen der Oberfläche.

## 2. Verfügbarkeit sicherstellen — ohne Vollständigkeit vorzutäuschen

### 2.1 Prüfung je tatsächlich gehaltener Identität

Die Instrumentliste stammt aus dem vorhandenen Positions-/Trade-Lesepfad. Keine manuelle
ISIN-Liste, keine Anlage eines Diagnoseinstruments und keine Zuordnung anhand ähnlicher Namen.
Zu prüfen sind jeweils Warrant bzw. Basiswert, das verifizierte Listing, Quotierungswährung,
Provider-Mapping einschließlich Version, Preisart und ursprünglicher Kurszeitpunkt.

Der Abdeckungsnachweis braucht pro angefragter Serie:

- angefragten Zeitraum und effektiven Kaufbeginn; frühesten und letzten vorhandenen Punkt;
- Anzahl echter Punkte, bekannte Lücken und Begründung einer fehlenden Serie;
- Herkunft, Preisart, Währung, Zeitpräzision und Art der Serie: abgeschlossene Tageskurse oder
  unregelmäßige beobachtete Quotes;
- getrennten Zustand des Abrufs, der dauerhaften Speicherung und der historischen Abdeckung.

Ein erster und letzter Datenpunkt beweisen keine lückenlose Historie. Für Tageskurse ist der
geprüfte Handelskalender relevant. Bei unregelmäßigen Quote-Beobachtungen lässt sich aus einem
regelmäßig erfolgreichen Polling keine vollständige Börsen-Tickhistorie ableiten. Ohne
verlässlichen Erwartungskalender bzw. Feedvertrag bleibt Vollständigkeit unbekannt.

### 2.2 Rückwirkendes Nachladen

Basiswerte verwenden den bestehenden EODHD-Import mit genauer Zeitraumsvorgabe,
aktiver verifizierter Zuordnung und unveränderten Kontingenten. Vor einem Nachladeauftrag
werden bereits vorhandene Bereiche geprüft. Der Chart-GET löst diesen Import niemals aus.
Ein größerer Zeitraum als der automatische Initialimport erfordert einen expliziten,
budgetierten Nachladepfad über denselben Importservice.

Für Optionsscheine sind zuerst Frankfurt, Vontobel und Stuttgart innerhalb ihrer bestehenden
Providergrenzen zu prüfen. Ein heutiger Last-/Close-/Bid-/Ask-Wert ist kein historischer Feed.
Ein Websitechart beweist keine erlaubte maschinelle Speicherung. Vontobels offizielle
Deritrade-Dokumentation beschreibt API-Autorisierung sowie Reference Data und Quoting/Trading;
daraus ergibt sich kein bestätigter frei nutzbarer Historienzugang für alle gehaltenen
Optionsscheine. Deutsche Börse beschreibt historische Datenprodukte, aber auch das ist noch
kein Nachweis eines berechtigten, instrumentgenauen Zugangs im Workspace. [E1–E3]

Ein Backfill wird erst nach Nachweis von exakter ISIN, Quelle/Handelsplatz, Preisart,
Währung, Datumspräzision, tatsächlicher Zeitraumabdeckung und Nutzungsrecht für Abruf,
Speicherung und Anzeige zugelassen. Keine bezahlte Aktivierung, keine neuen Zugangsdaten,
keine Umgehung von 401/403 und kein automatischer Providerwechsel.

### 2.3 Künftige Beobachtungen dauerhaft erhalten

Der vorhandene Abruf liefert nach erfolgreicher Identitäts-/Schema-/Währungsprüfung
normalisierte Beobachtungen an einen **Market-Data-eigenen Persistenzservice**.
Er verwendet `WarrantQuoteSnapshot` und das umgebende Provider-Ergebnis als Ausgangsvertrag.
Der konkrete Einhängepunkt muss auch indikative Referenzen berücksichtigen und darf
historisch brauchbare Daten nicht allein wegen fehlender aktueller Ausführbarkeit verwerfen.
Neue Quellensemantik wird nicht im Scheduler erfunden. [S1, S6]

Speicherfehler sind getrennt von Providererfolg sichtbar. Ein Quote im Cache darf nicht als
persistierter Historienpunkt gezählt werden. Wiederholungen sind idempotent und nutzen die
bestehenden Budgets/Abrufmechanismen. Eine ausgefallene Historisierung darf keine richtige
Tradebuchung verändern oder eine unabhängig funktionierende Bewertung als erfolgreich
historisiert ausgeben. Neustarts löschen keine bereits persistierten Beobachtungen.

Ohne nachgewiesenen Backfill heißt die Anzeige **„Beobachtete Kurse ab …“**, nicht
„Vollständiger Kursverlauf seit Kauf“. Bereits vor Einführung verlorene Cachewerte werden
weder geschätzt noch rückwirkend aus dem Basiswert modelliert.

## 3. Architektur und Datenvertrag

### 3.1 Eigentümer und Abhängigkeiten

| Bestandteil | Eigentümer / vorgesehene Erweiterung |
| --- | --- |
| Transport, Mapping, Normalisierung | Bestehende `backend/app/providers/`-Adapter und Markt-Datenverträge |
| Abrufplanung | Bestehender `MarketDataRefreshRuntime`; kein Browser-Polling gegen Provider |
| Historienpersistenz und Qualitätsprüfung | `backend/app/features/market_data/`, dessen Service-/Repository-/Unit-of-Work-Grenzen |
| Effektive Ausführungen und Positionskontext | Vorhandene öffentlichen Trade-Management-Lesepfade; keine neue Projektion aus Browserdaten |
| Positionsbezogene Zusammenstellung | Dünner öffentlicher Leseservice im Operational Workspace, delegiert an Market Data |
| Anzeige | `frontend/src/features/operational_workspace/`; Chart und Ladezustand unter `PositionDetails` |

Die verbindliche Source Architecture untersagt direkte Zugriffe auf interne Bestandteile
anderer Features. Deshalb exportiert Market Data einen Historien-Lesevertrag; der
Operational Workspace greift nicht selbst auf fremde SQLAlchemy-Modelle zu. Die bestehende
Tabelle bleibt leichtgewichtig und erhält nicht sämtliche Zeitreihen als zusätzliche Felder. [S7]

### 3.2 Persistenzvorschlag

Eine additive Erweiterung innerhalb von Market Data speichert Optionsscheinbeobachtungen.
`daily_prices` besitzt bisher Eigentümerbezüge zu `listings` oder `market_data_instruments`,
nicht unmittelbar zu `warrant_listings`. Optionsscheine dürfen nicht durch einen scheinbar
passenden Basiswert-Listing-Schlüssel in diese Tabelle eingeschleust werden. [S2]

Der neue Vertrag benötigt mindestens Workspace, Warrant-Identität, ursprüngliche
WarrantListing-/Mappingreferenz, Quelle und Provideridentität, Emittenten-/Börsenmodus,
Quotierungswährung, Preisart und unveränderte Dezimalwerte. Dazu kommen Quellzeit bzw.
Quell-Handelstag, Zeitpräzision/Zeitzone, ursprünglicher Abrufzeitpunkt, Speicherzeitpunkt,
Delay, Handelsstatus, Qualitätsgründe und nachvollziehbare Normalisierungsversion.
Eine Emittentenindikation erhält keinen erfundenen Handels-MIC.

Bid, Ask, Last und Previous Close bleiben typisiert; eine Serie wechselt nicht unsichtbar
zwischen ihnen. Wiederholtes Laden desselben Quellereignisses erzeugt keinen neuen Punkt.
Ein gleicher Preis zu einem späteren echten Quellzeitpunkt ist dagegen eine neue Beobachtung.
Idempotenz berücksichtigt Quellereignis/Identität und normalisierten Inhalt, nicht bloß den
Preis oder die Abrufzeit. Widersprüchliche Revisionen desselben Ereignisses werden kenntlich
und nachvollziehbar versioniert, nicht still überschrieben. Keine vollständigen Website-
Rohantworten oder geheimnishaltigen URLs als Nebenprodukt archivieren.

Retention, Backup und eine eventuell erlaubte Aggregation werden vor Aktivierung ausdrücklich
festgelegt. Keine automatische Löschung beim Positionsschluss. Downsampling betrifft die
Anzeige; eine Stichprobensammlung wird nicht zu echten OHLC-Kerzen oder amtlichen Schlusskursen.
Eine eigene Timeseries-Datenbank, zusätzliche Worker oder Replikate sind hierfür nicht erforderlich.
Die dokumentierte Single-Backend-Grenze bleibt bestehen. [S4]

### 3.3 Rein lesende API — vorgeschlagen, noch nicht vorhanden

Vorgeschlagener Vertrag:

```text
GET /api/v1/operational-workspace/positions/{position_id}/price-history
    ?instrument=WARRANT|UNDERLYING
    &range=SINCE_ENTRY|1M|3M|ALL_AVAILABLE
```

Die konkrete Route wird vor Implementierung mit den vorhandenen Positionsrouten abgeglichen.
Der Server prüft Workspace und Positionszuordnung und löst Warrant/Basiswert selbst auf;
keine frei zusammensetzbaren Provider-Symbole oder fremden Instrument-IDs aus dem Browser.
Es erfolgen keine Provideraufrufe, Imports, Mappingaktivierungen oder wirtschaftlichen Writes.
Ungültige Parameter und fremder Positionskontext sind keine vermeintlich leere Historie.

Das Response-DTO enthält `instrument`, `requested_range`, `available_range`, `as_of`,
`coverage`, `warnings` und `series[]`. Eine Serie beschreibt Quelle/Listing, Währung,
Preisart, Preismaßstab und Datenart; Punkte enthalten `observed_at` oder `trading_date`,
Zeitpräzision und einen Dezimalstring. Vorgeschlagene Abdeckungszustände
`COMPLETE`, `PARTIAL`, `EMPTY`, `UNKNOWN` sind **keine neuen produktiven
Bewertungs- oder Analyse-Policyzustände**. Abruf-/Speicherfehler bleiben davon getrennt.

`WarrantQuoteSnapshot` erlaubt bei Referenzpreisen einen fehlenden `observed_at`.
Solche Werte dürfen ohne belegbaren Quelltag nicht auf der Zeitachse erscheinen.
`retrieved_at` darf diese Lücke nicht ersetzen. Ein alter, zeitlich korrekt belegter
Historienpunkt bleibt darstellbar; sein Alter allein macht die historische Aussage nicht
ungültig. Die Aktualität des letzten Kurses und die aktuelle Ausführbarkeit sind getrennte
Hinweise. Der Chart stellt niemals eine Orderfreigabe dar. [S6]

## 4. Oberfläche und unveränderte Regeln

Der Zeitraum „Seit Kauf“ verwendet die effektive Execution History einschließlich
Datumskorrekturen, nicht Planfreigabe oder Erfassungszeit. Date-only-Käufe bleiben date-only;
Teilverkäufe setzen den Beginn nicht zurück. Eine Korrektur invalidiert den Positionskontext
und den betroffenen Chart-Cache, nicht die Quellkurse selbst.

Standard ist das ausgewählte Optionsscheinprodukt. Der Basiswert ist ein eindeutig
beschrifteter separater Umschalter, kein Ersatzkurs bei fehlender Produkthistorie.
Ein optionaler aktueller Ø-Einstand wird nur in belegbar gleicher Währung und Preisbasis
angezeigt und ausdrücklich als **heutiger** Referenzwert beschriftet; er ist keine historische
Einstandskurve. Basiswert-Stop und -Ziel gehören nicht in den Optionsscheinchart.
Im ersten Umfang sind keine Stop-/Ziel-Overlays oder neuen Hoch-/Performancekennzahlen nötig.
Keine Änderung an Phase, Score, dynamischem Stop, Modell oder Ausführungsregeln.

Quelle, Währung, Preisart, Abdeckungsbeginn und Lücken sind sichtbar. Ein Einzelwert wird
als Punkt und nicht als erfundene Linie dargestellt. Bekannte Ausfälle sowie Wechsel von
Quelle, Währung oder Preismaßstab werden nicht glatt verbunden. Keine fehlenden Werte als
null, kein Forward-Fill und keine geglättete Scheinpräzision. Tastaturbedienbare Zeitraumwahl,
lesbare Zusammenfassung und alternative Punktetabelle ergänzen die Grafik.

Daten werden erst beim Aufklappen geladen. Wiederverwendbarer Request-Cache, Abbruch und
Schutz vor verspäteten Responses verhindern Doppelabrufe und falsche Positionszuordnung.
Ein begrenztes serverseitiges Punktbudget oder Pagination verhindert unbeschränkte
`ALL_AVAILABLE`-Antworten; Kürzung/Aggregation muss im DTO erkennbar bleiben.
Vorher/nachher getrennt messen: UI-Rendering, DB-Lesezeit/Abfragezahl und Providerlast.
Abnahmeregel: Öffnen, Zeitraumwechsel und Schließen erzeugen **null Provideraufrufe**.

## 5. Umsetzung und Abnahme

Ein zusammenhängendes Featurepaket, in dieser Reihenfolge:

1. **Historienvertrag und Persistenz:** bestehende Daten nutzen, Optionsscheinbeobachtungen
   additiv historisieren, Idempotenz und Herkunft absichern; keine Aktivierung ungeprüfter Quellen.
2. **Leseservice und Abdeckung:** Positionskontext über öffentliche Services, Zeitraum-/Identitäts-
   und Workspaceprüfung, vorhandene Basiswertserien; noch unversorgte Produkte explizit leer/teilweise.
3. **Chart und Betrieb:** verzögertes Laden, Qualitätszustände und Regressionen; lokale
   instrumentbezogene Abnahme. Backfill nur innerhalb belegter Quellenrechte und Abdeckung.

Die erforderliche neue Migration muss gegen den dann aktuellen Alembic-Graph geplant und
auf einer Wegwerf-PostgreSQL-Datenbank mit Bestandsdaten-Upgrade geprüft werden. Diese
Dokumentationsänderung selbst enthält keine Migration und benötigt kein Deployment.
Ein Rollback darf die neue Historie nicht unbemerkt löschen; zunächst neuen Schreib-/Lesepfad
abschalten und Daten erhalten. Vor produktiver Aktivierung müssen Retention und Wiederherstellung
geprüft sein. Provider-/Abo-/Deploymentfreigaben bleiben getrennt.

| Regression / Gate | Erwartung |
| --- | --- |
| Neustart, doppelte Lieferung, Wiederanlauf | Punkte bleiben erhalten; gleiches Ereignis bleibt einmalig. |
| Falsche ISIN, Listing, Währung oder fremder Workspace | Keine Zuordnung bzw. keine Ausgabe; verständlicher Fehler. |
| Fehlende/alte Zeit, date-only, Sommerzeit | Keine erfundene Uhrzeit, keine Verjüngung; belegte Historie korrekt angezeigt. |
| BidOnly, Last/Close, Quellenwechsel, Revision | Typ und Provenance bleiben erkennbar; keine gemischte Scheinserie. |
| Fehlende Historie, Lücken, Einzelpunkt, älterer Kauf | Korrekte Teilabdeckung statt falscher Vollständigkeit. |
| 401/403, Rate Limit, einzelner Providerfehler | Bestehende Failure-/Fallback-Policy bleibt erhalten; keine versteckte Cachefreigabe. |
| Persistenzfehler bei erfolgreichem Abruf | Historienfehler sichtbar; keine falsche Speicher-Erfolgsmeldung. |
| Korrigierter Kauf, Nachkauf, Teilverkauf, Stornierung | Bestehende effektive Projektion bleibt maßgeblich und unverändert. |
| Auf-/Zuklappen, Zeitraum-/Positionswechsel | Abbruch, Cache, Race-Schutz, Tastaturzugang; keine wirtschaftliche Mutation. |
| PostgreSQL, Frontend, E2E, finale CI | Tatsächlich ausführen und am finalen Head dokumentieren; Fixturetests ersetzen keine Betriebsprüfung. |

### Bereits nutzbarer lokaler Prüfweg — ausschließlich lesend

```bash
curl -fsS http://localhost:8000/api/v1/market-data/refresh/status \
  | jq '{enabled, running, leader, current_job, pending_jobs, quote_storage,
         jobs: [.jobs[] | select(.held == true)
           | {name, isin, job, status, reason, checked_at, next_run_at}]}'
```

Diese vorhandene Route liest den Schedulerstatus; sie startet weder Abruf noch Buchung.
`PENDING` ist keine negative Coverage-Aussage, `AVAILABLE` kein Historien- oder Frischenachweis.
Die Ausgabe bleibt lokal; sie ist kein öffentliches PR-Artefakt. Der noch zu implementierende
Historien-Lesepfad ergänzt später frühestes/spätestes Datum, Punktzahl und Lücken.
Ein Aufruf von `POST .../refresh/run` oder `POST .../daily-prices/import` gehört ausdrücklich
**nicht** zu diesem lesenden Prüfweg. [S3–S4]

## 6. Dokumentationsumfang und Handoff

Dieses Dokument trennt geprüften Ist-Stand und vorgeschlagenen Soll-Vertrag. Bei der
Implementierung sind die bestehenden Market-Data-Vertragsunterlagen für das additive Schema
und den neuen öffentlichen Reader sowie `docs/automatic-market-data.md` für Persistenz,
Diagnostik, Recovery und Grenzen gezielt zu ergänzen. `docs/ui/positions-table.md` erhält nur
den Hinweis auf Chart und Qualitätszustände. Kein Umschreiben freigegebener Handelsregeln
und keine große parallele Prozessdokumentation.

PR #186 bleibt Eigentümer der offenen Quellenarbeit; #197 ist ein Forschungsdatenlauf,
kein produktiver Feed; #187 ist Regelarbeit. Diese Branches werden nicht verändert oder
ungeprüft als Voraussetzung übernommen. Der aktuelle Basiswert-Mappingfix #202 wird
wiederverwendet. Vor Beginn des Runtime-PRs offene Überschneidungen erneut prüfen.

**Prüfgrenze:** Repository-Code, genannte Runbooks, PR-Metadaten und öffentliche Primärquellen
wurden gelesen. Kein Zugriff auf den Nutzer-PC, dessen Datenbank, aktivierte Providerkonten
oder tatsächliche gespeicherte Zeitreihen. Keine Live-Coverage, Migration, Anwendungstests
oder Chartfunktion durch dieses Dokument nachgewiesen. Keine Provider-, Depot- oder
Strategieänderung ausgeführt. Die eigentliche Runtime-Implementierung ist noch offen.

## Quellen

Repositorybezüge gelten für die oben genannte Prüfbasis; neue APIs und Tabellen im Text
sind ausdrücklich Vorschläge.

- **S1:** `backend/app/features/market_data/service/refresh.py` — `status`, `_warrant`, `_underlying`.
- **S2:** `backend/app/features/market_data/persistence/models.py` — `DailyPriceModel`, `WarrantProviderMappingModel`.
- **S3:** `backend/app/features/market_data/api/router.py` — bestehende Import- und Statusrouten;
  `backend/app/features/market_data/service/query.py` — `MarketDataReader`.
- **S4:** [Automatic market data](../automatic-market-data.md).
- **S5:** [Underlying mapping discovery](../underlying-mapping-discovery.md), [PR #202](https://github.com/burckhju/trading-workspace/pull/202).
- **S6:** `backend/app/features/market_data/domain/models.py` — `WarrantQuoteSnapshot`.
- **S7:** [Source Architecture](../architecture/Source_Architecture.md),
  `frontend/src/features/operational_workspace/components/PositionDetails.tsx` und `types.ts`.
- **E1:** [Vontobel API Offering](https://api-docs.deritrade.com/docs/Introduction/offering/) — API-Arten und erforderliche Autorisierung; geprüft 13.09.2026.
- **E2:** [Vontobel Pricing and Trading API](https://api-docs.deritrade.com/api/quoting-trading/) — kein daraus belegter historischer Workspace-Feed; geprüft 13.09.2026.
- **E3:** [Deutsche Börse WSS](https://www.mds.deutsche-boerse.com/mds-en/Reference-Data/wss) — historische Datenprodukte, kein konkreter Coverage-/Zugangsbeleg; geprüft 13.09.2026.
