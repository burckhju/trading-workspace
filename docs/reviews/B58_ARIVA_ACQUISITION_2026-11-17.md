# B58: ARIVA-Beschaffungsprüfung vom 17.11.2026

## Aussage und Geltungsbereich

**Kein zugänglicher Pfad ist positiv B58-qualifiziert.** Ergänzung zum
[historischen Quellenbefund](B58_SOURCE_QUALIFICATION_2026-11-17.md), keine
Kaufempfehlung; Aufgabenstatus nur im [Backlog](../planning/PRODUCT_BACKLOG.md).
PC-Depot, Lizenzen und Providerzugänge waren hier unzugänglich. Die vom Nutzer
bestätigte Installation v1.5.47 beweist keine Quellenqualifikation. Öffentliche
Prüfinstrumente belegen keine Depotabdeckung. Keine Anmeldung, Tokenanforderung,
Kontaktaufnahme, Bestellung, Zustimmung oder produktive Aktivierung erfolgte.

## 1. Produktbezogene Auswahl

Die [DB-Produktseite][db-product] nennt für **Börse Frankfurt Certificates and
Warrants** Optionsscheine und bestes BID/ASK; Xetra Core enthält diese
Produktinformationen **ohne** bestes BID/ASK. ARIVA ist [offizieller Vendor][db-ariva]
für das Produkt in Real-time und Delayed. Das belegt ein Angebot, keine
Clientlieferung. [Kleine Pakete/Testzugänge][ariva-faq] sind auf Anfrage möglich;
konkrete Kosten, Rechte und Lieferumfang fehlen.

Die [Feedmatrix][db-feeds] führt Frankfurt-Optionsscheine bei Cloud Stream
nicht auf: kein generischer Cloud-Zugang für diesen Beschaffungsschritt.
Allgemeine Statusschemas ersetzen Produktdeckung nicht. Ein kostenloses
DB-Datenprodukt belegt keinen kostenlosen Vendorzugang oder Nutzungsrechte.

## 2. Tatsächlich gelesene technische Primärbelege

| Dokument | Originalabruf UTC | Ergebnis und SHA-256 |
| --- | --- | --- |
| [ARIVA OpenAPI][openapi] | 2026-11-17T09:26:13.147766Z | HTTP 200; 465056 Bytes; Version 0.6.25; `3444a4ab7c787cb2169d8efc8f20e2dc2c26c3af04e8ff7116cd43f6b2d097ff` |
| [ARIVA OIDC-Discovery][oidc] | 2026-11-17T09:33:48.740739Z | HTTP 200; 6180 Bytes; `fdeb22259973ee936cbf2681227424678032d062f17625f088c9cf2e8040d766` |

Weitere Primärseiten: gelesen am 17.11.2026, ohne erfasste Uhrzeit/Hash.

API-Basis: `https://mds.ariva-services.de/api/v1`. Die OpenAPI dokumentiert
`XSC` als Quellencode für Zertifikate Börse Frankfurt, nicht als ISO-MIC.
`instrumentId` akzeptiert die gespeicherte ISIN unmittelbar.

| Zweck | Dokumentierter GET-Pfad relativ zur API-Basis |
| --- | --- |
| Quelle/MIC prüfen | `/sources/XSC`: insbesondere `sourceId`, `operatingMic` |
| Listings gezielt entdecken | `/instruments/{isin}/listings?sourceId=XSC`: `items` mit `ListingdataWithIdAndQuality` |
| Einzelnes Listing prüfen | `/marketstates/{isin}/XSC/listing?listingVariant={variant}` |
| Gezielter Snapshot mehrerer vorhandener Instrumente | `/marketstates/` mit wiederholtem `marketstateQuery={isin}@XSC` und `quality=REALTIME`; alle Varianten an der fest genannten Quelle, keine Auswahl einer Variante |
| Snapshot/Instrumentstream | `/marketstates/{isin}/XSC?listingVariant={variant}&currency={currency}&quality=REALTIME`; JSON oder SSE, bei SSE optional `delta=true` |
| Feed initialisieren/fortsetzen | `/feeds/marketstates/XSC/initial-load?quality=REALTIME` und `/feeds/marketstates/XSC/delta?quality=REALTIME` |

`segmentMic`, Währung und `listingVariant` müssen zum vorhandenen Listing
passen; die Variante ist nicht zwingend eine Währung. Keine MIC-Annahme oder
Umstellung eines Emittentenlistings auf XSC. `quality=REALTIME` ausdrücklich
verlangen und prüfen; der Default kann DELAYED sein.

SSE: `Accept: text/event-stream`; `delta=true` liefert nach dem Initialbestand
geänderte Blöcke. Response: `MarketstateWithId` oder `Heartbeat`; nur die
Feedendpunkte dokumentieren zusätzlich `ContinuationToken` und den Requestheader
`ARIVA-MDS-Continuation-Token` zum Wiederanlauf. Feed-`filters` wählen Datenblöcke,
keinen belegten Instrumentfilter. Kein unbegrenztes Source-Feed-Abonnement als
vermeintlich kleine Instrumentprobe.

**Lücke:** `bid.datetime` hat eine generische Beschreibung; `Status` und seine
Hülle enthalten keine eigene Statuszeit. Heartbeat-Zeit und Listing-`changedAt`
ersetzen sie nicht. ACTIVE beweist kein OPEN. Status-only-Lieferung und
Recoverysemantik für XSC bleiben ungeklärt; siehe Anfrage.

Die OIDC-Discovery bestätigt `client_credentials` und unter anderem
`client_secret_basic`/`client_secret_post` am Token-Endpunkt
`https://auth.ariva-services.de/auth/realms/mds/protocol/openid-connect/token`.
Berechtigter Bearer-Token oder freigeschalteter Client ermöglichen den Probezugang,
keine Qualifikation; Secrets nicht in URLs/Logs. Dokumentiert: HTTP 200 sowie
allgemein 401/erneute Autorisierung. Fehlerschema, 403-/429-Verhalten, Quoten
und Retry-After-Vertrag fehlen.

## 3. Kleinster Evaluationsumfang und unversandter Anfrageentwurf

Vorbereitung: maximal **64 tatsächlich vorhandene ISINs**, rein lesender Export
des Depot-/Produktowners samt Listing/Währung, keine manuellen IDs.
Die Liste liegt hier noch nicht vor; Depotabdeckung bleibt zu prüfen.

**Anfrageentwurf — nicht versendet; keine Bestellung oder Zustimmung:**

> Wir möchten unverbindlich ARIVA MDS für private automatisierte Depotüberwachung
> evaluieren: „Börse Frankfurt Certificates and Warrants / Real-time“, XSC.
> Maximal 64 vorhandene ISINs mit Listing/Währung werden automatisch exportiert.
> Bitte nennen Sie Umfang, Kosten, Laufzeit, Grenzen und Nutzungsfreigaben.
>
> Benötigt werden ursprünglicher BID und seine eigene Quellzeit sowie ein
> instrument-/listingbezogener Marktstatus mit eigener Originalzeit. Bitte
> belegen Sie mit Feldbeschreibung und unveränderten Originalproben,
> wie ASK-/Last-Änderungen die BID-Zeit behandeln und ob Statuszeiten eine
> Beobachtung oder einen Zustandswechsel mit definierter Wirkung bezeichnen.
> Bitte erläutern Sie Beginn/Ende dieser Aussage einschließlich Zeitzone,
> Präzision, Widerruf und Korrektur.
>
> Bitte liefern Sie negative/preislose Originalmeldungen desselben Listings
> und erklären Sie ausgelassene, gelöschte und unveränderte
> Preisblöcke. Für Initialbestand, Delta und Wiederanlauf benötigen wir
> Sequenz-/Tokenbereich, Replaydauer, Ablauf, Reset, Lückenerkennung, Duplikate
> und verspätete Ereignisse samt unterbrochener/fortgesetzter Beispielsequenz.
> Bitte begrenzen Sie die Lieferung möglichst auf diese Instrumente.
>
> Bitte bestätigen Sie tatsächliche Verzögerungen/Netting, Abruf- und
> Verbindungsgrenzen sowie die zulässige automatisierte interne Auswertung und
> lokale Speicherung der benötigten Fakten. Falls die Standard-API die
> Status-Originalzeit nicht überträgt, nennen Sie die kleinste zusätzliche
> Lieferung. Ein Key allein genügt nicht. Dies ist kein Beschaffungsauftrag.

Die [DB-Beschaffungsbeschreibung][db-order] nennt Nutzungsdeklaration/Freigabe
und gegebenenfalls Non-Display-Vertrag; die konkrete Einordnung bleibt offen.
Kein Ersatz durch Kalender, Empfangszeit oder Nutzerbestätigung. Die 900 Sekunden
betreffen ausschließlich BID-Alter, keine Statusgültigkeit.

## 4. Ergänzende echte öffentliche Befunde

Die folgenden Abrufe wurden unabhängig im parallelen Quellenreview erhoben:

- [Frankfurt-Einzelinstrument][frankfurt-probe],
  2026-11-17T09:24:30.052543Z: HTTP 200, 559 Bytes,
  SHA-256 `efdc1ecda0bec8149f877afe24a226b54167fe4a1a59c6ff0cf2cb1a475e5208`.
  `DE000VH2LU21`, EUR, Last 0.146 mit
  `timestampLastPrice=2026-11-17T10:14:30+01:00`; kein BID und kein
  Instrumentstatus mit eigener Zeit. Aktualisierter Last-Pfad, kein B58-Beleg.
- [Stuttgart-Originaldatei][stuttgart-probe], verlinkt im
  [offiziellen Aussetzungsindex][stuttgart-index],
  2026-11-17T09:30:17.409420Z: HTTP 200, 920 Bytes,
  SHA-256 `5c7792e0422a06ac9c4448f5c979092b752a2481fd265e06932c6f2be4709192`.
  `DE000DN61D78`, Venue STUB, Aussetzung, `Ongoing=true`; Publication und
  Effective-from jeweils `2026-11-11T09:03:59`, Effective-to leer.
  Reale negative/preislose Einzelmeldung; ohne Offset ist die tatsächliche
  Zeitzone dieser CSV nicht bewiesen. Kein BID/OPEN, kein belegter vollständiger
  Statusstrom, Replayvertrag oder Depotbezug. Keine Zeitzone aus einer Norm
  ergänzen und kein fremdes Listing als XSC-Status verwenden.
- [Morgan-Stanley-Produktseite][ms-probe],
  2026-11-17T09:33:48.437319Z: HTTP 200, 62839 Bytes,
  SHA-256 `d8e8b86e9b62e687875180daeb577ac76666f54447205e4dafcec1614a636719`.
  `DE000MJ3QFV9`, EUR, BID `0,003`, ASK fehlt; beide Seiten verwenden denselben
  `lastquotetimestamp=17.11.2026 10:31:33` ohne Offset. Ein realer BID ist
  vorhanden, eigene BID-Zeitbedeutung/Zeitzone und Instrumentstatuszeit sind
  nicht belegt. `status_timestamp`/`SUSPENDED` im öffentlich verlinkten Bundle
  gehören zur Lightstreamer-Geräte-/Pushverwaltung, nicht zum Instrument;
  siehe [primären MPN-Vertrag][lightstreamer-mpn].
- [JPMorgan-Produktpfad][jpm-probe], 2026-11-17T09:33:49.512798Z:
  HTTP 200, 30243 Bytes,
  SHA-256 `f3088f5a496e5d200049c2237ea9f3e49b4ce95aae7bf11da7938e69da99add2`.
  Tatsächlich wurde eine Zustimmungsseite geliefert, kein Produktpayload.
  Die dort öffentlich verlinkten Bundles belegen keinen instrumentbezogenen
  Status mit eigener Originalzeit. Keine neue Zustimmung oder Produktsession.
  Diese Prüfung sagt nichts über einen eventuell bereits bestehenden
  Consent-Zustand auf dem Nutzer-PC aus.

## 5. Abgrenzung der vorbereiteten Umsetzung

Die CLI `app.tools.probe_ariva_b58` liest den vorhandenen passiven
Positionscoverage-Endpunkt auf Loopback und übernimmt dessen Instrumente und
Quellenbindungen. Sie greift nicht auf den aktualisierenden Quote-GET zu.
Die Produktionsregistry bleibt leer; keine Regelaktivierung. Zeitlücke,
Bindungskonflikt oder Transportfehler werden kein OPEN/CLOSED. Freigabe erst
mit belegter Lieferung, versioniertem Vertrag und Betriebsabnahme.

Aus einem Backend mit diesem Entwicklungsschnitt:

```bash
python -m app.tools.probe_ariva_b58
python -m app.tools.probe_ariva_b58 --fetch
```

Der erste Aufruf erstellt nur einen Plan ohne Anbieteraufruf oder Secretzugriff.
Der zweite erfordert die einmalig sicher bereitgestellten Umgebungswerte
`ARIVA_MDS_CLIENT_ID` und `ARIVA_MDS_CLIENT_SECRET` eines ausdrücklich
berechtigten Evaluationsclients. Er bezieht den Token automatisch und verwendet
die dokumentierten Originalendpunkte. Vorhandene Zugangswerte sind kein
Nutzungsrechtsnachweis. Kein Token oder Clientsecret gehört in Chat,
Kommandozeilenargumente oder den Prüfbericht. Es wurden hier keine solchen
Zugänge verwendet und keine echten OAuth-Token angefordert.

Der Bericht entsteht exklusiv mit Dateimodus `0600`, standardmäßig im lokalen
Tempverzeichnis; `--output` kann einen neuen privaten Zielpfad bestimmen.
Im Container ist das zunächst ein Containerpfad, kein automatisch auf den
PC-Desktop exportiertes Dokument. Bestehende Dateien werden nicht überschrieben.
Planerfolg hat Exitcode 0; fehlende Voraussetzungen und jeder weiterhin
unqualifizierte reale Abruf haben Exitcode 2. **Kein Erfolgs-/Exitcode dieses
Werkzeugs aktiviert B58.**

Originale erfolgreiche Quell-/Marketstate-/Listingantworten werden mit eigenem
Abrufzeitpunkt, URL, unverändertem UTF-8-Body und Hash erhalten. Fehlerantworten,
Tokenantworten und Zugangsdaten werden nicht gespeichert. Negative/preislose
Statusfelder bleiben erhalten, aber ohne belegte eigene Zeit unqualifiziert.
Der Vergleich mit gespeicherten Listingdaten stellt nur die nächsten
Qualifikationsfragen zusammen; er bestätigt keine historische Kaufwährung,
Ausführbarkeit oder unveränderten aktuellen Positionsbestand.

Ein solcher einmaliger Beschaffungsprüfer ist kein wiederkehrender
Monitoringbetrieb. Nach der belegten Lieferantenqualifikation benötigt der
produktive Adapter den ausdrücklichen Status-/Wiederanlaufvertrag und Anschluss
an den bestehenden Market-Data-Owner; B04/B57 und seine Episodenlogik bestehen
bereits. Der [Integrationsnachtrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b58-ariva-acquisition-probe-v1)
grenzt diesen Schnitt ab. Regelmäßige manuelle Tokens, Statusbestätigungen oder
erneute Depotdatenerfassung sind kein vorgesehener Betriebsweg.

[db-product]: https://www.mds.deutsche-boerse.com/mds-en/real-time-data/spot-markets/B-rse-Frankfurt-Certificates-and-Warrants-1341024
[db-ariva]: https://www.mds.deutsche-boerse.com/mds-en/real-time-data/vendorlist/ARIVA.DE-AG-1739678
[db-feeds]: https://www.mds.deutsche-boerse.com/mds-en/real-time-data/Real-time-data-feeds
[ariva-faq]: https://ariva.ag/f-a-q/
[openapi]: https://mds.ariva-services.de/swagger-ui/openapi.yml
[oidc]: https://auth.ariva-services.de/auth/realms/mds/.well-known/openid-configuration
[db-order]: https://www.mds.deutsche-boerse.com/mds-en/real-time-data/how-to-order-data/How-to-order-data-1333842
[frankfurt-probe]: https://api.live.deutsche-boerse.com/v1/data/price_information/single?isin=DE000VH2LU21&mic=XSC
[stuttgart-probe]: https://download.boerse-stuttgart.de/sar/2026/11/11/BSSAR_WEB_DE000DN61D78_20261111090359.csv
[stuttgart-index]: https://www.boerse-stuttgart.de/de-de/fuer-geschaeftspartner/reports/handelsaussetzungen-und-ausschluesse/
[ms-probe]: https://zertifikate.morganstanley.com/produktdetails/de000mj3qfv9
[lightstreamer-mpn]: https://sdk.lightstreamer.com/ls-web-client/9.2.1/api/MpnDevice.html
[jpm-probe]: https://www.jpmorgan-zertifikate.de/zertifikate-detail/DE000JE7KTY8
