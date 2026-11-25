# Emittentenquellen, Abrufrechte, Kosten und B58 — 20.11.2026

**Spätere praktische Ergänzung vom 24.11.:** Der
[Quellenkandidatenread und die gettex-Dateiprobe](DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md)
belegen einen passenden EUR/MUND-Bid für P01 in einer vollständig geprüften
offiziellen Originaldatei. gettex-Angebot und private Downloadbedingungen
wurden erneut gelesen. Das ist konkrete historische Produktdeckung;
Listing/Mapping, Preiseinheit und frischer PC-Verbraucherinput bleiben offen.
Die rund 657 MB große Einzeldatei macht Bandbreite/Taktung zu einer eigenen
Betriebsbedingung. P03/P04 fehlen nur in diesem Fenster; keine allgemeine
Nichtabdeckung und keine vollständige B58-Qualifikation abgeleitet.
Die [P01-Originalprüfung von 21:07 Uhr](DEPOT_SOURCE_COVERAGE_READBACK_2026-11-24.md#p01-originaleinheit)
klärt zusätzlich die fehlende Einheit: Sie steht nicht im bytegleichen KID,
ein Parserfix ist unbegründet. Das tatsächlich aktuell verlinkte gettex-Regelwerk
liefert eine ergänzende Quote-Konvention; ein gesonderter aktueller
Listing-Einheitenbeleg und sein
[Product-/V2-Anschluss](P01_LISTING_UNIT_IMPLEMENTATION_2026-11-24.md) sind
in PR #370 implementiert. Die am 24.11. noch fehlenden drei Regel-PDFs sind
am 25.11. als Nutzeruploads bereitgestellt und zusammen mit dem BSW-Original
[inhaltlich und technisch qualifiziert](GETTEX_LISTING_UNIT_ORIGINALS_2026-11-25.md).
Das feste Register enthält genau dieses Originalpaket. Das schließt die
Regeldokumentlücke, noch nicht die konkrete P01-Listing-/Mapping-/Verbraucherkette.
Die nachfolgende Neun-Emittenten- und Tarifübersicht behält ihren Prüfstand
vom 20.11.; andere Angebote wurden dadurch nicht neu verifiziert.

## Ergebnis und Prüfgrenze

Für alle neun angefragten Emittentengruppen gibt es konkrete öffentliche
Produktquellen. Mehrere bieten kostenlose Anzeigen oder Exporte an.
**Ein geeigneter kostenloser Dauerfeed für alle neun Gruppen ist damit noch
nicht belegt.** gettex dokumentiert kostenlose maschinenlesbare Dateien für
einen engeren Emittentenkreis. TAI-PAN dokumentiert eine kostenpflichtige
Entwicklerschnittstelle mit einem breiten Produktangebot. Für strenges B58
ist bei keinem hier untersuchten Zugang eine vollständige Versorgung des
tatsächlichen Depots nachgewiesen.

Prüfdatum: **20.11.2026**. Erneut gelesener Main:
`6c0f9160b91bee4c6c45849c9c47d4c4b5a3bf56` (Merge #369), weiterhin
`VERSION=1.5.52`. Gegenüber dem Produktcommit
`c7db441de36297a98d47cdf28c64b4e5d9994692` ändern sich ausschließlich fünf
Dokumente; die unten genannten Consumer und Verträge sind unverändert.
[PR #369](https://github.com/burckhju/trading-workspace/pull/369) enthält
keinen neueren PC-Datenbeleg. Die vollständige Betriebs-/Anforderungsanalyse
steht im [Datenversorgungsnachweis](DEPOT_DATA_SUPPLY_2026-11-20.md).

Diese Untersuchung umfasst öffentliche Primärunterlagen, gelesene
Webseitenrepräsentationen und vorhandenen Code. Ein Suchindex, eine
HTML-Ansicht, eine dokumentierte Schnittstelle und eine echte Lieferung
am Regelverbraucher sind verschiedene Nachweise. Keine aktuelle private
Positionsliste oder synchronisierte Liveantwort war verfügbar. Es wurden
keine Konten, Anbieterzustimmungen, Bestellungen, regelmäßigen Abrufe oder
neuen Providerfreigaben ausgelöst. Preise sind veröffentlichte Angaben,
keine eingeholten verbindlichen Angebote.

**Leseschlüssel:** „0 EUR“ steht nur bei einem ausdrücklich kostenlosen
Angebot. „Unbekannt“ bedeutet weder kostenlos noch verboten. Eine erlaubte
manuelle Exportfunktion bleibt nutzbar; sie beweist nicht automatisch
unbegrenztes Polling, dauerhafte Archivierung oder Weiterverteilung.
Die nachstehenden Rechtebefunde geben Anbieterbedingungen wieder und
ersetzen keine abweichende vorhandene Einzelvereinbarung.

## 1. Direkte Quellen für die neun Emittenten

| Emittent / offizieller Zugang | Konkret belegtes Angebot | Automatisierter privater Abruf und Kosten | Grenze des Nachweises |
| --- | --- | --- | --- |
| **DZ BANK** — [Wertpapierportal](https://www.dzbank-wertpapiere.de/) | Geld/Brief, Produktdaten und Originaldokumente; [Produktliste mit CSV-/Excel-Links](https://www.dzbank-wertpapiere.de/product/list/index/underlyingCategory/2). | [Bedingungen](https://www.dzbank-wertpapiere.de/rechtliche-hinweise) gestatten private nichtkommerzielle Nutzung in gesetzlichen Grenzen. Unterstützter Dauerabruf, Frequenz und Feedpreis **unbekannt**. | Exportlink gelesen; im Webreader nur Seitengerüst, keine CSV-Payload geprüft. Kein generelles Automationsverbot aus fehlender API-Dokumentation abgeleitet. |
| **BNP Paribas** — [Derivateportal](https://derivate.bnpparibas.com/) | [Trader’s Box](https://derivate.bnpparibas.com/service/traders-box-app/) ausdrücklich **kostenlos**; Produktseiten und Exportindiz. Separat [Cortex DataHub](https://developers.cib.bnpparibas.com/api-docs/overview-cortex-datahub), REST/JSON. | Die kostenlose App ist kein externer Datenfeed. [Portalbedingungen](https://derivate.bnpparibas.com/nutzungsbedingungen/) nennen Datenrechte; DataHub benötigt Onboarding. Retail-API-Preis **unbekannt**. | DataHub-Angebot dokumentiert, aber Privatkundenzugang und deutsche Optionsscheinabdeckung nicht belegt. Kostenlose [Entwicklerregistrierung](https://developers.cib.bnpparibas.com/terms-of-use) belegt keine kostenlosen Produktionsdaten. |
| **HSBC** — [Zertifikateportal](https://www.hsbc-zertifikate.de/) | Die offizielle [Watchlist-Anleitung vom März 2019](https://www.hsbc-zertifikate.de/pdfs/produktbeschreibungen/watchlist_anleitung.pdf) nennt kostenlose Pushkurse und CSV/PDF-Export. | [Bedingungen](https://www.hsbc-zertifikate.de/home/rechtlichehinweise.html) stellen die Vervielfältigung von Informationen/Daten unter vorherige Zustimmung. Kein veröffentlichter passender Privat-Feedtarif gefunden. | Historischer Exportbeleg, heutige Exportfunktion ohne Anmeldung ungeprüft. Laut [FAQ](https://www.hsbc-zertifikate.de/home/faq/Allgemeines.html) kein direkter Anlegerzugriff auf historische Emittentenkurse. |
| **JPMorgan** — [Zertifikateportal](https://www.jpmorgan-zertifikate.de/) | Öffentliche Produktansicht mit getrenntem Geld/Brief, EUR, Produktkalender und Originaldokumenten tatsächlich im Webreader gelesen. Stream-/Discoveryadapter im Repository vorhanden. | [Bedingungen](https://www.jpmorgan-zertifikate.de/nutzungsbedingungen/) verlangen Websitezustimmung und schränken Datenkopie/Caching ein. Passender privater Automations-/Speichervertrag und Preis **unbekannt**. | Beispielanzeige enthält Uhrzeit ohne zugeordnetes Produktkursdatum/Offset. Bestehende technische Verbindung oder Betreiberzustimmung ist kein Beleg umfassender Datenrechte. |
| **UniCredit/HVB** — [onemarkets](https://www.onemarkets.de/de.html) | [Trading Desk](https://www.onemarkets.de/tradingdesk-info) ausdrücklich **kostenlos**. [Watchlist](https://www.onemarkets.de/de/tools/watchlist.html) erlaubt Excel-Export zur Analyse außerhalb der Plattform. | Konkreter manueller Exportweg belegt. Unbeaufsichtigter Quoteabruf, Speicherumfang und Feedpreis **unbekannt**; [allgemeine Bedingungen](https://www.onemarkets.de/nutzungsbedingungen) zusätzlich beachten. | Kein Quote-API-Schema geprüft. Ein täglicher manueller Export wäre laufender Aufwand. Ein KID-Abruf ist bereits implementiert, kein eigener UniCredit-Quoteadapter. |
| **UBS** — [KeyInvest Deutschland](https://keyinvest-de.ubs.com/) | Produktsuche und indexierte Produkt-/Downloadfunktionen; direkter Webreader liefert JS-Gerüst. | [UBS-Bedingungen](https://www.ubs.com/global/de/legal/disclaimer.html) verlangen schriftliche Genehmigung für systematischen Abruf zum Aufbau einer Sammlung/Datenbank. Passende Privatkonditionen **unbekannt**. | [Portalzusatzbedingungen](https://keyinvest-de.ubs.com/disclaimer) gesondert abgleichen. Indextext „Historische Daten (CSV)“ steht teilweise beim PRIIP-RIY-Bereich und beweist keine historische Bid-Datei. |
| **Vontobel** — [Markets Deutschland](https://markets.vontobel.com/de-de) | [Kostenlose Informationen](https://markets.vontobel.com/de-de/hilfe-kontakt), Produktseiten und Originale. [Bedingungen](https://markets.vontobel.com/de-de/nutzungsbedingungen) erlauben ausdrücklich private nichtkommerzielle Downloads/Kopien. | Kein veröffentlichter Tarif oder unterstützter Vertrag für fortlaufende private Kursautomation gefunden. **Kein pauschales Verbot** behauptet; Umfang/Frequenz offen. | Deutsche [CSV-Angebote](https://markets.vontobel.com/de-de/systematische-internalisierung) betreffen RTS-27-Berichte; [Gesamtprodukt-CSV](https://markets.vontobel.com/de-ch/produktdownload) liegt im Schweizer Portal. Nicht als deutscher Livefeed ausgeben. |
| **SG EFF / SG Effekten** — [SG-Zertifikate](https://www.sg-zertifikate.de/) | Produktquellen und [Realtime-Pushangebot](https://www.sg-zertifikate.de/wissen/wissenswertes/faq-allgemein) dokumentiert. SG Effekten gehört laut [offiziellem Abschluss](https://www.sg-zertifikate.de/contentMgmt/media/d3pmwk45/konzernbilanz-der-societe-generale-effekten-gmbh-zum-31122024.pdf) zur SG-Gruppe. | [Rechtliche Hinweise, S.2](https://www.sg-zertifikate.de/contentmgmt/media/4cgadl23/legal_information_de.pdf): schriftlicher Genehmigungsvorbehalt einschließlich Caching; persönliche Ausnahme für Papierkopien. Privater Quote-API-Preis **unbekannt**. | [SG Markets Structured Products](https://sp.sgmarkets.com/public/en) richtet sich an institutionelle/professionelle Kunden. Kein belegter kostenloser privater Ersatz. Direkte Portalreads teilweise 503; keine Umgehung. |
| **MS / Morgan Stanley** — [Zertifikateportal](https://zertifikate.morganstanley.com/) | [Produktfinder](https://zertifikate.morganstanley.com/produktfinder) mit Geld/Brief und Excel-Export; vorhandener Repo-Webstream. | Der Finder verlangt schriftliche Zustimmung für Kopie/Weitergabe. Die separaten [Developer-Bedingungen](https://developer.morganstanley.com/terms) setzen Vertragszugang/Freigaben voraus. Passender privater Feedpreis **unbekannt**. | Excel-Funktion gelesen, Datei nicht geprüft. Streamschema und interne `provider_call_cost=0` sind kein kostenloser Liefervertrag. Keine Originalstatusqualifikation. |

Die in Portalbedingungen genannten Produkt-, Transaktions- oder Spreadkosten
sind keine Preise für Datenautomation. Institutionelle APIs bei BNP,
[JPM DataQuery](https://www.jpmorgan.com/markets/dataquery),
[UBS Neo](https://www.ubs.com/global/en/investment-bank/neo.html), SG oder MS
belegen ohne passenden Daten-/Kundenvertrag keine Retailversorgung.

### Welche Zeit- und Statusfelder sind tatsächlich belegt?

DZ-Ansichten zeigen beschriftete Geld-/Briefzeiten; die allgemeinen
Herkunftshinweise nennen teilweise GMT und Verzögerung. JPM-Ansichten
belegen Zeittexte, aber keine vollständige Originalzeit. Die schon
integrierten JPM-/MS-Indikationsadapter erhalten ihre Zeittexte und lassen
Originaldatum/Zeitzone beziehungsweise Status ausdrücklich unbekannt.
Vontobels Adapter liest einen gemeinsamen `price.latestTimestamp` und
`tradingHours.isOpen`; beide sind bislang nicht als Original-Bid-Seitenzeit
und instrumentbezogener Status mit eigener Statuszeit qualifiziert.

Codebelege:
[JPM-Adapter](../../backend/app/providers/jpmorgan/adapter.py),
[MS-Adapter](../../backend/app/providers/morganstanley/adapter.py),
[Vontobel-Adapter](../../backend/app/providers/vontobel_markets/adapter.py),
[Quote-Runtime](../../backend/app/features/position_monitoring/service/quote_runtime.py).
Die Namen tatsächlicher Klassen/Felder, nicht ihre bloße Übersetzung in
„aktuell“ oder „offen“, entscheiden über den Verbraucheranschluss.

**Bedingter Mappingbefund für SG:**
[product_review_documents.py](../../backend/app/providers/product_review_documents.py)
erkennt `societegenerale` und `sgeffekten`. Der wörtliche Kurzname `SG EFF`
wird zu `sgeff` und trifft diese KID-Route nicht. Nur wenn genau dieser
Name tatsächlich als Emittentenstammsatz verwendet wird, besteht diese
Aliaslücke. Ein realer PC-Fehler wird daraus nicht behauptet; der
Produktdokumentpfad ist außerdem kein Kursfeed.

## 2. Gemeinsame Quellen und veröffentlichte Kosten

| Quelle | Dokumentierter Umfang und Preis | Automatisierung / Integration | Grenze für das Depot und B58 |
| --- | --- | --- | --- |
| **gettex File-Service** | [Pretrade CSV.gz](https://www.gettex.de/handel/delayed-data/pretrade-data/), MUND/MUNC, **0 EUR**, höchstens 15 Minuten verzögert, UTC, mindestens 24 Stunden verfügbar. | Offiziell bereitgestellte, maschinenlesbare Dateien; [Bedingungen](https://www.gettex.de/handel/delayed-data/) für private natürliche Personen, keine Weiterverteilung. Vorhandenen Delayed-Adapter verwenden; keine unbegrenzten Abrufrechte behaupten. | [FAQ](https://www.gettex.de/ueber-gettex/faqs) nennt von den neun angefragten Gruppen nur **BNP, HSBC und UniCredit**. Konkrete ISIN/Listings prüfen. Gemeinsame Quellenzeit und fehlende Statusgeltung reichen nicht für B58; Transport kann Alter über 900 s erhöhen. |
| **Börse Stuttgart MiFIR** | [Kostenfreier Download](https://www.boerse-stuttgart.de/media/lfpd4xcs/verffentlichung-und-abruf-von-vor-und-nachhandelsdaten.pdf) verzögerter Vor-/Nachhandelsdaten, JSON.gz, 24 Stunden. [Emittentenverzeichnis](https://www.boerse-stuttgart.de/de-de/service/emittenten/) führt alle neun Gruppen. | [Dateizugang](https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/mifir-ii-delayed-data/) belegt mehr als Anzeige; unbeaufsichtigtes Polling/Archivieren bleibt wegen [Website-AGB](https://www.boerse-stuttgart.de/de-de/legal/agb-und-disclaimer/) und Disclaimer konkret zu klären. | XSTU und tatsächliche Produktlistings separat prüfen; nicht mit XSTP/XSTF ersetzen. Kostenloser Download ist belegt, weder private Dauerlizenz noch passende Preis-/Statuslieferung. Verzeichnis ist kein aktueller ISIN-Vollabdeckungsbeleg. |
| **TAI-PAN .NET-API / Lenz + Partner** | [API](https://www.tai-pan.de/tai-pan-dotnet-api/) **49 EUR/Monat** plus Global **29 EUR/Monat**; rechnerisch 78 EUR/Monat aus den veröffentlichten Komponenten. [Global](https://www.tai-pan.de/datenfeed-global/) bewirbt Realtime-Hebelprodukte aller Emittenten. | Explizite Entwicklerschnittstelle für eigene Anwendungen. .NET/C#-Anschluss und DevID nötig; kein vorhandener Repo-Adapter. Eigene dauerhafte Datenspeicherung muss zum konkreten API-Vertrag passen. | USt., Nutzerklasse, DevID-Konditionen und endgültiger Gesamtpreis nicht öffentlich eindeutig belegt. Tatsächliche ISIN-/Listingdeckung, Originalzeitsemantik und Instrumentstatus offen. **Keine bestätigte vollständige B58-Lösung.** |
| **ARIVA MDS** | [API-Angebot und FAQ](https://ariva.ag/f-a-q/): Datenpakete, individuelle Preise nach Umfang/Nutzung; ausgewählte Testzugänge auf Anfrage. Kein bestätigter Privatpreis. | REST/OpenAPI; Schema 0.6.26 bereits [praktisch geprüft](DEPOT_DATA_SUPPLY_2026-11-20.md). Vertrag und tatsächlicher Datensatz nötig. | Das gelesene Standardschema belegt keine eigene Originalstatuszeit. Anbieteranfrage ist vorbereitet, nicht versandt. Eine API mit Börsenrechten garantiert nicht jede ISIN. |
| **Deutsche Börse Delayed Data** | [Veröffentlichter Dateidienst](https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Delayed-data): **0 EUR**, 15 Minuten verzögert, JSON.gz, UTC. | Offizieller maschinenlesbarer Download; nach Produkt/Segment auswählen. | Die Seite weist für **Frankfurt Certificates and Warrants nur Post-Trade** aus. Das belegt keinen benötigten Bid. Allgemeines Frankfurt-Pretrade nicht ohne Segment-/ISINnachweis auf Optionsscheine übertragen. |

### Kosten präzise abgrenzen

Die [TAI-PAN-Entwicklerdokumentation](https://www.tai-pan.de/apis/dotnet-framework/)
beschreibt getrennte `TPRQuoteTypes.Bid`-Ticks mit `QuoteTick.Time` und
historische Bid-/Ask-Abfragen. Das ist ein konkreter technischer Kandidat.
Die genaue Originalzeit-/Zeitzonenbedeutung und ein Instrumentstatus bleiben
ungeklärt; `ConnectionStatus` bezeichnet nicht automatisch die Handelbarkeit
eines Produkts. DevID und Konto sind nötig. .NET-Core-Hinweise sind vorhanden;
Lauffähigkeit im vorhandenen Linux-/Python-Betrieb ist ungeprüft, nicht
pauschal ausgeschlossen. Ein C#-Anschluss wäre zusätzlicher Aufwand.

Der monatliche Global-Preis wird zusätzlich in der offiziellen
[ELWAVE-Anbindung](https://www.tai-pan.de/blog/elwave-datenanbindung/)
bestätigt; deren Test-/Kündigungskonditionen werden nicht auf den
API-Vertrag übertragen. Die API-Preisliste nennt für deutsche
Regionalbörsen-Realtime weitere 15 EUR; ob dieses Paket für das gewünschte
Listing nötig ist, muss die Probe entscheiden. Keine pauschale Zusatzbuchung.
Global bewirbt sechs Monate Tick- und zwölf Monate Periodenhistorie;
längere Historie kostet extra und ist je Instrument zu prüfen.

Die [TAI-PAN-AGB](https://www.tai-pan.de/agb/), insbesondere §§2.7–2.8,
3.1/3.5 und 4.5, verlangen Nutzereinstufung/gegebenenfalls Börsenerklärungen
und begrenzen Datenverwendung auf die vereinbarte Software. Deshalb sind
eigene Monitoring-Datenbank, Aufbewahrung und Vertragsende vor Bestellung
im API-Nutzungsumfang zu bestätigen. **78 EUR ist eine nachvollziehbare
Addition, kein zugesicherter Gesamtpreis für unseren konkreten Betrieb.**

Stuttgarts [aktuelle Vertragsunterlagen](https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/zugang-zu-boersendaten/vertragsdokumente/)
ab 01.09.2026 unterscheiden Realtime-Non-Display und Weiterverteilung.
Die dort genannten **Netto**beträge 700,86 EUR/Monat für Pretrade beziehungsweise
973,42 EUR/Monat für das Gesamtpaket pro Gerät sind **kein belegter
Privatpreis für den kostenlosen Delayed-Download**. Auch der gesonderte
Delayed-Weiterverteilungstarif wird nicht auf private Eigennutzung
übertragen. Kostenloser ausdrücklich angebotener Dateidownload und lokale
Speicherung werden nicht als verboten dargestellt; dauerhafte Automation
bedarf einer passenden Nutzungsgrundlage.

### Portale als weitere Gegenprüfung

[Onvista §6](https://www.onvista.de/nutzungsbedingungen) und die
[Anbietererläuterung](https://hilfe.onvista.de/de/verstoss-gegen-nutzungsbedingungen)
verlangen Zustimmung für automatische Abrufe.
[finanzen.net](https://hilfe.finanzen.net/hc/de/articles/7444475913244-Hinweis-zum-automatisierten-Auslesen)
erklärt automatisches Auslesen für unzulässig. Für eine gesondert erlaubte
Automation wurde kein öffentlicher Preis gefunden. Ein Anzeigeabo würde
diese Rechte nicht automatisch liefern. Eine vorhandene Erlaubnis oder
ein anders lizenzierter Datenweg wäre gesondert zu prüfen.

## 3. Bedeutung der angezeigten Uhrzeit

Die Nutzerannahme ist **plausibel für eine gekennzeichnete Indikation**:
Die neben einem Bid stehende Zeit kann dessen letzte Aktualisierung
bezeichnen. Sie wird nicht verworfen, nur weil kein technischer Feldvertrag
auf der Bildschirmansicht steht. Zu speichern wären der unveränderte
Zeittext, das tatsächlich bekannte Datum/Zeitzone, Bezugsfeld, Herkunft,
Empfangszeit und die Kennzeichnung, ob die Bedeutung belegt oder angenommen
ist. Eine heutige Uhrzeit darf nicht automatisch ein fehlendes Datum
auffüllen; insbesondere rund um Sitzungswechsel und Mitternacht.

**Für unverändert strenges B58 ersetzt eine Annahme keinen Nachweis.**
Zu klären bleibt, ob die Uhr ausschließlich beim Bid, bei Bid/Ask gemeinsam,
bei einem Trade oder beim Seitenrefresh fortgeschrieben wird. Ein frischer
Briefkurs darf keinen alten Geldkurs verjüngen. Ein bestätigter neuer Bid
kann dagegen denselben Zahlenwert haben: Eine Preisänderung ist keine
Voraussetzung für eine neue gültige Quote.

Im vorhandenen V2-Vertrag gibt es bereits einen bewusst begrenzten Umgang
mit unbekannter Originalzeit: registrierte Emittentenindikationen können
bis **300 Sekunden seit erfolgreichem Empfang** verwendet werden;
Originalkursalter bleibt unbekannt. Passende registrierte Delayed-Daten
verwenden ihre gemeinsame Quellenzeit mit höchstens **1.800 Sekunden**.
Eine neue Website muss trotzdem technisch/inhaltlich an diesen Vertrag
angeschlossen werden. Keine stillschweigende neue Quotezeitdefinition.

## 4. Welche B58-Bedingungen bleiben selbst unter der Zeitannahme offen?

Die Tabelle gewährt ausdrücklich die Hypothese: **Die angezeigte Uhrzeit
ist die Aktualisierung genau dieses Bid.** Auch dann müssen die folgenden
Bedingungen nachgewiesen werden. „Offen“ bedeutet nicht, dass die jeweilige
Website sie nachweislich verletzt.

| Bedingung | Noch benötigter Nachweis | Hilft eine zweite übereinstimmende Website? |
| --- | --- | --- |
| **Produkt / Listing** | Richtige ISIN, konkreter Quotegeber/Handelsplatz, Währung und Preismaßstab. Bid statt Ask/Last/Close. | Plausibilisiert nur bei gleicher Bedeutung. Zwei andere Plätze können berechtigt andere Bids haben. |
| **Alter höchstens 900 s** | Datum, Zeitzone, keine Zukunftszeit; Alter an der tatsächlichen Auswertung inklusive Übertragungszeit. Genau 900 s zulässig, 901 s nicht. | Gleichheit beweist keine Aktualität. Neueste Seite kann einen alten Originalpreis spiegeln. |
| **Produktsitzung** | Bid-Zeit **und** Auswertungszeit liegen jeweils in einer verifizierten Sitzung des Listings; Öffnung inklusiv, Schluss exklusiv; Kalender, Feiertage/Sonderzeiten, Zeitzone und Version belegt. | Zwei Preiswerte liefern keinen Kalender. Keine zusätzliche Forderung durchgehender Öffnung zwischen beiden Zeitpunkten. |
| **Instrument tatsächlich OPEN** | Status des konkreten Produkts/Listings zur Auswertungszeit mit eigener Originalstatuszeit und belegter zeitlicher Geltung. Frühere OPEN-Meldung, Quote oder Börsenkalender genügen nicht automatisch. | Zwei Bids beweisen keine fortbestehende Handelbarkeit. Gemeinsamer Ursprungsfeed ist keine unabhängige Statusbestätigung. |
| **20 abgeschlossene Basiswertsitzungen** | Zählung bereits zur Bid-Zeit anhand des gebundenen Basiswertlistings. Frühester effektiver BUY als Beginn; Kauftag = 0. Teilverkauf/Nachkauf starten nicht neu. | Preisportale liefern weder persönliche Ausführungszeit noch die qualifizierte Zählung. Ein erst zwischen Bid und Abruf erfolgter 20. Schluss zählt für diesen Bid nicht. |

**Technischer Anschluss zusätzlich:** Die Produktionsregistry
`QUALIFIED_B58_PATHS` ist leer. Der jetzige Original-Bid-Prüfer kennt nur den
qualifizierten Feldvertrag des vorhandenen Frankfurt-Produzenten; die
Statusauswertung implementiert nur `OBSERVED_AT_INSTANT`. Für einen
geeigneten anderen Lieferanten sind dessen echte Zeitsemantik, Statuspfad,
Listingbindung, Konflikt-/Lückenverhalten und Recovery gezielt anzuschließen.
Eine andere belegte Statusgeltung kann einen anderen Anschluss benötigen.
Die 900-Sekunden-Grenze ist **keine Status-TTL**. Eine Code-Whitelist beweist
keine prinzipielle Untauglichkeit von Webdaten.

**B04 separat:** Für `Bid < Einstand` braucht der Consumer tatsächliche
effektive Käufe/Verkäufe, Restmenge, gewichteten Bruttoeinstand,
historische Kaufwährung und vergleichbaren Produktmaßstab. Noch beitragende
Kauftranchen bestimmen diese wirtschaftliche Grundlage; sie setzen den
Beginn der 20-Sitzungen-Zählung nicht neu. Historischer persönlicher
Basiswerteinstieg, Zieltreffer und Schutzboden sind zusätzliche B06-Daten,
**keine B58-Voraussetzungen**. Produktfristen sind ebenfalls separat.

### Verbindliche Repositorybelege

- [Integrationsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md):
  B13 und B58 sowie
  [B04/B57](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b04-b57-loss-monitoring-v1),
  [Original-Bid](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-original-bid-evidence),
  [Status](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-market-status-evidence)
  und [Sitzungen](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-session-evidence).
- [Original-Bid-Prüfer](../../backend/app/features/position_monitoring/domain/hebeltrader_original_bid.py):
  Quellvertrag, Zeitfolge, 900-Sekunden-Grenze und Sitzungsintervall.
- [Sitzungsservice](../../backend/app/features/position_monitoring/service/hebeltrader_original_bid_sessions.py)
  und [Loss-Inputs](../../backend/app/features/position_monitoring/service/hebeltrader_loss_inputs.py):
  beide Produktzeitpunkte, frühester effektiver BUY und Zählung zur Bid-Zeit.
- [B58-Registry](../../backend/app/features/position_monitoring/service/hebeltrader_b58_sources.py):
  leere Produktivqualifikation, Identitäts-/Originalstatusprüfung und Versorgungslücken.
- [V2-Vertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-rule-v2):
  ausdrückliche Trennung von Original-Bid, verzögerten Quellen und Emittentenindikation.

## 5. Beschaffungsentscheidung und bestehende Zuständigkeit

Empfohlen ist zuerst der Abgleich der tatsächlichen ISINs/Listings mit
vorhandenen erlaubten Quellen und den kostenlosen Dateidiensten. Das kann
die freigegebene V2-Indikation verbessern. Für eine gemeinsame
Realtime-Versorgung aller neun Gruppen ist **TAI-PAN ein konkreter
Evaluationskandidat mit öffentlichem Komponentenpreis**, ARIVA eine
Alternative mit individuellem Angebot. Eine Bestellung ist erst sinnvoll,
wenn geeignete Bid-/Zeit-/Statusfelder, tatsächliche ISIN-Abdeckung und
Speicherrechte bestätigt sind. Eine zweite Website ist ein ergänzender
Plausibilitäts- und Ersatzweg, keine allgemeine Zwei-Stimmen-Freigabe.

| Fehlende Information | Beschaffung / Prüfung | Bestehender Owner / dadurch mögliche Prüfung |
| --- | --- | --- |
| Aktuelle tatsächliche Instrumente, Routen und Sperrgründe | Vorbereitete private lesende Verbraucherdiagnose; keine öffentliche Depotliste | Trade Position, Market Data, Monitoring; konkret messbare Quellen-/V2-/B58-Abdeckung |
| Erlaubter passender Bid mit belegter Zeit | Emittenten-/Dateiweg oder begrenzte Vendorprobe für exakt dieselben Listings | Market Data: Provideradapter, Mapping, Refresh und Originalspeicherung; B04/V2, mit restlichen Belegen B58 |
| Originalstatus und zeitliche Geltung | Passender Statusdatensatz/Anbieterklärung; bei Bedarf zusätzliche Originalquelle | Market Data-Statusjournal und Monitoring-B58-Registry; OPEN zur Auswertung |
| Sessionhistorie und persönliche Einstandsbasis | Offizielle Kalender plus vorhandene effektive Ausführungen/historische Währungs-/Skalenbelege | Market Data und Trade Position; 20-Sitzungen-Zählung und vergleichbarer Einstand |
| Auswahl mehrerer Routen | Nach Qualifikation: Quellenrangfolge, Aktualitätsvergleich, Konflikt-/Ersatzregeln konkret beschließen | Vorhandener Positionsquellenowner; derzeit kein automatisches „neueste“/„zwei identisch“ |

Vor einer möglichen Anbieteranfrage sind lediglich diese konkreten Punkte
vorzubereiten: unterstützte ISIN-/Listingliste, private interne
Depotüberwachung ohne Weitergabe, vorgesehene Abfragefrequenz, Aufbewahrung,
Bid-Zeitfeld mit Zeitzone, Instrumentstatus mit Zeitgeltung, Recovery,
Gesamtpreis inklusive aller Rechte/Steuern und gegebenenfalls DevID.
Keine Anfrage wurde versandt. Ein einzelnes Ja zu „Realtime“ wäre keine
vollständige Antwort.

Der **einzige nächste ausführbare Auftrag** bleibt im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt):
vollständige lesende Diagnose des aktuellen PC-Verbraucherbestands.
Diese Quellenübersicht liefert die Kandidaten für deren anschließenden
gezielten Abgleich und führt keine zweite Aufgabenstatusliste.
