# Realisierte Bruttoergebnisse nach Zeitraum — vertikale Qualifikation

Die lokalen Code- und Laufnachweise vom 17.10.2026 bleiben unten unverändert
zugeordnet. Die anschließende Veröffentlichungsfreigabe und erneute
Integrationsqualifikation sind im [Nachtrag vom 18.10.2026](#integrations--und-auslieferungsfortsetzung-18102026)
getrennt dokumentiert; frühere Aussagen über einen nur lokalen Branch sind
historischer Stand.

## Lieferumfang und Prüfgrenze

Der enge Bericht `realized-gross-sell-v1` und der dafür benötigte additive
Execution-Währungsowner sind im Aufgabenbranch implementiert. Der Nutzer wählt
inklusive Kalendertage, Berichtszeitzone und Berichtswährung. Er erhält wirksame
SELL-Beiträge, die vollständige Kostenbasis-Herkunft, Datenlücken und eine
qualifizierte Summe beziehungsweise Teilsumme aus einer gemeinsamen Quellenbasis.
Bestehende Buchungen ohne explizite Währungsbestätigung bleiben unbekannt.

Die Freigabe zur Umsetzung des zuvor konkret vorgelegten Vertrags erfolgte mit
**„Ok, umsetzen“** am 17.10.2026; siehe
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md).
Sie ist keine Endabnahme des fertigen Codes, Veröffentlichung, Produktionsmigration
oder PC-Abnahme. Maßgeblicher Arbeitsstatus bleibt ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics).
Die ursprüngliche M8-Baseline und sämtliche weitergehenden Anforderungen bleiben
erhalten. Dieser Nachweis enthält keine zweite Aufgabenstatusliste.

## Ausgangsstand und genaue Codebasis

| Bezug | Nachweis |
|---|---|
| Erneut gelesener Ausgangsstand | `main` / `e9aac2bfaadeb9133a6ed07e42d1dec39836b156`, Version 1.5.8. |
| Arbeitsbranch | `work/realized-gross-report-20261017`; kein direktes Arbeiten auf main. |
| Vorangehende Owner-Vorleistung | `8a3b9d662b6b32e384c6877447aedf4234af524d`, Quellen-/Qualifikationsdokumentation `bf44d72b4ba2a762e2917f561c318f90aef6901e`. |
| Vertikale Implementierung | `523da4791e53d222f29ea46c321b97a77ee4fb3c`. |
| Formatkorrektur einer SQL-Testzeichenfolge | `329673db79de54a82290e5923126911387bcd2ee`; Produktionscode bytegleich zu `523da479`. |
| Zusätzlicher echter Lernzustandsnachweis | `031f9117fa790102114bdceb77b28df4895617de`; nur neuer PostgreSQL-Test, Produktionscode weiterhin bytegleich zu `523da479`. |
| Abschließender UI-Receipt-Fix | `d4321433a4dcedc046a184b42196eedc2ac449c8`; nur Currency-Panel und drei ergänzende Regressionen. Backend/Migrationen bytegleich zu `523da479`, Backendtests bytegleich zu `031f911`. |
| Unabhängiger PR #249 | Am 17.10.2026 erneut als offen und Draft gelesen, Head `1ad81344a66be9e70c772828081b2ff7ac13ef1c`; kein Basiswertformular in diesem Diff. |
| Auslieferung | Lokaler überprüfbarer Diff und Commits; kein Push, Merge, Tag, Release, Deployment oder Versionssprung. |

Die ursprüngliche begrenzte Suche, Soll-/Ist-Konflikte und deren Auflösung stehen
im [Quellenvertrag](PERIOD_REALIZED_GROSS_READINESS.md). Die
[erste Trace-Qualifikation](PERIOD_REALIZED_GROSS_QUALIFICATION.md) bleibt ein
historischer, getrennt zu lesender Nachweis; ihre früheren Gatezahlen werden hier
nicht als neue Ausführung übernommen. #260/#261/#263 wurden als vorhandene
Journal-/Lesson-/Evidence-Fähigkeiten wiederverwendet.

## Quellenmatrix des gelieferten Schnitts

| Benötigtes Feld | Owner und Speicherung | Historische Bindung / Änderbarkeit | Read-Vertrag und Consumer | Testnachweis / verbleibende Voraussetzung |
|---|---|---|---|---|
| Workspace, eigener Trade, Origin, Storno | `trade_position`, `TradeModel` / `trades` | Konkrete Workspace-/Trade-/Produkt-IDs; vorhandener Stornovertrag bleibt erhalten. EXTERNAL bezeichnet bewusst als eigenen Trade erfasste Ausführungen. | Bericht liest bestehende Trade-Fakten; stornierte Trades separat in `excluded_trades`. | Report-Unit-/API- und PostgreSQL-Fälle. Reine externe Beobachtungen erzeugen keine Execution-Zeilen. Keine neue Authentifizierungsbehauptung aus Audit-Actors. |
| BUY-/SELL-Menge und tatsächlicher Stückpreis | `trade_position`, `ExecutionRecordModel` / `execution_records` | Unveränderliche Execution-ID; wirtschaftliche Korrektur ergänzt eine neue Execution mit `supersedes_execution_id`. Numeric-/Decimal-Vertrag bleibt erhalten. | Vollständige Historie vor Periodenfilter; `PositionProjector.project_with_trace()` bestimmt wirksame Reihenfolge und direkte SELL-Deltas. | Owner-Gleichheits-, Referenz-, Korrektur-, Decimal- und PostgreSQL-Tests. Ungültige Historie bleibt `HISTORY_INVALID`. |
| Tatsächliche Preiswährung | Derselbe Execution-Owner, neue `execution_currency_confirmations` | Exakte Execution-/Workspace-/Trade-ID, `USER_CONFIRMED`, Actor, Bestätigungszeit, Notiz, Request-ID, optionaler Vorgänger. Append-only; keine Änderung alter wirtschaftlicher Werte. | Capture-Commands und ausdrücklicher Bestätigungscommand schreiben; History-GET und Bericht lesen. Historische POST-Receipts sind keine neue Currentness-Bestätigung. | Neue Currency-Unit-/PostgreSQL-Tests: alle Capture-Einstiege, Legacy-Unknown, Supersession, Retry, konkurrierende Nachfolger, FKs, Schreibschutz und Downgrade. Reale Altbuchungen benötigen tatsächliche bewusste Bestätigung. |
| Wirtschaftlicher Verkaufszeitpunkt / Date-only | Execution-Owner, `executed_at`, `executed_on`, `execution_timezone` | Gespeicherte Präzision und Zone bleiben erhalten; Korrektur über Ersatzexecution. `recorded_at` bleibt Erfassungszeit. | Periodenreader verwendet Zeitinstant oder möglichen lokalen Kalendertag. Bei Date-only ist ausgegebenes `executed_at` null; interne Sortieranker werden nicht als Uhrzeit angezeigt. | Monats-/Jahresgrenzen, Sommerzeit, abweichende Zeitzonen, übersprungene/mehrdeutige Tagesgrenzen und rückwirkende Datumskorrektur qualifiziert. |
| Kostenbasis, Vor-/Restbestand, SELL-Beitrag | `trade_position.domain.projector.PositionProjector` | Reine Ableitung aus vollständiger wirksamer Historie und unveränderter Owner-Reihenfolge/Decimal-Präzision. Keine zweite Buchführung. | Eine gemeinsame Owner-Schleife; Bericht nutzt Trace und exakte `cost_basis_execution_ids`. | Unabhängiger September-/Oktoberfall, Korrektur und wiederholende Decimal-Werte; Restkosten vor technischem Close-Reset bleiben sichtbar. |
| Anzeigenstellen und Produktname | Market-Owner `CurrencyModel`; Product-Owner `WarrantModel` | Currency-Referenzversion und `minor_unit` stammen aus demselben Read. Produktname ist ausdrücklich heutige Anzeige. | Nur Anzeige; weder Listing-, Quote-, Strike-Währung noch Name bestätigen die historische Ausführungswährung. | Geändertes heutiges Listing lässt unbekannte Ausführungswährungen unbekannt; getrennte Währungen und Anzeigerundung getestet. |
| Quellenbasis, Definition und Zähler | Reiner Performance-Reader und Domain-Lesemodell | Kurzer Snapshot; Hash bindet Definition, Filter und materialisierte Quellen. Keine persistente Berichtshistorie. | Summary, alle Zeilen, Ausschlüsse und Drill-down stammen aus derselben Antwort. | Echte konkurrierend committene Preis-/Datum-/Währungskorrekturen, Basiswechsel, Pagination und verspätete UI-Antworten. |
| Journal, Review, Evidence, Lesson | Bestehende FT-011-/FT-012-Owner | Deren genaue Versionen, Currentness und Relationslinks bleiben getrennt. | Keine Eingabe und keine Voraussetzung dieses finanziellen Readers. | Echte gespeicherte unvollständige Nachbeobachtung, mehrere Evidence-/Lesson-Links und explizit revalidierter STALE-Review verändern den qualifizierten SELL nicht. |

## Freigegebener und implementierter Berichtsvertrag

Die Grundgesamtheit besteht aus wirksamen SELLs eigener nicht stornierter Trades
im Workspace. Teilverkäufe offener Trades zählen. Erfasstes EXTERNAL-Eigentum ist
zulässig; eine bloße externe Beobachtung ist keine Ausführung. BUYs liefern die
Kostenbasis, keinen eigenen realisierten Beitrag. Die gesamte wirksame Historie
wird projiziert, bevor einzelne SELLs der Periode zugeordnet werden. Heutiger
Closed-Status oder eine kumulierte Positionssumme ersetzen diese Zuordnung nicht.

Der Owner berechnet `quantity * (sale_price - average_cost_before_sale)` mit seiner
bestehenden Operationenreihenfolge. Für den Geldbeitrag müssen alle benötigten
BUY-Preisbestandteile und der betrachtete SELL-Preis explizit dieselbe Währung
besitzen. Frühere SELL-Erlöswährungen gehen nicht in die verbleibenden Kaufkosten
ein; deren Mengen und Quellen bleiben trotzdem Teil des Nachweises. Es gibt keine
FX-Umrechnung, automatische EUR-Annahme oder Ableitung aus heutigen Listings.

`from_date`, `to_date`, `report_currency` und `report_timezone` sind ausdrücklich
anzugeben. Die inklusiven Kalendertage werden in der IANA-Berichtszone getrennt
in ein halboffenes Intervall bis zum nächsten lokalen Tagesbeginn übersetzt.
Bei Date-only muss der gesamte mögliche gespeicherte Ausführungstag im Intervall
liegen. Teilüberlappung ist `PERIOD_AMBIGUOUS`, nicht interpretierbare Herkunft
`PERIOD_UNKNOWN`. Nicht unterstützte Anfragegrenzen werden abgelehnt. Ein internes
Mitternachts-Sortierdatum wird nicht zur tatsächlichen Uhrzeit umgedeutet.

| Summary-Zustand | Ergebnisbedeutung |
|---|---|
| `EMPTY` | Keine passenden SELLs und keine relevante ungeklärte Zuordnung; `total = "0"`, Oberfläche benennt die leere Auswahl. |
| `COMPLETE` | Mindestens ein verwendbarer Beitrag, keine relevante Lücke; exakter Gesamtwert einschließlich tatsächlich gemessener Null. |
| `PARTIAL` | Verwendbare Beiträge und relevante Lücken; `total = null`, ausgewiesene bekannte Teilsumme in `subtotal`. |
| `NOT_COMPUTABLE` | Relevante Fälle, aber kein verwendbarer Beitrag; weder Geldsumme noch Teilsumme berechenbar. |

Zeilengründe sind `CURRENCY_UNKNOWN`, `CURRENCY_MIXED`, `HISTORY_INVALID`,
`PERIOD_AMBIGUOUS`, `PERIOD_UNKNOWN`, `OTHER_CURRENCY` und `OUTSIDE_PERIOD`.
`TRADE_CANCELLED` erscheint ausschließlich bei ausgeschlossenen Trades.
`counts.cancelled` zählt Trades, alle anderen Ergebniszähler SELLs. Ein eindeutig
außerhalb liegender oder anderswähriger Verkauf macht die gewählte Auswahl nicht
unvollständig. Ein potenziell passender ungeklärter Fall verhindert die Behauptung
einer vollständigen Summe.

Die API liefert endliche Decimalstrings, Roh- und Anzeigewerte sowie die verwendete
Currency-Referenzversion. Der Backend-Owner behält Präzision 28; Anzeige verwendet
`ROUND_HALF_EVEN` gemäß `minor_unit`. Die Summe wird aus Rohbeiträgen gebildet und
anschließend gerundet. Eine Differenz zur Summe gerundeter Zeilen wird separat
ausgewiesen. Das Frontend führt keine Geldrechnung mit JavaScript-Floats aus.

Der Wissensstand lautet `CURRENT_EFFECTIVE_FACTS`: Eine neue Auswertung eines
früheren Zeitraums verwendet heute wirksame Korrekturen. Sie rekonstruiert keinen
damaligen Kenntnisstand. Die historische Originalexecution und bestehende
Journal-/Review-/Evidence-Inhalte werden vom Bericht nicht umgeschrieben.

### Unabhängiges Zahlenbeispiel und tatsächlich geprüfte Ausgabe

Unter der ausdrücklich synthetischen Annahme bestätigter EUR-Preise:

| Auswertung | September-Beiträge | September | Gesamthistorie nach Oktober |
|---|---|---|---|
| Originalbuchungen | 02.09.: +30,00; 12.09.: −20,00 | **+10,00 EUR** | **+50,00 EUR** |
| Wirksame Korrektur des 12.09.-SELL auf Preis 3,00 | 02.09.: +30,00; 12.09.: 0,00 | **+30,00 EUR** | **+70,00 EUR** |

Der September-SELL verwendet nach dem Nachkauf 100 Stück mit Kosten 300,00 EUR,
also Average Cost 3,00 EUR. Danach bleiben 60 Stück und 180,00 EUR Kostenbasis.
Der später geschlossene Trade bleibt im September auswertbar. Die alte korrigierte
SELL-ID bleibt im Quellen-Drill-down erhalten und wird nicht zusätzlich gezählt.
Diese erwarteten Werte wurden vor Implementierung unabhängig vorgerechnet.

## Änderungen, Consumer und Grenzen

- [Currency-Owner](../../backend/app/features/trade_position/service/currency_confirmations.py),
  [Persistenz](../../backend/app/features/trade_position/persistence/currency_models.py)
  und additive [Migration 0047](../../backend/migrations/versions/20261017_0047_execution_currency_confirmations.py).
  Alle bestehenden tatsächlichen Capture-Commands einschließlich Learning
  `execute-as-trade` können eine optionale ausdrückliche Bestätigung in derselben
  Transaktion speichern. Weglassen bleibt kompatibel und bedeutet unbekannt.
- Der Learning-Handoff benötigt für diesen atomaren Currency-Capture eine äußere
  Unit of Work. Ein tatsächlich reproduzierter bestehender Fehler — erster Request
  erfolgreich, anschließender sequenzieller Retry dauerhaft `IN_PROGRESS` — wurde
  eng behoben. Ein Fehler nach realem Link-Insert rollt nun Trade, BUY, Confirmation,
  Link und Idempotenzreceipt gemeinsam zurück.
- [Reportreader](../../backend/app/features/performance/service/reader.py),
  [Domain-Ausgabe](../../backend/app/features/performance/domain/report.py) und
  [Periodenregeln](../../backend/app/features/performance/domain/periods.py) konsumieren
  den bestehenden Owner-Trace. Registrierung in `backend/app/main.py`.
- `GET /api/v1/performance/realized-gross` liefert eine vollständige Antwort;
  Frontendroute `/performance/realized-gross`, Navigation „Realisierte Ergebnisse“.
  [Berichtsseite](../../frontend/src/features/performance/pages/RealizedGrossPage.tsx)
  zeigt Filter, Definition, Quellenstand, Abdeckung, Gründe, Beiträge und Herkunft.
  Die lokale Pagination zeigt 20 Zeilen; sie verändert weder Gesamtsumme noch Basis.
- Bestehende Erfassungsformulare und „Kauf- und Verkaufsdaten“ erlauben explizite
  Währungsbestätigung. Keine Vorbelegung mit EUR, keine Übernahme der Bestätigung
  einer wirtschaftlich ersetzten Execution. Nach einem POST bestimmt ausschließlich
  ein neuer History-GET, welche Bestätigung aktuell ist; ein historisches Receipt
  wird nicht als neue Currentness-Aussage ausgegeben.

### Begrenzte konsistente Lesegrenze

Der Reader verwendet eine frische Session mit `autoflush=False` und setzt vor dem
ersten fachlichen SELECT lokal `REPEATABLE READ READ ONLY`. Er materialisiert
Trade-/Storno-, Execution-/Supersession-, Währungsbestätigungs- und Anzeigequellen.
Erst nach Ende der Transaktion wird aus diesen unveränderlichen Eingaben gerechnet.
Keine globale Isolation, keine `FOR UPDATE`-Sperren, keine Schreibmaterialisierung
und keine über Nutzerinteraktionen offene Transaktion werden eingeführt.

Die Grenzen betragen **2.000 Trades, 20.000 historische Executions, 40.000
Währungsbestätigungen und 100.000 SELL-Präfixreferenzen**. Sie gelten für die
vollständige Workspace-Materialisierung. Ein engerer Zeitraum verkleinert den
Historienread nicht automatisch. `statement_timeout = 10000ms` gilt pro
SQL-Anweisung und garantiert keine Gesamtlaufzeit des Requests. Überschreitung
liefert HTTP 413 `REPORT_RESOURCE_LIMIT`, ein Datenbank-Lesefehler HTTP 503
`REPORT_READ_UNAVAILABLE`, eine ungültige Anfrage HTTP 422 `REPORT_INPUT_INVALID`.
Es wird keine gekappte Geldsumme als vollständiger Bericht ausgeliefert.

Der Basis-Hash bindet Definition, Filter und materialisierte Quellen; Lese- und
Berechnungszeiten sind gesondert ausgewiesen. Späteres Neulesen kann eine neue
Basis liefern. Das Frontend ersetzt dann den ganzen Bericht und zeigt den Wechsel.
Filteränderung entfernt die vorige Ausgabe unmittelbar; Abort-/Generation-Guards
verwerfen verspätete Antworten und Antworten mit nicht passenden Filterwerten.
Drill-down und Seitennavigation innerhalb einer Antwort lesen lokal. Der Hash
ist kein gespeicherter oder später rekonstruierbarer historischer Berichtssnapshot.

## Nachweis zu Akzeptanzkriterien 1–10

| Kriterium | Nachgewiesenes Ergebnis / genaue Grenze |
|---|---|
| 1 — Referenz und Korrektur | Owner-, Report-, API- und tatsächlicher Browser-/PostgreSQL-Weg liefern September 10/30 und Gesamthistorie 50/70; Käufe und Verkäufe vor/nach der Periode bleiben vollständig nachvollziehbar. |
| 2 — Teilverkäufe, BUY, Storno, Origin | Offene und später geschlossene Referenztrades, BUY-only, Storno und externe Beobachtungen werden getrennt behandelt. Kein Closed-Kohortenfilter und keine SELL-Vervielfachung. |
| 3 — Historische Währung | Explizite Bestätigung aller benötigten BUYs und des SELLs; Unknown, Mixed, getrennte EUR/USD-Auswahl, geändertes heutiges Listing und Ersatzexecution ohne geerbte Bestätigung qualifiziert. Kein Backfill und keine FX-Umrechnung. Reale Nutzerdaten wurden nicht bestätigt. |
| 4 — Leer, Null, Teilbetrag, unbekannt | Alle vier Summary-Zustände und bekannte Nullteilsummen getestet. Browser prüft zusätzlich unbestätigte Legacy-Quelle → bewusste Owner-Bestätigung → gemessene Null sowie einen leeren Zeitraum. |
| 5 — Präzision und Zeit | Date-only, spätere Erfassung, Monats-/Jahresgrenzen, Sommerzeit und mehrdeutige Zonenränder sind deterministisch. Echte rückwirkende Datumskorrektur verändert eine neue Berichtsperiode. Interne Anker erscheinen nicht als Ausführungsuhrzeit. |
| 6 — Eine Basis, Pagination, UI-Rennen | Vollständige Zeilen-/Quellen-/Summary-Antwort; lokale Pagination und Herkunft, Backend-Rundungsdifferenz, Filtergenerationen und sichtbarer Basiswechsel getestet. Historische Currency-Receipts benötigen ein neues Currentness-GET. |
| 7 — Gleichzeitige Korrektur | Echte PostgreSQL-Tests committen Preis-, Datum- und Währungskorrektur zwischen Reader-SELECTs. Ein laufender Bericht bleibt vollständig alt, das nächste Lesen vollständig neu; Writer wird nicht durch Report-Schreibsperren blockiert. Globale Connection-Defaults bleiben unverändert. |
| 8 — Lernunabhängigkeit und reines Lesen | Fehlendes Journal, tatsächlich gespeicherte unvollständige Nachbeobachtung, zusätzliche Evidence-/Lesson-Relationen und explizit persistierter STALE-Review ändern kein qualifiziertes Finanzergebnis. Vergleich aller öffentlichen Tabellen vor/nach GET; keine externen Provideraufrufe. |
| 9 — Backend bis Browser | Echter Browser gegen gebaute Oberfläche, reale Owner-REST-Schreibstrecke und PostgreSQL 17.11. Auswahl → Beiträge → Summe → Kostenherkunft, Preisersetzung, Legacy-Bestätigung, Desktop/Mobil und Tabellenfingerprint geprüft. Kein Mock-HTTP als Ersatz für diese Strecke. Vollständiges Compose-Gate mangels Docker-CLI nicht ausgeführt. |
| 10 — Gates und Dokumentation | Bestehende Gate-Skripte und Schwellen unverändert. Exakte neue Testläufe und verbleibende Werkzeuggrenzen unten; ADR, Readiness, FT-010, Capture-Anleitung, Architektur, Model Book, Traceability und maßgebliches Backlog fortgeschrieben. Keine M8-/PC-Endabnahme behauptet. |

## Ausgeführte Prüfungen und reproduzierbare Grenzen

Alle Schreibtests nutzten eigene synthetische Wegwerfdatenbanken auf Loopback.
Keine Nutzer-Volumes, bestehende `.env`, Providerzustimmungen oder produktiven
Bestände wurden geändert. Scheduler und Telegram waren deaktiviert; externe
Aufrufe in den einschlägigen Tests abgefangen. Der echte Browserstack blockierte
ausgehende HTTP-Aufrufe zusätzlich und protokollierte keine Versuche.

Versionen: Python 3.12.14; Backend-Abhängigkeiten aus den unveränderten Manifesten;
Node 22.16.0 und npm 10.9.2; Frontend-Playwright 1.55.0; Chromium 140.0.7339.16
(Build 1187); PostgreSQL 17.11 mit Checksums, `fsync`, `synchronous_commit` und
`full_page_writes` eingeschaltet. Die Produktionseinstellungen wurden nicht geändert.

| Prüfstrecke | Befund und Codebezug |
|---|---|
| Currency-Owner gezielt | 189 bestehende/neue Owner-/Learning-Unit-/API-Fälle sowie vier echte PostgreSQL-Integrationsfälle bestanden; im Commit `523da479` enthalten. |
| Performance gezielt | 79 Unit-/API-Fälle plus sechs PostgreSQL-Fälle bestanden (85 gesamt); Produktionscode in `523da479`. |
| Gespeicherte Lernzustände | Ein zusätzlicher echter PostgreSQL-Test, 1 bestanden in 6,14 s, Commit `031f911`. |
| Vollständiges Frontend-Gate | `bash scripts/check-frontend.sh` auf `d4321433`: **524 Tests in 110 Dateien bestanden**, Exit 0 in 69,48 s; Statements/Lines 92,82 %, Branches 84,11 %, Functions 85,10 %. Typecheck, ESLint, Prettier, Coverage-Gates und Build bestanden. Vorheriger Lauf auf `523da479`: 521 bestanden, gesondertes historisches Log. |
| Erster Backend-Anlauf | Auf `523da479` am unveränderten Ruff-Gate wegen einer 104 Zeichen langen neuen Test-SQL-Zeichenfolge beendet; reine Formatkorrektur in `329673db`. |
| Vollständiger Backend-Lauf auf `329673db` | 2.854 Tests bestanden, ein bestehender Journaltest beim Alembic-Zugriff mit PostgreSQL-OS-Dateifehler fehlgeschlagen; Coverage 87,62 % bei unverändertem Minimum 85 %. Ruff, Black und Mypy bestanden. Kein grüner Gesamtlauf daraus abgeleitet. |
| Unveränderter Journaltest, neuer temporärer Cluster | Auf `031f911` bestanden; `test_actual_exit_to_journal_evidence_lesson_and_execution_correction` einschließlich der erwarteten Downgrade-Schutzmeldung. |
| Backend-Gate-Wiederholung | `bash scripts/check-backend.sh` auf `031f911`: **2.856 bestanden**, 0 fehlgeschlagen, 0 übersprungen, eine bestehende Warnung, Coverage **87,62 %** bei unverändertem Minimum 85 %. Ruff, Black (963 Dateien), Mypy (551 Quelldateien) bestanden; gesamtes Gate Exit 0 in 603,22 s. Backend/Migrationen und Backendtests auf `d4321433` bytegleich. |
| Echter Browserweg auf finalem Produktionscode | Auf `d4321433`: **1 bestanden, 0 übersprungen, 0 Retries, 0 flaky**, gesamte Aufrufdauer 5,81 s. PostgreSQL-System-ID `7697730669057405773`, eigener markierter Testbestand auf Loopback 35432. Alle öffentlichen Tabellen vor/nach lesender Navigation unverändert; ausgehende HTTP-Versuche 0. Frühere erfolgreiche Läufe auf `329673db` sind getrennt archiviert. |
| Vollständiges Compose-E2E | `bash scripts/run-e2e.sh` nicht ausgeführt: Docker-CLI in dieser Umgebung nicht vorhanden. Der native Browserlauf qualifiziert die konkrete reale Strecke, nicht alle Compose-Dienste, Volumes, Start-/Stopskripte oder die vollständige bestehende E2E-Suite. |

Der Fehlversuch auf `329673db` betraf die ausschließlich synthetische Instanz
`7697720254017026969` auf Port 35432. Die Diagnose fand zahlreiche private
Clusterdateien mit abweichendem Betriebssystemeigentümer und PostgreSQL-Meldungen
`Permission denied`, unter anderem beim Zugriff auf `base/92930/2662`.
Es wurden weder fachliche Assertions gelockert noch SQL-Rechte umgangen. Für die
Wiederholung wurde ein neuer markierter temporärer Runtime-Pfad außerhalb des
Workspace angelegt: PostgreSQL-System-ID `7697728633607278449`, Loopback-Port 35433,
Testdatenbank `trading_workspace_test`, Betriebssystem-UID 65534. Dieser Lauf
verwendet dieselben Anwendungstests und die unveränderte Migrationskette.

Ein erster Browseraufruf auf `d4321433` endete noch vor Testausführung beim
Modulimport, weil der native Aufruf den bestehenden `NODE_PATH` aus
`scripts/run-e2e.sh` nicht übernommen hatte. Nach Setzen von
`NODE_PATH=<repository>/frontend/node_modules` lief derselbe Test unverändert
erfolgreich. Der fehlgeschlagene Start bleibt im eigenen Log erhalten; er war
kein ausgeführter Browserfall und erforderte keine Datenänderung oder Assertion-
Anpassung. Der neue Owner-Browsertest setzt ausdrücklich
`REPORT_E2E_WRITES_ALLOWED=1` und einen passenden Datenbankmarker voraus; diese
Freigabe war im dokumentierten Lauf aktiviert.

Die abschließende Remoteprüfung fand `origin/main` weiterhin auf `e9aac2b`;
die gelesenen offenen PRs enthalten keinen bereits integrierten Nachfolger dieses
Berichts. Lokal bleibt `20261017_0047` der einzige neue Schema-Head oberhalb des
Main-Heads `20261014_0046`. Keine bestehende Migration und kein Gate-Skript ist
gegenüber main verändert.

Relevante ausführbare Nachweise:

- [Owner-Trace](../../tests/unit/backend/features/trade_position/test_projector_trace.py)
  und [Currency-Units](../../tests/unit/backend/features/trade_position/test_currency_confirmations.py).
- [Currency-PostgreSQL](../../tests/integration/backend/test_execution_currency_confirmations_postgres.py).
- [Periodenregeln](../../tests/unit/backend/features/performance/test_periods.py),
  [Report-Arithmetik/Qualifikation](../../tests/unit/backend/features/performance/test_report.py)
  und [API-Vertrag](../../tests/unit/backend/features/performance/test_api.py).
- [Report-Snapshot/Owner-PostgreSQL](../../tests/integration/backend/test_realized_gross_report_postgres.py)
  und [gespeicherte Lernzustände](../../tests/integration/backend/test_realized_gross_learning_independence_postgres.py).
- [Frontend-Rennen/Pagination](../../frontend/src/features/performance/pages/RealizedGrossPage.test.tsx)
  und [echter Browserfall](../../tests/e2e/realized-gross-report-postgres.spec.ts)
  mit [Datenbankguard](../../tests/e2e/support/realized_gross_database_guard.py).

Die außerhalb des Repositories bereitgestellten Qualifikationsartefakte enthalten
vollständige neue Gate-Logs, Browserantworten, Tabellenfingerprints, Screenshots,
Laufzeitmetadaten, Dateihashes und den überprüfbaren Diff. Die kurzen gezielten
Agentenzusammenfassungen werden als solche bezeichnet und nicht als vollständiges
stdout-Protokoll ausgegeben. Desktop und schmale mobile Ansicht wurden visuell
geprüft; daraus folgt keine umfassende Barrierefreiheits- oder PC-Abnahme.

Nach den erfolgreichen Läufen wurden der lokale API-Server und beide neuen
temporären PostgreSQL-Cluster mit abschließendem Checkpoint geordnet beendet.
Die markierte synthetische Browserdatenbank wurde entfernt. Die abschließenden
temporären Cluster hatten keine Dateien mit abweichendem Betriebssystemeigentümer
und keine PostgreSQL-Dateizugriffsfehler. Der Backend-Testbestand stand vor dem
Shutdown auf `20261017_0047`. Diese Beobachtungen betreffen ausschließlich die
genannten Wegwerfumgebungen.

## Migration, Betrieb und verbleibende Anforderungen

Migration `20261017_0047` liegt additiv auf `20261014_0046`. Sie führt die
Confirmation-Tabelle, begrenzte Eindeutigkeits-/Fremdschlüssel und append-only
Trigger ein. Bestehende wirtschaftliche Execution-Fakten werden weder geändert
noch auf EUR gesetzt. Der Downgrade verweigert ausdrücklich das Entfernen, sobald
Bestätigungen existieren; er ist dann kein verlustfreier Rückbau. Bei leerer neuer
Relation bleibt der geprüfte Rückbau möglich. Frühere freigegebene Migrationen
wurden nicht nachträglich bearbeitet.
`backend/migrations/env.py` registriert das neue ORM-Modell in der bestehenden
Alembic-Metadatenbasis; die 46 vorhandenen Revisionsdateien sind unverändert.

Neue Captures können die bestätigte tatsächliche Preiswährung speichern.
Bestehende Buchungen lassen sich über eine bewusste Owner-Aktion ergänzen, mit
historischer Bestätigungszeit und unveränderten Mengen, Preisen, Ausführungsdaten
und Sortierankern. Jede wirtschaftliche Ersatzexecution braucht ihre eigene
Bestätigung. Ohne belegte Währung zeigt der Bericht eine Datenlücke. Es wurde
weder gemessen noch behauptet, welcher Anteil realer Nutzerbestände schon
auswertbar ist. Berichtswährung und synthetische EUR-Fixtures ersetzen diese
Herkunft nicht.

Bei der Schlussprüfung wurde ein bereits auf `e9aac2b` vorhandener Learning-Randfall
statisch festgestellt: Zwei erstmalige parallele `execute-as-trade`-Commands mit
demselben Idempotency-Key können nach ungeschütztem Lookup am bestehenden Unique-
Constraint kollidieren; der Verlierer wird generisch als 422 übersetzt. Das ist
keine neu reproduzierte PostgreSQL-Störung und keine Doppelbuchung. Die neue
Currency-Command-Konkurrenzgrenze sowie sequenzieller Learning-Replay und atomarer
Rollback wurden separat geprüft. Eine pauschale Replay-Zusage für jeden bestehenden
Learning-Parallelfall wird daraus nicht abgeleitet.

Gebühren, Kommissionen und Steuern bleiben außerhalb des Bruttovertrags; fehlende
Kosten werden nicht als null behandelt. Trade-Kohorten, Trefferquote,
Durchschnitt/Median, Profit-Faktor, Prozessbewertung, Diagramme und Export bleiben
im ursprünglichen Backlog. Netto-/FX-/Equity-/Drawdown-/TWR-/IRR- und weitere
Kennzahlen benötigen ihre eigenen Daten- und Methodenverträge. Es wurden keine
Handelsentscheidungen automatisiert, Modelle aktiviert oder Livekurse abgerufen.

Der nächste Schritt der damaligen lokalen Übergabe war die Entscheidung über den
fertigen Schnitt. Die darauf folgende ausdrückliche Veröffentlichungsanweisung
ist im nachstehenden Nachtrag berücksichtigt.

## Integrations- und Auslieferungsfortsetzung 18.10.2026

Der Nutzer hat ausdrücklich beauftragt: **„wenn prüfungen grün mergen und für den
pc verfügbar machen“**. Damit sind Veröffentlichung, normaler geschützter Merge
und Bereitstellung über den vorhandenen PC-Updateweg nach erfolgreichen Prüfungen
autorisiert. Diese Freigabe erweitert weder den Kennzahlenvertrag noch M8 und
belegt keine Installation oder fachliche Beobachtung auf JMBbot.

Der erneut gelesene Remote-Ausgangspunkt blieb `e9aac2bfaadeb9133a6ed07e42d1dec39836b156`
/ 1.5.8. Nach Wiederherstellung des lokalen Arbeitsbereichs wurden der erhaltene
Vollpatch und sämtliche 102 manifestierten Evidence-Dateien unabhängig geprüft.
Der rekonstruierte gesamte Git-Tree ist exakt
`fc12f0f7fa8d8e8157be3a9dc3818169301c48ec`; alle 84 geänderten Dateien stimmen mit
dem ausgelieferten SHA-256-Manifest überein. Der veröffentlichte Recovery-Commit
`d8dc36f5f891a6dd29cb0a0a8dba41d485201f76` auf
`feat/realized-gross-report-20261018` bindet diesen unveränderten Tree. Er ersetzt
nicht die historischen Commitkennungen der tatsächlich ausgeführten lokalen Tests.

PR #249 wurde am 18.10.2026 separat als
`79c5e0f44c055e2bfaf526db7c3841ab92018ff8` gemergt. Sein geprüfter Integrations-Head
`5b6a877e5610176a81e99aa5c39833c1b402ea63` enthält das erneut gelesene main;
die vier ursprünglichen Fix-Dateien sind bytegleich mit dessen geprüftem Head
`1ad81344a66be9e70c772828081b2ff7ac13ef1c`. Backend-Run `39129318977`, Frontend
`39129318998`, End-to-End `39129318963` und publication guards `39129318893`
wurden unmittelbar vor dem Merge erfolgreich gelesen. Der Performance-PR
übernimmt diesen Integrationsstand und ändert selbst kein Basiswertformular.

Die ergänzte CI-Grenze ist `End-to-End / realized gross owner` im vorhandenen
End-to-End-Workflow. `scripts/run-realized-gross-e2e.sh` erzeugt ausschließlich
einen eigenen synthetischen Compose-Stack, eine neue markierte PostgreSQL-17-
Datenbank und leere Testkonfiguration. Der vorhandene Berichtstest und sein
Datenbankguard bleiben unverändert. Ein erfolgreich beendeter Prozess genügt
nicht: Der JSON-Bericht muss genau einen bestandenen Fall, keine übersprungenen
oder instabilen Fälle und keinen Wiederholungsversuch ausweisen. Der bestehende
Smoke-Job bleibt erhalten; dessen getrennte Tests ersetzen diesen Owner-Lauf nicht.

Der erste neue Compose-Owner-Lauf auf PR-Head
`7414062ea289ef710b9175737500c38fdc26b224` beziehungsweise CI-Merge-Commit
`059f4c5de67ca8865b5fd7bfd92eedbfe2933276` ist ausdrücklich **fehlgeschlagen**:
[Run 39130432449, Job 117684304391](https://github.com/burckhju/trading-workspace/actions/runs/39130432449/job/117684304391)
meldet einen fehlgeschlagenen Fall ohne Skip oder Retry. Images, Migration auf
`20261017_0047`, PostgreSQL 17.11 und die Container-Healthchecks waren erfolgreich.
Der Datenbankguard konnte danach `127.0.0.1:35432` nicht erreichen. Der Fehler trat
vor der ersten synthetischen Owner-Buchung auf; der eigene Teststack wurde entfernt.
Das ausschließlich interne Docker-Netz hatte die benötigte Host-Portverbindung
nicht hergestellt. Dieser Lauf ist kein fachlicher Browsernachweis.

Die Korrektur bleibt im neuen CI-Runner: Das Backend ist ausschließlich mit dem
internen Projektnetz verbunden und hat keinen veröffentlichten Hostport.
PostgreSQL und Frontend besitzen zusätzlich eine eigene Ingress-Bridge für die
an `127.0.0.1` gebundenen Testports. Der vorhandene Frontend-Proxy erreicht das
Backend über das interne Netz. Preflight, Prüfung der tatsächlichen Container-
Netzmitgliedschaften und Portbindungen sowie Cleanup umfassen beide eigenen
Netze. Die Laufzeitevidenz wird als `network-and-ports.json` archiviert.
Produktions-Compose, Browserfall, Datenbankguard und regulärer Smoke-Job bleiben
unverändert. Der korrigierte Runner benötigt einen neuen erfolgreichen aktuellen
CI-Lauf; statische Konfigurationsprüfungen ersetzen diesen Nachweis nicht.

Die neue Softwareversion ist [1.5.9](../releases/V1.5.9-REALIZED-GROSS-REPORT.md).
PR-Checks und danach die vollständigen Backend-, Frontend- und End-to-End-
Workflows des tatsächlichen main-Pushs sind getrennte Veröffentlichungsgates.
Erst deren Erfolg auf genau dem aktuellen main-Commit erlaubt dem unveränderten
Version-Workflow, den neuen Tag zu erzeugen. Tatsächlich abgerufene Runs und
Commitbindungen stehen im Auslieferungs-PR; der geprüfte Tag bestimmt den
konkreten Update-Commit. Ein vorhandener Tag wird nicht verschoben.

**Genau nächster sinnvoller Schritt nach dieser Bereitstellung:** die bestehende
PC-Installation mit dem veröffentlichten Tag und seinem geprüften vollständigen
Commit über den vorhandenen Launcher aktualisieren und den Zustand anschließend
lesend prüfen. Echte Bestandskorrekturen oder Währungsbestätigungen erfolgen
weiterhin ausschließlich durch die bewusste zuständige Nutzeraktion.
