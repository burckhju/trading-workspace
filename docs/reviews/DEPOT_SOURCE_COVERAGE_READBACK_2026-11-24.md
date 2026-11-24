# Quellenkandidaten: tatsächlicher PC-Readback und Beschaffungsbefund — 24.11.2026

## Ergebnis und Geltungsbereich

**Der Quellenkandidatenexport ist erfolgreich ausgeführt und ausgewertet.**
P01, P03 und P04 sind weiterhin offen und eindeutig an dieselben archivierten
Positionen und Produkte gebunden. Alle drei haben unverändert keine ausgewählte
Kursquelle, keine gespeicherten Auswahlkandidaten und keine vom Coverage-Owner
ausgegebene Mappingroute. Der neueste gespeicherte V2-Entscheid ist jeweils
`UNAVAILABLE`. Zusätzlich fehlen belegte aktuelle Preiseinheiten; P04 hat
einen Produkt-/Basiswertkonflikt und keine verwendbare V2-Referenzkalenderdeckung.

Die KID-Beschaffung ist bei allen drei Positionen **erfolgreich**. Die spätere
[P01-Originalprüfung](#p01-originaleinheit) von **21:07 Uhr** klärt die bisher
offene Ursache: Das bytegleiche KID enthält keine ausdrückliche Preiseinheit;
`unit=null` ist dafür korrekt. Ein Parserfix wäre unbegründet. Für P03/P04
wird dieser Einzelbefund nicht übernommen. Ein zusätzlicher aktueller
Listing-Einheitenbeleg lässt sich aus dem offiziellen gettex-Regelwerk und
der exakt gebundenen Originalquelle vorbereiten; sein Product-Anschluss
fehlt noch. Die vollständige gettex-Dateiprobe bleibt von den gespeicherten
PC-Verbraucherbefunden getrennt.

Die letzte vollständige Inventur bleibt der
[Gesamtread vom 22.11.](DEPOT_DATA_READBACK_2026-11-22.md). Der heutige enge
Read umfasst die drei archivierten Kandidaten, nicht P02 oder neue Positionen.
Der [P02-Nachweis von 18:23 Uhr](P02_SOURCE_GAP_READBACK_2026-11-24.md) behält
seinen eigenen Zeitpunkt. Daraus wird keine heutige Gesamt-Abdeckungsquote
gebildet. Private Kennungen, Produkt-URLs, Preise, Mengen und Originaldateien
bleiben außerhalb des Repositories. Arbeitsstatus und genau ein aktueller
Auftrag stehen ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

## 1. Software, Sammlung und Integrität

Alle folgenden lokalen Uhrzeiten sind MEZ, also UTC+1.

| Gegenstand | Tatsächlich geprüft | Grenze |
| --- | --- | --- |
| Main und PC | `9a5e59dac3bb219cbc40641e62e75871eb2ed131`, v1.5.54 | Offener PR #370 und seine Tests sind weiterhin getrennt von der installierten App. |
| Installation vor/nach | Beide Dateien bytegleich; vier laufende gesunde Dienste | Revision-, Image- und Containerbindung; keine vollständige Konfigurationsprüfung. |
| Schema | `20261118_0060`, tatsächlicher lesender DB-Read | Identisch zur geprüften Referenz. |
| Sammlung | **24.11.2026, 20:33:55.944–20:33:58.490 Uhr** | UTC `19:33:55.944034–19:33:58.490047`. |
| Fachlicher DB-Lesestichtag | **20:33:57.754314 Uhr** | `REPEATABLE READ READ ONLY` tatsächlich bestätigt. |
| Umfang | P01/P03/P04, je `OPEN`, `ARCHIVED_POSITION_AND_PRODUCT_MATCH` | Archivlabels aus dem vollständigen alten Paket, nicht heutige Listenreihenfolge. |
| Gesamtstatus | `COMPLETE_PASSIVE_SOURCE_COVERAGE_READ_NOT_RULE_QUALIFICATION` | Vollständiger gebundener Lesetransport, keine neue Regelabnahme. |

Der unveränderte [Collector](../../scripts/collect-depot-data-supply.py)
validiert das Ergebnis gegen die neu aus dem Originalarchiv abgeleitete
Referenz: `source_coverage_complete(...) == True`. Payload-SHA256
`a1dc7c644ec99a0c3b5715fd220f996ac4c64a0a1b590cd2a6a9acd77d693721`
entspricht der [ausgelieferten Fassung](DEPOT_SOURCE_COVERAGE_COLLECTOR_2026-11-24.md).
`global_atomic_snapshot=false` bleibt erhalten: Coverage-GETs, Schema,
Installation und DB-Snapshot haben eigene Lesezeiten. Vor-/Nach-Bindungen
sind unverändert; Quellenpreise wurden durch diesen Collector nicht abgerufen.

| Privater Beleg | SHA256 |
| --- | --- |
| Neues Archiv | `9a23bdb3adb04987a3f14aa2ca932965d13f81e264bf4b0267b962cd1e5be291` |
| `source-coverage-private.json` | `11c852c89cb7a8fff0ad3937c7c1ee40d94f1c06aa3e8ae3074144df17b8a7fb` |
| Installation vor und nach | `21a5702d31ed740b629197635b90757cc9d3d20b23e95b6716b521c4319fa360` |
| `schema.json` | `61550140657c5d912d594f48d2446b0daff98b06ab29ae3600973f0e7d2902d7` |
| `summary.json` | `006b358efbbe88d9fad8cc662906c36c06303cb1f67d063d576e87d340efc43c` |

## 2. Konkrete Positionsbefunde

Die JSON-Nachweise liegen jeweils unter `positions[position_label=…]`.
`current_assessment` bezeichnet den gespeicherten Familien-Kettenkopf, keinen
durch die Diagnose neu berechneten Entscheid.

| Label / Emittent | Quelle und Kandidaten | Aktueller Product-Owner | Gespeicherte V2-Bewertung |
| --- | --- | --- | --- |
| P01 / BNP Paribas | `NO_VERIFIED_QUOTE_SOURCE`; je 0 verified/allowed/eligible Kandidaten; `routes=[]` | KID vorhanden, Beschaffung `AVAILABLE`, Produkt- und Basiswertkennung passen; EUR, `unit=null`, daher `PRODUCT_REVIEW_UNIT_UNPROVEN` | 24.11., **18:21:36.448610**, `UNAVAILABLE`: fehlende bestätigte Quelle, fehlende Einheit und `REVIEW_CURRENT_PRODUCT_UNIT_CURRENCY_MISMATCH` |
| P03 / BNP Paribas | Derselbe Quellenbefund; je 0 Kandidaten; `routes=[]` | KID vorhanden, Beschaffung `AVAILABLE`, Produkt- und Basiswertkennung passen; EUR, `unit=null` | 24.11., **18:21:33.672176**, `UNAVAILABLE`, dieselben drei Gründe wie P01 |
| P04 / UniCredit | Derselbe Quellenbefund; je 0 Kandidaten; `routes=[]` | KID vorhanden, Beschaffung `AVAILABLE`; Produktkennung passt, extrahierte Basiswertkennung weicht von der gespeicherten ab; EUR, `unit=null`; Product-Evidenz `UNSUITABLE` | 24.11., **18:21:35.425427**, `UNAVAILABLE`: fehlende Quelle, `PRODUCT_DOCUMENT_UNDERLYING_MISMATCH`, fehlende Einheit und `REVIEW_REFERENCE_CALENDAR_NOT_COVERED` |

Bei allen drei Positionen enthält der aktuelle Bewertungsinput keinen
gespeicherten Quote, keinen Provider und keine Quote-Empfangszeit;
`selection_policy` und `status_observations` sind leer. Ein Zeitstempelproblem
eines tatsächlich ausgewählten Preises ist hier deshalb nicht die erste
Sperre. Die separate aktuelle Refreshprojektion meldet jeweils um
**20:31:11 Uhr** `MISSING` / `NO_USABLE_WARRANT_QUOTE`, Coverage
`NO_USABLE_ROUTE`. Das ist keine neue Provider-HTTP-Fehlerdiagnose.

### Was die leeren Kandidaten tatsächlich beweisen

Die persistierte Auswahl hat noch dieselben IDs, Zeiten und Inhalte wie im
Archiv. Ihre historische erlaubte Providerliste enthält Frankfurt, gettex,
JPMorgan und Morgan Stanley. Bereits `verified_candidates` ist leer; damit ist
kein damaliger Allowlist- oder Währungsfilter als Ausschluss eines vorhandenen
Kandidaten nachgewiesen. Die Auswahlzeiten aus Oktober beweisen auch keinen
ausgebliebenen Abgleich: `PositionQuoteSourceSelector._create` erhält eine
unveränderte negative Entscheidung idempotent
([Auswahlowner](../../backend/app/features/market_data/service/position_quote_source.py)).

Die aktuelle [Coverage-Persistenzprojektion](../../backend/app/features/market_data/persistence/quote_coverage.py)
berücksichtigt auch unbrauchbare Mappingrouten. `routes=[]` ist daher ein
konkreter fehlender Mappingbefund, kein bloß aus einer Ansicht ausgefilterter
veralteter Quote. Er beweist weder ein fehlendes gettex-Angebot noch das Fehlen
eines **ungemappten** Produktlistings. Letzteres liest der vorhandene
Product-GET `/api/v1/warrants/{warrant_id}/listings`.

Aktuell konfigurierte Quellen sind Morgan Stanley, JPMorgan, Frankfurt und
gettex. Allgemein ist dies keine vollständig ausgelesene aktuelle Allowlist.
Für gettex ergibt sich jedoch aus
[quote_sources](../../backend/app/features/position_monitoring/service/quote_sources.py)
und [provider_eligibility](../../backend/app/features/market_data/service/provider_eligibility.py)
dieselbe technische Voraussetzung: der vorhandene gettex-Container.
Dies ist eine Codeinferenz zur technischen Eligibility, kein neuer externer
Nutzungsrechtsnachweis. Das Feld `issuer_probe_eligible` beschreibt hier nur
die Vontobel-Probe. `false` für BNP/UniCredit bewertet weder deren allgemeinen
Emittentenzugang noch die gettex-Verfügbarkeit
([Coverage-Service](../../backend/app/features/market_data/service/quote_coverage.py)).
Leere `discovery_reasons` sind keine vollständige historische Abrufdiagnose.

## 3. Dokumente, Einheiten und Kalender

Die drei aktuellen KIDs wurden am 24.11. gegen **18:21:33–36 Uhr** gespeichert
und mit `current-product-document-v2` verarbeitet. Beschaffungszustand ist
jeweils `AVAILABLE`, `problems=[]`; der nächste reguläre Beschaffungszeitpunkt
liegt am Folgetag. Das ist ein erfolgreicher Dokumentweg bis zu gespeicherten
Parserfakten, jedoch keine vollständige fachliche Eignung.
Bei allen drei Positionen stimmen aktuelle Product-Revision und Fingerprint
mit der im jüngeren V2-Head verwendeten `current_unit_evidence` überein;
die Einheits-/Konfliktbefunde sind keine bloß überholten Bewertungsgründe.

Der [Product-Reader](../../backend/app/features/product/service/review_evidence.py)
verlangt ausdrücklich `unit=CURRENCY_PER_WARRANT`. Bei P01/P03 genügen
Produktwährung und richtige Identität noch nicht, weil `unit=null` bleibt.
Auch `REVIEW_CURRENT_PRODUCT_UNIT_CURRENCY_MISMATCH` beweist für sich keinen
falschen EUR-Kurs: Der
[V2-Maßstabsvergleich](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py)
erzeugt diesen kombinierten Code bereits bei fehlender Einheit.

Für P01/P03 ist der freigegebene V2-Referenzkalenderpfad bereits `AVAILABLE`,
die 20-Sitzungen-Schwelle im gespeicherten Entscheid erreicht; Qualität
`CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED`. Dies ist keine ursprüngliche
historische Listing-/Kalenderbindung. Strenge historische Maßstabsbelege
bleiben `MISSING`. P04 benötigt zusätzlich die Auflösung des dokumentierten
Basiswertkonflikts und eine tatsächlich geeignete Referenzkalenderdeckung.
Welche Konfliktseite falsch ist, ist ohne Originalprüfung nicht entschieden;
kein automatisches Überschreiben der Stammdaten.

<a id="p01-originaleinheit"></a>
### P01: Originalprüfung und eindeutige Ursache

Der Nutzer hat nach der vorherigen automatischen Ablehnung die Übermittlung
der P01-Produktkennung an `kid.bnpparibas.com` ausdrücklich freigegeben.
Der einmalige lesende Abruf ist abgeschlossen; dafür ist keine weitere
Zustimmung oder erneute Bereitstellung desselben KID erforderlich.

| Nachweis | Tatsächlich geprüft |
| --- | --- |
| Originalabruf | **24.11.2026, 21:07:13.255979 Uhr MEZ** gespeichert; HTTP 200, 55.633 Bytes, drei PDF-Seiten; kein Redirect, Begrenzung auf die vorhandenen 2.000.000 Bytes |
| Herkunft und Integrität | Aus dem bestehenden `kid_url` abgeleitete Quellenreferenz entspricht beiden gespeicherten Referenzhashes; PDF-SHA256 entspricht exakt dem KID- und Product-Review-Hash des PC-Reads |
| Produktbindung | Produkt- und Basiswertkennung stimmen mit dem archivgebundenen P01-Produkt überein; Produktwährung EUR |
| Verbraucherparser | Unverändertes `current-product-document-v2` auf denselben Originalbytes: `unit=null` |
| Inhalt | Vollständiger Text und alle drei gerenderten Seiten geprüft; unabhängige zweite Textprüfung mit demselben Ergebnis |
| Privater Prüfbeleg | `p01-original-unit-review-private.json`, SHA256 `83c0c6a84d8fcf38c4d4bd2484df5f2a3e44a2e0f91ada06759813cf8e9f913d`; Original, Produktkennung und individuelle Quellenadresse bleiben privat |

| Seite | Für die Einheit relevantes Ergebnis |
| --- | --- |
| 1 | Produktart, Währung, Bezugsverhältnis und Auszahlungsregeln; keine ausdrückliche Stücknotierung oder unmittelbare Preisangabe je Optionsschein. Der Referenzpreis betrifft den Basiswert. |
| 2 | Beispielanlage und Performance-Szenarien; keine Notierungseinheit eines einzelnen Produkts. |
| 3 | Anlagekosten, Ausübung und allgemeiner Sekundärmarktverkauf; keine zusätzliche Stückpreisdefinition. |

**Ursache ist ein fehlendes Quelldatum in diesem KID, kein nachgewiesener
Extraktionsfehler.** Der [Parser](../../backend/app/providers/product_review_documents.py)
und seine Revision bleiben unverändert. Ein erneuter Download oder Reparse
derselben Originalbytes würde diese Lücke nicht schließen. Dieser Befund
belegt weder die Originaleinheit von P03/P04 noch eine neue P01-Bewertung.

<a id="gettex-listingeinheit"></a>
### Ergänzender aktueller Listing-Einheitenbeleg

Am 24.11. wurden die tatsächlich auf der offiziellen
[Regelwerkseite](https://www.gettex.de/handel/regelwerk) verlinkten Fassungen
gelesen, nicht lediglich ein älterer Suchtreffer:

| Primärquelle und Fundstelle | Belastbarer Beitrag |
| --- | --- |
| [Börsenordnung, Stand 02.11.2026](https://www.gettex.de/fileadmin/Regelwerke/261102_Boersenordnung.pdf), § 55, Seite 43 | Market-Maker-Quotes enthalten Produktkennung, Preis je Stück, Seite und Volumen; für Rententitel gilt die gesonderte Prozentnotierung. |
| Dieselbe Börsenordnung, § 34, Seite 28; § 63 Abs. 2, Seite 46 | Derivative Produktklassen sind gesondert beschrieben; die gettex-Vorhandelstransparenz veröffentlicht Quotes. |
| [Handelsordnung für den Freiverkehr](https://www.gettex.de/fileadmin/Regelwerke/180103_Handelsordnung_Freiverkehr.pdf), §§ 1 und 2 Abs. 2, Seite 2 | Gilt ausdrücklich auch für gettex; handelsbezogene Börsenordnung und Ausführungsbestimmungen gelten entsprechend. Der gedruckte Stand ist **03.01.2017**, obwohl der Dateiname mit `180103` beginnt. |
| [Ausführungsbestimmungen, Stand 17.01.2025](https://www.gettex.de/fileadmin/user_upload/www.gettex.de/Downloads/Regelwerk/250117_Ausfuehrungsbestimmungen.pdf), § 11 Abs. 2 Buchstabe d, Seite 14 | Hebelprodukte mit Stücknotiz sind von prozentnotierten Anlageprodukten getrennt. |
| [BSW-Produktklassifizierung](https://www.derbsw.de/de/bsw-produktklassifizierung/) | Ordnet Optionsscheine den Hebelprodukten zu; ergänzt die konkrete Produktart aus dem Original-KID. |

**Fachliche Schlussfolgerung aus diesen Quellen:** Die ausdrückliche
Quote-Konvention kann gemeinsam mit der nachgewiesenen Produktklasse und
dem exakten ISIN-/MUND-/EUR-Datensatz einen gesonderten aktuellen
Listing-Einheitenbeleg tragen. Die Einheitenableitung beruht damit auf der
Originalregel und ihrer konkreten Quellenbindung. Sie ist keine pauschale
Annahme aus Optionsschein, Währung oder Bezugsverhältnis. Die
[Dateiprobe](#4-offizieller-gettex-dateidienst-neue-praktische-probe) beweist
die konkrete Zeile, nicht die heutige PC-Route oder eine neue Preisfrische.

Der Text der Regeloriginale war über den Webreader zugänglich. Ein isolierter
direkter Download der aktuellen Börsenordnungs-PDF aus dieser Arbeitsumgebung
antwortete mit **HTTP 403**; kein Umgehungsversuch. Deshalb liegt für diese
Regeldatei hier noch kein importierbarer Originalbyte-/Hashbeleg vor. Dies ist
eine andere Abrufklasse als der erfolgreiche BNP-KID-Read und der erfolgreiche
gettex-Kursdateidownload. Ein dokumentierter Originalimport beziehungsweise
ein geeigneter offizieller Lesezugang schließt genau diese technische Lücke;
eine pauschale Aussage über die Erreichbarkeit vom Nutzer-PC folgt daraus nicht.

### Bestehender Owner und genau abgegrenzter Anschluss

Der [aktuelle Product-Reader](../../backend/app/features/product/service/review_evidence.py)
liest die Einheit ausschließlich aus der KID-Revision. Die
[Dokumentablage](../../backend/app/features/product/persistence/review_evidence.py)
unterstützt bisher `KID` und `LISTING_TERMS`; der bestehende Listingtermsimport
betrifft XSTU-Fristen. Keiner dieser Wege übernimmt bereits den neuen
aktuellen Einheitenbeleg.

Die vorhandene [Preismaßstabs-API](../../backend/app/features/product/api/price_scale_evidence.py)
ist ebenfalls kein freier Ersatz: Ihr
[Vertrag](../../backend/app/features/product/domain/price_scale_evidence.py)
verlangt ein tatsächlich belegtes endliches Intervall; für einen nutzbaren
unveränderten Maßstab außerdem `UNCHANGED_ORIGINAL`. Sperrende Revisionen
mit `ADJUSTMENT_REQUIRED` oder `WITHDRAWN` bleiben ausdrücklich möglich.
Heutige Börsenregeln und eine einzelne Originalquote
belegen keine unveränderte Skala seit den Kauftranchen.

Für den begrenzten V2-Anschluss ist deshalb eine additive aktuelle
Einheitenrevision beim Product-Owner vorzubereiten. Sie bindet Originalregel,
deren dokumentierte Geltung und Fundstelle, Produktklassifikation sowie
nachgewiesene Produkt-/Terms-/Listing-/MIC-/Währungsidentität. KID-Herkunft und
ergänzende Einheitenherkunft bleiben mit eigenen Revisionen, Hashes und Zeiten
getrennt und gehen gemeinsam in den Bewertungsfingerprint ein. Die
[V2-Inputkomposition](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py)
kennt `saved.route` bereits vor dem Product-Read und muss genau diese Route
gegen den zusätzlichen Beleg prüfen. Ein Wechsel zu einem anderen Listing
darf ihn nicht ungeprüft weiterverwenden.

Die 657-MB-Gesamtdatei passt nicht in einen bisherigen 2-MB-Originalimport.
Ein begrenzter Zielnachweis muss deshalb aus der vollständig geprüften Datei
gewonnen und an deren Hash, Dateifenster und Originalzeile gebunden werden;
ein frei behaupteter Dateihash reicht nicht. Die Qualität bleibt
`CURRENT_UNIT_HISTORY_ASSUMED`; KID-Fakten, historische Maßstabsimporte und
bekannte harte Widersprüche bleiben unverändert. Der geltende Vertrag wird
durch diesen Beschaffungsbefund noch nicht erweitert. Umsetzung und
Verbraucherabnahme gehören zum einen Auftrag im Backlog.

## 4. Offizieller gettex-Dateidienst: neue praktische Probe

Die offiziellen Seiten wurden am 24.11. erneut gelesen:
[Pretrade-Dateien](https://www.gettex.de/handel/delayed-data/pretrade-data/),
[Nutzungsbedingungen](https://www.gettex.de/handel/delayed-data/) und
[Emittenten-/Handelsplatz-FAQ](https://www.gettex.de/ueber-gettex/faqs).
Der Download ist für die dort beschriebene private Nutzung kostenlos,
mit bis zu 15 Minuten Verzögerung und UTC-Zeitangaben. BNP und UniCredit
gehören zum genannten Emittentenkreis. Dieses Angebot allein beweist keine
konkrete Produktdeckung; deshalb folgt eine tatsächliche Datei-/Parserprobe.

| Quellenbeleg | Beobachtung |
| --- | --- |
| Offizielle Datei | `pretrade.20261124.18.00.mund.csv.gz` am bestehenden konfigurierten `erdk.bayerische-boerse.de:8000`-Dateipfad |
| Abruf | 24.11., **20:40:50.143–20:41:25.104 Uhr MEZ**, HTTP 200, vollständige Länge 656.912.352 Bytes |
| SHA256 | `e63a856f94409f7390ee2ac8003336e775464aa6ad305f4237997b910796d79a` |
| Datenschutz | Gesamtdatei ohne Produktkennung im Request; Zuordnung ausschließlich anschließend lokal |
| Prüfung | Vorhandener `scan_gzip_quote_batch`, vollständiger GZIP-/CRC-Read mit privater Zielmenge; keine DB-/Mappingänderung |
| Zeitgrenze | Dateifenster **18:45–19:00 Uhr MEZ**; diese ältere Probe belegt keine aktuelle V2-Frische |

Der vorhandene Parser hat die Gesamtdatei einschließlich GZIP-Ende und CRC
erfolgreich geprüft. Der private pseudonymisierte Ergebnisbeleg hat SHA256
`59096d2014eb5054b7438a2e68617bbfb512e5697537f02f0fe949d606ce7663`.

| Ziel | Tatsächliches Ergebnis der vollständigen Datei | Zeit-/Feldqualität |
| --- | --- | --- |
| P01 | `VALID_TARGET_QUOTE`, positiver Bid und Ask vorhanden, EUR/MUND, kein Zielzeilenfehler | Gemeinsame Quellenzeit **24.11., 18:57:23.707737 Uhr MEZ**; keine gesonderte BID-Seitenzeit und kein Instrumentstatus |
| P03 | `TARGET_NOT_PRESENT_IN_FILE`, kein Zielzeilenfehler | Keine Aussage über andere Dateifenster oder generelle gettex-Abdeckung |
| P04 | `TARGET_NOT_PRESENT_IN_FILE`, kein Zielzeilenfehler | Dieselbe enge Aussagegrenze |

Der P01-Treffer ist ein tatsächlich geparster Produktdatensatz, keine Fixture
oder bloße Schemaaussage. Er wurde außerhalb des PC-Datenbestands gelesen und
nicht importiert. Die bewusst gewählte bekannte Datei ist beim Download schon
älter als die V2-Grenze von 1800 Sekunden; dieser Versuch prüft nicht die neueste
Veröffentlichung oder einen gegenwärtig auswertbaren Verbraucherpreis. Die
Kette bis zum tatsächlichen PC-Assessment bleibt daher unvollständig.

Der gemessene Umfang beträgt rund 657 MB für **ein** MUND-Fenster. Ein
kostenloser Preis bedeutet deshalb keinen vernachlässigbaren Betriebsaufwand.
Der vorhandene [Adapter](../../backend/app/providers/gettex_delayed/adapter.py)
teilt Cache und Vollscan je Workspace/MIC/Fenster über die Zielprodukte;
Downloadzeit, Bandbreite, Speichergrenze und automatischer Wiederanlauf müssen
auf dem tatsächlichen PC zur vorgesehenen Taktung passen. Diese Einzelprobe
belegt noch keine Dauerverfügbarkeit.

## 5. Beschaffung bis zum zuständigen Verbraucher

| Fehlende Information / Verbindung | Bestehender Weg und erforderliche Abnahme |
| --- | --- |
| Konkreter gettex-Produktdatensatz | Vollständige Originaldatei mit exakter lokaler ISIN-/MIC-/Währungszuordnung; eigener Parserfehler bleibt ein Ausschlussgrund. |
| Produktlisting und Mapping | Product-Owner `WarrantService.add_listing` für ein belegtes Listing; vorhandenes `configure_gettex_warrant` zunächst als lesende Vorschau. Es legt **kein** fehlendes Listing an und setzt genau ein aktives MUND/MUNC-Listing voraus. |
| Auswahl und wiederkehrender Bid | Bestehender `PositionQuoteSourceSelector`, regulärer Refresh und `RetainedWarrantQuoteProvider`; auf dem PC denselben Produkt-/Listing-/Quellenbezug bis zum gespeicherten V2-Input prüfen. |
| Aktuelle Preiseinheit | P01-KID enthält das Feld nachweislich nicht. Zusätzlichen aktuellen Listing-Einheitenbeleg aus expliziter gettex-Konvention und gebundenem Originaldatensatz beim Product-Owner anschließen; keine KID-Parseränderung. |
| V2-Entscheid | Positiver Bid, passendes Listing/Währung, `source_quote_at` nicht künftig und Alter **≤1800 s** für `DELAYED_SOURCE_BID`, passende Produkteinheit und Sitzungszählung zum Quellenereignis. |

Es gibt keinen automatischen gettex-Discoveryjob, der die fehlende Route
allein durch längeres Warten ergänzt. Der
[Refreshplan](../../backend/app/features/market_data/service/refresh.py)
plant andere vorhandene Discoverytypen; der gettex-Adapter verlangt bereits
eine validierte Route. Die zuständigen Schreibwege bleiben der
[Product-Service](../../backend/app/features/product/service/application.py)
und der [gettex-Mappinghelfer](../../backend/app/tools/configure_gettex_warrant.py).
Eine bloße Aktivierung des bereits vorhandenen Runners schließt diese Lücke
nicht. Der konkrete nächste Auftrag und seine Zugänge stehen im Backlog.

## 6. Weiterhin getrennte strengere Anforderungen

Der [V2-Vertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#indicative-review-rule-v2)
erlaubt den gemeinsamen verzögerten Quellenzeitpunkt bis 1800 Sekunden.
`original_bid_at` bleibt ohne eigene originale BID-Seitenzeit leer. B58 verlangt
weiterhin eigene geeignete BID-Zeit, höchstens 900 Sekunden Alter, passende
instrumentbezogene Statusdaten mit belegter zeitlicher Geltung sowie die
strengen historischen Sitzungs- und Maßstabsbezüge. Der gettex-Adapter setzt
den Status ausdrücklich auf `UNKNOWN`. Zweite Portalansichten oder gleiche
Preise ersetzen diese Felder nicht.

Der neue Kandidatenread enthält keine neue Produktfristbewertung, keine
neue Exitlisting-/Letzthandelstags-/produktspezifische Schlussgrenze und keine
B06-Ziel-/Folgestopgeschichte. Die entsprechenden Lücken des ursprünglichen
[Datenvertrags](DEPOT_DATA_SUPPLY_2026-11-20.md) und des Gesamtreadbacks bleiben
offen; eine neue Bidquelle löst sie nicht automatisch.
`deadline_for_review` benötigt selbst keine Preiseinheit. Deshalb folgt aus
`unit=null` kein zusätzlicher neuer Fristfehler. P04s harter Produktwiderspruch
bleibt auch dort relevant, ohne dass hier ein neuer Fristentscheid gelesen wurde.

## 7. Dokumentationsprüfung und getrennte Codequalifikation

Die Dokumentationsfortschreibung enthält ausschließlich technische und
pseudonymisierte Befunde. Auch die neuen öffentlichen Zeilen wurden gegen
**736** private Kennungen/Instrumentbezüge und die individuelle P01-KID-Adresse
geprüft: keine Treffer. Die Dokumentprüfung bestätigt **1.402** relative
Verweise und **573** Anker im gesamten Dokumentdiff gegenüber Main ohne
Fehler; Markdownstruktur und `git diff --check` sind geprüft. Der historische
Roadmapblob, der Collector und seine ausgelieferte Datei bleiben unverändert.

Die Originalprüfung verwendet Code aus
`b7743ed7b2ba293b1c65b5a3239b84f2354ddb16`; die relevanten Product-/V2-Pfade
entsprechen dem oben genannten installierten Main. Dieser ergänzende Schnitt
ändert sechs Dokumente, keine Anwendung, Parserrevision oder Datenbank.
Der echte P01-PDF-Parserlauf ist eine Quellenprobe und keine neue vollständige
Backendqualifikation. Die unabhängige fachliche Durchsicht bestätigt die
Trennung aktueller Listing-Evidenz, unveränderter KID-Fakten und weiterhin
fehlender historischer/B58-Qualifikation.

Der separate Testimportfix `10d853d3241f33857f839101cd1988472c5b8944` korrigiert
die beiden vorherigen CI-Importsortierungen. Die gezielte Projektprüfung
umfasst 56 erfolgreiche Tests und 87 Subtests; die tatsächliche Backend-CI
hat den früheren Ruff-Blocker überwunden. Gesamtgates bleiben an ihren
jeweiligen Head gebunden, siehe den
[Collector-Qualifikationsnachweis](DEPOT_SOURCE_COVERAGE_COLLECTOR_2026-11-24.md#4-qualifikation-und-nächster-tatsächlicher-beleg)
und den aktuellen PR. Keine neue Installation, Regelaktivierung, Provider-
zustimmung oder produktive Datenänderung folgt aus diesem Dokumentationsschnitt.
