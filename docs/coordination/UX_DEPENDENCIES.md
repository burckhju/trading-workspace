# UX-Abhängigkeiten und Integrationsfolge

Diese Datei steuert technische Reihenfolge und Konfliktauflösung, keine fachlichen Aufgabenstände. Maßgeblich bleiben [PRODUCT_BACKLOG](../planning/PRODUCT_BACKLOG.md), [Ownership](UX_OWNERSHIP.md) und [gemeinsame Verträge](UX_SHARED_CONTRACTS.md). Konkrete aktuelle Heads/CI: [Integrationsprotokoll](UX_INTEGRATION_STATUS.md).

## Gemeinsame Änderungsflächen

| Schnittstelle | Führender Owner | Abhängigkeit vor Integration |
|---|---|---|
| UX-1 / UX-2: `TradeManagementPage.tsx`, Formulare, Readback | UX-2 für Hostintegration | UX-1 liefert Preview-/Reload-Teilschnitt; beide prüfen Navigation, Entwurfserhalt und Invalidierung. |
| UX-1 / UX-3: Validierung und Herkunft | UX-1 für Eingabefakten | UX-3 konsumiert vorhandene Feld-/Reason-/Quelleninformationen; Darstellung ändert keine Domainentscheidung. |
| UX-2 / UX-3: Hinweisposition und Fokus | UX-2 | UX-3-Hinweismuster vor Hosteinbindung abstimmen; relevante Blockierung bleibt sichtbar. |
| UX-2 / UX-4: Diagrammslot und Nachladen | UX-2 | UX-4 liefert vorhandenen lesenden Baustein; keine neue Positions-/Kursabfrage allein durch Hashnavigation. |
| UX-3 / UX-4: Qualitätsdarstellung | UX-3 | UX-4 konsumiert konsistente Erklärung; leer, Fehler, fehlend, veraltet und gekürzt bleiben unterscheidbar. |
| Alle: APIs und Domainmodelle | Jeweils genau der Domain-Owner aus der Ownership-Tabelle | Additive Felder/Reads und historische Bedeutung erst mit allen betroffenen Consumern klären. Kein gemeinsamer „UX-Domainowner“. |

## Empfohlene Reihenfolge

1. **Koordinationsgrundlage im eigenen Draft-PR prüfen und als gemeinsamen Übergabepunkt verwenden.** Bestehende Leads verknüpfen exakten Koordinationshead, ihren eigenen Head und Dateiumfang. Die technische Abstimmung braucht keinen vorgezogenen Produktmerge.
2. **UX2-A / #311 zuerst integrationsfähig machen:** Lesson-URL-Consumer vollständig anpassen, gemeinsame Navigationsgrenze herstellen, aktuelle Head-/Testmerge-CI qualifizieren. UX-2 stabilisiert damit Kontext und Hostslots. Eine tatsächliche Integration erfolgt ausschließlich nach ausdrücklicher Mergefreigabe.
3. **UX1 / #312 anschließend auf dem tatsächlich integrierten Stand qualifizieren:** UTC-feste Performance-Testannahmen, bestehende API-/Previewgrenze und Domainprüfung abschließen; gezielte Hoständerung mit UX-2 einbinden. Neu basierten Head und gemeinsamen Laufzeitvertrag prüfen. Die eigenständigen Test-/Komponentenkorrekturen können schon parallel zu Schritt 2 erfolgen.
4. **UX-3-Präsentationsschnitt nach belegter Leadübergabe:** vorhandene Hinweise und Datenqualität vereinheitlichen, unveränderte Domainzustände und sichere Benutzerwege nachweisen. Keine neue Fachregel als Nebenänderung.
5. **UX-4-Präsentationsschnitt nach belegter Leadübergabe:** vereinbarte Qualitätsdarstellung in vorhandene Charts/Kennzahlen übernehmen. Unabhängige lesende Komponentenqualifikation kann parallel zu UX-3 laufen; gemeinsame Hoständerungen bleiben seriell bei UX-2.

#311 und #312 sind auf derselben Basis entwickelt; es besteht noch keine harte Codeabhängigkeit zwischen ihren Branches. Die Reihenfolge ist eine bewusste Integrationsentscheidung wegen Kontext-/Hostownership. Weder einen grünen Einzel-PR noch den konfliktfreien Textvergleich als gemeinsamen Laufzeitnachweis ausgeben.

Die Alt-PRs #187, #197, #205, #207 und #220 sind keine Voraussetzung dieser Folge. Ihre ursprünglichen Diffs, überholten Basen und inzwischen vorhandene Main-Implementierung müssen separat mit dem jeweiligen Fachowner abgeglichen werden. Insbesondere #205 liefert keine fehlende aktuelle Chartfunktion; #207 enthält am geprüften Head lediglich einen Entwicklungsworkflow. Keine eigenmächtige Übernahme oder Schließung.

## Gemeinsame Regressionen

| Bereich | Erforderlicher beobachtbarer Nachweis |
|---|---|
| Kontext / Navigation / Eingaben | Ungespeicherter SELL- und Korrekturentwurf über Bereichswechsel erhalten; echte Tradewechsel korrekt geschützt; A→B→A und verspätete Antworten isoliert. |
| Reads / Wiederverwendung | Bereichswechsel löst keine zusätzlichen Trade-/Positions-/Timeline-Reads aus. Erfolgreicher Buchungs-/Quellenreadback aktualisiert Preview und Historie, ohne manuelle Eingaben zu löschen. |
| Historische Quellen | Plan-, Review-, Journal- und Lessonpins bleiben exakt. Ungültige/mehrfache Pins werden nicht still auf aktuell umgebogen; fremde Quelle erzeugt keine gültige Anzeige. |
| Währung / Formulare | Vorhandene Resolver und UNKNOWN/MIXED/CONFLICT erhalten; Preview erzeugt keine `currency_confirmation`; Capture prüft erneut. Berichtszone explizit testen, einschließlich UTC-Umgebung und URL-Vorrang. |
| Journal / Lessons | Neue Lesson-URLs mit Query/Hash korrekt konsumieren: ID über URL-Pfad lesen; Trade-/Versions-/Rückkontext ausdrücklich prüfen. Schreibanzahl, Currentness, Korrektur und lokale API-Grenze erhalten. |
| Hinweise / Aktionen | Fachliches Risiko, Datenqualität, Scheduler und Zustellung getrennt; Rendering/Navigation ohne Mutation; Fehler nicht als leer oder gesund behandeln. |
| Charts / Statistik | Originalwerte, Währung, Preisart, Quelle, Lücke und Zeitgenauigkeit erhalten; Tabellenfallback, Kürzung und Fehler sichtbar; Gesamtkohorte statt sichtbarer Seite. |
| Responsivität / Barrierefreiheit | Kleine und große Viewports, Zoom, Keyboard, Fokus nach Navigation, Live-Regionen und alternative Datentabelle. Automatisierte Fälle und noch fehlende manuelle Abnahme getrennt dokumentieren. |

Vorhandene gezielte Suites: `TradeManagementPage`, `TradeManagementPriceHistory`, `TradeWorkspaceNavigation`, `ExecutionCurrencyPreview`, Performance-Seiten, `TradeAlertsPanel`, `MonitoringRuntimePanel`, `PositionPriceHistory`, `TimeSeriesChart`; Browserpfade `trade-workspace-navigation`, `execution-currency-reuse`, `post-trade-handoff-pin`, `post-trade-journal-postgres`, `position-price-history`. Neue Dateien aus offenen PRs sind vor deren Integration noch nicht Main-Bestand.

## Integrationsprüfung für jeden PR

MASTER prüft jeweils:

1. Vollständigen tatsächlichen Diff und Ursprungsschnitt; implementiert, vorbereitet und behauptet unterscheiden.
2. Unabhängigkeit oder exakte vorgelagerte Commit-/Vertragsabhängigkeit; vorhandene Funktionen nicht erneut liefern.
3. Einhaltung der Shared Contracts sowie des einzelnen API-/Domainowners.
4. Aktuelle GitHub-Run- und Jobergebnisse am richtigen Head; Testmerge und Eltern/Tree prüfen. Fehlend, abgebrochen und übersprungen sind kein erfolgreicher Test.
5. Erneut aufgelösten Main und Datei-/Semantikkonflikte; nach Änderungen am Head oder an der Basis betroffene Prüfung erneuern.
6. Gemeinsame Regressionen am tatsächlich vorgesehenen Gesamtstand, nicht nur isolierte Branchtests.
7. Verbleibende Domainentscheidungen, Fachabnahme, Review und ausdrückliche Mergeberechtigung.

Die bestehenden [Backend](../../.github/workflows/backend.yml)-, [Frontend](../../.github/workflows/frontend.yml)-, [E2E](../../.github/workflows/e2e.yml)- und [Publikationswächter](../../.github/workflows/version-tag.yml)-Gates bleiben unverändert. Tests mit Schreibzugriff nur in identifizierter Wegwerfumgebung mit synthetischen Daten und abgefangenen externen Aufrufen. Keine Sicherheits-/Ergebnis-/Coverageprüfung lockern, um neue UX-Consumer grün zu bekommen.

Erfolgreicher PR-Test, Main-Integration, Tagveröffentlichung, PC-Installation und menschliche Fachabnahme sind fünf getrennte Nachweise. Dieser Koordinationsauftrag gestattet nur Analyse, Dokumentationsbranch und Draft-PR.
