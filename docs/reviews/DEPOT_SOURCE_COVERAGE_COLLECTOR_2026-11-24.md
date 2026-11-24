# Gezielte Quellenkandidaten-Diagnose für bisher ungebundene Positionen

## Zweck und Nachweisgrenze

Der [enge P02-Readback](P02_SOURCE_GAP_READBACK_2026-11-24.md) ist ausgewertet.
Die übrigen am 22.11. ungebundenen Positionen wurden damit nicht neu gelesen.
Der nächste Teil desselben Versorgungsauftrags benötigt ihre heutigen
Quellenbindungen und die zuvor nicht exportierten Auswahlkandidaten.
Arbeitsstatus, weitere Datenversorgung und Abnahme stehen ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

Der bestehende [Standalone-Collector](../../scripts/collect-depot-data-supply.py)
erhält dafür `--source-coverage-from ARCHIVE.tar.gz`. Er verwendet das
ursprüngliche vollständige Diagnosearchiv als Identitätsreferenz. Der
engere P02-Export ist kein gültiges Referenzarchiv dieses Modus. Ein neues
App-Release oder ein installierter PR-370-Resolverfix ist nicht erforderlich.

Geprüfter Main und zuletzt tatsächlich nachgewiesener PC-Stand sind
`9a5e59dac3bb219cbc40641e62e75871eb2ed131` / v1.5.54. Die PC-Bestätigung
stammt weiterhin aus dem P02-Paket vom **24.11., 18:23:08–18:23:10 Uhr MEZ**;
dieser Entwicklungsschnitt ist kein neuer Betriebsread. Die vier regulären
CI-Läufe des vorherigen Arbeitsstands `40a9811476dbecfeaec2577dde9f8812caa16bf4`
sind inzwischen erfolgreich:
[Backend](https://github.com/burckhju/trading-workspace/actions/runs/45452822985),
[Frontend](https://github.com/burckhju/trading-workspace/actions/runs/45452823137),
[End-to-End](https://github.com/burckhju/trading-workspace/actions/runs/45452823034)
und [Versionsprüfung](https://github.com/burckhju/trading-workspace/actions/runs/45452823001).
Diese Läufe qualifizieren nicht automatisch den anschließend ergänzten Code.

## 1. Archivgebundene Auswahl

Der Host liest fünf begrenzte reguläre JSON-Dateien aus dem vollständigen
Archiv im Speicher; er entpackt keine Pfade. Die vorhandenen Größen-,
Tar-, JSON-, Installations- und Transportprüfungen bleiben erhalten.
Vor-/Nach-Inventur, private Positionsprojektionen und Archivlabels müssen
zusammenpassen. Der Workspace wird aus beiden archivierten Refreshreads
gebunden. Heutige Listenreihenfolge und Produktnamen sind keine Auswahlbasis.

Erfasst werden ausschließlich damals nicht ausgewählte Positionen:
fehlende Auswahl, `NO_VERIFIED_QUOTE_SOURCE` oder `AMBIGUOUS_SOURCE`.
Null Kandidaten und mehr als zwanzig Kandidaten werden vor dem PC-Read
begründet abgelehnt. Ein fehlendes damaliges Assessment, unbekannte WKN
oder fehlende Originalkursroute dürfen die Diagnose einer ungebundenen
Position nicht verhindern. Unbekannte historische Identitätsfelder bleiben
unbekannt; der heutige Bestand ergänzt sie nicht rückwirkend.

**Hostseitig am unveränderten gelieferten Originalarchiv geprüft:**
Die neue Referenzfunktion wählt genau **P01, P03 und P04** und lässt die
damals ausgewählte P02-Route aus. Archiv-SHA256:
`ea4ee60cbd4d212ac97cf5b140f168d1f959bd2aac48cf344bb4b26839ce73ab`.
Dies ist eine tatsächliche Archivprüfung, keine Ausführung auf der PC-Datenbank.
Private Kennungen und Kurs-/Einstandswerte werden hier nicht wiedergegeben.

## 2. Benötigte Fakten und bestehende Owner

| Fehlende Diagnoseevidenz | Bestehender lesender Zugriff | Aussagegrenze |
| --- | --- | --- |
| Heutige offene Positions-/Quellenbindung | `positions/quote-coverage` vor/nach | Fehlender Treffer bedeutet nicht automatisch geschlossen. |
| Produktidentität und Emittent, vorhandene Produktrouten, Mappingzustand, Quotes und Resolverkonfiguration | `warrants/quote-coverage` vor/nach | Enthält auch ungeeignete Routen. Der Emittent bleibt zur Quellenzuordnung im privaten Paket erhalten. `configured_sources` ist keine vollständige heutige Providerfreigabe. |
| Damalige und aktuelle gespeicherte Auswahlkandidaten | Gebundener SELECT auf `PositionQuoteSourceSelectionModel.evidence` | `verified_candidates`, `allowed_candidates`, `eligible_candidates` gelten jeweils zu ihrer gespeicherten Auswahlzeit. |
| Offen, geschlossen, storniert oder nicht mehr zuordenbar | `SqlAlchemyReadOnlyTradeRepository.get` und `SqlAlchemyPositionRepository.get_for_trade` | Archivierte Trade-/Positions-/Produktbindung prüfen; Storno aus dem Trade, nicht aus dem Defaultwert der Positionsprojektion. |
| Tatsächlich gespeicherte alte und aktuelle Bewertung | Gebundene archivierte Assessment-ID und `latest_indicative_assessment` | Familien-Kettenkopf V1/V2 verwenden; keine Neuberechnung, kein bloßes Sortieren nach Zeit. |
| Aktuelle Produkteignung und Beschaffungszustand | `ProductReviewEvidenceReader.current_for_review` und `acquisition_state` | Aktuelle gespeicherte Product-Evidenz getrennt von damaligen Assessmentinputs ausgeben. |
| KID-Parserfassung und Originalrevision | `latest_document` beim Product-Owner | Revisions-, Zeit-, Hash- und begrenzte Faktenmetadaten; keine Originaldokumentbytes. |

Die [Coverage-API](../../backend/app/features/market_data/api/quote_coverage.py)
existiert bereits. Der
[Coverage-Service](../../backend/app/features/market_data/service/quote_coverage.py)
übernimmt Discoverygründe nur aus aktuellen Frankfurt-/Vontobel-Mappingjobs.
Leere Runtimegründe sind kein Beweis für einen früheren Discoveryfehler.
Die [Auswahl-Evidenz](../../backend/app/features/market_data/service/position_quote_source.py)
enthält die beim Entscheid vorhandenen verifizierten, erlaubten und geeigneten
Kandidaten; ihre historische Providerliste wird nicht als heutige Zustimmung
ausgegeben. Die bestehenden Quellengrenzen werden nicht neu interpretiert.

## 3. Passive Durchführung und Zeitbindung

Der Helfer validiert dieselbe bestehende Installation vor und nach dem Read.
Der Host verwendet ausschließlich seine Standardbibliothek. Im bereits
laufenden Backend werden die vorhandenen GET-Verträge und Owner verwendet.
Die Referenz gelangt über JSON-stdin hinein; private Kennungen stehen nicht
in der Prozesskommandozeile.

Der ergänzende Datenbankread bestätigt tatsächlich
`REPEATABLE READ READ ONLY`, begrenzt Verbindungs-/Statement-/Lockwartezeiten
und verwendet `autoflush=False`. Sessionrollback, explizites SQL-`ROLLBACK`
und Enginefreigabe gelten auch bei Fehlern. Keine Auswahl-/Mappingcommands,
kein Providerabruf, kein Refresh, kein Import und kein Regellauf gehören
zum Collector. Insbesondere werden weder die sperrende Methode
`PositionQuoteSourceSelectionRepository.active_for_position()` noch
`ProductReviewReadiness.prepare_for_review()` aufgerufen.

Die GETs und der DB-Snapshot besitzen getrennte Lesezeiten;
`global_atomic_snapshot=false` bleibt erhalten. Vor-/Nach-Abgleich betrifft
strukturelle Zielbindungen. Reguläre neue Quotes oder Refreshzeiten werden
nicht als Identitätswechsel behandelt. Eine inzwischen vorhandene Auswahl
ist ein neuer beobachteter Zustand, keine stillschweigende Änderung der
Archividentität. Bei fremder oder nicht mehr eindeutiger Bindung werden
keine Ersatzposition und keine fremden Produktbelege gelesen.

Das private Paket enthält Installationsbelege, Schemaread,
`source-coverage-private.json` und Zusammenfassung. Verzeichnisrechte `0700`,
Datei-/Archivrechte `0600` und Fehlerpakete bleiben erhalten. Die Erfolgsmeldung
`COMPLETE_PASSIVE_SOURCE_COVERAGE_READ_NOT_RULE_QUALIFICATION` bezeichnet
vollständigen gebundenen Lesetransport, keine neue Bidversorgung oder
V2-/B58-Regelabnahme.

## 4. Qualifikation und nächster tatsächlicher Beleg

Die neue synthetische Prüfsuite steht unter
[test_collect_depot_source_coverage.py](../../tests/unit/backend/test_collect_depot_source_coverage.py).
**56 Tests bestanden**, keine übersprungenen Tests und keine ausgegebenen
Warnungen: 22 neue Quellenkandidatenfälle, 19 bestehende Standardfälle und
15 bestehende P02-Fälle. Ausgeführt mit Python 3.12.14 und den vorhandenen
Backend-Abhängigkeiten; die Tests verwenden die tatsächlich eingebetteten
Payloads, echte Coverage-DTOs und Owner-Signaturen mit abgefangenen
HTTP-/DB-/Docker-Grenzen. Ein positiver Dokumentfall verwendet das echte
`ProductReviewDocumentModel` und `ProductReviewEvidence` mit Revision,
Hash, Zeiten und Fakten. Auch der Emittent erreicht den privaten Zielbefund.

Kernaufruf aus der Repositorywurzel mit der eingerichteten Backend-Pythonumgebung;
`TMPDIR` war auf ein beschreibbares privates Testverzeichnis gesetzt:

```bash
PYTHONPATH=backend:. python -B -m unittest \
  tests.unit.backend.test_collect_depot_source_coverage \
  tests.unit.backend.test_collect_depot_data_supply \
  tests.unit.backend.test_collect_depot_source_gap -v
```

Der abschließende Lauf nach Formatierung meldete
`Ran 56 tests in 1.307s — OK`. `unittest` benötigt kein Konfigurationsflag;
Black und Ruff für die Testdatei verwenden `backend/pyproject.toml`.

Die Gegenfälle prüfen unter anderem fremde oder geänderte Bindungen,
fehlend/geschlossen/storniert, inzwischen ausgewählte Routen, aktuelle
statt historischer Mappingversion, reguläre Quoteänderungen,
unvollständige `PRESENT`-Produkt-/Dokument-/Bewertungsbelege und falsche
Vollständigkeitsflags. Host und Payload prüfen die Struktur selbst;
ein bloßes `bindings_unchanged=true` genügt nicht. Rollback und Dispose,
private Dateirechte, Fehlererhalt und die Entfernung synthetischer Secrets
sind gezielt geprüft. Alle drei bisherigen Payloads behalten ihre
eingefrorenen SHA256-Werte; Standardmodus und enger P02-Modus bleiben
gesondert geschützt.

Black 26.1.0 und Ruff 0.15.1 sind erfolgreich. Die Hostdatei ist zusätzlich
mit Python-3.10-Syntax und Ruff-Zielversion `py310` geprüft; der im
installierten Backend ausgeführte Payload nutzt dessen Python 3.12.
Die ausgelieferte Kopie ist bytegleich zum Repositoryskript, und ihre
ausgeführte CLI-Hilfe führt beide gezielten Modi auf.

| Bindung | Wert |
| --- | --- |
| Ausgelieferter Dateiname | `collect-depot-source-coverage-20261124.py` |
| Dateigröße | 145.803 Bytes |
| SHA256 der vollständigen Datei | `229c966063ca245f40fe492b14438c4c132fcb5d3fe75458ef20c0efbdd2688e` |
| Neuer Backend-Payload | 40.229 Bytes; SHA256 `a1dc7c644ec99a0c3b5715fd220f996ac4c64a0a1b590cd2a6a9acd77d693721` |

Der neue öffentliche Text wurde gegen 720 private Kennungen und
Instrumentbezüge aus den beiden vorhandenen Paketen geprüft: keine
Treffer. Historischer Roadmapblob unverändert. Die technischen Prüfungen
verwenden keine Live-Datenbank, keinen Dockerdaemon, keinen Provider und
keinen PC-Zugang; ein realer Kandidatenexport ist damit noch nicht belegt.

**CI-Abgleich vom 24.11., nach Veröffentlichung:** Der
[Backend-Job auf cdfea27a](https://github.com/burckhju/trading-workspace/actions/runs/45470108506/job/138715450864)
scheiterte um 20:26:31 Uhr MEZ an genau zwei Ruff-`I001`-Meldungen in den
Importblöcken des neuen Tests. Die nachfolgenden Test-/Migrationsschritte
wurden in diesem Lauf nicht ausgeführt. Der vorherige lokale Ruff-Aufruf
aus der Repositorywurzel mit explizitem Konfigurationspfad klassifizierte
die Imports anders als der tatsächliche CI-Aufruf aus `backend/`.
Die externen `pydantic`-/`sqlalchemy`-Imports stehen jetzt vor `app.*`.
Keine Assertion, kein Gate, kein Collector-/Anwendungscode wurde geändert;
der ausgelieferte Dateihash bleibt gleich. Der vollständige Ruff-Aufruf
aus dem tatsächlichen CI-Arbeitsverzeichnis sowie Black sind erfolgreich.
Der gezielte pytest-Lauf mit `backend/pyproject.toml` meldet
**56 passed, 87 subtests passed in 1.57s**, ohne Skips oder Warnungen.
Frontend, End-to-End und Version auf cdfea27a sind erfolgreich; der
korrigierte Arbeitsstand benötigt seinen eigenen regulären CI-Nachweis.

Hier besteht kein interaktiver Zugang zum privaten PC. Deshalb ist der
kleinste noch nötige tatsächliche Beleg genau dieser einmalige gebundene
Export auf der bestehenden Installation. Erst daraus folgt eine begründete
Korrektur an einer weiteren Position oder eine konkrete fehlende Quelle,
Zugangsentscheidung beziehungsweise Produktinformation. Der
[Betriebsaufruf](../technical/ISSUER_MONITORING_OPERATIONS.md#gezielter-quellenkandidatenread)
und die Abnahmekriterien im Backlog gehören zu demselben Auftrag.
