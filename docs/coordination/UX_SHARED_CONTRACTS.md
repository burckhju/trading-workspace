# Gemeinsame UX-Verträge

Basis und Zuständigkeiten: [Masterplan](UX_MASTER_PLAN.md), [Ownership](UX_OWNERSHIP.md). Diese Regeln präzisieren die Zusammenarbeit auf bestehenden Fachverträgen. Sie führen weder ein neues persistiertes Modell noch eine zusätzliche API oder Finanzberechnung ein.

## Kontext, Navigation und gemeinsame Importgrenze — Owner UX-2

- `trade_id`, Positions-/Produktidentität, historische Plan-/Review-/Journal-/Lessonversion und Berichts-Rückkontext bleiben explizit gebunden. URL-Parameter sind Navigation, keine fachliche Evidenz.
- Erlaubte historische Pins und Parameter unverändert transportieren. Doppelte/ungültige Werte nicht still zu einer gültigen aktuellen Auswahl normalisieren; bestehende Validatoren entscheiden.
- Bereichswechsel innerhalb desselben Trades erhalten Formulardrafts und erzeugen keine allein navigationsbedingten Trade-/Positions-/Timeline-Reads.
- Echter Identitätswechsel verwendet bestehende Dirty-/Busy-Guards und Generation-/Abortschutz. Alte Antworten dürfen auch bei A→B→A keinen fremden Kontext anzeigen.
- Quellenansicht, Journal und Performance sind getrennte Owner-Reads. Ein gemeinsamer Bildschirm darf sie nicht als einen atomar gelesenen Finanzsnapshot ausgeben.

Die [Frontendarchitektur](../architecture/FRONTEND_ARCHITECTURE.md) untersagt direkte Imports interner Komponenten/Services eines anderen Features. #311 ergänzt solche Importe für die Navigation; #312 nutzt einen neuen Previewbaustein über eine bestehende Featuregrenze. Vor Integration muss der jeweilige Lead diese Grenze am konkreten Diff auflösen.

Für die neue, tatsächlich gemeinsam benötigte Navigation ist ein schmales Modul im **bereits vorhandenen** `frontend/src/shared/` der bevorzugte Zuschnitt, beispielsweise `trade-workspace-navigation/`. Es darf nur Darstellung und reine URL-Verträge enthalten. Dieser Pfad ist ein Integrationsvorschlag, noch keine vorhandene Implementierung.

Kein Import aus dem gemeinsamen Modul zurück in interne `trade/services/sourceView`- oder `performance/services/closedReportContext`-Implementierungen. Gemeinsame URL-Schlüssel/Transportfunktionen genau einmal ausgliedern oder bereits qualifizierte Ownerlinks über typisierte Props übergeben. `verifyClosedReport`, `verifyClosedStatistics`, Quellenvalidierung und Finanzlogik verbleiben beim Fachowner. Ein bloßes Reexport-Barrel belegt die Architekturkonformität nicht. Eine bewusst abweichende neue Abhängigkeitsrichtung benötigt eine konkrete ADR-/Featurevertragsentscheidung.

## Eingabe, Validierung und historische Herkunft — Owner UX-1

Die eigentliche Währungs-/Executionsemantik besitzt weiterhin `trade_position`.

- Vorhandener Wert, Herkunft, Gültigkeitsbezug und manuelle Änderung bleiben unterscheidbar. Eine Vorschau erzeugt keinen bestätigten Ausführungsfakt.
- Der manuelle Entwurf hat Vorrang vor verspäteten Reads. Menge, Preis, Währung oder Notiz nicht aus einer Vorschau zurückschreiben.
- `UNKNOWN`, `MIXED` und `CONFLICT` sind qualifizierte Domainzustände. Keine Ableitung aus Berichtswährung EUR, Browserzone, heutiger Listingwährung oder aktuellem Quote.
- Historische Quelle, Version, Originalzeit und die Zeitgenauigkeit behalten. Date-only ist kein erfundener Intradayzeitpunkt.
- Formularformat-/Vollständigkeitsprüfung und fachliche Backendvalidierung unterscheiden. Bestehende Reason-Codes und Feldbezüge an UX-3 übergeben.
- #312s neue Currency-Preview-GETs konsumieren den bestehenden schreibgeschützten Reader und Resolver. Capture löst beim ausdrücklichen Schreiben erneut auf; eine gelesene Vorschau autorisiert keine spätere Buchung.
- Genau ein gespeicherter Auswahlrun der exakt gebundenen Planversion darf automatisch lesend geöffnet werden. Mehrere Runs erzwingen weiterhin eine bewusste Auswahl; keine Evaluation oder Produktwahl durch Anzeige.
- Eine gültige Browserzeitzone ist ein editierbarer Berichtsvorschlag. Explizite URL-Filter behalten Vorrang; Währung, Berichtskohorte und Formelvertrag ändern sich dadurch nicht.

## Hinweise, Datenqualität und Folgeaktionen — Owner UX-3

Hinweise erklären die vorhandene Feststellung, Ursache, Auswirkung und einen bestehenden bewussten Benutzerweg. Details dürfen aufklappbar sein; eine relevante Blockierung bleibt unmittelbar erkennbar.

Laden, erfolgreich, leer, fachliche Warnung, fachlicher Fehler, technischer Fehler und fehlende Berechtigung bleiben unterscheidbar. Unbekannte oder veraltete Daten sind weder Null noch gesund. „Keine Alerts“ belegt weder eine funktionierende Überwachung noch eine vollständige Abdeckung.

Fachliches Risiko, Datenqualität, Schedulerzustand und Notificationzustellung bleiben getrennte Dimensionen. UI-Priorisierung bestimmt die Sichtbarkeit vorhandener Hinweise; sie berechnet keine neue Handelsaussage und schwächt keine Domainblockierung ab. Domaincodes wie `REFERENCE_ONLY`, `TIMESTAMP_UNKNOWN`, `NOT_EVALUABLE` oder `truncated` werden nicht in eine neue globale Fachenum übersetzt.

Navigation und Rendering bleiben lesend. Ein Retry wiederholt nur den benannten vorhandenen Lesevorgang; Providerrefresh, Regelkonfiguration, Freigabe, Buchung oder Strategieaktivierung bleiben explizite bestehende Commands. Links benennen Ziel und Wirkung. Benachrichtigungsversand folgt nicht aus einem angezeigten Hinweis.

UX-2 legt Hostplatzierung und Fokusziele fest. UX-3 verwendet verständliche Texte, sichtbaren Fokus, passende Live-Regionen und zusätzliche Kennzeichnung neben Farbe. Ein neuer gemeinsamer Renderer wahrt die Importgrenze; bestehendes `market/components/ApiFeedback.tsx` ist kein automatisch freigegebener appweiter Contract.

## Diagramme, Kennzahlen und Datenlücken — Owner UX-4

- Vorhandene Backendantworten verwenden. PnL, Risiko, Trefferquote, Profit-Faktor, Normalisierung und Währungsqualifikation nicht im Frontend nachrechnen.
- Einheiten, Währung, Zeitraum, Quelle, Datenstand und vorhandene Definitions-/Berichtsgrundlagen sichtbar machen; genaue Geldwerte in der Evidenz erhalten. Numerische Plotkoordinaten sind keine neue Finanzquelle.
- Positionsverlauf trennt Währung, Preisart und Quelle; einzelne Kursbeobachtungen bleiben Punkte ohne suggerierte Verbindung. Marktcharts erhalten die qualifizierten Lücken und Vergleichsgrenzen.
- Datumgenaue Executions oder unbekannte Währungen bleiben in der Ereignis-/Evidenzliste mit Grund sichtbar. Präzise Marker benötigen vorhandene serverseitige Qualifikation.
- Leere Antwort, technischer Fehler, fehlende Berechtigung und gekürzte Daten getrennt anzeigen. Unvollständige Kennzahl nie als Null; Statistik bezieht sich auf die qualifizierte Gesamtkohorte, nicht auf die sichtbare Tabellenseite.
- Anzeige startet keinen Backfill, Providerabruf oder neue Kursspeicherung. Vorhandene Lazy-Load-, Retry- und stale-response-Grenzen erhalten.
- Eine zugängliche Tabelle oder gleichwertige Textansicht bleibt verfügbar, auch bei nicht ladbarem Diagrammmodul. Responsive Hauptansicht und aufklappbare Herkunft gemeinsam prüfen.

Referenzen: [Positionskursverlauf](../ui/position-price-history.md), [Monitoring-Datenqualität](../monitoring-data-quality.md), [Ausführungswährung](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md), [Abschlusskohorte](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md).

## Vertragsänderung und Prüfung

Ein neues Feld oder veränderte Bedeutung erhält vor Integration: genauen Domain-Owner, Producer/Consumer, Kompatibilitätsentscheidung, fehlende/veraltete/ungültige Fälle, historische Referenzen und betroffene Contract-/Integrationstests. Gemeinsame API-/Domainänderungen werden nicht gleichzeitig in mehreren unabhängigen PRs entwickelt.

UX-3 formuliert die Darstellung von Datenqualität; die fachliche Entscheidung über Qualität bleibt bei jedem bestehenden Owner. UX-2 koordiniert Readback/Hostinvalidierung; UX-1 und UX-4 prüfen ihre jeweiligen Reaktionen darauf. Diese Trennung ist bei jeder gemeinsamen Regression nachzuweisen.
