# Alternativen für Morgan Stanley, JPMorgan und UniCredit

Recherche vom 14.09.2026. Die Diagnose des Nutzers ergab 32 vorhandene und 20 fehlende
Optionsscheinbeobachtungen. Die fehlenden umfassen zehn Morgan-Stanley-, acht
JPMorgan-, einen UniCredit-Optionsschein sowie die unvollständige BNP-ISIN.
Eine Frankfurter 404-Antwort belegt nur fehlende Abdeckung dieses Endpoints, nicht
fehlende Börsennotierung oder fehlende Kurse bei anderen Anbietern.

## Konkrete Nachweise

| Emittent / betroffenes Beispiel | Offizielle Alternative | Nachweis und Grenze |
| --- | --- | --- |
| Morgan Stanley, BASF-Call `DE000MJ7DUX3` / MJ7DUX | [Emittenten-Produktseite](https://zertifikate.morganstanley.com/produktdetails/de000mj7dux3) | Produktidentität und EUR bestätigt. Direkter öffentlicher Seitenabruf lieferte Geld 0,044 / Brief 0,051, angezeigter Zeitpunkt 14.09.2026 20:12:07, Quelle Morgan Stanley Europe SE. Dies ist ein Recherche-Snapshot, keine aktuelle Orderfreigabe. |
| Morgan Stanley, dasselbe Produkt | [Börse Stuttgart](https://www.boerse-stuttgart.de/en/products/leverage-products/warrants/stuttgart/mj7dux/) | Exact-ISIN, WKN und Handelssegment EASY EUWAX belegt. Die Website-Abdeckung belegt keine Abdeckung des bisher konfigurierten MiFIR-Snapshots. |
| JPMorgan, Intel-Call `DE000JE7KTY8` | [Emittenten-Produktpfad](https://www.jpmorgan-zertifikate.de/zertifikate-detail/DE000JE7KTY8) | HTTP 200 beim direkten Abruf, aber nur Seitengerüst/Disclaimer statt eines verifizierten Produkt-Quotes. Der öffentlich ausgelieferte JavaScript-Code nennt eine strukturierte ISIN-/Namenssuche; der getestete Suchaufruf lieferte 404. Produkt-Quote-Abdeckung dieses Zugangs bleibt unbewiesen. |
| JPMorgan, Website allgemein | [Offizielle Website](https://www.jpmorgan-zertifikate.de/) | Andere offizielle Produktseiten zeigen Geld/Brief, ISIN und Zeit. Dies reicht nicht aus, diese Daten einem der acht betroffenen Produkte zuzuordnen. Keine Freischaltung oder Zustimmung im Namen des Nutzers erfolgt. |
| UniCredit, BNP-Paribas-Call `DE000UN37224` / UN3722 | [onemarkets Produktseite](https://www.onemarkets.de/content/onemarkets-relaunch/de.omr-redirect.html/DE000UN37224), [offizielles Basisinformationsblatt](https://www.onemarkets.de/kid/DE000UN37224/de) | Produkt und Emittent UniCredit Bank GmbH bestätigt. Direkte Abrufe von Produktweiterleitung und Startseite lieferten hier HTTP 200 mit leerem Body; daraus folgt keine belastbare Kursabdeckung. |
| UniCredit, dasselbe Produkt | [Börse Stuttgart](https://www.boerse-stuttgart.de/en/products/leverage-products/warrants/stuttgart/un3722/) | Öffentliche offizielle Seite zeigte Geld 0,072 / Brief 0,075 mit Anzeige 14.09., 20:11:11, Segment EASY EUWAX, XSTU. Werte ändern sich; Suchindex und direkter Abruf können unterschiedliche Stände liefern. Direkter maschineller Seitenabruf wurde hier mit 403 abgewiesen. Keine Umgehung. |

## Schnittstellen und Zugang

| Quelle | Maschinenlesbarkeit | Identität / Zeit | Kosten, Limits, Stabilität | Entscheidung |
| --- | --- | --- | --- | --- |
| Morgan Stanley Emittent | Die Produktseite konfiguriert Lightstreamer über `push-morganstanley.adesso-financial.de`, Adapter `SmarthouseFeed`. Produkt-Stream-Identität im konkreten HTML: `X00000D0400DE000MJ7DUX3`. Separates JSON-Initialobjekt enthält u.a. den Schlusswert, aber keinen vollständigen Bid-/Ask-Snapshot mit Datum. | Produkt- und Basiswert-Stream sind getrennt; ISIN/WKN gegen Stammdaten prüfen. Kein Zeitpunkt aus Abrufzeit oder undatiertem `_close` erfinden. | Kein veröffentlichter API-Vertrag, Preis oder verbindliches Abruflimit in den geprüften Seiten gefunden. Seitentoken ist kein API-Abonnement; weder verwenden noch speichern/committen. [Nutzungsbedingungen](https://zertifikate.morganstanley.com/nutzungsbedingungen/) und Seitenfooter enthalten Nutzungsvorbehalte. | Technisch stärkster Emittenten-Kandidat für die zehn MS-Produkte. Vor dauerhaftem Zugriff schriftlich privaten automatisierten Abruf und lokale Speicherung sowie ein unterstütztes API-/Stream-Verfahren klären. Kein HTML-Zahlen-Scraper implementiert. |
| JPMorgan Emittent | Öffentlicher JS-Code verweist auf `/api/v1/SuggestSearch/CheckIfProductIdOrName` und produktabhängige Detail-JSON-Abfragen. Kein funktionsfähiger, stabiler Quote-Endpunkt für die betroffenen ISINs verifiziert. | Exaktes Produkt und vollständiger Quote-Zeitstempel müssen im Payload bestätigt werden; reine Uhrzeit genügt nicht. | Kein bestätigter API-Tarif oder Limit; Website kann Disclaimer-/Sitzungszustand benötigen. [Nutzungsbedingungen](https://www.jpmorgan-zertifikate.de/nutzungsbedingungen/) prüfen lassen. | Offiziellen Quote-/Datenzugang mit den acht ISINs anfragen; bis dahin fehlende Abdeckung transparent lassen. |
| UniCredit onemarkets | Offizielle Produktdaten/KID vorhanden, aber kein nutzbarer strukturierter Quote-Payload im geprüften Zugriff. | Identität `DE000UN37224` bestätigt; Quote-Endpunkt und Zeitbasis offen. | Keine belastbare Kosten- oder API-Limitangabe gefunden. Öffentlicher Website-Zugang ist kein zugesagter Datenfeed. | Unterstützten privaten Quote-Zugang bei onemarkets klären; Stuttgart als alternative Abdeckung nachgewiesen. |
| Stuttgart / EASY EUWAX | Offizielle Website-Quotes für MS/UC nachgewiesen; automatisierte Website-Requests hier 403. Der vorhandene delayed-Adapter ist ein anderer Datenkanal. | XSTU und EASY EUWAX nicht in einen erfundenen Provider-/MIC-Code umdeuten. ISIN-Abdeckung am angebotenen Feed prüfen. | Kosten und Nutzungsrecht hängen vom tatsächlich angebotenen Datenprodukt ab. Ein kostenfreies Website-Angebot beweist keine freie Feed-/Redistributionslizenz. | Unterstützten Pre-Trade-Feed/API für diese ISINs und EASY EUWAX bestätigen lassen. Kein Umgehen von Zugriffssperren. |

Die Recherche rechtfertigt keine pauschale Aktivierung eines neuen Providers. Priorität:
verifizierter Emittenten-Quote, anschließend bestätigter Börsenfeed. Frankfurt bleibt
für nachgewiesene LAST_TRADE-/Schlusskurs-Abdeckung als indikative Quelle erhalten.
Vorhandene erfolgreiche Beobachtungen werden unabhängig davon dauerhaft aufbewahrt,
siehe [Kursaufbewahrung und Korrektur](retained-warrant-quotes.md).

Für eine Anbieterklärung konkret angeben: rein privates lokales Positionsmonitoring,
keine Weitergabe, diese ISIN-Liste, gewünschtes Intervall (derzeit 300 s je Optionsschein),
Bid/Ask plus vollständiger Zeitstempel/Zeitzone, Handelsstatus, deklarierter Delay,
Speicherung des letzten erfolgreichen Datensatzes über Ausfälle/Neustarts hinweg.
Benötigt werden Endpunkt/Stream-Vertrag, Identifikation, erlaubte Abrufrate, Authentisierung,
Speicherrecht und gegebenenfalls ein verbindlicher Preis. Es wurde kein kostenpflichtiger
Zugang bestellt und es wurde keine Nachricht an Anbieter versendet.

## Betroffene ISINs für eine Deckungsprüfung

- MS: DE000MM02AF0, DE000MJ3QMM4, DE000MJ3QFV9, DE000MK8B3F2,
  DE000MN50FN0, DE000MN2ZUN2, DE000MN25S42, DE000MM02M95,
  DE000MJ7DUX3, DE000MM34MJ0.
- JPM: DE000JY557T1, DE000JE85E17, DE000JZ0V6V0, DE000JZ91459,
  DE000JY27NF1, DE000JY10A58, DE000JE7KTY8, DE000JY3SF71.
- UC: DE000UN37224.

Dies sind Kennungen aus der übergebenen Diagnose. Die Tabelle weist die tatsächlich
geprüften Beispiele aus; vollständige Feed-Abdeckung aller 19 Produkte ist noch nicht belegt.
