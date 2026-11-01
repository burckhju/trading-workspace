# Komponentenentwurf und sichere Aktionen

[Übersicht](README.md) · [Vertrag](notice-contract.md) · [APIs](contracts.ts)

## 1. Kleine gemeinsame Präsentationsschicht

Eine gemeinsame Schicht ist sinnvoll, weil Ursache, Auswirkung, Details,
Statusänderung und Kontextlink in vielen Features dieselbe Darstellungsaufgabe
haben. Die [Inventur](inventory.md) belegt zugleich unterschiedliche fachliche
Bedeutungen gleichnamiger Codes. Deshalb bleiben die Mapper im jeweiligen
Feature; eine globale Funktion `noticeForStatus(status: string)` ist ungeeignet.

| Vorgeschlagener Baustein | Verantwortung | Eingabe | Grenze |
| --- | --- | --- | --- |
| `NoticeCard` | Titel, kurze Ursache/Wirkung, Automatik, notwendige oder optionale Aktion | Vom Owner geprüftes `NoticeView`, Überschriftenebene und Details-ID; der vollständige Dokumentvertrag erweitert dieselbe Projektion | Kein Fetch, Resolver, Retry, Command oder Fachgrenzwert. |
| `NoticeSummary` | Priorisierte eindeutige Hinweisgruppen und betroffene Objektanzahl | Bereits vom Host konsolidierte Gruppen | Zählt weder API-Polls noch Warnsymbole; erstellt keine globale Aufgabenliste. |
| `NoticeDetails` | Herkunft, Originalzeit, historische Gültigkeit, Diagnose, technische Referenzen | Bereits geladene und scopegeprüfte Detailzeilen | Quelleninformationen nur bei vorhandenen Rechten; kein automatischer Bestätigungs-Write. |
| `ContextActionLink` | Zugängliche Navigation zum geprüften Ziel | `NoticeAction` mit Objekt-/Versionskontext | Beide Aktionstypen navigieren nur; kein POST/PATCH/DELETE und kein generischer `onRetry`. |
| `NoticeStatus` | Ruhiges textliches Label samt relevanter Zeit | Fachlich zugeordnete Darstellung aus demselben Hinweis | Farbe und Symbol ergänzen Text; sie entscheiden nicht die Schwere. |

Die Konsolidierung UX3-K spezifizierte diese Komponenten. Der gesonderte
[B1/F1-Schnitt](../../implementation/UX3_B1_CURRENCY_NOTICE.md) implementiert
`NoticeCard`, `NoticeDetails` und `ContextActionLink` im
[Shared-Kern](../../../frontend/src/shared/notices/index.ts). Das ruhige Statuslabel
ist Bestandteil der Karte; `NoticeSummary` und eine eigenständige Statuskomponente
bleiben spätere Aufgaben. Es gibt keine globalen Provider, Toast-Stores, Router
oder Backendtabellen. Der Pilot verwendet einen bestehenden Host und eine fachlich
eng begrenzte Mapperfunktion.

`NoticeView` enthält nur die unverändert übernommenen präsentierbaren Felder
des Vertrags. Berichtskontext, Requestgeneration und Lifecycle bleiben beim
Feature-/Hostowner. B1/F1 erfindet keine Werte, um einen vollständigen
`NoticeContext` künstlich auszufüllen. Der Dokumenttyp `Notice<TFacts>` und
`ExistingDestination` erweitern dieselben Shared-Typen um ihre zusätzlichen
Bindungen; es entsteht kein zweites semantisches Meldungsmodell.

Für tatsächlich gemeinsame reine Präsentations-/Navigationsverträge gilt die
[öffentliche Importgrenze](../../coordination/UX_SHARED_CONTRACTS.md#kontext-navigation-und-gemeinsame-importgrenze--owner-ux-2):
das vorhandene `frontend/src/shared/` beziehungsweise qualifizierte Ownerlinks
über typisierte Props. Gemeinsame Komponenten importieren keine Featureinternas,
Finanz-/Quellenvalidatoren bleiben beim Featureowner. UX2s bereits vorbereitete
Shared-Navigation wird erhalten, keine zweite URLbibliothek oder bloßes
Reexport-Barrel eingeführt. Ein eigener Host-/Formularumbau ist kein Teil von B1/F1.

## 2. Aufbau der kompakten Darstellung

Reihenfolge: verständlicher Titel, ein bis zwei kurze Sätze zu Ursache und
Auswirkung, nötigenfalls Automatik-/Zeitangabe, präzise Aktion, aufklappbare Details.
Wesentliche Einschränkungen gehören neben die betroffene Zahl/Funktion und
dürfen nicht ausschließlich aufgeklappt sichtbar sein.

### Beispiel: fehlender historischer Währungsnachweis

> **Bruttobeitrag nicht berechenbar**
>
> Für eine frühere Kaufbuchung fehlt ein gültiger Währungsnachweis. Der Beitrag
> dieses Verkaufs und die vollständige Berichtssumme können deshalb nicht sicher
> ermittelt werden.
>
> **Vorhandene Kaufbelege prüfen** · Ursache und Quellen

Der Titel wird nur verwendet, wenn der Performance-Owner den betreffenden Verkauf
als `NOT_COMPUTABLE` und den Bericht entsprechend als unvollständig einordnet
und die Währungsursache belegt. Ein bloßer Quellenlesefehler oder `CURRENCY_UNKNOWN`
an einer `EXCLUDED`-Zeile rechtfertigt diesen Text nicht. In Details stehen Kaufdatum,
Produktname, betroffene BUY-/SELL-Referenzen, ursprünglicher Gültigkeitsbereich,
Resolverversion und tatsächlich gemeldeter Reason. `cost_basis_execution_ids`
allein beweist keine gemeinsame Kaufursache; der Prefix kann frühere SELLs enthalten.
Frühere Ableitungsversuche
werden nur gezeigt, wenn sie geliefert werden, nicht aus dem Ergebnis erfunden.

Das vorhandene Ziel `#execution-dates` führt bisher zum Buchungsbereich des
exakten Trades. Die betreffende Ausführung wird daher im Hinweis benannt; eine
bereits implementierte automatische Zeilenfokussierung wird nicht behauptet.

### Beispiel: sicher automatisch nachgewiesene Währung

> **Ausführungswährung belegt**
>
> Der vorhandene historische Ausführungsbeleg weist EUR aus. Die Anwendung
> verwendet diesen Nachweis bereits; eine erneute Eingabe ist nicht nötig.
>
> Herkunft anzeigen

Das ist eine Information über den vorhandenen Resolverausgang. Sie wird nicht
bei jedem Read als neue Erfolgsmeldung angekündigt und erzeugt keine menschliche
Bestätigung. Bei einer anderen Provenienz verwendet der Text deren tatsächliche
Herkunft, etwa ein historisch belegtes Listing statt „Ausführungsbeleg“.

### Beispiel: fehlgeschlagener Abruf mit gespeichertem Kurs

> **Neuer Kursabruf fehlgeschlagen**
>
> Der Anbieter hat den Abruf begrenzt. Der gespeicherte Kurs vom 30.10., 17:20 Uhr
> bleibt sichtbar; seine Verwendbarkeit richtet sich nach der ausgewiesenen
> Kursqualität.
>
> Nächste automatische Prüfung frühestens: 31.10., 09:05 Uhr.
>
> Kursdatenstatus anzeigen · Abruf und Quellen

Die Zeiten sind **synthetische Textbeispiele**. Produktiv kommen sie unverändert
aus `quote_observed_at` bzw. `next_run_at`, mit klarer Anzeigezeitzone. Die
Retry-Zeile entfällt ohne tatsächlichen Planungsbeleg. Kein „Jetzt abrufen“
umgeht `Retry-After`; ein lesender Status-Refresh ist kein Providerretry.

Ein normaler `LAST_AVAILABLE`-Sitzungskurs erhält dagegen zum Beispiel:

> **Letzter verfügbarer Sitzungskurs**
>
> Der vorhandene Kurs ist nach der Sitzungsbewertung verwendbar. Kurszeit und
> Quelle stehen bei der Bewertung.

Dieser Text benötigt das entsprechende Ownerurteil, nicht nur den Statusnamen.
Ein separat fehlgeschlagener Abruf bleibt unabhängig davon erklärbar.

### Beispiel: gespeicherte Änderung, aktueller Stand nicht lesbar

> **Bestätigung gespeichert — aktueller Stand noch nicht geladen**
>
> Die Speicherung wurde bestätigt. Der anschließende Leseversuch ist
> fehlgeschlagen. Der aktuelle Stand kann erneut geladen werden.
>
> Aktuellen Stand laden

Ein bestätigtes Receipt und der Readfehler bleiben zwei belegte Fakten. Der
erneute Klick liest ausschließlich. Dieser Readbutton gehört zum bestehenden
Host neben dem Hinweis; er ist kein `NoticeAction`-Link und kein versteckter
Fetchcallback von `onNavigate`. Bei **unklarem** Schreibausgang lautet die
Aussage stattdessen „Abschluss noch nicht bestätigt“. Ob weitere Commands eine
vorherige Prüfung verlangen, entscheidet der bestehende Ownerguard. Journal
besitzt den bewussten identischen Retry mit eingefrorenem Trade/Actor/Payload/Key;
GET oder Verwerfen klärt Unknown nicht. Lesson-Create, Governancevalidation,
Approval und Aktivierung erhalten daraus keine generische Wiederholungsgarantie.
Eine strukturierte Journal-503 bleibt nach Ownervertrag Unknown. Keine neue
Request-ID, kein veränderter Payload und keine Mutation aus einem Hinweisklick.

### Beispiel: Aktivierungsstand noch nicht verifiziert

> **Modell freigegeben — Aktivierungsstand nicht verifiziert**
>
> Die Freigabe ist bestätigt. Der aktuelle Runtime-Stand konnte nicht gelesen
> werden. Ob diese Version aktiv ist, ist damit noch nicht bestätigt.

Dieser Text benötigt eine passende Approval und den separat fehlgeschlagenen
Runtime-Read desselben Modellkontexts. Erst ein erfolgreiches `current=null`
belegt „keine aktive Version“. Die Reader behalten eigene Versions-/Zeit-/
Generationsbezüge; weder ein gemeinsamer Bildschirm noch ein UI-Token macht sie
atomar. Ein bekannter Lessonkontext kann navigiert werden; ein Modell-ID-Wert
allein erzeugt keinen erfundenen Governancepfad oder Aktivierungsknopf.

### Normale Zustände

`DRAFT`, gültige historische Versionen, ausgeschlossene stornierte Fehleinträge,
vollständig geprüfte leere Reportauswahl, laufende Nachbeobachtung und genehmigte,
noch nicht aktivierte Modelle werden ruhig eingeordnet. Sie brauchen keinen
Warnrahmen, blinkendes Symbol oder automatisch geöffneten Dialog.

## 3. Aktionen: Lesen und Schreiben ausdrücklich unterscheiden

| Aktion | Kategorie | Verhalten des Hinweises | Zuständige Folgehandlung |
| --- | --- | --- | --- |
| Ausführungsbeleg prüfen | Lesend | Exakten Trade und vorhandenen Buchungs-/Quellenbereich öffnen | Quellen lesen; Korrektur nur durch eigenen bewussten Schritt. |
| Historische Quelle öffnen | Lesend | Exakte verfügbare Version pinnen | Kein Wechsel auf aktuelle Version bei fehlender historischer Quelle. |
| Kursdatenstatus anzeigen | Lesend | Bereits verfügbare objektgebundene Diagnostik öffnen | Fehlender genauer Zielvertrag ist Integrationsbedarf; keine allgemeine Seite als exaktes Ziel ausgeben. |
| Planversion prüfen | Lesend | Plan-ID und Versions-ID gemeinsam übergeben | Freigabe bleibt gesonderter Ownercommand. |
| Journal fortsetzen | Entscheidungsworkflow öffnen | Existierendes Journal/Version öffnen | Entwurf speichern/finalisieren nur nach Nutzerhandlung; Öffnen erstellt keinen Entwurf. |
| Fehlende Produktzuordnung prüfen | Lesend | Bestehenden Run-/Produkt-Reparaturkontext öffnen | Stammdaten ändern nur im vorhandenen Fachformular. |
| Währungsbestätigung vorbereiten | Entscheidungsworkflow öffnen | Passenden bestehenden Ownereditor erreichen | Bestätigung/Korrektur braucht konkrete Evidenz, Version und ausdrücklichen Klick. |
| Modellfreigabe prüfen | Entscheidungsworkflow öffnen | Nur bei belegtem passenden Governancekontext anbieten | Validierung, Approval und Aktivierung bleiben getrennte Befugnisse/Commands. |

Im Vorschlag heißt der zweite Typ `open-decision`: Er kennzeichnet den Weg zu
einem **schreibenden Folgeschritt**, führt selbst aber ausschließlich Navigation
aus. Das vermeidet einen Link „Freigeben“, der heimlich eine Mutation ausführt.
Die Hinweis-API besitzt keinen Requestbody, keinen Mutationcallback und keinen
universellen Retrybutton. Bestehende direkte Feld-/Formularaktionen verbleiben
bei UX-1 und dem Domain-Owner.

Ein benannter Readbutton führt beim bestehenden Reader genau den angezeigten
Lesevorgang aus. Lokales Verwerfen ist kein Serverwrite, aber eine bewusste
Entscheidung im vorhandenen Dirty-Guard. Schreiben, Freigeben, Finalisieren und
Aktivieren bleiben ausdrücklich benannte Ownercommands mit ihren bestehenden
Versionen, Zustands-/Idempotenzpins und Bestätigungen. Kein generischer Callback
in `ContextActionLink` übernimmt eine dieser Wirkungen.

Die HTTP-Methode allein bestimmt die Wirkung nicht:
[Monitoring-Health](../../../backend/app/features/position_monitoring/service/health.py)
kann bei einem GET einen Provider lesen; Hinweisrendering/Navigation startet
keinen zusätzlichen solchen Aufruf. Ein Monitoring-Einmallauf kann Alerts und
Benachrichtigungen erzeugen und ist kein „Status neu laden“. POST `/risk/preview`
ist eine nicht persistente Vorschau; Risikoauswertung und Konfigurationsänderung
mutieren. Die belegte Wirkung und vorhandene Ownergrenze entscheiden, nicht GET
oder POST als pauschales Merkmal.

## 4. Nachweisbare bestehende Navigationsverträge

| Ziel | Vorhandene Form / Builder | Garantie und Grenze |
| --- | --- | --- |
| Trade | `/trade-management?trade_id=…` | Exakter Trade, Besitzprüfung bleibt im Backend/Reader. |
| Buchungsbereich | `/trade-management?trade_id=…#execution-dates` | Exakter Trade/Bereich; keine heute belegte `execution_id`-Zeilenfokussierung. |
| Historische Tradequellen | `sourceLink(query, pinKey, versionId)` | `view=sources`, `review_version_id`/`journal_version_id`; bewahrt zulässigen Berichtskontext. |
| Berichtsrückweg | `closedContextQuery`, `realizedContextQuery`, `preserveClosedContext` | Definition, Zeitraum, Währung, Zeitzone, View, Seite und Basis getrennt prüfen. URL ist kein Geld-/Quellennachweis. |
| Planversion | `/trade-plans?trade_plan_id=…&trade_plan_version_id=…` | `planViewContextKey` und vorhandene Responsevalidatoren nutzen. |
| Auswahlrun | `/product-selection?run_id=…` | `selectionRoute`/`assertRunContext` prüfen Plan-/Versionszusammenhang. |
| Produktreparatur | `selectionRepairUrl(runId, warrantId)` | `/warrants-admin?selection_run_id=…&warrant_id=…`; Ziel prüft Run, Produktmitgliedschaft und Basiswert. Nur mit belegtem Run-/Warrantbezug, kein allgemeiner Warrantfokus. |
| Journalversion | `/post-trade?trade_id=…&journal_version_id=…` | `selectJournalEntry` prüft Trade, Journal und Version. |
| Lessonversion | `/lessons/…?lesson_version_id=…#lesson-history` | Historische Version bleibt unverändert; explizite Folgeaktionen mit dieser Quelle entscheidet der Owner. Governancepanels leben in diesem Kontext, keine eigenständige `/governance`-Route. |
| Analyseversion | `/market-analyses/{analysis.id}?version={version.number}` | Exakte belegte Analyse und Version, kein Ersatz durch eine andere Analyse desselben Basiswerts. |
| Basiswert | `/underlyings/{underlying.id}` | Echte belegte ID; kein Name als Identitätsersatz. |
| Diagnose / Produktpflege ohne Run | `/workspace` beziehungsweise `/warrants-admin` | Übersichtslinks so benennen; kein belegter allgemeiner Incident-/Warrant-Deep-Link. |

Quellen:
[Router](../../../frontend/src/app/router.tsx),
[sourceView](../../../frontend/src/features/trade/services/sourceView.ts),
[Performance-Links](../../../frontend/src/features/performance/services/closedReportContext.ts),
[Plan-Kontext](../../../frontend/src/features/trade_plan/services/planViewContext.ts),
[Produktauswahl](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.tsx),
[Produktreparatur](../../../frontend/src/features/product/services/selectionRepairContext.ts),
[Reparaturconsumer](../../../frontend/src/features/product/pages/WarrantAdminRoutePage.tsx),
[Reparaturregression](../../../frontend/src/features/product/pages/WarrantSelectionRepair.test.tsx),
[Journal-Herkunft](../../../frontend/src/features/learning/components/JournalEvidenceOrigin.tsx),
[Lesson-Review](../../../frontend/src/features/learning/components/LessonReviewPanel.tsx).

Vor Navigation prüft der Host: passender aktueller Kontext, exakte Objektbeziehung,
zulässige Parameter und vorhandener Zielvertrag. Interne Links bleiben relativ
und innerhalb der Anwendung; keine externen `returnTo`-Ziele, Geldbeträge oder
vertrauten Statusbehauptungen aus der URL übernehmen. Fehlende/mehrdeutige Pins
bleiben Fehler, keine stille aktuelle Ersatzversion. Externe Quellen werden nur
als vom Owner geprüftes HTTP(S)-Ziel verlinkt; Freitext-`source_reference` wird
nicht automatisch zu einer URL. `javascript:`, `data:`, `file:` und
Protokoll-relative Ziele sind keine zulässigen Quellenlinks.

Die noch fehlenden exakten Sourcecheck-, Ausführungsfokus- und beliebigen
Governanceziele sind UX-2-Integrationspunkte. Bis zur Vereinbarung nur nachweisbar
funktionierende Objekt-/Bereichslinks oder lokale Details anbieten, keine
scheinbar funktionierenden Wunschparameter.

Vor Create oder bei unbekanntem Writeergebnis kann `SubjectRef` nur den bekannten
Vorgangs-/Elternkontext tragen. `ExistingDestination` verlangt weiterhin echte
bestätigte Objektidentität. Ohne passende Zielbeziehung bleibt eine konkrete
Anleitung; kein Dummy-ID-Link, kein Modell-ID→Lesson-ID-Ersatz. Die Reviewquelle
nutzt `view=sources&review_version_id=…`; der Journalpin bleibt
`/post-trade?trade_id=…&journal_version_id=…`. Nicht unterstützte Reviewparameter
auf `/post-trade` gelten nicht als historische Bindung.

Der [Koordinationsstand](integration-and-rollout.md#2a-verbindlicher-koordinationsstand)
benennt UX2s vorbereitete Shared-Helper und den tatsächlichen Main-/PR-Bezug.
Der konkrete Produktpilot verwendet den dann integrierten Ownervertrag und
erbaut keine parallele Navigation. Kopierter Link, Reload und Zurück/Vorwärts
müssen historische Pins und den erlaubten Berichtsrückkontext erhalten.

## 5. Mobile und barrierefreie Darstellung

Diese Punkte sind Abnahmeanforderungen für die Folgeimplementierung, keine
Behauptung bereits geprüfter Konformität:

- Kompakter Hinweis funktioniert bei 320 CSS-Pixel Breite und 200–400 % Zoom
  ohne abgeschnittene Ursache, Auswirkung oder Aktion. Lange Namen/IDs dürfen
  umbrechen; Tabellen und Rohdiagnosen können eine separat benannte Scrollregion besitzen.
- Der Titel beschreibt den Zustand. Ein Icon ist ergänzend und dekorativ
  (`aria-hidden`), wenn der Text seine Bedeutung bereits trägt. Farbe allein
  trägt keine Information.
- Native Links navigieren, native Buttons ändern lokale Ansicht/führen eine
  ausdrücklich beschriftete Owneraktion aus. Keine klickbaren `div`-Elemente.
- Details bevorzugt mit `details/summary`; alternativ Button mit
  `aria-expanded` und `aria-controls`. Eindeutige IDs pro Host/Objekt verhindern
  Konflikte zwischen Sammelansicht und Einzelkarte.
- Tastaturreihenfolge folgt Inhalt. Sichtbarer Fokus, verständlicher Linkname
  („Kaufbelege für … prüfen“ statt mehrfach „Öffnen“), keine reine Hoverinformation.
- Initial geladene und unveränderte Warnungen sind statischer Inhalt. Nicht
  jeder Warning-/Blocker-Typ bekommt automatisch `role=alert`.
- Neue oder verschlechterte relevante Zustände werden einmal über eine vom Host
  verantwortete Live-Region angekündigt. Normale Updates und belegte Erfolge
  `polite`; `assertive` nur für einen tatsächlich fehlgeschlagenen aktuell
  angeforderten Vorgang, der unmittelbare Beachtung verlangt. Keine Ansage aus
  Summary und Karte gleichzeitig.
- Während ein einzelner Abschnitt lädt, kann dieser `aria-busy` verwenden.
  Eine nicht geladene Anzeige ist weder Erfolg noch bestätigte Datenlücke.
- Beim Auf-/Zuklappen bleibt Fokus am auslösenden Element. Nach Navigation führt
  UX-2 den Fokus zur Zielüberschrift bzw. belegten Objektsektion. Bei fehlendem
  Ziel bleibt die Fehlermeldung erreichbar; kein Fokus auf ein fremdes Objekt.
- Entfällt ein fokussierter Hinweis nach belegter Behebung, setzt der Host den
  Fokus auf den logisch nächsten stabilen Bereich und kündigt die Änderung
  ruhig an. Polling verschiebt den Fokus nicht.
- Neue Dialoge sind für Hinweise nicht nötig. Bestehende Bestätigungsdialoge
  verbleiben in den Fachworkflows mitsamt Fokusfalle, Escape und Fokus-Rückgabe.
- Zeitangaben trennen Originalzeit und Prüfzeit; HTML `time` besitzt den originalen
  ISO-Wert. Die Anzeige nennt bei Zweifelsfällen die Zeitzone. Eine reine Uhrzeit
  ohne belegtes Datum/Zone wird nicht zu einem absoluten Kurszeitpunkt ergänzt.

## 6. Exemplarische Komponenten-APIs

Die implementierten reinen Props stehen im
[Shared-Kern](../../../frontend/src/shared/notices/types.ts); der vollständige
Ownervertrag erweitert sie in [contracts.ts](contracts.ts). B1/F1-Aufruf:

```tsx
<NoticeCard
  notice={currencyNotice}
  headingLevel={3}
  detailsId="trade-currency-evidence"
/>
```

`currencyNotice` wird vom Trade-/Performance-Adapter aus einem bereits gültigen
Snapshot geliefert. Die Karte navigiert über den geprüften internen Ownerlink
und erhält keinen Callback. Die gemeinsame Komponente importiert weder
CurrencyResolver noch Finanzberechnungen. `NoticeSummary` bleibt ein gesonderter
späterer Entwurf für bereits vom Host konsolidierte Meldungen und eindeutige
Objektanzahlen; der B1/F1-Pilot implementiert keine Berichtszusammenfassung.

Noch keine CSS-Bibliothek, kein Theme-Wechsel und kein Umbau des ApplicationLayout.
Die vorhandenen Tailwind-/React-Konventionen und Fachkomponenten werden im Pilot
weiterverwendet. Visuelle und Screenreader-Abnahme erfolgt erst an diesem Pilot.
