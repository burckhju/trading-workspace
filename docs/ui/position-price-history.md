# Positionskursverlauf aus vorhandenen Kursbelegen

Implementierung auf `main`-Basis `d1108ae4f7fba976f4771885e84b5b8662248edb`
(Produktstand `v1.5.31`), auf Grundlage des Vorschlags in
[PR #205](https://github.com/burckhju/trading-workspace/pull/205).
Repository und Tests belegen keine produktive Kurshistorie auf dem Nutzer-PC.

## Anzeige

Beim Aufklappen einer bestehenden Position lädt **Historischer Positionskurs**
automatisch die belegten Kurse des zugehörigen Optionsscheins. Standard ist
**Alle gespeicherten Kurse**; dadurch bleibt auch ein einzelner alter Kurs einer
Bestandsposition ohne zusätzliche Eingabe sichtbar. Optional sind 7, 31 und
90 Tage auswählbar. Zeitfenster und Diagrammkoordinaten verwenden die Originalkurszeit.

Die Grafik zeigt ausschließlich einzelne Punkte ohne Verbindungslinien. Zwischen
zwei Punkten ist kein Kurs belegt. Es gibt weder Interpolation noch Fortschreibung
oder aus Basiswert, Einstand oder heutiger Bewertung rückgerechnete Preise.
Das bereits vorhandene Basiswertdiagramm bleibt über seinen Link zugänglich.

Währungen erhalten getrennte Diagramme. Geld, Brief, letzter Handel und vorheriger
Schlusskurs bleiben eigene Serien; Provider, ursprüngliche Listing-/Quellidentität
und Quellenmodus trennen die Serien zusätzlich. Quellenwechsel werden nicht
glatt verbunden. Die Quellentabelle erhält die ursprünglichen Dezimalwerte,
Originalkurszeit, Empfangszeit, gegebenenfalls Stichprobenzeit, Erfassungsqualität
und Zeitbasis. UTC ist ausdrücklich bezeichnet. Ein alter, zeitlich belegter
Kurs bleibt historische Evidenz; die Grafik behauptet keine aktuelle Handelbarkeit.

Ladezustand, Ladefehler mit Wiederholung, fehlende zuordenbare Punkte und eine
begrenzte Antwort werden getrennt dargestellt. Ein abgebrochener oder verspäteter
Request darf nach dem Positionswechsel keine fremde Historie anzeigen. Die
Tabelle ist horizontal scrollbar und paginiert, die Grafik passt sich Mobil-
und Desktopbreiten an. Zeitraumwahl und Datenalternative sind per Tastatur nutzbar.

## Wiederverwendete Daten und Grenzen

| Bestehender Bestand | Verwendung |
| --- | --- |
| `warrant_quote_samples` aus #253 | Erste abgeschlossene Beobachtung je exakter Route und UTC-Fünfminutenintervall, einschließlich Fehlern. Nur zeitlich und fachlich zuordenbare Preise werden geplottet. |
| `warrant_quote_observations` aus #218 | Tatsächlich letzter erfolgreicher Kurs je Listing/Provider, auch für Bestände ohne Stichprobenhistorie. Der fehlende historische Speicherzeitpunkt bleibt `null`. |
| `WarrantQuoteSnapshot` | Unveränderte Preisart, Währung, genaue Listing-/ISIN-Zuordnung, Originalkurszeit und Quellenmodus. |
| Effektive Execution Records und Währungsresolver aus #298 | Tatsächliche Kauf-/Verkaufspreise und bestehende Währungsherkunft, unabhängig von heutigen Listingwährungen. |
| `daily_prices` / Marktcharts aus #243 | Basiswert-EOD bleibt im separaten Basiswertdiagramm. EOD-Handelstage sind keine Optionsschein-Originalzeitpunkte. |

`QuoteHistoryReader.prices()` erweitert den bestehenden Market-Data-Lesevertrag.
Das vorhandene Erfassungsprotokoll `QuoteHistoryReader.report()` bleibt unverändert:
Seine letzten 50 Einträge und sein Erfassungszeitfenster werden nicht als komplette
Kurshistorie missverstanden. Es entsteht keine Tabelle, Migration, neue Speicherung,
Providerauflösung oder Abrufplanung.

Der Preisleser prüft höchstens die neuesten **10.000 gespeicherten Stichproben**
nach Erfassungsreihenfolge sowie die vorhandenen letzten erfolgreichen Quotes.
`samples_available`, `samples_considered`, `sample_limit` und `truncated` machen
diese Grenze sichtbar. Sie gilt vor dem Originalzeitfilter; ein Zeitraumwunsch
garantiert deshalb bei sehr großen Beständen nicht, dass alle älteren Belege
untersucht wurden. Es werden weder Abdeckungsprozente noch Vollständigkeit
behauptet. Gleiche Preisart, Quelle, Identität, Währung, Originalzeit und Preis
werden nur einmal geplottet; Cachelesungen sind keine neuen Kurse. Ein gleicher
Preis zu einem späteren echten Quellzeitpunkt bleibt ein eigener Punkt.

Unbekannte Originalzeiten, widersprüchliche Uhren, fehlende Kurse, Fehlerbelege,
ungültige Payloads und Identitätsabweichungen erhalten getrennte Ausschlussgründe.
`retrieved_at`, `captured_at` und Fünfminuten-Slot ersetzen niemals `observed_at`.
Eine geänderte Providerroute entfernt keine alte, noch zum Produkt gehörende
Quellidentität; eine abweichende ISIN wird hingegen nicht übernommen.

## Rein lesende Positions-API

```text
GET /api/v1/trade-position/trades/{trade_id}/price-history
GET /api/v1/trade-position/trades/{trade_id}/price-history?days=31
```

Ohne `days` werden alle innerhalb des Budgets verfügbaren Originalkurszeiten
berücksichtigt; `days` akzeptiert 1 bis 366. Ungültige Parameter ergeben 422,
unbekannte, fremde oder stornierte Trades/Positionen 404. Ein nicht belegbarer
Owner-Kontext ergibt 409. Ein Speicher-/Transportfehler wird nicht als leere
Kurshistorie ausgegeben.

Der Trade-Owner löst Position und effektive Ausführungen auf und verwendet seinen
bestehenden Währungsresolver. Die API delegiert den Kurslesezugriff an Market Data;
sie liest keine fremden Persistenzmodelle direkt und ruft weder Produktbewertung
noch Quotes, Imports oder Provider auf. Öffnen, Wiederholen und Zeitraumwechsel
erzeugen keine wirtschaftlichen Writes. Bestehende Positionsbewertung,
Performanceberechnung, Stops, Ziele und Monitoring bleiben unverändert.

Position, Ausführungen, Währungsbelege und Kurse werden in derselben kurzen
PostgreSQL-Transaktion mit `REPEATABLE READ READ ONLY` gelesen. Ein
Statement-Timeout von zehn Sekunden begrenzt die Datenbankabfragen. Eine
zeitgleiche Buchungskorrektur verändert diese Antwort nicht auf halbem Weg.

Die Antwort enthält Positions-/Trade-/Produktidentität, Originalzeitfenster,
Stichprobenbudget und Ausschlussgründe, nach Quelle/Währung/Preisart getrennte
`series` sowie `events`. Pydantic serialisiert `Decimal` als String.
`collection_started_at` bezeichnet nur den Beginn gespeicherter Stichproben.

## Kauf- und Verkaufsereignisse

Nur aktuell effektive Ausführungen derselben Position und desselben Produkts
werden übernommen. Ersetzte Buchungen verschwinden aus den Markern; die bestehende
Trade-Historie bewahrt ihre Auditspur. Stornierte Trades erhalten keine Historienansicht.

Ein Marker benötigt die genaue tatsächliche Ausführungszeit und eine durch den
vorhandenen Resolver belegte Währung, zu der auch ein Kurssegment existiert.
Der Marker zeigt den erfassten Ausführungspreis, keinen geschätzten Marktkurs.
Kauf und Verkauf sind in Form/Farbe und im Tooltip als Buchungen gekennzeichnet.

`executed_on` bleibt ein Datum: Der interne Mitternachtsanker wird niemals
geplottet. Datumgenaue Buchungen, unbekannte Währungen und Buchungen ohne
passendes Kurs-Währungssegment bleiben in der Ereignisliste mit Begründung sichtbar.
Es erfolgt keine Ableitung aus dem heutigen Listing und keine FX-Umrechnung.

## Qualifikation

- Backend: reale SQL-/JSON-Rundläufe über vorhandene Retention-/Stichprobenmodelle;
  Originalzeiten, Cache-Duplikate, alte Einzelpunkte, Währungen, Providerwechsel,
  Fehler, leere Antworten und Begrenzung.
- Positionskontext/API: Workspace- und Produktbindung, Korrekturen, Stornierung,
  genaue versus datumgenaue Ausführungen, belegte/fehlende Währungen und lesende GETs.
- Frontend: automatische Requests, Zeitraumwechsel, Abbruch und A→B-Isolation,
  Dezimalwerte, Quellenangaben, Ereignisse, leere Daten und Wiederholung nach Fehler.
- Browser: Desktop und Mobilgerät, Einzelpunkt und Lücken ohne Linien,
  getrennte Währungen/Provider, Marker und Datumsbelege, Begrenzung und Fehler.

Alle Testdaten sind synthetisch. Reale Datenlücken, verloren gegangene frühere
Cachewerte und unbekannte Quellzeiten lassen sich mit diesem Lesefeature nicht
schließen. Rückwirkende Beschaffung, Providerfreigaben und ein Nutzer-PC-Update
benötigen weiterhin einen getrennten Auftrag.
