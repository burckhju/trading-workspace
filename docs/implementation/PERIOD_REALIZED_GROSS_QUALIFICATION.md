# Qualifikation: Owner-Trace für realisierte Bruttobeiträge

Prüftag: 17.10.2026. Auftrag: Startprompt 08, Fassung 1.1.
Maßgeblicher Aufgabenstatus bleibt im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations).
Dies ist ein Nachweis des abgegrenzten Entwicklungsstands, keine zweite Statusliste,
neue FT-ID, Fachfreigabe, Release- oder Installationsbestätigung.

**Historischer Nachweis des Vorleistungsschritts:** Die folgenden Ergebnisse
beziehen sich unverändert auf `8a3b9d66`. Die später am selben Tag erteilte
Umsetzungsfreigabe und der darauf aufbauende Währungs-/Berichtsschnitt stehen in
[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
und der [anschließenden Berichtsqualifikation](PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md).
Die früher hier dokumentierte offene DoR beschreibt ihren damaligen Zustand.

## Ergebnis und genaue Grenze

Der bestehende FT-010-Owner liefert additiv einen unveränderlichen Trace mit den
direkten arithmetischen SELL-Beiträgen und ihrer vollständigen vorherigen wirksamen
Execution-Historie. Die bestehende Average-Cost-Schleife, Decimal-Reihenfolge,
Validierung und der `Position`-Rückgabevertrag bleiben erhalten. Unabhängige
Erwartungswerte und ein echter PostgreSQL-/REST-Korrekturfall qualifizieren diese
Vorleistung.

Die **vertikale monetäre Periodenauswertung ist noch nicht ready und nicht
implementiert**. Es fehlt der qualifizierte historische Erfassungs-/Bestätigungsvertrag
der tatsächlichen Ausführungswährung. Auch die neue Auswahl-/Perioden-/Ausgabe-
Semantik ist noch nicht fachlich bestätigt. Bericht-API, UI, Währungsmigration,
Snapshotreader und Browserabnahme werden durch diesen Trace nicht vorweggenommen.
Die [Quellenmatrix und der konkrete Entscheidungsvorschlag](PERIOD_REALIZED_GROSS_READINESS.md)
begründen diese Grenze; die synthetische EUR-Annahme belegt keine Nutzerdatenwährung.

## Ausgangs- und Prüfcode

| Bezug | Geprüfter Stand |
|---|---|
| Ausgangscommit / erneut abgeglichenes `origin/main` | `e9aac2bfaadeb9133a6ed07e42d1dec39836b156`; `git fetch origin main` am 17.10.2026 erneut ohne neue Nachfolgeänderung |
| Softwareversion | 1.5.8; keine Versionsänderung dieses Schnitts |
| Aufgabenbranch | `work/realized-gross-readiness-20261017` |
| Implementierungs- und Testcommit | `8a3b9d662b6b32e384c6877447aedf4234af524d` |
| Folgende Dokumentation | Quellenvertrag, diese Qualifikation, FT-010-Nachtrag, Traceability und gezielte PB-017/PB-019-Fortschreibung; kein weiterer Rechencode |
| Fremde Änderungen | Frischer Checkout war sauber; keine fremden Änderungen überschrieben, verworfen oder gestasht |

Quellfingerprints des implementierten und getesteten Codes (SHA-256):

| Datei | SHA-256 |
|---|---|
| `backend/app/features/trade_position/domain/projector.py` | `5910f1af5bd089480a83a6cb2a4d0dd36ad908ad7ec0c22645c308612f5dc19a` |
| `tests/unit/backend/features/trade_position/test_projector_trace.py` | `e9dd841d5d9bcad28e8b216491a92dc275d91c96ce696bd8848c1485fb9cdcc6` |
| `tests/integration/backend/test_realized_gross_trace_postgres.py` | `4d8efefb2a54ba402ddf975a852e1954075c78a151e6d9151edd481c6c0d3660` |

#260, #261 und #263 sind im Ausgangsstand integriert. #249 ist im erneut geprüften
GitHub-Stand weiterhin ein offener Draft, Head
`1ad81344a66be9e70c772828081b2ff7ac13ef1c`; seine Basiswertformularänderung bleibt
getrennt und vor weiterer betrieblicher Ausweitung prioritär. Dieser Auftrag
verändert das Formular nicht und veröffentlicht oder merged keinen PR.
Die erneute Suche nach offenen PRs fand keine zusätzliche offene Berichtsstrecke
dieses Zuschnitts; vorhandene Datenversorgungs-, Formular- und Lernänderungen
bleiben getrennte Arbeiten.

## Bestehende und neue Verträge

Bereits entschieden: effektive Execution-Fakten und deren Korrekturen beim
FT-009/010-Owner; Average Cost und Brutto-PnL nach ADR-S10-004. Neue Fachentscheidungen
werden daraus nicht abgeleitet. Der ausführliche Readiness-Vertrag enthält die
noch zu bestätigenden Regeln für Währungsherkunft, Periodenzuordnung, Grundgesamtheit,
Teilsummen, Null-/Leerfälle und Anzeige.

Die einzige geänderte Produktionsdatei ist
`backend/app/features/trade_position/domain/projector.py`. Sie ergänzt
`PositionProjector.project_with_trace()`. `PositionProjectionTrace` enthält die
vollständige geordnete Execution-Folge genau einmal. Jede `SellProjectionTrace`
referenziert ihren SELL per Index und liefert geltenden Durchschnitt sowie
Menge/Kostenbasis vor und nach der Ausführung und den direkt errechneten Beitrag.
Der Präfix vor diesem Index erklärt die Kostenbasis einschließlich früherer SELLs.
Die immutable Execution selbst enthält Identität, Preis, Menge und ursprüngliche
Zeitpräzision. Bei vollständigem Verkauf wird der bisher intern auf null gesetzte
Kostenrest vor der Nullsetzung offengelegt, ohne das realisierte Ergebnis zu ändern.

`project()` bleibt der Consumer bestehender Commands. Der neue Trace hat zunächst
nur die neuen Testconsumer; er selektiert weder Wirksamkeit noch Storno, Periode
oder Währung. Insbesondere darf kein späterer Consumer ihn als bereits monetär
qualifizierte Berichtssumme behandeln.

Keine neue Persistenz, Migration, Route, DTO, Frontendberechnung, Kursabfrage,
Journal-/Review-/Evidence-Erzeugung oder Änderung der globalen Transaktionsisolation.
Keine bereits veröffentlichte Migration wurde verändert. Die M8-Baseline bleibt
erhalten; Product Backlog, FT-010 und Traceability verweisen auf denselben Schnitt.

## Unabhängige Erwartungswerte

Der Referenzfall verwendet genau die sechs Ausführungen des Auftrags; EUR ist
ausschließlich die ausdrücklich angenommene synthetische Einheit.

| SELL | Durchschnitt vor SELL | Direkter Beitrag | Restmenge / Restkosten |
|---|---:|---:|---:|
| 12.08.2026: 20 zu 2,50 | 2,00 | +10,00 | 80 / 160,00 |
| 02.09.2026: 30 zu 3,00 | 2,00 | +30,00 | 50 / 100,00 |
| 12.09.2026: 40 zu 2,50 | 3,00 | −20,00 | 60 / 180,00 |
| 03.10.2026: 60 zu 3,50 | 3,00 | +30,00 | 0 / 0,00 |

Die zwei ausdrücklich benannten September-SELL-IDs summieren sich auf **+10,00**,
die vollständige Folge auf **+50,00**. Vor dem Oktoberverkauf ist der Trade offen.
Nach tatsächlicher Ersetzung des zweiten September-SELL durch Preis 3,00 ist dessen
Beitrag **0,00**; September wird **+30,00**, die ganze Folge **+70,00**.
Die Auswahl über feste Fixture-IDs ist ein Testoracle, kein implementierter
Periodenfilter.

Der separate Dezimalbruchfall prüft exakte erwartete SELL-Deltas und das bisherige
Owner-Ergebnis `2.000000000000000000000000001`. Vor der bisherigen Vollverkaufs-
Nullsetzung bleiben `1E-27` Kosten. Es werden weder Floats, Toleranzen noch ein
geänderter Produktions-Decimal-Kontext eingeführt. Die Persistenzgleichheit des
Referenzfalls ist kein Beweis allgemeiner Gleichheit unquantisierter Domainwerte
mit SQL-Numeric-Werten; dessen Beträge sind an der Speichergrenze exakt darstellbar.

## Testnachweise

### Neue Unitfälle

[`test_projector_trace.py`](../../tests/unit/backend/features/trade_position/test_projector_trace.py)
enthält 17 Fälle einschließlich Parametrisierungen:

- Referenzbeiträge, offen gebliebener Septemberbestand und vollständige Herkunft;
- explizit vorgegebene wirksame Korrekturfolge und unveränderter alter Trace;
- BUY-only ohne SELL-Beiträge;
- unabhängige feste Decimal-Brucherwartungen einschließlich Vollverkaufsrest;
- gleiche Ausführungsinstants mit Sortierung nach Erfassungszeit und UUID;
- vier erhaltene Date-only-Quellen an den Berliner Sommerzeitgrenzen;
- unveränderte Eingabeliste und unveränderliche Trace-/Execution-Objekte;
- sechs unveränderte Fehlerpfade: leer, SELL vor BUY, Überverkauf,
  Wiedereröffnung sowie falsche Trade-/Produktidentität.

### Echter PostgreSQL-/Owner-API-Fall

[`test_realized_gross_trace_postgres.py`](../../tests/integration/backend/test_realized_gross_trace_postgres.py)
prüft `test_actual_captures_effective_correction_and_read_only_trace`.
Alle sechs wirtschaftlichen Ausführungen entstehen durch bestehende REST-Captures;
keine Execution wird per SQL als Fixture angelegt. Nach jedem Command werden die
unabhängig vorgegebenen Mengen, Kosten und kumulierten Ergebnisse geprüft.

Die tatsächlichen SQL-Repositories liefern danach volle und wirksame Historie.
Trace, direkte Deltas, Quellenpräfix und bestehender Position-GET ergeben den
Referenzfall. Ein echter Correction-POST ersetzt anschließend den September-SELL:
sechs wirksame und sieben historische Records, explizite Ersatzrelation,
unverändertes Original, neues Ergebnis und weiterhin unveränderter alter Trace.

Vor und nach beiden sequenziellen Read-Phasen werden alle Zeilen aus **17 explizit
geprüften Geschäftstabellen** verglichen. Darunter Executions, Positionen,
Management, Journal, Review, Evidence, Lessons, Post-Trade, Alerts, Notifications
und Monitoringzustände. Die geprüften Lernobjekttabellen bleiben im synthetischen
Fall leer. Das belegt keine gesonderte Abnahme bereits vorhandener STALE-/NOT_READY-
Inhalte und keine Aussage über nicht gelistete Tabellen. Reale synchrone und
asynchrone HTTPX-Transporte sind abgefangen und werden nicht aufgerufen.

Der Hilfsreader verwendet die vorhandenen Owner-Repositories einschließlich des
bekannten `FOR UPDATE` beim Trade-Commandreader. Er ist **kein neuer reiner
Berichtssnapshot**. Der Test ist sequenziell; Report-Nebenläufigkeit, Browser,
tatsächliche Währung und der vorgeschlagene Periodenfilter bleiben unqualifiziert.

### Zusätzlicher Vergleich mit dem unveränderten Ausgangscode

Ein separater deterministischer In-Memory-Lauf lädt den ursprünglichen Projector
bytegetreu mit `git show e9aac2bf:backend/app/features/trade_position/domain/projector.py`
als temporäres Modul. Seine vollständigen Positionsresultate werden gegen beide
neuen Zugriffe verglichen, auch jedes `Decimal.as_tuple()`, ohne Toleranz.
Der Generator verfolgt nur Mengen für gültige Folgen; er enthält keine zweite
Average-Cost-Rechnung und keine separat berechneten erwarteten SELL-Deltas.

Ergebnis: **100 Historien, 1.167 Executions und 565 SELL-Traces exakt gleich**;
60 offen, 40 geschlossen, 10 BUY-only, 90 mit Nachkauf nach Teilverkauf, 25 mit
Date-only und 75 mit präziser Zeit. Seed `2026101708`; Preise von `1E-10` bis
`99999999999999.9999999999`, alle innerhalb `Numeric(24,10)`. Bei 19 Vollverkäufen
zeigt der Trace den schon bestehenden von null verschiedenen Kostenrest vor dem
Reset; die projizierten Ergebnisse bleiben exakt gleich zum Ausgangsstand.
Das sind keine zusätzlichen 100 Repositorytests, kein Datenbank- oder Währungsbeleg.

Prüfcode: `/workspace/scratch/6e6cc87accad/verification/projector_differential_20261017.py`,
SHA-256 `d3bcec28a9fb29fb347589c1ca4afc23bd69d6ae7ed6d48f957e704723e35dc3`.
Protokoll: `projector-differential-20261017.json` im selben Verzeichnis.
Der Originalprojektor hat SHA-256
`a004376548081d27dde9b0d7333809ecdeee87f6758e06b419f25da6eeee77de`.
Geprüfter neuer Projektor entspricht dem oben fixierten Fingerprint; die
Domainmodelle sind unverändert. Dieser Prüfcode wird nicht als paralleler
Produktionspfad oder dauerhaft kopierter Projector ins Repository übernommen.

### Ausgeführte Läufe

| Prüfung | Ergebnis / Codebezug |
|---|---|
| Bestehender Projector plus neue Trace-Unitfälle | 24 bestanden; Vorbereitung mit demselben anschließend in `8a3b9d66` festgehaltenen Rechencode |
| Vollständiges Unitverzeichnis `features/trade_position` | 168 bestanden, 1 Warnung, 3,79 s; Vorprüfung des anschließend festgehaltenen Codes |
| Neuer PostgreSQL-/REST-Fall allein | 1 bestanden, 5,35 s; vor Commit, anschließend nur Black-Formatierung des SQL-Sortausdrucks |
| Exakter Differenzvergleich zum Projector aus `e9aac2bf` | 100 synthetische Historien bestanden, 0,14 s; vollständige Positionen und Decimal-Repräsentationen exakt, geprüfter Code `8a3b9d66` |
| `bash scripts/check-backend.sh` auf `8a3b9d66` | **Exit 0**: Ruff erfolgreich; Black 938 Dateien unverändert; mypy 535 Quelldateien erfolgreich; **2.754 Tests bestanden, 0 fehlgeschlagen, 0 übersprungen, 1 Warnung**. Coverage **87,10 %**, unveränderte Mindestgrenze 85 %. Pytest-Dauer 526,66 s. |
| `git diff --check` | Abschließend erfolgreich; auch keine Änderungen an Gates, Migrationen oder Versionsdateien. |

Die neuen 17 Unitfälle und der neue PostgreSQL-Fall sind im vollständigen
Backend-Gate enthalten; die gezielten Vorläufe werden nicht hinzuaddiert.
Die einzige Warnung stammt aus Starlettes TestClient: der Alias
`anyio.abc.BlockingPortal` ist deprecated. Sie wurde nicht ausgeblendet.
Das vollständige Laufprotokoll liegt unter
`/workspace/scratch/6e6cc87accad/verification/backend-gate-8a3b9d66.log`.
Die späteren Dokumentationsänderungen verändern keine getestete Produktions- oder
Testdatei; die drei oben genannten Fingerprints bleiben identisch.

Ein früherer PostgreSQL-Testlauf scheiterte an der Hilfsabfrage `ORDER BY id`,
weil `ft011_evidence` keine so benannte Spalte besitzt. Die Testabfrage sortiert
jetzt ganze Zeilen deterministisch mit `to_jsonb(snapshot_row)::text`. Keine
fachliche Assertion wurde entfernt oder gelockert; der vollständige gezielte
Wiederholungslauf bestand. Frühere lokale Testanläufe in der Standardsandbox
wurden wegen blockierter Sockets abgebrochen (Exit 130) und zählen nicht als
Erfolg. Die anschließend regulär außerhalb dieser Socketbeschränkung auf demselben
Wegwerfziel ausgeführten Läufe sind oben gesondert ausgewiesen.

## Identifizierte synthetische Testumgebung

- Python 3.12.14; Repo-Manifest 3.12. Die unveränderten `requirements-dev.txt`-
  Pins wurden in einer frischen lokalen `backend/.venv` installiert.
- PostgreSQL **17.11**, nativ aus dem unveränderten offiziellen Quellarchiv gebaut;
  keine SQLite-/Fake-Transaktionssimulation und kein Docker-Nachweis.
  Quelle: [offizielles PostgreSQL-17.11-Quellarchiv](https://ftp.postgresql.org/pub/source/v17.11/postgresql-17.11.tar.bz2);
  gegen die offizielle SHA-256 geprüft:
  `dd27f2b3c59e73ed14aa3324901242bf69a032a6347805f274e6260322d42979`.
- Frischer ausschließlich synthetischer Cluster auf `127.0.0.1:35432`, Rolle
  `tw_test_owner`, explizite Basisdatenbank `trading_workspace_test`.
  Beide Anwendungs-/Test-URLs zeigen auf diesen identifizierten Cluster.
  Clusterkennung `7697670067434780796`; Lauf unter UID 65534; Datenchecksummen,
  `fsync`, `synchronous_commit` und `full_page_writes` eingeschaltet.
- Lokale Build-/Runtime-Dateien liegen ausschließlich im neu angelegten
  `/workspace/scratch/6e6cc87accad/pg17-local-20261017/`.
  Die bestehende Fixture erzeugt/migriert und entfernt ausschließlich selbst
  generierte `tw_currency_ref_test_<uuid>`-Datenbanken. Kein Nutzer-Composeprojekt,
  Port, Volume, Bind-Mount, `.env` oder Zustimmungsbestand wurde verwendet/verändert.
- Alle Provider, Refresh, Issuer-Renderer, Positionsmonitoring und Telegram sind
  für die Läufe deaktiviert. Keine Anwendungsscheduler oder Benachrichtigungsdienste
  wurden für den Teststack gestartet. Der neue Test blockiert externe HTTPX-
  Transports zusätzlich explizit; lokale ASGI-Requests und PostgreSQL sind zulässig.
- Der native Cluster läuft in einer ausschließlich für diesen Test angelegten
  Chroot-Umgebung. Mangels `mknod` dient dort eine lokale reguläre Datei als
  Bootstrap-Umleitungsziel `/dev/null`; Zufall stammt nicht aus einer Ersatzdatei.
  OpenSSL/UUID-Erzeugung wurde geprüft. Das schränkt die Gleichheit mit dem
  üblichen Docker-Laufzeitbild ein, nicht den Einsatz echter PostgreSQL-Transaktionen.

Die unveränderte Migrationskette wurde mit `alembic upgrade head` bis
`20261014_0046` ausgeführt. Nach dem vollständigen Gate am 17.10.2026 um
16:29:20 UTC geprüft: SQL-Schema und `alembic heads` enthalten ausschließlich
`20261014_0046`; es sind keine generierten `tw_currency_ref_test_*`-Datenbanken
übrig. Clusterkennung und Port stimmen weiterhin mit der freigegebenen
Wegwerfinstanz überein. Anschließend hat `pg_ctl ... -m fast -w stop` ausschließlich
diesen Cluster erfolgreich beendet (`server stopped`, Exit 0). Datenverzeichnisse
oder Nutzer-Volumes wurden nicht gelöscht. Beobachtung und Stoppprotokoll liegen
in `verification/postgres-final-state.json` und `verification/postgres-stop.log`
im oben genannten übergeordneten Arbeitsverzeichnis.

### Reproduzierbare Prüfeinstiege

Vor einem Lauf muss ein eigener, sicher identifizierter PostgreSQL-Testserver
bereitstehen. Die folgenden URLs gelten ausschließlich für die oben dokumentierte
lokale Wegwerfinstanz, nicht für eine Nutzerinstallation. Aus dem Repositoryroot:

```bash
export TRADING_WORKSPACE_ENVIRONMENT=test
export TRADING_WORKSPACE_DATABASE_URL=postgresql+asyncpg://tw_test_owner@127.0.0.1:35432/trading_workspace_test
export TRADING_WORKSPACE_TEST_DATABASE_URL="$TRADING_WORKSPACE_DATABASE_URL"
export TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY=
export TRADING_WORKSPACE_MARKET_DATA__VONTOBEL_MARKETS__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__JPMORGAN__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__MORGANSTANLEY__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__GETTEX_DELAYED__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED=false
export TRADING_WORKSPACE_MARKET_DATA__REFRESH__ISSUER_RENDERER_ENABLED=false
export TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=false
export TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false

PYTHONPATH=backend:. backend/.venv/bin/python -m pytest \
  -c backend/pyproject.toml \
  tests/unit/backend/features/trade_position \
  tests/integration/backend/test_realized_gross_trace_postgres.py -q --tb=short

(cd backend && .venv/bin/python -m alembic upgrade head)
bash scripts/check-backend.sh
git diff --check
```

Die Befehle dokumentieren die tatsächlich verwendeten Einstiege; ein erneuter
Aufruf benötigt erneut eine Wegwerfumgebung. Dieser Abschnitt allein ist kein
Testnachweis. Die ausgeführten Ergebnisse stehen in der Tabelle darüber.

## Kriterien 1–10 des Gesamtauftrags

| Kriterium | Nachgewiesener Teilschnitt und verbleibende Grenze |
|---|---|
| 1: Referenz und Korrektur | Direkte Owner-Deltas, offene Septemberposition, SQL-Wirksamkeit und bestehende kumulierte API-Ausgabe belegt. Neue Perioden-API und UI fehlen; daher Gesamtkriterium noch nicht erfüllt. |
| 2: Teilverkauf, BUY, Storno, externer Ursprung | Offener Teilverkauf/BUY-only und bestehende Owner-Invarianten qualifiziert; tatsächlicher EXTERNAL-Capture im PG-Test. Berichtspopulation einschließlich Storno-/Beobachtungsausschlüssen ist als noch zu bestätigender Vertrag beschrieben. |
| 3: Ausführungswährung | Quellenlücke entlang aller Capturepfade belegt; minimale additive Bestätigung vorgeschlagen. Keine qualifizierte Geldaggregation und kein Währungstest für reale Bestände. |
| 4: Leer, null, unbekannt, teilweise | Eindeutiger V1-Zustands-/Zählervertrag vorgeschlagen; noch keine implementierte Berichtsausgabe. |
| 5: Zeitpräzision und Periodenränder | Originale Date-only-/Zeitzonenfelder, verspätete Erfassungszeit und vier DST-Anker im Trace erhalten. Perioden-/Monats-/Jahres-/Fremdzonenzuordnung ist beschrieben, nicht als Reader implementiert oder abgenommen. |
| 6: Gemeinsame Berechnungsbasis | Reiner immutable Trace für eine bereitgestellte vollständige History; Herkunft und Positionsprojektion passen zusammen. Bericht-Summary, Pagination, Quellenbasiswechsel und UI-Rennen bleiben eigener späterer Nachweis. |
| 7: Parallel committene Korrektur | Echter sequenzieller PG-Korrekturfall geliefert. Kein neuer Reportreader, deshalb kein behaupteter Snapshot-/Nebenläufigkeitsnachweis; eigener kurzer RR-Read und konkrete Zweiverbindungstests vorgeschlagen. |
| 8: Lernunabhängigkeit und Nebenwirkungen | Reiner Domain-Trace; tatsächliche Owner-/Positionsreads ohne Lernobjekte, geprüfte 17 Tabellen unverändert, HTTPX-Transports unbenutzt. Neuer Report-GET und vorhandene STALE-/NOT_READY-Lernbestände sind nicht gesondert qualifiziert. |
| 9: Backend-Owner und Browserweg | Eine Backend-Rechenschleife; echte REST-Captures/Korrektur und PostgreSQL nachgewiesen. Keine Bericht-UI und kein Browser-E2E. |
| 10: Gates, Verträge, Backlog, Gesamtumfang | Unveränderter vollständiger Backend-Gate erfolgreich, 2.754 Tests/87,10 % Coverage. Betroffene Verträge und zentrales Backlog aktualisiert, M8-Baseline erhalten. Keine Bereich-7/8-, Fach-, Release- oder PC-Gesamtabnahme. |

## Nicht ausgeführte Prüfungen und Betriebsfolgen

`bash scripts/check-frontend.sh` wurde nicht ausgeführt: Keine Frontend-, API- oder
DTO-Änderung und kein neuer Browserconsumer in diesem Slice. Der Host bietet
Node 24.19.0 / npm 11.9.0 statt der Repositoryvorgaben 22.16.0 / 10.9.2; das wird
nicht als qualifizierter Frontendlauf ausgegeben. Ein zukünftiger vertikaler
Bericht benötigt seinen betroffenen vollständigen Frontend-Gate.

`bash scripts/run-e2e.sh` wurde nicht ausgeführt: Docker ist in dieser Umgebung
nicht verfügbar; das Skript setzt einen eigenen Docker-Teststack voraus und kann
dessen Volumes entfernen. Es wird kein fremder Stack als Ersatz verwendet.
Die native Owner-/PostgreSQL-Integration ist kein Browser-E2E und kein Nachweis
des im Skript vorgesehenen Dockerbilds. Der Browserweg und die konkurrierenden
Report-Korrekturtests bleiben Abnahmebedingungen des erst nach DoR freigegebenen
vertikalen Schnitts.

Keine Migration oder Datenbereinigung für dieses Arbeitspaket, keine EUR-
Rückbefüllung, kein Providerzugriff, kein Modellzustandswechsel, kein Tag,
Deployment oder beobachteter PC-Betrieb. Die additive Währungsrelation aus dem
Entscheidungsvorschlag wäre ein eigener kompatibler Erfassungs-/Migrationsschnitt
beim selben Owner und ist hier ausdrücklich nicht umgesetzt.

## Genau nächster sinnvoller Schritt

**Fachliche Entscheidung des konkret beschriebenen Execution-Währungsbestätigungs-
und V1-Periodenvertrags** im [Readiness-Dokument](PERIOD_REALIZED_GROSS_READINESS.md).
Diese Freigabe ist ausdrücklich offen, weil der Auftrag seinen vorgeschlagenen
Kennzahlenvertrag nicht selbst als Fachfreigabe erklärt. Erst danach darf die
passende additive Owner-Erfassung qualifiziert und auf deren belegten Fakten die
vertikale Berichtsstrecke gebaut werden. Unabhängige Owner-Arithmetik ist geliefert;
eine vollständige Trading-/Depotperformance ist damit nicht behauptet.
