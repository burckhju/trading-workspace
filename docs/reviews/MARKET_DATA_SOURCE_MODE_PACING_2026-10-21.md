# TC-001 — Quellenmodus und Pacing: Qualifikation vom 21.10.2026

Dieser Bericht liefert begrenzte technische Nachweise für Planungssicht 2,
`TC-001 / market_data`. Aufgabenstatus bleibt ausschließlich im
[Product Backlog](../planning/PRODUCT_BACKLOG.md#market-data-refresh), ergänzt um
[Datenqualität](../planning/PRODUCT_BACKLOG.md#market-data-quality).

## Aktueller Releaseauftrag: v1.5.12

Der Nutzer hat Merge und PC-Bereitstellung unter der Bedingung grüner Prüfungen
ausdrücklich autorisiert. Die [Release-Notiz](../releases/V1.5.12-SNAPSHOT-QUOTE-PACING.md)
begrenzt den Umfang auf den gewählten Snapshot-Pacing-Fix samt qualifizierten
Tests und Dokumentation, ausgehend von v1.5.11 / Main
`5e9ede2dc29f52eaff601d30614df6bc9c25c426`. Frühere Hinweise auf einen noch nicht
beauftragten Merge oder Release dokumentieren den damaligen Arbeitsauftrag.

Die grüne PR-CI auf `25a59069efc2016e4cd5139589bb1bac4aea6716` ist die vorherige
Codequalifikation. Der finale Versionsstand muss erneut grün geprüft werden;
anschließend verlangt der unveränderte Autotag-Workflow erfolgreiche Backend-,
Frontend- und End-to-End-Läufe auf dem tatsächlichen aktuellen Main-Push.
Neue Prüfungen, Tag und PC-Installation werden hier nicht vorweggenommen.
Die vollständigen finalen SHA-/Run-/Tagbezüge werden in
[PR #271](https://github.com/burckhju/trading-workspace/pull/271) und der
abschließenden Übergabe nachgetragen. Aufgabenstatus und fachliche Restgrenzen
bleiben im Backlog; die nachfolgende Entscheidungshistorie bleibt erhalten.

## Nachtrag: Variante 2 entschieden

**Aktuelle Entscheidung vom 21.10.2026:** Mit „wie vorgeschlagen gezielt ändern“
hat der Nutzer Variante 2 ausdrücklich gewählt. Normalisierte
`HTTPS_JSON`-/`LOCAL_FILE`-Quoteaufrufe lassen die zusätzliche Schedulerpause
entfallen. Die frühere offene C-Entscheidung ist damit abgelöst. Ihre Prüfung auf
Testcommit `3d477326` und Dokumentationshead `bade0e33` bleibt unten als
Vorherstand erhalten. Die begrenzte Umsetzung bleibt bis zur Integration im
Arbeitsstatus **Technical Review**; dies ist keine vollständige fachliche
Abnahme, Veröffentlichung oder Betriebsabnahme.

### Beschlossener Vertrag und Auswirkungen

`_warrant()` ruft `_pace()` für eine ausgewählte aktive, validierte
`FRANKFURT_QUOTES`-Providerroute nur noch im Modus `PUBLIC_WEBSITE` auf.
Normalisierte Quoteaufrufe gehen unmittelbar an den vorhandenen Resolver; die
Ausnahme gilt für Cachehits und Cachemisses. Publicquote und Publicdiscovery
bleiben beim bisherigen Pacing. Die Providerroute bestimmt weiter den Aufruf;
es entsteht kein neuer MIC-Filter und kein alternativer Resolverpfad.

Clientlock, tatsächliches Ladebudget, TTL, positive und negative Caches,
Retry-After, Rechte und Zeitstempelregeln bleiben unverändert. Ein zulässiger
Snapshot-Hit benötigt keine Schedulerpause. Ein Miss oder Fehler während eines
gesperrten Clientslots umgeht weder die Sperre noch den vorhandenen
Resolver-/Retentionpfad. Ohne frühere Beobachtung bleibt der geprüfte
Throttlingpfad ein Fehler/MISSING; vorhandene Historie kann mit ursprünglichen
Zeiten und explizitem `refresh_error` als Analysebeobachtung verfügbar bleiben.
Es wird weder eine automatische Warte-/Wiederholungsschleife noch eine neue
Recovery-Fälligkeit eingeführt.

Die Jobintervalle beginnen weiterhin nach dem Jobabschluss. Ein früherer
Abschluss verschiebt daher spätere Fälligkeiten und möglicherweise Reloads;
identische Gesamtzugriffszahlen über beliebige lange Katalogläufe werden nicht
zugesagt. Besonders an Fehlergrenzen kann die tatsächliche Erholung **später**
erfolgen als im früheren, im Scheduler wartenden Ablauf: Erhält der Snapshot-
Client bei monotoner Testzeit 400 eine HTTP 429 mit `Retry-After: 120`, bleibt
seine Deadline 520.
Jobs bei 400 und 401 können sofort vorhandene Historie mit `refresh_error`
zurückgeben und werden bei 300 s Jobintervall regulär erst bei 700 bzw. 701
wieder fällig. Das Ende des Clientcooldowns bei 520 weckt diese Jobs nicht.
Diese Folge gehört zur gewählten Variante und wird mit dem echten `_job()`-
Pfad qualifiziert; sie ist keine neue Recovery-Retrylogik.

### Neuer Prüfstand und Abnahmenachweis

| Nachweis | Identität / Aussage |
|---|---|
| Historische Charakterisierung | `3d47732665c8b66984923d88a65cf99e74d96791`, 322 gezielte Tests; Produktionsbasis `5e9ede2`. Die damaligen Ergebnisse werden nicht auf den neuen Code übertragen. |
| Historischer C-Dokumentationshead | `bade0e33a67e21b9d2a7e504a798e95ba619dcd0`, Tree `563776df6a6103cb66e2411ace53297416f5722b`; Vorherstand von Draft-PR #271. |
| Neuer Implementierungscommit | `187c16b63e0d4dc16b2204f80aec4533c34173e6`, Tree `57da8170fab57f8ea8f45618fd40b2555ad05ae3`; der lokal geprüfte Code-/Testbestand ist darin unverändert festgehalten. |
| Vorher-/Nachher-Matrix | Dieselbe neue Drei-Modus-Matrix auf dem Produktionscode von `bade0e33`: 2 fehlgeschlagen (`HTTPS_JSON`/`LOCAL_FILE`: 115 statt 101), 1 bestanden (Public), 3 bewusst deselektiert. Nach der begrenzten Modusbedingung: 3 bestanden, 3 bewusst deselektiert. Der Hash der Matrixdatei ist zwischen diesen beiden Läufen identisch. Dies ist der gezielte Rot/Grün-Nachweis, kein vollständiger Lauf der Schedulerdatei oder Gesamtsuite. |
| Neue gezielte Gesamtsuite | **344 bestanden, 0 Fehler/Skips/Deselektionen**, 1 bestehender Starlette/AnyIO-Deprecationhinweis, 10.90 s; keine automatischen Testretries. Die beiden neu angelegten Testdateien enthalten jetzt 35 Fälle (25 Client-/10 Kompositionsfälle). Gegenüber dem historischen 322er-Lauf: vier ergänzte Fälle und 18 bereits vorhandene Tests zur automatischen Quellenwahl zusätzlich ausgeführt. |
| Vollständige statische Backendprüfungen | Ruff bestanden; Black: 968 Dateien unverändert; mypy: 552 Quelldateien ohne Befund. `git diff --check` bestanden. Keine Dependencies, Prüfeinstiege oder Assertions abgeschwächt. |
| Vollständige Gates | Bestehende Einstiege unverändert gegenüber `5e9ede2` und `bade0e33`; neue finale PR-Checks am neuen Head nachweisen. Frühere grüne Runs belegen ausschließlich ihren damaligen Head. |

Die neue Drei-Modus-Abnahme verwendet weiter echte Runtime, Resolver,
Retained-Provider, Adapter und Client mit synthetischem Transport und eigener
temporärer SQLite. Bei monoton 100/101 und Cache-TTL 300 s ist folgendes Verhalten nachgewiesen:

| Modus | Resolver / `_pace()` | Tatsächliches Warten / zweiter Read | HTTP / Datei | Hit-Zeit |
|---|---|---|---|---|
| `PUBLIC_WEBSITE` | 2 / 2 | 14 s / 115 | 2 / 0 | Zwei verschiedene ISIN-Misses; zweiter Abruf `NOW+15` |
| `HTTPS_JSON` | 2 / 0 | 0 s / 101 | 1 / 0 | Snapshot-Hit behält `retrieved_at=NOW` |
| `LOCAL_FILE` | 2 / 0 | 0 s / 101 | 0 / 1 | Snapshot-Hit behält `retrieved_at=NOW` |

Originalkurszeiten bleiben in allen Modi erhalten. Die Aufruf-, Sleep- und
HTTP-/Dateizähler werden getrennt bewertet; keine neue Produktionsinjektion ist
dafür erforderlich. Der Client-/Fehlervertrag und die unveränderten Lane-,
Same-Cycle-, Konkurrenz- und Lifecyclefälle werden in der neuen gezielten Suite
erneut erfolgreich geprüft. Ein vorhandenes Public-Testdouble erhält dafür ausdrücklich
`settings.source_mode`; seine fachliche Assertion bleibt erhalten.

Die Rot/Grün-Matrixdatei hatte in beiden gezielten Läufen SHA256
`1bc948fd2d6d0cdaa45d47a062515d0668da7f28ee2160947fd4145814a18cfb`.
Anschließend kamen die vier zusätzlichen Ablauf-/Fehlerfälle hinzu. Der lokale
Dateifehlerfall belegt per direktem `_warrant()`-Aufruf die erneute
Clientzugriffsbereitschaft bei 460/461, keine automatische Jobfälligkeit dort.
Die normale automatische Fälligkeit ist separat im HTTPS-`_job()`-Fall geprüft.

Die Fortschreibung der unten historisch erhaltenen Kriterien ist damit:

| Kriterien | Aktuelle Einordnung |
|---|---|
| A01 | Die zuvor offene Snapshot-Semantik ist durch die ausdrückliche Nutzerentscheidung geklärt. |
| A05 / A12 | Begrenzte Produktionsänderung mit identischem Drei-Modus-Test vor/nach Änderung; neuer Commit und Gesamtlauf sind oben getrennt zugeordnet. Die Aussage „keine Produktionsänderung“ gilt ausschließlich für den C-Vorherstand. |
| A02–A04 / A06–A11 | Bestehende Route-, Client-, Datenqualitäts-, Fehler- und Lifecyclegrenzen bleiben maßgeblich. Ihre erneute erfolgreiche Ausführung am neuen Stand ist oben nachgewiesen; die 400/401→700/701-Fälligkeiten werden ausdrücklich geprüft. |
| A13 / A14 | Eigener bestehender Aufgabenbranch, betroffene Dokumentationsfelder und unveränderte Gates; finale CI muss den neuen Head prüfen. Keine Integration, Release-, Liveprovider- oder PC-Abnahme daraus ableiten. |

<a id="entscheidung-und-prüfidentität"></a>
## Historischer C-Stand: Entscheidung und Prüfidentität

**Damals Ergebnis C: gezielt offene Entscheidung, keine Produktionsänderung.**
Public-Pacing blieb erhalten. Die zusätzliche Schedulerpause vor zulässigen
HTTPS-/Datei-Cachetreffern war reproduziert, aber durch die gelesenen Verträge
weder ausdrücklich ausgeschlossen noch als separat notwendige Regel bestätigt.
Deshalb wurde sie in diesem ersten Schnitt nicht als bewiesener Fehler entfernt.
Die unabhängige Prüfung, synthetische Charakterisierung und Dokumentation waren
durchgeführt; die Snapshot-Schedulerregel war bis zur obigen Entscheidung offen.

| Identität | Geprüfter Stand |
|---|---|
| Repository / Remote | `https://github.com/burckhju/trading-workspace.git` |
| Ausgangs-`main` | `5e9ede2dc29f52eaff601d30614df6bc9c25c426`, Version `1.5.11` |
| Ausgangs-Tree | `303e56c078efd578e6e147edcf2ebac6accf6ba5` |
| Eigener Arbeitsbranch | `fix/market-data-source-mode-pacing`, eigener frischer Checkout |
| Code-/Testcommit | `3d47732665c8b66984923d88a65cf99e74d96791` |
| Code-/Test-Tree | `1b8dd1badb32e9a9d017ffd44656065f1021ac4b` |
| Dokumentationshead des C-Stands | `bade0e33a67e21b9d2a7e504a798e95ba619dcd0`, Tree `563776df6a6103cb66e2411ace53297416f5722b` |
| Produktionsdiff im C-Stand | Kein Produktionscode geändert; zwei neue Testdateien, anschließend der damalige Dokumentationsschnitt |
| Integration | Aufgabenbranch/Draft-PR; kein Merge, Release, Tag oder PC-Update beauftragt |

`main` wurde vor dem Anlegen des Remote-Arbeitsbranches erneut auf denselben
Commit geprüft. Der damalige Dokumentationshead `bade0e33` und seine PR-Checks
sind vom lokalen Code-/Testnachweis `3d477326` sowie vom neuen Prüfstand getrennt
zu lesen. Ein Dokumentationscommit ist kein zusätzlicher Testlauf.

Gelesen: README, Development Guide, relevante Architektur-/Roadmap-/Katalog-/
Backlog-/Traceabilityabschnitte, Frankfurt- und Schedulerbetriebsvertrag,
einschlägige ADRs, Konfiguration, Container, Scheduler/Runner, Resolver/Retention,
Adapter/Client/Configure/Public/Schema, interaktive und CLI-Consumer sowie Tests,
Manifeste und bestehende Workflows. Im vollständigen Checkout wurde keine
`AGENTS.md` gefunden. Historische Installationsangaben wurden nicht als aktueller
Betriebsnachweis verwendet.

## Zuständigkeit, alte PRs und Parallelstränge

Dieser Schnitt umfasst Quellenmodus, vorhandenes Schedulerpacing, Client-/
Adaptergrenzen und passende Regressionen. Performance, Währungsresolver,
Trade-/Execution-/Managementverträge, Journal/Evidence/Lessons, Navigation,
Frontendumbau und allgemeine CI-Aufteilung bleiben außerhalb.

| PR | Am 21.10.2026 gelesener Head / Zustand | Einordnung |
|---|---|---|
| [#225](https://github.com/burckhju/trading-workspace/pull/225) | `79f607810196f172870a7127567f25109916e06a`, offen/Draft | Vollständige drei Datei-Patches gelesen. Lane-/Retry-Anteil inzwischen auf `main`; übrig bleiben Quellenmodusabsicht und separater Workflowvorschlag. |
| [#235](https://github.com/burckhju/trading-workspace/pull/235) | `86314c869147e6eba81c79fd7c2c88a28d6fa155`, offen, kein Draft | Zwei Patches gelesen; beschreibt ausdrücklich keine Frankfurt-Pacingänderung. Main berücksichtigt beim Same-Cycle-Retry bereits den Quote-Beginn, auch wenn das Quote-Ende nach Discovery liegt. |
| [#268](https://github.com/burckhju/trading-workspace/pull/268) | `eec41d6e00957625f9c836be4857ad08dbee5002`, offen/Draft | Gemeinsame Backlog-/Traceabilitydateien; dortige Hunks betreffen andere Nachweis-/Releasefelder, keine TC-001-Teilfähigkeit. |
| [#269](https://github.com/burckhju/trading-workspace/pull/269) | `58c842c367b0ce75fa8e445e908fd3e78ff8477c`, offen/Draft | Journal-/Evidence-Testjob, keine Übernahme. |
| [#270](https://github.com/burckhju/trading-workspace/pull/270) | `de413843a814ac6a1016f474f3e5366cd81ea96a`, offen/Draft | Gemeinsame Backlogdatei, aber PB-019-Statistiken; keine Übernahme. |
| [#204](https://github.com/burckhju/trading-workspace/pull/204) | `d279db33716ff0070c12ccd44f02036f137fa566`, offen/Draft | Navigation; Restbericht ausschließlich lesend herangezogen. |

Der [Restbericht auf dem #204-Head](https://github.com/burckhju/trading-workspace/blob/d279db33716ff0070c12ccd44f02036f137fa566/docs/reviews/LEGACY_PR_REMAINDERS_2026-10-20.md)
ist kein Dokument auf `main` und kein neuer Testlauf. Die Kommentar-/Review-
Timelines von #225/#235 waren leer. Unter zwölf offenen PRs sowie den vollständig
gelesenen relevanten Branchsuchseiten wurde kein aktiver exakter Nachfolger
gefunden; vor Branchanlage blieb die Suche nach `source-mode` leer.

Der alte #225-Filter war `XFRA` plus Publicmodus. Heute bestimmt die ausgewählte
aktive, validierte **Providerroute** den Aufruf. Ein MIC-Filter wird nicht
zurückübertragen. Selbst #225 ließ `_configure_frankfurt()` mit `_pace()` stehen;
er belegt keine allgemeine Abschaffung nichtöffentlicher Wartezeiten. Alte PRs
werden weder geschlossen noch als insgesamt ersetzt erklärt. Keine Änderungen
aus Parallelsträngen sind übernommen.

## Getrennte Verantwortungsebenen

| Ebene | Verantwortung und Zeitbasis im C-Vorherstand |
|---|---|
| Jobintervall | `_job()` setzt `_due` nach Abschluss mit monotoner Uhr. Warrant-, Discovery- und Underlyingintervalle sind getrennt; keine Startzeitgarantie. |
| Schedulerpacing | `_pace()` wartet auf das Maximum aus eigener Restfrist und `request_delay_seconds()`. Danach setzt es den eigenen nächsten Slot auf `now + max(request_spacing_seconds, refresh_interval_seconds)`. |
| Clientbudget | Ein `FrankfurtSnapshotClient` je Container mit echtem async Lock und `_next_fetch`. Tatsächlicher Zugriff erst nach dessen Prüfung; kein Budget je Instrument. |
| Cache | Public: exakte ISIN; HTTPS/Datei: `snapshot`. Aktiver Refresh: Container-TTL gleich Warrantintervall, standardmäßig 300 s. Ohne Refresh: Clientstandard gleich Abrufintervall. Ein Cachehit setzt keine Abrufzeit oder Frist neu. |
| Fehler | Public-404: Instrumentfrist plus gewöhnlicher Quellabstand. Snapshot-404 und übrige Quellfehler: mindestens 60 s; längeres gültiges Retry-After bleibt erhalten. 401/403 sperren die Quelle und löschen positive Cachewerte. |
| Datenqualität | Originalkurszeit, Snapshotzeit, UTC-Abrufzeit, Bewertungszeit und Job-Prüfzeit bleiben verschieden. Monotone Werte steuern Abstände, nicht Marktdatenzeitstempel. |

Die technischen Rechte-/Cache-/Fehlerregeln stehen im
[Frankfurtvertrag](../frankfurt-quotes.md), die Intervall-/Pacing-/Leaderregeln in
[Automatic market-data refresh](../automatic-market-data.md). Die dortige
Beschreibung eigener Queue-Pacinguhren entschied die Ausnahme für
Snapshot-Cacheleser damals nicht explizit; der Nachtrag klärt sie jetzt. Der ältere
[ADR-S3-006](../decisions/ADR-S3-006-RESILIENCE.md) gehört zum damaligen
EODHD-Resilienzschnitt; seine drei Versuche und 30-s-Retry-After-Grenze werden
nicht auf Frankfurts späteren Vertrag übertragen.

## Aufrufinventar

Die folgende Tabelle beschreibt den C-Vorherstand.

| Aufruf → Owner | Modus → Cache-Schlüssel | Tatsächlicher Zugriff | Limit / Zeitquelle | Fehler-/Wiederholung / Nachweisgrenze |
|---|---|---|---|---|
| `_warrant` → Refresh → `resolve_selected` → Retained-Provider → Containeradapter | Alle; ISIN oder `snapshot` | Public-GET, Snapshot-GET oder begrenztes Dateiöffnen, nur wenn Client es zulässt | Scheduler + geteilter Client; monotone Fristen, originale UTC-Daten | Resolver meldet Fehler; Retention nur als offengelegte historische Evidenz. Bestehende Persistenz-/Quellenreconciliation-Seiteneffekte bleiben. |
| `_configure_frankfurt` → `configure_warrant` | Nur Public; ISIN | Derselbe Containerclient | `_pace` + Lock/Budget | Strikte Verifikation ohne historischen Erfolgsfallback; `apply=True` kann Referenzen/Listings/Mappings schreiben. |
| Bewertung/Monitoring → `build_warrant_quote_resolver` | Alle; ISIN oder `snapshot` | Derselbe Containeradapter/-client | Clientbudget; kein neuer Client pro Instrument | Bestehende Provider-/Retention-/Frischeregeln. |
| Frankfurt-Listing-GET → `inspect` | Alle; ISIN oder `snapshot` | Möglich, nach Route-/Identitätsprüfung | Geteilter Client, keine zusätzliche Schedulerpause | Kein pauschal transportfreier Diagnoseweg. |
| Frankfurt-Health-GET | Alle | Kein Transport | Liest Restcooldown/Fehlerzahl | Verändert keine Deadline. |
| `probe_unique_frankfurt_quotes._apply` | Nur Public; ISIN | Resolver über Container | Liest `request_delay_seconds`, wartet; Client prüft erneut | Bestehender Public-only-Consumer; kein neues Budget. |
| Standalone Configure-/CSV-Probe | Configure nur Public; CSV alle Modi | Eigenständiger Prozess/Client; normalisierter Snapshot einmal vor CSV-Zeilenschleife | Eigenes prozesslokales Budget | Public-CSV bei Throttle: ein konfiguriertes Warten, genau ein weiterer Versuch. Keine gemeinsame Grenze mit gleichzeitigem API-Prozess behauptet. |

Alle Produktionsconsumer von `request_delay_seconds()` sind `_pace()`, das
Discovery-Throttle-Deferral in `_job()`, die Healthanzeige und
`probe_unique_frankfurt_quotes._apply`. `_pace()` selbst wird nur von
`_configure_frankfurt()` und ausgewählten Frankfurt-Quoterouten benutzt.

## Soll–Ist und Entscheidung je Modus

Diese Tabelle hält den C-Stand fest. Die Snapshot-Entscheidungen in der letzten
Spalte sind durch den obigen Nachtrag abgelöst.

| Modus | Belegter Sollvertrag | Code / Ist | Echte Zugriffe im Zweilisting-Szenario | Erforderliche Wartebedingung | Entscheidung |
|---|---|---|---|---|---|
| `PUBLIC_WEBSITE` | Exakte ISIN/XSC, Freigaben, gemeinsame Quellgrenze; Cachehit ist kein Providerabruf | Publiccache je ISIN, gemeinsamer Lock/Cooldown; Scheduler wartet vor Frankfurtquote und Discovery | 2 HTTP, 0 Datei | Neuer uncached Abruf erst nach gemeinsamem Budget; Instrument-/Quellsperren zusätzlich | **No-change:** kein belegter Korrekturbedarf am Public-Pacing. |
| `HTTPS_JSON` | Freigegebener HTTPS-Host/Quelle, Token nur im Header, keine Redirects, Timeout/Größe/Schema/Delay; gemeinsamer Snapshot | Schlüssel `snapshot`, Cache vor Transport; Scheduler wartet trotzdem vor jedem ausgewählten Frankfurtresolver | 1 HTTP, 0 Datei, zweiter Read HIT | Download erst bei Cacheablauf und freiem Clientbudget; Fehler-/Retry-After-Frist erhalten | **Gezielt offen:** zusätzliche Schedulerpause vor zulässigem Snapshot-Hit fachlich entscheiden. |
| `LOCAL_FILE` | Explizite lokale JSON-Datei, begrenztes Lesen und identische Snapshot-/Frischeregeln; kein öffentlicher HTTP-Zugriff | Schlüssel `snapshot`, `to_thread(_read_file)`, höchstens `max_response_bytes + 1`; gleiche Zusatzpause | 0 HTTP, 1 Datei, zweiter Read HIT | Neuer Dateiread erst bei Cacheablauf und freiem Clientbudget; Dateifehler mindestens 60 s Backoff | **Gezielt offen:** dieselbe Schedulerregel entscheiden; lokale Datei begründet keine unbegrenzten Reads. |

### Entscheidungsfähige Varianten

Die folgenden Varianten wurden im C-Stand vorbereitet. Variante 2 ist
inzwischen ausdrücklich gewählt; Variante 1 wird nicht umgesetzt.

1. **Bestehende Zusatzpause beibehalten und ausdrücklich bestätigen.** Sie gilt
   dann auch für Snapshot-Cacheleser. Abwärtskompatibilität ist vollständig;
   Cachezugriffe können weiterhin hinter eigener Schedulerfrist oder
   Quellcooldown warten. Kein Produktionsdiff erforderlich.
2. **Zusatzpause ausschließlich für normalisierte Snapshot-Quoteaufrufe
   entfallen lassen.** Publicquote und Publicdiscovery bleiben unverändert.
   Gemeinsamer Client, TTL, tatsächliches Ladebudget, negative Caches,
   Retry-After, Rechte und Datenqualität bleiben zwingend. Die beiden Leser des
   Tests könnten den vorhandenen Snapshot ohne die zusätzliche 14-s-Pause
   verarbeiten; der direkte Clienttest belegt dabei einen tatsächlichen Read.
   Im C-Stand war dies noch keine implementierte oder genehmigte Änderung.
   Schnellere Jobabschlüsse können spätere Fälligkeiten und Reloadzeitpunkte verschieben;
   gleiche Gesamtzugriffszahlen über beliebige lange Katalogläufe werden nicht
   zugesagt. An Cache-/Fehlergrenzen wäre dieser gewählte Pfad separat vor/nach
   zu qualifizieren.

Die damals offene, nun entschiedene Frage war genau die Semantik von
`REQUEST_SPACING_SECONDS` für Snapshotresolver einschließlich Cachehits.
Es fehlt keine pauschale erneute
Freigabe bereits erlaubter Quellen; aus Konfigurationsdefaults wird aber auch
keine zusätzliche externe Nutzungsberechtigung abgeleitet.

## Synthetische, reproduzierbare Ergebnisse

Die folgenden Ergebnisse gelten für den historischen Testcommit `3d477326`.
Alle Zahlen sind Testparameter, keine Providerempfehlung. Monotone Startzeit
100, Clientintervall und Schedulerabstand 15 s, Scheduler-Cache-TTL 300 s:

| Szenario | Beobachtung und Assertion |
|---|---|
| R1/R2 Schedulerkomposition | Erster Read bei 100; zweiter bei 101 angefordert, eine Sleepanforderung 14 s, Aufruf bei 115. Je Modus 2 Resolver- und 2 Pacingaufrufe. Public 2 HTTP/MISS; HTTPS 1 HTTP; Datei 1 Read. Snapshot-Hit behält `retrieved_at=NOW`; neuer Publicabruf erhält `NOW+15`. Originalkurse bleiben unverändert. |
| R1 direkter Client / Cacheablauf | Drei Modi × TTL-Standard/300: Hit bei 101 und unmittelbar vor Ablauf; exakt beim Ablauf ein neuer Read. Zweite Public-ISIN im gesperrten Slot wird gedrosselt; beide Snapshotidentitäten teilen ein Objekt. |
| R3 Retry-After | HTTPS-Erfolg bei 100, 429/503 bei 115 mit 120 s: Deadline 235. Leser bei 116, 130, 174 und 234.999 erzeugen keinen neuen Zugriff; Historienread verändert weder Deadline noch Abrufzeit. Bei 235 genau ein neuer Zugriff. Public-/Access-/404-Fälle zusätzlich bestehende Regressionen. |
| R4 Konkurrenz nach Vorprüfung, ohne frühere Beobachtung | Echter `_pace` bei 100, dann fremder Reader derselben Clientinstanz. Discovery: `DEFERRED`, kein Erfolgstimestamp, nächste Fälligkeit 115. Quote: `MISSING`, Quellversuch `ERROR/FRANKFURT_REQUEST_THROTTLED`, keine Quote; reguläre Quote-Fälligkeit 400. Vorprüfung bei 114 erzeugt keinen weiteren Transport. |
| R5 alte Datei | Originalkurs und Snapshot 901 s alt. Read bei 100, Hit bei 101, tatsächliche Reads bei 115/130 und jeweils geänderte mtime: weiterhin STALE, Originalzeit gleich, Alter wächst. Neue Abrufzeit ausschließlich bei tatsächlichem Read. |
| R5 Dateifehler | Nach warmem Erfolg fehlend/übergroß/ungültig/fremde Quelle/falscher Feed-Delay: ein Fehlerread bei 115, Deadline 175, kein erneuter Read vorher, nichttransienter Cache nicht wiederverwendbar; kontrollierte Erholung bei 175. |
| R6 Lock / Cancellation | Zwei mit Events koordinierte Leser: ein echter Clientlock, ein abgefangener HTTP-Zugriff. Abbruch des wartenden Lesers lässt Loader und Folgehit funktionieren. Abbruch während Schedulerpause joint den Lane-Worker; kein automatischer Neustart, späterer expliziter Lauf funktioniert. |

Bestehende historische Retention kann separat eine verfügbare Analysebeobachtung
mit ursprünglichen Zeitstempeln und explizitem `refresh_error` liefern. R4 prüft
den Fall ohne frühere Beobachtung und schließt diese transparente historische
Wiederverwendung nicht aus. Ein erfolgreicher Job beweist keinen frischen Marktpreis.

Die neue Schedulerdatei benutzt echte Runtime, `build_warrant_quote_resolver`,
Retained-Provider, Adapter und Client. Nur Katalog/Transport/Zeit sind kontrolliert;
Identitäts-/Routen-SQL läuft auf eigener temporärer SQLite. Der Container wird
direkt mit der aktuellen Build-TTL von 300 s verdrahtet. Das ist kein eigener
Beweis für PostgreSQL-Rowlocks oder die Containerfactory. Job-UTC bleibt echte
Wallclock; getestet sind relative `next_run_at`-Abstände und die separat
injizierten monotonen Deadlines. Alle Grenzen sind prozesslokal.

## Ausgeführte lokale Prüfungen und Grenzen

Dieser Abschnitt bewahrt die lokalen Ergebnisse des C-Vorherstands. Ergebnisse
der anschließenden Produktionsänderung werden ausschließlich im Nachtrag ergänzt.

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Bestehende gezielte Basisfälle, unveränderter Produktions-/Testbestand von `5e9ede2` | 239 bestanden, 1 bestehender Starlette/AnyIO-Deprecationhinweis; 4.68 s |
| Neue Clientdatei | 25 bestanden; drei Modi, Cache, Retry-After, Lock, lokale Fehler und Freigaben |
| Neue Schedulerkomposition | 6 bestanden; drei Modi, zwei Budgetkonkurrenzen und Shutdown/Wiederanlauf |
| Gemeinsame gezielte Suite auf Code-/Testcommit `3d477326` | 322 bestanden, 0 fehlgeschlagen/übersprungen/deselektiert, 1 bestehender Warnhinweis; 8.47 s. Keine Addition fremder PR-Testzahlen. |
| Ruff vollständig über App, Unit- und Integrationstests | Bestanden nach Korrektur ausschließlich der Importreihenfolge in den beiden neuen Dateien |
| Black vollständig über dieselben Pfade | Bestanden; 968 Dateien unverändert formatiert |
| mypy vollständig über `app` | Bestanden; 552 Quelldateien |
| `git diff --check` | Bestanden |

Frühere nichtgrüne/unvollständige Läufe bleiben getrennt: normaler Sandboxlauf
der Basis sowie ein einzelner Basis-Dateitest und der erste neue Clientlauf
wurden nach Dateitest-Timeout/Executor-Teardownblockade abgebrochen (Exit 130).
Eine unabhängige Minimalprobe `asyncio.to_thread(lambda: bytes)` reproduzierte
den Shutdownstillstand ohne Anwendungscode. Dieselbe Probe in der regulär
freigegebenen Ausführungsumgebung endete erfolgreich; dort bestanden die
unveränderten Tests. Kein Timeout, keine Assertion und kein Produktionscode
wurde dafür geändert. Ein Zwischenlauf nur HTTP/Public bestand mit 14 Fällen
und 10 ausdrücklich deselektierten Dateifällen; er ist kein Vollnachweis. Ein
24-Fälle-Lauf vor Ergänzung der Feed-Delay-Regression und die anfänglichen
Ruff-Importfehler werden nicht als finaler Stand ausgegeben. Es gibt keine
automatischen Testretries oder hinzugefügten Skips.

Lokal vorhanden: Python 3.12.14 und eigene `.venv` aus unveränderten
`requirements-dev.txt`; Node 24.19.0/npm 11.9.0 entsprechen nicht dem exakten
Frontendpin 22.16.0/10.9.2. PostgreSQL/Docker/Compose fehlen. Relevante
DB-/Docker-/Compose-Umgebungsvariablen waren vor Teststart unset; keine private
`.env` wurde benutzt. Alle Datei-/SQLitefälle liegen in eigenen Testverzeichnissen,
HTTP wird durch MockTransport abgefangen.

**Nicht lokal ausgeführt:** `bash scripts/check-backend.sh` als vollständiges
Unit-/PostgreSQL-/Coveragegate, `bash scripts/check-frontend.sh`,
`bash scripts/run-e2e.sh`, Image-/Renderer- und Owner-E2E-Gates. Die Integration-
Fixtures können Datenbank-Downgrades ausführen; der E2E-Cleanup löscht seine
Testvolumes. Ohne nachgewiesene eigene Ressourcen wurden diese Skripte nicht
gestartet. Keine Ersatz-DB, keine fremden Volumes, keine Workflowänderung.

Die vorhandene PR-CI bleibt zuständig für Backend quality (einschließlich
PostgreSQL und 85-%-Coverage), restrictive-umask image, issuer renderer sandbox,
Frontend quality, End-to-End smoke, realized gross owner und Version publication
guards. Der Version-Tagjob ist bei PRs planmäßig nicht anwendbar. Ihre tatsächlichen
Ergebnisse werden für den finalen PR-Head separat gelesen und berichtet; alte
grüne Checks anderer Heads zählen nicht. Das gelesene aktive `main`-Ruleset
`20249841` verlangt einen PR, gelöste Reviewthreads sowie `Backend / quality`,
`Frontend / quality` und `End-to-End / smoke` mit aktueller Basis. Der zusätzliche
klassische Branch-Protection-Endpunkt antwortete mit 403; dies wird nicht als
fehlender Schutz interpretiert. Kein Bypass ist vorgesehen.

### Gezielten Code-/Teststand reproduzieren

Auf dem oben benannten Commit, Python 3.12 und unveränderte Devrequirements,
aus `backend/` mit eigenem freien temporären Verzeichnis:

```bash
PYTHONPATH="$PWD:$PWD/.." \
TRADING_WORKSPACE_MARKET_DATA__EODHD__ENABLED=false \
TRADING_WORKSPACE_MARKET_DATA__EODHD__API_KEY= \
TRADING_WORKSPACE_MARKET_DATA__FRANKFURT__ENABLED=false \
TRADING_WORKSPACE_MARKET_DATA__REFRESH__ENABLED=false \
TRADING_WORKSPACE_POSITION_MONITORING__ENABLED=false \
TRADING_WORKSPACE_MARKET_DATA__STUTTGART_DELAYED__ENABLED=false \
TRADING_WORKSPACE_NOTIFICATION__TELEGRAM__ENABLED=false \
.venv/bin/python -m pytest -c pyproject.toml \
  ../tests/unit/backend/providers/frankfurt_quotes \
  ../tests/unit/backend/features/market_data/test_refresh.py \
  ../tests/unit/backend/features/market_data/test_refresh_backlog.py \
  ../tests/unit/backend/features/market_data/test_refresh_discovery.py \
  ../tests/unit/backend/features/market_data/test_refresh_lanes.py \
  ../tests/unit/backend/features/market_data/test_refresh_source_modes.py \
  ../tests/unit/backend/features/market_data/test_issuer_refresh_lane.py \
  ../tests/unit/backend/features/market_data/test_retained_quotes.py \
  ../tests/unit/backend/features/position_monitoring/test_provider_routing.py \
  ../tests/unit/backend/features/position_monitoring/test_quote_sources.py \
  ../tests/unit/backend/features/position_monitoring/test_quote_freshness.py \
  ../tests/unit/backend/test_dependency_injection.py
```

## Abnahmekriterien A01–A14

Die Zuordnung wurde vor Ergänzung der Tests festgelegt. `SM` bezeichnet
`tests/unit/backend/features/market_data/test_refresh_source_modes.py`, `SC`
bezeichnet `tests/unit/backend/providers/frankfurt_quotes/test_source_mode_contract.py`.
Diese Tabelle bewahrt die Bewertung des ursprünglichen C-Prüfauftrags auf
`3d477326`/`bade0e33`, nicht den Fertigstellungsgrad von Bereich 2. Die aktuelle
Fortschreibung steht im Entscheidungsnachtrag; Aufgabenstatus bleibt im Backlog.

| ID | Ergebnis / konkreter Nachweis |
|---|---|
| A01 | **Teilweise offen:** Vertrag und Aufrufpfad aller Modi belegt; Public No-change. Fachliche Entscheidung zur Snapshot-Zusatzpause fehlt, wie oben abgegrenzt. |
| A02 | **Qualifiziert:** bestehende `test_issuer_refresh_lane`, `test_adapter_api`, `test_provider_routing`; SM verwendet echte aktive/validierte Routen und Identitäts-SQL. Kein neuer MIC-Filter. |
| A03 | **Qualifiziert:** SC `test_mode_cache_hits_expiry_and_identity`, lokale Fehler und HTTPS-Recovery; bestehende `test_last_success`; SM zählt Resolver/Pacing/Sleep/Transporte getrennt. |
| A04 | **Prozesslokal qualifiziert:** Publicbudgetregressionen, echter Clientlock in SC; SM `test_slot_consumed_after_pacing_is_bounded_and_never_reported_as_success` für Discovery und Quote. |
| A05 | **Grenzen qualifiziert; Änderung offen:** Snapshot-Hits/TTL/Dateireads belegt. Keine Pause entfällt; Variante 2 benötigt die benannte Entscheidung und eigene Vorher-/Nachher-Prüfung. |
| A06 | **Qualifiziert:** `test_instrument_backoff`, `test_last_success`, `test_client`, SC HTTPS-Retry-After und fünf lokale Fehler; kein neuer Quellenfallback. |
| A07 | **Qualifiziert:** SM Konkurrenzfälle plus `test_refresh_backlog`; Discovery DEFERRED und Quote MISSING/ERROR ausdrücklich getrennt, keine unkontrollierte Wiederholung. |
| A08 | **Qualifiziert:** SC alte Datei/mtime/Cachezeit; SM Originalzeiten; `test_schema`, `test_public`, `test_reference_analysis`, Retention und Frischeregressionen. |
| A09 | **Qualifiziert:** unveränderte `test_refresh_lanes`/`test_issuer_refresh_lane`, einschließlich Quote-Beginn vor und Quote-Ende nach Discovery. Keine neue Lane oder zusätzliche Parallelisierung. |
| A10 | **Prozess-/Lifecyclegrenze qualifiziert:** SM Pacing-Cancellation, SC Lock-Cancellation, bestehende Stop/Heartbeat/Unlock-Tests. Leaderdatenbank dort gefakt; kein neuer verteilter PostgreSQL-Nachweis behauptet. |
| A11 | **Qualifiziert:** SC drei Modi × drei Freigabeschranken, bestehende Host-/URL-/Public-Konflikt-/Mappingtests; null echte Provideraktivierungen. |
| A12 | **Qualifiziert als Charakterisierung:** unveränderter Produktionscode, exakt benannter Testcommit; kein behaupteter Rot/Grün-Fix. Kontrollierte Uhren/Events/Transporte. |
| A13 | **Abgegrenzt:** eigener Checkout/Branch, fremde PRs nur gelesen; gemeinsame Dokumente nur betroffene Abschnitte. Kein Integrationsmerge und keine Nutzerbestandsänderung. |
| A14 | **Lokal teilweise; CI separat:** gezielte Tests und vollständige statische Backendgates ausgeführt. Vollständige Projekt-/Container-/Browsergates lokal nicht ausgeführt; finale PR-CI muss headgebunden ausgewiesen werden. |

## Unveränderte Grenzen und Übergabe

Keine Änderung an Providerreihenfolge, Quellenwahl, Mappingvalidierung,
Kursidentität/Währung/Preisart, Retention, Intervall-/Konfigurationsdefaults,
Fehlerwartezeiten, Leader-/Workerstruktur oder Shutdown. Kein zweiter Scheduler,
kein neuer fachlicher Owner und keine neue FT-/PB-ID. Die weiterhin serielle
Lane wird nicht als vollständig unabhängige Ausführung aller Quellen bezeichnet.

Reale Bestände, Providerzugänge, Zustimmungen, Benachrichtigungen, Modelle,
Releases und PC-Installation wurden **nicht verändert**. Die vorhandenen
Seiteneffekte von Refresh/Discovery/Retention wurden inventarisiert und im Test
ausschließlich mit synthetischen Ressourcen ausgeführt. Die begrenzte
Verhaltensänderung ist inzwischen durch den obigen Nachtrag beauftragt.
Integration und Livebeobachtung bleiben davon getrennte Schritte.
