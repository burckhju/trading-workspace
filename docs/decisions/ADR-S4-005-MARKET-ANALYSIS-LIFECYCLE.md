# ADR-S4-005: Append-only Lifecycle für Marktanalysen

## Status
Accepted – Sprint 4 / FT-006

## Kontext
Marktanalysen müssen versioniert, reproduzierbar und vollständig nachvollziehbar sein. Gleichzeitig dürfen abgeschlossene Runs und deren Snapshots nicht nachträglich verändert werden. Der fachliche Lebenszyklus enthält jedoch den Zustand `SUPERSEDED`, wenn eine Version durch eine neuere Version ersetzt wird.

## Entscheidung
Statusübergänge werden durch eine explizite Domain-State-Machine validiert. Ein Run wird zunächst als `RUNNING` zusammen mit seinem vollständigen Eingabe-Snapshot persistiert. Erst danach wird er in genau einen terminalen Ausführungsstatus überführt: `COMPLETED`, `COMPLETED_WITH_WARNINGS`, `NOT_EVALUABLE` oder `FAILED`.

Lifecycle-Ereignisse werden append-only in `market_analysis_events` gespeichert. Eine abgeschlossene Quellversion wird beim Supersede nicht verändert. Stattdessen dokumentiert ein `SUPERSEDED`-Event den historischen Status, die Quellversion und die Ersatzversion. Der persistierte Ausführungsstatus und Snapshot der Quellversion bleiben unverändert.

Retry ist ausschließlich für `FAILED` und `NOT_EVALUABLE` zulässig. Ein Retry verwendet den gespeicherten Snapshot, die aufgelösten Parameter sowie exakt dieselbe Modell-ID und Modellversion. Aktuelle Marktdaten werden nicht erneut gelesen. Ist die historische Modellversion nicht mehr verfügbar, wird der Retry abgelehnt.

## Zulässige Übergänge

- `DRAFT -> RUNNING`
- `RUNNING -> COMPLETED`
- `RUNNING -> COMPLETED_WITH_WARNINGS`
- `RUNNING -> NOT_EVALUABLE`
- `RUNNING -> FAILED`
- jeder terminale Status `-> SUPERSEDED` als append-only Event

Alle anderen Übergänge werden als `ANALYSIS_CONFLICT` abgelehnt.

## Reproduzierbarkeit
Die Datenalter-Bewertung wird relativ zum gespeicherten `analysis_time` berechnet und nicht relativ zum aktuellen Tagesdatum. Damit verändert sich das Ergebnis einer historischen Version nicht durch Zeitablauf.

Der Verifikationsendpunkt berechnet eine Version erneut aus dem gespeicherten Snapshot und prüft separat Modellverfügbarkeit, Eingabe-Hash, Kennzahlen, Kriterien, Qualitätsstatus und Hinweise.

## Konsequenzen
- abgeschlossene Versionen bleiben unveränderlich;
- Supersede ist trotzdem vollständig nachvollziehbar;
- Retry ist deterministisch und providerunabhängig;
- keine direkte Provider- oder Market-Data-Abhängigkeit im Retry-Pfad;
- die Event-Tabelle ist eine additive Persistence-Erweiterung;
- historische Modellimplementierungen müssen verfügbar gehalten werden, wenn alte Versionen erneut ausgeführt werden sollen.

## Technische Präzisierung 25.10.2026 — PR #278

Der bestehende Lifecycle bleibt erhalten. Die feste Auswahl für einen neu
angeforderten Run lautet im Aufgabenbranch `EOD_TREND_MOMENTUM/1.0.1`; ein
expliziter neuer `1.0.0`-Run bleibt möglich. Die Auswahl steht zentral in
`analysis/domain/model_versions.py`. Der gemeinsame Executor verlangt beide
Identitäten explizit. Listing- und echte Referenzanalysen verwenden denselben
Executor und die geerbten Retry-/Verify-Methoden.

Die Auswahl neuer Runs ändert keinen historischen Vertrag. Retry übernimmt
weiterhin Modell-ID, Runtimeversion, Parameter und Snapshot der Quellversion.
Eine gespeicherte unbekannte Identität wird abgewiesen; Verify meldet
Modell-Nichtverfügbarkeit statt einen Ersatzrechner auszuführen. Die ursprüngliche
Zeitbindung bleibt erhalten. Kriterien werden zur Verifikation nach Code
geordnet, weil der Repositoryreader eine andere Reihenfolge liefern darf;
alle Felder sowie fehlende oder doppelte Kriterien werden weiterhin verglichen.

Provenienz bindet nur genau eine zum tatsächlich ausgeführten Vertrag passende
genehmigte Baseline. Sie erzeugt keine Modellregistrierung, Genehmigung,
Aktivierung oder automatische Rückbefüllung. Die bestehenden Transaktions-,
Terminalitäts- und append-only Ereignisgrenzen bleiben maßgeblich.
Die Präzisierung dokumentiert den Entwicklungsschnitt und erweitert den
ursprünglichen Accepted-Status nicht um eine Fach-, Merge-, Release- oder
Betriebsfreigabe. Details und tatsächliche Nachweise:
[FT-006](../features/FT-006_MARKET_ANALYSIS.md),
[Provenienz](../features/FT-006_GOVERNED_MODEL_PROVENANCE.md) und
[Qualifikation](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md).
