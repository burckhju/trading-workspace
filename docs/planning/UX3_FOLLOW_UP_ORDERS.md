# UX3-B bis UX3-D — Gesonderte Umsetzungsaufträge

## Dokumentinformationen

| Feld | Wert |
| --- | --- |
| Dokumenttyp | Vorbereitete Umsetzungsaufträge, Entwurf 0.2 |
| Datum | 31.10.2026, Europe/Vienna |
| Geprüfte Basis | `main` / `1883f7f330719453958f8be1dd51d48db816662e`, v1.5.35 |
| Vertragsgrundlage | [UX3-A Hinweisvertrag](../ui/ux3-notice-contract.md) |
| Bestandsnachweis | [UX3-A Hinweisinventur](../ui/ux3-notice-inventory.md) |
| Arbeitsstatus | Ausschließlich [Product Backlog](PRODUCT_BACKLOG.md#operational-workspace) |
| Freigabegrenze | Noch keine gemeinsame Schnittstellen- oder Umsetzungsfreigabe für UX3-B/C/D |

Diese Aufträge bereiten kleine Folge-PRs vor. Sie starten keine Produktimplementierung.
UX3-A ändert ausschließlich Dokumentation. Vor dem ersten produktiven Schnitt sind
die tatsächlichen Schnittstellen mit UX-1, UX-2, UX-4 und den Domain-Ownern abzustimmen.
Dieses Dokument führt keine zweite Statusübersicht neben dem Product Backlog.
Die nachfolgenden Akzeptanzfälle sind Anforderungen, keine bereits bestandenen Tests.

## Gemeinsamer Rahmen

- Bestehende Domainzustände, erlaubte Operationen und Datenqualifikationen bleiben maßgeblich.
- Keine Währungsresolver, Finanzberechnungen, Providerqualifikationen, Tradingregeln oder Planfreigaben in UX-3.
- Keine automatische Buchung, Stornierung, Lesson, Modelländerung oder Runtime-Aktivierung.
- Keine neue persistierte Hinweis-, Quittierungs-, Dismiss- oder Recovery-Zustandsmaschine.
- Keine Produktivformulare oder Workspace-Komponenten vor abgestimmten Schnittstellen ändern.
- Keine Merges, Releases oder fachlichen Aktivierungen im Rahmen dieser Aufträge.
- Jeder PR besitzt einen begrenzten Nutzerfall, einen konkreten Bestandbeleg und passende Regressionen.
- Texte, Objektbezug, Auswirkung, Systemleistung und verbleibende Nutzeraktion zusammen prüfen.
- Fehlende Ursachen oder Namen sichtbar benennen; keine UUID als alleinigen Hinweistext verwenden.
- Historische Pins erhalten; Eingaben und Konfliktverhalten verbleiben beim bestehenden Owner. Keine automatische Neubindung eines bestätigungspflichtigen Auftrags.

## Abhängigkeiten und Übergaben

| Partner | Erforderliche Übergabe | Grenze |
| --- | --- | --- |
| UX-1, [Draft-PR #312](https://github.com/burckhju/trading-workspace/pull/312) | Tatsächlicher Head, Währungsvorschau, manuelle Eingabe, vorhandene Wiederverwendung und Preview-/Reload-Teilschnitt | Vorschau ist kein manuell bestätigter Beleg; keine Doppelableitung im Hinweisadapter. Hostinvalidierung gehört UX-2 |
| UX-2, [Draft-PR #311](https://github.com/burckhju/trading-workspace/pull/311) | Als einziger `TradeManagementPage`-Integrator: Anzeigeplätze, öffentliche URL-/Pinhelper, Rückkontext, Hostfokus, Readback/Invalidierung, Reader-/Formularlebensdauer und Guards | Draft-Verhalten nicht als Main-Bestand voraussetzen; keine parallele URLbibliothek oder gleichzeitige Hoständerung durch UX-3 |
| UX-4 | Visualisierung vorhandener Verwendbarkeitsflags, Abdeckung, Zeitarten und zugänglicher Legenden mit UX3-Qualitätssprache | Gemeinsamer Rahmen in #313 liegt vor; eigener UX4-Implementierungshead nicht identifiziert. Bedeutung liefert der Domain-Owner, keine UI-eigene Datenqualifikation |
| Domain-/API-Owner | Genaue Ursache, Operationsscope, erlaubter Command, vorhandene Retry- und Recoveryfakten | Grobe Fehlercodes nicht durch Parsing englischer Fehlermeldungen verfeinern |
| UX-MASTER, [Draft-PR #313](https://github.com/burckhju/trading-workspace/pull/313) | Gemeinsamer Vertrag, Dateiownership, Übergabe und Integrationsreihenfolge | Product Backlog bleibt einzige Arbeitsstatusquelle; veröffentlichter Vertrag beweist keine Kenntnisnahme anderer Leads |
| Paralleler UX3-Entwurf, [Draft-PR #314](https://github.com/burckhju/trading-workspace/pull/314) | Ein gemeinsamer Begriff-/Typvertrag, Kanonisierung und ein B1/F1-Pilot | Fünf Darstellungsarten vs. sieben Inhaltsfamilien, stabile Identität vs. Snapshot sowie Link-API vs. Owneraktionen gemäß Vertragsabgleich konsolidieren |

Vor jedem Schnitt den dann aktuellen Main und die betroffenen PR-Heads neu prüfen.
Eine Dokumentation über einen Draft-PR ist kein Nachweis gemeinsamer Integration.
Unveröffentlichte Arbeit bleibt eine offene Abhängigkeit; keine gegenseitigen
Feature-Branch-Merges und keine Übernahme fremder produktiver Änderungen allein
zur Vereinfachung dieses Auftrags.

Der [Koordinationsvertrag](https://github.com/burckhju/trading-workspace/blob/2312abfe8834a1b652b100fc635c4d36172d5c32/docs/coordination/UX_SHARED_CONTRACTS.md)
bevorzugt eine schmale öffentliche Grenze im bestehenden `frontend/src/shared/`.
UX2 hat die Navigation am [Draft-Head `9c9c949c`](https://github.com/burckhju/trading-workspace/commit/9c9c949c32f53eba7980cd8109bfa9f29e4d0bb5)
tatsächlich dort ausgegliedert; auf Main ist sie noch nicht vorhanden. Gemeinsame
Komponenten dürfen weder Featureinternas importieren noch Finanz-/Quellenvalidatoren
in Shared ziehen. Vorbereitete Ownerlinks über typisierte Props sind eine Alternative;
ein Reexport-Barrel allein löst die Importgrenze nicht.

Vorgeschlagene Integration aus #313: **Koordination → UX2-A → UX1 → UX3 → UX4**.
MASTER entscheidet die tatsächliche Reihenfolge und Konflikte. Dies ist keine harte
Codeabhängigkeit aller Einzel-PRs und keine Mergefreigabe: abgegrenzte autorisierte
Komponentenarbeit kann parallel qualifiziert werden; Hoständerungen bleiben bei UX-2.

### Einordnung der parallelen F1–F8-Aufträge

Die [Rollout-Aufträge aus #314](https://github.com/burckhju/trading-workspace/blob/52a24266dce1ec048b23360b4b75d5b3f54d746b/docs/ui/ux-3/integration-and-rollout.md)
und B/C/D sind alternative Zuschnitte derselben Arbeit, keine zwei gestarteten Programme.

| Auftrag aus #314 | Bezug hier | Konsolidierungsgrenze |
| --- | --- | --- |
| F1 | B1 | Genau ein lesender Pilot; `RealizedGrossSources` als gemeinsamer Kandidat |
| F2 | Zusätzliche Finanzowner-Abstimmung vor betroffener Migration | B2 korrigiert belegbar falsche Texte, autorisiert keine neue Zahlenqualifikation |
| F3 | Gesonderte Vorbereitung für Refreshdiagnostik | Kein pauschaler Blocker für B3s bereits vorhandene Alert-/Health-DTOs |
| F4 | B2 und Teile von D3 | Ein abgestimmter Kurs-/Recoveryzuschnitt |
| F5 | D2 und Performancekontext | Jeweils eine Berichtsart mit eigenem Ownervertrag |
| F6 | C1 und späterer Planadapter | Nicht mit B4s Kaufstatuskorrektur gleichsetzen |
| F7 | C1/C3 und spätere Quellenadapter | Historische Pins und unterschiedliche Writegarantien erhalten |
| F8 | D1–D3 | Genau eine vereinbarte Hinweisfläche im zuständigen UX2-Host |

## UX3-B — Wiederverwendbare Darstellung und gezielte Migration

### Ziel und Scope

Verständliche Hinweise aus bereits aufbereiteten Ownerfakten wiederverwendbar anzeigen.
Der gemeinsame Kern kennt Objektlabel, Kernaussage, Auswirkung, Ursachendetails,
Quellenverweis, Darstellungsrang und vorab geprüfte Folgeaktion. Featureadapter bleiben
beim fachlich zuständigen Consumer; sie treffen keine neue Verwendbarkeitsentscheidung.
Der bestehende `ErrorNotice` wird schrittweise und vorgangsbezogen behandelt.

### Kleine getrennte PR-Schnitte

| Schnitt | Konkrete Aufgabe | Abschlussgrenze |
| --- | --- | --- |
| B1 | Reine Präsentationsbausteine für kompakten Hinweis, Ursachendetails, Quelle, sichere Navigation und Status; genau ein lesender B1/F1-Pilot, Kandidat `RealizedGrossSources` | Gemeinsamen Vertrag zuerst konsolidieren; keine Datenbeschaffung oder Mutation im Baustein. Pilot und Anzeigeplatz mit UX-2/Performanceowner abgrenzen |
| B2 | Inventurbefund **Q12** in `ProductValuationPanel` und `PositionDetails`: falsche Ursachen in Auffangtexten korrigieren | Unbekannter Warningcode bedeutet nicht „veraltet“; MISSING/UNAVAILABLE/ERROR behauptet keinen vorhandenen Referenzkurs; LAST_AVAILABLE ist nicht pauschal STALE |
| B3 | **M02/M06** in `TradeAlertsPanel`: fehlgeschlagenen Health-Teilread, belegte Nichtanwendbarkeit und Alertinvalidierung richtig erklären | Historische Alerts erhalten; bei autoritativ geschlossener Position ist aktuelle Health nicht anwendbar. Fehler/404 allein beweist keine Schließung; INVALIDATED nach tatsächlichem Grund |
| B4 | `PlanPurchaseStatus`: fehlenden Kaufstatus und ungeklärte Trades präzise erklären | Fehlende Daten beweisen keinen veralteten Backendstand; UNKNOWN bleibt von NOT_STARTED getrennt; konkrete Trades lesend öffnen |
| Spätere Einzelschnitte | Jeweils einen vorhandenen Fehleradapter und dessen Operationskontext migrieren | Kein globaler Austausch aller Error-Komponenten, keine flächendeckende Formularkorrektur im selben PR |

B2 bis B4 sind gesonderte kleine Folge-PRs nach dem vereinbarten Komponentenvertrag.
Sie dürfen auch einen vorhandenen lokalen Anzeigeweg erhalten, wenn eine gemeinsame
Komponente für den konkreten Fall noch keine fachlich passende Schnittstelle bietet.
Die produktive Umsetzung eines Schnitts setzt die gemeinsame Schnittstellenfreigabe voraus.

### Abhängigkeiten

UX-1 liefert die nachgewiesene Eingabe-/Quellenableitung, UX-2 die Einbaufläche,
Hostfokus- und Lifecyclegrenze. Der Domain-Owner liefert die Qualitätsbedeutung;
UX-3 formuliert sie, UX-4 verwendet sie für Visualisierung und Legende. B2/B3 benötigen zusätzlich
die aktuellen Bewertungs-/Monitoringfelder; B4 den vorhandenen Kaufstatusprojektor.
Fehlen strukturierte Details, dokumentiert der Adapter die Begrenzung, statt neue
Domaincodes oder eine Ursache aus einem Freitext zu erzeugen.

### Akzeptanzkriterien

1. Jede wichtige Meldung beantwortet die fünf Fragen des Hinweisvertrags mit belegten Angaben.
2. Präsentationsbausteine führen beim Rendern, Aufklappen oder Aktivieren einer Quellennavigation keinen Fachcommand aus.
3. Loading, Erfolg, fehlgeschlagener Read, bestätigter Leerstand, fachlich UNKNOWN und belegte fehlende Berechtigung bleiben unterscheidbar. Kein Berechtigungsgrund aus HTTP 404, Netzwerkausfall oder bloßem Providerzugangsfehler ableiten.
4. Unbekannte Codes erhalten neutralen Vorgangsbezug; Code/UUID erscheinen nur sekundär und kopierbar.
5. B2 erhält `valuation_usable`, `analysis_usable` und getrennte G/V-Verwendbarkeit unverändert.
6. B3 zeigt einen echten Health-Lesefehler im offenen/ungeprüften Positionskontext auch bei leerer, erfolgreich geladener Alertliste. Bei autoritativ geschlossener Position ist die vom vorhandenen Health-Reader abgelehnte aktuelle Prüfung nicht anwendbar; historische Alerts bleiben sichtbar. Ein 404 allein beweist keine Schließung.
7. B3 unterscheidet vorhandene `invalidation_reason`-Werte; fehlender Grund bleibt ausdrücklich unbestimmt.
8. B4 nennt bei fehlenden Feldern nur den fehlenden Nachweis und einen bestehenden Leseschritt; kein unbelegtes Updategebot.
9. Keine automatischen neuen Reads pro Hinweis; vorhandene Owner-/mengenbasierte Identitätsabfragen bleiben zuständig.
10. Tastaturbedienung, Fokus und zugängliche Namen funktionieren; eine Ursache erzeugt keine doppelte Live-Ansage. Einen kleinen Pilot bei 390/1280 px prüfen; Text/Icon statt Farbe allein, kein abgeschnittener Blocker oder unerreichbare Aktion.
11. Sichtbare Farben und Begriffe versprechen keine positive Fachbewertung allein wegen eines gespeicherten Status.
12. Leere optionale Journaltexte oder eine historische Ansicht werden ohne Ownerbeleg nicht zum Blocker.

### Zielgerichtete bestehende Tests

| Schnitt | Bestehende Regressionseigentümer |
| --- | --- |
| B1 | `frontend/src/features/market/components/ApiFeedback.test.tsx` und Tests des konkret ausgewählten Piloten; neue gemeinsame Komponententests nur für zusätzliche Verhaltensverträge |
| B2 | `frontend/src/features/trade/components/ProductValuationPanel.test.tsx`, `ProductValuationPanel.currency.test.tsx`, `ProductValuationPanel.issuer-time.test.tsx`; `frontend/src/features/operational_workspace/pages/OpenPositionsPanel.test.tsx`, `OpenPositionsPanel.currency.test.tsx` |
| B3 | `frontend/src/features/alert/components/TradeAlertsPanel.test.tsx`; Ownerverträge `tests/unit/backend/features/position_monitoring/test_health.py`, `test_alert_projection.py`, `test_monitoring_application.py` |
| B4 | `frontend/src/features/trade_plan/components/PlanPurchaseStatus.test.tsx`; `tests/unit/backend/features/trade_plan/test_execution_overview.py`; `tests/e2e/trade-plan-purchase-status.spec.ts` |

Backendtests dienen als vorhandene Vertragsbelege; ihre bloße Existenz ist kein
neuer Laufnachweis. Bei einer reinen Textmigration nicht die Domainberechnung im
Frontendtest nachbauen. Die konkreten neuen Assertions prüfen falsche Ursache,
verlorenen Teilfehler oder irreführenden Status, jeweils am unveränderten Ownerergebnis.

### Nichtscope

Keine neue API, Migration, Auflösung historischer Währung, Kursfrischeberechnung,
Provideraktivierung oder Preisberechnung. Keine Planfreigabe, neue Formularpflicht
oder zentrale Ausführung von Schreibbefehlen. Keine vollständige Seitengestaltung.

## UX3-C — Kontextbezogene und sichere Folgeaktionen

### Ziel und Scope

Ein Hinweis führt zum tatsächlich betroffenen Objekt und gegebenenfalls zu seiner
konkreten Version. Die Aktion beschreibt ihre Wirkung vor dem Aufruf: lesen,
vorhandenen Editor öffnen, lokale Eingaben bewusst verwerfen oder einen vorhandenen
expliziten Command beim zuständigen Owner bedienen. Lokales Verwerfen ist kein
Serverwrite, bleibt aber eine ausdrückliche Entscheidung des Nutzers.

### Kleine getrennte PR-Schnitte

| Schnitt | Konkrete Aufgabe | Abschlussgrenze |
| --- | --- | --- |
| C1 | Vorhandene genaue Trade-, Plan-, Run-, Analyse-, Journal- und Lessonlinks sowie rungebundene Produktreparatur mit abgestimmten öffentlichen Helpern verwenden | Keine geratenen Objektbeziehungen; unterstützte Pins, Berichtsfilter und Rückwege erhalten |
| C2 | Fehlende Fokussierung auf eine Ausführung, einen Warrant ohne belegten Auswahlrun oder einen konkreten Diagnosevorfall separat vertraglich festlegen | Erst Consumer, Parameter, Identität und fehlendes Ziel klären; vorhandenen rungebundenen Reparaturweg nicht als fehlend ausgeben |
| C3 | Bestehende Reader-, Editor-, Versions- und Command-Owner aus dem Hinweis sicher erreichbar machen | Keine generischen Writes oder neue Retryengine; Berechtigung/Guard/Bestätigung bleiben beim Owner |

### Abhängigkeiten und konkrete Navigationsgrenzen

UX-2 bestimmt Zielhelper, Bereichsposition und Kontextschutz. UX-1 bestimmt, welche
Eingabe bereits belegt ist und welche explizite Bestätigung noch fehlt. UX-4 liefert
keine neue Aktion allein aus Farbe oder Diagrammzustand. Domain-Owner bestätigen
die tatsächliche Lesewirkung und vorhandene Commandvorbedingungen für C3.

Die HTTP-Methode ersetzt diese Prüfung nicht: Der vorhandene Monitoring-Health-GET
kann einen Provider lesen; POST `/risk/preview` ist eine nicht persistente Vorschau.
Risikoauswertung und Konfigurationsänderung mutieren dagegen. Tests fangen externe
Aufrufe ab und weisen die tatsächliche Ownerwirkung nach.

- Buchungen: Main hat `#execution-dates`, aber keine allgemeine `execution_id`-Fokussierung.
- Warrantquellen: `/warrants-admin` ist eine Übersicht. Der vorhandene `selectionRepairUrl(runId, warrantId)` öffnet dagegen `/warrants-admin?selection_run_id=…&warrant_id=…`; `WarrantAdminRoutePage` prüft Run, Mitgliedschaft und Basiswert. Ohne belegten Run gibt es keinen universellen Warrantfokus.
- Diagnose: `/workspace` ist kein objektgenauer Incidentlink; entsprechend beschriften.
- Exakte Reviewquelle: Tradequellenansicht mit `view=sources&review_version_id=…`.
- Exaktes Journal: `/post-trade?trade_id=…&journal_version_id=…`; nicht still zu latest wechseln.
- Lesson: `/lessons/{lessonId}?lesson_version_id=…#lesson-history`.
- Governance: kein eigenständiger Modell-/Aktivierungsroutevertrag; bekannte Lessonbindung verwenden oder Anleitung zeigen.

### Akzeptanzkriterien

1. Linkparameter stammen aus verifizierter Objektbeziehung, nicht aus Message-Text oder gleichartigen IDs.
2. Fehlende/fremde Pins bleiben sichtbare Fehler; keine andere Version wird automatisch eingesetzt.
3. Navigation und lesender Retry erzeugen keine Buchung, Freigabe, Evidence, Lesson oder Aktivierung.
4. Ein Editorlink lässt bestehende Entwürfe und Navigationguards intakt; ein Hinweis remountet keinen Owner allein zum Refresh.
5. „Status neu laden“ liest denselben Kontext. Ein Monitoring-Einmallauf ist kein solcher Read und wird nicht so angeboten.
6. Ein unbekannter Schreibausgang bleibt unklar, bis der vorhandene Owner die zulässige Klärung bestätigt.
7. Journalretry erhält Trade, Actor, Payload und Key; bloßer GET oder Verwerfen klärt Unknown nicht.
8. Lesson-Create, Approval, Validation und Aktivierung erhalten keine allgemeine idempotente Retrygarantie.
9. Nach bestätigtem Receipt und fehlendem Readback ausschließlich Lesen anbieten; Bestätigung bleibt sichtbar.
10. Der Hinweisbaustein verwirft oder bindet keinen Entwurf selbst um. Der bestehende Ownerkonfliktweg bleibt maßgeblich, auch wenn er einen Bestätigungsentwurf zurücksetzt oder bewusstes Abbrechen/Neuvorbereiten verlangt.
11. Ungültiger/fehlgeschlagener Runtime-Read bedeutet „nicht verifiziert“, nicht „keine aktive Version“.
12. Reload, Zurück/Vorwärts und kopierter Link erhalten den vereinbarten historischen Kontext.

### Zielgerichtete bestehende Tests

- `frontend/src/features/trade/components/TradeSourcesView.test.tsx` und `frontend/src/features/performance/pages/ClosedTradeSourceJourney.test.tsx`: genaue Quellen und Rückkontext.
- `frontend/src/features/trade/pages/TradeManagementPage.test.tsx`: vorhandene Buchungs-/Verkaufsanker und Kontextgrenzen.
- `frontend/src/features/product/pages/WarrantSelectionRepair.test.tsx`: vorhandene rungebundene Produktreparatur, keine Ersatzzuordnung.
- Nach Integration von UX2s neuer öffentlicher Grenze: `frontend/src/shared/trade-workspace-navigation/TradeWorkspaceNavigation.test.tsx`; dieser Pfad existiert am genannten Draft-Head, noch nicht auf Main.
- `frontend/src/features/learning/components/TradeJournalPanel.test.tsx`, `journalViewState.test.ts`: Pins, Guard, Konflikt, identischer Retry und Receipt/Readback.
- `frontend/src/features/learning/components/LessonDraftFromEvidence.test.tsx`, `LessonReviewPanel.test.tsx`: unterschiedliche Writegarantien, Quellenbindung und historische Auswahl.
- `frontend/src/features/model/components/RuntimeActivationPanel.journey.test.tsx`, `GovernanceCommands.journey.test.tsx`: explizite Befehle und bewusster Readback.
- `tests/e2e/post-trade-handoff-pin.spec.ts`, `post-trade-journal-ui.spec.ts`, `lesson-detail-consolidation.spec.ts`: echte Navigation/Reload/Entwurfsgrenzen.

### Nichtscope

Keine neuen Handelsaktionen, generischen POST-Callbacks, automatisch wiederholten
Commands oder veränderten Domainvorbedingungen. C2 autorisiert keine neue Route vor
Abstimmung und keine Datenbeschaffung aus einer nicht belegten Objektbeziehung.

## UX3-D — Priorisierung, Gruppierung und belastbare Recovery

### Ziel, Scope und Abhängigkeiten

Die vorhandene Aufmerksamkeit innerhalb einer vereinbarten Hinweisfläche verständlich
ordnen. UX-2 verantwortet die Platzierung; bestehende Workspaceprojektion und
Domainprioritäten bleiben maßgeblich. UX-1 liefert konkrete Quellenbeziehungen;
die Domain-Owner liefern Qualitätsbedeutung, UX-3 ihre Sprache und UX-4 die Visualisierung.
Fachliche Episoden/Recoverybelege
kommen ausschließlich aus dem zuständigen Owner, nicht aus lokaler Renderzeit.

| Schnitt | Konkrete Aufgabe | Abschlussgrenze |
| --- | --- | --- |
| D1 | Lokale Reihenfolge: belegter Vorgangsblocker, notwendige Entscheidung, fachliche Warnung/Datenqualität, Information | Kritische Alerts sichtbar erhalten; kein globaler „Trade gesund“-Score und keine neue Workspace-Aktionsprojektion |
| D2 | Nachgewiesene doppelte Währungshinweise und wiederholte Gründe unvollständiger Abschlussstatistiken konsolidieren | Ein Grund verständlich erklärt; betroffene Felder/Kennzahlen bleiben einzeln zugeordnet und unbekannte Werte bleiben unbekannt |
| D3 | Deduplikation nach Source, Objekt, Version, Operation und vorhandener Episode; Recovery exakt zuordnen | Keine persistierten ack/dismiss-Zustände, keine zeitbasierte Unterdrückung echter neuer Warnungen |

### Akzeptanzkriterien

1. Der Blocker nennt die tatsächlich gesperrte Operation; ein Teilreadfehler sperrt keine fachfremde Aktion.
2. Verkaufserfassung bleibt trotz fehlendem G/V oder Kurswarnung gemäß bestehenden Guards erreichbar.
3. Gleicher Text/Code allein dedupliziert nicht über verschiedene Objekte, Quellen oder Versionen.
4. SELL-Periodenbeiträge und vollständig abgeschlossene Trades bleiben unterschiedliche Berichtspopulationen.
5. Gruppenzahl und aufklappbare Objektliste erhalten jede tatsächliche Ursache und sichere Aktion.
6. Mehrfachrendern, Remount und neue Requestgeneration erzeugen keine wiederholten identischen Alarmansagen oder springende Reihenfolge. Ansagelebensdauer mit dem validierten Host-/Readkontext abstimmen.
7. Keine Warnung aus Leseausfall wird ohne aktuellen positiven Ownerbeleg als behoben dargestellt.
8. Ein anderer qualifizierter Kurs kann nach Ownerurteil die aktuelle Kursverwendbarkeit herstellen, behebt aber nicht die Störung der alten Providerquelle. Eine korrigierte wirksame Quelle kann neue aktuelle Ableitungen mit sichtbarer neuer Version/Berichtsgrundlage liefern; historische Pins bleiben exakt.
9. Alert, Zustellstörung, Providerfehler und letzter Referenzkurs bleiben getrennte Aussagen.
10. `RESOLVED`/`INVALIDATED` wird nach tatsächlich belegtem Grund erklärt; kein automatisches „Kurs erholt“.
11. Lesson-CURRENT, Quellenlinie CURRENT/SUPERSEDED und Review-CURRENT/STALE/UNKNOWN bleiben getrennt.
12. Lessonreview-RESOLVED/UNCHANGED_CONFIRMED repariert keine Quelle; Source-STALENESS ist kein Widerspruchsbeleg.
13. Ein Receipt und ein fehlgeschlagener Readback dürfen zusammen sichtbar sein; sie sind keine Textduplikate.
14. Eine belegte neue Episode oder relevante Ursache nach Recovery wird erneut sichtbar/zugänglich angekündigt.
15. `basis.id` validiert Inhalt und Vergleich, ist aber kein stabiler Schlüssel einer unveränderten Ursache. Fachlich fremde Änderungen der Gesamtbasis ersetzen aktuelle Werte/Belege vollständig, ohne allein neuen Alarm oder Recovery auszulösen.
16. Eine `EXCLUDED`-Zeile mit zusätzlichem `CURRENCY_UNKNOWN` erzeugt keine vom Owner nicht gelieferte Sperre der Summe. Gemeinsame BUY-Ursache nur aus belegten Quellbeziehungen, nicht allein aus `cost_basis_execution_ids`, ableiten; keine neue Resolverlogik.

### Zielgerichtete bestehende Tests und Nichtscope

`ExecutionCurrencySources.test.tsx` unter `frontend/src/features/trade/components`
sowie `ClosedTradesPage.test.tsx` und `PerformanceWorkspace.test.tsx` unter
`frontend/src/features/performance/pages` besitzen D2s Quellen-/Statistikfälle.
D1/D3 verwenden die bestehenden Alert-/Monitoringtests aus B3 sowie
`frontend/src/features/operational_workspace/pages/MarketDataRefreshPanel.diagnostics.test.tsx`.
Für getrennte Currentness gelten `EvidenceSourceStatus.test.tsx` und
`JournalEvidenceOrigin.test.tsx` unter `frontend/src/features/learning/components`.
Backend-Ownerbelege: `tests/unit/backend/features/position_monitoring/test_monitoring_application.py`
und `tests/unit/backend/features/learning/test_evidence_source_inspection.py`.
Keine neue Alertprojektion, Provider-Retryplanung, Finanzkohorte oder Eskalationsregel.

## Übergreifende Abnahmematrix

Die Fälle werden dem kleinsten tatsächlich betroffenen Folge-PR zugeordnet.
Sie verlangen keine vorgezogene Gesamtmigration oder Wiederholung fachfremder Tests.

| Fall | Schnitt | Eingabe / Aktion | Erwarteter Nachweis |
| --- | --- | --- | --- |
| A01 | B1 | Derselbe Hinweis zweimal gerendert/aufgeklappt | Keine Fachmutation, keine neue Quellenabfrage pro Instanz, eine passende Live-Ansage |
| A02 | B2 | Unbekannter `analysis_warning` | Neutraler Datenhinweis, sekundärer Code, keine erfundene Veraltung |
| A03 | B2 | MISSING/UNAVAILABLE/ERROR ohne nutzbaren Kurs | Kein behaupteter Referenzkurs; G/V und Marktwert getrennt nach Ownerflags |
| A04 | B3 | Health-Readfehler bei offener/ungeprüfter Position gegenüber autoritativ geschlossener Position | Echter Teilfehler sichtbar; bei belegtem Abschluss aktuelle Health nicht anwendbar. Kein CLOSED aus 404 ableiten; historische Alerts in beiden Fällen erhalten |
| A05 | B3/D3 | Unterschiedliche Gründe für INVALIDATED/RESOLVED | Grundtreue Darstellung; kein unbelegter Kurserholungs- oder Quittierungstext |
| A06 | B4 | Kaufstatusfelder fehlen oder Trade UNKNOWN | Ungeklärter Nachweis, kein NOT_STARTED und kein unbelegtes Backend-Updategebot |
| A07 | C1 | Historischer Journal-/Lesson-/Reviewpin, Reload und Back/Forward | Gleiche Version/Tradebindung und erlaubter Berichtsrückkontext; keine Writes |
| A08 | C1/C2 | Fremde/fehlende Version oder nur unbekannte Zielbeziehung | Fehler/Anleitung; kein latest-Fallback und kein erfundener Detailpfad |
| A09 | C3 | Dirty-Formular, lesende Hinweisnavigation | Vorhandener Guard; bewusste Auswahl; kein stiller Verlust/Remount |
| A10 | C3 | Journal-POST erhält Transportfehler oder strukturierte HTTP 503 | Unknown bleibt; expliziter Retry identisch mit Actor/Key/Payload; GET allein heilt nichts |
| A11 | C3 | Lesson-Create verliert Antwort | Kein generischer Schreib-Retry; Verweise lesend prüfen, Eingaben behalten |
| A12 | C3/D3 | Receipt bestätigt, exakter Readback fehlerhaft | Erfolg erhalten; ausschließlich Readback wiederholen; keine Duplikatunterdrückung dieser zwei Aussagen |
| A13 | C3 | Bestehender Journal-Draft, Reviewquelle STALE/unbereit | SAVE bleibt nach Ownervertrag möglich; keine globale Rebind-/Finalisierungsaufforderung |
| A14 | C3 | Runtime-Readfehler gegenüber bestätigtem `current=null` | „Nicht verifiziert“ getrennt von „keine aktive Version“; kein automatisches Aktivieren |
| A15 | B/D | Lesson CURRENT, Quelle SUPERSEDED, Review STALE | Drei Aussagen; unveränderte Bestätigung repariert keine Quelle |
| A16 | D1 | Kritischer Alert, fehlender G/V und tatsächlicher Verkauf | Alert sichtbar; Verkaufserfassung nach bestehenden Guards erreichbar |
| A17 | D2 | Vier Statistiken mit gleichem Grund, beziehungsweise doppelter Currencytext | Ein verständlicher Grund; jeder betroffene Wert bleibt fehlend, keine Nullersetzung |
| A18 | D3 | Gleicher Code in zwei Quellen/Versionen oder Berichtspopulationen | Getrennte Ursachen; nur passende Vorkommen konsolidiert |
| A19 | D3 | Recovery einer Quelle, andere Quelle weiterhin gestört; später neue belegte Episode | Keine falsche Gesamtrecovery; neuer relevanter Hinweis bleibt sichtbar |
| A20 | C3 | Candidate-Runtimestep COMPLETE, globales `can_evaluate=false` | Evaluation bleibt gesperrt; Teilstatus erzeugt keine Gesamtfreigabe |
| A21 | D3 | Unveränderte Ursache, spätere Lesezeit, Remount oder fachlich fremde Änderung der Reportbasis | Keine neue Alarmidentität; gesamter neuer gültiger Inhalt übernommen, keine alten Werte/Belege/Links gemischt |
| A22 | D2 | Gleicher Reason in zwei unabhängigen Ausführungen gegenüber belegter gemeinsamer BUY-Ursache | Keine falsche Ursachenzusammenführung; bei belegter Verbindung betroffene Beiträge erreichbar, Kohorten getrennt |
| A23 | B1/C1 | Noch unbekannte Objekt-ID, belegte Berechtigungslücke oder Run/Produkt widersprüchlich | Keine erfundene ID/Rolle/Route; genaue Operation beziehungsweise vorhandenen Fehler erklären |
| A24 | B1/D1 | Erstread oder Neustart ohne Vergleichshistorie | Nur aktueller Befund; kein unbelegtes „neu“, „verschlechtert“ oder „wiederhergestellt“ |

## Qualifikation und nächster Schritt

Jeder Folge-PR dokumentiert konkrete geänderte Komponenten, erhaltene Ownergrenzen,
die tatsächlich ausgeführten gezielten Tests und die unveränderten erforderlichen
Projektgates am geprüften Head. „Test vorhanden“ ist von „Test ausgeführt“ zu trennen.
HTTP-/Browsermocks ersetzen keinen PostgreSQL-Nachweis einer geänderten Fachmutation.
UX3-A führt keine Produktänderung und keinen dieser zukünftigen Testläufe aus.

Die Übergabe je Schnitt enthält Ziel/Nichtziele, Ausgangs-SHA, vollständige Dateiliste,
vorhandenen Code, Owner/Consumer, Abhängigkeiten, Tests, erlaubten Teilschnitt und
Abschlusskriterien. Vor Arbeit den konkreten Umfang im bestehenden Übergabebericht
mit Pfaden/Owner/Integrationsreihenfolge zuordnen; danach Branch, PR, Head und
Testmerge, tatsächlichen Diff, CI-Run-/Joblinks und offene Konflikte ergänzen.
Keine zusätzliche Lock- oder Aufgabenstatusliste einführen.

Bei tatsächlich berührten Hostflächen gemeinsam nachweisen: keine allein durch
Bereichsnavigation ausgelösten Trade-/Positions-/Timeline-Reads, A→B→A-Isolation,
Readback aktualisiert Preview/Historie nach Ownervertrag und erhält manuelle Entwürfe.
`ExecutionDatesPanel` behält seinen Timeline-Read. Ein grüner Einzel-PR oder sauberer
Textmerge ersetzt nicht diese Prüfung am vorgesehenen Integrationsstand. PR-CI,
Main-Integration, Tag, PC-Installation und menschliche Fachabnahme bleiben getrennt.

**Nächster Schritt:** #313/#314/#315 in genau einen gemeinsamen Hinweisvertrag
konsolidieren: kanonischer Einstieg, fünf Darstellungsarten/sieben Inhaltsfamilien,
stabile Identität vs. Snapshot, reine Link-API und Owneraktionen. Anhand A02, A10,
A12, A15 und A21 die Grenzen abnehmen, aktuelle UX1/2/4-Übergaben festhalten und
`RealizedGrossSources` als genau einen lesenden B1/F1-Piloten abgrenzen.
Erst nach dieser Schnittstellenfreigabe B1 als eigenen kleinen Draft-PR beginnen.

## Änderungshistorie

| Revision | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | Drei getrennte Folgeaufträge mit kleinen PR-Schnitten, Abhängigkeiten und 20 Abnahmefällen vorbereitet |
| 0.2 | 31.10.2026 | #313/#314 und neuer UX2-Draft-Head abgeglichen; eine gemeinsame Pilot-/Auftragsfolge, vollständige Übergaben, sichere Import-/Hostgrenzen und vier zusätzliche Abnahmefälle |
