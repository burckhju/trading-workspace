# Trading Workspace

Trading Workspace unterstützt einen benutzergesteuerten Tradingprozess: Referenzdaten und Marktanalysen, Tradevorbereitung und Produktauswahl, Erfassung tatsächlicher Ausführungen, Positionsmanagement sowie Nachbeobachtung und Lernen. Das System trifft und vollzieht keine autonomen Kauf-, Verkaufs-, Halte-, Produktwahl- oder Positionsgrößenentscheidungen. Tatsächliche Ausführungen sind vom Benutzer bestätigte Fakten, keine Brokerorders.

## Softwarestand und Planung

**PC-Lieferumfang v1.5.54:** Die [Bereitstellungsnotiz](docs/releases/V1.5.54-UI-FACHSTRUKTUR-PC-DELIVERY.md) liefert die in [PR #372](https://github.com/burckhju/trading-workspace/pull/372) integrierte Fachstruktur A: Aktuelles, Depot, Marktanalyse, Lessons Learned und Basisdaten, mit konsolidierten Depotdetails und erhaltener Rückkehrnavigation. Sie enthält den bisherigen Produkt- und Planungsstand aus v1.5.53. Der bestehende Linux-Launcher übernimmt den nach grüner Main-CI automatisch veröffentlichten Tag mit seinem vollständigen Commit. Die nachfolgende Nachweisfortschreibung bleibt auf ihren datierten Prüfstand begrenzt; Veröffentlichung, PC-Installation und reale Datenabdeckung sind getrennte Nachweise.

**Nachweisfortschreibung vom 20.11.2026:** Geprüft ist Main `c7db441de36297a98d47cdf28c64b4e5d9994692`, zugleich veröffentlichter Tag `v1.5.52`. Die [aktuelle Einstiegssicht](docs/planning/PRODUCT_BACKLOG.md#aktueller-stand) trennt implementierte Teilumfänge, Fachabnahme, Auslieferung und datierten PC-Betrieb. Der [eine nächste Arbeitsauftrag](docs/planning/PRODUCT_BACKLOG.md#naechster-schnitt) betrifft die reale V2-Datenbereitschaft nach dem inzwischen integrierten und veröffentlichten [Produktdatums-Fix #368](https://github.com/burckhju/trading-workspace/pull/368).

Die versionierte Software ist in [VERSION](VERSION) festgehalten. Die [Produkttermin-Auswertung v1.5.52](docs/releases/V1.5.52-PRODUCT-DATE-SEMANTICS.md) trennt belegtes Produktende und Zahlungstermin, korrigiert daraus entstandene falsche Widersprüche und wertet vorhandene Originalbelege automatisch neu aus. Ein kontrollierter privater Originalimport ergänzt den gesperrten Stuttgarter Kalenderabruf. Die [Build-Reparatur aus v1.5.51](docs/releases/V1.5.51-RELIABLE-BACKEND-BUILD.md) und der fachliche [V2-Umfang aus v1.5.50](docs/releases/V1.5.50-INDICATIVE-V2-AND-PRODUCT-DEADLINES.md) bleiben die Grundlage. Vorhandene Positionen und wirtschaftliche Belege werden weiterverwendet; echte Datenwidersprüche bleiben sichtbar. Die reale B58-Originalstatusversorgung ist weiterhin unbelegt. Ein Softwaretag bestätigt weder die Installation auf dem Nutzer-PC noch vollständige Hebeltrader-Überwachung.

Der [enge P02-Readback vom 24.11.2026](docs/reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md) belegt **v1.5.54 auf `9a5e59d…`**, Schema `20261118_0060` und vier gesunde laufende Dienste. Für dieselbe gebundene JPMorgan-Route ist um **18:21:41 Uhr MEZ** eine auswertbare V2-Bewertung gespeichert: `BELOW_ENTRY`, mit vorhandenem Bid und 10,456 Sekunden Empfangsalter. Die frühere Unterbrechung ist als `JPMORGAN_SNAPSHOT_TIMEOUT` konkretisiert; der damalige Quote war schon vor dessen Erfassung bidlos. Die aktuelle Originalstatuslücke ist keine neue V2-Preisunterbrechung. Original-Bidzeit und qualifizierter Instrumentstatus fehlen weiterhin für B58. Der [Gesamtreadback vom 22.11.2026](docs/reviews/DEPOT_DATA_READBACK_2026-11-22.md) bleibt die letzte vollständige Vierer-Inventur und Zyklusdiagnose; der neue Einzelread liefert keine heutige Gesamtquote. Der [einzige nächste Auftrag](docs/planning/PRODUCT_BACKLOG.md#naechster-schnitt) richtet sich auf die Versorgung einer weiteren tatsächlich offenen Position.

**Aktueller Arbeitsstatus und Abnahmematrix:** [Product Backlog](docs/planning/PRODUCT_BACKLOG.md). Es ist die einzige maßgebliche Aufgabenstatusquelle. Hier steht bewusst keine zweite vollständige Feature-Statusliste.

Der [Datenversorgungsnachweis vom 20.11.2026](docs/reviews/DEPOT_DATA_SUPPLY_2026-11-20.md)
verbindet die benötigten Regelinputs mit tatsächlichen Datenwegen,
konkreten Fehlerursachen und Beschaffungsoptionen. Die
[vollständige passive Depotdiagnose](docs/technical/ISSUER_MONITORING_OPERATIONS.md#lesende-depot-datenversorgungsdiagnose)
liest vorhandene Positionen und gespeicherte Prüfgründe, ohne einen
Kursabruf oder Regellauf auszulösen. Der [einzelne Diagnosecollector](scripts/collect-depot-data-supply.py)
kann außerhalb des installierten Checkouts laufen und liefert ein privates
Archiv einschließlich tatsächlicher Installations- und DB-Schemabelege.
Der vollständige Readback und die [enge passive P02-Ergänzung vom
24.11.2026](docs/reviews/P02_SOURCE_GAP_READBACK_2026-11-24.md) liegen vor.
Archivierte Bewertungsinputs und heutiger Journalbestand sind getrennt
ausgewertet. Ein erneuter P02-Export ist für diese Ursachenklärung nicht
erforderlich; die übrigen Positionen wurden mit dem neuen Paket nicht gelesen.
Für die zuvor ungebundenen Kandidaten ergänzt derselbe Collector den
[gezielten Quellenkandidatenread](docs/technical/ISSUER_MONITORING_OPERATIONS.md#gezielter-quellenkandidatenread).
Er verbindet vorhandene Coverage-GETs mit gespeicherten Auswahl-, Produkt-
und Bewertungsfakten. Der [Umsetzungsnachweis](docs/reviews/DEPOT_SOURCE_COVERAGE_COLLECTOR_2026-11-24.md)
trennt technische Qualifikation und den noch erforderlichen tatsächlichen
PC-Read; neue Datenabdeckung ist daraus noch nicht abgeleitet.

| Orientierung | Maßgebliche Quelle |
|---|---|
| Ursprüngliche Zusagen M0–M11 und Lieferziele A–D | [Roadmap](docs/foundation/ROADMAP.md) |
| Acht dauerhafte Funktionsbereiche, drei Querschnittsthemen, bestehende FT-IDs und Ownership | [Module and Feature Catalog](docs/planning/MODULE_AND_FEATURE_CATALOG.md) |
| Implementierung, Tests, Abnahme und Betrieb mit getrennten Nachweisen | [Traceability](docs/foundation/TRACEABILITY.md) |
| Fachliche Grundlagen und Architektur | [Project](docs/foundation/PROJECT.md), [Architecture](docs/foundation/ARCHITECTURE.md) |

Journal, Lessons, Positions-Brutto-PnL, tradeübergreifende Performance und Modellgovernance sind unterschiedliche Fähigkeiten. Fehlende Nachweise und offene ursprüngliche Anforderungen bleiben im Backlog sichtbar. Marktcharts oder eine vorhandene Kandidatenstrecke erklären keine benachbarten Funktionen für fertig.

Für die Hebeltrader-Positionsdetails beschreibt der [Integrationsvertrag](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-2-target-history) die vorhandene Belegabdeckung und den begrenzten Zielhistorien-Read mit ausdrücklichem Prüflauf. Der [Vergleichsbeleg-Vertrag](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-history-qualification) macht die erforderliche Kursqualifikation nachvollziehbar bedienbar. Der [Sitzungsevidenz-Vertrag](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-session-evidence) ergänzt versionierte Originalkalenderimporte und zeigt je Position die seit dem tatsächlichen Kauf abgeschlossenen Basiswertsitzungen oder konkrete Beleglücken. Der anschließende [Original-Geldkurs-Read](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-original-bid-evidence) zeigt separate BID-Zeit, Kursalter, historische Kaufwährung und dokumentierte Sitzungen zur tatsächlichen Kurszeit; der anschließende [Produktmaßstabsvertrag](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-product-price-scale) verbindet dokumentierte unveränderte Produkteinheiten mit sämtlichen noch beitragenden Käufen. Der [Originalstatus-Vertrag](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-market-status-evidence) erhält ausdrücklich gelieferte Statuszeitpunkte und erklärt deren Bezug zu Geldkurszeit und Lesestand. Fehlende Teilabdeckung, Anpassungsbedarf und ein nicht verifizierter offener Markt bleiben ausdrücklich sichtbar; ein gespeicherter OPEN-Punkt belegt keine Fortgeltung bis zum Lesen. Dokumentierte menschliche Quellenprüfung, technische Vollständigkeit und aktive Regelüberwachung bleiben getrennte Aussagen; B04/B05/B06/B58 werden damit noch nicht ausgewertet. Der Aufgabenstatus steht weiterhin ausschließlich im Backlog.

Die [preisunabhängige Statusversorgung](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-independent-status-observations) ergänzt beim vorhandenen Market-Data-Owner ein dauerhaftes Journal auch für negative/preislose Meldungen. Der [tatsächliche Quellenbefund](docs/reviews/B58_SOURCE_QUALIFICATION_2026-11-17.md) trennt erreichbare Originaldaten von weiterhin fehlender B58-Eignung.

Der anschließende [B04/B57-Regel- und Betriebsvertrag](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b04-b57-loss-monitoring-v1) ergänzt einen ausdrücklich begrenzten Verlustpfad: vorhandener Ausführungsowner, qualifizierte Eingänge, dauerhafte Verlustepisode, Hintergrundrunner und deduplizierter Hinweis im Arbeitsbereich. Dieser neue Commandpfad ändert die bisherigen passiven Evidenzreads nicht. Der zentrale Teilumfang ist standardmäßig ausgeschaltet; der Produktionskatalog geeigneter B58-Quellen ist leer. Synthetisch prüfbare Implementierung, reale Datenversorgung, Integration, Veröffentlichung und PC-Betrieb bleiben getrennt. Die vollständige Hebeltrader-Baseline wird dadurch nicht aktiviert.

Die gesonderte [indikative Positionsprüfung](docs/features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-entry-review-v1) nutzt vorhandene wirtschaftliche und Quellenbelege für einen ausdrücklich begrenzten alternativen Umfang. Dauerhafte Preis-, Prüf- und Datenproblemepisoden werden im bestehenden Runner ausgewertet; der Arbeitsbereich liest die gespeicherten Hinweise. Der [zentrale PC-Betriebsübergang](docs/technical/LINUX_LAUNCHER.md#einmaliger-übergang-auf-die-indikative-positionsprüfung) erhält die bestehende Installation und benötigt nach dem kontrollierten Update keine tägliche technische Bestätigung. Original-BID-Zeit, reine Empfangszeit und unbekannte Statusfortgeltung bleiben sichtbar getrennt.

## Entwicklung und Betrieb

Die [Entwicklungsanleitung](docs/technical/DEVELOPMENT_GUIDE.md) beschreibt die bestehenden Schichten, Versionen und Prüfeinstiege. Werkzeuge und Abhängigkeiten aus den aktuellen Manifesten/Lockdateien ermitteln; keine Gate-Absenkung. Tests mit Schreibzugriff nur in einer eindeutig identifizierten Wegwerfumgebung mit synthetischen Daten und abgefangenen externen Aufrufen ausführen.

Für vorhandene Installationen gelten die [Linux-Betriebsunterlagen](README_LINUX_DEPLOYMENT.md) und die jeweilige Release-Notiz. Bestehende Konfiguration, Compose-Kette, Consent-/Datenbestände und Sicherungen erhalten. Ein Monitoring-Einmallauf ist keine automatisch lesende Diagnose. Keine Modellaktivierung, echte Nachricht oder Providerzustimmung folgt aus einer Installation oder aus dieser Planung.
