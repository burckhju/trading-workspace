# Gemeinsame UX-Verträge

## Technischer Vertragsabgleich auf v1.5.46

Stand 11.11.2026, Main `d01c259f4b79fdfbdcec8743ececda035b69f9d1`.
Dieser Abschnitt aktualisiert Implementierungsbezüge; er ändert keine
Finanz-, Qualitäts-, Status- oder Freigaberegel der nachfolgenden Verträge.

- Öffentlicher BUY-only-`InitialPurchaseCurrencyPreview`, einmaliger
  `reportTimezoneError`, Hostreadback und die drei A→B→A-Regressionen bleiben
  implementiert. #331 ergänzt genau den belegten editierbaren Planwährungsvorschlag;
  der ursprüngliche Einzelrun-B-Schnitt bleibt eine andere Fähigkeit.
- Der kanonische #314-Vertrag einschließlich vier Typpräzisierungen ist erhalten.
  B1/F1 aus #320 ist inzwischen Produktbestand; der passive `shared/notices`-Pilot
  ist keine vollständige Implementierung sämtlicher Dokumentationstypen.
  Q12 in `ProductValuationPanel` und `PositionDetails` ist integriert.
- UX2-B liest die qualifizierte Position im Host und konsumiert die bestehende
  Bewertung. O1 erlaubt weiterhin keine ungeprüfte monetäre Darstellung roher
  Kostenbasis-/G/V-Felder. Navigation ist kein atomarer Finanzsnapshot.
- UX4-B/C/D und #340 verwenden qualifizierte Ownerwerte, getrennte Einheiten,
  Lücken und Tabellenalternativen. Der Watchlist-GET liest; die ausdrückliche
  Aktivierung bleibt ein bestehender Command. Anzeige allein ist keine Freigabe.
- Die sechs Gruppen in `TradeSourcesView` sind getrennte Belege mit eigenen
  Readgrenzen; sie begründen weder globale Lifecyclevollständigkeit noch
  vollständiges UX2-D.

Für die nächsten schmalen Schnitte sind bestehende Grenzen zu konkretisieren,
nicht fehlende Fachregeln in der UI zu erfinden:

| Schnitt | Vor Umsetzung zu belegende Grenze | Owner / Consumer |
|---|---|---|
| Historischer Analyse-/Kandidatenrückweg | Exakter Quellentyp, ID/Version, erlaubte Rückparameter und Dirty-/Busy-Verhalten. Vorhandenes `ANALYSIS` ist kein Freibrief für fremde Quellentypen oder Latest. | UX2: öffentlicher URLvertrag; Analysis/Candidate: jeweilige Identitäts-/Versionsprüfung; UX4: Quellenconsumer. |
| Historischer Auswahlrun | Bereits gespeicherte Selection exakt zum workspacegebundenen Run auflösen; kein Ersatz durch latest und keine neue persistierte Relation. | TradePosition: Source-Read; ProductSelection: Auswahl-/Runidentität; UX2: Navigation. |
| M06 und M02 | Gelieferte Invalidierungsursache erhalten; Healthfehler separat sichtbar. Geschlossen/nicht anwendbar nur aus autoritativem Positionskontext, nicht aus 404/leer. | UX3: Erklärung; PositionMonitoring: Health; Alert: persistierte Alert-/Invalidierungssemantik; Notification: Delivery; UX2: Hostkontext. |
| B4/TP06 | Fehlende optionale Executiondetails ohne unbelegte Updatepflicht erklären; UNKNOWN und NOT_STARTED bleiben verschieden. | UX3: Text; TradePlan/TradePosition: Kaufstatus; UX2: vorhandene Ziele. |
| Neue Positionscoveragefläche | Echte bestehende Payload, additive öffentliche Readtypgrenze, Slot/Readowner/Invalidierung und getrennte Populationen. | Market Data: Readvertrag; UX2: Host; UX4: Renderer; UX3: Qualitätssprache. |

Konkrete Test- und Abschlussgrenzen stehen in
[Masterplan](UX_MASTER_PLAN.md#soll-ist-abgleich-und-umsetzungsfolge-vom-11112026)
und [Integrationsfolge](UX_DEPENDENCIES.md#umsetzungsfolge-ab-v1546).
Die historischen Einordnungen zu noch offenen B1- und UX4-B/C/D-Entwürfen weiter unten
beschreiben den 01.11.2026; sie verteilen keine bereits integrierte Arbeit neu.

Basis und Zuständigkeiten: [Masterplan](UX_MASTER_PLAN.md), [Ownership](UX_OWNERSHIP.md). Diese Regeln präzisieren die Zusammenarbeit auf bestehenden Fachverträgen. Sie führen weder ein neues persistiertes Modell noch eine zusätzliche API oder Finanzberechnung ein.

**Historischer technischer Nachtrag vom 01.11.2026 nach `v1.5.37`:** Die folgenden Owner- und Schutzgrenzen bleiben erhalten. Ihre UX1/UX2-Umsetzung ist über #318 im veröffentlichten Produktmerge `bb49ffe781933270746b9f86f4aee99b6f8144c2` und unverändert im aktuellen Dokumentmain `484143d33aa5f2d443da6b2edf097ae1cb5aee3a` belegt; die UX3-K-Präzisierungen sind mit #314 integriert. Historische Lücken und Übernahmeaufträge werden unten als solche gekennzeichnet. [Getrennte Implementierungs-/CI-/Main-/Tagbelege](UX_INTEGRATION_STATUS.md#technischer-snapshot-nach-v1537).

## Kontext, Navigation und gemeinsame Importgrenze — Owner UX-2

- `trade_id`, Positions-/Produktidentität, historische Plan-/Review-/Journal-/Lessonversion und Berichts-Rückkontext bleiben explizit gebunden. URL-Parameter sind Navigation, keine fachliche Evidenz.
- Erlaubte historische Pins und Parameter unverändert transportieren. Doppelte/ungültige Werte nicht still zu einer gültigen aktuellen Auswahl normalisieren; bestehende Validatoren entscheiden.
- Bereichswechsel innerhalb desselben Trades erhalten Formulardrafts und erzeugen keine allein navigationsbedingten Trade-/Positions-/Timeline-Reads.
- Echter Identitätswechsel verwendet bestehende Dirty-/Busy-Guards und Generation-/Abortschutz. Alte Antworten dürfen auch bei A→B→A keinen fremden Kontext anzeigen.
- Quellenansicht, Journal und Performance sind getrennte Owner-Reads. Ein gemeinsamer Bildschirm darf sie nicht als einen atomar gelesenen Finanzsnapshot ausgeben.

Die [Frontendarchitektur](../architecture/FRONTEND_ARCHITECTURE.md) untersagt direkte Imports interner Komponenten/Services eines anderen Features. **#311 am Head `55072f8e90c00d309c3bd6ed6dd17f61ab33bd32` hat die früher beanstandeten Navigationsimporte bereits über `frontend/src/shared/trade-workspace-navigation/` aufgelöst.** Kontext, Linkbau und reine Closed-/Realized-Report-URL-Verträge liegen dort; bestehende Featureexports bleiben kompatibel. Diese Umsetzung erhalten und nicht erneut entwickeln. Die davon unabhängige Previewgrenze aus `product_selection` ist inzwischen durch den unten belegten öffentlichen BUY-Adapter umgesetzt und mit #318 qualifiziert.

Kein Import aus dem gemeinsamen Modul zurück in interne `trade/services/sourceView`- oder `performance/services/closedReportContext`-Implementierungen. Gemeinsame URL-Schlüssel/Transportfunktionen genau einmal ausgliedern oder bereits qualifizierte Ownerlinks über typisierte Props übergeben. `verifyClosedReport`, `verifyClosedStatistics`, Quellenvalidierung und Finanzlogik verbleiben beim Fachowner. Ein bloßes Reexport-Barrel belegt die Architekturkonformität nicht. Eine bewusst abweichende neue Abhängigkeitsrichtung benötigt eine konkrete ADR-/Featurevertragsentscheidung.

### Exakter Integrationsvertrag UX1/UX2

1. **Performancekontext:** Der vorhandene UX1-Helper `reportTimezoneError` ist einmalig in `shared/trade-workspace-navigation/realizedReportNavigation.ts` implementiert und über die gemeinsame Grenze exportiert; UX-2 bleibt Integrator. `reportFiltersErrors` ruft denselben Helper auf. `initialPerformanceFilters` bleibt im Performance-Feature und nutzt ihn für den editierbaren Browserzonenvorschlag; gültige explizite URL-Auswahl hat Vorrang. Bisherige Featureexporte bleiben erhalten. Kein zweiter Parser und kein Shared-Import zurück in das Feature. Gültigkeitsprüfung, bestehender Fallback und Fehlertexte werden semantisch unverändert übernommen.
2. **Host:** UX-2 erhält Navigation, Anker, `tradeLookupQuery`, Plan-/Review-/Journal-/Lessonpins und beide typgerechten Berichtsrückwege aus #311. UX-1s `ExecutionCurrencyPreview` ersetzt ausschließlich die bisherige Währungseingabedarstellung; manuelle Override-/Bestätigungszustände bleiben kontrollierte Formwerte. `historyReloadToken` erreicht SELL-Preview, Nachkauf-Preview und vorhandene Kurshistorie. Kein vollständiges Ersetzen der Hostdatei durch eine Branchfassung.
3. **Lebensdauer:** Ein reiner Hashwechsel behält alle Formulare gemountet und erzeugt keine neuen Trade-, Positions-, Timeline- oder Previewreads. Pfad-/Suchparameter-/Tradewechsel behalten Dirty-/Busy-Schutz. Bestätigtes Verwerfen bleibt bewusst; ein Reload ist keine persistente Entwurfssicherung.
4. **Antwortbindung:** Previewread bleibt an den vollständigen vorhandenen Eingabe-/Quellkontext und Reloadtoken gebunden, nicht an den URL-Hash. Generation/Abort und A→B→A-Schutz gelten auch bei verspätetem Erfolg oder Fehler und nach Unmount. Eine Antwort darf weder fremde Herkunft anzeigen noch Menge, Preis, Notiz oder manuelle Währung überschreiben. Nach erfolgreichem Readback wird die Herkunft neu gelesen; Capture validiert beim Schreiben erneut.
5. **Quellen und Berichte:** Derselbe Trade darf mehrere unabhängige Quellen-/Reportreads besitzen; gemeinsame Ansicht ist kein atomarer Finanzsnapshot. SELL- und Abschlussrückwege behalten ihre verschiedenen Filter-/Basis-/Seitengrenzen. Fremde Pins bei echtem Tradewechsel entfernen, Rückkontext einschließlich ungültiger Duplikate erhalten; ungültige Parameter nicht still gültig machen.
6. **Prüfung:** Beide gemeinsamen Performance-Testdateien erhalten UX1-Zeitzonenfälle und UX2-Rücklinkassertionen. Die [gemeinsame Regressionsmatrix](UX_DEPENDENCIES.md#gemeinsame-regressionen) gilt für den tatsächlich kombinierten Commit. Einzel-PR-CI ersetzt ihn nicht. Gemeinsame Quelländerungen führt der benannte UX-Lead aus; MASTER ändert nur diese Koordinationsdokumente.

Der gemeinsame Vertrag ist im geprüften Main tatsächlich umgesetzt: [Helperdefinition und gemeinsame Filterprüfung](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/shared/trade-workspace-navigation/realizedReportNavigation.ts), [öffentlicher Export](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/shared/trade-workspace-navigation/index.ts), [Performance-Consumer](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/features/performance/services/performanceReportContext.ts) und [Host mit Navigation/Preview/Reload](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/features/trade/pages/TradeManagementPage.tsx). Der [Reviewfix `86472f3…`](https://github.com/burckhju/trading-workspace/commit/86472f3571c127f6234b89ede08ac18fbd3adb48) invalidiert auch bereits abgeschlossene alte A-Erfolge und A-Fehler beim zwischenzeitlichen Eingabetupelwechsel. Die drei Regressionen erhalten zusätzlich den bewusst geöffneten leeren Override. Dies belegt die bestehende Antwortbindung; es führt keine neue Fachregel ein.

### Öffentliche Grenze für die Erstkaufvorschau

Der enge öffentliche Trade-UI-Adapter ist mit #318 integriert: [`frontend/src/features/trade/public/InitialPurchaseCurrencyPreview.tsx`](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/features/trade/public/InitialPurchaseCurrencyPreview.tsx). Nur Adapter und Props werden über [`frontend/src/features/trade/index.ts`](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/features/trade/index.ts) exportiert; `ProductSelectionPage.tsx` importiert aus `../../trade`. Die Umsetzung ist keine pauschale Freigabe interner Crossimports.

Der Adapter erhält `productId: string`, `date: string`, `time: string`, den vorhandenen kontrollierten Währungsentwurf `value`/`onChange` mit `code` und `note` sowie optional `disabled`. Er setzt intern fest `context={{ productId, side: 'BUY' }}` und delegiert an die vorhandene `ExecutionCurrencyPreview`. Keine frei wählbare Side, kein `tradeId`, kein Preis-/Mengenwert, kein Read-/Writecallback, keine neu kopierte Resolution oder Finanzenum in diesem öffentlichen Vertrag. Produktauswahl übergibt die bestehende `selectedEvaluation.warrant_id`, Kaufdatum/-zeit, Währungsentwurf und Busy-Zustand; Trade besitzt den Previewread einschließlich Abort, Retry und Provenienz. Produktauswahl behält Entwurf und ausdrückliches Capture.

Diese konkrete begrenzte Adapterentscheidung ist im bestehenden [Capture-/Qualifikationsvertrag](../implementation/UX1_INPUT_REUSE_QUALIFICATION.md) dokumentiert. Die [öffentlichen Adaptertests](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/frontend/src/features/trade/public/InitialPurchaseCurrencyPreview.test.tsx) und die gemeinsame #318-Qualifikation belegen den begrenzten technischen Schnitt; TradePosition-/ProductSelection-Ownership bleibt erhalten. Sie ersetzt weder den Domainreview der additiven Preview-GETs noch die Architekturregeln für andere Importe. Ein Barrel des gesamten internen Previewbausteins wäre keine Umsetzung dieser Grenze. Die öffentliche API muss BUY-only, keine Draftänderung durch Reads, Produktwechsel/stale Antworten, Readfehler und unveränderten bewussten Erstkauf ohne automatische `currency_confirmation` nachweisen.

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

### Kanonischer UX3-Hinweisvertrag — Masterentscheidung Phase 1

**Der kanonische UX3-K-Vertrag aus #314 ist integriert.** Finaler Head `cc547ef662d1bc28315d25df1930c32b94278d6b`, Merge `d80bd45d84d845aa920a7eac5b19a7fe6cd63307`; im geprüften Main enthalten sind genau ein [Einstieg](../ui/ux-3/README.md), [Hinweisvertrag](../ui/ux-3/notice-contract.md) und [Dokumentationstypmodell](../ui/ux-3/contracts.ts). Die Pflichtübernahmen aus #315 sind im kanonischen Vertrag nachvollziehbar. #315 `d9d85f1af3159c4356c8773d076decbf1dc604e4` bleibt offene Draft-Quelle; sein `docs/ui/ux3-notice-contract.md` wird nicht als zweiter normativer Vertrag integriert und der PR nicht geschlossen.

**Historischer Implementierungsbezug vom 01.11.2026:** Die frühere Aussage, vor der Konsolidierung sei keiner der Entwürfe integrationsfähig, gehört zum Snapshot vom 01.11.2026, 15:28 Uhr. Sie ist mit dem belegten #314-Abschluss historisch. Der separate B1/F1-Produktentwurf #320 ist noch kein Mainbestand und erhält seine eigene Prüfung. Sein aktueller Head `71e971a67be7f1ca10192e04e3832f843b8099bd` lässt den kanonischen Dokumentvertrag unverändert; der engere passive Pilot-View ist kein neuer globaler Fachvertrag.

Historische Herleitung: Schon #315 Revision 0.2 ordnete sieben fachliche Inventurfamilien den fünf Darstellungsarten zu und beschränkte die gemeinsame Action-API auf Navigation. Kanonisierung, eindeutige Typbindung und Übernahme der zusätzlichen Fach-/Recoveryfälle sind inzwischen im integrierten #314 umgesetzt. Die nachfolgende Vertragstabelle bleibt die gemeinsame Grenze.

| Gegenstand | Einziger gemeinsamer Vertrag |
|---|---|
| Arten | `information`, `warning`, `blocker`, `error`, `success` aus #314. Die sieben Familien aus #315 bleiben Inventurtaxonomie, keine zweite Enum. Blocker und Erfolg brauchen Operation und Ownerbeleg. Ein Fehler beweist ohne Ownerklassifikation keine endgültige Ablehnung eines Writes. |
| Feldnamen | `catalogRule`, `subject/context`, `evidence/authority`, `cause/impact`, `automatic`, `userNeed`, `lifecycle`, `time/details/actions`. #315s `presentationKey`, `origin`, `systemHandling`, `userStep`, `grouping` werden darauf abgebildet; keine parallelen Exporttypen. |
| Nutzerbedarf | `none`, `optional-inspection`, `required-for-operation`; Pflicht nur für die konkret gewünschte, vom Owner belegte Operation. Information und Erfolg begründen für sich keine Pflichtentscheidung; `information` mit `required-for-operation` ist unzulässig. Eine Datenlücke blockiert keine fachfremde Buchung. |
| Fachliche Autorität | Originalcodes, Finanzwerte, Qualität, Zulässigkeit, Quellen, Versionen, Retry und Recovery bleiben beim jeweiligen Domain-/Reader-/Commandowner. Keine persistierte `acknowledged`-/`dismissed`-/`resolved`-Wahrheit und kein globaler „Trade gesund“-Status. |
| Ursache | Stabile Identität aus Owner, Regel/Originalreason, echter Objekt-/Quellidentität, Operation/Aussagebereich und ursächlich relevanter Version/Episode. Berichtsart und fachlicher Filterkontext einschließlich Währung/Zone bleiben getrennt. Kein Schlüssel aus Text, Pollzeit, Rendercount, Requestgeneration oder allein globaler `basis.id`. |
| Gültiges Vorkommen | Werte, Belege, Fehler und Aktionen sind strikt an Kontext, Pins, Generation und validierte Reportbasis gebunden. Basiswechsel ersetzt den gültigen Inhalt; er erzeugt allein weder neue Ursache noch Recovery. Alte Antworten auch bei A→B→A vollständig verwerfen. Die in der Konsolidierung präzisierte T04-Grenze bleibt: Generation gehört zur Gültigkeit, nicht zur stabilen Ursache. |
| Aktionen | `NoticeAction` bleibt `read` oder `open-decision`; beide navigieren ausschließlich zu einem belegten bestehenden Ziel. Readbuttons bleiben beim benannten Reader, Verwerfen beim Dirty-Guard, Commands beim Fachformular. `#execution-dates` belegt den Buchungsbereich, keine individuelle Executionfokussierung. Kein erfundener Objekt-/Governancepfad oder Produktreparaturlink ohne Run-/Warrantbezug. |
| Writes und Readback | Explizite Ablehnung, unbekannter Writeausgang, bestätigter Receipt und danach fehlgeschlagener Readback bleiben unterschiedliche Ownerfakten. Ein GET oder Verwerfen beendet Journal-Unknown nicht. Für Journal darf ausschließlich dessen vorhandener Retry nach bewusstem Klick den eingefrorenen Trade/Actor/Payload/Idempotency-Key wiederverwenden; keine allgemeine Retrygarantie für Lesson-Create, Governancevalidation, Approval oder Aktivierung. |
| Recovery | Positiver aktueller Ownernachweis desselben Aussagebereichs und Quellen-/Listing-/Episodenbezugs erforderlich. Ein alternativer qualifizierter Kurs heilt keine andere Providerquelle. `qualified_success` belegt ohne passendes `provider_reachable=true` keinen Netzkontakt. Alert-`RESOLVED`, Regel-EXITED, Storno, Vollabschluss, Zustellung und Lessonreview bleiben getrennte Aussagen; kein rückwirkendes Heilen historischer Pins. |
| Priorität | Innerhalb der Hinweisfläche: belegte Operationsblockade, notwendige Entscheidung, relevantes Problem, Datenqualitätsinformation, reguläre Information/bestätigter Erfolg. Bestehende Domainpriorität und kritische Alerts erhalten. Bei Gleichrangigkeit Aufgabenbezug, belegte neue/verschlechterte Auswirkung, stabile Ownerreihenfolge und Hinweisidentität. Keine Änderung der Workspace-Projektion `ACTION/REVIEW/BLOCKED`. |
| Live-Ansage | Genau ein Host verantwortet die Ansage; unveränderte Polls und Remounts bleiben stumm. Summary/Detail kündigen nicht doppelt an. Ohne Vergleich nur aktuellen Befund zeigen; echte neue Ownerepisode nicht durch pauschales Zeitfenster unterdrücken. |
| Pilot | Genau ein lesender B1/F1-Pilot in `RealizedGrossSources`, auf bereits gelieferten gespeicherten Fakten. Karte, Details und bestehender Buchungslink; kein neuer Read, kein globaler Austausch von `ExecutionCurrencySources`, keine Preview als gespeicherter Ausführungsbeleg. |

**Gruppierung ist keine Finanzberechnung.** `cost_basis_execution_ids` enthält laut bestehendem Performanceowner auch frühere SELLs im vorausgehenden Executionprefix. Daraus keine gemeinsame BUY-Ursache ableiten. Nur tatsächliche Quellen mit `side`, `is_effective`, Resolver- und Confirmation-/Evidencebezug können sie belegen; andernfalls rein optisch gruppieren. Ebenso kann eine `EXCLUDED`-Zeile `CURRENCY_UNKNOWN` tragen: Der Reason allein blockiert nicht zusätzlich die gewählte Berichtssumme. Report-/Itemstatus und vorhandene monetäre Qualifikation sind maßgeblich. Die im kanonischen TC-01 präzisierte Grenze verlangt den konkreten Ownerbeleg für einen nicht berechenbaren G/V; eine beliebige fehlende Executionwährung genügt nicht.

#### Vier verpflichtende Typpräzisierungen in #314

**Im kanonischen Dokumentvertrag umgesetzt und integriert.** Die damaligen Lücken werden zur Rückverfolgbarkeit erhalten; sie sind keine noch offenen Integrationsaufträge. Belege: [contracts.ts](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/docs/ui/ux-3/contracts.ts) und [contracts.type-test.ts](https://github.com/burckhju/trading-workspace/blob/bb49ffe781933270746b9f86f4aee99b6f8144c2/docs/ui/ux-3/contracts.type-test.ts) mit 42 erwarteten negativen Typfällen. Diese Zahl bezeichnet vorhandene Testfälle, keinen in diesem Dokumentlauf neu ausgeführten Typcheck.

| Historische Lücke | In #314 umgesetzte Präzisierung | Erhaltene Gegenfälle |
|---|---|---|
| `SubjectRef.id` ist immer Pflicht | `KnownSubjectRef` und `OperationSubjectRef` unterscheiden echte Objektidentität vom Vorgangs-/Elternkontext ohne erfundene neue ID. `ExistingDestination.subject` verlangt weiterhin `KnownSubjectRef`. | Vor Create, unklarer Create-Response, bekanntes Elternobjekt; unbekannte neue ID darf kein Objektziel werden. |
| `ApiFailureNotice = Notice<ApiErrorResponse>` reicht für den Writeausgang nicht | `ApiFailureNotice` bindet `read-failed`, `write-rejected`, `write-unknown` und `receipt-confirmed-readback-failed` an Owner-/Operations-/Receiptbelege; kein generischer Retry. Originalfehler bleibt Evidenz, keine neue globale Outcome-/Recoveryengine. | Strukturierte Journal-503 bleibt unknown; bestätigter Receipt plus Readfehler; Lesson-Create ohne generischen Retry; explizite Ablehnung. |
| `GovernanceEvidence.approval/activation` ist nur nullable | Eigene `GovernanceRead`-Zustände `not-read/loading/ready/error` mit Modell-/Versions-/Generations-/Zeitbezug; nur `ready` darf bestätigtes `null` tragen. | Approval vorhanden plus Runtime-Readfehler, bestätigt `current=null`, fremdes Modell. Gemeinsamer UI-Token beweist keinen atomaren Snapshot. |
| Perioden-/Abschlussbeispiele sind nicht ausdrücklich an ihre Population gebunden | Diskriminierte `realized-gross`-/`closed-trades`-Kontexte binden Report, Item und Statistik an Population, `BasisId`, Definition und jeweilige Ownervalidatorbelege. | Falsche Population, Item-/Statistikbasis und Kontext abweisen. Heute gemeinsam geerbte Filter-/Basisfelder sind strukturell kompatibel; kein aktueller Finanzfehler wird behauptet. |

Die integrierten positiven und negativen Typfälle erhalten. TypeScript ersetzt weder Runtimevalidierung noch einen Quellen-/Generations-/Linkbeleg. Dokumentationstypen bleiben außerhalb des Produktimportgraphen, bis der einzelne Implementierungsschnitt freigegeben ist.

#### Verpflichtende Übernahmen aus #315

Die folgende Herkunftsmatrix beschreibt die mit #314 konsolidierten Vertrags-/Abnahmeplaninhalte. Die [kanonische Übernahmedokumentation](../ui/ux-3/README.md) erhält die Quellenzuordnung; geplante Produktabnahmefälle werden dadurch nicht zu bestandenen Produkttests.

| Quelle des Mehrwerts | Übernahme in den kanonischen Vertrag / Abnahmeplan |
|---|---|
| Vertrag §§2–3, 6.3; T04–T07, C06–C08, JL03–JL06/JL10, MG08–MG10 | Ownerklassifizierter Writeausgang, Receipt/Readback, Vor-Create-Identität und getrennte Governance-Reads; oben genannte Typfälle. |
| §7.2, P02–P08 | Ursachennachweis statt Executionprefix, EXCLUDED plus Reason, verschiedene Populationen, Basiswechsel/Remount ohne neue Ursache oder Doppelansage. |
| §8, M06–M07, JL07–JL13 | Scopegenaue Recovery; Alertabschluss/Invalidierung/Regel-EXITED/Storno/Delivery; Interpretations-, Quellen- und Reviewcurrentness getrennt. |
| Q12 / B2 | Unbekannter `analysis_warning` ist nicht automatisch stale; MISSING/UNAVAILABLE/ERROR belegt keinen Referenzkurs; LAST_AVAILABLE ist nicht pauschal STALE. Textkorrektur erfindet keine neue Geldqualifikation. |
| M02/M06 / B3 | Echte Health-Teilfehler sichtbar machen; bei nachgewiesen geschlossener Position Health nicht anwendbar. 404 alleine beweist keinen Vollabschluss. Historische Alerts und `invalidation_reason` erhalten. |
| TP05–TP07 / B4 | Kaufstatus bleibt von Planfreigabe getrennt; UNKNOWN ist nicht NOT_STARTED. Fehlendes optionales Executionfeld belegt kein notwendiges Backend-/PC-Update; Journalhistorie bleibt geschützt. |
| M01/M04–M11, MG01–MG11 | Wirkung von Healthreads, Risiko-/IV-/Attentiongrenzen, nichtpersistente POST-Vorschau versus Commands, `can_evaluate` als Gesamtguard, CONTRADICTS trotz technischer Validation, Approval ungleich Runtime und belegte Ziele. |
| Quellen-/Testregister, A01–A24 und B/C/D-Aufträge | Eine Inventur-/Abnahmematrix mit Herkunfts-IDs und EIN F1–F8-Rollout. B1/F1 ist derselbe Pilot. B2/B3/B4-Mehrwert ausdrücklich erhalten; keine zwei Gesamtmigrationen oder neue FT-/PB-IDs. |
| Backlog-/Workspace-Verweise | Nur kanonische Verweise und korrekte technische Nachweisgrenzen übernehmen. `PRODUCT_BACKLOG` bleibt einzige fachliche Statusquelle; keine Produkt-/Fachabnahme aus Dokumentation ableiten. |

Die 80 Inventurzeilen und 48 geplanten Fälle aus #314 sowie 79 Inventurzeilen und 24 Fälle aus #315 sind unterschiedliche Zuschnitte, keine addierbare Zahl unabhängiger Ursachen oder fertiger Tests. #314s genaue Produktauswahl-/Candidate-, Fokus-/Live-Region-/Zoom- und Negativtypfälle bleiben erhalten. Die integrierte Übernahmematrix ordnet diese Quellen dem einen Katalog zu; die zusätzlichen Fälle A02/A04/A06/A10–A12/A14–A15/A18/A20–A24 aus #315 bleiben als spätere Produktnachweise nachvollziehbar.

## Diagramme, Kennzahlen und Datenlücken — Owner UX-4

- Vorhandene Backendantworten verwenden. PnL, Risiko, Trefferquote, Profit-Faktor, Normalisierung und Währungsqualifikation nicht im Frontend nachrechnen.
- Einheiten, Währung, Zeitraum, Quelle, Datenstand und vorhandene Definitions-/Berichtsgrundlagen sichtbar machen; genaue Geldwerte in der Evidenz erhalten. Numerische Plotkoordinaten sind keine neue Finanzquelle.
- Positionsverlauf trennt Währung, Preisart und Quelle; einzelne Kursbeobachtungen bleiben Punkte ohne suggerierte Verbindung. Marktcharts erhalten die qualifizierten Lücken und Vergleichsgrenzen.
- Datumgenaue Executions oder unbekannte Währungen bleiben in der Ereignis-/Evidenzliste mit Grund sichtbar. Präzise Marker benötigen vorhandene serverseitige Qualifikation.
- Leere Antwort, technischer Fehler, fehlende Berechtigung und gekürzte Daten getrennt anzeigen. Unvollständige Kennzahl nie als Null; Statistik bezieht sich auf die qualifizierte Gesamtkohorte, nicht auf die sichtbare Tabellenseite.
- Anzeige startet keinen Backfill, Providerabruf oder neue Kursspeicherung. Vorhandene Lazy-Load-, Retry- und stale-response-Grenzen erhalten.
- Eine zugängliche Tabelle oder gleichwertige Textansicht bleibt verfügbar, auch bei nicht ladbarem Diagrammmodul. Responsive Hauptansicht und aufklappbare Herkunft gemeinsam prüfen.

Referenzen: [Positionskursverlauf](../ui/position-price-history.md), [Monitoring-Datenqualität](../monitoring-data-quality.md), [Ausführungswährung](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md), [Abschlusskohorte](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md).

### Kompatibilität von UX4-A / #316

**Historischer Implementierungsbezug vom 01.11.2026; die folgenden Schutzgrenzen gelten fort:** Der vollständige [Visualisierungsvertrag](../ui/ux4-visualization-contract.md) und die sechs UX4-A-Dokumente sind mit #316, finalem Head `82b11711a70aacf39fddf59a6545662fb7102b92` und Merge `5f2e12667759bfb54eb14f39c6d8426c9cd8080f`, im geprüften Main integriert. UX4-B/C/D bleiben getrennte Produktaufträge; der Dokumentabschluss belegt keine Umsetzung dieser Oberflächen. Historische #314/#315-Referenzen berechtigen nicht zu einem zweiten Hinweis-API-Modell.

- `realized-gross-sell-v2`: wirksame SELL-Beiträge im Zeitraum, einschließlich Teilverkäufen offener Trades. `closed-trade-gross-v1`: je qualifiziertem Vollabschluss das vollständige Lifetime-Ergebnis. Marktwert und unrealisierter G/V bilden weitere getrennte Aussagen. Keine populationsübergreifende Summe, Finanzkurve, Deduplikation oder neue Formel. Statistiknenner bleibt die vollständige qualifizierte Kohorte.
- `PositionPriceHistory`/`PositionPricePlot`/`PositionPriceHistoryEvidence` und `TimeSeriesChart` wiederverwenden. Einzelbeobachtungen bleiben Scatter; keine synthetische Linie, Glättung, interpolierten Kurse, erfundenen DATE_ONLY-Zeitpunkte oder unbelegte FX-Umrechnung. Bestehende EOD-Verbindung realer Punkte erhält ihre Lückengrenzen.
- #311 hat den vorhandenen Slot `#position-price-history` mit `tradeId`, `positionId`, `reloadToken={historyReloadToken}` bereits eingebunden. UX-2 bleibt Integrator, `ExecutionDatesPanel` behält Timeline/Recovery, UX-4 konsumiert Hostinvalidierung. Hash/Fokus ist kein neuer Leseschlüssel; nur qualifizierter erfolgreicher Readback erhöht den Historientoken.
- Währung, Provider-/Listingidentität, Preisart, Originalzeit und `plottable`-Qualifikation bleiben ownergebunden. Fehlend, exakt 0, EMPTY, PARTIAL, Fehler, nicht berechenbar und gekürzt bleiben sichtbar und verschieden. Zugängliche Evidenztabelle bleibt auch bei Diagrammfehler verfügbar.
- UX-3 liefert die eine Qualitätssprache; Domainowner liefern ihre fachliche Bedeutung. Ein bestehender Health-GET kann Providerzugriff enthalten. Rendering, Diagrammöffnung und reine Navigation dürfen deshalb keinen zusätzlichen solchen Aufruf auslösen; ein benannter Retry folgt dem nachgewiesenen bestehenden Readervertrag.

## Vertragsänderung und Prüfung

Ein neues Feld oder veränderte Bedeutung erhält vor Integration: genauen Domain-Owner, Producer/Consumer, Kompatibilitätsentscheidung, fehlende/veraltete/ungültige Fälle, historische Referenzen und betroffene Contract-/Integrationstests. Gemeinsame API-/Domainänderungen werden nicht gleichzeitig in mehreren unabhängigen PRs entwickelt.

UX-3 formuliert die Darstellung von Datenqualität; die fachliche Entscheidung über Qualität bleibt bei jedem bestehenden Owner. UX-2 koordiniert Readback/Hostinvalidierung; UX-1 und UX-4 prüfen ihre jeweiligen Reaktionen darauf. Diese Trennung ist bei jeder gemeinsamen Regression nachzuweisen.
