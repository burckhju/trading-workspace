# Kursbezug für Morgan Stanley, JPMorgan und UniCredit: erweiterte Recherche

Untersuchung der Quellen und Kursstände vom 14.09.2026, auf Repository-Stand
`e001d7c68dad7e50fa3e42e4e2a50500edc69b9d`. Ergänzt die
[erste Abdeckungsprüfung](issuer-quote-coverage.md). Gegenstand sind die dort
genannten zehn MS-, acht JPM- und ein UC-Produkt. Diese Recherche aktiviert keinen
Provider und bescheinigt keine dauerhafte Verfügbarkeit oder Orderausführbarkeit.

## Ergebnis und Entscheidung

| Quelle | Tatsächlich geprüft | Fachliche Einordnung | Nächster Schritt |
| --- | --- | --- | --- |
| MS, offizielle Produktseiten | Alle zehn ISINs, zehn Geldkurse, acht Briefkurse; Datum und Uhrzeit angezeigt | Emittentenabdeckung belegt. Strukturierter Lightstreamer-Vertrag im Seitenclient erkennbar, eigener Stream noch nicht getestet | Unterstützten privaten Stream-Zugang, Zeitbasis und Nutzungsrecht klären; dann gemeinsamer MS-Adapter |
| UC, offizieller gettex-Pre-Trade-Feed | Drei exakte Treffer für `DE000UN37224` in vollständig geprüfter MUND-Datei | Verzögerte Geld-/Briefdaten tatsächlich maschinenlesbar verfügbar | Beste nächste Integration ohne neues Datenabo; ein zentraler Dateisynchronisierer und ein verzögerter Quote-Adapter |
| JPM, Onvista-Produktpayload | `DE000JE7KTY8` mit getrennten JPMorgan- und Stuttgart-Quotes im JSON | Konkrete alternative Abdeckung belegt, aber automatisierter Abruf ausdrücklich einwilligungspflichtig | Ohne Einwilligung keinen Poller aktivieren; unterstützten Zugang anfragen |
| ARIVA MDS | Öffentliche OpenAPI: Identität, Quellen, Geld/Brief, Zeit, Qualität und Status | Konkreter Kandidat für einen lizenzierten Zugang über mehrere Emittenten | Zuerst Deckungsprüfung aller 19 ISINs und verbindliches Privatangebot |
| FactSet, SIX, Infront | Dokumentierte Marktdatenprodukte und Zugangswege | Weitere kommerzielle Alternativen; konkrete Produktabdeckung noch offen | Bei unpassendem ARIVA-Angebot nach identischer Spezifikation vergleichen |

Damit sind für zwölf der 19 Produkte alternative Kursbeobachtungen konkret
nachgewiesen: zehn MS, ein JPM, ein UC. Dies bedeutet **nicht zwölf einsatzbereite
automatische Anbindungen**. Für die weiteren sieben JPM-Produkte fehlt weiterhin
ein exakter Quote-Nachweis. Ein nicht bedienter Frankfurter Endpoint ist kein
Nachweis dafür, dass ein Produkt überhaupt keine Kurse besitzt.

## UniCredit: gettex vollständig geprüft

Die [offizielle Datenseite](https://www.gettex.de/en/trading/delayed-data) bietet
kostenlose verzögerte Pre-/Post-Trade-Dateien und erlaubt natürliche Personen als
private Nutzer, ohne Weitergabe oder kommerziellen Nutzen Dritter. Die Seite
nennt 15 Minuten Verzögerung, UTC, MUND für Freiverkehr und MUNC für regulierten
Markt. Echtzeitdaten können über Partner gegen eine Servicegebühr bezogen werden;
das ist ein anderes Angebot als der kostenlose Download.

Die [offizielle Produktseite](https://www.onemarkets.at/de/productpage.html/DE000UN37224)
führt für `DE000UN37224` gettex und Stuttgart auf. Ihre sichtbaren älteren
Websitekurse wurden nicht als aktuelle Feed-Beobachtung übernommen. Die deutsche
Produktweiterleitung lieferte im direkten Zugriff weiterhin einen leeren HTTP-200-Body.

Über die [offizielle Pre-Trade-Dateiliste](https://www.gettex.de/en/trading/delayed-data/pretrade-data/)
wurde folgende Datei ermittelt und vollständig gelesen:

```text
https://erdk.bayerische-boerse.de:8000/delayed-data/MUNC-MUND/pretrade/pretrade.20260914.18.45.mund.csv.gz
Komprimiert: 538279151 Bytes
SHA-256: 9f95cfbc1808f1e5edcd13e6609390003cbce0d752dca690428845834548e7b1
Vollständig dekomprimiert einschließlich GZip-Endprüfung: ja
Datensätze: 29884150
Beobachtetes Zeitfenster: 18:30:00.001383 bis 18:44:59.999867 UTC
Exakte Treffer DE000UN37224: 3
```

Ein erster auf 100 MB begrenzter Download war unvollständig und fand keinen
Treffer. Erst die vollständige Datei lieferte den Nachweis. Ein Downloadlimit
darf deshalb nicht als vollständige negative Deckungsprüfung gewertet werden.
Rohdaten und Quote-Dateien werden nicht in diesem öffentlichen Repository verteilt.

Beobachtetes Format: **kein Header**, sieben durch Komma getrennte Felder:

```text
ISIN,UTC-Uhrzeit,Währung,Geld,Geldvolumen,Brief,Briefvolumen
```

Datum und MIC stehen im Dateinamen, nicht zusätzlich in jeder Zeile. Die drei
UC-Treffer enthielten beide Kursseiten, Volumina und EUR. Ein Last-Trade-Preis
und ein expliziter Handelsstatus sind in diesem Pre-Trade-Format nicht enthalten.
Die Quelle ist MUND; MUNC wurde damit nicht geprüft. In der Datei gab es keinen
Treffer für die 18 MS-/JPM-ISINs. Laut [gettex-FAQ](https://www.gettex.de/en/about-gettex/faqs/)
sind BNP Paribas, Goldman Sachs, HSBC und UniCredit Zertifikate-Emittenten dort.
MS/JPM gehören nicht zu dieser Liste. Die Abwesenheit in einem Zeitfenster allein
wäre kein allgemeiner Abdeckungsbeweis.

### Konsequenzen für den Betrieb

Die Datenseite beschreibt 24-Stunden-Daten; die untersuchte einzelne Datei
enthielt tatsächlich nur ein 15-Minuten-Fenster. Dateiliste und Zeitfenster müssen
deshalb geprüft werden, statt jede Datei als kompletten Tagesbestand zu behandeln.
Bei gleichbleibender Größe wären vier Dateien rund **2,15 GB je Stunde**; dies
ist eine Hochrechnung aus einer Stichprobe, keine garantierte Datenrate.

Vorgeschlagene Integration in die vorhandenen Quote-Abstraktionen:

1. Neue Dateien zentral entdecken und jeweils einmal herunterladen. Keine
   Dateiabrufe pro Position und keine wiederholten Vollabrufe im 300-Sekunden-Takt.
2. GZip/CSV streamend lesen, auf konfigurierte ISINs filtern und je Instrument die
   jüngste gültige Beobachtung behalten. Vollständigkeit und Integrität prüfen,
   bevor der Datei-Checkpoint als erfolgreich gespeichert wird.
3. UTC-Datum aus verifiziertem Dateifenster rekonstruieren. Mitternacht, falsche
   Zeitbereiche, falsche ISIN/Währung, gekreuzte Preise und unvollständige Dateien
   müssen eigene Diagnosen erzeugen. Abrufzeit niemals als Kurszeit verwenden.
4. Den vorhandenen `GETTEX_DELAYED`-Platzhalter über
   `WarrantListingQuoteProvider` ersetzen; Mapping per ISIN plus verifiziertem MIC.
   Keine geratenen MUNC-/MUND-Listings und keine Datenmigration mit Benutzerprodukten.
5. Erfolgreiche Quotes in `warrant_quote_observations` speichern. Ein späterer
   fehlender Treffer oder Downloadfehler ersetzt keinen vorhandenen Kurs durch
   `null`. Fehlende Aktualisierung, ursprünglicher Zeitpunkt, Delay und Alter bleiben
   sichtbar, siehe [Aufbewahrungsregeln](retained-warrant-quotes.md).

Abnahmetests: vollständige/unvollständige GZip-Datei, leere Datei, unbekanntes
Schema, falsche ISIN, beide MICs separat, Tageswechsel, Duplikate, ältere Updates,
fehlende Kursseite, Restart mit gespeichertem Kurs, Downloadausfall und Queue-Fairness.
Für das Nutzerdeployment muss der ausgehende Zugriff auf Port 8000 erreichbar sein.
Kein API-Key nötig; Formatstabilität und Rate Limits sind nicht vertraglich zugesagt.
MUNC und Tageswechsel bleiben vor deren Aktivierung separat zu verifizieren.

## Morgan Stanley: alle zehn Produkte, zwei ohne Briefkurs

Normale öffentliche Abrufe der exakten offiziellen Produktpfade lieferten jeweils
HTTP 200, passende Identität und Produktfelder. Ergebnisse dieses Abrufstands:

| ISIN / offizielle Produktseite | Geld | Brief |
| --- | --- | --- |
| [DE000MM02AF0](https://zertifikate.morganstanley.com/produktdetails/de000mm02af0) | vorhanden | vorhanden |
| [DE000MJ3QMM4](https://zertifikate.morganstanley.com/produktdetails/de000mj3qmm4) | vorhanden | vorhanden |
| [DE000MJ3QFV9](https://zertifikate.morganstanley.com/produktdetails/de000mj3qfv9) | vorhanden | nicht gestellt |
| [DE000MK8B3F2](https://zertifikate.morganstanley.com/produktdetails/de000mk8b3f2) | vorhanden | vorhanden |
| [DE000MN50FN0](https://zertifikate.morganstanley.com/produktdetails/de000mn50fn0) | vorhanden | vorhanden |
| [DE000MN2ZUN2](https://zertifikate.morganstanley.com/produktdetails/de000mn2zun2) | vorhanden | nicht gestellt |
| [DE000MN25S42](https://zertifikate.morganstanley.com/produktdetails/de000mn25s42) | vorhanden | vorhanden |
| [DE000MM02M95](https://zertifikate.morganstanley.com/produktdetails/de000mm02m95) | vorhanden | vorhanden |
| [DE000MJ7DUX3](https://zertifikate.morganstanley.com/produktdetails/de000mj7dux3) | vorhanden | vorhanden |
| [DE000MM34MJ0](https://zertifikate.morganstanley.com/produktdetails/de000mm34mj0) | vorhanden | vorhanden |

Die Beobachtung eines Geldkurses reicht für eine ausdrücklich indikative
Bestandsbewertung; ein fehlender Briefkurs darf nicht durch Geld, Last oder Null
ersetzt werden. Spread/Mid bleiben ohne beide Seiten unbekannt. Eine ausführbare
Kauf-/Verkaufsorder folgt aus einer Website-Indikation nicht.

Der [offizielle Seitenclient](https://zertifikate.morganstanley.com/bundle/bundle-7ad89b64d9.min.js)
und die Produktattribute nennen:

- Lightstreamer-Server `https://push-morganstanley.adesso-financial.de/`,
  Adapter `SmarthouseFeed`;
- Produkt-Item beispielsweise `X00000D0400DE000MJ7DUX3`, getrennt vom
  Basiswert-Item `X00000C0400DE000BASF111`;
- `bid`, `ask`, `bidsize`, `asksize`, `lastquotetimestamp`;
- Verarbeitung des Zeitfelds als `DD/MM/YYYY HH:mm:ss.SSS` im JavaScript.

Die vollständige Zeitbasis/Zeitzone muss für einen Adapter bestätigt werden.
Es wurde kein eigener Stream verbunden und kein Seitentoken als Zugangsschlüssel
verwendet. HTML-Feldnachweis und Client-Protokoll sind noch kein verifizierter
serverseitiger Quote-Service. Ein unterstützter Stream wäre einer fragilen
HTML-Zahlenextraktion vorzuziehen.

Die [MS-Nutzungsbedingungen](https://zertifikate.morganstanley.com/nutzungsbedingungen/)
geben keine API-Verfügbarkeit oder Preiszusage. Vor Dauerbetrieb sind privater
automatischer Bezug, lokale Aufbewahrung, Authentisierung und erlaubte Rate mit
`strukturierte-produkte@morganstanley.com` zu klären. Kein kostenpflichtiger
Zugang wurde gebucht.

## JPMorgan: strukturierte Alternative gefunden, Einwilligung erforderlich

Der direkte Emittentenabruf liefert weiterhin einen Disclaimer statt einer
verifizierten Produktantwort. Zustimmung zu Nutzungsbedingungen oder Angaben zum
US-/Wohnsitzstatus wurden nicht im Namen des Nutzers vorgenommen.

Auf der [Onvista-Seite zu JE7KTY](https://www.onvista.de/derivate/Optionsscheine/328203424-JE7KTY-DE000JE7KTY8)
wurde bei HTTP 200 der strukturierte `__NEXT_DATA__`-Payload geprüft:

```text
props.pageProps.data.snapshot.instrument
  entityType = DERIVATIVE
  entitySubType = WARRANT
  entityValue = 328203424
  isin = DE000JE7KTY8
  wkn = JE7KTY

props.pageProps.data.snapshot.quoteList.list
  JPMorgan: idNotation 558377353, codeMarket @_JPML, außerbörslich
  Stuttgart: idNotation 558292292, codeMarket _STU
```

Beide Einträge enthielten Geld/Brief, getrennte Bid-/Ask-Zeitfelder mit UTC-Offset,
EUR und Stückzahlen. Die Produkt-ID war in beiden Quotes dieselbe. Der
Stuttgart-Last-Trade hatte einen anderen Zeitpunkt als der Bid-/Ask-Quote. Die
Anbieterkennung `RLT` ist eine deklarierte Qualität, kein gemessener Delay.
Die getrennte Intel-Basiswertstruktur enthielt USD-Aktienkurse und wurde ausgeschlossen.
Provider wäre Onvista; JPMorgan/Stuttgart sind die jeweiligen Ursprungsquellen.
`_STU` und `@_JPML` sind Providerkennungen, keine ISO-MICs.

Entscheidend: Abschnitt 6 der [Onvista-Nutzungsbedingungen](https://www.onvista.de/nutzungsbedingungen)
untersagt automatisierte Abfragen ohne ausdrückliche Einwilligung. Deshalb keine
weitere automatisierte Serienprüfung der acht JPM-Produkte und kein Workspace-Poller.
Ein öffentlicher JSON-Payload ersetzt weder Einwilligung noch API-Vertrag. Kosten,
Limits und Dauerstabilität eines zulässigen API-Zugangs sind offen.

JPMorgan selbst kann über die [offizielle Kontaktseite](https://www.jpmorgan-zertifikate.de/kontakt/)
um einen unterstützten Quote-Zugang gebeten werden. Ein Broker-Frontend mit
Realtime-Anzeige, etwa [justTRADE](https://www.justtrade.com/handelspartner/jpmorgan),
belegt ebenfalls keinen für den Workspace verfügbaren API-Zugang.

## Dokumentierte Datenprovider und Kosten

Die folgenden API-Produkte passen technisch zum Bedarf. Ohne individuelle
Freischaltung wurde bei keinem kommerziellen Anbieter ein Quote für alle 19 ISINs
verifiziert. Marketing-Abdeckung und erworbene Datenrechte sind getrennte Prüfungen.

| Anbieter | Identifikation und Kursdaten | Zugang / Stabilität | Kosten und noch offene Punkte | Aufwand |
| --- | --- | --- | --- | --- |
| [ARIVA MDS](https://ariva.ag/data-und-apis/) | ISIN/WKN; Marktquelle und Währung getrennt; Geld/Brief, Last, Zeit, Qualität und Handelsstatus | Öffentliche OpenAPI, JSON/Stream, OAuth2 Client Credentials | Angebot und Source-Entitlements erforderlich; keine bestätigte Privatpauschale oder numerische Abrufgrenze | Mittel; guter Anschluss an vorhandene Mappings |
| [FactSet Real-Time Quotes](https://developer.factset.com/api-catalog/real-time-quotes-api) | ISIN/WKN-Cross-Reference, Notation je Börse; Bid/Ask, Last und Status | Versionierte REST-API/SDK, OAuth2 oder API-Key; Qualitätsparameter explizit setzen | API- und Börsenlizenzen bestätigen lassen; kein getesteter Privattarif | Mittel; Instrument/Notation sauber trennen |
| [SIX Web API](https://www.six-group.com/en/products-services/financial-information/delivery-methods/api/web.html) | ISIN/WKN/MIC, breite internationale Datenquellen | REST/JSON, GraphQL, WebSocket; mTLS-Zertifikat | Individueller Zugang, Quellenfreigaben und Preis; Testzugang anfragbar | Mittel bis hoch durch Zertifikatsbetrieb |
| [Infront Data Manager API](https://www.infront.co/global/en/product/data-manager-api.html) | Markt-/Instrumentdaten; Snapshot oder Stream, JSON/CSV/XML | Dokumentierter kommerzieller Dienst; Stuttgart/gettex im Datenangebot | API-Angebot samt ISIN-Auflösung, konkreten Feldern und Rechten bestätigen lassen; Terminalpreis ist kein API-Gesamtpreis | Mittel, abhängig vom angebotenen API-Produkt |
| [Stuttgart direkt](https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/zugang-zu-boersendaten/vertragsdokumente/) | Börsen-Pre-/Post-Trade; genaue EASY-EUWAX-Abdeckung im bestellten Dienst prüfen | Vertragsgebundener Feed, technische Anbindung erforderlich | Aktuelle professionelle Non-Display-Tarife können erheblich sein; siehe unten | Hoch für ein privates Depot |

### Konkrete Integrationsverträge aus der Dokumentation

Die [ARIVA-OpenAPI](https://mds.ariva-services.de/swagger-ui/openapi.yml), geprüft
in Version 0.6.20, beschreibt die Produktionsbasis
`https://mds.ariva-services.de/api/v1`:

- `/search` zur Identifikation, `/sources/` zur tatsächlich verfügbaren Quelle;
- `/marketstates/{instrumentId}/{sourceId}` für den gezielten Kurs;
- Quote-Felder `value`, `quantity`, `date`/`datetime`, `isIndicative`;
- Qualität `REALTIME`, `DELAYED`, `END_OF_DAY` sowie getrennten Instrument-/Handelsstatus;
- `/ratelimit/statistics` zur Beobachtung der Nutzung, ohne daraus ein vertragliches
  Limit ableiten zu können.

Für den Workspace: Quelle eindeutig auswählen, ISIN und Währung prüfen, keine
zufällige Quellenauswahl und keine unbemerkte EOD-Substitution. Vom Provider berechnete
Indikationen (`isIndicative`) ausdrücklich kennzeichnen. Erforderlich wären
ausgestellte OAuth-Client-ID und Client-Secret sowie Quellenfreigaben. Die beworbene
[kostenlose ARIVA-Testaktion](https://ariva.ag/freeapi/) endete am **19.12.2025**;
sie ist kein aktuell zugesagter kostenloser Zugang.

Das [offizielle FactSet-SDK](https://github.com/factset/enterprise-sdk/tree/main/code/python/RealTimeQuotes/v3)
enthält `/instrument/crossReference/getByISIN`, `getByWKN`,
`/instrument/notation/list` und `/prices/bidAsk/get` unter
`https://api.factset.com/wealth/v3`. Die dokumentierte Standardqualität der
Bid-/Ask-Abfrage ist `DLY`. Eine Datenfreigabe darf deshalb nicht implizit als
Realtime interpretiert werden. Die separate
[Securitized Derivatives API](https://github.com/factset/enterprise-sdk/tree/main/code/python/SecuritizedDerivativesAPIforDigitalPortals/v4)
hilft bei Produktstammdaten und Screening, ersetzt aber nicht den Quote-Zugang.

### Stuttgart-Preise richtig einordnen

Die [Datennutzungspreisliste ab 01.09.2026](https://www.boerse-stuttgart.de/media/fizi51pu/preisliste-datennutzung_gueltig-ab-192026-31.pdf)
nennt für **Non-Display, ein Device, pro Monat** netto:

| Paket | Datennutzungsgebühr |
| --- | ---: |
| Pre-Trade | 700,86 EUR |
| Post-Trade | 340,70 EUR |
| Gesamt | 973,42 EUR |

Daneben aufgeführte B2C-Display-Gebühren von 3,96 EUR für Pre-Trade bzw. 5,50 EUR
für das Gesamtpaket je Zugangskennung sind **kein vollständiges individuelles
API-Angebot**. Ob privates automatisiertes Monitoring als Non-Display einzuordnen
ist und welche Anbindungs-/Vendor-Kosten entstehen, muss der Anbieter konkret
bestätigen. Diese professionellen Gebühren gelten nicht automatisch für den
kostenlosen privaten MiFIR-Download. Kein solcher Tarif wurde bestellt.

## Reihenfolge für trading-workspace

1. **gettex für verifizierte UC-/weitere tatsächlich abgedeckte Produkte** als
   verzögerte Quelle umsetzen. Dateigröße und Takt erfordern einen gemeinsamen
   Download, keine zusätzliche blockierende Schleife pro Optionsschein.
2. **Morgan Stanley** um unterstützten privaten Stream-Zugang bitten. Das beseitigt
   gezielt zehn Abdeckungslücken, sobald Zeitbasis, Zugriff und Wiederverbindung
   geprüft sind. Falls nicht zugänglich: derselbe lizenzierte Fallback wie für JPM.
3. **ARIVA als ersten kommerziellen Vergleich prüfen**, weil die öffentlich
   dokumentierte Quellenauswahl und ISIN-Identifikation zum bestehenden Modell passen.
   FactSet/SIX/Infront anhand derselben Anforderungen vergleichen. Diese Reihenfolge
   ist eine technische Einschätzung, keine bereits bestätigte Preisempfehlung.
4. **JPM** über einen freigegebenen Emittenten-/Börsen-/Vendor-Zugang integrieren;
   Onvista nur mit ausdrücklicher Erlaubnis für automatisierten Bezug und Speicherung.
5. Für jede Quelle bestehende Provider-Mappings und dauerhafte Quote-Aufbewahrung
   wiederverwenden. Letzter erfolgreicher Kurs bleibt für gekennzeichnete Analyse
   sichtbar; Warnungen beziehen sich auf Instrument, Preisart, Quelle und Zeit.
   `execution_usable` bleibt für verzögerte/alte/indikative Daten falsch.

Für eine Anbieteranfrage sind nötig: privater lokaler Nutzer, zunächst 19 konkrete
Optionsscheine, erweiterbares Depot mit mindestens 52 Positionen, keine Weitergabe,
300-Sekunden-Zielintervall oder gemeinsamer Stream, ISIN/WKN, Bid/Ask/Last getrennt,
vollständige Zeitstempel, Marktquelle/MIC, Delay, Handelsstatus, letzter erfolgreicher
Kurs über Neustarts hinweg, API-/Börsengebühren inklusive Steuern sowie feste Limits.
Eine Deckungsmatrix muss echte Quotes aus einer laufenden Sitzung pro ISIN enthalten.

Es wurden keine Anbieter kontaktiert, kostenpflichtigen Konten aktiviert oder
Zugangsdaten angefordert. Die nächsten kostenfreien Implementierungsarbeiten sind
für gettex konkret beschreibbar; eine dauerhafte MS-/JPM-Anbindung braucht noch den
oben benannten unterstützten Zugang bzw. die Nutzungsfreigabe.
