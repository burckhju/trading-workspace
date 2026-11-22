# Datenversorgung für die Depotüberwachung — 20.11.2026

> **Neuer tatsächlicher Betriebsbeleg vom 22.11.2026:** Der
> [vollständige private PC-Readback](DEPOT_DATA_READBACK_2026-11-22.md) bestätigt
> v1.5.52/c7db441…, Schema0060, vier offene Positionen und einen regulären
> V2-Zyklus mit je vier Einstands-/Fristdatenproblemen bei null technischen
> Positionsfehlern. Käufe/historische Kaufwährungen sind vierfach vorhanden;
> Produktende und Zahlung werden getrennt geführt. Drei Kursrouten fehlen,
> die bestätigte JPMorgan-Route liefert keinen verwendbaren Bid. Die
> folgenden Aussagen zu noch unzugänglichem PC-Readback oder fehlender
> Installationsbestätigung dokumentieren den Stand vom 20./21.11. und sind
> insoweit überholt. Quellen-/Kostenrecherche und Regelverträge behalten
> ihre dort genannten Daten und Grenzen. Der aktuelle Aufgabenstatus steht
> ausschließlich im [Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

## Ergebnis und Geltungsbereich

**Der belegte Engpass ist die Eignung der Daten am Regelverbraucher.** Der
V2-Runner funktioniert im zuletzt dokumentierten PC-Betrieb, beide
Prüfpfade melden aber weiterhin Datenprobleme. Ein konkreter
Produktdatumsfehler ist mit v1.5.52 repariert und ausgeliefert; die dadurch
tatsächlich wieder auswertbaren Depotpositionen sind noch nicht belegt.
Die strenge B04/B57/B58-Versorgung hat weiterhin keinen qualifizierten
Produktivpfad. B06 und vollständige Produktfristen benötigen zusätzlich
historische beziehungsweise produktspezifische Fakten und noch offene
Verarbeitung beim bestehenden fachlichen Owner.

Empfohlen wird eine **kombinierte Versorgung**: vorhandene Ausführungen und
belegte historische Währungen wiederverwenden, Produkt-/Listingfehler beim
zuständigen Owner korrigieren, Emittentenoriginale und offizielle Kalender
verknüpfen und einen geeigneten Bid-/Statusfeed anhand der tatsächlichen
Depotlistings qualifizieren. ARIVA MDS und die ergänzend untersuchte
TAI-PAN-API sind konkrete Beschaffungskandidaten; eine vollständige Eignung
ist nicht nachgewiesen.
Die gesondert freigegebene V2-Indikation bleibt bis dahin ein begrenzter
Teilumfang. Regeln werden nicht an ein verfügbares Feld angepasst.

**Ergänzung nach den Webseitenbeispielen des Nutzers:** Geeignete öffentliche
Webquellen sind ausdrücklich vorrangig zu prüfen. Ein kostenpflichtiger Feed
ist keine Vorbedingung. Die [Mehrquellenprüfung](#webquellen-mehrfachpruefung)
präzisiert den vorhandenen Anschluss, Zugangshürden und die vorgeschlagene,
noch nicht freigegebene Auswahlrichtlinie.

Die [Quellen-, Rechte- und Kostenübersicht für neun Emittenten](ISSUER_QUOTE_SOURCE_ACCESS_2026-11-20.md)
ergänzt konkrete direkte Portale, kostenlose Dateidienste und einen
veröffentlichten API-Komponentenpreis. Sie beantwortet ausdrücklich, welche
B58-Bedingungen auch bei angenommener Bid-Aktualisierungszeit offenbleiben.

Dieser Bericht enthält Quellenbefunde und technische Nachweise, **keine
zweite Aufgabenstatusliste**. Arbeitsstatus und genau ein nächster Auftrag
stehen im [Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).
Der Auftrag lautet zunächst auf eine vollständige, lesende Diagnose des
aktuellen Depots; der unten beschriebene Beschaffungsweg setzt deren
Instrument-/Listingabgleich voraus.

### Nachweisstufen

| Kennzeichnung | Aussage |
| --- | --- |
| Angebot / Dokumentation | Primärquelle nennt Daten oder Schnittstelle; keine Lieferung an das Depot bewiesen. |
| Praktisch geprüft | Ein konkreter Originalabruf beziehungsweise ein vorhandener Betriebsbeleg wurde geprüft; seine Zeit und Reichweite gelten. |
| Integriert | Codepfad und Consumer sind in dem unten gebundenen Main enthalten; Tests bleiben getrennte Nachweise. |
| Im Betrieb beobachtet | Datierter PC-Beleg zum tatsächlich installierten Stand; weder heutiger Zustand noch andere Positionen daraus ableitbar. |
| Nicht zugänglich / nicht belegt | Fehlender Nachweis; kein erfundener Nullwert und kein Beweis, dass Daten auf dem PC fehlen. |

## 1. Main, Software und Betriebsbelege

| Gegenstand | Verifizierter Stand | Bedeutung |
| --- | --- | --- |
| Aktueller Main / vollständiger Checkout | `6c0f9160b91bee4c6c45849c9c47d4c4b5a3bf56`, Tree `45ce0a3d95549e2946f0fc437e9c3109ca951d5a`; Merge [#369](https://github.com/burckhju/trading-workspace/pull/369) am 20.11.2026, 15:01:45 MEZ | Git-Remote erneut gelesen. Gegenüber der folgenden Produktbasis ausschließlich fünf Dokumente geändert; kein neuer PC-Datenbeleg. |
| Produktbasis / Softwaretag | `c7db441de36297a98d47cdf28c64b4e5d9994692`, Tree `e0c62e8ce82aa8bf1d4b9f247ae05f0b12675b22`; `v1.5.52` zeigt auf diesen Commit, aktuelles `VERSION=1.5.52` | Merge #368 am 19.11.2026, 20:16:53 MEZ. Quellcode und Monitoringvertrag gegenüber aktuellem Main unverändert; Veröffentlichung ist kein Installationsbeleg. |
| CI der Produktbasis | [Backend 44596683043](https://github.com/burckhju/trading-workspace/actions/runs/44596683043), [Frontend 44596682863](https://github.com/burckhju/trading-workspace/actions/runs/44596682863), [E2E 44596682853](https://github.com/burckhju/trading-workspace/actions/runs/44596682853): `completed/success`, identischer Produkt-SHA `c7db441…` | API-Metadaten gelesen. Testzahlen in #368 sind dortige Nachweise; keine Aussage über neue Main-CI allein aus diesen älteren Runs. Anwendungssuiten für diesen Dokumentationsauftrag nicht erneut ausgeführt. |
| Publisher | [44601501673](https://github.com/burckhju/trading-workspace/actions/runs/44601501673), beendet 19.11.2026, 20:45:03 MEZ, `success` | Tagbezug zusätzlich unabhängig geprüft. |
| Ausgangsbefund #367 | Nutzer-Audit vom 19.11.2026, **18:13:12 MEZ**; Zyklus **18:06:42–18:07:17 MEZ**, 35,307 s; v1.5.51 / `254f0bbd52ab42e0120d381e915dc96c1118796c`, Schema `20261118_0060`, V2 aktiv | Je sechs Bewertungen und sechs Datenprobleme bei Einstand und Frist; je null technische Positionsfehler. Sechs Frist-Datenwarnungen sind keine sechs Fristauslöser. |
| Neuerer vollständiger PC-Befund | [Dritter Betriebsnachtrag](../planning/PRODUCT_BACKLOG.md#dritter-betriebsnachtrag-19112026--belegte-v2-datumsursache-und-v1552) und [PR #368](https://github.com/burckhju/trading-workspace/pull/368), 19.11.2026, **ohne veröffentlichte genaue Diagnoseuhrzeit** | Vier offene Positionen, vier Einstands- und vier Fristdatenprobleme; aktive V2 unter v1.5.51; die technische Fehlerfreiheit des früheren Sechserzyklus ist gesondert belegt. Die Zahl sechs ist damit kein aktueller Inventarnenner. Die Ursache der Bestandsänderung wird nicht geraten. |
| Nach v1.5.52 | Kein neuerer PC-Installations-/Abdeckungsbeleg in den zugänglichen Quellen | Update und automatische Neuinterpretation vorhandener Originale sind implementiert; Erfolg je Position bleibt offen. |
| Offene Dokumentationsarbeit | [PR #369](https://github.com/burckhju/trading-workspace/pull/369), Head `84451218e525673de8728e075758b14082329e8d`, noch offen | Nicht mit Main oder einer neuen PC-Abnahme gleichgesetzt; keine fremde Branchänderung. |

Primärbelege zum Betrieb: [#367](https://github.com/burckhju/trading-workspace/pull/367)
und [#368](https://github.com/burckhju/trading-workspace/pull/368).
Ihre Beschreibungen und vorhandenen Kommentarlisten wurden erneut gelesen.
Die Rohdiagnose des PCs, private Depotidentitäten und Zugangsdaten standen
dieser Untersuchung nicht zur Verfügung. Die veröffentlichten Zusammenfassungen
werden als solche ausgewertet. Es gibt hier keinen Zugang zur produktiven
Datenbank und keine neue reale Positionsabnahme.

## 2. Fachlicher Datenvertrag

### Verbindlichkeit der Anforderungen

1. [PROJECT](../foundation/PROJECT.md) und die unveränderte
   [Roadmap vom 22.07.2026](../foundation/archive/ROADMAP_2026-07-22.md)
   verlangen den durchgängigen Ablauf von Marktanalyse über tatsächliche
   Ausführungen und Positionsmanagement bis Nachbeobachtung, Lernen und
   Performance. Quelle, Zeitbezug, Datenqualität und reproduzierbare Ergebnisse
   sind Querschnittsanforderungen. Die [heutige Roadmap](../foundation/ROADMAP.md)
   und [Traceability](../foundation/TRACEABILITY.md) erhalten diese Zusagen.
2. Die später bestätigte `HEBELTRADER_CONFIRMED_BASELINE/1.0.0` umfasst
   57 bestätigte Regeln und den ausdrücklichen Ausschluss B08. Historische
   Bestätigung: 14.09.2026, 04:53:07 UTC; Benachrichtigungen, keine Orders.
   Maßgeblich ist der [Integrationsvertrag, Herkunft und B01–B58](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#1-prüfstand-und-herkunft).
   Der historische Gesamtumfang ist kein Implementierungsnachweis.
3. B04/B57 mit B58-Eingängen ist ein eigener implementierter Teilumfang.
   Die ausdrücklich freigegebenen Alternativen V1 (17.11.) und V2 (18.11.)
   verwenden eigene Qualitätsgrenzen. Sie ersetzen die strengeren Regeln nicht.
   B07 bleibt separate Einstiegsprüfung; B08 bleibt ausgeschlossen.
   Forschung aus #197 und die ATR-Projektion `DYNAMIC_STOP_V1` sind keine
   automatische Ergänzung des bestätigten B06.

Die folgenden Anforderungen sind aus geltenden Quellen abgeleitet. Die
Verweise enthalten die normative Regel und die spätere implementierte
Präzisierung. Es wird kein neuer Datenvertrag freigegeben.

| Regel / Zweck | Pflichtdaten, Qualität und maßgeblicher Zeitpunkt | Quelle / bestehender Owner |
| --- | --- | --- |
| Tatsächlicher Bestand, Einstand, B10/B13/B26/B51–54 | Effektive BUY/SELLs samt Korrekturketten, tatsächlicher Menge und Preis, Restmenge und Restkosten. Gewichteter Bruttoeinstand aus noch beitragenden Käufen; keine Gebühren-/FIFO-Behauptung. Frühester gültiger BUY bestimmt den Beginn; Nachkauf/Teilverkauf setzt ihn nicht zurück. Jede beitragende Kaufwährung historisch belegt; heutige Listingwährung ist kein Ersatz. Ereigniszeit, Erfassung und EXACT/DATE_ONLY-Präzision getrennt. | [F207-4](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-4-evidence-read), [historische Währung](../implementation/HISTORICAL_EXECUTION_CURRENCY.md); Trade Position / FT-009/010, `PositionProjector.project_with_trace`. |
| Produkt-/Listingidentität | Gehaltenes Produkt, ISIN/WKN, Basiswert, Emittent, Terms-ID/-Version, Listing/Venue, Providerroute, Währung und Preisachse. Quellenlisting und persönlich gewähltes Exitlisting dürfen verschieden sein, brauchen aber jeweils exakte Bindung. Produktpreis nicht mit Basiswertmarke vergleichen. | [Produktmaßstab](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-product-price-scale); Product / Market, Mapping bei Market Data. |
| Strenger historischer Preismaßstab, B04/B57/B50 | `WARRANT`, `CURRENCY_PER_WARRANT`, Währung, `scale_id`, Quellenversion, Original und endliches Gültigkeitsintervall mit Offset. Sämtliche noch beitragenden BUYs und aktueller Original-BID müssen vom selben unveränderten Maßstab gedeckt sein; bei DATE_ONLY der gesamte mögliche Kauftag. Anpassung/Rücknahme sperrt. Gleiche ISIN oder Ratio beweist keine Kontinuität. | [F207-3-Maßstabsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-product-price-scale), `ProductPriceScaleEvidenceReader`. |
| B04/B57: Original-BID | Tatsächlicher Geldkurs des gehaltenen Listings, eigene unveränderte BID-Seitenzeit, Zeittext/Quellenfeld/Offset, Original- und Empfangsbeleg. Alter **0 bis einschließlich 900 Sekunden**; 901 Sekunden, Zukunft, Last/Close/Ask/Mid oder bloße Empfangsfrische unzulässig. Providerdelay separat ausweisen. B04: BID **unter** Bruttoeinstand; B57: nur geeigneter neuer BID **größer/gleich** Einstand beendet die Verlustepisode. | [Original-BID](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-original-bid-evidence), [B04/B57](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b04-b57-loss-monitoring-v1); Market Data → Monitoring. |
| B58: Marktstatus | Exaktes Instrument/Listing/Quelle, Originalstatus, eigene Originalstatuszeit und belegte zeitliche Bedeutung. OPEN muss die tatsächliche Auswertungszeit belegen. Vorhanden ist ausschließlich `OBSERVED_AT_INSTANT`; ein früheres OPEN gilt nicht fort. **Keine Status-TTL** aus der 900-s-BID-Grenze ableiten. Negative/preislose Meldungen, Konflikte, Versorgungslücken und Recovery separat erhalten. | [Originalstatus](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-market-status-evidence), [Statusjournal](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-independent-status-observations); Market Data / `B58SourceRegistry`. |
| B04/B58: Sitzungen | Fest gebundenes historisches Basiswertlisting, Kalender-ID/-Version/Deckung, IANA-Zeitzone, explizite SESSION/CLOSED/UNKNOWN-Tage und Öffnungs-/Schlussintervalle einschließlich Feiertagen, Sonderzeiten, DST und Pausen. Kauftag = 0; **mindestens 20 danach abgeschlossene Basiswertsitzungen bereits zur BID-Zeit**. Produktsitzung zu Kurszeit und Auswertung separat prüfen; Öffnung inklusiv, Schluss exklusiv. Kurslücke ist kein Feiertag; Kalender kein Instrumentstatus. | [Sitzungsevidenz](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-session-evidence), B13–15/B58; Market Data. |
| B05/B16–20: Frist | Verifiziertes Produktende, letzter Handelstag des persönlich gewählten Exitlistings, Produktkalender und **instrumentbezogene Schlussgrenze**. Maßgeblich `min(Produktende, letzter Handelstag)`; Zahlungstag unzulässig. Termintag ausgeschlossen; 20. vorherige Produktsitzung = Ausstiegstag, vorherige Sitzungsöffnung = spätestens Vorwarnung. 21 vorherige belegte Sitzungen für beide Termine. B20 verlangt tatsächliche Ausführung vor Produktschluss; offene Order genügt nicht. | [Fristrechner](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b05-documented-deadline-calculation), [V2-Produktfristen](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#documented-product-deadline-review-v1); Product + Market Data → Monitoring. |
| Ursprüngliche Ziele / B01–03/B09/B11/B21/B55 | Konkrete historische Quellen-/Planversion, Z1/Z2 auf passender Achse/Währung/Skala, Richtung, Originalausgabe und dauerhafter Treffer nach Einstieg. Abgeschlossene High-Daten können Zieltreffer belegen; Tageskerzen beweisen keine Intraday-Reihenfolge. Ursprüngliche Einstiegsgruppe samt Fill-IDs für 50%-Z1-Orientierung; echte zugeordnete SELLs separat. Zieltreffer ist keine Ausführung. | [Zielhistorie](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-2-target-history), [Historienqualifikation](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-history-qualification); Learning-/Trade-Owner, Monitoring. |
| B06 / persönlicher Basiswerteinstieg | Je noch beitragendem Produkt-BUY belegter **letzter geeigneter Basiswert-TRADE zum oder vor Kauf**, historische Listing-/Währungs-/Skalenbindung, Originalzeit/Präzision und Auswahlbeleg. Mit verbleibenden Mengen gewichten; fehlende Käufe nicht aus dem Nenner entfernen. Heute, Close und Produktkaufpreis ersetzen keinen damaligen Basiswert-TRADE. Kein künstliches 60-s-Maximalalter nachträglich einführen. | B12/B28–30/B54, [F207-4](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-4-evidence-read); Trade Position liest `underlying_trades`, Market Data müsste die historischen Originale beschaffen. |
| B06 / Schutz- und Verlaufshistorie | Ursprüngliches Z1, dauerhaft belegter Z1-Treffer, Z1-Tag = 0, spätestens nach **20 Basiswertsitzungen** Vorschlag `max(gültiger vergleichbarer Schutzboden, persönlicher Basiswerteinstieg, 0,8 × ursprüngliches Z1)`. Höheren Schutz erhalten; Bekanntgabezeit, spätere Berührung und Korrekturen belegen. Keine rückwirkende Stopgültigkeit oder erfundene Reihenfolge. Kein Z1-SELL als Voraussetzung. | B06/B14/B22/B44–49; [F207-2](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-2), Trade Management / Monitoring. Datenbeschaffung allein implementiert diese Restlogik nicht. |

Die aktuelle Zielhistorien-Implementierung qualifiziert aufsteigende
CALL-Konstellationen. PUT und unbekannte Richtung bleiben mit Sperrgründen
ausgewiesen; die High-/Zielprüfung wird nicht auf beliebige Positionen
übertragen ([Zielhistorienvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-2-target-history)).

### V2 ist eine eigene Aussage

| V2-Eingang | Zulässige Aussage | Bleibende Grenze |
| --- | --- | --- |
| Original-BID | Eigene Seitenzeit, höchstens 900 s; indikative Einstandsprüfung | Keine positive B58-Statusqualifikation. |
| Vorhandenes gettex-/Stuttgart-Delayed-BID | Gemeinsame `source_quote_at`, höchstens **1.800 s**; Sitzungsstand zur Quellenzeit | Keine eigene BID-Seitenzeit; nominell 15 Minuten Delay garantiert kein Alter ≤900 s. |
| Registrierte Emittentenindikation | BID und feste Identität; **300 s seit erfolgreichem Empfang** | Originalkursalter bleibt unbekannt; Empfang nicht zur Originalzeit erklären. |
| Aktuelles KID | Dokumentierte aktuelle Einheit und Referenzmarkt | `CURRENT_UNIT_HISTORY_ASSUMED` / `CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED`; kein strenger historischer Vertrag. Widerspruch/Rücknahme sperrt den schwächeren Ersatz. |
| DATE_ONLY-Kauf | Konservativ späterer möglicher Kalenderbeginn | Keine erfundene Ausführungsuhrzeit; strenge Mehrdeutigkeit bleibt. |
| XSTU-Tageskalender 2026 | Datumserinnerung `scheduled_on` | `B05_PARTIAL`, `qualified_b05=false`, `B20_UNVERIFIED`; keine Uhrzeit und keine Abdeckung 2027. |

Quellen: [V1](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-entry-review-v1),
[V2-Belege](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-readiness-v2)
und [V2-Regel](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-rule-v2).
Ein belegter 20-Sitzungen-Reminder kann trotz fehlendem Preis bestehen.
Der Preisvergleich benötigt seinen eigenen qualifizierten Zähler von mindestens
20 Sitzungen. Reminder, Verlust und Datenproblem sind getrennte Ergebnisse.
Erholung benötigt mindestens die stärkste während der Episode verwendete
Preis-/Maßstabsqualität; eine Datenlücke schließt keine Verlustepisode.

## 3. Tatsächliche Datenkette und konkrete Fehlerklassen

### Nachgewiesene Ursachen im letzten PC-Befund

| Befund | Klasse | Was ist belegt? | Geeignete Behebung / Grenze |
| --- | --- | --- | --- |
| `PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH` durch Datumsrollen | Verarbeitung | Vorhandenes `maturity_date` war ein im Original belegter Zahlungstag, der alte Parser verglich mit früherem Bewertungs-/Ausübungsende. Originalbytes waren vorhanden. | v1.5.52 trennt Rollen mit `current-product-document-v2`, erhält erwartete/späteste Zahlung als solche und reinterpretiert intakte alte Originale vor Netzbackoff. Consumer-Erfolg erst durch neuen PC-Readback. |
| Kalenderabruf HTTP 403 | Zugriff / Beschaffung | Gespeicherter Fehler des Stuttgarter Abrufs laut jüngster vollständiger Diagnose. Kein Beweis fehlender Börsentage oder eines geschlossenen Instruments. | Erlaubten Zugriff klären oder einmalig exakt qualifiziertes privates 2026-Original über vorhandenen Preview-/Importweg verwenden; 2027 und Produktschluss bleiben offen. |
| Tatsächlich falsche Basiswertidentität | Mapping / Stammdaten | Als eigenständige verbleibende Sperre dokumentiert; Datumsfix darf sie nicht übergehen. | Originalprodukt mit Basiswertidentität abgleichen und beim zuständigen Product-/Market-Owner korrigieren; abhängige Bindungen anschließend neu prüfen. Keine Neubuchung des Kaufs. |
| Fehlende Kursrouten / Stückmaßstäbe | Quellen- und/oder Bindungslücke | Als Rest genannt; die veröffentlichte Zusammenfassung ordnet sie nicht einzelnen Positionen zu. | Je Position Originallieferung und gespeicherte Route unterscheiden; Quelle qualifizieren beziehungsweise passenden Originalmaßstab beschaffen. |
| Exitwahl / letzter Handelstag / Folgekalender / Produktschluss | Fachentscheidung und Quelldaten | Restanforderungen ausdrücklich offen, keine genaue Verteilung je Position veröffentlicht. | Persönliches Exitlisting festlegen; Listingterminoriginal und vollständige Kalender-/Sonderzeitbelege importieren; instrumentbezogenen Schluss separat belegen. |

Quelle für alle fünf Zeilen:
[v1.5.52-Liefernotiz](../releases/V1.5.52-PRODUCT-DATE-SEMANTICS.md),
[#368](https://github.com/burckhju/trading-workspace/pull/368) und der
gebundene [Main-Backlognachtrag](https://github.com/burckhju/trading-workspace/blob/c7db441de36297a98d47cdf28c64b4e5d9994692/docs/planning/PRODUCT_BACKLOG.md#dritter-betriebsnachtrag-19112026--belegte-v2-datumsursache-und-v1552).
Die Daten erlauben **keine** erfundene Zuordnung „Position 1 hat Fehler X“.

### Abdeckung, die sich tatsächlich behaupten lässt

| Grundgesamtheit / Regel | Vollständig | Teilweise / nicht ausreichend | Unbekannt |
| --- | --- | --- | --- |
| Sechs Positionen im ersten V2-Zyklus vom 19.11., 18:06 MEZ | Keine vollständig geeignete V2-Preis-/Fristversorgung belegt | 6/6 Einstands- und 6/6 Fristdatenprobleme; technische Fehler 0 je Pfad | Einzelgründe fehlen im Performance-Audit. |
| Vier offene Positionen der späteren vollständigen Diagnose vom 19.11. | Keine vollständige V2-Abdeckung belegt | 4/4 Einstands- und 4/4 Fristdatenprobleme; wirtschaftlicher Bestand und Originale werden verarbeitet | Vollständige private Einzelmatrix nicht zugänglich; Reminder und einzelne vorhandene Fakten können trotzdem belegt sein. |
| Strenge B04/B57/B58 im geprüften Main | **Kein qualifizierter Produktionsquellenpfad** | Vorhandene Original-/Kalender-/Statusreader und Episodenlogik; Quelle allein fehlt nicht als einzige mögliche Sperre | Heutige persönliche Währungs-/Skalen-/Listingabdeckung ohne PC-Readback nicht quantifizierbar. |
| B06 / vollständiger B05/B20 | Kein Gesamtbetriebsnachweis | Zielhistorie beziehungsweise Fristrechner vorhanden; historische Schutzbelege, vollständiger Fristvertrag und/oder Verarbeitung offen | Konkrete aktuelle Belegabdeckung je Position. |
| Heutiges Depot / v1.5.52 nach Update | Nicht festgestellt | Keine Zahl aus dem historischen Vierer-/Sechserbestand fortschreiben | Aktuelle Inventur, installierter Stand und Gründe werden im nächsten Auftrag erhoben. |

Ein Datenproblemzähler beweist keine vollständige Unbrauchbarkeit aller
Einzelfakten. Umgekehrt beweisen ein befülltes KID, eine erfolgreiche
Beschaffung oder sechs technisch erfolgreiche Schleifendurchläufe keine
geeignete Regelversorgung.

### Kette bis zum tatsächlichen Verbraucher

Alle Codebelege dieser Tabelle beziehen sich auf den oben genannten Main.
Die Pfade sind verlinkt; Zeilenbereiche bezeichnen diesen Prüfstand.

| Quelle → Verarbeitung → Speicherung → Verbraucher | Tatsächlicher Codebefund und Qualitätsgrenze | Einzelbeleg |
| --- | --- | --- |
| Bestätigte Ausführungen → effektive Historie/Korrekturen → Projektor → Bewertungsbasis → B04/V2 | `basis_id` bindet wirtschaftliche Fakten und historische Währungsbelege. Unbekannte/gemischte Kaufwährung bleibt UNKNOWN/MIXED. Maßstab prüft verbleibende BUY-Beiträge; Währungsqualifikation des bestehenden Owners umfasst alle effektiven BUYs. Ohne konkrete Diagnose daraus keinen zusätzlichen Depotfehler behaupten. | [valuation_basis.py](../../backend/app/features/trade_position/service/valuation_basis.py), Z.123–239; [indicative_entry_inputs.py](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py), Z.247–296. |
| Produkt/Listing → verifiziertes Mapping → versionierte Quellenauswahl → Adapter | Identitätshash bindet Workspace, Produkt-/Listing-/Mappingversion, Venue, ISIN/WKN und Währung. Null geeignete Routen = `NO_VERIFIED_QUOTE_SOURCE`, mehrere = `AMBIGUOUS_SOURCE`. Bestehende Auswahl bleibt bei Ausfall stabil; Reconcile kann nach neuer verifizierter Zuordnung einen Nachfolger erzeugen. | [quote_identity.py](../../backend/app/features/market_data/persistence/quote_identity.py), Z.34–154; [Quellenauswahlvertrag](../technical/AUTOMATIC_POSITION_SOURCE_SELECTION_V1.md); [quote_sources.py](../../backend/app/features/position_monitoring/service/quote_sources.py), Z.87–123. |
| Adapter → RetainedProvider → last-success, Statusjournal und Samples | Produktidentität wird vor Abruf und unter Listinglock erneut geprüft; Status wird vor Preisvalidierung gespeichert. Ein Preisfehler darf ein negatives Statusereignis nicht verlieren. Erhaltener alter Erfolg ist retained/refresh_error, kein neuer erfolgreicher Kurs. | [retained_quotes.py](../../backend/app/features/market_data/service/retained_quotes.py), Z.59–236; [status_observations.py](../../backend/app/features/market_data/service/status_observations.py), Z.33–125. |
| last-success → passiver SavedQuote-Reader | Liest ausschließlich letzten gespeicherten Erfolg der aktuellen SELECTED-Route. Gründe u.a. `NO_CONFIRMED_SAVED_QUOTE_SOURCE`, `NO_SAVED_QUOTE_FOR_CURRENT_ROUTE`, `SAVED_QUOTE_ROUTE_IDENTITY_CHANGED`, `SAVED_QUOTE_HELD_INSTRUMENT_MISMATCH`, `SAVED_QUOTE_QUALITY_INVALID`. `LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER`: allein daraus ist der letzte Abrufversuch nicht bekannt. Speicherzeit fehlt im last-success-Store; Empfangszeit ist kein Ersatz. | [risk_read.py](../../backend/app/features/market_data/service/risk_read.py), Z.62–222; [risk_evidence.py](../../backend/app/features/market_data/domain/risk_evidence.py), Z.27–64. |
| Samples → historische Anzeige | Erste Beobachtung je Route und Fünf-Minuten-UTC-Slot, auch Fehler. Späterer Erfolg kann last-success ändern, ohne den ersten Slotwert zu ersetzen. Kein historischer Backfill, vollständiger Tick-/Bidverlauf oder synchroner Basiswertpreis. | [quote_history.py](../../backend/app/features/market_data/service/quote_history.py), Z.29–43, 74–210. |
| SavedQuote + Währung/Maßstab + Kalender/Status → B04/B57 | Strenger BID-Prüfer akzeptiert derzeit ausschließlich `FRANKFURT_QUOTES / frankfurt-quotes-v1 / bid_at / XFRA` in erlaubten Monitoring-Modi. Das ist ein Transportvertrag, keine reale Lieferantenqualifikation. `QUALIFIED_B58_PATHS=()`; Statussemantik nur punktbezogen. Ein neuer Feed benötigt Adapter **und** qualifizierte zeitliche Verarbeitung, nicht nur Konfiguration oder passendes JSON. | [hebeltrader_original_bid.py](../../backend/app/features/position_monitoring/domain/hebeltrader_original_bid.py), Z.34–97; [loss_inputs](../../backend/app/features/position_monitoring/service/hebeltrader_loss_inputs.py), Z.49–176; [B58-Registry](../../backend/app/features/position_monitoring/service/hebeltrader_b58_sources.py), Z.18–126. |
| Gespeicherte Quote + wirtschaftliche Basis + Originale/Kalender → V2-Entscheidung/Episode | Qualifiziert Original-BID, registrierten Delayed-BID und registrierte Emittentenindikation getrennt. Kein Last-/Ask-Ersatz. Preisvergleich, Review-Erinnerung und Datenproblem laufen getrennt. Spätere negative Statuspunkte und bekannte Versorgungslücke können alten Kurs sperren. | [indicative_entry.py](../../backend/app/features/position_monitoring/domain/indicative_entry.py), Z.59–234; [indicative_entry_inputs.py](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py), Z.168–219, 327–494, 557–575; [Runtime](../../backend/app/features/position_monitoring/service/indicative_entry_runtime.py). |
| Emittenten-KID → Parser → Originalrevision → Product-Read → V2/Frist | Automatische Dokumentrouten: JPMorgan, BNP, Société Générale, UniCredit/HVB. Explizite ISIN/Währung/Stücknotiz/Basiswert und getrennte Datumsrollen erforderlich. Originalbytes/Hash/Termsbindung/Parser-/Empfangs-/Speicherzeit bleiben append-only. `AVAILABLE` im Erwerbsstatus beweist keine Eignung; Consumer nennt z.B. `PRODUCT_REVIEW_UNIT_UNPROVEN`, `PRODUCT_REVIEW_CURRENCY_UNPROVEN`, `PRODUCT_DOCUMENT_UNDERLYING_MISMATCH`. | [product_review_documents.py](../../backend/app/providers/product_review_documents.py), Z.18–55, 112–216; [review_evidence.py](../../backend/app/features/product/service/review_evidence.py), Z.77–239, 273–330. |
| Offizieller Kalender → gebundenes Original/Revision → Sitzungsreader → Zählung/Frist | NYSE endlich 2025–2027, XSTU DAY_ONLY 2026. Identische Originale werden wiederverwendet; abweichender Hash erzeugt `REVIEW_CALENDAR_SOURCE_REVISION_CHANGED`. Automatischer Beschaffungspfad: nach Erfolg 24 h, nach Fehler frühestens 1 h; intakte alte Produktoriginale können vor Backoff lokal neu geparst werden. | [review_acquisition.py](../../backend/app/features/product/service/review_acquisition.py), Z.38–45, 79–170; [review_calendars.py](../../backend/app/features/market_data/service/review_calendars.py), Z.32–44, 121–125, 215–225. |
| Produktende + Listingterminoriginal + persönliche Exitwahl + Kalender → Fristbewertung/Episode | Unabhängig von Bid, Zielen, Einstandswährung und Stückmaßstab. Gründe u.a. `PRODUCT_MATURITY_EVIDENCE_MISSING`, `PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING`, `PRODUCT_EXIT_LISTING_MISSING`, `PRODUCT_LAST_TRADING_DAY_EXIT_VENUE_MISMATCH`. Produktschluss im begrenzten V2-Read weiterhin UNVERIFIED. | [product_deadline_review_inputs.py](../../backend/app/features/position_monitoring/service/product_deadline_review_inputs.py), Z.127–139; [Product-Reader](../../backend/app/features/product/service/review_evidence.py), Z.401–462; [Fristread](../../backend/app/features/position_monitoring/service/product_deadline_review_read.py), Z.25–82, 125–218. |

**Ausfallverhalten ist feldbezogen zu bewerten.** Der automatische Quoteabruf
hat vorhandene Pacing-/Retry-/Cooldownregeln, zwei Warteschlangen und
Positionspriorität; Intervalle sind Mindestpausen nach Jobende, keine
Aktualitätsgarantie. Prozesslokale Jobdiagnose wird nach Neustart neu aufgebaut,
Mappings, Originale und Regelereignisse sind dauerhaft.
[Automatischer Datenbetrieb](../automatic-market-data.md) und die obigen
Consumergrenzen verhindern, dass erhaltene Altdaten allein durch einen
erfolgreich gestarteten Runner frisch werden.

## 4. Beschaffungswege und Szenarien

### Fünf praktisch abgrenzbare Optionen

Aufwand ist eine technische Einschätzung, kein Anbieterangebot.
Die aktuelle private Instrumentliste ist unbekannt; keine Option erhält
eine erfundene Prozent- oder Vollabdeckungszusage.

| Szenario | Erfüllbarer Umfang / Positionsabdeckung | Aufwand, Zugang und Kosten | Dauerbetrieb / verbleibende Grenze | Nachweisstand |
| --- | --- | --- | --- | --- |
| **1. Bestehende Wege vervollständigen**: v1.5.52, richtige Basiswertbindung, zugelassene Routen, vorhandene KIDs, Kalenderoriginal und Exitwahl | Verbesserbare V2-Preis-/Prüfhinweise und begrenzte Fristen. Welche aktuellen Positionen geeignet werden, muss am Verbraucher gemessen werden. | Klein bis mittel; keine neue Providerbestellung. Einmalige belegte Korrekturen/Importe, bei Produkt-/Originaländerungen erneut. | Vorhandener Scheduler/Backoff und Originalerhalt; 403 wird nicht durch häufigeres Wiederholen gelöst. Historische Skala und B58 bleiben offen. | Integriert; alte Datenprobleme beobachtet, Wirkung v1.5.52 noch unbelegt. |
| **2. Offizieller Brokerimport** des tatsächlich verwendeten Brokers; Beispiele comdirect REST oder IBKR Flex | Ausführungs-IDs, BUY/SELL, Menge/Preis, Währung und Zeit können Einstands-/Sitzungs-/Performancegrundlage schließen. Kein Ersatz für Produktbedingungen/Zielgeschichte/B58. | Mittel, Import/Reconciliation. comdirect API ohne Zusatzgebühr; tatsächlicher Broker, sonstige Konto-/Datenkosten und Rechte unbekannt. Einmaliger Backfill, dann inkrementell. | Idempotente Execution-IDs, Korrekturen/Stornos, Vollständigkeit und Token-/Sessionerneuerung nötig. comdirect-TAN-Aufwand für Dauerbetrieb offen. Kein Brokerwechsel vorgeschlagen. | Dokumentiertes Angebot, kein Kontoexport geprüft, nicht integriert. |
| **3. Lizenzierter Vendor-/Börsenfeed**, begrenzte ARIVA- oder TAI-PAN-Probe bei passendem Listing | Potenziell geeignete Quotes/Historien; B58 nur mit zusätzlich belegter Originalstatuszeit/-semantik und vollständigen restlichen Inputs. Tatsächliche ISIN-/Listingdeckung offen. | Mittel bis hoch. ARIVA: individuelles Angebot, kein Privatpreis. TAI-PAN: 49 EUR/Monat API plus 29 EUR/Monat Global veröffentlicht; Gesamtpreis, USt./Nutzerklasse, Speicherung und mögliche Zusatzpakete offen. [Kostenprüfung](ISSUER_QUOTE_SOURCE_ACCESS_2026-11-20.md). | Automatische Auth-Erneuerung, begrenzter Backoff, Original-/Statusjournal, Lücken-/Replay-/Reconnectvertrag und fachliche Wiederqualifikation. Aktuelles ARIVA-Schema reicht nicht; TAI-PAN-Statusfeld nicht belegt. | ARIVA-Angebot und Schema praktisch geprüft; TAI-PAN-Angebot/SDK dokumentiert. Echte Depotlieferung/Integration/Betrieb offen. |
| **4. Kombination — Hauptempfehlung**: vorhandene Executions, nötige Brokerergänzungen, qualifizierter Bid-/Statusfeed, Emittentenoriginale, offizielle Kalender und historische Regelbelege | Tragfähiger Gesamtweg zu B04/B57/B58 und B05/B20; später B06 mit zusätzlicher Historie und offener Verarbeitung. Einzelkomponenten qualifizieren sich nicht gegenseitig. | Höherer einmaliger Anschlussaufwand, danach wenig regelmäßige Handarbeit; Kosten des tatsächlich benötigten Vendorpakets plus gezielte Ausnahmen. | Bestehende Owner erhalten; Fristpfad bleibt bei Quoteausfall verwendbar. Historische Archive und manuelle Entscheidungen können punktuell nötig bleiben. | Bausteine integriert; vollständige Versorgung des aktuellen Depots nicht belegt. |
| **5. Begrenzter Übergang**: vorhandene Emittentenindikationen/gettex-/Stuttgart-Delayed, KIDs, Originalkalender und dokumentierte Zuordnungen | Nur gesondertes V2, 20-Sitzungen-Erinnerung und B05_PARTIAL/B20_UNVERIFIED. Keine volle B58-/B06-Aussage. | Geringere unmittelbare Beschaffungskosten; Website-/Dateifehler, Produktausnahmen und Kalenderpflege bleiben Aufwand. Keine täglichen manuellen Kurs-/OPEN-Eingaben. | Nur innerhalb Quellenalter, unveränderter Bindungen und Kalenderdeckung. XSTU-Paket endet 2026; benötigte Folgejahre können Fristprüfung schon davor sperren. | Adapter/Regeln integriert; aktuelle brauchbare Positionszahl offen. |

### Neue ARIVA-Prüfung: dokumentierter Fortschritt, unveränderte Kernlücke

Ein direkter anonymer GET der
[Original-OpenAPI](https://mds.ariva-services.de/swagger-ui/openapi.yml)
lieferte am **20.11.2026, 12:50:22.630081 UTC / 13:50:22.630081 MEZ**
HTTP 200, **465.140 Bytes**, Version **0.6.26**, SHA256
`0ec994559799e96b0012ba3cc6b9309a0bdb07c79500a3b396b932f1f1a3f1ea`.
Hash und Version der erhaltenen Datei wurden gegengeprüft.
Die frühere Version 0.6.25 im [Prüfbericht vom 17.11.](B58_ARIVA_ACQUISITION_2026-11-17.md)
bleibt ein datierter historischer Beleg.

Erneut geprüft: `Status`, `Marketstate`, `MarketstateWithId`,
`IdFieldsListing`, `MarketstateQuote`, `BidAskHistoryData` sowie
History-/Feedpfade. **Status und Hülle enthalten weiterhin keine eigene
Originalstatuszeit.** `bid.datetime` ist vorhanden, seine unveränderte
BID-Seitenbedeutung bei reiner ASK-/Last-Änderung ist aber nicht belegt.
REALTIME/DELAYED/EOD, Bid-/Ask-Historien und OHLC sind dokumentiert;
tatsächlicher Historienbeginn, Lücken, Rechte und Anpassungsbasis je
Depotlisting fehlen. Feed-ContinuationToken belegt keine vollständige
Status-Recovery.

Die [Deutsche Börse](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/spot-markets/B-rse-Frankfurt-Certificates-and-Warrants-1341024)
nennt für Frankfurt Certificates and Warrants beste Geld-/Briefkurse;
Xetra Core enthält diese Produktdaten ohne diese Kurse.
[ARIVA ist offiziell als Vendor aufgeführt](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/vendorlist/ARIVA.DE-AG-1739678).
Laut [ARIVA-FAQ](https://ariva.ag/f-a-q/) sind kleine Pakete, Testzugänge und
historische Intraday-Daten möglich; Preise richten sich nach Umfang und
Nutzung, viele Services starten mit zwölf Monaten Laufzeit.
Die bis auf Weiteres kostenlose Börseninformation beweist keinen kostenlosen
Vendorzugang. Private automatisierte Verwendung, Speicherung, Abrufgrenzen,
SLA und konkreter Preis müssen für dieses Vorhaben bestätigt werden.

Vorhandener Evaluationsweg:
`python -m app.tools.probe_ariva_b58` erstellt nur einen Plan;
`--fetch` benötigt einen berechtigten Evaluationsclient und die gesondert
geklärten Rechte. Der [bestehende Prüfer](../../backend/app/tools/probe_ariva_b58.py)
nutzt tatsächliche Positionsbindungen und erhält Originalantworten privat.
Er wurde hier mangels PC-Zugang/Client nicht gegen Depotinstrumente ausgeführt.
Kein authentifizierter Marketstate-Payload wurde geprüft, kein Anbieter
kontaktiert. XSC bleibt Quellencode; MIC, Listingvariante und Währung sind
gegen die wirkliche Position abzugleichen.

### Broker, Originale und Kosten: konkrete Primärbelege

Alle folgenden Quellen wurden am 20.11.2026 gelesen. Es handelt sich um
Angebots-/Dokumentationsbelege, soweit kein Originalabruf ausdrücklich genannt ist.

| Zugang / Primärquelle | Belastbarer Nutzen | Konkrete Grenze |
| --- | --- | --- |
| [comdirect REST API](https://www.comdirect.de/cms/kontakt-zugaenge-api.html) | Depotübersicht/PostBox, Registrierung mit ClientCredentials und Session-TAN; API ohne zusätzliche Gebühr. | Offizielle Seite schließt eine Wertpapierkurs-Schnittstelle ausdrücklich aus; keine Sandbox. Gelesener offizieller Suchindextext, direkter Webreader HTTP 401. Keine reale Accountprobe, Historienvollständigkeit und unbeaufsichtigte Sessionerneuerung offen. |
| [IBKR Flex-Exportfelder](https://www.ibkrguides.com/reportingreference/reportguide/tradesfq.htm) | Currency, ISIN, Execution-/Trade-IDs, Trade Date/Time, Exchange, Quantity, Trade Price, Buy/Sell. Executiondetail statt Summenzeile verwenden. | Nur tatsächliche IBKR-Ausführungen; Übertragungsbestände, Korrekturen, Exportzeitzone und Historienumfang real prüfen. Broker-Cost-Basis/PnL kann Provisionen enthalten; für den vorhandenen Bruttoowner originale Mengen/Preise übernehmen. |
| [IBKR Flex-Token](https://www.interactivebrokers.com/docs/web-api/flex-web-service/client-portal-configuration/enable-and-create-access-token), [Requestgrenzen](https://www.interactivebrokers.com/docs/web-api/flex-web-service/using-flex-web-service/generate-the-report) | Token sechs Stunden bis ein Jahr, optionale IP-Bindung; Generierung/Abruf getrennt, höchstens ein Generierungsrequest/s und zehn/min. | Zugangsdauer ist keine Historienabdeckung. Keine tägliche technische Tokenpflege als Lösung einplanen; sichere Erneuerung vor Ablauf nötig. |
| [IBKR Datenrechte](https://www.interactivebrokers.com/support/faq/content/receive-real-time-data-tws-1491287373), [BidAsk-Ticks](https://www.interactivebrokers.com/docs/tws-api/doc/md/live-ticks), [historische Ticks](https://www.interactivebrokers.com/docs/tws-api/doc/md/historical-ticks) | Separat berechtigte Marktdaten und dokumentierte Tickabfrage. Historische Ticks laut Dokumentation bis drei Jahre, instrument-/berechtigungsabhängig. | Gemeinsamer BidAsk-Tickzeitpunkt ist kein eigener Statuszeitpunkt; tatsächliche deutsche Warrant-/Listingdeckung ungeprüft. Kein allgemeines B58-Versprechen aus Brokerkursen. |
| [Stuttgart-Marktdaten](https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/zugang-zu-boersendaten/marktdaten/), [Vertragsdokumente](https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/zugang-zu-boersendaten/vertragsdokumente/) | Realtime-/Delayed-/EOD-Angebot auch für strukturierte Produkte; Vendorweg für den privaten Einzelfall prüfen. | SID-/Institutionenzugang ist kein zugesagtes Privat-API-Paket. Feldzeit-/Statusvertrag und tatsächliche Produktabdeckung fehlen. |
| [Stuttgart-Datennutzungspreise ab 01.09.2026, S.12](https://www.boerse-stuttgart.de/media/fizi51pu/preisliste-datennutzung_gueltig-ab-192026-31.pdf), [Anbindung separat](https://www.boerse-stuttgart.de/media/5zppwrgy/preisliste-anbindung_gueltig-ab-192026-87.pdf) | Publizierter Non-Display-Tarif für ein Device: 973,42 EUR/Monat gesamt bzw. 700,86 EUR Pretrade, netto; Anbindung kann hinzukommen. | **Kein bestätigter Privatpreis und keine Feststellung, dass dieser Tarif für dieses Projekt erforderlich ist.** Einordnung/Privatangebot fehlen. Günstige Displaypreise ebenso wenig als Automatenlizenzpreis ansetzen. |
| [gettex Delayed Data](https://www.gettex.de/en/trading/delayed-data/) | Kostenlose MUNC-/MUND-Dateien, 15 Minuten verzögert, UTC, mindestens 24 h Vorhaltung; private Nutzung ohne Weitergabe. Zusätzlich Echtzeitzugang über Dienstleister gegen Servicegebühr auch für Privatpersonen beschrieben. | Kein eigener Instrumentstatus im bereits geprüften CSV-Schema; keine zugesagte Depotdeckung, exakte Dienstleisterkosten oder Originalstatussemantik. Keine neue Zustimmung oder erneuter Dateiabruf in dieser Prüfung. |
| [NYSE/ICE 2025–2027](https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx), [NYSE aktuell](https://www.nyse.com/trade/hours-calendars) | Feiertage und verkürzte Sitzungen; aktuelle Seite bereits 2026–2028. | Vorhandene Implementierung endlich 2025–2027; neue Seite erweitert gespeicherte Abdeckung nicht automatisch. Historische Sondermitteilungen zusätzlich erforderlich. |
| [Stuttgart-Handelszeiten](https://www.boerse-stuttgart.de/de-de/handel/handelszeiten/) | Verlinkter Kalender 2026; individuelle Produktzeiten laut Wertpapierstammdaten. | Keine dort belegte 2027-Erweiterung am Prüftag, kein aktuelles instrumentbezogenes OPEN, kein pauschaler Schluss für alle Produkte. |

**Nicht erneut vertiefte ungeeignete Wege:** Öffentlicher Frankfurt-Endpunkt
liefert in den [datierten Originalproben](B58_SOURCE_QUALIFICATION_2026-11-17.md)
Last/Previous Close, keinen passenden Bid/Status. Die
[aktuelle offizielle Feedmatrix](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Real-time-data-feeds)
führt Frankfurt-Warrants weiterhin nicht unter Cloud Stream;
CEF Core beziehungsweise lizenzierter Vendorzugang sind gesonderte Wege.
Die bereits untersuchten Emittenten-/Aussetzungsbeispiele liefern ebenfalls
keinen vollständigen Statusvertrag. Ihre bekannten öffentlichen Prüf-ISINs
werden **nicht** als heutige Depotpositionen bezeichnet. Ein weiterer
öffentlicher Einzelabruf würde weder Rechte noch die belegte Feldlücke lösen.

<a id="webquellen-mehrfachpruefung"></a>
### Ergänzung: öffentliche Webquellen und Gegenprüfung

Der Nutzer hat zwei Portalansichten unterschiedlicher Emittenten bereitgestellt
und vorgeschlagen, Quellen je Neuanlage zu prüfen sowie die aktuellste oder
zwei übereinstimmende Beobachtungen zu verwenden. Die Ansichten zeigen
Produktidentität, getrennte Geld-/Briefwerte, Währung, Quotegeber und Uhrzeit.
Das ist ein konkreter Ansatz für bessere Versorgung. Eine Depotzugehörigkeit
der Beispiele wird nicht vorausgesetzt; Bilder, private Zuordnungen und
Einzelwerte werden hier nicht veröffentlicht.

Die Recherche am 20.11.2026 bestätigt die Quellenklasse, qualifiziert aber
keinen laufenden Abruf. Gelesene Such-/Webseitenrepräsentationen sind keine
synchronisierten Originalantworten am Consumer. „Heute“, Uhrzeit und
Echtzeitlabel ergeben allein keinen belegten aktuellen UTC-Zeitpunkt.
Kein Portal-API wurde nachgebaut, kein Zugang aktiviert und keine
regelmäßige Abfrage eingerichtet.

| Primärbeleg | Geprüfte Aussage | Konsequenz |
| --- | --- | --- |
| [Onvista: Optionsscheinansicht](https://hilfe.onvista.de/de/welche-kurse-werden-in-der-optionsschein-einzelansicht-dargestellt), [Realtime-Angebot](https://hilfe.onvista.de/de/gibt-es-auf-onvista-realtime-kurse) | Börsen-Bid/Ask und Emittentenquotierungen werden angeboten; die Kursquelle gehört zur Anzeige. | Portal, ursprünglichen Quotegeber und Listing getrennt erfassen. Keine allgemeine Pflicht zur permanenten Quotierung oder belegte OPEN-Geltung daraus ableiten. |
| [Onvista-Bedingungen, Abschnitt 6](https://www.onvista.de/nutzungsbedingungen), [Erläuterung](https://hilfe.onvista.de/de/verstoss-gegen-nutzungsbedingungen) | Automatisierte Portalabfragen benötigen ausdrückliche Einwilligung; die Erläuterung verlangt vorherige schriftliche Zustimmung. | Dauerabruf nur nach passender Freigabe oder über einen anders berechtigten Lieferweg. Private Anzeige belegt diese Zustimmung nicht. Kein Preis für eine solche Erlaubnis festgestellt. |
| [DZ BANK: Herkunft, Zeit und Verzögerung](https://www.dzbank-wertpapiere.de/rechtliche-hinweise) | Mehrere Lieferanten, teilweise verzögerte Daten und teilweise GMT-Zeiten; allgemeine Hinweise qualifizieren nicht jedes einzelne Feld. | Ein genau passendes DZ-Produkt war als Webrepräsentation mit Bid/Ask, Quellname, Zeiten und Dokumentlinks lesbar. Automatischer Zugangsvertrag, genaue Feldzeitsemantik und Statusgeltung ungeprüft. |
| [HSBC-FAQ, Punkte 28–30](https://www.hsbc-zertifikate.de/home/faq/Allgemeines.html) | Kein direkter Anlegerzugriff auf historische Emittentenkurse; Verweis auf Stuttgart. Quotierung kann ausgesetzt und wieder aufgenommen werden. | Aktuelle Anzeige ersetzt keine Historie. Portale mit gemeinsamem Emittenten bleiben gegenüber dessen Ausfall abhängig. Für das konkrete HSBC-Beispiel wurde kein eigener Originalquote unabhängig gelesen; ähnliche Produkte wurden nicht substituiert. |

**Vorhandener Unterbau:** Der Refresh verarbeitet aktive, verifizierte
Mappingrouten getrennt und protokolliert deren Abrufversuche/Beobachtungen
([refresh.py](../../backend/app/features/market_data/service/refresh.py),
Z.630–715). Ein zusätzlicher Runner ist dafür nicht nötig. Unterstützte
Adapter und dynamische JPM-/Morgan-Discovery sind keine Freigabe für jede
beliebige Webseite oder jeden Emittenten.

Der Positionsowner entscheidet bei genau einer geeigneten Route; mehrere
bleiben `AMBIGUOUS_SOURCE`, eine ausgewählte Route bleibt auch bei Fehlern
erhalten ([position_quote_source.py](../../backend/app/features/market_data/service/position_quote_source.py),
Z.45–115, 156–239). Der allgemeine Resolver nimmt den ersten hinreichend
frischen Bid und hat kein Verfahren „neuester aller Bids“ oder „zwei identisch“
([quote_sources.py](../../backend/app/features/position_monitoring/service/quote_sources.py),
Z.87–136, 300–343). Eine URL-Liste schließt diese Auswahllücke nicht.

**Empfohlene Auswahllogik, noch keine beschlossene neue Regel:**

1. Quellenkatalog je Anbieter/Parser/Zugangsrecht hinterlegen. Bei Neuanlage
   unterstützte Quellen asynchron im vorhandenen Scheduler anhand der ISIN
   entdecken und exakt verifizieren. Listing, Währung, Einheit und
   Ursprungslieferant binden; keine Netzprüfung in der Kauftransaktion.
2. Zuerst nach dem jeweiligen Regelvertrag geeignete Kandidaten bestimmen.
   Innerhalb vergleichbarer Qualität und Listingbedeutung nach belegter
   Originalzeit auswählen. Unbekannte Originalzeit bleibt unbekannt;
   zulässige Empfangsfrische einer registrierten V2-Indikation bleibt separat.
3. Eine qualifizierte Hauptquelle kann genügen. Weitere erlaubte Routen als
   Ersatz und Gegenprüfung führen. Wechsel beim bestehenden Auswahlowner
   mit Grund versionieren. Börsen-/Quotegeberwechsel bleiben sichtbar.
4. „Zwei identisch“ ist ein Zusatzmerkmal: gleicher Kurstyp, Produkt,
   Einheit, Währung, Listingbedeutung und vergleichbares Zeitfenster.
   Spiegel desselben Originalfeeds können Transport-/Parserfehler aufdecken,
   beweisen aber keine unabhängige Preisentstehung, Aktualität oder OPEN.
   Verschiedene Plätze/Zeiten können legitime unterschiedliche Bids liefern.
   Keine Mehrheitsentscheidung über die tatsächlich gewählte Kurs-/Exitbörse.
5. Vergleichsfenster, Tick-/Rundungstoleranz, Rangfolge und Konfliktbehandlung
   vor Umsetzung festlegen; hier keine neuen Grenzwerte erfinden. Bei
   ungeklärtem maßgeblichem Konflikt keine sichere Entwarnung ableiten.
   Bestehende V2-Sperren für schwächere/nicht vergleichbare Erholungsbelege
   erhalten ([indicative_recovery.py](../../backend/app/features/position_monitoring/domain/indicative_recovery.py)).
6. Bei jedem regulären Abruf Identität, Zeit und Vollständigkeit prüfen.
   Format-/Zugangsänderungen sichtbar sperren; Wiederanlauf erst mit erneut
   geeigneter Beobachtung. Keine tägliche manuelle Quellenpflege vorsehen.

So kann V2 praktisch verbessert werden. Zwei gleiche Preise liefern keinen
instrumentbezogenen Originalstatus mit gültiger Zeitsemantik für B58.
Historische Kaufwährung, Anpassungen, B06-Basiswerttrades und Fristen bleiben
eigenständige Datenaufgaben. Frühere negative Einzelproben schließen nur
ihre konkret belegten Feldlücken aus, nicht die gesamte Quellenklasse.

Arbeitsstatus und bestehender nächster Diagnoseschnitt bleiben im
[Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt). Vorhandene geeignete,
mehrdeutige und unzugängliche Quellen je tatsächlicher Position getrennt
erfassen. Daraus den kleinsten Adapter-/Auswahlschnitt ableiten; ein bezahltes
Paket nicht vorziehen, wenn ein erlaubter geeigneter Webweg dieselben
benötigten Fakten liefert.

**Nachtrag zur Uhrzeitannahme und den neun Emittenten:** Die Uhr neben einem
Bid ist ein plausibler Aktualisierungshinweis; ihre angenommene Bedeutung
ist getrennt von bestätigter Originalzeit zu erhalten. Selbst unter dieser
Annahme bleiben Datum/Zeitzone und Alter ≤900 s, Produktsitzungen zu Quote
und Auswertung, instrumentbezogenes OPEN zur Auswertung und 20 bereits zur
Bid-Zeit abgeschlossene Basiswertsitzungen erforderlich. Der
[neue Quellenvergleich](ISSUER_QUOTE_SOURCE_ACCESS_2026-11-20.md)
trennt diese B58-Bedingungen von B04-Einstandsbasis, B06 und Produktfristen.
Er belegt gettex nur für BNP/HSBC/UniCredit aus der angefragten Gruppe,
Stuttgart als kostenlosen Dateidownload mit offenem Dauerabrufumfang und
TAI-PAN als kostenpflichtigen Entwicklerkandidaten. Keine Quelle wird ohne
tatsächliche ISIN-/Listingprobe als Vollabdeckung ausgewiesen.

## 5. Fehlende Information → Beschaffung → Owner → Regel

| Wesentliche Lücke | Konkrete Beschaffung / Entscheidung | Bestehende zuständige Komponente und nötiger Anschluss | Dadurch mögliche Prüfung |
| --- | --- | --- | --- |
| Historische Käufe/Verkäufe, Zeit/Währung unvollständig | Tatsächliche Brokerabrechnung/Executionexport; offizieller API-Read nur beim tatsächlich verwendeten Broker. Vorhandene Fakten zuerst abgleichen. | Trade Position / `read_position_execution_basis`, Projektor und historischer Währungsowner; idempotenter Import mit Originalreferenz, Korrektur und Präzision. Kein zweiter Bestand. | Qualifizierter persönlicher Einstand, B04/V2, tatsächlicher Restbestand und Brutto-Performance. |
| Falscher Basiswert / fehlende Quelle / Listingabweichung | Produktoriginal und Börsen-/Brokerlisting mit bestehender Position vergleichen; keine automatische Umwahl eines Exitlistings. | Product / Market Identität, Market Data `ProviderInstrumentMapping` und vorhandener Quellenauswahl-/Reconcile-Owner. | Richtiger Kalender, Kurs und Preisvergleich für betroffene Position. |
| Datumsrollen / aktueller Stückmaßstab | Gespeicherte Originale mit Parser v2 wiederverwenden; fehlende explizite Stücknotiz aus passenden Emittentenbedingungen beschaffen. | Product-Dokumentowner und `ProductDocumentReadinessService`; keine historischen Terms oder Ausführungen aus heutigen Werten überschreiben. | V2-Einstandsvergleich und korrektes Produktende im Fristpfad. |
| Historischer Maßstab / Produktanpassung, B50 | Historische Emittentenbedingungen und Anpassungsmitteilungen für **alle** beitragenden Käufe bis Kurszeit; Faktor und Wirkung belegen. | `ProductPriceScaleEvidenceReader`; verifizierte Anpassungsverarbeitung bleibt zusätzlicher qualifizierter Schnitt. | Strenger B04/B57-Vergleich auf der gehaltenen Produktachse. |
| Basiswertanpassung, B49 | Verifizierte Basiswert-Split-/Skalenevidenz, getrennt von Produktanpassungen; ursprüngliches Z1, persönlichen Basiswerteinstieg, Schutzmarken und Beobachtungen gemeinsam einmalig skalieren. | Market Data liefert Basiswert-Anpassungsbelege; Trade-/Monitoring-Consumer erhalten Originalwerte und wenden nur belegte gemeinsame Faktoren an. | Vergleichbare B02-/B06-Marken; aus dem Basiswertsplit folgt keine automatische Optionsscheinmengen-/Kostenänderung. |
| Original-BID / aktuelle Statusgeltung | Evaluation einer konkreten lizenzierbaren ISIN-/Listinglieferung, vorrangig ARIVA XSC bei tatsächlich passendem XFRA-Listing; bei fehlender Statuszeit zusätzliche originale Lieferung verlangen. | Market Data Original-/Statusjournal, Provideradapter, `assess_original_bid`, `B58SourceRegistry`; dokumentierte Semantik und Recovery implementieren und real qualifizieren. | B04/B57/B58, sobald alle übrigen Positionseingänge geeignet sind. |
| Basiswert- und Produktkalender | Offizielle historische Tage, Sitzungszeiten, Sondermitteilungen und Folgejahre; vorhandene 2026-Datei bei 403 einmalig kontrolliert importieren. | Market Data Session-/Reviewkalenderowner; Bindung, Originalhash, Revision und endliche Abdeckung erhalten. | B04/B06-Sitzungszahl und unabhängige B05-Frist. Kein OPEN-Nachweis. |
| Letzter Handelstag / Exitlisting / Produktschluss | Emittenten-/Listingoriginal plus persönliche Wahl aus vorhandenen Listings; instrumentbezogene Schlusszeit und verkürzte Handelstage belegen. | Product `ProductDeadlineEvidenceReader`, Listingterminimport und Exitwahl; Monitoring `calculate_product_deadline`. | Vollständige B05/B19/B20-Prüfung statt bloßer Datumserinnerung. |
| Basiswert-TRADE je Produktkauf | Historische Trade-Daten des damals gebundenen Basiswertlistings mit Zeitzone, Auflösung und as-of-Auswahl; zurück bis frühestem beitragendem Kauf. | Market Data historische Beschaffung → Trade Position `underlying_trades` / F207-4. Allgemeiner Trade-genauer Beschaffer noch nicht integriert. | Persönlicher Basiswerteinstieg für B02/B06/B54. Ein Broker-Produktfill enthält diesen Marktpreis regelmäßig nicht automatisch. |
| Ziele, Treffer, Schutz-/Bekanntgabehistorie | Bereits akzeptierte Originalquelle/Planversion, qualifizierte OHLC-Historie und tatsächliche Managementereignisse; fehlende Originale gezielt ergänzen. | Learning / Trade Management / vorhandene Target- und Evidence-Reader; restliches F207-2 einschließlich Schutzboden, Z1-Zähler und Bekanntgabe implementieren. | B01–03/B06/B09/B22; Feed allein reicht nicht. |

### Empfehlung und vorbereitete Entscheidungen

Die Kombination verwendet je Fakt seinen vorhandenen Owner. Sie ermöglicht,
kursunabhängige Fristen und geeignete V2-Positionen schon zu verbessern,
während die strengere Versorgung separat qualifiziert wird.

Eine Feedbeschaffung ist erst reviewfähig, wenn tatsächliche ISINs,
Listings, Währungen, Zeitraum ab frühestem relevantem Kauf und die gewünschten
Originalfelder feststehen. Das vorbereitete
[ARIVA-Anfragepaket](B58_ARIVA_ACQUISITION_2026-11-17.md#3-kleinster-evaluationsumfang-und-unversandter-anfrageentwurf)
bleibt unversendet. Erforderliche Entscheidung: begrenzter Evaluationszugang
mit bestätigten Nutzungsrechten, Kosten und Lieferumfang. API-Key, ein
erreichbares Schema oder ein automatischer Runner genügen nicht.

Kann die eigene Statuszeit mit ihrer Geltung nicht geliefert werden, ist der
präzise Rest **zusätzliche Originalstatusquelle beziehungsweise anderer
qualifizierter Zugang**. Eine dauerhafte Beschränkung auf Indikation wäre
eine ausdrückliche neue fachliche Entscheidung. Sie gilt nicht still als
Erfüllung der ursprünglichen B58-Anforderung.

**Begrenzte Übergangslösung:** freigegebenes V2 mit höchstens 30 Minuten alten
gemeinsamen Quellenzeiten beziehungsweise ausdrücklich nur empfangsfrischen
Emittentenindikationen, qualifizierten aktuellen Dokumenten und belegten
Kalendertagen. Die Aussage lautet „indikative Einstandsprüfung /
Prüferinnerung / Produktdatumserinnerung“, keine vollständige
Hebeltrader-Überwachung. Aufhebung der Grenze nur nach neuem Nachweis;
Kalenderende, Quellenalter und ungelöste Identitätsfehler sperren jeweils
den betroffenen Teil. Einmalige Dokumente/Exitwahl sind vertretbar;
tägliche manuelle OPEN-Bestätigungen oder Tokenpflege sind kein tragfähiger
Betrieb. Der konkrete aktuelle Historienqualifikationsweg kann dagegen bei
neuen Zeilen wiederholte menschliche Prüfung verlangen; dieser Aufwand
muss vor B06-Dauerbetrieb beseitigt oder ausdrücklich getragen werden.

## 6. Weitere ursprüngliche Projektziele

| Ursprünglicher Zweck | Erforderliche Daten / vorhandener Umfang | Verbleibende Lücke oder Entscheidung vor Beschaffung |
| --- | --- | --- |
| M2/M3/M9 Marktanalyse | Echte Listing-/Markt-/Sektorreferenz, persistierte qualifizierte OHLC/Adjusted-Close-Historie, Quellflags und Herkunft. `EOD_TREND_MOMENTUM/1.0.1`: standardmäßig min. **200** nutzbare Beobachtungen, SMA20/50/200, Momentum20/60/120, Volatilität20, Range52, höchstens **7 Kalendertage** alt; Parameter je Run gebunden. EODHD-Bestandspfad importiert zunächst bis 400 Kalendertage, später mit sieben Tagen Überlappung. | 400 Kalendertage garantieren keine 200 gültigen Werte oder Kalenderdeckung. Reale Mappings, Berechtigungen und Historien je Instrument prüfen. Scanneruniversum/Marktbreite-Grundgesamtheit und Berechnung teilweise noch fachlich offen; Benchmarkdaten ersetzen keine Marktbreite. |
| M4/M9 Produktauswahl/Produktscore | APPROVED-Planversion, Produkt-/Terms-Version zur Bewertung, Richtung/Laufzeit/Lifecycle, Listing, Bid/Ask und Qualität; tatsächliches Suchuniversum. | Freigegebener numerischer Score und Schwellen für Spread, Liquidität, Omega/Greeks/IV usw. sind im FT-008-V1 nicht vollständig definiert. Zuerst Formel/Universum/Umgang mit fehlenden Daten beschließen, dann passendes Paket bestellen. Historischer V1-Ausschluss beseitigt die ursprüngliche Zusage nicht. |
| M6 Nachbeobachtung / Exit Review | Effektiver Vollverkauf, gepinntes Underlyinglisting, ursprüngliche Plan-/Managementmarken; danach **20 abgeschlossene EOD-Beobachtungen**, Exitdatum ausgeschlossen; keine Interpolation. | Underlying-Verlauf ist keine virtuelle Optionsscheinrendite. Weitergehender Vergleich braucht definierten Produktpreis-/Liquiditäts-/Settlementvertrag und historische Produktdaten. Enge V1-Nachbeobachtung nicht als vollständige ursprüngliche virtuelle Weiterführung ausgeben. |
| M7 Journal / Lernen | Konkrete Ausführungs-, Plan-, Review-, Evidence- und Lesson-Versionen; Currentness und menschliche qualitative Bewertung. | Allgemeine Entscheidungsqualitäts-/Scoredefinition bleibt eigenständig; PnL ersetzt keine Bewertung der Entscheidung. |
| M8 Performance | Effektive BUY/SELLs, Korrekturen, historische Währung, Restkosten, echte Abschlüsse und getrennte SELL-/Abschlusskohorten. Bestehende EUR-Bruttoberichte und definierte vollständige Kohortenstatistik wiederverwenden. | Netto, Gebühren, Steuern, Cashflows, FX, Equity, Drawdown/Rendite-/Risikoquotienten benötigen einen beschlossenen Berechnungs-/Periodenvertrag. Keine Nullgebühren oder heutigen FX-Kurse zur Rekonstruktion. Unvollständige Kohorten nicht hochrechnen. |

Belege:
[FT-006](../features/FT-006_MARKET_ANALYSIS.md),
[Analyseparameter](../../backend/app/features/analysis/domain/models.py),
[automatischer Datenimport](../automatic-market-data.md),
[FT-008-Regelkatalog](../implementation/SPRINT_8_FT008_RULE_CATALOG.md),
[FT-011-Baseline](../implementation/SPRINT_11_FT011_SPECIFICATION_BASELINE.md),
[Nachbeobachtungssemantik](../decisions/ADR-S11-003-OBSERVATION-PERSISTENCE-AND-COUNTERFACTUAL-METRICS.md),
[Bruttostatistik](../implementation/CLOSED_TRADE_STATISTICS_V1.md),
[Währung/Perioden](../decisions/ADR-S10-008-EXECUTION-CURRENCY-AND-PERIOD-REALIZED-GROSS.md),
[Abschlusskohorte](../decisions/ADR-S10-009-CLOSED-TRADE-COHORT-AND-GROSS-RESULT.md).
Die ursprünglichen Zusagen und offenen fachlichen Definitionen werden damit
erhalten; Depotüberwachung ist die Priorität dieses Auftrags.

## 7. Kleinste fehlende Diagnose und Abnahme

**Fortschreibung 22.11.2026:** Der vollständige vorbereitete Export wurde
ausgeführt, bereitgestellt und ausgewertet. Die unten erhaltene allgemeine
Zugangslücke ist damit geschlossen. Konkrete verbleibende Ergänzung ist
der [P02-Journal-/Assessmentinput-Read](DEPOT_DATA_READBACK_2026-11-22.md#engste-noch-fehlende-passive-ergänzung)
beim vorhandenen Owner; aktuelle KID-/Parser-/Importdetails bleiben als
gesonderte fachliche Nachweisgrenzen sichtbar. Kein weiterer identischer
Gesamtcollector ist für die erkannte Gap-Informationslücke geeignet.

**Fortsetzung 21.11.2026:** Der nächste Auftrag wurde gegen Main
`febeb922c0f337029baa7f9d792c37f9f72ba02b` / `VERSION=1.5.53` begonnen.
Die relevanten Backendreader sind unverändert; ein neuer privater PC-Zugang
oder tatsächlicher Verbraucherbefund liegt nicht vor. Der frühere
Bash-Ablauf ist durch den [einzelnen Diagnosecollector](../../scripts/collect-depot-data-supply.py)
ersetzt: gezielte Installationsreads ohne den Nebenwirkungen erzeugenden
Launcherstatus, ausdrücklicher READ-ONLY-Schemaread und derselbe fachliche
GET-Collector. Das Paket bleibt außerhalb des Checkouts. Der
[Backlog-Nachtrag](../planning/PRODUCT_BACKLOG.md#depotdiagnose-20261121)
trennt diese konkrete Vorbereitung von noch ausstehender PC-Ausführung
und verbesserter Datenabdeckung. Die Marktquellen-/Kostenbefunde oben bleiben
an ihren Recherchetag 20.11.2026 gebunden.

Die konkrete lesende Vorgehensweise steht im
[Betriebsnachtrag zur vollständigen Depotdiagnose](../technical/ISSUER_MONITORING_OPERATIONS.md#lesende-depot-datenversorgungsdiagnose).
Sie benötigt genau ein privates Diagnosepaket aus der vorhandenen Installation.
Aktuellen Softwarestand, vollständigen offenen Bestand, Runtime vor/nach dem
Lesen und die vorhandenen passiven Evidenz-/V2-Reader zusammen erfassen.
Keine neuen Bewertungen, Quote-Refreshes, Zustimmungen oder Nachrichten
auslösen.

Das Paket muss für jede aktuelle Position V2-Einstand, V2-Frist, strenge
B04/B57/B58-Eingänge und B06-Evidenz getrennt mit Gründen ausweisen.
Fehlendes Quellfeld, falsche Identität, Import-/Parserfehler, Konfiguration,
bewusst unqualifizierte Semantik und fehlender Zugriff sind verschiedene
Ursachen. Ein technisch fehlgeschlagener GET ist kein fachliches
`MISSING`. Änderungen während der Sammlung kennzeichnen den Befund als
über mehrere Stände gelesen; keinen global atomaren Snapshot behaupten.

Die Veröffentlichung enthält nur aggregierte Zähler, zulässige Reason-Codes
und technische Ursachen. Rohantworten, IDs, ISIN-Positionsbindungen, Mengen,
Einstände, Dokumentinhalte und Zugangsdaten bleiben privat.
Zusammen mit dem Paket fehlt für eine eventuelle Brokeranbindung lediglich
die Angabe des tatsächlich verwendeten Brokers und eines bereits erlaubten
lesenden Zugangs; **keine Zugangsdaten im Chat oder Repository**.
Persönliche Exitlistingentscheidungen werden erst anhand der festgestellten
fehlenden Bindungen konkret vorgelegt.

Erfolgskriterien und der einzige aktuelle nächste Arbeitsauftrag stehen
ausschließlich im [Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).
Der aktuelle Befund wird dadurch von historischen 6/6- oder 4/4-Zählern
zu einer vollständigen, positionsbezogenen Ursachenmatrix verbessert.

## 8. Prüfung dieser Dokumentation

Gelesen wurden die verbindlichen Repository-Anweisungen in README und
[Development Guide](../technical/DEVELOPMENT_GUIDE.md), die geforderten
Grundlagen, der vollständige relevante Monitoringvertrag, Produkt-/Marktdaten-/
Kalender-/Betriebsunterlagen und die zugehörigen Consumer.
Quellenanalysen, neue öffentliche Primärquellenabrufe, frühere Originalproben,
synthetische Tests und PC-Berichte sind jeweils gekennzeichnet.

Der ursprüngliche Schnitt vom 20.11.2026 ändert Dokumentation. Keine wirtschaftlichen Daten,
Produktivkonfiguration, Providerfreigaben, Regeln, Migrationen oder Tags werden
geändert. Externe Originaldokumente und private Rohdaten werden nicht
eingecheckt. Die historische Roadmap und die markierte historische
Traceability bleiben unverändert.

Lokale Prüfung des vorausgehenden Dokumentationsstands: `git diff --check`, 104 neue beziehungsweise
geänderte relative Dateiverweise einschließlich Ankern, geschlossene
Codeblöcke/Details, `bash -n` und Python-Syntax des Diagnose-Snippets
bestanden. Die archivierte Roadmap ist byteidentisch
(Git-Blob `919ed7570580b1d883a409f864ed15747fbfda3e`); die bisherige
Traceability einschließlich historischem Abschnitt blieb byteidentisch
unter dem additiven neuen Verweis erhalten. Der nächste-Auftrag-Anker
ist eindeutig. Diese Prüfungen und die unabhängige fachliche/technische
Gegenprüfung sind kein ausgeführter PC-Readback.

Die ergänzende Quellen-/Kostenprüfung wurde gegen Main `6c0f916…`
fortgeschrieben. Die zwischenzeitlich integrierte Konsolidierung aus #369
ist erhalten; deren neue Nachweise sind von der historischen Traceability
getrennt. Alle relativen Verweise einschließlich Ankern in den acht gegenüber
Main geänderten Dokumenten, Codeblock-/Details-Abschlüsse, Konfliktfreiheit
und Whitespace wurden erneut erfolgreich geprüft. Die fachliche
Gegenprüfung bestätigt Preis-/Rechtegrenzen und die Trennung von B58/B06;
der gettex-Bedingungslink wurde dabei auf den spezifischen Dateivertrag
präzisiert. Neue Anwendungstests sind für diesen reinen Dokumentationsschnitt
nicht ausgeführt worden.

Zusätzlich wurde die Antwortprüfung der Vorlage isoliert gegen die tatsächlichen
Indicative-Report-Dataclassdefinitionen geprüft: eine vollständige Antwort mit
`latest_assessment=null` bleibt zulässig; ein unvollständiges HTTP-200-Objekt
und eine Lesezeit ohne Offset werden abgewiesen; HTTP 404 bleibt ein
Diagnosefehler. Dabei wurden weder HTTP noch DB oder Provider verwendet.
Der vollständige App-Import war hier mangels SQLAlchemy nicht ausführbar;
Imports und Response-Verträge wurden statisch gegengeprüft. Die Anleitung
validiert gegen die vorhandenen DTOs der installierten Anwendung.

### Qualifikation des eigenständigen Collectors am 21.11.2026

Die Fortsetzung ergänzt den [einzelnen Collector](../../scripts/collect-depot-data-supply.py)
und [19 isolierte Tests](../../tests/unit/backend/test_collect_depot_data_supply.py).
Ausgeführt mit `python -B -m unittest discover -s tests/unit/backend -p
test_collect_depot_data_supply.py -v`: alle 19 Tests erfolgreich. Die
kontrollierten Ersatzprozesse prüfen die zulässigen Git-/Dockeroperationen,
Installations-/Image-/Containerbindung, geänderte Bestände, Schemafehler,
fehlende B06-Antworten und private Dateirechte samt Fehlerarchiv. Die
Schema-Ersatzengine belegt SELECT in READ-ONLY-Transaktion, Rollback und
Freigabe der Verbindung im Erfolgs- und Fehlerfall; sie ist kein Zugriff
auf PostgreSQL oder den Nutzerbestand.

Black 26.1.0 und Ruff 0.15.1 bestehen für beide neuen Pythondateien; der
Host wird ausdrücklich mit Ruff-Ziel Python 3.10 geprüft. Zusätzlich
besteht `ast.parse(feature_version=(3, 10))`; ein Regressionstest simuliert
die älteren Grenzen des Zeitparsers für Docker-Zeitstempel mit neun
Nachkommastellen und `Z`. Eine echte Python-3.10-Laufzeit wurde nicht
ausgeführt. Die Hostabhängigkeiten bleiben auf die Standardbibliothek
begrenzt. Der bisherige fachliche GET-Payload ist vor/nach Formatierung
byteidentisch (SHA256 und Länge im Betriebsnachtrag); der neue
Schema-Payload umfasst 1.928 Bytes, SHA256
`7aba0ec505ed0c1bebbf190faa8c09c888bb1d78a8c3a22db2b2d4c1602f783d`.

Die gezielte Dokumentprüfung umfasst die relativen Links einschließlich
Ankern der acht gegenüber Main geänderten Dokumente, geschlossene
Codeblöcke/Details, Konfliktfreiheit und `git diff --check`. Die
archivierte Roadmap bleibt byteidentisch. Kein lokaler Test verbindet
sich mit Docker, der Anwendung, PostgreSQL oder einer Marktquelle.
Ein Gesamtanwendungstest und eine PC-Ausführung sind nicht Teil dieses
Helfernachweises. Der Abnahmebedarf aus dem Backlog bleibt offen.
