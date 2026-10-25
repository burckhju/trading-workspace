# Product Backlog

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Revision | Konsolidierung 2026-10-13; zur fachlichen Prüfung |
| Quellenstand | `main` / `a78288ad38610656480d0363abe657b567c7ba94` / Softwaretag `v1.5.5` |
| Funktion | Einzige maßgebliche Quelle des aktuellen Arbeitsstatus |
| Prüfgrenze | Statische Quellen- und CI-Prüfung; kein vollständiger lokaler Checkout, keine neue Fach- oder Liveabnahme |

> Fortschreibung 17.10.2026 auf `e9aac2bfaadeb9133a6ed07e42d1dec39836b156` / 1.5.8: Vollständiger Checkout für PB-017 Brutto-PnL und PB-019 Performance geprüft; [Quellenvertrag und V1-Entscheidungsvorschlag](../implementation/PERIOD_REALIZED_GROSS_READINESS.md) und [Owner-Trace-Qualifikation](../implementation/PERIOD_REALIZED_GROSS_QUALIFICATION.md). Die darunter erhaltene Konsolidierungsbasis beschreibt ihren damaligen Prüfstand. Die anschließende Nutzeranweisung „Ok, umsetzen“ gibt den konkreten Währungs-/Periodenvertrag zur Umsetzung frei ([ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)); die [Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) dokumentiert die Fortsetzung. Nur ausdrücklich ergänzte Teilfähigkeiten werden fortgeschrieben; keine fertige Fachabnahme, Veröffentlichung oder PC-Abnahme.

> Fortschreibung 18.10.2026: Der Nutzer hat mit „wenn prüfungen grün mergen und für den pc verfügbar machen“ die geschützte Integration und PC-Bereitstellung des konkret gelieferten Schnitts ausdrücklich autorisiert. [Version 1.5.9 und Updateweg](../releases/V1.5.9-REALIZED-GROSS-REPORT.md) verbinden diese Freigabe mit erneuter aktueller PR-/main-CI, dem getrennt vorgezogenen Integritätsfix #249 und dem tatsächlich veröffentlichten Tag. Die Aussagen vom 17.10. über fehlende Veröffentlichungsfreigabe sind damit historisch; eine PC-Installation oder vollständige M8-Abnahme wird weiterhin nicht behauptet.

## Pflegevertrag und Statusbedeutung

Nur die **Arbeitsstatus-Felder der Teilfähigkeiten** unten sind maßgeblich. PB-001 bis PB-020 bleiben erhalten; ihre Überschriften sind Container, keine zweite aggregierte Statusliste. Die unnummerierten Fähigkeiten bleiben unnummeriert. Beschreibende HTML-Anker sind lediglich Sprungziele innerhalb dieses Dokuments, keine neuen FT-/PB-IDs. Die Originalzuordnung und die Sichten sind statusfreie Ansichten auf dieselben Einträge.

Das vorhandene Feature-Lifecycle-Modell bleibt maßgeblich:
`Idea → Analysis → Specified → Approved for Build → In Development → Technical Review → Business Review → Accepted → Released → Observed`.
Hier bedeutet **Analysis** eine offene Umfangs-/Nachweisklärung, nicht automatisch „kein Code“. **Technical Review** bezeichnet den aktuellen Nachweisabgleich vorhandener Teilfähigkeiten, nicht deren erneute Implementierung oder den Widerruf historischer Freigaben. Historische `Done`, `Accepted`, `Released` und RC-Aussagen bleiben mit Quelle getrennt aufgeführt; sie werden weder rückwirkend erweitert noch durch neue, unbelegte Abnahmen ersetzt. Implementierung, erfolgreicher Test, fachliche Abnahme, Software-Auslieferung und beobachteter Betrieb sind verschiedene Nachweise.

Für jeden Beleg gilt der oben genannte Basiscommit, sofern explizit ein historischer Commit genannt ist. **Nicht verifiziert** ist weder „nachweislich fehlend“ noch „erledigt“. Ein Router beweist Anbindung, kein vollständiges Benutzerergebnis. Ein Verzeichnis, leeres Legacy-Paket oder eine unvollständige Codesuche beweist weder Funktion noch Abwesenheit. Breite Ausgangseinträge werden nur für den belegten Teil eingeordnet. Keine Fertigstellungsprozente werden abgeleitet.

## Orientierung und Priorisierung

Die [acht dauerhaften Planungssichten und drei Querschnittsthemen](MODULE_AND_FEATURE_CATALOG.md#planungssichten) sind keine neuen Paketgrenzen. Die [Lieferziele A–D](../foundation/ROADMAP.md#lieferziele) sind keine starre Reihenfolge. Fokus ist **B: Abschluss/Journal/Lernen** und **C: belastbare Performance**; belegte akute Daten- oder Betriebssicherheitsprobleme in A dürfen vorgezogen werden. D verwendet bestehende Kandidaten-Governance statt Neubau. Governance und Betrieb begleiten alle Ziele.

Die bisherigen Prioritätsklassen P0–P3 bleiben verwendbar; P0 steht für zwingende Voraussetzungen/Sicherheit, P1 für den nächsten umsetzbaren Nutzen. Die explizit markierten B-/C-Reste erhalten P1 als Planungsfokus; das behauptet keine erfüllte Definition of Ready. Es gibt keine neue durchnummerierte Feature- oder Sprintfolge.

<a id="originalzuordnung"></a>
## Originalzuordnung M0–M11

Vergleichsbasis ist die [unveränderte Roadmap vom 2026-07-22](../foundation/archive/ROADMAP_2026-07-22.md). Die folgenden **63 Inhaltsziel-Vorkommen** werden wortgetreu referenziert; dies ist eine Aussage über Rückverfolgbarkeit, nicht über Produktfertigstellung. Gleichartige ursprüngliche Vorkommen (Scanner, Produktscore) verweisen auf denselben Eintrag. Die Meilenstein-Ziel-/Ergebnisformulierungen bleiben zusätzlich in der Baseline erhalten; weder historische Versionsnamen noch heutige Tags erklären sie pauschal für erfüllt.

<a id="original-m0"></a>
### M0

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Repositorystruktur | [Repositorystruktur](#pb-004-repository) |
| Dokumentation | [Dokumentation und Spezifikationsführung](#pb-004-documentation) |
| Spezifikationen | [Projektweite Spezifikationen](#pb-004-specifications) |
| Terminologie | [Terminologie](#pb-004-terminology) |
| Architektur | [Fachliche Domain Map und Architektur](#pb-001-domain) |
| Entwicklungsstandards | [Entwicklungsstandards und Governance-Baselines](#pb-004-standards) |

<a id="original-m1"></a>
### M1

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Basiswerte | [Basiswerte, Listings und Identitäten im Backend](#pb-006-underlying) |
| Börsen | [Börsen und Handelsplätze](#pb-009-venues) |
| Emittenten | [Emittenten](#pb-010-issuers) |
| Instrumente | [Instrumente und Optionsscheine](#pb-011-warrants) |
| Optionsscheine | [Instrumente und Optionsscheine](#pb-011-warrants) |
| Datenprovider | [Datenprovider und benutzerverwaltete Konfiguration](#provider-configuration) |

<a id="original-m2"></a>
### M2

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Marktübersicht | [Marktübersicht](#pb-013-overview) |
| Scanner | [Scanner und Scanner-Modell](#pb-012-scanner) |
| Marktbreite | [Marktbreite](#pb-013-breadth) |
| Sektoren | [Sektoren und Referenzen](#pb-013-sectors) |
| Watchlist | [Watchlist](#pb-012-watchlist) |
| Kandidaten | [Kandidatenqualifikation](#pb-012-candidate) |

<a id="original-m3"></a>
### M3

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Analyse | [Reproduzierbare Analyse und Marktmodell](#pb-013-analysis) |
| Einstieg | [Einstieg planen](#pb-014-entry) |
| Stopstrategie | [Stopstrategie im TradePlan](#pb-014-stop) |
| Kursziele | [Kursziele im TradePlan](#pb-014-targets) |
| Risiko | [Risikoannahmen im TradePlan](#pb-014-risk) |
| Annahmen | [Annahmen, Freigabe und Herkunft des Plans](#pb-014-assumptions) |

<a id="original-m4"></a>
### M4

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Produktsuche | [Produktsuche und Suchuniversum](#pb-015-search) |
| Produktvergleich | [Produktvergleich und bewusste Auswahl](#pb-015-comparison) |
| Produktscore | [Produktscore und fachliche Modellfamilie](#pb-015-score) |
| Produktwechsel | [Produktwechsel](#pb-017-product-change) |

<a id="original-m5"></a>
### M5

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Trade eröffnen | [Trade eröffnen und tatsächliche Käufe erfassen](#pb-016-opening) |
| Depot | [Depot und abgeleitete offene Positionen](#pb-016-positions) |
| Stopmanagement | [Stop- und Zielmanagement](#pb-017-stop) |
| Teilverkauf | [Teilverkäufe](#pb-017-partial) |
| Trade schließen | [Vollverkauf und Abschluss](#pb-017-close) |
| Event-Historie | [Event-Historie und historische Korrekturen](#pb-017-history) |

<a id="original-m6"></a>
### M6

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Nachbeobachtung | [Zulässige Nachbeobachtung](#pb-018-observation) |
| Virtuelle Weiterführung | [Virtuelle Weiterführung](#pb-018-virtual) |
| Exit Review | [Exit Review und Handoff](#pb-018-review) |
| Vergleich tatsächlicher und virtueller Ausstiege | [Vergleich tatsächlicher und virtueller Ausstiege](#pb-018-exit-comparison) |

<a id="original-m7"></a>
### M7

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Journal | [Journalentwurf und Journalabschluss](#pb-019-journal) |
| Regelabweichungen | [Regelabweichungen dokumentieren](#pb-019-deviations) |
| Lessons Learned | [Belegte Lessons Learned](#pb-019-lessons) |
| Entscheidungsbewertung | [Entscheidungsbewertung getrennt vom Ergebnis](#pb-019-decision-quality) |

<a id="original-m8"></a>
### M8

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Performancekennzahlen | [Performancekennzahlen](#pb-019-performance-metrics) |
| Statistiken | [Tradeübergreifende Statistiken](#pb-019-performance-statistics) |
| Dashboards | [Performance-Dashboards](#pb-019-performance-dashboards) |
| Auswertungen | [Perioden- und Tradeauswertungen](#pb-019-performance-evaluations) |

<a id="original-m9"></a>
### M9

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Marktmodell | [Reproduzierbare Analyse und Marktmodell](#pb-013-analysis) |
| Scanner | [Scanner und Scanner-Modell](#pb-012-scanner) |
| Stopmodell | [Stopmodell](#pb-020-stop-model) |
| Zielmodell | [Zielmodell](#pb-020-target-model) |
| Produktscore | [Produktscore und fachliche Modellfamilie](#pb-015-score) |
| Trade Assistant | [Trade Assistant](#pb-020-assistant) |
| Nachbeobachtungsmodell | [Nachbeobachtungsmodell](#pb-020-observation-model) |

<a id="original-m10"></a>
### M10

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Erinnerungen | [Erinnerungen](#reminders) |
| Benachrichtigungen | [Benachrichtigungen und Zustellzustände](#notification-delivery) |
| Regelüberwachung | [Regelüberwachung und fachliche Alerts](#monitoring-rules) |
| Datenaktualisierung | [Datenaktualisierung und Schedulerzustände](#market-data-refresh) |
| Modellüberwachung | [Modellüberwachung](#model-monitoring) |

<a id="original-m11"></a>
### M11

| Ursprüngliches Inhaltsziel | Maßgebliche Teilfähigkeit |
|---|---|
| Performanceoptimierung | [Performanceoptimierung](#operations-optimization) |
| Stabilität | [Stabilität und sichere Betriebsgrenzen](#operations-stability) |
| Regressionstests | [Regressionstests](#operations-regression) |
| Dokumentationsreview | [Dokumentation und Spezifikationsführung](#pb-004-documentation) |
| Releasevorbereitung | [Releasevorbereitung und Softwarestand](#operations-release) |

<a id="nachweisregister"></a>
## Nachweisregister und erreichbare Prüfungen

Alle unten verlinkten Quellbelege sind auf den Basiscommit gepinnt. Historische Dateien können frühere Commitstände beschreiben; deren Zahlen und Freigaben sind keine heutigen Vollnachweise.

| Aktueller Basisnachweis | Erreichbares Ergebnis | Aussagegrenze |
|---|---|---|
| [Backend Run 38433996217](https://github.com/burckhju/trading-workspace/actions/runs/38433996217) | 2026-10-13, success; quality inkl. Ruff, Black, mypy, PostgreSQL-Migration, Tests/Coverage; restrictive-umask image; issuer renderer sandbox/isolierte Migrations- und Compose-Prüfung | Run-/Job-/Step-Ergebnisse gelesen; Rohlogs, Assertions und komplette Testreports nicht vollständig geprüft |
| [Frontend Run 38433996560](https://github.com/burckhju/trading-workspace/actions/runs/38433996560) | 2026-10-13, success; TypeScript, ESLint, Prettier, Unit/Coverage, Build | Kein lokaler neuer Lauf und keine menschliche Benutzerabnahme |
| [End-to-End Run 38433996404](https://github.com/burckhju/trading-workspace/actions/runs/38433996404) | 2026-10-13, success; Stackstart, Migration der Wegwerfdatenbank und Playwright smoke erfolgreich; fehlerabhängige Container-Log-Schritte skipped | Kein Liveprovider-/JMBbot-Nachweis; kein Beleg jedes ursprünglich versprochenen Features |
| [Git-Tag v1.5.5](https://github.com/burckhju/trading-workspace/tree/v1.5.5) | Ref zeigt auf a78288ad38610656480d0363abe657b567c7ba94; VERSION und Backend-/Frontend-Manifeste nennen 1.5.5 | Software-Auslieferung ist nicht Installation; vollständige Lock-/Versionsdateikonsistenz nicht erneut geprüft |

Die dokumentierten 2.567/445/48 Tests der Release-Notiz betreffen deren Nachweisstand und werden hier nicht als eigenständig nachgezählte Ergebnisse ausgegeben. Ebenso bleiben ältere 839-/274-/89-Testzahlen historische Belege.

**Zielinstallation:** JMBbot ist durch die 1.5.5-Release-Notiz identifiziert. Ihr dort genannter früher bestätigter PC-Stand ist v1.5.4 / `ab4730885b91fd954f3494434ff3d1f4734397db`. Aktuell installierte Revision, Schema, Compose-Kette, Providerrechte, Datenhistorie, reale Regeln und Zustellung wurden hier nicht beobachtet. Der in Release-Dokumenten genannte Schema-Head `20261012_0045` ist ein Dokument-/CI-Kontext, kein hier ausgeführtes `alembic heads/current` auf JMBbot.

**Nicht lokal ausgeführt:** `bash scripts/check-backend.sh`, `bash scripts/check-frontend.sh`, `bash scripts/run-e2e.sh`, gezielte Anwendungs-/DB-/Browserprüfungen. Ursache: nur eine hashgeprüfte Dokument-Arbeitskopie, kein vollständiger Checkout bzw. identifizierter lokaler Anwendungs-Teststack. Die drei Skripte wurden gelesen. Insbesondere löscht der E2E-Cleanup seine Testvolumes; er wurde nicht gegen unbekannte Ressourcen gestartet. Keine Provideraufrufe, echten Nachrichten oder Nutzerbestandsänderungen.

**Quellenzugriffsgrenzen:** Git-Klon/Archivzugriff im lokalen Laufzeitraum nicht verfügbar; GitHub-Datei-/Tree-/CI-Lesezugriff verfügbar. Code-Suche lieferte unvollständige Ergebnisse und wurde nicht als Abwesenheitsbeleg genutzt. Root/docs/foundation/docs/planning wurden auf anwendbare Anweisungsdateien geprüft; keine dortige AGENTS.md gefunden. Kein Zugriff auf nicht veröffentlichte Nutzer-Arbeitsbäume. Nicht sämtliche ADR-Volltexte, Feature Books, Backendservices, Migrationen, Lockdateien, Workflowdefinitionen, CI-Rohlogs und historischen Abnahmedokumente wurden vollständig neu geprüft. Diese Grenzen sind kein Grund, belegte Funktionen als Not Started zu führen.

<a id="konfliktaufloesung"></a>
## Statusdrift und Auflösung

| Konflikt am Basisstand | Geltende Einordnung und maßgeblicher Eintrag |
|---|---|
| Alte Sammelstatus PB-017–PB-020: Not Started, obwohl spätere Anbindungen/Nachweise vorhanden | Keine pauschale Freigabe; vorhandene Teilfähigkeiten einzeln unter PB-017–PB-020 mit Code-/Consumerbelegen führen |
| Alter FT-007-Hinweis Architecture Review Pending versus historische Traceability Accepted / PB-014 Released | Alten nächsten Sprintschritt nicht weiterführen; vorhandene Planfähigkeit erhalten, konkrete aktuelle Nachweise getrennt |
| Golden-Path-Closeout: Materialisierung/Runtime-Aktivierung offen | Extension 09, PostTradeLearningPage und RuntimeActivationService schließen spätere Teile; ursprüngliche Aussage bleibt historischer Stand |
| FT-013 V1: kein Aktivierungsendpoint; spätere FT-020-Strecke verlangt getrennte Aktivierung | V1-Nicht-Soll nicht als heutige Infrastruktur-Lücke verallgemeinern; Modellfamilien weiterhin separat prüfen |
| Alter Katalog nennt Produktwechsel; FT-010 V1 schließt ihn ausdrücklich aus | M4-Anspruch bleibt unter Produktwechsel offen; keine dauerhafte Verschiebung/Entfernung ohne Entscheidung |
| STOCK-only in alten Baselines; FT-006-/Chart-Nachtrag vom 2026-10-04 erlaubt ETF-Stammdaten | Historische Regel nur für ihren Umfang; aktuelle ETF-Stammdaten berücksichtigen, Indizes bleiben semantische Referenzen ohne erfundene Listings |
| Alter S8-Selektionshinweis versus begründeter NOT_EVALUABLE-Ausnahmeweg im aktuellen Domainvertrag | Ausnahme nicht als bestätigte Eignung darstellen; tatsächlichen aktuellen API-/UI-Vertrag vor fachlicher Behauptung prüfen |
| Alter Monitoringtext: unbedingte Underlying-Preisbasis | FT-010-Nachtrag 2026-09-14 verlangt explizite Instrument-/Währungsbindung; Legacy-ungebundene Regeln nicht als gültig behaupten |
| Alte README-Version/Checklisten versus aktuelle Manifeste/Tag | README führt zu VERSION, Release-Notiz und diesem Backlog; keine zweite vollständige Statusliste |
| Softwaretag 1.5.5 versus historisch genannter PC-Stand 1.5.4 | Aktueller JMBbot-Betriebsbeleg fehlt; kein erfundener Installationsstatus |

Offene PRs werden nicht dem Basiscommit zugerechnet: #249 Formularintegrität, #235/#225 Scheduler, #90 Learning-Navigation und die bereits gelesenen weiteren offenen Recherche-/Regel-/Historienentwürfe (#220/#207/#205/#204/#197/#187). Sie sind fremde/offene Änderungen; kein Merge, keine Übernahme und keine daraus abgeleitete neue Freigabe in diesem Auftrag.

<a id="abnahmematrix"></a>
## Abnahmematrix – maßgebliche Teilfähigkeiten

Die Felder „Soll“ und „Nicht-Soll“ sind die vor einer Umsetzung zu prüfenden Abnahmegrenzen. Fachliche Entscheidungen fehlen nur für die jeweils betroffenen Reste; unabhängige freigegebene Arbeit bleibt möglich. „Abnahme nicht verifiziert“ entwertet keinen früheren Beleg, sondern begrenzt diese Prüfung. Bereichsziffern beziehen sich auf den Katalog. Lieferzielbuchstaben beziehen sich auf die Roadmap.

### PB-001

[Fachliche Domain Map und Architektur](#pb-001-domain)

<a id="pb-001-domain"></a>
<details>
<summary>PB-001 — Fachliche Domain Map und Architektur</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Architektur. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Accepted (historische Dokumentbaseline) |
| Soll / Nicht-Soll | **Soll:** Kernobjekte, Schichten, Beziehungen und ein schreibender Owner je Objekt sind nachvollziehbar. **Nicht-Soll:** Keine Neuaufteilung der Pakete durch die acht Planungssichten. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [docs/domain/DOMAIN_MAP.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/domain/DOMAIN_MAP.md) und [docs/foundation/ARCHITECTURE.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/ARCHITECTURE.md) gelesen; tatsächliche Anbindung über [API-Komposition](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [UI-Router](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx). |
| Test / Commit | Quellenprüfung am Basiscommit; kein ausführbarer Test für die Dokumentfreigabe. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | DOMAIN_MAP Version 1.0 trägt Approved / 2026-08-03; keine neue Abnahme erteilt. |
| Software-Auslieferung | Nicht anwendbar: Dokumentbaseline. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Historische STOCK-only- und Prozessformulierungen gegen spätere Präzisierungen lesen, nicht pauschal als aktuellen Vertrag übernehmen. **Nächste Abhängigkeit:** PB-004: spätere Dokumentnachträge und Freigabegrenzen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-002

[Durchgängiger Prozess und Übergaben](#pb-002-process)

<a id="pb-002-process"></a>
<details>
<summary>PB-002 — Durchgängiger Prozess und Übergaben</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Spezifikationen; übergreifend M2–M9. Bereich/Querschnitt: Querschnitt: durchgängiger Arbeitsablauf/Bedienbarkeit. Bestehender Bezug: FT-005–FT-013. Lieferziel: B, D. |
| Arbeitsstatus | Accepted (historische Prozessbaseline) |
| Soll / Nicht-Soll | **Soll:** Explizite Übergaben, konkrete historische Versionen und Korrekturen verbinden den Gesamtprozess. **Nicht-Soll:** Kein automatischer Handels- oder Interpretations-Orchestrator; kein Journalentwurf-Gate durch Performance. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [docs/domain/TRADING_PROCESS_MODEL.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/domain/TRADING_PROCESS_MODEL.md) und [Golden-Path-Abschluss](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md) beschreiben Prozess bzw. benachbarte Integrationsstrecken; [Post-Trade-Consumer](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx) ergänzt spätere UI-Übergaben. |
| Test / Commit | Golden-Path-Nachweise sind historische, zusammengesetzte Integrationsnachweise; kein vollständiger neuer Browserlauf dieser Prüfung. CI-Basis siehe Nachweisregister. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | TRADING_PROCESS_MODEL Version 1.0 trägt Approved / 2026-08-03; vollständige aktuelle Nutzerstrecke nicht neu abgenommen. |
| Software-Auslieferung | Nicht anwendbar für die Prozessbeschreibung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Journalübergang und historische Korrekturen als eigene Restanforderungen prüfen; alte Prozessgrafik nicht als Laufzeitabhängigkeit auslegen. **Nächste Abhängigkeit:** PB-019: Journal; PB-018: Currentness; PB-020: konkrete Modellanwendung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-003

[Benutzer- und Workspace-Grenze](#pb-003-workspace)

<a id="pb-003-workspace"></a>
<details>
<summary>PB-003 — Benutzer- und Workspace-Grenze</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Architektur. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-001; alle workspacegebundenen Consumer. Lieferziel: A–D. |
| Arbeitsstatus | Accepted (historischer PB-003-Beleg) |
| Soll / Nicht-Soll | **Soll:** Bestehender unsichtbarer Workspace und Identitätsgrenzen bleiben erhalten. **Nicht-Soll:** Keine Multiuser-Erweiterung; Audit-Actor ist kein Authentifizierungsbeleg. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [docs/domain/DOMAIN_MAP.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/domain/DOMAIN_MAP.md) und [historische Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md) referenzieren ADR-S1-004 / ADR-S2-001 und serverseitige Workspace-Auflösung. |
| Test / Commit | Historische Persistenz-/Servicebelege in Traceability; aktuelle Authentifizierung nicht geprüft. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Der bisherige PB-003 ist Accepted; Beleg bleibt historisch und wird nicht erweitert. |
| Software-Auslieferung | Nicht anwendbar: Architekturentscheidung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Keine neue Architekturänderung; aktuelle Nachweise nur im jeweils betroffenen Consumer ergänzen. **Nächste Abhängigkeit:** Bestehende Workspace-Contracts. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-004

[Repositorystruktur](#pb-004-repository) · [Dokumentation und Spezifikationsführung](#pb-004-documentation) · [Terminologie](#pb-004-terminology) · [Entwicklungsstandards und Governance-Baselines](#pb-004-standards) · [Projektweite Spezifikationen](#pb-004-specifications)

<a id="pb-004-repository"></a>
<details>
<summary>PB-004 — Repositorystruktur</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Repositorystruktur. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Quell- und Dokumentstruktur sind nachvollziehbar, Aufgabenänderungen isoliert. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | Repository-Wurzel sowie docs/foundation, docs/planning und Router am Basiscommit gelesen; [Entwicklungsanleitung](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/technical/DEVELOPMENT_GUIDE.md). |
| Test / Commit | Dokument-/Strukturprüfung am Basiscommit; keine neue fachliche Abnahme. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Dokumentationsarbeit, kein Software-Release. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Vollständiger Git-Checkout und nicht veröffentlichte Nutzeränderungen hier nicht zugänglich. **Nächste Abhängigkeit:** Vollständiger Checkout vor Integration dieses Diffs. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-documentation"></a>
<details>
<summary>PB-004 — Dokumentation und Spezifikationsführung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Dokumentation; M11: Dokumentationsreview. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Eine aktuelle Statusquelle; Baseline, Entscheidungen und Nachweise sind verknüpft. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | Fünf Planungsdokumente gegen ihre Git-Blob-Hashes geprüft; historische Nachweise aus [historische Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md). |
| Test / Commit | Dokument-/Strukturprüfung am Basiscommit; keine neue fachliche Abnahme. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Dokumentationsarbeit, kein Software-Release. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Neue Dokumentrevision fachlich reviewen; historische Freigaben nicht auf neuen Umfang übertragen. **Nächste Abhängigkeit:** Review der konsolidierten Zuordnung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-terminology"></a>
<details>
<summary>PB-004 — Terminologie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Terminologie. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Begriffe trennen Fakten, Plan, Bewertung und Beobachtung. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | PROJECT, DOMAIN_MAP und tatsächlich gelesene Execution-/Learning-Verträge bilden den geprüften Begriffskontext. |
| Test / Commit | Dokument-/Strukturprüfung am Basiscommit; keine neue fachliche Abnahme. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Dokumentationsarbeit, kein Software-Release. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | GLOSSARY-Inhalt nicht eigenständig verifiziert; vollständigen Terminologieabgleich nachführen. **Nächste Abhängigkeit:** GLOSSARY und betroffene freigegebene Verträge. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-standards"></a>
<details>
<summary>PB-004 — Entwicklungsstandards und Governance-Baselines</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Entwicklungsstandards. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: kein eigener FT-Bezug. Lieferziel: A–D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Definition of Ready, getrennte Prüf-/Abnahmeschritte und Modellfreigaben sind verbindlich. **Nicht-Soll:** Keine Fachlogik- oder Laufzeitänderung. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [docs/technical/DEVELOPMENT_GUIDE.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/technical/DEVELOPMENT_GUIDE.md) gelesen; [docs/technical/FEATURE_LIFECYCLE.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/technical/FEATURE_LIFECYCLE.md) bis Lebenszyklus; [docs/foundation/MODEL_BOOK.md](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/MODEL_BOOK.md) weiterhin mit Review-Metadaten. |
| Test / Commit | Dokument-/Strukturprüfung am Basiscommit; keine neue fachliche Abnahme. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Dokumentationsarbeit, kein Software-Release. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Freigaben von REQUIREMENTS, MODEL_BOOK und FEATURE_LIFECYCLE einzeln belegen; keine pauschale Freigabe behaupten. **Nächste Abhängigkeit:** Product-Owner-/Modellverantwortlichen-Entscheidung je Dokument. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-004-specifications"></a>
<details>
<summary>PB-004 — Projektweite Spezifikationen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Spezifikationen. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: bestehende FT-001–FT-013 und spätere belegte Erweiterungen. Lieferziel: A–D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Originalziele haben testbare Verträge mit Soll, Nicht-Soll und Entscheidungskette. **Nicht-Soll:** Ein enger V1-Vertrag entfernt nicht automatisch den weiteren Roadmapanspruch. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | Foundation, Domain Map, Prozessmodell, gelesene FT-006/010/013/020-Verträge und [historische Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md) bilden die geprüfte Teilmenge. |
| Test / Commit | Statische Quellenprüfung; nicht sämtliche Feature Books und ADR-Volltexte erneut geprüft. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Nicht anwendbar für die Spezifikationsprüfung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Nicht gelesene Vertragsdetails gezielt am jeweils nächsten Umsetzungsschnitt prüfen. **Nächste Abhängigkeit:** Die in den Einzelanforderungen benannten offenen Umfangsentscheidungen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-005

[FT-001 Feature Book](#pb-005-spec)

<a id="pb-005-spec"></a>
<details>
<summary>PB-005 — FT-001 Feature Book</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M0: Spezifikationen; M1: Basiswerte. Bereich/Querschnitt: 1; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Approved for Build (historische FT-001-Baseline) |
| Soll / Nicht-Soll | **Soll:** Basiswert-/Listing-Vertrag und Regeln sind referenzierbar. **Nicht-Soll:** Keine Ableitung aktueller ETF-Grenzen allein aus der alten Aktienbaseline. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-001-Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md) referenziert U-R-001 bis U-R-021 und das Feature Book; [Nachtrag 2026-10-04](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-006_MARKET_ANALYSIS.md) erweitert Stammdaten auf ETF. |
| Test / Commit | Historische Spec-/Implementierungskette vorhanden; Feature Book nicht vollständig erneut gelesen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Bisheriger PB-005: Approved for Build; keine erneute oder weitergehende Freigabe. |
| Software-Auslieferung | Nicht anwendbar für die Spezifikation. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | ETF-Ergänzung und alte Feature-Book-Aussagen im nächsten fachlichen Review ausdrücklich zuordnen. **Nächste Abhängigkeit:** PB-006: tatsächlicher Stammdatenconsumer; PB-013: Charts. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-006

[Basiswerte, Listings und Identitäten im Backend](#pb-006-underlying)

<a id="pb-006-underlying"></a>
<details>
<summary>PB-006 — Basiswerte, Listings und Identitäten im Backend</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Basiswerte. Bereich/Querschnitt: 1. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Stabile Basiswert-/Listing-Identität, Änderungs- und Löschschutz; aktuelle Instrumentgrenzen beachten. **Nicht-Soll:** Indexreferenzen nicht als synthetische Wertpapierlistings anlegen; keine stille SHORT-Erweiterung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Underlying-/Reference-Router registriert](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py); [FT-001 Domain/Service/Persistenzkette](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); ETF-Ergänzung laut [Chart-Implementierungsbericht](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/MARKET_CHARTS.md). |
| Test / Commit | Historische FT-001-Tests in Traceability; aktueller Gesamt-CI-Lauf, aber Detailverträge hier nicht vollständig neu getestet. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Historischer PB-006 meldete Done; spezifischer aktueller Fachabnahmebeleg nicht neu ermittelt. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Aktuelle Stammdaten-/ETF-Regressionsfälle gezielt nachlesen; offene Formular-PR #249 nicht als main-Implementierung zählen. **Nächste Abhängigkeit:** Bestehende FT-001-Contracts; PB-009: Venue. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-007

[Basiswertverwaltung in der Oberfläche](#pb-007-underlying-ui)

<a id="pb-007-underlying-ui"></a>
<details>
<summary>PB-007 — Basiswertverwaltung in der Oberfläche</summary>

**A: Navigation — Nachweisfortschreibung 2026-10-25:** Der bestehende
[PR #204](https://github.com/burckhju/trading-workspace/pull/204) integriert Main
`fbd77fb94947a1fdbfc0aeb90811353fae655a59` / v1.5.14 konfliktfrei und erhält seine
veröffentlichte Historie. Die vorhandene URL-Navigation und der Formularschutz
bleiben unverändert; ergänzt werden gezielte Testverträge und aktuelle
Nachweise. Die [Navigationsqualifikation](../implementation/UNDERLYING_NAVIGATION_QUALIFICATION.md)
bindet A01–A14, die ausführbaren Quelltrees, 122 fokussierte Tests,
780 vollständige Frontendtests sowie 24 synthetische Browserfälle ohne Retry.
Die vollständigen aktuellen CI-Ergebnisse einschließlich beider Finanz- und
beider Lern-Ownerfälle werden im PR an den tatsächlichen Checkout/Tree gebunden.
Historische v1.5.11-Erfolge sind kein neuer Integrationsnachweis. Main-Merge,
Veröffentlichung, menschliche Abnahme und PC-Betrieb werden nicht vorweggenommen;
der neue Candidate-Governance-Auftrag B bleibt unberührt.

**Nachweisfortschreibung 2026-10-20:** Der ursprüngliche Formularschutz aus
[PR #249](https://github.com/burckhju/trading-workspace/pull/249) wurde am
18.10.2026 gemergt. Die Folgekorrektur auf Basis von
`254fe35b76027b72cd989715e17bd0ae55af55eb` behandelt zwei verbliebene Randfälle:
gleichwertige Querykodierungen dürfen bewusst bearbeitete Eingaben derselben
Formularinstanz nicht durch erneutes Laden überschreiben; alte Speicherantworten
dürfen bereits nach dem Commit der Zielansicht nicht mehr navigieren. Dazu gehören
ein stabiler Querysnapshot je Formularinstanz und eine Aktivitätsbereinigung in
der Layout-Phase, getrennt vom weiterhin passiven Ladeeffekt.

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Basiswerte. Bereich/Querschnitt: 1; Querschnitt: durchgängiger Arbeitsablauf/Bedienbarkeit. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Suchen, anlegen, ändern und deaktivieren über denselben fachlichen Owner. **Nicht-Soll:** Kein konkurrierender Stammdatenbestand in UI oder Workspace. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [UnderlyingFormPage](../../frontend/src/features/market/pages/UnderlyingFormPage.tsx) und [Formularvertrag](../features/underlying/FEATURE.md#sicheres-formular-bei-navigation-und-ladefehlern); ursprüngliche [Underlying-Routen](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx) sowie historische UI-Verträge und Tests in [historischer Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md). |
| Test / Commit | [Unit-Regressionen](../../frontend/src/features/market/pages/UnderlyingFormIsolation.test.tsx) und [Browserregressionen](../../tests/e2e/underlying-form-isolation.spec.ts) sichern Formularidentität, Lade-/Speicherreihenfolge, Eingabenerhalt und Doppelübermittlung einschließlich der beiden Randfälle. Exakter Prüfhead, tatsächlich ausgeführte Ergebnisse, Browserartefakte und CI-Läufe werden im zugehörigen Folge-PR zugeordnet; frühere Läufe von #249 sind kein Nachweis für die Ergänzung. |
| Fachliche Abnahme | Historischer PB-007: Done; aktuelle vollständige Benutzerabnahme nicht neu geprüft. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Folgekorrektur mit den unveränderten Gates und auf dem zugehörigen Prüfhead reviewen; keine Mergefreigabe aus dem Arbeitsauftrag ableiten. [PR #204](https://github.com/burckhju/trading-workspace/pull/204) bleibt als offener Draft für Listen-Rückkehrnavigation separat: Überschneidung in Formular und Feature-Dokument, eigener dokumentierter [Fixture-/CI-Befund](https://github.com/burckhju/trading-workspace/pull/204#issuecomment-5654574060). Eine spätere Integration muss dessen Rückkehrziel mit dem Aktivitätsschutz verbinden und erneut qualifizieren. **Nächste Abhängigkeit:** PB-006; tatsächlicher PR-Mergestand vor Umsetzung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-008

[FT-001 Integration und Abnahme](#pb-008-underlying-acceptance)

<a id="pb-008-underlying-acceptance"></a>
<details>
<summary>PB-008 — FT-001 Integration und Abnahme</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Basiswerte. Bereich/Querschnitt: 1; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-001. Lieferziel: A. |
| Arbeitsstatus | Accepted (historischer PB-008-Abnahmekern) |
| Soll / Nicht-Soll | **Soll:** Integration und Abnahme haben einen datierten, versionsgenauen Beleg. **Nicht-Soll:** Ein grüner Lauf ersetzt keine menschliche Fachabnahme. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-001 Gesamttraceability und Sprint-2-Abschlussreferenzen](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md). |
| Test / Commit | Historische 89 Backend- und 18 Frontendtests sind alte Nachweise, nicht heutige Testzahlen; aktuelle CI getrennt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Bisheriger PB-008 meldete Integration und fachliche Abnahme abgeschlossen; referenzierte Abschlussdateien hier nicht vollständig neu gelesen. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Den vollständigen aktuellen Abnahmeumfang inklusive späterer Erweiterungen verifizieren. **Nächste Abhängigkeit:** PB-006/007; Review des historischen Abschlussdokuments. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-009

[Börsen und Handelsplätze](#pb-009-venues)

<a id="pb-009-venues"></a>
<details>
<summary>PB-009 — Börsen und Handelsplätze</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Börsen und Handelsplätze. Bereich/Querschnitt: 1. Bestehender Bezug: FT-002. Lieferziel: A. |
| Arbeitsstatus | Released (belegter historischer Teilscope) |
| Soll / Nicht-Soll | **Soll:** Providerneutrale, stabile Identität und Lifecycle; historische Referenzen bleiben gültig. **Nicht-Soll:** Stammdaten sind weder Kursquelle noch Produktscore oder Benutzerwahl. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | Reference-Data-Router registriert; historische Venue-Reconciliation, Listing-FK, Deaktivierungsschutz und Low-input-Consumer in Traceability. [historische Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md) |
| Test / Commit | Historische Vertrags-/API-/DB-Nachweise; aktuelle CI auf Basiscommit. Nicht jeder Einzeltest neu gelesen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Historische Sprint-7A-Release-Evidence: PR #8 / 7f39bc0; keine neue Fachabnahme. |
| Software-Auslieferung | Historisch Released; Quelle: bisheriger PB-009 und Sprint-7A-Traceability. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Spätere Erweiterungen und aktueller Betrieb separat qualifizieren; keine pauschale Vollständigkeit der ursprünglichen Planung ableiten. **Nächste Abhängigkeit:** FT-001 Listing-Consumer. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-010

[Emittenten](#pb-010-issuers)

<a id="pb-010-issuers"></a>
<details>
<summary>PB-010 — Emittenten</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Emittenten. Bereich/Querschnitt: 1. Bestehender Bezug: FT-003. Lieferziel: A. |
| Arbeitsstatus | Released (belegter historischer Teilscope) |
| Soll / Nicht-Soll | **Soll:** Providerneutrale, stabile Identität und Lifecycle; historische Referenzen bleiben gültig. **Nicht-Soll:** Stammdaten sind weder Kursquelle noch Produktscore oder Benutzerwahl. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | Reference-Data-Router registriert; globale Issuer-Identität und Warrant-Consumer historisch dokumentiert. [historische Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md) |
| Test / Commit | Historische Vertrags-/API-/DB-Nachweise; aktuelle CI auf Basiscommit. Nicht jeder Einzeltest neu gelesen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Historische RC-Notiz wird nicht rückwirkend umgeschrieben; späterer PB-010 nennt Released. |
| Software-Auslieferung | Historisch Released laut PB-010; eigenständigen Tag nicht neu geprüft. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Spätere Erweiterungen und aktueller Betrieb separat qualifizieren; keine pauschale Vollständigkeit der ursprünglichen Planung ableiten. **Nächste Abhängigkeit:** FT-004-Consumer, keine Ableitung aus dem Underlying-Unternehmen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-011

[Instrumente und Optionsscheine](#pb-011-warrants)

<a id="pb-011-warrants"></a>
<details>
<summary>PB-011 — Instrumente und Optionsscheine</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Instrumente; Optionsscheine. Bereich/Querschnitt: 1. Bestehender Bezug: FT-004. Lieferziel: A. |
| Arbeitsstatus | Released (belegter historischer Teilscope) |
| Soll / Nicht-Soll | **Soll:** Providerneutrale, stabile Identität und Lifecycle; historische Referenzen bleiben gültig. **Nicht-Soll:** Stammdaten sind weder Kursquelle noch Produktscore oder Benutzerwahl. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | Product-Router registriert; [FT-008 konsumiert konkrete Warrant-/Terms-/Listing-IDs](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/domain/models.py). [historische Traceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md) |
| Test / Commit | Historische Vertrags-/API-/DB-Nachweise; aktuelle CI auf Basiscommit. Nicht jeder Einzeltest neu gelesen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Historischer FT-004-Umfang laut PB-011 und Traceability; keine neue Gesamtfreigabe. |
| Software-Auslieferung | Historisch v0.9.0-warrants / PR #13 laut PB-011. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Spätere Erweiterungen und aktueller Betrieb separat qualifizieren; keine pauschale Vollständigkeit der ursprünglichen Planung ableiten. **Nächste Abhängigkeit:** PB-009/010 und FT-001; Produktbelege separat. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-012

[Watchlist](#pb-012-watchlist) · [Kandidatenqualifikation](#pb-012-candidate) · [Scanner und Scanner-Modell](#pb-012-scanner)

<a id="pb-012-watchlist"></a>
<details>
<summary>PB-012 — Watchlist</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Watchlist. Bereich/Querschnitt: 3. Bestehender Bezug: FT-005. Lieferziel: A. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Benutzerverwaltete Beobachtungsliste mit nachvollziehbarer Zugehörigkeit, unabhängig vom Qualifikationsergebnis. **Nicht-Soll:** Kandidatenliste ist kein Nachweis eines generischen Watchlist-Aggregats. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [UI-Router](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx) zeigt Kandidaten; [bisheriger PB-012](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/PRODUCT_BACKLOG.md) benennt Watchlist ausdrücklich als Rest. Keine vollständige Watchlist-Consumerkette in den gelesenen Quellen verifiziert. |
| Test / Commit | Kein separater Watchlist-Test-/Abnahmebeleg verifiziert; negative Codesuche war unvollständig und ist kein Abwesenheitsbeweis. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Vorhandene alternative Ownership ausschließen und Watchlist-Vertrag mit Nutzeraktionen abgrenzen. **Nächste Abhängigkeit:** FT-005-Spezifikation / Product-Owner-Entscheidung; keine Voraussetzung für manuellen TradePlan. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-012-candidate"></a>
<details>
<summary>PB-012 — Kandidatenqualifikation</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Kandidaten. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-005; FT-019/FT-020 als vorhandene Kandidaten-Erweiterungen. Lieferziel: A, D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Nachvollziehbare Top-down-Evaluation mit konkreter Analyse-/Modellversion und explizitem Handoff. **Nicht-Soll:** Kein aggregierter Candidate-Score und keine automatische Planfreigabe. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Candidate-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [Kandidaten-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx) registriert; [qualifizierte Candidate→TradePlan-Naht](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md) und [spätere governte Konfiguration](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md). |
| Test / Commit | Historische Domain-/Orchestrierungs-/Integrationsbelege in Traceability; CI-Basis erfolgreich. Runtime-Adapter hier nicht vollständig neu gelesen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Historische Sprint-5-Reviewreferenzen; keine neue globale FT-005-Abnahme. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Versionsgenaue Reproduzierbarkeit und Rückkehrfall mit konkretem Candidate-Consumer prüfen; keine neue Kandidatenstrecke bauen. **Nächste Abhängigkeit:** PB-020: bestehende Runtime-Aktivierung; PB-013: qualifizierte Analysen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-012-scanner"></a>
<details>
<summary>PB-012 — Scanner und Scanner-Modell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Scanner; M9: Scanner. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-005 / FT-006; FT-013 für Governance. Lieferziel: A, D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Der ursprüngliche Scanneranspruch bleibt als eigener Umfang mit explizitem Suchuniversum, Auslöser und Modellbezug sichtbar. **Nicht-Soll:** Einzelne Candidate-Evaluation oder eine Liste ist nicht automatisch ein vollständiger Scanner. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Analyse→Kandidaten-Strecke](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md) vorhanden; vollständige eigenständige Scanner-Consumer-/Modellfamilie in der geprüften Teilmenge nicht verifiziert. |
| Test / Commit | Kein eindeutig dem vollständigen Scanneranspruch zugeordneter Test-/Abnahmebeleg verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Umfang des Scanners gegenüber bestehender Qualifikation entscheiden; freigegebene vorhandene Orchestrierung wiederverwenden. **Nächste Abhängigkeit:** Bestehende FT-005/006-Verträge und konkrete Modellfamilienentscheidung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-013

[Marktübersicht](#pb-013-overview) · [Marktbreite](#pb-013-breadth) · [Sektoren und Referenzen](#pb-013-sectors) · [Reproduzierbare Analyse und Marktmodell](#pb-013-analysis)

<a id="pb-013-overview"></a>
<details>
<summary>PB-013 — Marktübersicht</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Marktübersicht. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Markt- und Datenzustände nachvollziehbar lesen. **Nicht-Soll:** Chartvergleich ist keine Depot-Performance. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Analyse-/Chart-Routen](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [lesender Markt-/Sektor-/Aktienvergleich](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/MARKET_CHARTS.md). |
| Test / Commit | Historische Vertrags-/Regressionsergebnisse in Analyse-/Chart-Berichten; aktuelle CI, kein neuer lokaler Lauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Sprint-4-RC im bisherigen PB-013 als fachlich abgenommen bezeichnet; neuere Erweiterung / kompletter M2-Umfang nicht mitabgenommen. |
| Software-Auslieferung | Charts laut Implementierungsbericht in 1.5.0 ausgeliefert; kein Beleg vollständiger M2/M9-Erfüllung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Den ursprünglichen Übersichtsanspruch gegen vorhandene Darstellung und Ziel-A-Aufgaben prüfen. **Nächste Abhängigkeit:** Qualifizierte TC-001-Daten; bestehende Referenz-/Analysecontracts. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-013-breadth"></a>
<details>
<summary>PB-013 — Marktbreite</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Marktbreite. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Marktbreite besitzt eine definierte Grundgesamtheit, Berechnung und Datenqualität. **Nicht-Soll:** Marktbenchmark, Sektormatrix oder Relative Strength allein belegt keine Marktbreite. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [FT-006 V1](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-006_MARKET_ANALYSIS.md) dokumentiert SMA, Momentum, Volatilität und Handelsspanne, aber keinen vollständigen Marktbreite-Nachweis. |
| Test / Commit | Historische Analyse-/Chart-Testnachweise; aktuelle Basis-CI. Marktbreite-spezifischer Nachweis fehlt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Sprint-4-RC im bisherigen PB-013 als fachlich abgenommen bezeichnet; neuere Erweiterung / kompletter M2-Umfang nicht mitabgenommen. |
| Software-Auslieferung | Historische Analyse-RC-/Golden-Path-Nachweise; kein pauschaler Gesamtstatus. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Definition/Universum/Verfügbarkeit entscheiden und tatsächlichen Consumer nachweisen. **Nächste Abhängigkeit:** Qualifizierte TC-001-Daten; bestehende Referenz-/Analysecontracts. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-013-sectors"></a>
<details>
<summary>PB-013 — Sektoren und Referenzen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2: Sektoren. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Administrierte Sektor-/Marktreferenzen und ihre Datenabdeckung bleiben erkennbar. **Nicht-Soll:** Keine erfundenen Index-Listings; ETF-Vorschläge sind keine zweite Stammdatenwahrheit. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [D01-Nachfolge und dynamische Sektormatrix](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/MARKET_CHARTS.md); Reference-/Chart-Router angebunden. |
| Test / Commit | Historische Vertrags-/Regressionsergebnisse in Analyse-/Chart-Berichten; aktuelle CI, kein neuer lokaler Lauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Sprint-4-RC im bisherigen PB-013 als fachlich abgenommen bezeichnet; neuere Erweiterung / kompletter M2-Umfang nicht mitabgenommen. |
| Software-Auslieferung | Charts laut Implementierungsbericht in 1.5.0 ausgeliefert; kein Beleg vollständiger M2/M9-Erfüllung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Aktuelle Zuordnungen, Providerrechte und echte Historien auf JMBbot getrennt prüfen. **Nächste Abhängigkeit:** Qualifizierte TC-001-Daten; bestehende Referenz-/Analysecontracts. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-013-analysis"></a>
<details>
<summary>PB-013 — Reproduzierbare Analyse und Marktmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Analyse; M9: Marktmodell. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006; FT-013 als Governance-Querschnitt. Lieferziel: A, D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Beschreibende Analyse speichert Eingaben, Parameter, Quellen und konkrete Modellversion. **Nicht-Soll:** Keine Handelsentscheidung; Charts erzeugen keine FT-006-Runs. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [EOD_TREND_MOMENTUM, Retry-/Verify-Vertrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-006_MARKET_ANALYSIS.md); [Analysis-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [Analysis-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx). **Fortsetzung #278, 25.10.2026:** Feste neue Runtime EOD_TREND_MOMENTUM/1.0.1 für beide Owner/HTTP-Routen, Originalwarnungen, exakte historische Retry-/Verify-Dispatches und nullable Referenzreadback; [aktueller Qualitätsnachweis](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md). Historischer Rechner und Daten bleiben unverändert. |
| Test / Commit | Historische Vertrags-/Regressionsergebnisse in Analyse-/Chart-Berichten; aktuelle CI, kein neuer lokaler Lauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. **#278-Fortsetzung:** vollständiger Checkout ab cd395c9b auf aktuellem Main 7b70f0df; HTTP/UI-Regressionen am Vorhead rot und mit Anbindung grün. 52 gezielte Service-/Versionsfälle und anschließend 271 überlappende Analyse-/Candidate-Regressionen bestanden. Erster echter GOOD-B07-Pass auf `18e3e141`, Tree `4c0abfea`, PR-Testmerge `71f16737`: [Run `40182968277` / Job `121137734172`, Versuch 1](https://github.com/burckhju/trading-workspace/actions/runs/40182968277/job/121137734172). Native PostgreSQL-Gesamtergebnisse und finale CI einschließlich der eng reproduzierten Frontend-Testkorrektur werden am jeweiligen exakten PR-Head gebunden; Collection ist kein Pass. |
| Fachliche Abnahme | Sprint-4-RC im bisherigen PB-013 als fachlich abgenommen bezeichnet; neuere Erweiterung / kompletter M2-Umfang nicht mitabgenommen. |
| Software-Auslieferung | Historische Analyse-RC-/Golden-Path-Nachweise; kein pauschaler Gesamtstatus. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Jede fachliche Modellfamilie von der allgemeinen Governance unterscheiden; aktuellen Replay-/Verify-Test gezielt qualifizieren. **Nächste Abhängigkeit:** Qualifizierte TC-001-Daten; bestehende Referenz-/Analysecontracts. **Datierter Nachtrag #278, 25.10.2026:** Neuer Listing-/Referenzownerweg und GOOD-B07 sind auf `18e3e141` tatsächlich nativ belegt; [Quellen-/Hash-/Artefaktnachweis](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md). Die Gesamtqualifikation des Folgecommits mit eng belegter Frontend-Testkorrektur steht im bestehenden PR #278. Fachabnahme und gesonderte Mergefreigabe bleiben erforderlich; keine produktive Aktivierung abgeleitet. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-014

[Einstieg planen](#pb-014-entry) · [Stopstrategie im TradePlan](#pb-014-stop) · [Kursziele im TradePlan](#pb-014-targets) · [Risikoannahmen im TradePlan](#pb-014-risk) · [Annahmen, Freigabe und Herkunft des Plans](#pb-014-assumptions)

<a id="pb-014-entry"></a>
<details>
<summary>PB-014 — Einstieg planen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Einstieg. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (historischer FT-007-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Produktneutralen Einstieg in einer konkreten TradePlanVersion dokumentieren. **Nicht-Soll:** Keine Order, keine automatische Einstiegsempfehlung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [TradePlan-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [TradePlan-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [ADRs S6-001–008 und Implementierungskette](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [FT-008 konsumiert genaue APPROVED-Version](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py). |
| Test / Commit | Historische S6-13- und Golden-Path-Nachweise; aktuelle Basis-CI. Kein neuer lokaler Plan-Testlauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | S6 Architecture Review in historischer Traceability: Accepted; kein neues menschliches Approval. |
| Software-Auslieferung | Bisheriger PB-014: v0.6.0-trade-plan. Alte Review-Pending-Notiz ist kein heutiger Arbeitsauftrag. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Eingabe-/Amendment-Fälle bei nächster Planänderung versionsgenau prüfen. **Nächste Abhängigkeit:** Bestehender FT-007-Vertrag; Candidate nur optionaler Ursprung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-stop"></a>
<details>
<summary>PB-014 — Stopstrategie im TradePlan</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Stopstrategie. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (historischer FT-007-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Geplante Invalidation/Stopannahme bleibt unveränderlich referenzierbar. **Nicht-Soll:** Planparameter sind kein Nachweis eines eigenständigen Stopmodells. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [TradePlan-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [TradePlan-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [ADRs S6-001–008 und Implementierungskette](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [FT-008 konsumiert genaue APPROVED-Version](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py). |
| Test / Commit | Historische S6-13- und Golden-Path-Nachweise; aktuelle Basis-CI. Kein neuer lokaler Plan-Testlauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | S6 Architecture Review in historischer Traceability: Accepted; kein neues menschliches Approval. |
| Software-Auslieferung | Bisheriger PB-014: v0.6.0-trade-plan. Alte Review-Pending-Notiz ist kein heutiger Arbeitsauftrag. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Geplanten Stop, späteren Managementstop und Modellfamilie getrennt prüfen. **Nächste Abhängigkeit:** Bestehender FT-007-Vertrag; Candidate nur optionaler Ursprung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-targets"></a>
<details>
<summary>PB-014 — Kursziele im TradePlan</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Kursziele. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (historischer FT-007-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Ursprüngliche Ziele in der konkreten Planversion erhalten. **Nicht-Soll:** Keine automatische Zielwahl; Managementänderungen überschreiben nicht den Plan. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [TradePlan-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [TradePlan-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [ADRs S6-001–008 und Implementierungskette](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [FT-008 konsumiert genaue APPROVED-Version](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py). |
| Test / Commit | Historische S6-13- und Golden-Path-Nachweise; aktuelle Basis-CI. Kein neuer lokaler Plan-Testlauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | S6 Architecture Review in historischer Traceability: Accepted; kein neues menschliches Approval. |
| Software-Auslieferung | Bisheriger PB-014: v0.6.0-trade-plan. Alte Review-Pending-Notiz ist kein heutiger Arbeitsauftrag. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Zielhistorie und Handoff in die Nachbeobachtung gezielt regressieren. **Nächste Abhängigkeit:** Bestehender FT-007-Vertrag; Candidate nur optionaler Ursprung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-risk"></a>
<details>
<summary>PB-014 — Risikoannahmen im TradePlan</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Risiko. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (historischer FT-007-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Risikoannahmen und Grenzen transparent dokumentieren. **Nicht-Soll:** Keine Positionsgrößenentscheidung; fehlende Eingaben sind nicht Nullrisiko. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [TradePlan-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [TradePlan-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [ADRs S6-001–008 und Implementierungskette](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [FT-008 konsumiert genaue APPROVED-Version](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py). |
| Test / Commit | Historische S6-13- und Golden-Path-Nachweise; aktuelle Basis-CI. Kein neuer lokaler Plan-Testlauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | S6 Architecture Review in historischer Traceability: Accepted; kein neues menschliches Approval. |
| Software-Auslieferung | Bisheriger PB-014: v0.6.0-trade-plan. Alte Review-Pending-Notiz ist kein heutiger Arbeitsauftrag. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Abgrenzung gegen spätere Positionsrisiko-/IV-Sichten prüfen. **Nächste Abhängigkeit:** Bestehender FT-007-Vertrag; Candidate nur optionaler Ursprung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-014-assumptions"></a>
<details>
<summary>PB-014 — Annahmen, Freigabe und Herkunft des Plans</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M3: Annahmen. Bereich/Querschnitt: 4. Bestehender Bezug: FT-007. Lieferziel: A, B. |
| Arbeitsstatus | Released (historischer FT-007-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Versionierte Annahmen, explizite Freigabe und gegebenenfalls genaue CandidateEvaluation referenzieren. **Nicht-Soll:** Keine Verwendung von latest statt des historischen Ursprungs. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [TradePlan-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [TradePlan-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx); [ADRs S6-001–008 und Implementierungskette](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [FT-008 konsumiert genaue APPROVED-Version](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py). |
| Test / Commit | Historische S6-13- und Golden-Path-Nachweise; aktuelle Basis-CI. Kein neuer lokaler Plan-Testlauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | S6 Architecture Review in historischer Traceability: Accepted; kein neues menschliches Approval. |
| Software-Auslieferung | Bisheriger PB-014: v0.6.0-trade-plan. Alte Review-Pending-Notiz ist kein heutiger Arbeitsauftrag. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Historische Freigabe-/Amendment-Belege erhalten; aktuelle Benutzerabnahme nicht erfinden. **Nächste Abhängigkeit:** Bestehender FT-007-Vertrag; Candidate nur optionaler Ursprung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-015

[Produktsuche und Suchuniversum](#pb-015-search) · [Produktvergleich und bewusste Auswahl](#pb-015-comparison) · [Produktscore und fachliche Modellfamilie](#pb-015-score)

<a id="pb-015-search"></a>
<details>
<summary>PB-015 — Produktsuche und Suchuniversum</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktsuche. Bereich/Querschnitt: 4. Bestehender Bezug: FT-008; FT-004 Stammdaten; TC-001. Lieferziel: A. |
| Arbeitsstatus | Released (historischer FT-008-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Produkte und gültige Terms/Listings für die konkrete freigegebene Planversion nachvollziehbar ermitteln. **Nicht-Soll:** Provider-Discovery ist keine stabile Produktidentität und keine Eignungsbestätigung. |
| Vorhandenseinsnachweis | Vorhandener Code beziehungsweise tatsächlicher Consumer statisch gelesen; nur der im Implementierungsfeld benannte Teilscope ist dadurch belegt. |
| Implementierung / Consumer | [ProductSelectionService.start_run / _load_universe](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py) liest Warrants, Terms und Listings des Underlyings; API/UI über registrierte Router. |
| Test / Commit | Historische FT-008- und Golden-Path-Nachweise; aktuelle Basis-CI; Live-Suchabdeckung nicht geprüft. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine neue fachliche Live-Abnahme. |
| Software-Auslieferung | Bisheriger PB-015: v1.0.0-product-selection; vollständige Live-Produktsuche damit nicht bewiesen. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Provider-/Produktabdeckung und spätere Low-input-Erweiterungen gesondert nachweisen. **Nächste Abhängigkeit:** PB-011; konkrete freigegebene PB-014-Planversion. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-015-comparison"></a>
<details>
<summary>PB-015 — Produktvergleich und bewusste Auswahl</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktvergleich. Bereich/Querschnitt: 4. Bestehender Bezug: FT-008. Lieferziel: A. |
| Arbeitsstatus | Released (historischer FT-008-Teilscope) |
| Soll / Nicht-Soll | **Soll:** Inputs, Kriterien, Datenzustände und exakte Produktversionen erklären; Auswahl bleibt Benutzerentscheidung. **Nicht-Soll:** Vergleich ist kein numerischer Produktscore. Eine begründete Ausnahme bestätigt keine Eignung. |
| Vorhandenseinsnachweis | Vorhandener Code beziehungsweise tatsächlicher Consumer statisch gelesen; nur der im Implementierungsfeld benannte Teilscope ist dadurch belegt. |
| Implementierung / Consumer | [ProductEvaluation / ProductSelection.from_user_decision](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/domain/models.py) und [Service (gelesen bis Zeile 235)](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py); INELIGIBLE abgewiesen, NOT_EVALUABLE im Domainvertrag nur mit expliziter Begründung auswählbar. |
| Test / Commit | Historische S8-E2E-Notiz beschreibt engere damalige Grenzen; aktuelle Domain-Ausnahme nicht mit altem pauschalem Selektionsverbot überschreiben. Basis-CI erfolgreich. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Frühere Release-/Reviewbelege erhalten; konkrete heutige Ausnahme-Fachabnahme nicht verifiziert. |
| Software-Auslieferung | Bisheriger PB-015: v1.0.0-product-selection; neuere Abweichungen nicht rückwirkend freigegeben. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Ausnahmeweg durch tatsächlichen API-/UI-Consumer und gezielte Tests prüfen; Datenqualität bleibt unabhängig von Nutzerbestätigung. **Nächste Abhängigkeit:** FT-008 aktueller API-/UI-Vertrag; qualifizierte WarrantListing-Kursdaten. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-015-score"></a>
<details>
<summary>PB-015 — Produktscore und fachliche Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktscore; M9: Produktscore. Bereich/Querschnitt: 4; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-008; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Ein Produktscore benötigt definierte Bedeutung, Eingaben, Parameter, Modellversion und nachvollziehbare Validierung. **Nicht-Soll:** Allgemeine EvaluationMetric-Felder, Eligibility oder Sortierung sind kein fertiger Score. |
| Vorhandenseinsnachweis | Nachweislich außerhalb des im Eintrag benannten historischen V1-Umfangs. Heutige vollständige Implementierung des ursprünglichen Anspruchs nicht verifiziert. |
| Implementierung / Consumer | [ProductEvaluation enthält Kriterien/Metriken](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/domain/models.py); [S8-Abgrenzung: keine erfundenen numerischen V1-Schwellen](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md). Vollständiger Score-Consumer nicht verifiziert. |
| Test / Commit | Kein belastbarer Test-/Abnahmebeleg für den ursprünglichen Produktscore ermittelt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Geltende Scoreentscheidung und eventuell andere Consumer suchen; sonst konkreten Modell-/Scopevorschlag freigeben lassen. **Nächste Abhängigkeit:** Modellverantwortliche Entscheidung; qualifizierte Daten; bestehende FT-008-Ownership. |
| Umfangsentscheidung | Im engeren S8-V1 nicht freigegeben; das ist keine belegte Entfernung aus dem ursprünglichen Zielbild. Originalanspruch bleibt offen. |

</details>

### PB-016

[Trade eröffnen und tatsächliche Käufe erfassen](#pb-016-opening) · [Depot und abgeleitete offene Positionen](#pb-016-positions)

<a id="pb-016-opening"></a>
<details>
<summary>PB-016 — Trade eröffnen und tatsächliche Käufe erfassen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Trade eröffnen. Bereich/Querschnitt: 5. Bestehender Bezug: FT-009. Lieferziel: A, B. |
| Arbeitsstatus | Released (historischer FT-009-Teilscope); additive Execution-Währungsbestätigung in Technical Review, siehe PB-017-/PB-019-Qualifikation. |
| Soll / Nicht-Soll | **Soll:** Bestätigte Erst-/Nachkäufe als immutable Ausführungsfakten erfassen, Herkunft exakt behalten. **Nicht-Soll:** Keine Brokerorder, autonome Produktauswahl oder Mengenempfehlung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | Bestehende Erst-/Nachkauf- und EXTERNAL-Captures bleiben erhalten. Additive [Execution-Währungsbestätigung](../../backend/app/features/trade_position/service/currency_confirmations.py) in derselben Owner-Transaktion; einschließlich Learning execute-as-trade. Kein EUR-Default und keine rückwirkende Änderung wirtschaftlicher Werte. [Konkrete Qualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md). |
| Test / Commit | Historische PR-18-CI und Merge 1f98a4a2f4568dbe3e1352c0ae5e5e0c93034c2a bleiben getrennt. Neue atomare Currency-Capture-/Learning-Replay-/Rollback-Fälle und aktuelles vollständiges Backend-Gate sind in der [Berichtsqualifikation mit Codebezug](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) nachgewiesen. |
| Fachliche Abnahme | Historische Release-/Abnahmehinweise; keine neue menschliche Abnahme. |
| Software-Auslieferung | v1.1.0-trade-position laut historischer Traceability. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Additiven Currency-Capture zusammen mit PB-017/PB-019 fachlich abnehmen; ursprüngliche Kaufhistorie nicht umschreiben. Separater bestehender Learning-Randfall: gleichzeitige erstmalige execute-as-trade-Requests mit identischem Key können am Unique-Constraint generisch 422 statt Replay liefern (statischer Befund, keine neue PostgreSQL-Reproduktion); keine Doppelanlage. Sequenzieller Replay und atomarer Currency-Handoff sind im neuen Nachweis qualifiziert. **Nächste Abhängigkeit:** PB-011; Workspace-Ursprung zusätzlich PB-014/015. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-016-positions"></a>
<details>
<summary>PB-016 — Depot und abgeleitete offene Positionen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Depot. Bereich/Querschnitt: 5. Bestehender Bezug: FT-009, durch FT-010 weiterentwickelter gemeinsamer Execution-/Position-Vertrag. Lieferziel: A, C. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Offene Mengen und Einstand aus effektiven Ausführungsfakten reproduzierbar darstellen. **Nicht-Soll:** Positionsübersicht ist weder Brokerdepot-Synchronisation noch vollständige Depot-Equity. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Position-Owner und Projektion](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [FT-010 Average-Cost-/Korrekturvertrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md); Trade-UI registriert. |
| Test / Commit | Historische Projektor-/Korrekturtests und aktuelle Basis-CI; keine Nutzerbestandsprüfung. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Historische FT-009/010-Nachweise betreffen definierte Teilsichten, nicht alle denkbaren Depotfunktionen. |
| Software-Auslieferung | FT-009-Release und FT-010-Releasevorbereitungsdokument; kein Beleg einer Brokerintegration. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Daten-/Berechnungsgrenzen der Positionssicht von tradeübergreifender Performance getrennt abnehmen. **Nächste Abhängigkeit:** Effektive Execution-Historie; PB-019 Performance liest nur. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-017

[Stop- und Zielmanagement](#pb-017-stop) · [Teilverkäufe](#pb-017-partial) · [Vollverkauf und Abschluss](#pb-017-close) · [Event-Historie und historische Korrekturen](#pb-017-history) · [Produktwechsel](#pb-017-product-change) · [Positionsbezogenes realisiertes Brutto-PnL](#pb-017-gross-pnl)

<a id="pb-017-stop"></a>
<details>
<summary>PB-017 — Stop- und Zielmanagement</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Stopmanagement. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Technical Review (aktueller Nachweisabgleich) |
| Soll / Nicht-Soll | **Soll:** Bestätigte Managemententscheidungen historisieren; für automatische Prüfung Instrument und Währung explizit binden. **Nicht-Soll:** Managementereignis ist kein SELL und überschreibt keine Planversion. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-010 Vertrag samt späterer Preisbasis-Korrektur](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md); [Implementierung: service, projector, timeline, ft011_eligibility](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); API/UI registriert. |
| Test / Commit | [PR #22 / Merge 18fe1df90e4f63529867fc32b5b6441d90738ff4: historische Tests und Gates](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.2.0-TRADE-MANAGEMENT.md); aktuelle Basis-CI. Nicht hier neu ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige menschliche Abnahme im gelesenen Releasevorbereitungsdokument belegt. |
| Software-Auslieferung | FT-010-Notiz nennt READY FOR RELEASE TAG; Tagstatus nicht daraus ableiten. Implementierung ist im aktuellen Softwarestand enthalten. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Sep-14-Preisbindung in aktuellem Regelconsumer und Regression nachweisen; Legacy-ungebundene Regeln nicht als aktiv behandeln. **Nächste Abhängigkeit:** PB-016; für Übergabe PB-018-Currentness-Vertrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-partial"></a>
<details>
<summary>PB-017 — Teilverkäufe</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Teilverkauf. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Technical Review (aktueller Nachweisabgleich) |
| Soll / Nicht-Soll | **Soll:** SELL kleiner als offene Menge erzeugt einen Teilverkauf und reproduzierbare Restposition. **Nicht-Soll:** Keine negative Position und kein impliziter SHORT. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-010 Vertrag samt späterer Preisbasis-Korrektur](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md); [Implementierung: service, projector, timeline, ft011_eligibility](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); API/UI registriert. |
| Test / Commit | [PR #22 / Merge 18fe1df90e4f63529867fc32b5b6441d90738ff4: historische Tests und Gates](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.2.0-TRADE-MANAGEMENT.md); aktuelle Basis-CI. Nicht hier neu ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige menschliche Abnahme im gelesenen Releasevorbereitungsdokument belegt. |
| Software-Auslieferung | FT-010-Notiz nennt READY FOR RELEASE TAG; Tagstatus nicht daraus ableiten. Implementierung ist im aktuellen Softwarestand enthalten. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Gezielte Mengen-, Replay-, Korrektur- und Nebenläufigkeitsfälle bei nächster Änderung prüfen. **Nächste Abhängigkeit:** PB-016; für Übergabe PB-018-Currentness-Vertrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-close"></a>
<details>
<summary>PB-017 — Vollverkauf und Abschluss</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Trade schließen. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Technical Review (aktueller Nachweisabgleich) |
| Soll / Nicht-Soll | **Soll:** Realer voller SELL schließt wirtschaftlich durch effektive Historie; FT-011 erst danach. **Nicht-Soll:** Kein unabhängig editierbarer CLOSED-Status und keine virtuelle Ausführung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-010 Vertrag samt späterer Preisbasis-Korrektur](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md); [Implementierung: service, projector, timeline, ft011_eligibility](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); API/UI registriert. |
| Test / Commit | [PR #22 / Merge 18fe1df90e4f63529867fc32b5b6441d90738ff4: historische Tests und Gates](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.2.0-TRADE-MANAGEMENT.md); aktuelle Basis-CI. Nicht hier neu ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige menschliche Abnahme im gelesenen Releasevorbereitungsdokument belegt. |
| Software-Auslieferung | FT-010-Notiz nennt READY FOR RELEASE TAG; Tagstatus nicht daraus ableiten. Implementierung ist im aktuellen Softwarestand enthalten. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | UI→Execution→Position→FT-011-Eignung mit exakten Versionen und Korrekturfall nachweisen. **Nächste Abhängigkeit:** PB-016; für Übergabe PB-018-Currentness-Vertrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-history"></a>
<details>
<summary>PB-017 — Event-Historie und historische Korrekturen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: Event-Historie. Bereich/Querschnitt: 5. Bestehender Bezug: FT-010; FT-009 gemeinsamer Execution-/Position-Owner. Lieferziel: A, B. |
| Arbeitsstatus | Technical Review (aktueller Nachweisabgleich) |
| Soll / Nicht-Soll | **Soll:** Ausführungen und Managementevents unveränderlich erhalten; Korrektur/Supersession leitet aktuellen Zustand neu ab. **Nicht-Soll:** Keine zweite Verkaufstatsache in der Timeline, kein Überschreiben historischer Fakten. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-010 Vertrag samt späterer Preisbasis-Korrektur](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md); [Implementierung: service, projector, timeline, ft011_eligibility](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); API/UI registriert. |
| Test / Commit | [PR #22 / Merge 18fe1df90e4f63529867fc32b5b6441d90738ff4: historische Tests und Gates](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.2.0-TRADE-MANAGEMENT.md); aktuelle Basis-CI. Nicht hier neu ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige menschliche Abnahme im gelesenen Releasevorbereitungsdokument belegt. |
| Software-Auslieferung | FT-010-Notiz nennt READY FOR RELEASE TAG; Tagstatus nicht daraus ableiten. Implementierung ist im aktuellen Softwarestand enthalten. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Auswirkungen auf bestehende Observation/Review/LearningEvidence gezielt durchprüfen. **Nächste Abhängigkeit:** PB-016; für Übergabe PB-018-Currentness-Vertrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-017-product-change"></a>
<details>
<summary>PB-017 — Produktwechsel</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M4: Produktwechsel. Bereich/Querschnitt: 4, 5. Bestehender Bezug: FT-008/FT-010; Umsetzungseigentum erst nach Entscheidung, keine neue Paketgrenze. Lieferziel: B. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Wechsel zwischen konkreten Produkten erhält wirtschaftliche SELL-/BUY-Fakten, Planherkunft und verständliche Trade-Identität. **Nicht-Soll:** Kein PRODUCT_CHANGED-Ereignis, das Ausführungen verdeckt; keine Mutation von Trade.product_id. |
| Vorhandenseinsnachweis | Nachweislich außerhalb des im Eintrag benannten historischen V1-Umfangs. Heutige vollständige Implementierung des ursprünglichen Anspruchs nicht verifiziert. |
| Implementierung / Consumer | [Alter Katalog nennt Produktwechsel](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md); [FT-010 Product change boundary](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md) schließt ihn aus V1 aus und fordert eine eigene fachliche Entscheidung/ADR. |
| Test / Commit | Kein vollständiger Product-Switch-Consumer oder entsprechender Abnahmebeleg verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Entscheidungsvorschlag: getrennte reale Ausführungen und explizite, nachvollziehbare Wechselbeziehung; Trade-Identitätssemantik vor Umsetzung klären. **Nächste Abhängigkeit:** Product Owner: Trade-Identität und Korrektursemantik; danach vorhandene Execution-Contracts. |
| Umfangsentscheidung | Belegt: nicht Teil von FT-010 V1. Nicht belegt: dauerhafte Verschiebung/Entfernung aus M4. Dieser Eintrag verantwortet die Restklärung; PB-015 verweist nur hierher. |

</details>

<a id="pb-017-gross-pnl"></a>
<details>
<summary>PB-017 — Positionsbezogenes realisiertes Brutto-PnL</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5: abgeleitetes Positionsergebnis; Vorleistung für M8. Bereich/Querschnitt: 5, 8. Bestehender Bezug: FT-010 auf FT-009 Execution-/Position-Vertrag. Lieferziel: C. |
| Arbeitsstatus | Technical Review; enger SELL-Zeitraumbericht vorhanden. Kaufwährungs-Wiederverwendung und Eingabevereinfachung am 20.10.2026 ausdrücklich entschieden und implementiert; neue Qualifikation und Zielupdate gesondert belegen. |
| Soll / Nicht-Soll | **Soll:** Realisiertes Brutto-PnL und Einstand aus effektiven BUY-/SELL-Fakten nach bestehender Average-Cost-Semantik ableiten. **Nicht-Soll:** Keine Gebühren, Steuern, Nettoerträge, Depot-Equity oder tradeübergreifende Performance erfinden. |
| Vorhandenseinsnachweis | Bestehender FT-010-Average-Cost-Owner und SELL-Trace bleiben erhalten. Ein gemeinsamer reiner Resolver verwendet direkte Kaufbestätigungen, gleichseitige Korrekturherkunft und vollständige vorherige BUY-Basis; keine gespeicherte Zweitwahrheit. |
| Implementierung / Consumer | [PositionProjector.project/project_with_trace](../../backend/app/features/trade_position/domain/projector.py) behält eine Schleife und exakte Decimal-Reihenfolge. [Owner-Währungsresolver](../../backend/app/features/trade_position/domain/currency_resolution.py) ergänzt `currency_resolution` an Capture, Timeline, History und Report; eigene Bestätigungen bleiben append-only. Schema unverändert 0047. |
| Test / Commit | [Kaufwährungs-Wiederverwendung: Quellen, Vertrag und neue Qualifikation](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). Die [V1.5.9-Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) und vorherige Trace-Qualifikation bleiben historische Nachweise mit eigenem Codebezug. Synthetische Bestätigungen belegen keine Nutzerdatenwährung. |
| Fachliche Abnahme | V1-Vertrag am 17.10.2026 zur Umsetzung freigegeben. Am 20.10.2026 ausdrücklich präzisiert: Kaufwährung auch für Verkauf nutzen, so wenig zusätzliche Eingaben wie möglich (ADR-S10-008-Nachtrag). Merge und PC-Bereitstellung nach grünen Prüfungen bereits autorisiert. Keine vollständige M8- oder abschließende PC-Fachabnahme daraus abgeleitet. |
| Software-Auslieferung | V1.5.9 auf `254fe35b76027b72cd989715e17bd0ae55af55eb` veröffentlicht. [V1.5.10](../releases/V1.5.10-EXECUTION-CURRENCY-REUSE.md) ergänzt reine Owner-Währungsableitung ohne Migration; Veröffentlichung erst nach erfolgreichen aktuellen PR- und main-Prüfungen durch vorhandenen Version-Workflow. |
| Betriebsnachweis | Am 20.10.2026 meldet der Nutzer vier gesunde Dienste, `ready` und installiert 1.5.9 / `254fe35b76027b72cd989715e17bd0ae55af55eb`; lesende Berichtsansicht beobachtet. Kein Installations- oder Fachabnahmenachweis für 1.5.10 und keine Aussage über vollständige reale Währungsabdeckung. |
| Restarbeit / nächste Abhängigkeit | Kaufwährungs-Wiederverwendung auf geprüftem Stand ausliefern und am PC lesend prüfen. Fehlende echte Kaufbelege bleiben eine Datenlücke; keine neue Bestätigung je SELL nötig. **Nächste Abhängigkeit:** qualifizierter 1.5.10-Stand und tatsächliche Quellenabdeckung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-018

[Zulässige Nachbeobachtung](#pb-018-observation) · [Virtuelle Weiterführung](#pb-018-virtual) · [Exit Review und Handoff](#pb-018-review) · [Vergleich tatsächlicher und virtueller Ausstiege](#pb-018-exit-comparison) · [Korrekturen, Review-Currentness und historische Herkunft](#pb-018-currentness)

<a id="pb-018-observation"></a>
<details>
<summary>PB-018 — Zulässige Nachbeobachtung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Nachbeobachtung. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Nachbeobachtung startet nur nach tatsächlichem vollständigem wirtschaftlichem Exit und mit historischem Produkt-/Listingkontext. **Nicht-Soll:** Kein Beobachtungsstart allein durch manuell gesetzten Abschlussstatus; keine neue reale Position. |
| Vorhandenseinsnachweis | Vorhandener Code beziehungsweise tatsächlicher Consumer statisch gelesen; nur der im Implementierungsfeld benannte Teilscope ist dadurch belegt. |
| Implementierung / Consumer | [PostTradeObservationService.start](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/observation_service.py) prüft is_fully_closed und full_exit_at, Kontext und vorhandene Observation; [Post-Trade-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx) ist angebunden. |
| Test / Commit | Gelesener Service am Basiscommit; [Handoff-Unit-Tests](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/tests/unit/backend/features/post_trade/test_handoff_service.py) prüfen Folgegate mit Mocks. Historische Golden-Path-Naht und aktuelle Basis-CI; kein neuer lokaler Lauf. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Wiederholungs-, Listing-, Korrektur- und Nebenläufigkeitsfälle mit echter Persistenz gezielt qualifizieren. **Nächste Abhängigkeit:** PB-017 Vollverkauf; gültiger FT-004-Kontext und TC-001-Historie. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-virtual"></a>
<details>
<summary>PB-018 — Virtuelle Weiterführung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Virtuelle Weiterführung. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Der definierte Nachbeobachtungshorizont verwendet nachvollziehbare gespeicherte Beobachtungsdaten. **Nicht-Soll:** Keine virtuellen Daten als reale Ausführung, keine erfundene historische Warrant-Equity. |
| Vorhandenseinsnachweis | Vorhandener Code beziehungsweise tatsächlicher Consumer statisch gelesen; nur der im Implementierungsfeld benannte Teilscope ist dadurch belegt. |
| Implementierung / Consumer | [refresh](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/observation_service.py) liest persistierte Tagespreise und ruft build_observation_evidence mit Originalzielen/-stop und definiertem Zielhorizont auf. |
| Test / Commit | Historischer Golden-Path-Nachweis; Details der Metrik-/Kalenderberechnung hier nicht vollständig neu qualifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Horizont, zulässige Datenbasis und unvollständige Beobachtung in eigener Fachabnahme abgrenzen. **Nächste Abhängigkeit:** Qualifizierte Beobachtungen und ursprüngliche Planversion; keine Performancevoraussetzung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-review"></a>
<details>
<summary>PB-018 — Exit Review und Handoff</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Exit Review. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Abgeschlossene Beobachtung und finalisierte aktuelle Reviewversion erlauben einen versionsgenauen Handoff. **Nicht-Soll:** Finalisierung erzeugt keine automatische Lesson oder Modellfreigabe. |
| Vorhandenseinsnachweis | Vorhandener Code beziehungsweise tatsächlicher Consumer statisch gelesen; nur der im Implementierungsfeld benannte Teilscope ist dadurch belegt. |
| Implementierung / Consumer | [Ft012HandoffService](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/handoff_service.py) liefert READY nur für COMPLETED / FINALIZED / CURRENT mit konkreten IDs; [Review-UI und bewusster Übergang](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx). |
| Test / Commit | [tests/unit/backend/features/post_trade/test_handoff_service.py](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/tests/unit/backend/features/post_trade/test_handoff_service.py): sechs gelesene Tests für fehlende/unvollständige Observation, fehlendes/DRAFT/STALE Review und READY mit exakten IDs. Mock-Unit-Tests, kein DB-Abnahmeersatz; Basis-CI separat. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Fachliche Reviewbedienung, Validierungsfehler und Versionswechsel entlang der vollständigen UI-Strecke nachweisen. **Nächste Abhängigkeit:** PB-018 Beobachtung; FT-012 übernimmt nur qualifizierte konkrete Herkunft. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-exit-comparison"></a>
<details>
<summary>PB-018 — Vergleich tatsächlicher und virtueller Ausstiege</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6: Vergleich tatsächlicher und virtueller Ausstiege. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011. Lieferziel: B. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Tatsächliche Exitfakten und hypothetische Nachbeobachtung mit offengelegter Preis-/Datenbasis unterscheiden. **Nicht-Soll:** Underlying-Bewegung ist nicht automatisch hypothetische Warrant-Rendite oder Gebühren-/Netto-PnL. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Observation-Service](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/observation_service.py) konsumiert full_exit_at, originale Ziele/Stop und gespeicherte Preise; [historischer Review-Übergang](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md). Vollständige Vergleichsmetrik nicht neu verifiziert. |
| Test / Commit | Kein vollständiger aktueller Fach-/Berechnungsabnahmebeleg für jede ursprüngliche Vergleichsaussage verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Tatsächliche Vergleichsformeln und nicht anwendbare Fälle am Domain-Owner lesen und mit expliziten Datengrenzen abnehmen. **Nächste Abhängigkeit:** Reale effektive Exitfakten; Beobachtungsdaten, keine erfundenen Optionsscheinhistorien. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-018-currentness"></a>
<details>
<summary>PB-018 — Korrekturen, Review-Currentness und historische Herkunft</summary>

> Fortschreibung 21.10.2026: Die unabhängige [lesende Einzeltrade-Quellenansicht](../implementation/TRADE_SOURCE_VIEW_QUALIFICATION.md) verbindet konkrete Review-/Journalversionen mit getrennt ausgewiesener heutiger Quellenprüfung. Veröffentlicht in Draft-PR #272; echte Quellenreise über Browser/API/PostgreSQL auf 8cc68f6 bestanden, einschließlich unveränderter historischer Inhalte bei separat berechnetem STALE. Vollständige finale CI-/Mobilnachweise sind checkoutgebunden im PR zu prüfen; die damalige Abschlussstatistik-Integration blieb offen. Der getrennt beauftragte [Integrationsschnitt](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md) verbindet jetzt Liste, qualifiziertes Ergebnis und genaue Quellen im Entwicklungsbranch; neue Vollgate-/Browsernachweise bleiben an seinen PR gebunden. Keine automatische Revalidierung, kein main-Merge und kein neuer Release.


| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M5/M6/M7: historische Korrekturen als durchgängiger Vertrag. Bereich/Querschnitt: 7; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: FT-010 → FT-011 → FT-012. Lieferziel: B, D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Korrekturen erhalten alte Fakten und Versionen; veraltete Review-/Evidence-Kontexte bleiben erkennbar. **Nicht-Soll:** Keine nachträgliche Umschreibung bereits materialisierter Evidence auf latest. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [STALE blockiert READY](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/handoff_service.py); [exakte exit_review_version_id und keine historische Retargetierung](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_EXTENSION_09.md). |
| Test / Commit | [STALE-Unit-Test](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/tests/unit/backend/features/post_trade/test_handoff_service.py); vollständige Korrektur→Review→Evidence→Lesson-Regressionsstrecke nicht neu ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. **Nachtrag 23.10.2026:** Gemeinsamer Entwicklungsstand #273 + #269: exakte historische Quellen und die geschützte FT-011-/Korrekturstrecke werden zusammen geprüft; alte Versionspins und SOURCE_BUSY bleiben unverändert. [Gemeinsamer Nachweisvertrag](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md); exakte aktuelle Head-/Tree-/Run-/Artefaktbindung in [PR #273](https://github.com/burckhju/trading-workspace/pull/273), Herkunft #269 bleibt separat. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Auslösung von STALE/Currentness nach faktischer Korrektur und spätere Revalidierung separat prüfen. **Nächste Abhängigkeit:** Bestehende Supersession-/Currentnessverträge; PB-019 Materialisierung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### PB-019

[Exit-Review-Evidence bewusst materialisieren](#pb-019-materialization) · [Journalentwurf und Journalabschluss](#pb-019-journal) · [Regelabweichungen dokumentieren](#pb-019-deviations) · [Belegte Lessons Learned](#pb-019-lessons) · [Entscheidungsbewertung getrennt vom Ergebnis](#pb-019-decision-quality) · [Performancekennzahlen](#pb-019-performance-metrics) · [Tradeübergreifende Statistiken](#pb-019-performance-statistics) · [Performance-Dashboards](#pb-019-performance-dashboards) · [Perioden- und Tradeauswertungen](#pb-019-performance-evaluations)

<a id="pb-019-materialization"></a>
<details>
<summary>PB-019 — Exit-Review-Evidence bewusst materialisieren</summary>

> Fortschreibung 2026-10-16: neuer abgegrenzter Konsistenz-/Inventarschnitt aus v1.5.7 (`3faf0f76…`). Bestehende Journal-/Lesson-Owner und 20-EOD-Semantik unverändert. Historische Prüfbezüge unten sind keine Qualifikation der neuen Änderungen.
> Qualifikationsfortschreibung: [eigener Nachweis auf gemeinsamem Commit](../implementation/FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md). Die folgende Tabelle beschreibt diesen technischen Schnitt; ältere Notizen bleiben als historische Belege erhalten.

> Nachweisfortschreibung 2026-10-14: [vollständige Repository-Integration und abgegrenzte Qualifikation](../implementation/POST_TRADE_LEARNING_HANDOFF_REVIEW.md) in Draft-PR #259 auf v1.5.6. b40: 2600 Backendtests einschließlich drei unabhängiger PostgreSQL-Fälle; dort bezeichneter 8f-Testmerge: 456 Frontendtests und 51 Browserfälle. Drei neue Browserfälle verwenden abgefangenes HTTP, keine vollständige Journal-/DB-Nutzerreise.
> First-party-Review-Pin und UI-Readback sind ein technischer Teilschnitt, keine Abnahme des Journals oder des gesamten Lernprozesses. Arbeitsstatus und Betriebsfreigabe werden durch diese Notiz nicht hochgestuft.

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M6→M7: Übergang zum Lernen. Bereich/Querschnitt: 7. Bestehender Bezug: FT-012; FT-011 bleibt Quellowner. Lieferziel: B, D. |
| Arbeitsstatus | Technical Review — definierter Konsistenz-/Inventarschnitt technisch qualifiziert; fachliche Abnahme offen. |
| Soll / Nicht-Soll | **Soll:** Ein expliziter idempotenter FT-012-Befehl materialisiert unveränderliche Evidence mit exakter Reviewversion. **Nicht-Soll:** Keine automatische Interpretation, keine zweite Readinesslogik in FT-012. |
| Vorhandenseinsnachweis | Bestehender FT-012-Command mit transaktionsgebundenem FT-011-Quellschutz, tatsächlicher Owner-Fingerprintprüfung und unabhängigem historischen Evidence-Inventar einschließlich exakter alter LessonVersion-Relationen umgesetzt und auf PostgreSQL/Browser qualifiziert. |
| Implementierung / Consumer | [Guard/Handoff](../../backend/app/features/post_trade/application/materialization_handoff.py) bleibt FT-011; [FT-012-Inventar](../../backend/app/features/learning/application/ft011_evidence_history_service.py) und bestehende Materialisierung → [Bisherige Review-Evidence](../../frontend/src/features/learning/components/Ft011EvidenceHistory.tsx) im PostTradeLearningPage; genauer historischer Lesson-Detail-Link. Öffentlicher Handoff und Materialisierungsstatus verwenden denselben inspizierenden Owner. |
| Test / Commit | [Gemeinsame Qualifikation](../implementation/FT011_MATERIALIZATION_CONSISTENCY_QUALIFICATION.md), `0863248b0c44e7c36d41b29acbef56b451d2592f`, Lauf `38957166870`: Backend 2736, Frontend 500, Browser 53 bestanden; 92 gezielte Fälle einschließlich 11 echter PostgreSQL-Fälle und zwei retryfreie Wiederholungen des neuen Browserfalls. Keine Doppelzählung; rote Zwischenstände und Commitgrenzen dokumentiert. **Nachtrag 23.10.2026:** Der bestehende geschützte FT-011-Historienfall aus #269 gehört nun zur gemeinsamen Entwicklungsqualifikation mit #273; kein neuer Materialisierungsowner und keine Lockerung der historischen Bindung. [Gemeinsamer Nachweisvertrag](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md); exakte aktuelle Head-/Tree-/Run-/Artefaktbindung in [PR #273](https://github.com/burckhju/trading-workspace/pull/273), Herkunft #269 bleibt separat. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Definierter Code-/Testschnitt technisch qualifiziert. Aktuelle Pflichtprüfungen und tatsächlicher Integrations-/Mergebeleg werden in [PR #263](https://github.com/burckhju/trading-workspace/pull/263) nachgewiesen; nicht aus früherer CI abgeleitet. Keine neue Veröffentlichungsversion oder PC-Installation durch diesen Schnitt. |
| Betriebsnachweis | Das vom Nutzer bestätigte v1.5.7-Installationsprotokoll enthält den neuen Konsistenz-/Inventarschnitt noch nicht. Dessen Zielinstallations- und Lastnachweis bleibt offen. |
| Restarbeit / nächste Abhängigkeit | Die zwei benannten V1-Race-/Inventarlücken sind innerhalb [ADR-007](../decisions/ADR-POST-FT012-007-MATERIALIZATION-CONSISTENCY.md) technisch geschlossen. Historische Reads bleiben as-of-read; gleicher Listing-Kontext kann kurz SOURCE_BUSY liefern. **Nächste Abhängigkeit:** abgeschlossene aktuelle PR-Prüfungen/normaler Merge, danach gesondert freigegebener Release-/PC-Updateweg; große Historien, Mobil-/Barrierefreiheits- und Fachabnahme separat. |
| Umfangsentscheidung | Kein paralleler Owner, keine geänderte 20-EOD- oder Journal-Schreibregel. Ältere offene Race-/Inventarhinweise gelten für deren damalige Baselines; der neue Nachweis ist kein pauschaler Abschluss von M6/M7 oder aller PB-019-Fähigkeiten. |

</details>

<a id="pb-019-journal"></a>
<details>
<summary>PB-019 — Journalentwurf und Journalabschluss</summary>

> Umsetzungsschnitt 2026-10-14: [Journal-Schreibvertrag und Abnahmekriterien](../implementation/FT012_JOURNAL_WRITE_DOR.md), [ADR zur Versionierung/Quellenbindung](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md). Auf getrenntem Entwicklungsbranch aus PR #259: vorhandenes Modell → Commands/UOW → API → Entwurf/Finalisierung/Folgeversion → explizite Journal-Evidence. Historienanzeige bleibt bei veralteter Quelle verfügbar; TradePlan-Hard-Delete erhält eine Final-Historien-Sperre.
> Fortschreibung 2026-10-15: [eigene Journal-Qualifikation](../implementation/FT012_JOURNAL_WRITE_QUALIFICATION.md) auf gemeinsamem Prüfcommit abgeschlossen. Die Tabelle führt den aktuellen begrenzten Arbeitsstand. Keine menschliche Fachabnahme, Veröffentlichungsversion oder Zielinstallation wird behauptet. Die folgenden Bestandsnotizen bleiben als Stand **vor** diesem Journal-Schnitt erhalten.


> Bestandsnotiz 2026-10-14: [vollständiger Checkout und Journal-Vertragsvorschlag](../implementation/POST_TRADE_LEARNING_HANDOFF_REVIEW.md) bestätigen Journalmodelle und Evidence-Lesetypen, aber keinen Journal-Schreibservice, entsprechende UOW-Repositories, registrierte Schreibroute oder Editor im FT-012-Consumer. Die Domain erlaubt leere Finals und enthält dort keinen konkreten Review-Pin.
> Journal-Commands, API, UI, Finalisierung, Folgeversion und Datenbanknachweise sind durch den Handoff-Patch nicht geliefert. Keine automatische Verschärfung durch Performance und keine neue Freigabe für zusätzliche Pflichtbewertungen.

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Journal. Bereich/Querschnitt: 7. Bestehender Bezug: FT-012; bestehende Evaluation-Ownership. Lieferziel: B. |
| Arbeitsstatus | Technical Review; P1 – Fokus B. Journal-V1 technisch qualifiziert, fachliche Abnahme offen. |
| Soll / Nicht-Soll | **Soll:** Ein eigenständiger Journalentwurf dokumentiert Reflexion und genaue Trade-/Review-Herkunft; Abschlussregeln sind testbar festgelegt. **Nicht-Soll:** Performance ist keine Voraussetzung für einen Entwurf. Exit Review, LearningEvidence und Lesson sind kein stiller Ersatz für Journal. |
| Vorhandenseinsnachweis | Journal-V1 im bestehenden FT-012-Owner implementiert und im vollständigen Checkout einschließlich echtem PostgreSQL-/Browserweg technisch geprüft; Entwurf, finaler Stand und Folgeversion eigenständig. |
| Implementierung / Consumer | [JournalService](../../backend/app/features/learning/application/journal_service.py), bestehende Persistenz/UOW und [Journal-API](../../backend/app/features/learning/api/journal_router.py) → [TradeJournalPanel](../../frontend/src/features/learning/components/TradeJournalPanel.tsx) im PostTradeLearningPage. JournalEvidenceOrigin zeigt die genaue Quellenversion im Lesson-Detail. |
| Test / Commit | [Gemeinsamer Qualifikationsnachweis](../implementation/FT012_JOURNAL_WRITE_QUALIFICATION.md) auf `666e8ab07d4fd509e316eadfa9b31d57ce3d48c3`, Lauf `38683089292`: Backend 2645, Frontend 472, Browser 52 bestanden. Echte BUY/SELL-, 19/20-Beobachtungs-, Journal-/Lesson-/Korrekturstrecke und parallele PostgreSQL-Commands; keine Hochrechnung von Basis-CI. **Nachtrag 23.10.2026:** Der bestehende Journal-/Lesson-Folgeversions-/Korrekturfall aus #269 wird im separaten geschützten Job auf demselben Entwicklungsbaum wie #273 geprüft. Keine fachliche Journalpflicht für Geldresultate. [Gemeinsamer Nachweisvertrag](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md); exakte aktuelle Head-/Tree-/Run-/Artefaktbindung in [PR #273](https://github.com/burckhju/trading-workspace/pull/273), Herkunft #269 bleibt separat. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | PR #260 nach erneuten grünen Current-main-Prüfungen auf `9da6a809…` als `708d4bf6…` integriert. Kein neuer Release; additive Migration 20261014_0046 nur im Teststack ausgeführt, keine Nutzerinstallation. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Fachreview (insbesondere leerer Abschluss/Historienerhalt), Installationsfreigabe, externe Journale und Mobil-/Barrierefreiheitsabnahme bleiben offen. Allgemeiner Lesson-Review-/Folgeversionsdialog ist [separat qualifiziert](../implementation/FT012_LESSON_REVIEW_QUALIFICATION.md); FT011-Handoff-Race bleibt eigener Restscope. **Nächste Abhängigkeit:** bestehende Owner-/Versionsverträge, nicht Performance. |
| Umfangsentscheidung | M7 bleibt ursprüngliche Referenz. Journal-V1 ist kein pauschaler Abschluss von M7 oder des ganzen Lernbereichs; keine neuen Scores, Pflichtbewertungen, Importquellen oder Modellaktivierungen. |

</details>

<a id="pb-019-deviations"></a>
<details>
<summary>PB-019 — Regelabweichungen dokumentieren</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Regelabweichungen. Bereich/Querschnitt: 7; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-012; Reviewquelle FT-011. Lieferziel: B, D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Abweichungen beziehen sich auf die tatsächlich verwendete Regel-/Planversion und belegte Fakten. **Nicht-Soll:** Keine nachträgliche Bewertung alter Entscheidungen mit latest-Regeln. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [ExitReviewAssessment-Prozessfelder im Testvertrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/tests/unit/backend/features/post_trade/test_handoff_service.py); [ursprünglicher Journalprozess](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/domain/TRADING_PROCESS_MODEL.md). Eigenständige Regelabweichungsfunktion nicht vollständig verifiziert. |
| Test / Commit | Gelesene Handoff-Tests sind kein Test der vollständigen Abweichungsbewertung. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Vorhandene Review-/Lesson-Felder gegen Journalanspruch abgrenzen; Lücken und zulässige Bewertungen entscheiden. **Nächste Abhängigkeit:** Genaue historische Regel-/Planversion und Journalvertrag. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-019-lessons"></a>
<details>
<summary>PB-019 — Belegte Lessons Learned</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Lessons Learned. Bereich/Querschnitt: 7. Bestehender Bezug: FT-012. Lieferziel: B, D. |
| Arbeitsstatus | Technical Review — explizite Lesson-Prüfung/Folgeversion technisch qualifiziert; keine fachliche Abnahme oder Zielinstallation. |
| Soll / Nicht-Soll | **Soll:** Eine bewusste Interpretation referenziert konkrete LearningEvidence und eine unveränderliche LessonVersion. **Nicht-Soll:** Evidence-Transport erzeugt keine Lesson; Lesson erzeugt kein automatisches Modellapproval. |
| Vorhandenseinsnachweis | Bestehende Lesson-Erstellung und Journal-Evidence-Strecke um expliziten Quellen-/Widerspruchsreview und kontrollierte neue LessonVersion ergänzt. Tatsächlicher Browser-/PostgreSQL-Korrekturweg und unveränderte alte Inhalte/Relationen geprüft. |
| Implementierung / Consumer | LessonReviewCommands komponiert bestehende Lesson-/Review-Services mit exaktem Versions-/Status-/Signalpin und idempotentem Commit. LessonReviewPanel bietet Quellen-/Widerspruchsprüfung, ausdrückliche Auflösung und neue Snapshots.  Bestehendes LessonDraftFromEvidence und LessonDetailPage; FT-012 LessonService.create_with_tags schließt den expliziten Erstellungsbefehl atomar ab. JournalEvidenceOrigin liest konkrete Journalversion und heutige Quellenprüfung getrennt; keine automatische Neuinterpretation. |
| Test / Commit | [Qualifikation](../implementation/FT012_LESSON_REVIEW_QUALIFICATION.md), Code-/Testcommit `4081563509cb4ad4e765de499765a1759b59cdd3`, Lauf `38824269518`: drei unveränderte Gesamtgates erfolgreich, echter Journal→Lesson-V2-Browserweg zusätzlich zweimal ohne Retry. Historische Fehlversuche bleiben getrennt; finale Current-main-Prüfungen und Mergebeleg in PR #261. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Code in PR #261; normaler Merge nur nach grünen finalen Current-main-Prüfungen gemäß ausdrücklicher Nutzerfreigabe. Aktueller Mergebeleg in PR #261. Keine neue Migration oder Release-/Zielbetriebsbehauptung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | FT011-Materialisierungsrennen und historisches NOT_READY-Evidence-Inventar, allgemeine RETIRED-Reaktivierung, Titel-/Tag-Editor und vollständige Mobil-/Barrierefreiheitsabnahme bleiben getrennt. Fachliche Abnahme und Zielinstallation offen. PR #90 nicht als main-Funktion zählen. **Nächste Abhängigkeit:** bestehende FT-011-/FT-012-Quellenverträge; Journal ist keine neue Pflicht für die FT011-Lesson-Strecke. |
| Umfangsentscheidung | Vorhandene Lesson-Strecke erhalten, nicht neu bauen. Journal bleibt daneben eigener ursprünglicher Anspruch. |

</details>

<a id="pb-019-decision-quality"></a>
<details>
<summary>PB-019 — Entscheidungsbewertung getrennt vom Ergebnis</summary>

> Fortschreibung 21.10.2026: [Quellenansicht und A1–A16-Prüfgrenzen](../implementation/TRADE_SOURCE_VIEW_QUALIFICATION.md) ergänzen ausschließlich die Anzeige gespeicherter Exit-Bewertung, genauer Journal-/Evidence-/Lessonbeziehungen und Originalplanung. 598 Frontendtests und 680 betroffene Backend-Unitfälle bestanden; Quellen-Browserreise mit exakten L1-/Journalpins und Nichtmutation jetzt tatsächlich bestanden (Draft-PR #272). Der erste Backend-Volllauf fand zwei korrigierte Fixturefehler; sein Ergebnis wird nicht als grüner Abschluss gewertet. Finale Vollgate-/Mobilnachweise bleiben im PR getrennt gebunden. Gesamtergebnis/Abschlusslisten-Einstieg werden im gesonderten [Integrationsschnitt](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md) an den bestehenden Reportowner angebunden; exakte neue Prüfbindung im Integrations-PR. Menschliche Fachabnahme und Zielinstallation bleiben offen. Der allgemeine Bewertungsumfang bleibt **Analysis**, nicht durch reine Quellenanzeige erledigt.


| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M7: Entscheidungsbewertung. Bereich/Querschnitt: 7. Bestehender Bezug: FT-011 Review / FT-012 Journal und Lessons. Lieferziel: B, D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Prozess-/Entscheidungsqualität und wirtschaftliches Ergebnis werden mit erklärten Kriterien getrennt bewertet. **Nicht-Soll:** Ein positiver Ertrag beweist keine gute Entscheidung; keine erfundenen Scorekriterien. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Reviewvertrag enthält timing, process_adherence, risk_decision, overall_exit_decision](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/tests/unit/backend/features/post_trade/test_handoff_service.py); [Review-/Learning-UI](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/features/post_trade/pages/PostTradeLearningPage.tsx). |
| Test / Commit | Handoff-Test enthält Bewertungsfixtures, qualifiziert aber nicht die vollständige fachliche Bewertungsbedeutung. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. **Nachtrag 23.10.2026:** #273 und #269 werden gemeinsam technisch qualifiziert; gespeicherte GOOD/IMPROVABLE-Aussagen bleiben konkrete Versionen, keine aus Gewinn/Verlust abgeleitete Gesamtbewertung. Analysis des allgemeinen Bewertungsumfangs bleibt bestehen. [Gemeinsamer Nachweisvertrag](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md); exakte aktuelle Head-/Tree-/Run-/Artefaktbindung in [PR #273](https://github.com/burckhju/trading-workspace/pull/273), Herkunft #269 bleibt separat. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Originalen M7-Bewertungsumfang gegen vorhandene Review-/Lessonfelder abnehmen; ungeklärte Bewertungsmaßstäbe explizit entscheiden. **Nächste Abhängigkeit:** Freigegebene Kriterien; konkrete historische Evidence. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-019-performance-metrics"></a>
<details>
<summary>PB-019 — Performancekennzahlen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Performancekennzahlen. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Technical Review; enger SELL-Zeitraumbericht vorhanden. Kaufwährungs-Wiederverwendung und Eingabevereinfachung am 20.10.2026 ausdrücklich entschieden und implementiert; neue Qualifikation und Zielupdate gesondert belegen. |
| Soll / Nicht-Soll | **Soll:** Kennzahlen besitzen explizite Bedeutung, Daten-/Währungsgrenzen, Nenner und Behandlung unbekannter Werte. **Nicht-Soll:** Keine erfundene Equity, Nullgebühren, FX-Historie oder Netto-Performance. |
| Vorhandenseinsnachweis | Ausgangssuche auf e9aac2bf fand keinen passenden registrierten Consumer. Die neue registrierte Strecke zeigt vollständige SELL-Beiträge, Quellen, Perioden-/Währungsqualifikation und Datenabdeckung aus einem konsistenten Read. |
| Implementierung / Consumer | Bestehender Execution-Owner liefert gemeinsame nachvollziehbare Währungsableitung; PositionProjector liefert unveränderte SELL-Deltas. Vorhandener konsistenter performance-Reader, GET /api/v1/performance/realized-gross und Frontendroute /performance/realized-gross nutzen Definition `realized-gross-sell-v2`. [Präzisierter Vertrag und Herkunft](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). |
| Test / Commit | [Kaufwährungs-Wiederverwendung: Quellen, Vertrag und neue Qualifikation](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). Die [V1.5.9-Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) und vorherige Trace-Qualifikation bleiben historische Nachweise mit eigenem Codebezug. Synthetische Bestätigungen belegen keine Nutzerdatenwährung. |
| Fachliche Abnahme | V1-Vertrag am 17.10.2026 zur Umsetzung freigegeben. Am 20.10.2026 ausdrücklich präzisiert: Kaufwährung auch für Verkauf nutzen, so wenig zusätzliche Eingaben wie möglich (ADR-S10-008-Nachtrag). Merge und PC-Bereitstellung nach grünen Prüfungen bereits autorisiert. Keine vollständige M8- oder abschließende PC-Fachabnahme daraus abgeleitet. |
| Software-Auslieferung | V1.5.9 auf `254fe35b76027b72cd989715e17bd0ae55af55eb` veröffentlicht. [V1.5.10](../releases/V1.5.10-EXECUTION-CURRENCY-REUSE.md) ergänzt reine Owner-Währungsableitung ohne Migration; Veröffentlichung erst nach erfolgreichen aktuellen PR- und main-Prüfungen durch vorhandenen Version-Workflow. |
| Betriebsnachweis | Am 20.10.2026 meldet der Nutzer vier gesunde Dienste, `ready` und installiert 1.5.9 / `254fe35b76027b72cd989715e17bd0ae55af55eb`; lesende Berichtsansicht beobachtet. Kein Installations- oder Fachabnahmenachweis für 1.5.10 und keine Aussage über vollständige reale Währungsabdeckung. |
| Restarbeit / nächste Abhängigkeit | Neuen Wiederverwendungsschnitt fachlich am vorhandenen Bestand prüfen. Unbelegte historische Kaufwährungen bleiben unbekannt; eine belegte Kaufwährung qualifiziert die nachfolgenden gleichartigen Buchungen. Erweiterte Kennzahlen bleiben eigene Vorhaben. **Nächste Abhängigkeit:** geprüfte Auslieferung und reale Quellenabdeckung, keine Journalpflicht. |
| Umfangsentscheidung | Der enge erste Brutto-SELL-Schnitt erfüllt keinen vollständigen M8-Umfang. Statistik-/Kohorten-/Diagramm-/Exportanforderungen bleiben erhalten; weitere Kennzahlen behalten ihre eigenen offenen Fachverträge. |

</details>

<a id="pb-019-performance-statistics"></a>
<details>
<summary>PB-019 — Tradeübergreifende Statistiken</summary>

**Begrenzter Statistiknachtrag 25.10.2026:** Der neue Nutzerauftrag gibt
Trefferquote, durchschnittliches Bruttoergebnis, Median und Profit-Faktor brutto
als `closed-trade-statistics-v1` zur Umsetzung und Qualifikation bis zum
Draft-PR frei. Diese vier Kennzahlen waren im ursprünglichen ADR-S10-009 noch
ausgeschlossen. Sie verwenden ausschließlich vollständige Abschlussberichte
mit positiver Population, dieselben ungerundeten Ownerergebnisse und dieselbe
Berichtsbasis; Teilberichte liefern verständlich begründete Nullwerte.
[Neuer Vertrag, vorab bestimmte Referenzfälle und Qualifikation](../implementation/CLOSED_TRADE_STATISTICS_V1.md).
Die bisherigen Kohorten-/Quellennachweise bleiben erhalten. Dieser Auftrag
autorisiert keinen Merge, Release, Tag oder PC-Update; insbesondere wird die
frühere Freigabe für #278 nicht übertragen.

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Statistiken. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Technical Review; enger Abschlussbericht `closed-trade-gross-v1` nach ausdrücklicher Kohorten-, Abdeckungs- und Signumfreigabe implementiert. Vollständige M8-Statistik bleibt eigener Restumfang. |
| Soll / Nicht-Soll | **Soll:** Aggregation erklärt Population, offene/geschlossene Trades, Korrekturen und Filter. **Nicht-Soll:** Keine undefinierte Grundgesamtheit oder aus Teildaten abgeleitete Erfolgsquote. |
| Vorhandenseinsnachweis | Eigene lesende Abschlussübersicht: ein Trade pro stabiler ID, tatsächlicher Vollabschluss als Periodenquelle, vollständiges qualifiziertes Bruttoergebnis aller wirksamen Verkäufe sowie positive, negative und exakt neutrale Zähler. Sichtbare Datenlücken und acht disjunkte Fallgruppen verhindern scheinbar vollständige Summen. |
| Implementierung / Consumer | Bestehender PositionProjector, Execution-Währungsresolver und konsistenter Performance-Reader unverändert wiederverwendet. Neuer GET `/api/v1/performance/closed-trades` und registrierte Frontendroute `/performance/closed-trades`; [Vertrag](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md), [Quellen und Qualifikation](../implementation/CLOSED_TRADES_REPORT_QUALIFICATION.md). Keine Journalvoraussetzung und keine zweite Geldrechnung. Der getrennte [Quellenintegrationsschnitt](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md) ergänzt den lesenden Einzeltradeweg, sichere Filter-/Seitenrückkehr und ehrlichen Vergleich der gesamten Reportgrundlage; die aktuelle technische Qualifikation ist head-/treegebunden im Integrations-PR zu lesen und nicht mit Auslieferung gleichzusetzen. |
| Test / Commit | [PR #270](https://github.com/burckhju/trading-workspace/pull/270) bindet finalen Head/Checkout/Tree, unveränderte Gates und native Artefakte. Neue Domain-/API-, PostgreSQL-Race-, UI- und Owner-Browserfälle verwenden die vorab festgelegten T1–T6-Werte; [Prüfmatrix](../implementation/CLOSED_TRADES_REPORT_QUALIFICATION.md). Frühere Proposal-Läufe sind kein Kohortennachweis. **Nachtrag 23.10.2026:** Gemeinsamer Entwicklungsstand aus aktuellem Main, #273 und #269; vollständiges Tradeergebnis und SELL-Periodenergebnis bleiben getrennt. Keine Auslieferung durch die bereits vorhandene Versionsnummer 1.5.12. [Gemeinsamer Nachweisvertrag](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md); exakte aktuelle Head-/Tree-/Run-/Artefaktbindung in [PR #273](https://github.com/burckhju/trading-workspace/pull/273), Herkunft #269 bleibt separat. |
| Fachliche Abnahme | Nach Erläuterung der drei Nutzerwirkungen am 20.10.2026 mit „ok, umsetzen“ zur Implementierung freigegeben (ADR-S10-009). Keine Abnahme der fertig installierten Abschlussübersicht oder des vollständigen M8-Umfangs daraus abgeleitet. |
| Software-Auslieferung | Neuer Abschlussbericht als Entwicklungs-PR; kein neuer Merge-/Release- oder Versionsnachweis. Vorhandener SELL-Bericht bleibt eigenständig `realized-gross-sell-v2`. |
| Betriebsnachweis | Keine PC-Installation oder Bedienabnahme der neuen Abschlussübersicht nachgewiesen. Synthetische Bestätigungen sind keine Aussage über reale Nutzerwährungen. |
| Restarbeit / nächste Abhängigkeit | Technische PR-Prüfung und gesonderte fachliche Bedienabnahme. Trefferquote, Durchschnitt, Median und Profit-Faktor besitzen seit dem begrenzten Auftrag vom 25.10.2026 ihren eigenen [V1-Vertrag](../implementation/CLOSED_TRADE_STATISTICS_V1.md); deren neue Nachweise sind headgebunden im Statistik-PR zu prüfen. Diagramme, Export und breitere M8-Anforderungen bleiben offen. **Nächste Abhängigkeit:** aktuelle vollständige PR-Nachweise und passende tatsächliche Freigabe für Integration/Auslieferung. |
| Umfangsentscheidung | Die drei engen Kohortenregeln sind entschieden; ursprüngliches M8 bleibt sichtbar. Kein Netto-/FX-/Equity-Modell, keine Modellaktivierung und keine pauschale Erledigung weiterer Statistikanforderungen. |

</details>

<a id="pb-019-performance-dashboards"></a>
<details>
<summary>PB-019 — Performance-Dashboards</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Dashboards. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Technical Review; enger SELL-Zeitraumbericht vorhanden. Kaufwährungs-Wiederverwendung und Eingabevereinfachung am 20.10.2026 ausdrücklich entschieden und implementiert; neue Qualifikation und Zielupdate gesondert belegen. |
| Soll / Nicht-Soll | **Soll:** Lesende Auswertung zeigt Kennzahlen, Grenzen, Datenlücken und Herkunft verständlich. **Nicht-Soll:** Operational Workspace und Marktcharts sind kein Performance-Dashboard; keine Frontend-Zweitberechnung. |
| Vorhandenseinsnachweis | Ausgangssuche auf e9aac2bf fand keinen passenden registrierten Consumer. Die neue registrierte Strecke zeigt vollständige SELL-Beiträge, Quellen, Perioden-/Währungsqualifikation und Datenabdeckung aus einem konsistenten Read. |
| Implementierung / Consumer | Bestehender Execution-Owner liefert gemeinsame nachvollziehbare Währungsableitung; PositionProjector liefert unveränderte SELL-Deltas. Vorhandener konsistenter performance-Reader, GET /api/v1/performance/realized-gross und Frontendroute /performance/realized-gross nutzen Definition `realized-gross-sell-v2`. [Präzisierter Vertrag und Herkunft](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). |
| Test / Commit | [Kaufwährungs-Wiederverwendung: Quellen, Vertrag und neue Qualifikation](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). Die [V1.5.9-Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) und vorherige Trace-Qualifikation bleiben historische Nachweise mit eigenem Codebezug. Synthetische Bestätigungen belegen keine Nutzerdatenwährung. |
| Fachliche Abnahme | V1-Vertrag am 17.10.2026 zur Umsetzung freigegeben. Am 20.10.2026 ausdrücklich präzisiert: Kaufwährung auch für Verkauf nutzen, so wenig zusätzliche Eingaben wie möglich (ADR-S10-008-Nachtrag). Merge und PC-Bereitstellung nach grünen Prüfungen bereits autorisiert. Keine vollständige M8- oder abschließende PC-Fachabnahme daraus abgeleitet. |
| Software-Auslieferung | V1.5.9 auf `254fe35b76027b72cd989715e17bd0ae55af55eb` veröffentlicht. [V1.5.10](../releases/V1.5.10-EXECUTION-CURRENCY-REUSE.md) ergänzt reine Owner-Währungsableitung ohne Migration; Veröffentlichung erst nach erfolgreichen aktuellen PR- und main-Prüfungen durch vorhandenen Version-Workflow. |
| Betriebsnachweis | Am 20.10.2026 meldet der Nutzer vier gesunde Dienste, `ready` und installiert 1.5.9 / `254fe35b76027b72cd989715e17bd0ae55af55eb`; lesende Berichtsansicht beobachtet. Kein Installations- oder Fachabnahmenachweis für 1.5.10 und keine Aussage über vollständige reale Währungsabdeckung. |
| Restarbeit / nächste Abhängigkeit | Bestehende Zeitraum-/Quellenansicht mit direkt eingegebener und wiederverwendeter Währung am PC prüfen. Vollständige lokale Pagination und Schutz gegen verspätete Antworten erhalten. Weitergehende Dashboards, Diagramme und Export bleiben eigene Restanforderungen. **Nächste Abhängigkeit:** neuer geprüfter Schnitt und getrennte Abnahme. |
| Umfangsentscheidung | Der enge erste Brutto-SELL-Schnitt erfüllt keinen vollständigen M8-Umfang. Statistik-/Kohorten-/Diagramm-/Exportanforderungen bleiben erhalten; weitere Kennzahlen behalten ihre eigenen offenen Fachverträge. |

</details>

<a id="pb-019-performance-evaluations"></a>
<details>
<summary>PB-019 — Perioden- und Tradeauswertungen</summary>

**UI-Nachtrag 25.10.2026:** Auf ausdrücklichen Nutzerwunsch ist die
Berichtswährung in Verkaufs- und Abschlussübersicht fest EUR. Vorhandene
Nicht-EUR-Listenlinks werden ohne stillen Ersatzread erklärt; Buchungswährungen,
Quellen und Definitionen bleiben unverändert. [Umfang und neue
Qualifikation](../implementation/REPORT_EUR_UI_QUALIFICATION.md). Dies ist kein
Nachweis vollständiger realer Währungsabdeckung oder einer neuen Auslieferung.

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M8: Auswertungen. Bereich/Querschnitt: 8. Bestehender Bezug: FT-012; vorhandener Evaluation-Owner. Lieferziel: C. |
| Arbeitsstatus | Technical Review; enger SELL-Zeitraumbericht vorhanden. Kaufwährungs-Wiederverwendung und Eingabevereinfachung am 20.10.2026 ausdrücklich entschieden und implementiert; neue Qualifikation und Zielupdate gesondert belegen. |
| Soll / Nicht-Soll | **Soll:** Explizite Zeit-/Tradeauswahl, Stichtag und nachvollziehbare Berechnungsgrenzen. **Nicht-Soll:** Keine stillen historischen Rekonstruktionen eines damals unbekannten Datenstands. |
| Vorhandenseinsnachweis | Ausgangssuche auf e9aac2bf fand keinen passenden registrierten Consumer. Die neue registrierte Strecke zeigt vollständige SELL-Beiträge, Quellen, Perioden-/Währungsqualifikation und Datenabdeckung aus einem konsistenten Read. |
| Implementierung / Consumer | Bestehender Execution-Owner liefert gemeinsame nachvollziehbare Währungsableitung; PositionProjector liefert unveränderte SELL-Deltas. Vorhandener konsistenter performance-Reader, GET /api/v1/performance/realized-gross und Frontendroute /performance/realized-gross nutzen Definition `realized-gross-sell-v2`. [Präzisierter Vertrag und Herkunft](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). |
| Test / Commit | [Kaufwährungs-Wiederverwendung: Quellen, Vertrag und neue Qualifikation](../implementation/EXECUTION_CURRENCY_REUSE_QUALIFICATION.md). Die [V1.5.9-Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md) und vorherige Trace-Qualifikation bleiben historische Nachweise mit eigenem Codebezug. Synthetische Bestätigungen belegen keine Nutzerdatenwährung. |
| Fachliche Abnahme | V1-Vertrag am 17.10.2026 zur Umsetzung freigegeben. Am 20.10.2026 ausdrücklich präzisiert: Kaufwährung auch für Verkauf nutzen, so wenig zusätzliche Eingaben wie möglich (ADR-S10-008-Nachtrag). Merge und PC-Bereitstellung nach grünen Prüfungen bereits autorisiert. Keine vollständige M8- oder abschließende PC-Fachabnahme daraus abgeleitet. |
| Software-Auslieferung | V1.5.9 auf `254fe35b76027b72cd989715e17bd0ae55af55eb` veröffentlicht. [V1.5.10](../releases/V1.5.10-EXECUTION-CURRENCY-REUSE.md) ergänzt reine Owner-Währungsableitung ohne Migration; Veröffentlichung erst nach erfolgreichen aktuellen PR- und main-Prüfungen durch vorhandenen Version-Workflow. |
| Betriebsnachweis | Am 20.10.2026 meldet der Nutzer vier gesunde Dienste, `ready` und installiert 1.5.9 / `254fe35b76027b72cd989715e17bd0ae55af55eb`; lesende Berichtsansicht beobachtet. Kein Installations- oder Fachabnahmenachweis für 1.5.10 und keine Aussage über vollständige reale Währungsabdeckung. |
| Restarbeit / nächste Abhängigkeit | Nach Auslieferung die vorhandene Zeitraumauswahl erneut lesend prüfen: qualifizierte Käufe benötigen keine Einzelbestätigung ihrer Verkäufe. **Nächste Abhängigkeit:** v1.5.10 auf erfolgreich geprüftem main-Commit; danach technischer PC-Status und gesonderte fachliche Quellenkontrolle. Keine erneute pauschale Veröffentlichungsfreigabe erforderlich. |
| Umfangsentscheidung | Der enge erste Brutto-SELL-Schnitt erfüllt keinen vollständigen M8-Umfang. Statistik-/Kohorten-/Diagramm-/Exportanforderungen bleiben erhalten; weitere Kennzahlen behalten ihre eigenen offenen Fachverträge. |

</details>

### PB-020

[Modellinfrastruktur: Evidence bis Freigabe](#pb-020-governance) · [Gesonderte Runtime-Aktivierung und Rückkehr](#pb-020-activation) · [Stopmodell](#pb-020-stop-model) · [Zielmodell](#pb-020-target-model) · [Trade Assistant](#pb-020-assistant) · [Nachbeobachtungsmodell](#pb-020-observation-model) · [TOP_DOWN_CANDIDATE als konkrete Modellfamilie](#pb-020-candidate-family) · [MarketContext als fachliche Modellfamilie](#pb-020-market-context) · [Relative Strength als fachliche Modellfamilie](#pb-020-relative-strength)

<a id="pb-020-governance"></a>
<details>
<summary>PB-020 — Modellinfrastruktur: Evidence bis Freigabe</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: gemeinsame Governance der Modellfamilien. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013; FT-012 besitzt Evidence. Lieferziel: D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Explizite Hypothese, Proposal gegen konkrete genehmigte Basis, cutoffgebundene Validierung und Freigabe erzeugen eine neue immutable ModelVersion. **Nicht-Soll:** Freigabe ist weder Runtime-Aktivierung noch Handelsentscheidung; keine rückwirkende Evidence-Umschreibung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-013 Controlled Governance V1](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-013_CONTROLLED_MODEL_GOVERNANCE.md); [historische Governance-Naht](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md); Model-Governance-API in main registriert; [Candidate-Konfigurationsconsumer](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md). |
| Test / Commit | Historischer PostgreSQL-Golden-Path weist gezielte Flush-Korrekturen nach; aktuelle Basis-CI; keine neue vollständige Governance-Abnahme. **Strang B, 24.10.2026:** [begrenzte Proposal-Kontextqualifikation](../implementation/MODEL_PROPOSAL_CONTEXT_QUALIFICATION.md) gegen Main `2887d39b`: kontrollierte rote/grüne Component- und Browsernachweise für Hypothese/Modell/APPROVED-Basis, synchrone Doppelübermittlungssperre und gebundene Save-Antwort; bestehende Parent-Isolation erhalten. Zusätzlicher nativer PostgreSQL-Test prüft die bereits vorhandene Ablehnung eines falschen Modell/Basis-Paars ohne teilweise Governancefakten. Aktuelle vollständige CI und exakter Head/Checkout/Tree stehen im zugehörigen Entwicklungs-PR; lokale Mocktests ersetzen diese nicht. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. **B, 25.10.2026:** [Candidate-Governance-Fortsetzung](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md) ab `fbd77fb9`/v1.5.14: exakte historische Lessonbindung, gespeicherte Validation-Evidence-IDs und generische Hypothesen-Workspacegrenze gezielt lokal geprüft; #274 erhalten. Der erste echte S2–S6-Gesamtfall bestand in Run `40166152063`/Job `121087501390` auf Head `1109f047` ohne Retry/Skip/Flaky; Quellenketten und Cleanup geprüft. Native Cutoff-/Scope-/Stale-Fälle und vollständige finale Head-/CI-Bindung werden im PR #276 gesondert belegt. **#278-Fortsetzung, 25.10.2026:** Der bestehende Governance-Browserweg wird mit neuen FT-006-Quellen qualifiziert; Hypothese/L1, Evidence/Cutoff, Approval, Aktivierung und #274-Kontextschutz bleiben gleich. [FT-006-Nachweis](../implementation/FT006_SOURCE_QUALITY_QUALIFICATION.md): native Ausführung auf `18e3e141` in Run `40182968277` / Job `121137734172`, Versuch 1 bestanden; exakte historische L1/Evidence-/Approvalbindung und drei GOOD-Quellen tatsächlich geprüft. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Konkreten Kandidatenregel-Fall mit Basis-/Evidence-/Cutoff-Provenienz und expliziten Benutzeraktionen qualifizieren. **B, 25.10.2026:** Den nach nativer Sichtprüfung ergänzten Parent-Statusreadback sowie PostgreSQL-Grenzfälle und sämtliche regulären Gates am letzten Head binden; die erste vollständige Browserreise ist mit konkreten IDs/Requests/Readbacks im Bericht belegt. Gespeicherte Validation bleibt ein begründeter Befund, kein Backtest; keine neue SUPPORTS-only-Freigaberegel. **Nächste Abhängigkeit:** Bestehende LearningEvidence; freigegebene konkrete fachliche Regel. |
| Umfangsentscheidung | Vorhandene Governance wiederverwenden; der alte PB-020-Status Not Started ist überholt. |

</details>

<a id="pb-020-activation"></a>
<details>
<summary>PB-020 — Gesonderte Runtime-Aktivierung und Rückkehr</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: reproduzierbare Anwendung freigegebener Modelle. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance; technische Qualität/Betrieb. Bestehender Bezug: FT-013; vorhandener Candidate-Consumer FT-005/FT-019/FT-020. Lieferziel: D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Explizite Aktivierung einer kompatiblen freigegebenen Version, konkrete Aktivierungsherkunft und kontrollierte Rückkehr zu früherer Version. **Nicht-Soll:** Keine Aktivierung durch Installation, Migration, Review oder Modellfreigabe. |
| Vorhandenseinsnachweis | Vorhandener Code beziehungsweise tatsächlicher Consumer statisch gelesen; nur der im Implementierungsfeld benannte Teilscope ist dadurch belegt. |
| Implementierung / Consumer | [RuntimeActivationService.activate / resolve_by_key](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/model/service/runtime_activation_service.py) verlangt APPROVED und schreibt eine neue Aktivierung; auch frühere APPROVED-Versionen sind im Service nicht ausgeschlossen. [FT-020](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md) trennt Approval/Activation. |
| Test / Commit | Statische Serviceprüfung am Basiscommit; vollständiger Candidate-Consumer-, Konkurrenz-, Replay- und Rückkehrtest nicht neu verifiziert. Basis-CI ist nur Gesamtnachweis. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. **B, 25.10.2026:** [Gezielte Fortsetzung](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md) ergänzt die im tatsächlichen Consumer fehlende bewusste Auswahl der initialen kompatiblen APPROVED-Version A. Lokale Fälle prüfen A-Rückkehr über denselben Owner, fehlerhafte Reads, Doppelaktion und späte Antworten. Kein neuer Aktivierungsowner. Der echte A→B→A-Browserlauf `40166152063` bestand retryfrei; drei getrennte Aktivierungs-IDs, unveränderte B-/A-Historie, Desktop/Mobil und restloses Cleanup sind geprüft. Finale CI des letzten Heads wird separat gebunden. **#278-Fortsetzung, 25.10.2026:** derselbe geschützte A/A/B/A-Fall erhält drei explizite 1.0.1-GOOD-Analysequellen; keine Änderung des Aktivierungsowners oder der beiden Candidate-Policies. Neuer nativer Abschluss auf `18e3e141` in Run `40182968277` / Job `121137734172`, Versuch 1 bestanden: APPROVED-B lässt A aktiv; separate B-/A-Aktivierungen und unveränderte historische Evaluationen aus denselben drei GOOD-Quellen sind im datierten Bericht belegt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Eine konkrete Regel über Aktivierung, Candidate-Anwendung und Rückkehr auf exakte frühere Version nachweisen; nicht erneut implementieren, sofern belegt. **B, 25.10.2026:** Freigabe von B bei weiter aktivem A, eine weitere A-Evaluation, explizite B-/A-Aktivierungen und unveränderte Historie sind im ersten nativen Pass belegt. Nachfolgende Heads erhalten ihren eigenen CI-/Artefaktbezug; Clientlocks sind keine globale Exactly-once-Garantie. **Nächste Abhängigkeit:** Kompatible Kandidatenmodellversion; explizite Freigabe; aktuelle Runtime-Adapterprüfung. |
| Umfangsentscheidung | Die alte V1- und Golden-Path-Aussage ohne Runtime-Aktivierung ist historisch. Vorhandener Service schließt die Infrastruktur-Lücke, nicht jede Modellfamilien-/Betriebsabnahme. |

</details>

<a id="pb-020-stop-model"></a>
<details>
<summary>PB-020 — Stopmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Stopmodell. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 Governance; FT-007/FT-010 fachliche Consumer. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Eine konkrete fachliche Stopmodellfamilie hat definierte Inputs, Versionen und Consumer. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Stopmanagement und gebundene Stopprüfung](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md) sowie Planparameter sind vorhanden; daraus folgt kein vollständig governter Stopmodell-Consumer. |
| Test / Commit | Kein vollständiger familienbezogener Test-/Abnahme-/Betriebsnachweis verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Geltende Modellentscheidung und aktuellen Consumer identifizieren; fehlende fachliche Modellgrenzen entscheiden. **Nächste Abhängigkeit:** Bestehende fachliche Entscheidungen oder expliziter Entscheidungsvorschlag; konkrete Daten/Consumer. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-target-model"></a>
<details>
<summary>PB-020 — Zielmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Zielmodell. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 Governance; FT-007/FT-010 fachliche Consumer. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Eine konkrete Zielmodellfamilie ist fachlich definiert und reproduzierbar anwendbar. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Zielmanagement](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md) ist kein Nachweis eines eigenständigen governbaren Zielmodells. |
| Test / Commit | Kein vollständiger familienbezogener Test-/Abnahme-/Betriebsnachweis verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Modellfamilie von manuellen Planzielen und Monitoringregeln abgrenzen. **Nächste Abhängigkeit:** Bestehende fachliche Entscheidungen oder expliziter Entscheidungsvorschlag; konkrete Daten/Consumer. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-assistant"></a>
<details>
<summary>PB-020 — Trade Assistant</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Trade Assistant. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 laut ursprünglichem Modellplan; konkrete fachliche Consumer-/Ownershipentscheidung offen. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Eine begrenzte, nachvollziehbare Entscheidungsunterstützung mit explizitem Versionsbezug. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Ursprünglicher Modellkatalog](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md); Workspace/Plan-/Risikosichten liefern Unterstützung, aber keinen vollständigen Trade-Assistant-Modellnachweis. |
| Test / Commit | Kein vollständiger familienbezogener Test-/Abnahme-/Betriebsnachweis verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Konkreten Nutzen und Modell-/Consumervertrag entscheiden, vorhandene Unterstützung nicht parallel nachbauen. **Nächste Abhängigkeit:** Bestehende fachliche Entscheidungen oder expliziter Entscheidungsvorschlag; konkrete Daten/Consumer. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-observation-model"></a>
<details>
<summary>PB-020 — Nachbeobachtungsmodell</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M9: Nachbeobachtungsmodell. Bereich/Querschnitt: Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-011 fachlicher Consumer; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Definierte Nachbeobachtungslogik mit konkretem historischen Modellbezug. **Nicht-Soll:** Keine erfundenen Handels-/Scoring-/Risikoschwellen; generische Modellinfrastruktur belegt nicht diese Familie. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [FT-011 nutzt einen definierten Horizont und build_observation_evidence](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/post_trade/application/observation_service.py); eigenständige governte Modellfamilie nicht verifiziert. |
| Test / Commit | Kein vollständiger familienbezogener Test-/Abnahme-/Betriebsnachweis verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Vorhandene fachliche Logik, Modellversionierung und Runtime-Governance getrennt nachweisen. **Nächste Abhängigkeit:** Bestehende fachliche Entscheidungen oder expliziter Entscheidungsvorschlag; konkrete Daten/Consumer. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-candidate-family"></a>
<details>
<summary>PB-020 — TOP_DOWN_CANDIDATE als konkrete Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2/M9: spätere Präzisierung, FT-019/FT-020. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-005, FT-013, FT-019, FT-020. Lieferziel: D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Die bestehende konkrete Kandidatenregel über Hypothese, Proposal, Validation, Approval, separate Aktivierung und Anwendung nachvollziehen. **Nicht-Soll:** Keine neue Candidate-Strecke oder automatische Auswahl/Aktivierung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [FT-020 beschreibt 1.0→2.0 und 2.0→2.0 ohne Mutation](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md) mit zulässigen expliziten Policies und read-only unbekannten Definitionen; [ActivationService](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/model/service/runtime_activation_service.py). **#278-Fortsetzung, 25.10.2026:** Bestehender Resolver/Readiness liest auch exakte native MARKET_REFERENCE-Analysen; ältere Listing-Bridge bleibt für Identitäten ohne natives Instrument erhalten. Keine Policy-/Aggregationsänderung. |
| Test / Commit | Code der Aktivierung gelesen; konkreter Candidate-Adapter und seine vollständigen Regressionstests nicht neu qualifiziert. **Strang B, 24.10.2026:** [Proposal-Integritätsnachweis](../implementation/MODEL_PROPOSAL_CONTEXT_QUALIFICATION.md) erhält die fünf bestehenden FT-020-Fälle und ergänzt explizite V1→V2-/beidseitige V2-Payloads, No-op sowie unbekannte/unvollständige Definitionen. Der echte Lesson-Browserweg erzeugt nur DRAFT und keine Validation-/Approval-/Aktivierungsschreibaufrufe. Dies qualifiziert die Eingabestrecke, keine bessere Handelsregel oder neue Fach-/Betriebsabnahme. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. **B, 25.10.2026:** [Aktueller Nachweisstand](../implementation/CANDIDATE_GOVERNANCE_JOURNEY_QUALIFICATION.md) hält die beiden V2-Policies und V1-Verträge fest; tatsächliche Modell- und gespeicherte Analysequellenprojektion sowie genaue historische UI-Auswahl lokal geprüft. 59 Backend-, 115 UI- und 153 reine Runnerfälle sind getrennte gezielte lokale Ergebnisse, keine finale Gesamt-CI. Der neue native Fall bestand erstmals in Run `40166152063`/Job `121087501390`: identische ownererzeugte Analyseinputs, tatsächliche A→B→A-Ausführung und unveränderte historische Ergebnisse mit Qualität LIMITED. Vollständige finale CI steht gesondert im PR #276. **#278-Fortsetzung:** vorhandener geschützter Browserfall auf GOOD-Quellen mit echten Referenzidentitäten, Legacy-Reproduktion sowie eigenständige LIMITED-/INSUFFICIENT-Negative erweitert; 22 gezielte Candidate-Unitfälle bestanden. Browserausführung auf `18e3e141` bestanden: Run `40182968277` / Job `121137734172`, Versuch 1, genau ein Fall ohne Retry/Skip/Flaky. Alle fünf bisherigen nativen Ownerfälle bestanden ebenfalls; Gesamt-CI und Folgecommit werden im PR getrennt gebunden. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Genau einen bestehenden Policy-Wechsel samt unverändertem Basismodell, konkreter Anwendung und Rückkehr belegen. **B, 25.10.2026:** Der isolierte native LIMITED-A→B→A-Weg ist tatsächlich bestanden; finalen Head einschließlich Statusreadback und allen regulären Gates gesondert qualifizieren. B07 bleibt für die verlangte GOOD-Referenz offen, weil die bestehende FT-006-Ownerpipeline VALID-Preise als LIMITED auswertet; keine Qualitätsfixture oder Semantikänderung in diesem Schnitt. Eine gesonderte FT-006-Klärung und erneute GOOD-Referenzprüfung ist dafür abhängig. **Nächste Abhängigkeit:** PB-020 Governance / Aktivierung; freigegebene Evidence und kompatible Policy. **Datierter Nachtrag #278, 25.10.2026:** B07 ist für die technische GOOD-Referenz geschlossen: Head `18e3e1411b98d54812850ce006ce24c5ceab874d`, Tree `4c0abfea18cc6fbe48dd647f25ceeb3f37d4a2f6`, Testmerge `71f167371e35e6ba5c5dc6432270c1fa3d259245`, [Run `40182968277` / Job `121137734172`, Versuch 1](https://github.com/burckhju/trading-workspace/actions/runs/40182968277/job/121137734172), [Artefakt `12594962453`](https://github.com/burckhju/trading-workspace/actions/runs/40182968277/artifacts/12594962453). Drei echte GOOD-Owneranalysen ergeben A/A/B/A → QUALIFIED/QUALIFIED/NOT_QUALIFIED/QUALIFIED; vollständige Quellen, Prüfsummen, Readfenster, sechs gesichtete Desktop-/Mobilbilder und Cleanup sind im bestehenden Bericht nachgewiesen. Der historische LIMITED-Nachweis oben bleibt unverändert gültig. Erster Frontend-Gesamtlauf fehlgeschlagen; eng reproduzierter Select-Laderace ist ausschließlich im Test korrigiert. Finale Gesamt-CI steht mit eigenem Head/Tree im PR #278; B07 ersetzt keine Fach-/Merge-/Release-/Betriebsabnahme und keinen M8/M9-Gesamtabschluss. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-market-context"></a>
<details>
<summary>PB-020 — MarketContext als fachliche Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2/M9: spätere Top-down-Präzisierung. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006 / FT-005; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Fachliche Berechnung, historische Version und tatsächlicher Runtime-Consumer bleiben genau referenzierbar. **Nicht-Soll:** Governance der Kandidatenregel beweist nicht automatisch eine eigenständig governte Aktivierung dieser Familie. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Top-down-Regeltraceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [Analyse→Market Context/Relative Strength→Candidate](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md). Eigene Governance-/Aktivierungskette nicht vollständig verifiziert. |
| Test / Commit | Historische Domain-/Top-down-Fixturen referenziert; kein familienbezogener aktueller Aktivierungsnachweis. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Runtime-Verwendung und eigenständige Modellversionierung von vorhandener Candidate-Policy unterscheiden. **Nächste Abhängigkeit:** Geltender Analysevertrag; tatsächlicher Consumer; keine erfundene Parametrisierung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="pb-020-relative-strength"></a>
<details>
<summary>PB-020 — Relative Strength als fachliche Modellfamilie</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M2/M9: spätere Top-down-Präzisierung. Bereich/Querschnitt: 3; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-006 / FT-005; FT-013 Governance. Lieferziel: D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Fachliche Berechnung, historische Version und tatsächlicher Runtime-Consumer bleiben genau referenzierbar. **Nicht-Soll:** Governance der Kandidatenregel beweist nicht automatisch eine eigenständig governte Aktivierung dieser Familie. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Top-down-Regeltraceability](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/foundation/TRACEABILITY.md); [Analyse→Market Context/Relative Strength→Candidate](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/implementation/POST_D01_GOLDEN_PATH_CLOSEOUT.md). Eigene Governance-/Aktivierungskette nicht vollständig verifiziert. |
| Test / Commit | Historische Domain-/Top-down-Fixturen referenziert; kein familienbezogener aktueller Aktivierungsnachweis. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Runtime-Verwendung und eigenständige Modellversionierung von vorhandener Candidate-Policy unterscheiden. **Nächste Abhängigkeit:** Geltender Analysevertrag; tatsächlicher Consumer; keine erfundene Parametrisierung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

### Bestehende unnummerierte Fähigkeiten und Querschnittsarbeit

[Datenprovider und benutzerverwaltete Konfiguration](#provider-configuration) · [Marktdatenbereitschaft, Qualität und Herkunft](#market-data-quality) · [Datenaktualisierung und Schedulerzustände](#market-data-refresh) · [Kursprotokoll und versionierte Produktbelege](#market-data-evidence) · [IV-Datenbereitschaft und hypothetisches Modelllabor](#iv-risk-lab) · [Regelüberwachung und fachliche Alerts](#monitoring-rules) · [Benachrichtigungen und Zustellzustände](#notification-delivery) · [Erinnerungen](#reminders) · [Modellüberwachung](#model-monitoring) · [Täglicher Operational Workspace](#operational-workspace) · [Performanceoptimierung](#operations-optimization) · [Stabilität und sichere Betriebsgrenzen](#operations-stability) · [Regressionstests](#operations-regression) · [Releasevorbereitung und Softwarestand](#operations-release) · [Betriebsnachweis der identifizierten Zielinstallation](#operations-installation)

<a id="provider-configuration"></a>
<details>
<summary>unnummeriert — Datenprovider und benutzerverwaltete Konfiguration</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Datenprovider. Bereich/Querschnitt: 1, 2. Bestehender Bezug: separates Providerfeature; TC-001 nur technische Dateninfrastruktur. Lieferziel: A. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Provider-/Quellenidentität, Rechte und bewusste Einrichtung haben eindeutige Ownership. **Nicht-Soll:** TC-001 wird nicht zum erfundenen fachlichen Stammdatenowner; keine neue Zustimmung oder kostenpflichtiger Abruf. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Bestehende Providergrenze](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md); Marktdaten-/Referenzadministration in [registrierten Routern](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py). |
| Test / Commit | Aktuelle Konfigurations-/Rechteabnahme nicht geprüft; Ordnername provider ist kein Fehlbeleg. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Benutzerverwaltete Providerkonfiguration vom vorhandenen technischen Routing abgrenzen; fehlenden fachlichen Zuschnitt als Entscheidungsvorschlag führen. **Nächste Abhängigkeit:** Bestehende Administration und tatsächlich genutzte Consumer. |
| Umfangsentscheidung | Original M1 bleibt offen, soweit nicht belegt. Vorhandener Katalog sieht ein separates später zu spezifizierendes Providerfeature vor; keine neue FT-Nummer. |

</details>

<a id="market-data-quality"></a>
<details>
<summary>unnummeriert — Marktdatenbereitschaft, Qualität und Herkunft</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M1: Datenprovider; M2: Datenbasis; spätere TC-001-Fähigkeit. Bereich/Querschnitt: 2. Bestehender Bezug: TC-001; fachliche Consumer bleiben Eigentümer ihrer Ergebnisse. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Fehlende, veraltete, indikative und nicht anwendbare Daten sowie Kurs-, Abruf- und Erfassungszeiten unterscheiden. **Nicht-Soll:** Erfolgreicher Abruf ersetzt keine aktuelle verwertbare Quote; unbekannt ist nicht Null oder geringes Risiko. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Market-Data-/Reference-Router](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py); [NOT_EVALUABLE bei fehlender Datenquelle](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/product_selection/service/application.py); [1.5.5 Abrufdiagnose](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.5.5-ISSUER-COVERAGE.md) trennt Jobstatus und Kursnachweis. |
| Test / Commit | Historische Basis-CI bleibt erhalten. C-Vorherstand auf `3d47732665c8b66984923d88a65cf99e74d96791` (Produktionsbasis `5e9ede2`, Dokumentationshead `bade0e33`): 322 gezielte Tests bestanden, davon 31 neue Charakterisierungen; originale Kurs-/Abrufzeiten, Fehlerreuse und alte lokale Dateien geprüft. Nach der Nutzerentscheidung für Variante 2 wurden dieselben Datenqualitätsgrenzen am neuen Prüfcommit `187c16b63e0d4dc16b2204f80aec4533c34173e6` erneut qualifiziert; gezielte Gesamtsuite: `344 bestanden, 0 Fehler/Skips/Deselektionen`. [Getrennte Nachweise und Grenzen](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md). Aktuelle Diagnose-Liveabnahme / Quoten / Providerrechte auf JMBbot weiterhin nicht geprüft. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Qualifizierte Daten-/Readinesszustände für konkrete tägliche Aufgaben und Positionen belegen. Die technische Quellenmodusprüfung ersetzt keine reale Coverage-/Rechteabnahme. **Nächste Abhängigkeit:** Identifizierte Zielinstallation, vorhandene Rechte und unveränderte erlaubte Abrufwege. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="market-data-refresh"></a>
<details>
<summary>unnummeriert — Datenaktualisierung und Schedulerzustände</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Datenaktualisierung. Bereich/Querschnitt: 2, 6; Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: TC-001; bestehender Scheduler, keine neue FT-Nummer. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Abrufzustände und Datenbereitschaft nachvollziehbar zeigen; vorhandene Providergrenzen erhalten. **Nicht-Soll:** Kein Diagnoselauf mit unbeabsichtigtem Schreiben/Versand; neue Planung ist keine Providerzustimmung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Historische Schedulerbasis `5e9ede2`](https://github.com/burckhju/trading-workspace/blob/5e9ede2dc29f52eaff601d30614df6bc9c25c426/backend/app/features/market_data/service/refresh.py): vorhandene fünf Lanes und begrenzter Same-Cycle-Retry. Die beschlossene Variante 2 begrenzt `_pace()` im bestehenden `_warrant`-Pfad auf `PUBLIC_WEBSITE`; normalisierte HTTPS-/Datei-Quoteaufrufe gehen direkt an den vorhandenen Resolver. Providerroute statt MIC bestimmt weiter den Aufruf; Publicdiscovery und Clientgrenzen bleiben erhalten. [Entscheidung und Consumerinventar](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md). Die dokumentierten historischen #225/#235-Lane-Anteile sind kein zusätzlich zu übernehmender Umfang. |
| Test / Commit | Historischer C-Stand: `3d47732665c8b66984923d88a65cf99e74d96791`, Tree `1b8dd1badb32e9a9d017ffd44656065f1021ac4b`, Dokumentationshead `bade0e33`: 322 gezielte Tests und vollständige Ruff-/Black-/mypy-Prüfungen bestanden; damals 14 s Zusatzpause in allen drei Modi, Public 2 HTTP vs. Snapshot 1 Zugriff, Konkurrenz/Cancellation geprüft. Neuer Prüfcommit `187c16b63e0d4dc16b2204f80aec4533c34173e6`, gezielte Gesamtsuite `344 bestanden, 0 Fehler/Skips/Deselektionen`. Identische neue Drei-Modus-Matrix vor/nach Änderung: vorher 2 fehlgeschlagen/1 bestanden, nachher 3 bestanden, jeweils 3 bewusst deselektiert; keine Gesamtsuitenbehauptung daraus. [Nachtrag, A01–A14 und Grenzen](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md#nachtrag-variante-2-entschieden). Keine reale Schedulerbeobachtung. |
| Fachliche Abnahme | Die Nutzeranweisung „wie vorgeschlagen gezielt ändern“ entscheidet Variante 2 und beendet die offene Frage zur zusätzlichen Snapshot-Schedulerpause. Public-Pacing, Rechte und Clientgrenzen bleiben unverändert. Damit ist diese begrenzte Semantik entschieden; eine eigenständige fachliche Abnahme des vollständigen Zuschnitts ist weiterhin nicht verifiziert. |
| Software-Auslieferung | Nutzerfreigabe für Merge und PC-Bereitstellung bei grünen Prüfungen liegt vor. Der begrenzte Quellenmodus-Schnitt wird als [v1.5.12](../releases/V1.5.12-SNAPSHOT-QUOTE-PACING.md) vorbereitet; finale PR-/Main-Prüfungen und tatsächlicher Tag werden in [PR #271](https://github.com/burckhju/trading-workspace/pull/271) gebunden. Dies ist keine Abnahme des vollständigen Zuschnitts oder Nachweis der PC-Installation. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Begrenzte Umsetzung und ergänzte Cache-/Fehler-/Job-Fälligkeitstests sind am neuen Code-/Testbestand nachgewiesen; finale PR-Gates headgebunden im PR dokumentieren und Integration getrennt behandeln. Der [Entscheidungsnachtrag](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md#nachtrag-variante-2-entschieden) hält auch mögliche spätere Erholung bei unveränderten Jobintervallen fest; keine neue Recovery-Retrylogik. Technical Review bleibt bis zur Integration; aktuelle Betriebszustände auf JMBbot weiterhin separat prüfen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="market-data-evidence"></a>
<details>
<summary>unnummeriert — Kursprotokoll und versionierte Produktbelege</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | Nach ursprünglicher Baseline: 1.5.4-Ergänzung zu M1/M10. Bereich/Querschnitt: 1, 2. Bestehender Bezug: bestehende TC-001-/Produktbelegfähigkeit; keine neue FT-Zuordnung. Lieferziel: A, C. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Erlaubte Abrufe nachvollziehbar protokollieren und manuell geprüfte Belege an Produktidentität/TermsVersion binden. **Nicht-Soll:** Kein Backfill erfundener Historie; Empfangszeit ersetzt keine Originalkurszeit. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [1.5.4-Lieferumfang](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.5.4-IV-DATA-AND-RISK.md) dokumentiert warrant_quote_samples und warrant_valuation_evidence, Migration 20261012_0045. |
| Test / Commit | Aktuelle CI enthält erfolgreiche PostgreSQL-Migrationsschritte; konkrete neue Tabellen/Constraints hier nicht vollständig eigenständig gelesen oder lokal geprüft. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Version 1.5.4 laut Release-Notiz; in Softwarebasis 1.5.5 enthalten, aktuelle Installation separat. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Aufbewahrung, wachsenden Speicher und tatsächliche vorhandene Belege auf der Zielinstallation prüfen; Bericht nicht mit Livebeobachtung verwechseln. **Nächste Abhängigkeit:** Bestehende erlaubte Datenabrufe / manuelle Belegerfassung; unveränderte Providerzustimmungen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="iv-risk-lab"></a>
<details>
<summary>unnummeriert — IV-Datenbereitschaft und hypothetisches Modelllabor</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | Nach ursprünglicher Baseline: 1.5.4-Ergänzung. Bereich/Querschnitt: 4, 6; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: bestehende Risiko-/Modelllaborfähigkeit; genaue Code-Ownership hier nicht neu bestimmt. Lieferziel: A, D. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Reale Positionsdaten von eigenen hypothetischen Modellannahmen und deren Modellgrenzen unterscheiden. **Nicht-Soll:** Modelllabor ist kein Beleg echter Positions-IV, historischer IV-Ranks oder belastbarer realer Sensitivität. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [1.5.4-Notiz](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.5.4-IV-DATA-AND-RISK.md): Szenarien für europäische Vanilla-Calls/Puts, getrennte Datenbereitschaft und unbekannte reale Werte. |
| Test / Commit | Quellenbeleg aus Release-Dokument; spezifischer Modell-/UI-/Testcode nicht vollständig neu gelesen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Dokumentierter 1.5.4-Lieferumfang; keine fachliche Liveabnahme daraus ableiten. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Bestehende Modelleingaben und zulässige Produktgrenzen vor jeder weiteren fachlichen Nutzung nachweisen; keine neuen Schwellen erfinden. **Nächste Abhängigkeit:** Qualifizierte Produktbelege und ausdrücklich hypothetische Annahmen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="monitoring-rules"></a>
<details>
<summary>unnummeriert — Regelüberwachung und fachliche Alerts</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Regelüberwachung. Bereich/Querschnitt: 6. Bestehender Bezug: Position Monitoring & Alert Capability; FT noch offen. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Effektive Positions-/Managementregeln mit richtiger Instrument-/Währungsbasis auswerten; deduplizierte fachliche Alerts erhalten. **Nicht-Soll:** Alert ist keine Notification, kein SELL und keine automatische Stop-/Zieländerung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Monitoring-/Alert-Router registriert](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py); [bestehende getrennte Ownership](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md); [spätere explizite Preisbindung](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-010_TRADE_MANAGEMENT.md). |
| Test / Commit | Historische Monitoring-/Preisbindungs-/Betriebsregressionen referenziert; aktuelle Basis-CI. Nicht alle Regeln am Zielsystem geprüft. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Qualität und Auswertungsstatus je Regel mit gebundener Basis, Legacy-Sperren und Zustellzustand verständlich abnehmen. **Nächste Abhängigkeit:** Effektive FT-009/010-Zustände und qualifizierte TC-001-Daten. |
| Umfangsentscheidung | Bestehende unnummerierte Fähigkeit behalten; keine FT-Nummer erfinden. Frühere reine Underlying-EOD-Aussage nicht auf sämtliche spätere Regeln verallgemeinern. |

</details>

<a id="notification-delivery"></a>
<details>
<summary>unnummeriert — Benachrichtigungen und Zustellzustände</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Benachrichtigungen. Bereich/Querschnitt: 6. Bestehender Bezug: Notification Capability / austauschbarer Outbound-Adapter; FT noch offen. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Notification und DeliveryAttempts getrennt vom Alert führen; Fehler, Retry und erfolgreiche Zustellung sichtbar halten. **Nicht-Soll:** Keine echten Testnachrichten; Telegram ist kein Trading-Eingabekanal. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Notification-/Delivery-Ownership](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md); [historischer Schnitt und PR #74](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/PRODUCT_BACKLOG.md); API-Komposition und Workspace referenzieren vorhandene Fähigkeiten. |
| Test / Commit | Historische Success-/Failure-E2E-Verweise und aktuelle Basis-CI; kein spezifischer aktueller Zustell-/Livebeleg. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Consumer-/Restart-/Retry-Nachweise und reale Zustellzustände ohne Nachrichtenversand prüfen. **Nächste Abhängigkeit:** Persistierte fachliche Alerts; bestehende explizite Zustellkonfiguration. |
| Umfangsentscheidung | Vorhandene Capability, Nummerierungsentscheidung weiterhin separat offen; keine neue Plattform oder neuer Kanal. |

</details>

<a id="reminders"></a>
<details>
<summary>unnummeriert — Erinnerungen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Erinnerungen. Bereich/Querschnitt: 6. Bestehender Bezug: bestehende Notification-/Workspace-Bezüge; fachlicher Erinnerungsowner noch nicht belegt. Lieferziel: A. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Erinnerungsanlass, Fälligkeit, Benutzeraktion und Herkunft sind ausdrücklich definiert. **Nicht-Soll:** Ein Alert, Schedulerjob oder Workspace-Hinweis ist nicht automatisch ein vollständiger Reminder-Contract. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Workspace-/Notification-Bezüge](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md); eigener vollständiger Erinnerungsconsumer nicht verifiziert. |
| Test / Commit | Kein spezifischer Test-/Abnahmebeleg verifiziert. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Originalumfang gegen bestehende Aufgaben/Notifications abgrenzen; nur konkrete fehlende Fähigkeit nach Ownerentscheidung planen. **Nächste Abhängigkeit:** Fachlicher Anlass/Fälligkeitsvertrag; vorhandene Consumer. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="model-monitoring"></a>
<details>
<summary>unnummeriert — Modellüberwachung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M10: Modellüberwachung. Bereich/Querschnitt: 6; Querschnitt: Modelle/Regelgovernance. Bestehender Bezug: FT-013 und jeweilige fachliche Modellconsumer; keine neue Capability-ID. Lieferziel: A, D. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Aktive/angewendete Version, Kompatibilität und Datenbereitschaft bleiben überprüfbar. **Nicht-Soll:** Runtime-Auflösung ist nicht automatisch Modellgüte-/Driftüberwachung oder automatische Modelländerung. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [versionsgenaue Runtime-Auflösung](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/features/model/service/runtime_activation_service.py); [backend-authoritative Candidate-Readiness](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/features/FT-020_CANDIDATE_MODEL_CONFIGURATION_UX.md). Vollständiger M10-Modellüberwachungsumfang nicht verifiziert. |
| Test / Commit | Kein eigener vollständiger Monitoring-/Drift-Test- oder Betriebsnachweis ermittelt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Gewünschte Überwachungsanlässe und Metriken ohne erfundene Schwellen entscheiden; vorhandene Statusreader wiederverwenden. **Nächste Abhängigkeit:** Konkreter aktiver Modellconsumer und freigegebene Überwachungsbedeutung. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operational-workspace"></a>
<details>
<summary>unnummeriert — Täglicher Operational Workspace</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | Spätere Querschnittsfähigkeit zu M2–M10. Bereich/Querschnitt: Querschnitt: durchgängiger Arbeitsablauf/Bedienbarkeit. Bestehender Bezug: Operational Workspace; nur lesend. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Nächste Aufgaben, Datenbereitschaft, offene Positionen, Monitoring und Zustellung aus autoritativen Quellen verständlich zusammenführen. **Nicht-Soll:** Keine eigenen Done-/Acknowledge-/Assignment-Zustände und keine konkurrierende fachliche Schreibwahrheit. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | [Operational-Workspace-API](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/backend/app/main.py) / [/workspace](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/frontend/src/app/router.tsx) registriert; [ephemerer Read-model-Vertrag](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/planning/MODULE_AND_FEATURE_CATALOG.md). |
| Test / Commit | Aktuelle Basis-CI; vollständiger Aufgaben-/Fehler-/Readiness-Consumer hier nicht neu durchlaufen. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Kein gesonderter Release-Nachweis für den vollständigen Zuschnitt verifiziert; ein allgemeiner Softwaretag ersetzt ihn nicht. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | End-to-End-Lesbarkeit der konkreten täglichen Aufgaben in einer identifizierten Installation abnehmen. **Nächste Abhängigkeit:** Vorhandene Ownerzustände; fehlende Journal-/Performance-Funktionen nicht als erledigt anzeigen. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-optimization"></a>
<details>
<summary>unnummeriert — Performanceoptimierung</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Performanceoptimierung. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** Technische Leistung mit explizitem Szenario und messbarem Ausgangswert verbessern. **Nicht-Soll:** Keine Produktionsmutation, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | Vorhandene Diagnoseberichte zur Monitoring-Abrufabdeckung sind keine allgemeinen Laufzeitbenchmarks. |
| Test / Commit | Siehe CI-/Prüfregister mit exaktem Basiscommit; lokale Anwendungsgates nicht ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Nicht als vollständiger Abschluss von M11 zu interpretieren. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Engpass, Lastprofil und messbaren Zielwert erst nach Beleg bestimmen; keine erfundene Fertigstellungsquote. **Nächste Abhängigkeit:** Geeigneter isolierter Prüfstack bzw. autorisierter Releaseprozess. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-stability"></a>
<details>
<summary>unnummeriert — Stabilität und sichere Betriebsgrenzen</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Stabilität. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Wiederholbarkeit, Erhalt privater Konfiguration/Daten und nachvollziehbare Fehlerzustände. **Nicht-Soll:** Keine Produktionsmutation, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | Aktuelle Backend-CI qualifiziert restrictive-umask image und issuer renderer sandbox einschließlich isolierter Legacy-Migration/Compose-Provenienz. Historische Operations-Nachweise bleiben in Traceability. |
| Test / Commit | Siehe CI-/Prüfregister mit exaktem Basiscommit; lokale Anwendungsgates nicht ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Nicht als vollständiger Abschluss von M11 zu interpretieren. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Zielinstallation und Wiederherstellung separat prüfen; CI-Docker ist nicht JMBbot. **Nächste Abhängigkeit:** Geeigneter isolierter Prüfstack bzw. autorisierter Releaseprozess. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-regression"></a>
<details>
<summary>unnummeriert — Regressionstests</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Regressionstests. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Etablierte Backend-, Frontend-, PostgreSQL- und Browser-Gates bleiben unverändert. **Nicht-Soll:** Keine Mutation realer Betriebsdaten durch Tests, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | CI-Jobs und relevante Steps auf a78288ad erfolgreich; Backend quality, PostgreSQL migrations, FE type/lint/coverage/build, E2E migrate/smoke. |
| Test / Commit | Historisches CI-/Prüfregister mit exaktem Basiscommit bleibt erhalten. TC-001-C-Vorherstand auf `3d47732665c8b66984923d88a65cf99e74d96791` / Dokumentationshead `bade0e33`: 322 gezielte Tests und vollständige statische Backendgates bestanden. Die anschließend entschiedene Variante 2 ist getrennt nachgewiesen auf `187c16b63e0d4dc16b2204f80aec4533c34173e6`, gezielte Gesamtsuite `344 bestanden, 0 Fehler/Skips/Deselektionen`; vorherige grüne Checks zählen nicht als Nachweis des neuen Codes. [Prüfbericht mit Historie und Nachtrag](../reviews/MARKET_DATA_SOURCE_MODE_PACING_2026-10-21.md). Gate-Einstiege gegenüber `5e9ede2` und `bade0e33` unverändert; kein Abschluss aller Regressionen oder Ersatz aktueller finaler PR-Checks. **Nachtrag 23.10.2026:** Die gemeinsame Entwicklungsqualifikation erhält Smoke, zwei Finanzfälle in frischen Stacks und zwei Journal-/FT-011-Fälle im eigenen Job. Alle regulären Gates gelten unverändert; getrennte alte Erfolge ersetzen keine gemeinsame Ausführung. [Gemeinsamer Nachweisvertrag](../implementation/CLOSED_TRADE_SOURCE_INTEGRATION_QUALIFICATION.md); exakte aktuelle Head-/Tree-/Run-/Artefaktbindung in [PR #273](https://github.com/burckhju/trading-workspace/pull/273), Herkunft #269 bleibt separat. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Nicht als vollständiger Abschluss von M11 zu interpretieren. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | TC-001-Implementierungs-/Test- und Dokumentdiff prüfen; vollständige Anwendungsgates auf dem neuen finalen PR-Head ausführen lassen und getrennt vom historischen C-Stand belegen. Technical Review bleibt bis zur Integration. **Nächste Abhängigkeit:** Geeigneter isolierter Prüfstack und reguläre PR-CI; Integrations-/Releaseentscheidungen bleiben getrennt. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-release"></a>
<details>
<summary>unnummeriert — Releasevorbereitung und Softwarestand</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Releasevorbereitung. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: repositoryweite Qualität/Betrieb, kein neuer FT-Bezug. Lieferziel: A. |
| Arbeitsstatus | Technical Review |
| Soll / Nicht-Soll | **Soll:** Versionierte Software und nachvollziehbare Release-/CI-Bindung. **Nicht-Soll:** Keine Produktionsmutation, keine Gate-Absenkung und keine Gleichsetzung von Software-Release mit installierter Zielumgebung. |
| Vorhandenseinsnachweis | Dokument- und/oder Routing-Nachweis vorhanden; Details, historische Grenzen und nicht erneut geprüfte Implementierung im Eintrag. |
| Implementierung / Consumer | VERSION, backend/pyproject.toml und frontend/package.json nennen 1.5.5. Git-Tag v1.5.5 zeigt auf a78288ad; drei Main-Push-CI-Läufe erfolgreich. |
| Test / Commit | Siehe CI-/Prüfregister mit exaktem Basiscommit; lokale Anwendungsgates nicht ausgeführt. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Software v1.5.5 mit verifiziertem Git-Tag auf Basiscommit; das sagt nichts über vollständige M0–M11-Erfüllung. |
| Betriebsnachweis | Nicht geprüft: aktueller Betrieb auf JMBbot. |
| Restarbeit / nächste Abhängigkeit | Bei Integration dieses reinen Dokumentdiffs geltenden Releaseprozess beachten; keine Tagverschiebung oder Veröffentlichung durch diesen Auftrag. **Nächste Abhängigkeit:** Geeigneter isolierter Prüfstack bzw. autorisierter Releaseprozess. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="operations-installation"></a>
<details>
<summary>unnummeriert — Betriebsnachweis der identifizierten Zielinstallation</summary>

| Nachweisfeld | Einordnung |
|---|---|
| Zuordnung | M11: Betrieb; Ziel A. Bereich/Querschnitt: Querschnitt: technische Qualität/Betrieb. Bestehender Bezug: bestehende Betriebs-/Releaseverantwortung. Lieferziel: A. |
| Arbeitsstatus | Analysis |
| Soll / Nicht-Soll | **Soll:** JMBbot mit tatsächlich installierter Version/Commit, Schema, Compose-Provenienz, Daten-/Monitoring-/Zustellzuständen und Nachweiszeitpunkt identifizieren. **Nicht-Soll:** Keine Diagnoseanleitung als erfolgreichen Lauf ausgeben; kein Monitoring-Einmallauf, Deployment oder Nachricht. |
| Vorhandenseinsnachweis | Vollständige Teilfähigkeit nicht verifiziert. Vorhandene Nachbarfunktionen/Dokumente sind im Implementierungsfeld benannt; daraus folgt kein Abwesenheitsbeweis. |
| Implementierung / Consumer | [Release-Notiz 1.5.5](https://github.com/burckhju/trading-workspace/blob/a78288ad38610656480d0363abe657b567c7ba94/docs/releases/V1.5.5-ISSUER-COVERAGE.md) nennt zuvor bestätigten PC-Stand v1.5.4 / ab4730885b91fd954f3494434ff3d1f4734397db. Dies ist ein historischer Dokumentbeleg, keine aktuelle Beobachtung. |
| Test / Commit | CI-Wegwerfinstallationen qualifiziert; aktuelle JMBbot-Installation und Wiederherstellung nicht geprüft. Bezug: Basiscommit, soweit kein anderer Commit ausdrücklich genannt. |
| Fachliche Abnahme | Keine eigenständige fachliche Abnahme für diesen vollständigen Zuschnitt verifiziert. |
| Software-Auslieferung | Softwaretag 1.5.5 getrennt vom historisch genannten PC-Stand 1.5.4. |
| Betriebsnachweis | JMBbot identifiziert; aktueller Zustand nicht geprüft. Historischer PC-Stand nur laut Release-Notiz. |
| Restarbeit / nächste Abhängigkeit | Bei autorisiertem lesendem Zugriff Installation und Zustände mit vorhandenen sicheren Diagnosewegen belegen; keine Nutzerbestände ändern. **Nächste Abhängigkeit:** Erreichbare identifizierte Zielinstallation / zulässiger lesender Zugang. |
| Umfangsentscheidung | Bestehender Umfang bleibt erhalten. Offene Nachweise oder Erweiterungen sind keine belegte Verschiebung oder Entfernung ursprünglicher Zusagen. |

</details>

<a id="naechster-schnitt"></a>
## Genau nächster sinnvoller Umsetzungsschritt

**Nach der freigegebenen Bereitstellung Version 1.5.9 über den vorhandenen
PC-Launcher aktualisieren und den installierten Zustand lesend prüfen.**
Die [Release-Notiz](../releases/V1.5.9-REALIZED-GROSS-REPORT.md) beschreibt den
gepinnten Updateweg mit dem tatsächlich veröffentlichten Tag-Commit und Migration
0047. Die [Berichtsqualifikation](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
verbindet Quellen, Referenz/Korrektur, PostgreSQL-Rennen und den echten Browserweg.

Die Nutzeranweisungen „Ok, umsetzen“ und „wenn prüfungen grün mergen und für den pc
verfügbar machen“ liegen vor. Aktuelle PR-Prüfungen, normale geschützte Integration
und erfolgreiche main-Prüfungen vor der Tag-Erzeugung setzen diese Bedingung um.
PR #249 wird als eigener Integritätsfix vorgezogen; der Performance-Diff ändert
kein Basiswertformular. Die neue obligatorische Owner-Browserqualifikation liegt
zusätzlich im bestehenden End-to-End-Workflow und akzeptiert keinen Skip oder Retry.

Reale Nutzerbestände und ihre Währungsabdeckung wurden dabei nicht geprüft oder
verändert. Deren bewusste Bestätigung und die fachliche Beobachtung des installierten
Ergebnisses bleiben getrennt. Die durch #260/#261/#263 vorhandene Journal-/Lesson-/
Evidence-Strecke und sämtliche ursprünglichen M8-Restanforderungen bleiben in
ihren maßgeblichen Einträgen erhalten.

### Definition of Ready der ausgeführten Fortsetzung

[ADR-S10-008](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md)
hält die ausdrückliche Umsetzungsfreigabe des konkreten Währungs-/Periodenvertrags
fest. Der vorhandene Average-Cost-Owner wurde wiederverwendet; der additive
Execution-Währungsowner wurde auf PostgreSQL separat qualifiziert. API und UI
verwenden ausschließlich bestätigte Quellen für monetäre Beiträge. Synthetische
EUR-Fixtures und Berichtswährung belegen weiterhin keine Währung alter Nutzerdaten.

### Definition of Done und erhaltene Restanforderungen

Der enge technische Lieferumfang umfasst vollständige SELL-Beiträge, belegte
Kostenbasis, explizite Berichtswährung, Summe/Teilsumme, Datenabdeckung und dieselbe
Quellenbasis innerhalb einer Antwort. Testbefunde und verbleibende Gate-/
Betriebsgrenzen sind im [Qualifikationsnachweis](../implementation/PERIOD_REALIZED_GROSS_REPORT_QUALIFICATION.md)
konkret bezeichnet. Fertige Fachabnahme, Veröffentlichung und beobachteter Betrieb
bleiben eigenständig. Gewinner-/Verliererkohorten, Trefferquote, Durchschnitt/
Median, Profit-Faktor, Prozessbewertung, Diagramme und Export bleiben geplant;
Netto/FX/Equity/Drawdown und weitere Methoden benötigen eigene Verträge. Der
vorliegende Schnitt erklärt weder ursprüngliches M8 noch Bereich 7/8 als erledigt.
