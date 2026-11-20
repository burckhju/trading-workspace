# Roadmap

> Ursprüngliche Zusagen erhalten; heutige Arbeit über vier Lieferziele koordinieren.

## Dokumentinformationen

| Feld | Wert |
|---|---|
| Dokument-ID | DOC-004 (bestehende Kennung) |
| Revision | Nachweisfortschreibung 2026-11-20 auf v1.5.52; keine neue Produktumfangsentscheidung |
| Prüfstand | `c7db441de36297a98d47cdf28c64b4e5d9994692` / `main` / Softwaretag `v1.5.52` |
| Aktueller Arbeitsstatus | Ausschließlich im [Product Backlog](../planning/PRODUCT_BACKLOG.md) |

Die [datierte Einstiegssicht](../planning/PRODUCT_BACKLOG.md#aktueller-stand) und der [einzige nächste Arbeitsauftrag](../planning/PRODUCT_BACKLOG.md#naechster-schnitt) trennen den belegten v1.5.51-PC-Betrieb aus #367 von der inzwischen integrierten und veröffentlichten Produktkorrektur #368 / v1.5.52. Die reale Wirkung des Fixes auf dem privaten Bestand bleibt ein gesonderter Nachweis; seine erneute Implementierung, Integration oder Veröffentlichung ist kein offener Auftrag. Historische Vorbereitungs- und Freigabestände sind im Backlog gesondert eingeordnet.

<a id="historische-baseline"></a>
## Ursprüngliche Roadmap als unveränderte Referenz

Die [Roadmap vom 22.07.2026, Version 1.1](archive/ROADMAP_2026-07-22.md) ist die Vergleichsbasis. Sie wird als **genau eine unveränderte historische Baseline** im Repository erhalten. Der Inhalt entspricht bytegenau der vor der Konsolidierung vom 13.10.2026 archivierten Roadmap; Git-Blob `919ed7570580b1d883a409f864ed15747fbfda3e`, am 20.11.2026 erneut geprüft. Die Metadaten einschließlich damaligem Approved-Status und der ursprünglichen Reihenfolge bleiben historische Aussagen, keine neue Freigabe.

Die zwölf M-IDs M0–M11 werden weder umbenannt noch neu vergeben. Alle 63 ursprünglichen Inhaltsziel-Vorkommen sind im [Originalabgleich des zentralen Backlogs](../planning/PRODUCT_BACKLOG.md#originalzuordnung) einzeln einem maßgeblichen Eintrag zugeordnet. Ziel- und Ergebnisformulierungen jedes Meilensteins bleiben vollständig in der Baseline. Ein Softwaretag – auch `v1.5.52` – erklärt nicht rückwirkend alle ursprünglichen Meilensteinansprüche für erfüllt. Es werden keine Fertigstellungsprozente aus undefinierter Grundgesamtheit abgeleitet.

| Ursprünglicher Bezug | Rückverfolgbare Inhalte und aktueller Arbeitsstatus |
|---|---|
| M0 | [Zuordnung M0](../planning/PRODUCT_BACKLOG.md#original-m0) |
| M1 | [Zuordnung M1](../planning/PRODUCT_BACKLOG.md#original-m1) |
| M2 | [Zuordnung M2](../planning/PRODUCT_BACKLOG.md#original-m2) |
| M3 | [Zuordnung M3](../planning/PRODUCT_BACKLOG.md#original-m3) |
| M4 | [Zuordnung M4](../planning/PRODUCT_BACKLOG.md#original-m4) |
| M5 | [Zuordnung M5](../planning/PRODUCT_BACKLOG.md#original-m5) |
| M6 | [Zuordnung M6](../planning/PRODUCT_BACKLOG.md#original-m6) |
| M7 | [Zuordnung M7](../planning/PRODUCT_BACKLOG.md#original-m7) |
| M8 | [Zuordnung M8](../planning/PRODUCT_BACKLOG.md#original-m8) |
| M9 | [Zuordnung M9](../planning/PRODUCT_BACKLOG.md#original-m9) |
| M10 | [Zuordnung M10](../planning/PRODUCT_BACKLOG.md#original-m10) |
| M11 | [Zuordnung M11](../planning/PRODUCT_BACKLOG.md#original-m11) |

## Übergang zur dauerhaften Planung

Die [acht Funktionsbereiche](../planning/MODULE_AND_FEATURE_CATALOG.md#planungssichten) sind dauerhafte Planungssichten auf bestehende Features und Consumer, keine neuen Module, FT-IDs oder Paketgrenzen. Modelle/Regelgovernance, durchgängiger Arbeitsablauf/Bedienbarkeit und technische Qualität/Betrieb begleiten jeden Bereich. Sie beginnen nicht erst nach Abschluss der Features.

Vorhandene FT-/PB-Kennungen und ein schreibender fachlicher Owner je Objekt bleiben erhalten. Die [Abnahmematrix](../planning/PRODUCT_BACKLOG.md#abnahmematrix) ist Bestandteil des einzigen Backlogs. Katalog, Roadmap, README und Traceability verlinken darauf, statt Aufgabenstatus parallel zu pflegen. Historische Release-/Reviewbelege bleiben als datierte Nachweise erhalten.

<a id="lieferziele"></a>
## Lieferziele A–D

Die Buchstaben bezeichnen überprüfbare Ergebnisse, keine neue Meilensteinnummerierung oder starre Abfolge.

### A — Verlässlicher täglicher Arbeitsplatz

**Abnahmegrenze:** Der Benutzer erkennt seine nächsten Aufgaben, Datenbereitschaft, offenen Positionen, wirksamen Monitoringregeln sowie Alert-/Zustellzustände. Herkunft, fehlende/veraltete/indikative Daten und Fehler bleiben verständlich. Die lesende Zusammenführung erzeugt keine konkurrierenden Done-/Acknowledgement-/Assignment-Zustände.

**Betriebsgrenze:** Nachweise beziehen sich auf eine benannte Zielinstallation – in der gelesenen Release-Dokumentation JMBbot – mit tatsächlich installierter Version/Commit, Schema, unveränderter Compose-Provenienz und datierten Beobachtungen. Software-Auslieferung, historische Installationsnotiz und aktueller Betrieb sind getrennt. Eine Prüfanleitung gilt nicht als erfolgreicher Lauf.

**Abhängigkeiten:** Autoritative Fachzustände, qualifizierte vorhandene Daten und bereits erlaubte Provider-/Zustellkonfiguration. Keine neue Zustimmung, keine zusätzlichen Liveabrufe oder Testnachrichten aus diesem Planungsauftrag. [Workspace](../planning/PRODUCT_BACKLOG.md#operational-workspace), [Datenbereitschaft](../planning/PRODUCT_BACKLOG.md#market-data-quality), [Monitoring](../planning/PRODUCT_BACKLOG.md#monitoring-rules), [Zustellung](../planning/PRODUCT_BACKLOG.md#notification-delivery) und [Installation](../planning/PRODUCT_BACKLOG.md#operations-installation) werden getrennt nachgewiesen.

### B — Vollständiger Abschluss- und Lernprozess

**Abnahmegrenze:** Tatsächlicher Vollverkauf → zulässige Nachbeobachtung → Exit Review → Journal → belegte Lesson ist als Nutzerreise nachvollziehbar. Historische Korrekturen erhalten ursprüngliche Fakten und konkrete Versionen; veraltete Herkunft wird sichtbar, nicht still umgebogen. Journalentwurf, Journalabschluss, Evidence-Materialisierung und Lesson sind unterscheidbar.

**Nicht-Soll:** Performance ist keine Voraussetzung für einen Journalentwurf. Die Nutzerreise führt keine neue technische Zwangsabhängigkeit für bereits vorhandene Evidence-/Lesson-Funktionen ein. Weder Reviewabschluss noch Journal oder Evidence erzeugen automatisch eine Interpretation, Modellfreigabe oder tatsächliche Ausführung.

**Abhängigkeiten:** Effektive Execution-Historie, zulässige Beobachtungsdaten, explizite Review-Currentness und ein geklärter FT-012-Journalvertrag. Die vorhandenen Handoffs und Materialisierung werden wiederverwendet. [Vollverkauf](../planning/PRODUCT_BACKLOG.md#pb-017-close), [Nachbeobachtung](../planning/PRODUCT_BACKLOG.md#pb-018-observation), [Review](../planning/PRODUCT_BACKLOG.md#pb-018-review), [Journal](../planning/PRODUCT_BACKLOG.md#pb-019-journal), [Lessons](../planning/PRODUCT_BACKLOG.md#pb-019-lessons) und [Korrekturen](../planning/PRODUCT_BACKLOG.md#pb-018-currentness) behalten getrennte Nachweise.

### C — Belastbare Performance-Auswertung

**Abnahmegrenze:** Definierte Perioden-/Tradeauswertungen erläutern Grundgesamtheit, Zeitraum, Quellen, Korrekturstand, Währungs-/Preisgrundlagen, Berechnung und nicht berechenbare Werte. Ein konkreter Kennzahlensatz wird fachlich entschieden und anhand synthetischer Referenzfälle qualifiziert; API/UI konsumieren dieselbe Backendberechnung.

**Nicht-Soll:** Positions-Brutto-PnL oder Chart-Kursveränderung sind keine vollständige tradeübergreifende Performance. Keine erfundene Depot-Equity, Gebühren, Steuern, FX-Kurse, historischen Kenntnisstände oder Nettoergebnisse. Fehlend ist nicht Null. Kennzahlendefinitionen werden nicht still aus allgemeinem Finanzwissen ergänzt.

**Abhängigkeiten:** Wirksame Execution-Fakten, qualifizierte verfügbare Daten und explizite Kennzahlen-/Periodenverträge. B und C können unabhängige Teile liefern; C blockiert keinen Journalentwurf. [Brutto-PnL](../planning/PRODUCT_BACKLOG.md#pb-017-gross-pnl) bleibt Vorleistung; [Kennzahlen](../planning/PRODUCT_BACKLOG.md#pb-019-performance-metrics), [Statistiken](../planning/PRODUCT_BACKLOG.md#pb-019-performance-statistics), [Dashboard](../planning/PRODUCT_BACKLOG.md#pb-019-performance-dashboards) und [Periodenauswertung](../planning/PRODUCT_BACKLOG.md#pb-019-performance-evaluations) verweisen auf die zentrale Matrix.

### D — Kontrollierte Verbesserung einer konkreten Regel

**Abnahmegrenze:** Evidence → Hypothese → Vorschlag → Validierung → explizite Freigabe → gesonderte Aktivierung → reproduzierbare Anwendung und kontrollierte Rückkehr zu einer früheren Version wird für **eine konkrete bestehende Regel** belegt. Jede Entscheidung bindet genaue Evidence-/Basis-/Modell-/Aktivierungsidentitäten und gegebenenfalls den Validierungsstichtag.

**Nicht-Soll:** Keine zweite Kandidatenstrecke und keine automatische Aktivierung durch Installation, Migration oder Freigabe. Allgemeine Modellinfrastruktur beweist nicht Markt-, Scanner-, Stop-, Ziel-, Produktscore-, Trade-Assistant- oder Nachbeobachtungsmodell. Ein Preview ist keine fachliche Validierung oder Performanceprognose.

**Abhängigkeiten:** Vorhandene FT-012-/FT-013-Strukturen und passende freigegebene fachliche Definition. Die bestehende [Kandidatenfamilie](../planning/PRODUCT_BACKLOG.md#pb-020-candidate-family), [Governance](../planning/PRODUCT_BACKLOG.md#pb-020-governance) und [gesonderte Aktivierung](../planning/PRODUCT_BACKLOG.md#pb-020-activation) werden nachgewiesen, nicht pauschal neu gebaut. Familienbezogene Lücken bleiben eigene Einträge.

## Fokus und Umfangsentscheidungen

B und C behalten den begründeten Planungsfokus. Die aktuell belegten Datenprobleme in A begründen den im Backlog bestimmten Vorrang der [positionsweisen Ursachen- und Abdeckungsklärung](../planning/PRODUCT_BACKLOG.md#naechster-schnitt). D kann unabhängig qualifiziert werden, soweit vorhandene freigegebene Evidence und Regeln genügen. A–D schließen keine ursprünglichen Zusagen aus: Insbesondere der weitere Watchlist-Anspruch, Scanner, Marktbreite, Produktscore, Produktwechsel, weitere Modellfamilien und verbleibende Performanceanforderungen bleiben im [Originalabgleich](../planning/PRODUCT_BACKLOG.md#originalzuordnung). Bereits gelieferte Journal-, Bruttoauswertungs- und Kandidaten-Governance-Schnitte werden dort nicht erneut zur Implementierung eingeplant.

„Bewusst verschoben“ oder „aus Zielbild entfernt“ benötigt eine belegte Produktentscheidung mit Umfang, Datum und Referenz. Ein enger V1-Nicht-Scope ist keine dauerhafte Entfernung. Fehlt die Entscheidung, bleibt der Anspruch als offener Umfang bzw. Entscheidungsvorschlag im Backlog. Der [nächste einzelne Umsetzungsschnitt](../planning/PRODUCT_BACKLOG.md#naechster-schnitt) und die [Nachweisgrenzen](../planning/PRODUCT_BACKLOG.md#nachweisregister) werden ausschließlich dort gepflegt.
