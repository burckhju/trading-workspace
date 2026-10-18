# Trading Workspace

Trading Workspace unterstützt einen benutzergesteuerten Tradingprozess: Referenzdaten und Marktanalysen, Tradevorbereitung und Produktauswahl, Erfassung tatsächlicher Ausführungen, Positionsmanagement sowie Nachbeobachtung und Lernen. Das System trifft und vollzieht keine autonomen Kauf-, Verkaufs-, Halte-, Produktwahl- oder Positionsgrößenentscheidungen. Tatsächliche Ausführungen sind vom Benutzer bestätigte Fakten, keine Brokerorders.

## Softwarestand und Planung

Die versionierte Software ist in [VERSION](VERSION) festgehalten. Der am 13.10.2026 geprüfte Stand ist `v1.5.5` / `a78288ad38610656480d0363abe657b567c7ba94`; Einzelheiten und Betriebsgrenzen stehen in der [Release-Notiz](docs/releases/V1.5.5-ISSUER-COVERAGE.md). Ein Softwaretag belegt weder die aktuelle Installation auf dem Nutzer-PC noch die vollständige Erfüllung sämtlicher ursprünglicher Roadmap-Ziele.

**Aktueller Arbeitsstatus und Abnahmematrix:** [Product Backlog](docs/planning/PRODUCT_BACKLOG.md). Es ist die einzige maßgebliche Aufgabenstatusquelle. Hier steht bewusst keine zweite vollständige Feature-Statusliste.

| Orientierung | Maßgebliche Quelle |
|---|---|
| Ursprüngliche Zusagen M0–M11 und Lieferziele A–D | [Roadmap](docs/foundation/ROADMAP.md) |
| Acht dauerhafte Funktionsbereiche, drei Querschnittsthemen, bestehende FT-IDs und Ownership | [Module and Feature Catalog](docs/planning/MODULE_AND_FEATURE_CATALOG.md) |
| Implementierung, Tests, Abnahme und Betrieb mit getrennten Nachweisen | [Traceability](docs/foundation/TRACEABILITY.md) |
| Fachliche Grundlagen und Architektur | [Project](docs/foundation/PROJECT.md), [Architecture](docs/foundation/ARCHITECTURE.md) |

Journal, Lessons, Positions-Brutto-PnL, tradeübergreifende Performance und Modellgovernance sind unterschiedliche Fähigkeiten. Fehlende Nachweise und offene ursprüngliche Anforderungen bleiben im Backlog sichtbar. Marktcharts oder eine vorhandene Kandidatenstrecke erklären keine benachbarten Funktionen für fertig.

## Entwicklung und Betrieb

Die [Entwicklungsanleitung](docs/technical/DEVELOPMENT_GUIDE.md) beschreibt die bestehenden Schichten, Versionen und Prüfeinstiege. Werkzeuge und Abhängigkeiten aus den aktuellen Manifesten/Lockdateien ermitteln; keine Gate-Absenkung. Tests mit Schreibzugriff nur in einer eindeutig identifizierten Wegwerfumgebung mit synthetischen Daten und abgefangenen externen Aufrufen ausführen.

Für vorhandene Installationen gelten die [Linux-Betriebsunterlagen](README_LINUX_DEPLOYMENT.md) und die jeweilige Release-Notiz. Bestehende Konfiguration, Compose-Kette, Consent-/Datenbestände und Sicherungen erhalten. Ein Monitoring-Einmallauf ist keine automatisch lesende Diagnose. Keine Modellaktivierung, echte Nachricht oder Providerzustimmung folgt aus einer Installation oder aus dieser Planung.
