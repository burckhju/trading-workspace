# Sprint 4 – FT-006 Marktanalyse

## Erledigte Arbeiten

- eigenständiges Analyse-Feature mit Domain-, Service-, Persistence- und API-Schicht
- deterministisches EOD-Trend-/Momentum-Modell V1
- providerneutraler interner Market-Data-Read-Adapter
- versionierte Analyseausführungen mit vollständigem Snapshot und SHA-256-Hash
- additive Alembic-Migration `20260805_0003`
- REST API für Anlage, Liste, Ausführung und Versionsdetail
- React-Seite und API-Client für die Marktanalyseübersicht
- Domain-Tests für Determinismus, Reproduzierbarkeit und unzureichende Daten

## Offene Punkte

- Auswahl von Basiswert und Listing im Frontend über Stammdaten statt manueller UUID-Eingabe
- dedizierte Detailseite mit Parametereditor und Snapshot-Ansicht
- explizite Audit-Event-Tabelle für jeden Statusübergang
- Retry-/Supersede-Endpunkte
- Integrations- und E2E-Tests mit realer PostgreSQL-Testdatenbank

## Risiken

- Die V1-Ausführung ist synchron und sollte auf begrenzte EOD-Zeiträume beschränkt bleiben.
- Die Aktualitätsprüfung verwendet den lokalen Kalendertag; ein Handelskalender ist noch nicht Bestandteil des Systems.
- Volatilität verwendet für Logarithmus und Quadratwurzel intern Python-Float, während persistierte Ein- und Ausgaben Decimal-basiert bleiben. Eine vollständig dezimale Mathematikbibliothek kann später eingeführt werden.

## Testergebnisse

- neue Domain-Tests: 3 bestanden
- ausgewählte Regressionen aus Market Data und Dependency Injection: insgesamt 19 bestanden
- Python-Compile-Check für `backend/app`: erfolgreich
- Ruff, Black und mypy konnten in der gelieferten Umgebung nicht gestartet werden, weil die ausführbaren Werkzeuge nicht global installiert und die mitgelieferte virtuelle Umgebung nicht portabel ist
- Frontend-Quality-Gates bleiben wegen des unvollständigen mitgelieferten `node_modules`-Verzeichnisses offen

## Dokumentationsstatus

Feature-Dokumentation und zwei ADRs sind erstellt. API- und Datenbankreferenz sollten nach erfolgreichem Integrationslauf final synchronisiert werden.

## Empfohlener nächster Schritt

Testumgebungen frisch installieren, Migration gegen PostgreSQL ausführen und anschließend Integrations-, API- und Frontend-Tests vervollständigen.

## Nachgelagerte Verifikation vom 5. August 2026

- FT-006-REST-Vertragstests ergänzt: OpenAPI, Erzeugung, Ausführung, Correlation-ID, Datumsvalidierung sowie Fehlerabbildung.
- Einen Integrationsfehler im Fehlervertrag behoben: Analysefehler werden nun über den zentralen `ApplicationError`-Vertrag ausgegeben und nicht mehr als verschachtelte `HTTPException`-Details verworfen.
- Backend-Gesamtlauf: 174 Tests bestanden.
- Testabdeckung: 89,43 %; das Quality Gate von 85 % ist erfüllt.
- Python-Compile-Check erfolgreich.
- Alembic-Revisionskette geprüft: `20260805_0003` ist der einzige Head.
- Ein realer PostgreSQL-Upgrade-/Downgrade-Test war in der Ausführungsumgebung nicht möglich, da weder Docker noch eine PostgreSQL-Instanz bereitstanden.
- Ruff, Black und mypy konnten nicht installiert werden, weil die bereitgestellte Paketquelle die gepinnten Pakete nicht auslieferte.
- `npm ci` konnte nicht abgeschlossen werden, weil die Paketquelle `yocto-queue@0.1.0` nicht auslieferte. Frontend-Typecheck, Lint, Coverage und Build bleiben deshalb extern zu verifizieren.

## Arbeitseinheit 2026-08-06: Frontend-Auswahl und Analyse-Detailansicht

### Erledigt

- Manuelle UUID-Eingaben durch eine Basiswertauswahl über die bestehende FT-001-Such-API ersetzt.
- Aktive Listings werden nach Auswahl des Basiswerts über dessen bestehende Detail-API geladen.
- Das primäre aktive Listing wird automatisch vorausgewählt.
- Marktanalysen verlinken auf eine eigenständige Detailseite.
- Parametrisierte Ausführung neuer Analyseversionen ergänzt.
- Ergebnisübersicht mit Status, Qualitätsstatus, Modell, Datenquelle und Kennzahlen ergänzt.
- Kriterien inklusive Klassifikation, Wert und Erklärung dargestellt.
- Reproduzierbarkeitsinformationen mit aufgelösten Parametern, Analysezeitpunkt und Eingabe-Hash ergänzt.
- Verwendeter persistierter Marktdaten-Snapshot kann vollständig eingeblendet werden.
- Analyse-HTTP-Client auf den zentralen, strukturierten API-Fehlervertrag umgestellt.
- Drei Frontend-Komponententests für Auswahl, Ausführung, Kriterien und Snapshot ergänzt.

### Architektur

Es wurden keine neuen Backend- oder Provider-Abhängigkeiten eingeführt. Das Frontend verwendet ausschließlich die vorhandenen REST-Schnittstellen von `market` und `analysis`. Fachliche Berechnungen verbleiben vollständig im Backend.

### Testergebnisse

- Backend-Regression: `174 passed`.
- Frontend-Testdateien wurden ergänzt.
- `npm ci` ist in der bereitgestellten Umgebung weiterhin nicht ausführbar, da die konfigurierte Paketquelle `yocto-queue@0.1.0` mit HTTP 404 beantwortet.
- TypeScript-, Vitest-, ESLint-, Prettier- und Build-Gates sind daher in dieser Umgebung nicht abschließend ausführbar.

### Offene Punkte

- Frontend-Gates in CI oder einer Entwicklungsumgebung mit vollständiger npm-Registry ausführen.
- Nutzerfreundliche Namen von Basiswert und Listing auch in der bestehenden Analyseliste serverseitig oder über einen dedizierten View-Read-Model-Vertrag bereitstellen; aktuell zeigt die Liste zur vollständigen Traceability weiterhin IDs.
- Optional weitere Modellparameter wie Momentum-Fenster und Annualisierungsfaktor über einen erweiterten Expertenmodus editierbar machen.

### Risiken

- Die Basiswertsuche lädt für die Auswahl maximal 100 aktive Einträge. Bei größeren Beständen sollte auf eine serverseitig suchende Combobox mit Pagination umgestellt werden.
- Der Snapshot kann bei großen Analysezeiträumen viele Zeilen enthalten; aktuell wird er erst auf Nutzeraktion gerendert, langfristig ist serverseitige Pagination sinnvoll.

### Empfohlener nächster Schritt

Frontend-Gates in CI ausführen und anschließend serverseitige Snapshot-Pagination sowie eine suchende, paginierte Basiswertauswahl umsetzen.

## Arbeitseinheit 2026-08-06: Snapshot-Pagination und Basiswertsuche

### Erledigt

- Additiver REST-Endpunkt `GET /api/v1/market-analyses/{analysis_id}/runs/{version}/snapshot` mit `offset` und `limit`.
- Bestehender Run-Detail-Endpunkt bleibt kompatibel und unterstützt zusätzlich `include_snapshot=false`.
- Repository-Abfragen für Snapshot-Seiten und Gesamtanzahl ergänzt.
- Frontend lädt Analyse-Details ohne Snapshot und fordert Snapshot-Seiten erst bei Bedarf an.
- Snapshot-Navigation mit 50 Zeilen pro Seite ergänzt.
- Basiswertauswahl auf serverseitige Suche und Pagination umgestellt.
- Suche verwendet unverändert die FT-001-Schnittstelle und unterstützt Name, ISIN, WKN und Ticker gemäß bestehendem Suchvertrag.
- REST-Vertragstests für Snapshot-Pagination und Abwärtskompatibilität ergänzt.

### Architekturentscheidung

Die Erweiterung ist rein additiv. Persistenzmodell, Domain-Berechnung und Provider-Abstraktion bleiben unverändert. Snapshot-Daten werden weiterhin unveränderlich gespeichert; lediglich der Lesezugriff wird paginiert.

### Testergebnisse

- Backend: 177 Tests bestanden.
- Python-Compile-Check: bestanden.
- Frontend-Testdateien angepasst; Ausführung lokal nicht möglich, da `vitest` in der gelieferten npm-Umgebung fehlt.
- Ruff, Black und mypy nicht ausführbar, da die Programme in der Laufzeitumgebung nicht installiert sind.

### Offene Punkte und Risiken

- Frontend-Typecheck, Vitest, ESLint, Prettier und Produktions-Build müssen in CI mit vollständiger npm-Registry ausgeführt werden.
- Die Analyseübersicht selbst ist weiterhin nicht paginiert; bei stark wachsendem Bestand sollte auch dieser Read-Endpunkt paginiert werden.

### Empfohlener nächster Schritt

Analyseübersicht serverseitig paginieren und die UI um fachliche Basiswert-/Listing-Bezeichnungen statt UUID-Darstellung ergänzen.

## Arbeitseinheit 2026-08-06: Paginierte, fachlich lesbare Analyseübersicht

### Erledigt

- Additiver Read-Endpunkt `GET /api/v1/market-analyses/page` mit `offset` und `limit`.
- Der bestehende Endpunkt `GET /api/v1/market-analyses` bleibt unverändert erhalten.
- Übersichtsdaten werden über eine einzelne SQL-Join-Abfrage geladen.
- Rückgabe enthält Basiswertname, Ticker, MIC, Handelsplatzname und Währung.
- Frontend-Tabelle zeigt fachliche Bezeichnungen; UUIDs bleiben als technische Referenzen sichtbar.
- Vorwärts-/Rückwärtsnavigation für die Analyseübersicht ergänzt.
- REST-Vertragstest für Pagination und angereicherte Referenzdaten ergänzt.

### Testergebnisse

- 178 Backend-Tests bestanden.
- Python-Compile-Check für das Analysemodul bestanden.
- Frontend-Quality-Gates bleiben wegen der unvollständigen npm-Abhängigkeiten in der bereitgestellten Umgebung offen.

### Architekturentscheidung

Keine Breaking Change: Die Pagination wurde über einen additiven Endpunkt eingeführt. Stammdaten werden ausschließlich im Read-Pfad angereichert; Domain und persistierter Analyse-Snapshot bleiben unverändert.

### Risiken und offene Punkte

- Die Übersicht unterstützt derzeit keine serverseitige Filterung nach Basiswert, Status oder Zeitraum.
- Bei parallelem Anlegen neuer Analysen kann offset-basierte Pagination Verschiebungen zeigen; Cursor-Pagination ist bei sehr großen Datenbeständen zu prüfen.

### Empfohlener nächster Schritt

Serverseitige Filter- und Sortierparameter für die Analyseübersicht sowie Anzeige des letzten Ausführungsstatus und Analysezeitpunkts ergänzen.

## Arbeitseinheit 2026-08-06: Filter, Sortierung und letzter Ausführungsstand

### Erledigt

- additiv erweiterter paginierter Read-Endpunkt mit Filtern nach Basiswert, letztem Ausführungsstatus, letztem Qualitätsstatus und Analysezeitraum
- serverseitige Sortierung nach Erstellzeitpunkt, Basiswertname, letztem Analysezeitpunkt, Status oder Qualitätsstatus
- stabile Sortierrichtung `asc`/`desc` mit validierten API-Parametern
- Ermittlung des letzten Runs über eine gruppierte Subquery und Outer Join
- Analysen ohne Ausführung bleiben sichtbar und werden als „Noch nicht ausgeführt“ dargestellt
- Frontend-Filter für Status und Qualität sowie Sortierfeld und Sortierrichtung
- Anzeige von letzter Version, Status, Qualitätsstatus und Analysezeitpunkt in der Übersicht
- keine N+1-Abfragen und keine Änderungen am Domain- oder Persistenzmodell

### REST-Erweiterung

`GET /api/v1/market-analyses/page` unterstützt zusätzlich:

- `underlying_id`
- `status`
- `quality_status`
- `analysis_time_from`
- `analysis_time_to`
- `sort_by=created_at|underlying_name|latest_analysis_time|latest_status|latest_quality_status`
- `sort_direction=asc|desc`

Die Response-Einträge enthalten zusätzlich `latest_version`, `latest_status`, `latest_quality_status` und `latest_analysis_time`. Alle Felder sind nullable, damit Analysen ohne Run vollständig repräsentiert werden.

### Tests

- Python-Compile-Check bestanden
- vollständige Backend-Regression: 178 Tests bestanden
- REST-Vertrag für Filter, Sortierung und letzte Run-Daten aktualisiert

### Offene Punkte

- Frontend-Quality-Gates bleiben wegen der unvollständigen npm-Abhängigkeiten in dieser Umgebung offen.
- Die Zeitfilter sind API-seitig verfügbar; eine Datumsfilteroberfläche kann bei Bedarf ergänzt werden.

### Empfohlener nächster Schritt

Status- und Qualitätswerte im Frontend als fachlich übersetzte Badges darstellen, Filterzustand in der URL persistieren und einen CSV-Export der aktuell gefilterten Übersicht ergänzen.

## Arbeitseinheit 2026-08-06: Badges, URL-Filterzustand und CSV-Export

### Erledigt

- Status und Qualitätsstatus werden in der Analyseübersicht als fachlich übersetzte Badges dargestellt.
- Badge-Darstellung trennt Status und Datenqualität weiterhin fachlich und visuell.
- Pagination, Statusfilter, Qualitätsfilter und Sortierung werden in URL-Query-Parametern persistiert.
- Direkte Links und Browser-Navigation stellen den Filterzustand wieder her.
- Additiver CSV-Endpunkt `GET /api/v1/market-analyses/export.csv` ergänzt.
- Der Export verwendet dieselben Filter- und Sortierparameter wie die paginierte Übersicht.
- CSV-Ausgabe ist UTF-8 mit BOM und Semikolon-Trennung für deutschsprachige Tabellenkalkulationen.
- Export enthält Analyse-ID, fachliche Basiswert-/Listingdaten, letzte Version, Status, Qualitätsstatus, Analysezeitpunkt und Erstellzeitpunkt.

### Architekturentscheidung

Der CSV-Export liegt im Read-Pfad des Analysemoduls und verwendet den bestehenden Overview-Service. Es wurde keine Exportlogik in Domain oder Persistence dupliziert. Der bestehende Listen- und Seitenvertrag bleibt unverändert.

### Tests

- REST-Vertragstest für CSV-Inhalt, Header, Dateiname und Filterweitergabe ergänzt.
- Analyse-REST-Tests: 10 bestanden.
- Vollständige in diesem Artefakt enthaltene Backend-Unit-Test-Suite: 172 bestanden.
- Python-Compile-Check bestanden.
- Die zuvor dokumentierte Zahl von 178 Tests lässt sich mit dem als Ausgangspunkt gelieferten ZIP nicht reproduzieren; dieses ZIP enthält und sammelt 172 Backend-Unit-Tests. Es wurden keine Tests entfernt.
- Frontend-Quality-Gates bleiben wegen der unvollständigen npm-Abhängigkeiten offen.

### Risiken und offene Punkte

- Der CSV-Export ist zum Schutz der synchronen API auf 10.000 Datensätze begrenzt. Für größere Bestände ist ein asynchroner Export oder Streaming mit Cursor-Pagination vorzusehen.
- API-seitige Zeitfilter sind weiterhin nicht als Datumsfelder in der Oberfläche verfügbar.
- Die URL-Persistenz umfasst die Analyseübersicht, nicht die separate Basiswertsuche zum Anlegen einer Analyse.

### Empfohlener nächster Schritt

Datumsfilter für den Analysezeitraum im Frontend ergänzen, aktive Filter als entfernbare Chips anzeigen und einen expliziten „Filter zurücksetzen“-Vorgang bereitstellen.

## Arbeitseinheit 2026-08-06: Datumsfilter, Filterchips und Reset

### Erledigt

- Frontend-Datumsfilter `Analysezeit ab` und `Analysezeit bis` ergänzt.
- Zeitfilter werden an den bestehenden paginierten Read-Endpunkt weitergegeben.
- Zeitfilter werden zusammen mit Status, Qualität, Sortierung und Pagination in der URL persistiert.
- CSV-Export übernimmt exakt dieselben Zeitfilter wie die sichtbare Übersicht.
- Aktive fachliche Filter werden als einzeln entfernbare Chips dargestellt.
- Status- und Qualitätswerte werden in den Chips fachlich übersetzt.
- Zentrale Aktion `Filter zurücksetzen` entfernt Status-, Qualitäts- und Zeitfilter und setzt Sortierung sowie Pagination auf die Standardwerte zurück.
- Datumsfelder begrenzen sich gegenseitig über `min`/`max`, ohne zusätzliche Fachlogik im Frontend einzuführen.
- Frontend-Komponententest für URL-Wiederherstellung, Parameterweitergabe, Filterchips und Reset ergänzt.

### Architekturentscheidung

Die Erweiterung bleibt vollständig im bestehenden Overview-Read-Pfad. Es wurden weder Domain Model noch Persistence oder REST-Verträge verändert. Die API-seitig bereits vorhandenen Parameter `analysis_time_from` und `analysis_time_to` werden nun durchgängig von URL, Übersicht und Export verwendet.

### Tests

- vollständige Backend-Regression: 178 Tests bestanden.
- Frontend-Test wurde ergänzt, konnte in der bereitgestellten Umgebung jedoch nicht ausgeführt werden, da `vitest` im unvollständigen `node_modules`-Verzeichnis fehlt.
- Es wurden keine bestehenden Tests entfernt.

### Risiken und offene Punkte

- `datetime-local` enthält keine explizite Zeitzone. Die API interpretiert den eingegebenen lokalen Zeitpunkt gemäß bestehendem Request-Vertrag; für verteilte Benutzerstandorte sollte später eine explizite Zeitzonenanzeige ergänzt werden.
- Frontend-Typecheck, Vitest, ESLint, Prettier und Produktions-Build bleiben in einer vollständigen npm-Umgebung zu bestätigen.

### Empfohlener nächster Schritt

Die Filterbedienung um einen auswählbaren Basiswertfilter ergänzen und die aktuelle Filterkonfiguration als benannte Ansicht speicherbar machen, ohne die Analyse-Domain zu erweitern.

## Arbeitseinheit 2026-08-06: Basiswertfilter und benannte Ansichten

### Erledigt

- Serverseitigen Basiswertfilter der Analyseübersicht im Frontend integriert.
- Der bestehende API-Parameter `underlying_id` wird für Übersicht, URL-Zustand und CSV-Export identisch verwendet.
- Aktiver Basiswertfilter wird als entfernbarer Filterchip dargestellt.
- Benannte Filteransichten können gespeichert, angewendet und gelöscht werden.
- Eine Ansicht enthält Basiswert, Status, Qualitätsstatus, Analysezeitraum und Sortierung.
- Gespeicherte Ansichten werden als benutzerspezifische Browserpräferenz in `localStorage` abgelegt.
- Ungültige oder beschädigte lokale Daten werden defensiv ignoriert.
- Der zuvor versehentlich doppelt verschachtelte Frontend-Testblock wurde bereinigt.

### Architekturentscheidung

Benannte Ansichten sind eine UI-Präferenz und keine fachliche Marktanalyse. Sie werden deshalb nicht im Analysis-Domain- oder Persistence-Modell gespeichert. Die Speicherung ist auf das jeweilige Browserprofil beschränkt und führt keine neue Backend- oder Providerabhängigkeit ein. Für eine spätere geräteübergreifende Synchronisation ist ein separates User-Preferences-Modul vorzusehen.

### Tests

- vollständige Backend-Regression: 178 Tests bestanden.
- Python-Compile-Check bestanden.
- Frontend-Tests für Basiswertfilter und Speicherung benannter Ansichten ergänzt.
- Separate Unit-Tests für Persistenz, Wiederherstellung und beschädigte lokale Daten ergänzt.
- Frontend-Testausführung bleibt offen, da `vitest` in der gelieferten npm-Umgebung nicht vorhanden ist.

### Risiken und offene Punkte

- Gespeicherte Ansichten sind derzeit browser- und gerätespezifisch; es besteht keine serverseitige Synchronisation.
- Der Basiswertfilter verwendet die aktuell geladene, paginierte Basiswertauswahl. Für sehr große Bestände ist eine eigenständige suchende Combobox im Filterbereich sinnvoll.
- Umbenennen oder Überschreiben einer bestehenden Ansicht ist noch nicht vorgesehen; aktuell wird eine neue Ansicht erzeugt.

### Empfohlener nächster Schritt

Benannte Ansichten optional über ein eigenständiges User-Preferences-Modul serverseitig synchronisieren und den Basiswertfilter als suchende Combobox mit eigener Pagination ausführen.

## Arbeitseinheit: serverseitige Benutzeransichten und eigenständige Basiswertsuche

### Umsetzung

- Neues, fachlich unabhängiges Feature `user_preferences` für UI-Präferenzen.
- Preferences sind nach Workspace, Actor-ID, Typ und Name abgegrenzt.
- Der bestehende Header `X-Actor-ID` dient als Identitätsgrenze; solange keine Authentifizierung existiert, wird explizit `local-user` verwendet.
- Additive REST API zum Auflisten, Anlegen und Löschen benannter Ansichten.
- Additive Migration `20260806_0004_user_preferences`.
- Marktanalyse-Ansichten werden nicht mehr im Browser-`localStorage`, sondern über den Preferences-Vertrag gespeichert.
- Eigenständige suchende Basiswert-Combobox für den Übersichtsfilter mit serverseitiger Suche und eigener Pagination.
- Der ausgewählte Basiswertname wird zusammen mit der Ansicht gespeichert, damit gespeicherte Filter unabhängig von der aktuellen Suchseite lesbar bleiben.

### Architektur

Das Preferences-Modul enthält ausschließlich Benutzeroberflächenkonfigurationen. Es hängt nicht von der Analysis Domain ab und die Analysis Domain hängt nicht von Preferences ab. Die gespeicherten Werte sind transparente JSON-Dokumente; Filterauswertung und fachliche Analyse verbleiben in ihren bestehenden Modulen.

### Tests

- Actor-scoped Listing der Preferences
- lokaler Identitätsfallback
- Actor-scoped Delete
- additive und lineare Migration
- vollständige Backend-Regression: 183 Tests bestanden
- Python Compile Check bestanden

### Offene Verifikation

Frontend-Typecheck, Vitest, ESLint und Build konnten weiterhin nicht ausgeführt werden, da die bereitgestellten npm-Abhängigkeiten unvollständig sind (`tsc`/`vitest` nicht verfügbar).

### Risiko

`local-user` ist nur ein expliziter Übergangsmechanismus für den aktuellen Single-User-Betrieb. Vor Mehrbenutzerbetrieb muss `X-Actor-ID` ausschließlich aus einer authentifizierten Identität gesetzt und darf nicht frei vom Browser vorgegeben werden.

## Arbeitseinheit: Zentrale Request Identity

### Erledigt

- zentrale Backend-Abstraktion `RequestIdentity` eingeführt
- Headernormalisierung und lokaler Fallback in eine FastAPI-Dependency verschoben
- User-Preferences-Router auf Dependency Injection umgestellt
- zentralen Frontend-Identity-Provider eingeführt
- gemeinsamen HTTP-Transport um automatische Identity-Header ergänzt
- feste Actor-ID aus dem Analysis-Preferences-Client entfernt
- Backend-Tests für explizite Header und lokalen Fallback ergänzt
- ADR-S4-004 dokumentiert

### Architekturstatus

Die Identity-Auflösung liegt am technischen Anwendungsrand. Analysis und User Preferences kennen weder Authentifizierungsmechanismen noch Headerdetails. Der aktuelle Kontext kennzeichnet sich ausdrücklich als nicht authentifiziert.

### Testergebnisse

- 178 Backend-Unit-Tests bestanden
- Python-Compile-Check bestanden
- Frontend-Test für zentral gesetzte Identity ergänzt, in der bereitgestellten unvollständigen npm-Umgebung jedoch nicht ausführbar

### Offene Punkte und Risiken

- Es existiert weiterhin keine Authentifizierung oder Autorisierung.
- `X-Actor-ID` ist aktuell ein vertrauensbasierter Übergangsvertrag.
- Vor Mehrbenutzerbetrieb sind Auth-Adapter, Session-/Tokenvalidierung und Berechtigungsregeln erforderlich.

### Empfohlener nächster Schritt

Eine Authentifizierungsarchitektur mit klaren Sicherheitsanforderungen, Trust Boundary, Session- beziehungsweise Tokenstrategie und rollenbasierter Autorisierung entwerfen; erst nach Freigabe implementieren.

## Arbeitseinheit 2026-08-06: Analyse-Lifecycle, Retry/Supersede und Reproduzierbarkeitsprüfung

### Erledigt

- Explizite Domain-State-Machine für alle dokumentierten FT-006-Statusübergänge eingeführt.
- Append-only Persistence-Modell `market_analysis_events` ergänzt.
- Additive Alembic-Migration `20260806_0005_market_analysis_lifecycle` erstellt.
- Analyseausführungen persistieren `RUNNING` und den vollständigen Eingabe-Snapshot vor der Berechnung.
- Erfolgreiche Berechnungen wechseln kontrolliert in `COMPLETED`, `COMPLETED_WITH_WARNINGS` oder `NOT_EVALUABLE`.
- Berechnungsfehler werden als `FAILED` samt Fehlerhinweis und Lifecycle-Event persistiert.
- Retry für `FAILED` und `NOT_EVALUABLE` implementiert.
- Retry verwendet ausschließlich gespeicherten Snapshot, aufgelöste Parameter, Modell-ID und Modellversion; es erfolgt kein Zugriff auf aktuelle Marktdaten.
- Explizites Supersede einer älteren Version durch eine neuere Version implementiert.
- Abgeschlossene Run-Zeilen und Snapshots werden beim Supersede nicht verändert; die Ablösung wird ausschließlich als Event dokumentiert.
- Reproduzierbarkeitsprüfung implementiert.
- Datenalter-Bewertung von aktuellem Tagesdatum auf den persistierten Analysezeitpunkt umgestellt, damit historische Ergebnisse zeitstabil bleiben.

### Neue REST-Verträge

- `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/retry`
- `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/supersede`
- `GET /api/v1/market-analyses/{analysis_id}/events`
- `POST /api/v1/market-analyses/{analysis_id}/runs/{version}/verify`

Ungültige Lifecycle-Übergänge werden über den bestehenden zentralen Fehlervertrag als HTTP 409 mit `ANALYSIS_CONFLICT` ausgegeben.

### Reproduzierbarkeitsprüfung

Die Verifikation prüft getrennt:

- Verfügbarkeit der ursprünglichen Modell-ID und Modellversion;
- SHA-256-Eingabe-Hash;
- berechnete Kennzahlen;
- Einzelkriterien inklusive Klassifikation, Wert und Erklärung;
- Qualitätsstatus;
- Hinweise.

Nur wenn alle Prüfungen erfolgreich sind, ist `verified=true`.

### Persistence

Neue Tabelle `market_analysis_events` mit unter anderem:

- Analyse-ID;
- Run-ID und Version;
- Event-Typ;
- Ausgangs- und Zielstatus;
- Quellversion;
- Ersatzversion;
- Begründung;
- Correlation-ID;
- Ereigniszeitpunkt.

Die Revisionskette bleibt linear:

`20260803_0001 -> 20260805_0002 -> 20260805_0003 -> 20260806_0004 -> 20260806_0005`

### Testergebnisse

- vollständige Backend-Regression: **197 Tests bestanden**;
- Python-Compile-Check für Anwendung und Migrationen bestanden;
- State-Machine-Tests für erlaubte und verbotene Übergänge;
- Service-Test bestätigt Retry ohne Market-Data-Zugriff;
- Service-Test bestätigt deterministische Reproduzierbarkeit aus persistiertem Snapshot;
- REST-Vertragstests für Retry, Supersede, Events, Verification und Konfliktabbildung;
- Migrationstest für die lineare Revision `20260806_0005`.

### Architekturentscheidung

ADR-S4-005 dokumentiert die append-only Lifecycle-Strategie. Der historische Ausführungsstatus eines terminalen Runs bleibt unverändert. `SUPERSEDED` ist eine Lifecycle-Projektion aus einem unveränderlichen Event und keine nachträgliche Mutation des abgeschlossenen Runs.

### Risiken und offene Punkte

- Historische Modellversionen müssen künftig über eine Modell-Registry verfügbar gehalten werden, sobald mehr als eine Analysemodellversion existiert. Aktuell existiert ausschließlich `EOD_TREND_MOMENTUM 1.0.0`.
- Eine echte parallele Ausführung wird aktuell durch einen Application-Service-Conflict gegen bereits laufende Runs begrenzt. Für Multi-Worker-/Multi-User-Betrieb wäre zusätzlich eine transaktionale Datenbanksperre oder ein Job-Orchestrator erforderlich; für den aktuellen Single-User-Betrieb ist dies nicht notwendig.
- Die Frontend-Detailansicht stellt die neue Event-Historie und Retry/Supersede-Aktionen noch nicht dar.

### Empfohlener nächster Schritt

Die Analyse-Detailansicht um Versionshistorie, Lifecycle-Events, Reproduzierbarkeitsstatus und kontrollierte Retry-/Supersede-Aktionen erweitern. Danach kann der fachliche Architecture Review für FT-006 durchgeführt werden.


## Arbeitseinheit: Lifecycle-UI und Sprint-4-Abnahme

Die Analyse-Detailansicht wurde um Versionshistorie, Lifecycle-Events, Reproduzierbarkeitsprüfung sowie kontrollierte Retry-/Supersede-Aktionen erweitert. Ersetzte Versionen bleiben historisch unverändert und werden anhand append-only Events gekennzeichnet. Gründe für Fehler, Hinweise und Ablösungen werden in der Oberfläche sichtbar gemacht.

Die UI verwendet ausschließlich die bestehenden FT-006-REST-Verträge. Domain, Persistence und Provider-Abstraktion wurden in dieser Arbeitseinheit nicht verändert.


### Testergebnis dieser Arbeitseinheit

- Backend gesamt: **197 Tests bestanden** (`PYTHONPATH=backend python -m pytest -q`)
- Python Compile Check: bestanden
- Frontend Typecheck/Vitest/Build: in der gelieferten Umgebung weiterhin nicht ausführbar, da die npm-Installation unvollständig ist (`typescript/lib/tsc.js` und Vitest-Binaries fehlen).

## Arbeitseinheit 2026-08-06: Technischer Sprint-Closeout

### Reproduzierbare Ergebnisse

- vollständige Backend-Suite aus dem Repository-Root: **197 Tests bestanden**;
- Backend-Coverage: **87,20 %**, Gate >= 85 % bestanden;
- Alembic-Revisionskette linear, genau ein Head `20260806_0005`;
- Release-Readiness-Skript ausgeführt; lokaler Blocker ist fehlendes Docker.

Die zwischenzeitlich beobachtete Zahl von 196 Tests entstand durch die explizite Ausführung nur von `tests/unit/backend` und `tests/integration/backend`. Der projektübliche Root-Lauf sammelt zusätzlich einen weiteren konfigurierten Test und bestätigt die zuvor dokumentierten 197 Tests.

### Externe Blocker

- Frische Python-Abhängigkeiten können aus der konfigurierten Registry nicht vollständig installiert werden; unter anderem fehlen `hatchling>=1.27` und `alembic==1.18.4`.
- `npm ci` scheitert reproduzierbar an `yocto-queue@0.1.0` (HTTP 404 der internen npm-Registry).
- Docker/PostgreSQL stehen in der aktuellen Laufzeit nicht zur Verfügung.

Deshalb bleiben Ruff, Black, mypy, Frontend-Typecheck/Lint/Format/Vitest/Build, echter PostgreSQL-Migrationslauf und Playwright-E2E als externe Release-Gates offen.

### Release-Status

Der Stand wird als **v0.4.0-market-analysis-rc.1** klassifiziert. Eine finale Freigabe `v0.4.0-market-analysis` erfolgt erst nach grünen externen Quality Gates.

Siehe `docs/implementation/SPRINT_4_TECHNICAL_CLOSEOUT.md` und `docs/releases/V0.4.0-MARKET-ANALYSIS-RC1.md`.
