# Hebeltrader research preparation - technische Qualifikation

Nachweisstand 11.11.2026. Arbeitsstatus ausschließlich unter
[PB-019 Externe historische Forschung](../planning/PRODUCT_BACKLOG.md#pb-019-external-research).
Fachlicher Vertrag:
[HEBELTRADER_RESEARCH_PREPARATION](../features/HEBELTRADER_RESEARCH_PREPARATION.md).

## Ausgangsstand und Architekturentscheidung

Basiscommit: `d01c259f4b79fdfbdcec8743ececda035b69f9d1`, Software 1.5.46.
Eigener Entwicklungsbranch `feature/hebeltrader-222-evaluation`.

Die Inventur findet einen bestehenden PDF-Bulkimport im Learning-Owner,
separate Warrant-/Listing-/Terms-Verträge und qualifizierte Aktiendatenadapter.
Sie findet keinen bestehenden allgemeinen XLSX-/JSON-Empfehlungsimport und
keinen rückwirkenden vollständigen EUR-Optionsschein-Datenabruf. Ein direkter
Import in reale Trades oder in deren Performanceberichte wäre fachlich falsch.

Der neue Schnitt ist deshalb ein ausdrücklich lokaler Dateiweg. Reine Typen
und Prüfregeln bleiben beim Learning-Owner; die Anwendung erzeugt die
deterministischen Exportinhalte; `app.tools` adaptiert Argumente und Dateizugriff.
Er benötigt weder Settings noch Datenbank, Provider, Identitätsanlage oder
HTTP-Routen. Es gibt keine Migration und keine Frontendänderung.

## Währungen, Zeitbezug und Unbekanntes

Basiswertnotierung, Produktnotierung und Basispreiswährung werden unabhängig
erhalten. Ein USD-Basiswert mit EUR-Produkt ist ein gültiger Quellenfall.
EUR-Produktpreise werden nicht nochmals mit einem Aktien-FX-Kurs umgerechnet.
Ein von EUR abweichender Produktquellenwert bleibt als Konflikt sichtbar.

Veröffentlichungsdaten erhalten `DATE_ONLY`, keinen erfundenen UTC-Zeitpunkt.
Fälligkeit vor Veröffentlichung, fehlende Herkunft, unklare Produktart und
Turbo-Lifecycle-Bedarf bleiben je Fall sichtbar. Ein fälliges Produkt erhält
ohne Settlement-Beleg weder einen Nullkurs noch einen berechneten Verlust.

Eine vollständige Quellenvorbereitung ist keine vollständige Performanceanalyse.
Alle historischen Ergebnisfelder dieses Exports bleiben `NOT_COMPUTED`.
Vorhandene alte Ergebnisse mit anderem Stichtag werden nicht eingemischt.

## Wiederverwendung und bewusst getrennte Verträge

| Baustein | Nutzbare Verbindung | Nachweisgrenze |
|---|---|---|
| FT-012 ExternalObservation / Bulkimport | Herkunft, fachlicher Review und explizite Bestätigung | Der neue Dateiweg materialisiert keine Observation oder LearningEvidence. |
| Referenzdaten / Provider-Mappings | WKN/ISIN, konkrete Listings und versionierte Zuordnungen | WKN plus Währung ist zunächst eine Bedarfsgruppe, keine verifizierte Listing-ID. |
| Market Data / EODHD | Aktiendaten, Provenienz, Budget- und Qualitätsverträge | Aktien-OHLC liefern keine historischen deutschen Optionsschein-Bid-/Askpreise. |
| Warrant Terms / Quotes | Getrennte Währungen, Terms-Versionen und Originalzeit | Aufbewahrte Live-Samples sind kein nachträglicher Vollhistorienabruf. |
| Modell-Governance | Spätere nachvollziehbare Evidence und getrennte Modellversionen | Kein automatischer Lesson-/Hypothesen-/Approval-/Aktivierungswrite. |

Die bestehende Forschung in Draft-PR #197 hat einen eigenen Datenzeitraum und
einen eigenen Regelstand. Ihr Code kann separat geprüft werden. Historische
Erfolgskommentare ersetzen keine heute verfügbaren Rohdatenartefakte. Der
bestätigte Monitoring-Baselinevertrag und der alte Pilot bleiben ebenfalls
getrennte Modellstände.

## Prüfplan und tatsächliche Ausführung

| Prüfung am aktuellen Code-/Teststand | Tatsächliches Ergebnis |
|---|---|
| Neue synthetische Domain-/Parser-/Anwendungs-/CLI-Fälle | 60 bestanden; 98 % Statement-Abdeckung der vier neuen Module. |
| Dokumentierter CLI-Aufruf in isoliertem Subprozess | Mit `-I/-S`, leerer Umgebung und Auditblock gegen operative Imports und Netzwerkzugriffe bestanden. |
| Vollständiges Ruff-/Black-/strict-mypy-Gate | Bestanden; Black 1.050 Dateien, mypy 584 Quelldateien. Konfiguration unverändert. |
| Erster vollständiger lokaler Backendversuch | **Nicht bestanden:** 3.926 bestanden, 27 fehlgeschlagen, 199 regulär übersprungen, 64 Setupfehler; 84,53 % Gesamtcoverage unter unveränderten 85 %. |
| Enger Wiederlauf aller 27 fehlgeschlagenen Unitfälle | 27 bestanden nach Korrektur ausschließlich der lokalen Testumgebung; keine Quellcode-/Test-/Gateänderung. |
| Privater vollständiger Quellenlauf | 222 eindeutige Fälle, 164 Basiswert- und 222 Produktbedarfsgruppen; 2.220 Kursfelder unverändert, alle Ergebnisstatus `NOT_COMPUTED`. Originaldatei tatsächlich separat gehasht. Keine privaten Tabellen in Git/CI. |
| Unabhängige statische Review des neuen Offline-Schnitts | Kein blockierender Befund; Scope und Outputintegrität bestätigt. |

Der erste Gesamtversuch benutzte wegen des Sandbox-Temp-Fallbacks einen Ordner
innerhalb des Checkouts. 25 bestehende Launcher-/Migrationtests verweigerten
deshalb richtigerweise dort angelegte private Testzustände. Der Wiederlauf
verwendet einen expliziten `--basetemp` außerhalb aller Git-Checkouts. Zwei
HTTPX-Konstruktionstests scheiterten an der geerbten SOCKS-Proxykonfiguration
ohne optionale SOCKS-Unterstützung. Ausschließlich in der isolierten lokalen
virtuellen Testumgebung wurde `socksio==1.0.0` ergänzt; die Proxykonfiguration
und die Repository-Abhängigkeiten bleiben unverändert. Es fand kein Live-
Providerabruf statt. Alle 27 zuvor fehlgeschlagenen Unitfälle bestanden danach.

Alle 64 Setupfehler melden fehlende Testdatenbankkonfiguration, bevor eine
Verbindung aufgebaut wird. Lokal sind weder Docker noch PostgreSQL verfügbar.
Die reguläre Backend-CI stellt PostgreSQL 17 bereit und führt die Migrationen
und vollständigen Tests mit dem unveränderten 85-%-Gate aus. Dieser native
Gesamtnachweis muss am aktuellen PR-Head separat gelesen werden. Der enge
Wiederlauf macht den ersten fehlgeschlagenen Gesamtversuch nicht nachträglich
grün; Teilmengen werden nicht zu einer Gesamtgatezahl addiert.

Die neuen Tests prüfen deterministische Bytes, vollständige Sollanzahl,
Dubletten, getrennte Preisachsen, Quellenfingerprints, Maturitätskonflikte,
Turbo-Bedarf, ungültige Preise/Datentypen und den Schutz vorhandener Ausgaben.
Frontend, operative Datenbank und Provideradapter wurden nicht verändert.
Es gibt keinen Zielinstallations-, Release- oder vollständigen Renditenachweis.

## Verbleibende fachliche Arbeit

Historische Produktidentitäten, Emittentenbedingungen, Bid-/Ask-Historien,
Unternehmensereignisse und Handelskalender sind eigenständige Datenabhängigkeiten.
Der alte USD-Aktienpilot ist weder ein Mehrwährungs- noch ein Derivatesimulator.
Eine vollständige Studie muss daher ihre Ausführungs-, Kosten-, Zeit- und
Produkt-Lifecycle-Regeln festhalten und vorhandene Ergebniskenntnis offenlegen.
Diese Vorbereitung liefert dafür die vollständige Population und einen
prüfbaren Datenbedarf, aber keine Freigabe eines gewinnbringenden Modells.
