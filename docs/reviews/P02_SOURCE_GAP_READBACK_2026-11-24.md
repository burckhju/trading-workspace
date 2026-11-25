# P02: Quellenlücke und tatsächliche V2-Bewertung — Readback vom 24.11.2026

## Ergebnis und Geltungsbereich

**Die damals gespeicherte P02-Preisunterbrechung ist jetzt konkret auf
`JPMORGAN_SNAPSHOT_TIMEOUT` zurückgeführt. Auf derselben gebundenen Route
liegt inzwischen eine erfolgreiche indikative V2-Bewertung vor:**
`BELOW_ENTRY` mit `INDICATIVE_BID_BELOW_GROSS_ENTRY`, bewertet am
**24.11.2026 um 18:21:41 Uhr MEZ**. Der dabei verwendete Bid war vorhanden
und erst **10,456 Sekunden** zuvor empfangen worden.

Der bidlose Quote wurde **vor** der späteren Timeout-Erfassung empfangen.
Der Timeout belegt die damalige Unterbrechungsmarkierung; die Ursache des
bereits gespeicherten fehlenden Bids bleibt ungeklärt. Der aktuelle Journalgrund
`ORIGINAL_MARKET_STATUS_NOT_DELIVERED` ist eine fortbestehende
Originalstatuslücke, aber nach dem geltenden V2-Vertrag **keine neue
Preisunterbrechung**. Original-Bidzeit und verifizierter Marktstatus bleiben
für die strengere B58-Prüfung ungeklärt.

Dieser Nachweis beruht ausschließlich auf dem vom Nutzer ausgeführten
engen Collector und den gespeicherten Fakten. Er löst keinen Providerabruf,
Refresh oder Regellauf aus. P02 bezeichnet die im ursprünglichen privaten
Archiv gebundene Position, keine neu bestimmte zweite Listenposition.
Private Identitäten, Produktkennungen, Beträge, Mengen, Streambindungen und
Produkt-URLs werden nicht veröffentlicht. Arbeitsstatus und **genau ein
nächster Auftrag** stehen ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).

## 1. Software und tatsächlich beobachteter Lesestand

| Gegenstand | Nachweis | Grenze |
| --- | --- | --- |
| Geprüfter Main | `9a5e59dac3bb219cbc40641e62e75871eb2ed131`, `VERSION=1.5.54`, [PR #373](https://github.com/burckhju/trading-workspace/pull/373) | Getrennt vom weiterhin offenen [PR #370](https://github.com/burckhju/trading-workspace/pull/370). |
| Tatsächlicher PC | Derselbe Commit `9a5e59d…`, v1.5.54; `VERIFIED_INSTALLATION_BINDING` vor und nach dem Read | Die beiden Installationsdateien sind bytegleich. Revision-, Image- und Containerbindung sind geprüft, keine vollständige Konfigurationsprüfung. |
| Ursprüngliches Referenzpaket | `c7db441de36297a98d47cdf28c64b4e5d9994692`, v1.5.52; [Gesamtreadback vom 22.11.2026](DEPOT_DATA_READBACK_2026-11-22.md) | Die Änderung des Softwarestands ist ausdrücklich ausgewiesen: `same_software_as_reference=false`. |
| Datenbank | Tatsächlicher Read von `20261118_0060`, identisch zur geprüften Schemareferenz | Verbindung über die Datenbankkonfiguration des installierten Backends. |
| Enges Paket | **24.11.2026, 18:23:08.057–18:23:10.912 Uhr MEZ**, UTC `17:23:08.057344–17:23:10.912338` | Ein gebundener Positions-/Quellenread; keine aktuelle Gesamtinventur. |
| Fachlicher Lesestichtag | **24.11.2026, 18:23:10.374337 Uhr MEZ**, UTC `17:23:10.374337Z` | Bestätigte Transaktion `repeatable read`, `read_only=on`. |
| Paketabschluss | `COMPLETE_PASSIVE_SOURCE_GAP_READ_NOT_PRICE_QUALIFICATION` | Vollständiger enger Lesetransport; keine vollständige Preis-, Quellen- oder Regelqualifikation. |

Installation, Schema und Fachread sind getrennte Beobachtungen;
`global_atomic_snapshot=false` bleibt erhalten. Innerhalb des Fachreads
wurden archivierte Bewertung, aktueller Assessmenthead, gespeicherter Quote
und Statusjournal gemeinsam lesend betrachtet.

Die relevanten V2-, Market-Data- und JPMorganpfade sind zwischen c7db441… und
9a5e59d… unverändert. Die inzwischen im Arbeitsstand ergänzte
Resolver-Fehlerweitergabe ist auf diesem PC nicht installiert. Die neue
V2-Bewertung darf daher nicht dieser noch offenen PR-Korrektur zugerechnet
werden. Die nachfolgenden Kerncodezeilen beziehen sich auf 9a5e59d…; die
verlinkten Dateien sind für diese Funktionen im geprüften Arbeitsstand
unverändert.

## 2. Historischer und aktueller Befund bleiben getrennt

Alle Uhrzeiten in der Tabelle sind MEZ (UTC+1). Die privaten JSON-Dateien
bewahren die ursprünglichen UTC-Zeitstempel.

| Zeitpunkt | Tatsächlicher gespeicherter Befund | Bedeutung |
| --- | --- | --- |
| 21.11., **22:47:56.737909** | Alter Quote empfangen; Bid und Ask fehlen, Originalkurszeit unbekannt | Dieser bidlose Bestand liegt zeitlich vor dem später erfassten Timeout. |
| 21.11., **22:55:46.275936** | `latest_gap.reason=JPMORGAN_SNAPSHOT_TIMEOUT`; `retrieved_at=null` | Erfassung einer Beschaffungslücke; kein erfolgreich empfangener neuer Quote. |
| 21.11., **22:55:46.279226** | Archivierte V2-Bewertung `UNAVAILABLE`, Gründe `REVIEW_BID_MISSING` und `REVIEW_PRICE_SUPPLY_INTERRUPTED` | Der Gap war bereits 3,29 ms vor der Bewertung erfasst. Der alte Quote hatte 469,541 s Empfangsalter. |
| 24.11., **18:21:31.237251** | Neuer gespeicherter Quote mit Bid und Ask empfangen | Originalkurszeit und Originalmarktstatus bleiben unbekannt. |
| 24.11., **18:21:41.685107** | Aktueller Gap `ORIGINAL_MARKET_STATUS_NOT_DELIVERED`; Empfangszeit entspricht dem neuen Quote | Statusdatenlücke bei vorhandenem Preisbestand. |
| 24.11., **18:21:41.693527** | Aktuelle V2-Bewertung `BELOW_ENTRY`, Grund `INDICATIVE_BID_BELOW_GROSS_ENTRY` | Tatsächlich gespeicherter fachlicher Entscheid; Quote-Empfangsalter **10,456 s**. |
| 24.11., **18:23:10.374337** | Passiver Reader findet denselben Quote und denselben aktuellen Gap | Quote-Empfangsalter **99,137 s**; kein neuer Regellauf durch den Collector. |

Die alte Bewertung wurde am 21.11. um 22:55:46.431149 Uhr MEZ gespeichert,
die aktuelle am 24.11. um 18:21:41.924686 Uhr MEZ. Der Collector exportiert
die damaligen Assessmentinputs unter `archived_assessment` und den aktuellen
Head unter `current_assessment`. Der heutige Journalhead überschreibt den
historischen Grund nicht.

## 3. Konkrete Ursache und noch nicht unterscheidbare Preisleere

### Timeout und seine zeitliche Bedeutung

Der [JPMorgan-Stream](../../backend/app/providers/jpmorgan/stream.py),
Z.176–188, erzeugt `JPMORGAN_SNAPSHOT_TIMEOUT`, wenn das begrenzte Warten
endet und noch kein akzeptiertes Snapshotitem vorliegt. Das ist der jetzt
belegte konkrete Beschaffungsfehler. Es beweist weder einen dauerhaft
gestörten Anbieter noch eine bestimmte Netzwerkursache oder einen
geschlossenen Markt.

Die Erfassungszeit des Gaps ist nicht sicher der ursprüngliche
Netzwerk-Timeoutzeitpunkt: Der bestehende
[Batch-Owner](../../backend/app/providers/issuer_bindings.py), Z.131–134 und
154–166, cached auch Fehler und kann sie für einen späteren Request erneut
zurückgeben. Das Paket enthält für diesen Gap weder einen Cache-Hit noch
die ursprüngliche Requeststartzeit. Wiederholte Erfassungen dürften deshalb
nicht ohne weitere Belege als unabhängige neue Netzwerkfehler gezählt werden.

Der [Adapter](../../backend/app/providers/jpmorgan/adapter.py), Z.98–102,
reicht den begrenzten Fehlercode weiter. Der
[Retention-Owner](../../backend/app/features/market_data/service/retained_quotes.py),
Z.81–114, erhält ihn und schreibt den Gap unabhängig von der Preisannahme
in das Statusjournal. Die
[V2-Versorgungsprüfung](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py),
Z.449–461, erkennt diesen nach dem Quote-Empfang erfassten Timeout als
`REVIEW_PRICE_SUPPLY_INTERRUPTED`.

### Der ältere fehlende Bid hat keinen nachgewiesenen Parserfehler

Im alten gespeicherten Quote stehen `bid=null`, `ask=null`,
`retained=false` und `refresh_error=null`. Das widerspricht dem späteren
Timeout nicht: Der Retention-Owner persistiert nur den letzten Providererfolg,
nicht den später zurückgegebenen Fallbackzustand
([Code](../../backend/app/features/market_data/service/retained_quotes.py),
Z.131–145 und 171–184). Bei JPMorgan darf dieser Bestand zudem einen fehlenden
Bid enthalten; `quality_status=VALID` ist an dieser Stelle keine fachliche
V2-Bidqualifikation (Z.199–208).

Der Parser bildet fehlende/leere Originalpreise und numerische Null auf
fehlende Preise ab
([Adapter](../../backend/app/providers/jpmorgan/adapter.py), Z.30–43).
Die damaligen Rohfelder sind nicht im Paket. **Quellseitige Preisleere und
Preisnormalisierung bleiben daher nicht unterscheidbar.** Der spätere
Timeout ist kein Beweis für die Ursache dieses bereits älteren bidlosen
Bestands. Ein Parser- oder Produktmappingumbau folgt daraus nicht.

Auch `QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY` ist kein konkreter
Timeoutgrund: Der Adapter setzt diesen Hinweis für seinen Indikationsmodus
standardmäßig (Z.107–118). Die historisch ungenaue Resolverzusammenfassung
und der jetzt aus den gespeicherten Assessmentinputs gelesene konkrete
Gapgrund sind verschiedene Nachweise.

Die [V2-Preisqualifikation](../../backend/app/features/position_monitoring/domain/indicative_entry.py),
Z.81–110, prüft einen fehlenden Bid vor dem Empfangsalter. Der alte Quote
war mit **469,541 s** auch älter als die zugelassenen 300 s. Das Fehlen
eines zusätzlichen `REVIEW_ISSUER_RECEIPT_TOO_OLD`-Codes ist deshalb kein
Frischebeleg.

## 4. Tatsächliche V2-Teilabnahme und strenge Grenzen

Die aktuelle Bewertung `BELOW_ENTRY` ist ein gespeicherter Regelentscheid,
kein bloßer Lauf- oder Transportzähler. Nach der
[V2-Entscheidung](../../backend/app/features/position_monitoring/domain/indicative_entry.py),
Z.213–231, liegt dieser Ausgang hinter erfolgreicher Quote-/Inputprüfung,
gültigem Einstand und mindestens zwanzig abgeschlossenen relevanten
Sitzungen. Der aktuelle Quote stimmt inhaltlich mit dem in dieser Bewertung
gespeicherten Quote überein; dasselbe gilt für den aktuellen `latest_gap`.

| Merkmal | Belegter aktueller Befund | Fachliche Grenze |
| --- | --- | --- |
| Position und Quelle | `ARCHIVED_POSITION_AND_CURRENT_ROUTE_MATCH`; Provider `JPMORGAN`; Quellenbasis `SAVED_QUOTE_AND_SELECTION` | Bindung an die archivierte Position, keine Auswahl nach heutiger Listenreihenfolge. |
| Preis | Bid und Ask vorhanden; V2 bewertet den Bid als unter dem V2-Bruttoeinstand | Keine Veröffentlichung der Preise; keine autonome Handelsentscheidung. |
| Zeit | Empfangsalter 10,456 s bei Bewertung; 99,137 s beim späteren Read | Beide liegen unter der V2-Empfangsgrenze von 300 s. Empfangsfrische ist keine Originalkursfrische. |
| Quellenmodus | `OFFICIAL_ISSUER_INDICATION_TIME_ONLY`, `DATE_AND_TIMEZONE_UNKNOWN` | Die Anzeigeuhr belegt weder Datum noch Zeitzone oder ursprünglichen Bidzeitpunkt. |
| Listingbeleg | Interne Routen-/Identitätsbindung erhalten; `quote.venue_mic=null` | Die gebundene Route ist keine neu gelieferte Börsenlisting-Originalevidenz. |
| Originalkurs | `observed_at=null`, `original_evidence=null` | Keine eigene belegte Original-Bidzeit und kein Nachweis der B58-Grenze von höchstens 900 s. |
| Originalstatus | `original_market_status=null`; `NO_POINT_AT_EVENT`; `observed_status=null`; `status_validity_interval=NOT_ESTABLISHED` | Kein verifiziert offener Markt mit passender zeitlicher Geltung. |
| Aktueller Gap | `ORIGINAL_MARKET_STATUS_NOT_DELIVERED` | Echte Statusdatenlücke; ausdrücklich von der V2-Preisunterbrechung ausgenommen. |

Die Ausnahme für die registrierte Emittentenindikation mit unbekannter
Originalzeit ist im [V2-Code](../../backend/app/features/position_monitoring/domain/indicative_entry.py),
Z.97–115, begrenzt. Die
[Statusjournalerfassung](../../backend/app/features/market_data/service/status_observations.py),
Z.51–55 und 118–125, erzeugt auch bei vorhandenem Quote einen `GAP`, wenn
kein Originalstatus mitgeliefert wird. Die explizite V2-Ausnahme dafür steht
in [indicative_entry_inputs.py](../../backend/app/features/position_monitoring/service/indicative_entry_inputs.py),
Z.458. `GAP_PRESENT` allein darf daher nicht wieder als Preisabbruch
zusammengefasst werden.

Die Anzeigeuhr ohne Datum/Zeitzone darf weder aus dem Empfangsdatum ergänzt
noch mit UTC verrechnet werden. Ein Handelskalender oder eine interne
Listingbindung ersetzt keinen Original-OPEN-Status. Die strengeren
[B58-Anforderungen](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#b40b58--lebenszyklus-anpassungen-und-restmengen)
und der [Originalstatusvertrag](../features/HEBELTRADER_MONITORING_INTEGRATION_CONTRACT.md#f207-3-market-status-evidence)
bleiben unverändert; V2 aktiviert keine strenge B04/B57/B58-Abnahme.

**Dieser enge Nachweis enthält keine neue Gesamtinventur.** Die Vierer-Matrix
vom 22.11. ist eine historische Ausgangsbasis; daraus entsteht hier keine
aktuelle „1 von 4“-Abdeckungsquote. Der aktuelle Assessmenthead ist nicht
der direkte Nachfolger des archivierten Heads. Zwischenbewertungen, der
erste Wiederverfügbarkeitszeitpunkt und kontinuierliche Verfügbarkeit sind
nicht exportiert. Ebenso fehlen neue Belege für andere Positionen,
Produktfristen, B06, Episodenschließung und tatsächliche Zustellung.
Es wird keine lückenlose automatische Wiederherstellung behauptet.

Der Collector hat zum späteren Lesestichtag keine Neuberechnung erzeugt.
Er enthält nicht alle Kalender-, Einstands- und Einheiteninputs für eine
unabhängige vollständige Wiederholung der V2-Regel. Die Abnahme ist auf den
tatsächlich gespeicherten Entscheid und die eindeutig gebundenen aktuellen
Quellenfakten begrenzt.

## 5. Prüfpunkte im privaten Paket

Die Dateien bleiben privat. Die Pointer und Hashes erlauben den Abgleich,
ohne Depotkennungen oder Originalinhalte ins Repository zu übernehmen.

| Datei / JSON-Pointer | Nachgewiesene Aussage |
| --- | --- |
| `summary.json#/started_at`, `#/completed_at`, `#/reference_archive_verified`, `#/installation_unchanged_and_verified` | Paketzeit, geprüfte Referenz und unveränderte tatsächliche Installation. |
| `summary.json#/same_software_as_reference`, `#/source_gap_transport_complete`, `#/status` | Versionswechsel offen ausgewiesen; erfolgreicher enger Lesetransport mit begrenzter Aussage. |
| `schema.json#/versions`, `#/matches_reviewed_reference` | Tatsächlicher Schemastand und Referenzvergleich. |
| `source-gap-private.json#/reference`, `#/binding_status`, `#/status_provider_basis` | Archivgebundene Auswahl und heutige exakte Quellenbindung. |
| `source-gap-private.json#/archived_assessment/evaluated_at`, `#/archived_assessment/recorded_at`, `#/archived_assessment/outcome`, `#/archived_assessment/reasons` | Damaliger Bewertungszeitpunkt, Speicherzeit und Gründe. |
| `source-gap-private.json#/archived_assessment/inputs/saved_quote`, `#/archived_assessment/inputs/status_observations/latest_gap` | Historischer bidloser Quote und konkret damals bekannter Snapshot-Timeout. |
| `source-gap-private.json#/current_assessment/evaluated_at`, `#/current_assessment/recorded_at`, `#/current_assessment/outcome`, `#/current_assessment/reasons` | Neuer gespeicherter V2-Entscheid, getrennt von der archivierten Bewertung. |
| `source-gap-private.json#/current_assessment/inputs/saved_quote`, `#/current_assessment/inputs/status_observations/latest_gap` | Tatsächlich zum neuen Assessment gespeicherte Quelleninputs. |
| `source-gap-private.json#/saved_quote`, `#/current_status`, `#/read_at`, `#/transaction` | Heutiger gespeicherter Quellen-/Journalbestand im bestätigten lesenden Snapshot. |
| `source-gap-private.json#/archived_assessment/stored_input_fields_present`, `#/current_assessment/stored_input_fields_present` | Das Feld `current_refresh_failed` war in beiden ursprünglichen Inputobjekten nicht gespeichert; `false` ist hier ein Präsenzmarker, kein historischer Wert „Refresh erfolgreich“. Der exportierte Inputwert ist `null`. |

Der vorhandene [Collector](../../scripts/collect-depot-data-supply.py)
akzeptiert das Paket mit `source_gap_complete=True`. Payloadhash und
Referenzhash passen; die alte Assessmentidentität, Regelversion, Zeiten,
Gründe und Ownerbasis stimmen mit dem ursprünglichen privaten P02-Read
überein. Die Ownerbasis ist auch im aktuellen Head gleich. Das ist eine
Bindungsprüfung, keine Rekonstruktion fehlender Zwischenbewertungen.

### SHA-256 der unveränderten Belege

| Gegenstand | SHA-256 |
| --- | --- |
| Enges Privatarchiv vom 24.11.2026 | `5bbfc9578cf0725b3412d0817f011efb46f65256bc03c5df41636badb00c07ee` |
| `installation-before.json` | `21a5702d31ed740b629197635b90757cc9d3d20b23e95b6716b521c4319fa360` |
| `installation-after.json` | `21a5702d31ed740b629197635b90757cc9d3d20b23e95b6716b521c4319fa360` |
| `schema.json` | `5c5cf41d2d937e4718a122269ebf496ed2cf1fc9a1edc4a851ff135df3138162` |
| `source-gap-private.json` | `843e90c462e52bf706200ce9c13393d63561919e8b86fb10d76cc275098ffd11` |
| `summary.json` | `67ee1d0404435648443ee99a4cce1adade3812ffea29dad5600a797a6e122158` |
| Referenziertes ursprüngliches Privatarchiv | `ea4ee60cbd4d212ac97cf5b140f168d1f959bd2aac48cf344bb4b26839ce73ab` |
| Darin referenzierte `monitoring-private.json` | `e10a1b814ed00850c1d03b1694d8c6458797280a3fa5c3b5dd8427bde0e8b8ed` |
| Ausgeführter enger Backendpayload | `56123ebd72cb83621f706bf13ee2d9a46dc05e54559f8ce51b7b9cf3038134dd` |

## 6. Codequalifikation und Weiterführung

Für den geprüften Arbeitscommit
`41a0cf80b1f0702d3322bcf268ed83da8cf84de2` sind auf GitHub vier erfolgreiche
Workflowläufe belegt:
[Backend 45262911140](https://github.com/burckhju/trading-workspace/actions/runs/45262911140),
[Frontend 45262911117](https://github.com/burckhju/trading-workspace/actions/runs/45262911117),
[E2E 45262911015](https://github.com/burckhju/trading-workspace/actions/runs/45262911015)
und [Version 45262911040](https://github.com/burckhju/trading-workspace/actions/runs/45262911040).
Das ist Codequalifikation des weiterhin offenen PR #370 und kein
Installationsnachweis. Für diesen reinen Dokumentationsschnitt wurden
keine neuen Anwendungstests ausgeführt. Er dokumentiert den tatsächlich
bereitgestellten PC-Readback und dessen Grenzen.

Der neue Dokumentdiff wurde separat geprüft: sechs betroffene Dokumente,
1.336 relative Verweise und 552 Ankerverweise in den zehn gegenüber Main
geänderten Markdown-Dateien, keine fehlenden Ziele; Details-Blöcke,
eindeutige explizite Anker und `git diff --check` ohne Fehler. Der Abgleich
des neu hinzugefügten Textes gegen 720 private Kennungen/Instrumentbezüge
aus beiden Paketen hat keine Treffer. Backend, Frontend, Skripte und Tests
sind gegenüber 41a0cf80… unverändert; ebenso der historische Roadmapblob
`919ed7570580b1d883a409f864ed15747fbfda3e`.

Der neue Einzelbeleg ergänzt die
[historische Gesamtmatrix](DEPOT_DATA_READBACK_2026-11-22.md). Sie bleibt
Ausgangspunkt für die Auswahl einer weiteren tatsächlich noch offenen
Position; heutige Position und Quellen-/Produktbindung müssen dazu aktuell
bestätigt werden. Der konkrete Ownerauftrag, seine Auswahl und Abnahme
stehen ausschließlich unter
[Nächster Auftrag im Product Backlog](../planning/PRODUCT_BACKLOG.md#naechster-schnitt).
