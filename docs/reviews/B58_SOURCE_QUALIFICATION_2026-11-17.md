# B58: tatsächliche Quellenprüfung vom 17.11.2026

## Ergebnis und Aussagegrenze

**Kein in dieser Entwicklungsumgebung zugänglicher Quellenpfad ist positiv für
B58 qualifiziert.** Der bestehende öffentliche Frankfurt-Pfad für
`DE000VH2LU21` wurde tatsächlich abgerufen: Er liefert Last/Previous Close,
keinen Original-BID und keinen instrumentbezogenen Status. Das ist ein Befund
über einen existierenden Lieferanten, kein Test des anwendungseigenen
`frankfurt-quotes-v1`-Formats.

Prüfbasis des Codes: #350, Commit
`77b3312da20b83d207f1da9c9b5f379b705dc8bb`, mit den unveränderten Vorgängern
#348/#349. [Integrationsvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-market-status-evidence),
[Frankfurt-Vertrag](../frankfurt-quotes.md) und
[frühere Emittentenprüfung](ISSUER_QUOTE_QUALIFICATION_2026-10-30.md) bleiben
maßgeblich; deren historische Befunde sind kein neuer Live-Nachweis.
Aufgabenstatus wird ausschließlich im [Backlog](../planning/PRODUCT_BACKLOG.md#monitoring-rules)
geführt.

Die tatsächliche Nutzerinstallation, deren Datenbank, vorhandene Zustimmungen,
Depotpositionen und Providerzugänge waren hier nicht verfügbar. Die verwendete
ISIN ist der bereits im Repository dokumentierte Quellenprüffall. Weder ihre
heutige Depotzugehörigkeit noch die Abdeckung des gesamten Depots ist bestätigt.
Es wurden keine Konfigurationen, Zustimmungen, Positionen oder wirtschaftlichen
Fakten verändert und keine externen Nachrichten gesendet. Veröffentlichte
Produktdaten werden nicht als aktuelle ausführbare Quotes bezeichnet.

## 1. Konkreter Frankfurt-Pfad: Originalabruf

Quelle:
[offizieller Einzelinstrument-Endpunkt](https://api.live.deutsche-boerse.com/v1/data/price_information/single?isin=DE000VH2LU21&mic=XSC).
Ein anonymer HTTPS-GET mit `Accept: application/json` lieferte am
**17.11.2026, 05:06:34.917591 UTC** HTTP 200, **565 Bytes**,
SHA-256 `589b9e8a46473a1a9ed385f9332b0c61e2086091392cc0a94e39fd51dc7d5ba0`.
Die vollständige Originalantwort war:

```json
{"changeToPrevDayAbsolute":0.0330,"changeToPrevDayInPercent":28.4500,"closingPricePrevTradingDay":0.149,"currency":{"originalValue":"EUR","translations":{"others":"Euro"}},"dayHigh":0.173,"dayLow":0.149,"isin":"DE000VH2LU21","lastPrice":0.149,"lastPriceIndicator":null,"mic":"XSC","minimumTradableUnit":1,"priceFixings":2,"timestampLastPrice":"2026-11-16T19:45:03+01:00","tradedInPercent":false,"tradingTimeEnd":"22:00:00","tradingTimeStart":"08:00:00","turnoverInEur":2768.0000,"turnoverInPieces":16000,"turnoverNominal":null,"weeks52High":2.13,"weeks52Low":0.097}
```

Die [offizielle Produktseite](https://live.deutsche-boerse.com/derivative/de000vh2lu21-call-auf-unitedhealth-group)
lieferte ebenfalls HTTP 200: am 17.11.2026, 05:07:04.741606 UTC, 423.732 Bytes,
SHA-256 `6288f84b6716dd26e19c953112ca7e4ff81206e4d047f66eb30e262503737558`.
Ihre eingebetteten Instrumentdaten identifizieren `DE000VH2LU21`, `VH2LU2`,
Vontobel, `instrumentTypeKey=derivative`, `defaultMic=XSC`, `mics=[XSC]`.
`XSC` bleibt der Providercode; daraus wird kein ISO-MIC oder neues Listing geraten.
Der bestehende Adapter bindet diesen öffentlichen Modus gesondert an XFRA.

| Benötigter Nachweis | Tatsächlicher Befund dieses Pfads |
| --- | --- |
| Original-Geldkurs | Nicht geliefert. `lastPrice` und `closingPricePrevTradingDay` sind andere Preisarten. |
| Eigene Original-BID-Zeit | Nicht geliefert. `timestampLastPrice` gehört ausschließlich zum Last-Trade. |
| Instrumentbezogener Marktstatus | Nicht geliefert. Handelszeit-Uhrzeiten und Umsatz ersetzen ihn nicht. |
| Eigene Originalstatuszeit und zeitliche Bedeutung | Nicht geliefert; weder Abrufzeit noch Last-Zeit können sie herstellen. |
| Negative und reine Statusmeldungen | In dieser Antwort und im implementierten öffentlichen Vertrag nicht enthalten. Ein 404 oder Transportfehler ist kein CLOSED. |
| Grenzen | Kein belegter Feed-Delay, keine garantierte Aktualisierung/Abdeckung und kein Statusstrom. Der einzelne erfolgreiche Abruf beweist keine kontinuierliche Versorgung. |

Der bestehende `providers/frankfurt_quotes/public.py` weist diese Antwort deshalb
weiter als `FRANKFURT_POST_TRADE_ONLY` aus. Der öffentliche Pfad wird weder mit
dem vendor-neutralen Snapshotimport noch mit einem lizenzierten BID-Feed
gleichgesetzt. Die [offiziellen Website-/Downloadbedingungen](https://live.deutsche-boerse.com/en/disclaimer-en)
beschreiben insbesondere eingeschränkte Nutzungsrechte und keine Gewähr für
Aktualität/Vollständigkeit. Daraus folgt kein neu bestätigtes automatisiertes
Non-Display-Nutzungsrecht und keine produktive Aktivierung.

## 2. Vontobel-Emittentenpfad: Lieferung und fehlende Semantik

Konkreter vorhandener Adapterpfad:
`VONTOBEL_MARKETS / DE000VH2LU21 / ISSUER / EUR` auf der
[offiziellen Produktseite](https://markets.vontobel.com/de-de/produkte/hebel/optionsscheine/DE000VH2LU21).
Ein direkter Abruf aus dieser Umgebung antwortete mit **HTTP 403**. Es wurde
keine Sperre umgangen. Der Webreader lieferte eine datierte Suchindexansicht mit
seiteneigenem „Heute“ 11./12.09.2026; sie ist ausdrücklich keine Kursbeobachtung
vom 17.11.2026.

Der vorhandene Adapter liest aus `__NEXT_DATA__` die Felder `price.bid`,
`price.ask`, `price.currency`, das gemeinsame `price.latestTimestamp` und
`tradingHours.isOpen`. Das beschreibt den Codevertrag, nicht den heute erhaltenen
Originalpayload. Die vorhandenen Adaptertests erzeugen synthetische Payloads
und sind kein zusätzlicher Lieferantennachweis.

| Benötigter Nachweis | Befund |
| --- | --- |
| Original-Geldkurs | Der implementierte Pfad liest `price.bid`; heute kein Original-BID erhalten. Emittentenindikation, keine nachgewiesene börsliche Ausführbarkeit. |
| Eigene Original-BID-Zeit | `latestTimestamp` ist gemeinsam. Seine Bedeutung als unveränderte BID-Seitenzeit ist nicht unabhängig dokumentiert. |
| Instrumentstatus | Adapter liest `tradingHours.isOpen`. Es fehlt ein verifizierter Vertrag, ob dies Instrumenthandel oder nur planmäßige Handelszeit bezeichnet. |
| Statuszeit und Bedeutung | Keine eigene Originalstatuszeit oder belegte Gültigkeitsaussage im bestehenden Pfad. |
| Negative/status-only | Ohne `price` beziehungsweise ohne beide Preisseiten liefert der bisherige Parser `None`, bevor der Status ausgewertet wird. Ein unabhängiger Originalstatuskanal ist nicht belegt. |
| Grenzen | Heutiger Direktzugriff 403; keine nachgewiesene maximale Verzögerung, Abruffrequenz oder Wiederanlaufvollständigkeit. |

Die [Vontobel-Nutzungsbedingungen](https://markets.vontobel.com/de-de/nutzungsbedingungen)
lassen Verzögerungen/Korrekturen zu, begrenzen den Nutzerkreis und erlauben
Downloads/Kopien nur privat ohne Weitergabe. Sie garantieren keine fortlaufende
Verfügbarkeit oder Eignung. Diese Prüfung erteilt keine neue Zustimmung oder
Nutzungsfreigabe.

## 3. Weitere vorhandene Originale und Beschaffungskandidaten

| Pfad | Verfügbare Evidenz | B58-Grenze |
| --- | --- | --- |
| Morgan Stanley / bestehende ISSUER-Routen | `tests/fixtures/morganstanley/user-snapshots-20260921.json` kennzeichnet echte, vom Nutzer gelieferte Serverbeobachtungen. Schema: `bid`, `bidsize`, `ask`, `asksize`, `lastquotetimestamp`. Originaldatum des Nachweises: 21.09.2026. | Historische Preiswerte sind keine heutigen Quotes. Der Zeittext besitzt keine Zeitzone; separate BID-/Statuszeit und Instrumentstatus fehlen. Die bestehende Normalisierung `observed_at=None`, `trading_status=UNKNOWN` bleibt korrekt. Kein neuer Streamabruf. |
| gettex MUND/MUNC | Die [offizielle Delayed-Data-Seite](https://www.gettex.de/en/trading/delayed-data/) wurde erneut gelesen: UTC-Zeit, verzögerter Dateiservice, 15 Minuten nach Erstveröffentlichung, mindestens 24 Stunden Bereitstellung; private Nutzung ohne Weitergabe. Der bestehende Parser erhält ISIN/MIC, Währung und getrennte Seiten. | Das siebenfeldrige beobachtete CSV-Schema enthält keinen Instrumentstatus oder eigene Statuszeit. Nominale 900 Sekunden Delay garantieren kein tatsächliches BID-Alter ≤900 Sekunden einschließlich Transport. Kein neuer Dateiabruf, der zugleich Bedingungen bestätigen würde. |
| ARIVA MDS | [Original-OpenAPI](https://mds.ariva-services.de/swagger-ui/openapi.yml) heute HTTP 200, Version **0.6.25**, 465.056 Bytes, SHA-256 `3444a4ab7c787cb2169d8efc8f20e2dc2c26c3af04e8ff7116cd43f6b2d097ff`, Abruf 05:07:19.963503 UTC. Instrument-/Listingidentität, Bid/Ask, Quality, SSE und OAuth2 Client Credentials sind dokumentiert. | Das gelesene `Status`-Schema enthält `tradingPhase`, `instrumentStatus`, `secTradingStatus`, `currentTradingStatus` u.a., aber **keine eigene Statuszeit**. Zugang, Rechte und echte Ziel-ISIN-Lieferung fehlen ebenfalls. Ein Vertrag oder Beispiel muss gerade diese Lücke schließen; API-Dokumentation allein qualifiziert nichts. |
| Deutsche Börse Cloud Stream | [Originalhandbuch](https://www.mds.deutsche-boerse.com/resource/blob/3404652/0a8944ad250282051219361caf7fcc19/data/Cloud%20Stream%20User%20Manual_V3_4.pdf), tatsächlich gelesene **Version 4.3**, gültig ab 09.11.2026. Beschreibt API-Key-Zugang, Stream-Sequenzen/Recovery, Preisdaten und feedabhängige Handelsstatusfelder. | Kein vorhandener freigeschalteter Zugang, keine geprüfte Optionsschein-/Listingabdeckung und keine echten Status-only-Ereignisse dieser Instrumente. Feldkatalog und gemeinsame MDEntryTime beweisen noch keine geeignete eigene Statuszeit oder Fortschreibungssemantik. Kein neuer Adapter, Abonnement oder Account. |

Beim ARIVA-Dokument bedeutet `Marketstate.status` nicht automatisch einen
aktuellen offenen Markt. Bei Cloud Stream dürfen Feedfamilien, Instrumenttypen
und Statuscodes nicht pauschal zwischen Eurex, Tradegate und Xetra übertragen
werden. Das Handbuch nennt Verbindungs-/Requestgrenzen ohne allgemein verwendbare
numerische Freigabe; ein Beispielstream ersetzt keine Depotabdeckung.

## 4. Kleinste noch notwendige Beschaffung

Benötigt wird **ein tatsächlich verfügbarer, nutzungsrechtlich geklärter Pfad für
mindestens ein vorhandenes Depotinstrument auf seinem gebundenen Listing**.
Vor Aktivierung muss dessen Originalbelegpaket enthalten:

1. Exakte ISIN, Listing/Providercode, Währung, Original-BID und unveränderte eigene
   BID-Zeit mit Zeitzone; der Lieferant muss die Seitensemantik erklären.
2. Instrumentbezogener Status mit eigenem Originalzeitpunkt und dokumentierter
   Aussage: punktbezogene Beobachtung oder ausdrücklich definierte Gültigkeit.
   Empfangszeit und Preiszeit zählen nicht als Ersatz.
3. Echte OPEN-, CLOSED-/SUSPENDED- und preislose Statusbeispiele sowie den Vertrag
   für Reihenfolge, Widersprüche, verspätete Ereignisse und Quellenwechsel.
4. Belegte Lücken-/Reconnect-/Recovery-Regeln, Verzögerung und private
   automatisierte Nutzung einschließlich lokaler Speicherung und Abrufgrenzen.
5. Ein Abgleich der bereits gespeicherten Quellenauswahl mit der tatsächlich
   lizenzierten Instrumentliste. Keine Neuerfassung von Positionen oder
   persönlichen Ausführungen.

Das kann ein ergänzter Vertrag/Originalexport eines bereits zugelassenen
Lieferanten oder ein begrenzter Evaluationszugang sein. Welche Beschaffung
beauftragt und freigegeben wird, bleibt eine ausdrückliche Entscheidung; diese
Prüfung hat keinen Anbieter kontaktiert. Ein weiterer Vertrauensschalter,
`contract_verified`, selbst erzeugte Status-JSONs oder tägliche manuelle
OPEN-Bestätigungen schließen die Lücke nicht.

Die **900 Sekunden gelten ausschließlich für das BID-Alter**. Dieses Dokument
definiert weder Status-TTL noch eine neue Bedingung durchgehender Marktöffnung.
Negative Originalpunkte bleiben belegte Punkte, ein altes OPEN wird ohne
nachgewiesene zeitliche Aussage nicht bis zur Auswertung verlängert.

## 5. Unabhängiger B05-Anschluss: reale Quellen und verbleibender Scope

Die offiziellen Originalkalender sind tatsächlich erreichbar:

| Originalquelle | Abruf am 17.11.2026 (UTC) / Bytes / SHA-256 |
| --- | --- |
| [FWB/Xetra/Frankfurt 2026](https://cashmarket.deutsche-boerse.com/resource/blob/4481276/1b643791fcb4d60bdd7f25efad3f4626/data/deutsche-boerse-trading-calendar-2026.pdf) | 05:07:40.759913 / 126.974 / `1edfc7b737ae1f5fe93179bfa9af59223b3c9d11cc8deddd127b386fb87e44b6` |
| [FWB/Xetra/Frankfurt 2027](https://cashmarket.deutsche-boerse.com/resource/blob/5674438/fb6e22c77930acea97641cf7d65ef78a/data/deutsche-boerse-trading-calendar-2027.pdf) | 05:07:45.603132 / 103.199 / `5c62bf0a78afb8f6123638d6e7b9a30c864799e2c2210b73b13bcdb6e9a64cf2` |
| [Sonderzeiten 30.12.2026](https://cashmarket.deutsche-boerse.com/resource/blob/5673886/22764993c4b1617c5f465186066344e6/data/Final%20trading%20session%202026.pdf) | 05:07:50.923144 / 158.845 / `d3618ef9738a3cae92909d11d4eaf820ab7b71d1e723c1fa04a21062e9738115` |

Alle drei Abrufe lieferten HTTP 200. Kalender 2026/2027 belegen Handelstage und
Ausnahmen über den Jahreswechsel. Die gesonderte Mitteilung zum 30.12.2026
nennt XFRA/T7 und veränderte Marktphasen; die pauschale reguläre Schlusszeit
darf diesen Nachtrag nicht überdecken. Die
[Kalenderseite](https://cashmarket.deutsche-boerse.com/cash-en/trading/trading-calendar-and-trading-hours)
weist außerdem auf mögliche künftige Änderungen hin. Keine dieser Quellen ist
ein aktueller Instrumentstatus.

Die datierte offizielle Vontobel-Produktansicht nennt für `DE000VH2LU21`
**15.01.2027 als letzten Handelstag und Bewertungstag**, **22.01.2027 als
Rückzahlung**. Die Rückzahlung darf nicht zum maßgeblichen Termin umgedeutet
werden. Der heutige Originalimport der verbindlichen Produktbedingungen,
etwaige Revisionen, die genaue Produktschlusszeit und die dauerhafte Bindung des
tatsächlichen Depots an sein Ausstiegslisting fehlen hier. Auch ein belegtes
XFRA-Listing darf nicht still an die Stelle einer vorhandenen ISSUER-Auswahl
treten.

Damit lässt sich unabhängig eine **Rückwärtszählung auf vollständig belegten
Kalendertagen** vorbereiten und synthetisch testen: den früheren verifizierten
Produkttermin ausschließen, die 20. vorherige Produktsitzung wählen,
Kalenderlücken/-revisionen und Jahreswechsel ausdrücklich behandeln. Für eine
anwendbare persönliche Frist müssen Product-Owner-Belege zum letzten Handelstag
und maßgeblichen Termin sowie das feste Ausstiegslisting hinzukommen; für die
Handelsschlussgrenze zusätzlich die produktspezifische Schlusszeit. Eine
implementierte Kalenderfunktion oder der historische Produktseitenbefund ist
noch keine aktive B05-Überwachung. Die B05-Prüfung erhält keine BID-Abhängigkeit.

## 6. Nachweisdisziplin

Direkte Abrufe, Suchindexansichten, Codeanalyse und historische Originale sind
oben getrennt bezeichnet. HTTP 403 betrifft den jeweiligen Zugriff aus dieser
Umgebung; es beweist keine allgemeine Nichtverfügbarkeit. Erfolgreiche
öffentliche Einzelabfragen sind keine Betriebsabnahme und keine Garantie einer
kontinuierlichen Versorgung. Hashes dokumentieren die untersuchten Bytes; sie
bestätigen nicht unabhängig die fachliche Wahrheit des Lieferanten.

Synthetische Tests dürfen den vollständigen Daten-/Regel-/Zustellpfad ausüben.
Ihr Erfolg aktiviert weder diese Quellen noch die vollständige
`HEBELTRADER_CONFIRMED_BASELINE`. Main-Integration, Release, PC-Installation und
echter unbeaufsichtigter Betrieb benötigen ihre eigenen ausdrücklichen Nachweise.
