# Module and Feature Catalog

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokumenttyp | Product Architecture / Planungssichten |
| Revision | Konsolidierung 2026-10-13; zur fachlichen Prüfung |
| Aufgabenstatus | Nur im [Product Backlog](PRODUCT_BACKLOG.md#abnahmematrix) |
| Baseline | [Ursprüngliche Roadmap und Übergang](../foundation/ROADMAP.md#historische-baseline) |

## Zweck und Grenzen

Dieser Katalog ordnet bestehende Features und Querschnittsfähigkeiten acht dauerhaften Planungssichten zu. Er erfindet keine FT-IDs, keine neue technische Paketstruktur und keine neue schreibende Ownership. Fachliches Feature, technischer Paketname, Modellfamilie und Planungssicht bleiben unterschiedliche Begriffe. Die historische Modulgliederung in ARCHITECTURE wird dadurch nicht still umgebaut.

<a id="planungssichten"></a>
## Acht dauerhafte Funktionsbereiche

| Sicht | Gegenstand und Grenze | Bestehende FT-/Capability-Bezüge | Maßgebliche Backlog-Einstiege |
|---|---|---|---|
| **1. Stammdaten und Instrumente** | Stabile Identitäten, Listings, Terms, Referenzdaten; Kursdaten sind kein Stammdateneigentum. | FT-001–FT-004; separates Providerfeature noch ohne neue Nummer. | [Basiswerte, Listings und Identitäten im Backend](PRODUCT_BACKLOG.md#pb-006-underlying); [Börsen und Handelsplätze](PRODUCT_BACKLOG.md#pb-009-venues); [Emittenten](PRODUCT_BACKLOG.md#pb-010-issuers); [Instrumente und Optionsscheine](PRODUCT_BACKLOG.md#pb-011-warrants); [Datenprovider und benutzerverwaltete Konfiguration](PRODUCT_BACKLOG.md#provider-configuration) |
| **2. Marktdaten und Datenqualität** | Providerneutrale Datenbereitschaft, Qualität, Herkunft, erlaubte Aktualisierung und Kursbelege. | TC-001; vorhandene Daten-/Produktbelegfähigkeit, Consumer bleiben fachliche Owner. | [Marktdatenbereitschaft, Qualität und Herkunft](PRODUCT_BACKLOG.md#market-data-quality); [Datenaktualisierung und Schedulerzustände](PRODUCT_BACKLOG.md#market-data-refresh); [Kursprotokoll und versionierte Produktbelege](PRODUCT_BACKLOG.md#market-data-evidence) |
| **3. Marktanalyse und Kandidaten** | Markt-/Sektor-/Underlying-Analyse und Kandidaten; Watchlist, Scanner und Marktbreite getrennt. | FT-005/FT-006; vorhandene FT-019/FT-020-Kandidaten-Erweiterungen. | [Marktübersicht](PRODUCT_BACKLOG.md#pb-013-overview); [Marktbreite](PRODUCT_BACKLOG.md#pb-013-breadth); [Watchlist](PRODUCT_BACKLOG.md#pb-012-watchlist); [Scanner und Scanner-Modell](PRODUCT_BACKLOG.md#pb-012-scanner); [Kandidatenqualifikation](PRODUCT_BACKLOG.md#pb-012-candidate) |
| **4. Tradevorbereitung und Produktauswahl** | Produktneutraler Plan, explizite Freigabe, Produktsuche/-vergleich/-wahl; Produktscore separat. | FT-007/FT-008; FT-004/TC-001 als Quellen. | [Annahmen, Freigabe und Herkunft des Plans](PRODUCT_BACKLOG.md#pb-014-assumptions); [Produktsuche und Suchuniversum](PRODUCT_BACKLOG.md#pb-015-search); [Produktvergleich und bewusste Auswahl](PRODUCT_BACKLOG.md#pb-015-comparison); [Produktscore und fachliche Modellfamilie](PRODUCT_BACKLOG.md#pb-015-score) |
| **5. Tradeerfassung und Management** | Tatsächliche bestätigte Ausführungen, Position und eigene Managementhistorie; Produktwechsel benötigt eigenen Fachentscheid. | FT-009/FT-010; keine zweite Ausführungswahrheit. | [Trade eröffnen und tatsächliche Käufe erfassen](PRODUCT_BACKLOG.md#pb-016-opening); [Depot und abgeleitete offene Positionen](PRODUCT_BACKLOG.md#pb-016-positions); [Vollverkauf und Abschluss](PRODUCT_BACKLOG.md#pb-017-close); [Event-Historie und historische Korrekturen](PRODUCT_BACKLOG.md#pb-017-history); [Produktwechsel](PRODUCT_BACKLOG.md#pb-017-product-change) |
| **6. Monitoring und Benachrichtigungen** | Regelprüfung, fachliche Alerts, getrennte Notifications und DeliveryAttempts; keine Handelsausführung. | Bestehende unnummerierte Monitoring-/Alert-/Notification-Fähigkeiten; TC-001 und FT-013 als Consumerbezüge. | [Regelüberwachung und fachliche Alerts](PRODUCT_BACKLOG.md#monitoring-rules); [Benachrichtigungen und Zustellzustände](PRODUCT_BACKLOG.md#notification-delivery); [Erinnerungen](PRODUCT_BACKLOG.md#reminders); [Modellüberwachung](PRODUCT_BACKLOG.md#model-monitoring) |
| **7. Nachbeobachtung, Journal und Lernen** | Nachbeobachtung, Review, Journal, Evidence und Lesson; jede Fähigkeit mit eigener Grenze. | FT-011/FT-012; Korrekturen lesen FT-009/010. | [Zulässige Nachbeobachtung](PRODUCT_BACKLOG.md#pb-018-observation); [Exit Review und Handoff](PRODUCT_BACKLOG.md#pb-018-review); [Journalentwurf und Journalabschluss](PRODUCT_BACKLOG.md#pb-019-journal); [Exit-Review-Evidence bewusst materialisieren](PRODUCT_BACKLOG.md#pb-019-materialization); [Belegte Lessons Learned](PRODUCT_BACKLOG.md#pb-019-lessons) |
| **8. Performance und Auswertung** | Explizit definierte Kennzahlen, Statistiken und Perioden-/Tradeauswertungen. Brutto-PnL und Charts sind nur abgegrenzte Vorleistungen. | FT-012 / Evaluation als bestehende fachliche Zuordnung; FT-009/010/TC-001 als Datenquellen. | [Positionsbezogenes realisiertes Brutto-PnL](PRODUCT_BACKLOG.md#pb-017-gross-pnl); [Performancekennzahlen](PRODUCT_BACKLOG.md#pb-019-performance-metrics); [Tradeübergreifende Statistiken](PRODUCT_BACKLOG.md#pb-019-performance-statistics); [Performance-Dashboards](PRODUCT_BACKLOG.md#pb-019-performance-dashboards); [Perioden- und Tradeauswertungen](PRODUCT_BACKLOG.md#pb-019-performance-evaluations) |

## Drei Querschnittsthemen

| Thema | Bestehende Verantwortung und Grenze | Maßgeblicher Verweis |
|---|---|---|
| **Modelle/Regelgovernance** | FT-013 verwaltet Modell-/Freigabe-/Aktivierungsartefakte; fachliche Berechnung und Anwendung bleiben beim jeweiligen Consumer. Jede Modellfamilie wird gesondert nachgewiesen. Freigabe und Aktivierung sind getrennte Benutzeraktionen. | [Governance](PRODUCT_BACKLOG.md#pb-020-governance), [Aktivierung](PRODUCT_BACKLOG.md#pb-020-activation), [Modellfamilien](PRODUCT_BACKLOG.md#pb-020-candidate-family) |
| **durchgängiger Arbeitsablauf/Bedienbarkeit** | Bestehende API-/UI-Consumer und Operational Workspace verbinden den Arbeitsablauf; der Workspace ist ausschließlich ephemerer Leser und speichert keine konkurrierenden Aufgabenwahrheiten. | [Prozessmodell](PRODUCT_BACKLOG.md#pb-002-process), [Workspace](PRODUCT_BACKLOG.md#operational-workspace) |
| **technische Qualität/Betrieb** | Bestehende Schichten, Versionen, Migrationen, Fehler-/Transaktionsmuster und Gates; Release, Installation und beobachteter Betrieb bleiben verschieden. Begleitet jeden Lieferschnitt. | [Governance-Baselines](PRODUCT_BACKLOG.md#pb-004-standards), [Regression](PRODUCT_BACKLOG.md#operations-regression), [JMBbot-Nachweis](PRODUCT_BACKLOG.md#operations-installation) |

Keines dieser Themen ist eine erst nach M8 oder nach allen Features beginnende Phase.

<a id="feature-katalog"></a>
## Bestehender Feature-Katalog – keine Statusliste

| Bestehende ID | Feature / fachliche Zuordnung | Originalbezug und wichtige Grenze |
|---|---|---|
| FT-001 | Basiswertverwaltung (`underlying` als logische Kennung; tatsächlicher Code in `market`) / Reference Data | M1; Basiswert und Listing getrennt. Ursprünglich STOCK; ETF-Stammdaten durch späteren Chart-/Analyse-Nachtrag gesondert beachten. |
| FT-002 | Börsen und Handelsplätze / Reference Data | M1; stabile Venue-Identität, Low-input-Consumer, keine Provider-ID als fachliche ID. |
| FT-003 | Emittenten / Reference Data | M1; globale Issuer-Identität, kein Underlying-Unternehmen als Ersatz. |
| FT-004 | Optionsscheinverwaltung / Reference Data | M1/M4; Warrant, TermsVersion und Listing getrennt; keine implizite neue Produktfamilie. |
| FT-005 | Watchlisten und Kandidaten / Market Discovery | M2; generische Watchlist und Scanneranspruch nicht mit bestehender Kandidatenqualifikation gleichsetzen. |
| FT-006 | Marktanalyse / Market Discovery | M2/M3/M9; persistierte, reproduzierbare beschreibende Analyse und lesende Charts unterscheiden. Marktbreite bleibt sichtbar. |
| FT-007 | TradePlan / Trade Preparation | M3; produktneutral, versionsgenaue bewusste Freigabe, Candidate-Ursprung optional und konkret. |
| FT-008 | Produktauswahl / Product Selection | M4; Evaluation/Comparison, Nutzerwahl und Produktscore getrennt. |
| FT-009 | Trade und Position / Purchase Execution Capture | M5; Eigentum an Trade/ExecutionRecord/Position, von FT-010 im selben Vertrag erweitert. |
| FT-010 | Trade Management | M5; Ausführungen und Managementevents getrennt. Produktwechsel steht zwar im alten Zielbild, ist aber ausdrücklich kein V1-Managementevent. Offener M4-Anspruch bleibt referenziert. |
| FT-011 | Nachbeobachtung und Exit Review / Post Trade Learning | M6; realer Vollverkauf als Eignungsgrundlage; virtuelle Beobachtung nicht als reale Ausführung darstellen. |
| FT-012 | Journal, Lessons Learned und Performance / Evaluation | M7/M8; bestehende Ownership auch für LearningEvidence und Lessons. Materialisierung/Lesson ersetzen weder Journal noch Performance. |
| FT-013 | Modellkatalog und Modellbewertung / Model Governance | M9; allgemeine Governance, separate Runtime-Aktivierung und jede fachliche Familie getrennt. |
| FT-019 / FT-020 | Bereits referenzierte Kandidaten-Erweiterungen / Candidate Model Configuration UX | Spätere Präzisierung von FT-005/FT-013; keine neue Vergabe dieser Kennungen. FT-020 verweist auf FT-019 als Vorgänger; keine Umnummerierung oder neue Paketownership. |

Die bisherigen PB-001–PB-020 bleiben im [Backlog](PRODUCT_BACKLOG.md#abnahmematrix) bestehen. Kein Feature wird durch seine Zuordnung zu einer Sicht als vollständig fertig erklärt. Nicht gelesene Detailverträge und fehlende Freigaben sind dort benannt.

## Bestehende Querschnittsfähigkeiten

**TC-001 / `market_data`** verantwortet die technische providerneutrale Datenversorgung, Qualitäts-/Herkunftszustände, Cache und Persistenz. Consumer sind insbesondere FT-004, FT-006, FT-008, FT-011, FT-013 sowie bestehende Monitoring-/Analysefähigkeiten. Die benutzerverwaltete Providerkonfiguration bleibt laut bisherigem Katalog ein separat zu spezifizierender fachlicher Zuschnitt; kein neues FT und keine Eigentumsübernahme durch TC-001 werden erfunden.

**Operational Workspace** bleibt eine lesende, ephemere Projektion bestehender Owner-Zustände. Er konsumiert unter anderem FT-005/FT-020, FT-007–FT-011, Position Monitoring und Notification Delivery. Benutzeraktionen gehen an den jeweiligen schreibenden Fachowner. Es gibt keine zusätzlichen persistierten Done-, Acknowledge- oder Assignment-Fakten.

Für die laufende Positionsbewertung qualifiziert derselbe FT-009/010-Owner die
wirksame Kaufkostenbasis über seine bestehende Projektion und Währungsauflösung.
Marktwert und nicht realisiertes Brutto-PnL bleiben getrennte Aussagen. Depot,
Trade-Management, Filter und Summen konsumieren diese Backendqualifikation ohne
zweite Kostenrechnung oder Bestätigungswahrheit. Quellen- und Versionsbezug
stehen im [engen Bewertungsvertrag](../implementation/POSITION_VALUATION_CURRENCY_QUALIFICATION.md);
Arbeitsstatus weiterhin ausschließlich in PB-016, PB-017 und Operational Workspace.

**Position Monitoring & Alert Capability** besitzt MonitoringRuleState und Alert. **Notification Capability** besitzt Notification und DeliveryAttempt. Die noch offene Nummerierungsentscheidung wird nicht vorweggenommen. Der historische rein tägliche Underlying-Scope darf nicht spätere dokumentierte Preisbindungs-/Produktdaten-Erweiterungen verdecken. Aktuelle Arbeits-/Nachweisstände stehen nur im Backlog.

<a id="ownership"></a>
## Ein schreibender fachlicher Owner je Objekt

| Objekt | Bestehender schreibender Owner | Wesentliche lesende Consumer / Grenze |
|---|---|---|
| Basiswert / Listing | FT-001; tatsächliche Implementierung `market` | FT-004–FT-008, FT-012; Referenzen/Charts lesen denselben Identitätskontext. |
| Börse / Handelsplatz | FT-002 | FT-004, FT-008, FT-009. |
| Emittent | FT-003 | FT-004, FT-008. |
| Provider / Datenquelle | Separates Providerfeature gemäß bestehendem Katalog | FT-004/006/008/013; technische Adapter/Mapping-Infrastruktur nicht mit neuer fachlicher Ownership verwechseln. |
| Instrument / Warrant / TermsVersion / WarrantListing | FT-004 | FT-008–FT-012; konkrete Terms-/Listing-Identität bleibt historisch. |
| Watchlist / Candidate / CandidateEvaluation | FT-005 | FT-007 und Workspace; Watchlist-Zuordnung ist keine Implementierungsbehauptung. |
| Analyse / Analyseversion | FT-006 | FT-005, FT-007, FT-012, FT-013; Fachberechnung nicht im Frontend duplizieren. |
| TradePlan / TradePlanVersion | FT-007 | FT-008–FT-012, Workspace; spätere Managemententscheidung verändert keine historische Planversion. |
| ProductSelectionRun / ProductEvaluation / ProductSelection | FT-008 | FT-009, FT-012, Workspace; Berechnung und Benutzerwahl sind verschiedene Objekte. |
| Trade / ExecutionRecord / Position | FT-009, durch FT-010 erweiterter gemeinsamer Vertrag in `trade_position` | FT-010–FT-012, Monitoring, Workspace; kein zweiter Verkauf/Positionsowner. |
| TradeManagementEvent | FT-010 | FT-011, FT-012, Monitoring, Workspace; ein SELL bleibt ExecutionRecord. |
| MonitoringRuleState / Alert | Bestehende Position Monitoring & Alert Capability | Notification, Workspace; keine implizite Ausführung. |
| Notification / DeliveryAttempt | Bestehende Notification Capability | Delivery-Adapter, Workspace; Zustellung ist nicht der fachliche Alert. |
| PostTradeObservation / ExitReview / ExitReviewVersion | FT-011 in `post_trade` | FT-012 über freigegebenen Handoff; FT-013 und Workspace als nachgelagerte Consumer. |
| LearningEvidence / Lesson / LessonVersion | FT-012 in `learning` | FT-013, Learning-UI; Evidence-Transport ist keine Interpretation. |
| Journal / Performance Record | FT-012 gemäß bestehender fachlicher Zuordnung | FT-013 und lesende Auswertung; kein Schluss auf vorhandene vollständige Implementierung. |
| Model / ModelVersion / Freigabe-/Aktivierungsartefakte | FT-013 in `model` | Jeweiliger fachlicher Modellconsumer; freigegeben ist nicht automatisch aktiv. |

Die Tabelle bewahrt vorhandene fachliche Zuständigkeiten; sie ist kein Auftrag zur Paketverschiebung. Für später dokumentierte IV-/Produktbeleg-Erweiterungen wird ohne vollständige Vertragsprüfung keine zusätzliche Code-Ownership erfunden. Das [Backlog](PRODUCT_BACKLOG.md#market-data-evidence) benennt diese Nachweisgrenze.

## Verbindliche Auslegungsregeln

FT-001 bleibt Referenzfeature für Feature-Dokumentation, CRUD-/Konflikt-/Auditkonventionen und Traceability. Basiswert/Listing-Trennung, stabile UUIDs, Eindeutigkeit bei vorhandenen ISIN/WKN, Deaktivierung referenzierter Objekte und bestehende Workspace-Grenzen bleiben erhalten. Der spätere ETF-Stammdaten-Nachtrag ist keine Erweiterung auf beliebige Instrumente oder SHORT-Prozesse; direkte Indexreferenzen erhalten weiterhin keine erfundenen Listings.

Die Originalanforderungen für Watchlist, Marktbreite, Produktscore, Produktwechsel und alle Modellfamilien bleiben über die Matrix auffindbar. Eine neue Bereichsdefinition darf keinen alten Anspruch verdecken. Scopeänderungen benötigen belegte Entscheidungen. Historische „Not Started“, „Review Pending“ oder „Released“-Angaben werden nicht hier repliziert; [Konflikte und ihre Auflösung](PRODUCT_BACKLOG.md#konfliktaufloesung) stehen beim maßgeblichen Arbeitsstand.
