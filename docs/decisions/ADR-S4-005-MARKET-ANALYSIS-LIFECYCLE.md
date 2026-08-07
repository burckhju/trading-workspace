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
