# UX3-A — Fachlicher Hinweisvertrag

## Dokumentinformationen

| Feld | Wert |
| --- | --- |
| Dokumenttyp | Darstellungs- und Schnittstellenentwurf, Revision 0.1 |
| Prüfdatum | 31.10.2026, Europe/Vienna |
| Geprüfte Implementierung | `main` / `1883f7f330719453958f8be1dd51d48db816662e`, `VERSION` 1.5.35 |
| Freigabe | Zur Abstimmung mit UX-1, UX-2, UX-4 und den jeweiligen Domain-Ownern; noch keine gemeinsame Schnittstellenfreigabe |
| Autorisierter Umfang | UX3-A: Inventur, Vertrag und getrennte Folgeaufträge als Dokumentations-Draft-PR |
| Arbeitsstatus | Maßgeblich bleibt [Product Backlog](../planning/PRODUCT_BACKLOG.md#operational-workspace) |

Die [Hinweisinventur](ux3-notice-inventory.md) belegt den Ist-Stand. Dieses Dokument
beschreibt den vorgeschlagenen Vertrag; es führt weder einen REST-Endpunkt noch einen
produktiven Typ, eine Komponente, einen Resolver oder einen neuen Domainzustand ein.
[UX3-B bis UX3-D](../planning/UX3_FOLLOW_UP_ORDERS.md) sind eigene, noch abzustimmende
Umsetzungsaufträge. Produktive Formulare und Workspace-Komponenten werden in UX3-A
nicht geändert. Merge, Release und Handelsaktionen sind nicht autorisiert.

## 1. Zuständigkeit und fachliche Grenzen

Ein wichtiger Hinweis beantwortet in dieser Reihenfolge:

1. **Was ist betroffen?** Konkretes Objekt, Vorgang und gegebenenfalls Version oder Zeitraum.
2. **Warum?** Beobachtete Ursache oder ausdrücklich noch unbekannter Grund.
3. **Welche Auswirkung besteht?** Betroffene Aussage, Zahl oder Operation mit ihrer Grenze.
4. **Was löst das System bereits?** Nur belegte Wiederverwendung, laufende Verarbeitung oder Wiederholung.
5. **Was bleibt für den Nutzer?** Konkreter nächster Schritt oder ausdrücklich keine derzeit erforderliche Aktion.

Die Informationen dürfen auf Kurztext, Details und Aktion verteilt werden. Eine
Ursachenkette darf aufklappbar sein; der entscheidende Blocker und seine Auswirkung
dürfen nicht ausschließlich in Details verschwinden.

| Owner | Liefert / entscheidet | UX-3 darf |
| --- | --- | --- |
| Bestehende Domains / Readmodelle | Fachzustand, Fehlercode, Verwendbarkeit, Identität, Version, finanzielle Ergebnisse, zulässige Commands, Retry-/Recoveryfakten | Diese Fakten unverändert und verständlich darstellen |
| UX-1 | Sichere Eingabeableitung und Wiederverwendung aus diesen Ownern; Vorschau und manuelle Eingabe bleiben getrennt | Erklären, welche vorhandene Quelle verwendet wurde und welche Entscheidung offen bleibt |
| UX-2 | Positionierung, Arbeitskontext, Bereichsnavigation, Formular-/Reader-Lebensdauer und Rückwege | Den vereinbarten Anzeigeplatz und die bestehenden Navigationshelper nutzen |
| UX-4 | Visualisierung vorhandener Datenqualität, Abdeckung und Zeitbezüge | Textbedeutung, Legende und zugängliche Beschreibung beitragen |
| UX-3 | Formulierungen, Belegdarstellung, sichere Aktionsbeschreibung, semantische Gruppierung | Präsentationsadapter und wiederverwendbare Anzeige nach gemeinsamer Freigabe spezifizieren |

UX-3 berechnet weder Währungen, Geldbeträge, Nenner, Kursfrische, Providerqualität,
Risikoschwellen, Tradingregeln, Planfreigaben noch Runtimebereitschaft. Ein
Hinweisadapter darf keine alternative Zustandsmaschine, persistierte Aufgabenliste
oder generischen `acknowledged`-/`dismissed`-/`resolved`-Zustand besitzen.

Maßgeblich bleiben insbesondere [Workspace-Statusmeldungen](workspace-statusmeldungen.md),
[Trade-Capture-Sicherheit](../trade-capture-safety.md),
[historische Ausführungswährung](../implementation/HISTORICAL_EXECUTION_CURRENCY.md),
[Bewertungswährung](../implementation/POSITION_VALUATION_CURRENCY_QUALIFICATION.md),
[Monitoring-Datenqualität](../monitoring-data-quality.md),
[Journal-Lifecycle](../decisions/ADR-POST-FT012-005-JOURNAL-WRITE-LIFECYCLE.md),
[Lesson-Review](../decisions/ADR-POST-FT012-006-EXPLICIT-LESSON-REVIEW.md) und
[Hebeltrader-Integrationsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md).
Dessen dokumentierte Sollregeln sind kein Nachweis ihrer produktiven Umsetzung.

## 2. Verschiedene Aussagen getrennt halten

| Aussage | Beispiel vorhandener Quelle | Unzulässige Gleichsetzung |
| --- | --- | --- |
| Fachlicher Lebenszyklus | Position `is_closed`/`is_cancelled`, Tradequellenprojektion `OPEN`/`CLOSED`/`CANCELLED`/`UNKNOWN`, Plan `APPROVED`, Alert `RESOLVED` | `APPROVED` = Runtime aktiv; `RESOLVED` = Kurs hat sich erholt |
| Fachliche Aufmerksamkeit | Offener `STOP_REACHED`-Alert, vorhandenes Positionssignal | Datenlücke = Verkaufssignal; Hinweis = Brokerorder |
| Datenverwendbarkeit | `valuation_usable`, `analysis_usable`, Währungsauflösung, Berichtspopulation | Abruf erfolgreich = Kurs aktuell/ausführbar; unbekannter Betrag = 0 |
| Technische Verarbeitung | Scheduler `PENDING`/`DEFERRED`, Laufzeit aktiv, Transportfehler | `DEFERRED` = Kurs fehlt; Dienst aktiv = alle Regeln geprüft |
| Verfügbarkeit eines Schritts | `can_evaluate`, erlaubte Journalaktion, bestehender Commandguard | Lesender Quellenfehler sperrt alle fachfremden Formulare |
| Ergebnis einer Benutzeraktion | Explizite Ablehnung, bestätigter Write, unklarer Writeausgang, fehlgeschlagener Readback | Jede Exception = nichts gespeichert; erneuter GET = Write wiederholen |

Diese Achsen werden referenziert, nicht in einen neuen globalen Status wie
„Trade gesund“ zusammengerechnet. Ein Objekt darf gleichzeitig einen fachlichen
Alert, einen alten Referenzkurs und eine noch offene Zustellstörung haben.

Lesson-`CURRENT` beschreibt den Stand der Interpretation. Quellenlinie
`CURRENT`/`SUPERSEDED` und Reviewcurrentness `CURRENT`/`STALE`/`UNKNOWN` sind
eigenständige Aussagen. Quellenalter ist kein Widerspruchsbeleg. Ein fehlgeschlagener
Runtime-Read ist ebenfalls keine bestätigte Aussage „keine Version aktiv“;
Letzteres benötigt einen erfolgreichen Ownerread mit `current=null`.

## 3. Vertrag eines einzelnen Hinweises

Die folgende Struktur ist ein **fachlicher Übergabevertrag**, keine neue persistierte
Domain-Entität. Feldnamen sind Vorschläge für die Schnittstellenabstimmung; konkrete
TypeScript-Typen und Adapter entstehen erst in UX3-B. Alle Werte stammen aus dem
aktuellen, kontextgeprüften Owner-Ergebnis oder aus belegter lokaler Formularvalidierung.

| Bestandteil | Pflicht / Inhalt | Verbindliche Regel |
| --- | --- | --- |
| `presentationKey` | Stabile Kennung der Textvorlage | Kein neuer Domainfehlercode und keine Identität eines fachlichen Alerts |
| `subject` | Objekttyp und echte ID soweit belegt, lesbare Bezeichnung; sonst genauer Vorgangs-/Formular-/Filterkontext und bekannte Elternreferenz | Nach unklarem Create oder vor dem ersten Read keine ID erfinden. Belegte IDs dienen Zuordnung/Navigation; sichtbarer Titel verwendet Namen, WKN/ISIN, Buchungsart und Datum soweit vorhanden |
| `context` | Workspace; exakte Trade-/Plan-/Review-/Journal-/Lessonversion, Instrument-/Listingbezug oder Berichtsart/Filter soweit einschlägig | Kein Wechsel auf `latest`, keine Objektzuordnung über gleiche Namen oder ähnlich aussehende IDs |
| `origin` | Zuständiger Reader/Command; unverändertes Statusfeld, Fehler-/Reason-Code und Referenz auf die belegenden Daten | Freitext wird nicht nach Schlüsselwörtern geparst, um eine spezifischere Ursache zu erfinden |
| `cause` | Verständliche Erklärung des belegten Grundes | Fehlt der Grund: genau sagen, welche Beobachtung vorliegt und dass die Ursache nicht näher bestimmt ist |
| `impact` | Welche Operation oder Aussage betroffen ist; separat, was weiterhin fachlich verfügbar ist | Nur bestehende Guards/Flags begründen eine Sperre. Unvollständige Bewertung darf eine tatsächliche Verkaufserfassung nicht neu blockieren |
| `systemHandling` | Belegte bereits ausgeführte oder eingeplante Systemleistung mit ihrer Grenze | „Wiederholung eingeplant“ nur mit Schedulerbeleg; keine Erfolgs-, Termin- oder automatischen Reparaturversprechen |
| `userStep` | Konkrete verbleibende Entscheidung oder „derzeit keine zusätzliche Eingabe erforderlich“ | Ein Problem erzeugt nicht automatisch eine Pflichtentscheidung. Keine unnötige Wiederholung bereits belegter Eingaben |
| `evidence` | Quellenart, Originalreferenz, Version, Gültigkeitszeitraum, fachlicher Zeitpunkt, Lesezeitfenster soweit geliefert | Kurszeit, Ausführungszeit, Erfassungszeit und Lesezeit unterscheiden; mehrere Reader nicht als atomaren Gesamtsnapshot ausgeben |
| `actions` | Nur verifizierte Ziele beziehungsweise bereits vorhandene Command-Owner; siehe Abschnitt 6 | Fehlendes Ziel erzeugt erklärende Anleitung, keinen geratenen Link und keinen generischen Schreibcallback |
| `grouping` | Optionaler belegter Ursachenbezug und exakter Kontext; siehe Abschnitt 7 | Ohne belegten gemeinsamen Ursachenbezug nur identische Vorkommen deduplizieren |

**Fehlende Namen:** „Produktname nicht verfügbar“ mit vorhandener WKN/ISIN ist
zulässig. Bei ganz fehlender Anzeigeidentität: „Betroffener Trade“ plus vorhandenes
Datum/Elternkontext. Technische UUID und Diagnosecode bleiben kopierbar in
„Technische Details“, niemals alleiniger Hinweistext. Fremde Stammdaten werden
nicht als Namenersatz geladen. Kein zusätzlicher Request pro Hinweis; vorhandene
mengenbasierte Identitätsreader und bereits geladener Kontext bleiben zuständig.

**Fehlende Ursache:** Ein fehlgeschlagener Request ist eine nachgewiesene technische
Beobachtung. Er belegt weder einen Providerausfall noch veraltete Kurse oder eine
fehlende Währung. Zulässiger Text: „Die Währungsherkunft konnte nicht gelesen werden.
Ob ein verwendbarer Beleg vorliegt, ist derzeit nicht bestätigt.“

**Fehlertransport:** Der vorhandene Vertrag enthält `code`, `message`, `details[]`
mit `field`/`context` und `timestamp`;
[MarketApiError / MarketTransportError](../../frontend/src/features/market/services/http.ts)
unterscheiden strukturierte API-Fehlerantworten und Transportfehler. Ob ein Command
endgültig abgewiesen wurde oder sein Ausgang unklar bleibt, bestimmt der jeweilige
Ownervertrag. Insbesondere strukturierte HTTP-5xx-Antworten sowie ungültige oder
nicht sicher zuordenbare Erfolgsantworten beweisen nicht, dass nichts gespeichert
wurde. Ein Code wie
`TRADE_PLAN_VALIDATION_ERROR` oder `MODEL_GOVERNANCE_CONFLICT` darf nur so fein
erklärt werden, wie seine strukturierten Daten es belegen. Englische
`ValueError`-Texte werden nicht zu einer zweiten maschinenlesbaren Fachschnittstelle.
Fehlende strukturierte Detailcodes werden als Owner-Abhängigkeit erfasst.

Unbekannte Codes erhalten einen neutralen, vorgangsbezogenen Ersatztext und
behalten den Code als sekundäre Diagnose. Rohe Exceptions, HTML, Providerantworten,
Zugangsdaten und beliebige `details.context`-Werte werden nicht ungefiltert gerendert.
Nur bekannte, für den Benutzer relevante Detailfelder werden angezeigt.

## 4. Vorgeschlagene Meldungstypen und Statusdarstellung

Die Typen wählen eine Darstellung; sie verändern keine Domainstatuswerte.

| Meldungstyp | Einsatz | Beispiel / Begrenzung |
| --- | --- | --- |
| Vorgangsblocker | Vorhandener Owner untersagt den konkret angeforderten Schritt | `OPEN_TRADE_EXISTS`: Erstkauf für dasselbe Produkt abgewiesen; bestehenden Trade öffnen |
| Erforderliche Entscheidung | Owner verlangt tatsächlich eine Auswahl, Begründung oder explizite Bestätigung | Erneute Quellenbestätigung für eine konkret angeforderte quellengebundene Journalaktion; vorhandene gültige Drafttexte bleiben nach Ownerregeln speicherbar, keine automatische Neubindung |
| Fachlicher Hinweis | Bereits vorhandener Alert oder fachliche Aufmerksamkeit | Stop erreicht mit gebundenem Instrument, Preisbasis und Originalzeit; keine Verkaufsanweisung |
| Datenqualität / Aussagegrenze | Fehlende, ungeklärte, eingeschränkte oder veraltete Daten | PnL nicht bestimmbar, obwohl qualifizierter Marktwert separat verfügbar ist |
| Verarbeitung / technischer Fehler | Lesezugriff, Warteschlange, Laufzeit oder Zustellung | Zustellfehler getrennt vom weiterhin offenen fachlichen Alert |
| Quellen- / Kontextinformation | Provenienz, historische Version, bekannte Präzisionsgrenze | Ausführungstag bekannt, Uhrzeit nicht bekannt; kein fiktiver Mitternachtskauf |
| Bestätigtes Ergebnis / Recovery | Owner bestätigt Operation oder nachgewiesene Wiederherstellung | Gespeichert mit neuer Version; Quelle im exakt passenden Kontext wieder verfügbar |

Text, Icon und Farbe tragen dieselbe Bedeutung. Farbe allein reicht nicht.
„Lädt“, „nicht geladen“, „leer“, „nicht verfügbar“ und „fehlgeschlagen“ bleiben
unterscheidbar. „Unauffällig“ bedeutet ausschließlich: kein Hinweis in den konkret
geprüften Dimensionen; es ist keine Empfehlung zu halten oder eine globale Entwarnung.
`PARTIAL` wird je Berichtstyp/Verwendbarkeit übersetzt, nicht global als „teilweise OK“.

Auch eine **belegte Nichtanwendbarkeit** ist vom Fehler zu trennen: Der vorhandene
Health-Reader setzt eine offene Position voraus und liefert bei deren Fehlen 404.
Bei anderweitig autoritativ belegter geschlossener Position ist aktuelle Health
nicht anwendbar; historische Alerts bleiben lesbar. Ein 404 oder ein fehlgeschlagener
Read allein beweist keine Schließung. Im offenen beziehungsweise ungeprüften Kontext
bleibt der fehlende aktuelle Gesundheitsnachweis sichtbar. Kein neuer Domainstatus
und kein Parsing von „No open position“-Fehlertexten.

Ein kompakter Hinweis enthält Objekt, Kernaussage/Auswirkung und höchstens eine
vorrangige sichere Aktion. Details enthalten Ursachen, weitere betroffene Objekte,
Quellen und sekundäre Aktionen. Persistente Informationen verwenden keine ständig
erneut ausgelöste Alarmansage. Vorgangsbezogene Fehler werden an den betroffenen
Feldern und einmal zusammenfassend zugänglich gemacht; keine doppelte Live-Ansage.

## 5. Textbeispiele mit belegten Voraussetzungen

Die Beispiele sind Solltexte für die spätere Umsetzung, keine Behauptung über ein
persönliches Depot. Platzhalter werden ausschließlich aus dem geprüften Objekt gefüllt.

| Voraussetzung / Quelle | Vorgeschlagene Darstellung | Systemleistung und verbleibender Schritt |
| --- | --- | --- |
| `OPEN_TRADE_EXISTS` mit belegter bestehender Trade-ID | „Für {Produkt} besteht bereits ein offener Trade. Ein weiterer Erstkauf wurde nicht erfasst.“ | „Bestehenden Trade öffnen“; tatsächlichen Nachkauf dort ausdrücklich erfassen, keine automatische Umwandlung |
| Währungsauflösung `UNKNOWN` ohne nutzbaren Beleg | „Die Währung der Buchung vom {Datum} ist noch nicht belegt.“ Nur wenn der jeweilige Ergebnisowner zusätzlich fehlende Währungsherkunft als Unverwendbarkeitsgrund liefert: „{Konkretes Ergebnis} kann deshalb nicht ausgewiesen werden.“ | Vorhandene Resolverprüfung benennen; „Buchung und Währungsbelege prüfen“. Eine unbekannte ersetzte Buchung oder SELL-Währung beweist keinen fehlenden offenen Positions-G/V; keine allgemeine Erfassungssperre |
| `USER_CONFIRMED` beziehungsweise belegtes `PRIOR_BUYS` | „Währung {Code} aus Ihrer Bestätigung“ beziehungsweise „aus den belegten früheren Käufen übernommen“ | Quelle aufklappbar; Ableitung ist keine neue manuelle Bestätigung und setzt kein Formularfeld im Hintergrund |
| Nicht erkannter `analysis_warning` | „Für diese Bewertung liegt ein noch nicht zugeordneter Datenhinweis vor.“ | Tatsächliche Verwendbarkeit separat aus dem Owner; kein pauschales „Kursdaten veraltet“ |
| Kurs fehlt, kein verwendbarer Referenzkurs | „Für {Produkt} liegt in dieser Bewertung kein verwendbarer Kurs vor.“ | Keine Behauptung einer indikativen Bewertung; belegte Scheduleraktivität getrennt anzeigen |
| Qualifizierter indikativ nutzbarer Referenzkurs | „Indikativer Referenzkurs vom {Originalzeitpunkt}. Die genannte Analyse ist mit dieser Datenbasis verfügbar.“ | Preisart, Quelle und Owner-Warnungen; keine Ausführbarkeit oder aktuelle Kurszeit ableiten |
| Performancebericht `PARTIAL` | „{Vom Owner gelieferte Abdeckung} ist auswertbar. Für die übrigen Beiträge fehlen {belegte Gründe}.“ | Betroffene Verkäufe oder abgeschlossene Trades separat öffnen; keine gemeinsame Population und kein eigener Nenner |
| Scheduler `DEFERRED` mit `next_run_at` | „Abruf aufgeschoben. Nächste Prüfung frühestens {Zeit}.“ | Eingeplante Wiederholung anzeigen; kein neuer manueller Abrufzwang und kein Versprechen eines Kurses zu dieser Zeit |
| Alert `RESOLVED`, keine strukturierte Abschlussursache | „Diese Meldung ist abgeschlossen.“ | Historischen Alert/Quellstand lesbar lassen; weder Kurserholung noch erfolgreiche Zustellung behaupten |
| Alert `INVALIDATED` mit `RISK_CONFIGURATION_OR_IDENTITY_SUPERSEDED` | „Diese Meldung gehört zu einer ersetzten Risikokonfiguration oder Identität.“ | Tatsächlichen Invalidierungsgrund zeigen; nicht als ungeklärten Legacy-Kursbezug oder Recovery erklären |
| Modellversion `APPROVED`, keine belegte Runtimeaktivierung | „Modellversion freigegeben. Die Runtime-Aktivierung ist ein eigener Schritt.“ | Bestehenden Governancekontext verwenden, sofern exakt verfügbar; keine automatische Aktivierung oder erfundene Route |

## 6. Sichere Folgeaktionen

### 6.1 Aktionsvertrag

| Aktionsklasse | Verhalten | Voraussetzungen |
| --- | --- | --- |
| Quelle / Objekt öffnen | Native Navigation in einen vorhandenen Owner; kein Command durch Mounten oder Linkaufruf | Identität und Versionsbezug geprüft, Ziel unterstützt die Parameter |
| Daten erneut lesen | Bestehender Reader lädt genau denselben Kontext erneut | Gleiches Objekt/Filter/Version; Abort-/Generationsschutz; keine Mutation als Retry tarnen |
| Bearbeitung prüfen | Öffnet vorhandenen Editor/Vorschau, schreibt noch nichts | Betroffenes Objekt und Auswirkung erkennbar; vorhandene Entwürfe und Pending-Navigation-Guards erhalten |
| Lokalen Entwurf verwerfen | Ausdrückliche lokale Entscheidung ohne Serverwrite | Vorhandener Guard/Bestätigungsweg; nicht als nebenwirkungsfreies Lesen beschriften |
| Expliziter Command | Nur über den bereits zuständigen Formular-/Command-Owner | Bestehende Versionen, Tokens, Idempotenz, Validierung und erforderliche Bestätigung vollständig erhalten |

Jede Aktion beschreibt zusätzlich Zielobjekt/-version, sichtbare Beschriftung,
Lese-/Schreibwirkung, gegebenenfalls Providerzugriff, benötigten Ownerguard,
Pending-Verhalten und Behandlung eines fehlgeschlagenen Ergebnisses. Ein deaktivierter
Schritt nennt den belegten Grund. Die Beschriftung „Öffnen“ bedeutet Navigation;
„Status neu laden“ bedeutet Lesen; „Speichern“, „Freigeben“, „Finalisieren“ oder
„Stornieren“ bezeichnet ausdrücklich den jeweiligen schreibenden Command.

HTTP GET allein beweist keine nebenwirkungsfreie lokale Diagnose: Der bestehende
[Monitoring-Health-Reader](../../backend/app/features/position_monitoring/service/health.py)
kann einen Provider lesen. Der Refresh-Statusreader liest Diagnosen; ein
Monitoring-Einmallauf kann Alerts und Benachrichtigungen erzeugen und ist **kein**
Refresh-Link. UX3-B erhält zunächst nur Anzeige und lesende beziehungsweise
Editor-öffnende Aktionen, keine neue zentrale Commandausführung.
Umgekehrt ist der bestehende POST auf `/risk/preview` eine nicht persistente
Berechnungsvorschau. Die fachliche Wirkung folgt immer dem Ownervertrag, nicht
allein der HTTP-Methode; Risikoauswertung und Konfigurationsänderung bleiben Writes.

### 6.2 Verifizierte Zielmatrix auf Main

Die Routerbasis ist [router.tsx](../../frontend/src/app/router.tsx). Parameter sind
mit den bestehenden Helpern/`URLSearchParams` zu kodieren, nicht durch freie
Stringverkettung aus Fehlermeldungen. Ein Link beweist nur das hier genannte Ziel.

| Betroffenes Objekt | Vorhandenes Ziel | Präzision / Grenze |
| --- | --- | --- |
| Trade / Position | `/trade-management?trade_id={trade.id}` | Echte Trade-ID, kein Produkt- oder Positions-ID-Ersatz |
| Buchung / Währungsbeleg | `/trade-management?trade_id={trade.id}#execution-dates` | Tradegenauer Buchungsbereich; Main besitzt keinen allgemeinen Deep Link auf genau einen Währungseditor. Exakte Ausführungsfokussierung ist UX3-C-Abstimmung |
| Tatsächlichen Verkauf prüfen | `/trade-management?trade_id={trade.id}#sale-capture` | Öffnet das vorhandene Formular; bucht und ordert nichts |
| Tradequellen | `/trade-management?trade_id={trade.id}&view=sources` | Optional exakte `review_version_id` und `journal_version_id`; vorhandener `sourceLink` erhält erlaubten Berichtskontext |
| Planversion | `/trade-plans?trade_plan_id={plan.id}&trade_plan_version_id={version.id}` | Historische gespeicherte Version, kein stiller Latest-Fallback |
| Produktauswahlrun | `/product-selection?run_id={run.id}` | `product_selection_id` ist keine `run_id`; nur aufgelöste tatsächliche Runbeziehung nutzen |
| Analyseversion | `/market-analyses/{analysis.id}?version={version.number}` | Version aus tatsächlicher Analysequelle; nicht irgendeine aktuelle Analyse desselben Basiswerts |
| Journal / Exit Review | `/post-trade?trade_id={trade.id}` | Journalpin `journal_version_id` nach bestehendem Consumer; Reviewquelle alternativ in der lesenden Tradequellenansicht pinnen |
| Lessonversion | `/lessons/{lesson.id}?lesson_version_id={version.id}#lesson-history` | Exakte Lessonversion; Governancepanels leben in diesem Kontext, keine eigenständige `/governance`-Route |
| Performance | `/performance/realized-gross` beziehungsweise `/performance/closed-trades` | Berichtsart, Datum, Zeitzone und unterstützten Rückkontext behalten; Main-Ansicht ist auf EUR festgelegt. Einen übergebenen Nicht-EUR-Quellenkontext nicht still auf EUR umschreiben; vorhandene bewusste neue Berichtsauswahl verwenden |
| Konkreter Basiswert | `/underlyings/{underlying.id}` | Belegte Basiswert-ID; keine Ersatzzuordnung anhand eines Namens |
| Kursdiagnose / Scheduler | `/workspace` | Existierende Panels, aber kein allgemeiner objektgenauer Diagnose-Deep-Link; als Übersichtslink beschriften |
| Produktstammdaten | `/warrants-admin` | Übersicht; kein belegter universeller `?warrant_id`-Consumer. Exakte Ansteuerung bleibt offener Routingauftrag |
| Candidate-Runtimeblocker ohne Governancekontext | Bestehende Anleitung im Candidate-Owner | Kein geratener Aktivierungslink; weitere Routing-/Ownerfreigabe nötig |

UX2-A in [Draft-PR #311](https://github.com/burckhju/trading-workspace/pull/311) ergänzt
Bereichslinks und Rückkontext. Diese Vorschläge sind am geprüften Main noch nicht
verfügbar. UX3-C übernimmt nach Abstimmung die dortigen Helper, statt einen
zweiten URL-/Pinvertrag anzulegen. Fehlende beziehungsweise fremde Zielversionen
bleiben sichtbar fehlerhaft; sie werden weder auf die neueste Version umgebogen
noch durch eine ähnliche Identität ersetzt.

### 6.3 Wiederholen nach Fehlern

| Nachgewiesene Situation | Aussage | Zulässiger Folgeschritt |
| --- | --- | --- |
| Lesender Request fehlgeschlagen | „{Daten} konnten nicht geladen werden.“ | Exakten Read erneut ausführen; vorhandene bestätigte Fakten nicht in 0/leer umwandeln |
| Command ausdrücklich fachlich abgewiesen | „{Vorgang} wurde abgewiesen: {belegter Grund}.“ | Vorhandenen Korrektur-/Konfliktweg öffnen; erforderliche Nutzerentscheidung erhalten |
| Antwort eines Writes verloren, Serverfehler oder ungültige/nicht sicher zuordenbare Speicherantwort | „Das Ergebnis von {Vorgang} ist noch nicht bestätigt.“ | Klassifikation und Recovery ausschließlich nach bestehendem Ownervertrag: Readback oder dessen dokumentierte ausdrückliche Wiederholung desselben Commands; keine neue Request-ID/Payload erfinden |
| Write bestätigt, nachfolgender Read fehlgeschlagen | „Gespeichert. Die aktualisierte Ansicht konnte noch nicht geladen werden.“ | Nur Readback wiederholen; Erfolg nicht zurücknehmen, Write nicht erneut senden |
| Version / State-Token inzwischen veraltet | „Die Grundlage hat sich geändert. Bitte den aktuellen Stand prüfen.“ | Der generische Hinweis verwirft oder bindet keinen Entwurf selbst um. Bestehender Ownerkonfliktweg einschließlich vorgeschriebener neuer Prüfung/Bestätigung oder bewusstem Abbrechen und Neuvorbereiten bleibt maßgeblich |
| Abgebrochener oder überholter Read durch Kontextwechsel | Keine neue Fehlermeldung für das jetzt angezeigte Objekt | Späte Antwort ignorieren; keine Recovery des alten Objekts im neuen Kontext ausrufen |

Ein generischer Hinweisbutton darf bestehende Idempotenz-, Konflikt- oder
Readbacklogik niemals ersetzen. Alle Handels-, Plan-, Journal-, Lesson- und
Governanceentscheidungen verbleiben beim Nutzer und beim fachlich zuständigen Owner.

Journalbefehle besitzen einen ausdrücklich bedienten Retry des eingefrorenen
Auftrags mit identischem Trade, Actor, Payload und Idempotency-Key. Ein erfolgreicher
GET oder lokales Verwerfen klärt dessen unbekannten Ausgang nicht automatisch.
Für Lesson-Erstellung sowie Governance-Validation, Approval und Aktivierung besteht
keine allgemeine entsprechende Retrygarantie. Ein vorhandener Konfliktweg darf
eine neue Prüfung verlangen und einen Bestätigungsentwurf zurücksetzen; UX-3
überschreibt dieses Verhalten nicht durch einen globalen Erhaltungs- oder Retrymechanismus.

## 7. Priorisierung und Redundanz

### 7.1 Reihenfolge

1. **Belegte Blocker für den aktuellen Vorgang.** Gesperrte Operation und Ursache nennen;
   ein Quellenfehler in einem Nebenteil ist kein globaler Seitenblocker.
2. **Tatsächlich notwendige Nutzerentscheidungen.** Nur Entscheidungen, die ein
   vorhandener Fachvertrag verlangt. Kritische fachliche Aufmerksamkeit bleibt
   entsprechend der gelieferten Domainpriorität sichtbar, ohne daraus einen Command abzuleiten.
3. **Fachliche Warnungen und Datenqualitätsgrenzen.** Nach vorhandener Dringlichkeit
   und betroffenem Kontext gruppieren; kritische Alerts nicht in einer Sammelzahl verstecken.
4. **Verarbeitung, Quelleninformationen und bestätigte Ergebnisse.** Nahe am
   betroffenen Objekt; Routinefortschritt darf Blocker nicht verdrängen.

Das ist eine Reihenfolge **innerhalb einer Hinweisfläche**, keine Änderung der
bestehenden Workspace-Aktionsprojektion, ihres `ACTION`/`REVIEW`/`BLOCKED`-Vertrags
oder eines fachlichen Risikoscores. UX-2 entscheidet über Positionierung; UX3-D
muss die Übereinstimmung mit bestehenden kritischen Alerts gesondert nachweisen.
Innerhalb gleichrangiger Hinweise bleibt die Reihenfolge stabil: vorhandene
Ownerpriorität, Objektkontext, danach ein stabiler technischer Schlüssel. Wiederholtes
Polling ändert nicht allein durch die Renderzeit die Reihenfolge.

### 7.2 Deduplikationsvertrag

Identische Vorkommen dürfen nur zusammengeführt werden, wenn Owner, Code/Reason,
betroffene Objektidentität, konkrete Ursache/Quellenreferenz, Version beziehungsweise
Episode, Operation und fachlicher Geltungsbereich übereinstimmen. Für Berichte
gehören Berichtsart, Filter, Währung, Zeitzone und gelieferte Grundlage dazu; für
Kurse Instrument, Listing, Quelle, Preisart und gebundener Zeitpunkt/Regelbezug.

Eine Textgleichheit oder derselbe `UNKNOWN`-/`PARTIAL`-Status reicht nicht. Fehlt eine
belegte gemeinsame Ursachen-ID, wird keine künstliche globale Root Cause erfunden.
Mehrere Renderorte derselben bereits identifizierten Ursache teilen dagegen eine
Hauptbeschreibung und verweisen mit lokal verständlicher Auswirkung darauf.

- **Eine Ursache, mehrere Auswirkungen:** Ein belegter Währungskonflikt kann im Trade
  erklärt werden; PnL und Bericht verweisen darauf und erhalten ihre eigene Abdeckung.
- **Mehrere Objekte, gleiche Ursachenart:** Gruppenkopf mit Anzahl und aufklappbarer
  Objektliste; jede echte Ursache und jede sichere Aktion bleibt erreichbar.
- **Unterschiedliche Populationen:** Periodenverkäufe und vollständig geschlossene
  Trades werden nicht dedupliziert, auch wenn dieselbe Buchung beide beeinflusst.
- **Unterschiedliche Ebenen:** Alert, Zustellfehler, Providerstörung und letzter
  verfügbarer Kurs bleiben verschiedene Aussagen.
- **Darstellungswiederholung:** Ein kompakter Bereichshinweis und seine Details dürfen
  dieselbe Ursache erläutern; nicht zwei gleichlautende Warnkästen und Alarmansagen erzeugen.

Für Rendering und Live-Ansagen darf UX-3 die bereits angezeigte, unveränderte
Hinweisinstanz erkennen. Das ist kein fachliches Quittieren. Ein Ein-/Ausklappen
oder Sitzungswechsel behebt keine Ursache. Ohne Owner-Episodenbeleg darf ein Zeitfenster
keine neue echte Warnung unterdrücken. Kein persistenter Dismiss- oder Entwarnungszustand.

## 8. Recovery und historische Hinweise

„Wieder verfügbar“ setzt einen aktuellen positiven Ownernachweis für **denselben**
betroffenen Quellen-/Listing-/Identitätskontext voraus. Ein expliziter historischer
Versionspin bleibt exakt; ein aktueller Folgestand muss eine neue wirksame
Quellenversion beziehungsweise Berichtsgrundlage offen ausweisen. Ein erfolgreicher anderer
Quellversuch, ein gespeicherter Ersatzkurs, `PENDING`, `DEFERRED`, eine verschwundene
Zeile, ein geschlossener Aufklappbereich oder ein abgebrochener Read genügen nicht.
Existierende `recovered_at`-/Fehlerdiagnosen werden nur in ihrer tatsächlichen
Backendlaufzeit und Episode dargestellt.

Die Beseitigung einer Ursache kann die davon abhängige Warnung nach autoritativem
Readback entfernen. Unabhängige Einschränkungen bleiben bestehen. Ein noch nicht
aktualisierter Folge-Reader wird als solcher beschrieben; es wird kein gleichzeitiger
Erfolg mehrerer Lesefenster behauptet.

`RESOLVED` bei Alerts bedeutet ohne weiteren strukturierten Grund lediglich
abgeschlossen: Der vorhandene Monitoringservice kann Alerts auch bei geänderter
Schwelle/Preisbindung abschließen. Der Trade-Cancellation-Owner schließt außerdem
offene Alerts bei einem Storno ab; daraus folgt keine entsprechende Behauptung für
jeden normalen Vollverkauf. `INVALIDATED` ist ein eigener
historischer Zustand. Weder bedeutet dies eine Nutzerquittierung noch zwingend
Kurserholung. Eine behobene Zustellstörung entscheidet ebenfalls nichts über den Alert.

Gespeicherte historische Quellen, Bestätigungen, Freigaben und Evidenceversionen
bleiben unverändert. Neu gelesene Ableitungen aus aktuell wirksamen Fakten können
durch eine Quellenkorrektur oder einen Widerruf anders ausfallen; historische
Buchungswährung und finanzielle Qualifikation werden nach bestehendem Ownervertrag
neu gelesen, gegebenenfalls mit neuer Reportbasis. Ein heutiger Erfolg belegt keine
damalige Datenverfügbarkeit und ersetzt keinen expliziten historischen Pin.

Bei Lessonreviews bestätigt `RESOLVED` beziehungsweise `UNCHANGED_CONFIRMED` eine
menschliche Prüfentscheidung. Dadurch wird keine Quelle repariert, aktualisiert oder
umgebunden; Interpretationsstatus und Quellenqualität bleiben getrennt.

## 9. Komponentenvertrag für UX3-B

| Geplanter Baustein | Eingabe / Verantwortung | Nicht enthalten |
| --- | --- | --- |
| Kompakter Hinweis | Fertig aufbereitete Identität, Kurztext, Auswirkung, vorhandener Darstellungsrang und eine vorrangige Aktion | Datenfetch, Finanzrechnung, Schreibcommand |
| Ursachendetails | Belegte Gründe, weitere Auswirkungen und optionale technische Diagnose | Reason-Parsing, neue Ursache, allgemeiner Ausweichrat |
| Quellenverweis | Genaue Referenz/Version und lesbares Label, unterschiedliche Zeitarten | Wahl einer neueren oder ähnlichen Quelle |
| Sichere Folgeaktion | Vorab validierter Navigation-/Reader-/Editorauftrag mit Wirkung und Ownerguard | Generische API-Mutation oder eigene Retrylogik |
| Statusdarstellung | Vorhandener fachlicher Status plus Text/Icon und sichtbare Bedeutung | Globaler Qualitäts- oder Freigabestatus |

Featureadapter bleiben bei ihren Ownern; die gemeinsamen Darstellungskomponenten
kennen keine Währungsresolver oder Providerregeln. Der Ablageort unter vorhandenen
`frontend/src/components`/Featuregrenzen ist vor Umsetzung mit UX-2 abzustimmen.
Der bestehende [ErrorNotice](../../frontend/src/features/market/components/ApiFeedback.tsx)
wird nicht in einem unkontrollierten Gesamtaustausch ersetzt. Ein kleiner lesender
Pilot erhält eine Kompatibilitätsgrenze und wird separat qualifiziert.

## 10. Offene Schnittstellenentscheidungen und Abnahmefälle

| Entscheidung | Verantwortliche | Voraussetzung für Folgeumsetzung |
| --- | --- | --- |
| Bestehende oder zusätzliche strukturierte Ursachenfelder bei groben Fehlercodes | Jeweiliger Domain-/API-Owner, UX-1, UX-3 | Konkrete Lücke aus Inventur; kein zusätzlicher Backendvertrag allein wegen Textwünschen |
| Währungsvorschau, manuelle Entwürfe, Readbackinvalidierung | UX-1, UX-3 | Tatsächlichen Head von #312 prüfen; Vorschau ist kein manueller Beleg |
| Anzeigeplatz, genaue Objekt-/Versionsziele und Formularschutz | UX-2, UX-3 | Tatsächlichen Head von #311 prüfen; fehlende Objektfokussierung separat entscheiden |
| Bedeutung von Verwendbarkeit, Abdeckung, Originalzeit, Legende | UX-4, Domain-Owner, UX-3 | Bestehende Flags und Reason-Codes; aktuell kein veröffentlichter UX-4-Vertrag identifiziert |
| Ursachenidentität / Wiederauftreten / Recoverybeleg | Domain-Owner, UX-3 | Vorhandene IDs/Versionen verwenden; fehlende Episode nicht im Frontend erfinden |
| Pilot und Integrationsreihenfolge | UX-1/2/4, UX-3 | Konkrete Schnittstellenfreigabe am aktuellen Main; keine gegenseitigen Feature-Branch-Merges |

Die [Folgeaufträge](../planning/UX3_FOLLOW_UP_ORDERS.md) enthalten prüfbare
Akzeptanzfälle, Tests und Abhängigkeiten. Besonders zu prüfen sind unbekannte Codes,
schreibende Requests mit verlorenem Ergebnis, bestätigtes Speichern mit fehlerhaftem
Readback, verschiedene Berichtspopulationen, historische Pins, doppelte Live-Ansagen
und echte neue Warnungen nach einer belegten Recovery.

## Änderungshistorie

| Revision | Datum | Änderung |
| --- | --- | --- |
| 0.1 | 31.10.2026 | Initialer, noch abzustimmender UX3-A-Hinweisvertrag auf geprüftem Main; ausschließlich Dokumentation |
