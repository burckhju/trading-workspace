# S&P 500 und 30 ETF-Charts: belegtes Analyseuniversum

## Stand und Zweck

- Quellenprüfung: **2026-11-09**.
- Gelesene Repositorybasis: Main `0fe00f5a332c276c14ee6d36dcd0746047623124`, Version `1.5.45`.
- Unmittelbar vor dem Schreiben erneut per `git ls-remote origin refs/heads/main` bestätigt.
- Katalogversion: `GLOBAL_MARKETS_ETF_V1_20261109`; JSON-Schema: `1`.
- Maschinenlesbarer Katalog: [etf_chart_universe_v1.json](../../backend/app/features/market/service/etf_chart_universe_v1.json).
- Umfang: **genau 30 eigenständige ETFs**, geordnete Positionen 1–30. Der direkte S&P-500-Index gehört **zusätzlich** als listingfreie `MarketReference` zur Beobachtungsliste und ist kein ETF-Eintrag dieser Datei.

Der Auftrag wurde als globale Marktübersicht konkretisiert. Die einmalige Schwerpunktfrage blieb unbeantwortet; deshalb setzt dieser Katalog den angekündigten Default mit US-Listings um. Die Reihenfolge drückt keine Rangfolge nach Vermögen, Liquidität, Rendite oder Anlageeignung aus. Es handelt sich um ein Analyseuniversum mit überlappenden Beobachtungsbereichen, ohne Portfolio-Gewichte oder Kaufempfehlung.

## Auswahlbegründung und Abdeckungsgrenze

Die **elf US-Sektoren** übernehmen die bereits vorhandene GICS-/Select-Sector-SPDR-Struktur. Die **zehn breiten und regionalen Aktien-ETFs** ergänzen Welt, breiten US-Markt, S&P 500 als eigenständiges ETF-Wertpapier, Nasdaq-100, kleinere US-Unternehmen, entwickelte Märkte außerhalb der USA, Schwellenländer, Europa, Japan und China. Die **neun Anleihe-ETFs** machen US-Gesamtmarkt, internationale Anleihen, unterschiedliche Treasury-Laufzeitbereiche, inflationsgebundene Treasuries sowie Unternehmensanleihen mit unterschiedlicher Bonität beobachtbar.

**BIL ist der 30. Eintrag.** Ein eigener Gold-/Rohstoffbaustein wird in dieser Version nicht behauptet. Der eindeutig belegte Treasury-Bill-ETF vermeidet, einen europäischen Gold-ETC in das vorhandene `UnderlyingType.ETF` umzudeuten. Zum Typunterschied siehe beispielsweise die [offizielle Produktseite des iShares Physical Gold ETC](https://www.ishares.com/uk/individual/en/products/258441/ishares-physical-gold-etc), die ETC und `UCITS No` ausweist. Es wird kein ETC, ETN, Einzelwert, synthetisch erzeugter Index oder Ersatzkurs als ETF aufgenommen.

BNDX besitzt laut [Emittentenbeschreibung](https://www.vanguardsouthamerica.com/en/product/etf/fixed-income/3711/vanguard-total-international-bond-etf) eine vom Fonds vorgesehene Währungsabsicherung. Das ist eine Produkteigenschaft; die Anwendung berechnet dafür weder eine Absicherung noch eine Währungsumrechnung. Sämtliche unten gewählten **US-Listings** werden in USD geführt. Die Währungen ihrer Anlagen und andere Listings derselben ISIN bleiben davon getrennt.

## 1. US-Sektoren — 11 Einträge

Die Namen werden ohne Marken-/Registrierungszeichen gespeichert. Die ISINs und NYSE-Arca-Listings entsprechen den Listingtabellen des jeweiligen Emittenten.

| Pos. | Katalogcode | Name | ISIN | Börsenticker | MIC | Währung | Hauptbeleg |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | `ETF_US_XLE` | State Street Energy Select Sector SPDR ETF | US81369Y5069 | XLE | ARCX | USD | [Emittent](https://www.ssga.com/us/en/institutional/etfs/state-street-energy-select-sector-spdr-etf-xle) |
| 2 | `ETF_US_XLB` | State Street Materials Select Sector SPDR ETF | US81369Y1001 | XLB | ARCX | USD | [Emittent](https://www.ssga.com/us/en/individual/etfs/state-street-materials-select-sector-spdr-etf-xlb) |
| 3 | `ETF_US_XLI` | State Street Industrial Select Sector SPDR ETF | US81369Y7040 | XLI | ARCX | USD | [Emittent](https://www.ssga.com/us/en/institutional/etfs/state-street-industrial-select-sector-spdr-etf-xli) |
| 4 | `ETF_US_XLY` | State Street Consumer Discretionary Select Sector SPDR ETF | US81369Y4070 | XLY | ARCX | USD | [Emittent](https://www.ssga.com/us/en/intermediary/etfs/state-street-consumer-discretionary-select-sector-spdr-etf-xly) |
| 5 | `ETF_US_XLP` | State Street Consumer Staples Select Sector SPDR ETF | US81369Y3080 | XLP | ARCX | USD | [Emittent](https://www.ssga.com/us/en/intermediary/etfs/state-street-consumer-staples-select-sector-spdr-etf-xlp) |
| 6 | `ETF_US_XLV` | State Street Health Care Select Sector SPDR ETF | US81369Y2090 | XLV | ARCX | USD | [Emittent](https://www.ssga.com/us/en/intermediary/etfs/state-street-health-care-select-sector-spdr-etf-xlv) |
| 7 | `ETF_US_XLF` | State Street Financial Select Sector SPDR ETF | US81369Y6059 | XLF | ARCX | USD | [Emittent](https://www.ssga.com/us/en/intermediary/etfs/state-street-financial-select-sector-spdr-etf-xlf) |
| 8 | `ETF_US_XLK` | State Street Technology Select Sector SPDR ETF | US81369Y8030 | XLK | ARCX | USD | [Emittent](https://www.ssga.com/us/en/intermediary/etfs/state-street-technology-select-sector-spdr-etf-xlk) |
| 9 | `ETF_US_XLC` | State Street Communication Services Select Sector SPDR ETF | US81369Y8527 | XLC | ARCX | USD | [Emittent](https://www.ssga.com/us/en/institutional/etfs/state-street-communication-services-select-sector-spdr-etf-xlc) |
| 10 | `ETF_US_XLU` | State Street Utilities Select Sector SPDR ETF | US81369Y8865 | XLU | ARCX | USD | [Emittent](https://www.ssga.com/us/en/institutional/etfs/state-street-utilities-select-sector-spdr-etf-xlu) |
| 11 | `ETF_US_XLRE` | State Street Real Estate Select Sector SPDR ETF | US81369Y8600 | XLRE | ARCX | USD | [Emittent](https://www.ssga.com/us/en/intermediary/etfs/state-street-real-estate-select-sector-spdr-etf-xlre) |

## 2. Aktienmärkte und Regionen — 10 Einträge

| Pos. | Katalogcode | Name | ISIN | Börsenticker | MIC | Währung | Hauptbeleg |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 12 | `ETF_US_VT` | Vanguard Total World Stock ETF | US9220427424 | VT | ARCX | USD | [Emittent](https://www.vanguardsouthamerica.com/en/product/etf/equity/3141/vanguard-total-world-stock-etf) |
| 13 | `ETF_US_VTI` | Vanguard Morningstar Total Stock Market ETF | US9229087690 | VTI | ARCX | USD | [Emittent](https://advisors.vanguard.com/investments/products/vti/vanguard-total-stock-market-etf) |
| 14 | `ETF_US_SPY` | State Street SPDR S&P 500 ETF Trust | US78462F1030 | SPY | ARCX | USD | [Emittent](https://www.ssga.com/us/en/institutional/etfs/state-street-spdr-sp-500-etf-trust-spy) |
| 15 | `ETF_US_QQQ` | Invesco QQQ Trust, Series 1 | US46090E1038 | QQQ | XNMS | USD | [Emittent](https://www.invesco.com/us/en/financial-products/etfs/invesco-qqq-trust-series-1.html) |
| 16 | `ETF_US_IWM` | iShares Russell 2000 ETF | US4642876555 | IWM | ARCX | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239710/ishares-russell-2000-etf) |
| 17 | `ETF_US_VEA` | Vanguard FTSE Developed Markets ETF | US9219438580 | VEA | ARCX | USD | [Emittent](https://www.vanguardsouthamerica.com/es/producto/etf/renta-variable/0936/vanguard-ftse-developed-markets-etf) |
| 18 | `ETF_US_VWO` | Vanguard FTSE Emerging Markets ETF | US9220428588 | VWO | ARCX | USD | [Emittent](https://www.vanguardsouthamerica.com/es/producto/etf/renta-variable/0964/vanguard-ftse-emerging-markets-etf) |
| 19 | `ETF_US_VGK` | Vanguard FTSE Europe ETF | US9220428745 | VGK | ARCX | USD | [Emittent](https://www.vanguardsouthamerica.com/en/product/etf/equity/0963/vanguard-ftse-europe-etf) |
| 20 | `ETF_US_EWJ` | iShares MSCI Japan ETF | US46434G8226 | EWJ | ARCX | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239665/ishares-msci-japan-etf) |
| 21 | `ETF_US_MCHI` | iShares MSCI China ETF | US46429B6719 | MCHI | XNMS | USD | [Emittent](https://www.ishares.com/uk/professionals/en/products/239619/ishares-msci-china-etf?siteEntryPassthrough=true) |

Ergänzende Identitätsbelege:

- **VTI:** Die [Vanguard-Produktcodes](https://www.vanguardsouthamerica.com/en/product/etf/equity/0970/vanguard-total-stock-market-etf) nennen `US9229087690`. Die regionale Seite stellt zugleich einen australischen Cross-Listing-Kontext mit AUD/ASX und eigener australischer ISIN dar. Diese Listingangaben wurden **nicht** in den US-Eintrag übernommen. Für aktuellen US-Namen und US-Börsenplatz wurden die [US-Emittentenseite](https://advisors.vanguard.com/investments/products/vti/vanguard-total-stock-market-etf) und das [offizielle Other-Listed-Verzeichnis](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt) verwendet. Beide führen inzwischen **Vanguard Morningstar Total Stock Market ETF**.
- **EWJ:** Die ISIN `US46434G8226` ist zusätzlich im [offiziellen BMV-Instrumentenprofil](https://www.bmv.com.mx/en/issuers/statistics/EWJ-6512) belegt. Das ausgewählte Listing ist die separate Zeile **NYSE Arca / EWJ / USD** der BlackRock-Listingtabelle; das mexikanische MXN-Listing wird nicht übernommen.
- **MCHI:** Die ISIN `US46429B6719` ist zusätzlich im [offiziellen BMV-Profil](https://www.bmv.com.mx/es/emisoras/perfil/MCHI-7680) belegt. Das Nasdaq-Segment wird durch das offizielle Symbolverzeichnis unten konkretisiert.
- **QQQ:** Die [Invesco-Übersicht](https://www.invesco.com/qqq-etf/en/about.html) bezeichnet den Handelsplatz ausdrücklich als **Nasdaq/NMS (Global Market)**. Die ISIN ist auf der Hauptproduktseite angegeben.
- **Vanguard:** Die Produktcodes belegen die jeweiligen ISINs; die US-Listings werden zusätzlich durch die offiziellen Symbolverzeichnisse abgesichert. USD bezieht sich auf den ausgewählten US-Produkt-/Listingkontext. Regionale Portalwährungen, Fondsbasiswährung und andere Handelswährungen werden nicht als austauschbare Felder behandelt.

## 3. Anleihen — 9 Einträge

| Pos. | Katalogcode | Name | ISIN | Börsenticker | MIC | Währung | Hauptbeleg |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 22 | `ETF_US_AGG` | iShares Core U.S. Aggregate Bond ETF | US4642872265 | AGG | ARCX | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239458/ishares-core-total-us-bond-market-etf?printable=true) |
| 23 | `ETF_US_BNDX` | Vanguard Total International Bond ETF | US92203J4076 | BNDX | XNMS | USD | [Emittent](https://www.vanguardsouthamerica.com/en/product/etf/fixed-income/3711/vanguard-total-international-bond-etf) |
| 24 | `ETF_US_SHY` | iShares 1-3 Year Treasury Bond ETF | US4642874576 | SHY | XNMS | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239452/ishares-13-year-treasury-bond-etf) |
| 25 | `ETF_US_IEF` | iShares 7-10 Year Treasury Bond ETF | US4642874402 | IEF | XNMS | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239456/) |
| 26 | `ETF_US_TLT` | iShares 20+ Year Treasury Bond ETF | US4642874329 | TLT | XNMS | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239454/ishares-20-year-treasury-bond-etf) |
| 27 | `ETF_US_TIP` | iShares TIPS Bond ETF | US4642871762 | TIP | ARCX | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239467/ishares-tips-bond-etf) |
| 28 | `ETF_US_HYG` | iShares iBoxx $ High Yield Corporate Bond ETF | US4642885135 | HYG | ARCX | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239565/) |
| 29 | `ETF_US_LQD` | iShares iBoxx $ Investment Grade Corporate Bond ETF | US4642872422 | LQD | ARCX | USD | [Emittent](https://www.blackrock.com/mx/intermediarios/productos/239566/) |
| 30 | `ETF_US_BIL` | State Street SPDR Bloomberg 1-3 Month T-Bill ETF | US78468R6633 | BIL | ARCX | USD | [Emittent](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-bloomberg-1-3-month-t-bill-etf-bil) |

Für BlackRock wurden die Zeilen der US-Listings verwendet. Auf denselben Seiten vorhandene MXN- oder CLP-Listings derselben Fonds sind separate Listings und keine Währungsalternative für dieses Katalogtupel.

## Konkrete Handelsplätze statt Operating-MIC-Vereinfachung

Der Katalog verwendet **24-mal `ARCX`** und **sechsmal `XNMS`**:

| MIC im Katalog | Handelsplatzname | ISO-Ebene | Operating MIC, nur zur Einordnung |
| --- | --- | --- | --- |
| `ARCX` | NYSE Arca | Aktiver Segment-MIC | `XNYS` |
| `XNMS` | Nasdaq Global Market | Aktiver Segment-MIC | `XNAS` |

Quelle ist das [offizielle ISO-10383-MIC-Verzeichnis](https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.pdf). Die verwendeten aktiven Segmentcodes werden nicht auf ihre Operating-MICs umgeschrieben. Die [ISO-Veröffentlichungsseite](https://www.iso20022.org/market-identifier-codes) trennt Veröffentlichung und Inkrafttreten von Änderungen; ein Veröffentlichungsdatum ersetzt keinen Wirksamkeitsnachweis einer neuen MIC-Änderung.

Für **QQQ, BNDX, MCHI, SHY, IEF und TLT** weist das [offizielle Nasdaq-Symbolverzeichnis](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt) jeweils **Market Category `G`** und **ETF `Y`** aus. Die [offiziellen Felddefinitionen](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs) lösen `G` als **Nasdaq Global Market** auf. Daraus folgt der konkrete ISO-Code `XNMS`; das ist keine EODHD-Exchange-Kennung.

Für die fünf NYSE-Arca-Vanguard-Aktien-ETFs **VT, VTI, VEA, VWO und VGK** weist das [Other-Listed-Verzeichnis](https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt) **Exchange `P`** und **ETF `Y`** aus. Die Felddefinitionen lösen `P` als **NYSE ARCA** auf. Die geprüften Verzeichnisfassungen tragen den Dateitag 2026-11-09.

Die Länderkennung `US` und die Zuordnung New York sind mit den MIC-Zeilen belegt. `America/New_York` bezeichnet die Zeitzone des Handelsplatzes. Die Börsen veröffentlichen ihre Handelszeiten in Eastern Time: [NYSE](https://www.nyse.com/trade/hours-calendars?os=vb) und [Nasdaq](https://www.nasdaq.com/market-activity/stock-market-holiday-schedule). Diese Zeitzone erzeugt **keine künstliche Uhrzeit** für DATE_ONLY-/EOD-Kursbeobachtungen.

## Separater direkter S&P-500-Index

Der zusätzliche Indexeintrag verwendet die offizielle [S&P-500-Indexseite von S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/indices/equity/sp-500/) als Identitätsquelle, geprüft am 2026-11-09.

Er bleibt listingfrei: keine ETF-ISIN, kein erfundenes Listing und keine Übernahme von SPY als stiller Ersatz. Ein bestehender Provider-Vorschlag für `GSPC`/`INDX` gehört zum vorhandenen Reference-/Provider-Owner und muss dort aktuell und exakt geprüft werden. Diese Recherche bestätigt keine Renditegrundlage einer konkreten Mappingrevision.

## Quellenmodell und Weiterverarbeitung

Das Feld `reviewed_on` ist der **Prüftag der statischen Quellen**, weder der letzte Handelstag noch ein Kurszeitpunkt. Emittentenseiten können abweichende Produkt-/Datenstichtage enthalten. Die Quellenliste ersetzt keine aktuelle Providerantwort.

Je JSON-Eintrag werden gespeichert:

- stabiler Katalogcode `ETF_US_<Börsenticker>`, unverändert zu haltende Identität und explizite Position;
- Name, `kind=ETF`, Gruppe und fachliche Beobachtungsabdeckung;
- tatsächliche ISIN sowie das ausgewählte Tupel aus Börsenticker, MIC und Listingwährung;
- Handelsplatzname, Land, Zeitzone und MIC-Quelle;
- Hauptbeleg `source_url`, ergänzende Quellen mit Rollen und Prüftag;
- `provider_coverage=NOT_VERIFIED`.

`source_url` verweist auf die Emittentenidentität. Wo deren regionale Darstellung mehrere Listings oder unvollständig angezeigte Kennungen enthält, liefern die zusätzlichen Rollen `exchange_isin`, `issuer_isin`, `issuer_listing` und `listing_and_etf_type` den jeweiligen zusätzlichen Nachweis. `mic_registry` und `exchange_timezone` sichern getrennte Handelsplatzinformationen ab.

**Es sind keine Provider-Symbole oder Provider-Exchange-Codes hinterlegt.** Aus Börsenticker, MIC oder dem ähnlichen Namen eines Suchtreffers darf kein bestätigtes EODHD-Mapping konstruiert werden. Ein vorgeschlagenes Providerinstrument muss aktuell eindeutig auf die konkrete Wertpapier-/Listingidentität geprüft werden. Abweichende Währung oder Börsenidentität bleibt ein einzelner belegter Einrichtungsfehler.

Der Katalog ist von Depotpositionen unabhängig. Bestehende tatsächliche Underlyings werden über ihre Identität wiederverwendet; die Auswahl schafft keine Position und ändert keine bestehende Benchmark-/Sektorzuordnung. Einrichtung und spätere Aktualisierung verwenden die jeweiligen Market-/Market-Data-Owner.

## Erhaltene Fachverträge

Maßgeblich bleiben [ADR-CHARTS-001](../decisions/ADR-CHARTS-001-EOD-COMPARISON-AND-ETF-IDENTITY.md) und [MARKET_CHARTS.md](../implementation/MARKET_CHARTS.md):

- Market besitzt Wertpapieridentitäten, Listings und zeitabhängige Zuordnungen.
- Market Data besitzt Mappingprüfung, gespeicherte EOD-Historie und explizite Aktualisierung.
- Analysis besitzt bestehende Ausrichtung/Normalisierung; dieser Katalog ergänzt keine Finanz- oder Kursberechnung.
- Chart-GETs bleiben lesend; lokale Diagramminteraktion löst keinen Providerabruf aus.
- Kursfrische, vorhandene Historie, Providerverfügbarkeit und technische Mappingvalidität bleiben getrennte Aussagen.
- Der vorhandene begrenzte Serienvergleich wird durch die Größe des Auswahlkatalogs nicht erweitert.

## Tatsächlich durchgeführte Datenprüfung

Eine lokale Prüfung der geschriebenen JSON-Datei am 2026-11-09 ergab:

| Prüfung | Ergebnis |
| --- | --- |
| JSON lesbar, Schema/Katalogversion korrekt | bestanden |
| Genau 30 Einträge, ausschließlich `ETF` | bestanden |
| Codes, ISINs, Börsenticker und Positionen eindeutig | jeweils 30 eindeutige Werte |
| Positionen vollständig und geordnet | 1–30 |
| ISIN-Prüfziffer | 30 von 30 gültig |
| Gruppenanzahl | 11 Sektoren / 10 Aktienmärkte und Regionen / 9 Anleihen |
| MIC-Verteilung | 24 `ARCX` / 6 `XNMS` |
| Listingwährung im Katalog | 30-mal `USD` |
| Providerkennungen im Katalog | keine |
| Quellen-URLs | HTTPS, ohne eingebettete Zugangsdaten |

Die Prüfzifferprüfung bestätigt die **Syntax**, nicht die Identität; dafür dienen die genannten Primärquellen. Diese Datenprüfung ist kein Ergebnis der vollständigen Anwendungs-CI und kein Nachweis erfolgreicher Providerabrufe oder verfügbarer Historien auf dem PC. Es wurden keine Providerkeys, privaten Bestände oder authentifizierten Providerendpunkte verwendet.
