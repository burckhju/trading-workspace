# Abgeschlossene Trades — entschiedener Vertrag und Readiness

Prüfstand: **20.10.2026**, `main` und Tag `v1.5.11` auf
`5e9ede2dc29f52eaff601d30614df6bc9c25c426`, Tree
`303e56c078efd578e6e147edcf2ebac6accf6ba5`. Aufgabenbranch:
`docs/closed-trade-report-readiness`.
Arbeitsstatus bleibt ausschließlich in
[PB-019 Kennzahlen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics)
und [Tradeübergreifende Statistiken](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics)
sowie [Periodenauswertungen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations).
Dieses Dokument schafft weder eine Feature-ID noch ein zweites Statusregister.

## Entscheidung vom 20.10.2026 und bestätigter Umfang

**Die drei unten beschriebenen Regeln sind zur Umsetzung freigegeben.** Der
Startauftrag vom 20.10.2026, Abschnitt 5, enthielt zunächst einen Vorschlag.
Nach dessen prüfbarer Ausarbeitung in PR #270 fragte der Nutzer nach den
jeweiligen Auswirkungen für die Bedienung. Anschließend bestätigte er den
erläuterten Umfang mit **„ok, umsetzen“**. Diese spätere Entscheidung umfasst
Vollabschlusskohorte, vollständige monetäre Qualifikation mit sichtbaren Lücken
und Klassifikation nach ungerundetem Vorzeichen.
[ADR-S10-009](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md)
hält diese neue Entscheidung getrennt vom weiterhin gültigen
[SELL-Vertrag](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
fest. Sie ist keine Abnahme der fertigen Umsetzung und erweitert keine frühere
Merge-, Release- oder PC-Freigabe für andere Änderungen.

**Bestätigte Gesamtentscheidung:** Ein rein lesender Bericht wählt eigene
Trades nach ihrem heute wirksamen tatsächlichen Vollabschluss im Zeitraum aus,
zeigt je Trade das gesamte qualifizierte Bruttoergebnis und zählt vollständig
qualifizierte positive, negative und exakt neutrale Ergebnisse. Ungeklärte
potenziell relevante Trades bleiben sichtbar und verhindern eine vollständige
Gesamtsumme. Trefferquote, Durchschnitt, Median und Profit-Faktor gehören nicht
zum ersten Schnitt. Dafür werden keine neue Eingabe, Migration oder dauerhafte
Trade-Währung benötigt. Der konkrete Schnitt verwendet
`GET /api/v1/performance/closed-trades`, die Frontendroute
`/performance/closed-trades` und die Definition `closed-trade-gross-v1`.

| Bestätigte Regel | Beispiel und Nutzerwirkung | Abgrenzung / Konsequenz |
|---|---|---|
| Vollabschlusskohorte: stabile Trade-ID einmal; aktuell wirksamer Abschluss-SELL bestimmt den Zeitraum; alle wirksamen SELL-Beiträge dieses Trades gehören zum Ergebnis. Eigene ausdrücklich erfasste EXTERNAL-Trades zählen mit. | T1 wird im Oktober einmal mit **50 EUR** ausgewertet, obwohl der Oktober-SELL allein **30 EUR** beiträgt. Im September ist T1 kein abgeschlossener Trade. | Nur Verkäufe im Zeitraum auszuwerten ist bereits der bestehende Bericht. Eine Kohorte anhand des damaligen Wissensstands würde einen gesonderten historischen Quellenvertrag benötigen. |
| Vollständige Qualifikation je Trade und konservative Abdeckung: alle benötigten Kaufkosten und sämtliche Erlösbeiträge müssen in derselben belegten Währung vorliegen. Ungeklärte Historie/Abschlusszuordnung verhindert Vollständigkeit. | Ein früherer abweichender USD-SELL macht ein vollständiges EUR-Tradeergebnis unberechenbar, auch wenn der letzte EUR-SELL einzeln verwendbar bleibt. T4 zählt als Lücke, nicht als Gewinner oder neutral. | Nur vollständig bekannte Trades auszuwählen und den Rest getrennt zu melden wäre eine Auswertung einer bekannten Teilmenge; sie dürfte nicht als vollständige Abschlusskohorte bezeichnet werden. Eine vollständige Summe trotz potenziell relevanter Lücken wird nicht vorgeschlagen. |
| Vorzeichen des vollständigen **ungerundeten Owner-Ergebnisses**; neutral nur bei exakt null. Zähler nur für qualifizierte Trades; keine Quote im ersten Schnitt. | `+0.004 EUR` ist positiv und `-0.004 EUR` negativ, obwohl beide mit zwei Nachkommastellen als `0,00 EUR` erscheinen. Rohwert und Erklärung werden zugänglich. | Eine wirtschaftliche Break-even-Schwelle oder Klassifikation nach Anzeige wäre eine andere Kennzahl mit ausdrücklich zu definierender Währungs-/Präzisionsregel. Ohne Signumfreigabe können die neuen Zähler nicht geliefert werden. |

Die bereits bestätigte Ausführungswährungswiederverwendung gilt unverändert.
Die neue Entscheidung ergänzt ausschließlich Berichtsauswahl,
Trade-Gesamtqualifikation, Abdeckung und Klassifikation. Journal-Testsicherung
und Listennavigation behalten ihre eigenständigen Entwicklungs-PRs.

## Bestätigter Vertrag

### Identität, Abschluss und Wissensstand

Grundlage sind tatsächliche Trades des aktuellen Workspace, keine externen
Beobachtungen. `Trade.id` zählt einmal, auch bei identischem Produktnamen oder
mehreren Journal-/Evidence-/Lessonrelationen. Storno ist kein Verkauf.
Nachbeobachtung, CURRENT-Review, Journal und Lesson sind keine Finanzvoraussetzung.

Die vollständige wirksame Historie wird mit
`PositionProjector.project_with_trace()` qualifiziert. Abschlussquelle ist der
SELL-Trace mit positiver Vorhermenge und `open_quantity_after == 0`; die
zugehörige Execution-ID wird ausdrücklich referenziert. Der bloße
Positionszustand (`Position.is_closed`), ein manueller Status oder ein leeres Zahlenfeld genügt
nicht. Die Owner-Regel gegen BUY nach Vollabschluss bleibt erhalten. Fehlende
Position, fehlende Historie, unzulässige Reihenfolge oder andere Projektionsfehler
werden nicht als offene Trades oder als Abwesenheit umgedeutet.

Es gelten heute wirksame korrigierte Fakten. Eine zulässige Preis-, Mengen-,
Datums- oder Währungskorrektur kann Ergebnis, Abschlussperiode oder
Abschlusseignung ändern. Historische Executions, Journal-/Review-/Evidence-
Snapshots bleiben erhalten. Eine neue Berichtsbasis zeigt den Wechsel; es wird
kein damaliger Wissensstand rekonstruiert.

### Zeitraum, Währung und Beträge

Inklusive Kalendertage, ausdrücklich gewählte Berichtswährung und IANA-Zone
verwenden den bestehenden `periods.py`-Vertrag. Nur die tatsächliche
Abschluss-Execution bestimmt die Periodenzugehörigkeit. Bei Date-only muss das
gesamte mögliche Tagesintervall enthalten sein; Teilüberschneidung bleibt
mehrdeutig, uninterpretierbare Quelle unbekannt. Der interne
`Position.closed_at`-Anker wird niemals als bekannte Uhrzeit ausgegeben.

Der Zeitraum beschneidet keine Kostenbasis und keine früheren Ergebnisbeiträge.
Der Betrag ist das vollständige Owner-Ergebnis aller wirksamen Verkäufe des
qualifizierten Trades. Die bestehende Reihenfolge
`(executed_at, recorded_at, id)`, Decimal-Operationen und der ausgewiesene
`cost_basis_before_close_reset` bleiben unverändert. Kein neuer
Average-Cost-Algorithmus und kein Ausgleich eines Decimalrests wird eingeführt.

Der gemeinsame Execution-Resolver gilt unverändert: direkte aktuelle Erklärung,
danach bestätigter gleichseitiger Vorgänger, danach vollständig bekannter und
einheitlicher vorheriger wirksamer BUY-Präfix. Spätere Käufe heilen keine
früheren unbekannten Käufe; GET erzeugt keine Bestätigungszeilen.
Für das vollständige Tradeergebnis müssen alle erforderlichen BUY-Preisquellen
und alle wirksamen SELL-Erlösquellen qualifiziert sein. Die letzte SELL-Währung
allein beweist weder vollständiges EUR noch einen sicheren USD-Ausschluss.
Ein vollständig belegter einwährungsfähiger anderer Trade darf ausgeschlossen
werden; unbekannte oder gemischte Quellen bleiben eine potenzielle Lücke.

Rohbeträge bleiben endliche Decimalstrings, Anzeige nach belegter
`minor_unit`/`reference_version` und `ROUND_HALF_EVEN`. Zuerst Rohwerte summieren,
danach anzeigen; Rundungsdifferenzen zu einzeln gerundeten Zeilen erklären.
Die Signumregel verwendet den ungerundeten Owner-Wert, einschließlich seiner
bereits qualifizierten endlichen Decimalpräzision. Keine versteckte Toleranz.

### Disjunkte Zähler und Vollständigkeit

Die folgenden Bezeichnungen sind fachliche Gruppen des **bestätigten Vertrags**.
Die konkreten DTO-Zähler sind in der neuen Qualifikation zugeordnet. Alle Zähler
zählen Trade-IDs. Pro untersuchtem
Workspace-Trade gilt die erste zutreffende Gruppe; zusätzliche Gründe dürfen
erklärt werden, erhöhen aber keinen Zähler:

| Priorität | Gruppe | Wirkung |
|---|---|---|
| 1 | Storniert | Sichtbarer Ausschluss; weder Abschluss noch Geldbeitrag. |
| 2 | Historie oder Abschluss nicht zuverlässig bestimmbar | Relevante Unklarheit; keine Geldzahl oder Signumklassifikation. |
| 3 | Gültig projiziert und noch offen, einschließlich BUY-only | Sichtbarer Ausschluss aus der Abschlusskohorte. |
| 4 | Gültig abgeschlossen, Abschluss sicher außerhalb des Zeitraums | Sichtbarer Ausschluss; eine monetäre Unklarheit dieses sicher anderen Zeitraums blockiert den gewählten Zeitraum nicht. |
| 5 | Gültig abgeschlossen, vollständige Preisquellen sicher in einer anderen einheitlichen Währung | Sichtbarer Währungsausschluss; keine FX-Addition. |
| 6 | Gültig abgeschlossen, Zeitraum mehrdeutig oder unbekannt und Währungszugehörigkeit nicht sicher ausgeschlossen | Relevante zeitliche Unklarheit; nicht als sicher abgeschlossener Trade dieser Periode zählen. |
| 7 | Abschluss sicher in der Periode, vollständiges Ergebnis monetär nicht qualifiziert | Wirtschaftlich zugeordneter, monetär ungeklärter Trade. |
| 8 | Abschluss sicher in der Periode, vollständiges Ergebnis in Berichtswährung qualifiziert | Genau eine positive, negative oder neutrale Klassifikation und ein vollständiger Tradebetrag. |

Damit gilt: untersuchte Trades = Summe der acht Gruppen;
qualifizierte Trades = positive + negative + neutrale;
relevante ungeklärte Fälle = Gruppen 2 + 6 + 7.
Sicher zugeordnete wirtschaftliche Abschlüsse der Währungsauswahl bestehen aus
Gruppen 7 + 8; dieser Zähler wird getrennt von zeitlich/historisch unklaren
Kandidaten ausgewiesen. Reine Beobachtungen und fremde Workspace-IDs sind
keine untersuchten tatsächlichen Trades dieses Readers.

**Bewusste Folge der bestätigten Abdeckungsregel:** Eine nicht zuverlässig
projektierbare eigene Historie kann ohne belegbare Abschlusszuordnung auch
einen ansonsten bekannten Monatsbericht unvollständig machen. Sie wird weder
durch vermeintlich alten Zeitstempel noch durch letzten SELL-Code versteckt.
Soll ein engerer Ausschluss zulässig sein, braucht er einen nachgewiesenen
fachlichen Ausschlussgrund; ein Heuristikdatum wird nicht eingeführt.

| Gruppen 8 / 2+6+7 | Status | Gesamtsumme / Teilsumme |
|---|---|---|
| Keine / keine | `EMPTY` | `"0"` / `null`, ausdrücklich leere Auswahl. |
| Mindestens eine / keine | `COMPLETE` | Vollständige Summe, auch exakt `"0"` / `null`. |
| Mindestens eine / mindestens eine | `PARTIAL` | `null` / Summe ausschließlich vollständiger qualifizierter Tradeergebnisse, auch `"0"`. |
| Keine / mindestens eine | `NOT_COMPUTABLE` | `null` / `null`; keine künstliche Null. |

Innerhalb eines ungeklärten Trades wird kein bekannter Restbetrag zur
Trade-Teilsumme oder Gewinnerklassifikation hochgestuft. Die Berichts-Teilsumme
ist die Summe vollständig qualifizierter Trades. Einzelne ältere SELLs bleiben
im Quellendetail mit ihrer eigenen Bedeutung nachvollziehbar.

## Unabhängige synthetische Sollfälle

Die folgenden Werte wurden vor der Umsetzung unabhängig festgelegt und sind
nun Erwartungen des bestätigten Vertrags. Sie beweisen keine Währung realer
Nutzerdaten; ihre tatsächliche Ausführung ist gesondert nachzuweisen.
T1 erhält genau eine synthetische EUR-BUY-Erklärung, danach die bestehende
v2-Wiederverwendung. Alle hier datierten Buchungen verwenden Europe/Berlin.

| T1-Ausführung | Owner-Beitrag |
|---|---|
| 05.08.2026 BUY 100 × 2,00 | Kaufbasis 200,00 |
| 12.08.2026 SELL 20 × 2,50 | +10,00 |
| 02.09.2026 SELL 30 × 3,00 | +30,00 |
| 06.09.2026 BUY 50 × 4,00 | Danach Menge 100, Basis 300,00, Average Cost 3,00 |
| 12.09.2026 SELL 40 × 2,50 | −20,00; danach Menge 60, Basis 180,00 |
| 03.10.2026 SELL 60 × 3,50 | +30,00; tatsächlicher Vollabschluss |

| Auswertung nur T1 | Ursprünglich | Nach wirksamer Preiskorrektur des September-SELL auf 3,00 |
|---|---|---|
| Bestehender September-SELL-Bericht | +10,00 EUR | +30,00 EUR |
| Bestehender Oktober-SELL-Bericht | +30,00 EUR | +30,00 EUR |
| September-Abschlusskohorte | `EMPTY`, kein Abschluss | Weiterhin kein Abschluss |
| Oktober-Abschlusskohorte | 1 positiver Trade, vollständig +50,00 EUR | Derselbe Trade einmal, vollständig +70,00 EUR |

Vor dem letzten SELL bleibt T1 offen; seine September-SELLs sind weiterhin
auswertbar. Die alte korrigierte Execution-ID bleibt Quelle, zählt aber nicht
zusätzlich. Wird der finale SELL zulässig auf 30.09. verschoben, wechselt der
vollständige Trade in die Septemberkohorte. Wird seine Menge zulässig von 60
auf 59 korrigiert, bleibt eine Einheit offen und T1 gehört aktuell in keine
Abschlusskohorte.

| Ergänzung mit eigener Trade-ID | Erwartetes Oktober-Ergebnis bei EUR-Auswahl |
|---|---|
| T2: BUY 10 × 5,00; Voll-SELL 10 × 4,00 im Oktober, EUR belegt | −10,00 EUR; negativ. |
| T3: BUY 10 × 5,00; Voll-SELL 10 × 5,00 im Oktober, EUR belegt | Exakt 0,00 EUR; neutral. |
| T4: BUY 10 × 5,00; Voll-SELL 10 × 6,00 im Oktober, Herkunft unzureichend | Monetär ungeklärt; kein EUR-Betrag und keine Signumklasse. |
| T5: vollständig belegter USD-Trade mit Vollabschluss im Oktober | Bekannte andere Währung; ausgeschlossen. |
| T6: EUR-BUY 10 × 5,00; SELL 5 × 7,00 im Oktober | Offen; der bestehende SELL-Bericht kann +10,00 EUR zeigen, keine Abschlussklassifikation. |
| Tatsächlich stornierter BUY-Fehleintrag / reine externe Beobachtung | Storno-Ausschluss / kein Trade des Readers; kein Gewinn-/Verlustfall. |

Nur T1/T2/T3: **3 qualifizierte Trades, 1 positiv, 1 negativ, 1 neutral,
vollständige Summe +40,00 EUR**, nach T1-Korrektur **+60,00 EUR**.
Mit T4 bleiben 3 qualifizierte und 1 monetär ungeklärter Trade;
**+40,00 / +60,00 EUR sind ausschließlich Teilsummen** (`PARTIAL`).
Nur T4 ergibt `NOT_COMPUTABLE`; nur T3 `COMPLETE` mit Null; ausschließlich
sicher ausgeschlossene Fälle ergeben `EMPTY`. T5/T6 verändern die Signumzähler
nicht. Gleiche Produktnamen, mehrere Seiten oder Lernrelationen vervielfachen nichts.

Zusätzlich vor Fachimplementierung festgelegte Grenzen: frühere abweichende
SELL-Währung trotz bekannter letzter EUR-Währung; Date-only an Monats-/DST-
Grenzen; `0`, `+0.004` und `-0.004`; fehlende Position/BUY-Historie; mehrere
Seiten; gleiche Produktnamen bei unterschiedlichen IDs; Preis-, Datums-,
Mengen- und Währungskorrektur mit unverändert erhaltenen Originalquellen.

## Quellenstand vor der Umsetzung und festgelegte Prüfpflichten

Die folgende Matrix hält den vor der Fachimplementierung gelesenen Bestand und
die daraus abgeleiteten Ergänzungen fest. Der konkrete neue Consumer und seine
Prüfdateien sind in der [Umsetzungsqualifikation](CLOSED_TRADES_REPORT_QUALIFICATION.md)
zugeordnet; die historischen Nachweise werden dadurch nicht umdatiert.

| Vertrag / vorhandener Owner oder Consumer | Gelesene Quellen und vorhandene Tests | Ergänzung und erforderlicher Nachweis |
|---|---|---|
| Identität, Storno, wirksame Historie, Replay | [Trade-/Execution-/Position-Modell](../../backend/app/features/trade_position/domain/models.py), [Repositories](../../backend/app/features/trade_position/persistence/repositories.py), [Owner-Service](../../backend/app/features/trade_position/service/application.py), [Capturevertrag](../trade-capture-safety.md); `test_trade_read.py`, `test_corrections_timeline.py`, `test_capture_safety.py` unter `tests/unit/backend/features/trade_position/` | Vollabschlussquelle aus wirksamem Trace binden; ungültige Historien im neuen Tradezähler sichtbar erhalten. Bestehende Commands nicht ändern. |
| Einzige Average-Cost-Rechnung | [Projector](../../backend/app/features/trade_position/domain/projector.py), [Trace-Tests](../../tests/unit/backend/features/trade_position/test_projector_trace.py), [PG-Trace](../../tests/integration/backend/test_realized_gross_trace_postgres.py) | Trace konsumieren; keine zweite Berechnung aus gespeicherter Positionssumme oder UI. |
| Währungsherkunft | [Reiner Resolver](../../backend/app/features/trade_position/domain/currency_resolution.py), [Bestätigungsservice](../../backend/app/features/trade_position/service/currency_confirmations.py), [Resolver-Units](../../tests/unit/backend/features/trade_position/test_currency_resolution.py), [PG-Wiederverwendung](../../tests/integration/backend/test_execution_currency_reuse_postgres.py) | Gesamte BUY-/SELL-Qualifikation des abgeschlossenen Trades, keine neue SELL-Erklärung. Frühere SELL-Erlöse sind für den Gesamttrade nötig, obwohl sie keine spätere Kaufkostenkomponente sind. |
| Zeitraum | [Periodenfunktionen](../../backend/app/features/performance/domain/periods.py), [Perioden-Units](../../tests/unit/backend/features/performance/test_periods.py) | Auf konkrete Abschlussquelle anwenden; keine `closed_at`-Heuristik. |
| Vollständiger konsistenter Read | [Snapshotreader](../../backend/app/features/performance/service/reader.py), [Service](../../backend/app/features/performance/service/application.py), [PG-Report/Races](../../tests/integration/backend/test_realized_gross_report_postgres.py) | Reader hat bereits alle benötigten Workspace-Trade-, Execution-, Supersession-, Bestätigungs- und Anzeigenquellen. Neue Auswertung aus demselben materialisierten Snapshot; echter korrigierender Writer-Race für Abschlusszuordnung/Counts zusätzlich nachzuweisen. |
| Bestehender SELL-Bericht | [Report](../../backend/app/features/performance/domain/report.py), [DTO](../../backend/app/features/performance/api/dtos.py), [Router](../../backend/app/features/performance/api/router.py), [Report-Units](../../tests/unit/backend/features/performance/test_report.py), [API-Units](../../tests/unit/backend/features/performance/test_api.py) | `realized-gross-sell-v2` bleibt kompatibel. Dessen periodenbeschnittene `USABLE`-Zeilen lassen sich nicht zum vollständigen Tradebericht gruppieren. Reine Quell-/Anzeigehelfer allenfalls eng gemeinsam nutzen. |
| Lernen unabhängig / lesend | [PG-Lernunabhängigkeit](../../tests/integration/backend/test_realized_gross_learning_independence_postgres.py), unveränderte Tabellen-Fingerprints im PG-Report | Auch neuer GET, lokale Pagination und Drill-down schreiben nichts und rufen keine Provider auf; Read-Fingerprints nur innerhalb der Lesefenster vergleichen. |
| Oberfläche und echter Owner-Weg | [Bestehende Seite](../../frontend/src/features/performance/pages/RealizedGrossPage.tsx), [UI-Tests](../../frontend/src/features/performance/pages/RealizedGrossPage.test.tsx), [Owner-Browserfall](../../tests/e2e/realized-gross-report-postgres.spec.ts), [Router](../../frontend/src/app/router.tsx) | Eindeutige Navigation „Verkäufe im Zeitraum“ / „Trades mit Vollabschluss im Zeitraum“, ein Trade pro Zeile, alte SELL-Beiträge im Quellendetail, Zustände/Rennen/Seiten prüfen. Neuer tatsächlicher Browser→Owner→PostgreSQL-Nachweis und gesichtete Desktop-/Mobilbilder erforderlich. |

Gelesener Testcode ist kein neuer Testlauf. Die bestehenden
[Berichts-](PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) und
[Währungsqualifikationen](EXECUTION_CURRENCY_REUSE_QUALIFICATION.md) bleiben an
ihre damaligen Code-/Runstände gebunden.

Der bestehende Reader begrenzt auf **2.000 Trades, 20.000 Executions,
40.000 Bestätigungen**, **100.000 Provenienzverknüpfungen** im Report und
**10.000 ms je Datenbankstatement**. Überschreitung führt zum vollständigen
Fehler, nie zur gekürzten Historie. Vor neuer Nutzung Grenzen einschließlich
Gesamtprovenienz prüfen, nicht pauschal anheben. Die kurze frische
`REPEATABLE READ READ ONLY`-Transaktion endet vor Berechnung/Bedienung; keine
globale Isolation, `FOR UPDATE`, N+1-Schleife oder künstliche HTTP-Gesamtperiode.
Definition, Filter und materialisierte Eingaben binden die neue Quellenbasis.

Die [Foundation-Architektur](../foundation/ARCHITECTURE.md) trennt Finanz- und
Lernprozess ausdrücklich. [Projektprinzipien](../foundation/PROJECT.md) und
[Model Book](../foundation/MODEL_BOOK.md) verlangen eindeutige Zuständigkeit,
nachvollziehbare Einheiten/Versionen und unveränderte historische Zuordnungen.
Der erste Schnitt erfüllt weder alle ursprünglichen
[M8-Anforderungen](../foundation/archive/ROADMAP_2026-07-22.md#m8--performance)
noch fachliche Abnahme, Release, Installation oder Modellaktivierung.

## Historische Prüfung des ursprünglichen Dokumentationsschnitts

Dieser Abschnitt beschreibt ausschließlich den ursprünglichen Proposal-Head
`59d9de576b7ec53bed4f6ef7eeeef64324b1b426`. Die nachfolgende Umsetzungsfreigabe
und neue Anwendungstests machen diese damaligen Tests nicht rückwirkend zu
Nachweisen der Abschlussübersicht.

Auf dem genannten unveränderten Anwendungscode wurden am 20.10.2026 mit Python
**3.12.14** sechs eng begrenzte synthetische In-Memory-Prüfungen ausgeführt:
T1-Owner/September/Oktober/Exitquelle; T1 vor letztem SELL; wirksame
Preiskorrektur und Basiswechsel; unabhängige T2/T3-Ownerwerte und arithmetische
Kohorten-Sollzahlen; Rohvorzeichen gegenüber Anzeige; bestehender späterer
EUR-SELL bei früherem abweichendem USD-Erlös. Alle sechs Assertionsgruppen
bestanden. Sie verwenden die bestehenden `performance/fixtures.py`-Fakten,
`PositionProjector`, `build_report`, `periods.py` und `displayed`; keine neue
produktive Auswahl-/Klassifikationsfunktion wurde dabei implementiert.

Die unabhängigen Sollzahlen sind oben ausdrücklich vorgegeben. Der Ablauf
prüft sie gegen bestehende Owner-/SELL-Funktionen; **er ist weder ein neuer
Abschlussberichtstest noch eine Ausführung der Pytest-Suite, API, PostgreSQL
oder Browserstrecke**. Pytest und Backend-Abhängigkeiten waren in diesem
Dokumentationsarbeitsstand bei dieser ersten Prüfung nicht installiert. Für eine
reine Vorschlagsdatei wurden keine Repository-Dependencies, Gates oder Schutzflags verändert.

Eine anschließende gezielte Prüfung des unveränderten Anwendungscodes mit den
gepinnten Backend-Testabhängigkeiten und Python 3.12.14 bestand mit **123 Tests,
null Fehlern und null Skips**:

```bash
PYTHONPATH="$PWD/backend:$PWD" python -m pytest -c backend/pyproject.toml \
  tests/unit/backend/features/trade_position/test_projector_trace.py \
  tests/unit/backend/features/trade_position/test_currency_resolution.py \
  tests/unit/backend/features/performance
```

Die Provider-/Telegram-Flags waren wie im bestehenden Backend-Prüfskript
deaktiviert. Ein erster Lauf im eingeschränkten lokalen Ausführungskontext
blieb beim API-Testmodul ohne Abschluss hängen und wurde mit Exit 130 beendet.
Der identische Lauf im regulär genehmigten Ausführungskontext bestand in
0,94 Sekunden; keine Code-/Assertion-/Gateänderung. Die 123 Fälle prüfen
vorhandene Owner-, Währungs-, Perioden-, API- und SELL-Verträge, weiterhin
keine neue Kohortenfunktion und keine native PostgreSQL-/Browserstrecke.

Unveränderte geprüfte Code-Teilbäume:
`backend/app/features/trade_position` = `7069a3f725d5b90531333e6ea49472231059805d`,
`backend/app/features/performance` = `5dd810ad63ec50e8104c442e58b6e83aed546568`;
verwendete Performance-Unitfixtures im Teilbaum
`tests/unit/backend/features/performance` = `6a1b8890d5b2522642e162be908cc0ff8859eecd`.
Alle darin verlinkten lokalen Dateien existieren.
`git diff --no-index --check /dev/null docs/implementation/CLOSED_TRADES_READINESS.md`
bestand für die neue Datei. Es wurden nur diese Vorschlagsdatei und keine
Anwendungs-, Migrations-, Test- oder Gate-Dateien geändert.

Die spätere Zustimmung ist im Entscheidungsabschnitt dokumentiert. Die
Fortsetzung verwendet denselben Entwicklungsbranch und PR #270 für den
konkreten Performance-Consumer. Neue Goldens, Zähler-, Korrektur-, Lesefenster-
und Browsernachweise werden an den jeweils tatsächlich geprüften Code gebunden;
die alten 123 Tests sind kein Ersatz dafür.
