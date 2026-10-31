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
| `NoticeCard` | Titel, kurze Ursache/Wirkung, Automatik, notwendige oder optionale Aktion | Geprüftes `Notice<TFacts>` und Überschriftenebene | Kein Fetch, Resolver, Retry, Command oder Fachgrenzwert. |
| `NoticeSummary` | Priorisierte eindeutige Hinweisgruppen und betroffene Objektanzahl | Bereits vom Host konsolidierte Gruppen | Zählt weder API-Polls noch Warnsymbole; erstellt keine globale Aufgabenliste. |
| `NoticeDetails` | Herkunft, Originalzeit, historische Gültigkeit, Diagnose, technische Referenzen | Bereits geladene und scopegeprüfte Detailzeilen | Quelleninformationen nur bei vorhandenen Rechten; kein automatischer Bestätigungs-Write. |
| `ContextActionLink` | Zugängliche Navigation zum geprüften Ziel | `NoticeAction` mit Objekt-/Versionskontext | Beide Aktionstypen navigieren nur; kein POST/PATCH/DELETE und kein generischer `onRetry`. |
| `NoticeStatus` | Ruhiges textliches Label samt relevanter Zeit | Fachlich zugeordnete Darstellung aus demselben Hinweis | Farbe und Symbol ergänzen Text; sie entscheiden nicht die Schwere. |

Diese Komponenten werden in Phase 1 **nicht implementiert**. Insbesondere
werden keine neuen Hooks, globalen Provider, Toast-Stores, Router oder
Backendtabellen angelegt. Ein späterer Pilot verwendet zuerst einen Host und
eine fachlich eng begrenzte Mapperfunktion.

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
als `NOT_COMPUTABLE` einordnet und die Währungsursache belegt. Ein bloßer
Quellenlesefehler rechtfertigt diesen Text nicht. In Details stehen Kaufdatum,
Produktname, betroffene BUY-/SELL-Referenzen, ursprünglicher Gültigkeitsbereich,
Resolverversion und tatsächlich gemeldeter Reason. Frühere Ableitungsversuche
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
> fehlgeschlagen. Vor weiteren Änderungen muss der aktuelle Stand geladen werden.
>
> Aktuellen Stand laden

Ein bestätigtes Receipt und der Readfehler bleiben zwei belegte Fakten. Der
erneute Klick liest ausschließlich. Dieser Readbutton gehört zum bestehenden
Host neben dem Hinweis; er ist kein `NoticeAction`-Link und kein versteckter
Fetchcallback von `onNavigate`. Bei **unklarem** Schreibausgang lautet die
Aussage stattdessen „Abschluss noch nicht bestätigt“; ein unveränderter Retry
bleibt im bestehenden idempotenten Ownerworkflow.

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

## 4. Nachweisbare bestehende Navigationsverträge

| Ziel | Vorhandene Form / Builder | Garantie und Grenze |
| --- | --- | --- |
| Trade | `/trade-management?trade_id=…` | Exakter Trade, Besitzprüfung bleibt im Backend/Reader. |
| Buchungsbereich | `/trade-management?trade_id=…#execution-dates` | Exakter Trade/Bereich; keine heute belegte `execution_id`-Zeilenfokussierung. |
| Historische Tradequellen | `sourceLink(query, pinKey, versionId)` | `view=sources`, `review_version_id`/`journal_version_id`; bewahrt zulässigen Berichtskontext. |
| Berichtsrückweg | `closedContextQuery`, `realizedContextQuery`, `preserveClosedContext` | Definition, Zeitraum, Währung, Zeitzone, View, Seite und Basis getrennt prüfen. URL ist kein Geld-/Quellennachweis. |
| Planversion | `/trade-plans?trade_plan_id=…&trade_plan_version_id=…` | `planViewContextKey` und vorhandene Responsevalidatoren nutzen. |
| Auswahlrun | `/product-selection?run_id=…` | `selectionRoute`/`assertRunContext` prüfen Plan-/Versionszusammenhang. |
| Produktreparatur | `selectionRepairUrl(runId, warrantId)` | `/warrants-admin?selection_run_id=…&warrant_id=…`; vorhandene Reparaturnavigation wiederverwenden. |
| Journalversion | `/post-trade?trade_id=…&journal_version_id=…` | `selectJournalEntry` prüft Trade, Journal und Version. |
| Lessonversion | `/lessons/…?lesson_version_id=…#lesson-history` | Historische Inhalte bleiben schreibgeschützt. |

Quellen:
[Router](../../../frontend/src/app/router.tsx),
[sourceView](../../../frontend/src/features/trade/services/sourceView.ts),
[Performance-Links](../../../frontend/src/features/performance/services/closedReportContext.ts),
[Plan-Kontext](../../../frontend/src/features/trade_plan/services/planViewContext.ts),
[Produktauswahl](../../../frontend/src/features/product_selection/pages/ProductSelectionPage.tsx),
[Produktreparatur](../../../frontend/src/features/product/services/selectionRepairContext.ts),
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

Die während der Analyse sichtbar gewordenen **offenen** UX-2-Änderungen ergänzen
diese Main-Ziele um einen kontexterhaltenden Builder und Abschnittsfokus. Der
[Parallelabgleich](integration-and-rollout.md#2a-nachtrag-zu-den-inzwischen-sichtbaren-parallel-prs)
nennt den geprüften Head und die neuen Anker. Nach dessen Integration soll UX-3
diesen Ownervertrag verwenden; es baut die Navigation nicht parallel nach.

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

Die vollständigen Props stehen in [contracts.ts](contracts.ts). Geplanter Aufruf:

```tsx
<NoticeCard
  notice={currencyNotice}
  headingLevel={3}
  detailsId="trade-currency-evidence"
  onNavigate={navigateVerifiedOwnerTarget}
/>

<NoticeSummary groups={hostGroups} onOpenGroup={focusExistingNoticeGroup} />
```

`currencyNotice` wird vom Trade-/Performance-Adapter aus einem bereits gültigen
Snapshot geliefert. `hostGroups` enthält bereits konsolidierte Meldungen und
Count eindeutiger betroffener Objekte. Die gemeinsame Komponente importiert weder
CurrencyResolver noch Finanzberechnungen. `onNavigate` darf nur das validierte
Ziel öffnen; seine Signatur ist keine Berechtigung für Schreibaktionen.

Noch keine CSS-Bibliothek, kein Theme-Wechsel und kein Umbau des ApplicationLayout.
Die vorhandenen Tailwind-/React-Konventionen und Fachkomponenten werden im Pilot
weiterverwendet. Visuelle und Screenreader-Abnahme erfolgt erst an diesem Pilot.
