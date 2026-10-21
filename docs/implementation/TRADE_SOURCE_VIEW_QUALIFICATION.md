# Lesende Einzeltrade-Quellenansicht — Entwicklungsnachweis

Stand: 21.10.2026. **Lokaler, teilweise geprüfter Entwicklungsschnitt; keine technische Merge-Reife.**
Der Product Backlog bleibt die einzige maßgebliche Aufgabenstatusquelle. Diese Datei
beschreibt den Quellenvertrag und den konkreten Nachweis, keine neue FT-/PB-ID.

## Ausgangslage und Sicherungsgrenze

Erneut gelesener Main: `5e9ede2dc29f52eaff601d30614df6bc9c25c426` / v1.5.11.
Der Remote-Arbeitsbranch `feature/trade-result-source-view` steht auf
`d0c6d34ae876f1a550f37acafd016766220517ee`, Tree
`b3682321a251bf73f0de47f7ccc42ba60721c99a`. Dieser Basisstand enthält gegenüber Main
nur den bereits vorhandenen Recovery-Transportworkflow, nicht die Anwendungserweiterung.
Die Suche nach einem PR dieses Branches war am 21.10.2026 leer.

Die vorherige Chat-Aussage über eine dauerhaft gesicherte Implementierung konnte aus
den verfügbaren Anhängen nicht bestätigt werden. Verfügbar waren Basis-Git-Bundle und
Offline-Toolchain. Deshalb wurde die Implementierung aus vorhandenen Änderungstexten
neu aufgebaut, gegen den Basiscode geprüft und neu getestet. Das ist **keine belegte
bitidentische Wiederherstellung** des früher genannten lokalen Implementierungscommits.
Der neue lokale Branch heißt `recovery/trade-result-source-view-20261021`.
Der finale Commit/Tree und die Datei-Hashes stehen im mitgelieferten `DELIVERY-STATUS.json`;
das unabhängig prüfbare Bundle und der Patch sind Bestandteil desselben Übergabepakets.

[Abschlussstatistik #270](https://github.com/burckhju/trading-workspace/pull/270)
ist erneut als offen, Draft und ungemergt gelesen worden; Head
`de413843a814ac6a1016f474f3e5366cd81ea96a`. Die dort dokumentierte Qualifikation
wird nicht auf diesen Schnitt übertragen. Der Einzeltrade-Einstieg ist unabhängig;
Übergang aus Abschlussliste, Filterrückkehr und qualifiziertes Trade-Gesamtergebnis
bleiben offen. Kein Rohpositions-PnL und kein Geldwert aus URL-Parametern ersetzt sie.

## Wiederverwendete Quellen und Grenzen

| Abschnitt | Owner / konkreter Leser | Bindung und Zeitbezug | Consumer / Restgrenze |
|---|---|---|---|
| Trade, Durchführung, Währung | Execution-Owner; bestehende Execution-/Management-/Position-Repositories, `compose_trade_timeline`, `resolve_execution_currencies` | Workspace und eigene Trade-ID; ursprüngliche und ersetzende IDs; Date-only bleibt ohne Uhrzeit; Erfassung getrennt | `TradeSourcesView`, reiner Quellenread; keine neue Geldrechnung |
| Originalplan | `SqlAlchemyWorkspaceSelectionResolver`, `TradePlanQueryService.get_version` | Referenzierte Plan-/Version-/Evaluation-/Approval-Herkunft, nicht latest; fremde Relation ist Fehler | P1 und gespeicherte Freigabe; EXTERNAL ohne Herkunft bleibt ohne Plan |
| Exit-Review | `PostTradeQueryService`, `ExitReviewService.inspect_version_currentness` | Exakte angeforderte Version oder ausdrücklich heutige Auswahl; gespeicherter Status und heutige Prüfung separat | Bestehende vier Kategorien und Begründung; nur Exit-Bewertung, kein Tradequalitätsscore |
| Journal | `SqlAlchemyJournalRepository`; vorhandener Review-Inspektor | Konkrete Version, DRAFT-Bearbeitungsrevision, Review-Quelle; keine automatische Finalisierung | Historie und leeres Final getrennt von fehlendem Journal und Lesefehler |
| Evidence / Lessons | `SqlAlchemyFt011MaterializationRepository`, `SqlAlchemyLessonEvidenceReadRepository`, vorhandene Journal-Evidence-Verknüpfung | Trade-/Workspace-Relation, konkrete Evidence- und Lessonversionen, alle gespeicherten Relationsarten | Vorhandene exakte Lesson-Historienroute; unbekannte Altprovenienz bleibt unbekannt |
| Finanzielles Gesamtergebnis | Separater qualifizierter Abschlussreport aus #270 | Hier noch nicht integriert | Sichtbarer Integrationshinweis statt unqualifizierter Zahl |

Heutiger Produktname ist Orientierung, keine rekonstruierte historische Stammdatenversion.
Freitext ist Benutzerreflexion und wird als Text dargestellt, nicht als Roh-HTML ausgeführt.
Planmarken und Optionsscheinpreise erhalten keine automatisch erfundene Vergleichsachse.
Gewinn/Verlust, Dokumentationsstatus und gespeicherte Bewertung bleiben verschiedene Dinge.

## Lese- und Navigationsvertrag

Fünf zusätzliche reine GETs unter `/api/v1/trade-position/trades/{trade_id}/sources`:
Basis, `/plan`, `/reviews`, `/journal`, `/evidence`. Review und Journal unterstützen
jeweils genau einen optionalen `version_id`-Parameter. Doppelte/ungültige Parameter
liefern 422; unbekannte oder unpassende historische Versionen 404 ohne latest-Fallback.
Kernidentität wird vor Kindquellen gelesen. DB-Lesefehler werden bereinigt als 503
`SOURCE_READ_UNAVAILABLE`, Relationskonflikte als 409 und Quellenlimits als 413 dargestellt.

Jeder Abschnitt erhält eine eigene kurze `REPEATABLE READ READ ONLY`-Transaktion,
10 Sekunden Statementlimit und explizite Beginn-/Endzeit. Das ist **keine globale
Snapshot-Garantie für mehrere Abschnitte**. Bestehende Command-Repositories behalten ihre
Schreibsperren; ein eigener `TradeReader`/lockfreier Adapter dient nur den neuen Reads.
Alle Daten werden vor Transaktionsende materialisiert. Grenzen: 2.000 Fakten,
100 Versionen/Quellenwurzeln, 1.000 Links gemäß konkreten Readerabfragen; Limitüberschreitung
ist sichtbar und wird nicht als vollständige abgeschnittene Historie ausgegeben.
Keine neue Persistenz, Migration, Currentness-Revalidierung oder Providerabfrage.

Die bestehende Tradeverwaltung hat den Modus `view=sources`. Der Einstieg öffnet
explizit einen neuen Tab (`noopener noreferrer`), damit bestehende Formulare nicht
für einen Quellenread ungemountet und ungespeicherte Eingaben nicht verworfen werden.
Der Lesemodus mountet keine Eingabe-/Command-Komponenten. Trade-ID und genaue
Review-/Journal-Pins stehen in der URL; eine Besuchsidentität einschließlich Router-Key
trennt auch A→B→A und Versionswechsel. Jeder Abschnitt besitzt eigenen Abbruch-/Requestschutz
und einen bewusst ausgelösten Wiederholungsweg. Rückkehr ist ein festes internes
Tradeziel, kein frei übernommenes `returnTo`. Abschlusslisten-Kontext ist noch nicht integriert.

## Tatsächlich ausgeführte lokale Prüfungen

Werkzeuge: Python 3.12.15, Node 22.16.0, npm 10.9.2; versionierte Abhängigkeiten/Lockdateien,
Gates, Retries und Schutzvariablen wurden nicht gelockert. Offline-Toolchain: alle 51
vorhandenen Nutzdateien stimmten mit ihren SHA-256-Einträgen überein. Das gelieferte
Manifest nennt zusätzlich eine nicht vorhandene temporäre `SHA256SUMS.tmp`; daraus
wird kein vollständig fehlerfreier Archivmanifest-Nachweis gemacht.

| Prüfung | Ergebnis / Grenze | Log im Übergabepaket |
|---|---|---|
| Neue API-/Reader-Unitfälle | 33 bestanden; Mocks/SQL-Kompilation, kein nativer DB-Nachweis | `source-api-tests.log` |
| Neue Oberflächenfälle | 22 bestanden | `source-ui-tests.log` |
| Betroffene Backend-Unitbereiche TradePosition/PostTrade/Learning/Performance | 680 bestanden, kein Skip; eine vorhandene Starlette-/AnyIO-DeprecationWarning | `backend-regression.log` |
| Vollständiges unverändertes Frontend-Gate | Typecheck, ESLint, Prettier, 598 Tests / 112 Dateien, Coverage und Build bestanden | `frontend-gate.log` |
| Frontend-Coverage | Statements/Zeilen 92,95 %, Branches 84,64 %, Funktionen 85,49 %; unveränderte Grenzen | `frontend-gate.log` |
| Backend-Statik | Ruff/Black über Anwendung und beide Backendtestsammlungen; striktes mypy über 554 App-Dateien | `backend-static-final.log` |
| Neue native PostgreSQL-Fälle | **Fünf nur gesammelt, nicht ausgeführt**; bestehende geschützte Wegwerf-DB- und externe HTTP-Sperren wiederverwendet | `native-collection.log` |
| Vollständiges Backend-Gate mit Integration/Coverage | Nicht ausgeführt; keine native PostgreSQL-Testumgebung | Kein grüner Vollgate-Nachweis |
| Browser→API→PostgreSQL / Desktop-/Mobilansicht | Nicht ausgeführt; kein neuer tatsächlicher Browser- oder Screenshotnachweis | Offen |

Zwei zuvor gestartete Backend-Teilbereichsläufe wurden von der Ausführungsumgebung vor
Abschluss beendet. Ihre Logs bleiben als `backend-regression-interrupted*.log` erhalten;
sie zählen nicht als erfolgreiche Läufe. Der anschließend vollständig abgeschlossene
680-Testlauf ist separat dokumentiert. Vite meldet informativ ein großes Build-Chunk;
kein Grenzwert und keine Assertion wurde dafür verändert. Der erste abschließende
Statiklauf beanstandete in der neuen nativen Testdatei eine überlange Zeile und eine
unbenutzte Variable. Beide wurden ohne Änderung von Erwartungen/Schutzregeln korrigiert;
der rote Lauf bleibt als `backend-static-initial-failure.log` erhalten.

Die nativen Fälle in `test_trade_source_view_postgres.py` bereiten echte Ownerdaten,
P1/P2, Review/Journal/Evidence/Lesson-Historie, Korrektur und kontrollierte konkurrierende
Writer vor. +50/+70 und September +10/+30 werden unabhängig als Decimal-Sollwerte gegen
den **bestehenden SELL-Report** geprüft; das ist nicht die hier fehlende neue Gesamtergebnis-UI.
Diese Tests wurden nur gesammelt. Ihre Assertions sind kein behaupteter Laufnachweis.

## Akzeptanz A1–A16 — kein pauschales Grün

Abkürzungen: U = `tests/unit/backend/features/trade_position/test_source_view.py`;
UI = `frontend/src/features/trade/components/TradeSourcesView.test.tsx`;
PG = `tests/integration/backend/test_trade_source_view_postgres.py` (nur gesammelt).

| ID | Konkreter Stand und Nachweis | Offene Grenze |
|---|---|---|
| A1 | Bestehender Trade-Einstieg und festes internes Rückziel implementiert; UI prüft fremdes/nested returnTo | Abschlusslisten-Filter/Seite/Sortierung und Browserweg offen |
| A2 | Keine erfundene Geldsumme; U prüft Decimal-/Datumsserialisierung ohne Total; PG bereitet 50/70 und 10/30 vor | Qualifizierte vollständige Trade-Ergebnisanzeige nicht integriert; native Sollwerte nicht ausgeführt |
| A3 | Optionale Quellen unabhängig geladen; UI fehlend/Fehler/gezielter Retry; Finanz-Owner unverändert | Identische wirtschaftliche Fakten im vollständigen neuen Weg noch nativ nachweisen |
| A4 | Exakter Planleser und P1-UI-Fall, kein latest-Aufruf | Native P1/P2-/Approval-/Fremdbezüge nur vorbereitet |
| A5 | Bestehende Owner-Timeline/Währungsauflösung; UI zeigt Storno und ersetzte Fakten | Tatsächlicher DB-Abgleich der neuen Komposition offen |
| A6 | UI unterscheidet Kategorien, fehlend, DRAFT und ausdrückliches NOT_ASSESSABLE ohne Score | Gewinn/IMPROVABLE und Verlust/GOOD mit realer Geldanzeige offen |
| A7 | UI prüft Freitext und P1 ohne inferierten Regelverstoß; Preisachsenwarnung | Kein allgemeiner Regelprüfer oder neue Qualitätsmethodik geliefert |
| A8 | UI prüft genaue Journal-Pins, Revision und leeres Final; U prüft Pin-Weitergabe | Native Korrektur-/Finalhistorie nur vorbereitet |
| A9 | UI bewahrt genaue L1-Links und widersprechende Relationen; invalider Pin fällt nicht auf latest | Echter Browserlink/Reload und native Relation noch offen |
| A10 | Beziehungsliste ohne eigene Geldaggregation; mehrere Lessonrelationslinks erhalten | Geldbetrag-Einmaligkeit im integrierten Gesamtweg offen |
| A11 | U/ UI unterscheiden leer, NOT_ASSESSABLE, Status, technischen Fehler; gezielter Retry | Native aktuelle Quellenprüfung muss noch laufen |
| A12 | UI mit kontrollierten Promises: A→B→A, Version, späte Erfolge/Fehler, Unmount | Kein vollständiger nativer Browsernachweis |
| A13 | Separate Lesefenster sichtbar; PG enthält zwei kontrollierte Writer-Races | PostgreSQL-Konsistenzlauf und Bezugswechsel Abschlussliste→Detail offen |
| A14 | U nur GET/POST 405; UI kein Editor; bestehende Command-Locks erhalten | Tabellenfingerprints und echte Netzwerkbeobachtung in PG/Browser offen |
| A15 | Scoped Reader vor Kindauflösung; U Fehlerfälle/DB-Details bereinigt | Native fremde Workspace-/Relationsfälle nur vorbereitet |
| A16 | 598 Frontendtests und 680 betroffene Backend-Unitfälle bestanden | Vollständige Backend-CI, neue native Browserreise und Desktop/Mobil-Sichtprüfung offen |

## Liefer- und Befugnisgrenze

Container hat kein Docker, PostgreSQL-Binary oder konfiguriertes Testdatenbankziel.
Git-Remotezugriff scheitert an DNS; der GitHub-Leseconnector bestätigt den Remotezustand,
bietet in dieser Sitzung aber keine schreibende Publikationsaktion. Kein Schutzflag wurde
gefälscht, keine private `.env`/Nutzerdatenbank verwendet, kein Provider aktiviert.
Kein neuer Remote-Commit/PR, Merge, Release, Tag, Produktionsmigration oder PC-Update.
Keine fachliche Benutzerabnahme, kein beobachteter Betrieb, kein Abschluss von M7/M8.

Nächster zusammenhängender Schritt: das verifizierte Bundle auf einen eigenen normalen
Entwicklungsbranch übernehmen und im bestehenden geprüften Wegwerf-/CI-Stack die vollständigen
Backend- sowie neuen PostgreSQL-/Browsernachweise ausführen; erst danach technische Merge-Reife
beurteilen. Die Integration von #270 bleibt eine ausdrücklich separate Abhängigkeit.
